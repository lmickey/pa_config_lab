"""
Default management system.

Centralized system for identifying and filtering default/system items
across all configuration types.
"""

from typing import List, Set, Optional
import logging

logger = logging.getLogger(__name__)


class DefaultManager:
    """
    Manages identification and filtering of default/system items.
    
    This class provides centralized logic for determining whether
    items are defaults/system items that should typically be excluded
    from pull/push operations.
    """
    
    # Folder names that contain default items
    DEFAULT_FOLDERS = {
        'Predefined',
        'Default',
        'System',
    }
    
    # Snippet names that contain default items
    DEFAULT_SNIPPETS = {
        'predefined',
        'predefined-snippet',  # Full name
        'default',
        'system',
        'optional-default',  # Another common default
    }
    
    # Name prefixes that indicate default items
    DEFAULT_NAME_PREFIXES = {
        'default-',
        'paloalto-',
        'panw-',
        'system-',
    }
    
    # Item types that are always considered default
    ALWAYS_DEFAULT_TYPES = set()
    
    def __init__(
        self,
        custom_folders: Optional[Set[str]] = None,
        custom_snippets: Optional[Set[str]] = None,
        custom_prefixes: Optional[Set[str]] = None
    ):
        """
        Initialize DefaultManager.
        
        Args:
            custom_folders: Additional folders to consider as default
            custom_snippets: Additional snippets to consider as default
            custom_prefixes: Additional name prefixes to consider as default
        """
        self.default_folders = self.DEFAULT_FOLDERS.copy()
        self.default_snippets = self.DEFAULT_SNIPPETS.copy()
        self.default_prefixes = self.DEFAULT_NAME_PREFIXES.copy()
        
        if custom_folders:
            self.default_folders.update(custom_folders)
        if custom_snippets:
            self.default_snippets.update(custom_snippets)
        if custom_prefixes:
            self.default_prefixes.update(custom_prefixes)
    
    def is_default(self, item: 'ConfigItem') -> bool:
        """
        Determine if an item is a default/system item.
        
        NOTE: For snippets, filtering should be done at the API level
        based on the snippet's 'type' field (custom vs predefined).
        This method focuses on item-level defaults within snippets.
        
        Args:
            item: ConfigItem to check
            
        Returns:
            True if item is a default/system item
        """
        # Check item type
        if hasattr(item, 'item_type') and item.item_type in self.ALWAYS_DEFAULT_TYPES:
            return True
        
        # Check default property
        if hasattr(item, 'default') and item.default:
            return True
        
        # Check folder
        if hasattr(item, 'folder') and item.folder:
            if self._is_default_folder(item.folder):
                return True
        
        # NOTE: Don't check snippet by name - snippets are filtered
        # at API level by their 'type' field (custom vs predefined)
        # If a snippet made it here, its items should be processed
        
        # Check name
        if hasattr(item, 'name') and item.name:
            if self._is_default_name(item.name):
                return True
        
        return False
    
    def _is_default_folder(self, folder: str) -> bool:
        """Check if folder name indicates default items."""
        folder_lower = folder.lower()
        
        # Check exact match
        if folder in self.default_folders:
            return True
        
        # Check case-insensitive match
        for default_folder in self.default_folders:
            if folder_lower == default_folder.lower():
                return True
        
        # Check if folder contains default keywords
        for keyword in ['predefined', 'default', 'system']:
            if keyword in folder_lower:
                return True
        
        return False
    
    def _is_default_snippet(self, snippet: str) -> bool:
        """Check if snippet name indicates default items."""
        snippet_lower = snippet.lower()
        
        # Check exact match
        if snippet in self.default_snippets:
            return True
        
        # Check case-insensitive match
        for default_snippet in self.default_snippets:
            if snippet_lower == default_snippet.lower():
                return True
        
        # Check if snippet contains default keywords
        for keyword in ['predefined', 'default', 'system']:
            if keyword in snippet_lower:
                return True
        
        return False
    
    def _is_default_name(self, name: str) -> bool:
        """Check if item name indicates a default item."""
        name_lower = name.lower()
        
        # Check prefixes
        for prefix in self.default_prefixes:
            if name_lower.startswith(prefix.lower()):
                return True
        
        return False
    
    def filter_defaults(
        self,
        items: List['ConfigItem'],
        include_defaults: bool = False
    ) -> List['ConfigItem']:
        """
        Filter out default items from a list.
        
        Args:
            items: List of ConfigItem instances
            include_defaults: If True, return all items; if False, exclude defaults
            
        Returns:
            Filtered list of items
        """
        if include_defaults:
            return items
        
        filtered = []
        for item in items:
            if not self.is_default(item):
                filtered.append(item)
            else:
                logger.debug(f"Filtering out default item: {item.item_type} '{item.name}'")
        
        return filtered
    
    def get_default_folders(self) -> Set[str]:
        """
        Get set of default folder names.
        
        Returns:
            Set of default folder names
        """
        return self.default_folders.copy()
    
    def get_default_snippets(self) -> Set[str]:
        """
        Get set of default snippet names.
        
        Returns:
            Set of default snippet names
        """
        return self.default_snippets.copy()
    
    def add_default_folder(self, folder: str) -> None:
        """
        Add a folder to the default folders set.
        
        Args:
            folder: Folder name to add
        """
        self.default_folders.add(folder)
        logger.info(f"Added default folder: {folder}")
    
    def add_default_snippet(self, snippet: str) -> None:
        """
        Add a snippet to the default snippets set.
        
        Args:
            snippet: Snippet name to add
        """
        self.default_snippets.add(snippet)
        logger.info(f"Added default snippet: {snippet}")
    
    def add_default_prefix(self, prefix: str) -> None:
        """
        Add a name prefix to the default prefixes set.
        
        Args:
            prefix: Name prefix to add
        """
        self.default_prefixes.add(prefix)
        logger.info(f"Added default prefix: {prefix}")
    
    def remove_default_folder(self, folder: str) -> None:
        """
        Remove a folder from the default folders set.
        
        Args:
            folder: Folder name to remove
        """
        self.default_folders.discard(folder)
        logger.info(f"Removed default folder: {folder}")
    
    def remove_default_snippet(self, snippet: str) -> None:
        """
        Remove a snippet from the default snippets set.
        
        Args:
            snippet: Snippet name to remove
        """
        self.default_snippets.discard(snippet)
        logger.info(f"Removed default snippet: {snippet}")
    
    def remove_default_prefix(self, prefix: str) -> None:
        """
        Remove a name prefix from the default prefixes set.
        
        Args:
            prefix: Name prefix to remove
        """
        self.default_prefixes.discard(prefix)
        logger.info(f"Removed default prefix: {prefix}")
