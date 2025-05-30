import requests, os, pickle, ipaddress, sys, json, string, secrets

########### Define Functions ################
def prisma_access_auth(tsg,user,password):
    scmUrl = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
    scope = 'tsg_id: '+tsg
    paramValues = {'grant_type':'client_credentials','scope':scope}
    
    response = requests.get(scmUrl, auth=(user, password), params=paramValues)

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        return None

def get_pa_config(token):
    paConfig = {}
    headers = {'Accept': 'application/json','Authorization': 'Bearer '+token}
    baseURL = 'https://api.sase.paloaltonetworks.com/sse/config/v1/'

    # Get infrastructure settings
    infraConfig = requests.get(baseURL+'shared-infrastructure-settings',header=headers)
    response = infraConfig.json()
    if response.status_code == 200:
        paConfig['paInfraBGPAS'] = response['infra_bgp_as']
        paConfig['paInfraSubnet'] = response['infrastructure_subnet']
        paConfig['paTunnelMonitor'] = response['tunnel_monitor_ip_address']
    else:
        return None

    # Get Mobile User Configuration
    muConfig = requests.get(baseURL+'mobile-agent/infrastructure-settings',header=headers)
    response = muConfig.json()
    if response.status_code == 200:
        paConfig['paMobUserSubnet'] = response[0]['ip_pools'][0]['ip_pool']
        paConfig['paPortalHostname'] = response[0]['name']
    else:
        return None

    # Set Defaults for SC configuration
    paConfig['scName'] = 'SPOV_Serivce_Connection'
    paConfig['scLocation'] = 'US East'
    paConfig['scSubnet'] = ''
    paConfig['scTunnelName'] = 'SC-Tunnel'
    # Generate random password 
    char_pool = string.ascii_lowercase + string.ascii_uppercase + string.digits + string.punctuation
    paConfig['scAuthKey'] = ''.join(secrets.choice(char_pool) for _ in range(15))

    return paConfig

def get_config_from_file(fileName=None):
    if not fileName:
        fileName = 'fwdata.py'

    # Load config from file
    try:
        with open("my_dictionary.pkl", "rb") as f:
            loaded_dict = pickle.load(f)
            return loaded_dict
    except Exception as e:
        print ('Unable to load config from file :',e)

def load_defaults():
    return {'fwData':{},'paData':{}}

def save_config_to_file(firewallConfig=None,prismaAccessConfig=None):
    # Reset counts
    fileName = 'fwdata.py'
    fwUpCount = 0
    paUpCount = 0
    configFile = False

    # Verify file exists
    if os.path.exists(fileName):
        savedConfiguration = get_config_from_file(fileName)
        configFile = True
    elif os.path.exists(fileName+'.example'):
        savedConfiguration = get_config_from_file(fileName+'.example')
    else:
        savedConfiguration = load_defaults()
    
    # See if there's any updates to make
    if firewallConfig:
        for key, value in firewallConfig:
            if not savedConfiguration['fwData'][key] == value:
                savedConfiguration['fwData'][key] = value
                fwUpCount += 1

    if prismaAccessConfig:
        for key, value in prismaAccessConfig:
            if not savedConfiguration['paData'][key] == value:
                savedConfiguration['paData'][key] = value
                paUpCount += 1

    # If config has never been saved or there are updates, save the config
    if not configFile or fwUpCount > 0 or paUpCount > 0:
        # Code to save config to file
        try:
            with open(fileName, "wb") as file:
                pickle.dump(savedConfiguration, file)
            return True
        except Exception as e:
            print("An error occurred while saving configuration:", e)
            sys.exit()
    else:
        return False
def load_terraform_config(configLines):
    # Load config from Terraform
    # Set defaults if using terraform
    fwData = {
        "tunnelInt":"tunnel.1",
        "tunnelAddr":"192.168.1.1/32",
    }
    valueMap = {
        'ngfw_untrust_fqdn':'untrustURL',
        'ngfw_mgmt_fqdn':'mgmtUrl',
        'ngfw_default_route':'untrustDFGW',
        'ngfw_trust_address':'trustAddr',
        'ngfw_untrust_address':'untrustAddr',
        'ngfw_trust_interface':'trustInt',
        'ngfw_untrust_interface':'untrustInt',
        'username':'mgmtUser',
        'password':'mgmtPass'
    }

    for line in configLines:
        # get setting this line has
        key = line.split('=')[0].strip('" ')
        value = line.split('=')[1].strip('" ')
        fwData[valueMap[key]] = value

def load_spov_questionnaire(fileName):
    # test access to the file for reading and load contents into json
    try:
        with open(fileName, 'r') as file:
            spovJson = json.load(file)
    except FileNotFoundError:
        print(f"Error: File not found or no access for '{fileName}'")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file '{fileName}'")
        return None
    
    # Grab all Prisma Access configuration items from JSON
    # Infrastructure Settings
    paConfig['paInfraBGPAS'] = spovJson['infra_bgp_as']
    paConfig['paInfraSubnet'] = spovJson['infra_subnet']
    paConfig['paTunnelMonitor'] = ipaddress.ip_network(spovJson['infra_subnet']).hosts[-1]

    # Mobile User Settings
    if 'Mobile User' in spovJson['use_case']:
        paConfig['paMobUserSubnet'] = spovJson['gp_ip_pool_list'][0]
        paConfig['paPortalHostname'] = spovJson['gp_portal_name']+'.gpcloudservice.com'
    else:
        paConfig['paMobUserSubnet'] = '100.72.0.0/16'
        paConfig['paPortalHostname'] = 'sase-quick-pov.gpcloudservice.com'
    
    # Service Connection Settings
    if 'Service Connection' in spovJson['use_case']:
        paConfig['scName'] = spovJson['sc_name']
        paConfig['scLocation'] = spovJson['sc_bandwidth_allocation_location']
        paConfig['scSubnet'] = spovJson['sc_subnet']
        paConfig['scTunnelName'] = spovJson['sc_tunnel_name']
        paConfig['scAuthKey'] = spovJson['sc_authentication_key']
    else:
        paConfig['scName'] = 'SPOV_Serivce_Connection'
        paConfig['scLocation'] = 'US East'
        paConfig['scSubnet'] = ''
        paConfig['scTunnelName'] = 'SC-Tunnel'
        # Generate random password 
        char_pool = string.ascii_lowercase + string.ascii_uppercase + string.digits + string.punctuation
        paConfig['scAuthKey'] = ''.join(secrets.choice(char_pool) for _ in range(15))
    
    return paConfig

########### Initial questions to determine if SCM/Panorama and if Terraform deployed  ################
while True:
    try:
        scmOrPan = input("Is this Panorama Managed PA? (y/n):")
        if scmOrPan in ['N','n','Y','y']:
            if scmOrPan in ['N','n']:
                scmOrPan = 'scm'
            else:
                scmOrPan = 'pan'
            break
        else:
            raise ValueError("Invalid value Please enter a valid option")
    except ValueError:
        print("Invalid value Please enter a valid option")

while True:
    try:
        spovOrScm = input("Do you have a SPOV Questionnaire for Configuration? (y/n):")
        if spovOrScm in ['N','n','Y','y']:
            if spovOrScm in ['N','n']:
                spovOrScm = 'scm'
            else:
                spovOrScm = 'spov'
            break
        else:
            raise ValueError("Invalid value Please enter a valid option")
    except ValueError:
        print("Invalid value Please enter a valid option")

while True:
    try:
        terraformDeploy = input("Is the lab deployed by Terraform? (y/n):")
        if terraformDeploy in ['N','n','Y','y']:
            break
        else:
            raise ValueError("Invalid value Please enter a valid option")
    except ValueError:
        print("Invalid value Please enter a valid option")

########### Get SCM information if SCM managed ###########
if scmOrPan == 'scm' or spovOrScm == 'scm':
    scm = {}
    scm['TSG'] = input("Prisma Access Tenant TSG:").strip()
    scm['user'] = input("Prisma Access Tenant API User:").strip()
    scm['pass'] = input("Prisma Access Tenant API Pass:").strip()

    # Authenticate and get token
    accessToken = prisma_access_auth(scm['tsg'],scm['user'],scm['pass'])
    if accessToken:
        print ("Loading Configuration from Prisma Access")
    else:
        print ("Error Authenticating to SCM, check credentials and TSG and try again")
        sys.exit()

    # Get all available information from Prisma Access
    paConfig = get_pa_config(accessToken)

# Load the SPOV Questionnaire for PA Config
if spovOrScm == 'spov':
    spovFile = input("Input full path to SPOV Questionnaire JSON File:").strip()
    paConfig = load_spov_questionnaire(spovFile)

# Once SCM config or SPOV file have been loaded, confirm details and save to file
if paConfig and len(paConfig) > 1:
    print ("PA configuration Loaded successfully, please review the following for accuracy")
    for key, value in paConfig.items():
        print(f"{key}: {value}")
    while True:
        try:
            paConfigValid = input("PA Configuration Above is Accurate? (y/n):")
            if paConfigValid in ['N','n','Y','y']:
                if paConfigValid in ['Y','y']:
                    print ("Saving configuration to file, please update values in fwdata.py")
                    save_config_to_file(prismaAccessConfig=paConfig)
                    break
                else:
                    print ("Configuration not accurate, please restart the script")
                    sys.exit()
            else:
                raise ValueError("Invalid value Please enter a valid option")
        except ValueError:
            print("Invalid value Please enter a valid option")
else:
    print ("Error loading configuration from SCM, check credentials and TSG and try again")
    sys.exit()

########### Get Firewall information ###########
if terraformDeploy in ['Y','y']:
    # Get all FW Data values from Terraform configuration deployment
    lines = []
    print("Paste Terraform Data here (press Enter twice after paste):")
    while True:
        line = input()
        if not line:
            break
        lines.append(line)
    print("Config received")
    
    fwConf = load_terraform_config(lines)
else:
    # Get all FW Data values from user input
    fwConf = {}
    fwConf['mgmtUrl'] = input("Firewall Management Public URL:").strip()
    fwConf['mgmtAddr'] = input("Firewall Management Public IP:").strip()
    fwConf['mgmtUser'] = input("Firewall User:").strip()
    fwConf['mgmtPass'] = input("Firewall Password:").strip()
    fwConf['untrustURL'] = input("Firewall Untrust Public URL:").strip()
    fwConf['untrustPubAddr'] = input("Untrust Interface Public IP Address:").strip()
    fwConf['untrustAddr'] = input("Firewall Untrust Interface IP:").strip()
    untrustNet = ipaddress.ip_network(fwConf['untrustAddr'])
    fwConf['untrustSubnet'] = untrustNet.network_address
    fwConf['untrustInt'] = input("Untrust Interface (default: ethernet1/1):").strip()
    fwConf['untrustDFGW'] = untrustNet.hosts()[0]
    fwConf['trustAddr'] = input("Firewall Trust Interface IP:").strip()
    trustNet = network = ipaddress.ip_network(fwConf['trustAddr'])
    fwConf['trustSubnet'] = input("Firewall User:").strip()
    fwConf['trustInt'] = input("Trust Interface (default: ethernet1/2):").strip()
    fwConf['tunnelInt'] = input("Tunnel Interface (default: tunnel.1):").strip()
    fwConf['tunnelAddr'] = input("Optional - IP address for tunnel interface:").strip()
    fwConf['panoramaAddr'] = input("Panorama IP Address (default: "+trustNet.hosts()[5]+"):").strip()

# After getting all values save the config
if save_config_to_file(firewallConfig=fwConf,prismaAccessConfig=paConfig):
    print ("Config values Saved to file, run 'python configure_firewally.py' to configure firewall")
else:
    print ("Unable to save configuration to file, please try again")