import pytest
from asyncio import Queue

from format.jaus.services import (
    EventsService,
    ManagementService,
    AccessControlService,
)
from format.jaus import Message
from format.jaus.core.events import (
    CreateEvent,
    ConfirmEventRequest,
    Event,
    EventType,
)
from format.jaus.core.management import (
    QueryStatus,
    ReportStatus,
    ManagementStatus,
    SetEmergency,
    EmergencyCode,
    ClearEmergency,
)
from format.jaus.core.access_control import (
    RequestControl,
    ConfirmControl,
    ReleaseControl,
    RejectControl,
)

@pytest.fixture
def core_service_list():
    return [EventsService, AccessControlService, ManagementService]

@pytest.fixture
def control_connection(test_control_core_connection):
    return test_control_core_connection

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__query_status__standby(test_connection, component_id):
    await test_connection.send_message(
        QueryStatus()._write(),
        destination_id=component_id)

    reply_bytes, source_id = await test_connection.listen(timeout=2)
    reply = Message._read(reply_bytes)
    assert reply == ReportStatus(status=ManagementStatus.STANDBY)
    assert source_id == component_id

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__set_emergency_and_restore(control_connection, component_id, recv_msg):
    await control_connection.send_message(
        SetEmergency(emergency_code=EmergencyCode.STOP)._write(),
        destination_id=component_id)

    await control_connection.send_message(
        QueryStatus()._write(),
        destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == ReportStatus(status=ManagementStatus.EMERGENCY)


    await control_connection.send_message(
        ClearEmergency(emergency_code=EmergencyCode.STOP)._write(),
        destination_id=component_id)

    await control_connection.send_message(
        QueryStatus()._write(),
        destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == ReportStatus(status=ManagementStatus.STANDBY)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__set_emergency__not_controlled__denies_control(test_connection, component_id, recv_msg):
    await test_connection.send_message(
        SetEmergency(emergency_code=EmergencyCode.STOP)._write(),
        destination_id=component_id)

    await test_connection.send_message(
        RequestControl(authority_code=5)._write(),
        destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert reply == ConfirmControl(response_code=ConfirmControl.ResponseCode.NOT_AVAILABLE)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__set_emergency__controlled__denies_control_and_release(control_connection, component_id, recv_msg):
    await control_connection.send_message(
        SetEmergency(emergency_code=EmergencyCode.STOP)._write(),
        destination_id=component_id)

    await control_connection.send_message(
        RequestControl(authority_code=5)._write(),
        destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == ConfirmControl(response_code=ConfirmControl.ResponseCode.NOT_AVAILABLE)

    await control_connection.send_message(
        ReleaseControl()._write(),
        destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert reply == RejectControl(response_code=RejectControl.ResponseCode.NOT_AVAILABLE)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__status_listener_notified(test_connection, component_id, component, recv_msg):
    await test_connection.send_message(
        CreateEvent(
            request_id=10,
            event_type=EventType.EVERY_CHANGE,
            requested_periodic_rate=0,
            query_message=QueryStatus()._write())._write(),
        destination_id=component_id)
    msg = await recv_msg(test_connection, src_id=component_id)
    assert msg.request_id == 10
    assert msg.confirmed_periodic_rate == 0
    event_id = msg.event_id

    component.management.status = ManagementStatus.EMERGENCY
    msg = await recv_msg(test_connection, src_id=component_id)
    assert msg.event_id == event_id
    assert Message._read(msg.report_message) == ReportStatus(status=ManagementStatus.EMERGENCY)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__status_listener_custom_notified(component):
    q = Queue()
    async def watcher(dct):
        await q.put(dct)
    component.management.state.watcher(watcher, keys=('status',))
    component.management.status = ManagementStatus.EMERGENCY
    dct = await q.get()
    assert dct == {'status': ManagementStatus.EMERGENCY}

