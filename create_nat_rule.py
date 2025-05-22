from fwdata import fwData
from panos.firewall import Firewall
from panos.policies import Rulebase, NatRule

# Establish connection
firewall = Firewall(
    hostname=fwData["mgmtUrl"],
    username=fwData['mgmtUser'],
    password=fwData["mgmtPass"]
)

# Get existing rule base
base = Rulebase()
firewall.add(base)

# Define rule attributes
internetNAT = NatRule(
    name="Outbound Internet",
    description="Allow internal systems on Trust zone to internet with PAT",
    nat_type="ipv4",
    fromzone=["trust"],
    tozone=["untrust"],
    to_interface=fwData["trustInt"],
    service="any",
    source=["Trust-Network"],
    destination=["any"],
    source_translation_type="dynamic_ip_and_port",
    source_translation_interface=fwData["untrustInt"]
)
panoramaNAT = NatRule(
    name="Panorama Management",
    description="Allow external management of Panorama on Trust Network",
    nat_type="ipv4",
    fromzone=["untrust"],
    tozone=["trust"],
    to_interface=fwData["untrustInt"],
    service="443",
    source=["any"],
    destination=[fwData["untrustAddr"][:-3]],
    source_translation_type="dynamic_ip_and_port",
    source_translation_interface=fwData["trustInt"],
    destination_translated_address="Panorama-Server"
)

# Create the NAT rule using the SDK
try:
    firewall.add(internetNAT)
    print("Outbound NAT rule created successfully!")
except Exception as e:
    print(f"Error creating Outbound NAT rule: {e}")

# Create the NAT rule using the SDK
try:
    firewall.add(panoramaNAT)
    print("Panorama NAT rule created successfully!")
except Exception as e:
    print(f"Error creating Panorama NAT rule: {e}")

# Create and Commit
firewall.commit()
