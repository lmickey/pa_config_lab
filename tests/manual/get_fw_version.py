from fwdata import fwData
from panos.firewall import Firewall

######## WORKS AND DONE  ############

# Establish connection
firewall = Firewall( fwData["mgmtUrl"],fwData['mgmtUser'],fwData["mgmtPass"],vsys=None, is_virtual=True)
version = firewall.refresh_system_info().version
print (version)