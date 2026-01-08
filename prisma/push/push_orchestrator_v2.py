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
    OBJECT_TYPES = {
        'address': 'address',
        'address_group': 'address_group',
        'service': 'service',
        'service_group': 'service_group',
        'application': 'application',
        'application_group': 'application_group',
        'application_filter': 'application_filter',
        'external_dynamic_list': 'external_dynamic_list',
        'url_category': 'url_category',
        'tag': 'tag',
    }
    
    PROFILE_TYPES = {
        'security_profile_group': 'profile_group',
        'anti_spyware_profile': 'anti_spyware_profile',
        'vulnerability_protection_profile': 'vulnerability_protection_profile',
        'url_filtering_profile': 'url_filtering_profile',
        'file_blocking_profile': 'file_blocking_profile',
        'wildfire_antivirus_profile': 'wildfire_antivirus_profile',
        'decryption_profile': 'decryption_profile',
        'dns_security_profile': 'dns_security_profile',
    }
    
    RULE_TYPES = {
        'security_rule': 'security_rule',
        'rule': 'security_rule',  # Alias
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
            elif result.action == 'skipped':
                self.summary.skipped += 1
            elif result.action == 'renamed':
                self.summary.renamed += 1
        else:
            self.summary.failed += 1
            if result.error:
                self.summary.errors.append(f"{result.item_type}/{result.item_name}: {result.error}")
    
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
        
        Args:
            selected_items: Dictionary from selection list with folders, snippets, infrastructure
            destination_config: Optional destination config for conflict detection
            
        Returns:
            Push results dictionary
        """
        self.summary = PushSummary(start_time=datetime.now())
        self._created_snippets = set()
        self._name_mappings = {}
        
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
            
            # Step 3: Sort items by dependency order
            # For now, simple ordering: objects -> profiles -> rules
            sorted_items = self._sort_by_dependencies(items)
            
            # Step 4: Push each item
            current = 0
            for item in sorted_items:
                current += 1
                
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
                
                self._report_progress(
                    f"Pushing {item.item_type}: {item.name}...",
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
        
        # Check if we have destination data with actual settings
        # 'is_inherited' means user selected "Inherit from Parent" in dropdown
        has_explicit_dest = dest_data and (
            dest_data.get('is_new_snippet') or 
            dest_data.get('is_rename_snippet') or
            not dest_data.get('is_inherited', True)  # Not inherited = explicit
        )
        
        if not dest_data or not has_explicit_dest:
            # Use original location (inherit behavior)
            dest = PushDestination(
                location_type=LocationType.SNIPPET if snippet else LocationType.FOLDER,
                location_name=snippet or folder or 'Shared',
                strategy=PushStrategy(default_strategy),
            )
            logger.debug(f"  -> Using original location: {dest.location_name}")
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
        2. Base objects (addresses, services)
        3. Object groups (address_groups, service_groups) - depend on base objects
        4. Application filters (must exist before app groups that reference them)
        5. Application groups (depend on application_filters)
        6. Other objects (external_dynamic_list, url_category)
        7. Profiles
        8. Infrastructure
        9. Rules (depend on objects and profiles)
        """
        tags = []
        base_objects = []  # addresses, services
        object_groups = []  # address_groups, service_groups
        app_filters = []  # application_filter - must be before app_groups
        app_groups = []  # application_group - depends on app_filters
        other_objects = []  # EDLs, url_category, etc.
        profiles = []
        rules = []
        infrastructure = []
        other = []
        
        for item in items:
            item_type = item.item_type
            
            if item_type == 'tag':
                tags.append(item)
            elif item_type in ('address', 'service'):
                base_objects.append(item)
            elif item_type in ('address_group', 'service_group'):
                object_groups.append(item)
            elif item_type == 'application_filter':
                app_filters.append(item)
            elif item_type == 'application_group':
                app_groups.append(item)
            elif item_type in self.OBJECT_TYPES:
                other_objects.append(item)
            elif item_type in self.PROFILE_TYPES:
                profiles.append(item)
            elif item_type in self.RULE_TYPES:
                rules.append(item)
            elif item_type in ('remote_network', 'service_connection', 'ipsec_tunnel',
                                'ike_gateway', 'ike_crypto_profile', 'ipsec_crypto_profile'):
                infrastructure.append(item)
            else:
                other.append(item)
        
        # Return in dependency order
        # Tags -> Base Objects -> Object Groups -> App Filters -> App Groups -> Other Objects -> Profiles -> Infra -> Rules
        return (tags + base_objects + object_groups + app_filters + app_groups + 
                other_objects + profiles + infrastructure + rules + other)
    
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
        
        # Check if item exists (for conflict resolution)
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
                # Delete existing item first
                deleted = self._delete_existing_item(item, dest_location, is_snippet, destination_config)
                if not deleted:
                    self._add_result(PushResult(
                        item_name=item.name,
                        item_type=item.item_type,
                        destination=dest_location,
                        action='failed',
                        success=False,
                        message='Could not delete existing item for overwrite',
                        error='Delete failed'
                    ))
                    return
        
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
        """Check if an item exists in the destination."""
        # For now, rely on API errors for conflict detection
        # TODO: Implement proper existence checking using destination_config
        return False
    
    def _delete_existing_item(
        self,
        item: PushItem,
        location: str,
        is_snippet: bool,
        destination_config: Optional[Dict[str, Any]]
    ) -> bool:
        """Delete an existing item for OVERWRITE mode."""
        # TODO: Implement delete logic
        # For Phase 1, we'll skip overwrite and just let creates fail
        logger.warning(f"Delete not implemented for {item.item_type}/{item.name}")
        return False
    
    def _create_item(self, item: PushItem, location: str, is_snippet: bool):
        """Create an item using the appropriate API method."""
        item_type = item.item_type
        data = item.data
        
        # Route to appropriate create method based on item type
        if item_type == 'address':
            self._create_address(data, location, is_snippet)
        elif item_type == 'address_group':
            self._create_address_group(data, location, is_snippet)
        elif item_type == 'service':
            self._create_service(data, location, is_snippet)
        elif item_type == 'service_group':
            self._create_service_group(data, location, is_snippet)
        elif item_type == 'application_filter':
            self._create_application_filter(data, location, is_snippet)
        elif item_type == 'application_group':
            self._create_application_group(data, location, is_snippet)
        elif item_type in ('security_rule', 'rule'):
            self._create_security_rule(data, location, is_snippet)
        elif item_type == 'tag':
            self._create_tag(data, location, is_snippet)
        elif item_type == 'url_category':
            self._create_url_category(data, location, is_snippet)
        elif item_type == 'external_dynamic_list':
            self._create_edl(data, location, is_snippet)
        elif item_type == 'security_profile_group':
            self._create_profile_group(data, location, is_snippet)
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
