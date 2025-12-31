# Comprehensive Configuration Capture - User Guide

## Overview

The Prisma Access Comprehensive Configuration Capture system enables you to extract, store, and migrate complete configurations from Prisma Access SCM-managed tenants. This guide covers all features and workflows.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Core Concepts](#core-concepts)
3. [Configuration Structure](#configuration-structure)
4. [Pull Workflow](#pull-workflow)
5. [Push Workflow](#push-workflow)
6. [Default Detection](#default-detection)
7. [Dependency Management](#dependency-management)
8. [Storage Formats](#storage-formats)
9. [CLI Usage](#cli-usage)
10. [Best Practices](#best-practices)

## Getting Started

### Prerequisites

- Python 3.8+
- Prisma Access SCM tenant credentials
- API Client ID and Secret with appropriate permissions

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd pa_config_lab

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration Setup

Set up API credentials as environment variables:

```bash
export PRISMA_TSG_ID="your-tsg-id"
export PRISMA_API_USER="your-api-client-id"
export PRISMA_API_SECRET="your-api-client-secret"
```

Or use the configuration file:

```bash
python get_settings.py
```

## Core Concepts

### Folders vs Snippets

- **Folders**: Containers for security policies (rules, objects, profiles)
- **Snippets**: Metadata containers that reference rules from folders
- Both are captured, but folders contain the actual configuration

### Default Configurations

- Automatically detected default configurations (e.g., "Shared" folder, "any" objects)
- Can be excluded from exports to focus on custom configurations
- Documented in configuration metadata

### Dependencies

- Objects referenced by rules (address groups → address objects)
- Profiles referenced by rules (authentication, security, decryption)
- Parent-level dependencies (items from parent folders)

## Configuration Structure

The configuration follows a hierarchical JSON structure:

```json
{
  "metadata": {
    "version": "2.0.0",
    "created": "2024-01-01T00:00:00Z",
    "source_tenant": "tsg-1234567890",
    "source_type": "scm"
  },
  "infrastructure": {
    "service_connections": [],
    "remote_networks": []
  },
  "security_policies": {
    "folders": [
      {
        "name": "Shared",
        "path": "/config/security-policy/folders/Shared",
        "is_default": false,
        "security_rules": [],
        "objects": {
          "address_objects": [],
          "address_groups": []
        },
        "profiles": {
          "authentication_profiles": [],
          "security_profiles": {},
          "decryption_profiles": {}
        },
        "parent_dependencies": {
          "address_objects": [],
          "security_rules": []
        }
      }
    ],
    "snippets": []
  }
}
```

See [JSON Schema Reference](JSON_SCHEMA.md) for complete schema documentation.

## Pull Workflow

### Basic Pull

Pull configuration from a tenant:

```python
from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.config_pull import pull_configuration

# Initialize API client
client = PrismaAccessAPIClient(
    tsg_id="tsg-1234567890",
    api_user="client-id",
    api_secret="client-secret"
)

# Pull all folders
config = pull_configuration(
    client,
    folder_names=None,  # None = all folders
    include_snippets=True
)
```

### Selective Pull

Pull specific folders or exclude defaults:

```python
# Pull specific folders
config = pull_configuration(
    client,
    folder_names=["Shared", "Mobile Users"],
    include_snippets=False
)

# Pull with default exclusion (via CLI)
# Use pull_cli.py for interactive selection
```

### Saving Configuration

```python
from config.storage.json_storage import save_config_json

# Save unencrypted JSON
save_config_json(config, "backup.json", encrypt=False)

# Save encrypted JSON
from config.storage.json_storage import derive_key
from cryptography.fernet import Fernet
cipher = derive_key("your-password")
save_config_json(config, "backup.json", cipher=cipher, encrypt=True)
```

## Push Workflow

### Basic Push

Push configuration to a target tenant:

```python
from prisma.push.config_push import push_configuration
from config.storage.json_storage import load_config_json

# Load configuration
config = load_config_json("backup.json")

# Initialize target API client
target_client = PrismaAccessAPIClient(
    tsg_id="target-tsg-id",
    api_user="target-client-id",
    api_secret="target-client-secret"
)

# Push configuration
result = push_configuration(
    target_client,
    config,
    folder_names=None,  # None = all folders
    dry_run=True  # Set to False to actually push
)
```

### Conflict Resolution

The system detects conflicts (existing items with same name):

```python
from prisma.push.conflict_resolver import ConflictResolver, ConflictResolution

resolver = ConflictResolver()

# Detect conflicts
conflicts = resolver.detect_conflicts(config, target_client)

# Set resolution strategy
resolver.set_default_strategy(ConflictResolution.SKIP)  # or OVERWRITE, RENAME

# Push with conflict resolution
result = push_configuration(
    target_client,
    config,
    conflict_strategy=ConflictResolution.SKIP
)
```

## Default Detection

### Automatic Detection

Defaults are automatically detected during pull:

- Default folders: "Shared", "Service Connections", etc.
- Default objects: "any", "any-tcp", etc.
- Default profiles: "default", "best-practice", etc.
- Default rules: Deny-all rules with default patterns

### Filtering Defaults

```python
from config.defaults.default_detector import DefaultDetector

detector = DefaultDetector()

# Detect defaults in configuration
defaults = detector.detect_defaults_in_config(config)

# Filter out defaults
filtered_config = detector.filter_defaults(config, include_defaults=False)
```

## Dependency Management

### Dependency Resolution

The system automatically resolves dependencies:

```python
from prisma.dependencies.dependency_resolver import DependencyResolver

resolver = DependencyResolver()

# Build dependency graph
resolver.build_dependency_graph(config)

# Validate dependencies
validation = resolver.validate_dependencies(config)

# Get resolution order (for push)
order = resolver.get_resolution_order(config)
```

### Parent-Level Dependencies

Items from parent folders are tracked separately:

```json
{
  "parent_dependencies": {
    "address_objects": [],
    "address_groups": [],
    "security_rules": [],
    "authentication_profiles": [],
    "security_profiles": {},
    "decryption_profiles": {}
  }
}
```

## Storage Formats

### JSON Format (v2.0)

- Human-readable
- Versioned schema
- Supports encryption
- Enables manual editing

### Pickle Format (Legacy)

- Backward compatible
- Automatic migration to JSON
- See [Migration Guide](MIGRATION_GUIDE.md)

## CLI Usage

### Pull CLI

```bash
python cli/pull_cli.py
```

Interactive menu for:
- Selecting folders to pull
- Selecting snippets (with default inclusion option)
- Saving configuration

### Application Search CLI

```bash
python cli/application_search.py
```

Search for applications by name or category.

## Best Practices

### 1. Regular Backups

- Pull configurations regularly
- Store backups with timestamps
- Keep multiple backup versions

### 2. Test Before Push

- Always use `dry_run=True` first
- Review conflicts before pushing
- Test in non-production tenants

### 3. Dependency Awareness

- Understand parent-level dependencies
- Validate dependencies before push
- Resolve conflicts appropriately

### 4. Default Handling

- Exclude defaults for cleaner exports
- Document defaults separately if needed
- Be aware of default dependencies

### 5. Error Handling

- Check pull/push results
- Review error logs
- Handle partial failures gracefully

## See Also

- [Pull & Push Guide](PULL_PUSH_GUIDE.md) - Detailed workflow guide
- [JSON Schema Reference](JSON_SCHEMA.md) - Complete schema documentation
- [API Reference](API_REFERENCE.md) - API client documentation
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
