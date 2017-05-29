import pytest

from format.jaus import Message
from format.jaus.core.list_manager import (
        QueryElementList,
        ReportElementList,
        SetElement,
        ListElement,
        ListElementID,
        ConfirmElementRequest,
        RejectElementRequest,
        QueryElement,
        ReportElement,
        DeleteElement,
        QueryElementCount,
        ReportElementCount,
)

from format.jaus.services import (
        EventsService,
        AccessControlService,
        ManagementService,
        ListManagerService,
)

@pytest.fixture
def core_service_list():
    return [
        EventsService,
        AccessControlService,
        ManagementService,
        ListManagerService,
    ]

@pytest.fixture
def control_connection(test_control_core_connection):
    return test_control_core_connection

async def get_elements(connection, component_id, recv_msg):
    await connection.send_message(
            QueryElementList()._write(),
            destination_id=component_id)
    reply = await recv_msg(connection, src_id=component_id)
    assert isinstance(reply, ReportElementList)
    return reply.elements

async def setup_list(control_connection, component_id, recv_msg):
    await control_connection.send_message(
            SetElement(
                request_id=1,
                elements=[
                    ListElement(uid=2, prev=0, next=5, data=b'aa'),
                    ListElement(uid=5, prev=2, next=0, data=b'bb'),
                ])._write(),
            destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == ConfirmElementRequest(request_id=1)


@pytest.mark.asyncio
async def test__query_element_list__empty(component_id, test_connection, recv_msg):
    await test_connection.send_message(
            QueryElementList()._write(),
            destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert reply == ReportElementList(elements=[])

@pytest.mark.asyncio
async def test__set_element(component_id, control_connection, recv_msg):
    await setup_list(control_connection, component_id, recv_msg)
    elements = await get_elements(control_connection, component_id, recv_msg)
    assert elements == [ListElementID(uid=2), ListElementID(uid=5)]

@pytest.mark.asyncio
async def test__query_element(component_id, control_connection, recv_msg):
    await setup_list(control_connection, component_id, recv_msg)

    await control_connection.send_message(
            QueryElement(element_uid=5)._write(),
            destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == ReportElement(uid=5, prev=2, next=0, data=b'bb')

@pytest.mark.asyncio
async def test__query_element_count(component_id, control_connection, recv_msg):
    await setup_list(control_connection, component_id, recv_msg)

    await control_connection.send_message(
            QueryElementCount()._write(),
            destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == ReportElementCount(element_count=2)

@pytest.mark.asyncio
async def test__delete_element(component_id, control_connection, recv_msg):
    await setup_list(control_connection, component_id, recv_msg)

    await control_connection.send_message(
            DeleteElement(
                request_id=2,
                element_ids=[ListElementID(uid=5)])._write(),
            destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == ConfirmElementRequest(request_id=2)

    elements = await get_elements(control_connection, component_id, recv_msg)
    assert elements == [ListElementID(uid=2)]

