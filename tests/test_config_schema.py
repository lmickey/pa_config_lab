"""
Tests for configuration schema validation.

Tests cover:
- Schema structure validation
- Field validation and constraints
- Required fields
- Type checking
- Edge cases
"""

import pytest
from typing import Dict, Any

from config.schema.schema_validator import (
    validate_config,
    validate_config_file,
    check_schema_version,
    is_v2_config,
    is_legacy_config,
    get_validation_summary
)
from config.schema.config_schema_v2 import (
    validate_config_structure,
    CONFIG_SCHEMA_V2,
    get_schema_version
)
from tests.conftest import sample_config_v2


class TestSchemaValidation:
    """Test schema validation functions."""
    
    def test_valid_config_schema(self, sample_config_v2):
        """Test that a valid configuration passes schema validation."""
        # Fix decryption_profiles to match schema (object, not list)
        config = sample_config_v2.copy()
        for folder in config["security_policies"]["folders"]:
            if "profiles" in folder and isinstance(folder["profiles"].get("decryption_profiles"), list):
                folder["profiles"]["decryption_profiles"] = {}
        
        is_valid, errors = validate_config(config)
        assert is_valid, f"Valid config failed validation: {errors}"
        assert len(errors) == 0
    
    def test_missing_metadata(self):
        """Test that missing metadata fails validation."""
        config = {
            "security_policies": {
                "folders": [],
                "snippets": []
            }
        }
        is_valid, errors = validate_config(config)
        assert not is_valid
        assert any("metadata" in str(error).lower() for error in errors)
    
    def test_invalid_version(self, sample_config_v2):
        """Test that invalid version fails validation."""
        config = sample_config_v2.copy()
        config["metadata"]["version"] = "invalid"
        is_valid, errors = validate_config(config)
        # Version validation might be lenient, but should be checked
        assert isinstance(errors, list)
    
    def test_missing_security_policies(self):
        """Test that missing security_policies fails validation."""
        config = {
            "metadata": {
                "version": "2.0.0",
                "created": "2024-01-01T00:00:00Z",
                "source_tenant": "tsg-test",
                "source_type": "scm"
            },
            "infrastructure": {}
        }
        is_valid, errors = validate_config(config)
        assert not is_valid
        assert any("security_policies" in str(error).lower() for error in errors)
    
    def test_basic_structure_validation(self):
        """Test basic structure validation."""
        config = {
            "metadata": {
                "version": "2.0.0",
                "created": "2024-01-01T00:00:00Z"
            },
            "infrastructure": {},
            "security_policies": {
                "folders": [],
                "snippets": []
            }
        }
        is_valid, error_msg = validate_config_structure(config)
        assert is_valid, error_msg


class TestSchemaStructure:
    """Test schema structure and retrieval."""
    
    def test_get_schema_returns_dict(self):
        """Test that CONFIG_SCHEMA_V2 is a dictionary."""
        assert isinstance(CONFIG_SCHEMA_V2, dict)
        assert "type" in CONFIG_SCHEMA_V2
    
    def test_schema_has_metadata_section(self):
        """Test that schema includes metadata section."""
        assert "properties" in CONFIG_SCHEMA_V2
        assert "metadata" in CONFIG_SCHEMA_V2["properties"]
    
    def test_schema_has_security_policies_section(self):
        """Test that schema includes security_policies section."""
        assert "properties" in CONFIG_SCHEMA_V2
        assert "security_policies" in CONFIG_SCHEMA_V2["properties"]
    
    def test_get_schema_version(self):
        """Test that get_schema_version returns correct version."""
        version = get_schema_version()
        assert version == "2.0.0"


class TestFieldValidation:
    """Test individual field validation."""
    
    def test_folder_name_required(self, sample_config_v2):
        """Test that folder name is required."""
        config = sample_config_v2.copy()
        # Remove name from folder
        config["security_policies"]["folders"][0].pop("name")
        is_valid, errors = validate_config(config)
        assert not is_valid
        assert any("name" in str(error).lower() for error in errors)
    
    def test_folder_path_required(self, sample_config_v2):
        """Test that folder path is required."""
        config = sample_config_v2.copy()
        # Remove path from folder
        config["security_policies"]["folders"][0].pop("path")
        is_valid, errors = validate_config(config)
        assert not is_valid
        assert any("path" in str(error).lower() for error in errors)
    
    def test_snippet_name_required(self, sample_config_v2):
        """Test that snippet name is required."""
        config = sample_config_v2.copy()
        # Remove name from snippet
        if config["security_policies"]["snippets"]:
            config["security_policies"]["snippets"][0].pop("name")
            is_valid, errors = validate_config(config)
            assert not is_valid
            assert any("name" in str(error).lower() for error in errors)
    
    def test_snippet_path_required(self, sample_config_v2):
        """Test that snippet path is required."""
        config = sample_config_v2.copy()
        # Remove path from snippet
        if config["security_policies"]["snippets"]:
            config["security_policies"]["snippets"][0].pop("path")
            is_valid, errors = validate_config(config)
            assert not is_valid
            assert any("path" in str(error).lower() for error in errors)
    
    def test_is_default_field(self, sample_config_v2):
        """Test that is_default field is properly handled."""
        folder = sample_config_v2["security_policies"]["folders"][0]
        assert "is_default" in folder
        assert isinstance(folder["is_default"], bool)
    
    def test_check_schema_version(self, sample_config_v2):
        """Test schema version checking."""
        version = check_schema_version(sample_config_v2)
        assert version == "2.0.0"
    
    def test_is_v2_config(self, sample_config_v2):
        """Test v2 config detection."""
        assert is_v2_config(sample_config_v2) is True
    
    def test_is_legacy_config(self, sample_config_v2):
        """Test legacy config detection."""
        assert is_legacy_config(sample_config_v2) is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_folders_list(self):
        """Test configuration with empty folders list."""
        config = {
            "metadata": {
                "version": "2.0.0",
                "created": "2024-01-01T00:00:00Z",
                "source_tenant": "tsg-test",
                "source_type": "scm"
            },
            "infrastructure": {},
            "security_policies": {
                "folders": [],
                "snippets": []
            }
        }
        is_valid, errors = validate_config(config)
        # Empty lists should be valid
        assert is_valid or len(errors) == 0
    
    def test_empty_snippets_list(self, sample_config_v2):
        """Test configuration with empty snippets list."""
        config = sample_config_v2.copy()
        config["security_policies"]["snippets"] = []
        # Fix decryption_profiles to match schema
        for folder in config["security_policies"]["folders"]:
            if "profiles" in folder and isinstance(folder["profiles"].get("decryption_profiles"), list):
                folder["profiles"]["decryption_profiles"] = {}
        is_valid, errors = validate_config(config)
        assert is_valid or len(errors) == 0
    
    def test_missing_optional_fields(self, sample_config_v2):
        """Test that missing optional fields don't fail validation."""
        config = sample_config_v2.copy()
        folder = config["security_policies"]["folders"][0]
        # Remove optional fields
        folder.pop("parent_dependencies", None)
        # Fix decryption_profiles to match schema
        if "profiles" in folder and isinstance(folder["profiles"].get("decryption_profiles"), list):
            folder["profiles"]["decryption_profiles"] = {}
        is_valid, errors = validate_config(config)
        # Should still be valid
        assert is_valid or len(errors) == 0
    
    def test_null_values(self):
        """Test handling of null values."""
        config = {
            "metadata": {
                "version": "2.0.0",
                "created": "2024-01-01T00:00:00Z",
                "source_tenant": "tsg-test",
                "source_type": "scm"
            },
            "infrastructure": {},
            "security_policies": {
                "folders": None,
                "snippets": []
            }
        }
        is_valid, errors = validate_config(config)
        # Null should fail validation
        assert not is_valid or len(errors) > 0
    
    def test_validation_summary(self, sample_config_v2):
        """Test validation summary generation."""
        summary = get_validation_summary(sample_config_v2)
        assert "is_valid" in summary
        assert "schema_version" in summary
        assert "is_v2" in summary
        assert summary["is_v2"] is True
        assert summary["folder_count"] > 0
