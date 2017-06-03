import format as _format
import format.jaus as _jaus
import format.jaus.core.events as _events
import asyncio as _asyncio
import math


class QueryLocalPose(_jaus.Message):
    message_code = _jaus.Message.Code.QueryLocalPose

    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _jaus.PresenceVector('presence_vector', bytes=2, fields=[
            'x',
            'y',
            'z',
            'position_rms',
            'roll',
            'pitch',
            'yaw',
            'attitude_rms',
        ])


class ReportLocalPose(_jaus.Message):
    message_code = _jaus.Message.Code.ReportLocalPose

    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.with_presence_vector(bytes=2, optional=[
            _jaus.ScaledFloat('x', bytes=4, le=True, lower_limit=-100000, upper_limit=100000),
            _jaus.ScaledFloat('y', bytes=4, le=True, lower_limit=-100000, upper_limit=100000),
            _jaus.ScaledFloat('z', bytes=4, le=True, lower_limit=-100000, upper_limit=100000),
            _jaus.ScaledFloat('position_rms', bytes=4, le=True, lower_limit=0, upper_limit=100),
            _jaus.ScaledFloat('roll', bytes=2, le=True, lower_limit=-math.pi, upper_limit=math.pi),
            _jaus.ScaledFloat('pitch', bytes=2, le=True, lower_limit=-math.pi, upper_limit=math.pi),
            _jaus.ScaledFloat('yaw', bytes=2, le=True, lower_limit=-math.pi, upper_limit=math.pi),
            _jaus.ScaledFloat('attitude_rms', bytes=2, le=True, lower_limit=0, upper_limit=math.pi),
            _format.Instance('timestamp', specification=_jaus.Timestamp),
        ])


class Service(_jaus.Service):
    """
    Responsible for reporting the local position and orientation of the platform relative to a local reference frame.
    """

    name = 'local_pose_sensor'
    uri = 'urn:jaus:jss:mobility:LocalPoseSensor'
    version = (1, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = _jaus.ServiceState(
                {
                    'x': 0,
                    'y': 0,
                    'yaw': 0,
                },
                loop=self.loop)
        self.state.watcher(_events.change_watcher(self, query_codes=(_jaus.Message.Code.QueryLocalPose,)),
                keys=('x', 'y', 'yaw'))
 
    def __getattr__(self, key):
        if key in self.state:
            return self.state[key]
        else:
            return super().__getattr__(self, key)

    def __setattr__(self, key, val):
        if key in ('x', 'y', 'yaw',):
            self.state[key] = val
        else:
            super().__setattr__(key, val)

    @_jaus.message_handler(_jaus.Message.Code.QueryLocalPose)
    @_asyncio.coroutine
    def on_query_local_pose(self, message, source_id):
        fields = {}
        if 'x' in message.presence_vector:
            fields['x'] = 0
        if 'y' in message.presence_vector:
            fields['y'] = 0
        if 'yaw' in message.presence_vector:
            fields['yaw'] = 0
        if 'timestamp' in message.presence_vector:
            fields['timestamp'] = Timestamp(ms=0, sec=0, min=0, hr=0, day=0)
        return ReportLocalPose(**fields)
