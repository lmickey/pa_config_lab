# API Reference

## Overview

This document provides a complete reference for the Prisma Access API client and all available endpoints.

## API Client

### PrismaAccessAPIClient

Main API client for interacting with Prisma Access SCM API.

#### Initialization

```python
from prisma.api_client import PrismaAccessAPIClient

client = PrismaAccessAPIClient(
    tsg_id="tsg-1234567890",
    api_user="api-client-id",
    api_secret="api-client-secret",
    rate_limit=100,      # Optional: requests per minute (default: 100)
    cache_ttl=300        # Optional: cache TTL in seconds (default: 300)
)
```

#### Authentication

```python
# Automatic authentication on initialization
# Manual authentication
success = client.authenticate()
if success:
    print(f"Token expires at: {client.token_expires}")
```

### API Endpoints

The system uses two API bases:

- **Strata API**: For folders and infrastructure setup
- **SASE API**: For security policies, objects, profiles

#### Endpoint Classes

```python
from prisma.api_endpoints import APIEndpoints

# Get endpoint URLs
folders_url = APIEndpoints.SECURITY_POLICY_FOLDERS
rules_url = APIEndpoints.SECURITY_RULES
addresses_url = APIEndpoints.ADDRESSES
```

## Security Policy Endpoints

### Folders

```python
# List all folders
folders = client.get_security_policy_folders()

# Get specific folder
folder = client.get_security_policy_folder("Shared")
```

### Security Rules

```python
# Get all security rules (with pagination)
rules = client.get_all_security_rules(folder="Shared")

# Get specific rule
rule = client.get_security_rule(rule_id="rule-123")
```

### Snippets

```python
# List snippets
snippets = client.get_security_policy_snippets()

# Get specific snippet
snippet = client.get_security_policy_snippet(snippet_id="snippet-123")
```

## Object Endpoints

### Address Objects

```python
# Get all address objects
addresses = client.get_all_addresses(folder="Shared")

# Get specific address
address = client.get_address(address_id="addr-123")
```

### Address Groups

```python
# Get all address groups
groups = client.get_all_address_groups(folder="Shared")

# Get specific group
group = client.get_address_group(group_id="group-123")
```

### Service Objects

```python
# Get all service objects
services = client.get_all_services(folder="Shared")

# Get specific service
service = client.get_service(service_id="svc-123")
```

### Service Groups

```python
# Get all service groups
groups = client.get_all_service_groups(folder="Shared")

# Get specific group
group = client.get_service_group(group_id="group-123")
```

### Applications

```python
# Get all applications
applications = client.get_all_applications(folder="Shared")

# Get specific application
app = client.get_application(app_id="app-123")
```

## Profile Endpoints

### Authentication Profiles

```python
# Get all authentication profiles
profiles = client.get_all_authentication_profiles(folder="Shared")

# Get specific profile
profile = client.get_authentication_profile(profile_id="auth-123")
```

### Security Profiles

```python
# Get all security profiles (returns dict by type)
profiles = client.get_all_security_profiles(folder="Shared")
# Returns: {
#   "antivirus": [...],
#   "anti_spyware": [...],
#   "vulnerability": [...],
#   ...
# }

# Get specific profile type
antivirus = client.get_security_profiles("antivirus", folder="Shared")
```

### Decryption Profiles

```python
# Get all decryption profiles
profiles = client.get_decryption_profiles(folder="Shared")

# Get specific profile
profile = client.get_decryption_profile(profile_id="decrypt-123")
```

## Infrastructure Endpoints

### Service Connections

```python
# Get all service connections
connections = client.get_all_service_connections()

# Get specific connection
connection = client.get_service_connection(connection_id="conn-123")
```

### Remote Networks

```python
# Get all remote networks
networks = client.get_all_remote_networks()

# Get specific network
network = client.get_remote_network(network_id="net-123")
```

## Request Features

### Rate Limiting

Automatic rate limiting (default: 100 requests/minute):

```python
client = PrismaAccessAPIClient(
    tsg_id="...",
    api_user="...",
    api_secret="...",
    rate_limit=100  # Adjust as needed
)
```

### Caching

Response caching for GET requests (default: 5 minutes):

```python
client = PrismaAccessAPIClient(
    tsg_id="...",
    api_user="...",
    api_secret="...",
    cache_ttl=300  # Cache TTL in seconds
)

# Disable cache for specific request
data = client._make_request("GET", url, use_cache=False)
```

### Pagination

Automatic pagination handling:

```python
# get_all_* methods handle pagination automatically
all_rules = client.get_all_security_rules(folder="Shared")
# Returns all rules across all pages
```

### Error Handling

Automatic retry on failures:

```python
# Uses @retry_on_failure decorator
# Retries up to 3 times with exponential backoff
data = client.get_all_security_rules(folder="Shared")
```

## Advanced Usage

### Custom Requests

```python
# Make custom API request
response = client._make_request(
    method="GET",
    url="https://api.sase.paloaltonetworks.com/sse/config/v1/custom-endpoint",
    params={"folder": "Shared"},
    use_cache=True
)
```

### Folder Encoding

Folder names are automatically encoded:

```python
# Spaces become %20 (not +)
# "Access Agent" -> "Access%20Agent"
encoded = client._encode_folder_name("Access Agent")
```

## Error Handling

### Authentication Errors

```python
try:
    client.authenticate()
except Exception as e:
    print(f"Authentication failed: {e}")
    # Check credentials and permissions
```

### API Errors

```python
try:
    rules = client.get_all_security_rules(folder="Shared")
except Exception as e:
    print(f"API error: {e}")
    # Check folder name, permissions, network connectivity
```

## See Also

- [Comprehensive Configuration Guide](README_COMPREHENSIVE_CONFIG.md)
- [Pull & Push Guide](PULL_PUSH_GUIDE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
