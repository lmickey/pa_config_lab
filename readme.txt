Instructions:

## Prerequisites
- Python 3.x installed
- Palo Alto Networks firewall or VM-Series firewall accessible
- Prisma Access tenant (if configuring Service Connections)
- Required Python packages (install via: pip install -r requirements.txt)

## Initial Setup

1. **Create Configuration File**
   - Run `python get_settings.py` to create a new encrypted configuration file
   - Enter firewall management URL, username, and password (minimum required)
   - Follow prompts to configure firewall and Prisma Access settings
   - Configuration files are encrypted and stored as `*-fwdata.bin` files

2. **Configure Initial Firewall Settings**
   - Run `python configure_initial_config.py` to set NTP/DNS configuration
   - This configures:
     - NTP servers (0.pool.ntp.org, 1.pool.ntp.org)
     - DNS servers (8.8.8.8, 8.8.4.4)
     - High Availability settings (disabled by default)

3. **Register and License Firewall**
   - Register the firewall with https://support.paloaltonetworks.com to your SE CSP
   - Get licenses and generate OTP
   - Obtain device certificate

4. **Configure Firewall (Interfaces, Zones, Routes, Policies)**
   - Run `python configure_firewall.py` to configure:
     - Zones (trust, untrust)
     - Interfaces (ethernet1/1 untrust, ethernet1/2 trust)
     - Static routes (default route)
     - Address objects (Trust-Network, Untrust-Network, Panorama-Server)
     - Security rules (Outbound Internet, Allow Panorama Management, Deny All)
     - NAT rules (Outbound Internet PAT, Panorama Management)

## Prisma Access Service Connection Configuration

### For SCM (Prisma Access Cloud) Managed Deployments

1. **Configure Service Connection in SCM**
   - Run `python configure_service_connection.py`
   - When prompted, answer 'y' to configure Prisma Access end
   - Script will create:
     - IKE Crypto Profile
     - IPSec Crypto Profile
     - IKE Gateway
     - IPSec Tunnel
     - Service Connection
   - Configuration is automatically committed to SCM

2. **Configure Firewall End of Service Connection**
   - Continue with the same script (`configure_service_connection.py`)
   - When prompted, answer 'y' to configure firewall end
   - Script will configure:
     - VPN zone
     - Tunnel interface
     - Static routes for Prisma Access subnets
     - Address objects and groups
     - IKE/IPSec crypto profiles
     - IKE Gateway
     - IPSec Tunnel
     - Security rules for Service Connection traffic

### For Panorama Managed Deployments

1. **Configure Panorama** (Manual Step)
   - Panorama Service Connection configuration requires:
     - Prisma Access plugin installed on Panorama
     - Manual configuration through Panorama UI or REST API
   - Run `python configure_service_connection.py` for guidance
   - Ensure the following are configured in Panorama:
     - Service Connection Name
     - Location
     - Subnet
     - Pre-shared Key
     - Firewall FQDN

2. **Configure Firewall End**
   - Run `python configure_service_connection.py`
   - Answer 'n' to Prisma Access configuration (already done manually)
   - Answer 'y' to firewall configuration
   - Script will configure the firewall side as described above

## Utility Scripts

- `get_settings.py` - Create or edit encrypted configuration files
- `load_settings.py` - Load and decrypt configuration files (used by other scripts)
- `print_settings.py` - Display current configuration (passwords masked)
- `get_fw_version.py` - Retrieve and display firewall version

## Configuration File Management

- Configuration files are encrypted using Fernet encryption
- Files are named: `{config-name}-fwdata.bin`
- Use `get_settings.py` to create new configurations or edit existing ones
- Protected fields (passwords, secrets) are masked when displayed

## Troubleshooting

- **Configuration load errors**: Verify encryption password is correct
- **Firewall connection errors**: Check management URL, credentials, and network connectivity
- **Missing variables**: Run `get_settings.py` to add missing configuration values
- **SCM authentication errors**: Verify TSG ID, Client ID, and Client Secret in configuration

## Notes

- All scripts require a valid encrypted configuration file
- Configuration files must be created using `get_settings.py` before running other scripts
- Firewall commits are performed automatically after each configuration step
- Service Connection configuration requires proper Prisma Access tenant setup