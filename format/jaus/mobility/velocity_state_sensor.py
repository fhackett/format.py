import asyncio as _asyncio

import format as _format
import format.jaus as _jaus


class QueryVelocityState(_jaus.Message):
    message_code = _jaus.Message.Code.QueryVelocityState
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _jaus.PresenceVector('presence_vector', bytes=2,
            fields=[
                'x',
                'y',
                'x',
                'velocity_rms',
                'roll',
                'pitch',
                'yaw_rate',
                'angular_rms',
                'timestamp',
            ])

class ReportVelocityState(_jaus.Message):
    message_code = _jaus.Message.Code.ReportVelocityState
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.with_presence_vector(
            bytes=2,
            optional=[
                _jaus.ScaledFloat('x', bytes=4, le=True, lower_limit=-327.68, upper_limit=327.67),
                _jaus.ScaledFloat('y', bytes=4, le=True, lower_limit=-327.68, upper_limit=327.67),
                _jaus.ScaledFloat('z', bytes=4, le=True, lower_limit=-327.68, upper_limit=327.67),
                _jaus.ScaledFloat('velocity_rms', bytes=4, le=True, lower_limit=0, upper_limit=100),
                _jaus.ScaledFloat('roll', bytes=2, le=True, lower_limit=-32.768, upper_limit=32.767),
                _jaus.ScaledFloat('pitch', bytes=2, le=True, lower_limit=-32.768, upper_limit=32.767),
                _jaus.ScaledFloat('yaw_rate', bytes=2, le=True, lower_limit=-32.768, upper_limit=32.767),
                _jaus.ScaledFloat('angular_rms', bytes=2, le=True, lower_limit=0, upper_limit=math.pi),
                _format.Instance('timestamp', _jaus.Timestamp),
            ])

class Service(_jaus.Service):
    name = 'velocity_state_sensor'
    uri = 'urn:jaus:jss:mobility:VelocityStateSensor'
    version = (1, 0)

    @_jaus.message_handler(_jaus.Message.Code.QueryVelocityState)
    @_asyncio.coroutine
    def on_query_velocity_state(self, message, **kwargs):
        fields = {}
        if 'x' in message.presence_vector:
            fields['x'] = 0
        if 'yaw_rate' in message.presence_vector:
            fields['yaw_rate'] = 0
        if 'timestamp' in message.presence_vector:
            fields['timestamp'] = _jaus.Timestamp(ms=0, sec=0, min=0, hr=0, day=0)
        return ReportVelocityState(**fields)
