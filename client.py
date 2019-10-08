import asyncio
import json
import pprint

CLIENT_VERSION = 1


class Client:
    def __init__(self, username: str):
        self.username = username

    async def connect(self):
        print("connecting...")
        self.reader, self.writer = await asyncio.open_connection("127.0.0.1", 8080)
        print("connected!")

    async def login(self):
        print("logging in...")

        if self.writer is not None:
            r = json.dumps(
                {"version": CLIENT_VERSION, "from": self.username, "verb": "LOGN"}
            )
            self.writer.write(r.encode())
        else:
            raise ConnectionError("must connect before logging in")
        print("logged in!")

    async def read_packets(self):
        line = await self.reader.readline()

        while line is not None:
            self.handle_packet(line)

    async def handle_packet(self, line):
        packet = json.dumps(json.loads(line))
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(packet)
        # TODO


async def main():
    c = Client(username=input("username: "))
    await c.connect()
    await c.login()
    await c.read_packets()
    asyncio.run(c.read_packets())


if __name__ == "__main__":
    asyncio.run(main())
