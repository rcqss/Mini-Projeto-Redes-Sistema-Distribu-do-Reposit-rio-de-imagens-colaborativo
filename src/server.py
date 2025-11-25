import socket
import threading
import os
import json
from datetime import datetime
from PIL import Image

HOST = "0.0.0.0"
PORT = 5000
BASE_DIR = "imagens"       #pasta base onde as imagens serao salvas
META_FILE = "metadata.json"  #arquivo com historico de uploads

lock = threading.Lock()    #para acesso concorrente ao metadata na memoria



#funcoees auxiliares

def carregar_metadata():
    """Carrega histórico de arquivos do disco."""
    if not os.path.exists(META_FILE):
        return []
    with open(META_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_metadata(meta):
    """Salva histórico de arquivos no disco."""
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


metadata = carregar_metadata()


def recv_line(conn):
    """Lê dados do socket até encontrar '\\n'."""
    data = b""
    while True:
        ch = conn.recv(1)
        if not ch:
            return None  #conexao fechada
        if ch == b"\n":
            break
        data += ch
    return data.decode("utf-8")


def recv_all(conn, n):
    """Lê exatamente n bytes do socket (ou até a conexão fechar)."""
    data = b""
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    return data


def criar_thumbnail(path_origem, path_thumb, tamanho=(128, 128)):
    """Gera uma miniatura da imagem usando Pillow."""
    img = Image.open(path_origem)
    img.thumbnail(tamanho)
    img.save(path_thumb, "JPEG")



#handlers dos comandos

def handle_auth(conn, state, parts):
    """
    Comando: AUTH|username
    Define o usuário atual da conexão para registrar autoria.
    """
    if len(parts) >= 2:
        state["username"] = parts[1]
    conn.sendall(b"OK\n")


def handle_upload(conn, state, parts):
    """
    Comando: UPLOAD|nome_arquivo.jpg|tamanho_em_bytes
    Após o READY, o cliente envia os bytes da imagem.
    """
    if len(parts) != 3:
        conn.sendall(b"ERROR|Formato invalido\n")
        return

    filename = parts[1]
    try:
        size = int(parts[2])
    except ValueError:
        conn.sendall(b"ERROR|Tamanho invalido\n")
        return

    username = state["username"]
    user_dir = os.path.join(BASE_DIR, username)
    os.makedirs(user_dir, exist_ok=True)

    #avisa que esta pronto para receber os bytes
    conn.sendall(b"READY\n")

    # recebe os bytes da imagem
    file_bytes = recv_all(conn, size)
    filepath = os.path.join(user_dir, filename)
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    #cria thumbnail
    thumb_path = os.path.join(user_dir, f"thumb_{filename}")
    try:
        criar_thumbnail(filepath, thumb_path)
        has_thumb = 1
    except Exception as e:
        print("Erro ao criar thumbnail:", e)
        thumb_path = ""
        has_thumb = 0

    #registra metadados
    info = {
        "filename": filename,
        "author": username,
        "path": filepath,
        "thumb_path": thumb_path,
        "size": size,
        "has_thumb": has_thumb,
        "datetime": datetime.now().isoformat(timespec="seconds"),
    }

    with lock:
        metadata.append(info)
        salvar_metadata(metadata)

    conn.sendall(b"OK\n")


def handle_list(conn, state, parts):
    """
    Comando: LIST
    Retorna uma linha por arquivo e depois END.
    formato: nome|autor|data|tamanho|has_thumb
    """
    with lock:
        for info in metadata:
            line = f"{info['filename']}|{info['author']}|{info['datetime']}|{info['size']}|{info['has_thumb']}\n"
            conn.sendall(line.encode("utf-8"))
    conn.sendall(b"END\n")


def handle_download(conn, state, parts):
    """
    Comando: DOWNLOAD|nome_arquivo.jpg
    Servidor responde SIZE|tamanho e, após READY, envia os bytes.
    """
    if len(parts) != 2:
        conn.sendall(b"ERROR|Formato invalido\n")
        return

    filename = parts[1]
    with lock:
        info = next((m for m in metadata if m["filename"] == filename), None)

    if not info or not os.path.exists(info["path"]):
        conn.sendall(b"ERROR|Arquivo nao encontrado\n")
        return

    size = os.path.getsize(info["path"])
    conn.sendall(f"SIZE|{size}\n".encode("utf-8"))

    ready = recv_line(conn)
    if ready is None or ready.strip().upper() != "READY":
        return

    with open(info["path"], "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            conn.sendall(chunk)


def handle_view(conn, state, parts):
    """
    Comando: VIEW|nome_arquivo.jpg
    Igual ao download, mas envia a thumbnail.
    """
    if len(parts) != 2:
        conn.sendall(b"ERROR|Formato invalido\n")
        return

    filename = parts[1]
    with lock:
        info = next((m for m in metadata if m["filename"] == filename), None)

    thumb_path = info["thumb_path"] if info else ""
    if not thumb_path or not os.path.exists(thumb_path):
        conn.sendall(b"ERROR|Thumbnail nao disponivel\n")
        return

    size = os.path.getsize(thumb_path)
    conn.sendall(f"SIZE_THUMB|{size}\n".encode("utf-8"))

    ready = recv_line(conn)
    if ready is None or ready.strip().upper() != "READY":
        return

    with open(thumb_path, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            conn.sendall(chunk)



#conexao

def handle_client(conn, addr):
    print(f"[+] Conexao de {addr}")
    state = {"username": "anon"}  # estado associado àquele cliente

    COMMANDS = {
        "AUTH": handle_auth,
        "UPLOAD": handle_upload,
        "LIST": handle_list,
        "DOWNLOAD": handle_download,
        "VIEW": handle_view,
    }

    try:
        while True:
            line = recv_line(conn)
            if line is None:
                break  # cliente fechou conexão

            print(f"[{addr}] {line.strip()}")
            parts = line.strip().split("|")
            cmd = parts[0].upper()

            func = COMMANDS.get(cmd)
            if func is None:
                conn.sendall(b"ERROR|Comando desconhecido\n")
            else:
                func(conn, state, parts)
    finally:
        conn.close()
        print(f"[-] Conexao encerrada {addr}")


def main():
    os.makedirs(BASE_DIR, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor ouvindo em {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            # cada cliente e tratado em uma thread separada
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()


if __name__ == "__main__":
    main()
