"""
Comprehensive JSON validation with security checks.

This module provides strict validation of JSON configuration data
to prevent injection attacks, resource exhaustion, and malformed data.
"""

import json
from typing import Dict, Any
from jsonschema import validate, ValidationError


class ConfigurationValidator:
    """Secure configuration validator with comprehensive checks."""

    MAX_CONFIG_SIZE = 100_000_000  # 100MB
    MAX_STRING_LENGTH = 50_000  # 50KB per string
    MAX_ARRAY_LENGTH = 50_000  # 50K items per array
    MAX_NESTING_DEPTH = 20  # Maximum object nesting
    MAX_OBJECT_KEYS = 10_000  # Maximum keys in a single object

    @staticmethod
    def validate_json_structure(
        data: str, schema: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate JSON structure and size limits.

        Args:
            data: JSON string to validate
            schema: Optional JSON schema for validation

        Returns:
            Parsed and validated configuration dictionary

        Raises:
            ValueError: If validation fails

        Example:
            >>> json_data = '{"metadata": {"version": "2.0.0"}}'
            >>> config = ConfigurationValidator.validate_json_structure(json_data)
        """
        # Check size
        if len(data) > ConfigurationValidator.MAX_CONFIG_SIZE:
            raise ValueError(
                f"Configuration exceeds maximum size "
                f"({ConfigurationValidator.MAX_CONFIG_SIZE} bytes, got {len(data)} bytes)"
            )

        # Parse JSON
        try:
            config = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

        # Validate against schema if provided
        if schema:
            try:
                validate(instance=config, schema=schema)
            except ValidationError as e:
                raise ValueError(f"Configuration schema validation failed: {e.message}")

        # Check nesting depth
        max_depth = ConfigurationValidator._get_max_depth(config)
        if max_depth > ConfigurationValidator.MAX_NESTING_DEPTH:
            raise ValueError(
                f"Configuration exceeds maximum nesting depth "
                f"({ConfigurationValidator.MAX_NESTING_DEPTH}, got {max_depth})"
            )

        # Validate string lengths
        ConfigurationValidator._validate_strings(config)

        # Validate array lengths
        ConfigurationValidator._validate_arrays(config)

        # Validate object sizes
        ConfigurationValidator._validate_objects(config)

        return config

    @staticmethod
    def validate_json_bytes(
        data: bytes, schema: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate JSON from bytes.

        Args:
            data: JSON bytes to validate
            schema: Optional JSON schema

        Returns:
            Parsed and validated configuration

        Raises:
            ValueError: If validation fails
        """
        # Check size before decoding
        if len(data) > ConfigurationValidator.MAX_CONFIG_SIZE:
            raise ValueError(
                f"Data exceeds maximum size ({ConfigurationValidator.MAX_CONFIG_SIZE} bytes)"
            )

        try:
            json_str = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid UTF-8 encoding: {e}")

        return ConfigurationValidator.validate_json_structure(json_str, schema)

    @staticmethod
    def _get_max_depth(obj: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth."""
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(
                ConfigurationValidator._get_max_depth(v, current_depth + 1)
                for v in obj.values()
            )
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(
                ConfigurationValidator._get_max_depth(item, current_depth + 1)
                for item in obj
            )
        else:
            return current_depth

    @staticmethod
    def _validate_strings(obj: Any, path: str = "root"):
        """Validate all string lengths in configuration."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if (
                    isinstance(key, str)
                    and len(key) > ConfigurationValidator.MAX_STRING_LENGTH
                ):
                    raise ValueError(
                        f"String key too long at {path}.{key[:50]}... "
                        f"({len(key)} > {ConfigurationValidator.MAX_STRING_LENGTH})"
                    )
                ConfigurationValidator._validate_strings(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                ConfigurationValidator._validate_strings(item, f"{path}[{i}]")
        elif isinstance(obj, str):
            if len(obj) > ConfigurationValidator.MAX_STRING_LENGTH:
                raise ValueError(
                    f"String value too long at {path} "
                    f"({len(obj)} > {ConfigurationValidator.MAX_STRING_LENGTH})"
                )

    @staticmethod
    def _validate_arrays(obj: Any, path: str = "root"):
        """Validate all array lengths in configuration."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                ConfigurationValidator._validate_arrays(value, f"{path}.{key}")
        elif isinstance(obj, list):
            if len(obj) > ConfigurationValidator.MAX_ARRAY_LENGTH:
                raise ValueError(
                    f"Array too long at {path} "
                    f"({len(obj)} > {ConfigurationValidator.MAX_ARRAY_LENGTH} items)"
                )
            for i, item in enumerate(obj):
                ConfigurationValidator._validate_arrays(item, f"{path}[{i}]")

    @staticmethod
    def _validate_objects(obj: Any, path: str = "root"):
        """Validate object sizes (number of keys)."""
        if isinstance(obj, dict):
            if len(obj) > ConfigurationValidator.MAX_OBJECT_KEYS:
                raise ValueError(
                    f"Object too large at {path} "
                    f"({len(obj)} > {ConfigurationValidator.MAX_OBJECT_KEYS} keys)"
                )
            for key, value in obj.items():
                ConfigurationValidator._validate_objects(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                ConfigurationValidator._validate_objects(item, f"{path}[{i}]")
