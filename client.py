import socket
import select
import sys
import threading
from typing import Tuple

VERSION = "FC1"
user_input = [None] # global for input between threads

class Client:
    def __init__(self, username=None, userid=None):
        self.username = username
        self.userid = userid

class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.clients = [Client()]

    def connect(self):
        # connect and set ip and clients
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(None) # make socket non-blocking
        self.sock.connect((self.ip, self.port))
        self.reciever = threading.Thread(target=self.recieve)
        self.reciever.daemon = True
        self.reciever.start()
        self.connected = True
        print("connected!")

    def login(self, username):
        self.sock.send("LOGN {0} {1}\n".format(username, VERSION).encode())
        data = self.sock.recv(256)
        self.id = data[4:].strip().decode()
        self.get_clients()

    def execute(self, command):
        print(command)
        words = command.split()
        verb = words[0].lower()
        if verb == "send":
            self.send(words[1], words[2])
        elif verb == "disconnect":
            self.disconnect()
        pass

    def get_clients(self):
        self.sock.send("WHOO\n".encode())

    def disconnect(self):
        self.sock.send("GDBY\n".encode())
        self.connected = False

    def get_user_by_id(self, userid):
        for c in self.clients:
            if c.userid == userid:
                return c
        return None

    def recieve(self):
        while True:
            data = self.sock.recv(256)
            if data != b'':
                words = data.decode().split(maxsplit=1)
                command = words[0]
                if command == "RECV":
                    id_message = words[1].split(':')
                    from_client = self.get_user_by_id(id_message[0].strip())
                    if from_client is not None:
                        from_username = from_client.username
                        print("message recieved from {0}: \"{1}\"".format(from_username, id_message[1].split('\n')[0].strip()))
                    else:
                        self.get_clients()
                        from_client = self.get_user_by_id(id_message[0].strip())
                        if from_client is not None:
                            from_username = from_client.get_username(from_client)
                        print("message recieved from {0}: \"{1}\"".format(from_username, id_message[1].split('\n')[0].strip()))
                    # if the client didn't exist in our client list, try to
                    # refresh the list of connected clients first and try once more

                elif command == "CONN":
                    id_user = words[1].split(':')
                    self.clients.append(Client(userid=id_user[0].strip(), username=id_user[1].strip()))

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
