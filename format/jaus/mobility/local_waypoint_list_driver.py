import asyncio as _asyncio
import format.jaus as _jaus
import format as _format

class QueryActiveElement(_jaus.Message):
    message_code = _jaus.Message.Code.QueryActiveElement
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class ReportActiveElement(_jaus.Message):
    message_code = _jaus.Message.Code.ReportActiveElement
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('uid', bytes=2, le=True)

class Service(_jaus.Service):
    name = 'local_waypoint_list_driver'
    uri = 'urn:jaus:jss:mobility:LocalWaypointListDriver'
    version = (1, 0)

    @_jaus.message_handler(_jaus.Message.Code.QueryActiveElement)
    @_asyncio.coroutine
    def on_query_active_element(self, messsage, source_id):
        return ReportActiveElement(uid=0)
