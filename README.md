# Mini-Projeto-Redes-Sistema-Distribu-do-Reposit-rio-de-imagens-colaborativo
atividade proposta na cadeira de Introdução aos Sistemas Distribuídos e Redes de Computadores do CIn UFPE. 

Trabalho de Sistemas Distribuídos Equipe 01
Cliente-servidor usando Sockets TCP para um repositório colaborativo de imagens.

O servidor permite:
- Upload de imagens com registro de autor
- Listagem das imagens disponíveis (com histórico)
- Download de imagens
- Visualização de miniaturas (thumbnails)

O cliente se conecta ao servidor, envia comandos e interage via menu em linha de comando.

Tecnologias:
- Python
- Sockets TCP (`socket`)
- Threads (`threading`)
- Manipulação de imagens com **Pillow** (para thumbnails)
  

Estrutura do projeto

src/
 ├─ server.py   # Servidor TCP: trata AUTH, UPLOAD, LIST, DOWNLOAD, VIEW
 └─ client.py   # Cliente TCP: menu interativo e envio dos comandos

docs/
 └─ atividade.pdf  # Enunciado da atividade (opcional)

requirements.txt   # Dependências Python
README.md          # Este arquivo
.gitignore         # Arquivos/pastas ignorados no Git
