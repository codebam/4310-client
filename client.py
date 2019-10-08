import asyncio
import json

CLIENT_VERSION = 1


class Client:
    def __init__(self, username: str):
        self.username = username

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection("127.0.0.1", 8080)

    async def login(self):
        if self.writer is not None:
            r = json.dumps(
                {"version": CLIENT_VERSION, "from": self.username, "verb": "LOGN"}
            )
            self.writer.write(r.encode())
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
