"""
JSON-based storage functions for Prisma Access configuration.

This module provides functions to save and load configurations in JSON format,
replacing the previous pickle-based storage system.
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import hashlib
import getpass

from ..schema.config_schema_v2 import create_empty_config_v2, get_schema_version
from ..schema.schema_validator import validate_config, is_v2_config


def derive_key(password: str) -> Fernet:
    """
    Derive a Fernet key from a password.
    
    Args:
        password: Password string
        
    Returns:
        Fernet cipher instance
    """
    hash_bytes = hashlib.sha256(password.encode()).digest()
    key = base64.urlsafe_b64encode(hash_bytes)
    return Fernet(key)


def encrypt_json_data(data: str, cipher: Fernet) -> bytes:
    """
    Encrypt JSON string data.
    
    Args:
        data: JSON string to encrypt
        cipher: Fernet cipher instance
        
    Returns:
        Encrypted bytes
    """
    return cipher.encrypt(data.encode('utf-8'))


def decrypt_json_data(encrypted_data: bytes, cipher: Fernet) -> str:
    """
    Decrypt JSON data.
    
    Args:
        encrypted_data: Encrypted bytes
        cipher: Fernet cipher instance
        
    Returns:
        Decrypted JSON string
    """
    decrypted_bytes = cipher.decrypt(encrypted_data)
    return decrypted_bytes.decode('utf-8')


def save_config_json(
    config: Dict[str, Any],
    file_path: str,
    cipher: Optional[Fernet] = None,
    encrypt: bool = True,
    pretty: bool = True
) -> bool:
    """
    Save configuration to JSON file.
    
    Args:
        config: Configuration dictionary
        file_path: Path to save file
        cipher: Optional Fernet cipher for encryption
        encrypt: Whether to encrypt the file
        pretty: Whether to format JSON with indentation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Update metadata timestamp
        if "metadata" in config:
            config["metadata"]["updated"] = datetime.utcnow().isoformat() + "Z"
        
        # Convert to JSON string
        if pretty:
            json_str = json.dumps(config, indent=2, ensure_ascii=False)
        else:
            json_str = json.dumps(config, ensure_ascii=False)
        
        # Encrypt if requested
        if encrypt:
            if cipher is None:
                password = getpass.getpass("Enter password for encryption: ")
                cipher = derive_key(password)
            
            encrypted_data = encrypt_json_data(json_str, cipher)
            
            # Save encrypted file
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
        else:
            # Save unencrypted JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return True
        
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False


def load_config_json(
    file_path: str,
    cipher: Optional[Fernet] = None,
    encrypted: Optional[bool] = None
) -> Optional[Dict[str, Any]]:
    """
    Load configuration from JSON file.
    
    Args:
        file_path: Path to configuration file
        cipher: Optional Fernet cipher for decryption
        encrypted: Whether file is encrypted (None = auto-detect)
        
    Returns:
        Configuration dictionary or None if error
    """
    try:
        # Auto-detect encryption by trying to read as binary first
        if encrypted is None:
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                # Try to decode as UTF-8, if fails assume encrypted
                try:
                    data.decode('utf-8')
                    encrypted = False
                except UnicodeDecodeError:
                    encrypted = True
            except Exception:
                encrypted = False
        
        if encrypted:
            if cipher is None:
                password = getpass.getpass("Enter password for decryption: ")
                cipher = derive_key(password)
            
            # Read encrypted file
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt
            json_str = decrypt_json_data(encrypted_data, cipher)
        else:
            # Read unencrypted file
            with open(file_path, 'r', encoding='utf-8') as f:
                json_str = f.read()
        
        # Parse JSON
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


def list_config_files(base_dir: Optional[str] = None, pattern: str = "*-config.json") -> list[str]:
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
    file_path: Optional[str] = None
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
        description=description or f"Configuration: {config_name}"
    )
    
    return config
