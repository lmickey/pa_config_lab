# Configuration Model Examples Index

This index provides a quick reference to all example configuration files.

## Objects (`objects/`)

### Addresses

| File | Description | Key Features |
|------|-------------|--------------|
| `address_minimal.json` | Basic address object | Folder-based, ip_netmask, minimal fields |
| `address_full.json` | Complete address object | All metadata, tags, timestamps |
| `address_snippet.json` | Snippet-based address | Shows snippet usage |
| `address_fqdn.json` | FQDN address | Domain-based addressing |
| `address_range.json` | IP range address | IP range format (start-end) |
| `address_group_minimal.json` | Static address group | Static members (dependencies) |
| `address_group_dynamic.json` | Dynamic address group | Tag-based filter |

### Services

| File | Description | Key Features |
|------|-------------|--------------|
| `service_minimal.json` | TCP service | Custom port definition |
| `service_group_minimal.json` | Service group | Multiple service members |

### Applications

| File | Description | Key Features |
|------|-------------|--------------|
| `application_minimal.json` | Custom application | Category/risk attributes |
| `application_group_minimal.json` | Application group | Multiple application members |
| `application_filter_minimal.json` | Application filter | Dynamic filtering by category/risk |

### Schedules

| File | Description | Key Features |
|------|-------------|--------------|
| `schedule_minimal.json` | Recurring schedule | Weekly business hours |
| `schedule_non_recurring.json` | Non-recurring schedule | Specific date ranges |

## Policies (`policies/`)

| File | Description | Key Features |
|------|-------------|--------------|
| `security_rule_minimal.json` | Basic security rule | Minimal required fields |
| `security_rule_full.json` | Complete security rule | Profile groups, metadata, position |
| `security_rule_disabled.json` | Disabled rule | Shows disabled=true |
| `security_rule_with_dependencies.json` | Rule with dependencies | Multiple object references |

## Profiles (`profiles/`)

| File | Description | Key Features |
|------|-------------|--------------|
| `authentication_profile_minimal.json` | SAML auth profile | SAML IdP configuration |
| `decryption_profile_minimal.json` | Decryption profile | TLS version settings |
| `url_filtering_profile_minimal.json` | URL filtering | Block/alert/allow actions |
| `profile_group_minimal.json` | Security profile group | Best-practice example, default flag |
| `hip_profile_minimal.json` | HIP profile | Device compliance |

## Infrastructure (`infrastructure/`)

| File | Description | Key Features |
|------|-------------|--------------|
| `ike_crypto_profile_minimal.json` | IKE crypto profile | Phase 1 encryption |
| `ipsec_crypto_profile_minimal.json` | IPsec crypto profile | Phase 2 encryption |
| `ike_gateway_minimal.json` | IKE gateway | PSK authentication, peer config |
| `ipsec_tunnel_minimal.json` | IPsec tunnel | References IKE gateway & crypto |
| `service_connection_minimal.json` | Service connection | BGP, subnets, dependencies |
| `service_connection_full.json` | Full service connection | Complete BGP config, NAT |
| `agent_profile_minimal.json` | GlobalProtect agent profile | Split tunneling config |

## Usage Patterns

### Testing Basic Parsing
```python
# Use minimal examples
with open('tests/examples/config/models/objects/address_minimal.json') as f:
    config = json.load(f)
```

### Testing Full Feature Support
```python
# Use full examples
with open('tests/examples/config/models/objects/address_full.json') as f:
    config = json.load(f)
```

### Testing Dependencies
```python
# Use examples with dependencies
with open('tests/examples/config/models/policies/security_rule_with_dependencies.json') as f:
    config = json.load(f)
```

### Testing Folder vs Snippet
```python
# Folder-based
with open('tests/examples/config/models/objects/address_minimal.json') as f:
    folder_config = json.load(f)

# Snippet-based
with open('tests/examples/config/models/objects/address_snippet.json') as f:
    snippet_config = json.load(f)
```

## Adding Production Examples

To add examples from your production tenant:

1. **Pull configuration**: Use the Pull workflow to capture config
2. **Sanitize**: Remove sensitive data (IPs, passwords, real names)
3. **Save**: Place in appropriate directory with descriptive name
4. **Document**: Add entry to this index

Example sanitization:
```bash
# Replace real IPs with RFC 5737 test IPs
sed -i 's/real-ip-here/203.0.113.10/g' example.json

# Replace sensitive strings
sed -i 's/"key": ".*"/"key": "********"/g' example.json
```
