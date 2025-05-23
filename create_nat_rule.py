from fwdata import fwData
from panos.firewall import Firewall
from panos.policies import Rulebase, NatRule

# Establish connection
firewall = Firewall( fwData["mgmtUrl"],fwData['mgmtUser'],fwData["mgmtPass"],vsys=None, is_virtual=True)

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
    service='any',
    source=['Trust-Network'],
    destination=['any'],
    source_translation_type='persistent dynamic ip and port',
    source_translation_address_type='interface address',
    source_translation_interface=fwData['untrustInt'],
    source_translation_translated_addresses=fwData['untrustAddr']
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
    source_translation_type='dynamic ip and port',
    source_translation_address_type='interface address',
    source_translation_interface=fwData['trustInt'],
    source_translation_translated_addresses=fwData['trustAddr'],
    #destination_translation_type='static',
    destination_translated_address='Panorama-Server'
)

# Create the NAT rule using the SDK
configFail=False
#try:
base.add(internetNAT)
internetNAT.create()
#    print("Outbound NAT rule created successfully!")
#except Exception as e:
#    print(f"Error creating Outbound NAT rule: {e}")
#    configFail=True

# Create the NAT rule using the SDK
try:
    base.add(panoramaNAT)
    panoramaNAT.create()
    print("Panorama NAT rule created successfully!")
except Exception as e:
    print(f"Error creating Panorama NAT rule: {e}")
    configFail=True

# Commit Changes
#if not configFail:
#  firewall.commit()
