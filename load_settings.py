import glob, os, pickle, base64, hashlib, requests, sys, getpass
from cryptography.fernet import Fernet

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

    # Read file contents
    with open(filePath, 'rb') as f:
        encrypted_data = f.read()
    
    # Decrpt config file, load from pickle format into dictionaries
    try:
        decrypted_data = cipher.decrypt(encrypted_data)
        data = pickle.loads(decrypted_data)
        print ("Config File Loaded")
        #Add the cipher and filename so we can save config if needed
        data['configName'] = os.path.basename(fileNameList[int(configChoice)-1]).split('-')[0]
        data['configCipher'] = cipher
        return data
    except Exception as e:
        print("Decryption failed:", e)
        return None

def prisma_access_auth(tsg,user,password):
    scmUrl = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
    scope = 'tsg_id:'+tsg
    paramValues = {'grant_type':'client_credentials','scope':scope}
    
    response = requests.post(scmUrl, auth=(user, password), params=paramValues)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        return None


def list_config_files(directory):
    filePattern = "*-fwdata.bin"  # Matches all config files in current directory
    count = 0

    # Construct the full pattern for glob
    fullPattern = os.path.join(directory, filePattern)

    # List files matching the pattern
    matchingFiles = glob.glob(fullPattern)

    for file in matchingFiles:
        count += 1
        print(str(count) + " - " + os.path.basename(file).split('-')[0])
    
    return matchingFiles