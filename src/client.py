import socket
import os

HOST = "127.0.0.1"  #endereço do servidor (localhost)
PORT = 5000

#funcoes auxiliares
def recv_line(conn):
    """Lê dados do socket até encontrar '\\n'."""
    data = b""
    while True:
        ch = conn.recv(1)
        if not ch:
            return None
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


#cmds do client

def cmd_upload(sock):
    path = input("Caminho da imagem: ").strip()
    if not os.path.exists(path):
        print("Arquivo não existe.")
        return

    filename = os.path.basename(path)
    size = os.path.getsize(path)

    #envia cmd UPLOAD
    sock.sendall(f"UPLOAD|{filename}|{size}\n".encode("utf-8"))

    resp = recv_line(sock)
    if not resp or not resp.startswith("READY"):
        print("Erro do servidor:", resp)
        return

    #envia os bytes do arquivo
    with open(path, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            sock.sendall(chunk)

    resp = recv_line(sock)
    print("Resposta:", resp.strip())


def cmd_list(sock):
    sock.sendall(b"LIST\n")
    print("\n=== Imagens disponíveis ===")
    while True:
        line = recv_line(sock)
        if line is None:
            print("Conexão encerrada.")
            return
        line = line.strip()
        if line == "END":
            break
        filename, autor, data, tamanho, thumb = line.split("|")
        tem_thumb = "sim" if thumb == "1" else "não"
        print(f"- {filename} | autor={autor} | data={data} | tam={tamanho} bytes | thumbnail={tem_thumb}")


def cmd_download(sock):
    nome = input("Nome do arquivo para download: ").strip()
    if not nome:
        return

    sock.sendall(f"DOWNLOAD|{nome}\n".encode("utf-8"))
    resp = recv_line(sock)
    if not resp:
        print("Sem resposta do servidor.")
        return

    if resp.startswith("ERROR"):
        print(resp.strip())
        return

    _, size_str = resp.strip().split("|")
    size = int(size_str)

    sock.sendall(b"READY\n")

    data = recv_all(sock, size)
    out_name = "baixado_" + nome
    with open(out_name, "wb") as f:
        f.write(data)

    print("Arquivo salvo como", out_name)


def cmd_view(sock):
    nome = input("Nome do arquivo para visualizar (thumbnail): ").strip()
    if not nome:
        return

    sock.sendall(f"VIEW|{nome}\n".encode("utf-8"))
    resp = recv_line(sock)
    if not resp:
        print("Sem resposta do servidor.")
        return

    if resp.startswith("ERROR"):
        print(resp.strip())
        return

    _, size_str = resp.strip().split("|")
    size = int(size_str)

    sock.sendall(b"READY\n")

    data = recv_all(sock, size)
    out_name = "thumb_" + nome
    with open(out_name, "wb") as f:
        f.write(data)

    print("Thumbnail salva como", out_name)


#interface do menu

def menu():
    print("\n=== Cliente Imagens ===")
    print("1 - Upload")
    print("2 - Listar")
    print("3 - Download")
    print("4 - View (thumbnail)")
    print("5 - Sair")
    return input("Opção: ").strip()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        username = input("Informe seu usuário: ").strip() or "anon"
        s.sendall(f"AUTH|{username}\n".encode("utf-8"))
        resp = recv_line(s)
        print("Servidor:", resp.strip())

        while True:
            op = menu()
            if op == "1":
                cmd_upload(s)
            elif op == "2":
                cmd_list(s)
            elif op == "3":
                cmd_download(s)
            elif op == "4":
                cmd_view(s)
            elif op == "5":
                print("Saindo...")
                break
            else:
                print("Opção inválida.")


if __name__ == "__main__":
    main()
