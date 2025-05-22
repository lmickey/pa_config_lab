from fwdata import fwData
from panos.firewall import Firewall
from panos.objects import AddressObject, AddressGroup

######## WORKS AND DONE  ############

# Establish connection
firewall = Firewall( fwData["mgmtUrl"],fwData['mgmtUser'],fwData["mgmtPass"],vsys=None, is_virtual=True)

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
