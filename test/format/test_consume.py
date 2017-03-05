import pytest
import format

class Foo(format.Specification):
    @classmethod
    def _data(self, data):
        yield from super()._data(data)
        yield format.Integer('foo', bytes=1)

class Bar(format.Specification):
    @classmethod
    def _data(self, data):
        yield from super()._data(data)
        yield format.Consume('foos', specification=Foo)

def test__instantiate():
    assert Bar(foos=[]) == Bar(foos=[])
    assert Bar(foos=[Foo(foo=1), Foo(foo=2)]) == Bar(foos=[Foo(foo=1), Foo(foo=2)])

def test___write():
    b1 = Bar(foos=[])
    b2 = Bar(foos=[Foo(foo=1), Foo(foo=2)])

    assert b1._write() == b''
    assert b2._write() == b'\x01\x02'

def test___read():
    assert Bar._read(b'') == Bar(foos=[])
    assert Bar._read(b'\x02\x03') == Bar(foos=[Foo(foo=2), Foo(foo=3)])
