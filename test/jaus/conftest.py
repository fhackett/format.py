import asyncio
import pytest

from format.jaus import Component, Id, Message
from format.jaus.judp import ConnectedJUDPProtocol

from format.jaus.core.access_control import (
    RequestControl,
    ConfirmControl,
    ReleaseControl,
    RejectControl,
)

@pytest.fixture
def core_component_id():
    return Id(subsystem=0x0001, node=0x01, component=0x01)

@pytest.fixture
def protocol_port(unused_tcp_port_factory):
    return unused_tcp_port_factory()

@pytest.fixture
def test_protocol_port(unused_tcp_port_factory):
    return unused_tcp_port_factory()

@pytest.fixture
def protocol(event_loop, protocol_port):
    _, protocol = event_loop.run_until_complete(event_loop.create_datagram_endpoint(
        lambda: ConnectedJUDPProtocol(loop=event_loop),
        local_addr=('localhost', protocol_port)))
    yield protocol
    event_loop.run_until_complete(protocol.close())

@pytest.fixture
def test_protocol(event_loop, test_protocol_port, core_component_id, protocol_port):
    _, protocol = event_loop.run_until_complete(event_loop.create_datagram_endpoint(
        lambda: ConnectedJUDPProtocol(loop=event_loop),
        local_addr=('localhost', test_protocol_port)))
    protocol.routings[core_component_id] = ('localhost', protocol_port)
    yield protocol
    event_loop.run_until_complete(protocol.close())

@pytest.fixture
def test_id():
    return Id(subsystem=0x0002, node=0x02, component=0x02)

@pytest.fixture
def test_core_connection(test_protocol, test_id, core_component):
    return test_protocol.connect(test_id)

@pytest.fixture
def test_connection(test_core_connection):
    return test_core_connection

@pytest.fixture
def core_connection(protocol, core_component_id):
    return protocol.connect(core_component_id)

@pytest.fixture
def core_service_list():
    return []

@pytest.fixture
def core_component(event_loop, core_component_id, core_connection, core_service_list):
    component = Component(
        id=core_component_id,
        name='TestCore',
        node_name='TestNode',
        subsystem_name='TestSubsystem',
        services=core_service_list,
        loop=event_loop)
    component.listen(core_connection, loop=event_loop)
    yield component
    event_loop.run_until_complete(component.close())

@pytest.fixture
def recv_msg():
    async def impl(connection, *, src_id, timeout=2):
        reply_bytes, source_id = await connection.listen(timeout=timeout)
        reply = Message._read(reply_bytes)
        assert source_id == src_id
        return reply
    return impl

@pytest.fixture
def test_control_core_connection(test_core_connection, core_component_id, event_loop, recv_msg):
    async def setup():
        await test_core_connection.send_message(
            RequestControl(authority_code=5)._write(),
            destination_id=core_component_id)
        reply = await recv_msg(test_core_connection, src_id=core_component_id)
        assert reply == ConfirmControl(response_code=ConfirmControl.ResponseCode.CONTROL_ACCEPTED)
    async def teardown():
        await test_core_connection.send_message(
            ReleaseControl()._write(),
            destination_id=core_component_id)
        await recv_msg(test_core_connection, src_id=core_component_id)
    event_loop.run_until_complete(setup())
    yield test_core_connection
    # for the moment, let tests exit any old way they like (saves teardown code in tests)
    #event_loop.run_until_complete(teardown())

@pytest.fixture
def component(core_component):
    return core_component

@pytest.fixture
def component_id(core_component_id):
    return core_component_id
