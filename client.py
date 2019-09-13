class Server:
    def init(self):
        self.connect()

    def send(self, content):
        # parse then send
        pass

    def parse_content(content) -> (client_id, message):
        pass

    def connect(self):
        # connect and set ip and clients
        self.ip = ip
        self.clients = clients
        pass

    def disconnect(self):
        pass

    def recieve(self, content):
        pass
        # pass onto verb functions

    def new_client(self):
        pass

    def show_message(self):
        pass

class Client:
    def init(self, _id, username):
        self._id = _id
        self.username = username

class Message:
    def init(self, client_id, content):
        self.client_id = client_id
        self.content = content

def main():
    # open socket to server
    # initiate connection
    # start listening
    # show verb prompt
