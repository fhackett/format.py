import bitstring as _bitstring
import pytest as _pytest

import format as _f

class Foo(_f.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _f.Integer('foo', bits=6)
        yield _f.Integer('bar', bits=10, default=15)

@_pytest.fixture
def test_data1():
    return '0b000011 0000000010' # foo=3, bar=2

@_pytest.fixture
def f1():
    return Foo(foo=3, bar=2)

def test__constructor(f1):
    assert f1.foo == 3
    assert f1.bar == 2

def test___write(f1, test_data1):
    s = _bitstring.BitStream()
    assert f1 == Foo(foo=3, bar=2)
    f1._write(s)
    assert f1 == Foo(foo=3, bar=2)
    assert s == test_data1

def test___read(f1, test_data1):
    assert Foo._read(_bitstring.BitStream(test_data1)) == f1

def test__constructor_defaults():
    f2 = Foo(foo=2)
    assert f2.foo == 2
    assert f2.bar == 15

def test__constructor_raises_on_missing_required_field():
    with _pytest.raises(_f.MissingParameterError) as excinfo:
        Foo(bar=2)
    assert excinfo.value.args == ('foo',)

def test__constructor_raises_on_extra_argument():
    with _pytest.raises(_f.UnusedParametersError) as excinfo:
        Foo(foo=2, ping=5)
    assert excinfo.value.args == ({'ping': 5},)
