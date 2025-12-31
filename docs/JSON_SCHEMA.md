# JSON Schema Reference

## Overview

The Prisma Access configuration uses a versioned JSON schema (v2.0) for storing comprehensive configurations. This document provides a complete reference for the schema structure.

## Schema Version

- **Current Version**: 2.0.0
- **Format**: JSON Schema (JSON Schema Draft 7)
- **Validation**: Uses `jsonschema` library

## Top-Level Structure

```json
{
  "metadata": {...},
  "infrastructure": {...},
  "security_policies": {...}
}
```

## Metadata Section

```json
{
  "metadata": {
    "version": "2.0.0",              // Required: Schema version
    "created": "2024-01-01T00:00:00Z", // Required: ISO 8601 timestamp
    "source_tenant": "tsg-1234567890", // Optional: Source TSG ID
    "source_type": "scm",             // Optional: "scm" or "panorama"
    "description": "...",             // Optional: Human-readable description
    "updated": "2024-01-01T00:00:00Z" // Optional: Last update timestamp
  }
}
```

### Metadata Fields

- **version** (required): Schema version string matching pattern `^2\.\d+\.\d+$`
- **created** (required): ISO 8601 timestamp when configuration was created
- **source_tenant** (optional): Source tenant identifier
- **source_type** (optional): Management type - `"scm"` or `"panorama"`
- **description** (optional): Human-readable description
- **updated** (optional): ISO 8601 timestamp of last update

## Infrastructure Section

```json
{
  "infrastructure": {
    "shared_infrastructure_settings": {},  // Optional: Shared settings
    "mobile_agent": {},                    // Optional: Mobile agent config
    "service_connections": [],             // Optional: Service connections
    "remote_networks": []                  // Optional: Remote networks
  }
}
```

All infrastructure fields are optional objects or arrays.

## Security Policies Section

### Folders

```json
{
  "security_policies": {
    "folders": [
      {
        "name": "Shared",                    // Required: Folder name
        "path": "/config/security-policy/folders/Shared", // Required: Folder path
        "is_default": false,                 // Optional: Default folder flag
        "security_rules": [],                // Optional: Array of security rules
        "objects": {
          "address_objects": [],
          "address_groups": [],
          "service_objects": [],
          "service_groups": [],
          "applications": [],
          "application_filters": [],
          "application_groups": [],
          "application_signatures": [],
          "url_filtering_categories": [],
          "external_dynamic_lists": [],
          "fqdn_objects": []
        },
        "profiles": {
          "authentication_profiles": [],
          "security_profiles": {
            "antivirus": [],
            "anti_spyware": [],
            "vulnerability": [],
            "url_filtering": [],
            "file_blocking": [],
            "wildfire": [],
            "data_filtering": []
          },
          "decryption_profiles": {
            "ssl_forward_proxy": [],
            "ssl_inbound_inspection": [],
            "ssl_ssh_proxy": []
          }
        },
        "parent_dependencies": {
          "address_objects": [],
          "address_groups": [],
          "service_objects": [],
          "service_groups": [],
          "applications": [],
          "security_rules": [],
          "authentication_profiles": [],
          "security_profiles": [],
          "decryption_profiles": []
        }
      }
    ]
  }
}
```

### Folder Fields

- **name** (required): Folder name string
- **path** (required): Folder path string
- **is_default** (optional): Boolean indicating if folder is a default folder
- **security_rules** (optional): Array of security rule objects
- **objects** (optional): Object containing various object types
- **profiles** (optional): Object containing profile types
- **parent_dependencies** (optional): Object containing dependencies from parent folders

### Objects Structure

All object types are arrays of objects:

- `address_objects`: Address object definitions
- `address_groups`: Address group definitions (reference address objects)
- `service_objects`: Service object definitions
- `service_groups`: Service group definitions (reference service objects)
- `applications`: Application definitions
- `application_filters`: Application filter definitions
- `application_groups`: Application group definitions
- `application_signatures`: Application signature definitions
- `url_filtering_categories`: URL filtering category definitions
- `external_dynamic_lists`: External dynamic list definitions
- `fqdn_objects`: FQDN object definitions

### Profiles Structure

#### Authentication Profiles

Array of authentication profile objects.

#### Security Profiles

Object with profile type arrays:

- `antivirus`: Antivirus profile array
- `anti_spyware`: Anti-spyware profile array
- `vulnerability`: Vulnerability protection profile array
- `url_filtering`: URL filtering profile array
- `file_blocking`: File blocking profile array
- `wildfire`: WildFire profile array
- `data_filtering`: Data filtering profile array

#### Decryption Profiles

Object with profile type arrays:

- `ssl_forward_proxy`: SSL forward proxy profile array
- `ssl_inbound_inspection`: SSL inbound inspection profile array
- `ssl_ssh_proxy`: SSL SSH proxy profile array

### Parent Dependencies

Tracks items from parent folders that are referenced but not created in this folder:

- Arrays for each object/profile/rule type
- Used for dependency tracking
- Not included in folder's own configuration

### Snippets

```json
{
  "security_policies": {
    "snippets": [
      {
        "name": "snippet-name",              // Required: Snippet name
        "path": "/config/security-policy/snippets/snippet-name", // Required: Path
        "is_default": false,                  // Optional: Default snippet flag
        "security_rules": []                   // Optional: Referenced rules
      }
    ]
  }
}
```

## Validation

### Schema Validation

```python
from config.schema.schema_validator import validate_config

is_valid, errors = validate_config(config)
if not is_valid:
    for error in errors:
        print(f"Validation error: {error}")
```

### Version Checking

```python
from config.schema.schema_validator import is_v2_config, check_schema_version

# Check if config is v2.0
if is_v2_config(config):
    version = check_schema_version(config)
    print(f"Config version: {version}")
```

## Example Configuration

See `tests/conftest.py` for a complete example configuration with all fields populated.

## Schema Evolution

The schema is versioned to support future changes:

- **v2.0.0**: Current version with comprehensive security policy support
- Future versions may add new fields while maintaining backward compatibility

## See Also

- [Comprehensive Configuration Guide](README_COMPREHENSIVE_CONFIG.md)
- [Migration Guide](MIGRATION_GUIDE.md) - Migrating from legacy formats
