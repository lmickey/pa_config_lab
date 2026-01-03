"""
Configuration adapter for GUI widgets.

Provides compatibility layer for widgets to work with both:
- Old format: Dict[str, Any] (legacy saved configs)
- New format: Configuration object (Phase 10)
"""

from typing import Dict, Any, Optional, List
from config.models.containers import Configuration, FolderConfig, SnippetConfig


class ConfigAdapter:
    """
    Adapter to convert between Configuration objects and dict format.
    
    Provides a consistent interface for GUI widgets regardless of source.
    """
    
    @staticmethod
    def to_dict(config: Any) -> Optional[Dict[str, Any]]:
        """
        Convert Configuration object or dict to standardized dict format.
        
        Args:
            config: Either Configuration object or dict
            
        Returns:
            Standardized dictionary format for GUI widgets
        """
        if config is None:
            return None
        
        # If already a dict, return as-is (legacy format)
        if isinstance(config, dict):
            return config
        
        # If Configuration object, convert to dict
        if isinstance(config, Configuration):
            return ConfigAdapter._configuration_to_dict(config)
        
        # Unknown format
        return None
    
    @staticmethod
    def _configuration_to_dict(config: Configuration) -> Dict[str, Any]:
        """Convert Configuration object to dict format for GUI widgets."""
        result = {
            "metadata": {
                "program_version": getattr(config, 'program_version', Configuration.PROGRAM_VERSION),
                "config_version": getattr(config, 'config_version', 1),
                "source_tsg": config.source_tsg,
                "source_tenant": getattr(config, 'source_tenant', None),
                "source_config": getattr(config, 'source_config', None),
                "load_type": config.load_type,
                "created_at": config.created_at,
                "modified_at": config.modified_at,
                "saved_credentials_ref": config.saved_credentials_ref,
            },
            "folders": {},
            "snippets": {},
            "infrastructure": {},
            "stats": {},
        }
        
        # Convert folders
        for folder_name, folder_config in config.folders.items():
            result["folders"][folder_name] = ConfigAdapter._folder_to_dict(folder_config)
        
        # Convert snippets
        for snippet_name, snippet_config in config.snippets.items():
            result["snippets"][snippet_name] = ConfigAdapter._snippet_to_dict(snippet_config)
        
        # Convert infrastructure
        result["infrastructure"] = ConfigAdapter._infrastructure_to_dict(config.infrastructure)
        
        # Add statistics
        all_items = config.get_all_items()
        items_by_type = {}
        for item in all_items:
            items_by_type[item.item_type] = items_by_type.get(item.item_type, 0) + 1
        
        result["stats"] = {
            "total_items": len(all_items),
            "total_folders": len(config.folders),
            "total_snippets": len(config.snippets),
            "total_infrastructure": len(config.infrastructure.items),
            "items_by_type": items_by_type,
        }
        
        return result
    
    @staticmethod
    def _folder_to_dict(folder_config: FolderConfig) -> Dict[str, Any]:
        """Convert FolderConfig to dict."""
        result = {}
        # Group items by type
        for item in folder_config.get_all_items():
            item_type = item.item_type
            if item_type not in result:
                result[item_type] = []
            result[item_type].append(item.to_dict())
        return result
    
    @staticmethod
    def _snippet_to_dict(snippet_config: SnippetConfig) -> Dict[str, Any]:
        """Convert SnippetConfig to dict."""
        result = {}
        # Group items by type
        for item in snippet_config.get_all_items():
            item_type = item.item_type
            if item_type not in result:
                result[item_type] = []
            result[item_type].append(item.to_dict())
        return result
    
    @staticmethod
    def _infrastructure_to_dict(infrastructure_config) -> Dict[str, Any]:
        """Convert InfrastructureConfig to dict."""
        result = {}
        for item in infrastructure_config.items:
            item_type = item.item_type
            if item_type not in result:
                result[item_type] = []
            result[item_type].append(item.to_dict())
        return result
    
    @staticmethod
    def get_all_items_list(config: Any) -> List[Dict[str, Any]]:
        """
        Get a flat list of all config items as dicts.
        
        Args:
            config: Configuration object or dict
            
        Returns:
            List of item dictionaries
        """
        config_dict = ConfigAdapter.to_dict(config)
        if not config_dict:
            return []
        
        items = []
        
        # From folders
        for folder_name, folder_data in config_dict.get("folders", {}).items():
            for item_type, type_items in folder_data.items():
                if isinstance(type_items, list):
                    items.extend(type_items)
        
        # From snippets
        for snippet_name, snippet_data in config_dict.get("snippets", {}).items():
            for item_type, type_items in snippet_data.items():
                if isinstance(type_items, list):
                    items.extend(type_items)
        
        # From infrastructure
        for item_type, type_items in config_dict.get("infrastructure", {}).items():
            if isinstance(type_items, list):
                items.extend(type_items)
        
        return items
    
    @staticmethod
    def get_stats(config: Any) -> Dict[str, Any]:
        """
        Get statistics about the configuration.
        
        Args:
            config: Configuration object or dict
            
        Returns:
            Statistics dictionary
        """
        config_dict = ConfigAdapter.to_dict(config)
        if not config_dict:
            return {
                "total_items": 0,
                "total_folders": 0,
                "total_snippets": 0,
                "total_infrastructure": 0,
                "items_by_type": {},
            }
        
        return config_dict.get("stats", {})
    
    @staticmethod
    def get_metadata(config: Any) -> Dict[str, Any]:
        """
        Get metadata from the configuration.
        
        Args:
            config: Configuration object or dict
            
        Returns:
            Metadata dictionary
        """
        config_dict = ConfigAdapter.to_dict(config)
        if not config_dict:
            return {}
        
        return config_dict.get("metadata", {})
