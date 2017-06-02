import asyncio
from format.jaus.judp import ConnectedJUDPProtocol, Packet, make_multicast_socket
from format.jaus import Id, Component


event_loop = asyncio.get_event_loop()

component = Component(123, "a", "b", "c")

_, protocol = event_loop.run_until_complete(event_loop.create_datagram_endpoint(
    lambda: ConnectedJUDPProtocol(loop=event_loop),
    sock=make_multicast_socket()))

connection = protocol.connect(123)
component.listen(connection)

event_loop.run_forever()
