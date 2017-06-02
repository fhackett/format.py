import enum as _enum
import asyncio as _asyncio

import format as _format
import format.jaus as _jaus
import format.jaus.core.events as _events
import format.jaus.core.management as _management

class RequestControl(_jaus.Message):
    message_code = _jaus.Message.Code.RequestControl
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('authority_code', bytes=1)

class ReleaseControl(_jaus.Message):
    message_code = _jaus.Message.Code.ReleaseControl
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class QueryControl(_jaus.Message):
    message_code = _jaus.Message.Code.QueryControl
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class QueryAuthority(_jaus.Message):
    message_code = _jaus.Message.Code.QueryAuthority
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class SetAuthority(_jaus.Message):
    message_code = _jaus.Message.Code.SetAuthority
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('authority_code', bytes=1)

class QueryTimeout(_jaus.Message):
    message_code = _jaus.Message.Code.QueryTimeout
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)


class ReportControl(_jaus.Message):
    message_code = _jaus.Message.Code.ReportControl
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Instance('id', specification=_jaus.Id)
        yield _format.Integer('authority_code', bytes=1)

class RejectControl(_jaus.Message):
    message_code = _jaus.Message.Code.RejectControl
    class ResponseCode(_enum.Enum):
        CONTROL_RELEASED = 0
        NOT_AVAILABLE = 1
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('response_code', enum=cls.ResponseCode, bytes=1)

class ConfirmControl(_jaus.Message):
    message_code = _jaus.Message.Code.ConfirmControl
    class ResponseCode(_enum.Enum):
        CONTROL_ACCEPTED = 0
        NOT_AVAILABLE = 1
        INSUFFICIENT_AUTHORITY = 2
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('response_code', enum=cls.ResponseCode, bytes=1)


class ReportAuthority(_jaus.Message):
    message_code = _jaus.Message.Code.ReportAuthority
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('authority_code', bytes=1)

class ReportTimeout(_jaus.Message):
    message_code = _jaus.Message.Code.ReportTimeout
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('timeout', bytes=1)


class Service(_jaus.Service):
    name = 'access_control'
    uri = 'urn:jaus:jss:core:AccessControl'
    version = (1, 0)

    # Watchable attributes
    controlling_component = _events.change_watcher(
        '_controlling_component',
        query_codes=(_jaus.Message.Code.QueryControl,))
    authority = _events.change_watcher(
        '_authority',
        query_codes=(_jaus.Message.Code.QueryAuthority,))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._controlling_component = None
        self._authority = self.component.default_authority
        self.timeout_routine = _asyncio.ensure_future(self._timeout_routine(), loop=self.loop)
        self.timeout = 5 # seconds

    async def close(self):
        self.timeout_routine.cancel()
        await super().close()

    @property
    def is_controlled(self):
        return self.controlling_component is not None

    def has_control(self, component_id):
        return self.controlling_component == component_id

    @_asyncio.coroutine
    def _timeout_routine(self):
        if self.timeout == 0:
            return
        yield from _asyncio.sleep(self.timeout, loop=self.loop)
        if self.is_controlled:
            if not self.control_available:
                self.reset_timeout()
                return
            controlling_component = self.controlling_component
            print('Control by component {} timed out'
                .format(controlling_component))
            self.controlling_component = None
            yield from self.component.send_message(
                destination_id=controlling_component,
                message=RejectControl(
                    response_code=RejectControl.ResponseCode.CONTROL_RELEASED))

    def reset_timeout(self):
        self.timeout_routine.cancel()
        self.timeout_routine = _asyncio.ensure_future(self._timeout_routine(), loop=self.loop)

    @_jaus.message_handler(
        _jaus.Message.Code.RequestControl,
        supports_events=False)
    @_asyncio.coroutine
    def on_request_control(self, message, source_id):
        if not self.is_controlled:
            if self.control_available:
                if self.component.default_authority > message.authority_code:
                    return ConfirmControl(
                        response_code=ConfirmControl.ResponseCode.INSUFFICIENT_AUTHORITY)
                else:
                    self.controlling_component = source_id
                    self.authority = message.authority_code
                    self.reset_timeout()
                    return ConfirmControl(
                        response_code=ConfirmControl.ResponseCode.CONTROL_ACCEPTED)
            else:
                return ConfirmControl(
                    response_code=ConfirmControl.ResponseCode.NOT_AVAILABLE)
        else:
            if self.control_available:
                if self.controlling_component == source_id:
                    if self.component.default_authority > message.authority_code:
                        # somehow the controller's authority decreased, so we reject them
                        self.reset_timeout()
                        self.controlling_component = None
                        return RejectControl(
                            response_code=RejectControl.ResponseCode.CONTROL_RELEASED)
                    else:
                        # reset control info, same controller
                        self.authority = message.authority_code
                        self.reset_timeout()
                        return ConfirmControl(
                            response_code=ConfirmControl.ResponseCode.CONTROL_ACCEPTED)
                else:
                    if self.authority < message.authority_code:
                        # new controller has greater authority than current; switch
                        self.authority = message.authority_code
                        yield from self.reject_control(source_id)
                        return ConfirmControl(
                            response_code=ConfirmControl.ResponseCode.CONTROL_ACCEPTED)
                    else:
                        return ConfirmControl(
                            response_code=ConfirmControl.ResponseCode.INSUFFICIENT_AUTHORITY)
            else:
                return ConfirmControl(
                    response_code=ConfirmControl.ResponseCode.NOT_AVAILABLE)

    @_jaus.message_handler(
        _jaus.Message.Code.ReleaseControl,
        supports_events=False)
    @_asyncio.coroutine
    def on_release_control(self, message, source_id):
        if not self.is_controlled:
            return RejectControl(
                response_code=RejectControl.ResponseCode.CONTROL_RELEASED)
        else:
            if self.control_available:
                if source_id == self.controlling_component:
                    self.reset_timeout()
                    self.controlling_component = None
                    return RejectControl(
                        response_code=RejectControl.ResponseCode.CONTROL_RELEASED)
                else:
                    # if they are not the controlling client, apparently we are suposed
                    # to just ignore them...?
                    return None
            else:
                return RejectControl(
                    response_code=RejectControl.ResponseCode.NOT_AVAILABLE)

    @_asyncio.coroutine
    def reject_control(self, source_id=None):
        if self.is_controlled:
            self.reset_timeout()
            controlling_component = self.controlling_component
            self.controlling_component = source_id
            yield from self.component.send_message(
                destination_id=controlling_component,
                message=RejectControl(
                    response_code=RejectControl.ResponseCode.CONTROL_RELEASED))

    @_jaus.message_handler(
        _jaus.Message.Code.QueryTimeout)
    @_asyncio.coroutine
    def on_query_timeout(self, message, source_id):
        return ReportTimeout(
            timeout=self.timeout)

    @_jaus.message_handler(
        _jaus.Message.Code.QueryAuthority)
    @_asyncio.coroutine
    def on_query_authority(self, message, source_id):
        return ReportAuthority(
            authority_code=self.authority)

    @_jaus.message_handler(
        _jaus.Message.Code.QueryControl)
    @_asyncio.coroutine
    def on_query_control(self, message, source_id):
        if self.is_controlled:
            controlling_component = self.controlling_component
        else:
            controlling_component = _jaus.Id(subsystem=0, node=0, component=0)

        return ReportControl(
            id=controlling_component,
            authority_code=self.authority)

    @_jaus.message_handler(
        _jaus.Message.Code.SetAuthority,
        supports_events=False)
    @_asyncio.coroutine
    def on_set_authority(self, message, source_id):
        # manually implement command semantics since currently
        # services can't depend on themselves
        if not self.has_control(source_id):
            return None

        authority_code = message.authority_code
        if authority_code <= self.authority and authority_code >= self.component.default_authority:
            self.authority = message.authority_code

    @property
    def control_available(self):
        return self.component.management.status in (
            _management.ManagementStatus.READY,
            _management.ManagementStatus.STANDBY)
