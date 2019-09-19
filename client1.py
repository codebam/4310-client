import socket
import select
import sys
#get the username through the console
from dnf.pycomp import raw_input

username = str(raw_input("Enter your username: "))
#open a socket stream
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.connect(("localhost", 5000))
#send a tcp packet to the server
server.send("LOGN " + username)
while True:
    #get a list of all connections
    sockets_list = [sys.stdin, server]
    read_sockets,write_socket, error_socket = select.select(sockets_list,[],[])
    for socks in read_sockets:
        #message from the server
        if socks == server:
            message = socks.recv(2048)
            if("SUCC" in message):
                # "SUCC 5\n"
                print("successully joined the chat room")
            else:
                print(message)
        else:
            #clients own stream for sendinig
            message = sys.stdin.readline()
            server.send(message)
            sys.stdout.flush()
