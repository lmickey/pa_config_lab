"""
Supporting VM models - Servers, clients, and ZTNA connectors.

These are auxiliary VMs deployed alongside firewalls for testing:
- ServerVM: Backend servers (web, app, database)
- ClientVM: User workstations (Windows, Linux)
- ZTNAConnectorVM: ZTNA connector appliance
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

from .base import CloudItem
from .firewall import VMImageConfig, VMSettings, NetworkInterfaceConfig

if TYPE_CHECKING:
    from .deployment import CloudDeployment

logger = logging.getLogger(__name__)


class OSType(str, Enum):
    """Operating system types"""
    LINUX = "linux"
    WINDOWS = "windows"


def _linux_image_factory() -> VMImageConfig:
    """Factory for Linux image config"""
    return VMImageConfig(
        publisher="Canonical",
        offer="0001-com-ubuntu-server-jammy",
        sku="22_04-lts-gen2",
        version="latest",
    )


def _windows_image_factory() -> VMImageConfig:
    """Factory for Windows image config"""
    return VMImageConfig(
        publisher="MicrosoftWindowsDesktop",
        offer="Windows-11",
        sku="win11-22h2-pro",
        version="latest",
    )


def _ztna_image_factory() -> VMImageConfig:
    """Factory for ZTNA connector image config"""
    return VMImageConfig(
        publisher="paloaltonetworks",
        offer="ztna-connector",
        sku="byol",
        version="latest",
    )


@dataclass
class LinuxImageConfig(VMImageConfig):
    """Ubuntu Linux image"""
    publisher: str = "Canonical"
    offer: str = "0001-com-ubuntu-server-jammy"
    sku: str = "22_04-lts-gen2"
    version: str = "latest"


@dataclass
class WindowsImageConfig(VMImageConfig):
    """Windows Desktop image"""
    publisher: str = "MicrosoftWindowsDesktop"
    offer: str = "Windows-11"
    sku: str = "win11-22h2-pro"
    version: str = "latest"


@dataclass
class ZTNAImageConfig(VMImageConfig):
    """ZTNA Connector image"""
    publisher: str = "paloaltonetworks"
    offer: str = "ztna-connector"
    sku: str = "byol"
    version: str = "latest"


@dataclass
class ServiceConfig:
    """Service running on a server VM"""
    service_type: str  # web_server, ssh, rdp, database, etc.
    port: int
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.service_type,
            'port': self.port,
            'enabled': self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceConfig':
        return cls(
            service_type=data['type'],
            port=data['port'],
            enabled=data.get('enabled', True),
        )


@dataclass
class GlobalProtectConfig:
    """GlobalProtect client configuration"""
    install: bool = True
    portal: str = ""
    pre_logon: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'install': self.install,
            'portal': self.portal,
            'pre_logon': self.pre_logon,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalProtectConfig':
        return cls(
            install=data.get('install', True),
            portal=data.get('portal', ''),
            pre_logon=data.get('pre_logon', False),
        )


class SupportingVM(CloudItem):
    """
    Base class for supporting VMs.

    Common functionality for servers, clients, and ZTNA connectors.
    """

    item_type = "supporting_vm"
    vm_type = "supporting"  # Override in subclasses

    def __init__(self, raw_config: Dict[str, Any], deployment: 'CloudDeployment' = None):
        super().__init__(raw_config, deployment)

        # OS type
        self.os_type: str = raw_config.get('os', OSType.LINUX.value)

        # VM settings with OS-appropriate image
        vm_data = raw_config.get('vm_settings', {})
        if vm_data:
            self.vm_settings = VMSettings.from_dict(vm_data)
        else:
            self.vm_settings = VMSettings(
                size="Standard_B2s",
                image=self._get_default_image(),
            )

        # Network interface
        interface_data = raw_config.get('interface', {})
        if interface_data:
            self.interface = NetworkInterfaceConfig.from_dict(interface_data)
        elif self.deployment:
            self.interface = NetworkInterfaceConfig(
                name="primary",
                subnet_name=self.deployment.get_subnet_name('trust'),
                public_ip=False,
            )
        else:
            self.interface = None

        # Index for multiple VMs
        self.index: Optional[int] = raw_config.get('index')

        # Credential reference
        self.credentials_ref: str = raw_config.get('credentials_ref', 'supporting_vms')

        # Deployed resource info
        self.private_ip: Optional[str] = None
        self.public_ip: Optional[str] = None

    def _get_default_image(self) -> VMImageConfig:
        """Get default image based on OS type"""
        if self.os_type == OSType.WINDOWS.value:
            return _windows_image_factory()
        return _linux_image_factory()

    def _generate_name(self) -> str:
        """Generate name - override in subclasses"""
        if not self.deployment:
            return f"{self.vm_type}-vm"
        rg = self.deployment.resource_group
        if self.index is not None:
            return f"{rg}-{self.vm_type}{self.index}"
        return f"{rg}-{self.vm_type}"

    @property
    def terraform_resource_type(self) -> str:
        """Get Terraform resource type based on OS"""
        if self.os_type == OSType.WINDOWS.value:
            return "azurerm_windows_virtual_machine"
        return "azurerm_linux_virtual_machine"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'os': self.os_type,
            'vm_type': self.vm_type,
            'vm_settings': self.vm_settings.to_dict(),
            'interface': self.interface.to_dict() if self.interface else None,
            'index': self.index,
            'credentials_ref': self.credentials_ref,
            'private_ip': self.private_ip,
            'public_ip': self.public_ip,
        })
        return data

    def to_terraform_vars(self) -> Dict[str, Any]:
        """Generate Terraform variables"""
        base_vars = super().to_terraform_vars()
        base_vars.update({
            'vm_name': self.name,
            'os_type': self.os_type,
            'vm_size': self.vm_settings.size,
            'vm_image': self.vm_settings.image.to_dict(),
            'interface_subnet': self.interface.subnet_name if self.interface else None,
            'public_ip': self.interface.public_ip if self.interface else False,
        })
        return base_vars


class ServerVM(SupportingVM):
    """
    Server VM - Backend server for testing.

    Examples: web server, database server, application server.
    """

    item_type = "server_vm"
    vm_type = "server"

    def __init__(self, raw_config: Dict[str, Any], deployment: 'CloudDeployment' = None):
        super().__init__(raw_config, deployment)

        # Services running on this server
        services_data = raw_config.get('services', [])
        self.services: List[ServiceConfig] = [
            ServiceConfig.from_dict(s) for s in services_data
        ]

    def _generate_name(self) -> str:
        if not self.deployment:
            return "server"
        rg = self.deployment.resource_group
        if self.index is not None:
            return f"{rg}-server{self.index}"
        return f"{rg}-server"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['services'] = [s.to_dict() for s in self.services]
        return data

    def to_terraform_vars(self) -> Dict[str, Any]:
        """Generate Terraform variables"""
        base_vars = super().to_terraform_vars()
        base_vars['services'] = {
            s.service_type: {'port': s.port, 'enabled': s.enabled}
            for s in self.services
        }
        return base_vars

    @classmethod
    def from_dict(cls, data: Dict[str, Any], deployment: 'CloudDeployment' = None) -> 'ServerVM':
        return cls(data, deployment)


class ClientVM(SupportingVM):
    """
    Client VM - User workstation for testing.

    Can be Windows or Linux with optional GlobalProtect installation.
    """

    item_type = "client_vm"
    vm_type = "uservm"

    def __init__(self, raw_config: Dict[str, Any], deployment: 'CloudDeployment' = None):
        super().__init__(raw_config, deployment)

        # GlobalProtect configuration
        gp_data = raw_config.get('globalprotect', {})
        self.globalprotect: Optional[GlobalProtectConfig] = (
            GlobalProtectConfig.from_dict(gp_data) if gp_data else None
        )

    def _generate_name(self) -> str:
        if not self.deployment:
            return f"uservm-{self.os_type}"
        rg = self.deployment.resource_group
        os_suffix = "win" if self.os_type == OSType.WINDOWS.value else "linux"
        if self.index is not None:
            return f"{rg}-uservm-{os_suffix}{self.index}"
        return f"{rg}-uservm-{os_suffix}"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['globalprotect'] = self.globalprotect.to_dict() if self.globalprotect else None
        return data

    def to_terraform_vars(self) -> Dict[str, Any]:
        """Generate Terraform variables"""
        base_vars = super().to_terraform_vars()
        if self.globalprotect:
            base_vars['globalprotect'] = self.globalprotect.to_dict()
        return base_vars

    @classmethod
    def from_dict(cls, data: Dict[str, Any], deployment: 'CloudDeployment' = None) -> 'ClientVM':
        return cls(data, deployment)


class ZTNAConnectorVM(SupportingVM):
    """
    ZTNA Connector VM - Prisma Access ZTNA connector.

    Managed via Prisma Access, minimal local configuration needed.
    """

    item_type = "ztna_connector_vm"
    vm_type = "ztna"

    def __init__(self, raw_config: Dict[str, Any], deployment: 'CloudDeployment' = None):
        # ZTNA is always Linux
        raw_config['os'] = OSType.LINUX.value
        super().__init__(raw_config, deployment)

        # Override with ZTNA image
        self.vm_settings.image = _ztna_image_factory()

    def _generate_name(self) -> str:
        if not self.deployment:
            return "ztna"
        rg = self.deployment.resource_group
        if self.index is not None:
            return f"{rg}-ztna{self.index}"
        return f"{rg}-ztna"

    @classmethod
    def from_dict(cls, data: Dict[str, Any], deployment: 'CloudDeployment' = None) -> 'ZTNAConnectorVM':
        return cls(data, deployment)
