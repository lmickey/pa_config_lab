# Migration Guide

## Overview

This guide covers migrating configurations from legacy pickle format to the new JSON format (v2.0).

## Migration Paths

### 1. Pickle to JSON Migration

Migrate from encrypted pickle files (`*-fwdata.bin`) to JSON format.

#### Automatic Migration

```python
from config.storage.config_migration import migrate_config_file

# Migrate single file
success = migrate_config_file(
    source_path="config-fwdata.bin",
    dest_path="config.json",  # Optional: auto-generated if None
    cipher=None,  # Will prompt for password
    preserve_legacy=True,  # Keep fwData/paData in v2 format
    backup=True  # Create backup of source file
)
```

#### Batch Migration

```python
from config.storage.config_migration import batch_migrate_configs

results = batch_migrate_configs(
    source_dir=".",
    dest_dir=None,  # Defaults to source_dir
    pattern="*-fwdata.bin",
    preserve_legacy=True,
    backup=True
)

for file, success in results.items():
    print(f"{file}: {'Success' if success else 'Failed'}")
```

### 2. Format Detection

The system automatically detects configuration format:

```python
from config.storage.pickle_compat import detect_config_format

format_type = detect_config_format("config.bin")
# Returns: 'pickle', 'json', or 'unknown'
```

### 3. Auto-Load

Load configuration regardless of format:

```python
from config.storage.pickle_compat import load_config_auto

config = load_config_auto("config.bin")  # Works with both formats
```

## Migration Process

### Step 1: Identify Legacy Files

```python
from config.storage.json_storage import list_config_files

# List all config files
files = list_config_files()

# Filter pickle files
pickle_files = [f for f in files if f.endswith('.bin')]
```

### Step 2: Backup Original Files

Always backup before migration:

```python
import shutil

for file in pickle_files:
    backup_path = file + '.backup'
    shutil.copy2(file, backup_path)
    print(f"Backed up: {backup_path}")
```

### Step 3: Migrate Files

```python
from config.storage.config_migration import migrate_config_file
from config.storage.json_storage import derive_key
from cryptography.fernet import Fernet

# Get password for decryption
password = input("Enter encryption password: ")
cipher = derive_key(password)

for file in pickle_files:
    success = migrate_config_file(
        source_path=file,
        cipher=cipher,
        backup=True
    )
    if success:
        print(f"Migrated: {file}")
```

### Step 4: Verify Migration

```python
from config.storage.json_storage import load_config_json
from config.schema.schema_validator import validate_config, is_v2_config

# Load migrated config
config = load_config_json("config.json", encrypted=False)

# Verify it's v2.0 format
if is_v2_config(config):
    print("Migration successful - v2.0 format")
    
    # Validate schema
    is_valid, errors = validate_config(config)
    if is_valid:
        print("Schema validation passed")
    else:
        print("Schema validation errors:", errors)
```

## Format Differences

### Legacy Pickle Format

- Encrypted binary format
- Structure: `{"fwData": {...}, "paData": {...}}`
- Not human-readable
- Difficult to edit manually

### New JSON Format (v2.0)

- Human-readable JSON
- Hierarchical structure with metadata
- Schema-validated
- Supports encryption (optional)
- Easy to edit manually

## Breaking Changes

### Structure Changes

1. **Top-level keys**: Changed from `fwData`/`paData` to `metadata`/`infrastructure`/`security_policies`
2. **Security policies**: New hierarchical structure with folders and snippets
3. **Metadata**: Added version, timestamps, source information

### Backward Compatibility

The system maintains backward compatibility:

- Can load legacy pickle files
- Automatic conversion to v2.0 format
- Legacy data preserved in `infrastructure` section if `preserve_legacy=True`

## Migration Checklist

- [ ] Identify all legacy configuration files
- [ ] Create backups of original files
- [ ] Test migration on one file first
- [ ] Verify migrated configuration loads correctly
- [ ] Validate schema compliance
- [ ] Test pull/push workflows with migrated config
- [ ] Update scripts/tools to use new format
- [ ] Archive or remove legacy files (after verification)

## Troubleshooting

### Password Issues

If you forget the encryption password:

1. Check if password is stored securely
2. Legacy files cannot be decrypted without password
3. Consider re-pulling configuration from source if password is lost

### Format Detection Failures

If format detection fails:

```python
# Manually specify format
from config.storage.pickle_compat import load_pickle_config
from config.storage.json_storage import load_config_json

# Try pickle format
try:
    config = load_pickle_config("file.bin", cipher=cipher)
except:
    # Try JSON format
    config = load_config_json("file.bin", encrypted=False)
```

### Schema Validation Errors

If migrated config fails validation:

1. Check schema version
2. Review validation errors
3. Manually fix structure issues
4. Re-validate

## Best Practices

1. **Always backup** before migration
2. **Test migration** on one file first
3. **Verify functionality** after migration
4. **Keep backups** until migration is verified
5. **Document passwords** securely
6. **Test pull/push** with migrated configs

## See Also

- [Comprehensive Configuration Guide](README_COMPREHENSIVE_CONFIG.md)
- [JSON Schema Reference](JSON_SCHEMA.md)
- [Storage Functions](../config/storage/json_storage.py)
