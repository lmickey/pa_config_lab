# Infrastructure Capture Guide

**Prisma Access Configuration Capture Tool v2.0**  
**Last Updated:** December 21, 2025

---

## Table of Contents

1. [Introduction](#introduction)
2. [What's New](#whats-new)
3. [Infrastructure Components](#infrastructure-components)
4. [Getting Started](#getting-started)
5. [Using the GUI](#using-the-gui)
6. [Using the CLI](#using-the-cli)
7. [Using the API](#using-the-api)
8. [Configuration Options](#configuration-options)
9. [Understanding the Output](#understanding-the-output)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [Advanced Usage](#advanced-usage)

---

## Introduction

The Prisma Access Configuration Capture Tool v2.0 now includes comprehensive infrastructure capture capabilities. This guide will help you understand and use the new infrastructure features to capture complete configurations from your Prisma Access tenant.

### What Can You Capture?

The tool can now capture:

**Core Configuration** (existing):
- Security policy folders and rules
- Security objects (addresses, services, applications)
- Security profiles (AV, AS, vulnerability, etc.)
- Configuration snippets

**Infrastructure** (NEW):
- Remote Networks (branch offices, data centers)
- Service Connections (on-premises connectivity)
- IPsec Tunnels and IKE Gateways
- Crypto Profiles (IKE and IPsec)
- Mobile User Infrastructure (GlobalProtect)
- HIP Objects and Profiles
- Regions and Bandwidth Allocations

---

## What's New

### Version 2.0 Infrastructure Enhancements

✅ **30+ New API Methods** - Comprehensive infrastructure endpoint coverage  
✅ **Rate Limiting** - Configured to 45 req/min (90% of 50 req/min limit) for safe operation  
✅ **GUI Integration** - 6 new checkboxes for infrastructure components  
✅ **Custom Applications** - Option to capture custom/user-created applications  
✅ **Graceful Degradation** - Handles unavailable endpoints (e.g., HIP in some environments)  
✅ **Comprehensive Testing** - 300+ test cases for infrastructure capture  
✅ **Schema Extensions** - Updated JSON schema to accommodate all infrastructure data

---

## Infrastructure Components

### 1. Remote Networks

**What:** Branch offices and data center connections to Prisma Access.

**Includes:**
- Remote network definitions
- BGP configuration
- IPsec tunnel associations
- Subnet assignments
- Region/location information
- Licensing details

**When to capture:**
- Documenting branch connectivity
- Backup before changes to remote networks
- Migration planning

**Example Use Case:**  
You have 50 branch offices connected via remote networks. Capture this to document the configuration before restructuring your network topology.

---

### 2. Service Connections

**What:** On-premises connectivity for services (e.g., data centers, cloud providers).

**Includes:**
- Service connection definitions
- NAT configuration
- Subnet mappings
- QoS settings
- Onboarding type (classic/next-gen)

**When to capture:**
- Before modifying service connection settings
- Documenting data center connectivity
- Compliance/audit requirements

**Example Use Case:**  
Your organization connects to AWS and Azure via service connections. Capture these configurations for disaster recovery planning.

---

### 3. IPsec Tunnels & Crypto

**What:** VPN tunnel infrastructure including tunnels, gateways, and encryption settings.

**Includes:**
- IPsec tunnel configurations
- IKE gateway settings
- IKE crypto profiles (Phase 1)
- IPsec crypto profiles (Phase 2)
- Peer authentication settings
- Tunnel monitoring configuration

**When to capture:**
- Security audit requirements
- Before changing encryption standards
- Documenting VPN infrastructure

**Example Use Case:**  
Compliance requires documentation of all encryption settings. Capture IPsec infrastructure to generate a report showing AES-256 encryption is used everywhere.

---

### 4. Mobile User Infrastructure

**What:** GlobalProtect configuration for mobile and remote users.

**Includes:**
- GlobalProtect gateway configurations
- GlobalProtect portal settings
- IP pool assignments
- Authentication profile associations
- Tunnel interface mappings

**When to capture:**
- Before modifying remote user access
- Documenting mobile user setup
- Troubleshooting connectivity issues

**Example Use Case:**  
Your organization has 5,000 remote workers using GlobalProtect. Capture the infrastructure to understand IP pool allocation and gateway distribution.

---

### 5. HIP Objects & Profiles

**What:** Host Information Profile (HIP) checks for endpoint compliance.

**Includes:**
- HIP object definitions (OS checks, antivirus, disk encryption)
- HIP profile assignments
- Matching criteria

**When to capture:**
- Documenting endpoint security requirements
- Backup before modifying compliance policies
- Audit trail for security standards

**Example Use Case:**  
Capture HIP configuration to document that all endpoints must have antivirus and disk encryption enabled.

**Note:** HIP endpoints may not be available in all Prisma Access environments. The tool handles this gracefully.

---

### 6. Regions & Bandwidth

**What:** Prisma Access deployment regions and bandwidth allocations.

**Includes:**
- Enabled locations/regions
- Bandwidth allocation per region
- Compute unit allocation
- Service types per region

**When to capture:**
- Capacity planning
- Cost analysis
- Before scaling operations

**Example Use Case:**  
Capture region and bandwidth data to analyze costs and plan for expanding to additional regions.

---

## Getting Started

### Prerequisites

1. **Prisma Access API Credentials:**
   - TSG ID (Tenant Service Group ID)
   - Client ID (API User)
   - Client Secret (API Secret)

2. **Python Environment:**
   - Python 3.8+
   - Required packages (see `requirements.txt`)

3. **Network Access:**
   - Connectivity to Prisma Access API endpoints
   - No firewall blocking HTTPS to Palo Alto Networks cloud

### Installation

```bash
# Clone/download the repository
cd pa_config_lab

# Install dependencies
pip install -r requirements.txt
```

---

## Using the GUI

### Launching the GUI

```bash
python3 run_gui.py
```

Or on Windows:
```batch
run_gui.bat
```

### Step-by-Step: Pulling Infrastructure Configuration

#### Step 1: Connect to Prisma Access

1. Click **"Connect"** tab
2. Enter your credentials:
   - **TSG ID:** `tsg-1234567890`
   - **Client ID:** Your API client ID
   - **Client Secret:** Your API secret
3. Click **"Connect"**
4. Wait for green "Connected" message

#### Step 2: Configure Pull Options

1. Click **"Pull"** tab
2. You'll see several sections:

**Configuration Components** (Core):
- ☑ Security Policy Folders
- ☑ Configuration Snippets
- ☑ Security Rules
- ☑ Security Objects
- ☑ Security Profiles
- ☐ Custom Applications (see below)

**Infrastructure Components** (NEW):
- ☑ Remote Networks
- ☑ Service Connections
- ☑ IPsec Tunnels & Crypto
- ☑ Mobile User Infrastructure
- ☑ HIP Objects & Profiles
- ☑ Regions & Bandwidth

**Advanced Options:**
- ☐ Filter Default Configurations

#### Step 3: Select What to Capture

**Option A: Capture Everything** (recommended for initial backup)
- Click **"Select All"** button
- All checkboxes will be selected (except Custom Applications)

**Option B: Capture Specific Components**
- Check only the components you need
- Example: Only check infrastructure options if you just need infrastructure

**Option C: Custom Applications** (advanced)
- Check **"Custom Applications"**
- Click **"Select Applications..."** button
- Enter application names (comma-separated): `CustomApp1, CustomApp2`
- Note: Only needed for custom/user-created applications. Predefined applications are already included in Security Objects.

#### Step 4: Start the Pull

1. Click **"Pull Configuration"** button
2. Monitor progress in the Progress section:
   - Progress bar shows completion
   - Status messages appear in real-time
3. Wait for completion (typically 1-5 minutes depending on configuration size)

#### Step 5: Review Results

The Results section shows:
- Components captured and counts
- Any errors or warnings
- Total time elapsed

Example output:
```
✅ Pull completed successfully!

Captured:
- Folders: 5
- Rules: 127
- Objects: 342
- Profiles: 28
- Remote Networks: 23
- Service Connections: 4
- IPsec Tunnels: 23
- IKE Gateways: 23
- Mobile User Infrastructure: 2 gateways, 1 portal
- Regions: 3 enabled locations

Time: 2m 34s
```

#### Step 6: Save Configuration

1. Click **"Save"** tab
2. Choose filename (e.g., `prod_backup_2025-12-21.json`)
3. Optional: Enable encryption (recommended for production configs)
4. Click **"Save Configuration"**

---

## Using the CLI

### Basic CLI Pull

```bash
python3 -m cli.pull_cli
```

### Interactive Mode

The CLI will prompt you for:
1. **Connection:** TSG ID, Client ID, Client Secret
2. **Folders:** Multi-select folders to include
3. **Snippets:** Multi-select snippets to include
4. **Components:** What to capture (rules, objects, profiles)
5. **Infrastructure:** Which infrastructure components to capture
6. **Custom Applications:** (Optional) Search and select custom applications
7. **Output:** Filename for saved configuration

### Non-Interactive Mode

```bash
# Pull everything to a specific file
python3 -m cli.pull_cli \
  --tsg-id tsg-1234567890 \
  --client-id "your-client-id" \
  --client-secret "your-client-secret" \
  --output full_backup.json \
  --all-components \
  --all-infrastructure
```

### Selective Infrastructure Pull

```bash
# Pull only network infrastructure
python3 -m cli.pull_cli \
  --tsg-id tsg-1234567890 \
  --client-id "your-client-id" \
  --client-secret "your-client-secret" \
  --output network_infra.json \
  --include-remote-networks \
  --include-service-connections \
  --include-ipsec-tunnels
```

---

## Using the API

### Python Script Example

```python
#!/usr/bin/env python3
"""
Example: Capture all infrastructure programmatically
"""

from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.pull_orchestrator import PullOrchestrator
from config.storage.json_storage import JSONConfigStorage

# Initialize API client
client = PrismaAccessAPIClient(
    tsg_id="tsg-1234567890",
    api_user="your-client-id",
    api_secret="your-client-secret",
    rate_limit=45  # 45 req/min (90% of 50)
)

# Verify authentication
if not client.token:
    print("Authentication failed!")
    exit(1)

print(f"✅ Connected to {client.tsg_id}")

# Initialize pull orchestrator
orchestrator = PullOrchestrator(client)

# Pull complete configuration with all infrastructure
print("📥 Pulling configuration...")

config = orchestrator.pull_complete_configuration(
    # Core components
    include_folders=True,
    include_snippets=True,
    include_rules=True,
    include_objects=True,
    include_profiles=True,
    
    # Infrastructure components (all enabled)
    include_remote_networks=True,
    include_service_connections=True,
    include_ipsec_tunnels=True,
    include_mobile_users=True,
    include_hip=True,
    include_regions=True,
    
    # Optional: Custom applications
    application_names=None,  # or ["CustomApp1", "CustomApp2"]
    
    # Optional: Default detection
    detect_defaults=False
)

# Check results
if config:
    metadata = config.get('metadata', {})
    stats = metadata.get('pull_stats', {})
    
    print("\n✅ Pull completed successfully!")
    print(f"   Folders: {stats.get('folders', 0)}")
    print(f"   Rules: {stats.get('rules', 0)}")
    print(f"   Objects: {stats.get('objects', 0)}")
    print(f"   Time: {stats.get('elapsed_seconds', 0):.1f}s")
    
    # Save to file
    storage = JSONConfigStorage()
    filename = "complete_config.json"
    storage.save_config(config, filename)
    print(f"\n💾 Saved to {filename}")
else:
    print("❌ Pull failed!")
```

### Infrastructure-Only Script

```python
#!/usr/bin/env python3
"""
Example: Capture only infrastructure (no security policies)
"""

from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.infrastructure_capture import InfrastructureCapture
import json

client = PrismaAccessAPIClient(
    tsg_id="tsg-1234567890",
    api_user="your-client-id",
    api_secret="your-client-secret"
)

capture = InfrastructureCapture(client)

# Capture all infrastructure
infra = capture.capture_all_infrastructure()

# Save to file
with open('infrastructure_only.json', 'w') as f:
    json.dump(infra, f, indent=2)

print(f"✅ Captured infrastructure:")
print(f"   Remote Networks: {len(infra.get('remote_networks', []))}")
print(f"   Service Connections: {len(infra.get('service_connections', []))}")
print(f"   IPsec Tunnels: {len(infra.get('ipsec_tunnels', {}).get('ipsec_tunnels', []))}")
```

---

## Configuration Options

### Rate Limiting

**Default:** 45 requests per minute (90% of 50 req/min API limit)

**Why:** Provides a safety buffer to prevent hitting the API rate limit, which would cause delays.

**Customization:**
```python
# Increase to 48 req/min (96% of limit)
client = PrismaAccessAPIClient(
    tsg_id=tsg_id,
    api_user=api_user,
    api_secret=api_secret,
    rate_limit=48
)
```

### Default Detection

**What:** Automatically identifies and excludes default/predefined configurations.

**When to use:**
- Backup for migration (only need custom configs)
- Cleaner configuration files
- Focus on user-created objects

**When NOT to use:**
- Complete backup (include everything)
- Disaster recovery planning
- Compliance/audit (need full picture)

**Enable in GUI:** Check "Filter Default Configurations" under Advanced Options

**Enable in CLI:** Add `--detect-defaults` flag

**Enable in API:**
```python
config = orchestrator.pull_complete_configuration(
    detect_defaults=True,  # Enable default detection
    ...
)
```

---

## Understanding the Output

### Configuration File Structure

```json
{
  "metadata": {
    "version": "2.0.0",
    "created": "2025-12-21T10:30:00Z",
    "source_tenant": "tsg-1234567890",
    "pull_stats": {
      "folders": 5,
      "rules": 127,
      "objects": 342,
      "profiles": 28,
      "errors": 0,
      "elapsed_seconds": 154.3
    }
  },
  "infrastructure": {
    "shared_infrastructure_settings": {},
    "mobile_agent": {},
    "service_connections": [...],
    "remote_networks": [...],
    "ipsec_tunnels": [...],
    "ike_gateways": [...],
    "ike_crypto_profiles": [...],
    "ipsec_crypto_profiles": [...]
  },
  "mobile_users": {
    "infrastructure_settings": {},
    "gp_gateways": [...],
    "gp_portals": [...]
  },
  "hip": {
    "hip_objects": [...],
    "hip_profiles": [...]
  },
  "regions": {
    "locations": [...],
    "bandwidth_allocations": [...]
  },
  "security_policies": {
    "folders": [...]
  }
}
```

### Interpreting Infrastructure Data

**Remote Network Example:**
```json
{
  "id": "rn-branch-office-chicago",
  "name": "Chicago-Branch",
  "region": "us-central-1",
  "subnets": ["10.50.0.0/16"],
  "ipsec_tunnel": "ipsec-tunnel-chicago",
  "license_type": "FWAAS-AGGREGATE"
}
```

**IPsec Tunnel Example:**
```json
{
  "id": "tunnel-chicago-primary",
  "name": "Chicago-Primary-Tunnel",
  "auto_key": {
    "ike_gateway": [{"name": "chicago-ike-gw"}],
    "ipsec_crypto_profile": "aes256-sha256"
  },
  "anti_replay": true,
  "tunnel_monitor": {"enable": true}
}
```

---

## Best Practices

### 1. Regular Backups

**Schedule regular captures:**
- Daily: For production environments
- Weekly: For stable environments
- Before changes: Always capture before modifications

**Automation example:**
```bash
#!/bin/bash
# backup.sh - Daily backup script

DATE=$(date +%Y%m%d)
FILENAME="backup_${DATE}.json"

python3 -m cli.pull_cli \
  --tsg-id $PRISMA_TSG_ID \
  --client-id $PRISMA_CLIENT_ID \
  --client-secret $PRISMA_CLIENT_SECRET \
  --output "backups/${FILENAME}" \
  --all-components \
  --all-infrastructure \
  --encrypt

echo "✅ Backup saved to backups/${FILENAME}"
```

### 2. Use Encryption

**Always encrypt production configurations:**
- Contains sensitive information (IPs, tunnel configs)
- Required for compliance
- Protects against unauthorized access

**Enable in GUI:** Check "Encrypt configuration" when saving

**Enable in CLI:** Add `--encrypt` flag

### 3. Selective Captures

**Don't always capture everything:**
- **Infrastructure changes:** Only pull infrastructure components
- **Policy changes:** Only pull security policies
- **Faster captures:** Skip unnecessary components

**Example - Network infrastructure only:**
```python
infra = capture.capture_all_infrastructure(
    include_remote_networks=True,
    include_service_connections=True,
    include_ipsec_tunnels=True,
    include_mobile_users=False,  # Skip
    include_hip=False,  # Skip
    include_regions=False  # Skip (unless needed)
)
```

### 4. Monitor Rate Limiting

**Watch the logs:**
```
INFO - Rate limit approaching, waiting 1.5 seconds...
```

If you see frequent rate limit messages:
- Consider reducing pull frequency
- Capture fewer components per pull
- Split large captures into multiple runs

### 5. Handle Unavailable Endpoints

**Some endpoints may not be available:**
- HIP endpoints (not in all environments)
- Newer features (may not be enabled)

**The tool handles this automatically:**
- Logs warning
- Returns empty list
- Continues with other components

**Check logs for warnings:**
```
WARNING - HIP endpoint unavailable (404), skipping
INFO - Successfully captured 5 of 6 infrastructure components
```

---

## Troubleshooting

### Issue: Authentication Failed

**Symptoms:**
- "Authentication failed" error
- "Invalid credentials" message

**Solutions:**
1. Verify TSG ID format: `tsg-1234567890`
2. Check Client ID and Secret (no extra spaces)
3. Ensure API credentials have proper permissions
4. Verify network connectivity to Prisma Access

---

### Issue: Rate Limit Errors

**Symptoms:**
- "Rate limit exceeded" errors
- Long delays during pull
- 429 status code errors

**Solutions:**
1. Reduce rate limit in configuration:
   ```python
   client = PrismaAccessAPIClient(..., rate_limit=30)
   ```
2. Add delays between pulls
3. Capture fewer components per pull

---

### Issue: HIP Endpoint Unavailable

**Symptoms:**
- "404 Not Found" for HIP objects
- Empty HIP section in output

**Solution:**
- This is expected in some environments
- HIP endpoints may not be enabled
- Tool handles gracefully - no action needed
- Uncheck "HIP Objects & Profiles" if not needed

---

### Issue: Incomplete Infrastructure Data

**Symptoms:**
- Some infrastructure sections are empty
- Expected objects missing

**Checks:**
1. Verify objects exist in Prisma Access (check via web UI)
2. Check folder filters (objects may be in different folder)
3. Review pull logs for errors
4. Verify API permissions include infrastructure access

---

### Issue: Slow Performance

**Symptoms:**
- Pull takes >10 minutes
- GUI appears frozen

**Solutions:**
1. Use CLI instead of GUI for large captures
2. Capture in stages:
   - First: Core configuration
   - Second: Infrastructure
3. Increase rate limit (carefully):
   ```python
   client = PrismaAccessAPIClient(..., rate_limit=48)
   ```
4. Check network latency to Prisma Access

---

## Advanced Usage

### Custom Infrastructure Queries

```python
from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.infrastructure_capture import InfrastructureCapture

client = PrismaAccessAPIClient(tsg_id, api_user, api_secret)
capture = InfrastructureCapture(client)

# Capture only remote networks in a specific folder
rns = capture.capture_remote_networks(folder="Remote Networks")

# Filter by region
us_east_rns = [rn for rn in rns if rn.get('region') == 'us-east-1']

print(f"Remote Networks in us-east-1: {len(us_east_rns)}")
```

### Generating Reports

```python
import json
from datetime import datetime

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Generate infrastructure summary report
report = {
    "report_date": datetime.now().isoformat(),
    "tenant": config['metadata']['source_tenant'],
    "infrastructure_summary": {
        "remote_networks": len(config['infrastructure']['remote_networks']),
        "service_connections": len(config['infrastructure']['service_connections']),
        "ipsec_tunnels": len(config['infrastructure']['ipsec_tunnels']),
        "gp_gateways": len(config['mobile_users']['gp_gateways']),
        "enabled_regions": len(config['regions']['locations'])
    },
    "security_summary": {
        "folders": len(config['security_policies']['folders']),
        "total_rules": sum(
            len(folder.get('security_rules', []))
            for folder in config['security_policies']['folders']
        )
    }
}

# Save report
with open('infrastructure_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("📊 Report generated: infrastructure_report.json")
```

### Comparing Configurations

```python
import json

def compare_infrastructure(config1_file, config2_file):
    """Compare infrastructure between two configurations."""
    
    with open(config1_file) as f1, open(config2_file) as f2:
        config1 = json.load(f1)
        config2 = json.load(f2)
    
    # Compare remote networks
    rn1_names = {rn['name'] for rn in config1['infrastructure']['remote_networks']}
    rn2_names = {rn['name'] for rn in config2['infrastructure']['remote_networks']}
    
    added = rn2_names - rn1_names
    removed = rn1_names - rn2_names
    
    print("Remote Networks Comparison:")
    print(f"  Added: {added}")
    print(f"  Removed: {removed}")
    print(f"  Unchanged: {len(rn1_names & rn2_names)}")

# Compare before/after configurations
compare_infrastructure('before_change.json', 'after_change.json')
```

### Scheduled Backups with Rotation

```bash
#!/bin/bash
# scheduled_backup.sh - Backup with rotation

BACKUP_DIR="backups"
MAX_BACKUPS=30  # Keep 30 days of backups

# Create backup
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="${BACKUP_DIR}/backup_${DATE}.json"

python3 -m cli.pull_cli \
  --tsg-id $PRISMA_TSG_ID \
  --client-id $PRISMA_CLIENT_ID \
  --client-secret $PRISMA_CLIENT_SECRET \
  --output "$FILENAME" \
  --all-components \
  --all-infrastructure \
  --encrypt

# Rotate old backups
cd $BACKUP_DIR
ls -t backup_*.json | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm

echo "✅ Backup complete: $FILENAME"
echo "📁 Keeping $MAX_BACKUPS most recent backups"
```

---

## See Also

- [API Reference](API_REFERENCE_INFRASTRUCTURE.md) - Detailed API documentation
- [User Guide](USAGE.md) - General usage instructions
- [Security Guide](SECURITY.md) - Security best practices
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions

---

**Questions or Issues?**

Refer to the main documentation or check the logs in the application for detailed error messages.

---

**End of Infrastructure Capture Guide**
