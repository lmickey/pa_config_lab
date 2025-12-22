# Infrastructure Capture API Reference

**Version:** 2.0.0  
**Last Updated:** December 21, 2025

---

## Overview

The Infrastructure Capture module provides comprehensive functionality for capturing Prisma Access infrastructure configurations including:

- **Remote Networks** - Branch offices and data centers
- **Service Connections** - On-premises connectivity
- **IPsec/IKE Infrastructure** - VPN tunnels, gateways, and crypto profiles
- **Mobile User Infrastructure** - GlobalProtect gateways and portals
- **HIP (Host Information Profile)** - Objects and profiles
- **Regions & Bandwidth** - Deployed locations and bandwidth allocations

---

## Table of Contents

1. [API Client Methods](#api-client-methods)
2. [Infrastructure Capture Module](#infrastructure-capture-module)
3. [Pull Orchestrator Integration](#pull-orchestrator-integration)
4. [Configuration Schema](#configuration-schema)
5. [Rate Limiting](#rate-limiting)
6. [Error Handling](#error-handling)
7. [Examples](#examples)

---

## API Client Methods

### Remote Networks

#### `get_remote_networks(folder=None, limit=200, offset=0)`

Retrieve remote network configurations with pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name
- `limit` (int): Maximum number of results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing remote network data

**Example:**
```python
client = PrismaAccessAPIClient(tsg_id, api_user, api_secret)
response = client.get_remote_networks(folder="Remote Networks")
```

#### `get_all_remote_networks(folder=None)`

Retrieve all remote networks with automatic pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of all remote network objects

**Example:**
```python
all_rns = client.get_all_remote_networks()
for rn in all_rns:
    print(f"Remote Network: {rn['name']} - Region: {rn['region']}")
```

#### `get_remote_network(network_id)`

Retrieve a specific remote network by ID.

**Parameters:**
- `network_id` (str): Remote network ID

**Returns:**
- `dict`: Remote network object

---

### Service Connections

#### `get_service_connections(folder=None, limit=200, offset=0)`

Retrieve service connection configurations with pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing service connection data

#### `get_all_service_connections(folder=None)`

Retrieve all service connections with automatic pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of all service connection objects

#### `get_service_connection(connection_id)`

Retrieve a specific service connection by ID.

**Parameters:**
- `connection_id` (str): Service connection ID

**Returns:**
- `dict`: Service connection object

---

### IPsec Tunnels

#### `get_ipsec_tunnels(folder=None, limit=200, offset=0)`

Retrieve IPsec tunnel configurations with pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing IPsec tunnel data

#### `get_all_ipsec_tunnels(folder=None)`

Retrieve all IPsec tunnels with automatic pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of all IPsec tunnel objects

#### `get_ipsec_tunnel(tunnel_id)`

Retrieve a specific IPsec tunnel by ID.

**Parameters:**
- `tunnel_id` (str): IPsec tunnel ID

**Returns:**
- `dict`: IPsec tunnel object

---

### IKE Gateways

#### `get_ike_gateways(folder=None, limit=200, offset=0)`

Retrieve IKE gateway configurations with pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing IKE gateway data

#### `get_all_ike_gateways(folder=None)`

Retrieve all IKE gateways with automatic pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of all IKE gateway objects

#### `get_ike_gateway(gateway_id)`

Retrieve a specific IKE gateway by ID.

**Parameters:**
- `gateway_id` (str): IKE gateway ID

**Returns:**
- `dict`: IKE gateway object

---

### Crypto Profiles

#### `get_ike_crypto_profiles(folder=None, limit=200, offset=0)`

Retrieve IKE crypto profile configurations with pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing IKE crypto profile data

#### `get_all_ike_crypto_profiles(folder=None)`

Retrieve all IKE crypto profiles with automatic pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of all IKE crypto profile objects

#### `get_ipsec_crypto_profiles(folder=None, limit=200, offset=0)`

Retrieve IPsec crypto profile configurations with pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing IPsec crypto profile data

#### `get_all_ipsec_crypto_profiles(folder=None)`

Retrieve all IPsec crypto profiles with automatic pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of all IPsec crypto profile objects

---

### Mobile User Infrastructure

#### `get_mobile_user_infrastructure()`

Retrieve mobile user infrastructure settings.

**Returns:**
- `dict`: Mobile user infrastructure configuration

#### `get_globalprotect_gateways(folder=None, limit=200, offset=0)`

Retrieve GlobalProtect gateway configurations with pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing GlobalProtect gateway data

#### `get_all_globalprotect_gateways(folder=None)`

Retrieve all GlobalProtect gateways with automatic pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of all GlobalProtect gateway objects

#### `get_globalprotect_portals(folder=None, limit=200, offset=0)`

Retrieve GlobalProtect portal configurations with pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing GlobalProtect portal data

#### `get_all_globalprotect_portals(folder=None)`

Retrieve all GlobalProtect portals with automatic pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of all GlobalProtect portal objects

---

### HIP Objects and Profiles

#### `get_hip_objects(folder=None, limit=200, offset=0)`

Retrieve HIP (Host Information Profile) object configurations with pagination.

**Note:** HIP endpoints may not be available in all environments. The API will return 404 if unavailable.

**Parameters:**
- `folder` (str, optional): Filter by folder name
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing HIP object data

**Raises:**
- `Exception`: May raise exception with "404" if endpoint unavailable

#### `get_all_hip_objects(folder=None)`

Retrieve all HIP objects with automatic pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of all HIP object objects

#### `get_hip_profiles(folder=None, limit=200, offset=0)`

Retrieve HIP profile configurations with pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing HIP profile data

#### `get_all_hip_profiles(folder=None)`

Retrieve all HIP profiles with automatic pagination.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of all HIP profile objects

---

### Regions and Bandwidth

#### `get_locations(limit=200, offset=0)`

Retrieve enabled Prisma Access locations/regions with pagination.

**Parameters:**
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing location data

#### `get_all_locations()`

Retrieve all enabled locations with automatic pagination.

**Returns:**
- `list`: List of all location objects

#### `get_bandwidth_allocations(limit=200, offset=0)`

Retrieve bandwidth allocation configurations with pagination.

**Parameters:**
- `limit` (int): Maximum results per page (default: 200)
- `offset` (int): Pagination offset (default: 0)

**Returns:**
- `dict`: API response containing bandwidth allocation data

#### `get_all_bandwidth_allocations()`

Retrieve all bandwidth allocations with automatic pagination.

**Returns:**
- `list`: List of all bandwidth allocation objects

---

## Infrastructure Capture Module

### Class: `InfrastructureCapture`

**Module:** `prisma.pull.infrastructure_capture`

High-level interface for capturing infrastructure components with error handling and graceful degradation.

#### `__init__(api_client)`

Initialize infrastructure capture.

**Parameters:**
- `api_client` (PrismaAccessAPIClient): Authenticated API client instance

**Example:**
```python
from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.infrastructure_capture import InfrastructureCapture

client = PrismaAccessAPIClient(tsg_id, api_user, api_secret)
capture = InfrastructureCapture(client)
```

---

#### `capture_remote_networks(folder=None)`

Capture remote network configurations.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of remote network objects (empty list on error)

**Example:**
```python
remote_networks = capture.capture_remote_networks(folder="Remote Networks")
print(f"Found {len(remote_networks)} remote networks")
```

---

#### `capture_service_connections(folder=None)`

Capture service connection configurations.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `list`: List of service connection objects (empty list on error)

**Example:**
```python
service_conns = capture.capture_service_connections()
for sc in service_conns:
    print(f"Service Connection: {sc['name']}")
```

---

#### `capture_ipsec_tunnels(folder=None)`

Capture IPsec tunnel configurations and related components.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `dict`: Dictionary containing:
  - `ipsec_tunnels`: List of IPsec tunnel objects
  - `ike_gateways`: List of IKE gateway objects
  - `ike_crypto_profiles`: List of IKE crypto profile objects
  - `ipsec_crypto_profiles`: List of IPsec crypto profile objects
  
  Empty lists returned for failed components.

**Example:**
```python
ipsec_infra = capture.capture_ipsec_tunnels(folder="Shared")
print(f"IPsec Tunnels: {len(ipsec_infra['ipsec_tunnels'])}")
print(f"IKE Gateways: {len(ipsec_infra['ike_gateways'])}")
print(f"IKE Crypto: {len(ipsec_infra['ike_crypto_profiles'])}")
print(f"IPsec Crypto: {len(ipsec_infra['ipsec_crypto_profiles'])}")
```

---

#### `capture_mobile_user_infrastructure()`

Capture mobile user infrastructure configurations.

**Returns:**
- `dict`: Dictionary containing:
  - `infrastructure_settings`: Mobile user infrastructure settings object
  - `gp_gateways`: List of GlobalProtect gateway objects
  - `gp_portals`: List of GlobalProtect portal objects
  
  Empty structures returned on error.

**Example:**
```python
mobile_infra = capture.capture_mobile_user_infrastructure()
print(f"GP Gateways: {len(mobile_infra['gp_gateways'])}")
print(f"GP Portals: {len(mobile_infra['gp_portals'])}")
```

---

#### `capture_hip_objects_and_profiles(folder=None)`

Capture HIP (Host Information Profile) objects and profiles.

**Note:** HIP endpoints may return 404 in some environments. This method handles such errors gracefully.

**Parameters:**
- `folder` (str, optional): Filter by folder name

**Returns:**
- `dict`: Dictionary containing:
  - `hip_objects`: List of HIP object objects
  - `hip_profiles`: List of HIP profile objects
  
  Empty lists returned on error or unavailable endpoint.

**Example:**
```python
hip_config = capture.capture_hip_objects_and_profiles(folder="Shared")
if hip_config['hip_objects']:
    print(f"Found {len(hip_config['hip_objects'])} HIP objects")
else:
    print("No HIP objects or endpoint unavailable")
```

---

#### `capture_regions_and_bandwidth()`

Capture region and bandwidth allocation configurations.

**Returns:**
- `dict`: Dictionary containing:
  - `locations`: List of enabled location/region objects
  - `bandwidth_allocations`: List of bandwidth allocation objects
  
  Empty lists returned on error.

**Example:**
```python
regions = capture.capture_regions_and_bandwidth()
for location in regions['locations']:
    print(f"Region: {location['name']} - {location.get('display_name', 'N/A')}")
```

---

#### `capture_all_infrastructure(folder=None, include_remote_networks=True, include_service_connections=True, include_ipsec_tunnels=True, include_mobile_users=True, include_hip=True, include_regions=True)`

Capture all infrastructure components with selective inclusion.

**Parameters:**
- `folder` (str, optional): Filter by folder name (where applicable)
- `include_remote_networks` (bool): Include remote networks (default: True)
- `include_service_connections` (bool): Include service connections (default: True)
- `include_ipsec_tunnels` (bool): Include IPsec/IKE infrastructure (default: True)
- `include_mobile_users` (bool): Include mobile user infrastructure (default: True)
- `include_hip` (bool): Include HIP objects and profiles (default: True)
- `include_regions` (bool): Include regions and bandwidth (default: True)

**Returns:**
- `dict`: Dictionary with keys for each included component type

**Example:**
```python
# Capture all infrastructure
all_infra = capture.capture_all_infrastructure()

# Capture selective components
selected_infra = capture.capture_all_infrastructure(
    include_remote_networks=True,
    include_service_connections=False,
    include_ipsec_tunnels=True,
    include_mobile_users=False,
    include_hip=False,
    include_regions=True
)
```

---

## Pull Orchestrator Integration

The `PullOrchestrator` class has been enhanced to support infrastructure capture.

### Updated Method: `pull_complete_configuration(...)`

**New Parameters:**
- `include_remote_networks` (bool): Pull remote networks (default: True)
- `include_service_connections` (bool): Pull service connections (default: True)
- `include_ipsec_tunnels` (bool): Pull IPsec/IKE infrastructure (default: True)
- `include_mobile_users` (bool): Pull mobile user infrastructure (default: True)
- `include_hip` (bool): Pull HIP objects and profiles (default: True)
- `include_regions` (bool): Pull regions and bandwidth (default: True)
- `application_names` (list, optional): List of custom application names to capture

**Example:**
```python
from prisma.pull.pull_orchestrator import PullOrchestrator

orchestrator = PullOrchestrator(api_client)

config = orchestrator.pull_complete_configuration(
    include_folders=True,
    include_snippets=True,
    include_rules=True,
    include_objects=True,
    include_profiles=True,
    # Infrastructure options
    include_remote_networks=True,
    include_service_connections=True,
    include_ipsec_tunnels=True,
    include_mobile_users=True,
    include_hip=True,
    include_regions=True,
    # Custom applications
    application_names=["CustomApp1", "CustomApp2"]
)
```

---

## Configuration Schema

The configuration schema has been extended to include infrastructure components.

### Infrastructure Section

```json
{
  "infrastructure": {
    "shared_infrastructure_settings": {},
    "mobile_agent": {},
    "service_connections": [],
    "remote_networks": [],
    "ipsec_tunnels": [],
    "ike_gateways": [],
    "ike_crypto_profiles": [],
    "ipsec_crypto_profiles": []
  },
  "mobile_users": {
    "infrastructure_settings": {},
    "gp_gateways": [],
    "gp_portals": []
  },
  "hip": {
    "hip_objects": [],
    "hip_profiles": []
  },
  "regions": {
    "locations": [],
    "bandwidth_allocations": []
  }
}
```

---

## Rate Limiting

The API client enforces rate limiting to prevent overwhelming the Prisma Access API.

### Configuration

- **Default Rate Limit:** 45 requests per minute (90% of 50 req/min for safety)
- **Time Window:** 60 seconds
- **Per-Endpoint Limits:** Configurable via `set_endpoint_limit()`

### Rate Limiter Class

The `RateLimiter` class (in `prisma.api_utils`) provides:
- Thread-safe rate limiting
- Per-endpoint rate limits
- Automatic wait insertion
- Logging of rate limit events

**Example:**
```python
# Initialize client with custom rate limit
client = PrismaAccessAPIClient(
    tsg_id=tsg_id,
    api_user=api_user,
    api_secret=api_secret,
    rate_limit=45  # 45 requests per minute
)

# Set custom endpoint limit
client.rate_limiter.set_endpoint_limit("ipsec/tunnels", max_requests=30)
```

### Rate Limiting Behavior

When rate limit is approached:
1. Rate limiter calculates required wait time
2. Logs wait message: `"Rate limit approaching for endpoint X, waiting Y seconds"`
3. Sleeps for calculated duration
4. Resumes API call

---

## Error Handling

Infrastructure capture includes comprehensive error handling:

### Graceful Degradation

- **404 Errors:** Endpoint unavailable → Return empty list/dict
- **Network Errors:** Connection issues → Return empty list/dict and log error
- **Timeout Errors:** Request timeout → Return empty list/dict and log error
- **Malformed Responses:** Invalid data → Return empty list/dict and log error

### Example Error Handling

```python
try:
    hip_config = capture.capture_hip_objects_and_profiles()
    # May return empty lists if endpoint unavailable
    if not hip_config['hip_objects']:
        logger.info("HIP objects unavailable or empty")
except Exception as e:
    logger.error(f"Error capturing HIP config: {e}")
    # Capture continues with other components
```

### Logging

All infrastructure capture operations log:
- Success: `INFO` level with counts
- Warnings: `WARNING` level for unavailable endpoints
- Errors: `ERROR` level with exception details

---

## Examples

### Example 1: Capture All Infrastructure

```python
from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.infrastructure_capture import InfrastructureCapture

# Initialize
client = PrismaAccessAPIClient(
    tsg_id="tsg-1234567890",
    api_user="client-id",
    api_secret="client-secret"
)

capture = InfrastructureCapture(client)

# Capture everything
infra = capture.capture_all_infrastructure()

# Process results
print(f"Remote Networks: {len(infra.get('remote_networks', []))}")
print(f"Service Connections: {len(infra.get('service_connections', []))}")
print(f"IPsec Tunnels: {len(infra.get('ipsec_tunnels', {}).get('ipsec_tunnels', []))}")
print(f"GP Gateways: {len(infra.get('mobile_users', {}).get('gp_gateways', []))}")
print(f"Regions: {len(infra.get('regions', {}).get('locations', []))}")
```

### Example 2: Selective Infrastructure Capture

```python
# Capture only network infrastructure
infra = capture.capture_all_infrastructure(
    include_remote_networks=True,
    include_service_connections=True,
    include_ipsec_tunnels=True,
    include_mobile_users=False,
    include_hip=False,
    include_regions=False
)
```

### Example 3: Full Configuration Pull with Infrastructure

```python
from prisma.pull.pull_orchestrator import PullOrchestrator

orchestrator = PullOrchestrator(client)

config = orchestrator.pull_complete_configuration(
    include_folders=True,
    include_snippets=True,
    include_rules=True,
    include_objects=True,
    include_profiles=True,
    # Infrastructure
    include_remote_networks=True,
    include_service_connections=True,
    include_ipsec_tunnels=True,
    include_mobile_users=True,
    include_hip=True,
    include_regions=True,
    # Custom applications
    application_names=["MyCustomApp"]
)

# Save to file
from config.storage.json_storage import JSONConfigStorage

storage = JSONConfigStorage()
storage.save_config(config, "full_config.json")
```

### Example 4: Error-Resilient Capture

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

capture = InfrastructureCapture(client)

# Capture with error handling
try:
    infra = capture.capture_all_infrastructure()
    
    # Check what was successfully captured
    components = []
    if infra.get('remote_networks'):
        components.append("Remote Networks")
    if infra.get('service_connections'):
        components.append("Service Connections")
    if infra.get('ipsec_tunnels', {}).get('ipsec_tunnels'):
        components.append("IPsec Infrastructure")
    if infra.get('mobile_users', {}).get('gp_gateways'):
        components.append("Mobile Users")
    if infra.get('regions', {}).get('locations'):
        components.append("Regions")
    
    logger.info(f"Successfully captured: {', '.join(components)}")
    
except Exception as e:
    logger.error(f"Infrastructure capture failed: {e}")
```

---

## See Also

- [Infrastructure Capture Guide](INFRASTRUCTURE_CAPTURE_GUIDE.md)
- [User Documentation](../docs/USAGE.md)
- [API Endpoints Reference](../prisma/api_endpoints.py)
- [Configuration Schema](../config/schema/config_schema_v2.py)

---

**End of API Reference**
