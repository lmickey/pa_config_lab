from fwdata import fwData
from panos.firewall import Firewall
from panos.network import VirtualRouter, StaticRoute

##### Establish connection
firewall = Firewall(
    hostname=fwData["mgmtUrl"],
    username=fwData['mgmtUser'],
    password=fwData["mgmtPass"]
)

# Get the default virtual router
vr = VirtualRouter(name='default')
firewall.add(vr)

#Create a default static route
default_route = StaticRoute(
    name='default-route',
    destination='0.0.0.0/0',
    interface=fwData["untrustInt"],
    next_hop='192.168.1.1',
    admin_distance=10,
    metric=10
)

vr.add(default_route)
default_route.create()

#Create a default static route
default_route = StaticRoute(
    name='default-route',
    destination='0.0.0.0/0',
    interface=fwData["untrustInt"],
    next_hop='192.168.1.1',
    admin_distance=10,
    metric=10
)

vr.add(default_route)
default_route.create()

#Create a route for Mobile User Networks
default_route = StaticRoute(
    name='Mobile-Users',
    destination=fwData["paMobUserSubnet"],
    interface=fwData["untrustInt"],
    next_hop='192.168.1.1',
    admin_distance=10,
    metric=10
)

vr.add(default_route)
default_route.create()
