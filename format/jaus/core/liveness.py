import asyncio as _asyncio

import format.jaus as _jaus


class QueryHeartbeatPulse(_jaus.Message):
    _variant_key = _jaus.Message.Code.QueryHeartbeatPulse

class ReportHeartbeatPulse(_jaus.Message):
    _variant_key = _jaus.Message.Code.ReportHeartbeatPulse

class Service(_jaus.Service):
    name = 'liveness'
    uri = 'urn:jaus:jss:core:ListManager'
    version = (1, 0)

    @_jaus.message_handler(_jaus.Message.Code.QueryHeartbeatPulse)
    @_asyncio.coroutine
    def on_query_heartbeat(self, **kwargs):
        return ReportHeartbeatPulse()
