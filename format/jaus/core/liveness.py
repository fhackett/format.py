import asyncio as _asyncio

import format.jaus as _jaus


class QueryHeartbeatPulse(_jaus.Message):
    _variant_key = _jaus.Message.Code.QueryHeartbeatPulse
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class ReportHeartbeatPulse(_jaus.Message):
    _variant_key = _jaus.Message.Code.ReportHeartbeatPulse
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class Service(_jaus.Service):
    name = 'liveness'
    uri = 'urn:jaus:jss:core:ListManager'
    version = (1, 0)

    @_jaus.message_handler(_jaus.Message.Code.QueryHeartbeatPulse)
    @_asyncio.coroutine
    def on_query_heartbeat(self, message, source_id):
        return ReportHeartbeatPulse()
