from fwdata import fwData
from panos.firewall import Firewall
from panos.policies import Rulebase, SecurityRule

# Establish connection
firewall = Firewall( fwData["mgmtUrl"],fwData['mgmtUser'],fwData["mgmtPass"],vsys=None, is_virtual=True)

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