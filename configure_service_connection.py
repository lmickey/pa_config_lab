from panos.firewall import Firewall
from panos.network import Zone, TunnelInterface, VirtualRouter, StaticRoute
from panos.objects import AddressObject, AddressGroup
from panos.policies import Rulebase, SecurityRule
import load_settings, sys, getpass, datetime

# Get Settings encryption password
encryptPass = load_settings.derive_key(getpass.getpass("Enter password for encryption: "))

# Example usage
data = load_settings(encryptPass)
if not data:
    print("Failed to decrypt data.")
    sys.exit()
fwData = data['fwData']
paData = data['paData']

###################################
##### Configure Prisma Access #####
###################################

#Check what to configure (SCM or Panorama)
if 'paManagedBy' in paData and paData['paManagedBy'] == 'scm':
   # Configure SC in SCM
   # Default encryption settings:
   cryptoAuth = 'sha256'
   cryptoEncryp = 'aes-256-cbc'
   cryptoDHGroup = 'group20'
   ikeTime = 28800
   ipsecTime = 3600
   
   # Setup the body for all requests to be made
   ikeCrypto = {"authentication_multiple": 0,"dh_group": [cryptoDHGroup],"encryption": [cryptoEncryp],"hash": [cryptoAuth],"lifetime": {"seconds": ikeTime},"name": "SC-IKE-Crypto"}
   ipsecCrypto = {"dh_group": cryptoDHGroup,"lifesize": {"kb": 0},"lifetime": {"seconds": ipsecTime},"name": "SC-IPSec-Crypto","esp": {"authentication": [cryptoAuth],"encryption": [cryptoEncryp]}}
   ikeGateway = {
        "authentication": {"pre_shared_key": {"key": paData['psk']}},
        "local_id": {"id": "prisma","type": "string"},
        "name": "SC-IKE-Gateway",
        "peer_address": {"fqdn": fwData['untrustURL']},
        "peer_id": {"id": fwData['untrustURL'],"type": "fqdn"},
        "protocol": {"ikev2": {"dpd": {"enable": True},"ike_crypto_profile": "SC-IKE-Crypto"},"version": "ikev2"},
        "protocol_common": {"fragmentation": {"enable": False},"nat_traversal": {"enable": True},"passive_mode": True}
    }
   ipsecTunnel = {"name": paData['scName'],"anti_replay": True,"auto_key": {"ike_gateway": [{"name": "SC-IKE-Gateway"}],"ipsec_crypto_profile": "SC-IPSec-Crypto"},"enable_gre_encapsulation": False}

   #Token is only good for 15min, we will probably need to reauth at some point
   authTokenTimer = datetime.datetime.now()
   authToken = load_settings.prisma_access_auth(paData['tsg'],paData['user'],paData['pass'])
   if not authToken:
      print ("Unable to login to SCM, please check credentials using get_settings.py and try again")
      sys.exit()
   headers = {'Content-Type': 'application/json','Authorization': 'Bearer '+authToken}
   
##################################
##### Configure the Firewall #####
##################################

##### Establish connection
firewall = Firewall(fwData["mgmtUrl"],fwData['mgmtUser'],fwData["mgmtPass"],vsys=None, is_virtual=True)
firewall.vsys = None

##### Define the zone for the VPN termination
zoneVPN = Zone(name='vpn', mode='layer3')
firewall.add(zoneVPN)
zoneVPN.create()

##### NEED TO ADD CHECK THAT THE INTERFACE DOESN'T EXIST
##### get list of current interfaces and add next number
# Configure the tunnel interface (default: tunnel.1 vpn)
tun1 = TunnelInterface(fwData['tunnelInt'], fwData['tunnelAddr'])
firewall.add(tun1)
tun1.set_zone('vpn', mode='layer3', refresh=True, update=True)
tun1.set_virtual_router('default', refresh=True, update=True)
tun1.create()

firewall.commit()


######### Configure Static Routes ###################
# Get the default virtual router
vrouter = VirtualRouter(name='default')

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
vrouter.add(mobileUsers)
vrouter.add(prismaInfra)
mobileUsers.create()
prismaInfra.create()

firewall.commit()

####### Configure Address and Group Objects #############

# Define basic address objects
addr = {}
addr['paMU'] = AddressObject("Prisma-Mobile-Users", fwData['paMobUserSubnet'], description="Company web server")
addr['paInfra'] = AddressObject("Prisma-Infrastructure", fwData['paInfraSubnet'], description="Company web server")

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

firewall.commit()

####### Configure Firewall Policy #############

# Get existing rule base
base = Rulebase()
firewall.add(base)

# Define rule attributes
rule=[]
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
