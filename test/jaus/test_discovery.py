import pytest

from format.jaus.services import (
    LivenessService,
    DiscoveryService,
)
from format.jaus.core.discovery import (
    ServiceRecord,
    RegisterServices,
    QueryServices,
    NodeRequest,
    ComponentRequest,
    ReportServices,
    NodeServiceListReport,
    ComponentServiceListReport,
    SubsystemListRequest,
    QueryServiceList,
    NodeListRequest,
    ComponentListRequest,
    ReportServiceList,
)

@pytest.fixture
def core_service_list():
    return [LivenessService, DiscoveryService]

multicast_addr = ('239.255.0.1', 3794)

# first, we should support multicast...
"""
@pytest.mark.asyncio(forbid_global_loop=True)
def test__identification__multicast(connection_multicast):
    connection = connection_multicast
    yield from connection.send_message(_messages.QueryIdentificationMessage(
        type=_messages.IdentificationQueryType.COMPONENT), addr=multicast_addr)

    results = yield from connection.receive_messages(message_count=2)
    assert set(results) == {
        _messages.ReportIdentificationMessage(
            query_type=_messages.IdentificationQueryType.COMPONENT,
            type=_messages.IdentificationType.COMPONENT,
            identification='Core'),
        _messages.ReportIdentificationMessage(
            query_type=_messages.IdentificationQueryType.COMPONENT,
            type=_messages.IdentificationType.COMPONENT,
            identification='Mobility'),
    }
"""

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__identification__query_services(test_connection, component_id, recv_msg, test_id):
    await test_connection.send_message(RegisterServices(
        services=[
            ServiceRecord(uri='foobinator', major_version=3, minor_version=2),
            ServiceRecord(uri='barinator', major_version=0, minor_version=1),
        ])._write(),
        destination_id=component_id)
    await test_connection.send_message(QueryServices(
        nodes=[
            NodeRequest(
                id=25,
                components=[
                    ComponentRequest(id=2),
                ]),
            NodeRequest(
                id=1,
                components=[
                    ComponentRequest(id=1),
                ]),
        ])._write(),
        destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert isinstance(reply, ReportServices)
    nodes = {node.id: node for node in reply.nodes}
    assert nodes.keys() == {1, 25}
    assert len(nodes[1].components) == 1
    assert nodes[1].components[0].id == 1
    assert set(nodes[1].components[0].services) == {
        ServiceRecord(uri='urn:jaus:jss:core:Liveness', major_version=1, minor_version=0),
        ServiceRecord(uri='urn:jaus:jss:core:Discovery', major_version=1, minor_version=0),
    }
    assert nodes[25].components == [
        ComponentServiceListReport(id=2, services=[])
    ]

    await test_connection.send_message(
        QueryServiceList(
            subsystems=[
                SubsystemListRequest(
                    id=test_id.subsystem,
                    nodes=[
                        NodeListRequest(
                            id=test_id.node,
                            components=[
                                ComponentListRequest(id=test_id.component)
                            ])
                    ])
            ])._write(),
        destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert isinstance(reply, ReportServiceList)
    assert reply.subsystems[0].id == test_id.subsystem
    assert reply.subsystems[0].nodes[0].id == test_id.node
    assert reply.subsystems[0].nodes[0].components[0].id == test_id.component
    services = reply.subsystems[0].nodes[0].components[0].services
    assert set(services) == {
        ServiceRecord(uri='foobinator', major_version=3, minor_version=2),
        ServiceRecord(uri='barinator', major_version=0, minor_version=1),
    }
