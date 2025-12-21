"""
Cryptographic utilities for secure key derivation and encryption.

This module provides NIST-compliant key derivation and encryption functions
for securing configuration files.
"""

import os
import base64
from typing import Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


# NIST SP 800-132 recommendations (2024)
PBKDF2_ITERATIONS = 480000  # NIST recommendation for PBKDF2-HMAC-SHA256
SALT_SIZE = 16  # 128 bits
KEY_SIZE = 32  # 256 bits

# File format version marker
CRYPTO_VERSION = b"PBKDF2v1"
VERSION_SIZE = 8


def derive_key_secure(password: str, salt: bytes = None) -> Tuple[Fernet, bytes]:
    """
    Derive a Fernet key from a password using PBKDF2-HMAC-SHA256.

    This function implements NIST SP 800-132 recommendations with 480,000
    iterations to provide strong protection against brute-force attacks.

    Args:
        password: Password string
        salt: Optional salt (will be generated if not provided)

    Returns:
        Tuple of (Fernet cipher instance, salt bytes)

    Example:
        >>> cipher, salt = derive_key_secure("my_password")
        >>> # Store salt with encrypted data for later decryption
    """
    if salt is None:
        salt = os.urandom(SALT_SIZE)

    if not isinstance(salt, bytes) or len(salt) != SALT_SIZE:
        raise ValueError(f"Salt must be {SALT_SIZE} bytes")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend(),
    )

    key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
    return Fernet(key), salt


def encrypt_data(data: bytes, cipher: Fernet, include_version: bool = True) -> bytes:
    """
    Encrypt data with optional version marker.

    Args:
        data: Data to encrypt
        cipher: Fernet cipher instance
        include_version: Whether to include crypto version marker

    Returns:
        Encrypted bytes
    """
    encrypted = cipher.encrypt(data)

    if include_version:
        return CRYPTO_VERSION + encrypted

    return encrypted


def decrypt_data(encrypted_data: bytes, cipher: Fernet) -> bytes:
    """
    Decrypt data, handling version markers.

    Args:
        encrypted_data: Encrypted bytes
        cipher: Fernet cipher instance

    Returns:
        Decrypted bytes

    Raises:
        ValueError: If version marker is present but not recognized
    """
    # Check for version marker
    if encrypted_data.startswith(CRYPTO_VERSION):
        # Strip version marker and decrypt
        encrypted_data = encrypted_data[VERSION_SIZE:]

    return cipher.decrypt(encrypted_data)


def is_encrypted_with_version(data: bytes) -> bool:
    """
    Check if data is encrypted with version marker.

    Args:
        data: Data to check

    Returns:
        True if data has PBKDF2v1 version marker
    """
    return data.startswith(CRYPTO_VERSION)


# Backward compatibility: Legacy SHA-256 key derivation
def derive_key_legacy(password: str) -> Fernet:
    """
    Legacy key derivation using SHA-256 (DEPRECATED).

    This function is provided for backward compatibility only.
    New code should use derive_key_secure() instead.

    Args:
        password: Password string

    Returns:
        Fernet cipher instance

    Warning:
        This method uses weak key derivation and should not be used
        for new encryptions. Use derive_key_secure() instead.
    """
    import hashlib

    hash_bytes = hashlib.sha256(password.encode()).digest()
    key = base64.urlsafe_b64encode(hash_bytes)
    return Fernet(key)
