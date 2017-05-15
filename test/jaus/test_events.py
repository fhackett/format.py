import asyncio
import pytest
import time

from format.jaus import Message
from format.jaus.core.liveness import (
    QueryHeartbeatPulse,
    ReportHeartbeatPulse,
)
from format.jaus.core.events import (
    QueryEventTimeout,
    ReportEventTimeout,
    QueryEventsAll,
    CreateEvent,
    ReportEvents,
    ConfirmEventRequest,
    CancelEvent,
    EventType,
    Event,
)
from format.jaus.services import (
    LivenessService,
    EventsService,
)

@pytest.fixture
def core_service_list():
    return [LivenessService, EventsService]

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__report_event_timeout(test_connection, component_id):
    await test_connection.send_message(QueryEventTimeout()._write(), destination_id=component_id)
    reply, source_id = await test_connection.listen(timeout=2)
    assert Message._read(reply) == ReportEventTimeout(timeout=1)
    assert source_id == component_id

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__report_events__no_events(test_connection, component_id):
    await test_connection.send_message(QueryEventsAll()._write(), destination_id=component_id)
    reply, source_id = await test_connection.listen(timeout=2)
    assert Message._read(reply) == ReportEvents(events=[])
    assert source_id == component_id

def check_confirm_event_request(reply, request_id, rate=5, event_id=None):
    assert reply.message_code is _messages.MessageCode.ConfirmEventRequest
    msg_body = reply.body
    if event_id is not None:
        assert event_id == msg_body.event_id
    event_id = msg_body.event_id
    assert msg_body.request_id == request_id
    assert round(msg_body.confirmed_periodic_rate) == round(rate)
    return event_id


async def setup_event(connection, component_id, type, query, request_id, rate=5):
    await connection.send_message(CreateEvent(
        request_id=request_id,
        event_type=type,
        requested_periodic_rate=rate,
        query_message=query._write())._write(), destination_id=component_id)
    reply_bytes, source_id = await connection.listen(timeout=2)
    reply = Message._read(reply_bytes)
    assert isinstance(reply, ConfirmEventRequest)
    assert reply.request_id == request_id
    assert round(reply.confirmed_periodic_rate) == round(rate)
    assert source_id == component_id

    return reply.event_id

async def teardown_event(connection, component_id, event_id, request_id, rate=5):
    await connection.send_message(
        CancelEvent(request_id=request_id, event_id=event_id)._write(),
        destination_id=component_id)

    reply_bytes, source_id = await connection.listen(timeout=2)
    reply = Message._read(reply_bytes)
    assert isinstance(reply, ConfirmEventRequest)
    assert reply.request_id == request_id
    assert reply.event_id == event_id
    assert round(reply.confirmed_periodic_rate) == round(rate)
    assert source_id == component_id

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__report_events__one_event(test_connection, component_id):
    event_id = await setup_event(
        test_connection,
        component_id,
        type=EventType.EVERY_CHANGE,
        query=QueryHeartbeatPulse(),
        request_id=1,
        rate=0)

    await test_connection.send_message(QueryEventsAll()._write(), destination_id=component_id)

    reply_bytes, source_id = await test_connection.listen(timeout=2)
    reply = Message._read(reply_bytes)
    assert reply == ReportEvents(events=[
        ReportEvents.Event(
            type=EventType.EVERY_CHANGE,
            id=event_id,
            query_message=QueryHeartbeatPulse()._write(),
        ),
    ])
    assert source_id == component_id

    await teardown_event(test_connection, component_id, event_id=event_id, request_id=2, rate=0)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__event_rate(test_connection, component_id):
    rate = 5
    event_id = await setup_event(
        test_connection,
        component_id,
        type=EventType.PERIODIC,
        query=QueryHeartbeatPulse(),
        request_id=1,
        rate=rate)

    results = []
    for i in range(20):
        start_time = time.perf_counter()
        reply_bytes, source_id = await test_connection.listen(timeout=2)
        results.append(time.perf_counter() - start_time)
        reply = Message._read(reply_bytes)
        assert reply == Event(
            event_id=event_id,
            sequence_number=i,
            report_message=ReportHeartbeatPulse()._write())
        assert source_id == component_id

    assert round(sum(results)/20, 1) == round(1/5, 1)

    await teardown_event(
        test_connection,
        component_id,
        event_id=event_id,
        request_id=2,
        rate=rate)

@pytest.mark.asyncio(forbid_global_loop=True)
async def test__event_timeout(test_connection, component_id, component):
    # "fixes" event timeout so we don't have to wait a whole minute
    component.events.event_timeout = 3

    event_id = await setup_event(
        test_connection,
        component_id,
        type=EventType.EVERY_CHANGE,
        query=QueryHeartbeatPulse(),
        request_id=1,
        rate=0)

    start_time = time.perf_counter()
    timeout_bytes, source_id = await test_connection.listen(timeout=5)
    timeout = Message._read(timeout_bytes)
    assert timeout == ConfirmEventRequest(
        request_id=1,
        event_id=event_id,
        confirmed_periodic_rate=0)
    assert source_id == component_id
    assert round(time.perf_counter()-start_time) == 3
