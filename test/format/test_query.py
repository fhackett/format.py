import format as _format
import pytest as _pytest
import bitstring as _bitstring

class A(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        d = yield _format.Query('d')

def test__empty_read():
    a = A(d=2)
    assert a.d == 2
    assert a._write() == b''
    assert A._read(b'') == A()

def counted_list(name, specification):
    lst = yield _format.Query(name)
    count = yield _format.Integer(
        bytes=1,
        default=_format.transform(lst, lambda lst: len(lst)))
    lst = yield _format.Repeat(specification=specification, count=count, default=lst)
    return (yield _format.Computed(name, value=lst))

class BS(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('foo', bytes=1)

class B(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from counted_list('lst', BS)

def test__counted_list():
    s = b'\x03\x01\x02\x03'
    assert B(lst=[BS(foo=1),BS(foo=2),BS(foo=3)])._write() == s
    assert B._read(s) == B(lst=[BS(foo=1),BS(foo=2),BS(foo=3)])
