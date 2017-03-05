import pytest
import asyncio
import format.jaus.judp as judp
import format.jaus as jaus

@pytest.fixture
def connection1(event_loop):
    protocol = event_loop.create_datagram_endpoint(
        lambda: judp.ConnectedJUDPProtocol(loop=event_loop),
        local_addr=('localhost', 5001))
    yield protocol.connect(jaus.Id(subsystem=1, node=1, component=1))

@pytest.mark.asyncio
def test__single_packet(event_loop):
    pass
