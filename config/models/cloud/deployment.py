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
import json
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

    def get_subnet_by_purpose(self, purpose: str) -> Optional[SubnetConfig]:
        """
        Get subnet by purpose (first match).

        Args:
            purpose: Subnet purpose (management, untrust, trust)

        Returns:
            SubnetConfig or None
        """
        for subnet in self.virtual_network.subnets:
            if subnet.purpose == purpose:
                return subnet
        return None

    # ========== Serialization ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
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
