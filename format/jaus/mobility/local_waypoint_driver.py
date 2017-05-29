import asyncio as _asyncio
import math

import format.jaus as _jaus

def _local_waypoint():
    yield from _jaus.with_presence_vector(
        bytes=1,
        optional=[
            _jaus.ScaledFloat('x', bytes=4, le=True, lower_limit=-100000, upper_limit=100000),
            _jaus.ScaledFloat('y', bytes=4, le=True, lower_limit=-100000, upper_limit=100000),
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
    name = 'local_waypoint_driver'
    uri = 'urn:jaus:jss:mobility:LocalWaypointDriver'
    version = (1, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.travel_speed = 0
        self.x = 0
        self.y = 0

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
        fields = {}
        if 'x' in message.presence_vector:
            fields['x'] = self.x
        if 'y' in message.presence_vector:
            fields['y'] = self.y
        return ReportLocalWaypoint(**fields)

    @_jaus.message_handler(_jaus.Message.Code.SetTravelSpeed, is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_set_travel_speed(self, message, src_id):
        self.travel_speed = message.speed

    @_jaus.message_handler(_jaus.Message.Code.QueryTravelSpeed)
    @_asyncio.coroutine
    def on_query_travel_speed(self, message, src_id):
        return ReportTravelSpeed(speed=self.travel_speed)
