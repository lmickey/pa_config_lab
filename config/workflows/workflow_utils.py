"""
Workflow utility functions.

Common utility functions used across workflows for:
- Configuration validation
- Default filtering
- Dependency resolution
- Execution order
- Error handling
"""

from typing import List, Dict, Any, Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def validate_configuration(config: 'WorkflowConfig') -> Tuple[bool, List[str]]:
    """
    Validate workflow configuration.
    
    Args:
        config: WorkflowConfig to validate
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Check batch size
    if config.batch_size < 1:
        errors.append("batch_size must be at least 1")
    
    # Check max_retries
    if config.max_retries < 0:
        errors.append("max_retries cannot be negative")
    
    # Check retry_delay
    if config.retry_delay < 0:
        errors.append("retry_delay cannot be negative")
    
    # Check max_workers
    if config.parallel and config.max_workers < 1:
        errors.append("max_workers must be at least 1 when parallel is enabled")
    
    # Check for conflicting settings
    # Note: A folder can be in both default_folders and excluded_folders if:
    # - It's excluded for folder-based configs (no folder items)
    # - But included for infrastructure configs (e.g., Service Connections)
    # So we only warn if there's overlap, but it's not necessarily an error
    if config.default_folders and config.excluded_folders:
        overlap = set(config.default_folders) & config.excluded_folders
        if overlap:
            # This is informational, not an error - some folders may be infrastructure-only
            logger.debug(f"Folders in both default and excluded (may be infrastructure-only): {overlap}")
    
    if config.default_snippets and config.excluded_snippets:
        overlap = set(config.default_snippets) & config.excluded_snippets
        if overlap:
            errors.append(f"Snippets in both default and excluded: {overlap}")
    
    return (len(errors) == 0, errors)


def filter_defaults(
    items: List['ConfigItem'],
    include_defaults: bool = False
) -> List['ConfigItem']:
    """
    Filter out default/system items if configured.
    
    Args:
        items: List of ConfigItem instances
        include_defaults: Whether to include default items
        
    Returns:
        Filtered list of items
    """
    if include_defaults:
        return items
    
    filtered = []
    for item in items:
        # Check various default indicators
        is_default = False
        
        # Check if item has default property
        if hasattr(item, 'default') and item.default:
            is_default = True
        
        # Check folder/snippet for "Default" or "Predefined"
        if hasattr(item, 'folder') and item.folder:
            folder_lower = item.folder.lower()
            if 'default' in folder_lower or 'predefined' in folder_lower:
                is_default = True
        
        if hasattr(item, 'snippet') and item.snippet:
            snippet_lower = item.snippet.lower()
            if 'default' in snippet_lower or 'predefined' in snippet_lower:
                is_default = True
        
        # Check name for default patterns
        if hasattr(item, 'name') and item.name:
            name_lower = item.name.lower()
            if name_lower.startswith('default-') or name_lower.startswith('paloalto-'):
                is_default = True
        
        if not is_default:
            filtered.append(item)
    
    return filtered


def resolve_dependencies(
    items: List['ConfigItem'],
    include_external: bool = False
) -> Dict[str, Set[str]]:
    """
    Build dependency graph for items.
    
    Args:
        items: List of ConfigItem instances
        include_external: Include dependencies not in the items list
        
    Returns:
        Dictionary mapping item names to set of dependency names
    """
    from config.dependencies.dependency_resolver import DependencyResolver
    
    dependency_graph = {}
    item_names = {item.name for item in items}
    
    for item in items:
        if hasattr(item, 'get_dependencies'):
            deps = item.get_dependencies()
            
            if include_external:
                dependency_graph[item.name] = deps
            else:
                # Only include dependencies that are in our items list
                dependency_graph[item.name] = deps & item_names
        else:
            dependency_graph[item.name] = set()
    
    return dependency_graph


def build_execution_order(
    items: List['ConfigItem'],
    reverse: bool = False
) -> List['ConfigItem']:
    """
    Order items for execution based on dependencies.
    
    Args:
        items: List of ConfigItem instances
        reverse: If True, reverse order (for deletion)
        
    Returns:
        Ordered list of items
    """
    from config.dependencies.dependency_resolver import DependencyResolver
    
    # Build dependency graph
    dependency_graph = resolve_dependencies(items, include_external=False)
    
    # Use DependencyResolver to get topological sort
    resolver = DependencyResolver()
    
    # Add all items to resolver
    for item in items:
        deps = dependency_graph.get(item.name, set())
        resolver.add_item(item.name, item.item_type, deps)
    
    # Get execution order
    try:
        ordered_names = resolver.get_execution_order()
        
        # Map back to items
        item_map = {item.name: item for item in items}
        ordered_items = [item_map[name] for name in ordered_names if name in item_map]
        
        if reverse:
            ordered_items.reverse()
        
        return ordered_items
        
    except Exception as e:
        logger.warning(f"Could not resolve dependencies: {e}. Using original order.")
        if reverse:
            return list(reversed(items))
        return items


def handle_workflow_error(
    error: Exception,
    item: Optional['ConfigItem'],
    operation: str,
    result: 'WorkflowResult',
    config: 'WorkflowConfig'
) -> bool:
    """
    Handle error during workflow execution.
    
    Args:
        error: Exception that occurred
        item: ConfigItem being processed (if applicable)
        operation: Operation being performed
        result: WorkflowResult to update
        config: WorkflowConfig with error handling settings
        
    Returns:
        True if workflow should continue, False if should stop
    """
    # Extract error details
    error_type = type(error).__name__
    error_message = str(error)
    
    # Get item info
    item_type = item.item_type if item and hasattr(item, 'item_type') else 'unknown'
    item_name = item.name if item and hasattr(item, 'name') else 'unknown'
    
    # Add error to result
    result.add_error(
        item_type=item_type,
        item_name=item_name,
        operation=operation,
        error_type=error_type,
        message=error_message,
        details={
            'exception': error_type,
            'traceback': str(error)
        }
    )
    
    # Log error
    logger.error(f"Error during {operation} for {item_type} '{item_name}': {error_message}")
    
    # Check if should stop
    if config.stop_on_error:
        logger.error("Stopping workflow due to error (stop_on_error=True)")
        return False
    
    return True


def filter_by_location(
    items: List['ConfigItem'],
    folders: Optional[List[str]] = None,
    snippets: Optional[List[str]] = None
) -> List['ConfigItem']:
    """
    Filter items by folder or snippet location.
    
    Args:
        items: List of ConfigItem instances
        folders: List of folders to include (None = all)
        snippets: List of snippets to include (None = all)
        
    Returns:
        Filtered list of items
    """
    filtered = []
    
    for item in items:
        include = False
        
        # Check folder
        if folders is not None and hasattr(item, 'folder') and item.folder:
            if item.folder in folders:
                include = True
        
        # Check snippet
        if snippets is not None and hasattr(item, 'snippet') and item.snippet:
            if item.snippet in snippets:
                include = True
        
        # If no filters specified, include all
        if folders is None and snippets is None:
            include = True
        
        if include:
            filtered.append(item)
    
    return filtered


def filter_by_type(
    items: List['ConfigItem'],
    item_types: List[str]
) -> List['ConfigItem']:
    """
    Filter items by type.
    
    Args:
        items: List of ConfigItem instances
        item_types: List of item types to include
        
    Returns:
        Filtered list of items
    """
    return [item for item in items if item.item_type in item_types]


def group_by_type(
    items: List['ConfigItem']
) -> Dict[str, List['ConfigItem']]:
    """
    Group items by type.
    
    Args:
        items: List of ConfigItem instances
        
    Returns:
        Dictionary mapping item types to lists of items
    """
    grouped = {}
    
    for item in items:
        item_type = item.item_type
        if item_type not in grouped:
            grouped[item_type] = []
        grouped[item_type].append(item)
    
    return grouped


def group_by_location(
    items: List['ConfigItem']
) -> Dict[str, List['ConfigItem']]:
    """
    Group items by location (folder or snippet).
    
    Args:
        items: List of ConfigItem instances
        
    Returns:
        Dictionary mapping locations to lists of items
    """
    grouped = {}
    
    for item in items:
        # Determine location
        location = None
        if hasattr(item, 'folder') and item.folder:
            location = f"folder:{item.folder}"
        elif hasattr(item, 'snippet') and item.snippet:
            location = f"snippet:{item.snippet}"
        else:
            location = "no_location"
        
        if location not in grouped:
            grouped[location] = []
        grouped[location].append(item)
    
    return grouped


def validate_items(
    items: List['ConfigItem'],
    result: 'WorkflowResult'
) -> List['ConfigItem']:
    """
    Validate items and track errors.
    
    Args:
        items: List of ConfigItem instances to validate
        result: WorkflowResult to update with errors
        
    Returns:
        List of valid items
    """
    valid_items = []
    
    for item in items:
        try:
            item.validate()
            valid_items.append(item)
        except Exception as e:
            result.add_error(
                item_type=item.item_type,
                item_name=item.name,
                operation='validate',
                error_type=type(e).__name__,
                message=str(e)
            )
    
    return valid_items


def batch_items(
    items: List['ConfigItem'],
    batch_size: int
) -> List[List['ConfigItem']]:
    """
    Split items into batches.
    
    Args:
        items: List of ConfigItem instances
        batch_size: Size of each batch
        
    Returns:
        List of batches (each batch is a list of items)
    """
    batches = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batches.append(batch)
    
    return batches
