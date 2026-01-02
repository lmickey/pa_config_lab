"""
Container classes for organizing configuration items.

This module contains container classes that organize ConfigItem instances:
- FolderConfig: Represents a folder and its contents (objects, profiles, rules)
- SnippetConfig: Represents a snippet and its contents (objects, profiles, rules)
- InfrastructureConfig: Represents infrastructure items (Remote Networks, Mobile Users)
- Configuration: Top-level container for entire configuration
"""

from typing import List, Dict, Any, Optional, Union, Type
import logging
from config.models.base import ConfigItem

logger = logging.getLogger(__name__)


class FolderConfig:
    """
    Represents a folder and its contents.
    
    A folder contains objects, profiles, and rules for a specific folder location.
    All items in a FolderConfig have their 'folder' property set to this folder's name.
    """
    
    def __init__(self, name: str, parent: Optional[str] = None):
        """
        Initialize folder configuration.
        
        Args:
            name: Folder name
            parent: Parent folder name (if hierarchical)
        """
        self.name = name
        self.parent = parent
        self.items: List[ConfigItem] = []
    
    def add_item(self, item: ConfigItem) -> None:
        """Add an item to this folder"""
        if item.folder != self.name:
            raise ValueError(f"Item folder '{item.folder}' does not match folder name '{self.name}'")
        if item not in self.items:
            self.items.append(item)
            logger.debug(f"Added {item.item_type} '{item.name}' to folder '{self.name}'")
    
    def remove_item(self, item: ConfigItem) -> None:
        """Remove an item from this folder"""
        if item in self.items:
            self.items.remove(item)
            logger.debug(f"Removed {item.item_type} '{item.name}' from folder '{self.name}'")
    
    def get_item(self, name: str, item_type: Optional[str] = None) -> Optional[ConfigItem]:
        """Get an item by name and optionally by type"""
        for item in self.items:
            if item.name == name:
                if item_type is None or item.item_type == item_type:
                    return item
        return None
    
    def get_items_by_type(self, item_type: str) -> List[ConfigItem]:
        """Get all items of a specific type"""
        return [item for item in self.items if item.item_type == item_type]
    
    def get_all_items(self) -> List[ConfigItem]:
        """Get all items in this folder"""
        return self.items.copy()
    
    def filter_defaults(self) -> List[ConfigItem]:
        """Get only non-default items"""
        return [item for item in self.items if not item.is_default]
    
    def filter_enabled(self) -> List[ConfigItem]:
        """Get only enabled items (for rules)"""
        enabled = []
        for item in self.items:
            if hasattr(item, 'is_enabled'):
                if item.is_enabled:
                    enabled.append(item)
            else:
                # Non-rule items are always considered "enabled"
                enabled.append(item)
        return enabled
    
    def mark_all_for_deletion(self) -> None:
        """Mark all items in this folder for deletion"""
        for item in self.items:
            item.mark_for_deletion()
        logger.info(f"Marked all {len(self.items)} items in folder '{self.name}' for deletion")
    
    def validate_all(self) -> Dict[str, List[str]]:
        """
        Validate all items in this folder.
        
        Returns:
            Dict mapping item names to lists of validation errors
        """
        errors = {}
        for item in self.items:
            item_errors = item.validate()
            if item_errors:
                errors[item.name] = item_errors
        return errors
    
    def get_dependencies(self, item: ConfigItem) -> List[ConfigItem]:
        """
        Get dependencies of an item that exist in this folder.
        
        Args:
            item: The item to get dependencies for
            
        Returns:
            List of ConfigItem instances that this item depends on
        """
        deps = []
        dep_tuples = item.get_dependencies()
        
        for dep_type, dep_name in dep_tuples:
            dep_item = self.get_item(dep_name, dep_type)
            if dep_item:
                deps.append(dep_item)
        
        return deps
    
    def __len__(self) -> int:
        """Get number of items in this folder"""
        return len(self.items)
    
    def __repr__(self) -> str:
        parent_str = f", parent={self.parent}" if self.parent else ""
        return f"<FolderConfig(name='{self.name}'{parent_str}, items={len(self.items)})>"


class SnippetConfig:
    """
    Represents a snippet and its contents.
    
    A snippet contains objects, profiles, and rules that can be applied to multiple folders.
    Items in a SnippetConfig have their 'snippet' property set and may have 'folder' unset.
    
    Note: Tags are unique - they can have BOTH folder AND snippet properties.
    """
    
    def __init__(self, name: str, snippet_type: Optional[str] = None):
        """
        Initialize snippet configuration.
        
        Args:
            name: Snippet name
            snippet_type: Snippet type (e.g., 'predefined', 'custom')
        """
        self.name = name
        self.snippet_type = snippet_type
        self.items: List[ConfigItem] = []
    
    def add_item(self, item: ConfigItem) -> None:
        """Add an item to this snippet"""
        if item.snippet != self.name:
            raise ValueError(f"Item snippet '{item.snippet}' does not match snippet name '{self.name}'")
        if item not in self.items:
            self.items.append(item)
            logger.debug(f"Added {item.item_type} '{item.name}' to snippet '{self.name}'")
    
    def remove_item(self, item: ConfigItem) -> None:
        """Remove an item from this snippet"""
        if item in self.items:
            self.items.remove(item)
            logger.debug(f"Removed {item.item_type} '{item.name}' from snippet '{self.name}'")
    
    def get_item(self, name: str, item_type: Optional[str] = None) -> Optional[ConfigItem]:
        """Get an item by name and optionally by type"""
        for item in self.items:
            if item.name == name:
                if item_type is None or item.item_type == item_type:
                    return item
        return None
    
    def get_items_by_type(self, item_type: str) -> List[ConfigItem]:
        """Get all items of a specific type"""
        return [item for item in self.items if item.item_type == item_type]
    
    def get_all_items(self) -> List[ConfigItem]:
        """Get all items in this snippet"""
        return self.items.copy()
    
    def filter_defaults(self) -> List[ConfigItem]:
        """Get only non-default items"""
        return [item for item in self.items if not item.is_default]
    
    def filter_enabled(self) -> List[ConfigItem]:
        """Get only enabled items (for rules)"""
        enabled = []
        for item in self.items:
            if hasattr(item, 'is_enabled'):
                if item.is_enabled:
                    enabled.append(item)
            else:
                # Non-rule items are always considered "enabled"
                enabled.append(item)
        return enabled
    
    def mark_all_for_deletion(self) -> None:
        """Mark all items in this snippet for deletion"""
        for item in self.items:
            item.mark_for_deletion()
        logger.info(f"Marked all {len(self.items)} items in snippet '{self.name}' for deletion")
    
    def validate_all(self) -> Dict[str, List[str]]:
        """
        Validate all items in this snippet.
        
        Returns:
            Dict mapping item names to lists of validation errors
        """
        errors = {}
        for item in self.items:
            item_errors = item.validate()
            if item_errors:
                errors[item.name] = item_errors
        return errors
    
    def get_dependencies(self, item: ConfigItem) -> List[ConfigItem]:
        """
        Get dependencies of an item that exist in this snippet.
        
        Args:
            item: The item to get dependencies for
            
        Returns:
            List of ConfigItem instances that this item depends on
        """
        deps = []
        dep_tuples = item.get_dependencies()
        
        for dep_type, dep_name in dep_tuples:
            dep_item = self.get_item(dep_name, dep_type)
            if dep_item:
                deps.append(dep_item)
        
        return deps
    
    def __len__(self) -> int:
        """Get number of items in this snippet"""
        return len(self.items)
    
    def __repr__(self) -> str:
        type_str = f", type={self.snippet_type}" if self.snippet_type else ""
        return f"<SnippetConfig(name='{self.name}'{type_str}, items={len(self.items)})>"


class InfrastructureConfig:
    """
    Represents infrastructure configuration items.
    
    Infrastructure items include:
    - Remote Networks: IKE/IPsec crypto profiles, gateways, tunnels, service connections
    - Mobile Users: Agent profiles, portals, gateways
    
    All infrastructure items MUST have 'folder' property set.
    Infrastructure is organized by category rather than location.
    """
    
    # Remote Networks infrastructure types
    REMOTE_NETWORK_TYPES = {
        'ike_crypto_profile',
        'ipsec_crypto_profile',
        'ike_gateway',
        'ipsec_tunnel',
        'service_connection',
    }
    
    # Mobile Users infrastructure types
    MOBILE_USER_TYPES = {
        'agent_profile',
        'portal',
        'gateway',
    }
    
    def __init__(self):
        """Initialize infrastructure configuration"""
        self.items: List[ConfigItem] = []
    
    def add_item(self, item: ConfigItem) -> None:
        """
        Add an infrastructure item.
        
        Args:
            item: ConfigItem to add
            
        Raises:
            ValueError: If item doesn't have folder or isn't infrastructure type
        """
        if not item.folder:
            raise ValueError(f"Infrastructure item '{item.name}' must have folder property set")
        
        if item.item_type not in (self.REMOTE_NETWORK_TYPES | self.MOBILE_USER_TYPES):
            raise ValueError(f"Item type '{item.item_type}' is not an infrastructure type")
        
        if item not in self.items:
            self.items.append(item)
            logger.debug(f"Added infrastructure {item.item_type} '{item.name}'")
    
    def remove_item(self, item: ConfigItem) -> None:
        """Remove an infrastructure item"""
        if item in self.items:
            self.items.remove(item)
            logger.debug(f"Removed infrastructure {item.item_type} '{item.name}'")
    
    def get_item(self, name: str, item_type: Optional[str] = None) -> Optional[ConfigItem]:
        """Get an item by name and optionally by type"""
        for item in self.items:
            if item.name == name:
                if item_type is None or item.item_type == item_type:
                    return item
        return None
    
    def get_items_by_type(self, item_type: str) -> List[ConfigItem]:
        """Get all items of a specific type"""
        return [item for item in self.items if item.item_type == item_type]
    
    def get_all_items(self) -> List[ConfigItem]:
        """Get all infrastructure items"""
        return self.items.copy()
    
    def get_remote_network_items(self) -> List[ConfigItem]:
        """Get all Remote Networks infrastructure items"""
        return [item for item in self.items if item.item_type in self.REMOTE_NETWORK_TYPES]
    
    def get_mobile_user_items(self) -> List[ConfigItem]:
        """Get all Mobile Users infrastructure items"""
        return [item for item in self.items if item.item_type in self.MOBILE_USER_TYPES]
    
    def get_service_connections(self) -> List[ConfigItem]:
        """Get all service connections"""
        return self.get_items_by_type('service_connection')
    
    def get_crypto_profiles(self) -> List[ConfigItem]:
        """Get all crypto profiles (IKE and IPsec)"""
        ike = self.get_items_by_type('ike_crypto_profile')
        ipsec = self.get_items_by_type('ipsec_crypto_profile')
        return ike + ipsec
    
    def filter_defaults(self) -> List[ConfigItem]:
        """Get only non-default items"""
        return [item for item in self.items if not item.is_default]
    
    def mark_all_for_deletion(self) -> None:
        """Mark all infrastructure items for deletion"""
        for item in self.items:
            item.mark_for_deletion()
        logger.info(f"Marked all {len(self.items)} infrastructure items for deletion")
    
    def validate_all(self) -> Dict[str, List[str]]:
        """
        Validate all infrastructure items.
        
        Returns:
            Dict mapping item names to lists of validation errors
        """
        errors = {}
        for item in self.items:
            item_errors = item.validate()
            if item_errors:
                errors[item.name] = item_errors
        return errors
    
    def get_dependencies(self, item: ConfigItem) -> List[ConfigItem]:
        """
        Get dependencies of an infrastructure item.
        
        Handles deep dependency chains (e.g., SC → Tunnel → Gateway → Crypto).
        
        Args:
            item: The infrastructure item to get dependencies for
            
        Returns:
            List of ConfigItem instances that this item depends on
        """
        deps = []
        dep_tuples = item.get_dependencies()
        
        for dep_type, dep_name in dep_tuples:
            dep_item = self.get_item(dep_name, dep_type)
            if dep_item:
                deps.append(dep_item)
        
        return deps
    
    def resolve_dependency_chain(self, item: ConfigItem) -> List[ConfigItem]:
        """
        Resolve full dependency chain for an infrastructure item.
        
        Example: ServiceConnection → IPsecTunnel → IKEGateway → IKECryptoProfile
        
        Args:
            item: The infrastructure item to resolve chain for
            
        Returns:
            List of all dependencies in order (deepest first)
        """
        chain = []
        visited = set()
        
        def _resolve(current_item: ConfigItem):
            if current_item.name in visited:
                return
            visited.add(current_item.name)
            
            # Get direct dependencies
            deps = self.get_dependencies(current_item)
            
            # Recursively resolve their dependencies first
            for dep in deps:
                _resolve(dep)
            
            # Add current item after its dependencies
            if current_item != item:  # Don't include the item itself
                chain.append(current_item)
        
        _resolve(item)
        return chain
    
    def __len__(self) -> int:
        """Get number of infrastructure items"""
        return len(self.items)
    
    def __repr__(self) -> str:
        rn_count = len(self.get_remote_network_items())
        mu_count = len(self.get_mobile_user_items())
        return f"<InfrastructureConfig(remote_networks={rn_count}, mobile_users={mu_count}, total={len(self.items)})>"


class Configuration:
    """
    Top-level container for entire configuration.
    
    Contains multiple FolderConfig, SnippetConfig, and InfrastructureConfig instances.
    Provides cross-container querying and dependency resolution.
    """
    
    def __init__(self):
        """Initialize configuration"""
        self.folders: Dict[str, FolderConfig] = {}
        self.snippets: Dict[str, SnippetConfig] = {}
        self.infrastructure: InfrastructureConfig = InfrastructureConfig()
    
    def add_folder(self, folder: FolderConfig) -> None:
        """Add a folder to the configuration"""
        self.folders[folder.name] = folder
        logger.debug(f"Added folder '{folder.name}' to configuration")
    
    def add_snippet(self, snippet: SnippetConfig) -> None:
        """Add a snippet to the configuration"""
        self.snippets[snippet.name] = snippet
        logger.debug(f"Added snippet '{snippet.name}' to configuration")
    
    def get_folder(self, name: str) -> Optional[FolderConfig]:
        """Get a folder by name"""
        return self.folders.get(name)
    
    def get_snippet(self, name: str) -> Optional[SnippetConfig]:
        """Get a snippet by name"""
        return self.snippets.get(name)
    
    def get_all_folders(self) -> List[FolderConfig]:
        """Get all folders"""
        return list(self.folders.values())
    
    def get_all_snippets(self) -> List[SnippetConfig]:
        """Get all snippets"""
        return list(self.snippets.values())
    
    def get_all_items(self) -> List[ConfigItem]:
        """Get all items from all containers"""
        items = []
        
        # Folder items
        for folder in self.folders.values():
            items.extend(folder.get_all_items())
        
        # Snippet items
        for snippet in self.snippets.values():
            items.extend(snippet.get_all_items())
        
        # Infrastructure items
        items.extend(self.infrastructure.get_all_items())
        
        return items
    
    def get_item(self, name: str, item_type: Optional[str] = None, location: Optional[str] = None) -> Optional[ConfigItem]:
        """
        Get an item by name across all containers.
        
        Args:
            name: Item name
            item_type: Optional item type to filter by
            location: Optional location (folder/snippet name) to search in
            
        Returns:
            First matching ConfigItem or None
        """
        # Search in specific location if provided
        if location:
            if location in self.folders:
                item = self.folders[location].get_item(name, item_type)
                if item:
                    return item
            
            if location in self.snippets:
                item = self.snippets[location].get_item(name, item_type)
                if item:
                    return item
        
        # Search in all folders
        for folder in self.folders.values():
            item = folder.get_item(name, item_type)
            if item:
                return item
        
        # Search in all snippets
        for snippet in self.snippets.values():
            item = snippet.get_item(name, item_type)
            if item:
                return item
        
        # Search in infrastructure
        item = self.infrastructure.get_item(name, item_type)
        if item:
            return item
        
        return None
    
    def get_items_by_type(self, item_type: str) -> List[ConfigItem]:
        """Get all items of a specific type across all containers"""
        items = []
        
        # Folder items
        for folder in self.folders.values():
            items.extend(folder.get_items_by_type(item_type))
        
        # Snippet items
        for snippet in self.snippets.values():
            items.extend(snippet.get_items_by_type(item_type))
        
        # Infrastructure items
        items.extend(self.infrastructure.get_items_by_type(item_type))
        
        return items
    
    def filter_defaults(self) -> List[ConfigItem]:
        """Get all non-default items across all containers"""
        items = []
        
        for folder in self.folders.values():
            items.extend(folder.filter_defaults())
        
        for snippet in self.snippets.values():
            items.extend(snippet.filter_defaults())
        
        items.extend(self.infrastructure.filter_defaults())
        
        return items
    
    def validate_all(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Validate all items in all containers.
        
        Returns:
            Nested dict: {location: {item_name: [errors]}}
        """
        all_errors = {}
        
        # Validate folders
        for folder_name, folder in self.folders.items():
            errors = folder.validate_all()
            if errors:
                all_errors[f"folder:{folder_name}"] = errors
        
        # Validate snippets
        for snippet_name, snippet in self.snippets.items():
            errors = snippet.validate_all()
            if errors:
                all_errors[f"snippet:{snippet_name}"] = errors
        
        # Validate infrastructure
        errors = self.infrastructure.validate_all()
        if errors:
            all_errors["infrastructure"] = errors
        
        return all_errors
    
    def resolve_dependencies(self, item: ConfigItem) -> List[ConfigItem]:
        """
        Resolve dependencies for an item across all containers.
        
        Args:
            item: The item to resolve dependencies for
            
        Returns:
            List of ConfigItem instances that this item depends on
        """
        deps = []
        dep_tuples = item.get_dependencies()
        
        for dep_type, dep_name in dep_tuples:
            # Try to find dependency in all containers
            dep_item = self.get_item(dep_name, dep_type)
            if dep_item:
                deps.append(dep_item)
        
        return deps
    
    def __len__(self) -> int:
        """Get total number of items across all containers"""
        return len(self.get_all_items())
    
    def __repr__(self) -> str:
        return f"<Configuration(folders={len(self.folders)}, snippets={len(self.snippets)}, infrastructure_items={len(self.infrastructure)}, total_items={len(self)})>"
