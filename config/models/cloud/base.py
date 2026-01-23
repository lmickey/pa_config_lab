"""
Base class for cloud infrastructure items.

Cloud items differ from SCM ConfigItems:
- No folder/snippet requirement (deployment reference instead)
- Auto-generated names from naming convention
- Terraform and XML serialization methods
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from abc import ABC, abstractmethod
import json
import logging

if TYPE_CHECKING:
    from .deployment import CloudDeployment

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
