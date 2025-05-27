from fwdata import fwData
from panos.firewall import Firewall
from panos.network import EthernetInterface, Zone, TunnelInterface, VirtualRouter, StaticRoute
from panos.objects import AddressObject, AddressGroup
from panos.policies import Rulebase, SecurityRule, NatRule

##### Establish connection
firewall = Firewall(fwData["mgmtUrl"],fwData['mgmtUser'],fwData["mgmtPass"],vsys=None, is_virtual=True)
firewall.vsys = None

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

# Configure the interfaces (eth1/1 untrust)
eth1 = EthernetInterface(fwData['untrustInt'], mode='layer3')
eth1.ip = fwData['untrustAddr']
firewall.add(eth1)
eth1.set_zone('untrust', mode='layer3', refresh=True, update=True)
eth1.set_virtual_router('default', refresh=True, update=True)
eth1.create()

# Configure the interfaces (eth1/2 trust)
eth2 = EthernetInterface(fwData['trustInt'], mode='layer3')
eth2.ip = fwData['trustAddr']
firewall.add(eth2)
eth2.set_zone('trust', mode='layer3', refresh=True, update=True)
eth2.set_virtual_router('default', refresh=True, update=True)
eth2.create()

# Configure the interfaces (tun.1 vpn)
tun1 = TunnelInterface(fwData['tunnelInt'], fwData['tunnelAddr'])
firewall.add(tun1)
tun1.set_zone('vpn', mode='layer3', refresh=True, update=True)
tun1.set_virtual_router('default', refresh=True, update=True)
tun1.create()

firewall.commit()


######### Configure Static Routes ###################
# Get the default virtual router
vrouter = VirtualRouter(name='default')

#Create a default static route
defaultRoute = StaticRoute(
    name='default-route',
    destination='0.0.0.0/0',
    interface=fwData["untrustInt"],
    nexthop_type='ip-address',
    nexthop=fwData['untrustDFGW']
)


#Create a static route for mobile users
mobileUsers = StaticRoute(
    name='Prisma-Access-Mobile-Users',
    destination=fwData['paMobUserSubnet'],
    interface=fwData['tunnelInt'],
    nexthop_type='None'
)


#Create a static route for prisma infrastructure
prismaInfra = StaticRoute(
    name='Prisma-Access-Infrastructure',
    destination=fwData["paInfraSubnet"],
    interface=fwData["tunnelInt"],
    nexthop_type='None'
)

#Add and commit config
firewall.add(vrouter)
vrouter.add(defaultRoute)
vrouter.add(mobileUsers)
vrouter.add(prismaInfra)
defaultRoute.create()
mobileUsers.create()
prismaInfra.create()

firewall.commit()

####### Configure Address and Group Objects #############

# Define basic address objects
addr = {}
addr['paMU'] = AddressObject("Prisma-Mobile-Users", fwData['paMobUserSubnet'], description="Company web server")
addr['paInfra'] = AddressObject("Prisma-Infrastructure", fwData['paInfraSubnet'], description="Company web server")
addr['netTrust'] = AddressObject("Trust-Network", fwData['trustSubnet'], description="Company web server")
addr['netUntrust'] = AddressObject("Untrust-Network", fwData['untrustSubnet'], description="Company web server")
addr['panorama'] = AddressObject("Panorama-Server", fwData['panoramaAddr'], description="Company web server")

# Create objects
for i in addr:
  firewall.add(addr[i])
  addr[i].create()

# Define basic address objects
grp = {}
grp['paMU'] = AddressGroup("Prisma-Trust-Networks", ["Prisma-Mobile-Users","Prisma-Infrastructure"], description="Company web server")

# Create objects
for i in grp:
  firewall.add(grp[i])
  grp[i].create()

####### Configure Firewall Policy #############

# Get existing rule base
base = Rulebase()
firewall.add(base)

# Define rule attributes
rule=[]
rule.append( SecurityRule(
    name='Outbound Internet',
    description='Allow trust zone to internet',
    fromzone=['trust'],
    tozone=['untrust'],
    source=["Trust-Network"],
    destination=['any'],
    application=['ssl','web-browsing'],
    action='allow',
    log_end=True
))
rule.append( SecurityRule(
    name='Allow SC Tunnel',
    description='Allow the service connection VPN traffic',
    fromzone=['vpn'],
    tozone=['vpn'],
    source=[fwData['untrustAddr'],fwData['paSCEndpoint']],
    destination=[fwData['untrustAddr'],fwData['paSCEndpoint']],
    application=['ike','ipsec-esp','ipsec-esp-udp'],
    action='allow',
    log_end=True
))
rule.append( SecurityRule(
    name='Outbound to Prisma Access',
    description='Allow traffic across the service connection',
    fromzone=['trust'],
    tozone=['vpn'],
    source=["Trust-Network"],
    destination=['Prisma-Trust-Networks'],
    application=['any'],
    action='allow',
    log_end=True
))
rule.append( SecurityRule(
    name='Inbound from Prisma Access',
    description='Allow traffic across the service connection',
    fromzone=['vpn'],
    tozone=['trust'],
    source=['Prisma-Trust-Networks'],
    destination=['Trust-Network'],
    application=['any'],
    action='allow',
    log_end=True
))
rule.append( SecurityRule(
    name='Allow Panorama Management',
    description='Allow Panorama Management from the Internet',
    fromzone=['untrust'],
    tozone=['trust'],
    source=['any'],
    destination=[fwData['panoramaAddr']],
    application=['ssl','web-browsing','ssh'],
    action='allow',
    log_end=True
))
rule.append( SecurityRule(
    name='Deny All',
    description='Deny All',
    fromzone=['any'],
    tozone=['any'],
    source=['any'],
    destination=['any'],
    application=['any'],
    action='deny',
    log_end=True
))

# Add the rules and create
for i in rule:
  base.add(i)
  i.create()

# Commit Changes
firewall.commit()

####### Configure NAT Policy #############
# Get existing rule base
base = Rulebase()
firewall.add(base)

# Define rule attributes
internetNAT = NatRule(
    name='Outbound Internet',
    description='Allow internal systems on Trust zone to internet with PAT',
    nat_type='ipv4',
    fromzone=['trust'],
    tozone=['untrust'],
    to_interface=fwData['untrustInt'],
    source=['Trust-Network'],
    source_translation_type='dynamic-ip-and-port',
    source_translation_address_type='interface-address',
    source_translation_interface=fwData['untrustInt'],
)
panoramaNAT = NatRule(
    name='Panorama Management',
    description='Allow external management of Panorama on Trust Network',
    nat_type='ipv4',
    fromzone=['untrust'],
    tozone=['trust'],
    to_interface=fwData['untrustInt'],
    service='service-https',
    source=['any'],
    destination=[fwData['untrustAddr'][:-3]],
    source_translation_type='dynamic-ip-and-port',
    source_translation_address_type='interface-address',
    source_translation_interface=fwData['trustInt'],
    destination_translated_address='Panorama-Server'
)

# Create the NAT rule using the SDK
configFail=False
try:
    base.add(internetNAT)
    internetNAT.create()
    print("Outbound NAT rule created successfully!")
except Exception as e:
    print(f"Error creating Outbound NAT rule: {e}")
    configFail=True

# Create the NAT rule using the SDK
try:
    base.add(panoramaNAT)
    panoramaNAT.create()
    print("Panorama NAT rule created successfully!")
except Exception as e:
    print(f"Error creating Panorama NAT rule: {e}")
    configFail=True

# Commit Changes
if not configFail:
  firewall.commit()


####### Configure Security Policy #############
  # Get existing rule base
base = Rulebase()
firewall.add(base)

# Define rule attributes
rule=[]
rule.append( SecurityRule(
    name='Outbound Internet',
    description='Allow trust zone to internet',
    fromzone=['trust'],
    tozone=['untrust'],
    source=["Trust-Network"],
    destination=['any'],
    application=['ssl','web-browsing'],
    action='allow',
    log_end=True
))
rule.append( SecurityRule(
    name='Allow SC Tunnel',
    description='Allow the service connection VPN traffic',
    fromzone=['vpn'],
    tozone=['vpn'],
    source=[fwData['untrustAddr'],fwData['paSCEndpoint']],
    destination=[fwData['untrustAddr'],fwData['paSCEndpoint']],
    application=['ike','ipsec-esp','ipsec-esp-udp'],
    action='allow',
    log_end=True
))
rule.append( SecurityRule(
    name='Outbound to Prisma Access',
    description='Allow traffic across the service connection',
    fromzone=['trust'],
    tozone=['vpn'],
    source=["Trust-Network"],
    destination=['Prisma-Trust-Networks'],
    application=['any'],
    action='allow',
    log_end=True
))
rule.append( SecurityRule(
    name='Inbound from Prisma Access',
    description='Allow traffic across the service connection',
    fromzone=['vpn'],
    tozone=['trust'],
    source=['Prisma-Trust-Networks'],
    destination=['Trust-Network'],
    application=['any'],
    action='allow',
    log_end=True
))
rule.append( SecurityRule(
    name='Allow Panorama Management',
    description='Allow Panorama Management from the Internet',
    fromzone=['untrust'],
    tozone=['trust'],
    source=['any'],
    destination=[fwData['panoramaAddr']],
    application=['ssl','web-browsing','ssh'],
    action='allow',
    log_end=True
))
rule.append( SecurityRule(
    name='Deny All',
    description='Deny All',
    fromzone=['any'],
    tozone=['any'],
    source=['any'],
    destination=['any'],
    application=['any'],
    action='deny',
    log_end=True
))

# Add the rules and create
for i in rule:
    try:
        base.add(i)
        i.create()
        print("Security Policy created successfully!")
    except Exception as e:
        print(f"Error creating Security Policy: {e}")
        configFail=True

# Commit Changes
if not configFail:
    firewall.commit()