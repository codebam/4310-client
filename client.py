import trio
import json
import hashlib
from typing import List

_CLIENT_VERSION = 1
_RECEIVE_SIZE = 4096  # pretty arbitrary
_HELP = """
valid commands: send, all, who, bye

examples: "send bob hello"
          "all hello"
          "who"
          "bye"

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


packetSentCapacity = 512 # Maximum number of past packets that we will store for resend
packetSent = list([])    # List of past packets that we will maintain for resend if need

class Packet:
    packetNumber = 0
    def __init__(
        self,
        version=_CLIENT_VERSION,
        number=None,
        _from=None,
        to=None,
        verb=None,
        data="",
        hash_fun=hashlib.sha256,
    ):
        self.packetNumber = self.packetNumber + 1
        self.__json_packet = json.dumps(
            {
                "version": version,
                "number": number,
                "from": _from,
                "to": to,
                "verb": verb,
                "data": data,
                "packet":self.packetNumber,
                "checksum": hash_fun(bytes(data, "utf-8")).hexdigest(),
            }
        )
        if(len(packetSent) < packetSentCapacity):
            # Add the packet to the list (growing the list until it reaches capacity)
            packetSent.append(self) 
        else:
            # If we are already at capacity, we will overwrite one of 
            # the past packets use modulus arithmetic to determine 
            # where in the list we will overwrite based on packetNumber
            packetSent[self.packetNumber%packetSentCapacity] = self

    def _encode(self) -> bytes:
        return self.__json_packet.encode() + b"\n"

    async def send(self, stream):
        await stream.send_all(self._encode())


class Client:
    def __init__(self, username: str):
        self.username = username
        self.__queue: List[Packet] = []
        self.monitorCapacity = 64
        self.receivedPackets = [-1] * self.monitorCapacity # marker that says never received 

    async def run(self, host="127.0.0.1", port=59944):
        self.__stream = await trio.open_tcp_stream(host, port)

        send_channel, receive_channel = trio.open_memory_channel(0)
        async with receive_channel, trio.open_nursery() as nursery:
            nursery.start_soon(self.__sender, receive_channel)
            nursery.start_soon(self.__receiver, send_channel)
            nursery.start_soon(self.__logn, send_channel)
            nursery.start_soon(self.__show_prompt, send_channel)

    async def __logn(self, send_channel):
        await send_channel.send(
            Packet(_from=self.username, verb="LOGN", hash_fun=hashlib.sha256)
        )

    async def __sender(self, receive_channel):
        async for packet in receive_channel:
            await packet.send(self.__stream)
        # send packets

   async def __check_sequence(self, packet):
        p_2 = self.receivedPackets[(packet-2)%self.monitorCapacity] 
        p_1 = self.receivedPackets[(packet-1)%self.monitorCapacity] 
        p_0 = self.receivedPackets[(packet)%self.monitorCapacity] 
        
        if p_1 == -1 and p_2 == -1:
            return true
            
        diff12 = p_1 - p_2
        diff01 = p_0 - p_1
        if diff01 != 1 or diff12 !=1:
            return false
        return true

    async def __receiver(self, send_channel):
        chan = TerminatedFrameReceiver(self.__stream, b"\n")
        async for message in chan:
            decoded = json.loads(message)
            verb = decoded["verb"]
            
            # Decode the packet numebr from server side
            serverpacket = decoded["packet"]
            # Store received packet number in a list
            self.receivedPackets[serverpacket % self.monitorCapacity] = serverpacket
            
            # Dont want to implement this until packet numbers are in the server
            if not self.__check_sequence(serverpacket):
                # need to request a resend of one or more missed packets
                # request a resend of serverpacket-1
                packet = Packet(_from=self.username, verb="RESEND", data=str(serverpacket-1)))
                packet.send(self.__stream)
    
            
            self.lastPacket = serverpacket

            if verb == "SUCC":
                print("logged in")
            elif verb == "RECV":
                print(
                    "<{_from}> {message}".format(
                        _from=decoded["from"], message=decoded["data"]
                    )
                )
            elif verb == "CONN":
                print("user list:")
                user_list = json.loads(decoded["data"])["conn"]
                for user in user_list:
                    print(user)
            elif verb == "DISC":
                client_name = decoded["data"]
                print("{} left the chat.".format(client_name))
            elif verb == "RESEND":
                packet_id = decoded["packet"]
                await packetSent[packet_id%packetSentCapacity].send(self.__stream)
                
            else:
                print("<received verb that I don't understand. {}>".format(verb))
        await self.__stream.aclose()

    async def __execute(self, command, send_channel):
        args = command.split(" ")
        verb = args[0].lower()

        if verb == "send":
            to = args[1]
            packet = Packet(
                _from=self.username, to=[args[1]], verb="SEND", data=" ".join(args[2:])
            )
        elif verb == "all":
            packet = Packet(_from=self.username, verb="SALL", data=" ".join(args[1:]))
        elif verb == "who":
            packet = Packet(_from=self.username, verb="WHOO")
        elif verb == "bye":
            packet = Packet(_from=self.username, verb="DISC")
            await send_channel.send(packet)
            await self.__stream.aclose()
        elif verb == "":
            return
        # if the user presses return, just print a new prompt
        # allows easier checking of messages
        else:
            raise InvalidCommand
        await send_channel.send(packet)

    async def __show_prompt(self, send_channel):
        while True:
            await trio.sleep(0.25)
            # let other async threads do work
            try:
                await self.__execute(input("command: ").strip(), send_channel)
            except InvalidCommand:
                print("\nInvalid command specified.", _HELP)
            # get user input

            await trio.sleep(0.25)
            # let other async threads do work


async def main():
    client = Client(username=input("enter your username: ").strip())
    await client.run()


if __name__ == "__main__":
    try:
        trio.run(main)
    except trio.ClosedResourceError:
        print("goodbye!")