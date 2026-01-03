"""
Encryption utilities for configuration files.

Provides AES-256 encryption with PBKDF2 key derivation for secure
configuration storage, plus configurable password validation.
"""

import os
import json
import base64
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Encryption constants
PBKDF2_ITERATIONS = 480000  # NIST SP 800-132 recommendation
SALT_SIZE = 16  # 128 bits
KEY_SIZE = 32   # 256 bits

# File format identifiers
FORMAT_ENCRYPTED_V1 = "pac_encrypted_v1"
FORMAT_PLAIN = "pac_plain_v1"
FILE_EXTENSION_ENCRYPTED = ".pac"
FILE_EXTENSION_PLAIN = ".json"


@dataclass
class PasswordPolicy:
    """Configurable password policy settings."""
    
    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_characters: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Additional options
    disallow_common_passwords: bool = True
    disallow_username_in_password: bool = True
    
    # Common passwords to reject (basic list)
    common_passwords: List[str] = field(default_factory=lambda: [
        "password", "123456", "12345678", "qwerty", "abc123",
        "monkey", "1234567", "letmein", "trustno1", "dragon",
        "baseball", "iloveyou", "master", "sunshine", "ashley",
        "passw0rd", "shadow", "123123", "654321", "superman",
        "admin", "administrator", "root", "welcome", "login",
    ])


class PasswordValidator:
    """Validates passwords against configurable policy."""
    
    def __init__(self, policy: Optional[PasswordPolicy] = None):
        """
        Initialize password validator.
        
        Args:
            policy: Password policy to enforce (uses defaults if None)
        """
        self.policy = policy or PasswordPolicy()
    
    def validate(self, password: str, username: str = "") -> Tuple[bool, List[str]]:
        """
        Validate a password against the policy.
        
        Args:
            password: Password to validate
            username: Optional username to check against
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Length checks
        if len(password) < self.policy.min_length:
            errors.append(f"Password must be at least {self.policy.min_length} characters")
        
        if len(password) > self.policy.max_length:
            errors.append(f"Password must be at most {self.policy.max_length} characters")
        
        # Character requirements
        if self.policy.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.policy.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.policy.require_digit and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if self.policy.require_special:
            # Escape special regex characters
            escaped_chars = re.escape(self.policy.special_characters)
            if not re.search(f'[{escaped_chars}]', password):
                errors.append(f"Password must contain at least one special character ({self.policy.special_characters})")
        
        # Common password check
        if self.policy.disallow_common_passwords:
            if password.lower() in [p.lower() for p in self.policy.common_passwords]:
                errors.append("Password is too common, please choose a stronger password")
        
        # Username check
        if self.policy.disallow_username_in_password and username:
            if username.lower() in password.lower():
                errors.append("Password cannot contain your username")
        
        return len(errors) == 0, errors
    
    def get_strength(self, password: str) -> Tuple[str, int]:
        """
        Calculate password strength.
        
        Args:
            password: Password to evaluate
            
        Returns:
            Tuple of (strength_label, strength_score 0-100)
        """
        score = 0
        
        # Length score (up to 30 points)
        length_score = min(len(password) * 2, 30)
        score += length_score
        
        # Character variety (up to 40 points)
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[^a-zA-Z\d]', password):
            score += 10
        
        # Bonus for mixing (up to 30 points)
        unique_chars = len(set(password))
        variety_score = min(unique_chars * 2, 30)
        score += variety_score
        
        # Determine label
        if score < 30:
            label = "Very Weak"
        elif score < 50:
            label = "Weak"
        elif score < 70:
            label = "Fair"
        elif score < 85:
            label = "Strong"
        else:
            label = "Very Strong"
        
        return label, min(score, 100)
    
    def get_requirements_text(self) -> str:
        """Get human-readable password requirements."""
        requirements = [f"• At least {self.policy.min_length} characters"]
        
        if self.policy.require_uppercase:
            requirements.append("• At least one uppercase letter (A-Z)")
        if self.policy.require_lowercase:
            requirements.append("• At least one lowercase letter (a-z)")
        if self.policy.require_digit:
            requirements.append("• At least one digit (0-9)")
        if self.policy.require_special:
            requirements.append(f"• At least one special character ({self.policy.special_characters})")
        
        return "\n".join(requirements)


def _derive_key(password: str, salt: bytes = None) -> Tuple[Fernet, bytes]:
    """
    Derive encryption key from password using PBKDF2.
    
    Args:
        password: Password string
        salt: Optional salt (generated if None)
        
    Returns:
        Tuple of (Fernet cipher, salt)
    """
    if salt is None:
        salt = os.urandom(SALT_SIZE)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
    return Fernet(key), salt


def encrypt_config(
    config_data: Dict[str, Any],
    password: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Encrypt configuration data with password.
    
    Args:
        config_data: Configuration dictionary to encrypt
        password: Encryption password
        metadata: Optional metadata to include (stored unencrypted)
        
    Returns:
        Encrypted configuration dictionary
    """
    # Serialize config to JSON
    config_json = json.dumps(config_data, indent=2)
    config_bytes = config_json.encode('utf-8')
    
    # Derive key and encrypt
    cipher, salt = _derive_key(password)
    encrypted_data = cipher.encrypt(config_bytes)
    
    # Build encrypted file structure
    now = datetime.now().isoformat()
    
    result = {
        "format": FORMAT_ENCRYPTED_V1,
        "encryption": {
            "algorithm": "AES-256-Fernet",
            "kdf": "PBKDF2-SHA256",
            "iterations": PBKDF2_ITERATIONS,
            "salt": base64.b64encode(salt).decode('utf-8'),
        },
        "metadata": {
            "name": metadata.get("name", "Untitled Configuration") if metadata else "Untitled Configuration",
            "description": metadata.get("description", "") if metadata else "",
            "created_at": metadata.get("created_at", now) if metadata else now,
            "modified_at": now,
            "version": "1.0",
            # Additional metadata
            "source_tenant": metadata.get("source_tenant") if metadata else None,
            "source_tsg": metadata.get("source_tsg") if metadata else None,
            "pull_date": metadata.get("pull_date") if metadata else None,
            "item_count": metadata.get("item_count") if metadata else None,
            "folders_count": metadata.get("folders_count") if metadata else None,
            "snippets_count": metadata.get("snippets_count") if metadata else None,
        },
        "data": base64.b64encode(encrypted_data).decode('utf-8'),
    }
    
    logger.info(f"Encrypted configuration: {result['metadata']['name']}")
    return result


def decrypt_config(encrypted_data: Dict[str, Any], password: str) -> Dict[str, Any]:
    """
    Decrypt configuration data with password.
    
    Args:
        encrypted_data: Encrypted configuration dictionary
        password: Decryption password
        
    Returns:
        Decrypted configuration dictionary
        
    Raises:
        ValueError: If format is invalid or decryption fails
    """
    # Validate format
    if encrypted_data.get("format") != FORMAT_ENCRYPTED_V1:
        raise ValueError(f"Unknown format: {encrypted_data.get('format')}")
    
    # Extract encryption parameters
    encryption = encrypted_data.get("encryption", {})
    salt = base64.b64decode(encryption.get("salt", ""))
    
    if not salt:
        raise ValueError("Missing encryption salt")
    
    # Derive key and decrypt
    try:
        cipher, _ = _derive_key(password, salt)
        encrypted_bytes = base64.b64decode(encrypted_data.get("data", ""))
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        config_data = json.loads(decrypted_bytes.decode('utf-8'))
        
        logger.info(f"Decrypted configuration: {encrypted_data.get('metadata', {}).get('name', 'Unknown')}")
        return config_data
        
    except InvalidToken:
        raise ValueError("Incorrect password or corrupted data")
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")


def is_encrypted_file(file_path: str) -> bool:
    """
    Check if a file is encrypted.
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        True if file is encrypted
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data.get("format") == FORMAT_ENCRYPTED_V1
    except Exception:
        return False


def get_config_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata from a configuration file without decrypting.
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        Metadata dictionary or None if file is invalid
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Encrypted format
        if data.get("format") == FORMAT_ENCRYPTED_V1:
            metadata = data.get("metadata", {})
            metadata["encrypted"] = True
            return metadata
        
        # Plain format - extract from config
        if data.get("format") == FORMAT_PLAIN:
            metadata = data.get("metadata", {})
            metadata["encrypted"] = False
            return metadata
        
        # Legacy plain JSON format
        metadata = data.get("metadata", {})
        metadata["encrypted"] = False
        metadata["name"] = metadata.get("name", os.path.basename(file_path))
        return metadata
        
    except Exception as e:
        logger.warning(f"Failed to read metadata from {file_path}: {e}")
        return None


def save_config_to_file(
    file_path: str,
    config_data: Dict[str, Any],
    password: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Save configuration to file, optionally encrypted.
    
    Args:
        file_path: Path to save file
        config_data: Configuration dictionary
        password: If provided, encrypt the file
        metadata: Optional metadata to include
    """
    if password:
        # Encrypted save
        encrypted = encrypt_config(config_data, password, metadata)
        with open(file_path, 'w') as f:
            json.dump(encrypted, f, indent=2)
    else:
        # Plain save
        output = {
            "format": FORMAT_PLAIN,
            "metadata": metadata or {},
            "config": config_data,
        }
        with open(file_path, 'w') as f:
            json.dump(output, f, indent=2)
    
    logger.info(f"Saved configuration to {file_path}")


def load_config_from_file(file_path: str, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from file, decrypting if necessary.
    
    Args:
        file_path: Path to configuration file
        password: Password for encrypted files
        
    Returns:
        Configuration dictionary
        
    Raises:
        ValueError: If file is encrypted but no password provided
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    if data.get("format") == FORMAT_ENCRYPTED_V1:
        if not password:
            raise ValueError("File is encrypted, password required")
        return decrypt_config(data, password)
    
    if data.get("format") == FORMAT_PLAIN:
        return data.get("config", {})
    
    # Legacy format - return as-is
    return data


def generate_filename(name: str, encrypted: bool = True) -> str:
    """
    Generate a filename from a friendly name.
    
    Args:
        name: Friendly configuration name
        encrypted: Whether file will be encrypted
        
    Returns:
        Sanitized filename with timestamp
    """
    # Sanitize name
    sanitized = name.lower()
    sanitized = re.sub(r'[^a-z0-9\s-]', '', sanitized)  # Remove special chars
    sanitized = re.sub(r'\s+', '-', sanitized)  # Replace spaces with hyphens
    sanitized = re.sub(r'-+', '-', sanitized)  # Collapse multiple hyphens
    sanitized = sanitized.strip('-')[:50]  # Limit length
    
    if not sanitized:
        sanitized = "config"
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Add extension
    ext = FILE_EXTENSION_ENCRYPTED if encrypted else FILE_EXTENSION_PLAIN
    
    return f"{sanitized}_{timestamp}{ext}"
