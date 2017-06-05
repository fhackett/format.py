import pytest

from bitstring import BitStream

from format.jaus.judp import Payload, Packet
from format.jaus import Message, Id

from format.jaus.core.discovery import QueryIdentification
from format.jaus.mobility.local_waypoint_driver import SetLocalWaypoint

@pytest.mark.parametrize('msg,expected', [
        (
            '0x0200110009ffffffff0201e803002b020400',
            Payload(
                transport_version=2,
                packets=[
                    Packet(
                        message_type=0,
                        HC_flags=Packet.HCFlags.NONE,
                        contents=b'\x00+\x02',
                        data_size=17,
                        data_flags=Packet.DataFlags.SINGLE_PACKET,
                        ack_nack=Packet.ACKNACKFlags.NO_RESPONSE_REQUIRED,
                        broadcast=Packet.BroadcastFlags.GLOBAL,
                        priority=Packet.Priority.STANDARD,
                        destination_id=Id(subsystem=65535, node=255, component=255),
                        source_id=Id(subsystem=1000, node=1, component=2),
                        sequence_number=4)]),),
    ])
def test__payloads__parse_3rd_party(msg, expected):
    bits = BitStream(msg)
    actual = Payload._read(bits)
    assert actual == expected
    assert actual.packets[0].data_size == len(bits)/8 - 1

@pytest.mark.parametrize('msg,expected', [
        ('0x002b02', QueryIdentification(type=QueryIdentification.QueryType.SUBSYSTEM)),
        (b'\r\x04\x00\xdcF\x03\x80\x00\x00\x00\x80', SetLocalWaypoint(x=10.00000629806891, y=2.3283064365386963e-05)),
    ])
def test__messages__parse_3rd_party(msg, expected):
    actual = Message._read(BitStream(msg))
    assert actual == expected

def test__id__parse():
    assert Id._read(BitStream('0x0201e803')) == Id(subsystem=1000, node=1, component=2)

