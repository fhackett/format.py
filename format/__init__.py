import abc as _abc
import bitstring as _bitstring


class MissingParameterError(Exception):
    """A parameter was missing on instantiation of a Specification."""

class Record(metaclass=_abc.ABCMeta):
    representation = NotImplemented
    def __init__(self, name, default=NotImplemented):
        super().__init__()
        self.name = name
        self.default = default
    def instantiate(self, dct):
        if self.name in dct:
            return dct[self.name]
        else:
            if self.default is NotImplemented:
                raise MissingParameterError(self.name)
            if self.representation is not NotImplemented:
                return self.representation(self.default)
            else:
                return self.default
    @_abc.abstractmethod
    def read(self, stream, data):
        pass
    @_abc.abstractmethod
    def write(self, val, stream, data):
        pass

class Query(Record):
    """
    Gets the current value of a data field.

    Will be `NotImplemented` on read or if you are trying to read a field that has not yet been parsed.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def instantiate(self, dct):
        return dct.get(self.name, self.default)
    def read(self, stream, data):
        return self.default
    def write(self, val, stream, data):
        pass

class SpecificationMeta(_abc.ABCMeta):
    def __new__(meta, name, bases, props):
        # Detect variants by their magic class attribute
        if '_variant_key_name' in props:
            props['_registry'] = {}
            props['_is_variant'] = True
        else:
            props['_is_variant'] = False
        klass = super(SpecificationMeta, meta).__new__(meta, name, bases, props)
        # Auto-register subclasses of variants in the variant system
        if '_variant_key' in props:
            for base in bases:
                if base._is_variant:
                    base._registry[props['_variant_key']] = klass
        return klass

def _run_generator(gen, data, fn):
    try:
        current = None
        while True:
            try:
                record = gen.send(current)
                current = fn(record)
                if record.name is not None:
                    data[record.name] = current
            except Exception as e:
                gen.throw(e)
    except StopIteration as ex:
        return ex.value

class Composite(Record):
    def __init__(self, name, gen, default=NotImplemented, *args, **kwargs):
        super().__init__(name, default)
        self.gen_args = args
        self.gen_kwargs = kwargs
        self.gen = gen
    def read(self, stream, data):
        def run(record):
            return record.read(stream, data)
        return _run_generator(
            self.gen(self.name, *self.gen_args, **self.gen_kwargs),
            data=data,
            fn=run)
    def write(self, val, stream, data):
        def run(record):
            d = data.get(record.name)
            if d is not None and record.default is not NotImplemented:
                d = record.default
            record.write(d, stream, data)
            return d
        _run_generator(
            self.gen(self.name, *self.gen_args, **self.gen_kwargs),
            data=data,
            fn=run)

class UnusedParametersError(Exception):
    """A Specification was instantiated with arguments that were not used."""

class Specification(metaclass=SpecificationMeta):
    """Tricked out superclass for making inheritable parser and record types.

    Override _data with a generator that yields `Record`s - this will produce a
    class that allows the following:
    ```
    class Message(Specification):
        @classmethod
        def _data(cls, data):
            yield Integer('foo', bytes=1)

    m = Message(foo=5)
    Message._read(b'5')
    s = BitStream()
    m._write(s)
    assert s == b'5'
    ```

    The magic class attributes '_variant_key_name' and '_variant_key'
    allow the definition of variant classes that while uninstantiatable will seamlessly replace
    themselves with an instance of a subclass when instantiated or read.

    This makes it easy to make a class of messages that describes some common structural preamble,
    keeping all the subclasses DRY.
    """
    def __new__(cls, **kwargs):
        if cls._is_variant:
            data = {}
            def run(record):
                return record.instantiate(kwargs)
            _run_generator(
                gen=cls._data(data),
                data=data,
                fn=run)
            return cls._registry[data[cls._variant_key_name]](**kwargs)
        else:
            return super(Specification, cls).__new__(cls)
    def __init__(self, **kwargs):
        super().__init__()
        data = self.__dict__
        # Don't allow people to instantiate a variant subclass with the wrong key
        sup = super()
        if isinstance(sup, Specification) and sup._is_variant:
            if sup._variant_key_name in kwargs:
                assert kwargs[sup._variant_key_name] == self._variant_key
            else:
                kwargs[sup._variant_key_name] = self._variant_key

        fields_used = set()
        self._fields = fields_used
        def run(record):
            fields_used.add(record.name)
            return record.instantiate(kwargs)
        _run_generator(
            gen=self._data(data),
            data=data,
            fn=run)

        # check we used all the fields provided
        unused_fields = set(kwargs.keys()) - fields_used
        if len(unused_fields):
            raise UnusedParametersError({
                name: kwargs[name]
                for name in unused_fields})
    def __eq__(self, other):
        if isinstance(other, type(self)):
            own_fields = {name: getattr(self, name) for name in self._fields}
            other_fields = {name: getattr(other, name) for name in other._fields}
            return own_fields == other_fields
        else:
            return super().__eq__(self, other)
    def __repr__(self):
        return '{name}({repr})'.format(
            name=type(self).__name__,
            repr=repr({
                name: getattr(self, name)
                for name in self._fields}))
    @classmethod
    def _read(cls, stream):
        data = {}
        old_pos = stream.pos
        def run(record):
            return record.read(stream, data)
        _run_generator(
            gen=cls._data(data),
            data=data,
            fn=run)
        # if you try to instantiate a variant, you should get a subclass.
        # otherwise, business as usual
        if cls._is_variant:
            stream.pos = old_pos
            return cls._registry[data[cls._variant_key_name]]._read(stream)
        else:
            return cls(**data)
    @classmethod
    @_abc.abstractmethod
    def _data(cls, data):
        return iter(())
    def _write(self, stream):
        data = self.__dict__
        def run(record):
            d = data.get(record.name)
            if d is None and record.default is not NotImplemented:
                d = record.default
            record.write(d, stream, data)
            return d
        _run_generator(
            gen=self._data(data),
            data=data,
            fn=run)

class Integer(Record):
    def __init__(self, name, bits=None, bytes=None, le=None, unsigned=True, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        if bits is None:
            bits = 0
        if bytes is not None:
            bits += bytes*8
        assert bits > 0
        self.max = (2**bits) - 1
        if le is None:
            endianness = ''
        else:
            endianness = 'le' if le else 'be'
        self.format = '{}int{}:{}'.format(
            'u' if unsigned else '',
            endianness,
            bits)
    def read(self, stream, data):
        return stream.read(self.format)
    def write(self, val, stream, data):
        stream.insert('{}={}'.format(self.format, val))

class Bits(Record):
    representation = _bitstring.Bits
    def __init__(self, name, bits=None, bytes=None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        if bits is None:
            bits = 0
        if bytes is not None:
            bits += bytes * 8
        self.bits = bits
        self.format = 'bits:{}'.format(bits)
    def read(self, stream, data):
        return stream.read(self.format)
    def write(self, val, stream, data):
        stream.insert(_bitsting.Bits(val, length=self.bits))

class Bytes(Record):
    representation = bytes
    def __init__(self, name, length, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._format = 'bytes:{}'.format(length)
        self.length = length
    def read(self, stream, data):
        return stream.read(self._format)
    def write(self, val, stream, data):
        assert len(val) == self.length
        stream.insert(val)

class String(Bytes):
    representation = str
    def __init__(self, name, encoding='ascii', *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.encoding = encoding
    def read(self, stream, data):
        return super().read(stream).decode(encoding=self.encoding)
    def write(self, val, stream, data):
        super().write(val.encode(encoding=self.encoding))

class Enum(Integer):
    def __init__(self, name, enum, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.representation = enum
        self.enum = enum
    def read(self, stream, data):
        data = super().read(stream)
        return self.enum(data)
    def write(self, val, stream, data):
        super().write(val.value, stream)

class Instance(Record):
    def __init__(self, name, specification, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.specification = specification
    def read(self, stream, data):
        return self.specification._read(stream)
    def write(self, val, stream, data):
        val._write(stream)

class Repeat(Instance):
    def __init__(self, name, count, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.count = count
    def read(self, stream, data):
        return [super().read(stream) for i in range(self.count)]
    def write(self, val, stream, data):
        for v in val:
            super().write(v, stream)
