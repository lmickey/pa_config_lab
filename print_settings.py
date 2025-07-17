import load_settings, sys

#Protected fields
protectedFields = ['paSCPsk','pass','mgmtPass','scmPass','paApiUser','paApiSecret']
# Load settings from config file
configFile = load_settings.load_settings()
if not configFile:
    print("Failed to load configuration file.")
    sys.exit()
fwData = configFile['fwData']
paData = configFile['paData']

# Print firewall/Panorama data
print ("Firewall & Panorama Configuration Settings")
for key,value in fwData.items():
    if key not in protectedFields: 
        print (str(key) + ":\t" + str(value))
    else:
        print (str(key) + ":\t************")

# Prisma Access Configuration
print ("\n\nPrisma Access Configuration Settings")
for key,value in paData.items():
    if key not in protectedFields: 
        print (str(key) + ":\t" + str(value))
    else:
        print (str(key) + ":\t************")
