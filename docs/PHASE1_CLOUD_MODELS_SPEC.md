# Phase 1: Cloud Infrastructure Models - Detailed Specification

This document provides implementation-level specifications for the cloud infrastructure configuration models. These models extend the existing configuration framework to support Azure deployments.

---

## 1. Design Principles

### 1.1 Follow Existing Patterns

All cloud models follow the patterns established in `config/models/base.py`:

| Pattern | Source | Application |
|---------|--------|-------------|
| `raw_config` storage | `ConfigItem.__init__` | Store original data for serialization |
| `to_dict()` / `from_dict()` | `ConfigItem` methods | JSON serialization with clean copies |
| `validate()` | `ConfigItem.validate()` | Return list of error strings |
| Type registration | `ConfigItemFactory._type_registry` | Enable factory instantiation |
| Dependency caching | `ConfigItem._dependencies_cache` | Lazy computation of dependencies |

### 1.2 Key Differences from SCM Models

| Aspect | SCM ConfigItem | Cloud Models |
|--------|----------------|--------------|
| Location | `folder` or `snippet` required | `deployment` reference (optional) |
| API endpoint | SCM REST API | Terraform / Firewall XML API |
| Identification | `id` (UUID from SCM) | `name` (auto-generated) |
| Serialization | `to_dict()` | `to_dict()`, `to_terraform_vars()`, `to_xml()` |

### 1.3 Auto-Naming Convention

All cloud resources have auto-generated names based on the deployment configuration:

```python
# Resource Group: {customer}-{location}-{management_type}-rg
resource_group = f"{deployment.customer_name}-{deployment.location}-{deployment.management_type}-rg"

# Resources: {resource_group}-{resource_type}
firewall_name = f"{resource_group}-fw"
panorama_name = f"{resource_group}-panorama"
```

---

## 2. Base Classes

### 2.1 CloudItem Base Class

**File:** `config/models/cloud/base.py`

```python
"""
Base class for cloud infrastructure items.

Cloud items differ from SCM ConfigItems:
- No folder/snippet requirement (deployment reference instead)
- Auto-generated names from naming convention
- Terraform and XML serialization methods
"""

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class CloudItem(ABC):
    """
    Base class for all cloud infrastructure items.

    Cloud items represent Azure resources managed via Terraform and
    Palo Alto devices configured via XML API.
    """

    # Class properties - override in subclasses
    item_type: Optional[str] = None
    terraform_resource_type: Optional[str] = None  # e.g., "azurerm_virtual_machine"

    def __init__(self, raw_config: Dict[str, Any], deployment: 'CloudDeployment' = None):
        """
        Initialize cloud item.

        Args:
            raw_config: Configuration dictionary
            deployment: Parent CloudDeployment for naming context
        """
        self.raw_config = raw_config.copy()
        self.deployment = deployment

        # Name can be explicit or auto-generated
        self._explicit_name = raw_config.get('name')

        # Metadata
        self.metadata = raw_config.get('metadata', {})

        # State tracking
        self.deployed = False
        self.deploy_error: Optional[str] = None

    @property
    def name(self) -> str:
        """
        Get resource name.

        Returns explicit name if set, otherwise auto-generates from deployment.
        """
        if self._explicit_name:
            return self._explicit_name
        return self._generate_name()

    @abstractmethod
    def _generate_name(self) -> str:
        """
        Generate name from deployment context.

        Returns:
            Auto-generated resource name
        """
        pass

    @property
    def resource_group(self) -> Optional[str]:
        """Get resource group from deployment"""
        if self.deployment:
            return self.deployment.resource_group
        return None

    # ========== Serialization Methods ==========

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation
        """
        import json
        data = json.loads(json.dumps(self.raw_config))
        data['item_type'] = self.item_type
        data['name'] = self.name  # Include resolved name
        data['deployed'] = self.deployed
        data['deploy_error'] = self.deploy_error
        data['metadata'] = json.loads(json.dumps(self.metadata)) if self.metadata else {}
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], deployment: 'CloudDeployment' = None) -> 'CloudItem':
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation
            deployment: Parent deployment for context

        Returns:
            CloudItem instance
        """
        instance = cls(data, deployment)
        if 'deployed' in data:
            instance.deployed = data['deployed']
        if 'deploy_error' in data:
            instance.deploy_error = data['deploy_error']
        return instance

    def to_terraform_vars(self) -> Dict[str, Any]:
        """
        Generate Terraform variable values for this resource.

        Override in subclasses for resource-specific variables.

        Returns:
            Dictionary of Terraform variable values
        """
        return {
            'name': self.name,
            'resource_group': self.resource_group,
        }

    # ========== Validation ==========

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Require deployment for auto-naming
        if not self._explicit_name and not self.deployment:
            errors.append(f"{self.item_type}: Name required when no deployment context")

        errors.extend(self._validate_specific())
        return errors

    def _validate_specific(self) -> List[str]:
        """Override in subclasses for specific validation"""
        return []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"
```

---

## 3. CloudDeployment Model

**File:** `config/models/cloud/deployment.py`

The CloudDeployment model contains all Azure deployment settings and implements the naming convention logic.

### 3.1 Class Definition

```python
"""
CloudDeployment model - Azure deployment settings and naming.

Handles:
- Customer/region/management type settings
- Resource group naming convention
- Virtual network configuration
- Subnet auto-generation for multiple firewalls
- Terraform state settings
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class SubnetConfig:
    """Subnet configuration"""
    name: str
    prefix: str
    purpose: str  # management, untrust, trust
    shared: bool = False
    for_firewall: Optional[str] = None  # datacenter, branch1, branch2, etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'prefix': self.prefix,
            'purpose': self.purpose,
            'shared': self.shared,
            'for_firewall': self.for_firewall,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubnetConfig':
        return cls(
            name=data['name'],
            prefix=data['prefix'],
            purpose=data.get('purpose', 'unknown'),
            shared=data.get('shared', False),
            for_firewall=data.get('for_firewall'),
        )


@dataclass
class VirtualNetworkConfig:
    """Virtual network configuration"""
    address_space: List[str] = field(default_factory=lambda: ["10.100.0.0/16"])
    subnets: List[SubnetConfig] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'address_space': self.address_space.copy(),
            'subnets': [s.to_dict() for s in self.subnets],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VirtualNetworkConfig':
        return cls(
            address_space=data.get('address_space', ["10.100.0.0/16"]),
            subnets=[SubnetConfig.from_dict(s) for s in data.get('subnets', [])],
        )


class CloudDeployment:
    """
    Azure deployment configuration.

    Manages cloud provider settings, naming conventions, and network configuration.
    This is the central settings object that all cloud resources reference.
    """

    item_type = "cloud_deployment"

    # Valid management types
    MANAGEMENT_TYPES = ['scm', 'pan']

    # Valid cloud providers (azure only for v1)
    PROVIDERS = ['azure']

    def __init__(self, raw_config: Dict[str, Any] = None):
        """
        Initialize deployment configuration.

        Args:
            raw_config: Configuration dictionary (optional)
        """
        raw_config = raw_config or {}
        self.raw_config = raw_config.copy()

        # Naming components (REQUIRED)
        self.customer_name: str = raw_config.get('customer_name', '')
        self.management_type: str = raw_config.get('management_type', 'scm')

        # Cloud provider settings
        self.provider: str = raw_config.get('provider', 'azure')
        self.subscription_id: str = raw_config.get('subscription_id', '')
        self.tenant_id: str = raw_config.get('tenant_id', '')
        self.location: str = raw_config.get('location', '')

        # Tags
        self.tags: Dict[str, str] = raw_config.get('tags', {})

        # Network configuration
        vnet_data = raw_config.get('virtual_network', {})
        self.virtual_network = VirtualNetworkConfig.from_dict(vnet_data) if vnet_data else VirtualNetworkConfig()

        # Terraform state settings
        tf_state = raw_config.get('terraform_state', {})
        self.terraform_backend: str = tf_state.get('backend', 'local')
        self.terraform_encrypt: bool = tf_state.get('encrypt', True)
        self.terraform_state_path: Optional[str] = tf_state.get('path')

        # Metadata
        self.metadata: Dict[str, Any] = raw_config.get('metadata', {})

    # ========== Naming Convention Properties ==========

    @property
    def resource_group(self) -> str:
        """
        Generate resource group name from naming convention.

        Format: {customer}-{location}-{management_type}-rg

        Returns:
            Resource group name
        """
        if not self.customer_name or not self.location:
            return ""
        return f"{self.customer_name}-{self.location}-{self.management_type}-rg"

    @property
    def vnet_name(self) -> str:
        """Virtual network name"""
        rg = self.resource_group
        return f"{rg}-vnet" if rg else ""

    def get_subnet_name(self, purpose: str, firewall_id: Optional[str] = None) -> str:
        """
        Generate subnet name.

        Args:
            purpose: Subnet purpose (management, untrust, trust)
            firewall_id: Firewall identifier for dedicated trust subnets

        Returns:
            Subnet name
        """
        rg = self.resource_group
        if not rg:
            return ""

        if purpose == 'trust' and firewall_id and firewall_id != 'datacenter':
            return f"{rg}-trust-{firewall_id}-subnet"
        return f"{rg}-{purpose}-subnet"

    # ========== Subnet Management ==========

    def ensure_default_subnets(self):
        """
        Ensure default subnets exist (management, untrust, datacenter trust).

        Called automatically when deployment is configured.
        """
        if not self.virtual_network.subnets:
            self._create_default_subnets()

    def _create_default_subnets(self):
        """Create default subnet configuration"""
        base_prefix = self.virtual_network.address_space[0] if self.virtual_network.address_space else "10.100.0.0/16"

        # Extract base octets (e.g., "10.100" from "10.100.0.0/16")
        parts = base_prefix.split('.')
        base = f"{parts[0]}.{parts[1]}"

        self.virtual_network.subnets = [
            SubnetConfig(
                name=self.get_subnet_name('mgmt'),
                prefix=f"{base}.0.0/24",
                purpose='management',
            ),
            SubnetConfig(
                name=self.get_subnet_name('untrust'),
                prefix=f"{base}.1.0/24",
                purpose='untrust',
                shared=True,
            ),
            SubnetConfig(
                name=self.get_subnet_name('trust'),
                prefix=f"{base}.2.0/24",
                purpose='trust',
                for_firewall='datacenter',
            ),
        ]

    def add_branch_subnet(self, branch_id: str, prefix: Optional[str] = None) -> SubnetConfig:
        """
        Add a dedicated trust subnet for a branch firewall.

        Args:
            branch_id: Branch identifier (branch1, branch2, etc.)
            prefix: Optional CIDR prefix (auto-calculated if not provided)

        Returns:
            Created SubnetConfig
        """
        if not prefix:
            # Auto-calculate next available /24
            prefix = self._next_available_prefix()

        subnet = SubnetConfig(
            name=self.get_subnet_name('trust', branch_id),
            prefix=prefix,
            purpose='trust',
            for_firewall=branch_id,
        )
        self.virtual_network.subnets.append(subnet)
        return subnet

    def _next_available_prefix(self) -> str:
        """Calculate next available /24 prefix"""
        existing_third_octets = []
        for subnet in self.virtual_network.subnets:
            parts = subnet.prefix.split('.')
            if len(parts) >= 3:
                existing_third_octets.append(int(parts[2]))

        next_octet = max(existing_third_octets, default=2) + 1

        base_prefix = self.virtual_network.address_space[0] if self.virtual_network.address_space else "10.100.0.0/16"
        parts = base_prefix.split('.')
        return f"{parts[0]}.{parts[1]}.{next_octet}.0/24"

    def get_subnet_for_firewall(self, firewall_type: str, firewall_id: str) -> Optional[SubnetConfig]:
        """
        Get trust subnet for a specific firewall.

        Args:
            firewall_type: 'datacenter' or 'branch'
            firewall_id: Firewall identifier

        Returns:
            SubnetConfig or None
        """
        target = firewall_id if firewall_type == 'branch' else 'datacenter'
        for subnet in self.virtual_network.subnets:
            if subnet.purpose == 'trust' and subnet.for_firewall == target:
                return subnet
        return None

    # ========== Serialization ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        import json
        return {
            'item_type': self.item_type,
            'customer_name': self.customer_name,
            'management_type': self.management_type,
            'provider': self.provider,
            'subscription_id': self.subscription_id,
            'tenant_id': self.tenant_id,
            'location': self.location,
            'resource_group': self.resource_group,  # Computed, read-only
            'tags': json.loads(json.dumps(self.tags)),
            'virtual_network': self.virtual_network.to_dict(),
            'terraform_state': {
                'backend': self.terraform_backend,
                'encrypt': self.terraform_encrypt,
                'path': self.terraform_state_path,
            },
            'metadata': json.loads(json.dumps(self.metadata)) if self.metadata else {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CloudDeployment':
        """Deserialize from dictionary"""
        return cls(data)

    def to_terraform_vars(self) -> Dict[str, Any]:
        """
        Generate Terraform variable values.

        Returns:
            Dictionary for terraform.tfvars
        """
        return {
            'customer_name': self.customer_name,
            'resource_group_name': self.resource_group,
            'location': self.location,
            'subscription_id': self.subscription_id,
            'tenant_id': self.tenant_id,
            'vnet_name': self.vnet_name,
            'vnet_address_space': self.virtual_network.address_space,
            'subnets': {
                s.name: {
                    'prefix': s.prefix,
                    'purpose': s.purpose,
                }
                for s in self.virtual_network.subnets
            },
            'tags': self.tags,
        }

    # ========== Validation ==========

    def validate(self) -> List[str]:
        """Validate deployment configuration"""
        errors = []

        if not self.customer_name:
            errors.append("Customer name is required")

        if self.management_type not in self.MANAGEMENT_TYPES:
            errors.append(f"Invalid management type: {self.management_type}. Must be one of: {self.MANAGEMENT_TYPES}")

        if self.provider not in self.PROVIDERS:
            errors.append(f"Invalid provider: {self.provider}. Must be one of: {self.PROVIDERS}")

        if not self.location:
            errors.append("Location is required")

        if self.provider == 'azure':
            if not self.subscription_id:
                errors.append("Azure subscription_id is required")
            if not self.tenant_id:
                errors.append("Azure tenant_id is required")

        if not self.virtual_network.address_space:
            errors.append("Virtual network address space is required")

        return errors

    def __repr__(self) -> str:
        return f"<CloudDeployment(resource_group='{self.resource_group}')>"
```

### 3.2 Naming Utility Functions

**File:** `config/models/cloud/naming.py`

```python
"""
Naming convention utilities for cloud resources.

All resource names follow the pattern:
  {customer}-{region}-{management_type}-rg  (resource group)
  {resource_group}-{resource_type}          (individual resources)
"""

import re
from typing import Optional


def sanitize_name(name: str, max_length: int = 63) -> str:
    """
    Sanitize name for Azure resource naming.

    Azure naming rules:
    - Alphanumeric and hyphens only
    - Cannot start or end with hyphen
    - Various length limits (typically 63 chars)

    Args:
        name: Raw name to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized name
    """
    # Convert to lowercase
    name = name.lower()

    # Replace underscores and spaces with hyphens
    name = re.sub(r'[_\s]+', '-', name)

    # Remove any character that's not alphanumeric or hyphen
    name = re.sub(r'[^a-z0-9-]', '', name)

    # Remove leading/trailing hyphens
    name = name.strip('-')

    # Collapse multiple hyphens
    name = re.sub(r'-+', '-', name)

    # Truncate to max length
    if len(name) > max_length:
        name = name[:max_length].rstrip('-')

    return name


def generate_resource_group_name(
    customer: str,
    location: str,
    management_type: str
) -> str:
    """
    Generate resource group name.

    Format: {customer}-{location}-{management_type}-rg

    Args:
        customer: Customer name
        location: Azure region (e.g., eastus)
        management_type: scm or pan

    Returns:
        Resource group name
    """
    customer = sanitize_name(customer, 20)
    location = sanitize_name(location, 20)
    management_type = sanitize_name(management_type, 5)

    return f"{customer}-{location}-{management_type}-rg"


def generate_resource_name(
    resource_group: str,
    resource_type: str,
    index: Optional[int] = None
) -> str:
    """
    Generate individual resource name.

    Format: {resource_group}-{resource_type}[{index}]

    Args:
        resource_group: Resource group name
        resource_type: Type identifier (fw, panorama, server, etc.)
        index: Optional numeric index for multiple resources

    Returns:
        Resource name
    """
    name = f"{resource_group}-{resource_type}"
    if index is not None:
        name = f"{name}{index}"
    return sanitize_name(name)


def generate_vm_username(resource_group: str) -> str:
    """
    Generate VM admin username.

    Format: {resource_group}_admin (with sanitization)

    Args:
        resource_group: Resource group name

    Returns:
        Admin username
    """
    # Replace hyphens with underscores for username
    base = resource_group.replace('-', '_')
    return f"{base}_admin"[:20]  # Azure username max 20 chars
```

---

## 4. CloudFirewall Model

**File:** `config/models/cloud/firewall.py`

### 4.1 Class Definition

```python
"""
CloudFirewall model - VM-Series firewall configuration.

Represents a Palo Alto firewall VM to be deployed in Azure:
- VM settings (size, image, availability zone)
- Network interfaces (management, untrust, trust)
- Device configuration (hostname, DNS, NTP)
- Security configuration (zones, interfaces, policies)
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from .base import CloudItem
import logging

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
        if not self.interfaces:
            self._create_default_interfaces()

        # Device configuration
        device_data = raw_config.get('device', {})
        self.device = DeviceConfig.from_dict(device_data)

        # Credential reference
        self.credentials_ref: str = raw_config.get('credentials_ref', 'firewall')

        # Deployed resource info (populated after deployment)
        self.management_ip: Optional[str] = None
        self.untrust_ip: Optional[str] = None

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
        firewall_id = f"branch{self.index}" if self.firewall_type == self.TYPE_BRANCH else None
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
        vars = super().to_terraform_vars()
        vars.update({
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
        return vars

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
```

---

## 5. CloudPanorama Model

**File:** `config/models/cloud/panorama.py`

### 5.1 Class Definition

```python
"""
CloudPanorama model - Panorama management server configuration.

Represents a Panorama VM for initial deployment:
- VM settings and network interface
- Licensing status tracking
- Plugin configuration
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from .base import CloudItem
from .firewall import VMImageConfig, VMSettings, NetworkInterfaceConfig, DeviceConfig
import logging

logger = logging.getLogger(__name__)


@dataclass
class PanoramaVMSettings(VMSettings):
    """Panorama-specific VM settings"""
    size: str = "Standard_DS4_v2"  # Panorama needs more resources
    image: VMImageConfig = field(default_factory=lambda: VMImageConfig(
        publisher="paloaltonetworks",
        offer="panorama",
        sku="byol",
        version="latest",
    ))


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
            self.interface = NetworkInterfaceConfig(
                name="management",
                subnet_name=self.deployment.get_subnet_name('mgmt'),
                public_ip=True,
            )
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
        from datetime import datetime
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
        vars = super().to_terraform_vars()
        vars.update({
            'panorama_name': self.name,
            'vm_size': self.vm_settings.size,
            'vm_image': self.vm_settings.image.to_dict(),
            'interface_subnet': self.interface.subnet_name if self.interface else None,
            'public_ip': self.interface.public_ip if self.interface else True,
        })
        return vars

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
```

---

## 6. Supporting VM Models

**File:** `config/models/cloud/supporting_vms.py`

### 6.1 Class Definitions

```python
"""
Supporting VM models - Servers, clients, and ZTNA connectors.

These are auxiliary VMs deployed alongside firewalls for testing:
- ServerVM: Backend servers (web, app, database)
- ClientVM: User workstations (Windows, Linux)
- ZTNAConnectorVM: ZTNA connector appliance
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from .base import CloudItem
from .firewall import VMImageConfig, VMSettings, NetworkInterfaceConfig
import logging

logger = logging.getLogger(__name__)


class OSType(str, Enum):
    """Operating system types"""
    LINUX = "linux"
    WINDOWS = "windows"


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
    terraform_resource_type = "azurerm_linux_virtual_machine"

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
            return WindowsImageConfig()
        return LinuxImageConfig()

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
            'vm_settings': self.vm_settings.to_dict(),
            'interface': self.interface.to_dict() if self.interface else None,
            'index': self.index,
            'credentials_ref': self.credentials_ref,
            'private_ip': self.private_ip,
            'public_ip': self.public_ip,
        })
        return data


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any], deployment: 'CloudDeployment' = None) -> 'ServerVM':
        instance = cls(data, deployment)
        return instance


class ClientVM(SupportingVM):
    """
    Client VM - User workstation for testing.

    Can be Windows or Linux with optional GlobalProtect installation.
    """

    item_type = "client_vm"
    vm_type = "client"

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

    @classmethod
    def from_dict(cls, data: Dict[str, Any], deployment: 'CloudDeployment' = None) -> 'ClientVM':
        instance = cls(data, deployment)
        return instance


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
        self.vm_settings.image = ZTNAImageConfig()

    def _generate_name(self) -> str:
        if not self.deployment:
            return "ztna"
        rg = self.deployment.resource_group
        if self.index is not None:
            return f"{rg}-ztna{self.index}"
        return f"{rg}-ztna"

    @classmethod
    def from_dict(cls, data: Dict[str, Any], deployment: 'CloudDeployment' = None) -> 'ZTNAConnectorVM':
        instance = cls(data, deployment)
        return instance
```

---

## 7. WorkflowState Model

**File:** `config/models/cloud/workflow_state.py`

### 7.1 Class Definition

```python
"""
WorkflowState model - Deployment workflow state tracking.

Enables pause/resume of deployments by tracking:
- Current phase
- Phase status and timestamps
- Terraform outputs
- User notes
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PhaseStatus(str, Enum):
    """Workflow phase status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowPhase(str, Enum):
    """Deployment workflow phases"""
    CONFIG_COMPLETE = "config_complete"
    TERRAFORM_RUNNING = "terraform_running"
    TERRAFORM_COMPLETE = "terraform_complete"
    LICENSING_PENDING = "licensing_pending"
    FIREWALL_CONFIG = "firewall_config"
    PANORAMA_CONFIG = "panorama_config"
    SCM_CONFIG = "scm_config"
    COMPLETE = "complete"


@dataclass
class PhaseState:
    """State for a single workflow phase"""
    status: PhaseStatus = PhaseStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    awaiting: List[str] = field(default_factory=list)  # What we're waiting for

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error': self.error,
            'outputs': self.outputs.copy(),
            'awaiting': self.awaiting.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PhaseState':
        return cls(
            status=PhaseStatus(data.get('status', 'pending')),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            error=data.get('error'),
            outputs=data.get('outputs', {}),
            awaiting=data.get('awaiting', []),
        )


class WorkflowState:
    """
    Deployment workflow state manager.

    Tracks the progress of a POV deployment through all phases,
    enabling pause/resume functionality.
    """

    item_type = "workflow_state"

    def __init__(self, raw_config: Dict[str, Any] = None):
        raw_config = raw_config or {}
        self.raw_config = raw_config.copy()

        # Current phase
        self.current_phase: str = raw_config.get('current_phase', WorkflowPhase.CONFIG_COMPLETE.value)
        self.last_updated: str = raw_config.get('last_updated', datetime.utcnow().isoformat())

        # Phase states
        phases_data = raw_config.get('phases', {})
        self.phases: Dict[str, PhaseState] = {}

        # Initialize all phases
        for phase in WorkflowPhase:
            if phase.value in phases_data:
                self.phases[phase.value] = PhaseState.from_dict(phases_data[phase.value])
            else:
                self.phases[phase.value] = PhaseState()

        # User notes
        self.notes: str = raw_config.get('notes', '')

    # ========== Phase Management ==========

    def start_phase(self, phase: WorkflowPhase):
        """
        Mark a phase as started.

        Args:
            phase: Phase to start
        """
        state = self.phases[phase.value]
        state.status = PhaseStatus.IN_PROGRESS
        state.started_at = datetime.utcnow().isoformat()
        self.current_phase = phase.value
        self._update_timestamp()
        logger.info(f"Started phase: {phase.value}")

    def complete_phase(self, phase: WorkflowPhase, outputs: Dict[str, Any] = None):
        """
        Mark a phase as complete.

        Args:
            phase: Phase to complete
            outputs: Optional outputs from this phase (e.g., IPs from Terraform)
        """
        state = self.phases[phase.value]
        state.status = PhaseStatus.COMPLETE
        state.completed_at = datetime.utcnow().isoformat()
        if outputs:
            state.outputs = outputs
        self._update_timestamp()
        logger.info(f"Completed phase: {phase.value}")

    def fail_phase(self, phase: WorkflowPhase, error: str):
        """
        Mark a phase as failed.

        Args:
            phase: Phase that failed
            error: Error message
        """
        state = self.phases[phase.value]
        state.status = PhaseStatus.FAILED
        state.error = error
        self._update_timestamp()
        logger.error(f"Phase {phase.value} failed: {error}")

    def pause_for(self, phase: WorkflowPhase, awaiting: List[str]):
        """
        Pause workflow awaiting external action.

        Args:
            phase: Current phase
            awaiting: List of things we're waiting for
        """
        state = self.phases[phase.value]
        state.status = PhaseStatus.IN_PROGRESS
        state.awaiting = awaiting
        self.current_phase = phase.value
        self._update_timestamp()
        logger.info(f"Paused at phase {phase.value}, awaiting: {awaiting}")

    def skip_phase(self, phase: WorkflowPhase):
        """
        Skip a phase (e.g., Panorama config when using SCM).

        Args:
            phase: Phase to skip
        """
        state = self.phases[phase.value]
        state.status = PhaseStatus.SKIPPED
        self._update_timestamp()
        logger.info(f"Skipped phase: {phase.value}")

    def _update_timestamp(self):
        """Update last_updated timestamp"""
        self.last_updated = datetime.utcnow().isoformat()

    # ========== Query Methods ==========

    def get_phase_state(self, phase: WorkflowPhase) -> PhaseState:
        """Get state for a specific phase"""
        return self.phases[phase.value]

    def get_current_phase_state(self) -> PhaseState:
        """Get current phase state"""
        return self.phases[self.current_phase]

    @property
    def is_paused(self) -> bool:
        """Check if workflow is paused awaiting action"""
        current = self.get_current_phase_state()
        return current.status == PhaseStatus.IN_PROGRESS and len(current.awaiting) > 0

    @property
    def is_complete(self) -> bool:
        """Check if workflow is fully complete"""
        return self.current_phase == WorkflowPhase.COMPLETE.value

    @property
    def is_failed(self) -> bool:
        """Check if any phase has failed"""
        for state in self.phases.values():
            if state.status == PhaseStatus.FAILED:
                return True
        return False

    @property
    def terraform_outputs(self) -> Dict[str, Any]:
        """Get Terraform outputs (stored in terraform_complete phase)"""
        return self.phases[WorkflowPhase.TERRAFORM_COMPLETE.value].outputs

    def get_completed_phases(self) -> List[str]:
        """Get list of completed phase names"""
        return [
            name for name, state in self.phases.items()
            if state.status == PhaseStatus.COMPLETE
        ]

    def get_pending_phases(self) -> List[str]:
        """Get list of pending phase names"""
        return [
            name for name, state in self.phases.items()
            if state.status == PhaseStatus.PENDING
        ]

    # ========== Serialization ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'item_type': self.item_type,
            'current_phase': self.current_phase,
            'last_updated': self.last_updated,
            'phases': {
                name: state.to_dict()
                for name, state in self.phases.items()
            },
            'notes': self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowState':
        """Deserialize from dictionary"""
        return cls(data)

    # ========== Resume Information ==========

    def get_resume_summary(self) -> Dict[str, Any]:
        """
        Get summary for resume prompt dialog.

        Returns:
            Dictionary with phase status summary
        """
        summary = {
            'current_phase': self.current_phase,
            'last_updated': self.last_updated,
            'is_paused': self.is_paused,
            'awaiting': self.get_current_phase_state().awaiting if self.is_paused else [],
            'notes': self.notes,
            'phases': [],
        }

        # Build ordered phase list with status
        phase_order = [
            (WorkflowPhase.CONFIG_COMPLETE, "Configuration saved"),
            (WorkflowPhase.TERRAFORM_COMPLETE, "Terraform deployment"),
            (WorkflowPhase.LICENSING_PENDING, "Licensing"),
            (WorkflowPhase.FIREWALL_CONFIG, "Firewall configuration"),
            (WorkflowPhase.PANORAMA_CONFIG, "Panorama configuration"),
            (WorkflowPhase.SCM_CONFIG, "SCM configuration"),
            (WorkflowPhase.COMPLETE, "Complete"),
        ]

        for phase, label in phase_order:
            state = self.phases[phase.value]
            summary['phases'].append({
                'phase': phase.value,
                'label': label,
                'status': state.status.value,
                'is_current': phase.value == self.current_phase,
            })

        return summary

    def __repr__(self) -> str:
        return f"<WorkflowState(current='{self.current_phase}', paused={self.is_paused})>"
```

---

## 8. CloudConfig Container

**File:** `config/models/cloud/cloud_config.py`

### 8.1 Class Definition

```python
"""
CloudConfig container - Aggregates all cloud infrastructure.

Top-level container that holds:
- CloudDeployment settings
- List of CloudFirewall instances
- Optional CloudPanorama
- Supporting VMs (servers, clients, ZTNA connectors)
- WorkflowState
"""

from typing import Optional, Dict, Any, List, TypeVar, Type
import logging

from .deployment import CloudDeployment
from .firewall import CloudFirewall
from .panorama import CloudPanorama
from .supporting_vms import ServerVM, ClientVM, ZTNAConnectorVM, SupportingVM
from .workflow_state import WorkflowState

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=SupportingVM)


class CloudConfig:
    """
    Cloud infrastructure configuration container.

    Aggregates all cloud resources with convenience methods for
    adding, removing, and querying resources.
    """

    item_type = "cloud_config"

    def __init__(self, raw_config: Dict[str, Any] = None):
        raw_config = raw_config or {}
        self.raw_config = raw_config.copy()

        # Deployment settings
        deployment_data = raw_config.get('deployment', {})
        self.deployment = CloudDeployment(deployment_data) if deployment_data else None

        # Firewalls
        firewalls_data = raw_config.get('firewalls', [])
        self.firewalls: List[CloudFirewall] = [
            CloudFirewall.from_dict(f, self.deployment) for f in firewalls_data
        ]

        # Panorama (optional)
        panorama_data = raw_config.get('panorama')
        self.panorama: Optional[CloudPanorama] = (
            CloudPanorama.from_dict(panorama_data, self.deployment)
            if panorama_data else None
        )

        # Supporting VMs
        supporting_data = raw_config.get('supporting_vms', {})

        servers_data = supporting_data.get('servers', [])
        self.servers: List[ServerVM] = [
            ServerVM.from_dict(s, self.deployment) for s in servers_data
        ]

        clients_data = supporting_data.get('clients', [])
        self.clients: List[ClientVM] = [
            ClientVM.from_dict(c, self.deployment) for c in clients_data
        ]

        ztna_data = supporting_data.get('ztna_connectors', [])
        self.ztna_connectors: List[ZTNAConnectorVM] = [
            ZTNAConnectorVM.from_dict(z, self.deployment) for z in ztna_data
        ]

        # Workflow state
        workflow_data = raw_config.get('workflow_state', {})
        self.workflow_state = WorkflowState(workflow_data)

    # ========== Deployment Management ==========

    def set_deployment(self, deployment: CloudDeployment):
        """
        Set deployment configuration.

        Updates all resources with new deployment context.
        """
        self.deployment = deployment

        # Update all resources with new deployment
        for fw in self.firewalls:
            fw.deployment = deployment
        if self.panorama:
            self.panorama.deployment = deployment
        for vm in self.all_supporting_vms:
            vm.deployment = deployment

        logger.info(f"Set deployment: {deployment.resource_group}")

    # ========== Firewall Management ==========

    def add_firewall(self, firewall: CloudFirewall):
        """Add a firewall"""
        firewall.deployment = self.deployment

        # Auto-assign index if multiple of same type
        same_type = [f for f in self.firewalls if f.firewall_type == firewall.firewall_type]
        if same_type:
            firewall.index = len(same_type) + 1
            # Update existing firewalls to have indices
            if len(same_type) == 1 and same_type[0].index is None:
                same_type[0].index = 1

        # For branch firewalls, ensure dedicated subnet exists
        if firewall.firewall_type == CloudFirewall.TYPE_BRANCH and self.deployment:
            branch_id = f"branch{firewall.index or 1}"
            self.deployment.add_branch_subnet(branch_id)

        self.firewalls.append(firewall)
        logger.info(f"Added firewall: {firewall.name}")

    def remove_firewall(self, name: str) -> bool:
        """Remove a firewall by name"""
        for i, fw in enumerate(self.firewalls):
            if fw.name == name:
                self.firewalls.pop(i)
                logger.info(f"Removed firewall: {name}")
                return True
        return False

    def get_firewall(self, name: str) -> Optional[CloudFirewall]:
        """Get firewall by name"""
        for fw in self.firewalls:
            if fw.name == name:
                return fw
        return None

    def get_firewalls_by_type(self, firewall_type: str) -> List[CloudFirewall]:
        """Get all firewalls of a specific type"""
        return [f for f in self.firewalls if f.firewall_type == firewall_type]

    # ========== Panorama Management ==========

    def set_panorama(self, panorama: CloudPanorama):
        """Set Panorama configuration"""
        panorama.deployment = self.deployment
        self.panorama = panorama
        logger.info(f"Set Panorama: {panorama.name}")

    def remove_panorama(self):
        """Remove Panorama"""
        self.panorama = None
        logger.info("Removed Panorama")

    # ========== Supporting VM Management ==========

    @property
    def all_supporting_vms(self) -> List[SupportingVM]:
        """Get all supporting VMs"""
        return self.servers + self.clients + self.ztna_connectors

    def add_server(self, server: ServerVM):
        """Add a server VM"""
        server.deployment = self.deployment
        if len(self.servers) > 0:
            server.index = len(self.servers) + 1
            if self.servers[0].index is None:
                self.servers[0].index = 1
        self.servers.append(server)
        logger.info(f"Added server: {server.name}")

    def add_client(self, client: ClientVM):
        """Add a client VM"""
        client.deployment = self.deployment
        # Index by OS type
        same_os = [c for c in self.clients if c.os_type == client.os_type]
        if same_os:
            client.index = len(same_os) + 1
            if same_os[0].index is None:
                same_os[0].index = 1
        self.clients.append(client)
        logger.info(f"Added client: {client.name}")

    def add_ztna_connector(self, ztna: ZTNAConnectorVM):
        """Add a ZTNA connector"""
        ztna.deployment = self.deployment
        if len(self.ztna_connectors) > 0:
            ztna.index = len(self.ztna_connectors) + 1
            if self.ztna_connectors[0].index is None:
                self.ztna_connectors[0].index = 1
        self.ztna_connectors.append(ztna)
        logger.info(f"Added ZTNA connector: {ztna.name}")

    # ========== Validation ==========

    def validate(self) -> List[str]:
        """
        Validate entire cloud configuration.

        Returns:
            List of error messages
        """
        errors = []

        # Require deployment
        if not self.deployment:
            errors.append("Deployment configuration is required")
            return errors  # Can't validate further without deployment

        # Validate deployment
        errors.extend(self.deployment.validate())

        # Validate firewalls
        for fw in self.firewalls:
            fw_errors = fw.validate()
            errors.extend([f"Firewall '{fw.name}': {e}" for e in fw_errors])

        # Validate Panorama if present
        if self.panorama:
            pan_errors = self.panorama.validate()
            errors.extend([f"Panorama: {e}" for e in pan_errors])

        # Validate supporting VMs
        for vm in self.all_supporting_vms:
            vm_errors = vm.validate()
            errors.extend([f"VM '{vm.name}': {e}" for e in vm_errors])

        # Cross-validation
        if not self.firewalls and not self.panorama:
            errors.append("At least one firewall or Panorama must be configured")

        return errors

    # ========== Serialization ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'item_type': self.item_type,
            'deployment': self.deployment.to_dict() if self.deployment else None,
            'firewalls': [f.to_dict() for f in self.firewalls],
            'panorama': self.panorama.to_dict() if self.panorama else None,
            'supporting_vms': {
                'servers': [s.to_dict() for s in self.servers],
                'clients': [c.to_dict() for c in self.clients],
                'ztna_connectors': [z.to_dict() for z in self.ztna_connectors],
            },
            'workflow_state': self.workflow_state.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CloudConfig':
        """Deserialize from dictionary"""
        return cls(data)

    def to_terraform_vars(self) -> Dict[str, Any]:
        """
        Generate complete Terraform variable set.

        Returns:
            Dictionary for terraform.tfvars.json
        """
        if not self.deployment:
            return {}

        vars = self.deployment.to_terraform_vars()

        # Add firewall configs
        vars['firewalls'] = {}
        for fw in self.firewalls:
            vars['firewalls'][fw.name] = fw.to_terraform_vars()

        # Add Panorama if present
        if self.panorama:
            vars['panorama'] = self.panorama.to_terraform_vars()
            vars['create_panorama'] = True
        else:
            vars['create_panorama'] = False

        # Add supporting VMs
        vars['servers'] = {s.name: s.to_terraform_vars() for s in self.servers}
        vars['clients'] = {c.name: c.to_terraform_vars() for c in self.clients}
        vars['ztna_connectors'] = {z.name: z.to_terraform_vars() for z in self.ztna_connectors}

        return vars

    # ========== Summary ==========

    def get_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary for UI display.

        Returns:
            Summary dictionary
        """
        return {
            'resource_group': self.deployment.resource_group if self.deployment else None,
            'location': self.deployment.location if self.deployment else None,
            'management_type': self.deployment.management_type if self.deployment else None,
            'firewall_count': len(self.firewalls),
            'datacenter_firewalls': len(self.get_firewalls_by_type('datacenter')),
            'branch_firewalls': len(self.get_firewalls_by_type('branch')),
            'has_panorama': self.panorama is not None,
            'server_count': len(self.servers),
            'client_count': len(self.clients),
            'ztna_connector_count': len(self.ztna_connectors),
            'workflow_phase': self.workflow_state.current_phase,
            'is_paused': self.workflow_state.is_paused,
        }

    def __repr__(self) -> str:
        rg = self.deployment.resource_group if self.deployment else "no-deployment"
        return f"<CloudConfig(rg='{rg}', firewalls={len(self.firewalls)})>"
```

---

## 9. Factory Registration

**File:** `config/models/factory.py` (update)

### 9.1 Register Cloud Types

```python
# Add to existing ConfigItemFactory._type_registry

from .cloud import (
    CloudDeployment,
    CloudFirewall,
    CloudPanorama,
    ServerVM,
    ClientVM,
    ZTNAConnectorVM,
    CloudConfig,
    WorkflowState,
)

# In ConfigItemFactory class:
_type_registry = {
    # ... existing types ...

    # Cloud types
    'cloud_deployment': CloudDeployment,
    'cloud_firewall': CloudFirewall,
    'cloud_panorama': CloudPanorama,
    'server_vm': ServerVM,
    'client_vm': ClientVM,
    'ztna_connector_vm': ZTNAConnectorVM,
    'cloud_config': CloudConfig,
    'workflow_state': WorkflowState,
}
```

---

## 10. Integration with Configuration Container

**File:** `config/models/containers.py` (update)

### 10.1 Add Cloud to Configuration

```python
# In Configuration class:

from .cloud import CloudConfig, WorkflowState

class Configuration:
    """Top-level configuration container."""

    def __init__(self, ...):
        # ... existing initialization ...

        # Cloud infrastructure (NEW)
        cloud_data = data.get('cloud', {})
        self.cloud: Optional[CloudConfig] = (
            CloudConfig.from_dict(cloud_data) if cloud_data else None
        )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            # ... existing fields ...
            'cloud': self.cloud.to_dict() if self.cloud else None,
        }
        return data
```

---

## 11. File Structure

Create the following directory structure:

```
config/models/cloud/
├── __init__.py
├── base.py              # CloudItem base class
├── naming.py            # Naming utilities
├── deployment.py        # CloudDeployment
├── firewall.py          # CloudFirewall
├── panorama.py          # CloudPanorama
├── supporting_vms.py    # ServerVM, ClientVM, ZTNAConnectorVM
├── workflow_state.py    # WorkflowState
└── cloud_config.py      # CloudConfig container
```

### 11.1 `__init__.py`

```python
"""
Cloud infrastructure configuration models.

Provides models for Azure deployments, firewalls, Panorama, and supporting VMs.
"""

from .base import CloudItem
from .naming import (
    sanitize_name,
    generate_resource_group_name,
    generate_resource_name,
    generate_vm_username,
)
from .deployment import CloudDeployment, SubnetConfig, VirtualNetworkConfig
from .firewall import CloudFirewall, VMSettings, VMImageConfig, NetworkInterfaceConfig, DeviceConfig
from .panorama import CloudPanorama, LicensingStatus, PluginConfig
from .supporting_vms import (
    SupportingVM,
    ServerVM,
    ClientVM,
    ZTNAConnectorVM,
    ServiceConfig,
    GlobalProtectConfig,
    OSType,
)
from .workflow_state import WorkflowState, PhaseState, PhaseStatus, WorkflowPhase
from .cloud_config import CloudConfig

__all__ = [
    # Base
    'CloudItem',

    # Naming
    'sanitize_name',
    'generate_resource_group_name',
    'generate_resource_name',
    'generate_vm_username',

    # Deployment
    'CloudDeployment',
    'SubnetConfig',
    'VirtualNetworkConfig',

    # Firewall
    'CloudFirewall',
    'VMSettings',
    'VMImageConfig',
    'NetworkInterfaceConfig',
    'DeviceConfig',

    # Panorama
    'CloudPanorama',
    'LicensingStatus',
    'PluginConfig',

    # Supporting VMs
    'SupportingVM',
    'ServerVM',
    'ClientVM',
    'ZTNAConnectorVM',
    'ServiceConfig',
    'GlobalProtectConfig',
    'OSType',

    # Workflow
    'WorkflowState',
    'PhaseState',
    'PhaseStatus',
    'WorkflowPhase',

    # Container
    'CloudConfig',
]
```

---

## 12. Testing Strategy

### 12.1 Unit Tests

**File:** `tests/test_cloud_models.py`

```python
"""Unit tests for cloud infrastructure models."""

import pytest
from config.models.cloud import (
    CloudDeployment,
    CloudFirewall,
    CloudPanorama,
    ServerVM,
    ClientVM,
    ZTNAConnectorVM,
    CloudConfig,
    WorkflowState,
    WorkflowPhase,
)


class TestCloudDeployment:
    """Tests for CloudDeployment model."""

    def test_resource_group_naming(self):
        """Test resource group name generation."""
        deployment = CloudDeployment({
            'customer_name': 'acme',
            'location': 'eastus',
            'management_type': 'scm',
        })
        assert deployment.resource_group == "acme-eastus-scm-rg"

    def test_vnet_name(self):
        """Test VNet name generation."""
        deployment = CloudDeployment({
            'customer_name': 'acme',
            'location': 'eastus',
            'management_type': 'scm',
        })
        assert deployment.vnet_name == "acme-eastus-scm-rg-vnet"

    def test_validation_errors(self):
        """Test validation catches missing fields."""
        deployment = CloudDeployment({})
        errors = deployment.validate()
        assert "Customer name is required" in errors
        assert "Location is required" in errors


class TestCloudFirewall:
    """Tests for CloudFirewall model."""

    def test_name_generation(self):
        """Test firewall name generation."""
        deployment = CloudDeployment({
            'customer_name': 'acme',
            'location': 'eastus',
            'management_type': 'scm',
        })
        firewall = CloudFirewall({'type': 'datacenter'}, deployment)
        assert firewall.name == "acme-eastus-scm-rg-fw"

    def test_multiple_firewall_indexing(self):
        """Test firewall indexing for multiple firewalls."""
        deployment = CloudDeployment({
            'customer_name': 'acme',
            'location': 'eastus',
            'management_type': 'scm',
        })
        firewall = CloudFirewall({'type': 'branch', 'index': 2}, deployment)
        assert firewall.name == "acme-eastus-scm-rg-fw2"


class TestWorkflowState:
    """Tests for WorkflowState model."""

    def test_phase_progression(self):
        """Test workflow phase transitions."""
        state = WorkflowState()

        state.start_phase(WorkflowPhase.TERRAFORM_RUNNING)
        assert state.current_phase == "terraform_running"
        assert state.get_phase_state(WorkflowPhase.TERRAFORM_RUNNING).status.value == "in_progress"

        state.complete_phase(WorkflowPhase.TERRAFORM_RUNNING, {'firewall_ips': ['1.2.3.4']})
        assert state.get_phase_state(WorkflowPhase.TERRAFORM_RUNNING).status.value == "complete"

    def test_pause_resume(self):
        """Test pause/resume functionality."""
        state = WorkflowState()

        state.pause_for(WorkflowPhase.LICENSING_PENDING, ['panorama_license'])
        assert state.is_paused
        assert 'panorama_license' in state.get_current_phase_state().awaiting


class TestCloudConfig:
    """Tests for CloudConfig container."""

    def test_add_firewall_auto_indexing(self):
        """Test automatic firewall indexing."""
        config = CloudConfig()
        config.set_deployment(CloudDeployment({
            'customer_name': 'acme',
            'location': 'eastus',
            'management_type': 'scm',
        }))

        config.add_firewall(CloudFirewall({'type': 'branch'}))
        config.add_firewall(CloudFirewall({'type': 'branch'}))

        assert config.firewalls[0].index == 1
        assert config.firewalls[1].index == 2

    def test_serialization_roundtrip(self):
        """Test serialize/deserialize preserves data."""
        config = CloudConfig()
        config.set_deployment(CloudDeployment({
            'customer_name': 'acme',
            'location': 'eastus',
            'management_type': 'scm',
        }))
        config.add_firewall(CloudFirewall({'type': 'datacenter'}))

        data = config.to_dict()
        restored = CloudConfig.from_dict(data)

        assert restored.deployment.customer_name == 'acme'
        assert len(restored.firewalls) == 1
```

---

## 13. Implementation Checklist

| # | Task | File | Status |
|---|------|------|--------|
| 1.1 | Create `config/models/cloud/` directory | Directory | ☐ |
| 1.2 | Create `base.py` with CloudItem | `cloud/base.py` | ☐ |
| 1.3 | Create `naming.py` utilities | `cloud/naming.py` | ☐ |
| 1.4 | Create `deployment.py` | `cloud/deployment.py` | ☐ |
| 1.5 | Create `firewall.py` | `cloud/firewall.py` | ☐ |
| 1.6 | Create `panorama.py` | `cloud/panorama.py` | ☐ |
| 1.7 | Create `supporting_vms.py` | `cloud/supporting_vms.py` | ☐ |
| 1.8 | Create `workflow_state.py` | `cloud/workflow_state.py` | ☐ |
| 1.9 | Create `cloud_config.py` | `cloud/cloud_config.py` | ☐ |
| 1.10 | Create `__init__.py` with exports | `cloud/__init__.py` | ☐ |
| 1.11 | Update `factory.py` with cloud types | `config/models/factory.py` | ☐ |
| 1.12 | Update `containers.py` with CloudConfig | `config/models/containers.py` | ☐ |
| 1.13 | Create unit tests | `tests/test_cloud_models.py` | ☐ |
| 1.14 | Run tests and fix issues | - | ☐ |

---

*Document Version: 1.0*
*Last Updated: 2024*
*Status: DETAILED SPECIFICATION - Ready for Implementation*
