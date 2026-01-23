"""
Credential Manager - Manage device credentials for cloud deployments.

This module provides credential management for:
- Firewalls (username/password, API key, or certificate)
- Panorama (username/password, API key, or certificate)
- Supporting VMs (username/password, SSH key)

Includes secure password generation for auto-generated credentials.
"""

import secrets
import string
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AuthType(str, Enum):
    """Authentication types"""
    PASSWORD = "password"
    API_KEY = "api_key"
    CERTIFICATE = "certificate"


class CredentialType(str, Enum):
    """Credential categories"""
    FIREWALL = "firewall"
    PANORAMA = "panorama"
    SUPPORTING_VM = "supporting_vms"


# ========== Password Generation ==========

class PasswordGenerator:
    """
    Secure password generator for cloud deployments.

    Generates passwords that meet common requirements:
    - Minimum 16 characters (configurable)
    - Mix of uppercase, lowercase, digits, and symbols
    - Avoids ambiguous characters (0, O, l, 1, I)
    - Uses cryptographically secure random source
    """

    # Character sets (excluding ambiguous characters)
    LOWERCASE = 'abcdefghjkmnpqrstuvwxyz'  # no l
    UPPERCASE = 'ABCDEFGHJKLMNPQRSTUVWXYZ'  # no I, O
    DIGITS = '23456789'  # no 0, 1
    SYMBOLS = '!@#$%^&*-_=+'  # safe for most systems

    # Azure-safe symbols (more restrictive)
    AZURE_SYMBOLS = '@#$%^&*-_+'

    @classmethod
    def generate(
        cls,
        length: int = 20,
        include_symbols: bool = True,
        azure_compatible: bool = True
    ) -> str:
        """
        Generate a secure random password.

        Args:
            length: Password length (minimum 12)
            include_symbols: Include special characters
            azure_compatible: Use Azure-safe character set

        Returns:
            Secure random password
        """
        if length < 12:
            length = 12
            logger.warning("Password length increased to minimum of 12")

        # Build character set
        chars = cls.LOWERCASE + cls.UPPERCASE + cls.DIGITS
        if include_symbols:
            chars += cls.AZURE_SYMBOLS if azure_compatible else cls.SYMBOLS

        # Generate password with guaranteed character types
        password = []

        # Ensure at least one of each required type
        password.append(secrets.choice(cls.LOWERCASE))
        password.append(secrets.choice(cls.UPPERCASE))
        password.append(secrets.choice(cls.DIGITS))
        if include_symbols:
            symbols = cls.AZURE_SYMBOLS if azure_compatible else cls.SYMBOLS
            password.append(secrets.choice(symbols))

        # Fill remaining length
        remaining = length - len(password)
        password.extend(secrets.choice(chars) for _ in range(remaining))

        # Shuffle to avoid predictable positions
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)

        return ''.join(password_list)

    @classmethod
    def generate_username(cls, base_name: str, max_length: int = 20) -> str:
        """
        Generate a sanitized username from a base name.

        Args:
            base_name: Base name to derive username from
            max_length: Maximum username length

        Returns:
            Sanitized username
        """
        # Replace hyphens with underscores
        username = base_name.replace('-', '_')

        # Remove invalid characters (keep alphanumeric and underscore)
        username = ''.join(c for c in username if c.isalnum() or c == '_')

        # Ensure doesn't start with number
        if username and username[0].isdigit():
            username = 'u' + username

        # Truncate if needed
        if len(username) > max_length:
            username = username[:max_length]

        # Default if empty
        if not username:
            username = 'admin'

        return username.lower()

    @classmethod
    def generate_ssh_keypair(cls, key_type: str = 'rsa', bits: int = 4096) -> tuple:
        """
        Generate SSH key pair.

        Args:
            key_type: Key type ('rsa' or 'ed25519')
            bits: Key size for RSA (ignored for ed25519)

        Returns:
            Tuple of (private_key_pem, public_key_openssh)

        Raises:
            ImportError: If cryptography library not available
        """
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
            from cryptography.hazmat.backends import default_backend
        except ImportError:
            raise ImportError("cryptography library required for SSH key generation")

        if key_type == 'ed25519':
            private_key = ed25519.Ed25519PrivateKey.generate()
        else:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=bits,
                backend=default_backend()
            )

        # Serialize private key (PEM format)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        # Serialize public key (OpenSSH format)
        public_key = private_key.public_key()
        public_openssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        ).decode('utf-8')

        return private_pem, public_openssh


# ========== Credential Data Classes ==========

@dataclass
class CertificateConfig:
    """Certificate authentication configuration"""
    enabled: bool = False
    cert_path: Optional[str] = None
    key_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'enabled': self.enabled,
            'cert_path': self.cert_path,
            'key_path': self.key_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CertificateConfig':
        return cls(
            enabled=data.get('enabled', False),
            cert_path=data.get('cert_path'),
            key_path=data.get('key_path'),
        )

    def validate(self) -> List[str]:
        """Validate certificate configuration"""
        errors = []
        if self.enabled:
            if not self.cert_path:
                errors.append("Certificate path required when certificate auth enabled")
            elif not Path(self.cert_path).exists():
                errors.append(f"Certificate file not found: {self.cert_path}")

            if not self.key_path:
                errors.append("Key path required when certificate auth enabled")
            elif not Path(self.key_path).exists():
                errors.append(f"Key file not found: {self.key_path}")
        return errors


@dataclass
class DeviceCredentials:
    """
    Credentials for a Palo Alto device (firewall or Panorama).

    Supports:
    - Password authentication (default)
    - API key authentication
    - Certificate authentication (SSH)
    """
    use_generated: bool = True
    auth_type: AuthType = AuthType.PASSWORD
    username: str = "admin"
    password: Optional[str] = None
    api_key: Optional[str] = None
    certificate: CertificateConfig = field(default_factory=CertificateConfig)
    generated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'use_generated': self.use_generated,
            'auth_type': self.auth_type.value if isinstance(self.auth_type, AuthType) else self.auth_type,
            'username': self.username,
            'password': self.password,
            'api_key': self.api_key,
            'certificate': self.certificate.to_dict(),
            'generated_at': self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceCredentials':
        auth_type = data.get('auth_type', 'password')
        if isinstance(auth_type, str):
            auth_type = AuthType(auth_type)

        cert_data = data.get('certificate', {})
        certificate = CertificateConfig.from_dict(cert_data) if cert_data else CertificateConfig()

        return cls(
            use_generated=data.get('use_generated', True),
            auth_type=auth_type,
            username=data.get('username', 'admin'),
            password=data.get('password'),
            api_key=data.get('api_key'),
            certificate=certificate,
            generated_at=data.get('generated_at'),
        )

    def generate_password(self, length: int = 20) -> str:
        """
        Generate and set a new password.

        Args:
            length: Password length

        Returns:
            Generated password
        """
        self.password = PasswordGenerator.generate(length=length)
        self.generated_at = datetime.utcnow().isoformat()
        self.auth_type = AuthType.PASSWORD
        logger.info(f"Generated new password for {self.username}")
        return self.password

    def has_credentials(self) -> bool:
        """Check if credentials are configured"""
        if self.auth_type == AuthType.PASSWORD:
            return bool(self.password)
        elif self.auth_type == AuthType.API_KEY:
            return bool(self.api_key)
        elif self.auth_type == AuthType.CERTIFICATE:
            return self.certificate.enabled and bool(self.certificate.cert_path)
        return False

    def validate(self) -> List[str]:
        """Validate credential configuration"""
        errors = []

        if not self.username:
            errors.append("Username is required")

        if self.auth_type == AuthType.PASSWORD:
            if not self.use_generated and not self.password:
                errors.append("Password required when not using generated credentials")
        elif self.auth_type == AuthType.API_KEY:
            if not self.api_key:
                errors.append("API key required when using API key authentication")
        elif self.auth_type == AuthType.CERTIFICATE:
            errors.extend(self.certificate.validate())

        return errors

    def clear_sensitive(self):
        """Clear sensitive data (for display/export)"""
        self.password = None
        self.api_key = None


@dataclass
class VMCredentials:
    """
    Credentials for supporting VMs (Windows/Linux).

    Supports:
    - Password authentication
    - SSH public key (Linux only)
    """
    use_generated: bool = True
    username: Optional[str] = None  # Auto-generated from resource group
    password: Optional[str] = None
    ssh_public_key: Optional[str] = None
    ssh_private_key: Optional[str] = None  # Stored separately, not in tenant file
    generated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'use_generated': self.use_generated,
            'username': self.username,
            'password': self.password,
            'ssh_public_key': self.ssh_public_key,
            # Note: ssh_private_key intentionally not serialized to tenant file
            'generated_at': self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VMCredentials':
        return cls(
            use_generated=data.get('use_generated', True),
            username=data.get('username'),
            password=data.get('password'),
            ssh_public_key=data.get('ssh_public_key'),
            generated_at=data.get('generated_at'),
        )

    def generate_credentials(
        self,
        resource_group: str,
        include_ssh_key: bool = True,
        password_length: int = 20
    ) -> Dict[str, str]:
        """
        Generate username, password, and optionally SSH key.

        Args:
            resource_group: Resource group name for username generation
            include_ssh_key: Generate SSH key pair
            password_length: Password length

        Returns:
            Dictionary with generated credentials
        """
        result = {}

        # Generate username from resource group
        self.username = PasswordGenerator.generate_username(
            f"{resource_group}_admin",
            max_length=20
        )
        result['username'] = self.username

        # Generate password
        self.password = PasswordGenerator.generate(length=password_length)
        result['password'] = self.password

        # Generate SSH key if requested
        if include_ssh_key:
            try:
                private_key, public_key = PasswordGenerator.generate_ssh_keypair()
                self.ssh_private_key = private_key
                self.ssh_public_key = public_key
                result['ssh_private_key'] = private_key
                result['ssh_public_key'] = public_key
            except ImportError:
                logger.warning("SSH key generation skipped: cryptography library not available")

        self.generated_at = datetime.utcnow().isoformat()
        logger.info(f"Generated VM credentials for {self.username}")

        return result

    def has_credentials(self) -> bool:
        """Check if credentials are configured"""
        return bool(self.username and (self.password or self.ssh_public_key))

    def validate(self) -> List[str]:
        """Validate credential configuration"""
        errors = []

        if not self.use_generated and not self.username:
            errors.append("Username required when not using generated credentials")

        if not self.use_generated and not self.password and not self.ssh_public_key:
            errors.append("Password or SSH key required when not using generated credentials")

        return errors

    def clear_sensitive(self):
        """Clear sensitive data (for display/export)"""
        self.password = None
        self.ssh_private_key = None


@dataclass
class SCMCredentials:
    """
    Credentials for Prisma Access SCM API.

    Migrated from existing tenant structure.
    """
    tsg_id: str = ""
    client_id: str = ""
    client_secret: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tsg_id': self.tsg_id,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SCMCredentials':
        return cls(
            tsg_id=data.get('tsg_id', ''),
            client_id=data.get('client_id', ''),
            client_secret=data.get('client_secret', ''),
        )

    def has_credentials(self) -> bool:
        """Check if credentials are configured"""
        return bool(self.tsg_id and self.client_id and self.client_secret)

    def validate(self) -> List[str]:
        """Validate credential configuration"""
        errors = []
        if not self.tsg_id:
            errors.append("TSG ID is required")
        if not self.client_id:
            errors.append("Client ID is required")
        if not self.client_secret:
            errors.append("Client secret is required")
        return errors


# ========== Tenant Credentials Container ==========

@dataclass
class TenantCredentials:
    """
    Complete credential set for a tenant/POV.

    Contains:
    - SCM credentials (Prisma Access API)
    - Firewall credentials (shared by all firewalls)
    - Panorama credentials
    - Supporting VM credentials
    """
    scm: SCMCredentials = field(default_factory=SCMCredentials)
    firewall: DeviceCredentials = field(default_factory=DeviceCredentials)
    panorama: DeviceCredentials = field(default_factory=DeviceCredentials)
    supporting_vms: VMCredentials = field(default_factory=VMCredentials)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scm': self.scm.to_dict(),
            'firewall': self.firewall.to_dict(),
            'panorama': self.panorama.to_dict(),
            'supporting_vms': self.supporting_vms.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TenantCredentials':
        return cls(
            scm=SCMCredentials.from_dict(data.get('scm', {})),
            firewall=DeviceCredentials.from_dict(data.get('firewall', {})),
            panorama=DeviceCredentials.from_dict(data.get('panorama', {})),
            supporting_vms=VMCredentials.from_dict(data.get('supporting_vms', {})),
        )

    @classmethod
    def from_legacy_tenant(cls, tenant_data: Dict[str, Any]) -> 'TenantCredentials':
        """
        Create from legacy tenant format (backward compatibility).

        Legacy format has tsg_id, client_id, client_secret at top level.

        Args:
            tenant_data: Legacy tenant dictionary

        Returns:
            TenantCredentials instance
        """
        # Check if already new format
        if 'scm' in tenant_data:
            return cls.from_dict(tenant_data)

        # Convert legacy format
        return cls(
            scm=SCMCredentials(
                tsg_id=tenant_data.get('tsg_id', ''),
                client_id=tenant_data.get('client_id', ''),
                client_secret=tenant_data.get('client_secret', ''),
            ),
            firewall=DeviceCredentials(),
            panorama=DeviceCredentials(),
            supporting_vms=VMCredentials(),
        )

    def generate_all_device_credentials(
        self,
        resource_group: str = "",
        include_ssh: bool = True
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate credentials for all devices that need them.

        Args:
            resource_group: Resource group name (for VM username)
            include_ssh: Include SSH keys for VMs

        Returns:
            Dictionary with generated credentials by type
        """
        result = {}

        # Generate firewall password if needed
        if self.firewall.use_generated and not self.firewall.password:
            password = self.firewall.generate_password()
            result['firewall'] = {
                'username': self.firewall.username,
                'password': password,
            }

        # Generate Panorama password if needed
        if self.panorama.use_generated and not self.panorama.password:
            password = self.panorama.generate_password()
            result['panorama'] = {
                'username': self.panorama.username,
                'password': password,
            }

        # Generate VM credentials if needed
        if self.supporting_vms.use_generated and not self.supporting_vms.has_credentials():
            vm_creds = self.supporting_vms.generate_credentials(
                resource_group=resource_group or 'pov',
                include_ssh_key=include_ssh,
            )
            result['supporting_vms'] = vm_creds

        return result

    def validate(self) -> Dict[str, List[str]]:
        """
        Validate all credentials.

        Returns:
            Dictionary of errors by credential type
        """
        errors = {}

        scm_errors = self.scm.validate()
        if scm_errors:
            errors['scm'] = scm_errors

        fw_errors = self.firewall.validate()
        if fw_errors:
            errors['firewall'] = fw_errors

        pan_errors = self.panorama.validate()
        if pan_errors:
            errors['panorama'] = pan_errors

        vm_errors = self.supporting_vms.validate()
        if vm_errors:
            errors['supporting_vms'] = vm_errors

        return errors

    def get_summary(self) -> Dict[str, Any]:
        """
        Get credential summary (without sensitive data).

        Returns:
            Summary dictionary
        """
        return {
            'scm': {
                'configured': self.scm.has_credentials(),
                'tsg_id': self.scm.tsg_id,
            },
            'firewall': {
                'configured': self.firewall.has_credentials(),
                'use_generated': self.firewall.use_generated,
                'auth_type': self.firewall.auth_type.value,
                'username': self.firewall.username,
                'generated_at': self.firewall.generated_at,
            },
            'panorama': {
                'configured': self.panorama.has_credentials(),
                'use_generated': self.panorama.use_generated,
                'auth_type': self.panorama.auth_type.value,
                'username': self.panorama.username,
                'generated_at': self.panorama.generated_at,
            },
            'supporting_vms': {
                'configured': self.supporting_vms.has_credentials(),
                'use_generated': self.supporting_vms.use_generated,
                'username': self.supporting_vms.username,
                'has_ssh_key': bool(self.supporting_vms.ssh_public_key),
                'generated_at': self.supporting_vms.generated_at,
            },
        }


# ========== Credential Manager ==========

class CredentialManager:
    """
    Manager for handling credential generation and validation.

    Provides utilities for:
    - Generating secure credentials
    - Validating credential configurations
    - Preparing credentials for Terraform
    """

    @staticmethod
    def generate_password(length: int = 20, azure_compatible: bool = True) -> str:
        """Generate a secure password"""
        return PasswordGenerator.generate(length=length, azure_compatible=azure_compatible)

    @staticmethod
    def generate_username(base_name: str, max_length: int = 20) -> str:
        """Generate a sanitized username"""
        return PasswordGenerator.generate_username(base_name, max_length)

    @staticmethod
    def generate_ssh_keypair(key_type: str = 'rsa') -> tuple:
        """Generate SSH key pair"""
        return PasswordGenerator.generate_ssh_keypair(key_type)

    @staticmethod
    def prepare_terraform_credentials(
        tenant_credentials: TenantCredentials,
        resource_group: str
    ) -> Dict[str, Any]:
        """
        Prepare credentials for Terraform deployment.

        Generates any missing credentials and returns them in Terraform-ready format.

        Args:
            tenant_credentials: Tenant credentials object
            resource_group: Resource group name for naming

        Returns:
            Dictionary ready for terraform.tfvars
        """
        # Generate any missing credentials
        tenant_credentials.generate_all_device_credentials(
            resource_group=resource_group
        )

        return {
            'firewall_admin_username': tenant_credentials.firewall.username,
            'firewall_admin_password': tenant_credentials.firewall.password,
            'panorama_admin_username': tenant_credentials.panorama.username,
            'panorama_admin_password': tenant_credentials.panorama.password,
            'vm_admin_username': tenant_credentials.supporting_vms.username,
            'vm_admin_password': tenant_credentials.supporting_vms.password,
            'vm_ssh_public_key': tenant_credentials.supporting_vms.ssh_public_key,
        }

    @staticmethod
    def mask_password(password: str, show_chars: int = 4) -> str:
        """
        Mask a password for display.

        Args:
            password: Password to mask
            show_chars: Number of characters to show at start

        Returns:
            Masked password string
        """
        if not password:
            return ""
        if len(password) <= show_chars:
            return "*" * len(password)
        return password[:show_chars] + "*" * (len(password) - show_chars)
