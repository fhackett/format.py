import format as _format
import format.jaus as _jaus


class QueryLocalPose(_jaus.Message):
    _variant_key = _jaus.Message.Code.QueryLocalPose
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
    _variant_key = _jaus.Message.Code.ReportLocalPose
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
            _format.Instance('timestamp', _jaus.Timestamp),
        ])

class Service(_jaus.Service):
    name = 'local_pose_sensor'
    uri = 'urn:jaus:jss:mobility:LocalPoseSensor'
    version = (1, 0)

    @message_handler(_jaus.Message.Code.QueryLocalPose)
    @_asyncio.coroutine
    def on_query_local_pose(self, message, **kwargs):
        fields = {}
        if 'x' in message.presence_vector:
            fields['x'] = 0
        if 'y' in message.presence_vector:
            fields['y'] = 0
        if 'yaw' in message.presence_vector:
            fields['yaw'] = 0
        if 'timestamp' in message.presence_vectore:
            fields['timestamp'] = Timestamp(ms=0, sec=0, min=0, hr=0, day=0)
        return ReportLocalPose(**fields)
