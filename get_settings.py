import requests, os, pickle, ipaddress, sys, json, string, secrets, getpass, base64, hashlib, load_settings
from cryptography.fernet import Fernet

########### Define Functions ################
def derive_key(password: str) -> bytes:
    # Use SHA-256 hash to derive a 32-byte key from password
    hash = hashlib.sha256(password.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(hash))

def prisma_access_auth(tsg,user,password):
    """
    Authenticate with Prisma Access SCM Authentication Service.
    
    Uses basic auth with Client ID as username and Client Secret as password.
    Sends grant_type and scope as form data in request body.
    
    Args:
        tsg: TSG ID
        user: Client ID (username for basic auth)
        password: Client Secret (password for basic auth)
        
    Returns:
        Access token string or None if authentication fails
    """
    scmUrl = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
    scope = 'tsg_id:'+tsg
    
    # Form data in request body (not query params)
    data = {
        'grant_type': 'client_credentials',
        'scope': scope
    }
    
    # Headers for form-urlencoded content type
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Basic auth: Client ID as username, Client Secret as password
    response = requests.post(scmUrl, auth=(user, password), data=data, headers=headers)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        return None

def get_pa_config(token):
    paConfig = {}
    reqHeaders = {'Accept': 'application/json','Authorization': 'Bearer '+token}
    baseURL = 'https://api.sase.paloaltonetworks.com/sse/config/v1/'

    # Get infrastructure settings
    infraConfig = requests.get(baseURL+'shared-infrastructure-settings',headers=reqHeaders)
    response = infraConfig.json()
    if infraConfig.status_code == 200:
        paConfig['paInfraBGPAS'] = response['infra_bgp_as']
        paConfig['paInfraSubnet'] = response['infrastructure_subnet']
        paConfig['paTunnelMonitor'] = response['tunnel_monitor_ip_address']
    else:
        return None

    # Get Mobile User Configuration
    muConfig = requests.get(baseURL+'mobile-agent/infrastructure-settings',headers=reqHeaders)
    response = muConfig.json()
    if muConfig.status_code == 200:
        paConfig['paMobUserSubnet'] = response[0]['ip_pools'][0]['ip_pool'][0]
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

# Load and decrypt data if existing config file
def get_config_from_file(cipher,filePath=None):
    if not filePath:
        fileName = 'fwdata.bin.example'
        scriptDir = os.getcwd()
        filePath = os.path.join(scriptDir, fileName)

    with open(filePath, 'rb') as f:
        encrypted_data = f.read()
    try:
        decrypted_data = cipher.decrypt(encrypted_data)
        data = pickle.loads(decrypted_data)
        return data
    except Exception as e:
        print("Decryption failed:", e)
        return None

def load_defaults():
    return {
        'fwData':{
            'mgmtUrl': '', 
        	'mgmtUser': '', 
	        'mgmtPass': '', 
	        'untrustURL': '', 
            'untrustAddr':'10.32.0.4/24',
            'untrustSubnet':'10.32.0.0/24',
            'untrustInt':'ethernet1/1',
            'untrustDFGW':'10.32.0.1',
            'trustAddr':'10.32.1.4/24',
            'trustSubnet':'10.32.1.0/24',
            'trustInt':'ethernet1/2',
            'tunnelInt':'tunnel.1',
            'tunnelAddr':'192.168.1.1/32',
            'panoramaAddr':''
        },
        'paData':{
            'paManagedBy':'scm',
            'paTSGID':'',
            'paApiUser':'',
            'paApiSecret':'',
            'paInfraSubnet':'192.168.254.0/24',
            'paInfraBGPAS':'65434',
            'paMobUserSubnet':'100.64.0.0/16',
            'paPortalHostname':'',
            'paZtnaContSubnet':'172.16.0.0/20',
            'paZtnaAppSubnet':'172.20.0.0/16',
            'paSCEndpoint':'',
            'scName': 'SPOV_Serivce_Connection',
            'scLocation':'US East',
            'scTunnelName':'SC-Tunnel',
            'scAuthKey': 'testpsktestpsk123'
        }
    }

def save_config_to_file(configName,cipher,firewallConfig=None,prismaAccessConfig=None):
    # Reset counts
    fileName = configName.strip().lower().replace(" ","_") +'-fwdata.bin'
    scriptDir = os.getcwd()
    filePath = os.path.join(scriptDir, fileName)
    fwUpCount = 0
    paUpCount = 0
    configFile = False

    # Verify file exists
    if os.path.exists(fileName):
        # Confirm overwrite of existing configuration
        while True:
            try:
                overwrite = input("Overwrite Existing Configuration? (y/n):")
                if overwrite.lower() == 'n':
                    configName = input("Enter new configuration name: ")
                    fileName = configName.strip().lower().replace(" ","_") +'-fwdata.bin'
                    filePath = os.path.join(scriptDir, fileName)
                    savedConfiguration = load_defaults()
                    break
                elif overwrite.lower() == 'y':
                    savedConfiguration = get_config_from_file(cipher,filePath)
                    configFile = True
                    break
                else:
                    raise ValueError("Invalid value Please enter a valid option")
            except ValueError:
                print("Invalid option Please enter a valid option")
    else:
        savedConfiguration = load_defaults()

    # See if there's any updates to make
    if firewallConfig:
        for key, value in firewallConfig.items():
            if key not in savedConfiguration['fwData'] or (key in savedConfiguration['fwData'] and not savedConfiguration['fwData'][key] == value):
                savedConfiguration['fwData'][key] = value
                fwUpCount += 1

    if prismaAccessConfig:
        for key, value in prismaAccessConfig.items():
            if key not in savedConfiguration['paData'] or ( key in savedConfiguration['paData'] and not savedConfiguration['paData'][key] == value):
                savedConfiguration['paData'][key] = value
                paUpCount += 1

    if (fwUpCount + paUpCount) > 0: print (str(fwUpCount+paUpCount) + " Config Changes, Saving")
    if not configFile: print ("Saving Config")
    # If config has never been saved or there are updates, save the config
    if not configFile or (fwUpCount + paUpCount) > 0:
        # Code to save config to file
        try:
            # Serialize (pickle) and encrypt
            encrypted_data = cipher.encrypt(pickle.dumps(savedConfiguration))

            # Save encrypted data to a file
            with open(filePath, 'wb') as f:
                f.write(encrypted_data)
            
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
    paConfig = {}

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
    print(json.dumps(spovJson,indent=4))
    # Grab all Prisma Access configuration items from JSON
    # Infrastructure Settings
    paConfig['paInfraBGPAS'] = spovJson['infra_bgp_as']
    paConfig['paInfraSubnet'] = spovJson['infra_subnet']
    paConfig['paTunnelMonitor'] = ipaddress.IPv4Network(spovJson['infra_subnet'])[-1]

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

########### Section to see if i need to add/edit existing config or create new #######################
if __name__ == "__main__":
    while True:
        try:
            runReason = input("Create new configuration? (y/n):")
            if runReason.lower() in ['n','y']:
                if runReason in ['N','n']:
                    runReason = 'edit'
                else:
                    runReason = 'new'
                break
            else:
                raise ValueError("Invalid value Please enter a valid option")
        except ValueError:
            print("Invalid value Please enter a valid option")

    if runReason == 'edit':
        # Load list of configurations, have user pick one
        # Load settings from config file
        configFile = load_settings.load_settings()
        if not configFile:
            print("Failed to load configuration file.")
            sys.exit()
        fwData = configFile['fwData']
        paData = configFile['paData']
        #Protected fields
        protectedFields = ['paSCPsk','pass','mgmtPass','scmPass','paApiSecret']


        while True:
            # Reset vars if we edited/added and need to re-print/re-number all config settings again
            configKeys = []
            configNum = 0        
            settingCount = 0
        
            # Print firewall/Panorama data
            print ("\nFirewall & Panorama Configuration Settings")
            for key,value in fwData.items():
                settingCount += 1
                configKeys.append(key)
                tabs = "\t\t" if (len(key) < 11 and settingCount < 10) or (len(key) < 10 and settingCount > 9) else '\t'
                if key not in protectedFields: 
                    print (str(settingCount) + " - " + str(key) + ":" + tabs + str(value))
                else:
                    print (str(settingCount) + " - " + str(key) + ":" + tabs + "************")

            # How to know if it's FW config or PA config setting to update
            configNum = settingCount

            # Prisma Access Configuration
            print ("\nPrisma Access Configuration Settings")
            for key,value in paData.items():
                settingCount += 1
                configKeys.append(key)
                tabs = "\t\t" if (len(key) < 11 and settingCount < 10) or (len(key) < 10 and settingCount > 9) else '\t'
                if key not in protectedFields: 
                    print (str(settingCount) + " - " + str(key) + ":" + tabs + str(value))
                else:
                    print (str(settingCount) + " - " + str(key) + ":" + tabs + "************")
            
            # Pause and ask what the user wants to do
            try:
                editOption = input("\nChoose Setting to edit 1-" + str(settingCount) +"\na to add a setting | s to save/quit | q to quit\nSelection:")
                if editOption.lower() in ['a','s','q'] or int(editOption)-1 in range(settingCount):
                    # Quit updating the configuration
                    if editOption.lower() == 'q':
                        sys.exit()
                    # Save the config, then quit
                    elif editOption.lower() == 's':
                        if save_config_to_file(configFile['configName'],configFile['configCipher'],fwData,paData):
                            print ("Config values Saved to file, run 'python configure_firewally.py' to configure firewall")
                        else:
                            print ("Unable to save configuration to file, please try again")
                        sys.exit()
                    # Add a new configuration setting
                    elif editOption.lower() == 'a':
                        newKey = input ("Enter Name of new setting:")
                        newVal = input ("Enter Value for " + newKey + ":")
                        while True:
                            try:
                                fwOrPa = input ("Firewall (f) or Prisma Access (p) Setting? (f/p)")
                                if fwOrPa.lower() in ['f','p']:
                                    if fwOrPa.lower() == 'f':
                                        fwData[newKey] = newVal
                                        break
                                    else:
                                        paData[newKey] = newVal
                                        break
                                else:
                                    raise ValueError("Invalid value Please enter a valid option")
                            except ValueError:
                                print ("Invalid value Please enter a valid option")
                    # Update a setting, based on the number entered
                    else:
                        newVal = input ("Enter new value for " + configKeys[int(editOption)-1] + ":")
                        if int(editOption)-1 < configNum:
                            fwData[configKeys[int(editOption)-1]] = newVal
                        else:
                            paData[configKeys[int(editOption)-1]] = newVal
                else:
                    raise ValueError("Invalid value Please enter a valid option")
            except ValueError:
                print("Invalid value Please enter a valid option")

    ########### Initial questions to determine if SCM/Panorama and if Terraform deployed  ################
    configName = input("Enter a name for this configuration: ")
    encryptPass = derive_key(getpass.getpass("Enter password for encryption: "))
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
            spovOrPA = input("Do you have a SPOV Questionnaire for Configuration? (y/n):")
            if spovOrPA in ['N','n','Y','y']:
                if spovOrPA in ['N','n']:
                    spovOrPA = 'pa'
                else:
                    spovOrPA = 'spov'
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
    if scmOrPan == 'scm':
        scmCreds = {}
        scmCreds['paTSGID'] = input("Prisma Access Tenant TSG:").strip()
        scmCreds['paApiUser'] = input("Prisma Access Tenant Client ID:").strip()
        scmCreds['paApiSecret'] = getpass.getpass("Prisma Access Tenant Client Secret:").strip()

        # Authenticate and get token
        accessToken = prisma_access_auth(scmCreds['paTSGID'],scmCreds['paApiUser'], scmCreds['paApiSecret'])
        if accessToken:
            print ("Loading Configuration from Prisma Access")
        else:
            print ("Error Authenticating to SCM, check credentials and TSG and try again")
            sys.exit()

        # Check for SPOV config or do we load from SCM
        if spovOrPA == 'spov':
            # Load the SPOV Questionnaire for PA Config
            spovFile = input("Input full path to SPOV Questionnaire JSON File:").strip()
            paConfig = load_spov_questionnaire(spovFile)
        else:
            # Get all available information from Prisma Access
            paConfig = get_pa_config(accessToken)
        
        # Save TSG/Credentials to paConfig var
        paConfig.update(scmCreds)

        # Once SCM config or SPOV file have been loaded, confirm details and save to file
        if paConfig and len(paConfig) > 3:
            paConfig['paManagedBy'] = scmOrPan
            print ("PA configuration Loaded successfully, please review the following for accuracy")
            for key, value in paConfig.items():
                print(f"{key}: {value}")
            while True:
                try:
                    paConfigValid = input("PA Configuration Above is Accurate? (y/n):")
                    if paConfigValid in ['Y','y']:
                        break
                    elif paConfigValid in ['N','n']:
                        print ("Configuration not accurate, please restart the script")
                        sys.exit()
                    else:
                        raise ValueError
                except ValueError:
                    print("Invalid value Please enter a valid option")
        else:
            print ("Error loading configuration from SCM, check credentials and TSG and try again")
            sys.exit()
    else:
        ## If it's panorama managed, confirm if panorama is already configured or should we get configuration from spov
        # @todo - ask for panorama mgmt url and credentials

        # Check on where we're loading the configuration from, SPOV questionnaire or live Panorama
        if spovOrPA == 'spov':
            # Load the SPOV Questionnaire for PA Config
            spovFile = input("Input full path to SPOV Questionnaire JSON File:").strip()
            paConfig = load_spov_questionnaire(spovFile)
        else:
            panConf = {'panMgmtUrl':'','panUser':'','panPass':''}
            # Panorama is already configured? So must not be deployed by terraform
            # @todo - create new def to login to panorama (api/cli?) and get PA Config

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
        print ("\n\nEnter Firewall Configuration\n\n")
        fwConf = {}
        fwConf['mgmtUrl'] = input("Firewall Management Public URL:").strip()
        fwConf['mgmtUser'] = input("Firewall User:").strip()
        fwConf['mgmtPass'] = getpass.getpass("Firewall Password:").strip()
        fwConf['untrustURL'] = input("Firewall Untrust Public URL:").strip()
        fwConf['untrustAddr'] = input("Firewall Untrust Interface IP:").strip()
        fwConf['untrustSubnet'] = str(ipaddress.IPv4Interface(fwConf['untrustAddr']).network)
        fwConf['untrustInt'] = input("Untrust Interface (default: ethernet1/1):").strip()
        if fwConf['untrustInt'] == '': fwConf['untrustInt'] = "ethernet1/1"
        fwConf['untrustDFGW'] = str(ipaddress.IPv4Network(ipaddress.IPv4Interface(fwConf['untrustAddr']).network)[1])
        fwConf['trustAddr'] = input("Firewall Trust Interface IP:").strip()
        fwConf['trustSubnet'] = str(ipaddress.IPv4Interface(fwConf['trustAddr']).network)
        fwConf['trustInt'] = input("Trust Interface (default: ethernet1/2):").strip()
        if fwConf['trustInt'] == '': fwConf['trustInt'] = "ethernet1/2"
        fwConf['tunnelInt'] = input("Tunnel Interface (default: tunnel.1):").strip()
        if fwConf['tunnelInt'] == '': fwConf['tunnelInt'] = "tunnel.1"
        fwConf['tunnelAddr'] = input("Optional - IP address for tunnel interface:").strip()
        if scmOrPan == 'pan':
            fwConf['panoramaAddr'] = input("Panorama IP Address (default: " + str(ipaddress.IPv4Network(fwConf['trustSubnet'])[5]) + "):").strip()
        if fwConf['panoramaAddr'] == '': fwConf['panoramaAddr'] = str(ipaddress.IPv4Network(fwConf['trustSubnet'])[5])

    # After getting all values save the config
    if save_config_to_file(configName,encryptPass,fwConf,paConfig):
        print ("Config values Saved to file, run 'python configure_firewally.py' to configure firewall")
    else:
        print ("Unable to save configuration to file, please try again")