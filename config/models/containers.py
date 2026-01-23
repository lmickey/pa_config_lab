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
from config.models.cloud import CloudConfig

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
    
    def get_ike_gateways(self) -> List[ConfigItem]:
        """Get all IKE gateways"""
        return self.get_items_by_type('ike_gateway')
    
    def get_ipsec_tunnels(self) -> List[ConfigItem]:
        """Get all IPsec tunnels"""
        return self.get_items_by_type('ipsec_tunnel')
    
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
    
    Metadata includes source information, version tracking, and push history.
    """
    
    # Program version - dynamically determined from git
    try:
        from config.version import __version__ as _version
        PROGRAM_VERSION = _version
    except ImportError:
        PROGRAM_VERSION = "1.0.0"
    
    def __init__(self, 
                 source_tsg: Optional[str] = None,
                 source_tenant: Optional[str] = None,
                 source_config: Optional[str] = None,
                 load_type: Optional[str] = None,
                 saved_credentials_ref: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            source_tsg: Source Tenant Service Group ID
            source_tenant: Friendly name of source tenant (connection name)
            source_config: Source config name (friendly name if loaded from file)
            load_type: How config was loaded ('From File', 'From Pull', 'From API')
            saved_credentials_ref: Reference to saved credentials (tenant name)
        """
        self.folders: Dict[str, FolderConfig] = {}
        self.snippets: Dict[str, SnippetConfig] = {}
        self.infrastructure: InfrastructureConfig = InfrastructureConfig()

        # Cloud infrastructure (POV deployments)
        self.cloud: Optional[CloudConfig] = None

        # Metadata
        self.source_tsg = source_tsg
        self.source_tenant = source_tenant  # Friendly tenant name
        self.source_config = source_config  # Friendly config name (when loaded from file)
        self.load_type = load_type  # 'From File', 'From Pull', 'From API'
        self.saved_credentials_ref = saved_credentials_ref
        
        # Version tracking
        self.program_version: str = self.PROGRAM_VERSION  # Version of program that created/modified this
        self.config_version: int = 1  # Increments each time config is saved
        self.created_at: Optional[str] = None
        self.modified_at: Optional[str] = None
        
        # Push history (for future use)
        self.push_history: List[Dict[str, Any]] = []
        # Format: [{'timestamp': '...', 'destination_tsg': '...', 'items_pushed': N, 'status': 'success/failure', ...}]
    
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
    
    def save_to_file(
        self, 
        file_path: str, 
        compress: bool = False, 
        description: Optional[str] = None,
        password: Optional[str] = None,
        friendly_name: Optional[str] = None
    ) -> None:
        """
        Save configuration to file, optionally with encryption.
        
        Serializes all folders, snippets, infrastructure, metadata, and history
        to a JSON file. If password is provided, encrypts the file using AES-256.
        
        Args:
            file_path: Path to save configuration file (.json, .json.gz, or .pac)
            compress: Whether to compress with gzip (default: False, ignored if encrypted)
            description: Optional description to include in metadata
            password: If provided, encrypt the file with this password
            friendly_name: Optional friendly name for display (used with encryption)
            
        Raises:
            IOError: If file cannot be written
            ValueError: If configuration is invalid
        """
        import json
        import gzip
        from pathlib import Path
        from datetime import datetime
        
        logger.info(f"Saving configuration to {file_path}")
        logger.debug(f"Compress: {compress}, Description: {description}, Encrypted: {bool(password)}")
        
        # Update timestamps - modified_at is always updated on save
        # created_at should already be set from pull; only set if missing
        self.modified_at = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = self.modified_at
        
        # Update program version to current version
        self.program_version = self.PROGRAM_VERSION
        
        # Increment config version on each save (if not first save)
        if not hasattr(self, 'config_version') or self.config_version is None:
            self.config_version = 1
        else:
            self.config_version += 1
        
        # Build configuration dictionary
        config_dict = {
            "program_version": self.program_version,
            "config_version": self.config_version,
            "format_version": "1.0",
            "metadata": {
                "source_tsg": self.source_tsg,
                "source_tenant": getattr(self, 'source_tenant', None),
                "source_config": getattr(self, 'source_config', None),
                "load_type": self.load_type,
                "saved_credentials_ref": self.saved_credentials_ref,
                "created_at": self.created_at,
                "modified_at": self.modified_at,
                "description": description
            },
            "push_history": self.push_history,
            "folders": {},
            "snippets": {},
            "infrastructure": {
                "items": []
            },
            "cloud": None,
            "stats": {}
        }
        
        logger.debug(f"Serializing {len(self.folders)} folders")
        # Serialize folders
        for folder_name, folder in self.folders.items():
            config_dict["folders"][folder_name] = {
                "parent": folder.parent,
                "items": [item.to_dict(include_id=True) for item in folder.items]
            }
            logger.debug(f"  Folder '{folder_name}': {len(folder.items)} items")
        
        logger.debug(f"Serializing {len(self.snippets)} snippets")
        # Serialize snippets
        for snippet_name, snippet in self.snippets.items():
            config_dict["snippets"][snippet_name] = {
                "items": [item.to_dict(include_id=True) for item in snippet.items]
            }
            logger.debug(f"  Snippet '{snippet_name}': {len(snippet.items)} items")
        
        logger.debug(f"Serializing infrastructure")
        # Serialize infrastructure
        config_dict["infrastructure"]["items"] = [
            item.to_dict(include_id=True) for item in self.infrastructure.items
        ]
        logger.debug(f"  Infrastructure: {len(self.infrastructure.items)} items")

        # Serialize cloud infrastructure (if present)
        if self.cloud:
            logger.debug("Serializing cloud infrastructure")
            config_dict["cloud"] = self.cloud.to_dict()
            logger.debug(f"  Cloud: {len(self.cloud.firewalls)} firewalls, panorama={self.cloud.panorama is not None}")

        # Generate stats
        all_items = self.get_all_items()
        items_by_type = {}
        for item in all_items:
            items_by_type[item.item_type] = items_by_type.get(item.item_type, 0) + 1
        
        config_dict["stats"] = {
            "total_items": len(all_items),
            "items_by_type": items_by_type,
            "folders_count": len(self.folders),
            "snippets_count": len(self.snippets),
            "infrastructure_count": len(self.infrastructure.items)
        }
        
        logger.info(f"Configuration prepared: {config_dict['stats']['total_items']} total items")
        
        # Write to file
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first (atomic write)
        temp_path = file_path_obj.with_suffix(file_path_obj.suffix + '.tmp')
        
        try:
            logger.debug(f"Writing to temporary file: {temp_path}")
            
            if password:
                # Encrypted save
                from config.utils.encryption import encrypt_config
                
                # Prepare metadata for encryption wrapper
                enc_metadata = {
                    "name": friendly_name or "Configuration",
                    "description": description or "",
                    "created_at": self.created_at,
                    "source_tenant": getattr(self, 'source_tenant', None),
                    "source_tsg": self.source_tsg,
                    "pull_date": self.created_at,
                    "item_count": config_dict["stats"]["total_items"],
                    "folders_count": config_dict["stats"]["folders_count"],
                    "snippets_count": config_dict["stats"]["snippets_count"],
                }
                
                encrypted = encrypt_config(config_dict, password, enc_metadata)
                
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(encrypted, f, indent=2)
                logger.debug("Wrote encrypted file")
                
            elif compress or file_path.endswith('.gz'):
                with gzip.open(temp_path, 'wt', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2, sort_keys=False)
                logger.debug("Wrote compressed file")
            else:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2, sort_keys=False)
                logger.debug("Wrote uncompressed file")
            
            # Move temp file to final location (atomic)
            temp_path.rename(file_path_obj)
            logger.info(f"Configuration saved successfully to {file_path}")
            logger.info(f"File size: {file_path_obj.stat().st_size} bytes")
            
        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            logger.error(f"Failed to save configuration: {e}", exc_info=True)
            raise IOError(f"Failed to save configuration to {file_path}: {e}") from e
    
    @classmethod
    def load_from_file(
        cls, 
        file_path: str, 
        strict: bool = True, 
        on_error: str = "fail",
        password: Optional[str] = None
    ) -> 'Configuration':
        """
        Load configuration from file, with optional decryption.
        
        Deserializes a JSON file created by save_to_file() and recreates the complete
        Configuration object with all folders, snippets, infrastructure, and metadata.
        If the file is encrypted, a password must be provided.
        
        Args:
            file_path: Path to configuration file (.json, .json.gz, or .pac)
            strict: If True, fail on any validation error. If False, allow partial load (default: True)
            on_error: How to handle errors: "fail" (raise), "warn" (log warning), "skip" (silent) (default: "fail")
            password: Password for encrypted files (required if file is encrypted)
            
        Returns:
            Configuration instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid, incompatible, or password is wrong/missing
            IOError: If file cannot be read
        """
        import json
        import gzip
        from pathlib import Path
        from datetime import datetime
        from config.models.factory import ConfigItemFactory
        
        logger.info(f"Loading configuration from {file_path}")
        logger.debug(f"Strict: {strict}, On error: {on_error}")
        
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Read file (handle compressed, uncompressed, and encrypted)
        try:
            logger.debug("Reading file")
            if file_path.endswith('.gz'):
                with gzip.open(file_path_obj, 'rt', encoding='utf-8') as f:
                    config_dict = json.load(f)
                logger.debug("Loaded compressed file")
            else:
                with open(file_path_obj, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                logger.debug("Loaded uncompressed file")
        except Exception as e:
            logger.error(f"Failed to read configuration file: {e}")
            raise IOError(f"Failed to read configuration file {file_path}: {e}") from e
        
        # Check if file is encrypted
        if config_dict.get('format') == 'pac_encrypted_v1':
            logger.info("File is encrypted, decrypting...")
            if not password:
                raise ValueError("File is encrypted but no password provided")
            
            from config.utils.encryption import decrypt_config
            try:
                config_dict = decrypt_config(config_dict, password)
                logger.debug("Decrypted successfully")
            except ValueError as e:
                logger.error(f"Decryption failed: {e}")
                raise
        
        # Validate format version
        format_version = config_dict.get('format_version', '1.0')
        if not format_version.startswith('1.'):
            raise ValueError(f"Unsupported format version: {format_version}. This version supports 1.x only.")
        
        logger.info(f"Configuration format version: {format_version}")
        
        # Extract metadata
        metadata = config_dict.get('metadata', {})
        
        # Get friendly name from encrypted wrapper metadata or description
        # Try: encrypted metadata 'name' -> metadata description -> filename
        friendly_name = None
        if isinstance(config_dict.get('metadata'), dict):
            # Check if this was from encrypted file (has outer metadata with 'name')
            friendly_name = metadata.get('name') or metadata.get('description')
        if not friendly_name:
            # Use filename without extension as fallback
            friendly_name = file_path_obj.stem
        
        # Create Configuration instance
        config = cls(
            source_tsg=metadata.get('source_tsg'),
            source_tenant=metadata.get('source_tenant'),
            source_config=friendly_name,  # Friendly name of the loaded config
            load_type='From File',
            saved_credentials_ref=metadata.get('saved_credentials_ref')
        )
        
        # Restore version info
        config.program_version = config_dict.get('program_version', cls.PROGRAM_VERSION)
        config.config_version = config_dict.get('config_version', 1)
        config.created_at = metadata.get('created_at')
        config.modified_at = metadata.get('modified_at')
        config.push_history = config_dict.get('push_history', [])
        
        logger.debug(f"Metadata loaded: TSG={config.source_tsg}, Created={config.created_at}")
        
        # Track errors
        errors = []
        items_loaded = 0
        items_skipped = 0
        
        # Load folders
        folders_dict = config_dict.get('folders', {})
        logger.info(f"Loading {len(folders_dict)} folders")
        
        for folder_name, folder_data in folders_dict.items():
            logger.debug(f"Loading folder '{folder_name}'")
            folder = FolderConfig(
                name=folder_name,
                parent=folder_data.get('parent')
            )
            
            items_data = folder_data.get('items', [])
            logger.debug(f"  {len(items_data)} items in folder")
            
            for item_idx, item_data in enumerate(items_data):
                try:
                    item_type = item_data.get('item_type')
                    item_name = item_data.get('name', f'item_{item_idx}')
                    
                    if not item_type:
                        raise ValueError(f"Item missing 'item_type': {item_name}")
                    
                    logger.debug(f"    Creating {item_type} '{item_name}'")
                    item = ConfigItemFactory.create_from_dict(item_type, item_data)
                    folder.add_item(item)
                    items_loaded += 1
                    
                except Exception as e:
                    error_msg = f"Failed to load item in folder '{folder_name}': {item_data.get('name', 'unknown')}: {e}"
                    errors.append(error_msg)
                    items_skipped += 1
                    
                    if on_error == "fail" or (strict and on_error != "skip"):
                        logger.error(error_msg)
                        raise ValueError(error_msg) from e
                    elif on_error == "warn":
                        logger.warning(error_msg)
                    # on_error == "skip": silent
            
            config.add_folder(folder)
            logger.info(f"Loaded folder '{folder_name}': {len(folder.items)} items")
        
        # Load snippets
        snippets_dict = config_dict.get('snippets', {})
        logger.info(f"Loading {len(snippets_dict)} snippets")
        
        for snippet_name, snippet_data in snippets_dict.items():
            logger.debug(f"Loading snippet '{snippet_name}'")
            snippet = SnippetConfig(name=snippet_name)
            
            items_data = snippet_data.get('items', [])
            logger.debug(f"  {len(items_data)} items in snippet")
            
            for item_idx, item_data in enumerate(items_data):
                try:
                    item_type = item_data.get('item_type')
                    item_name = item_data.get('name', f'item_{item_idx}')
                    
                    if not item_type:
                        raise ValueError(f"Item missing 'item_type': {item_name}")
                    
                    logger.debug(f"    Creating {item_type} '{item_name}'")
                    item = ConfigItemFactory.create_from_dict(item_type, item_data)
                    snippet.add_item(item)
                    items_loaded += 1
                    
                except Exception as e:
                    error_msg = f"Failed to load item in snippet '{snippet_name}': {item_data.get('name', 'unknown')}: {e}"
                    errors.append(error_msg)
                    items_skipped += 1
                    
                    if on_error == "fail" or (strict and on_error != "skip"):
                        logger.error(error_msg)
                        raise ValueError(error_msg) from e
                    elif on_error == "warn":
                        logger.warning(error_msg)
            
            config.add_snippet(snippet)
            logger.info(f"Loaded snippet '{snippet_name}': {len(snippet.items)} items")
        
        # Load infrastructure
        infrastructure_dict = config_dict.get('infrastructure', {})
        items_data = infrastructure_dict.get('items', [])
        logger.info(f"Loading {len(items_data)} infrastructure items")
        
        for item_idx, item_data in enumerate(items_data):
            try:
                item_type = item_data.get('item_type')
                item_name = item_data.get('name', f'item_{item_idx}')
                
                if not item_type:
                    raise ValueError(f"Item missing 'item_type': {item_name}")
                
                logger.debug(f"  Creating {item_type} '{item_name}'")
                item = ConfigItemFactory.create_from_dict(item_type, item_data)
                config.infrastructure.add_item(item)
                items_loaded += 1
                
            except Exception as e:
                error_msg = f"Failed to load infrastructure item: {item_data.get('name', 'unknown')}: {e}"
                errors.append(error_msg)
                items_skipped += 1
                
                if on_error == "fail" or (strict and on_error != "skip"):
                    logger.error(error_msg)
                    raise ValueError(error_msg) from e
                elif on_error == "warn":
                    logger.warning(error_msg)

        # Load cloud infrastructure (if present)
        cloud_dict = config_dict.get('cloud')
        if cloud_dict:
            logger.info("Loading cloud infrastructure")
            try:
                config.cloud = CloudConfig.from_dict(cloud_dict)
                logger.info(f"Loaded cloud: {len(config.cloud.firewalls)} firewalls, panorama={config.cloud.panorama is not None}")
            except Exception as e:
                error_msg = f"Failed to load cloud infrastructure: {e}"
                errors.append(error_msg)
                if on_error == "fail" or (strict and on_error != "skip"):
                    logger.error(error_msg)
                    raise ValueError(error_msg) from e
                elif on_error == "warn":
                    logger.warning(error_msg)

        # Log summary
        logger.normal("=" * 80)
        logger.normal(f"CONFIGURATION LOADED: {items_loaded} items")
        logger.normal("=" * 80)
        logger.info(f"Load summary: {items_loaded} items loaded, {items_skipped} skipped")
        logger.info(f"Folders: {len(config.folders)}, Snippets: {len(config.snippets)}, Infrastructure: {len(config.infrastructure.items)}")
        
        if errors and on_error == "warn":
            logger.warning(f"Load completed with {len(errors)} errors (items skipped)")
        
        return config
    
    def push_to_destination(self, api_client) -> Dict[str, Any]:
        """
        Push configuration to destination tenant.
        
        TODO: Implement push logic using SelectivePushOrchestrator.
        Should validate, resolve dependencies, handle conflicts, and push items.
        
        Args:
            api_client: PrismaAccessAPIClient instance with destination connection
            
        Returns:
            Dict with push results (created, updated, failed, skipped counts)
        """
        raise NotImplementedError("push_to_destination() will be implemented in future phase")
    
    def add_push_history_entry(self, entry: Dict[str, Any]) -> None:
        """
        Add an entry to push history.
        
        Args:
            entry: Dict with push details (timestamp, destination_tsg, items_pushed, status, etc.)
        """
        self.push_history.append(entry)
        logger.info(f"Added push history entry: {entry.get('status')} to {entry.get('destination_tsg')}")
    
    def __len__(self) -> int:
        """Get total number of items across all containers"""
        return len(self.get_all_items())
    
    def __repr__(self) -> str:
        source = f", source_tsg={self.source_tsg}" if self.source_tsg else ""
        load = f", load_type={self.load_type}" if self.load_type else ""
        return f"<Configuration(folders={len(self.folders)}, snippets={len(self.snippets)}, infrastructure_items={len(self.infrastructure)}, total_items={len(self)}{source}{load})>"
