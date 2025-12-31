import glob, os, pickle, base64, hashlib, requests, sys, getpass, json
from cryptography.fernet import Fernet

# Import new storage modules (with fallback for backward compatibility)
try:
    from config.storage.pickle_compat import detect_config_format, load_config_auto
    from config.storage.json_storage import load_config_json, list_config_files as list_json_configs
    NEW_STORAGE_AVAILABLE = True
except ImportError:
    NEW_STORAGE_AVAILABLE = False

# Defined functions
def derive_key(password: str) -> bytes:
    # Use SHA-256 hash to derive a 32-byte key from password
    hash = hashlib.sha256(password.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(hash))

# Load and decrypt data then return to script that needs it
def load_settings(cipher=None):
    scriptDir = os.getcwd()

    # Get list of config files in current directory and print list
    fileNameList = list_config_files(scriptDir)

    #Ask user which file to load
    while True:
        try:
            configChoice = input("Enter Number for Configuration to Load (x to Exit):")
            if configChoice.lower() == 'x': sys.exit()
            if int(configChoice) in range(len(fileNameList)+1):
                print ("Loading " + os.path.basename(fileNameList[int(configChoice)-1]).split('-')[0] + " Config")
                # Set file path to selected file
                filePath = os.path.join(scriptDir, fileNameList[int(configChoice)-1])
                break
            else:
                raise ValueError
        except ValueError:
            print("Invalid value Please enter a valid option")
        
    # Get Settings encryption password if empty
    if not cipher: cipher = derive_key(getpass.getpass("Enter password for config file: "))

    # Use new storage system if available, otherwise fall back to legacy
    if NEW_STORAGE_AVAILABLE:
        try:
            # Try to load using new system (supports both formats)
            data = load_config_auto(filePath, cipher)
            
            if data:
                print ("Config File Loaded")
                # Extract config name from filename
                base_name = os.path.basename(fileNameList[int(configChoice)-1])
                # Remove extensions and suffixes
                config_name = base_name.split('-')[0]
                if config_name.endswith('-fwdata'):
                    config_name = config_name[:-7]
                if config_name.endswith('-config'):
                    config_name = config_name[:-7]
                
                #Add the cipher and filename so we can save config if needed
                data['configName'] = config_name
                data['configCipher'] = cipher
                data['configFilePath'] = filePath
                
                # If v2 format, ensure backward compatibility fields exist
                if 'metadata' in data and 'version' in data['metadata']:
                    version = data['metadata']['version']
                    if version and version.startswith('2.'):
                        # Ensure fwData and paData exist for backward compatibility
                        if 'fwData' not in data:
                            data['fwData'] = {}
                        if 'paData' not in data:
                            data['paData'] = {}
                
                return data
        except Exception as e:
            print(f"Error loading with new storage system: {e}")
            print("Falling back to legacy format...")
    
    # Legacy pickle loading (fallback)
    try:
        # Read file contents
        with open(filePath, 'rb') as f:
            encrypted_data = f.read()
        
        # Decrypt config file, load from pickle format into dictionaries
        decrypted_data = cipher.decrypt(encrypted_data)
        data = pickle.loads(decrypted_data)
        print ("Config File Loaded (Legacy Format)")
        #Add the cipher and filename so we can save config if needed
        data['configName'] = os.path.basename(fileNameList[int(configChoice)-1]).split('-')[0]
        data['configCipher'] = cipher
        data['configFilePath'] = filePath
        return data
    except Exception as e:
        print("Decryption failed:", e)
        return None

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


def list_config_files(directory):
    """
    List all configuration files (both legacy .bin and new .json formats).
    
    Args:
        directory: Directory to search
        
    Returns:
        List of configuration file paths
    """
    matchingFiles = []
    
    # List legacy pickle files
    filePattern = "*-fwdata.bin"
    fullPattern = os.path.join(directory, filePattern)
    pickleFiles = glob.glob(fullPattern)
    matchingFiles.extend(pickleFiles)
    
    # List new JSON files (if new storage available)
    if NEW_STORAGE_AVAILABLE:
        try:
            jsonFiles = list_json_configs(directory, "*-config.json")
            matchingFiles.extend(jsonFiles)
        except Exception:
            pass
    
    # Remove duplicates and sort
    matchingFiles = sorted(list(set(matchingFiles)))
    
    # Print list
    count = 0
    for file in matchingFiles:
        count += 1
        base_name = os.path.basename(file)
        # Extract config name
        config_name = base_name.split('-')[0]
        if config_name.endswith('-fwdata'):
            config_name = config_name[:-7]
        if config_name.endswith('-config'):
            config_name = config_name[:-7]
        
        # Show format indicator
        if file.endswith('.json'):
            format_indicator = " [JSON]"
        else:
            format_indicator = " [Legacy]"
        
        print(str(count) + " - " + config_name + format_indicator)
    
    return matchingFiles