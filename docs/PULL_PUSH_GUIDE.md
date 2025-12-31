# Pull & Push Workflow Guide

## Overview

This guide provides detailed instructions for pulling configurations from Prisma Access tenants and pushing them to target tenants.

## Pull Workflow

### Step 1: Initialize API Client

```python
from prisma.api_client import PrismaAccessAPIClient

client = PrismaAccessAPIClient(
    tsg_id="tsg-1234567890",
    api_user="your-api-client-id",
    api_secret="your-api-client-secret"
)
```

### Step 2: Discover Available Resources

```python
from prisma.pull.folder_capture import FolderCapture
from prisma.pull.snippet_capture import SnippetCapture

folder_capture = FolderCapture(client)
snippet_capture = SnippetCapture(client)

# List folders
folders = folder_capture.list_folders_for_capture(include_defaults=True)
print("Available folders:", [f["name"] for f in folders])

# List snippets
snippets = snippet_capture.discover_snippets()
print("Available snippets:", [s["name"] for s in snippets])
```

### Step 3: Pull Configuration

#### Option A: Pull All Folders

```python
from prisma.pull.config_pull import pull_configuration

config = pull_configuration(
    client,
    folder_names=None,  # None = all folders
    include_snippets=True,
    include_defaults=False  # Exclude default folders
)
```

#### Option B: Pull Specific Folders

```python
config = pull_configuration(
    client,
    folder_names=["Shared", "Mobile Users"],
    include_snippets=False
)
```

#### Option C: Using CLI

```bash
python cli/pull_cli.py
```

Interactive menu for selecting folders and snippets.

### Step 4: Save Configuration

```python
from config.storage.json_storage import save_config_json

# Save unencrypted (for testing)
save_config_json(config, "backup.json", encrypt=False)

# Save encrypted
from config.storage.json_storage import derive_key
cipher = derive_key("your-password")
save_config_json(config, "backup.json", cipher=cipher, encrypt=True)
```

## Push Workflow

### Step 1: Load Configuration

```python
from config.storage.json_storage import load_config_json

# Load unencrypted
config = load_config_json("backup.json", encrypted=False)

# Load encrypted
from config.storage.json_storage import derive_key
cipher = derive_key("your-password")
config = load_config_json("backup.json", cipher=cipher, encrypted=True)
```

### Step 2: Validate Configuration

```python
from prisma.push.push_validator import PushValidator

validator = PushValidator()
target_client = PrismaAccessAPIClient(...)

validation = validator.validate_configuration(config, target_client)

if not validation.get("valid"):
    print("Validation errors:", validation.get("errors"))
    # Fix errors before pushing
```

### Step 3: Detect Conflicts

```python
from prisma.push.conflict_resolver import ConflictResolver

resolver = ConflictResolver()
conflicts = resolver.detect_conflicts(config, target_client)

if conflicts.get("has_conflicts"):
    print(f"Found {conflicts['conflict_count']} conflicts")
    for conflict in conflicts["conflicts"]:
        print(f"  - {conflict['type']}: {conflict['name']} in {conflict['folder']}")
```

### Step 4: Resolve Conflicts

```python
from prisma.push.conflict_resolver import ConflictResolution

# Set default strategy
resolver.set_default_strategy(ConflictResolution.SKIP)  # Skip conflicting items
# or
resolver.set_default_strategy(ConflictResolution.OVERWRITE)  # Replace existing
# or
resolver.set_default_strategy(ConflictResolution.RENAME)  # Create with new name
```

### Step 5: Push Configuration

#### Dry Run (Recommended First)

```python
from prisma.push.config_push import push_configuration

result = push_configuration(
    target_client,
    config,
    folder_names=None,  # None = all folders
    dry_run=True  # Don't actually push
)

print("Dry run result:", result)
```

#### Actual Push

```python
result = push_configuration(
    target_client,
    config,
    folder_names=["Shared"],  # Push specific folders
    dry_run=False,
    conflict_strategy=ConflictResolution.SKIP
)

if result.get("success"):
    print("Push completed successfully!")
    print("Stats:", result.get("stats"))
else:
    print("Push failed:", result.get("message"))
```

## Complete Example

### Pull → Modify → Push

```python
from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.config_pull import pull_configuration
from prisma.push.config_push import push_configuration
from prisma.push.conflict_resolver import ConflictResolution
from config.storage.json_storage import save_config_json, load_config_json

# 1. Pull from source
source_client = PrismaAccessAPIClient(
    tsg_id="source-tsg-id",
    api_user="source-client-id",
    api_secret="source-client-secret"
)

config = pull_configuration(
    source_client,
    folder_names=["Shared"],
    include_snippets=False
)

# 2. Save backup
save_config_json(config, "backup.json", encrypt=False)

# 3. Modify configuration (example: add a rule)
config["security_policies"]["folders"][0]["security_rules"].append({
    "name": "New Rule",
    "action": "allow",
    "source": ["any"],
    "destination": ["any"],
    "application": ["any"],
    "service": ["any"]
})

# 4. Push to target
target_client = PrismaAccessAPIClient(
    tsg_id="target-tsg-id",
    api_user="target-client-id",
    api_secret="target-client-secret"
)

# Validate first
from prisma.push.push_validator import PushValidator
validator = PushValidator()
validation = validator.validate_configuration(config, target_client)

if validation.get("valid"):
    # Dry run
    result = push_configuration(
        target_client,
        config,
        dry_run=True,
        conflict_strategy=ConflictResolution.SKIP
    )
    
    if result.get("success"):
        # Actual push
        result = push_configuration(
            target_client,
            config,
            dry_run=False,
            conflict_strategy=ConflictResolution.SKIP
        )
        print("Push completed:", result)
```

## Conflict Resolution Strategies

### SKIP (Default)

Skip conflicting items - don't push them:

```python
result = push_configuration(
    client,
    config,
    conflict_strategy=ConflictResolution.SKIP
)
```

**Use when**: You want to preserve existing configuration and only add new items.

### OVERWRITE

Replace existing items with new configuration:

```python
result = push_configuration(
    client,
    config,
    conflict_strategy=ConflictResolution.OVERWRITE
)
```

**Use when**: You want to update existing items with new values.

### RENAME

Create items with modified names:

```python
result = push_configuration(
    client,
    config,
    conflict_strategy=ConflictResolution.RENAME
)
```

**Use when**: You want to keep both old and new versions.

## Dependency Handling

### Automatic Resolution

Dependencies are automatically resolved during push:

1. Objects are pushed before groups that reference them
2. Profiles are pushed before rules that reference them
3. Parent-level dependencies are tracked separately

### Manual Validation

```python
from prisma.dependencies.dependency_resolver import DependencyResolver

resolver = DependencyResolver()
validation = resolver.validate_dependencies(config)

if not validation.get("valid"):
    print("Missing dependencies:", validation.get("missing_dependencies"))
    # Fix missing dependencies before pushing
```

## Error Handling

### Check Push Results

```python
result = push_configuration(client, config)

if not result.get("success"):
    print("Push failed:", result.get("message"))
    print("Errors:", result.get("stats", {}).get("errors", []))
    
    # Check conflicts
    if "conflicts" in result:
        print("Conflicts:", result["conflicts"])
```

### Partial Failures

The system continues on errors:

```python
stats = result.get("stats", {})
print(f"Objects pushed: {stats.get('objects_pushed', 0)}")
print(f"Rules pushed: {stats.get('rules_pushed', 0)}")
print(f"Errors: {len(stats.get('errors', []))}")
```

## Best Practices

1. **Always use dry_run first** - Test before actual push
2. **Review conflicts** - Understand what will be skipped/overwritten
3. **Validate dependencies** - Ensure all dependencies exist
4. **Backup target** - Pull target configuration before pushing
5. **Test in non-production** - Use test tenants first
6. **Monitor errors** - Check error logs after push

## See Also

- [Comprehensive Configuration Guide](README_COMPREHENSIVE_CONFIG.md)
- [API Reference](API_REFERENCE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
