import enum as _enum
import format as _format
import asyncio as _asyncio


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
        message_type = yield _format.Integer('message_type', bits=6, default=0)
        assert message_type == 0

        HC_flags = yield _format.Enum('HC_flags', enum=HCFlags, bits=2, default=HCFlags.NONE)
        packet_overhead = 14 if HC_flags is HCFlags.NONE else 16

        default_data_size = yield _format.Query(
            'contents',
            transform=lambda contents: len(contents) + packet_overhead)
        data_size = yield _format.Integer('data_size', bytes=2, le=True, default=default_data_size)

        # these fields only exist if header compression is used
        if HC_flags is not HCFlags.NONE:
            yield _format.Integer('HC_number', bytes=1)
            yield _format.Integer('HC_length', bytes=1)

        yield _format.Enum('priority', enum=Priority, bits=2, default=Priority.STANDARD)
        yield _format.Enum('broadcast', enum=BroadcastFlags, bits=2, default=BroadcastFlags.LOCAL)
        yield _format.Enum('ack_nack', enum=ACKNACKFlags, bits=2, default=ACKNACKFlags.NO_RESPONSE_REQUIRED)
        yield _format.Enum('data_flags', enum=DataFlags, bits=2)
        yield _format.Instance('destination_id', _format.jaus.Id)
        yield _format.Instance('source_id', _format.jaus.Id)
        yield _format.Bytes(
            'contents',
            length=data_size-packet_overhead)
        yield _format.Integer('sequence_number', bytes=2, le=True)

class Payload(_format.Specification):
    @classmethod
    def _data(self, data):
        version = yield _format.Integer('transport_version', bytes=1, default=2)
        # We only support transport version 2
        assert version == 2
        yield _format.Consume('packets', specification=Packet)

MAX_PAYLOAD_SIZE = 512



class JUDPProtocol(_asyncio.DatagramProtocol):
    def __init__(self, loop=None):
        super().__init__()
        if loop is None:
            loop = _asyncio.get_event_loop()
        self._accumulators = {}
        self._resolvers = {}
        self.loop = loop
        self.transport = None
        self.routings = {}
        self._send_queue = []
        async def sender():
            while True:
                self._send_packets(self._send_queue)
                self._send_queue = []
                await _asyncio.sleep(0, loop=self.loop)
        self._sender = _asyncio.ensure_future(sender(), loop=self.loop)

    def _find_destination_addr(self, packet):
        # TODO add broadcast options
        return self.routings[packet.destination_id]

    def _send_packets(self, packets):
        for addr, payload in self._make_payloads(packets):
            self.transport.sendto(payload._write(), addr)

    def _send_packet(self, packet):
        self._send_queue.append(packet)
        if packet.ack_nack is Packet.ACKNACKFlags.RESPONSE_REQUIRED:
            resolvers = self._resolvers.setdefault(packet.destination_id, {})
            resp = self.loop.create_future()
            resolvers[packet.sequence_number] = resp
            return resp

    def _split_into_packets(contents, **kwargs):
        SINGLE_PACKET_OVERHEAD = 14 + 1 # uncompressed packet overhead + payload overhead
        if len(contents)+SINGLE_PACKET_OVERHEAD <= MAX_PAYLOAD_SIZE:
            return Packet(
                contents=contents,
                data_flags=Packet.DataFlags.SINGLE_PACKET,
                **kwargs)
        else:
            parts = []
            while len(contents)+SINGLE_PACKET_OVERHEAD > MAX_PAYLOAD_SIZE:
                split_point = MAX_PAYLOAD_SIZE-SINGLE_PACKET_OVERHEAD
                parts.append(contents[:split_point])
                contents = contents[split_point:]
            if len(contents) > 0:
                parts.append(contents)
            begin = Packet(
                contents=parts[0],
                data_flags=Packet.DataFlags.FIRST_PACKET,
                **kwargs)
            end = Packet(
                contents=parts[-1],
                data_flags=Packet.DataFlags.LAST_PACKET,
                **kwargs)
            if len(parts) > 2:
                return [begin, end]
            else:
                middle = [
                    Packet(
                        contents=part,
                        data_flags=Packet.DataFlags.NORMAL_PACKET,
                        **kwargs)
                    for part in parts[1:-1]]
                return [begin] + middle + [end]

    def send_message(self, contents, source_id, destination_id, broadcast=Packet.BroadcastFlags.NONE, priority=Packet.Priority.STANDARD, require_ack=False):
        packets = self._split_into_packets(
            contents,
            priority=priority,
            broadcast=broadcast,
            ack_nack=Packet.ACKNACKFlags.RESPONSE_REQUIRED if require_ack else Packet.ACKNACKFlags.NO_RESPONSE_REQUIRED,
            destination_id=source_id,
            source_id=destination_id)
        if require_ack:
            async def check_send(packet):
                response = None
                retry_count = 0
                while response is None or response.ack_nack is not Packet.ACKNACKFlags.ACK:
                    if retry_count > 5:
                        raise Exception("couldn't send packet")
                    try:
                        response = await _asyncio.wait_for(
                            self._send_packet(packet), 5,
                            loop=self.loop)
                    except _asyncio.TimeoutError:
                        pass
                    retry_count += 1
            return _asyncio.ensure_future(
                _asyncio.gather(*[check_send(packet) for packet in packets], loop=self.loop),
                loop=self.loop)
        else:
            for packet in packets:
                self._send_packet(packet)

    def _calculate_payload_size(packets):
        return sum(packet.data_size for packet in packets) + 1

    def _make_payloads(self, packets):
        packets_by_destination_addr = {}
        for packet in packets:
            addr = self._find_destination_addr(packet)
            packets = packets_by_destination_addr.setdefault(addr, [])
            if self._calculate_payload_size(packets + packet) > MAX_PAYLOAD_SIZE:
                packets_by_destination_addr[addr] = [packet]
                yield addr, Payload(packets=packets)
            else:
                packets.append(packet)
        for addr, packets in packets_by_destination_addr:
            yield addr, Payload(packets=packets)

    def connection_made(self, transport):
        self.transport = transport

    def _find_first_packet(self, packet, dct):
        while packet is not None and p.data_flags is not Packet.DataFlags.FIRST_PACKET:
            packet = dct.get(packet.sequence_number-1)
        return packet

    def _try_sequence_from_first_packet(self, packet, dct):
        packets = []
        while packet is not None and p.data_flags is not Packet.DataFlags.LAST_PACKET:
            packets.append(packet)
            packet = dct.get(packet.sequence_number+1)
        if packet is not None:
            packets.append(packet)
            return packets
        else:
            return None

    def _try_reconstruct_message(self, packet, dst_id):
        if packet.data_flags is Packet.DataFlags.SINGLE_PACKET:
            return packet.contents
        if packet.data_flags is Packet.DataFlags.FIRST_PACKET:
            accumulators = self._accumulators[dst_id]
            first = self._find_first_packet(packet, accumulators)
            sequence = self._try_sequence_from_first_packet(packet, accumulators)
            if sequence is not None:
                for p in sequence:
                    del accumulators[p.sequence_number]
                return sum(p.contents for p in sequence)
            else:
                return None

    def _packet_received(self, packet, addr):
        self.routings[packet.source_id] = addr
        accumulators = self._accumulators.setdefault(packet.destination_id, {})
        resolvers = self._resolvers.setdefault(packet.destination_id, {})
        if packet.ack_nack in (Packet.ACKNACKFlags.ACK, Packet.ACKNACKFlags.NACK):
            if packet.sequence_number in resolvers:
                resolvers[packet.sequence_number].set_result(packet)
                del resolvers[packet.sequence_number]
        else:
            if packet.ack_nack is Packet.ACKNACKFlags.RESPONSE_REQUIRED:
                ack = Packet(
                    priority=packet.priority,
                    broadcast=Packet.BroadcastFlags.NONE,
                    ack_nack=Packet.ACKNACKFlags.ACK,
                    data_flags=packet.data_flags,
                    destination_id=packet.source_id,
                    source_id=packet.destination_id)
                self._send_packet(ack)
            msg = self._try_reconstruct_message(packet, packet.destination_id)
            if msg is None:
                accumulators[packet.destination_id] = packet
            else:
                self.message_received(msg, packet.source_id, packet.destination_id)

    def datagram_received(self, data, addr):
        payload = Payload._read(data)
        for packet in payload.packets:
            self._packet_received(packet, addr)

    def message_received(self, message, src_id, dst_id):
        pass

    def close(self):
        self._sender.cancel()
        super().close()

class ConnectedJUDPProtocol(JUDPProtocol):
    class Connection:
        def __init__(self, protocol, recv_queue, own_id):
            self.protocol = protocol
            self.recv_queue = recv_queue
            self.own_id = own_id
        async def listen(self):
            return (await self.recv_queue.get())
        async def send_message(self, contents, **kwargs):
            result = self.protocol.send_message(contents, source_id=self.own_id, **kwargs)
            if result is not None:
                await result
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._receive_queue = {}
    def message_received(self, message, src_id, dst_id):
        if dst_id in self._receive_queues:
            self._receive_queues[dst_id].put_nowait((message, src_id))
    def connect(self, own_id):
        recv_queue = _asyncio.Queue(loop=self.loop)
        self._receive_queues[own_id] = q
        return Connection(self, recv_queue, own_id)
