import pytest
import asyncio
import format.jaus.judp as judp
import format.jaus as jaus

@pytest.fixture
def protocol1(event_loop):
    _, protocol = event_loop.run_until_complete(event_loop.create_datagram_endpoint(
        lambda: judp.ConnectedJUDPProtocol(loop=event_loop),
        local_addr=('localhost', 5001)))
    # discretely inform one of the JUDPProtocols of the other's address
    protocol.routings[jaus.Id(subsystem=1, node=1, component=1)] = ('localhost', 5001)
    protocol.routings[jaus.Id(subsystem=1, node=1, component=2)] = ('localhost', 5002)
    protocol.routings[jaus.Id(subsystem=1, node=1, component=3)] = ('localhost', 5001)
    yield protocol
    event_loop.run_until_complete(protocol.close())

@pytest.fixture
def protocol2(event_loop):
    _, protocol = event_loop.run_until_complete(event_loop.create_datagram_endpoint(
        lambda: judp.ConnectedJUDPProtocol(loop=event_loop),
        local_addr=('localhost', 5002)))
    yield protocol
    event_loop.run_until_complete(protocol.close())

@pytest.fixture
def connection1(protocol1):
    return protocol1.connect(jaus.Id(subsystem=1, node=1, component=1))

@pytest.fixture
def connection2(protocol2):
    return protocol2.connect(jaus.Id(subsystem=1, node=1, component=2))

@pytest.fixture
def connection3(protocol1):
    return protocol1.connect(jaus.Id(subsystem=1, node=1, component=3))

@pytest.mark.asyncio
async def test__single_packet(connection1, connection2):
    await connection1.send_message(b'aaaa', destination_id=jaus.Id(subsystem=1, node=1, component=2))
    msg, src = await connection2.listen(timeout=2)
    assert msg == b'aaaa'
    assert src == jaus.Id(subsystem=1, node=1, component=1)

@pytest.mark.asyncio
async def test__oversize_packet(connection1, connection2):
    sent_msg = b'ab'*256
    await connection1.send_message(sent_msg, destination_id=jaus.Id(subsystem=1, node=1, component=2))
    msg, src = await connection2.listen(timeout=2)
    assert msg == sent_msg
    assert src == jaus.Id(subsystem=1, node=1, component=1)

@pytest.mark.asyncio
async def test__huge_packet(connection1, connection2):
    sent_msg = b'ab'*128 + b'cd'*128 + b'ef'*128 + b'gh'*128
    await connection1.send_message(sent_msg, destination_id=jaus.Id(subsystem=1, node=1, component=2))
    msg, src = await connection2.listen(timeout=2)
    assert msg == sent_msg
    assert src == jaus.Id(subsystem=1, node=1, component=1)

@pytest.mark.asyncio
async def test__multiple_small_packets(connection1, connection2):
    await connection1.send_message(b'aaaa', destination_id=jaus.Id(subsystem=1, node=1, component=2))
    await connection1.send_message(b'bbbb', destination_id=jaus.Id(subsystem=1, node=1, component=2))
    await connection1.send_message(b'cccc', destination_id=jaus.Id(subsystem=1, node=1, component=2))
    results = set()
    for i in range(3):
        results.add(await connection2.listen(timeout=2))
    assert results == {
        (b'aaaa', jaus.Id(subsystem=1, node=1, component=1)),
        (b'bbbb', jaus.Id(subsystem=1, node=1, component=1)),
        (b'cccc', jaus.Id(subsystem=1, node=1, component=1)),
    }

@pytest.mark.asyncio
async def test__multiplexing_on_one_port(connection1, connection3):
    await connection1.send_message(b'aaaa', destination_id=jaus.Id(subsystem=1, node=1, component=3))
    await connection3.send_message(b'bbbb', destination_id=jaus.Id(subsystem=1, node=1, component=1))
    msg, src = await connection1.listen(timeout=2)
    assert msg == b'bbbb'
    assert src == jaus.Id(subsystem=1, node=1, component=3)
    msg, src = await connection3.listen(timeout=2)
    assert msg == b'aaaa'
    assert src == jaus.Id(subsystem=1, node=1, component=1)

@pytest.mark.asyncio
async def test__learns_new_addresses(connection1, connection2):
    await connection1.send_message(b'aaaa', destination_id=jaus.Id(subsystem=1, node=1, component=2))
    msg, src = await connection2.listen(timeout=2)
    assert msg == b'aaaa'
    assert src == jaus.Id(subsystem=1, node=1, component=1)

    # test that connection2, which has no routing info at the start, can reply
    await connection2.send_message(b'bbbb', destination_id=jaus.Id(subsystem=1, node=1, component=1))
    msg, src = await connection1.listen(timeout=2)
    assert msg == b'bbbb'
    assert src == jaus.Id(subsystem=1, node=1, component=2)
