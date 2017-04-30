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
    _variant_key = _jaus.Message.Code.Shutdown

class Standby(_jaus.Message):
    _variant_key = _jaus.Message.Code.Standby

class Resume(_jaus.Message):
    _variant_key = _jaus.Message.Code.Resume

class Reset(_jaus.Message):
    _variant_key = _jaus.Message.Code.Reset

class SetEmergency(_jaus.Message):
    _variant_key = _jaus.Message.Code.SetEmergency
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('emergency_code', enum=EmergencyCode, bytes=1)

class ClearEmergency(_jaus.Message):
    _variant_key = _jaus.Message.Code.ClearEmergency
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('emergency_code', enum=EmergencyCode, bytes=1)

class QueryStatus(_jaus.Message):
    _variant_key = _jaus.Message.Code.QueryStatus


class ReportStatus(_jaus.Message):
    _variant_key = _jaus.Message.Code.ReportStatus
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('status', enum=ManagementStatus, bytes=1)
        yield _format.Integer('reserved', bytes=4, le=True, default=0)


class Service(_jaus.Service):
    name = 'management'
    uri = 'urn:jaus:jss:core:Management'
    version = (1, 0)

    status = _events.change_watcher(
        '_status',
        query_codes=(_jaus.Message.Code.QueryStatus,))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._status = ManagementStatus.STANDBY
        self.old_status = None
        self.id_store = set()

    @_jaus.message_handler(
        _jaus.Message.Code.Shutdown,
        is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_shutdown(self, **kwargs):
        yield from self.component.access_control.reject_control()
        self.status = ManagementStatus.SHUTDOWN

    @_jaus.message_handler(
        _jaus.Message.Code.Standby,
        is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_standby(self, **kwargs):
        if self.status is ManagementStatus.READY:
            self.status = ManagementStatus.STANDBY

    @_jaus.message_handler(
        _jaus.Message.Code.Resume,
        is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_resume(self, **kwargs):
        # this is a command, so don't worry about not being controlled
        if self.status is ManagementStatus.STANDBY:
            self.status = ManagementStatus.READY

    @_jaus.message_handler(
        _jaus.Message.Code.Reset,
        is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_reset(self, **kwargs):
        if self.status in (ManagementStatus.STANDBY, ManagementStatus.READY):
            yield from self.component.access_control.reject_control()
            self.status = ManagementStatus.STANDBY

    @_jaus.message_handler(
        _jaus.Message.Code.SetEmergency)
    @_asyncio.coroutine
    def on_set_emergency(self, source_id, **kwargs):
        self.id_store |= set(source_id)
        if self.status is not ManagementStatus.EMERGENCY:
            self.old_status = self.status
            self.status = ManagementStatus.EMERGENCY

    @_jaus.message_handler(
        _jaus.Message.Code.ClearEmergency)
    @_asyncio.coroutine
    def on_clear_emergency(self, source_id, **kwargs):
        self.id_store -= set(source_id)
        if not self.id_store:
            self.status = self.old_status

    @_jaus.message_handler(
        _jaus.Message.Code.QueryStatus)
    @_asyncio.coroutine
    def on_query_status(self, **kwargs):
        return ReportStatus(
            status=self.status)
