import pytest

from format.jaus import Message
from format.jaus.core.events import (
        CreateEvent,
        ConfirmEventRequest,
        EventType,
)
from format.jaus.mobility.local_pose_sensor import (
        QueryLocalPose,
        ReportLocalPose,
)
from format.jaus.mobility.velocity_state_sensor import (
        QueryVelocityState,
        ReportVelocityState,
)
from format.jaus.mobility.local_waypoint_driver import (
        SetLocalWaypoint,
        QueryLocalWaypoint,
        ReportLocalWaypoint,
        SetTravelSpeed,
        QueryTravelSpeed,
        ReportTravelSpeed,
)
from format.jaus.mobility.local_waypoint_list_driver import (
        QueryActiveElement,
        ReportActiveElement,
)
from format.jaus.services import (
        EventsService,
        ManagementService,
        AccessControlService,
        LocalPoseSensorService, 
        VelocityStateSensorService,
        LocalWaypointDriverService,
        LocalWaypointListDriverService,
)


@pytest.fixture
def core_service_list():
    return [
            EventsService,
            ManagementService,
            AccessControlService,
            LocalPoseSensorService,
            VelocityStateSensorService,
            LocalWaypointDriverService,
            LocalWaypointListDriverService,
    ]

@pytest.fixture
def control_connection(test_control_core_connection):
    return test_control_core_connection

def test__qlp_message():
    b = QueryLocalPose(presence_vector=['x', 'y'])._write()
    print(b)
    assert QueryLocalPose(presence_vector={'x', 'y'}) == QueryLocalPose._read(b)


@pytest.mark.asyncio
async def test__query_local_pose(component_id, test_connection, recv_msg):
    await test_connection.send_message(
            QueryLocalPose(presence_vector=['x', 'y'])._write(),
            destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert isinstance(reply, ReportLocalPose)
    assert reply.presence_vector == {'x', 'y'}
    assert round(reply.x) == 0
    assert round(reply.y) == 0

@pytest.mark.asyncio
async def test__query_velocity_state(component_id, test_connection, recv_msg):
    await test_connection.send_message(
            QueryVelocityState(presence_vector=['x', 'y'])._write(),
            destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert isinstance(reply, ReportVelocityState)
    assert reply.presence_vector == {'x'}
    assert round(reply.x) == 0

@pytest.mark.asyncio
async def test__local_waypoint_controlled(component_id, control_connection, recv_msg):
    await control_connection.send_message(
            SetLocalWaypoint(x=5, y=6)._write(),
            destination_id=component_id)
    await control_connection.send_message(
            QueryLocalWaypoint(presence_vector={'x', 'y', 'z'})._write(),
            destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert isinstance(reply, ReportLocalWaypoint)
    assert (round(reply.x), round(reply.y), reply.z) == (5, 6, None)

@pytest.mark.asyncio
async def test__travel_speed_uncontrolled(component_id, test_connection, recv_msg):
    await test_connection.send_message(
            SetTravelSpeed(speed=5)._write(),
            destination_id=component_id)
    await test_connection.send_message(
            QueryTravelSpeed()._write(),
            destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert isinstance(reply, ReportTravelSpeed)
    assert round(reply.speed) == 0

@pytest.mark.asyncio
async def test__travel_speed_controlled(component_id, control_connection, recv_msg):
    await control_connection.send_message(
            SetTravelSpeed(speed=5)._write(),
            destination_id=component_id)
    await control_connection.send_message(
            QueryTravelSpeed()._write(),
            destination_id=component_id)
    reply = await recv_msg(control_connection, src_id=component_id)
    assert isinstance(reply, ReportTravelSpeed)
    assert round(reply.speed) == 5

@pytest.mark.asyncio
async def test__query_active_element(component_id, test_connection, recv_msg):
    await test_connection.send_message(
            QueryActiveElement()._write(),
            destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert reply == ReportActiveElement(uid=0)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__local_pose_event(component_id, test_connection, component, recv_msg):
    await test_connection.send_message(
        CreateEvent(
            request_id=2,
            event_type=EventType.EVERY_CHANGE,
            requested_periodic_rate=0,
            query_message=QueryLocalPose(
                presence_vector={'x', 'y', 'yaw'})._write())._write(),
        destination_id=component_id)
    reply = await recv_msg(test_connection, src_id=component_id)
    assert isinstance(reply, ConfirmEventRequest)
    event_id = reply.event_id
    for i in (1,2):
        component.local_pose_sensor.x = 5
        event = await recv_msg(test_connection, src_id=component_id)
        report = Message._read(event.report_message)
        assert report.presence_vector == {'x', 'y', 'yaw'}
        assert round(report.x) == 5
        assert round(report.y) == 0
        assert round(report.yaw) == 0
 
    component.local_pose_sensor.x = 5
    component.local_pose_sensor.y = 6
    component.local_pose_sensor.yaw = 1
    event = await recv_msg(test_connection, src_id=component_id)
    report = Message._read(event.report_message)
    assert report.presence_vector == {'x', 'y', 'yaw'}
    assert round(report.x) == 5
    assert round(report.y) == 6
    assert round(report.yaw) == 1

