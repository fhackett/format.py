import format.jaus as _jaus
import format.jaus.core.events as _events
import asyncio as _asyncio
import math


def _local_waypoint():
    yield from _jaus.with_presence_vector(
        bytes=1,
        required=[
            _jaus.ScaledFloat('x', bytes=4, le=True, lower_limit=-100000, upper_limit=100000),
            _jaus.ScaledFloat('y', bytes=4, le=True, lower_limit=-100000, upper_limit=100000),
        ],
        optional=[
            _jaus.ScaledFloat('z', bytes=4, le=True, lower_limit=-100000, upper_limit=100000),
            _jaus.ScaledFloat('roll', bytes=2, le=True, lower_limit=-math.pi, upper_limit=math.pi),
            _jaus.ScaledFloat('pitch', bytes=2, le=True, lower_limit=-math.pi, upper_limit=math.pi),
            _jaus.ScaledFloat('yaw', bytes=2, le=True, lower_limit=-math.pi, upper_limit=math.pi),
            _jaus.ScaledFloat('waypoint_tolerance', bytes=2, le=True, lower_limit=0, upper_limit=100),
            _jaus.ScaledFloat('path_tolerance', bytes=4, le=True, lower_limit=0, upper_limit=100000),
        ])


class SetLocalWaypoint(_jaus.Message):
    message_code = _jaus.Message.Code.SetLocalWaypoint

    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _local_waypoint()


class QueryLocalWaypoint(_jaus.Message):
    message_code = _jaus.Message.Code.QueryLocalWaypoint

    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _jaus.PresenceVector('presence_vector', bytes=1, fields=[
            'x',
            'y',
            'z',
            'roll',
            'pitch',
            'yaw',
            'waypoint_tolerance',
            'path_tolerance',
        ])


class QueryTravelSpeed(_jaus.Message):
    message_code = _jaus.Message.Code.QueryTravelSpeed

    @classmethod
    def _data(cls, data):
        yield from super()._data(data)


class SetTravelSpeed(_jaus.Message):
    message_code = _jaus.Message.Code.SetTravelSpeed

    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _jaus.ScaledFloat('speed', bytes=4, le=True, lower_limit=0, upper_limit=327.67)


class ReportLocalWaypoint(_jaus.Message):
    message_code = _jaus.Message.Code.ReportLocalWaypoint

    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _local_waypoint()


class ReportTravelSpeed(_jaus.Message):
    message_code = _jaus.Message.Code.ReportTravelSpeed

    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _jaus.ScaledFloat('speed', bytes=4, le=True, lower_limit=0, upper_limit=327.67)


class Service(_jaus.Service):
    """
    Responsible for moving the platform when given a single target waypoint, desired travel speed, current pose,
    and current velocity state.

    The waypoint remains unchanged until a new SetLocalWaypoint message is received.
    """

    name = 'local_waypoint_driver'
    uri = 'urn:jaus:jss:mobility:LocalWaypointDriver'
    version = (1, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = _jaus.ServiceState(
                {
                    'travel_speed': 0,
                    'x': 0,
                    'y': 0,
                },
                loop=self.loop)
        self.state.watcher(_events.change_watcher(self, query_codes=(_jaus.Message.Code.QueryTravelSpeed,)),
                keys=('x','y',))
        self.state.watcher(_events.change_watcher(self, query_codes=(_jaus.Message.Code.QueryLocalWaypoint,)),
                keys=('travel_speed',))
    
    def __getattr__(self, key):
        if key in self.state:
            return self.state[key]
        else:
            raise AttributeError(key)

    def __setattr__(self, key, val):
        if key in ('x', 'y', 'travel_speed',):
            self.state[key] = val
        else:
            super().__setattr__(key, val)


    @_jaus.message_handler(_jaus.Message.Code.SetLocalWaypoint, is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_set_local_waypoint(self, message, src_id):
        if message.x is not None:
            self.x = message.x
        if message.y is not None:
            self.y = message.y

    @_jaus.message_handler(_jaus.Message.Code.QueryLocalWaypoint)
    @_asyncio.coroutine
    def on_query_local_waypoint(self, message, src_id):
        return ReportLocalWaypoint(x=self.x, y=self.y)

    @_jaus.message_handler(_jaus.Message.Code.SetTravelSpeed, is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_set_travel_speed(self, message, src_id):
        self.travel_speed = message.speed

    @_jaus.message_handler(_jaus.Message.Code.QueryTravelSpeed)
    @_asyncio.coroutine
    def on_query_travel_speed(self, message, src_id):
        return ReportTravelSpeed(speed=self.travel_speed)
