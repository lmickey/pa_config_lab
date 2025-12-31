"""
Configuration migration utilities.

This module provides utilities for migrating between configuration formats
and versions.
"""

import os
from typing import Dict, Any, Optional

from .pickle_compat import (
    convert_pickle_to_json,
    detect_config_format,
    load_config_auto,
)
from .json_storage import get_config_file_path
from ..schema.schema_validator import (
    is_v2_config,
    is_legacy_config,
    check_schema_version,
)


def migrate_config_file(
    source_path: str,
    dest_path: Optional[str] = None,
    cipher: Optional[Any] = None,
    preserve_legacy: bool = True,
    backup: bool = True,
) -> bool:
    """
    Migrate a configuration file from pickle to JSON format.

    Args:
        source_path: Path to source configuration file
        dest_path: Path to destination file (auto-generated if None)
        cipher: Optional Fernet cipher
        preserve_legacy: Whether to preserve legacy fwData/paData
        backup: Whether to create backup of source file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Detect source format
        source_format = detect_config_format(source_path)

        if source_format == "json":
            print(f"File is already JSON format: {source_path}")
            return False

        if source_format != "pickle":
            print(f"Unknown or unsupported format: {source_path}")
            return False

        # Generate destination path if not provided
        if dest_path is None:
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            # Remove -fwdata suffix if present
            if base_name.endswith("-fwdata"):
                base_name = base_name[:-7]
            dest_path = get_config_file_path(base_name)

        # Create backup if requested
        if backup:
            backup_path = source_path + ".backup"
            import shutil

            shutil.copy2(source_path, backup_path)
            print(f"Backup created: {backup_path}")

        # Convert
        converted_config = convert_pickle_to_json(
            source_path, dest_path, cipher=cipher, preserve_legacy=preserve_legacy
        )

        if converted_config:
            print("Migration successful!")
            print(f"  Source: {source_path}")
            print(f"  Destination: {dest_path}")
            return True
        else:
            print("Migration failed")
            return False

    except Exception as e:
        print(f"Error during migration: {e}")
        return False


def batch_migrate_configs(
    source_dir: str,
    dest_dir: Optional[str] = None,
    pattern: str = "*-fwdata.bin",
    preserve_legacy: bool = True,
    backup: bool = True,
) -> Dict[str, bool]:
    """
    Migrate multiple configuration files in batch.

    Args:
        source_dir: Source directory
        dest_dir: Destination directory (defaults to source_dir)
        pattern: File pattern to match
        preserve_legacy: Whether to preserve legacy data
        backup: Whether to create backups

    Returns:
        Dictionary mapping file paths to success status
    """
    if dest_dir is None:
        dest_dir = source_dir

    import glob

    full_pattern = os.path.join(source_dir, pattern)
    pickle_files = glob.glob(full_pattern)

    results = {}

    print(f"Found {len(pickle_files)} configuration files to migrate")

    for pickle_file in pickle_files:
        base_name = os.path.splitext(os.path.basename(pickle_file))[0]
        if base_name.endswith("-fwdata"):
            base_name = base_name[:-7]

        json_file = get_config_file_path(base_name, dest_dir)

        print(f"\nMigrating: {os.path.basename(pickle_file)}")
        success = migrate_config_file(
            pickle_file, json_file, preserve_legacy=preserve_legacy, backup=backup
        )

        results[pickle_file] = success

    return results


def upgrade_config_to_latest(
    config: Dict[str, Any], target_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upgrade a configuration to the latest version.

    Args:
        config: Configuration dictionary
        target_version: Target version (defaults to latest)

    Returns:
        Upgraded configuration dictionary
    """
    current_version = check_schema_version(config)

    if current_version and current_version.startswith("2."):
        # Already v2, check if needs upgrade
        if target_version and current_version != target_version:
            # Future: implement version-specific upgrades
            print(
                f"Configuration is version {current_version}, target is {target_version}"
            )
        return config

    # Legacy format - convert to v2
    if is_legacy_config(config):
        from .pickle_compat import convert_to_v2_format

        return convert_to_v2_format(config, preserve_legacy=True)

    # Unknown format
    print(f"Unknown configuration format (version: {current_version})")
    return config


def validate_migration(
    source_path: str, dest_path: str, cipher: Optional[Any] = None
) -> bool:
    """
    Validate that a migration was successful.

    Args:
        source_path: Path to source configuration
        dest_path: Path to migrated configuration
        cipher: Optional cipher for decryption

    Returns:
        True if migration appears valid, False otherwise
    """
    try:
        # Load both configs
        source_config = load_config_auto(source_path, cipher)
        dest_config = load_config_auto(dest_path, cipher)

        if not source_config or not dest_config:
            print("Failed to load one or both configurations")
            return False

        # Check that dest is v2 format
        if not is_v2_config(dest_config):
            print("Destination is not v2 format")
            return False

        # Check that legacy data is preserved
        if "fwData" in source_config:
            if "fwData" not in dest_config:
                print("Warning: fwData not preserved in migration")
                return False

        if "paData" in source_config:
            if "paData" not in dest_config:
                print("Warning: paData not preserved in migration")
                return False

        print("Migration validation passed")
        return True

    except Exception as e:
        print(f"Error validating migration: {e}")
        return False
