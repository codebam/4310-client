import trio
import json
import pprint

_CLIENT_VERSION = 1
_RECEIVE_SIZE = 4096  # pretty arbitrary


class TerminatedFrameReceiver:
    def __init__(self, stream, terminator, max_frame_length=16384):
        self.stream = stream
        self.terminator = terminator
        self.max_frame_length = max_frame_length
        self._buf = bytearray()
        self._next_find_idx = 0

    async def receive(self):
        while True:
            terminator_idx = self._buf.find(self.terminator, self._next_find_idx)

            if terminator_idx < 0:
                # no terminator found

                if len(self._buf) > self.max_frame_length:
                    raise ValueError("frame too long")
                # next time, start the search where this one left off
                self._next_find_idx = max(0, len(self._buf) - len(self.terminator) + 1)
                # add some more data, then loop around
                more_data = await self.stream.receive_some(_RECEIVE_SIZE)

                if more_data == b"":
                    if self._buf:
                        raise ValueError("incomplete frame")
                    raise trio.EndOfChannel
                self._buf += more_data
            else:
                # terminator found in buf, so extract the frame
                frame = self._buf[:terminator_idx]
                # Update the buffer in place, to take advantage of bytearray's
                # optimized delete-from-beginning feature.
                del self._buf[: terminator_idx + len(self.terminator)]
                # next time, start the search from the beginning
                self._next_find_idx = 0

                return frame

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.receive()
        except trio.EndOfChannel:
            raise StopAsyncIteration


class Packet:
    def __init__(
        self,
        version=_CLIENT_VERSION,
        number=None,
        _from=None,
        to=None,
        verb=None,
        data=None,
    ):
        self.__json_packet = json.dumps(
            {
                "version": version,
                "number": number,
                "from": _from,
                "to": to,
                "verb": verb,
                "data": data,
            }
        )

    def encode(self) -> bytes:
        return self.__json_packet.encode() + b"\n"


class Client:
    def __init__(self, username: str):
        self.username = username

    async def run(self, host="127.0.0.1", port=8080):
        self.__stream = await trio.open_tcp_stream(host, port)

        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.__receiver)
            nursery.start_soon(self.__sender)

    async def __logn(self):
        p = Packet(_from=self.username, verb="LOGN")
        await self.__stream.send_all(p.encode())
        # d = """{ "version": 1, "from": "codebam", "verb": "LOGN" }\n"""
        # await self.__stream.send_all(bytes(d, "utf8"))

    async def __sender(self):
        await self.__logn()
        # await self.__stream.aclose()

    async def __receiver(self):
        chan = TerminatedFrameReceiver(self.__stream, b"\n")
        async for message in chan:
            print(f"Got message: {message!r}")


async def main():
    client = Client(username=input("enter your username: ").strip())
    await client.run()


if __name__ == "__main__":
    trio.run(main)
