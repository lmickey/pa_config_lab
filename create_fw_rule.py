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
rule[0] = SecurityRule(
    name='Outbound Internet',
    description='Allow trust zone to internet',
    fromzone=['trust'],
    tozone=['untrust'],
    source=["Trust-Network"],
    destination=['any'],
    application=['ssl','web-browsing'],
    action='allow',
    log_end=True
)
rule[1] = SecurityRule(
    name='Allow SC Tunnel',
    description='Allow trust zone to internet',
    fromzone=['trust'],
    tozone=['untrust'],
    source=["Trust-Network"],
    destination=['any'],
    application=['ssl','web-browsing'],
    action='allow',
    log_end=True
)
rule[2] = SecurityRule(
    name='Outbound Internet',
    description='Allow trust zone to internet',
    fromzone=['trust'],
    tozone=['untrust'],
    source=["Trust-Network"],
    destination=['any'],
    application=['ssl','web-browsing'],
    action='allow',
    log_end=True
)
rule[3] = SecurityRule(
    name='Outbound Internet',
    description='Allow trust zone to internet',
    fromzone=['trust'],
    tozone=['untrust'],
    source=["Trust-Network"],
    destination=['any'],
    application=['ssl','web-browsing'],
    action='allow',
    log_end=True
)
rule[4] = SecurityRule(
    name='Outbound Internet',
    description='Allow trust zone to internet',
    fromzone=['trust'],
    tozone=['untrust'],
    source=["Trust-Network"],
    destination=['any'],
    application=['ssl','web-browsing'],
    action='allow',
    log_end=True
)

# Add the rule
firewall.add(rule)

# Create and Commit
rule.create()
firewall.commit()