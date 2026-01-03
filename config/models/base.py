"""
Base classes for configuration items.

Provides ConfigItem base class and specialized base classes for different
configuration types (policies, objects, profiles, rules).
"""

from typing import Optional, Dict, Any, List, Type
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ConfigItem(ABC):
    """
    Base class for all configuration items.
    
    All configuration items (objects, policies, profiles, etc.) inherit from this class.
    Provides common properties and methods for configuration management.
    """
    
    # Class properties - override in subclasses
    api_endpoint: Optional[str] = None
    item_type: Optional[str] = None
    
    def __init__(self, raw_config: Dict[str, Any]):
        """
        Initialize configuration item from API response.
        
        Args:
            raw_config: Raw configuration dictionary from API
            
        Raises:
            ValueError: If neither folder nor snippet is set, or both are set
        """
        self.raw_config = raw_config.copy()
        
        # Core identification
        self.name = raw_config.get('name', '')
        self.id = raw_config.get('id')  # UUID from SCM API (optional, read-only)
        
        # Location - one of folder/snippet MUST be set
        self.folder = raw_config.get('folder')
        self.snippet = raw_config.get('snippet')
        
        # Validation: at least one of folder/snippet should be set
        # Note: Some items may have BOTH when a snippet is assigned to a folder
        if not self.folder and not self.snippet:
            raise ValueError(f"Either folder or snippet must be set for {self.name}")
        
        # Configuration state
        self.is_default = raw_config.get('is_default', False)
        self.push_strategy = 'create'  # Default: create, skip, overwrite, rename
        
        # Metadata
        self.metadata = raw_config.get('metadata', {})
        if not self.metadata:
            self.metadata = self._extract_metadata(raw_config)
        
        # Deletion tracking
        self.deleted = False
        self.delete_success: Optional[bool] = None  # None=not attempted, True=success, False=failed
        
        # Dependency cache (computed on demand)
        self._dependencies_cache: Optional[List[tuple]] = None
        self._parent_cache = None
        self._children_cache = None
    
    # ========== Lightweight Properties (Computed) ==========
    
    @property
    def has_parent(self) -> bool:
        """
        Check if item has a parent without loading it.
        
        Returns:
            True if item has a parent reference
        """
        # Check if parent is referenced in raw config
        if 'parent' in self.raw_config:
            return True
        
        # For groups, check if members reference other items
        if hasattr(self, '_check_parent_exists'):
            return self._check_parent_exists()
        
        return False
    
    @property
    def has_child(self) -> bool:
        """
        Check if item has children without loading them.
        
        Returns:
            True if item has child items
        """
        # Check for common child patterns in config
        child_keys = ['members', 'static', 'dynamic', 'rules', 'entries']
        for key in child_keys:
            if key in self.raw_config and self.raw_config[key]:
                return True
        
        return False
    
    @property
    def has_dependencies(self) -> bool:
        """
        Check if item has dependencies without fully loading them.
        
        Returns:
            True if item has dependencies on other config items
        """
        # Quick check without computing full dependency graph
        if self._dependencies_cache:
            return len(self._dependencies_cache) > 0
        
        # Check for common dependency patterns
        dependency_keys = [
            'source', 'destination', 'service', 'application',
            'members', 'static', 'dynamic', 'profile', 'profile_group'
        ]
        
        for key in dependency_keys:
            if key in self.raw_config:
                value = self.raw_config[key]
                # Check if it's a non-empty list or dict
                if isinstance(value, (list, dict)) and value:
                    return True
                # Check if it's a non-empty string reference
                if isinstance(value, str) and value and value not in ['any', 'none']:
                    return True
        
        return False
    
    @property
    def has_tags(self) -> bool:
        """
        Check if item has tags.
        
        Returns:
            True if item has one or more tags
        """
        tags = self.raw_config.get('tag', [])
        return isinstance(tags, list) and len(tags) > 0
    
    def get_tags(self) -> List[str]:
        """
        Get list of tag names associated with this item.
        
        Returns:
            List of tag names (empty list if no tags)
        """
        tags = self.raw_config.get('tag', [])
        if isinstance(tags, list):
            return tags.copy()
        return []
    
    # ========== Location Methods ==========
    
    def get_location(self) -> str:
        """
        Get the location (folder or snippet name) of this item.
        
        Returns:
            Folder or snippet name
        """
        return self.folder if self.folder else self.snippet
    
    def is_in_folder(self) -> bool:
        """Check if item is in a folder (vs snippet)"""
        return self.folder is not None
    
    def is_in_snippet(self) -> bool:
        """Check if item is in a snippet (vs folder)"""
        return self.snippet is not None
    
    # ========== Serialization Methods ==========
    
    def to_dict(self, include_id: bool = True) -> Dict[str, Any]:
        """
        Serialize item to JSON-compatible dictionary.
        
        IMPORTANT: Uses json.loads(json.dumps()) to ensure clean copy
        without shared references. This is slower but safer for GUI threading.
        
        Args:
            include_id: Whether to include the 'id' field (default: True)
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        import json
        
        # Use JSON serialization for clean copy (no shared references)
        # This is slower but prevents memory corruption
        data = json.loads(json.dumps(self.raw_config))
        
        # Add item_type for factory deserialization
        data['item_type'] = self.item_type
        
        # Add our tracking fields
        data['is_default'] = self.is_default
        data['push_strategy'] = self.push_strategy
        data['deleted'] = self.deleted
        data['delete_success'] = self.delete_success
        data['metadata'] = json.loads(json.dumps(self.metadata)) if self.metadata else {}
        
        # Include id if present and requested
        if include_id and self.id:
            data['id'] = self.id
        elif not include_id:
            data.pop('id', None)
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigItem':
        """
        Deserialize item from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            ConfigItem instance
        """
        # Create instance from raw_config
        instance = cls(data)
        
        # Restore tracking fields if present
        if 'push_strategy' in data:
            instance.push_strategy = data['push_strategy']
        if 'deleted' in data:
            instance.deleted = data['deleted']
        if 'delete_success' in data:
            instance.delete_success = data['delete_success']
        
        return instance
    
    # ========== Validation Methods ==========
    
    def validate(self) -> List[str]:
        """
        Validate item configuration.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not self.name:
            errors.append("Name is required")
        
        if not self.folder and not self.snippet:
            errors.append("Either folder or snippet must be set")
        
        # Note: Items CAN have both folder and snippet when snippet is assigned to folder
        
        # Subclasses can add more validation
        errors.extend(self._validate_specific())
        
        return errors
    
    def _validate_specific(self) -> List[str]:
        """
        Subclass-specific validation.
        Override in subclasses for custom validation rules.
        
        Returns:
            List of validation errors
        """
        return []
    
    # ========== Dependency Methods ==========
    
    def get_dependencies(self) -> List[tuple]:
        """
        Get all dependencies for this item.
        
        Returns:
            List of tuples: (dependency_type, dependency_name)
            Example: [('address', 'server-subnet'), ('service', 'tcp-443')]
        """
        if self._dependencies_cache is not None:
            return self._dependencies_cache
        
        # Compute dependencies (override in subclasses)
        self._dependencies_cache = self._compute_dependencies()
        return self._dependencies_cache
    
    def _compute_dependencies(self) -> List[tuple]:
        """
        Compute dependencies from configuration.
        Override in subclasses to implement specific dependency logic.
        
        Returns:
            List of (type, name) tuples
        """
        # Default: no dependencies
        return []
    
    def clear_dependency_cache(self):
        """Clear cached dependencies (call after modifications)"""
        self._dependencies_cache = None
    
    # ========== Modification Methods ==========
    
    def rename(self, new_name: str):
        """
        Rename this item.
        
        Note: This only updates the item itself. References in other items
        must be updated separately by the container.
        
        Args:
            new_name: New name for the item
        """
        old_name = self.name
        self.name = new_name
        self.raw_config['name'] = new_name
        
        logger.info(f"Renamed {self.item_type} from '{old_name}' to '{new_name}'")
    
    def mark_for_deletion(self):
        """Mark item for deletion from tenant"""
        self.deleted = True
        logger.info(f"Marked {self.item_type} '{self.name}' for deletion")
    
    def unmark_for_deletion(self):
        """Unmark item for deletion"""
        self.deleted = False
        self.delete_success = None
        logger.info(f"Unmarked {self.item_type} '{self.name}' for deletion")
    
    # ========== API Operations ==========
    
    def delete(self, api_client) -> bool:
        """
        Delete item from tenant.
        
        Args:
            api_client: PrismaAccessAPIClient instance
            
        Returns:
            True if deletion succeeded, False otherwise
        """
        if not self.id:
            logger.error(f"Cannot delete {self.name}: no ID set")
            self.delete_success = False
            return False
        
        try:
            # Use endpoint from class property
            if not self.api_endpoint:
                logger.error(f"Cannot delete {self.name}: no API endpoint defined")
                self.delete_success = False
                return False
            
            # Build URL with ID
            url = f"{self.api_endpoint}/{self.id}"
            api_client._make_request("DELETE", url, use_cache=False)
            
            self.delete_success = True
            logger.info(f"Successfully deleted {self.item_type} '{self.name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting {self.item_type} '{self.name}': {e}")
            self.delete_success = False
            return False
    
    def create(self, api_client) -> bool:
        """
        Create item on tenant.
        
        Args:
            api_client: PrismaAccessAPIClient instance
            
        Returns:
            True if creation succeeded, False otherwise
        """
        try:
            if not self.api_endpoint:
                logger.error(f"Cannot create {self.name}: no API endpoint defined")
                return False
            
            # Build URL with folder/snippet query
            url = self.api_endpoint
            if self.folder:
                url += f"?folder={self.folder}"
            elif self.snippet:
                url += f"?snippet={self.snippet}"
            
            # Remove fields that shouldn't be sent
            data = self.raw_config.copy()
            data.pop('id', None)
            data.pop('is_default', None)
            data.pop('push_strategy', None)
            data.pop('deleted', None)
            data.pop('delete_success', None)
            
            response = api_client._make_request("POST", url, data=data, use_cache=False)
            
            # Update ID from response
            if isinstance(response, dict) and 'id' in response:
                self.id = response['id']
                self.raw_config['id'] = response['id']
            
            logger.info(f"Successfully created {self.item_type} '{self.name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error creating {self.item_type} '{self.name}': {e}")
            return False
    
    def update(self, api_client) -> bool:
        """
        Update existing item on tenant.
        
        Args:
            api_client: PrismaAccessAPIClient instance
            
        Returns:
            True if update succeeded, False otherwise
        """
        if not self.id:
            logger.error(f"Cannot update {self.name}: no ID set")
            return False
        
        try:
            if not self.api_endpoint:
                logger.error(f"Cannot update {self.name}: no API endpoint defined")
                return False
            
            # Build URL with ID
            url = f"{self.api_endpoint}/{self.id}"
            
            # Remove fields that shouldn't be sent
            data = self.raw_config.copy()
            data.pop('id', None)
            data.pop('is_default', None)
            data.pop('push_strategy', None)
            data.pop('deleted', None)
            data.pop('delete_success', None)
            
            api_client._make_request("PUT", url, data=data, use_cache=False)
            
            logger.info(f"Successfully updated {self.item_type} '{self.name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error updating {self.item_type} '{self.name}': {e}")
            return False
    
    def refresh(self, api_client) -> str:
        """
        Refresh item from tenant and return status.
        
        Args:
            api_client: PrismaAccessAPIClient instance
            
        Returns:
            Status string:
            - "exists": Item exists and matches
            - "missing": Item not found on tenant
            - "outdated": Item exists but has different values
            - "error": Error occurred during refresh
        """
        try:
            # Fetch from API using class method
            location = self.get_location()
            is_snippet = self.is_in_snippet()
            
            current = self.__class__.get(api_client, self.name, location, is_snippet)
            
            if not current:
                logger.info(f"{self.item_type} '{self.name}' not found on tenant")
                return "missing"
            
            # Compare timestamps or content
            if self._is_outdated(current):
                logger.info(f"{self.item_type} '{self.name}' is outdated")
                return "outdated"
            
            logger.info(f"{self.item_type} '{self.name}' exists and is current")
            return "exists"
            
        except Exception as e:
            logger.error(f"Error refreshing {self.item_type} '{self.name}': {e}")
            return "error"
    
    def _is_outdated(self, current: 'ConfigItem') -> bool:
        """
        Check if current version is outdated compared to tenant version.
        
        Args:
            current: Current version from tenant
            
        Returns:
            True if local version is outdated
        """
        # Compare updated timestamps if available
        local_updated = self.metadata.get('updated', '')
        current_updated = current.metadata.get('updated', '')
        
        if local_updated and current_updated:
            return local_updated < current_updated
        
        # If no timestamps, assume it's current
        return False
    
    @classmethod
    def get(cls, api_client, name: str, location: str, is_snippet: bool = False) -> Optional['ConfigItem']:
        """
        Fetch single item from API by name.
        
        Args:
            api_client: PrismaAccessAPIClient instance
            name: Item name
            location: Folder or snippet name
            is_snippet: True if location is a snippet, False if folder
            
        Returns:
            ConfigItem instance or None if not found
        """
        if not cls.api_endpoint:
            logger.error(f"Cannot fetch {name}: no API endpoint defined for {cls.__name__}")
            return None
        
        try:
            # Build query: ?folder=X or ?snippet=X
            query_param = "snippet" if is_snippet else "folder"
            url = f"{cls.api_endpoint}?{query_param}={location}"
            
            # Get all items (API doesn't support name filter)
            response = api_client._make_request("GET", url)
            items = response.get('data', []) if isinstance(response, dict) else response
            
            # Find item by name
            for item in items:
                if item.get('name') == name:
                    return cls(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching {cls.__name__} '{name}' from {location}: {e}")
            return None
    
    # ========== Helper Methods ==========
    
    def _extract_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata fields from raw config.
        
        Args:
            data: Raw configuration data
            
        Returns:
            Metadata dictionary
        """
        return {
            "created": data.get("created", ""),
            "updated": data.get("updated", ""),
            "created_by": data.get("created_by", ""),
            "updated_by": data.get("updated_by", ""),
        }
    
    def __repr__(self) -> str:
        """String representation of item"""
        location = f"folder={self.folder}" if self.folder else f"snippet={self.snippet}"
        return f"<{self.__class__.__name__}(name='{self.name}', {location})>"
    
    def __str__(self) -> str:
        """Human-readable string"""
        return f"{self.item_type}: {self.name} ({self.get_location()})"


# ========== Specialized Base Classes ==========

class PolicyItem(ConfigItem):
    """Base class for all policy/rule items"""
    pass


class ObjectItem(ConfigItem):
    """Base class for all object items"""
    pass


class ProfileItem(ConfigItem):
    """Base class for all profile items"""
    pass


class RuleItem(PolicyItem):
    """
    Base class for all rule types.
    
    Rules have common properties like position, enabled state, logging.
    """
    
    @property
    def is_enabled(self) -> bool:
        """Check if rule is enabled"""
        # Most rules have 'disabled' field (inverted logic)
        if 'disabled' in self.raw_config:
            return not self.raw_config['disabled']
        return True
    
    @property
    def position(self) -> Optional[int]:
        """Get rule position in rulebase"""
        return self.raw_config.get('position')
