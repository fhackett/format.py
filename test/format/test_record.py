import format as _format
import pytest as _pytest

class rc(_format.Record):
    def read(self, stream, data):
        pass
    def write(self, val, stream, data):
        pass

def test__normal_instantiate():
    assert rc('foo', 'bar').instantiate({'foo': 'ping'}) == 'ping'
    assert rc('foo', 'bar').instantiate({}) == 'bar'
    with _pytest.raises(_format.MissingParameterError) as excinfo:
        rc('foo').instantiate({})
    assert excinfo.value.args == ('foo',)

def test__anonymous_instantiate():
    assert rc(default='bar').instantiate({}) == 'bar'
    with _pytest.raises(_format.NoDefaultForAnonymousRecord):
        rc().instantiate({})

class rep:
    def __init__(self, v):
        self.v = v
    def __eq__(self, other):
        return self.v == other.v

class rrc(rc):
    representation = rep

def test__represented_instantiate():
    assert rrc(default='bar').instantiate({}) == rep('bar')
    assert rrc('foo', 'bar').instantiate({}) == rep('bar')
    assert rrc('foo', 'bar').instantiate({'foo': 'ping'}) == 'ping'
