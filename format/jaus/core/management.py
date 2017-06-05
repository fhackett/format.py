import enum as _enum
import asyncio as _asyncio

import format as _format
import format.jaus as _jaus
import format.jaus.core.events as _events


class ManagementStatus(_enum.Enum):
    INIT = 0
    READY = 1
    STANDBY = 2
    SHUTDOWN = 3
    FAILURE = 4
    EMERGENCY = 5

class EmergencyCode(_enum.Enum):
    STOP = 1

class Shutdown(_jaus.Message):
    message_code = _jaus.Message.Code.Shutdown
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class Standby(_jaus.Message):
    message_code = _jaus.Message.Code.Standby
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class Resume(_jaus.Message):
    message_code = _jaus.Message.Code.Resume
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class Reset(_jaus.Message):
    message_code = _jaus.Message.Code.Reset
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class SetEmergency(_jaus.Message):
    message_code = _jaus.Message.Code.SetEmergency
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('emergency_code', enum=EmergencyCode, bytes=1)

class ClearEmergency(_jaus.Message):
    message_code = _jaus.Message.Code.ClearEmergency
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('emergency_code', enum=EmergencyCode, bytes=1)

class QueryStatus(_jaus.Message):
    message_code = _jaus.Message.Code.QueryStatus
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)


class ReportStatus(_jaus.Message):
    message_code = _jaus.Message.Code.ReportStatus
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('status', enum=ManagementStatus, bytes=1)
        yield _format.Integer('reserved', bytes=4, le=True, default=0)


class Service(_jaus.Service):
    name = 'management'
    uri = 'urn:jaus:jss:core:Management'
    version = (1, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = _jaus.ServiceState(
                {'status': ManagementStatus.STANDBY},
                loop=self.loop)
        self.state.watcher(
                fn=_events.change_watcher(self,
                    query_codes=(_jaus.Message.Code.QueryStatus,)),
                keys=('status',))
        self.old_status = None
        self.id_store = set()

    def __getattr__(self, key):
        if key in self.state:
            return self.state[key]
        else:
            raise AttributeError(key)

    def __setattr__(self, key, val):
        if key in ('status',):
            self.state[key] = val
        else:
            super().__setattr__(key, val)

    @_jaus.message_handler(
        _jaus.Message.Code.Shutdown,
        is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_shutdown(self, message, source_id):
        yield from self.component.access_control.reject_control()
        self.status = ManagementStatus.SHUTDOWN

    @_jaus.message_handler(
        _jaus.Message.Code.Standby,
        is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_standby(self, message, source_id):
        if self.status is ManagementStatus.READY:
            self.status = ManagementStatus.STANDBY

    @_jaus.message_handler(
        _jaus.Message.Code.Resume,
        is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_resume(self, message, source_id):
        # this is a command, so don't worry about not being controlled
        if self.status is ManagementStatus.STANDBY:
            self.status = ManagementStatus.READY

    @_jaus.message_handler(
        _jaus.Message.Code.Reset,
        is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_reset(self, message, source_id):
        if self.status in (ManagementStatus.STANDBY, ManagementStatus.READY):
            yield from self.component.access_control.reject_control()
            self.status = ManagementStatus.STANDBY

    @_jaus.message_handler(
        _jaus.Message.Code.SetEmergency)
    @_asyncio.coroutine
    def on_set_emergency(self, message, source_id):
        self.id_store |= {source_id}
        if self.status is not ManagementStatus.EMERGENCY:
            self.old_status = self.status
            self.status = ManagementStatus.EMERGENCY

    @_jaus.message_handler(
        _jaus.Message.Code.ClearEmergency)
    @_asyncio.coroutine
    def on_clear_emergency(self, message, source_id):
        self.id_store -= {source_id}
        if not self.id_store:
            self.status = self.old_status

    @_jaus.message_handler(
        _jaus.Message.Code.QueryStatus)
    @_asyncio.coroutine
    def on_query_status(self, message, source_id):
        return ReportStatus(
            status=self.status)
