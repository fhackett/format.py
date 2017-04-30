import format
import pytest
import enum

class A(format.Specification):
    _variant_key_name = 'foo'
    class AA(enum.Enum):
        A1 = 1
        A2 = 2
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield format.Enum('foo', enum=cls.AA, bytes=1, default=getattr(cls, 'foo', NotImplemented))

class A1(A):
    _variant_key_name = 'bar'
    foo = A.AA.A1
    class BB(enum.Enum):
        B1 = 3
        B2 = 4
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield format.Enum('bar', enum=cls.BB, bytes=1, default=getattr(cls, 'bar', NotImplemented))

class A2(A):
    foo = A.AA.A2

class B1(A1):
    bar = A1.BB.B1

class B2(A1):
    bar = A1.BB.B2

def test__single_level_variant():
    assert A2() == A(foo=A.AA.A2)
    assert A._read(b'\x02') == A2()
    assert A2()._write() == b'\x02'

def test__multi_level_variant():
    assert B1() == A1(bar=A1.BB.B1)
    assert B2() == A1(bar=A1.BB.B2)
    assert B1()._write() == b'\x01\x03'
    assert A1._read(b'\x01\x04') == B2()
