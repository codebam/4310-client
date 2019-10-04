import socket
import threading
import asyncio
'''
FoocChat client 
|
| Name: Client.py
|
| Written by:  Kevin Dsane-Selby, Sean Behan
|
| Purpose: to enable user communication with the server to be done seamlessly
|
|
|
| Subroutines/libraries required:
this is includes threading from the threading library to allow parallelism 
| 


'''


VERSION = "FC1"
user_input = [None] # global for input between threads

class Client:
    # connect and set ip and clients
     async def __init__(self, username=None, userid=None):
        self.username = username
        self.userid = userid

class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.clients = [Client()]

    def connect(self, transport):
        # connect and set ip and clients
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(None) # make socket non-blocking
        try:
          #setting up connections for receiving and sending meassages using threading.
            self.sock.connect((self.ip, self.port))
            self.transport = transport
            self.reciever = threading.Thread(target=self.recieve)
            self.reciever.daemon = True
            self.reciever.start()
            self.connected = True
            print("connected!")
        # connection refused exception if the user doesen't exist
        except ConnectionRefusedError:
            self.connected = False
            print("connection refused.")

 # creating login definition and format
    def login(self, username):
        self.sock.send("LOGN {0} {1}\n".format(username, VERSION).encode())
        self.get_clients()

    # execute accepts a command and uses that to send a message to all users or one user and
    def execute(self, command):
        try:
            words = command.split(maxsplit=1)
            verb = words[0].lower()

            if verb == "send":
                x = words[1].split(':', maxsplit=1)
                to = x[0]
                message = x[1]
                self.send(to, message)
            elif verb in ["sendall", "sendall:"]:
                self.send(str(0), words[1])
            elif verb == "disconnect":
                self.disconnect()
        except:
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
# converts data into bytes to be used and commands are used to receive s
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
                        print("\n--- refreshing client list.")
                        self.get_clients()
                        from_client = self.get_user_by_id(id_message[0].strip())

                        if from_client is not None:
                            from_username = from_client.get_username(from_client)
                            print("message recieved from {0}: \"{1}\"".format(from_username, id_message[1].split('\n')[0].strip()))
                    # if the client didn't exist in our client list, try to
                    # refresh the list of connected clients first and try once more
                elif command == "SUCC":
                    self.id = data[4:].strip().decode()

                elif command == "CONN":
                    id_user = words[1].split(':')
                    username = id_user[1].strip()
                    print("\n--- {0} has joined the chatroom.".format(username))
                    self.clients.append(Client(userid=id_user[0].strip(),
                        username=username))

                elif command == "DISC":
                    id_user = words[1]

                    for client in self.clients:
                        if client.userid == id_user:
                            clients.remove(client)
                            print("\n--- {0} has left the chatroom.".format(client.username))



    def send(self, to, message):
        self.sock.send("SEND {0}:{1}\n".format(to, message).encode())
        # print("recipient is not connected.")

 # class defines messages attatched with the users id for messages to be identified by the client
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
    server = Server("127.0.0.1", 59444)
    server.connect()
    # open socket to server

    if server.connected:
        username = str(input("Enter your username: "))
        server.login(username)
    # initiate connection

    while server.connected:
        command = str(input("enter a command: "))
        server.execute(command)
    # show prompt
    print("connection closed.")

if __name__ == "__main__":
    main()
