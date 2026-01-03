# Configuration File Format

**Version:** 1.0  
**Date:** January 2, 2026

This document defines the JSON file format for saving and loading Prisma Access configurations.

---

## File Format Overview

Configuration files are JSON files with the `.json` extension. They contain:
1. **Metadata** - Source information, version, timestamps
2. **Push History** - Record of all push operations
3. **Folders** - Folder containers with their items
4. **Snippets** - Snippet containers with their items
5. **Infrastructure** - Infrastructure items (Remote Networks, IPsec tunnels, etc.)

---

## File Structure

```json
{
  "version": "3.1.x",
  "format_version": "1.0",
  "metadata": {
    "source_tsg": "1570970024",
    "source_file": null,
    "load_type": "pull",
    "saved_credentials_ref": "SCM Lab",
    "created_at": "2026-01-02T19:00:00Z",
    "modified_at": "2026-01-02T19:30:00Z",
    "description": "Production configuration snapshot"
  },
  "push_history": [
    {
      "timestamp": "2026-01-02T19:15:00Z",
      "destination_tsg": "1234567890",
      "items_pushed": 150,
      "items_created": 145,
      "items_updated": 5,
      "items_failed": 0,
      "status": "success",
      "duration_seconds": 45.2,
      "conflict_strategy": "SKIP"
    }
  ],
  "folders": {
    "Mobile Users": {
      "parent": null,
      "items": [...]
    },
    "Remote Networks": {
      "parent": null,
      "items": [...]
    }
  },
  "snippets": {
    "default": {
      "items": [...]
    }
  },
  "infrastructure": {
    "items": [...]
  },
  "stats": {
    "total_items": 150,
    "items_by_type": {
      "address_object": 45,
      "security_rule": 12,
      ...
    },
    "folders_count": 3,
    "snippets_count": 1,
    "infrastructure_count": 8
  }
}
```

---

## Field Definitions

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Application version that created the file |
| `format_version` | string | Yes | Configuration file format version (currently "1.0") |
| `metadata` | object | Yes | Configuration metadata |
| `push_history` | array | No | History of push operations |
| `folders` | object | Yes | Folder containers and their items |
| `snippets` | object | Yes | Snippet containers and their items |
| `infrastructure` | object | Yes | Infrastructure items |
| `stats` | object | No | Summary statistics (for quick reference) |

### Metadata Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_tsg` | string | No | Source Tenant Service Group ID |
| `source_file` | string | No | Source file path (if loaded from file) |
| `load_type` | string | No | How loaded: "pull", "file", "api" |
| `saved_credentials_ref` | string | No | Reference to saved credentials (tenant name) |
| `created_at` | string | Yes | ISO 8601 timestamp when config was created |
| `modified_at` | string | Yes | ISO 8601 timestamp when config was last modified |
| `description` | string | No | User-provided description |

### Push History Entry

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 timestamp of push operation |
| `destination_tsg` | string | Yes | Destination Tenant Service Group ID |
| `items_pushed` | int | Yes | Total items attempted to push |
| `items_created` | int | Yes | Items successfully created |
| `items_updated` | int | Yes | Items successfully updated |
| `items_failed` | int | Yes | Items that failed to push |
| `status` | string | Yes | "success" or "failure" |
| `duration_seconds` | float | No | Push operation duration |
| `conflict_strategy` | string | No | "SKIP", "OVERWRITE", or "RENAME" |
| `notes` | string | No | Additional notes or error details |

### Folder/Snippet Container

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parent` | string | No | Parent folder name (for hierarchical folders) |
| `items` | array | Yes | Array of ConfigItem objects |

Each item in `items` array is the output of `item.to_dict(include_id=True)`.

### Infrastructure Container

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `items` | array | Yes | Array of infrastructure ConfigItem objects |

---

## ConfigItem Serialization

Each ConfigItem is serialized using its `to_dict(include_id=True)` method. Example:

```json
{
  "id": "abc-123-def-456",
  "name": "web-server",
  "item_type": "address_object",
  "folder": "Mobile Users",
  "ip_netmask": "10.0.1.10/32",
  "description": "Web server in DMZ",
  "tag": ["Production", "DMZ"]
}
```

**Key fields in all items:**
- `id` - Prisma Access object ID (if exists)
- `name` - Object name
- `item_type` - Type identifier for factory deserialization
- `folder` or `snippet` - Location (mutually exclusive for most types)

---

## File Naming Convention

Recommended naming:
```
{source_name}_{timestamp}.json
```

Examples:
- `scm_lab_2026-01-02_19-00-00.json`
- `production_snapshot_2026-01-02.json`
- `mobile_users_config_20260102.json`

---

## Compression

Configuration files can optionally be compressed using gzip:
```
config_file.json.gz
```

The save/load methods automatically detect and handle compressed files.

---

## Validation

When loading a configuration file, the following validations are performed:

1. **Format Version Check:**
   - File `format_version` must be compatible with current version
   - Incompatible versions are rejected

2. **Required Fields:**
   - All required top-level fields must be present
   - All required metadata fields must be present

3. **Item Validation:**
   - Each item must have required fields (`name`, `item_type`)
   - Item type must be registered in `ConfigItemFactory`
   - Each item is validated using its model class validation

4. **Reference Integrity:**
   - Dependencies are checked (optional warning if missing)
   - Folder/snippet references are validated

---

## Partial Loading

If validation errors occur during load, the system supports **partial loading**:

```python
config = Configuration.load_from_file(
    "config.json",
    strict=False,  # Allow partial load
    on_error="warn"  # "warn" or "skip" or "fail"
)
```

- `strict=True`: Fail completely on any error (default)
- `strict=False`: Load valid items, skip invalid ones
- `on_error="warn"`: Log warnings for invalid items
- `on_error="skip"`: Silently skip invalid items
- `on_error="fail"`: Fail on first invalid item

---

## Example: Complete Configuration File

```json
{
  "version": "3.1.154",
  "format_version": "1.0",
  "metadata": {
    "source_tsg": "1570970024",
    "source_file": null,
    "load_type": "pull",
    "saved_credentials_ref": "SCM Lab",
    "created_at": "2026-01-02T19:00:00Z",
    "modified_at": "2026-01-02T19:30:00Z",
    "description": "Production configuration with mobile users and remote networks"
  },
  "push_history": [
    {
      "timestamp": "2026-01-02T19:15:00Z",
      "destination_tsg": "9876543210",
      "items_pushed": 150,
      "items_created": 145,
      "items_updated": 5,
      "items_failed": 0,
      "status": "success",
      "duration_seconds": 45.2,
      "conflict_strategy": "SKIP",
      "notes": "Initial configuration push to DR environment"
    }
  ],
  "folders": {
    "Mobile Users": {
      "parent": null,
      "items": [
        {
          "id": "abc-123",
          "name": "web-server",
          "item_type": "address_object",
          "folder": "Mobile Users",
          "ip_netmask": "10.0.1.10/32",
          "description": "Web server",
          "tag": ["Production"]
        },
        {
          "id": "def-456",
          "name": "Allow-Web",
          "item_type": "security_rule",
          "folder": "Mobile Users",
          "from": ["any"],
          "to": ["any"],
          "source": ["any"],
          "destination": ["web-server"],
          "application": ["web-browsing"],
          "service": ["application-default"],
          "action": "allow"
        }
      ]
    },
    "Remote Networks": {
      "parent": null,
      "items": [
        {
          "id": "ghi-789",
          "name": "qos-high",
          "item_type": "qos_profile",
          "folder": "Remote Networks",
          "class_bandwidth_type": {
            "mbps": {
              "class": [
                {
                  "class_bandwidth": 100,
                  "name": "class1",
                  "priority": "high"
                }
              ]
            }
          }
        }
      ]
    }
  },
  "snippets": {
    "default": {
      "items": [
        {
          "id": "jkl-012",
          "name": "corp-dns",
          "item_type": "address_object",
          "snippet": "default",
          "ip_netmask": "10.0.0.1/32",
          "description": "Corporate DNS server"
        }
      ]
    }
  },
  "infrastructure": {
    "items": [
      {
        "id": "mno-345",
        "name": "HQ-RN",
        "item_type": "remote_network",
        "region": "us-east-1",
        "spn_name": "us-east-1-spn",
        "ipsec_tunnel": "HQ-Tunnel",
        "license_type": "FWAAS-AGGREGATE"
      },
      {
        "id": "pqr-678",
        "name": "HQ-Tunnel",
        "item_type": "ipsec_tunnel",
        "auto_key": {
          "ike_gateway": [
            {
              "name": "HQ-Gateway"
            }
          ],
          "ipsec_crypto_profile": "default"
        },
        "tunnel_monitor": {
          "enable": true,
          "destination_ip": "192.168.1.1"
        }
      },
      {
        "id": "stu-901",
        "name": "HQ-Gateway",
        "item_type": "ike_gateway",
        "peer_address": {
          "ip": "203.0.113.1"
        },
        "authentication": {
          "pre_shared_key": {
            "key": "encrypted_key_here"
          }
        },
        "protocol": {
          "ikev1": {
            "ike_crypto_profile": "default"
          }
        }
      }
    ]
  },
  "stats": {
    "total_items": 7,
    "items_by_type": {
      "address_object": 2,
      "security_rule": 1,
      "qos_profile": 1,
      "remote_network": 1,
      "ipsec_tunnel": 1,
      "ike_gateway": 1
    },
    "folders_count": 2,
    "snippets_count": 1,
    "infrastructure_count": 3
  }
}
```

---

## Backward Compatibility

**Format Version 1.0** is the initial version. Future versions will maintain backward compatibility when possible:

- **Minor changes** (1.0 → 1.1): Add new optional fields, remain compatible
- **Major changes** (1.0 → 2.0): Breaking changes, require migration

The load method will:
- Accept `format_version` 1.x files
- Warn on deprecated fields
- Reject incompatible major versions (2.0+)

---

## Security Considerations

1. **Sensitive Data:**
   - Pre-shared keys and passwords are stored encrypted (as returned by API)
   - Configuration files should be treated as sensitive
   - Recommended to store in encrypted locations

2. **File Permissions:**
   - Save with restricted permissions (0600 on Unix)
   - Verify file ownership before loading

3. **Validation:**
   - Always validate files before loading
   - Reject files with suspicious content
   - Log all load attempts

---

## Performance

**File Size Estimates:**
- Small config (10 items): ~5 KB
- Medium config (100 items): ~50 KB
- Large config (1000 items): ~500 KB

**Load/Save Times:**
- Small: <0.1s
- Medium: <0.5s
- Large: <2s

**Compression:**
- Typical compression ratio: 5-10x
- Large configs: 500 KB → 50-100 KB

---

## Summary

The configuration file format is:
- ✅ **Human-readable** JSON
- ✅ **Self-documenting** with metadata
- ✅ **Versioned** for future compatibility
- ✅ **Comprehensive** includes all data and history
- ✅ **Validated** on load
- ✅ **Flexible** supports partial loading
- ✅ **Efficient** with optional compression

---

*Version 1.0 - January 2, 2026*
