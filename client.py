import trio
import json
import pprint
from typing import List

_CLIENT_VERSION = 1
_RECEIVE_SIZE = 4096  # pretty arbitrary
_HELP = """
valid commands: send, sendall, disconnect

examples: "send bob: hello"
          "sendall: hello"
          "disconnect"

"""


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


class InvalidCommand(Exception):
    pass


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

    def _encode(self) -> bytes:
        return self.__json_packet.encode() + b"\n"

    async def send(self, stream):
        await stream.send_all(self._encode())


class Client:
    def __init__(self, username: str):
        self.username = username
        self.__queue: List[Packet] = []

    async def run(self, host="127.0.0.1", port=8080):
        try:
            self.__stream = await trio.open_tcp_stream(host, port)

            send_channel, receive_channel = trio.open_memory_channel(0)
            async with receive_channel, trio.open_nursery() as nursery:
                nursery.start_soon(self.__sender, receive_channel)
                nursery.start_soon(self.__receiver, send_channel)
                nursery.start_soon(self.__logn, send_channel)
                nursery.start_soon(self.__show_prompt)
        except trio.ClosedResourceError:
            print("goodbye!")

    async def __logn(self, send_channel):
        await send_channel.send(Packet(_from=self.username, verb="LOGN"))

    async def __sender(self, receive_channel):
        async for packet in receive_channel:
            await packet.send(self.__stream)
        # send packets

    async def __receiver(self, send_channel):
        chan = TerminatedFrameReceiver(self.__stream, b"\n")
        async for message in chan:
            decoded = json.loads(message)
            verb = decoded["verb"]

            if verb == "SUCC":
                print("logged in")
            elif verb == "RECV":
                print(
                    "<{_from}> {message}".format(
                        _from=decoded["from"], message=decoded["data"]
                    )
                )
            else:
                print("<received verb {}>".format(verb))
        await self.__stream.aclose()

    async def __execute(self, command):
        args = command.split(" ")
        verb = args[0].lower()

        if verb == "send":
            to = args[1]
            packet = Packet(to=[args[1]], verb="SEND", data=" ".join(args[2:]))
            await packet.send(self.__stream)
        elif verb == "sendall":
            pass
        elif verb == "disconnect":
            packet = Packet(verb="DISC")
            await packet.send(self.__stream)
            await self.__stream.aclose()
        else:
            raise InvalidCommand

    async def __show_prompt(self):
        while True:
            await trio.sleep(0.25)
            # let other async threads do work
            try:
                await self.__execute(input("command: ").strip())
            except InvalidCommand:
                print("\nInvalid command specified.", _HELP)
            # get user input

            await trio.sleep(0.25)
            # let other async threads do work


async def main():
    client = Client(username=input("enter your username: ").strip())
    await client.run()


if __name__ == "__main__":
    trio.run(main)
