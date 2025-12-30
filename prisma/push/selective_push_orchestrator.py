"""
Selective Push Orchestrator for Prisma Access Configuration.

This module handles pushing selected configuration items to a destination
Prisma Access tenant, with conflict resolution and detailed result tracking.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time
import logging

from ..api_client import PrismaAccessAPIClient

# Set up logger
logger = logging.getLogger(__name__)


class SelectivePushOrchestrator:
    """Orchestrate selective push of configuration items."""

    def __init__(
        self,
        api_client: PrismaAccessAPIClient,
        conflict_resolution: str = "SKIP"
    ):
        """
        Initialize selective push orchestrator.

        Args:
            api_client: PrismaAccessAPIClient instance for destination tenant
            conflict_resolution: Conflict resolution strategy (SKIP/OVERWRITE/RENAME)
        """
        self.api_client = api_client
        self.conflict_resolution = conflict_resolution
        
        # Progress callback
        self.progress_callback: Optional[Callable[[str, int, int], None]] = None
        
        # Name mapping for RENAME mode (old_name -> new_name)
        # Used to update references in dependent items
        self.name_mappings: Dict[str, str] = {}
        
        # Results tracking
        self.results = {
            'summary': {
                'total': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'failed': 0,
                'renamed': 0,
                'deleted': 0
            },
            'details': [],
            'errors': []
        }

    def set_progress_callback(self, callback: Callable[[str, int, int], None]):
        """
        Set progress callback function.

        Args:
            callback: Function(message, current, total)
        """
        self.progress_callback = callback

    def _report_progress(self, message: str, current: int = 0, total: int = 0):
        """Report progress if callback is set."""
        if self.progress_callback:
            try:
                self.progress_callback(message, current, total)
            except Exception as e:
                # Silently ignore callback errors to prevent crashes
                pass
        # Don't print in threads - can cause Qt crashes
        # print(f"[{current}/{total}] {message}")

    def _add_result(
        self,
        item_type: str,
        name: str,
        folder: str,
        action: str,
        status: str,
        message: str,
        error: Optional[Exception] = None
    ):
        """Add a result entry."""
        result = {
            'type': item_type,
            'name': name,
            'folder': folder,
            'action': action,
            'status': status,
            'message': message
        }
        
        if error:
            result['error'] = str(error)
            self.results['errors'].append({
                'type': item_type,
                'name': name,
                'error': str(error)
            })
        
        self.results['details'].append(result)
        
        # Update summary
        self.results['summary']['total'] += 1
        if status == 'success':
            if action == 'created':
                self.results['summary']['created'] += 1
            elif action == 'updated':
                self.results['summary']['updated'] += 1
            elif action == 'skipped':
                self.results['summary']['skipped'] += 1
            elif action == 'renamed':
                self.results['summary']['renamed'] += 1
            elif action == 'deleted':
                self.results['summary']['deleted'] += 1
        elif status == 'failed':
            self.results['summary']['failed'] += 1
        
        # Log the action
        log_msg = f"[{action.upper()}] {item_type}: {name} (folder: {folder}) - {message}"
        
        # Check if this is a placeholder/not implemented action
        is_placeholder = 'API not implemented' in message or 'placeholder' in message.lower()
        
        if status == 'success':
            if is_placeholder:
                # Highlight placeholder actions as warnings
                logger.warning(f"⚠️  {log_msg}")
            elif action == 'skipped':
                logger.info(log_msg)
            else:
                logger.info(log_msg)
        elif status == 'failed':
            logger.error(log_msg)
            if error:
                logger.error(f"  Error details: {str(error)}")
        else:
            logger.warning(log_msg)

    def _update_references_in_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update references in a configuration item to use renamed names.
        
        Args:
            item: Configuration item dictionary
            
        Returns:
            Updated item with renamed references
        """
        if not self.name_mappings:
            return item
        
        # Deep copy to avoid modifying original
        import copy
        updated_item = copy.deepcopy(item)
        
        # Common fields that may contain object references
        reference_fields = [
            'source', 'destination',  # Security rules
            'source_address', 'destination_address',  # Various
            'members',  # Address groups, service groups
            'application',  # Security rules
            'service',  # Security rules
            'profile_setting',  # Security rules
            'log_setting',  # Security rules
            'schedule',  # Security rules
        ]
        
        def update_value(value):
            """Recursively update values that match renamed items."""
            if isinstance(value, str):
                # Check if this value matches any renamed item
                return self.name_mappings.get(value, value)
            elif isinstance(value, list):
                return [update_value(v) for v in value]
            elif isinstance(value, dict):
                return {k: update_value(v) for k, v in value.items()}
            return value
        
        # Update all reference fields
        for field in reference_fields:
            if field in updated_item:
                updated_item[field] = update_value(updated_item[field])
        
        return updated_item

    def push_selected_items(
        self,
        selected_items: Dict[str, Any],
        destination_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Push selected configuration items to destination tenant.

        Args:
            selected_items: Dictionary of selected items to push
            destination_config: Optional destination config for conflict detection

        Returns:
            Push results dictionary with summary and details
        """
        start_time = time.time()
        
        # Reset results and name mappings
        self.name_mappings = {}
        self.results = {
            'summary': {
                'total': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'failed': 0,
                'renamed': 0,
                'deleted': 0
            },
            'details': [],
            'errors': []
        }
        
        try:
            # Count total items for progress
            total_items = self._count_items(selected_items)
            current_item = 0
            
            logger.info("=" * 80)
            logger.info("STARTING SELECTIVE PUSH OPERATION")
            logger.info(f"Destination Tenant: {self.api_client.tsg_id}")
            logger.info(f"Conflict Resolution: {self.conflict_resolution}")
            logger.info(f"Total Items to Push: {total_items}")
            logger.info("=" * 80)
            
            self._report_progress("Starting push operation", 0, total_items)
            
            # PHASE 1: If OVERWRITE mode, delete existing items in REVERSE dependency order
            # (top-down: rules → profiles → hip → objects → infrastructure → folders)
            if self.conflict_resolution == 'OVERWRITE' and destination_config:
                logger.info("-" * 80)
                logger.info("PHASE 1: Deleting existing conflicting items (reverse dependency order)")
                logger.info("-" * 80)
                
                # Delete in reverse order: rules first, objects last
                if 'folders' in selected_items:
                    current_item = self._delete_security_rules(
                        selected_items['folders'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                if 'snippets' in selected_items:
                    current_item = self._delete_snippets(
                        selected_items['snippets'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                if 'folders' in selected_items:
                    current_item = self._delete_folder_hip(
                        selected_items['folders'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                if 'folders' in selected_items:
                    current_item = self._delete_folder_profiles(
                        selected_items['folders'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                if 'infrastructure' in selected_items:
                    current_item = self._delete_infrastructure(
                        selected_items['infrastructure'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                if 'folders' in selected_items:
                    current_item = self._delete_folder_objects(
                        selected_items['folders'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                logger.info("-" * 80)
                logger.info("PHASE 1 COMPLETE: All conflicting items deleted")
                logger.info("-" * 80)
            
            # PHASE 2: Create/Update items in FORWARD dependency order
            # (bottom-up: folders → objects → profiles → hip → infrastructure → rules → snippets)
            logger.info("-" * 80)
            logger.info("PHASE 2: Creating/updating items (forward dependency order)")
            logger.info("-" * 80)
            
            # 1. Push folders (create if needed)
            if 'folders' in selected_items:
                current_item = self._push_folders(
                    selected_items['folders'],
                    destination_config,
                    current_item,
                    total_items
                )
            
            # 2. Push objects
            if 'folders' in selected_items:
                current_item = self._push_folder_objects(
                    selected_items['folders'],
                    destination_config,
                    current_item,
                    total_items
                )
            
            # 3. Push profiles
            if 'folders' in selected_items:
                current_item = self._push_folder_profiles(
                    selected_items['folders'],
                    destination_config,
                    current_item,
                    total_items
                )
            
            # 4. Push HIP
            if 'folders' in selected_items:
                current_item = self._push_folder_hip(
                    selected_items['folders'],
                    destination_config,
                    current_item,
                    total_items
                )
            
            # 5. Push infrastructure
            if 'infrastructure' in selected_items:
                current_item = self._push_infrastructure(
                    selected_items['infrastructure'],
                    destination_config,
                    current_item,
                    total_items
                )
            
            # 6. Push security rules
            if 'folders' in selected_items:
                current_item = self._push_security_rules(
                    selected_items['folders'],
                    destination_config,
                    current_item,
                    total_items
                )
            
            # 7. Push snippets
            if 'snippets' in selected_items:
                current_item = self._push_snippets(
                    selected_items['snippets'],
                    destination_config,
                    current_item,
                    total_items
                )
            
            logger.info("-" * 80)
            logger.info("PHASE 2 COMPLETE: All items created/updated")
            logger.info("-" * 80)
            
            elapsed_time = time.time() - start_time
            
            self._report_progress("Push operation complete", total_items, total_items)
            
            # Log completion summary
            logger.info("=" * 80)
            logger.info("PUSH OPERATION COMPLETED")
            logger.info(f"Total Items: {self.results['summary']['total']}")
            logger.info(f"Created: {self.results['summary']['created']}")
            logger.info(f"Updated: {self.results['summary']['updated']}")
            logger.info(f"Deleted: {self.results['summary']['deleted']}")
            logger.info(f"Skipped: {self.results['summary']['skipped']}")
            logger.info(f"Failed: {self.results['summary']['failed']}")
            logger.info(f"Elapsed Time: {elapsed_time:.2f} seconds")
            logger.info("=" * 80)
            
            return {
                'success': True,
                'message': 'Push completed',
                'results': self.results,
                'elapsed_seconds': elapsed_time
            }
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error("PUSH OPERATION FAILED")
            logger.error(f"Error: {str(e)}")
            logger.error("=" * 80)
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'message': f'Push failed: {str(e)}',
                'results': self.results,
                'error': str(e)
            }

    def _count_items(self, selected_items: Dict[str, Any]) -> int:
        """Count total items to push."""
        count = 0
        
        # Count folders
        if 'folders' in selected_items:
            for folder in selected_items['folders']:
                # Count folder itself
                count += 1
                
                # Count objects in folder
                if 'objects' in folder:
                    for obj_type, obj_list in folder.get('objects', {}).items():
                        count += len(obj_list)
                
                # Count profiles in folder
                if 'profiles' in folder:
                    for prof_type, prof_list in folder.get('profiles', {}).items():
                        count += len(prof_list)
                
                # Count HIP in folder
                if 'hip' in folder:
                    for hip_type, hip_list in folder.get('hip', {}).items():
                        count += len(hip_list)
                
                # Count rules in folder
                if 'security_rules' in folder:
                    count += len(folder.get('security_rules', []))
        
        # Count infrastructure
        if 'infrastructure' in selected_items:
            for infra_type, infra_list in selected_items['infrastructure'].items():
                if isinstance(infra_list, list):
                    count += len(infra_list)
        
        # Count snippets
        if 'snippets' in selected_items:
            count += len(selected_items['snippets'])
        
        return count

    # ========================================================================
    # DELETE METHODS (for OVERWRITE mode - reverse dependency order)
    # ========================================================================
    
    def _delete_security_rules(
        self,
        folders: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Delete existing security rules (Phase 1 - OVERWRITE mode)."""
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            
            if 'security_rules' not in folder:
                continue
            
            for rule in folder.get('security_rules', []):
                rule_name = rule.get('name', 'Unknown')
                
                # Check if exists in destination
                exists = False
                if destination_config and 'security_rules' in destination_config:
                    dest_rules = destination_config['security_rules'].get(folder_name, [])
                    exists = any(r.get('name') == rule_name for r in dest_rules)
                
                if exists:
                    self._report_progress(
                        f"Deleting security_rule: {rule_name}",
                        current_item,
                        total_items
                    )
                    
                    # TODO: Implement delete API call
                    self._add_result(
                        'security_rule',
                        rule_name,
                        folder_name,
                        'deleted',
                        'success',
                        'Deleted (placeholder - API not implemented)'
                    )
                    current_item += 1
        
        return current_item
    
    def _delete_snippets(
        self,
        snippets: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Delete existing snippets (Phase 1 - OVERWRITE mode)."""
        for snippet in snippets:
            snippet_name = snippet.get('name', 'Unknown')
            
            # Check if exists in destination
            exists = False
            if destination_config and 'snippets' in destination_config:
                exists = any(s.get('name') == snippet_name for s in destination_config['snippets'])
            
            if exists:
                self._report_progress(
                    f"Deleting snippet: {snippet_name}",
                    current_item,
                    total_items
                )
                
                # TODO: Implement delete API call
                self._add_result(
                    'snippet',
                    snippet_name,
                    'Global',
                    'deleted',
                    'success',
                    'Deleted (placeholder - API not implemented)'
                )
                current_item += 1
        
        return current_item
    
    def _delete_folder_hip(
        self,
        folders: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Delete existing HIP objects/profiles (Phase 1 - OVERWRITE mode)."""
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            
            if 'hip' not in folder:
                continue
            
            for hip_type, hip_list in folder.get('hip', {}).items():
                for hip_item in hip_list:
                    hip_name = hip_item.get('name', 'Unknown')
                    
                    # Check if exists in destination
                    exists = False
                    if destination_config and 'hip' in destination_config:
                        dest_hip = destination_config['hip'].get(hip_type, {})
                        exists = hip_name in dest_hip
                    
                    if exists:
                        self._report_progress(
                            f"Deleting {hip_type}: {hip_name}",
                            current_item,
                            total_items
                        )
                        
                        # TODO: Implement delete API call
                        self._add_result(
                            hip_type,
                            hip_name,
                            folder_name,
                            'deleted',
                            'success',
                            'Deleted (placeholder - API not implemented)'
                        )
                        current_item += 1
        
        return current_item
    
    def _delete_folder_profiles(
        self,
        folders: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Delete existing profiles (Phase 1 - OVERWRITE mode)."""
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            
            if 'profiles' not in folder:
                continue
            
            for prof_type, prof_list in folder.get('profiles', {}).items():
                for prof in prof_list:
                    prof_name = prof.get('name', 'Unknown')
                    
                    # Check if exists in destination
                    exists = False
                    if destination_config and 'profiles' in destination_config:
                        dest_profiles = destination_config['profiles'].get(prof_type, {})
                        exists = prof_name in dest_profiles
                    
                    if exists:
                        self._report_progress(
                            f"Deleting {prof_type}: {prof_name}",
                            current_item,
                            total_items
                        )
                        
                        # TODO: Implement delete API call
                        self._add_result(
                            prof_type,
                            prof_name,
                            folder_name,
                            'deleted',
                            'success',
                            'Deleted (placeholder - API not implemented)'
                        )
                        current_item += 1
        
        return current_item
    
    def _delete_infrastructure(
        self,
        infrastructure: Dict[str, Any],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Delete existing infrastructure items (Phase 1 - OVERWRITE mode)."""
        for infra_type, infra_list in infrastructure.items():
            if not isinstance(infra_list, list):
                continue
            
            for infra_item in infra_list:
                infra_name = infra_item.get('name', 'Unknown')
                
                # Check if exists in destination
                exists = False
                if destination_config and 'infrastructure' in destination_config:
                    dest_infra = destination_config['infrastructure'].get(infra_type, [])
                    if isinstance(dest_infra, list):
                        exists = any(i.get('name') == infra_name for i in dest_infra)
                    elif isinstance(dest_infra, dict):
                        exists = infra_name in dest_infra
                
                if exists:
                    self._report_progress(
                        f"Deleting {infra_type}: {infra_name}",
                        current_item,
                        total_items
                    )
                    
                    # TODO: Implement delete API call
                    self._add_result(
                        infra_type,
                        infra_name,
                        'Infrastructure',
                        'deleted',
                        'success',
                        'Deleted (placeholder - API not implemented)'
                    )
                    current_item += 1
        
        return current_item
    
    def _delete_folder_objects(
        self,
        folders: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Delete existing objects (Phase 1 - OVERWRITE mode)."""
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            
            if 'objects' not in folder:
                continue
            
            for obj_type, obj_list in folder.get('objects', {}).items():
                for obj in obj_list:
                    obj_name = obj.get('name', 'Unknown')
                    
                    # Check if exists in destination
                    exists = False
                    if destination_config and 'objects' in destination_config:
                        dest_objects = destination_config['objects'].get(obj_type, {})
                        exists = obj_name in dest_objects
                    
                    if exists:
                        self._report_progress(
                            f"Deleting {obj_type}: {obj_name}",
                            current_item,
                            total_items
                        )
                        
                        # TODO: Implement delete API call
                        self._add_result(
                            obj_type,
                            obj_name,
                            folder_name,
                            'deleted',
                            'success',
                            'Deleted (placeholder - API not implemented)'
                        )
                        current_item += 1
        
        return current_item
    
    # ========================================================================
    # PUSH/CREATE METHODS (forward dependency order)
    # ========================================================================
    
    def _push_folders(
        self,
        folders: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Push folders (create if needed)."""
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            
            self._report_progress(
                f"Processing folder: {folder_name}",
                current_item,
                total_items
            )
            
            # Check if folder exists in destination
            exists = False
            if destination_config and 'folders' in destination_config:
                exists = folder_name in destination_config['folders']
            
            if exists:
                # Folder exists - skip (folders themselves are not updated)
                self._add_result(
                    'folder',
                    folder_name,
                    folder_name,
                    'skipped',
                    'success',
                    'Folder already exists'
                )
            else:
                # Create folder
                # TODO: Implement folder creation API call
                # For now, just track as placeholder
                self._add_result(
                    'folder',
                    folder_name,
                    folder_name,
                    'created',
                    'success',
                    'Folder created (placeholder - API not implemented)'
                )
            
            current_item += 1
        
        return current_item

    def _push_folder_objects(
        self,
        folders: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Push objects from folders."""
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            
            if 'objects' not in folder:
                continue
            
            for obj_type, obj_list in folder.get('objects', {}).items():
                for obj in obj_list:
                    obj_name = obj.get('name', 'Unknown')
                    
                    self._report_progress(
                        f"Pushing {obj_type}: {obj_name}",
                        current_item,
                        total_items
                    )
                    
                    # Check if exists in destination
                    # Note: In OVERWRITE mode, items were already deleted in Phase 1,
                    # so we should always CREATE, not UPDATE
                    exists = False
                    if self.conflict_resolution != 'OVERWRITE':
                        if destination_config and 'objects' in destination_config:
                            dest_objects = destination_config['objects'].get(obj_type, {})
                            exists = obj_name in dest_objects
                    
                    # Apply conflict resolution
                    if exists:
                        if self.conflict_resolution == 'SKIP':
                            self._add_result(
                                obj_type,
                                obj_name,
                                folder_name,
                                'skipped',
                                'success',
                                'Already exists, skipped per conflict resolution'
                            )
                        elif self.conflict_resolution == 'RENAME':
                            # Create with "-copy" suffix and track name mapping
                            new_name = f"{obj_name}-copy"
                            self.name_mappings[obj_name] = new_name
                            
                            logger.info(f"Name mapping: {obj_name} → {new_name}")
                            
                            # TODO: Implement create with renamed API call
                            self._add_result(
                                obj_type,
                                new_name,
                                folder_name,
                                'renamed',
                                'success',
                                f'Created as {new_name} (placeholder - API not implemented)'
                            )
                    else:
                        # Create new (or recreate after delete in OVERWRITE mode)
                        # TODO: Implement create API call
                        self._add_result(
                            obj_type,
                            obj_name,
                            folder_name,
                            'created',
                            'success',
                            'Created (placeholder - API not implemented)'
                        )
                    
                    current_item += 1
        
        return current_item

    def _push_folder_profiles(
        self,
        folders: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Push profiles from folders."""
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            
            if 'profiles' not in folder:
                continue
            
            for prof_type, prof_list in folder.get('profiles', {}).items():
                for prof in prof_list:
                    prof_name = prof.get('name', 'Unknown')
                    
                    self._report_progress(
                        f"Pushing {prof_type}: {prof_name}",
                        current_item,
                        total_items
                    )
                    
                    # Check if exists in destination
                    # Note: In OVERWRITE mode, items were already deleted in Phase 1
                    exists = False
                    if self.conflict_resolution != 'OVERWRITE':
                        if destination_config and 'profiles' in destination_config:
                            dest_profiles = destination_config['profiles'].get(prof_type, {})
                            exists = prof_name in dest_profiles
                    
                    # Apply conflict resolution
                    if exists:
                        if self.conflict_resolution == 'SKIP':
                            self._add_result(
                                prof_type,
                                prof_name,
                                folder_name,
                                'skipped',
                                'success',
                                'Already exists, skipped per conflict resolution'
                            )
                        elif self.conflict_resolution == 'RENAME':
                            # Create with "-copy" suffix and track name mapping
                            new_name = f"{prof_name}-copy"
                            self.name_mappings[prof_name] = new_name
                            
                            logger.info(f"Name mapping: {prof_name} → {new_name}")
                            
                            self._add_result(
                                prof_type,
                                new_name,
                                folder_name,
                                'renamed',
                                'success',
                                f'Created as {new_name} (placeholder - API not implemented)'
                            )
                    else:
                        # Create new (or recreate after delete in OVERWRITE mode)
                        self._add_result(
                            prof_type,
                            prof_name,
                            folder_name,
                            'created',
                            'success',
                            'Created (placeholder - API not implemented)'
                        )
                    
                    current_item += 1
        
        return current_item

    def _push_folder_hip(
        self,
        folders: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Push HIP objects/profiles from folders."""
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            
            if 'hip' not in folder:
                continue
            
            for hip_type, hip_list in folder.get('hip', {}).items():
                for hip_item in hip_list:
                    hip_name = hip_item.get('name', 'Unknown')
                    
                    self._report_progress(
                        f"Pushing {hip_type}: {hip_name}",
                        current_item,
                        total_items
                    )
                    
                    # Check if exists in destination
                    # Note: In OVERWRITE mode, items were already deleted in Phase 1
                    exists = False
                    if self.conflict_resolution != 'OVERWRITE':
                        if destination_config and 'hip' in destination_config:
                            dest_hip = destination_config['hip'].get(hip_type, {})
                            exists = hip_name in dest_hip
                    
                    # Apply conflict resolution
                    if exists:
                        if self.conflict_resolution == 'SKIP':
                            self._add_result(
                                hip_type,
                                hip_name,
                                folder_name,
                                'skipped',
                                'success',
                                'Already exists, skipped per conflict resolution'
                            )
                        elif self.conflict_resolution == 'RENAME':
                            # Create with "-copy" suffix and track name mapping
                            new_name = f"{hip_name}-copy"
                            self.name_mappings[hip_name] = new_name
                            
                            logger.info(f"Name mapping: {hip_name} → {new_name}")
                            
                            self._add_result(
                                hip_type,
                                new_name,
                                folder_name,
                                'renamed',
                                'success',
                                f'Created as {new_name} (placeholder - API not implemented)'
                            )
                    else:
                        # Create new (or recreate after delete in OVERWRITE mode)
                        self._add_result(
                            hip_type,
                            hip_name,
                            folder_name,
                            'created',
                            'success',
                            'Created (placeholder - API not implemented)'
                        )
                    
                    current_item += 1
        
        return current_item

    def _push_infrastructure(
        self,
        infrastructure: Dict[str, Any],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Push infrastructure items."""
        for infra_type, infra_list in infrastructure.items():
            if not isinstance(infra_list, list):
                continue
            
            for item in infra_list:
                item_name = item.get('name', item.get('id', 'Unknown'))
                folder_name = item.get('folder', 'N/A')
                
                self._report_progress(
                    f"Pushing {infra_type}: {item_name}",
                    current_item,
                    total_items
                )
                
                # Check if exists in destination
                # Note: In OVERWRITE mode, items were already deleted in Phase 1
                exists = False
                if self.conflict_resolution != 'OVERWRITE':
                    if destination_config and 'infrastructure' in destination_config:
                        dest_infra = destination_config['infrastructure'].get(infra_type, [])
                        if isinstance(dest_infra, list):
                            exists = any(i.get('name') == item_name for i in dest_infra)
                        elif isinstance(dest_infra, dict):
                            exists = item_name in dest_infra
                
                # Apply conflict resolution
                if exists:
                    if self.conflict_resolution == 'SKIP':
                        self._add_result(
                            infra_type,
                            item_name,
                            folder_name,
                            'skipped',
                            'success',
                            'Already exists, skipped per conflict resolution'
                        )
                    elif self.conflict_resolution == 'RENAME':
                        # Create with "-copy" suffix and track name mapping
                        new_name = f"{item_name}-copy"
                        self.name_mappings[item_name] = new_name
                        
                        logger.info(f"Name mapping: {item_name} → {new_name}")
                        
                        self._add_result(
                            infra_type,
                            new_name,
                            folder_name,
                            'renamed',
                            'success',
                            f'Created as {new_name} (placeholder - API not implemented)'
                        )
                else:
                    # Create new (or recreate after delete in OVERWRITE mode)
                    self._add_result(
                        infra_type,
                        item_name,
                        folder_name,
                        'created',
                        'success',
                        'Created (placeholder - API not implemented)'
                    )
                
                current_item += 1
        
        return current_item

    def _push_security_rules(
        self,
        folders: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Push security rules from folders."""
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            
            if 'security_rules' not in folder:
                continue
            
            for rule in folder.get('security_rules', []):
                rule_name = rule.get('name', 'Unknown')
                
                self._report_progress(
                    f"Pushing security rule: {rule_name}",
                    current_item,
                    total_items
                )
                
                # Update references in rule to use renamed items (RENAME mode)
                updated_rule = self._update_references_in_item(rule)
                
                # Check if exists in destination
                # Note: In OVERWRITE mode, items were already deleted in Phase 1
                exists = False
                if self.conflict_resolution != 'OVERWRITE':
                    if destination_config and 'security_rules' in destination_config:
                        dest_rules = destination_config['security_rules'].get(folder_name, [])
                        exists = any(r.get('name') == rule_name for r in dest_rules)
                
                # Apply conflict resolution
                if exists:
                    if self.conflict_resolution == 'SKIP':
                        self._add_result(
                            'security_rule',
                            rule_name,
                            folder_name,
                            'skipped',
                            'success',
                            'Already exists, skipped per conflict resolution'
                        )
                    elif self.conflict_resolution == 'RENAME':
                        # Create with "-copy" suffix and track name mapping
                        new_name = f"{rule_name}-copy"
                        self.name_mappings[rule_name] = new_name
                        
                        logger.info(f"Name mapping: {rule_name} → {new_name}")
                        
                        # Log reference updates if any
                        if self.name_mappings:
                            logger.info(f"  Updated references in rule: {list(self.name_mappings.keys())}")
                        
                        # TODO: Use updated_rule with renamed references
                        self._add_result(
                            'security_rule',
                            new_name,
                            folder_name,
                            'renamed',
                            'success',
                            f'Created as {new_name} (placeholder - API not implemented)'
                        )
                else:
                    # Create new (or recreate after delete in OVERWRITE mode)
                    # TODO: Use updated_rule if in RENAME mode and there are mappings
                    self._add_result(
                        'security_rule',
                        rule_name,
                        folder_name,
                        'created',
                        'success',
                        'Created (placeholder - API not implemented)'
                    )
                
                current_item += 1
        
        return current_item

    def _push_snippets(
        self,
        snippets: List[Dict[str, Any]],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """Push snippets."""
        for snippet in snippets:
            snippet_name = snippet.get('name', 'Unknown')
            
            self._report_progress(
                f"Pushing snippet: {snippet_name}",
                current_item,
                total_items
            )
            
            # Check if exists in destination
            # Note: In OVERWRITE mode, items were already deleted in Phase 1
            exists = False
            if self.conflict_resolution != 'OVERWRITE':
                if destination_config and 'snippets' in destination_config:
                    exists = any(s.get('name') == snippet_name for s in destination_config['snippets'])
            
            # Apply conflict resolution
            if exists:
                if self.conflict_resolution == 'SKIP':
                    self._add_result(
                        'snippet',
                        snippet_name,
                        'Global',
                        'skipped',
                        'success',
                        'Already exists, skipped per conflict resolution'
                    )
                elif self.conflict_resolution == 'RENAME':
                    # Create with "-copy" suffix and track name mapping
                    new_name = f"{snippet_name}-copy"
                    self.name_mappings[snippet_name] = new_name
                    
                    logger.info(f"Name mapping: {snippet_name} → {new_name}")
                    
                    self._add_result(
                        'snippet',
                        new_name,
                        'Global',
                        'renamed',
                        'success',
                        f'Created as {new_name} (placeholder - API not implemented)'
                    )
            else:
                # Create new (or recreate after delete in OVERWRITE mode)
                self._add_result(
                    'snippet',
                    snippet_name,
                    'Global',
                    'created',
                    'success',
                    'Created (placeholder - API not implemented)'
                )
            
            current_item += 1
        
        return current_item
