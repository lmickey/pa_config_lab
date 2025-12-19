"""
JSON Schema validation for Prisma Access configuration files.

This module provides validation functions using the jsonschema library
for comprehensive validation of configuration files.
"""

import json
from typing import Dict, Any, List, Tuple, Optional
import sys

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

from .config_schema_v2 import CONFIG_SCHEMA_V2, validate_config_structure


class SchemaValidationError(Exception):
    """Custom exception for schema validation errors."""
    pass


def validate_config(config: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str]]:
    """
    Validate a configuration dictionary against the schema.
    
    Args:
        config: Configuration dictionary to validate
        schema: Optional custom schema (defaults to CONFIG_SCHEMA_V2)
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if schema is None:
        schema = CONFIG_SCHEMA_V2
    
    errors = []
    
    # Basic structure validation (always available)
    is_valid, error_msg = validate_config_structure(config)
    if not is_valid:
        errors.append(error_msg)
        return False, errors
    
    # Full JSON Schema validation if available
    if JSONSCHEMA_AVAILABLE:
        try:
            validator = Draft7Validator(schema)
            validation_errors = list(validator.iter_errors(config))
            
            if validation_errors:
                for error in validation_errors:
                    error_path = " -> ".join(str(p) for p in error.path)
                    errors.append(f"{error_path}: {error.message}")
                return False, errors
            
            return True, []
            
        except Exception as e:
            errors.append(f"Schema validation error: {str(e)}")
            return False, errors
    else:
        # If jsonschema not available, only basic validation
        return True, []


def validate_config_file(file_path: str) -> Tuple[bool, List[str]]:
    """
    Validate a configuration JSON file.
    
    Args:
        file_path: Path to JSON configuration file
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return validate_config(config)
        
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {str(e)}"]
    except FileNotFoundError:
        return False, [f"File not found: {file_path}"]
    except Exception as e:
        return False, [f"Error reading file: {str(e)}"]


def check_schema_version(config: Dict[str, Any]) -> Optional[str]:
    """
    Check the schema version of a configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Schema version string or None if not found
    """
    metadata = config.get("metadata", {})
    return metadata.get("version")


def is_v2_config(config: Dict[str, Any]) -> bool:
    """
    Check if configuration is v2.0 format.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if v2.0 format, False otherwise
    """
    version = check_schema_version(config)
    if version:
        return version.startswith("2.")
    return False


def is_legacy_config(config: Dict[str, Any]) -> bool:
    """
    Check if configuration is legacy format (has fwData/paData but no metadata).
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if legacy format, False otherwise
    """
    has_metadata = "metadata" in config
    has_fwdata = "fwData" in config
    has_padata = "paData" in config
    
    # Legacy format has fwData/paData but no metadata
    if not has_metadata and (has_fwdata or has_padata):
        return True
    
    # Also check if it's a v2 config with legacy data
    if has_metadata and has_fwdata:
        version = check_schema_version(config)
        if version and version.startswith("2."):
            # v2 config can have legacy data for compatibility
            return False
    
    return False


def get_validation_summary(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary of configuration validation status.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary with validation summary
    """
    is_valid, errors = validate_config(config)
    version = check_schema_version(config)
    
    summary = {
        "is_valid": is_valid,
        "schema_version": version,
        "is_v2": is_v2_config(config),
        "is_legacy": is_legacy_config(config),
        "error_count": len(errors),
        "errors": errors
    }
    
    # Count configuration items
    if is_v2_config(config):
        security_policies = config.get("security_policies", {})
        folders = security_policies.get("folders", [])
        snippets = security_policies.get("snippets", [])
        
        summary["folder_count"] = len(folders)
        summary["snippet_count"] = len(snippets)
        
        # Count rules
        rule_count = 0
        for folder in folders:
            rule_count += len(folder.get("security_rules", []))
        for snippet in snippets:
            rule_count += len(snippet.get("security_rules", []))
        
        summary["security_rule_count"] = rule_count
    
    return summary
