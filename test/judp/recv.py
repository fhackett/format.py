import asyncio
from format.jaus.judp import ConnectedJUDPProtocol, Packet, PORT, MULTICAST_ADDR
from format.jaus import Id
import socket

async def main(loop):
    _, protocol = await loop.create_datagram_endpoint(
            lambda: ConnectedJUDPProtocol(loop=loop),
            local_addr=(MULTICAST_ADDR, PORT),
            family=socket.AF_INET)
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


