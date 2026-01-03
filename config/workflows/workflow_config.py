"""
Workflow configuration system.

Defines settings for workflow operations including:
- Default folders and snippets to process
- Filters (include defaults, enabled only, etc.)
- Validation rules
- Error handling behavior
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class WorkflowConfig:
    """
    Configuration settings for workflow operations.
    
    This class manages settings that control how workflows process
    items, handle errors, and apply filters.
    
    Attributes:
        default_folders: List of folders to process by default
        default_snippets: List of snippets to process by default
        excluded_folders: Folders to always skip
        excluded_snippets: Snippets to always skip
        include_defaults: Whether to include system default items
        enabled_only: Whether to only process enabled items
        validate_before_push: Whether to validate items before pushing
        validate_before_pull: Whether to validate items after pulling
        stop_on_error: Whether to stop workflow on first error
        max_retries: Maximum number of retries for failed operations
        retry_delay: Delay in seconds between retries
        batch_size: Number of items to process in a batch
        parallel: Whether to enable parallel processing
        max_workers: Maximum number of parallel workers
    """
    
    # Folder/snippet configuration
    default_folders: List[str] = field(default_factory=lambda: [
        'Mobile Users',
        'Remote Networks',
        'Service Connections',
    ])
    default_snippets: List[str] = field(default_factory=list)
    excluded_folders: Set[str] = field(default_factory=lambda: {
        'Colo Connect',  # Sensitive
        'Service Connections',  # Sensitive
    })
    excluded_snippets: Set[str] = field(default_factory=set)
    
    # Filtering options
    include_defaults: bool = False
    enabled_only: bool = False
    
    # Validation options
    validate_before_push: bool = True
    validate_before_pull: bool = True
    
    # Error handling
    stop_on_error: bool = False
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Performance options
    batch_size: int = 100
    parallel: bool = False
    max_workers: int = 4
    
    # Additional filters
    custom_filters: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowConfig':
        """
        Create WorkflowConfig from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            WorkflowConfig instance
        """
        # Convert sets from lists if present
        if 'excluded_folders' in data and isinstance(data['excluded_folders'], list):
            data['excluded_folders'] = set(data['excluded_folders'])
        if 'excluded_snippets' in data and isinstance(data['excluded_snippets'], list):
            data['excluded_snippets'] = set(data['excluded_snippets'])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert WorkflowConfig to dictionary.
        
        Returns:
            Configuration dictionary
        """
        data = {}
        for field_name in self.__annotations__:
            value = getattr(self, field_name)
            # Convert sets to lists for JSON serialization
            if isinstance(value, set):
                value = list(value)
            data[field_name] = value
        return data
    
    @classmethod
    def load_from_file(cls, path: Path) -> 'WorkflowConfig':
        """
        Load workflow configuration from JSON file.
        
        Args:
            path: Path to configuration file
            
        Returns:
            WorkflowConfig instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def save_to_file(self, path: Path) -> None:
        """
        Save workflow configuration to JSON file.
        
        Args:
            path: Path to save configuration to
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def is_folder_allowed(self, folder: str) -> bool:
        """
        Check if a folder should be processed.
        
        Args:
            folder: Folder name
            
        Returns:
            True if folder should be processed
        """
        return folder not in self.excluded_folders
    
    def is_snippet_allowed(self, snippet: str) -> bool:
        """
        Check if a snippet should be processed.
        
        Args:
            snippet: Snippet name
            
        Returns:
            True if snippet should be processed
        """
        return snippet not in self.excluded_snippets
    
    def get_allowed_folders(self, folders: List[str]) -> List[str]:
        """
        Filter list of folders to only allowed ones.
        
        Args:
            folders: List of folder names
            
        Returns:
            Filtered list of allowed folders
        """
        return [f for f in folders if self.is_folder_allowed(f)]
    
    def get_allowed_snippets(self, snippets: List[str]) -> List[str]:
        """
        Filter list of snippets to only allowed ones.
        
        Args:
            snippets: List of snippet names
            
        Returns:
            Filtered list of allowed snippets
        """
        return [s for s in snippets if self.is_snippet_allowed(s)]
    
    def should_process_item(self, item: Any) -> bool:
        """
        Determine if an item should be processed based on filters.
        
        Args:
            item: ConfigItem to check
            
        Returns:
            True if item should be processed
        """
        # Check if enabled_only filter applies
        if self.enabled_only and hasattr(item, 'disabled'):
            if item.disabled:
                return False
        
        # Check location
        if hasattr(item, 'folder') and item.folder:
            if not self.is_folder_allowed(item.folder):
                return False
        
        if hasattr(item, 'snippet') and item.snippet:
            if not self.is_snippet_allowed(item.snippet):
                return False
        
        # Apply custom filters
        for filter_name, filter_func in self.custom_filters.items():
            if not filter_func(item):
                return False
        
        return True
    
    def add_custom_filter(self, name: str, filter_func: callable) -> None:
        """
        Add a custom filter function.
        
        Args:
            name: Filter name
            filter_func: Function that takes item and returns bool
        """
        self.custom_filters[name] = filter_func
    
    def remove_custom_filter(self, name: str) -> None:
        """
        Remove a custom filter.
        
        Args:
            name: Filter name to remove
        """
        self.custom_filters.pop(name, None)
