"""
Pull orchestration for Prisma Access configuration capture.

This module orchestrates the complete pull process using:
- Smart folder selection (bottom-level folders capture inherited configs)
- Bulk queries per folder (3 folders instead of looping through all)
- ConfigItem objects
- Workflow infrastructure
- Efficient distribution to folders/snippets

For Prisma Access, querying bottom-level folders (Mobile Users, Remote Networks, 
Explicit Proxy) automatically includes inherited configs from parent folders.
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import logging

from ..api_client import PrismaAccessAPIClient
from ..api_endpoints import is_folder_allowed, FOLDER_EXCLUSIONS, FOLDER_ONLY
from config.workflows import WorkflowConfig, WorkflowResult, WorkflowState, DefaultManager
from config.workflows.workflow_utils import (
    validate_configuration,
    filter_by_location,
    group_by_location,
    handle_workflow_error,
)
from config.models.factory import ConfigItemFactory
from config.models.base import ConfigItem

logger = logging.getLogger(__name__)


class PullOrchestrator:
    """
    Orchestrate the complete configuration pull process.
    
    For Prisma Access, this uses an optimized approach:
    - Query 3 bottom-level folders (Mobile Users, Remote Networks, Explicit Proxy)
    - These folders inherit configs from parent folders
    - Loop through all snippets (can't be bulk queried)
    - Bulk fetch infrastructure items (no folder parameter needed)
    """
    
    # Bottom-level folders for Prisma Access (no children)
    # Querying these captures inherited configs from parents
    PRISMA_ACCESS_BOTTOM_FOLDERS = [
        'Mobile Users',
        'Remote Networks',
        'Mobile Users Explicit Proxy',
    ]

    # Display name mapping (API name -> User-friendly display name)
    # IMPORTANT: Always use display names in logs, progress messages, and UI
    FOLDER_DISPLAY_NAMES = {
        'All': 'Global',
        'Shared': 'Prisma Access',
        'Mobile Users Container': 'Mobile Users Container',
        'Mobile Users': 'Mobile Users',
        'Mobile Users Explicit Proxy': 'Mobile Users Explicit Proxy',
        'Remote Networks': 'Remote Networks',
    }

    @classmethod
    def get_display_name(cls, api_name: str) -> str:
        """Convert API folder name to user-friendly display name."""
        return cls.FOLDER_DISPLAY_NAMES.get(api_name, api_name)
    
    # Configuration item types to capture (folder-based)
    FOLDER_TYPES = [
        'address_object',
        'address_group',
        'region',  # Address regions
        'service_object',
        'service_group',
        'tag',
        # 'application_object',  # Excluded: 7000+ predefined apps, only pull if specifically requested
        'application_group',
        'application_filter',
        'schedule',
        'hip_object',
        'hip_profile',
        'external_dynamic_list',
        'custom_url_category',
        'anti_spyware_profile',
        'vulnerability_profile',
        'file_blocking_profile',
        'wildfire_profile',
        'dns_security_profile',
        'decryption_profile',
        'http_header_profile',
        'certificate_profile',
        'profile_group',
        # Note: qos_profile has folder restrictions - handled separately
        'local_user',
        'local_user_group',
        'security_rule',
        'decryption_rule',
        'authentication_rule',
        'qos_policy_rule',
    ]
    
    # Types that only work in specific folders - now uses centralized FOLDER_ONLY from api_endpoints
    # This is kept for backwards compatibility but the actual check uses is_folder_allowed()
    FOLDER_RESTRICTED_TYPES = FOLDER_ONLY
    
    # Snippet-based types (must loop through all snippets)
    # Should match FOLDER_TYPES for consistency - snippets can contain the same item types
    SNIPPET_TYPES = [
        'address_object',
        'address_group',
        'region',  # Address regions
        'service_object',
        'service_group',
        'tag',
        # 'application_object',  # Excluded: 7000+ predefined apps, only pull if specifically requested
        'application_group',
        'application_filter',
        'schedule',
        'hip_object',
        'hip_profile',
        'external_dynamic_list',
        'custom_url_category',
        'anti_spyware_profile',
        'vulnerability_profile',
        'file_blocking_profile',
        'wildfire_profile',
        'dns_security_profile',
        'decryption_profile',
        'http_header_profile',
        'certificate_profile',
        'profile_group',
        'local_user',
        'local_user_group',
        'security_rule',
        'decryption_rule',
        'authentication_rule',
        'qos_policy_rule',
    ]
    
    # Infrastructure types (no folder parameter needed)
    # Note: Some types may fail if no infrastructure is configured
    # The pull will continue even if individual types fail
    # 
    # Note: IKE/IPsec items exist in BOTH Remote Networks and Service Connections
    # We need to pull them from both folders
    #
    # Note: 'portal' and 'gateway' (GlobalProtect) are NOT supported via SCM API
    # They return 404 errors - these are managed differently in Prisma Access
    INFRASTRUCTURE_TYPES = [
        'remote_network',
        'ike_gateway',
        'ipsec_tunnel',
        'ike_crypto_profile',
        'ipsec_crypto_profile',
        'service_connection',
        'agent_profile',
        'auto_tag_action',  # General infrastructure - no folder parameter
        # 'portal',   # Not available via SCM API (404)
        # 'gateway',  # Not available via SCM API (404)
    ]
    
    # Infrastructure items that exist in multiple folders
    # These need to be pulled separately for each folder
    MULTI_FOLDER_INFRA_TYPES = {
        'ike_gateway': ['Remote Networks', 'Service Connections'],
        'ipsec_tunnel': ['Remote Networks', 'Service Connections'],
        'ike_crypto_profile': ['Remote Networks', 'Service Connections'],
        'ipsec_crypto_profile': ['Remote Networks', 'Service Connections'],
        'agent_profile': ['Mobile Users'],  # Mobile agent items need folder parameter
        # 'portal' and 'gateway' removed - not available via SCM API
    }
    
    # Infrastructure type to folder mapping (for single-folder types)
    # Multi-folder types are handled separately
    INFRASTRUCTURE_FOLDER_MAP = {
        'remote_network': 'Remote Networks',
        'service_connection': 'Service Connections',
    }
    
    # Default snippet values that indicate system/predefined items
    # These should be filtered when include_defaults=False
    DEFAULT_SNIPPETS = {
        'default',           # General system defaults (crypto profiles, tags, addresses)
        'hip-default',       # HIP-specific defaults (HIP objects and profiles)
        'optional-default',  # Optional pre-built defaults
        # Named default snippets from Prisma Access
        'Web Security Global',
        'PA_predefined_embargo_rule',
        'best-practice',
        'decrypt-bypass',
        'Block-brute-force',
    }

    # Default item names by type - these are system-provided items that should be
    # filtered when include_defaults=False, regardless of which snippet they're in
    DEFAULT_ITEM_NAMES = {
        'address_object': {
            'Palo Alto Networks Sinkhole',
        },
        'application_filter': {
            'general-browsing',
            'All New apps',
            'DLP App Exclusion',
        },
        'service_object': {
            'service-http',
            'service-https',
        },
        'tag': {
            'Sanctioned',
            'Tolerated',
            'empty',
        },
        'external_dynamic_list': {
            'Palo Alto Networks - Authentication Portal Exclude List',
        },
        'profile_group': {
            'best-practice',
            'Explicit Proxy - Unknown Users',
        },
        'anti_spyware_profile': {
            'best-practice',
        },
        'vulnerability_profile': {
            'best-practice',
        },
        'wildfire_profile': {
            'best-practice',
        },
        'dns_security_profile': {
            'best-practice',
        },
        'url_access_profile': {
            'best-practice',
            'Explicit Proxy - Unknown Users',
        },
        'file_blocking_profile': {
            'best-practice',
        },
        'decryption_profile': {
            'best-practice',
            'web-security-default',
        },
    }
    
    def __init__(
        self,
        api_client: PrismaAccessAPIClient,
        config: Optional[WorkflowConfig] = None
    ):
        """
        Initialize pull orchestrator.
        
        Args:
            api_client: PrismaAccessAPIClient instance
            config: WorkflowConfig (uses defaults if not provided)
        """
        logger.detail("Initializing Pull Orchestrator")
        logger.debug(f"API Client: {type(api_client).__name__}")
        
        self.api_client = api_client
        self.config = config or WorkflowConfig()
        self.default_manager = DefaultManager()
        self.progress_callback = None  # For GUI progress updates
        
        logger.debug(f"Workflow config: include_defaults={self.config.include_defaults}, "
                     f"validate_items={self.config.validate_before_pull}")
        
        # Initialize folder filter (set in pull_all for each pull)
        # Only folders use filtering - snippets/infrastructure query all items
        self._folder_filter: Optional[Dict[str, List[str]]] = None
        
        # Cancellation flag
        self._cancelled = False
        
        # Validate configuration
        is_valid, errors = validate_configuration(self.config)
        if not is_valid:
            logger.warning(f"Configuration validation errors: {errors}")
        else:
            logger.debug("Configuration validation passed")
    
    def set_progress_callback(self, callback):
        """
        Set callback for progress updates.
        
        Args:
            callback: Function(message: str, percentage: int)
        """
        self.progress_callback = callback
    
    def cancel(self):
        """Request cancellation of the current pull operation."""
        logger.info("Pull cancellation requested")
        self._cancelled = True
    
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled
        
    def _emit_progress(self, message: str, percentage: int):
        """Emit progress update if callback is set."""
        if self.progress_callback:
            try:
                self.progress_callback(message, percentage)
            except Exception as e:
                logger.debug(f"Error emitting progress: {e}")
    
    def _calculate_progress(self, base_pct: int, current: int, total: int, range_pct: int) -> int:
        """
        Calculate progress percentage within a range.
        
        Args:
            base_pct: Starting percentage for this phase
            current: Current item number
            total: Total items in this phase
            range_pct: Percentage range for this phase
            
        Returns:
            Calculated percentage
        """
        if total == 0:
            return base_pct
        return base_pct + int((current / total) * range_pct)
    
    def _is_default_item(self, item_data: dict, item_type: str = None) -> bool:
        """
        Determine if an item is a system default based on its snippet field or name.

        The snippet field in the API response is the authoritative source for
        determining if an item is a system default vs user-created. Additionally,
        certain items are filtered by name (e.g., "best-practice" profiles).

        Default snippets include:
        - 'default': General system defaults (crypto profiles, tags, etc.)
        - 'hip-default': HIP-specific defaults (HIP objects/profiles)
        - 'optional-default': Optional pre-built defaults
        - Any snippet ending in '-default'
        - Named default snippets like 'Web Security Global', 'best-practice', etc.

        Args:
            item_data: Raw item data dictionary from API response
            item_type: Optional item type to check for default item names

        Returns:
            True if item is a system default, False if custom/user-created
        """
        snippet = item_data.get('snippet', '')
        item_name = item_data.get('name', '')

        # Check if item name is in the default names list for this type
        if item_type and item_type in self.DEFAULT_ITEM_NAMES:
            if item_name in self.DEFAULT_ITEM_NAMES[item_type]:
                return True

        # Check known default snippet values
        if snippet and snippet in self.DEFAULT_SNIPPETS:
            return True

        # Check for any snippet ending in -default (catch future patterns)
        if snippet and snippet.endswith('-default'):
            return True
        
        return False
    
    def _calculate_progress_ranges(
        self, 
        include_folders: bool,
        include_snippets: bool, 
        include_infrastructure: bool,
        num_folders: int,
        num_snippets: int
    ) -> dict:
        """
        Calculate dynamic progress ranges based on what's being pulled.
        
        This prevents progress bar from jumping when items are filtered out.
        Progress is allocated proportionally based on estimated work.
        
        Args:
            include_folders: Whether folders are included
            include_snippets: Whether snippets are included
            include_infrastructure: Whether infrastructure is included
            num_folders: Number of folders to pull
            num_snippets: Number of snippets to pull (after filtering)
            
        Returns:
            Dictionary with start/end percentages for each phase
        """
        # Reserve 10% for initialization/finalization
        start_pct = 10
        end_pct = 90
        available_range = end_pct - start_pct
        
        # Calculate weights based on estimated API calls
        folder_weight = len(self.FOLDER_TYPES) * num_folders if include_folders else 0
        snippet_weight = len(self.SNIPPET_TYPES) * num_snippets if include_snippets else 0
        infra_weight = len(self.INFRASTRUCTURE_TYPES) if include_infrastructure else 0
        
        total_weight = folder_weight + snippet_weight + infra_weight
        
        if total_weight == 0:
            # No work to do - just return even split
            return {
                'folders_start': start_pct,
                'folders_end': start_pct,
                'snippets_start': start_pct,
                'snippets_end': start_pct,
                'infrastructure_start': start_pct,
                'infrastructure_end': end_pct,
            }
        
        # Calculate proportional ranges
        folder_range = int((folder_weight / total_weight) * available_range) if folder_weight > 0 else 0
        snippet_range = int((snippet_weight / total_weight) * available_range) if snippet_weight > 0 else 0
        infra_range = available_range - folder_range - snippet_range  # Remainder goes to infrastructure
        
        # Calculate start/end points
        folders_start = start_pct
        folders_end = folders_start + folder_range
        
        snippets_start = folders_end
        snippets_end = snippets_start + snippet_range
        
        infrastructure_start = snippets_end
        infrastructure_end = end_pct
        
        logger.debug(f"Progress ranges: folders={folders_start}-{folders_end}%, "
                    f"snippets={snippets_start}-{snippets_end}%, "
                    f"infra={infrastructure_start}-{infrastructure_end}%")
        
        return {
            'folders_start': folders_start,
            'folders_end': folders_end,
            'folders_range': folder_range,
            'snippets_start': snippets_start,
            'snippets_end': snippets_end,
            'snippets_range': snippet_range,
            'infrastructure_start': infrastructure_start,
            'infrastructure_end': infrastructure_end,
            'infrastructure_range': infra_range,
        }
        
        logger.detail("Pull Orchestrator initialized")
    
    def pull_all(
        self,
        include_folders: bool = True,
        include_snippets: bool = True,
        include_infrastructure: bool = True,
        use_bottom_folders: bool = True,
        folder_list: Optional[List[str]] = None,
        snippet_list: Optional[List[str]] = None,
        folder_filter: Optional[Dict[str, List[str]]] = None,
        snippet_filter: Optional[Dict[str, List[str]]] = None,
        infrastructure_filter: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """
        Pull all configurations.
        
        Args:
            include_folders: Whether to pull folder-based items
            include_snippets: Whether to pull snippet-based items
            include_infrastructure: Whether to pull infrastructure items
            use_bottom_folders: Use optimized bottom folder approach (Prisma Access only)
            folder_list: Optional list of specific folder names to query (None = use bottom folders)
            snippet_list: Optional list of specific snippet names to pull (None = all)
            folder_filter: Optional dict of {folder_name: [component_types]} to control storage
                          Empty list means all components. Missing folder means exclude.
            snippet_filter: Optional dict of {snippet_name: [component_types]} to control what's pulled/stored
                          Empty list means all components. Missing snippet means exclude.
            infrastructure_filter: Optional dict with keys like:
                          - remote_networks: bool
                          - service_connections: bool  
                          - mobile_users: bool
                          - rn_ipsec_tunnels, sc_ipsec_tunnels: bool (granular)
                          - etc. Controls which infra types/folders to pull from
            
        Returns:
            WorkflowResult with complete pull results
        """
        # Store filters for use during configuration building
        self._folder_filter = folder_filter
        self._snippet_filter = snippet_filter
        self._infrastructure_filter = infrastructure_filter
        logger.normal("=" * 80)
        logger.normal("STARTING PULL OPERATION")
        logger.normal("=" * 80)
        logger.info(f"Pull config: folders={include_folders}, snippets={include_snippets}, "
                   f"infrastructure={include_infrastructure}")
        logger.debug(f"Use bottom folders: {use_bottom_folders}")
        logger.debug(f"Include defaults: {self.config.include_defaults}")
        
        self._emit_progress("Starting pull operation...", 5)
        
        # Initialize result and state
        result = WorkflowResult(operation='pull')
        state = WorkflowState(
            workflow_id=f'pull_{int(datetime.now().timestamp())}',
            operation='pull'
        )
        state.start()
        logger.debug(f"Workflow ID: {state.workflow_id}")
        
        try:
            # Determine folders to query
            if include_folders:
                self._emit_progress("Identifying folders...", 10)
                if folder_list:
                    # Use specific folders provided by user
                    folders = folder_list
                    display_names = [self.get_display_name(f) for f in folders]
                    logger.info(f"Using user-selected folders: {display_names}")
                elif use_bottom_folders:
                    # Prisma Access optimization: query bottom folders only
                    folders = self.PRISMA_ACCESS_BOTTOM_FOLDERS
                    display_names = [self.get_display_name(f) for f in folders]
                    logger.info(f"Using bottom-level folders (Prisma Access optimized): {display_names}")
                    logger.debug(f"Bottom folders capture inherited configs from parents")
                else:
                    # Get all folders from API
                    logger.info("Fetching all folders from API...")
                    state.start_operation('fetch_folders')
                    folders = self._get_folders()
                    display_names = [self.get_display_name(f) for f in folders]
                    logger.info(f"Found {len(folders)} folders")
                    logger.detail(f"Folders: {display_names}")
                    state.complete_operation()
                
                state.store_result('folders', folders)
            else:
                logger.info("Skipping folder-based items")
                folders = []
            
            # Get snippets
            snippets = []
            if include_snippets:
                self._emit_progress("Fetching snippets...", 12)
                logger.info("Fetching snippets from API...")
                state.start_operation('fetch_snippets')
                snippets = self._get_snippets(snippet_list)
                logger.info(f"Found {len(snippets)} snippets")
                logger.detail(f"Snippets: {snippets}")
                state.store_result('snippets', snippets)
                state.complete_operation()
            else:
                logger.info("Skipping snippet-based items")
            
            # Calculate total work for progress tracking
            # Note: This is an estimate - actual work may be less if defaults are filtered
            total_work = 0
            if include_folders:
                total_work += len(folders) * len(self.FOLDER_TYPES)
            if include_snippets:
                total_work += len(snippets) * len(self.SNIPPET_TYPES)
            if include_infrastructure:
                total_work += len(self.INFRASTRUCTURE_TYPES)
            
            self.total_work = total_work
            self.completed_work = 0
            logger.debug(f"Total API calls estimated: {total_work}")
            
            # Calculate dynamic progress ranges based on what's actually being pulled
            # This prevents progress bar from jumping when snippets/folders are filtered
            progress_ranges = self._calculate_progress_ranges(
                include_folders, include_snippets, include_infrastructure,
                len(folders), len(snippets)
            )
            
            # Pull folder-based items
            if include_folders and folders:
                self._emit_progress(f"Pulling folder configs from {len(folders)} folders...", progress_ranges['folders_start'])
                logger.normal(f"Pulling folder-based items from {len(folders)} folders...")
                folder_items = self._pull_folder_items(folders, state, result, progress_ranges)
                state.store_result('folder_items', folder_items)
                logger.info(f"Pulled {len(folder_items)} folder-based items")

            # Check for cancellation after folders
            if self._cancelled:
                logger.info("Pull cancelled by user after folder phase")
                self._emit_progress("Pull cancelled", 0)
                result.cancelled = True
                return result

            # Pull snippet-based items
            if include_snippets and snippets:
                self._emit_progress(f"Pulling snippet configs from {len(snippets)} snippets...", progress_ranges['snippets_start'])
                logger.normal(f"Pulling snippet-based items from {len(snippets)} snippets...")
                snippet_items = self._pull_snippet_items(snippets, state, result, progress_ranges)
                state.store_result('snippet_items', snippet_items)
                logger.info(f"Pulled {len(snippet_items)} snippet-based items")

            # Check for cancellation after snippets
            if self._cancelled:
                logger.info("Pull cancelled by user after snippet phase")
                self._emit_progress("Pull cancelled", 0)
                result.cancelled = True
                return result

            # Pull infrastructure items
            if include_infrastructure:
                self._emit_progress("Pulling infrastructure configs...", progress_ranges['infrastructure_start'])
                logger.normal("Pulling infrastructure items...")
                infra_items = self._pull_infrastructure_items(state, result, progress_ranges)
                state.store_result('infrastructure_items', infra_items)
                logger.info(f"Pulled {len(infra_items)} infrastructure items")

            # Check for cancellation after infrastructure
            if self._cancelled:
                logger.info("Pull cancelled by user after infrastructure phase")
                self._emit_progress("Pull cancelled", 0)
                result.cancelled = True
                return result

            # Build Configuration object from pulled items
            self._emit_progress("Building configuration object...", 90)
            logger.info("Building Configuration object...")
            from config.models.containers import Configuration, FolderConfig, SnippetConfig, InfrastructureConfig
            
            configuration = Configuration(
                source_tsg=self.api_client.tsg_id,
                load_type='From Pull',
                saved_credentials_ref=None  # Will be set by PullWorker with connection_name
            )
            # source_tenant will be set by PullWorker after pull_all returns
            
            # Set timestamps at pull time
            pull_timestamp = datetime.now().isoformat()
            configuration.created_at = pull_timestamp
            configuration.modified_at = pull_timestamp
            configuration.config_version = 1  # First version
            
            # Add folder items
            folder_items_dict = state.get_result('folder_items') or {}
            
            # Build allowed folders set and per-folder component filters from folder_filter
            # The folder_filter is a dict of {folder_name: [component_types]}
            # We need to apply BOTH folder AND component filtering as a PAIR
            allowed_folders = None
            folder_component_map = {}  # {folder_name: set of allowed component types or None for all}
            
            if self._folder_filter is not None:
                allowed_folders = set(self._folder_filter.keys())
                for folder_name, components in self._folder_filter.items():
                    if components:
                        folder_component_map[folder_name] = set(components)
                    else:
                        # Empty list means all components for this folder
                        folder_component_map[folder_name] = None
                logger.detail(f"Folder filter active: allowed folders = {allowed_folders}")
                logger.detail(f"Per-folder component filters: {folder_component_map}")
            
            # Only initialize folders that are in the allowed list (or all if no filter)
            # Don't auto-create core folders if they weren't selected
            if allowed_folders:
                for folder_name in allowed_folders:
                    if folder_name not in configuration.folders:
                        configuration.folders[folder_name] = FolderConfig(name=folder_name)
            
            items_stored = 0
            items_filtered_by_type = 0
            items_filtered_by_folder = 0
            for folder_name, item_types_dict in folder_items_dict.items():
                for item_type, items_list in item_types_dict.items():
                    for item in items_list:
                        # Use the item's actual folder from the API response
                        # Items can be in parent folders (All, Prisma Access, Mobile Users Container)
                        # when querying child folders (Mobile Users, Remote Networks, etc.)
                        item_folder = getattr(item, 'folder', folder_name)
                        
                        # Filter by allowed folders - only store items from selected folders
                        # This prevents parent folder configs from appearing when only child folders are selected
                        if allowed_folders is not None and item_folder not in allowed_folders:
                            items_filtered_by_folder += 1
                            continue
                        
                        # Apply per-folder component type filter
                        # Check if this item_type is allowed for this specific folder
                        if item_folder in folder_component_map:
                            allowed_types = folder_component_map[item_folder]
                            if allowed_types is not None and item_type not in allowed_types:
                                items_filtered_by_type += 1
                                continue
                        
                        # Create folder config if it doesn't exist
                        if item_folder not in configuration.folders:
                            configuration.folders[item_folder] = FolderConfig(name=item_folder)
                        
                        # Check if we already have this item (by id/name) to avoid duplicates
                        existing_items = configuration.folders[item_folder].get_items_by_type(item_type)
                        item_id = getattr(item, 'id', None) or getattr(item, 'name', None)
                        
                        # Skip if we already have this item
                        if item_id and any(
                            (getattr(existing, 'id', None) == item_id or 
                             getattr(existing, 'name', None) == item_id)
                            for existing in existing_items
                        ):
                            continue
                        
                        configuration.folders[item_folder].add_item(item)
                        items_stored += 1
            
            logger.normal(f"Folder items: {items_stored} stored, {items_filtered_by_type} filtered by type, {items_filtered_by_folder} filtered by folder")
            
            # Add snippet items
            snippet_items_dict = state.get_result('snippet_items') or {}
            
            # Default/system snippet names to skip when filtering defaults
            DEFAULT_SNIPPET_NAMES = {
                'predefined', 'default', 'hip-default', 'optional-default',
                'predefined-snippet', 'dlp-predefined-snippet'
            }
            
            snippet_items_stored = 0
            snippet_items_filtered = 0
            for snippet_name, item_types_dict in snippet_items_dict.items():
                for item_type, items_list in item_types_dict.items():
                    for item in items_list:
                        # Use the item's actual snippet from the API response
                        # Items can be in parent snippets when querying child snippets
                        item_snippet = getattr(item, 'snippet', snippet_name)
                        
                        # Skip items from default/system snippets when filtering defaults
                        if not self.config.include_defaults:
                            if item_snippet in DEFAULT_SNIPPET_NAMES or item_snippet.endswith('-default'):
                                logger.debug(f"Skipping item from default snippet: {item_snippet}")
                                snippet_items_filtered += 1
                                continue
                        
                        # Create snippet config if it doesn't exist
                        if item_snippet not in configuration.snippets:
                            configuration.snippets[item_snippet] = SnippetConfig(name=item_snippet)
                        
                        # Check if we already have this item (by id/name) to avoid duplicates
                        existing_items = configuration.snippets[item_snippet].get_items_by_type(item_type)
                        item_id = getattr(item, 'id', None) or getattr(item, 'name', None)
                        
                        # Skip if we already have this item
                        if item_id and any(
                            (getattr(existing, 'id', None) == item_id or 
                             getattr(existing, 'name', None) == item_id)
                            for existing in existing_items
                        ):
                            continue
                        
                        configuration.snippets[item_snippet].add_item(item)
                        snippet_items_stored += 1
            
            logger.normal(f"Snippet items: {snippet_items_stored} stored, {snippet_items_filtered} filtered by defaults")
            
            # Add infrastructure items
            infra_items_dict = state.get_result('infrastructure_items') or {}
            # Flatten dictionary of lists into single list
            # Note: bandwidth_allocation items are raw dicts, not ConfigItems
            for item_type, items_list in infra_items_dict.items():
                if item_type == 'bandwidth_allocation':
                    # Store bandwidth allocations as raw data (they don't have ConfigItem models)
                    configuration._bandwidth_allocations = items_list
                else:
                    for item in items_list:
                        configuration.infrastructure.add_item(item)
            
            # Attach configuration to result
            result.configuration = configuration
            logger.normal(f"Configuration object created with {len(configuration.get_all_items())} total items")
            
            # Mark complete
            state.complete()
            result.mark_complete()
            result.success = True
            
            logger.normal("=" * 80)
            logger.normal(f"PULL COMPLETE: {result.items_processed} items processed")
            logger.normal("=" * 80)
            logger.info(f"Pull summary: {result.items_processed} processed, "
                       f"{result.items_created} created, {result.items_skipped} skipped")
            logger.debug(f"Duration: {(datetime.now() - state.start_time).total_seconds():.2f}s")
            
        except Exception as e:
            state.fail(str(e))
            result.success = False
            logger.error(f"Pull failed: {e}", exc_info=True)
            result.add_error(
                item_type='workflow',
                item_name='pull',
                operation='pull',
                error_type=type(e).__name__,
                message=str(e)
            )
        
        return result
    
    def _get_folders(self, folder_list: Optional[List[str]] = None) -> List[str]:
        """
        Get list of folders to process.
        
        Args:
            folder_list: Optional specific folders (None = all)
            
        Returns:
            List of folder names
        """
        try:
            # Get all folders from API (uses Strata API, not SASE API)
            from ..api_endpoints import APIEndpoints
            response = self.api_client._make_request(
                "GET",
                APIEndpoints.SECURITY_POLICY_FOLDERS,
                item_type='folder'
            )
            
            all_folders = []
            if isinstance(response, dict) and 'data' in response:
                all_folders = [f['name'] for f in response['data'] if 'name' in f]
            
            # Filter by provided list
            if folder_list:
                all_folders = [f for f in all_folders if f in folder_list]
            
            # Apply configuration filters
            all_folders = self.config.get_allowed_folders(all_folders)
            
            return all_folders
            
        except Exception as e:
            logger.error(f"Error fetching folders: {e}")
            return []
    
    def _get_snippets(self, snippet_list: Optional[List[str]] = None) -> List[str]:
        """
        Get list of snippets to process.
        
        Args:
            snippet_list: Optional specific snippets (None = all)
            
        Returns:
            List of snippet names (filtered for custom snippets if include_defaults=False)
        """
        try:
            # Get all snippets from API (uses Strata API, not SASE API)
            from ..api_endpoints import APIEndpoints
            response = self.api_client._make_request(
                "GET",
                APIEndpoints.SECURITY_POLICY_SNIPPETS,
                item_type='snippet'
            )
            
            # Extract snippet objects with name and type
            all_snippet_objs = []
            if isinstance(response, dict) and 'data' in response:
                all_snippet_objs = response['data']
            
            logger.debug(f"Fetched {len(all_snippet_objs)} snippet objects from API")
            
            # Filter by type if include_defaults=False
            # Snippets with type='predefined' or 'readonly' are system defaults
            # type='custom' or unknown/missing type could be user-created
            # Known predefined types to exclude
            PREDEFINED_SNIPPET_TYPES = {'predefined', 'readonly'}
            
            if not self.config.include_defaults:
                logger.info(f"Filtering snippets by type (include_defaults=False)")
                logger.info(f"  Total snippets before filtering: {len(all_snippet_objs)}")
                
                custom_snippets = []
                for snippet_obj in all_snippet_objs:
                    snippet_name = snippet_obj.get('name', 'unnamed')
                    snippet_type = snippet_obj.get('type', '')
                    
                    # Skip known predefined types
                    if snippet_type in PREDEFINED_SNIPPET_TYPES:
                        logger.info(f"  ✗ SKIPPING predefined snippet: '{snippet_name}' (type={snippet_type})")
                        continue
                    
                    # Keep custom type explicitly
                    if snippet_type == 'custom':
                        logger.info(f"  ✓ KEEPING custom snippet: '{snippet_name}' (type={snippet_type})")
                        custom_snippets.append(snippet_obj)
                        continue
                    
                    # For unknown/missing type, check if it looks like a system snippet
                    # System snippets often have specific naming patterns or are in our known defaults list
                    is_likely_system = any([
                        snippet_name.startswith('predefined-'),
                        snippet_name.endswith('-default'),
                        snippet_name.endswith('-Default'),
                        'Default' in snippet_name and 'Snippet' in snippet_name,
                        snippet_name in self.DEFAULT_SNIPPETS,  # Check named default snippets
                    ])

                    if is_likely_system:
                        logger.info(f"  ✗ SKIPPING likely system snippet: '{snippet_name}' (type={snippet_type or 'none'})")
                    else:
                        logger.info(f"  ✓ KEEPING snippet (unknown type, not system pattern): '{snippet_name}' (type={snippet_type or 'none'})")
                        custom_snippets.append(snippet_obj)
                
                logger.info(f"  Total snippets after filtering: {len(custom_snippets)}")
                logger.info(f"Filtered snippets: {len(all_snippet_objs)} → {len(custom_snippets)} "
                           f"(removed {len(all_snippet_objs) - len(custom_snippets)} predefined)")
                all_snippet_objs = custom_snippets
            else:
                logger.info(f"Including all snippets (include_defaults=True)")
            
            # Extract just the names
            all_snippets = [s.get('name') for s in all_snippet_objs if 'name' in s]
            
            # If user explicitly selected specific snippets, use those (from the full list, not filtered)
            # This allows user to pull system snippets if they explicitly select them
            if snippet_list:
                # Get all snippet names before filtering
                all_snippet_names = [s.get('name') for s in (response.get('data', []) if isinstance(response, dict) else []) if 'name' in s]
                # Only include snippets that exist and were requested
                all_snippets = [s for s in snippet_list if s in all_snippet_names]
                logger.info(f"User selected specific snippets: {all_snippets}")
            
            # Apply configuration filters
            all_snippets = self.config.get_allowed_snippets(all_snippets)
            
            return all_snippets
            
        except Exception as e:
            logger.error(f"Error fetching snippets: {e}")
            return []
    
    def _pull_folder_items(
        self,
        folders: List[str],
        state: WorkflowState,
        result: WorkflowResult,
        progress_ranges: dict
    ) -> Dict[str, Dict[str, List[ConfigItem]]]:
        """
        Pull all folder-based items from specified folders.
        
        For Prisma Access with bottom folders, this is optimized:
        - Only 3 folders to query (Mobile Users, Remote Networks, Explicit Proxy)
        - Each folder query includes inherited configs from parents
        - Result: 3 folders × M types instead of N folders × M types
        
        Args:
            folders: List of folder names (bottom folders for Prisma Access)
            state: WorkflowState for tracking
            result: WorkflowResult for error tracking
            progress_ranges: Dict with start/end/range percentages
            
        Returns:
            Dict mapping folder -> item_type -> List[ConfigItem]
        """
        state.start_operation('pull_folder_items')
        logger.info(f"Pulling folder-based items from {len(folders)} folders...")
        display_names = [self.get_display_name(f) for f in folders]
        logger.info(f"Folders: {display_names}")
        logger.debug(f"Item types to pull: {len(self.FOLDER_TYPES)} types")
        
        # Initialize structure: folder -> type -> items
        folder_items: Dict[str, Dict[str, List[ConfigItem]]] = {
            folder: {} for folder in folders
        }
        
        total_items_fetched = 0
        
        # Process each folder
        for folder_idx, folder in enumerate(folders, 1):
            # Check for cancellation
            if self._cancelled:
                logger.info("Pull cancelled by user")
                self._emit_progress("Pull cancelled", 0)
                break
            
            # Calculate progress for this folder using dynamic range
            folder_progress = self._calculate_progress(
                progress_ranges['folders_start'],
                folder_idx - 1,
                len(folders),
                progress_ranges['folders_range']
            )
            display_name = self.get_display_name(folder)
            self._emit_progress(f"[{folder_idx}/{len(folders)}] Pulling from folder: {display_name}...", folder_progress)

            logger.normal(f"[{folder_idx}/{len(folders)}] Processing folder: {display_name}")
            logger.debug(f"Folder item types: {self.FOLDER_TYPES}")
            
            folder_item_count = 0
            
            # Determine which item types to query for this folder
            # If folder_filter specifies components, only query those
            if self._folder_filter and folder in self._folder_filter:
                allowed_types = self._folder_filter[folder]
                if allowed_types:
                    # Filter to only selected component types
                    types_to_query = [t for t in self.FOLDER_TYPES if t in allowed_types]
                    logger.info(f"  Filtering to selected components: {types_to_query}")
                else:
                    # Empty list means all components
                    types_to_query = self.FOLDER_TYPES
            else:
                types_to_query = self.FOLDER_TYPES
            
            # Process each item type for this folder
            for type_idx, item_type in enumerate(types_to_query, 1):
                # Check for cancellation
                if self._cancelled:
                    break
                
                # Update progress for each type
                type_progress = self._calculate_progress(
                    folder_progress,
                    type_idx - 1,
                    len(types_to_query),
                    int(progress_ranges['folders_range'] / len(folders))  # Use dynamic range
                )
                type_display = item_type.replace('_', ' ').title()
                self._emit_progress(
                    f"[{folder_idx}/{len(folders)}] {folder}: {type_display} ({type_idx}/{len(types_to_query)})...",
                    type_progress
                )
                
                logger.debug(f"  [{type_idx}/{len(types_to_query)}] Processing {item_type}")
                
                try:
                    # Check if this type is allowed in this folder (uses centralized restrictions)
                    if not is_folder_allowed(item_type, folder):
                        logger.debug(f"  Skipping {item_type} in folder '{folder}' (API restriction)")
                        continue
                    
                    # Get model class for this type
                    logger.debug(f"  Getting model class for {item_type}")
                    model_class = ConfigItemFactory.get_model_class(item_type)
                    if not model_class or not hasattr(model_class, 'api_endpoint'):
                        logger.debug(f"  Skipping {item_type} (no model/endpoint)")
                        continue
                    
                    logger.debug(f"  Model class: {model_class.__name__}")
                    logger.debug(f"  API endpoint: {model_class.api_endpoint}")
                    
                    # Fetch items for this type in this folder
                    from urllib.parse import quote
                    encoded_folder = quote(folder, safe='')
                    url = f"{model_class.api_endpoint}?folder={encoded_folder}"
                    logger.detail(f"  Fetching from: {url}")
                    
                    response = self.api_client._make_request("GET", url, item_type=item_type)
                    
                    # Extract items
                    raw_items = []
                    if isinstance(response, dict) and 'data' in response:
                        raw_items = response['data']
                        logger.detail(f"  Response contains 'data' with {len(raw_items)} items")
                    elif isinstance(response, list):
                        raw_items = response
                        logger.detail(f"  Response is list with {len(raw_items)} items")
                    else:
                        logger.detail(f"  Response format unexpected: {type(response)}")
                    
                    if raw_items:
                        logger.info(f"  {item_type}: {len(raw_items)} items retrieved")
                        logger.detail(f"  First item keys: {list(raw_items[0].keys()) if raw_items else 'none'}")
                    
                    # Instantiate items
                    items = []
                    skipped_count = 0
                    default_count = 0
                    
                    for item_idx, raw_item in enumerate(raw_items):
                        item_name = raw_item.get('name', f'item_{item_idx}')
                        logger.debug(f"    [{item_idx+1}/{len(raw_items)}] Creating {item_type} '{item_name}'")
                        
                        try:
                            # Check defaults BEFORE creating ConfigItem (more efficient)
                            # Use snippet field from raw API response
                            if not self.config.include_defaults and self._is_default_item(raw_item, item_type):
                                snippet_val = raw_item.get('snippet', '')
                                logger.debug(f"    Skipping '{item_name}' (default item, snippet='{snippet_val}')")
                                result.items_skipped += 1
                                default_count += 1
                                continue
                            
                            item = ConfigItemFactory.create_from_dict(item_type, raw_item)
                            logger.debug(f"    Created {item_type} '{item.name}'")
                            
                            # Apply additional filters
                            if not self.config.should_process_item(item):
                                logger.debug(f"    Skipping '{item.name}' (filtered by config)")
                                result.items_skipped += 1
                                skipped_count += 1
                                continue
                            
                            items.append(item)
                            result.items_processed += 1
                            logger.debug(f"    Added {item_type} '{item.name}' to results")
                            
                        except Exception as e:
                            handle_workflow_error(e, None, f'parse_{item_type}', result, self.config)
                    
                    # Store items for this type
                    if items:
                        if item_type not in folder_items[folder]:
                            folder_items[folder][item_type] = []
                        folder_items[folder][item_type].extend(items)
                
                except Exception as e:
                    handle_workflow_error(e, None, f'fetch_{item_type}_from_{folder}', result, self.config)
        
        state.complete_operation()
        return folder_items
    
    def _pull_snippet_items(
        self,
        snippets: List[str],
        state: WorkflowState,
        result: WorkflowResult,
        progress_ranges: dict
    ) -> Dict[str, Dict[str, List[ConfigItem]]]:
        """
        Pull all snippet-based items by looping through each snippet.
        
        Note: Unlike folders, we must query each snippet individually.
        Snippet items don't reliably show up in folder queries.
        
        Args:
            snippets: List of snippet names
            state: WorkflowState for tracking
            result: WorkflowResult for error tracking
            progress_ranges: Dict with start/end/range percentages
            
        Returns:
            Dict mapping snippet -> item_type -> List[ConfigItem]
        """
        state.start_operation('pull_snippet_items')
        logger.info(f"Pulling snippet-based items from {len(snippets)} snippets...")
        logger.debug(f"Snippet types: {self.SNIPPET_TYPES}")
        
        # Build allowed component types for snippets (similar to folder filtering)
        snippet_allowed_types = {}
        if self._snippet_filter is not None:
            for snippet_name, components in self._snippet_filter.items():
                if components:  # Non-empty list = specific components
                    snippet_allowed_types[snippet_name] = set(components)
                else:  # Empty list = all components
                    snippet_allowed_types[snippet_name] = None
            logger.detail(f"Snippet filter active: {len(snippet_allowed_types)} snippets with component filters")
        
        # Initialize structure: snippet -> type -> items
        snippet_items: Dict[str, Dict[str, List[ConfigItem]]] = {
            snippet: {} for snippet in snippets
        }
        
        total_items_fetched = 0
        
        # Process each snippet
        for snippet_idx, snippet in enumerate(snippets, 1):
            # Calculate progress using dynamic range
            snippet_progress = self._calculate_progress(
                progress_ranges['snippets_start'],
                snippet_idx - 1,
                len(snippets),
                progress_ranges['snippets_range']
            )
            self._emit_progress(f"[{snippet_idx}/{len(snippets)}] Pulling from snippet: {snippet}...", snippet_progress)
            
            logger.normal(f"[{snippet_idx}/{len(snippets)}] Processing snippet: {snippet}")
            snippet_item_count = 0
            
            # Determine which item types to pull for this snippet
            allowed_types_for_snippet = None
            if self._snippet_filter is not None:
                allowed_types_for_snippet = snippet_allowed_types.get(snippet)
                if allowed_types_for_snippet is not None:
                    logger.info(f"  Filtering to selected components: {sorted(allowed_types_for_snippet)}")
            
            # Process each item type for this snippet
            for type_idx, item_type in enumerate(self.SNIPPET_TYPES, 1):
                # Skip item types not in the allowed list (if filtering is active)
                if allowed_types_for_snippet is not None and item_type not in allowed_types_for_snippet:
                    logger.debug(f"  Skipping {item_type} (not in selected components)")
                    continue
                # Update progress for each type within snippet
                type_progress = self._calculate_progress(
                    snippet_progress,
                    type_idx - 1,
                    len(self.SNIPPET_TYPES),
                    int(progress_ranges['snippets_range'] / len(snippets)) if len(snippets) > 0 else 0
                )
                type_display = item_type.replace('_', ' ').title()
                self._emit_progress(
                    f"[{snippet_idx}/{len(snippets)}] {snippet}: {type_display} ({type_idx}/{len(self.SNIPPET_TYPES)})...",
                    type_progress
                )
                
                logger.debug(f"  Processing {item_type} for snippet '{snippet}'")
                try:
                    # Get model class for this type
                    model_class = ConfigItemFactory.get_model_class(item_type)
                    if not model_class or not hasattr(model_class, 'api_endpoint'):
                        logger.debug(f"  Skipping {item_type} (no model/endpoint)")
                        continue
                    
                    # Fetch items for this type in this snippet
                    from urllib.parse import quote
                    encoded_snippet = quote(snippet, safe='')
                    url = f"{model_class.api_endpoint}?snippet={encoded_snippet}"
                    response = self.api_client._make_request("GET", url, item_type=item_type)
                    
                    # Extract items
                    raw_items = []
                    if isinstance(response, dict) and 'data' in response:
                        raw_items = response['data']
                    elif isinstance(response, list):
                        raw_items = response
                    
                    if raw_items:
                        logger.info(f"  {item_type}: {len(raw_items)} items")
                    
                    # Instantiate items
                    items = []
                    default_count = 0
                    for raw_item in raw_items:
                        item_name = raw_item.get('name', 'unknown')
                        try:
                            # Check defaults BEFORE creating ConfigItem (more efficient)
                            # Use snippet field from raw API response
                            if not self.config.include_defaults and self._is_default_item(raw_item, item_type):
                                snippet_val = raw_item.get('snippet', '')
                                logger.debug(f"    Skipping '{item_name}' (default item, snippet='{snippet_val}')")
                                result.items_skipped += 1
                                default_count += 1
                                continue
                            
                            item = ConfigItemFactory.create_from_dict(item_type, raw_item)
                            
                            # Apply additional filters
                            if not self.config.should_process_item(item):
                                result.items_skipped += 1
                                continue
                            
                            items.append(item)
                            result.items_processed += 1
                            
                        except Exception as e:
                            handle_workflow_error(e, None, f'parse_{item_type}', result, self.config)
                    
                    if default_count > 0:
                        logger.debug(f"  Filtered {default_count} default {item_type} items from snippet '{snippet}'")
                    
                    # Store items for this type
                    if items:
                        if item_type not in snippet_items[snippet]:
                            snippet_items[snippet][item_type] = []
                        snippet_items[snippet][item_type].extend(items)
                
                except Exception as e:
                    handle_workflow_error(e, None, f'fetch_{item_type}_from_{snippet}', result, self.config)
        
        state.complete_operation()
        return snippet_items
    
    def _pull_infrastructure_items(
        self,
        state: WorkflowState,
        result: WorkflowResult,
        progress_ranges: dict
    ) -> Dict[str, List[ConfigItem]]:
        """
        Pull infrastructure items with hierarchical progress reporting.
        
        Hierarchy matches the viewer/selection tree:
        - Remote Networks (1 section with 5 sub-items)
          - Remote Networks (items)
          - IPSec Tunnels
            - IKE Gateways
              - IKE Crypto Profiles
            - IPSec Crypto Profiles
        - Service Connections (1 section with 5 sub-items)
          - Service Connections (items)
          - IPSec Tunnels
            - IKE Gateways
              - IKE Crypto Profiles
            - IPSec Crypto Profiles
        - Mobile Users (1 section with 1 sub-item)
          - Agent Profiles
        
        Args:
            state: WorkflowState for tracking
            result: WorkflowResult for error tracking
            progress_ranges: Dict with start/end/range percentages
            
        Returns:
            Dict mapping item_type -> List[ConfigItem]
        """
        state.start_operation('pull_infrastructure_items')
        logger.info("Pulling infrastructure items...")
        
        # Build set of allowed folders based on infrastructure filter
        allowed_folders = set()
        if self._infrastructure_filter:
            if self._infrastructure_filter.get('remote_networks', False):
                allowed_folders.add('Remote Networks')
            if self._infrastructure_filter.get('service_connections', False):
                allowed_folders.add('Service Connections')
            if self._infrastructure_filter.get('mobile_users', False):
                allowed_folders.add('Mobile Users')
            logger.detail(f"Infrastructure filter active: allowed folders = {allowed_folders}")
        else:
            # No filter - allow all
            allowed_folders = {'Remote Networks', 'Service Connections', 'Mobile Users'}
        
        infra_items: Dict[str, List[ConfigItem]] = {}
        
        # Calculate total sections for progress (only count enabled sections)
        # Each main section (RN, SC, MU, Regions) counts as 1
        total_sections = 0
        if 'Remote Networks' in allowed_folders:
            total_sections += 1
        if 'Service Connections' in allowed_folders:
            total_sections += 1
        if 'Mobile Users' in allowed_folders:
            total_sections += 1
        
        # Check if regions/bandwidth is enabled
        include_regions = self._infrastructure_filter.get('regions', False) if self._infrastructure_filter else False
        include_bandwidth = self._infrastructure_filter.get('bandwidth', False) if self._infrastructure_filter else False
        if include_regions or include_bandwidth:
            total_sections += 1
        
        if total_sections == 0:
            logger.info("No infrastructure sections selected")
            state.complete_operation()
            return infra_items
        
        current_section = 0
        
        # IPSec-related types for RN and SC hierarchy
        # Order: parent items, then IPSec tunnels, then IKE gateways, then crypto profiles
        IPSEC_HIERARCHY = [
            'ipsec_tunnel',
            'ike_gateway',
            'ike_crypto_profile',
            'ipsec_crypto_profile',
        ]

        # QoS types available in RN and SC folders
        QOS_TYPES = ['qos_profile']

        # ========== Remote Networks Section ==========
        if 'Remote Networks' in allowed_folders:
            current_section += 1
            section_base_pct = self._calculate_progress(
                progress_ranges['infrastructure_start'],
                current_section - 1,
                total_sections,
                progress_ranges['infrastructure_range']
            )
            section_range = progress_ranges['infrastructure_range'] // total_sections

            # 6 sub-items in RN: remote_network, ipsec_tunnel, ike_gateway, ike_crypto_profile, ipsec_crypto_profile, qos_profile
            rn_sub_items = ['remote_network'] + IPSEC_HIERARCHY + QOS_TYPES
            
            for sub_idx, item_type in enumerate(rn_sub_items, 1):
                sub_progress = self._calculate_progress(section_base_pct, sub_idx - 1, len(rn_sub_items), section_range)
                type_display = item_type.replace('_', ' ').title()
                self._emit_progress(
                    f"[{current_section}/{total_sections}] Remote Networks: {type_display} ({sub_idx}/{len(rn_sub_items)})...",
                    sub_progress
                )
                
                try:
                    if item_type == 'remote_network':
                        # Pull remote_network items globally (they're in Remote Networks folder)
                        items = self._pull_infra_global(item_type, result)
                        if items:
                            infra_items[item_type] = infra_items.get(item_type, []) + items
                        logger.info(f"  Fetched {len(items)} remote_network items")
                    else:
                        # Pull IPSec-related items from Remote Networks folder
                        items = self._pull_infra_from_folder(item_type, 'Remote Networks', result)
                        if items:
                            infra_items[item_type] = infra_items.get(item_type, []) + items
                        logger.info(f"  Fetched {len(items)} {item_type} items from 'Remote Networks'")
                except Exception as e:
                    logger.error(f"Error fetching {item_type} for Remote Networks: {e}")
                    handle_workflow_error(e, None, f'fetch_{item_type}_rn', result, self.config)
        
        # ========== Service Connections Section ==========
        if 'Service Connections' in allowed_folders:
            current_section += 1
            section_base_pct = self._calculate_progress(
                progress_ranges['infrastructure_start'],
                current_section - 1,
                total_sections,
                progress_ranges['infrastructure_range']
            )
            section_range = progress_ranges['infrastructure_range'] // total_sections
            
            # 6 sub-items in SC: service_connection, ipsec_tunnel, ike_gateway, ike_crypto_profile, ipsec_crypto_profile, qos_profile
            sc_sub_items = ['service_connection'] + IPSEC_HIERARCHY + QOS_TYPES
            
            for sub_idx, item_type in enumerate(sc_sub_items, 1):
                sub_progress = self._calculate_progress(section_base_pct, sub_idx - 1, len(sc_sub_items), section_range)
                type_display = item_type.replace('_', ' ').title()
                self._emit_progress(
                    f"[{current_section}/{total_sections}] Service Connections: {type_display} ({sub_idx}/{len(sc_sub_items)})...",
                    sub_progress
                )
                
                try:
                    if item_type == 'service_connection':
                        # Pull service_connection items globally (they're in Service Connections folder)
                        items = self._pull_infra_global(item_type, result)
                        if items:
                            infra_items[item_type] = infra_items.get(item_type, []) + items
                        logger.info(f"  Fetched {len(items)} service_connection items")
                    else:
                        # Pull IPSec-related items from Service Connections folder
                        items = self._pull_infra_from_folder(item_type, 'Service Connections', result)
                        if items:
                            infra_items[item_type] = infra_items.get(item_type, []) + items
                        logger.info(f"  Fetched {len(items)} {item_type} items from 'Service Connections'")
                except Exception as e:
                    logger.error(f"Error fetching {item_type} for Service Connections: {e}")
                    handle_workflow_error(e, None, f'fetch_{item_type}_sc', result, self.config)
        
        # ========== Mobile Users Section ==========
        if 'Mobile Users' in allowed_folders:
            current_section += 1
            section_base_pct = self._calculate_progress(
                progress_ranges['infrastructure_start'],
                current_section - 1,
                total_sections,
                progress_ranges['infrastructure_range']
            )
            section_range = progress_ranges['infrastructure_range'] // total_sections
            
            # 1 sub-item in MU: agent_profile
            mu_sub_items = ['agent_profile']
            
            for sub_idx, item_type in enumerate(mu_sub_items, 1):
                sub_progress = self._calculate_progress(section_base_pct, sub_idx - 1, len(mu_sub_items), section_range)
                type_display = item_type.replace('_', ' ').title()
                self._emit_progress(
                    f"[{current_section}/{total_sections}] Mobile Users: {type_display} ({sub_idx}/{len(mu_sub_items)})...",
                    sub_progress
                )
                
                try:
                    # Pull agent_profile from Mobile Users folder
                    items = self._pull_infra_from_folder(item_type, 'Mobile Users', result)
                    if items:
                        infra_items[item_type] = infra_items.get(item_type, []) + items
                    logger.info(f"  Fetched {len(items)} agent_profile items from 'Mobile Users'")
                except Exception as e:
                    logger.error(f"Error fetching agent_profile for Mobile Users: {e}")
                    handle_workflow_error(e, None, f'fetch_agent_profile_mu', result, self.config)
        
        # ========== Regions & Bandwidth Section ==========
        include_regions = self._infrastructure_filter.get('regions', False) if self._infrastructure_filter else False
        include_bandwidth = self._infrastructure_filter.get('bandwidth', False) if self._infrastructure_filter else False
        
        if include_regions or include_bandwidth:
            current_section += 1
            section_base_pct = self._calculate_progress(
                progress_ranges['infrastructure_start'],
                current_section - 1,
                total_sections,
                progress_ranges['infrastructure_range']
            )
            section_range = progress_ranges['infrastructure_range'] // total_sections
            
            # Count sub-items for this section
            regions_sub_items = []
            if include_bandwidth:
                regions_sub_items.append('bandwidth_allocation')
            
            for sub_idx, item_type in enumerate(regions_sub_items, 1):
                sub_progress = self._calculate_progress(section_base_pct, sub_idx - 1, len(regions_sub_items), section_range)
                type_display = 'Bandwidth Allocations' if item_type == 'bandwidth_allocation' else item_type.replace('_', ' ').title()
                self._emit_progress(
                    f"[{current_section}/{total_sections}] Regions: {type_display} ({sub_idx}/{len(regions_sub_items)})...",
                    sub_progress
                )
                
                try:
                    if item_type == 'bandwidth_allocation':
                        # Pull bandwidth allocations directly from API
                        allocations = self._pull_bandwidth_allocations(result)
                        if allocations:
                            infra_items['bandwidth_allocation'] = allocations
                        logger.info(f"  Fetched {len(allocations)} bandwidth allocation items")
                except Exception as e:
                    logger.error(f"Error fetching {item_type}: {e}")
                    handle_workflow_error(e, None, f'fetch_{item_type}', result, self.config)
        
        state.complete_operation()
        return infra_items
    
    def _pull_infra_from_folder(
        self,
        item_type: str,
        folder: str,
        result: WorkflowResult
    ) -> List[ConfigItem]:
        """
        Pull infrastructure items from a specific folder.
        
        Args:
            item_type: Type of infrastructure item
            folder: Folder name
            result: WorkflowResult for error tracking
            
        Returns:
            List of ConfigItem instances
        """
        items = []
        
        try:
            # Get model class
            model_class = ConfigItemFactory.get_model_class(item_type)
            if not model_class or not hasattr(model_class, 'api_endpoint'):
                logger.warning(f"No model class or endpoint for {item_type}")
                return items
            
            # Fetch items with folder parameter
            from urllib.parse import quote
            encoded_folder = quote(folder, safe='')
            url = f"{model_class.api_endpoint}?folder={encoded_folder}"
            
            response = self.api_client._make_request("GET", url, item_type=item_type)
            
            # Extract items
            raw_items = []
            if isinstance(response, dict) and 'data' in response:
                raw_items = response['data']
            elif isinstance(response, list):
                raw_items = response
            
            # Instantiate items
            default_count = 0
            for raw_item in raw_items:
                item_name = raw_item.get('name', 'unknown')
                try:
                    # Add folder if missing
                    if 'folder' not in raw_item:
                        raw_item['folder'] = folder
                        logger.debug(f"  Added folder='{folder}' to {item_type} '{item_name}'")
                    
                    # Check defaults BEFORE creating ConfigItem (more efficient)
                    # Use snippet field from raw API response
                    if not self.config.include_defaults and self._is_default_item(raw_item, item_type):
                        snippet_val = raw_item.get('snippet', '')
                        logger.debug(f"  Skipping '{item_name}' (default item, snippet='{snippet_val}')")
                        result.items_skipped += 1
                        default_count += 1
                        continue
                    
                    item = ConfigItemFactory.create_from_dict(item_type, raw_item)
                    items.append(item)
                    result.items_processed += 1
                except Exception as e:
                    handle_workflow_error(e, None, f'parse_{item_type}_from_{folder}', result, self.config)
            
            if default_count > 0:
                logger.info(f"  Filtered {default_count} default {item_type} items from '{folder}'")
        
        except Exception as e:
            logger.error(f"Error fetching {item_type} from '{folder}': {e}")
            handle_workflow_error(e, None, f'fetch_{item_type}_from_{folder}', result, self.config)
        
        return items
    
    def _pull_infra_global(
        self,
        item_type: str,
        result: WorkflowResult
    ) -> List[ConfigItem]:
        """
        Pull infrastructure items from global endpoint (no folder parameter).
        
        Args:
            item_type: Type of infrastructure item
            result: WorkflowResult for error tracking
            
        Returns:
            List of ConfigItem instances
        """
        items = []
        
        try:
            # Get model class
            model_class = ConfigItemFactory.get_model_class(item_type)
            if not model_class or not hasattr(model_class, 'api_endpoint'):
                logger.warning(f"No model class or endpoint for {item_type}")
                return items
            
            # Fetch all items (no folder parameter)
            url = model_class.api_endpoint
            response = self.api_client._make_request("GET", url, item_type=item_type)
            
            # Extract items
            raw_items = []
            if isinstance(response, dict) and 'data' in response:
                raw_items = response['data']
            elif isinstance(response, list):
                raw_items = response
            
            # Instantiate items
            default_count = 0
            for raw_item in raw_items:
                item_name = raw_item.get('name', 'unknown')
                try:
                    # Infrastructure items need a folder but API doesn't provide one
                    # Set the correct folder based on infrastructure type
                    if 'folder' not in raw_item and 'snippet' not in raw_item:
                        # Get the correct folder for this infrastructure type
                        folder = self.INFRASTRUCTURE_FOLDER_MAP.get(item_type)
                        if folder:
                            raw_item['folder'] = folder
                            logger.debug(f"  Added folder='{folder}' to {item_type} '{item_name}'")
                        else:
                            logger.warning(f"  No folder mapping for {item_type}, skipping")
                            continue
                    
                    # Check defaults BEFORE creating ConfigItem (more efficient)
                    # Use snippet field from raw API response
                    if not self.config.include_defaults and self._is_default_item(raw_item, item_type):
                        snippet_val = raw_item.get('snippet', '')
                        logger.debug(f"  Skipping '{item_name}' (default item, snippet='{snippet_val}')")
                        result.items_skipped += 1
                        default_count += 1
                        continue
                    
                    item = ConfigItemFactory.create_from_dict(item_type, raw_item)
                    items.append(item)
                    result.items_processed += 1
                except Exception as e:
                    handle_workflow_error(e, None, f'parse_{item_type}', result, self.config)
            
            if default_count > 0:
                logger.info(f"  Filtered {default_count} default {item_type} items")
        
        except Exception as e:
            logger.error(f"Error fetching {item_type}: {e}")
            handle_workflow_error(e, None, f'fetch_{item_type}', result, self.config)
        
        return items
    
    def _pull_bandwidth_allocations(self, result: WorkflowResult) -> List[Dict[str, Any]]:
        """
        Pull bandwidth allocation configurations.
        
        Bandwidth allocations provide information about Prisma Access regional
        deployments and allocated bandwidth per region.
        
        Args:
            result: WorkflowResult for error tracking
            
        Returns:
            List of bandwidth allocation dictionaries (raw data, not ConfigItem)
        """
        allocations = []
        
        try:
            logger.info("Fetching bandwidth allocations...")
            raw_allocations = self.api_client.get_all_bandwidth_allocations()
            
            for alloc in raw_allocations:
                # Bandwidth allocations don't have a ConfigItem model yet,
                # so we store them as raw dicts
                allocations.append(alloc)
                result.items_processed += 1
            
            logger.info(f"  Fetched {len(allocations)} bandwidth allocations")
            
        except Exception as e:
            error_str = str(e).lower()
            if "404" in error_str:
                logger.info("  Bandwidth allocations endpoint not available - skipping")
            else:
                logger.error(f"Error fetching bandwidth allocations: {e}")
                handle_workflow_error(e, None, 'fetch_bandwidth_allocations', result, self.config)
        
        return allocations
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pull statistics.
        
        Returns:
            Dictionary with pull statistics
        """
        return {
            'folder_types': len(self.FOLDER_TYPES),
            'snippet_types': len(self.SNIPPET_TYPES),
            'infrastructure_types': len(self.INFRASTRUCTURE_TYPES),
        }
