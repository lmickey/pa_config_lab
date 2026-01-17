"""
Push Orchestrator V2 - Item-centric push for Prisma Access Configuration.

This is a redesigned push orchestrator that:
1. Treats each item individually (not container-centric)
2. Supports per-item destination overrides
3. Handles snippet creation as a first-class operation
4. Uses simpler, more maintainable code structure

Phase 1: Snippet creation and pushing items into snippets
Phase 2: Folder operations with rename support
"""

from typing import Dict, Any, List, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)


class PushStrategy(Enum):
    """How to handle conflicts when pushing."""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"


# Default/system profile names that cannot be modified
# These are created by Palo Alto and should always be skipped during push
DEFAULT_PROFILE_NAMES = {
    'best-practice',
    'default',
    'strict',
    'Strict',
}

# Profile types that may have default names
PROFILE_ITEM_TYPES = {
    'wildfire_profile', 'wildfire_antivirus_profile',
    'anti_spyware_profile',
    'vulnerability_profile', 'vulnerability_protection_profile',
    'url_filtering_profile',
    'file_blocking_profile',
    'dns_security_profile',
    'decryption_profile',
    'security_profile_group', 'profile_group',
}


class LocationType(Enum):
    """Type of destination location."""
    FOLDER = "folder"
    SNIPPET = "snippet"
    NEW_SNIPPET = "new_snippet"


@dataclass
class PushDestination:
    """Describes where an item should be pushed."""
    location_type: LocationType
    location_name: str
    strategy: PushStrategy = PushStrategy.SKIP
    new_snippet_name: Optional[str] = None
    include_dependencies: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PushDestination':
        """Create PushDestination from _destination dict.
        
        Expected keys from selection_row.get_destination_settings():
            - folder: effective folder name (or snippet name)
            - name: destination name (may be same as original)
            - strategy: conflict strategy ('skip', 'overwrite', 'rename')
            - is_inherited: bool - if inherited from parent
            - is_new_snippet: bool - if creating a new snippet (includes rename)
            - is_rename_snippet: bool - if renaming an existing snippet
            - is_existing_snippet: bool - if destination is an existing snippet (not folder)
            - new_snippet_name: str - name for new/renamed snippet
            - include_dependencies: bool
            - create_duplicates: bool
        """
        if not data:
            return cls(
                location_type=LocationType.FOLDER,
                location_name="Shared",
                strategy=PushStrategy.SKIP
            )
        
        # Log the destination data for debugging
        logger.debug(f"Parsing destination: {data}")
        
        # Check for new snippet (includes rename_snippet)
        is_new_snippet = data.get('is_new_snippet', False)
        is_rename_snippet = data.get('is_rename_snippet', False)
        is_existing_snippet = data.get('is_existing_snippet', False)
        new_snippet_name = data.get('new_snippet_name', '')
        
        if is_new_snippet or is_rename_snippet:
            # Creating a new snippet (or renaming)
            loc_type = LocationType.NEW_SNIPPET
            loc_name = new_snippet_name or 'New Snippet'
            logger.debug(f"  -> NEW_SNIPPET: {loc_name} (rename={is_rename_snippet})")
        elif is_existing_snippet:
            # Destination is an existing snippet selected from dropdown
            snippet_name = data.get('folder', 'Shared')  # 'folder' holds the snippet name
            loc_type = LocationType.SNIPPET
            loc_name = snippet_name
            logger.debug(f"  -> EXISTING SNIPPET: {loc_name}")
        elif data.get('is_inherited', False):
            # Inherited - use original location (resolved by caller)
            folder = data.get('folder', 'Shared')
            loc_type = LocationType.FOLDER
            loc_name = folder
            logger.debug(f"  -> INHERITED from folder: {loc_name}")
        else:
            # Explicit folder selection
            folder = data.get('folder', 'Shared')
            loc_type = LocationType.FOLDER
            loc_name = folder
            logger.debug(f"  -> FOLDER: {loc_name}")
        
        # Parse strategy
        strategy_str = data.get('strategy', 'skip')
        if strategy_str:
            strategy_str = strategy_str.lower()
        else:
            strategy_str = 'skip'
        
        try:
            strategy = PushStrategy(strategy_str)
        except ValueError:
            logger.warning(f"Unknown strategy '{strategy_str}', defaulting to SKIP")
            strategy = PushStrategy.SKIP
        
        logger.debug(f"  -> Strategy: {strategy.value}")
        
        return cls(
            location_type=loc_type,
            location_name=loc_name,
            strategy=strategy,
            new_snippet_name=new_snippet_name,
            include_dependencies=data.get('include_dependencies', True)
        )


@dataclass
class PushItem:
    """Represents a single item to be pushed."""
    name: str
    item_type: str
    data: Dict[str, Any]
    destination: PushDestination
    original_folder: str = ""
    original_snippet: str = ""
    
    @property
    def original_location(self) -> str:
        """Get the original location (folder or snippet)."""
        return self.original_folder or self.original_snippet or ""


@dataclass
class PushResult:
    """Result of pushing a single item."""
    item_name: str
    item_type: str
    destination: str
    action: str  # 'created', 'updated', 'skipped', 'failed', 'renamed'
    success: bool
    message: str
    error: Optional[str] = None


@dataclass
class PushSummary:
    """Summary of a push operation."""
    total: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    skipped: int = 0
    failed: int = 0
    renamed: int = 0
    snippets_created: int = 0
    results: List[PushResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'summary': {
                'total': self.total,
                'created': self.created,
                'updated': self.updated,
                'skipped': self.skipped,
                'failed': self.failed,
                'renamed': self.renamed,
                'snippets_created': self.snippets_created,
            },
            'details': [
                {
                    'name': r.item_name,
                    'type': r.item_type,
                    'destination': r.destination,
                    'action': r.action,
                    'success': r.success,
                    'message': r.message,
                    'error': r.error,
                }
                for r in self.results
            ],
            'errors': self.errors,
            'elapsed_seconds': self.elapsed_seconds,
        }


class PushOrchestratorV2:
    """
    New push orchestrator with item-centric design.
    
    Phase 1 Focus: Creating new snippets and pushing items into them.
    """
    
    # Item types and their API method mappings
    # Includes aliases for different naming conventions from config sources
    OBJECT_TYPES = {
        'address': 'address',
        'address_object': 'address',  # Alias
        'address_group': 'address_group',
        'service': 'service',
        'service_object': 'service',  # Alias
        'service_group': 'service_group',
        'application': 'application',
        'application_group': 'application_group',
        'application_filter': 'application_filter',
        'external_dynamic_list': 'external_dynamic_list',
        'url_category': 'url_category',
        'tag': 'tag',
        'schedule': 'schedule',
    }
    
    PROFILE_TYPES = {
        'security_profile_group': 'profile_group',
        'anti_spyware_profile': 'anti_spyware_profile',
        'vulnerability_protection_profile': 'vulnerability_protection_profile',
        'url_filtering_profile': 'url_filtering_profile',
        'file_blocking_profile': 'file_blocking_profile',
        'wildfire_antivirus_profile': 'wildfire_antivirus_profile',
        'wildfire_profile': 'wildfire_antivirus_profile',  # Alias
        'decryption_profile': 'decryption_profile',
        'dns_security_profile': 'dns_security_profile',
        'hip_object': 'hip_object',
        'hip_profile': 'hip_profile',
    }
    
    RULE_TYPES = {
        'security_rule': 'security_rule',
        'rule': 'security_rule',  # Alias
        'authentication_rule': 'authentication_rule',
        'decryption_rule': 'decryption_rule',
    }
    
    def __init__(self, api_client):
        """
        Initialize the push orchestrator.
        
        Args:
            api_client: Authenticated PrismaAccessAPIClient
        """
        self.api_client = api_client
        self.progress_callback: Optional[Callable[[str, int, int], None]] = None
        self.summary = PushSummary()
        
        # Track created snippets to avoid duplicates
        self._created_snippets: Set[str] = set()
        
        # Track name mappings for RENAME mode
        self._name_mappings: Dict[str, str] = {}
    
    def set_progress_callback(self, callback: Callable[[str, int, int], None]):
        """Set progress callback function."""
        self.progress_callback = callback
    
    def _report_progress(self, message: str, current: int = 0, total: int = 0):
        """Report progress if callback is set."""
        logger.info(f"[{current}/{total}] {message}")
        if self.progress_callback:
            try:
                self.progress_callback(message, current, total)
            except Exception:
                pass  # Ignore callback errors
    
    def _add_result(self, result: PushResult):
        """Add a result to the summary."""
        self.summary.results.append(result)
        self.summary.total += 1
        
        if result.success:
            if result.action == 'created':
                self.summary.created += 1
            elif result.action == 'updated':
                self.summary.updated += 1
            elif result.action == 'deleted':
                self.summary.deleted += 1
            elif result.action == 'skipped':
                self.summary.skipped += 1
            elif result.action == 'renamed':
                self.summary.renamed += 1
        else:
            self.summary.failed += 1
            if result.error:
                self.summary.errors.append(f"{result.item_type}/{result.item_name}: {result.error}")
    
    def _is_default_profile(self, item: 'PushItem') -> bool:
        """Check if an item is a default/system profile that should be skipped."""
        return item.item_type in PROFILE_ITEM_TYPES and item.name in DEFAULT_PROFILE_NAMES
    
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    def push_selected_items(
        self,
        selected_items: Dict[str, Any],
        destination_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Push selected configuration items to destination tenant.
        
        Uses a two-phase approach for OVERWRITE strategy:
        1. PHASE 1 (DELETE): Delete existing items in reverse dependency order (parents first)
        2. PHASE 2 (CREATE): Create items in dependency order (children first)
        
        Args:
            selected_items: Dictionary from selection list with folders, snippets, infrastructure
            destination_config: Optional destination config for conflict detection
            
        Returns:
            Push results dictionary
        """
        self.summary = PushSummary(start_time=datetime.now())
        self._created_snippets = set()
        self._name_mappings = {}
        self._failed_deletes: Set[str] = set()  # Track failed delete item keys
        self._skipped_due_to_dependency: Set[str] = set()  # Track items skipped due to dep failure
        
        logger.info("=" * 80)
        logger.info("PUSH ORCHESTRATOR V2 - STARTING PUSH OPERATION")
        logger.info(f"Destination Tenant: {self.api_client.tsg_id}")
        logger.info("=" * 80)
        
        try:
            # Step 1: Convert selected_items to PushItem list
            items = self._extract_push_items(selected_items)
            total_items = len(items)
            
            logger.info(f"Total items to push: {total_items}")
            self._report_progress("Preparing push operation", 0, total_items)
            
            if total_items == 0:
                logger.warning("No items to push!")
                return self._build_result(success=True, message="No items to push")
            
            # Step 2: Identify and create new snippets first
            new_snippets = self._identify_new_snippets(items)
            failed_snippets = set()
            if new_snippets:
                self._report_progress(f"Creating {len(new_snippets)} new snippet(s)", 0, total_items)
                failed_snippets = self._create_new_snippets(new_snippets, destination_config)
                
                if failed_snippets:
                    logger.warning(f"[Push] {len(failed_snippets)} snippet(s) failed to create: {sorted(failed_snippets)}")
                    # Count how many items will be skipped due to failed snippets
                    items_to_skip = sum(1 for item in items 
                                       if item.destination.location_type == LocationType.NEW_SNIPPET 
                                       and (item.destination.new_snippet_name in failed_snippets 
                                            or item.destination.location_name in failed_snippets))
                    if items_to_skip > 0:
                        logger.warning(f"[Push] {items_to_skip} item(s) will be skipped due to failed snippet creation")
            
            # Step 3: Identify items that need OVERWRITE (delete + create)
            logger.info(f"[Push] Checking {len(items)} items for OVERWRITE strategy...")
            logger.debug(f"[Push] destination_config keys: {list(destination_config.keys()) if destination_config else 'None'}")
            if destination_config:
                logger.debug(f"[Push] snippet_objects keys: {list(destination_config.get('snippet_objects', {}).keys())}")
                logger.debug(f"[Push] objects keys: {list(destination_config.get('objects', {}).keys())}")
            
            overwrite_items = []
            skipped_default_profiles = []
            for item in items:
                # Skip default profiles entirely - remove from push
                if self._is_default_profile(item):
                    skipped_default_profiles.append(item)
                    logger.info(f"[Push] Skipping default profile: {item.item_type}/{item.name}")
                    continue
                
                is_overwrite = item.destination.strategy == PushStrategy.OVERWRITE
                exists = self._item_exists_in_dest(item, destination_config) if is_overwrite else False
                logger.info(f"[Push] Item {item.item_type}/{item.name}: strategy={item.destination.strategy}, "
                           f"location_type={item.destination.location_type}, location={item.destination.location_name}, "
                           f"is_overwrite={is_overwrite}, exists={exists}")
                if is_overwrite and exists:
                    overwrite_items.append(item)
            
            # Record skipped default profiles
            for item in skipped_default_profiles:
                self._add_result(PushResult(
                    item_name=item.name,
                    item_type=item.item_type,
                    destination=item.destination.location_name,
                    action='skipped',
                    success=True,
                    message='Default/system profile - cannot be modified'
                ))
            
            logger.info(f"[Push] Found {len(overwrite_items)} items requiring DELETE before CREATE")
            
            # Step 4: PHASE 1 - DELETE existing items (reverse dependency order: parents/groups first)
            if overwrite_items:
                logger.info(f"[Push] Phase 1: Deleting {len(overwrite_items)} existing items for OVERWRITE")
                self._report_progress(f"Phase 1: Deleting {len(overwrite_items)} existing items...", 0, total_items)
                
                # Sort for delete: reverse dependency order (delete parents/groups first, then children)
                delete_order = self._sort_for_delete(overwrite_items)
                
                for idx, item in enumerate(delete_order):
                    item_key = f"{item.item_type}:{item.name}"
                    
                    # Check if this item depends on a failed delete
                    if self._should_skip_due_to_dep_failure(item):
                        self._skipped_due_to_dependency.add(item_key)
                        self._report_progress(
                            f"  ⊘ Skipping delete: {item.name} (dependency delete failed)",
                            idx + 1,
                            len(delete_order)
                        )
                        continue
                    
                    self._report_progress(
                        f"  Deleting {item.item_type}: {item.name}...",
                        idx + 1,
                        len(delete_order)
                    )
                    
                    success = self._delete_item_for_overwrite(item, destination_config)
                    
                    if success:
                        self._report_progress(
                            f"  ✓ Deleted: {item.name}",
                            idx + 1,
                            len(delete_order)
                        )
                        # Record successful delete
                        self._add_result(PushResult(
                            item_name=item.name,
                            item_type=item.item_type,
                            destination=self._get_item_destination(item),
                            action='deleted',
                            success=True,
                            message=f"Deleted for overwrite"
                        ))
                    else:
                        self._failed_deletes.add(item_key)
                        self._report_progress(
                            f"  ⚠️ Delete failed: {item.name}",
                            idx + 1,
                            len(delete_order)
                        )
                        # Record as failure
                        self._add_result(PushResult(
                            item_name=item.name,
                            item_type=item.item_type,
                            destination=self._get_item_destination(item),
                            action='failed',
                            success=False,
                            message=f"Could not delete existing {item.item_type} for overwrite",
                            error="Delete failed"
                        ))
                
                if self._failed_deletes:
                    logger.warning(f"[Push] {len(self._failed_deletes)} items failed to delete")
            
            # Step 5: Sort items for CREATE (dependency order: children/primitives first)
            sorted_items = self._sort_by_dependencies(items)
            
            # Step 6: PHASE 2 - CREATE items
            phase2_label = "Phase 2: " if overwrite_items else ""
            logger.info(f"[Push] {phase2_label}Creating {len(sorted_items)} items")
            
            current = 0
            for item in sorted_items:
                current += 1
                item_key = f"{item.item_type}:{item.name}"
                
                # Skip default profiles - already recorded in Step 3
                if self._is_default_profile(item):
                    continue
                
                # Check if this item targets a failed snippet - skip it
                if failed_snippets and item.destination.location_type == LocationType.NEW_SNIPPET:
                    target_snippet = item.destination.new_snippet_name or item.destination.location_name
                    if target_snippet in failed_snippets:
                        self._report_progress(
                            f"  ⊘ Skipped: {item.name} (target snippet '{target_snippet}' failed to create)",
                            current,
                            total_items
                        )
                        # Record as skipped
                        self.summary.results.append(PushResult(
                            name=item.name,
                            item_type=item.item_type,
                            success=False,
                            action='skipped',
                            message=f"Target snippet '{target_snippet}' failed to create",
                            error=None
                        ))
                        self.summary.skipped += 1
                        self.summary.total += 1
                        continue
                
                # Check if this item's delete failed - skip create
                if item_key in self._failed_deletes:
                    self._report_progress(
                        f"  ⊘ Skipped create: {item.name} (delete failed, cannot recreate)",
                        current,
                        total_items
                    )
                    # Don't add result - already added during delete failure
                    # Just increment skip counter
                    self.summary.skipped += 1
                    self.summary.total += 1
                    continue
                
                # Check if this item should be skipped due to dependency failure
                if item_key in self._skipped_due_to_dependency or self._should_skip_due_to_dep_failure(item):
                    self._report_progress(
                        f"  ⊘ Skipping: {item.name} (dependency delete failed)",
                        current,
                        total_items
                    )
                    self._add_result(PushResult(
                        item_name=item.name,
                        item_type=item.item_type,
                        destination=self._get_item_destination(item),
                        action='skipped',
                        success=True,
                        message="Skipped due to dependency failure"
                    ))
                    continue
                
                self._report_progress(
                    f"{phase2_label}Pushing {item.item_type}: {item.name}...",
                    current,
                    total_items
                )
                
                # Track results before push to detect new result
                results_before = len(self.summary.results)
                self._push_single_item(item, destination_config)
                
                # Report outcome for this item
                if len(self.summary.results) > results_before:
                    last_result = self.summary.results[-1]
                    if last_result.success:
                        if last_result.action == 'skipped':
                            self._report_progress(
                                f"  ⊘ Skipped: {item.name} ({last_result.message})",
                                current,
                                total_items
                            )
                        else:
                            self._report_progress(
                                f"  ✓ {last_result.action.capitalize()}: {item.name}",
                                current,
                                total_items
                            )
                    else:
                        # Extract meaningful error message
                        error_short = last_result.error or last_result.message
                        if "'already in use'" in str(error_short):
                            error_short = "Name already exists in tenant"
                        elif "'is not a valid reference'" in str(error_short):
                            error_short = "Invalid reference"
                        elif len(str(error_short)) > 60:
                            error_short = str(error_short)[:60] + "..."
                        self._report_progress(
                            f"  ✗ FAILED: {item.name} - {error_short}",
                            current,
                            total_items
                        )
            
            self.summary.end_time = datetime.now()
            
            logger.info("=" * 80)
            logger.info("PUSH OPERATION COMPLETED")
            logger.info(f"Total: {self.summary.total}, Created: {self.summary.created}, "
                       f"Skipped: {self.summary.skipped}, Failed: {self.summary.failed}")
            logger.info(f"Elapsed: {self.summary.elapsed_seconds:.2f}s")
            logger.info("=" * 80)
            
            success = self.summary.failed == 0
            message = self._build_summary_message()
            return self._build_result(success=success, message=message)
            
        except Exception as e:
            logger.error(f"Push operation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.summary.end_time = datetime.now()
            self.summary.errors.append(str(e))
            return self._build_result(success=False, message=f"Push failed: {str(e)}")
    
    def _build_result(self, success: bool, message: str) -> Dict[str, Any]:
        """Build the result dictionary."""
        return {
            'success': success,
            'message': message,
            'results': self.summary.to_dict(),
        }
    
    def _build_summary_message(self) -> str:
        """Build a human-readable summary message."""
        s = self.summary
        lines = [
            "Push completed!",
            "",
            f"Total: {s.total}",
            f"Created: {s.created}",
            f"Updated: {s.updated}",
            f"Skipped: {s.skipped}",
            f"Failed: {s.failed}",
        ]
        if s.renamed > 0:
            lines.append(f"Renamed: {s.renamed}")
        if s.snippets_created > 0:
            lines.append(f"Snippets Created: {s.snippets_created}")
        return "\n".join(lines)
    
    # =========================================================================
    # ITEM EXTRACTION
    # =========================================================================
    
    def _extract_push_items(self, selected_items: Dict[str, Any]) -> List[PushItem]:
        """
        Extract all items from the selected_items structure into a flat list.
        
        Args:
            selected_items: The selection from the UI with folders, snippets, infrastructure
            
        Returns:
            List of PushItem objects
        """
        items = []
        default_strategy = selected_items.get('default_strategy', 'skip')
        
        # Process folders
        for folder in selected_items.get('folders', []):
            folder_name = folder.get('name', '')
            
            # Extract objects from folder
            for obj_type, obj_list in folder.get('objects', {}).items():
                for obj in obj_list:
                    items.append(self._create_push_item(
                        obj, obj_type, folder_name, '', default_strategy
                    ))
            
            # Extract profiles from folder
            for prof_type, prof_list in folder.get('profiles', {}).items():
                for prof in prof_list:
                    items.append(self._create_push_item(
                        prof, prof_type, folder_name, '', default_strategy
                    ))
            
            # Extract HIP from folder
            for hip_type, hip_list in folder.get('hip', {}).items():
                for hip in hip_list:
                    items.append(self._create_push_item(
                        hip, hip_type, folder_name, '', default_strategy
                    ))
            
            # Extract security rules from folder
            for rule in folder.get('security_rules', []):
                items.append(self._create_push_item(
                    rule, 'security_rule', folder_name, '', default_strategy
                ))
        
        # Process snippets
        for snippet in selected_items.get('snippets', []):
            snippet_name = snippet.get('name', '')
            
            # Extract objects from snippet
            for obj_type, obj_list in snippet.get('objects', {}).items():
                for obj in obj_list:
                    items.append(self._create_push_item(
                        obj, obj_type, '', snippet_name, default_strategy
                    ))
            
            # Extract profiles from snippet
            for prof_type, prof_list in snippet.get('profiles', {}).items():
                for prof in prof_list:
                    items.append(self._create_push_item(
                        prof, prof_type, '', snippet_name, default_strategy
                    ))
            
            # Extract security rules from snippet
            for rule in snippet.get('security_rules', []):
                items.append(self._create_push_item(
                    rule, 'security_rule', '', snippet_name, default_strategy
                ))
        
        # Process infrastructure (these have fixed folders)
        for infra_type, infra_list in selected_items.get('infrastructure', {}).items():
            for infra in infra_list:
                folder_name = infra.get('folder', '')
                items.append(self._create_push_item(
                    infra, infra_type, folder_name, '', default_strategy
                ))
        
        logger.info(f"Extracted {len(items)} items to push")
        return items
    
    def _create_push_item(
        self,
        data: Dict[str, Any],
        item_type: str,
        folder: str,
        snippet: str,
        default_strategy: str
    ) -> PushItem:
        """Create a PushItem from raw data."""
        name = data.get('name', 'Unknown')
        
        # Get destination from _destination field or use defaults
        dest_data = data.get('_destination', {})
        
        logger.debug(f"Creating push item: {item_type}/{name}")
        logger.debug(f"  Source: folder={folder}, snippet={snippet}")
        logger.debug(f"  _destination: {dest_data}")
        
        # Check if we have destination data with explicit location settings
        # 'is_inherited' means user selected "Inherit from Parent" in dropdown for LOCATION
        # But they may still have set a different STRATEGY (skip, overwrite, rename)
        has_explicit_location = dest_data and (
            dest_data.get('is_new_snippet') or
            dest_data.get('is_rename_snippet') or
            dest_data.get('is_existing_snippet') or
            (dest_data.get('folder') and not dest_data.get('is_inherited', True))
        )

        # Get the strategy from destination data, falling back to default
        item_strategy_str = dest_data.get('strategy', default_strategy) if dest_data else default_strategy
        try:
            item_strategy = PushStrategy(item_strategy_str.lower() if item_strategy_str else default_strategy)
        except ValueError:
            item_strategy = PushStrategy(default_strategy)

        if not dest_data or not has_explicit_location:
            # Use original location (inherit behavior) but honor the item's strategy
            dest = PushDestination(
                location_type=LocationType.SNIPPET if snippet else LocationType.FOLDER,
                location_name=snippet or folder or 'Shared',
                strategy=item_strategy,
            )
            logger.debug(f"  -> Using original location: {dest.location_name}, strategy: {item_strategy.value}")
        else:
            # Parse explicit destination from UI settings
            dest = PushDestination.from_dict(dest_data)
            # If strategy not set in destination, use default
            if not dest_data.get('strategy'):
                dest.strategy = PushStrategy(default_strategy)
        
        # Clean the data - remove internal fields
        clean_data = self._clean_item_data(data)
        
        return PushItem(
            name=name,
            item_type=item_type,
            data=clean_data,
            destination=dest,
            original_folder=folder,
            original_snippet=snippet,
        )
    
    def _clean_item_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove internal fields from item data before pushing."""
        # Fields to remove
        INTERNAL_FIELDS = {
            '_destination', 'id', 'folder', 'snippet',
            'is_default', 'push_strategy', 'item_type',
            'created_at', 'modified_at', 'metadata',
            'deleted', 'delete_success',
        }
        
        return {k: v for k, v in data.items() if k not in INTERNAL_FIELDS}
    
    # =========================================================================
    # SNIPPET CREATION
    # =========================================================================
    
    def _identify_new_snippets(self, items: List[PushItem]) -> Set[str]:
        """Identify all new snippets that need to be created."""
        new_snippets = set()
        
        for item in items:
            if item.destination.location_type == LocationType.NEW_SNIPPET:
                snippet_name = item.destination.new_snippet_name or item.destination.location_name
                logger.debug(f"[Push] Item '{item.name}' targets new snippet:")
                logger.debug(f"[Push]   new_snippet_name: '{item.destination.new_snippet_name}'")
                logger.debug(f"[Push]   location_name: '{item.destination.location_name}'")
                logger.debug(f"[Push]   resolved to: '{snippet_name}'")
                if snippet_name:
                    new_snippets.add(snippet_name)
        
        logger.normal(f"[Push] Identified {len(new_snippets)} new snippet(s) to create: {sorted(new_snippets)}")
        return new_snippets
    
    def _create_new_snippets(
        self,
        snippet_names: Set[str],
        destination_config: Optional[Dict[str, Any]]
    ) -> Set[str]:
        """Create new snippets in the destination tenant.
        
        Returns:
            Set of snippet names that failed to create (items targeting these should be skipped)
        """
        logger.normal(f"[Push] Creating {len(snippet_names)} new snippet(s): {sorted(snippet_names)}")
        
        failed_snippets = set()
        
        for snippet_name in snippet_names:
            if snippet_name in self._created_snippets:
                logger.detail(f"[Push] Snippet '{snippet_name}' already in created list, skipping")
                continue
            
            # Check if snippet already exists
            exists = self._snippet_exists(snippet_name, destination_config)
            
            if exists:
                logger.normal(f"[Push] Snippet '{snippet_name}' already exists in destination, skipping creation")
                self._report_progress(f"  ⊘ Snippet '{snippet_name}' already exists, skipping", 0, 0)
                self._created_snippets.add(snippet_name)
                continue
            
            # Create the snippet
            logger.normal(f"[Push] Creating new snippet: '{snippet_name}'")
            self._report_progress(f"  Creating snippet: {snippet_name}...", 0, 0)
            try:
                snippet_data = {
                    "name": snippet_name,
                    "description": f"Created by PA Config Lab on {datetime.now().isoformat()}",
                }
                
                result = self.api_client.create_snippet(snippet_data)
                logger.normal(f"[Push] ✓ Snippet '{snippet_name}' created successfully (ID: {result.get('id', 'no-id')})")
                self._report_progress(f"  ✓ Snippet '{snippet_name}' created successfully", 0, 0)
                self._created_snippets.add(snippet_name)
                self.summary.snippets_created += 1
                
            except Exception as e:
                error_msg = f"Failed to create snippet '{snippet_name}': {str(e)}"
                logger.error(f"[Push] ✗ {error_msg}")
                self._report_progress(f"  ✗ Snippet '{snippet_name}' FAILED to create: {str(e)[:50]}...", 0, 0)
                self.summary.errors.append(error_msg)
                failed_snippets.add(snippet_name)
        
        return failed_snippets
    
    def _snippet_exists(
        self,
        snippet_name: str,
        destination_config: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if a snippet exists in the destination."""
        # First check destination_config if available
        if destination_config:
            snippets = destination_config.get('snippets', {})
            # Handle both dict format (name -> snippet) and list format
            if isinstance(snippets, dict):
                if snippet_name in snippets:
                    return True
            elif isinstance(snippets, list):
                if any(s.get('name') == snippet_name for s in snippets):
                    return True
        
        # Otherwise query the API
        try:
            snippets = self.api_client.get_security_policy_snippets()
            return any(s.get('name') == snippet_name for s in snippets)
        except Exception as e:
            logger.warning(f"Could not check if snippet exists: {e}")
            return False
    
    # =========================================================================
    # DEPENDENCY SORTING
    # =========================================================================
    
    def _sort_by_dependencies(self, items: List[PushItem]) -> List[PushItem]:
        """
        Sort items by dependency order.
        
        Detailed ordering:
        1. Tags (can be referenced by many objects)
        2. Schedules (can be referenced by rules)
        3. Base objects (addresses, services)
        4. Object groups (address_groups, service_groups) - depend on base objects
        5. Application filters (must exist before app groups that reference them)
        6. Application groups (depend on application_filters)
        7. Other objects (external_dynamic_list, url_category)
        8. HIP objects (must exist before HIP profiles)
        9. HIP profiles (depend on HIP objects)
        10. Security profiles (anti-spyware, vulnerability, wildfire, etc.)
        11. Security profile groups (depend on individual profiles)
        12. Infrastructure
        13. Rules (depend on objects and profiles) - security rules last
        """
        tags = []
        schedules = []
        base_objects = []  # addresses, services
        object_groups = []  # address_groups, service_groups
        app_filters = []  # application_filter - must be before app_groups
        app_groups = []  # application_group - depends on app_filters
        other_objects = []  # EDLs, url_category, etc.
        hip_objects = []  # HIP objects before HIP profiles
        hip_profiles = []  # HIP profiles depend on HIP objects
        security_profiles = []  # Individual security profiles
        profile_groups = []  # Security profile groups depend on individual profiles
        infrastructure = []
        auth_rules = []  # Authentication rules
        decryption_rules = []  # Decryption rules
        security_rules = []  # Security rules last (depend on most things)
        other = []
        
        for item in items:
            item_type = item.item_type
            
            if item_type == 'tag':
                tags.append(item)
            elif item_type == 'schedule':
                schedules.append(item)
            elif item_type in ('address', 'address_object', 'service', 'service_object'):
                base_objects.append(item)
            elif item_type in ('address_group', 'service_group'):
                object_groups.append(item)
            elif item_type == 'application_filter':
                app_filters.append(item)
            elif item_type == 'application_group':
                app_groups.append(item)
            elif item_type == 'hip_object':
                hip_objects.append(item)
            elif item_type == 'hip_profile':
                hip_profiles.append(item)
            elif item_type in ('security_profile_group', 'profile_group'):
                profile_groups.append(item)
            elif item_type in self.PROFILE_TYPES:
                security_profiles.append(item)
            elif item_type in ('security_rule', 'rule'):
                security_rules.append(item)
            elif item_type == 'authentication_rule':
                auth_rules.append(item)
            elif item_type == 'decryption_rule':
                decryption_rules.append(item)
            elif item_type in self.OBJECT_TYPES:
                other_objects.append(item)
            elif item_type in ('remote_network', 'service_connection', 'ipsec_tunnel',
                                'ike_gateway', 'ike_crypto_profile', 'ipsec_crypto_profile'):
                infrastructure.append(item)
            else:
                other.append(item)
        
        # Return in dependency order
        # Tags -> Schedules -> Base Objects -> Object Groups -> App Filters -> App Groups -> 
        # Other Objects -> HIP Objects -> HIP Profiles -> Security Profiles -> Profile Groups ->
        # Infra -> Auth Rules -> Decryption Rules -> Security Rules -> Other
        return (tags + schedules + base_objects + object_groups + app_filters + app_groups + 
                other_objects + hip_objects + hip_profiles + security_profiles + profile_groups +
                infrastructure + auth_rules + decryption_rules + security_rules + other)
    
    # =========================================================================
    # ITEM PUSHING
    # =========================================================================
    
    def _push_single_item(
        self,
        item: PushItem,
        destination_config: Optional[Dict[str, Any]]
    ):
        """Push a single item to the destination."""
        dest = item.destination
        
        # Resolve destination location
        if dest.location_type == LocationType.NEW_SNIPPET:
            dest_location = dest.new_snippet_name or dest.location_name
            is_snippet = True
        elif dest.location_type == LocationType.SNIPPET:
            dest_location = dest.location_name
            is_snippet = True
        else:
            dest_location = dest.location_name
            is_snippet = False
        
        logger.debug(f"Pushing {item.item_type}/{item.name} to {'snippet' if is_snippet else 'folder'}: {dest_location}")
        
        # Skip default/system profiles - they cannot be modified
        if item.item_type in PROFILE_ITEM_TYPES and item.name in DEFAULT_PROFILE_NAMES:
            logger.info(f"Skipping default profile: {item.item_type}/{item.name}")
            self._add_result(PushResult(
                item_name=item.name,
                item_type=item.item_type,
                destination=dest_location,
                action='skipped',
                success=True,
                message='Default/system profile - cannot be modified'
            ))
            return
        
        # Check if item exists (for conflict resolution)
        # IMPORTANT: For NEW snippets, items CANNOT exist (the snippet doesn't exist yet)
        # This is especially important for security rules which have global name uniqueness
        # We warn about global conflicts during validation, but allow the push to proceed
        if dest.location_type == LocationType.NEW_SNIPPET:
            logger.debug(f"_item_exists: {item.item_type}/{item.name} -> NEW SNIPPET '{dest_location}', skipping existence check")
            exists = False
        else:
            exists = self._item_exists(item, dest_location, is_snippet, destination_config)
        
        # Apply conflict resolution
        if exists:
            if dest.strategy == PushStrategy.SKIP:
                self._add_result(PushResult(
                    item_name=item.name,
                    item_type=item.item_type,
                    destination=dest_location,
                    action='skipped',
                    success=True,
                    message='Already exists, skipped per conflict resolution'
                ))
                return
            
            elif dest.strategy == PushStrategy.RENAME:
                # Rename the item
                new_name = f"{item.name}-copy"
                item.data['name'] = new_name
                self._name_mappings[item.name] = new_name
                logger.info(f"Renaming {item.name} -> {new_name}")
            
            elif dest.strategy == PushStrategy.OVERWRITE:
                # In Phase 2, delete was already done in Phase 1
                # If delete succeeded, item no longer exists - proceed to create
                # If delete failed, this item would have been skipped before reaching here
                # So we can proceed directly to create
                pass
        
        # Create the item
        try:
            self._create_item(item, dest_location, is_snippet)
            
            action = 'renamed' if dest.strategy == PushStrategy.RENAME and exists else 'created'
            self._add_result(PushResult(
                item_name=item.data.get('name', item.name),
                item_type=item.item_type,
                destination=dest_location,
                action=action,
                success=True,
                message=f'Successfully {action}'
            ))
            
        except Exception as e:
            error_msg = str(e)
            # Check for "already exists" errors
            if 'already exists' in error_msg.lower() or '409' in error_msg:
                self._add_result(PushResult(
                    item_name=item.name,
                    item_type=item.item_type,
                    destination=dest_location,
                    action='skipped',
                    success=True,
                    message='Already exists (detected during create)'
                ))
            else:
                logger.error(f"Failed to create {item.item_type}/{item.name}: {e}")
                self._add_result(PushResult(
                    item_name=item.name,
                    item_type=item.item_type,
                    destination=dest_location,
                    action='failed',
                    success=False,
                    message='Creation failed',
                    error=error_msg[:500]  # Allow longer errors for better diagnostics
                ))
    
    def _item_exists(
        self,
        item: PushItem,
        location: str,
        is_snippet: bool,
        destination_config: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if an item exists in the destination.

        For snippet destinations, only checks if the item exists in that specific snippet.
        For folder destinations, checks global objects.
        Security rules are handled specially based on destination type.
        """
        if not destination_config:
            logger.debug(f"_item_exists: No destination_config for {item.item_type}/{item.name}")
            return False

        item_type = item.item_type
        item_name = item.name

        # SECURITY RULES - check based on destination type
        # Snippets are isolated until associated with a folder
        if item_type in ('security_rule', 'rule'):
            all_rule_names = destination_config.get('all_rule_names', {})

            if is_snippet:
                # For snippet destination, only check if rule exists in THIS specific snippet
                rule_info = all_rule_names.get(item_name, {})
                if isinstance(rule_info, dict):
                    exists = rule_info.get('snippet') == location
                else:
                    exists = False
                logger.debug(f"_item_exists: Checking snippet '{location}' for {item_type}/{item_name}: {exists}")
            else:
                # For folder destination, check if rule exists in any folder
                exists = item_name in all_rule_names
                logger.debug(f"_item_exists: Checking all_rule_names for {item_type}/{item_name}: {exists} (total rules: {len(all_rule_names)})")
            return exists

        # For snippet destinations, ONLY check snippet_objects for that specific snippet
        # Do NOT check global objects - items in folders don't prevent creation in snippets
        if is_snippet:
            snippet_objects = destination_config.get('snippet_objects', {}).get(location, {})
            type_objects = snippet_objects.get(item_type, {})
            exists = item_name in type_objects
            logger.debug(f"_item_exists: Checking snippet '{location}' for {item_type}/{item_name}: {exists}")
            # Also check plural forms for snippet
            if not exists:
                plural_type = f"{item_type}s" if not item_type.endswith('s') else item_type
                type_objects_plural = snippet_objects.get(plural_type, {})
                exists = item_name in type_objects_plural
                if exists:
                    logger.debug(f"_item_exists: Found {item_type}/{item_name} in snippet plural key '{plural_type}'")
            return exists

        # For folder destinations, check global objects
        objects = destination_config.get('objects', {}).get(item_type, {})
        exists = item_name in objects
        logger.debug(f"_item_exists: Checking global objects for {item_type}/{item_name}: {exists}")
        if exists:
            return True

        # Also check plural forms (e.g., 'application_filters' vs 'application_filter')
        plural_type = f"{item_type}s" if not item_type.endswith('s') else item_type
        objects_plural = destination_config.get('objects', {}).get(plural_type, {})
        if item_name in objects_plural:
            logger.debug(f"_item_exists: Found {item_type}/{item_name} in plural key '{plural_type}'")
            return True

        return False
    
    def _delete_existing_item(
        self,
        item: PushItem,
        location: str,
        is_snippet: bool,
        destination_config: Optional[Dict[str, Any]]
    ) -> bool:
        """Delete an existing item for OVERWRITE mode (legacy - use _delete_item_for_overwrite)."""
        return self._delete_item_for_overwrite(item, destination_config)
    
    def _item_exists_in_dest(
        self,
        item: PushItem,
        destination_config: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if item exists in destination for OVERWRITE detection."""
        if not destination_config:
            return False
        
        dest = item.destination
        
        # Resolve location
        if dest.location_type == LocationType.NEW_SNIPPET:
            # New snippets can't have existing items
            return False
        elif dest.location_type == LocationType.SNIPPET:
            location = dest.location_name
            is_snippet = True
        else:
            location = dest.location_name
            is_snippet = False
        
        return self._item_exists(item, location, is_snippet, destination_config)
    
    def _get_item_destination(self, item: PushItem) -> str:
        """Get the destination location string for an item."""
        dest = item.destination
        if dest.location_type == LocationType.NEW_SNIPPET:
            return dest.new_snippet_name or dest.location_name
        return dest.location_name
    
    def _sort_for_delete(self, items: List[PushItem]) -> List[PushItem]:
        """
        Sort items for DELETE phase (reverse dependency order).
        
        Delete order: Items that REFERENCE others must be deleted FIRST.
        - Rules reference objects (addresses, services, profiles)
        - Groups reference their members
        - Profile groups reference individual profiles
        
        So: Rules -> Profile Groups -> Groups -> Profiles -> Base Objects -> Tags
        """
        # Define delete priority (higher = delete first)
        # RULES must be deleted first - they reference everything else
        delete_priority = {
            # Rules (delete first - they reference objects)
            'security_rule': 100,
            'rule': 100,
            'authentication_rule': 100,
            'decryption_rule': 100,
            
            # Profile groups (reference individual profiles)
            'security_profile_group': 90,
            'profile_group': 90,
            
            # Groups (reference their members)
            'application_group': 80,
            'address_group': 80,
            'service_group': 80,
            
            # Individual profiles (may be referenced by profile groups and rules)
            'hip_profile': 70,
            'wildfire_profile': 70,
            'wildfire_antivirus_profile': 70,
            'anti_spyware_profile': 70,
            'vulnerability_profile': 70,
            'vulnerability_protection_profile': 70,
            'url_filtering_profile': 70,
            'file_blocking_profile': 70,
            'decryption_profile': 70,
            'dns_security_profile': 70,
            
            # Application filters (may be in groups)
            'application_filter': 65,
            
            # HIP objects (referenced by HIP profiles)
            'hip_object': 60,
            
            # Base objects (referenced by rules and groups)
            'address': 50,
            'address_object': 50,
            'service': 50,
            'service_object': 50,
            'schedule': 50,
            
            # Tags and categories (may be on any object)
            'tag': 40,
            'url_category': 40,
            'external_dynamic_list': 40,
        }
        
        def get_delete_order(item: PushItem) -> int:
            return -delete_priority.get(item.item_type, 0)  # Negative for descending
        
        return sorted(items, key=get_delete_order)
    
    def _should_skip_due_to_dep_failure(self, item: PushItem) -> bool:
        """
        Check if an item should be skipped because a dependency failed to delete.
        
        For example:
        - If application_group delete failed, skip its application_filters
        - If address_group delete failed, skip its addresses
        """
        item_type = item.item_type
        
        # Check based on item type and its potential parents
        if item_type == 'application_filter':
            # Check if any application_group failed (they reference filters)
            for failed in self._failed_deletes:
                if failed.startswith('application_group:'):
                    # Check if this filter is referenced by the failed group
                    # For now, be conservative and skip all filters if any group failed
                    return True
        
        elif item_type == 'address':
            # Check if any address_group failed
            for failed in self._failed_deletes:
                if failed.startswith('address_group:'):
                    return True
        
        elif item_type == 'service':
            # Check if any service_group failed
            for failed in self._failed_deletes:
                if failed.startswith('service_group:'):
                    return True
        
        return False
    
    def _delete_item_for_overwrite(
        self,
        item: PushItem,
        destination_config: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Delete an existing item for OVERWRITE mode.
        
        Returns True if delete succeeded, False otherwise.
        """
        item_type = item.item_type
        item_name = item.name
        
        # Get item ID from destination config
        item_id = self._get_item_id_from_dest(item, destination_config)
        
        if not item_id:
            logger.warning(f"Cannot delete {item_type}/{item_name}: ID not found in destination config")
            return False
        
        try:
            logger.info(f"Deleting {item_type}/{item_name} (ID: {item_id})")
            
            # Route to appropriate delete method
            # Address objects
            if item_type in ('address', 'address_object'):
                self.api_client.delete_address(item_id)
            elif item_type == 'address_group':
                self.api_client.delete_address_group(item_id)
            
            # Service objects
            elif item_type in ('service', 'service_object'):
                self.api_client.delete_service(item_id)
            elif item_type == 'service_group':
                self.api_client.delete_service_group(item_id)
            
            # Application objects
            elif item_type == 'application_filter':
                self.api_client.delete_application_filter(item_id)
            elif item_type == 'application_group':
                self.api_client.delete_application_group(item_id)
            
            # Rules
            elif item_type in ('security_rule', 'rule'):
                self.api_client.delete_security_rule(item_id)
            elif item_type == 'authentication_rule':
                self.api_client.delete_authentication_rule(item_id)
            elif item_type == 'decryption_rule':
                self.api_client.delete_decryption_rule(item_id)
            
            # Security profiles
            elif item_type in ('wildfire_profile', 'wildfire_antivirus_profile'):
                self.api_client.delete_wildfire_profile(item_id)
            elif item_type == 'anti_spyware_profile':
                self.api_client.delete_anti_spyware_profile(item_id)
            elif item_type in ('vulnerability_profile', 'vulnerability_protection_profile'):
                self.api_client.delete_vulnerability_profile(item_id)
            elif item_type == 'url_filtering_profile':
                self.api_client.delete_url_filtering_profile(item_id)
            elif item_type == 'file_blocking_profile':
                self.api_client.delete_file_blocking_profile(item_id)
            elif item_type == 'dns_security_profile':
                self.api_client.delete_dns_security_profile(item_id)
            elif item_type == 'decryption_profile':
                self.api_client.delete_decryption_profile(item_id)
            elif item_type in ('security_profile_group', 'profile_group'):
                self.api_client.delete_profile_group(item_id)
            
            # HIP objects
            elif item_type == 'hip_profile':
                self.api_client.delete_hip_profile(item_id)
            elif item_type == 'hip_object':
                self.api_client.delete_hip_object(item_id)
            
            # Schedules
            elif item_type == 'schedule':
                self.api_client.delete_schedule(item_id)
            
            # Tags
            elif item_type == 'tag':
                self.api_client.delete_tag(item_id)
            
            # Types that don't support delete - skip gracefully
            elif item_type == 'url_category':
                logger.warning(f"Delete not implemented for url_category (system object)")
                return True  # Treat as success to continue
            elif item_type == 'external_dynamic_list':
                self.api_client.delete_external_dynamic_list(item_id)
            
            else:
                logger.warning(f"Delete not implemented for {item_type}")
                return False
            
            logger.info(f"Successfully deleted {item_type}/{item_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete {item_type}/{item_name}: {e}")
            return False
    
    def _get_item_id_from_dest(
        self,
        item: PushItem,
        destination_config: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Get item ID from destination config for deletion."""
        if not destination_config:
            return None
        
        dest = item.destination
        item_type = item.item_type
        item_name = item.name
        
        # SECURITY RULES are stored differently - check all_rule_names or security_rules
        if item_type in ('security_rule', 'rule'):
            # First check all_rule_names (has location info but may not have ID)
            all_rule_names = destination_config.get('all_rule_names', {})
            if item_name in all_rule_names:
                rule_info = all_rule_names[item_name]
                if isinstance(rule_info, dict) and rule_info.get('id'):
                    return rule_info.get('id')
            
            # Check security_rules dict which has full rule data by folder
            security_rules = destination_config.get('security_rules', {})
            for folder_name, folder_rules in security_rules.items():
                if isinstance(folder_rules, dict) and item_name in folder_rules:
                    rule_data = folder_rules[item_name]
                    if isinstance(rule_data, dict) and rule_data.get('id'):
                        return rule_data.get('id')
            
            # Check all_dest_rules which may have full rule data
            all_dest_rules = destination_config.get('all_dest_rules', {})
            if item_name in all_dest_rules:
                rule_data = all_dest_rules[item_name]
                if isinstance(rule_data, dict) and rule_data.get('id'):
                    return rule_data.get('id')
        
        # AUTHENTICATION RULES and DECRYPTION RULES - may be stored similarly
        if item_type in ('authentication_rule', 'decryption_rule'):
            # Check in objects with type key
            auth_rules = destination_config.get('objects', {}).get(item_type, {})
            if item_name in auth_rules:
                obj = auth_rules[item_name]
                if isinstance(obj, dict):
                    return obj.get('id')
        
        # Check snippet_objects for snippet destinations
        if dest.location_type == LocationType.SNIPPET:
            snippet_name = dest.location_name
            snippet_objects = destination_config.get('snippet_objects', {}).get(snippet_name, {})
            type_objects = snippet_objects.get(item_type, {})
            if item_name in type_objects:
                obj = type_objects[item_name]
                if isinstance(obj, dict):
                    return obj.get('id')
        
        # Check global objects
        objects = destination_config.get('objects', {}).get(item_type, {})
        if item_name in objects:
            obj = objects[item_name]
            if isinstance(obj, dict):
                return obj.get('id')
        
        # Also check if we have the full objects list with plural/alias forms
        all_objects = destination_config.get('objects', {})
        type_aliases = {
            'address_object': ['address', 'address_object', 'addresses'],
            'service_object': ['service', 'service_object', 'services'],
            'wildfire_profile': ['wildfire_profile', 'wildfire_profiles', 'wildfire_antivirus_profile'],
            'authentication_rule': ['authentication_rule', 'authentication_rules'],
            'hip_profile': ['hip_profile', 'hip_profiles'],
            'hip_object': ['hip_object', 'hip_objects'],
        }
        
        check_keys = type_aliases.get(item_type, [item_type, f"{item_type}s"])
        for type_key in check_keys:
            type_objs = all_objects.get(type_key, {})
            if isinstance(type_objs, dict) and item_name in type_objs:
                obj = type_objs[item_name]
                if isinstance(obj, dict):
                    return obj.get('id')
        
        return None
    
    def _create_item(self, item: PushItem, location: str, is_snippet: bool):
        """Create an item using the appropriate API method."""
        item_type = item.item_type
        data = item.data
        
        # Route to appropriate create method based on item type
        # Objects
        if item_type in ('address', 'address_object'):
            self._create_address(data, location, is_snippet)
        elif item_type == 'address_group':
            self._create_address_group(data, location, is_snippet)
        elif item_type in ('service', 'service_object'):
            self._create_service(data, location, is_snippet)
        elif item_type == 'service_group':
            self._create_service_group(data, location, is_snippet)
        elif item_type == 'application_filter':
            self._create_application_filter(data, location, is_snippet)
        elif item_type == 'application_group':
            self._create_application_group(data, location, is_snippet)
        elif item_type == 'tag':
            self._create_tag(data, location, is_snippet)
        elif item_type == 'url_category':
            self._create_url_category(data, location, is_snippet)
        elif item_type == 'external_dynamic_list':
            self._create_edl(data, location, is_snippet)
        elif item_type == 'schedule':
            self._create_schedule(data, location, is_snippet)
        # HIP
        elif item_type == 'hip_object':
            self._create_hip_object(data, location, is_snippet)
        elif item_type == 'hip_profile':
            self._create_hip_profile(data, location, is_snippet)
        # Security Profiles
        elif item_type == 'security_profile_group':
            self._create_profile_group(data, location, is_snippet)
        elif item_type == 'anti_spyware_profile':
            self._create_anti_spyware_profile(data, location, is_snippet)
        elif item_type in ('vulnerability_protection_profile', 'vulnerability_profile'):
            self._create_vulnerability_profile(data, location, is_snippet)
        elif item_type == 'url_filtering_profile':
            self._create_url_filtering_profile(data, location, is_snippet)
        elif item_type == 'file_blocking_profile':
            self._create_file_blocking_profile(data, location, is_snippet)
        elif item_type in ('wildfire_antivirus_profile', 'wildfire_profile'):
            self._create_wildfire_profile(data, location, is_snippet)
        elif item_type == 'decryption_profile':
            self._create_decryption_profile(data, location, is_snippet)
        elif item_type == 'dns_security_profile':
            self._create_dns_security_profile(data, location, is_snippet)
        elif item_type == 'http_header_profile':
            self._create_http_header_profile(data, location, is_snippet)
        elif item_type == 'certificate_profile':
            self._create_certificate_profile(data, location, is_snippet)
        # Rules
        elif item_type in ('security_rule', 'rule'):
            self._create_security_rule(data, location, is_snippet)
        elif item_type == 'authentication_rule':
            self._create_authentication_rule(data, location, is_snippet)
        elif item_type == 'decryption_rule':
            self._create_decryption_rule(data, location, is_snippet)
        # Infrastructure
        elif item_type == 'ike_crypto_profile':
            self._create_ike_crypto_profile(data, location)
        elif item_type == 'ipsec_crypto_profile':
            self._create_ipsec_crypto_profile(data, location)
        elif item_type == 'ike_gateway':
            self._create_ike_gateway(data, location)
        elif item_type == 'ipsec_tunnel':
            self._create_ipsec_tunnel(data, location)
        else:
            raise ValueError(f"Unsupported item type: {item_type}")
    
    # =========================================================================
    # API CREATE WRAPPERS
    # =========================================================================
    
    def _create_address(self, data: Dict, location: str, is_snippet: bool):
        """Create an address object."""
        from prisma.api_endpoints import APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.ADDRESSES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            self.api_client.create_address(data, location)
    
    def _create_address_group(self, data: Dict, location: str, is_snippet: bool):
        """Create an address group."""
        from prisma.api_endpoints import APIEndpoints, SASE_BASE_URL
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.ADDRESS_GROUPS}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            self.api_client.create_address_group(data, location)
    
    def _create_service(self, data: Dict, location: str, is_snippet: bool):
        """Create a service object."""
        from prisma.api_endpoints import APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.SERVICES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            self.api_client.create_service(data, location)
    
    def _create_service_group(self, data: Dict, location: str, is_snippet: bool):
        """Create a service group."""
        from prisma.api_endpoints import APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.SERVICE_GROUPS}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            self.api_client.create_service_group(data, location)
    
    def _create_application_filter(self, data: Dict, location: str, is_snippet: bool):
        """Create an application filter."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.APPLICATION_FILTERS}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.APPLICATION_FILTERS + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_application_group(self, data: Dict, location: str, is_snippet: bool):
        """Create an application group."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.APPLICATION_GROUPS}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.APPLICATION_GROUPS + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_security_rule(self, data: Dict, location: str, is_snippet: bool):
        """Create a security rule."""
        from prisma.api_endpoints import APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.SECURITY_RULES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            self.api_client.create_security_rule(data, location)
    
    def _create_tag(self, data: Dict, location: str, is_snippet: bool):
        """Create a tag."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.TAGS}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.TAGS + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_url_category(self, data: Dict, location: str, is_snippet: bool):
        """Create a URL category."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.URL_CATEGORIES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.URL_CATEGORIES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_edl(self, data: Dict, location: str, is_snippet: bool):
        """Create an external dynamic list."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.EXTERNAL_DYNAMIC_LISTS}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.EXTERNAL_DYNAMIC_LISTS + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_profile_group(self, data: Dict, location: str, is_snippet: bool):
        """Create a security profile group."""
        from prisma.api_endpoints import APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.PROFILE_GROUPS}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            self.api_client.create_profile_group(data, location)
    
    def _create_schedule(self, data: Dict, location: str, is_snippet: bool):
        """Create a schedule object."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.SCHEDULES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.SCHEDULES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_hip_object(self, data: Dict, location: str, is_snippet: bool):
        """Create a HIP object."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.HIP_OBJECTS}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.HIP_OBJECTS + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_hip_profile(self, data: Dict, location: str, is_snippet: bool):
        """Create a HIP profile."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.HIP_PROFILES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.HIP_PROFILES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_anti_spyware_profile(self, data: Dict, location: str, is_snippet: bool):
        """Create an anti-spyware profile."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.ANTI_SPYWARE_PROFILES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.ANTI_SPYWARE_PROFILES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_vulnerability_profile(self, data: Dict, location: str, is_snippet: bool):
        """Create a vulnerability protection profile."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.VULNERABILITY_PROTECTION_PROFILES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.VULNERABILITY_PROTECTION_PROFILES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_url_filtering_profile(self, data: Dict, location: str, is_snippet: bool):
        """Create a URL filtering profile."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.URL_ACCESS_PROFILES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.URL_ACCESS_PROFILES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_file_blocking_profile(self, data: Dict, location: str, is_snippet: bool):
        """Create a file blocking profile."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.FILE_BLOCKING_PROFILES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.FILE_BLOCKING_PROFILES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_wildfire_profile(self, data: Dict, location: str, is_snippet: bool):
        """Create a WildFire antivirus profile."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.WILDFIRE_ANTI_VIRUS_PROFILES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.WILDFIRE_ANTI_VIRUS_PROFILES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_decryption_profile(self, data: Dict, location: str, is_snippet: bool):
        """Create a decryption profile."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.DECRYPTION_PROFILES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.DECRYPTION_PROFILES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_dns_security_profile(self, data: Dict, location: str, is_snippet: bool):
        """Create a DNS security profile."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.DNS_SECURITY_PROFILES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.DNS_SECURITY_PROFILES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)

    def _create_http_header_profile(self, data: Dict, location: str, is_snippet: bool):
        """Create an HTTP header profile."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.HTTP_HEADER_PROFILES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.HTTP_HEADER_PROFILES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)

    def _create_certificate_profile(self, data: Dict, location: str, is_snippet: bool):
        """Create a certificate profile."""
        from prisma.api_endpoints import build_folder_query, APIEndpoints
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        if is_snippet:
            url = f"{APIEndpoints.CERTIFICATE_PROFILES}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = APIEndpoints.CERTIFICATE_PROFILES + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)

    def _create_authentication_rule(self, data: Dict, location: str, is_snippet: bool):
        """Create an authentication rule."""
        from prisma.api_endpoints import build_folder_query, SASE_BASE_URL
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        # Authentication rules endpoint
        endpoint = f"{SASE_BASE_URL}/authentication-rules"
        if is_snippet:
            url = f"{endpoint}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = endpoint + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)
    
    def _create_decryption_rule(self, data: Dict, location: str, is_snippet: bool):
        """Create a decryption rule."""
        from prisma.api_endpoints import build_folder_query, SASE_BASE_URL
        from urllib.parse import quote
        encoded_loc = quote(location, safe="")
        # Decryption rules endpoint
        endpoint = f"{SASE_BASE_URL}/decryption-rules"
        if is_snippet:
            url = f"{endpoint}?snippet={encoded_loc}"
            self.api_client._make_request("POST", url, data=data, use_cache=False)
        else:
            url = endpoint + build_folder_query(location)
            self.api_client._make_request("POST", url, data=data, use_cache=False)

    # =========================================================================
    # INFRASTRUCTURE CREATE WRAPPERS
    # =========================================================================

    def _create_ike_crypto_profile(self, data: Dict, location: str):
        """Create an IKE crypto profile (folder only, no snippet support)."""
        self.api_client.create_ike_crypto_profile(data, location)

    def _create_ipsec_crypto_profile(self, data: Dict, location: str):
        """Create an IPSec crypto profile (folder only, no snippet support)."""
        self.api_client.create_ipsec_crypto_profile(data, location)

    def _create_ike_gateway(self, data: Dict, location: str):
        """Create an IKE gateway (folder only, no snippet support)."""
        self.api_client.create_ike_gateway(data, location)

    def _create_ipsec_tunnel(self, data: Dict, location: str):
        """Create an IPSec tunnel (folder only, no snippet support)."""
        self.api_client.create_ipsec_tunnel(data, location)
