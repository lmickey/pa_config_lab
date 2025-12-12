from panos.firewall import Firewall
from panos.network import Zone, TunnelInterface, VirtualRouter, StaticRoute, IkeCryptoProfile, IkeGateway, IpsecCryptoProfile, IpsecTunnel
from panos.objects import AddressObject, AddressGroup
from panos.policies import Rulebase, SecurityRule
import load_settings, sys, datetime, requests, time, json

# Load settings from config file
configFile = load_settings.load_settings()
if not configFile:
    print("Failed to load configuration file.")
    sys.exit()
fwData = configFile['fwData']
paData = configFile['paData']


#### Verify all variables are configured before starting
requiredFWVariables = ['untrustURL','untrustAddr','untrustInt','tunnelInt']
requiredPAVariables = ['paManagedBy','paSCPsk','paMobUserSubnet','paInfraSubnet','paInfraSubnet','paApiUser','paApiSecret','scLocation']
for key in requiredFWVariables:
    if key not in fwData or not str(fwData[key]) > '':
        print("Missing required Variable: " + key + " - run get_settings.py")
        sys.exit()
for key in requiredPAVariables:
    if key not in paData or not str(paData[key]) > '':
        print("Missing required Variable: " + key + " - run get_settings.py")
        sys.exit()

###################################
##### Configure Prisma Access #####
###################################

def pa_post_request(url,headers,body,folder='shared'):
    url += '?folder='+folder
    response = requests.request("POST", url, headers=headers, data=body)
    print(json.dumps(response.json(), indent=4))
    if response.status_code == 200:
        return response.json()
    else:
        return False

def pa_get_request(url,headers,folder=None):
    if folder: url += '?folder='+folder
    response = requests.request("GET", url, headers=headers)
    print(json.dumps(response.json(), indent=4))
    if response.status_code == 200:
        return response.json()
    else:
        return False
    
def pa_del_request(url,headers,folder=None):
    if folder: url += '?folder='+folder
    response = requests.request("DELETE", url, headers=headers)
    print(json.dumps(response.json(), indent=4))
    if response.status_code == 200:
        return response.json()
    else:
        return False

def create_ike_crypto_profile(config,headers):
    # First, get list of profiles
    ikeCryptoList = pa_get_request(baseURL+'ike-crypto-profiles',headers,'Service Connections')
    matched = ''

    ## Check if profile already exists, confirm if user wants to overwrite
    for crypto in ikeCryptoList['data']:
        if crypto.name == config.name:
            while True:
                try:
                    overwrite = input(config.name + " Crypto Profile Alread Exists, overwrite? (y/n):")
                    if overwrite.lower() in ['n','y']:
                        if overwrite.lower() == 'n':
                            ## @TODO allow entry of different crypto profile name or base it off SC name somehow
                            print("Please delete IDKE Crypto Profile manually before continuing")
                            sys.exit()
                        else:
                            matched = crypto.id
                            break
                    else:
                        raise ValueError("Invalid value Please enter a valid option")
                except ValueError:
                    print("Invalid value Please enter a valid option")
        if matched != '': break
    
    ## If profile was found, delete it first before creating
    if matched != '':
        if not pa_del_request(baseURL+'ike-crypto-profiles/'+matched,headers,'Service Connections'):
            print ("Unable to delete IKE Crypto Profile duplicate, please delete manually before continuing")
            sys.exit()
    
            
# Default encryption settings:
cryptoAuth = 'sha256'
cryptoEncryp = 'aes-256-cbc'
cryptoDHGroup = 'group20'
ikeTime = 28800 #8 hours
ipsecTime = 3600 #1 hour

#Check what to configure (SCM or Panorama)
while True:
    try:
        configPrisma = input("Configure the Prisma Access end of the SC Tunnel? (y/n):")
        if configPrisma.lower() in ['n','y']:
            break
        else:
            raise ValueError("Invalid value Please enter a valid option")
    except ValueError:
        print("Invalid value Please enter a valid option")

if 'paManagedBy' in paData and paData['paManagedBy'] == 'scm' and configPrisma.lower() == 'y':
    ######### Configure the Service Connection in SCM #####################
    
    # Confirm all required fields are configured
    requiredFWConfig = ['untrustURL','trustSubnet']
    requiredPAConfig = ['paSCPsk','scLocation','paTSGID','paApiUser','paApiSecret']
    for key in requiredFWConfig:
        if key not in fwData:
            print ("Required FW information - " + key + " - to configure SC in SCM is missing, please rerun get_settings.py to add this setting")
            sys.exit()
    for key in requiredPAConfig:
        if key not in paData:
            print ("Required PA information - " + key + " - to configure SC in SCM is missing, please rerun get_settings.py to add this setting")
            sys.exit()

    #URL info
    baseURL = 'https://api.sase.paloaltonetworks.com/sse/config/v1/'
    ikeCryptoUrl = baseURL+'ike-crypto-profiles'
    ipsecCryptoUrl = baseURL+'ipsec-crypto-profiles'
    ikeGatewayUrl = baseURL+'ike-gateways'
    ipsecTunnelUrl = baseURL+'ipsec-tunnels'
    serviceConnectionUrl = 'service-connections'
    # Setup the body for all requests to be made
    ikeCrypto = {"authentication_multiple": 0,"dh_group": [cryptoDHGroup],"encryption": [cryptoEncryp],"hash": [cryptoAuth],"lifetime": {"seconds": ikeTime},"name": "SC-IKE-Crypto"}
    ipsecCrypto = {"dh_group": cryptoDHGroup,"lifesize": {"kb": 0},"lifetime": {"seconds": ipsecTime},"name": "SC-IPSec-Crypto","esp": {"authentication": [cryptoAuth],"encryption": [cryptoEncryp]}}
    ikeGateway = {
        "authentication": {"pre_shared_key": {"key": paData['paSCPsk']}},
        "local_id": {"id": "prisma","type": "string"},
        "name": "SC-IKE-Gateway",
        "peer_address": {"fqdn": fwData['untrustURL']},
        "peer_id": {"id": fwData['untrustURL'],"type": "fqdn"},
        "protocol": {"ikev2": {"dpd": {"enable": True},"ike_crypto_profile": "SC-IKE-Crypto"},"version": "ikev2"},
        "protocol_common": {"fragmentation": {"enable": False},"nat_traversal": {"enable": True},"passive_mode": True}
    }
    ipsecTunnel = {"name": 'SC-Tunnel',"anti_replay": True,"auto_key": {"ike_gateway": [{"name": "SC-IKE-Gateway"}],"ipsec_crypto_profile": "SC-IPSec-Crypto"},"enable_gre_encapsulation": False}
    serviceConnection = {"ipsec_tunnel": 'SC-Tunnel','name':'SC-Datacenter',"onboarding_type": "classic","region": [paData['scLocation']],"subnets": [fwData['trustSubnet']]}

    #Token is only good for 15min, we will probably need to reauth at some point
    authTokenTimer = datetime.datetime.now()
    authToken = load_settings.prisma_access_auth(paData['paTSGID'],paData['paApiUser'],paData['paApiSecret'])
    if not authToken:
        print ("Unable to login to SCM, please check credentials using get_settings.py and try again")
        sys.exit()
    headers = {'Content-Type': 'application/json','Authorization': 'Bearer '+authToken}
    paFolder = "Service Connections"

    #@TODO add checks to see if they already exist instead of just blindly creating
    # First create the crypto profiles
    
    ikeCryptoData = pa_post_request(ikeCryptoUrl,headers,json.dumps(ikeCrypto),paFolder)
    if 'id' not in ikeCryptoData:
        print('Unable to create IKE Crypto Profile, exiting')
        sys.exit()
    print(json.dumps(ipsecCrypto, indent=4))
    if not pa_post_request(ipsecCryptoUrl,headers,json.dumps(ipsecCrypto),paFolder):
        print('Unable to create IPSEC Crypto Profile, exiting')
        sys.exit()
    
    # Create IKE Gateway
    print(json.dumps(ikeGateway, indent=4))
    if not pa_post_request(ikeGatewayUrl,headers,json.dumps(ikeGateway),paFolder):
        print('Unable to create IKE Gateway, exiting')
        sys.exit()

    # Create IPSEC Tunnel
    print(json.dumps(ipsecTunnel, indent=4))
    if not pa_post_request(ipsecTunnelUrl,headers,json.dumps(ipsecTunnel),paFolder):
        print('Unable to create IPSEC Tunnel, exiting')
        sys.exit()

    # Add Service Connection
    print(json.dumps(serviceConnection, indent=4))
    if not pa_post_request(serviceConnectionUrl,headers,json.dumps(serviceConnection),paFolder):
        print('Unable to create Service Connection, exiting')
        sys.exit()

    print("Successfully Configured Service Connection, Commiting Configuration")

    # If everything was created successfully then push config
    jobInfo = pa_post_request(baseURL+'config-versions/candidate:push',headers,{'description':'Pushing Service Connection Setup', "folders": [paFolder]})
    commitFinished = False
    waitCount = 0

    # Wait until the push is complete, if authToken expires get a new one
    jobStatus = None
    while True:
        # Every 10 seconds print update to user, every 30 seconds, get job status
        waitCount += 1        
        time.sleep(10)
        if waitCount % 6 == 0 or waitCount == 1:
            print(f"\rChecking Push Status ", end="")
            sys.stdout.flush()
        else:
            print('.', end="")
            sys.stdout.flush()

        # Get job status
        if waitCount % 3 == 0:
            jobStatus = pa_get_request(baseURL+'jobs/'+jobInfo['job_id'],headers)

        # If job is complete, exit loop
        if jobStatus and 'data' in jobStatus and len(jobStatus['data']) > 0:
            if jobStatus['data'][0]['job_status'] == '2' and jobStatus['data'][0]['status_str'] == 'FIN':
                commitFinished = True
                break
        else:
            # Check if token will expire before next run
            currentTime = datetime.datetime.now()
            diffTime = currentTime - authTokenTimer
            if diffTime.total_seconds() > 825:
                authTokenTimer = datetime.datetime.now()
                authToken = load_settings.prisma_access_auth(paData['paTSGID'],paData['paApiUser'],paData['paApiSecret'])
                headers = {'Content-Type': 'application/json','Authorization': 'Bearer '+authToken}
    
    # Verify commit was successful
    if jobStatus and 'data' in jobStatus and len(jobStatus['data']) > 0:
        if jobStatus['data'][0]['job_result'] == '2' and jobStatus['data'][0]['result_str'] == 'OK':
            print ('Commit Successful, Service Connection configuration complete')

        # Get the list of service connections and find the one we just created
        scList = pa_get_request(baseURL+'service-connections',headers,'Service Connections')
        if scList and 'data' in scList:
            for scmSC in scList['data']:
                if scmSC.get('name') == 'SC-Datacenter':
                    # This is the correct service connection, get the endpoint information
                    scTunnel = pa_get_request(baseURL+'service-connections/'+scmSC['id'],headers)
                    if scTunnel and 'data' in scTunnel:
                        # Extract endpoint information and save to config if needed
                        print(f"Service Connection endpoint information retrieved for {scmSC['name']}")
                        # @TODO: Save endpoint information to paData if needed for firewall configuration
        else:
            print ('Service Connection configuration error, please check SCM and try again')
            sys.exit()

elif 'paManagedBy' in paData and paData['paManagedBy'] == 'pan' and configPrisma.lower() == 'y':
    ######### Configure the Service Connection in Panorama #####################
    from panos.panorama import Panorama
    
    # Confirm all required fields are configured
    requiredFWConfig = ['untrustURL','trustSubnet']
    requiredPAConfig = ['paSCPsk','scLocation','panMgmtUrl','panUser','panPass']
    for key in requiredFWConfig:
        if key not in fwData:
            print ("Required FW information - " + key + " - to configure SC in Panorama is missing, please rerun get_settings.py to add this setting")
            sys.exit()
    for key in requiredPAConfig:
        if key not in paData:
            print ("Required PA/Panorama information - " + key + " - to configure SC in Panorama is missing, please rerun get_settings.py to add this setting")
            sys.exit()
    
    # Establish connection to Panorama
    panorama = Panorama(paData['panMgmtUrl'], paData['panUser'], paData['panPass'])
    
    # Note: Service Connection configuration in Panorama requires Prisma Access plugin
    # This typically involves configuring through the Panorama UI or using REST API
    # The pan-os-python SDK doesn't have direct support for Prisma Access Service Connections
    # This would need to be done via Panorama REST API calls similar to SCM approach
    
    print("Panorama Service Connection configuration requires:")
    print("1. Prisma Access plugin installed on Panorama")
    print("2. Service Connection configured through Panorama UI or REST API")
    print("3. The following configuration values:")
    print(f"   - Service Connection Name: {paData.get('scName', 'SC-Datacenter')}")
    print(f"   - Location: {paData.get('scLocation', 'US East')}")
    print(f"   - Subnet: {fwData['trustSubnet']}")
    print(f"   - Pre-shared Key: {paData['paSCPsk']}")
    print(f"   - Firewall FQDN: {fwData['untrustURL']}")
    print("\nPlease configure the Service Connection manually in Panorama or use the Panorama REST API.")
    print("After configuration, ensure paSCEndpoint is set in your configuration file.")

##################################
##### Configure the Firewall #####
##################################
#Check what to configure (SCM or Panorama)
while True:
    try:
        configFirewall = input("Configure the Firewall end of the SC Tunnel? (y/n):")
        if configFirewall.lower() in ['n','y']:
            if configFirewall.lower() == 'n': sys.exit()
            break
        else:
            raise ValueError("Invalid value Please enter a valid option")
    except ValueError:
        print("Invalid value Please enter a valid option")

##### Establish connection
firewall = Firewall(fwData["mgmtUrl"],fwData['mgmtUser'],fwData["mgmtPass"],vsys=None, is_virtual=True)
firewall.vsys = None

##### Define the zone for the VPN termination
zoneVPN = Zone(name='vpn', mode='layer3')
firewall.add(zoneVPN)
zoneVPN.create()

##### @todo check that the tunnel interface doesn't exist first before creating it
##### @todo or get list of current interfaces and add next number
# Configure the tunnel interface (default: tunnel.1 vpn)
if 'tunnelAddr' in fwData and fwData['tunnelAddr']:
    tun1 = TunnelInterface(fwData['tunnelInt'], fwData['tunnelAddr'])
else:
    tun1 = TunnelInterface(fwData['tunnelInt'])
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
    destination=paData['paMobUserSubnet'],
    interface=fwData['tunnelInt'],
    nexthop_type='None'
)

#Create a static route for prisma infrastructure
prismaInfra = StaticRoute(
    name='Prisma-Access-Infrastructure',
    destination=paData["paInfraSubnet"],
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
addr['paMU'] = AddressObject("Prisma-Mobile-Users", paData['paMobUserSubnet'], description="Prisma Access Mobile Users")
addr['paInfra'] = AddressObject("Prisma-Infrastructure", paData['paInfraSubnet'], description="Prisma Access Infrastructure")

# Create objects
for i in addr:
  firewall.add(addr[i])
  addr[i].create()

# Define basic address objects
grp = {}
grp['paMU'] = AddressGroup("Prisma-Trust-Networks", ["Prisma-Mobile-Users","Prisma-Infrastructure"], description="Prisma Access Networks")

# Create objects
for i in grp:
  firewall.add(grp[i])
  grp[i].create()

firewall.commit()

####### Setup the Crypto Policies #############
# Defaults from above
#cryptoAuth = 'sha256'
#cryptoEncryp = 'aes-256-cbc'
#cryptoDHGroup = 'group20'
#ikeTime = 28800 #8 hours
#ipsecTime = 3600 #1 hour
fwIkeCrypto = IkeCryptoProfile(
    name='SC-IKE-Crypto',
    dh_group=cryptoDHGroup,
    authentication=cryptoAuth,
    encryption=cryptoEncryp,
    lifetime_seconds=ikeTime,
    authentication_multiple=0
)

fwIpsecCrypto = IpsecCryptoProfile(
    name='SC-IPSec-Crypto',
    dh_group=cryptoDHGroup,
    esp_authentication=cryptoAuth,
    esp_encryption=cryptoEncryp,
    lifetime_seconds=ipsecTime,
    authentication_multiple=0
)

firewall.add(fwIkeCrypto)
firewall.add(fwIpsecCrypto)

####### Configure IKE Gateway #################
fwIkeGateway = IkeGateway(
    name='SC-IKE-Gateway',
    version='ikev2-prefered',
    peer_ip_type='fqdn',
    peer_ip_value=paData['paSCEndpoint'],
    interface=fwData['untrustInt'],
    local_ip_address_type='ip',
    local_ip_address=fwData['untrustAddr'],
    auth_type='pre-shared-key',
    pre_shared_key=paData['paSCPsk'],
    local_id_type='fqdn',
    local_id_value='untrustURL',
    peer_id_type='fqdn',
    peer_id_value=paData['paSCEndpoint'],
    enable_passive_mode=False,
    enable_nat_traversal=True,
    ikev1_crypto_profile='SC-IKE-Crypto',
    ikev2_crypto_profile='SC-IKE-Crypto',
)

firewall.add(fwIkeGateway)

####### Create IPSec Tunnel Config ############
fwIPSecTunnel = IpsecTunnel(
    name='SC-IPSec-Tunnel',
    tunnel_interface=fwData['tunnelInt'],
    type='auto-key',
    ak_ike_gateway='SC-IKE-Gateway',
    ak_ipsec_crypto_profile='SC-IPSec-Crypto',
    anti_replay=True,
    enable_tunnel_monitor=False,
    #tunnel_monitor_dest_ip - @todo add in tunnel monitor configuration
    #tunnel_monitor_profile
)

firewall.add(fwIPSecTunnel)

# Commit Crypto/gateway/tunnel configuraiton
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
