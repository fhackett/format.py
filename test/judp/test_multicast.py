import pytest
import asyncio
from format.jaus.judp import ConnectedJUDPProtocol, Packet, make_multicast_socket
from format.jaus import Id

@pytest.fixture
def protocol1(event_loop):
    _, protocol = event_loop.run_until_complete(event_loop.create_datagram_endpoint(
        lambda: ConnectedJUDPProtocol(loop=event_loop),
        sock=make_multicast_socket(port=5001)))
    yield protocol
    event_loop.run_until_complete(protocol.close())

@pytest.fixture
def protocol2(event_loop):
    _, protocol = event_loop.run_until_complete(event_loop.create_datagram_endpoint(
        lambda: ConnectedJUDPProtocol(loop=event_loop),
        sock=make_multicast_socket()))
    yield protocol
    event_loop.run_until_complete(protocol.close())

id1 = Id(subsystem=1, node=1, component=1)
id2 = Id(subsystem=2, node=2, component=2)

@pytest.fixture
def connection1(protocol1):
    return protocol1.connect(id1)

@pytest.fixture
def connection2(protocol2):
    return protocol2.connect(id2)

@pytest.mark.asyncio
async def test__broadcast_packet(connection1, connection2):
    await connection1.send_message(b'aaaa', destination_id=id2, broadcast=Packet.BroadcastFlags.GLOBAL)
    msg, src = await connection2.listen(timeout=2)
    assert src == id1
    assert msg == b'aaaa'

    await connection2.send_message(b'bbbb', destination_id=id1)

    msg, src = await connection1.listen(timeout=2)
    assert src == id2
    assert msg == b'bbbb'

