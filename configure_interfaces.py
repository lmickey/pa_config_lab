from fwdata import fwData
from panos.firewall import Firewall
from panos.network import EthernetInterface, Zone, TunnelInterface

##### Establish connection
firewall = Firewall(
    hostname=fwData["mgmtUrl"],
    username=fwData['mgmtUser'],
    password=fwData["mgmtPass"]
)

##### Define the zones and add to the firewall
zoneTrust = Zone(name='trust', mode='layer3')
zoneUntrust = Zone(name='untrust', mode='layer3')
zoneVPN = Zone(name='vpn', mode='layer3')

firewall.add(zoneTrust)
firewall.add(zoneUntrust)
firewall.add(zoneVPN)
zoneTrust.create()
zoneUntrust.create()
zoneVPN.create()

# Configure the interfaces (eth0/1 untrust)
eth0 = EthernetInterface(fwData['untrustInt'], mode='layer3')
eth0.ip = fwData['untrustAddr']  # Assign IP address and subnet mask
eth0.zone = 'untrust'          # Assign to a security zone
eth0.set_virtual_router = 'default'

firewall.add(eth0)
eth0.create()

# Configure the interfaces (eth1/1 trust)
eth1 = EthernetInterface(fwData['trustInt'], mode='layer3')
eth1.ip = fwData['trustAddr']  # Assign IP address and subnet mask
eth1.zone = 'trust'          # Assign to a security zone
eth1.set_virtual_router = 'default'

firewall.add(eth1)
eth1.create()

# Configure the interfaces (tun.1 vpn)
tun1 = TunnelInterface(fwData['tunnelInt'], fwData['tunnelAddr'])
tun1.zone = 'vpn'          # Assign to a security zone
tun1.set_virtual_router = 'default'

firewall.add(tun1)
tun1.create()
