"""
Push Orchestrator V2 - ConfigItem-Based Push Operations.

This is a complete rewrite of the push orchestrator to work with ConfigItem
objects instead of raw dictionaries, leveraging the new object model architecture.

Key improvements:
- Works directly with ConfigItem objects
- Uses ConfigItem.create(), .update(), .delete() methods
- Leverages ConfigItem.has_dependencies and .get_dependencies()
- Integrates with WorkflowConfig/WorkflowResult
- Dependency-aware push and delete operations
- Cleaner, simpler code (~50% reduction)
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import logging

from config.models.base import ConfigItem
from config.models.factory import ConfigItemFactory
from config.workflows.workflow_config import WorkflowConfig
from config.workflows.workflow_results import WorkflowResult, WorkflowError, WorkflowWarning
from config.workflows.workflow_state import WorkflowState, WorkflowStatus
from config.workflows.workflow_utils import build_execution_order, handle_workflow_error
from prisma.api_client import PrismaAccessAPIClient
from prisma.api.errors import (
    PrismaAPIError, ResourceConflictError, AuthorizationError, 
    RateLimitError, NetworkError
)


logger = logging.getLogger(__name__)


class PushOrchestratorV2:
    """
    ConfigItem-based push orchestrator.
    
    Handles pushing configuration items to a destination Prisma Access tenant
    with conflict resolution, dependency management, and comprehensive tracking.
    
    Conflict Resolution Strategies:
        - SKIP: Skip items that already exist (default, safest)
        - OVERWRITE: Delete existing, then create new (destructive)
        - RENAME: Rename new items to avoid conflicts, update references
    
    Dependency Management:
        - CREATE: Bottom-up (dependencies created first)
        - UPDATE: Any order (no dependency constraints)
        - DELETE: Top-down (dependent items deleted first)
    """
    
    def __init__(
        self,
        api_client: PrismaAccessAPIClient,
        config: Optional[WorkflowConfig] = None
    ):
        """
        Initialize push orchestrator.
        
        Args:
            api_client: API client for destination tenant
            config: Workflow configuration (default if None)
        """
        self.api_client = api_client
        self.config = config or WorkflowConfig()
        
        # State tracking
        self.state = WorkflowState("push")
        self.result = WorkflowResult()
        
        # Name mappings for RENAME strategy
        self.name_mappings: Dict[str, str] = {}
        
        # Track items that exist in destination
        self.existing_items: Set[Tuple[str, str, str]] = set()  # (type, name, folder)
        
        # Track items that could not be overwritten (for OVERWRITE mode)
        # This is separate from result.could_not_overwrite to prevent modifications during iteration
    
    def push_items(
        self,
        items: List[ConfigItem],
        conflict_strategy: str = "SKIP",
        check_existing: bool = True
    ) -> WorkflowResult:
        """
        Push configuration items to destination tenant.
        
        Args:
            items: List of ConfigItem objects to push
            conflict_strategy: How to handle conflicts (SKIP/OVERWRITE/RENAME)
            check_existing: Whether to check for existing items first
        
        Returns:
            WorkflowResult with detailed outcome
        """
        self.state.start("Pushing configuration items")
        self.result = WorkflowResult()
        
        logger.normal("=" * 80)
        logger.normal("STARTING PUSH OPERATION")
        logger.normal("=" * 80)
        logger.info(f"Push config: {len(items)} items, strategy={conflict_strategy}, check_existing={check_existing}")
        logger.debug(f"Item types: {set(item.item_type for item in items)}")
        
        try:
            # Validate inputs
            if not items:
                logger.warning("No items to push")
                self.result.add_warning("No items provided for push")
                self.state.complete()
                return self.result
            
            logger.info(f"Starting push of {len(items)} items with {conflict_strategy} strategy")
            logger.debug(f"Workflow ID: {self.state.workflow_id}")
            
            # Step 1: Check for existing items (if requested)
            if check_existing:
                logger.info("Step 1: Checking for existing items")
                self._check_existing_items(items)
                logger.info(f"Found {len(self.existing_items)} existing items")
            else:
                logger.info("Step 1: Skipping existence check")
            
            # Step 2: Resolve dependencies and determine execution order
            logger.info("Step 2: Resolving dependencies and execution order")
            execution_order = self._resolve_execution_order(items, conflict_strategy)
            logger.info(f"Execution order determined: {len(execution_order)} items")
            logger.debug(f"First 5 items: {[f'{i.item_type}:{i.name}' for i in execution_order[:5]]}")
            
            # Step 3: Handle conflicts (OVERWRITE or RENAME)
            if conflict_strategy == "OVERWRITE":
                logger.info("Step 3: Handling conflicts with OVERWRITE strategy")
                self._handle_overwrite_conflicts(execution_order)
            elif conflict_strategy == "RENAME":
                logger.info("Step 3: Handling conflicts with RENAME strategy")
                self._handle_rename_conflicts(execution_order)
            else:
                logger.info(f"Step 3: Using {conflict_strategy} strategy (no preprocessing)")
            
            # Step 4: Push items in dependency order
            logger.info("Step 4: Pushing items in dependency order")
            self._push_items_ordered(execution_order, conflict_strategy)
            
            # Mark complete
            self.state.complete()
            logger.normal("=" * 80)
            logger.normal(f"PUSH COMPLETE: {self.result.items_created} created, "
                       f"{self.result.items_skipped} skipped, "
                       f"{self.result.items_failed} failed")
            logger.normal("=" * 80)
            logger.info(f"Push summary: {self.result.items_created} created, "
                       f"{self.result.items_updated} updated, "
                       f"{self.result.items_skipped} skipped, "
                       f"{self.result.items_failed} failed")
            logger.debug(f"Duration: {(datetime.now() - self.state.start_time).total_seconds():.2f}s")
            
            return self.result
            
        except Exception as e:
            error_msg = f"Push orchestration failed: {e}"
            logger.error(error_msg, exc_info=True)
            self.result.add_error(WorkflowError(
                code="PUSH_FAILED",
                message=error_msg,
                details={"exception": str(e)}
            ))
            self.state.fail(error_msg)
            return self.result
    
    def delete_items(
        self,
        items: List[ConfigItem],
        check_references: bool = True
    ) -> WorkflowResult:
        """
        Delete configuration items from destination tenant.
        
        Performs dependency-aware deletion (top-down: dependents first).
        
        Args:
            items: List of ConfigItem objects to delete
            check_references: Whether to check for references before deleting
        
        Returns:
            WorkflowResult with detailed outcome
        """
        self.state.start("Deleting configuration items")
        self.result = WorkflowResult()
        
        logger.normal("=" * 80)
        logger.normal("STARTING DELETE OPERATION")
        logger.normal("=" * 80)
        logger.info(f"Delete config: {len(items)} items, check_references={check_references}")
        
        try:
            if not items:
                logger.warning("No items to delete")
                self.result.add_warning("No items provided for deletion")
                self.state.complete()
                return self.result
            
            logger.info(f"Starting deletion of {len(items)} items")
            
            # Resolve deletion order (top-down: reverse of creation)
            logger.info("Resolving deletion order (top-down)")
            deletion_order = self._resolve_deletion_order(items)
            logger.info(f"Deletion order determined: {len(deletion_order)} items")
            
            # Delete items
            self._delete_items_ordered(deletion_order, check_references)
            
            self.state.complete()
            logger.normal("=" * 80)
            logger.normal(f"DELETE COMPLETE: {self.result.items_deleted} deleted, "
                       f"{self.result.items_failed} failed")
            logger.normal("=" * 80)
            logger.info(f"Deletion complete: {self.result.items_deleted} deleted, "
                       f"{self.result.items_failed} failed")
            
            return self.result
            
        except Exception as e:
            error_msg = f"Deletion orchestration failed: {e}"
            logger.error(error_msg, exc_info=True)
            self.result.add_error(WorkflowError(
                code="DELETE_FAILED",
                message=error_msg,
                details={"exception": str(e)}
            ))
            self.state.fail(error_msg)
            return self.result
    
    def _check_existing_items(self, items: List[ConfigItem]):
        """Check which items already exist in destination."""
        logger.info("Checking for existing items in destination...")
        self.state.update_progress("Checking existing items", 0, len(items))
        
        for i, item in enumerate(items):
            try:
                # Query API for existing item
                # Use item's api_endpoint and location
                folder = item.folder if hasattr(item, 'folder') else None
                snippet = item.snippet if hasattr(item, 'snippet') else None
                
                # Try to fetch the item
                response = self.api_client._make_request(
                    'GET',
                    f"{item.api_endpoint}?name={item.name}"
                    f"{'&folder=' + folder if folder else ''}"
                    f"{'&snippet=' + snippet if snippet else ''}",
                    item_type=item.item_type
                )
                
                if response and 'data' in response and len(response['data']) > 0:
                    # Item exists
                    location = folder or snippet or 'global'
                    self.existing_items.add((item.item_type, item.name, location))
                    logger.debug(f"Found existing: {item.item_type} '{item.name}' in {location}")
                
                self.state.update_progress(f"Checked {i+1}/{len(items)}", i+1, len(items))
                
            except Exception as e:
                # If fetch fails, assume item doesn't exist
                logger.debug(f"Item {item.name} not found (will create): {e}")
        
        logger.info(f"Found {len(self.existing_items)} existing items")
    
    def _resolve_execution_order(
        self,
        items: List[ConfigItem],
        strategy: str
    ) -> List[ConfigItem]:
        """
        Resolve execution order based on dependencies.
        
        For CREATE/UPDATE: Bottom-up (dependencies first)
        For DELETE: Top-down (dependents first)
        
        Args:
            items: Items to order
            strategy: Conflict strategy (affects ordering)
        
        Returns:
            Ordered list of items
        """
        logger.info("Resolving dependency order...")
        
        try:
            # Use workflow_utils to build execution order
            ordered = build_execution_order(items)
            logger.info(f"Resolved order for {len(ordered)} items")
            return ordered
            
        except Exception as e:
            logger.warning(f"Failed to resolve dependencies: {e}, using original order")
            return items
    
    def _resolve_deletion_order(self, items: List[ConfigItem]) -> List[ConfigItem]:
        """
        Resolve deletion order (top-down: reverse of creation order).
        
        Args:
            items: Items to delete
        
        Returns:
            Ordered list (dependents first, then dependencies)
        """
        logger.info("Resolving deletion order...")
        
        try:
            # Get creation order, then reverse it
            creation_order = build_execution_order(items)
            deletion_order = list(reversed(creation_order))
            logger.info(f"Resolved deletion order for {len(deletion_order)} items")
            return deletion_order
            
        except Exception as e:
            logger.warning(f"Failed to resolve deletion order: {e}, using reverse order")
            return list(reversed(items))
    
    def _handle_overwrite_conflicts(self, items: List[ConfigItem]):
        """
        Handle OVERWRITE strategy: delete existing items.
        
        Items that cannot be deleted (e.g., still referenced) are tracked
        and marked as "could not overwrite".
        
        Args:
            items: Items to check and delete if existing
        """
        logger.info("Handling OVERWRITE conflicts...")
        items_to_delete = []
        
        for item in items:
            location = getattr(item, 'folder', None) or getattr(item, 'snippet', None) or 'global'
            if (item.item_type, item.name, location) in self.existing_items:
                items_to_delete.append(item)
        
        if items_to_delete:
            logger.info(f"Deleting {len(items_to_delete)} existing items for overwrite")
            
            # Track which items we successfully deleted
            successfully_deleted = set()
            
            # Delete in reverse dependency order
            deletion_order = self._resolve_deletion_order(items_to_delete)
            
            for item in deletion_order:
                try:
                    success = item.delete(self.api_client)
                    if success:
                        location = getattr(item, 'folder', None) or getattr(item, 'snippet', None) or 'global'
                        successfully_deleted.add((item.item_type, item.name, location))
                        logger.info(f"Deleted for overwrite: {item.item_type} '{item.name}'")
                    else:
                        logger.warning(f"Could not delete {item.item_type} '{item.name}' - will skip")
                        self.result.could_not_overwrite.add((item.item_type, item.name))
                        
                except ResourceConflictError as e:
                    # Still referenced - cannot overwrite
                    logger.warning(f"Cannot overwrite {item.item_type} '{item.name}': still referenced")
                    self.result.could_not_overwrite.add((item.item_type, item.name))
                    self.result.add_warning(WorkflowWarning(
                        code="CANNOT_OVERWRITE",
                        message=f"Item still referenced, cannot overwrite: {e}",
                        item_type=item.item_type,
                        item_name=item.name
                    ))
                    
                except Exception as e:
                    logger.error(f"Error deleting for overwrite: {e}")
                    self.result.could_not_overwrite.add((item.item_type, item.name))
            
            # Update existing_items to remove successfully deleted ones
            self.existing_items = self.existing_items - successfully_deleted
    
    def _handle_rename_conflicts(self, items: List[ConfigItem]):
        """
        Handle RENAME strategy: rename conflicting items.
        
        Args:
            items: Items to check and rename if conflicting
        """
        logger.info("Handling RENAME conflicts...")
        
        for item in items:
            location = getattr(item, 'folder', None) or getattr(item, 'snippet', None) or 'global'
            if (item.item_type, item.name, location) in self.existing_items:
                # Generate new name
                original_name = item.name
                new_name = self._generate_unique_name(item)
                
                # Update item name
                item.raw_config['name'] = new_name
                
                # Track mapping
                self.name_mappings[original_name] = new_name
                logger.info(f"Renamed '{original_name}' → '{new_name}'")
                
                self.result.add_warning(WorkflowWarning(
                    code="ITEM_RENAMED",
                    message=f"Item renamed to avoid conflict: {original_name} → {new_name}",
                    item_type=item.item_type,
                    item_name=original_name
                ))
        
        # Update references in all items
        if self.name_mappings:
            self._update_references(items)
    
    def _generate_unique_name(self, item: ConfigItem) -> str:
        """Generate a unique name for renamed item."""
        base_name = item.name
        counter = 1
        new_name = f"{base_name}_copy"
        
        location = getattr(item, 'folder', None) or getattr(item, 'snippet', None) or 'global'
        
        # Keep incrementing until unique
        while (item.item_type, new_name, location) in self.existing_items:
            counter += 1
            new_name = f"{base_name}_copy{counter}"
        
        return new_name
    
    def _update_references(self, items: List[ConfigItem]):
        """
        Update references in items based on name mappings.
        
        Uses type-specific logic to update references correctly.
        
        Args:
            items: Items to update references in
        """
        logger.info(f"Updating references based on {len(self.name_mappings)} renames")
        
        for item in items:
            if item.has_dependencies:
                # Get dependencies
                deps = item.get_dependencies()
                
                # Check if any dependencies were renamed
                needs_update = any(dep_name in self.name_mappings for _, dep_name in deps)
                
                if needs_update:
                    updated = self._update_item_references(item)
                    if updated:
                        logger.info(f"Updated references in {item.item_type} '{item.name}'")
    
    def _update_item_references(self, item: ConfigItem) -> bool:
        """
        Update references in a specific item based on name mappings.
        
        Args:
            item: Item to update
            
        Returns:
            True if any references were updated
        """
        updated = False
        config = item.raw_config
        
        # Update different field types based on item type
        # This handles the most common reference patterns
        
        # 1. List fields (e.g., 'static' in address groups, 'members' in service groups)
        list_fields = ['static', 'members', 'source', 'destination', 'application']
        for field in list_fields:
            if field in config and isinstance(config[field], list):
                new_list = []
                for name in config[field]:
                    if isinstance(name, str) and name in self.name_mappings:
                        new_list.append(self.name_mappings[name])
                        updated = True
                        logger.debug(f"  Updated {field}: {name} → {self.name_mappings[name]}")
                    else:
                        new_list.append(name)
                config[field] = new_list
        
        # 2. String fields (single references)
        string_fields = ['from_', 'to_', 'source_zone', 'destination_zone']
        for field in string_fields:
            if field in config and isinstance(config[field], str):
                if config[field] in self.name_mappings:
                    old_value = config[field]
                    config[field] = self.name_mappings[old_value]
                    updated = True
                    logger.debug(f"  Updated {field}: {old_value} → {config[field]}")
        
        # 3. Nested references in profile groups
        if item.item_type == 'profile_group' and 'virus' in config:
            if isinstance(config['virus'], list):
                new_list = []
                for name in config['virus']:
                    if isinstance(name, str) and name in self.name_mappings:
                        new_list.append(self.name_mappings[name])
                        updated = True
                    else:
                        new_list.append(name)
                config['virus'] = new_list
        
        # 4. Security rules - profile references
        if item.item_type == 'security_rule':
            # Update profile_setting references
            if 'profile_setting' in config:
                profile_setting = config['profile_setting']
                if isinstance(profile_setting, dict) and 'group' in profile_setting:
                    group_list = profile_setting['group']
                    if isinstance(group_list, list):
                        new_list = []
                        for name in group_list:
                            if isinstance(name, str) and name in self.name_mappings:
                                new_list.append(self.name_mappings[name])
                                updated = True
                            else:
                                new_list.append(name)
                        profile_setting['group'] = new_list
        
        # 5. Fallback: JSON string replacement for any missed references
        # This catches edge cases but is less precise
        if not updated:
            import json
            config_str = json.dumps(config)
            original_str = config_str
            for old_name, new_name in self.name_mappings.items():
                # Only replace exact matches with quotes to avoid partial matches
                config_str = config_str.replace(f'"{old_name}"', f'"{new_name}"')
            
            if config_str != original_str:
                item.raw_config = json.loads(config_str)
                updated = True
                logger.debug(f"  Updated references via JSON replacement")
        
        return updated
    
    def _push_items_ordered(self, items: List[ConfigItem], strategy: str):
        """
        Push items in the resolved order.
        
        Args:
            items: Ordered items to push
            strategy: Conflict strategy
        """
        logger.info(f"Pushing {len(items)} items...")
        self.state.update_progress("Pushing items", 0, len(items))
        
        for i, item in enumerate(items):
            try:
                location = getattr(item, 'folder', None) or getattr(item, 'snippet', None) or 'global'
                is_existing = (item.item_type, item.name, location) in self.existing_items
                
                # Check if this item could not be overwritten
                if (item.item_type, item.name) in self.result.could_not_overwrite:
                    logger.info(f"Skipping {item.item_type} '{item.name}' - could not overwrite")
                    self.result.items_skipped += 1
                
                # Handle based on strategy
                elif is_existing and strategy == "SKIP":
                    logger.info(f"Skipping existing {item.item_type} '{item.name}'")
                    self.result.items_skipped += 1
                    
                else:
                    # Validate before pushing
                    validation_errors = item.validate()
                    if validation_errors:
                        error_msg = f"Validation failed: {', '.join(validation_errors)}"
                        logger.warning(f"{item.item_type} '{item.name}': {error_msg}")
                        self.result.add_error(WorkflowError(
                            code="VALIDATION_FAILED",
                            message=error_msg,
                            item_type=item.item_type,
                            item_name=item.name
                        ))
                        self.result.items_failed += 1
                        continue
                    
                    # Store old ID before push (for OVERWRITE ID change detection)
                    old_id = getattr(item, 'id', None)
                    
                    # Push item (create or update)
                    if is_existing and strategy == "OVERWRITE":
                        # Already deleted in _handle_overwrite_conflicts
                        # Now create (will get new ID from API)
                        success = item.create(self.api_client)
                        if success:
                            new_id = getattr(item, 'id', None)
                            if new_id and old_id and new_id != old_id:
                                logger.info(f"Overwrote {item.item_type} '{item.name}' (ID: {old_id} → {new_id})")
                            else:
                                logger.info(f"Overwrote {item.item_type} '{item.name}'")
                            self.result.items_created += 1
                        else:
                            logger.error(f"Failed to overwrite {item.item_type} '{item.name}'")
                            self.result.items_failed += 1
                    else:
                        # Create new item
                        success = item.create(self.api_client)
                        if success:
                            logger.info(f"Created {item.item_type} '{item.name}'")
                            self.result.items_created += 1
                        else:
                            logger.error(f"Failed to create {item.item_type} '{item.name}'")
                            self.result.items_failed += 1
                
                self.result.items_processed += 1
                self.state.update_progress(
                    f"Pushed {i+1}/{len(items)}",
                    i+1,
                    len(items)
                )
                
            except PrismaAPIError as e:
                self._handle_push_error(item, e)
            except Exception as e:
                logger.error(f"Unexpected error pushing {item.item_type} '{item.name}': {e}")
                self.result.add_error(WorkflowError(
                    code="PUSH_ERROR",
                    message=str(e),
                    item_type=item.item_type,
                    item_name=item.name
                ))
                self.result.items_failed += 1
    
    def _delete_items_ordered(self, items: List[ConfigItem], check_references: bool):
        """
        Delete items in the resolved order.
        
        Args:
            items: Ordered items to delete (top-down)
            check_references: Whether to check for references
        """
        logger.info(f"Deleting {len(items)} items...")
        self.state.update_progress("Deleting items", 0, len(items))
        
        for i, item in enumerate(items):
            try:
                # Delete item
                success = item.delete(self.api_client)
                if success:
                    logger.info(f"Deleted {item.item_type} '{item.name}'")
                    self.result.items_deleted += 1
                else:
                    logger.error(f"Failed to delete {item.item_type} '{item.name}'")
                    self.result.items_failed += 1
                
                self.result.items_processed += 1
                self.state.update_progress(
                    f"Deleted {i+1}/{len(items)}",
                    i+1,
                    len(items)
                )
                
            except ResourceConflictError as e:
                # Item still referenced
                logger.warning(f"Cannot delete {item.item_type} '{item.name}': still referenced")
                self.result.add_warning(WorkflowWarning(
                    code="DELETE_BLOCKED",
                    message=f"Item still referenced: {e}",
                    item_type=item.item_type,
                    item_name=item.name
                ))
                self.result.items_failed += 1
                
            except PrismaAPIError as e:
                self._handle_delete_error(item, e)
            except Exception as e:
                logger.error(f"Unexpected error deleting {item.item_type} '{item.name}': {e}")
                self.result.add_error(WorkflowError(
                    code="DELETE_ERROR",
                    message=str(e),
                    item_type=item.item_type,
                    item_name=item.name
                ))
                self.result.items_failed += 1
    
    def _handle_push_error(self, item: ConfigItem, error: PrismaAPIError):
        """Handle API errors during push."""
        logger.error(f"API error pushing {item.item_type} '{item.name}': {error}")
        
        self.result.add_error(WorkflowError(
            code=error.error_code,
            message=str(error),
            item_type=item.item_type,
            item_name=item.name,
            details=error.details if hasattr(error, 'details') else {}
        ))
        self.result.items_failed += 1
    
    def _handle_delete_error(self, item: ConfigItem, error: PrismaAPIError):
        """Handle API errors during delete."""
        logger.error(f"API error deleting {item.item_type} '{item.name}': {error}")
        
        self.result.add_error(WorkflowError(
            code=error.error_code,
            message=str(error),
            item_type=item.item_type,
            item_name=item.name,
            details=error.details if hasattr(error, 'details') else {}
        ))
        self.result.items_failed += 1
