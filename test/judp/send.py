import asyncio
from format.jaus.judp import ConnectedJUDPProtocol, Packet, make_multicast_socket
from format.jaus import Id

async def main(loop):
    _, protocol = await loop.create_datagram_endpoint(
            lambda: ConnectedJUDPProtocol(loop=loop),
            sock=make_multicast_socket(port=5002))
    con = protocol.connect(Id(subsystem=1, node=1, component=1))
    await con.send_message(b'aaaa',
            destination_id=Id(subsystem=2, node=2, component=2),
            broadcast=Packet.BroadcastFlags.GLOBAL)
    msg, src_id = await con.listen(timeout=2)
    print(msg)
    await protocol.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))

