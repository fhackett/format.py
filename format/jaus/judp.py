import enum as _enum
import format as _format


class Packet(_format.Specification):

    class DataFlags(_enum.Enum):
        SINGLE_PACKET = 0b00
        FIRST_PACKET = 0b01
        NORMAL_PACKET = 0b10
        LAST_PACKET = 0b11
    class HCFlags(_enum.Enum):
        NONE = 0
        REQUESTED = 1
        HC_LENGTH = 2
        COMPRESSED = 3
    class Priority(_enum.Enum):
        LOW = 0
        STANDARD = 1
        HIGH = 2
        SAFETY = 3
    class BroadcastFlags(_enum.Enum):
        # single destination
        NONE = 0
        # local destinations only
        LOCAL = 1
        # all destinations
        GLOBAL = 2
    class ACKNACKFlags(_enum.Enum):
        NO_RESPONSE_REQUIRED = 0
        RESPONSE_REQUIRED = 1
        # Responses
        NACK = 2
        ACK = 3

    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('message_type', bits=6, default=0)
        assert data['message_type'] == 0

        yield _format.Enum('HC_flags', enum=HCFlags, bits=2, default=HCFlags.NONE)
        packet_overhead = 14 if data['HC_flags'] is HCFlags.NONE else 16

        if 'contents' in data:
            default_data_size = len(data['contents']) + packet_overhead
        else:
            default_data_size = NotImplemented
        yield _format.Integer('data_size', bytes=2, le=True, default=default_data_size)

        # these fields only exist if header compression is used
        if data['HC_flags'] is not HCFlags.NONE:
            yield _format.Integer('HC_number', bytes=1)
            yield _format.Integer('HC_length', bytes=1)

        yield _format.Enum('priority', enum=Priority, bits=2, default=Priority.STANDARD)
        yield _format.Enum('broadcast', enum=BroadcastFlags, bits=2, default=BroadcastFlags.LOCAL)
        yield _format.Enum('ack_nack', enum=ACKNACKFlags, bits=2, default=ACKNACKFlags.NO_RESPONSE_REQUIRED)
        yield _format.Enum('data_flags', enum=DataFlags, bits=2)
        yield _format.Instance('destination_id', _format.jaus.Id),
        yield _format.Instance('source_id', _format.jaus.Id)
        yield _format.Bytes(
            'contents',
            length=data['data_size']-packet_overhead)
        yield _format.Integer('sequence_number', bytes=2, le=True),
