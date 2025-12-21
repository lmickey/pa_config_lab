"""
JSON-based storage functions for Prisma Access configuration.

This module provides functions to save and load configurations in JSON format,
replacing the previous pickle-based storage system.

Security: Uses PBKDF2-HMAC-SHA256 with 480,000 iterations for key derivation,
compliant with NIST SP 800-132 recommendations (2024).
"""

import json
import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from cryptography.fernet import Fernet
import getpass

from ..schema.config_schema_v2 import create_empty_config_v2, CONFIG_SCHEMA_V2
from ..schema.schema_validator import validate_config, is_v2_config
from .crypto_utils import (
    derive_key_secure,
    derive_key_legacy,
    encrypt_data,
    decrypt_data,
    is_encrypted_with_version,
)
from .path_validator import PathValidator
from .json_validator import ConfigurationValidator


def derive_key(password: str) -> Tuple[Fernet, bytes]:
    """
    Derive a Fernet key from a password using secure PBKDF2.

    This function uses PBKDF2-HMAC-SHA256 with 480,000 iterations
    as recommended by NIST SP 800-132 (2024).

    Args:
        password: Password string

    Returns:
        Tuple of (Fernet cipher instance, salt bytes)

    Note:
        For backward compatibility with legacy files, use
        derive_key_legacy() from crypto_utils module.
    """
    return derive_key_secure(password)


def encrypt_json_data(data: str, cipher: Fernet, salt: bytes) -> bytes:
    """
    Encrypt JSON string data with salt.

    Args:
        data: JSON string to encrypt
        cipher: Fernet cipher instance
        salt: Salt bytes used for key derivation

    Returns:
        Encrypted bytes (salt + version marker + encrypted data)
    """
    encrypted = encrypt_data(data.encode("utf-8"), cipher, include_version=True)
    # Prepend salt to encrypted data
    return salt + encrypted


def decrypt_json_data(
    encrypted_data: bytes, password: str = None, cipher: Fernet = None
) -> Tuple[str, bytes]:
    """
    Decrypt JSON data, automatically detecting format.

    Args:
        encrypted_data: Encrypted bytes (salt + version + data or legacy format)
        password: Password for decryption (required if cipher not provided)
        cipher: Optional pre-derived cipher (for legacy format)

    Returns:
        Tuple of (decrypted JSON string, salt bytes or None for legacy)

    Raises:
        ValueError: If neither password nor cipher provided
    """
    # Check if this is new format (starts with salt)
    if len(encrypted_data) > 16:
        potential_salt = encrypted_data[:16]
        remaining = encrypted_data[16:]

        # Check if remaining data has version marker
        if is_encrypted_with_version(remaining):
            # New format with salt
            if cipher is None:
                if password is None:
                    raise ValueError("Password required for decryption")
                cipher, _ = derive_key_secure(password, salt=potential_salt)

            decrypted_bytes = decrypt_data(remaining, cipher)
            return decrypted_bytes.decode("utf-8"), potential_salt

    # Legacy format without salt
    if cipher is None:
        if password is None:
            raise ValueError("Password or cipher required for decryption")
        cipher = derive_key_legacy(password)

    decrypted_bytes = cipher.decrypt(encrypted_data)
    return decrypted_bytes.decode("utf-8"), None


def save_config_json(
    config: Dict[str, Any],
    file_path: str,
    cipher: Optional[Fernet] = None,
    encrypt: bool = True,
    pretty: bool = True,
    validate: bool = True,
) -> bool:
    """
    Save configuration to JSON file with security validation.

    Args:
        config: Configuration dictionary
        file_path: Path to save file
        cipher: Optional Fernet cipher for encryption
        encrypt: Whether to encrypt the file
        pretty: Whether to format JSON with indentation
        validate: Whether to validate configuration structure

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If path validation or JSON validation fails
    """
    try:
        # Validate file path
        safe_path = PathValidator.validate_config_path(
            file_path, must_exist=False, must_be_file=True, create_parents=True
        )

        # Update metadata timestamp
        if "metadata" in config:
            config["metadata"]["updated"] = datetime.utcnow().isoformat() + "Z"

        # Convert to JSON string
        if pretty:
            json_str = json.dumps(config, indent=2, ensure_ascii=False)
        else:
            json_str = json.dumps(config, ensure_ascii=False)

        # Validate JSON structure if requested
        if validate:
            ConfigurationValidator.validate_json_structure(
                json_str, schema=CONFIG_SCHEMA_V2
            )

        # Encrypt if requested
        if encrypt:
            if cipher is None:
                password = getpass.getpass("Enter password for encryption: ")
                cipher, salt = derive_key(password)
            else:
                # If cipher provided, generate a salt
                # (caller should have provided salt too, but generate as fallback)
                import os

                salt = os.urandom(16)

            encrypted_data = encrypt_json_data(json_str, cipher, salt)

            # Save encrypted file
            with open(safe_path, "wb") as f:
                f.write(encrypted_data)
        else:
            # Save unencrypted JSON
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(json_str)

        return True

    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False


def load_config_json(
    file_path: str,
    cipher: Optional[Fernet] = None,
    encrypted: Optional[bool] = None,
    validate: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Load configuration from JSON file with security validation.

    Args:
        file_path: Path to configuration file
        cipher: Optional Fernet cipher for decryption
        encrypted: Whether file is encrypted (None = auto-detect)
        validate: Whether to validate JSON structure and size limits

    Returns:
        Configuration dictionary or None if error

    Raises:
        ValueError: If path validation or JSON validation fails
    """
    try:
        # Validate file path
        safe_path = PathValidator.validate_config_path(
            file_path, must_exist=True, must_be_file=True
        )
        # Auto-detect encryption by trying to read as binary first
        if encrypted is None:
            try:
                with open(safe_path, "rb") as f:
                    data = f.read()
                # Try to decode as UTF-8
                try:
                    decoded = data.decode("utf-8").strip()
                    # Check if it starts with valid JSON characters
                    if decoded.startswith("{") or decoded.startswith("["):
                        # Try to parse as JSON to confirm it's not encrypted
                        try:
                            json.loads(decoded)
                            encrypted = False
                        except json.JSONDecodeError:
                            # Can decode but not valid JSON - likely encrypted
                            encrypted = True
                    else:
                        # Doesn't start with JSON - likely encrypted
                        encrypted = True
                except UnicodeDecodeError:
                    # Can't decode as UTF-8 - definitely encrypted
                    encrypted = True
            except Exception:
                encrypted = False

        if encrypted:
            # Read encrypted file
            with open(safe_path, "rb") as f:
                encrypted_data = f.read()

            # Get password if cipher not provided
            password = None
            if cipher is None:
                password = getpass.getpass("Enter password for decryption: ")

            # Decrypt (auto-detects format)
            json_str, salt = decrypt_json_data(
                encrypted_data, password=password, cipher=cipher
            )
        else:
            # Read unencrypted file
            with open(safe_path, "r", encoding="utf-8") as f:
                json_str = f.read()

        # Validate JSON structure if requested
        if validate:
            config = ConfigurationValidator.validate_json_structure(
                json_str, schema=CONFIG_SCHEMA_V2
            )
        else:
            # Parse JSON without validation
            config = json.loads(json_str)

        # Validate if v2 config
        if is_v2_config(config):
            is_valid, errors = validate_config(config)
            if not is_valid:
                print("Warning: Configuration validation errors:")
                for error in errors:
                    print(f"  - {error}")

        return config

    except FileNotFoundError:
        print(f"Configuration file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in configuration file: {e}")
        return None
    except ValueError as e:
        print(f"Validation error: {e}")
        return None
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None


def get_config_file_path(config_name: str, base_dir: Optional[str] = None) -> str:
    """
    Get the standard file path for a configuration.

    Args:
        config_name: Configuration name
        base_dir: Base directory (defaults to current directory)

    Returns:
        Full file path
    """
    if base_dir is None:
        base_dir = os.getcwd()

    # Normalize config name
    normalized_name = config_name.strip().lower().replace(" ", "_")
    file_name = f"{normalized_name}-config.json"

    return os.path.join(base_dir, file_name)


def list_config_files(
    base_dir: Optional[str] = None, pattern: str = "*-config.json"
) -> list[str]:
    """
    List all configuration JSON files in a directory.

    Args:
        base_dir: Base directory (defaults to current directory)
        pattern: File pattern to match

    Returns:
        List of file paths
    """
    if base_dir is None:
        base_dir = os.getcwd()

    import glob

    full_pattern = os.path.join(base_dir, pattern)
    return glob.glob(full_pattern)


def create_new_config(
    config_name: str,
    source_tenant: Optional[str] = None,
    source_type: str = "scm",
    description: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new empty v2.0 configuration.

    Args:
        config_name: Name for the configuration
        source_tenant: Source tenant identifier
        source_type: Source type ('scm' or 'panorama')
        description: Optional description
        file_path: Optional file path (auto-generated if not provided)

    Returns:
        New configuration dictionary
    """
    config = create_empty_config_v2(
        source_tenant=source_tenant,
        source_type=source_type,
        description=description or f"Configuration: {config_name}",
    )

    return config
