import asyncio
import pytest

from format.jaus import Component, Id
from format.jaus.judp import ConnectedJUDPProtocol

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
def component(core_component):
    return core_component

@pytest.fixture
def component_id(core_component_id):
    return core_component_id
