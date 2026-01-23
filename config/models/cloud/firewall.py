"""
CloudFirewall model - VM-Series firewall configuration.

Represents a Palo Alto firewall VM to be deployed in Azure:
- VM settings (size, image, availability zone)
- Network interfaces (management, untrust, trust)
- Device configuration (hostname, DNS, NTP)
- Security configuration (zones, interfaces, policies)
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field
import json
import logging

from .base import CloudItem

if TYPE_CHECKING:
    from .deployment import CloudDeployment

logger = logging.getLogger(__name__)


@dataclass
class VMImageConfig:
    """VM image configuration"""
    publisher: str = "paloaltonetworks"
    offer: str = "vmseries-flex"
    sku: str = "byol"
    version: str = "latest"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'publisher': self.publisher,
            'offer': self.offer,
            'sku': self.sku,
            'version': self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VMImageConfig':
        return cls(
            publisher=data.get('publisher', 'paloaltonetworks'),
            offer=data.get('offer', 'vmseries-flex'),
            sku=data.get('sku', 'byol'),
            version=data.get('version', 'latest'),
        )


@dataclass
class VMSettings:
    """VM deployment settings"""
    size: str = "Standard_DS3_v2"
    image: VMImageConfig = field(default_factory=VMImageConfig)
    availability_zone: str = "1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'size': self.size,
            'image': self.image.to_dict(),
            'availability_zone': self.availability_zone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VMSettings':
        return cls(
            size=data.get('size', 'Standard_DS3_v2'),
            image=VMImageConfig.from_dict(data.get('image', {})),
            availability_zone=data.get('availability_zone', '1'),
        )


@dataclass
class NetworkInterfaceConfig:
    """Firewall network interface"""
    name: str  # management, ethernet1/1, ethernet1/2
    subnet_name: str
    public_ip: bool = False
    private_ip: Optional[str] = None  # Static IP if specified

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'subnet_name': self.subnet_name,
            'public_ip': self.public_ip,
            'private_ip': self.private_ip,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NetworkInterfaceConfig':
        return cls(
            name=data['name'],
            subnet_name=data['subnet_name'],
            public_ip=data.get('public_ip', False),
            private_ip=data.get('private_ip'),
        )


@dataclass
class DeviceConfig:
    """Firewall device settings"""
    hostname: Optional[str] = None  # Auto-generated if None
    timezone: str = "US/Pacific"
    dns_primary: str = "8.8.8.8"
    dns_secondary: str = "8.8.4.4"
    ntp_primary: str = "time.google.com"
    ntp_secondary: str = "time.windows.com"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'hostname': self.hostname,
            'timezone': self.timezone,
            'dns_primary': self.dns_primary,
            'dns_secondary': self.dns_secondary,
            'ntp_primary': self.ntp_primary,
            'ntp_secondary': self.ntp_secondary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceConfig':
        return cls(
            hostname=data.get('hostname'),
            timezone=data.get('timezone', 'US/Pacific'),
            dns_primary=data.get('dns_primary', '8.8.8.8'),
            dns_secondary=data.get('dns_secondary', '8.8.4.4'),
            ntp_primary=data.get('ntp_primary', 'time.google.com'),
            ntp_secondary=data.get('ntp_secondary', 'time.windows.com'),
        )


class CloudFirewall(CloudItem):
    """
    VM-Series firewall configuration.

    Represents a firewall to be deployed in Azure, including VM settings,
    network configuration, and device settings.
    """

    item_type = "cloud_firewall"
    terraform_resource_type = "azurerm_linux_virtual_machine"

    # Firewall types
    TYPE_DATACENTER = "datacenter"
    TYPE_BRANCH = "branch"
    VALID_TYPES = [TYPE_DATACENTER, TYPE_BRANCH]

    # Role mapping
    TYPE_TO_ROLE = {
        TYPE_DATACENTER: "service_connection",
        TYPE_BRANCH: "remote_network",
    }

    def __init__(self, raw_config: Dict[str, Any], deployment: 'CloudDeployment' = None):
        super().__init__(raw_config, deployment)

        # Firewall type and role
        self.firewall_type: str = raw_config.get('type', self.TYPE_DATACENTER)
        self.role: str = raw_config.get('role', self.TYPE_TO_ROLE.get(self.firewall_type, ''))

        # Index for multiple firewalls of same type
        self.index: Optional[int] = raw_config.get('index')

        # VM settings
        vm_data = raw_config.get('vm_settings', {})
        self.vm_settings = VMSettings.from_dict(vm_data)

        # Network interfaces
        interfaces_data = raw_config.get('interfaces', [])
        self.interfaces: List[NetworkInterfaceConfig] = [
            NetworkInterfaceConfig.from_dict(i) for i in interfaces_data
        ]
        if not self.interfaces and self.deployment:
            self._create_default_interfaces()

        # Device configuration
        device_data = raw_config.get('device', {})
        self.device = DeviceConfig.from_dict(device_data)

        # Credential reference
        self.credentials_ref: str = raw_config.get('credentials_ref', 'firewall')

        # Deployed resource info (populated after deployment)
        self.management_ip: Optional[str] = None
        self.untrust_ip: Optional[str] = None

    def set_deployment(self, deployment: 'CloudDeployment'):
        """Set deployment and create default interfaces if needed."""
        self.deployment = deployment
        if not self.interfaces:
            self._create_default_interfaces()

    def _generate_name(self) -> str:
        """Generate firewall name from deployment context"""
        if not self.deployment:
            return "firewall"

        rg = self.deployment.resource_group
        if self.index is not None:
            return f"{rg}-fw{self.index}"
        return f"{rg}-fw"

    def _create_default_interfaces(self):
        """Create default interface configuration"""
        if not self.deployment:
            return

        # Management interface
        self.interfaces.append(NetworkInterfaceConfig(
            name="management",
            subnet_name=self.deployment.get_subnet_name('mgmt'),
            public_ip=True,
        ))

        # Untrust interface (shared)
        self.interfaces.append(NetworkInterfaceConfig(
            name="ethernet1/1",
            subnet_name=self.deployment.get_subnet_name('untrust'),
            public_ip=True,
        ))

        # Trust interface (depends on type)
        firewall_id = f"branch{self.index}" if self.firewall_type == self.TYPE_BRANCH and self.index else None
        self.interfaces.append(NetworkInterfaceConfig(
            name="ethernet1/2",
            subnet_name=self.deployment.get_subnet_name('trust', firewall_id),
            public_ip=False,
        ))

    @property
    def hostname(self) -> str:
        """Get hostname (auto-generated from name if not set)"""
        return self.device.hostname or self.name

    # ========== Serialization ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        data = super().to_dict()
        data.update({
            'type': self.firewall_type,
            'role': self.role,
            'index': self.index,
            'vm_settings': self.vm_settings.to_dict(),
            'interfaces': [i.to_dict() for i in self.interfaces],
            'device': self.device.to_dict(),
            'credentials_ref': self.credentials_ref,
            'management_ip': self.management_ip,
            'untrust_ip': self.untrust_ip,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], deployment: 'CloudDeployment' = None) -> 'CloudFirewall':
        """Deserialize from dictionary"""
        instance = cls(data, deployment)
        if 'management_ip' in data:
            instance.management_ip = data['management_ip']
        if 'untrust_ip' in data:
            instance.untrust_ip = data['untrust_ip']
        return instance

    def to_terraform_vars(self) -> Dict[str, Any]:
        """Generate Terraform variables"""
        base_vars = super().to_terraform_vars()
        base_vars.update({
            'firewall_name': self.name,
            'firewall_type': self.firewall_type,
            'vm_size': self.vm_settings.size,
            'vm_image': self.vm_settings.image.to_dict(),
            'availability_zone': self.vm_settings.availability_zone,
            'interfaces': {
                i.name: {
                    'subnet': i.subnet_name,
                    'public_ip': i.public_ip,
                    'private_ip': i.private_ip,
                }
                for i in self.interfaces
            },
        })
        return base_vars

    def to_bootstrap_vars(self) -> Dict[str, Any]:
        """
        Generate bootstrap variables for VM-Series.

        Returns:
            Variables for init-cfg.txt
        """
        return {
            'hostname': self.hostname,
            'timezone': self.device.timezone,
            'dns-primary': self.device.dns_primary,
            'dns-secondary': self.device.dns_secondary,
            'ntp-primary': self.device.ntp_primary,
            'ntp-secondary': self.device.ntp_secondary,
        }

    # ========== Validation ==========

    def _validate_specific(self) -> List[str]:
        """Firewall-specific validation"""
        errors = []

        if self.firewall_type not in self.VALID_TYPES:
            errors.append(f"Invalid firewall type: {self.firewall_type}")

        if len(self.interfaces) < 3:
            errors.append("Firewall requires at least 3 interfaces (management, untrust, trust)")

        return errors

    def __repr__(self) -> str:
        return f"<CloudFirewall(name='{self.name}', type='{self.firewall_type}')>"
