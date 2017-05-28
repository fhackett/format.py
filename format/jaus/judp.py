import enum as _enum
import format as _format
import asyncio as _asyncio
import socket as _socket
import struct as _struct

#MULTICAST_ADDR = '239.255.0.1'
MULTICAST_ADDR = '224.3.29.71'
PORT = 3794
MAX_PAYLOAD_SIZE = 512

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

        HC_flags = yield _format.Enum('HC_flags', enum=Packet.HCFlags, bits=2, default=Packet.HCFlags.NONE)
        packet_overhead = 14 if HC_flags is Packet.HCFlags.NONE else 16

        default_data_size = yield _format.Query(
            'contents',
            transform=lambda contents: len(contents) + packet_overhead)
        data_size = yield _format.Integer('data_size', bytes=2, le=True, default=default_data_size)

        # these fields only exist if header compression is used
        if HC_flags is not Packet.HCFlags.NONE:
            yield _format.Integer('HC_number', bytes=1)
            yield _format.Integer('HC_length', bytes=1)

        yield _format.Enum('priority', enum=Packet.Priority, bits=2, default=Packet.Priority.STANDARD)
        yield _format.Enum('broadcast', enum=Packet.BroadcastFlags, bits=2, default=Packet.BroadcastFlags.LOCAL)
        yield _format.Enum('ack_nack', enum=Packet.ACKNACKFlags, bits=2, default=Packet.ACKNACKFlags.NO_RESPONSE_REQUIRED)
        yield _format.Enum('data_flags', enum=Packet.DataFlags, bits=2)
        yield _format.Instance('destination_id', specification=_format.jaus.Id)
        yield _format.Instance('source_id', specification=_format.jaus.Id)
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

class JUDPProtocol(_asyncio.DatagramProtocol):
    def __init__(self, loop=None, multicast_addr=MULTICAST_ADDR, multicast_port=PORT):
        super().__init__()
        if loop is None:
            loop = _asyncio.get_event_loop()
        self._accumulators = {}
        self._resolvers = {}
        self.loop = loop
        self.transport = None
        self.routings = {}
        self._send_queue = []
        self._sequence_numbers = {}
        self.multicast_addr = multicast_addr
        self.multicast_port = multicast_port

        async def sender():
            while True:
                self._send_packets(self._send_queue)
                self._send_queue = []
                await _asyncio.sleep(0.02, loop=self.loop)
        self._sender = _asyncio.ensure_future(sender(), loop=self.loop)

    def _find_destination_addr(self, packet):
        if packet.broadcast in (Packet.BroadcastFlags.LOCAL, Packet.BroadcastFlags.GLOBAL):
            return (self.multicast_addr, self.multicast_port)
        else:
            return self.routings[packet.destination_id]

    def _generate_next_sequence_number(self, source_id, destination_id):
        index = (source_id, destination_id)
        n = self._sequence_numbers.setdefault(index, 0)
        self._sequence_numbers[index] = n+1
        return n

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

    def _split_into_packets(self, contents, **kwargs):
        SINGLE_PACKET_OVERHEAD = 14 + 1 # uncompressed packet overhead + payload overhead
        source_id = kwargs['source_id']
        destination_id = kwargs['destination_id']
        if len(contents)+SINGLE_PACKET_OVERHEAD <= MAX_PAYLOAD_SIZE:
            return [Packet(
                contents=contents,
                data_flags=Packet.DataFlags.SINGLE_PACKET,
                sequence_number=self._generate_next_sequence_number(source_id, destination_id),
                **kwargs)]
        else:
            parts = []
            while len(contents)+SINGLE_PACKET_OVERHEAD > MAX_PAYLOAD_SIZE:
                split_point = MAX_PAYLOAD_SIZE-SINGLE_PACKET_OVERHEAD
                parts.append(contents[:split_point])
                contents = contents[split_point:]
            if len(contents) > 0:
                parts.append(contents)
            return [
                Packet(
                    contents=part,
                    data_flags=data_flag,
                    sequence_number=self._generate_next_sequence_number(source_id, destination_id),
                    **kwargs)
                for part, data_flag in zip(
                    parts,
                    (
                        [Packet.DataFlags.FIRST_PACKET]
                        +[Packet.DataFlags.NORMAL_PACKET]*(len(parts)-2)
                        +[Packet.DataFlags.LAST_PACKET]))]

    def send_message(self, contents, source_id, destination_id, broadcast=Packet.BroadcastFlags.NONE, priority=Packet.Priority.STANDARD, require_ack=False):
        packets = self._split_into_packets(
            contents,
            priority=priority,
            broadcast=broadcast,
            ack_nack=Packet.ACKNACKFlags.RESPONSE_REQUIRED if require_ack else Packet.ACKNACKFlags.NO_RESPONSE_REQUIRED,
            destination_id=destination_id,
            source_id=source_id)
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

    def _calculate_payload_size(self, packets):
        return sum(packet.data_size for packet in packets) + 1

    def _make_payloads(self, packets):
        packets_by_destination_addr = {}
        for packet in packets:
            addr = self._find_destination_addr(packet)
            packets = packets_by_destination_addr.setdefault(addr, [])
            if self._calculate_payload_size(packets + [packet]) > MAX_PAYLOAD_SIZE:
                yield addr, Payload(packets=packets)
                packets_by_destination_addr[addr] = [packet]
            else:
                packets.append(packet)
        for addr, packets in packets_by_destination_addr.items():
            yield addr, Payload(packets=packets)

    def connection_made(self, transport):
        self.transport = transport
        # thanks, reddit!
        # https://www.reddit.com/r/learnpython/comments/4drk0a/asyncio_multicast_udp_socket_on_342/

        # Allow receiving multicast broadcasts on the JAUS multicast group
        sock = self.transport.get_extra_info('socket')
        group = _socket.inet_aton(MULTICAST_ADDR)
        mreq = _struct.pack('4sL', group, _socket.INADDR_ANY)
        sock.setsockopt(_socket.IPPROTO_IP, _socket.IP_ADD_MEMBERSHIP, mreq)
        # Also allow sending
        sock.setsockopt(_socket.IPPROTO_IP, _socket.IP_MULTICAST_TTL, 32)
        sock.setsockopt(_socket.IPPROTO_IP, _socket.IP_MULTICAST_LOOP, 1)

    def _find_first_packet(self, packet, dct):
        while packet is not None and packet.data_flags is not Packet.DataFlags.FIRST_PACKET:
            packet = dct.get(packet.sequence_number-1)
        return packet

    def _try_sequence_from_first_packet(self, packet, dct):
        packets = []
        while packet is not None and packet.data_flags is not Packet.DataFlags.LAST_PACKET:
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
        accumulators = self._accumulators[dst_id]
        first = self._find_first_packet(packet, accumulators)
        sequence = self._try_sequence_from_first_packet(first, accumulators)
        if sequence is not None:
            for p in sequence:
                del accumulators[p.sequence_number]
            return b''.join(p.contents for p in sequence)
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
            accumulators[packet.sequence_number] = packet
            msg = self._try_reconstruct_message(packet, packet.destination_id)
            if msg is not None:
                self.message_received(msg, packet.source_id, packet.destination_id)

    def datagram_received(self, data, addr):
        payload = Payload._read(data)
        for packet in payload.packets:
            self._packet_received(packet, addr)

    def message_received(self, message, src_id, dst_id):
        pass

    async def close(self):
        self._sender.cancel()
        self.transport.close()
        await _asyncio.sleep(0, loop=self.loop)

class ConnectedJUDPProtocol(JUDPProtocol):
    class Connection:
        def __init__(self, protocol, recv_queue, own_id, loop):
            self.protocol = protocol
            self.recv_queue = recv_queue
            self.own_id = own_id
            self.loop = loop
        async def listen(self, timeout=None):
            return (await _asyncio.wait_for(
                self.recv_queue.get(),
                timeout=timeout,
		loop=self.loop))
        async def send_message(self, contents, **kwargs):
            result = self.protocol.send_message(contents, source_id=self.own_id, **kwargs)
            if result is not None:
                await result
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._receive_queues = {}
    def message_received(self, message, src_id, dst_id):
        if dst_id in self._receive_queues:
            self._receive_queues[dst_id].put_nowait((message, src_id))
        else:
            print('Received message with wrong destination', dst_id, 'I am', self._receive_queues.keys(), message)
    def connect(self, own_id):
        recv_queue = _asyncio.Queue(loop=self.loop)
        self._receive_queues[own_id] = recv_queue
        return ConnectedJUDPProtocol.Connection(self, recv_queue, own_id, self.loop)
