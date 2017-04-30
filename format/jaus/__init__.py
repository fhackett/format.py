import abc as _abc
import enum as _enum
import asyncio as _asyncio
from functools import wraps

import format as _format


class Id(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('subsystem', bytes=2, le=True)
        yield _format.Integer('node', bytes=1)
        yield _format.Integer('component', bytes=1)

def message_handler(message_code, is_command=False, supports_events=True):
    def process(fn):
        fn.is_message_handler = True
        fn.message_code = message_code
        fn.supports_events = supports_events
        fn.is_command = is_command
        return fn
    return process

def is_command(fn):
    """
    Annotation to make simple has-authority-or-ignore commands more DRY.

    Wraps a coroutine with another coroutine, and requires a component with
    an access_control service. Makes no sense otherwise.
    """
    @wraps(fn)
    @_asyncio.coroutine
    def wrapper(self, source_id, **kwargs):
        if self.component.access_control.has_control(source_id):
            return (yield from fn(self, source_id=source_id, **kwargs))
        else:
            # ignore commands with insufficient authority
            return None
    return wrapper

class ServiceMeta(_abc.ABCMeta):
    def __init__(klass, name, bases, dct):
        klass.message_handler_names = {
            val.message_code: name
            for name, val in dct.items()
            if getattr(val, 'is_message_handler', False)
        }
        return super().__init__(name, bases, dct)

class Service(metaclass=ServiceMeta):
    def __init__(self, component, loop=None):
        super().__init__()
        self.component = component
        self.loop = loop
        self.message_handlers = {
            message_code: getattr(self, handler_name)
            for message_code, handler_name in self.message_handler_names.items()
        }
    async def close(self):
        pass

class Component:
    def __init__(self, id, name, node_name, subsystem_name, services=[], default_authority=0, loop=None):
        self.id = id
        self.services = {}
        self.default_authority = default_authority
        self.name = name
        self.node_name = node_name
        self.subsystem_name = subsystem_name
        self.loop = loop if loop is not None else _asyncio.get_event_loop()

        self._listener = None
        self._connection = None
        self.message_handlers = {}

        for service in services:
            instance = service(component=self, loop=self.loop)
            self.services[instance.name] = instance
            self.message_handlers.update(instance.message_handlers)

    def __getattr__(self, name):
        if name in self.services:
            return self.services[name]
        else:
            raise AttributeError(name)

    async def dispatch_message(self, message, source_id):
        if message.message_code in self.message_handlers:
            handler = self.message_handlers[message.message_code]
            return await handler(message, source_id)
        else:
            print('Message with no registered handler: {}'.format(message))

    async def send_message(self, message, destination_id):
        await self._connection.send_message(message._write(), destination_id=destination_id)

    async def _listener_fn(self, connection, loop=None):
        self._connection = connection
        while True:
            message_bytes, source_id = await connection.listen()
            message = Message._read(message_bytes)
            print('Message received', message, source_id)
            result = await self.dispatch_message(message, source_id)
            if result is not None:
                await self.send_message(result, destination_id=source_id)

    def listen(self, connection, *, loop=None):
        if loop is None:
            loop = _asyncio.get_event_loop()
        assert self._listener is None
        self._listener = loop.create_task(self._listener_fn(connection, loop=loop))

    async def close(self):
        if self._listener is not None:
            self._listener.cancel()
            self._listener = None
        for s in self.services.values():
            await s.close()

class Message(_format.Specification):
    _variant_key_name = 'message_code'

    class Code(_enum.Enum):
        ## Liveness
        QueryHeartbeatPulse = 0x2202

        ReportHeartbeatPulse = 0x4202

        ## Events
        CreateEvent = 0x01F0
        UpdateEvent = 0x01F1
        CancelEvent = 0x01F2
        CreateCommandEvent = 0x01F6
        QueryEvents = 0x21F0
        QueryEventTimeout = 0x21F2

        ConfirmEventRequest = 0x01F3
        RejectEventRequest = 0x01F4
        ReportEvents = 0x41F0
        Event = 0x41F1
        ReportEventTimeout = 0x41F2
        CommandEvent = 0x41F6

        ## Access Control
        RequestControl = 0x000D
        ReleaseControl = 0x000E
        QueryControl = 0x200D
        QueryAuthority = 0x2001
        SetAuthority = 0x0001
        QueryTimeout = 0x2003

        ReportControl = 0x400D
        RejectControl = 0x0010
        ConfirmControl = 0x000F
        ReportAuthority = 0x4001
        ReportTimeout = 0x4003

        ## Management
        Shutdown = 0x0002
        Standby = 0x0003
        Resume = 0x0004
        Reset = 0x0005
        SetEmergency = 0x0006
        ClearEmergency = 0x0007
        QueryStatus = 0x2002

        ReportStatus = 0x4002

        ## ListManager
        SetElement = 0x041A
        DeleteElement = 0x041B
        QueryElement = 0x241A
        QueryElementList = 0x241B
        QueryElementCount = 0x241C

        ConfirmElementRequest = 0x041C
        RejectElementRequest = 0x041D
        ReportElement = 0x441A
        ReportElementList = 0x441B
        ReportElementCount = 0x441C

        ## Discovery
        RegisterServices = 0x0B00
        QueryIdentification = 0x2B00
        QueryConfiguration = 0x2B01
        QuerySubsystemList = 0x2B02
        QueryServices = 0x2B03
        QueryServiceList = 0x2B04

        ReportIdentification = 0x4B00
        ReportConfiguration = 0x4B01
        ReportSubsystemList = 0x4B02
        ReportServices = 0x4B03
        ReportServiceList = 0x4B04

        ## LocalPoseSensor
        QueryLocalPose = 0x2403

        ReportLocalPose = 0x4403

        ## VelocityStateSensor
        QueryVelocityState = 0x2404

        ReportVelocityState = 0x4404

        ## LocalWaypointDriver
        SetTravelSpeed = 0x040A
        SetLocalWaypoint = 0x040D
        QueryTravelSpeed = 0x240A
        QueryLocalWaypoint = 0x240D

        ReportTravelSpeed = 0x440A
        ReportLocalWaypoint = 0x440D

        ## LocalWaypointListDriver
        QueryActiveElement = 0x241E

        ReportActiveElement = 0x441E

    @classmethod
    @_abc.abstractmethod
    def _data(cls, data):
        super()._data(data)
        yield _format.Enum(
            'message_code',
            enum=cls.Code,
            bytes=2, le=True,
            default=getattr(cls, 'message_code', NotImplemented))

def counted_bytes(name, *args, **kwargs):
    bytes = yield _format.Query(name)
    default_count = NotImplemented
    if bytes is not NotImplemented:
        default_count = len(bytes)

    count_name = name + '_count'
    count = (yield _format.Integer(count_name, default=default_count, **kwargs))
    yield _format.Bytes(name, length=count)

class ScaledFloat(_format.Integer):
    def __init__(self, name, lower_limit, upper_limit, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
    def read(self, *args, **kwargs):
        result = super().read(*args, **kwargs)
        return (result/self.max * self.range) + self.lower_limit
    @property
    def range(self):
        return self.upper_limit - self.lower_limit
    def write(self, val, stream, data):
        encoded_value = round(
            (val - self.lower_limit)/self.range*self.max)
        super().write(encoded_value, stream, data)

class Timestamp(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield ScaledFloat('ms', bits=10, lower_limit=0, upper_limit=999)
        yield ScaledFloat('sec', bits=6, lower_limit=0, upper_limit=59)
        yield ScaledFloat('min', bits=6, lower_limit=0, upper_limit=59)
        yield ScaledFloat('hr', bits=5, lower_limit=0, upper_limit=23)
        yield ScaledFloat('day', bits=5, lower_limit=1, upper_limit=31)

def with_presence_vector(required=[], optional=[], bits=None, bytes=None, le=True):
    if bits is None:
        bits = 0
    if bytes is not None:
        bits += bytes*8
    default_presence_vector = _bitstring.Bits(
        auto=[
            (yield _format.Query(opt.name)) is not None
            for opt in optional
        ],
        length=bits)

    presence_vector = yield _format.Bits(
        'presence_vector',
        bits=bits,
        le=le,
        default=default_presence_vector)
    for req in required:
        yield req
    for present, opt in zip(presence_vector, optional):
        if present:
            yield opt
        else:
            yield _format.Record(opt.name, default=None)

class PresenceVector(_format.Bits):
    def __init__(self, name, fields, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.fields = fields
    def read(self, *args, **kwargs):
        mask = super().read(*args, **kwargs)
        return {field for field, present in zip(self.fields, mask) if present}
    def write(self, val, stream):
        super().write(_bitstring.Bits(field in val for field in self.fields))

def counted_list(name, specification, *args, **kwargs):
    lst = yield _format.Query(name)
    count = yield _format.Integer(
        default=len(lst) if lst is not NotImplemented else NotImplemented,
        *args, **kwargs)
    return (yield _format.Repeat(name, specification=specification, count=count))

def counted_string(name, *args, **kwargs):
    s = yield _format.Query(name)
    count = yield _format.Integer(
        default=len(s) if s else NotImplemented,
        *args, **kwargs)
    return (yield _format.String(name, length=count))
