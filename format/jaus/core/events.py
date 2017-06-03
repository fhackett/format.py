import enum as _enum
import asyncio as _asyncio

import format as _format
import format.jaus as _jaus


def change_watcher(self, query_codes):
    """
    When on a Service, alerts the events service that ON_CHANGE events with
    the provided query codes should be fired if the given property has changed.
    """
    async def fn(state):
        await self.component.events.post_change(message_codes=query_codes)
    return fn


class EventType(_enum.Enum):
    PERIODIC = 0
    EVERY_CHANGE = 1

class CreateEvent(_jaus.Message):
    message_code = _jaus.Message.Code.CreateEvent
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('request_id', bytes=1)
        yield _format.Enum('event_type', enum=EventType, bytes=1)
        yield _jaus.ScaledFloat(
            'requested_periodic_rate',
            bytes=2,
            le=True,
            lower_limit=0,
            upper_limit=1092)
        yield from _jaus.counted_bytes('query_message', bytes=4, le=True)

class UpdateEvent(_jaus.Message):
    message_code = _jaus.Message.Code.UpdateEvent
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Int('request_id', bytes=1)
        yield _format.Enum('event_type', enum=EventType, bytes=1)
        yield _jaus.ScaledFloat(
            'requested_periodic_rate',
            bytes=2,
            le=True,
            lower_limit=0,
            upper_limit=1092)
        yield _format.Integer('event_id', bytes=1)
        yield from _jaus.counted_bytes('query_message', bytes=4, le=True)

class CancelEvent(_jaus.Message):
    message_code = _jaus.Message.Code.CancelEvent
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('request_id', bytes=1)
        yield _format.Integer('event_id', bytes=1)

class CreateCommandEvent(_jaus.Message):
    message_code = _jaus.Message.Code.CreateCommandEvent
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('request_id', bytes=1),
        yield _format.Integer('maximum_allowed_duration', bytes=4, le=True)
        yield from _jaus.counted_bytes('command_message', bytes=4, le=True)


class QueryEvents(_jaus.Message):
    message_code = _jaus.Message.Code.QueryEvents

    _variant_key_name = 'variant'
    class Variant(_enum.Enum):
        MESSAGE_ID = 0
        EVENT_TYPE = 1
        EVENT_ID = 2
        ALL_EVENTS = 3
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('variant', enum=cls.Variant, bytes=1, default=getattr(cls, 'variant', NotImplemented))

class QueryEventsByMessageId(QueryEvents):
    variant = QueryEvents.Variant.MESSAGE_ID
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('message_code', enum=_jaus.Message.Code, bytes=2, le=True)

class QueryEventsByType(QueryEvents):
    variant = QueryEvents.Variant.EVENT_TYPE
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('event_type', enum=EventType, bytes=1)

class QueryEventsByID(QueryEvents):
    variant = QueryEvents.Variant.EVENT_ID
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('event_id', bytes=1)

class QueryEventsAll(QueryEvents):
    variant = QueryEvents.Variant.ALL_EVENTS
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('all_events', bytes=1, default=0)


class QueryEventTimeout(_jaus.Message):
    message_code = _jaus.Message.Code.QueryEventTimeout
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class ConfirmEventRequest(_jaus.Message):
    message_code = _jaus.Message.Code.ConfirmEventRequest
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('request_id', bytes=1)
        yield _format.Integer('event_id', bytes=1)
        yield _jaus.ScaledFloat(
            'confirmed_periodic_rate',
            bytes=2,
            le=True,
            lower_limit=0,
            upper_limit=1092)



class RejectEventRequest(_jaus.Message):
    message_code = _jaus.Message.Code.RejectEventRequest
    class ResponseCode(_enum.Enum):
        PERIODIC_EVENTS_NOT_SUPPORTED = 1
        CHANGE_BASED_EVENTS_NOT_SUPPORTED = 2
        CONNECTION_REFUSED = 3
        INVALID_EVENT_SETUP = 4
        MESSAGE_NOT_SUPPORTED = 5
        INVALID_EVENT_ID_FOR_UPDATE = 6
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.with_presence_vector(
            bytes=1,
            required=[
                _format.Integer('request_id', bytes=1),
                _format.Enum('response_code', enum=ResponseCode, bytes=1),
            ],
            optional=[
                _format.Bytes('error_message', length=80),
            ])

class ReportEvents(_jaus.Message):
    message_code = _jaus.Message.Code.ReportEvents
    class Event(_format.Specification):
        @classmethod
        def _data(cls, data):
            yield from super()._data(data)
            yield _format.Enum('type', enum=EventType, bytes=1)
            yield _format.Integer('id', bytes=1)
            yield from _jaus.counted_bytes('query_message', bytes=4, le=True)

    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.counted_list('events', cls.Event, bytes=1)

class Event(_jaus.Message):
    message_code = _jaus.Message.Code.Event
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('event_id', bytes=1)
        yield _format.Integer('sequence_number', bytes=1)
        yield from _jaus.counted_bytes('report_message', bytes=4, le=True)

class ReportEventTimeout(_jaus.Message):
    message_code = _jaus.Message.Code.ReportEventTimeout
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('timeout', bytes=1)

class CommandEvent(_jaus.Message):
    message_code = _jaus.Message.Code.CommandEvent
    class Result(_enum.Enum):
        SUCCESSFUL = 0
        UNSUCCESSFUL = 1
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('event_id', bytes=1)
        yield _format.Enum('command_result', enum=CommandResult, bytes=1)


class EventRecord:
    def __init__(self, timeout, process, id, destination_id, message, type, periodic_rate, request_id):
        self.timeout = timeout
        self.id = id
        self.process = process
        self.sequence_number = 0
        self.destination_id = destination_id
        self.message = message
        self.type = type
        self.periodic_rate = periodic_rate
        self.request_id = request_id
    def stop(self):
        self.timeout.cancel()
        self.process.cancel()

class Service(_jaus.Service):
    name = 'events'
    uri = 'urn:jaus:jss:core:Events'
    version = (1, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handlers = {}
        self.events = {}
        self._next_event_id = 0
        self.event_timeout = 60

    async def close(self):
        for e in self.events.values():
            e.stop()
        await super().close()

    @_asyncio.coroutine
    def _fire_event(self, event):
        response = yield from self.component.dispatch_message(
            message=event.message,
            source_id=event.destination_id)

        yield from self.component.send_message(
            Event(
                event_id=event.id,
                sequence_number=event.sequence_number,
                report_message=response._write()),
            destination_id=event.destination_id)
        event.sequence_number += 1
        if event.sequence_number > 255:
            event.sequence_number = 0
    @_asyncio.coroutine
    def _event_timeout(self, event_id):
        event = self.events[event_id]
        yield from _asyncio.sleep(self.event_timeout, loop=self.loop)
        event.process.cancel()
        del self.events[event.id]
        yield from self.component.send_message(
            destination_id=event.destination_id,
            message=ConfirmEventRequest(
                request_id=event.request_id,
                event_id=event.id,
                confirmed_periodic_rate=event.periodic_rate))
    @_asyncio.coroutine
    def _process_event(self, event_id):
        event = self.events[event_id]
        if event.type is EventType.PERIODIC:
            while True:
                yield from self._fire_event(event)
                yield from _asyncio.sleep(1/event.periodic_rate, loop=self.loop)

    def _get_event_id(self):
        event_id = self._next_event_id
        self._next_event_id += 1
        return event_id

    def _normalise_periodic_rate(self, requested_periodic_rate, event_type):
        if event_type is EventType.EVERY_CHANGE:
            return 0
        else:
            return 5

    @_asyncio.coroutine
    def post_change(self, message_codes):
        for event in self.events.values():
            if (event.message.message_code in message_codes
                    and event.type is EventType.EVERY_CHANGE):
                yield from self._fire_event(event)

    @_jaus.message_handler(
        _jaus.Message.Code.CreateEvent,
        supports_events=False)
    @_asyncio.coroutine
    def on_create_event(self, message, source_id):
        event_id = self._get_event_id()
        periodic_rate = self._normalise_periodic_rate(
            message.requested_periodic_rate,
            message.event_type)
        event = EventRecord(
            id=event_id,
            destination_id=source_id,
            message=_jaus.Message._read(
                message.query_message),
            type=message.event_type,
            timeout=_asyncio.ensure_future(self._event_timeout(event_id), loop=self.loop),
            process=_asyncio.ensure_future(self._process_event(event_id), loop=self.loop),
            periodic_rate=periodic_rate,
            request_id=message.request_id)
        self.events[event_id] = event
        return ConfirmEventRequest(
            request_id=message.request_id,
            event_id=event_id,
            confirmed_periodic_rate=periodic_rate)

    @_jaus.message_handler(
        _jaus.Message.Code.UpdateEvent,
        supports_events=False)
    @_asyncio.coroutine
    def on_update_event(self, message, source_id):
        if message.event_id not in self.events:
            return RejectEventRequest(
                presence_vector=0,
                request_id=message.request_id,
                response_code=RejectEventRequest.ResponseCode.INVALID_EVENT_ID_FOR_UPDATE,
                error_message=None)
        periodic_rate = self._normalise_periodic_rate(
            message.requested_periodic_rate,
            message.event_type)
        event = EventRecord(
            id=message.event_id,
            destination_id=source_id,
            message=_jaus.Message._read(message.query_message),
            type=message.event_type,
            timeout=_asyncio.ensure_future(timeout, loop=self.loop),
            process=_asyncio.ensure_future(process, loop=self.loop),
            periodic_rate=periodic_rate,
            request_id=message.request_id)
        self.events[message.event_id].stop()
        self.events[message.event_id] = event
        return ConfirmEventRequest(
            request_id=message.request_id,
            event_id=message.event_id,
            confirmed_periodic_rate=periodic_rate)

    @_jaus.message_handler(
        _jaus.Message.Code.CancelEvent,
        supports_events=False)
    @_asyncio.coroutine
    def on_cancel_event(self, message, source_id):
        if message.event_id in self.events:
            event = self.events[message.event_id]
            event.stop()
            return ConfirmEventRequest(
                request_id=message.request_id,
                event_id=message.event_id,
                confirmed_periodic_rate=event.periodic_rate)
        else:
            return RejectEventRequest(
                presence_vector=0,
                request_id=message.request_id,
                response_code=RejectEventRequest.ResponseCode.INVALID_EVENT_ID_FOR_UPDATE,
                error_message=None)

    @_jaus.message_handler(
        _jaus.Message.Code.QueryEvents,
        supports_events=False)
    @_asyncio.coroutine
    def on_query_events(self, message, source_id):
        variant = message.variant
        def report_event(event):
            return ReportEvents.Event(
                type=event.type,
                id=event.id,
                query_message=event.message._write())
        if variant is QueryEvents.Variant.MESSAGE_ID:
            predicate = lambda event: event.message.message_code is message.message_code
        elif variant is QueryEvents.Variant.EVENT_TYPE:
            predicate = lambda event: event.type is message.event_type
        elif variant is QueryEvents.Variant.EVENT_ID:
            predicate = lambda event: event.id == message.event_id
        elif variant is QueryEvents.Variant.ALL_EVENTS:
            predicate = lambda event: True

        report = [
            report_event(event)
            for event in self.events.values()
            if predicate(event)]
        return ReportEvents(events=report)

    @_jaus.message_handler(
        _jaus.Message.Code.QueryEventTimeout,
        supports_events=False)
    @_asyncio.coroutine
    def on_query_event_timeout(self, message, source_id):
        return ReportEventTimeout(
            timeout=int(self.event_timeout/60))
