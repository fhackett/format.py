import asyncio
import pytest
import time

from format.jaus import Id, Message
from format.jaus.services import (
    EventsService,
    AccessControlService,
    ManagementService,
)
from format.jaus.core.access_control import (
    QueryControl,
    ReportControl,
    RequestControl,
    ConfirmControl,
    ReleaseControl,
    RejectControl,
    QueryTimeout,
    ReportTimeout,
    QueryAuthority,
    ReportAuthority,
    SetAuthority,
)

@pytest.fixture
def core_service_list():
    return [EventsService, AccessControlService, ManagementService]

@pytest.fixture
def control_connection(test_control_core_connection):
    return test_control_core_connection

@pytest.fixture
def test_id2():
    return Id(subsystem=0x0003, node=0x03, component=0x03)

@pytest.fixture
def connection2(test_protocol, test_id2):
    return test_protocol.connect(test_id2)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__query_control__not_controlled(test_connection, component_id):
    await test_connection.send_message(
        QueryControl()._write(),
        destination_id=component_id)
    reply_bytes, source_id = await test_connection.listen(timeout=2)
    reply = Message._read(reply_bytes)
    assert reply == ReportControl(
        id=Id(subsystem=0, node=0, component=0),
        authority_code=0)
    assert source_id == component_id

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__request_control__release_control(test_connection, component_id, recv_msg):
    await test_connection.send_message(
        RequestControl(authority_code=5)._write(),
        destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert reply == ConfirmControl(response_code=ConfirmControl.ResponseCode.CONTROL_ACCEPTED)

    await test_connection.send_message(
        ReleaseControl()._write(),
        destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert reply == RejectControl(response_code=RejectControl.ResponseCode.CONTROL_RELEASED)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__query_control__controlled(control_connection, component_id, recv_msg, test_id):
    await control_connection.send_message(
        QueryControl()._write(),
        destination_id=component_id)

    reply = await recv_msg(control_connection, src_id=component_id)
    assert ReportControl(id=test_id, authority_code=5)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__preemption__insufficient_authority(control_connection, connection2, component_id, recv_msg):
    await connection2.send_message(
        RequestControl(authority_code=4)._write(),
        destination_id=component_id)
    reply = await recv_msg(connection2, src_id=component_id)
    assert reply == ConfirmControl(response_code=ConfirmControl.ResponseCode.INSUFFICIENT_AUTHORITY)

"""@asyncio.coroutine
def reacquire_control(connection):
    yield from connection.send_message(messages.RequestControlMessage(
        authority_code=5))
    results = yield from connection.receive_messages(types=(messages.MessageCode.ConfirmControl,))
    assert results == [messages.ConfirmControlMessage(
        response_code=messages.ConfirmControlResponseCode.CONTROL_ACCEPTED)]

@asyncio.coroutine
def release_control(connection):
    yield from connection.send_message(messages.ReleaseControlMessage())
    results = yield from connection.receive_messages(types=(messages.MessageCode.RejectControl,))
    assert results == [messages.RejectControlMessage(
        response_code=messages.RejectControlResponseCode.CONTROL_RELEASED)]
"""

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__preemption__sufficient_authority(control_connection, connection2, component_id, recv_msg):
    await connection2.send_message(
        RequestControl(authority_code=6)._write(),
        destination_id=component_id)
    reply = await recv_msg(connection2, src_id=component_id)
    assert reply == ConfirmControl(response_code=ConfirmControl.ResponseCode.CONTROL_ACCEPTED)

    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == RejectControl(response_code=RejectControl.ResponseCode.CONTROL_RELEASED)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__control_timeout(control_connection, component_id, recv_msg):
    # wait for timeout_routine
    start_time = time.perf_counter()
    reply = await recv_msg(control_connection, src_id=component_id, timeout=6)
    assert round(time.perf_counter() - start_time) == 5
    assert reply == RejectControl(response_code=RejectControl.ResponseCode.CONTROL_RELEASED)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__query_timeout(test_connection, component_id, recv_msg):
    await test_connection.send_message(
        QueryTimeout()._write(),
        destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert reply == ReportTimeout(timeout=5)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__query_authority(control_connection, component_id, recv_msg):
    await control_connection.send_message(
        QueryAuthority()._write(),
        destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == ReportAuthority(authority_code=5)

@pytest.mark.parametrize('code,response', [
    (0, 0),
    (3, 0),
    (5, 0),
    (10, 0),
])
@pytest.mark.asyncio(forbid_global_loop=True)
async def test__set_authority__no_control(test_connection, component_id, recv_msg, code, response):
    await test_connection.send_message(
        SetAuthority(authority_code=code)._write(),
        destination_id=component_id)
    await test_connection.send_message(
        QueryAuthority()._write(),
        destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert reply == ReportAuthority(authority_code=response)

@pytest.mark.parametrize('code,response', [
    (0, 0),
    (3, 3),
    (5, 5),
    (10, 5),
])
@pytest.mark.asyncio(forbid_global_loop=True)
async def test__set_authority__control(control_connection, component_id, recv_msg, code, response):
    await control_connection.send_message(
        SetAuthority(authority_code=code)._write(),
        destination_id=component_id)
    await control_connection.send_message(
        QueryAuthority()._write(),
        destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == ReportAuthority(authority_code=response)
