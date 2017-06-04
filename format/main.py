import asyncio

from format.jaus.core.management import ManagementStatus
from format.jaus.judp import ConnectedJUDPProtocol, Packet, make_multicast_socket
from format.jaus import Id, Component
from format.jaus.services import *

SUB_SYSTEM = 101
#192.168.1.101

def notify_status():
    while True:
        current_status = navigation_reporting_component.management.status

        if current_status in (ManagementStatus.EMERGENCY, ManagementStatus.SHUTDOWN):
            print("Shutting down")
            break
        else:
            print("\n\neverything is okay\n\n")
        yield from asyncio.sleep(1)


event_loop = asyncio.get_event_loop()

# Platform Management will have node id of 1 and component id of 1
platform_management_component = \
    Component(id=Id(subsystem=SUB_SYSTEM, node=1, component=1),
              name="PlatformManagement",
              node_name="plat_man_comp",
              subsystem_name="jackfrostpm",
              services=[
                  TransportService,
                  DiscoveryService,
                  EventsService,
                  LivenessService,
                  AccessControlService
              ]
              )

#Navigation and Reporting Component is arbitrarily assigned node id of 1 and component id of 2
navigation_reporting_component = \
    Component(id=Id(subsystem=SUB_SYSTEM, node=1, component=2),
              name="NavigationReport",
              node_name="nav_rep_comp",
              subsystem_name="jackfrostnr",
              services=[
                TransportService,
                EventsService,
                AccessControlService,
                ManagementService,
                LivenessService,
                LocalWaypointDriverService,
                LocalWaypointListDriverService,
                VelocityStateSensorService,
                LocalPoseSensorService
              ]
              )

_, protocol = event_loop.run_until_complete(event_loop.create_datagram_endpoint(
    lambda: ConnectedJUDPProtocol(loop=event_loop),
    sock=make_multicast_socket(3794)))

# Hook up the Component with the protocol
plat_man_connection = protocol.connect(Id(subsystem=SUB_SYSTEM, node=1, component=1))
platform_management_component.listen(plat_man_connection)

nav_rep_connection = protocol.connect(Id(subsystem=SUB_SYSTEM, node=1, component=2))
navigation_reporting_component.listen(nav_rep_connection)

event_loop.run_until_complete(notify_status())
