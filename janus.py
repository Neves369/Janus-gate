import socket

IP = "192.168.x.x"
PORT = 443 # Ou 444, porta padrão do netcat

c = socket.socket((socket.AF_NET, socket.SOCK_STREAM))
C.connect((IP ,PORT))

while True:
    data = c.recv(1024).decode().strip()
    print(data)