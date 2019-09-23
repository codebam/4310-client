import socket
import select
import sys
import threading
from typing import Tuple

VERSION = "FC1"
user_input = [None] # global for input between threads

class Client:
    def init(self, username=None, userid=None):
        self.username = username
        self.userid = userid

class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.clients = [Client]

    def connect(self):
        # connect and set ip and clients
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(None) # make socket non-blocking
        self.sock.connect((self.ip, self.port))
        self.reciever = threading.Thread(target=self.recieve, args=(user_input))
        self.reciever.daemon = True
        self.reciever.start()
        self.connected = True
        print("connected!")

    def login(self, username):
        self.sock.send("LOGN {0} {1}\n".format(username, VERSION).encode())
        data = self.sock.recv(256)
        self.id = data[4:].strip().decode()

    def execute(self, command):
        print(command)
        words = command.split()
        verb = words[0].lower()
        if verb == "send":
            self.send(words[1], words[2])
        elif verb == "disconnect":
            self.disconnect()
        pass

    def disconnect(self):
        self.sock.send("GDBY\n".encode())
        self.connected = False

    def recieve(self, content):
        while True:
            data = self.sock.recv(256)
            if data != b'':
                print(data.decode())
    # pass onto verb functions

    def send(self, to, message):
        self.sock.send("SEND {0} {1}\n".format(to, message).encode())

    def new_client(self):
        pass

    def show_message(self):
        pass

class Message:
    def init(self, client_id, content):
        self.client_id = client_id
        self.content = content

def main():
    print("example commands:")
    print("""\nsend alice: hello
sendall: hello world
disconnect\n""")
    input("press enter to start...\n")

    print("connecting to server...")
    server = Server("127.0.0.1", 3333)
    server.connect()
    # open socket to server

    username = str(input("Enter your username: "))
    server.login(username)
    # initiate connection

    # start listening
    while server.connected:
        command = str(input("enter a command: "))
        server.execute(command)
    # show verb prompt
    print("connection closed.")

if __name__ == "__main__":
    main()
