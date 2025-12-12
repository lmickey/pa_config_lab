from panos.firewall import Firewall
from panos.device import NTPServerPrimary, NTPServerSecondary, SystemSettings
from panos.ha import HighAvailability
import load_settings, sys, getpass

# Get Settings encryption password
encryptPass = load_settings.derive_key(getpass.getpass("Enter password for encryption: "))

# Example usage
data = load_settings.load_settings(encryptPass)
if not data:
    print("Failed to decrypt data.")
    sys.exit()

##### Establish connection
firewall = Firewall(data['fwData']["mgmtUrl"],data['fwData']['mgmtUser'],data['fwData']["mgmtPass"],vsys=None, is_virtual=True)

# Configure HA disabled
haConf = HighAvailability(enabled=False,config_sync=False,state_sync=False)
firewall.add(haConf)
haConf.apply()

# Update DNS Settings
system = SystemSettings(dns_primary='8.8.8.8', dns_secondary='8.8.4.4')

# Add primary NTP server
ntp1 = NTPServerPrimary(address='0.pool.ntp.org', authentication_type='None')
system.add(ntp1)

# Add secondary NTP server
ntp2 = NTPServerSecondary(address='1.pool.ntp.org', authentication_type='None')
system.add(ntp2)


firewall.add(system)
system.apply()
firewall.commit()