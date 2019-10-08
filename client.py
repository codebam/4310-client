import asyncio
import json

CLIENT_VERSION = 1


class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer


class Client:
    def __init__(self, username: str):
        self.username = username

    async def connect(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", 8080)
        self.conn = Connection(reader, writer)

    async def login(self):
        if self.conn is not None:
            r = json.dumps(
                {"version": CLIENT_VERSION, "from": self.username, "verb": "LOGN"}
            )
            self.conn.writer.write(r.encode())
        else:
            raise ConnectionError("must connect before logging in")


async def main():
    c = Client(username=input("username: "))
    print("connecting...")
    await c.connect()
    print("connected!")
    print("logging in...")
    await c.login()
    print("logged in!")


if __name__ == "__main__":
    asyncio.run(main())
