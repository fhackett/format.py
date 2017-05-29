import enum as _enum
import asyncio as _asyncio

import format as _format
import format.jaus as _jaus

import format.jaus.core._list_manager as _list_manager

class ListElementType(_enum.Enum):
    JAUS_MESSAGE = 0
    USER_DATA = 1

def _element_rec(): 
    yield _format.Integer('uid', bytes=2, le=True)
    yield _format.Integer('prev', bytes=2, le=True)
    yield _format.Integer('next', bytes=2, le=True)
    yield _format.Enum('format', enum=ListElementType, bytes=1, default=ListElementType.USER_DATA)
    # this is a variable format field apparently...
    # (only instance I've ever seen of one)
    yield from _jaus.counted_bytes('data', bytes=2, le=True)

class ListElement(_format.Specification):
    @classmethod
    def _data(cls, data):
        super()._data(data)
        yield from _element_rec()

class ListElementID(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('uid', bytes=2, le=True)

class SetElement(_jaus.Message):
    message_code = _jaus.Message.Code.SetElement
    @classmethod
    def _data(cls, data):
        yield from super()._data(cls)
        yield _format.Integer('request_id', bytes=1)
        yield from _jaus.counted_list('elements', ListElement, bytes=1)

class DeleteElement(_jaus.Message):
    message_code = _jaus.Message.Code.DeleteElement
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('request_id', bytes=1)
        yield from _jaus.counted_list('element_ids', ListElementID, bytes=1)

class QueryElement(_jaus.Message):
    message_code = _jaus.Message.Code.QueryElement
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('element_uid', bytes=2, le=True)

class QueryElementList(_jaus.Message):
    message_code = _jaus.Message.Code.QueryElementList
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)

class QueryElementCount(_jaus.Message):
    message_code = _jaus.Message.Code.QueryElementCount
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)


class ConfirmElementRequest(_jaus.Message):
    message_code = _jaus.Message.Code.ConfirmElementRequest
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('request_id', bytes=1)

class RejectElementRequest(_jaus.Message):
    message_code = _jaus.Message.Code.RejectElementRequest
    class ResponseCode(_enum.Enum):
        INVALID_ELEMENT_ID = 1
        INVALID_PREVIOUS_ELEMENT = 2
        INVALID_NEXT_ELEMENT = 3
        UNSUPPORTED_ELEMENT_TYPE = 4
        ELEMENT_ID_NOT_FOUND = 5
        OUT_OF_MEMORY = 6
        UNSPECIFIED_ERROR = 7
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('request_id', bytes=1)
        yield _format.Enum('response_code', enum=cls.ResponseCode, bytes=1)

class ReportElement(_jaus.Message):
    message_code = _jaus.Message.Code.ReportElement
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _element_rec()

class ReportElementList(_jaus.Message):
    message_code = _jaus.Message.Code.ReportElementList
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.counted_list('elements', ListElementID, bytes=2, le=True)

class ReportElementCount(_jaus.Message):
    message_code = _jaus.Message.Code.ReportElementCount
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('element_count', bytes=2, le=True)


class Service(_jaus.Service):
    name = 'list_manager'
    uri = 'urn:jaus:jss:core:ListManager'
    version = (1, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._impl = _list_manager.ListManager()

    @_jaus.message_handler(
        _jaus.Message.Code.QueryElement)
    @_asyncio.coroutine
    def on_query_element(self, message, source_id):
        element = self._impl.get(message.element_uid)
        if element is not None:
            return ReportElement(
                uid=element.uid,
                prev=element.prev,
                next=element.next,
                data=element.data)

    @_jaus.message_handler(
        _jaus.Message.Code.QueryElementList)
    @_asyncio.coroutine
    def on_query_element_list(self, message, source_id):
        return ReportElementList(
            elements=[
                ListElementID(uid=element.uid)
                for element in _list_manager.to_list(self._impl)])

    @_jaus.message_handler(
        _jaus.Message.Code.QueryElementCount)
    @_asyncio.coroutine
    def on_query_element_count(self, message, source_id):
        return ReportElementCount(
            element_count=self._impl.count)

    @_jaus.message_handler(
        _jaus.Message.Code.SetElement,
        is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_set_element(self, message, source_id):
        def rejection(response_code):
            return RejectElementRequest(
                request_id=message.request_id,
                response_code=response_code)
        try:
            self._impl.insert_batch([
                _list_manager.Element(next=e.next, prev=e.prev, uid=e.uid, data=e.data)
                for e in message.elements
            ])
            return ConfirmElementRequest(
                request_id=message.request_id)
        except _list_manager.BrokenReference as e:
            if e.uid == e.element.next:
                return rejection(RejectElementRequest.ResponseCode.INVALID_NEXT_ELEMENT)
            else:
                return rejection(RejectElementRequest.ResponseCode.INVALID_PREVIOUS_ELEMENT)
        except _list_manager.ElementAlreadyExists:
            return rejection(RejectElementRequest.ResponseCode.INVALID_ELEMENT_ID)
        except _list_manager.ListError:
            return rejection(RejectElementRequest.ResponseCode.UNSPECIFIED_ERROR)

    @_jaus.message_handler(
        _jaus.Message.Code.DeleteElement,
        is_command=True)
    @_jaus.is_command
    @_asyncio.coroutine
    def on_delete_element(self, message, source_id):
        def rejection(response_code):
            return RejectElementRequest(
                request_id=message.request_id,
                response_code=response_code)
        try:
            self._impl.delete_batch(e.uid for e in message.element_ids)
            return ConfirmElementRequest(
                request_id=message.request_id)
        except _list_manager.BrokenReference as e:
            if e.uid == e.element.next:
                return rejection(RejectElementRequest.ResponseCode.INVALID_NEXT_ELEMENT)
            else:
                return rejection(RejectElementRequest.ResponseCode.INVALID_PREVIOUS_ELEMENT)
        except _list_manager.NoSuchElement:
            return rejection(RejectElementRequest.ResponseCode.INVALID_ELEMENT_ID)
        except _list_manager.ListError:
            return rejection(RejectElementRequest.ResponseCode.UNSPECIFIED_ERROR)
