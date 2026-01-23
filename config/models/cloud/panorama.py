"""
CloudPanorama model - Panorama management server configuration.

Represents a Panorama VM for initial deployment:
- VM settings and network interface
- Licensing status tracking
- Plugin configuration
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

from .base import CloudItem
from .firewall import VMImageConfig, VMSettings, NetworkInterfaceConfig, DeviceConfig

if TYPE_CHECKING:
    from .deployment import CloudDeployment

logger = logging.getLogger(__name__)


def _panorama_image_factory() -> VMImageConfig:
    """Factory for Panorama image config"""
    return VMImageConfig(
        publisher="paloaltonetworks",
        offer="panorama",
        sku="byol",
        version="latest",
    )


@dataclass
class PanoramaVMSettings(VMSettings):
    """Panorama-specific VM settings"""
    size: str = "Standard_DS4_v2"  # Panorama needs more resources
    image: VMImageConfig = field(default_factory=_panorama_image_factory)


@dataclass
class LicensingStatus:
    """Licensing tracking"""
    status: str = "pending"  # pending, licensed, skipped
    licensed_at: Optional[str] = None
    plugins_installed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status,
            'licensed_at': self.licensed_at,
            'plugins_installed': self.plugins_installed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LicensingStatus':
        return cls(
            status=data.get('status', 'pending'),
            licensed_at=data.get('licensed_at'),
            plugins_installed=data.get('plugins_installed', False),
        )


@dataclass
class PluginConfig:
    """Panorama plugin configuration"""
    name: str
    version: str = "latest"
    installed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'version': self.version,
            'installed': self.installed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginConfig':
        return cls(
            name=data['name'],
            version=data.get('version', 'latest'),
            installed=data.get('installed', False),
        )


class CloudPanorama(CloudItem):
    """
    Panorama management server configuration.

    Represents Panorama for initial deployment. Managing firewalls
    via Panorama is a future feature.
    """

    item_type = "cloud_panorama"
    terraform_resource_type = "azurerm_linux_virtual_machine"

    def __init__(self, raw_config: Dict[str, Any], deployment: 'CloudDeployment' = None):
        super().__init__(raw_config, deployment)

        # VM settings (Panorama defaults)
        vm_data = raw_config.get('vm_settings', {})
        if vm_data:
            self.vm_settings = VMSettings.from_dict(vm_data)
        else:
            self.vm_settings = PanoramaVMSettings()

        # Single management interface
        interface_data = raw_config.get('interface', {})
        if interface_data:
            self.interface = NetworkInterfaceConfig.from_dict(interface_data)
        elif self.deployment:
            self._create_default_interface()
        else:
            self.interface = None

        # Credential reference
        self.credentials_ref: str = raw_config.get('credentials_ref', 'panorama')

        # Licensing
        licensing_data = raw_config.get('licensing', {})
        self.licensing = LicensingStatus.from_dict(licensing_data)

        # Device configuration
        device_data = raw_config.get('device', {})
        self.device = DeviceConfig.from_dict(device_data)

        # Plugins
        plugins_data = raw_config.get('plugins', [])
        self.plugins: List[PluginConfig] = [
            PluginConfig.from_dict(p) for p in plugins_data
        ]
        if not self.plugins:
            # Default: cloud_services plugin
            self.plugins.append(PluginConfig(name="cloud_services"))

        # FUTURE: Device groups and templates
        self.device_groups: List[Dict] = raw_config.get('device_groups', [])
        self.templates: List[Dict] = raw_config.get('templates', [])

        # Deployed resource info
        self.management_ip: Optional[str] = None

    def _create_default_interface(self):
        """Create default management interface."""
        if self.deployment:
            self.interface = NetworkInterfaceConfig(
                name="management",
                subnet_name=self.deployment.get_subnet_name('mgmt'),
                public_ip=True,
            )

    def set_deployment(self, deployment: 'CloudDeployment'):
        """Set deployment and create default interface if needed."""
        self.deployment = deployment
        if not self.interface:
            self._create_default_interface()

    def _generate_name(self) -> str:
        """Generate Panorama name from deployment context"""
        if not self.deployment:
            return "panorama"
        return f"{self.deployment.resource_group}-panorama"

    @property
    def hostname(self) -> str:
        """Get hostname"""
        return self.device.hostname or self.name

    @property
    def is_licensed(self) -> bool:
        """Check if Panorama is licensed"""
        return self.licensing.status == "licensed"

    @property
    def is_ready(self) -> bool:
        """Check if Panorama is ready for configuration"""
        return self.is_licensed and self.licensing.plugins_installed

    # ========== Licensing Management ==========

    def mark_licensed(self):
        """Mark Panorama as licensed"""
        self.licensing.status = "licensed"
        self.licensing.licensed_at = datetime.utcnow().isoformat()
        logger.info(f"Panorama '{self.name}' marked as licensed")

    def mark_plugins_installed(self):
        """Mark plugins as installed"""
        self.licensing.plugins_installed = True
        for plugin in self.plugins:
            plugin.installed = True
        logger.info(f"Panorama '{self.name}' plugins marked as installed")

    def skip_licensing(self):
        """Skip licensing (for SCM-managed deployments)"""
        self.licensing.status = "skipped"
        logger.info(f"Panorama '{self.name}' licensing skipped")

    # ========== Serialization ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        data = super().to_dict()
        data.update({
            'vm_settings': self.vm_settings.to_dict(),
            'interface': self.interface.to_dict() if self.interface else None,
            'credentials_ref': self.credentials_ref,
            'licensing': self.licensing.to_dict(),
            'device': self.device.to_dict(),
            'plugins': [p.to_dict() for p in self.plugins],
            'device_groups': self.device_groups,
            'templates': self.templates,
            'management_ip': self.management_ip,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], deployment: 'CloudDeployment' = None) -> 'CloudPanorama':
        """Deserialize from dictionary"""
        instance = cls(data, deployment)
        if 'management_ip' in data:
            instance.management_ip = data['management_ip']
        return instance

    def to_terraform_vars(self) -> Dict[str, Any]:
        """Generate Terraform variables"""
        base_vars = super().to_terraform_vars()
        base_vars.update({
            'panorama_name': self.name,
            'vm_size': self.vm_settings.size,
            'vm_image': self.vm_settings.image.to_dict(),
            'interface_subnet': self.interface.subnet_name if self.interface else None,
            'public_ip': self.interface.public_ip if self.interface else True,
        })
        return base_vars

    # ========== Validation ==========

    def _validate_specific(self) -> List[str]:
        """Panorama-specific validation"""
        errors = []

        if not self.interface:
            errors.append("Panorama requires a management interface configuration")

        return errors

    def __repr__(self) -> str:
        status = self.licensing.status
        return f"<CloudPanorama(name='{self.name}', status='{status}')>"
