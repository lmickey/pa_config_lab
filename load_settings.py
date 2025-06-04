import os, pickle, base64, hashlib, requests
from cryptography.fernet import Fernet

# Defined functions
def derive_key(password: str) -> bytes:
    # Use SHA-256 hash to derive a 32-byte key from password
    hash = hashlib.sha256(password.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(hash))

# Load and decrypt data
def load_settings(cipher):
    fileName = 'fwdata.bin'
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

def prisma_access_auth(tsg,user,password):
    scmUrl = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
    scope = 'tsg_id:'+tsg
    paramValues = {'grant_type':'client_credentials','scope':scope}
    
    response = requests.post(scmUrl, auth=(user, password), params=paramValues)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        return None


