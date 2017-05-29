import asyncio
from format.jaus.judp import ConnectedJUDPProtocol, Packet, make_multicast_socket
from format.jaus import Id

async def main(loop):
    _, protocol = await loop.create_datagram_endpoint(
            lambda: ConnectedJUDPProtocol(loop=loop),
            sock=make_multicast_socket())
    con = protocol.connect(Id(subsystem=2, node=2, component=2))
    msg, src_id = await con.listen(timeout=20)
    print(msg)
    await con.send_message(
            msg,
            destination_id=src_id)
    await protocol.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))


