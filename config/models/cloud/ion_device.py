"""
IONDevice model - SD-WAN ION appliance configuration.

Represents a Prisma SD-WAN ION virtual appliance deployed in Azure:
- Azure marketplace image (Prisma SD-WAN ION Virtual Appliance)
- Two interfaces: WAN (untrust subnet, public IP) + LAN (trust subnet)
- No bootstrap storage (ION bootstraps via SD-WAN cloud controller)
- Used for datacenter service connections instead of VM-Series firewalls
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
class IONImageConfig:
    """ION marketplace image configuration"""
    publisher: str = "paloaltonetworks"
    offer: str = "prisma-sd-wan-ion-virtual-appliance"
    sku: str = "prisma-sdwan-ion-virtual-appliance"
    version: str = "latest"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'publisher': self.publisher,
            'offer': self.offer,
            'sku': self.sku,
            'version': self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IONImageConfig':
        return cls(
            publisher=data.get('publisher', 'paloaltonetworks'),
            offer=data.get('offer', 'prisma-sd-wan-ion-virtual-appliance'),
            sku=data.get('sku', 'prisma-sdwan-ion-virtual-appliance'),
            version=data.get('version', 'latest'),
        )


@dataclass
class IONVMSettings:
    """ION VM deployment settings"""
    size: str = "Standard_DS3_v2"
    image: IONImageConfig = field(default_factory=IONImageConfig)
    availability_zone: str = "1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'size': self.size,
            'image': self.image.to_dict(),
            'availability_zone': self.availability_zone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IONVMSettings':
        return cls(
            size=data.get('size', 'Standard_DS3_v2'),
            image=IONImageConfig.from_dict(data.get('image', {})),
            availability_zone=data.get('availability_zone', '1'),
        )


@dataclass
class IONInterfaceConfig:
    """ION network interface"""
    name: str  # wan or lan
    subnet_name: str
    public_ip: bool = False
    private_ip: Optional[str] = None
    ip_forwarding: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'subnet_name': self.subnet_name,
            'public_ip': self.public_ip,
            'private_ip': self.private_ip,
            'ip_forwarding': self.ip_forwarding,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IONInterfaceConfig':
        return cls(
            name=data['name'],
            subnet_name=data['subnet_name'],
            public_ip=data.get('public_ip', False),
            private_ip=data.get('private_ip'),
            ip_forwarding=data.get('ip_forwarding', True),
        )


class IONDevice(CloudItem):
    """
    SD-WAN ION virtual appliance configuration.

    Represents an ION device deployed in Azure for datacenter service
    connections. ION devices bootstrap via the Prisma SD-WAN cloud
    controller — no bootstrap storage account is needed.
    """

    item_type = "ion_device"
    terraform_resource_type = "azurerm_linux_virtual_machine"

    # ION types
    TYPE_DATACENTER = "datacenter"
    VALID_TYPES = [TYPE_DATACENTER]

    def __init__(self, raw_config: Dict[str, Any], deployment: 'CloudDeployment' = None):
        super().__init__(raw_config, deployment)

        # ION type and role
        self.ion_type: str = raw_config.get('ion_type', self.TYPE_DATACENTER)
        self.role: str = raw_config.get('role', 'service_connection')

        # Index for multiple ION devices
        self.index: Optional[int] = raw_config.get('index')

        # VM settings
        vm_data = raw_config.get('vm_settings', {})
        self.vm_settings = IONVMSettings.from_dict(vm_data)

        # Network interfaces (WAN + LAN only, no management NIC)
        interfaces_data = raw_config.get('interfaces', [])
        self.interfaces: List[IONInterfaceConfig] = [
            IONInterfaceConfig.from_dict(i) for i in interfaces_data
        ]
        if not self.interfaces and self.deployment:
            self._create_default_interfaces()

        # Credential reference
        self.credentials_ref: str = raw_config.get('credentials_ref', 'ion')

        # Deployed resource info (populated after deployment)
        self.wan_ip: Optional[str] = None
        self.lan_ip: Optional[str] = None

    def set_deployment(self, deployment: 'CloudDeployment'):
        """Set deployment and create default interfaces if needed."""
        self.deployment = deployment
        if not self.interfaces:
            self._create_default_interfaces()

    def _generate_name(self) -> str:
        """Generate ION name from deployment context"""
        if not self.deployment:
            return "ion"
        rg = self.deployment.resource_group
        if self.index is not None:
            return f"{rg}-ion{self.index}"
        return f"{rg}-ion"

    def _create_default_interfaces(self):
        """Create default WAN and LAN interface configuration."""
        if not self.deployment:
            return

        # WAN interface (untrust subnet, public IP for SD-WAN tunnels)
        self.interfaces.append(IONInterfaceConfig(
            name="wan",
            subnet_name=self.deployment.get_subnet_name('untrust'),
            public_ip=True,
            ip_forwarding=True,
        ))

        # LAN interface (trust subnet, no public IP)
        self.interfaces.append(IONInterfaceConfig(
            name="lan",
            subnet_name=self.deployment.get_subnet_name('trust'),
            public_ip=False,
            ip_forwarding=True,
        ))

    # ========== Serialization ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        data = super().to_dict()
        data.update({
            'ion_type': self.ion_type,
            'role': self.role,
            'index': self.index,
            'vm_settings': self.vm_settings.to_dict(),
            'interfaces': [i.to_dict() for i in self.interfaces],
            'credentials_ref': self.credentials_ref,
            'wan_ip': self.wan_ip,
            'lan_ip': self.lan_ip,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], deployment: 'CloudDeployment' = None) -> 'IONDevice':
        """Deserialize from dictionary"""
        instance = cls(data, deployment)
        if 'wan_ip' in data:
            instance.wan_ip = data['wan_ip']
        if 'lan_ip' in data:
            instance.lan_ip = data['lan_ip']
        return instance

    def to_terraform_vars(self) -> Dict[str, Any]:
        """Generate Terraform variables"""
        base_vars = super().to_terraform_vars()
        base_vars.update({
            'ion_name': self.name,
            'ion_type': self.ion_type,
            'vm_size': self.vm_settings.size,
            'vm_image': self.vm_settings.image.to_dict(),
            'availability_zone': self.vm_settings.availability_zone,
            'interfaces': {
                i.name: {
                    'subnet': i.subnet_name,
                    'public_ip': i.public_ip,
                    'private_ip': i.private_ip,
                    'ip_forwarding': i.ip_forwarding,
                }
                for i in self.interfaces
            },
        })
        return base_vars

    # ========== Validation ==========

    def _validate_specific(self) -> List[str]:
        """ION-specific validation"""
        errors = []

        if self.ion_type not in self.VALID_TYPES:
            errors.append(f"Invalid ION type: {self.ion_type}")

        if len(self.interfaces) < 2:
            errors.append("ION device requires at least 2 interfaces (WAN, LAN)")

        return errors

    def __repr__(self) -> str:
        return f"<IONDevice(name='{self.name}', type='{self.ion_type}')>"
