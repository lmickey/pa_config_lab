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
        
        # Track if delete phase had critical failures
        self.delete_phase_failed = False
        
        # Track items that failed to delete (for OVERWRITE mode)
        # Format: {(item_type, item_name, folder): error_message}
        self.failed_deletes: Dict[tuple, str] = {}
        
        # Results tracking
        self.results = {
            'summary': {
                'total': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'failed': 0,
                'renamed': 0,
                'deleted': 0,
                'could_not_overwrite': 0  # Items that couldn't be deleted in OVERWRITE mode
            },
            'details': [],
            'errors': [],
            'could_not_overwrite': []  # List of items that couldn't be overwritten
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
                # Limit error details to prevent log overflow
                error_str = str(error)[:500]
                logger.error(f"  Error details: {error_str}")
        else:
            logger.warning(log_msg)

    def _check_failed_delete(self, item_type: str, item_name: str, folder: str, current_item: int) -> bool:
        """
        Check if an item failed to delete in Phase 1 (OVERWRITE mode).
        If it did, skip creation attempt (item already counted in Phase 1).
        
        Args:
            item_type: Type of item
            item_name: Name of item
            folder: Folder name
            current_item: Current item number (for tracking)
            
        Returns:
            True if item failed to delete (should skip creation), False otherwise
        """
        key = (item_type, item_name, folder)
        if key in self.failed_deletes:
            # Item already has a result from Phase 1 (delete failed or skipped)
            # Don't add another result or increment counts - just skip the create
            return True
        return False
    
    def _extract_409_references(self, error: Exception) -> str:
        """
        Extract reference information from a 409 Conflict error.
        
        Args:
            error: Exception from API call
            
        Returns:
            Human-readable string describing what references this item
        """
        # For requests.HTTPError, parse the response body
        if hasattr(error, 'response') and error.response is not None:
            try:
                response_json = error.response.json()
                errors = response_json.get('_errors', [])
                
                for err in errors:
                    details = err.get('details', {})
                    error_type = details.get('errorType', '')
                    
                    # Check if this is a "Reference Not Zero" error
                    if error_type == 'Reference Not Zero':
                        # Extract the reference paths
                        messages = details.get('message', [])
                        errors_list = details.get('errors', [])
                        
                        # Build a readable message
                        references = []
                        
                        # Get the reference paths from messages
                        for msg in messages:
                            if isinstance(msg, str) and '->' in msg:
                                # Clean up the path
                                parts = [p.strip() for p in msg.split('->')]
                                # Get the last few meaningful parts
                                meaningful_parts = [p for p in parts if p and p != 'plugins' and p != 'cloud_services']
                                if meaningful_parts:
                                    references.append(' → '.join(meaningful_parts[-3:]))
                        
                        # Get additional details from errors list
                        for error_detail in errors_list:
                            if error_detail.get('type') == 'NON_ZERO_REFS':
                                extra = error_detail.get('extra', [])
                                for extra_path in extra:
                                    if isinstance(extra_path, str):
                                        # Extract the readable part from path like:
                                        # "plugins/cloud_services/pbf-target/group/[Main SC]/target/[Azure SCM Lab]"
                                        parts = extra_path.split('/')
                                        # Find bracketed items which are the actual names
                                        names = [p.strip('[]') for p in parts if '[' in p]
                                        if names:
                                            references.append(' → '.join(names))
                        
                        if references:
                            # Deduplicate and format
                            unique_refs = list(set(references))
                            return f"Referenced by: {', '.join(unique_refs)}"
                
            except Exception as parse_err:
                # If parsing fails, return generic message
                pass
        
        # Default for non-409 or unparseable errors
        return "Reference conflict (details unavailable)"
    
    def _is_already_exists_error(self, error: Exception) -> bool:
        """
        Check if an error is an 'already exists' error from the API.
        
        Args:
            error: Exception to check
            
        Returns:
            True if this is an 'already exists' error
        """
        error_str = str(error).lower()
        
        # Check the error message
        if 'already exists' in error_str or 'object_already_exists' in error_str:
            return True
        
        # For requests.HTTPError, check the response body
        if hasattr(error, 'response') and error.response is not None:
            try:
                response_text = error.response.text.lower()
                if 'already exists' in response_text or 'object_already_exists' in response_text:
                    return True
            except:
                pass
        
        return False
    
    def _clean_item_for_api(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove read-only fields from an item before sending to API.
        
        These fields are returned by GET operations but should not be
        included in POST/PUT operations.
        
        Args:
            item: Configuration item dictionary
            
        Returns:
            Cleaned item without read-only fields
        """
        # Use simple dict copy instead of deepcopy to avoid memory issues
        # We don't need deep copy since we're only modifying top-level keys
        cleaned = dict(item)
        
        # List of read-only fields that should be removed
        readonly_fields = [
            'id',              # API-generated ID
            'metadata',        # Created/updated timestamps and users
            'override_id',     # Override-specific fields
            'override_loc',
            'override_type',
            'is_default',      # System-defined flag
            'created',         # Timestamps
            'updated',
            'created_by',      # User tracking
            'updated_by',
        ]
        
        for field in readonly_fields:
            cleaned.pop(field, None)  # Use pop with default instead of checking 'if field in'
        
        return cleaned
    
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
        
        # Shallow copy to avoid modifying original, but reuse nested structures
        updated_item = dict(item)
        
        # Common fields that may contain object references
        reference_fields = [
            # Security rules
            'source', 'destination',
            'source_address', 'destination_address',
            'application', 'service',
            'profile_setting', 'log_setting', 'schedule',
            
            # Groups
            'members',  # Address groups, service groups
            
            # Infrastructure - IPsec Tunnels
            'auto_key',  # Contains ike_gateway reference
            'tunnel_monitor',  # May contain destination_ip
            
            # Infrastructure - IKE Gateways  
            'authentication',  # Contains pre_shared_key or certificate
            'protocol',  # Contains ikev1/ikev2 settings
            'protocol_common',  # Common protocol settings
            
            # Infrastructure - Service Connections
            'ipsec_tunnel',  # Reference to IPsec tunnel name
            'backup_SC',  # Backup service connection
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
        
        # Special handling for infrastructure items with nested references
        
        # IPsec Tunnels: auto_key.ike_gateway is a direct reference
        if 'auto_key' in updated_item and isinstance(updated_item['auto_key'], dict):
            if 'ike_gateway' in updated_item['auto_key']:
                old_gateway = updated_item['auto_key']['ike_gateway']
                updated_item['auto_key']['ike_gateway'] = self.name_mappings.get(old_gateway, old_gateway)
        
        # IKE Gateways: protocol.ikev1/ikev2.ike_crypto_profile
        if 'protocol' in updated_item and isinstance(updated_item['protocol'], dict):
            for version in ['ikev1', 'ikev2']:
                if version in updated_item['protocol'] and isinstance(updated_item['protocol'][version], dict):
                    if 'ike_crypto_profile' in updated_item['protocol'][version]:
                        old_profile = updated_item['protocol'][version]['ike_crypto_profile']
                        updated_item['protocol'][version]['ike_crypto_profile'] = self.name_mappings.get(old_profile, old_profile)
        
        # IPsec Tunnels: anti_replay, copy_tos, enable_gre_encapsulation contain ipsec_crypto_profile in tunnel_interface
        if 'tunnel_interface' in updated_item and isinstance(updated_item['tunnel_interface'], dict):
            if 'ipsec_crypto_profile' in updated_item['tunnel_interface']:
                old_profile = updated_item['tunnel_interface']['ipsec_crypto_profile']
                updated_item['tunnel_interface']['ipsec_crypto_profile'] = self.name_mappings.get(old_profile, old_profile)
        
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
        self.failed_deletes = {}  # Reset failed deletes tracking
        self.results = {
            'summary': {
                'total': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'failed': 0,
                'renamed': 0,
                'deleted': 0,
                'could_not_overwrite': 0
            },
            'details': [],
            'errors': [],
            'could_not_overwrite': []
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
            # (top-down: rules → snippets → infrastructure → hip → profiles → objects → folders)
            # Note: Infrastructure must be deleted BEFORE profiles because infra uses profiles
            if self.conflict_resolution == 'OVERWRITE' and destination_config:
                logger.info("-" * 80)
                logger.info("PHASE 1: Deleting existing conflicting items (reverse dependency order)")
                logger.info("-" * 80)
                
                # Delete in reverse order: rules first, objects last
                # 1. Security rules (depend on everything)
                if 'folders' in selected_items:
                    current_item = self._delete_security_rules(
                        selected_items['folders'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                # 2. Snippets
                if 'snippets' in selected_items:
                    current_item = self._delete_snippets(
                        selected_items['snippets'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                # 3. Infrastructure (uses profiles, so delete BEFORE profiles)
                if 'infrastructure' in selected_items:
                    current_item = self._delete_infrastructure(
                        selected_items['infrastructure'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                # 4. HIP (may use profiles)
                if 'folders' in selected_items:
                    current_item = self._delete_folder_hip(
                        selected_items['folders'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                # 5. Profiles (used by infrastructure and HIP)
                if 'folders' in selected_items:
                    current_item = self._delete_folder_profiles(
                        selected_items['folders'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                # 6. Objects (used by rules and profiles)
                if 'folders' in selected_items:
                    current_item = self._delete_folder_objects(
                        selected_items['folders'],
                        destination_config,
                        current_item,
                        total_items
                    )
                
                logger.info("-" * 80)
                logger.info("PHASE 1 COMPLETE: All conflicting items deleted")
                
                # Check if there were delete failures
                delete_failures = sum(1 for d in self.results['details'] if d.get('action') == 'deleted' and d.get('status') == 'failed')
                if delete_failures > 0:
                    logger.warning(f"⚠️  {delete_failures} items failed to delete in Phase 1")
                    logger.warning("⚠️  Continuing with Phase 2, but some items may fail to create due to conflicts")
                    self.delete_phase_failed = True
                
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
            
            # Report final progress (wrapped to prevent crashes)
            try:
                self._report_progress("Push operation complete", total_items, total_items)
            except Exception as prog_err:
                pass  # Silently ignore progress errors
            
            # Log completion summary (wrapped to prevent crashes)
            try:
                logger.info("=" * 80)
                logger.info("PUSH OPERATION COMPLETED")
                logger.info(f"Total Items: {self.results['summary']['total']}")
            except Exception as e:
                pass  # Silently ignore logging errors
            
            try:
                logger.info(f"Created: {self.results['summary']['created']}")
                logger.info(f"Updated: {self.results['summary']['updated']}")
                logger.info(f"Deleted: {self.results['summary']['deleted']}")
                logger.info(f"Renamed: {self.results['summary']['renamed']}")
                logger.info(f"Skipped: {self.results['summary']['skipped']}")
                logger.info(f"Failed: {self.results['summary']['failed']}")
            except Exception as e:
                pass  # Silently ignore logging errors
            
            # Log items that couldn't be overwritten
            try:
                could_not_overwrite = self.results['summary'].get('could_not_overwrite', 0)
                if could_not_overwrite > 0:
                    logger.warning(f"Could Not Overwrite: {could_not_overwrite}")
                    logger.warning("Items that could not be overwritten (delete failed):")
                    # Safely iterate with error handling
                    for item in self.results.get('could_not_overwrite', []):
                        try:
                            item_type = item.get('type', 'unknown')
                            item_name = item.get('name', 'unknown')
                            item_folder = item.get('folder', 'unknown')
                            item_reason = str(item.get('reason', 'unknown'))[:200]  # Truncate reason
                            logger.warning(f"  - {item_type}: {item_name} (folder: {item_folder}) - {item_reason}")
                        except Exception as item_err:
                            pass  # Silently ignore item logging errors
            except Exception as e:
                pass  # Silently ignore logging errors
            
            try:
                logger.info(f"Elapsed Time: {elapsed_time:.2f} seconds")
                logger.info("=" * 80)
            except Exception as e:
                pass  # Silently ignore logging errors
            
            # Build return dictionary safely
            try:
                result_dict = {
                    'success': True,
                    'message': 'Push completed',
                    'results': self.results,
                    'elapsed_seconds': elapsed_time
                }
                return result_dict
            except Exception as ret_err:
                # Return minimal safe result (don't print from thread)
                return {
                    'success': True,
                    'message': 'Push completed (error building full results)',
                    'results': {'summary': {'total': 0}},
                    'elapsed_seconds': elapsed_time
                }
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error("PUSH OPERATION FAILED")
            logger.error(f"Error: {str(e)}")
            logger.error("=" * 80)
            import traceback
            # Log traceback to file instead of console
            logger.error(traceback.format_exc())
            
            # Create a safe copy of results to avoid serialization issues
            try:
                safe_results = {
                    'summary': dict(self.results.get('summary', {})),
                    'details': [],  # Don't include details on error to avoid size issues
                    'errors': self.results.get('errors', [])[:10],  # Limit to first 10 errors
                    'could_not_overwrite': self.results.get('could_not_overwrite', [])[:10]
                }
            except:
                safe_results = {'summary': {}, 'details': [], 'errors': [], 'could_not_overwrite': []}
            
            return {
                'success': False,
                'message': f'Push failed: {str(e)[:200]}',  # Limit error message length
                'results': safe_results,
                'error': str(e)[:200]
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
    # HELPER METHODS - API Call Wrappers
    # ========================================================================
    
    def _create_object(self, obj_type: str, obj_data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """
        Create an object using the appropriate API method.
        
        Args:
            obj_type: Object type (e.g., 'address_objects', 'service_objects')
            obj_data: Object data
            folder: Folder name
            
        Returns:
            API response
        """
        # Map object type to API method
        type_to_method = {
            'address_objects': self.api_client.create_address,
            'address_groups': self.api_client.create_address_group,
            'service_objects': self.api_client.create_service,
            'service_groups': self.api_client.create_service_group,
        }
        
        method = type_to_method.get(obj_type)
        if not method:
            raise ValueError(f"Unknown object type: {obj_type}")
        
        return method(obj_data, folder)
    
    def _delete_object(self, obj_type: str, obj_id: str) -> Dict[str, Any]:
        """
        Delete an object using the appropriate API method.
        
        Args:
            obj_type: Object type
            obj_id: Object ID
            
        Returns:
            API response
        """
        type_to_method = {
            'address_objects': self.api_client.delete_address,
            'address_groups': self.api_client.delete_address_group,
            'service_objects': self.api_client.delete_service,
            'service_groups': self.api_client.delete_service_group,
        }
        
        method = type_to_method.get(obj_type)
        if not method:
            raise ValueError(f"Unknown object type: {obj_type}")
        
        return method(obj_id)
    
    def _create_security_rule(self, rule_data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a security rule."""
        return self.api_client.create_security_rule(rule_data, folder)
    
    def _delete_security_rule(self, rule_id: str) -> Dict[str, Any]:
        """Delete a security rule."""
        return self.api_client.delete_security_rule(rule_id)
    
    def _create_profile(self, prof_type: str, prof_data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """
        Create a profile using the appropriate API method.
        
        Args:
            prof_type: Profile type (e.g., 'anti_spyware_profiles', 'decryption_profiles')
            prof_data: Profile data
            folder: Folder name
            
        Returns:
            API response
        """
        type_to_method = {
            'anti_spyware_profiles': self.api_client.create_anti_spyware_profile,
            'dns_security_profiles': self.api_client.create_dns_security_profile,
            'file_blocking_profiles': self.api_client.create_file_blocking_profile,
            'url_access_profiles': self.api_client.create_url_access_profile,
            'vulnerability_protection_profiles': self.api_client.create_vulnerability_protection_profile,
            'wildfire_anti_virus_profiles': self.api_client.create_wildfire_anti_virus_profile,
            'decryption_profiles': self.api_client.create_decryption_profile,
            'authentication_profiles': self.api_client.create_authentication_profile,
        }
        
        method = type_to_method.get(prof_type)
        if not method:
            raise ValueError(f"Unknown profile type: {prof_type}")
        
        return method(prof_data, folder)
    
    def _delete_profile(self, prof_type: str, prof_id: str) -> Dict[str, Any]:
        """
        Delete a profile using the appropriate API method.
        
        Args:
            prof_type: Profile type
            prof_id: Profile ID
            
        Returns:
            API response
        """
        type_to_method = {
            'anti_spyware_profiles': self.api_client.delete_anti_spyware_profile,
            'dns_security_profiles': self.api_client.delete_dns_security_profile,
            'file_blocking_profiles': self.api_client.delete_file_blocking_profile,
            'url_access_profiles': self.api_client.delete_url_access_profile,
            'vulnerability_protection_profiles': self.api_client.delete_vulnerability_protection_profile,
            'wildfire_anti_virus_profiles': self.api_client.delete_wildfire_anti_virus_profile,
            'decryption_profiles': self.api_client.delete_decryption_profile,
            'authentication_profiles': self.api_client.delete_authentication_profile,
        }
        
        method = type_to_method.get(prof_type)
        if not method:
            raise ValueError(f"Unknown profile type: {prof_type}")
        
        return method(prof_id)
    
    def _create_hip(self, hip_type: str, hip_data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """
        Create a HIP object or profile.
        
        Args:
            hip_type: HIP type ('hip_objects' or 'hip_profiles')
            hip_data: HIP data
            folder: Folder name
            
        Returns:
            API response
        """
        if hip_type == 'hip_objects':
            return self.api_client.create_hip_object(hip_data, folder)
        elif hip_type == 'hip_profiles':
            return self.api_client.create_hip_profile(hip_data, folder)
        else:
            raise ValueError(f"Unknown HIP type: {hip_type}")
    
    def _delete_hip(self, hip_type: str, hip_id: str) -> Dict[str, Any]:
        """
        Delete a HIP object or profile.
        
        Args:
            hip_type: HIP type
            hip_id: HIP ID
            
        Returns:
            API response
        """
        if hip_type == 'hip_objects':
            return self.api_client.delete_hip_object(hip_id)
        elif hip_type == 'hip_profiles':
            return self.api_client.delete_hip_profile(hip_id)
        else:
            raise ValueError(f"Unknown HIP type: {hip_type}")
    
    def _create_infrastructure(self, infra_type: str, infra_data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """
        Create an infrastructure item.
        
        Args:
            infra_type: Infrastructure type (e.g., 'remote_networks', 'ipsec_tunnels')
            infra_data: Infrastructure data
            folder: Folder name
            
        Returns:
            API response
        """
        type_to_method = {
            'remote_networks': self.api_client.create_remote_network,
            'service_connections': self.api_client.create_service_connection,
            'ipsec_tunnels': self.api_client.create_ipsec_tunnel,
            'ike_gateways': self.api_client.create_ike_gateway,
            'ike_crypto_profiles': self.api_client.create_ike_crypto_profile,
            'ipsec_crypto_profiles': self.api_client.create_ipsec_crypto_profile,
        }
        
        method = type_to_method.get(infra_type)
        if not method:
            raise ValueError(f"Unknown infrastructure type: {infra_type}")
        
        return method(infra_data, folder)
    
    def _delete_infrastructure_item(self, infra_type: str, infra_id: str) -> Dict[str, Any]:
        """
        Delete an infrastructure item.
        
        Args:
            infra_type: Infrastructure type
            infra_id: Infrastructure ID
            
        Returns:
            API response
        """
        type_to_method = {
            'remote_networks': self.api_client.delete_remote_network,
            'service_connections': self.api_client.delete_service_connection,
            'ipsec_tunnels': self.api_client.delete_ipsec_tunnel,
            'ike_gateways': self.api_client.delete_ike_gateway,
            'ike_crypto_profiles': self.api_client.delete_ike_crypto_profile,
            'ipsec_crypto_profiles': self.api_client.delete_ipsec_crypto_profile,
        }
        
        method = type_to_method.get(infra_type)
        if not method:
            raise ValueError(f"Unknown infrastructure type: {infra_type}")
        
        return method(infra_id)
    
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
                    dest_rules = destination_config['security_rules'].get(folder_name, {})
                    # dest_rules is a dict: {rule_name: rule_obj}
                    exists = rule_name in dest_rules
                
                if exists:
                    self._report_progress(
                        f"Deleting security_rule: {rule_name}",
                        current_item,
                        total_items
                    )
                    
                    # Get rule ID from destination config
                    try:
                        rule_id = dest_rules[rule_name].get('id')
                        if rule_id:
                            self._delete_security_rule(rule_id)
                            self._add_result(
                                'security_rule',
                                rule_name,
                                folder_name,
                                'deleted',
                                'success',
                                'Deleted successfully'
                            )
                        else:
                            self._add_result(
                                'security_rule',
                                rule_name,
                                folder_name,
                                'deleted',
                                'failed',
                                'Rule ID not found in destination config'
                            )
                    except Exception as e:
                        # Extract 409 reference details if available
                        error_msg = f'Failed to delete: {str(e)}'
                        if '409' in str(e):
                            ref_details = self._extract_409_references(e)
                            error_msg = f'Failed to delete (409 Conflict): {ref_details}'
                            logger.error(f"  security_rule: {rule_name} - {ref_details}")
                        
                        self._add_result(
                            'security_rule',
                            rule_name,
                            folder_name,
                            'deleted',
                            'failed',
                            error_msg,
                            error=e
                        )
                        # Track failed delete for Phase 2
                        self.failed_deletes[('security_rule', rule_name, folder_name)] = str(e)[:200]
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
                        
                        # Get HIP ID from destination config
                        try:
                            hip_id = dest_hip[hip_name].get('id')
                            if hip_id:
                                self._delete_hip(hip_type, hip_id)
                                self._add_result(
                                    hip_type,
                                    hip_name,
                                    folder_name,
                                    'deleted',
                                    'success',
                                    'Deleted successfully'
                                )
                            else:
                                self._add_result(
                                    hip_type,
                                    hip_name,
                                    folder_name,
                                    'deleted',
                                    'failed',
                                    'HIP ID not found in destination config'
                                )
                        except Exception as e:
                            self._add_result(
                                hip_type,
                                hip_name,
                                folder_name,
                                'deleted',
                                'failed',
                                f'Failed to delete: {str(e)}',
                                error=e
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
                        
                        # Get profile ID from destination config
                        try:
                            prof_id = dest_profiles[prof_name].get('id')
                            if prof_id:
                                self._delete_profile(prof_type, prof_id)
                                self._add_result(
                                    prof_type,
                                    prof_name,
                                    folder_name,
                                    'deleted',
                                    'success',
                                    'Deleted successfully'
                                )
                            else:
                                self._add_result(
                                    prof_type,
                                    prof_name,
                                    folder_name,
                                    'deleted',
                                    'failed',
                                    'Profile ID not found in destination config'
                                )
                        except Exception as e:
                            # Extract 409 reference details if available
                            error_msg = f'Failed to delete: {str(e)}'
                            if '409' in str(e):
                                ref_details = self._extract_409_references(e)
                                error_msg = f'Failed to delete (409 Conflict): {ref_details}'
                                logger.error(f"  {prof_type}: {prof_name} - {ref_details}")
                            
                            self._add_result(
                                prof_type,
                                prof_name,
                                folder_name,
                                'deleted',
                                'failed',
                                error_msg,
                                error=e
                            )
                            # Track failed delete for Phase 2 checking
                            self.failed_deletes[(prof_type, prof_name, folder_name)] = str(e)[:200]
                        current_item += 1
        
        return current_item
    
    def _delete_infrastructure(
        self,
        infrastructure: Dict[str, Any],
        destination_config: Optional[Dict[str, Any]],
        current_item: int,
        total_items: int
    ) -> int:
        """
        Delete existing infrastructure items (Phase 1 - OVERWRITE mode).
        
        CRITICAL: Infrastructure has internal dependencies and must be deleted
        in the correct order to avoid 409 Conflict errors:
        
        1. ipsec_tunnels (use: ike_gateways, ipsec_crypto_profiles)
        2. ike_gateways (use: ike_crypto_profiles)
        3. ike_crypto_profiles
        4. ipsec_crypto_profiles
        5. remote_networks
        6. service_connections
        7. mobile_users (gp_gateways, portals, agent_profiles - use auth profiles)
        8. bandwidth_allocations
        """
        # Define the correct delete order for infrastructure
        # Infrastructure dependency map  
        # Key: item type that failed, Value: list of types that DEPEND on it (should be skipped)
        # When X fails to delete, skip all items in infra_dependencies[X]
        infra_dependencies = {
            'service_connections': ['ipsec_tunnels', 'ike_gateways', 'ike_crypto_profiles', 'ipsec_crypto_profiles'],  # If SC fails, can't delete anything it references
            'ipsec_tunnels': ['ike_gateways', 'ike_crypto_profiles', 'ipsec_crypto_profiles'],  # If tunnel fails, can't delete what it references
            'ike_gateways': ['ike_crypto_profiles'],  # If gateway fails, can't delete the crypto it uses
            # Note: crypto profiles don't have dependencies (they're at the bottom)
        }
        
        # Track items that should be skipped due to dependency failures
        dependency_failed_items = set()  # {(item_type, item_name)}
        
        infra_delete_order = [
            # Delete from top-down: things that reference others FIRST
            'service_connections',   # FIRST! Service connections reference tunnels
            'ipsec_tunnels',         # Tunnels reference gateways and crypto profiles
            'ike_gateways',          # Gateways reference IKE crypto profiles
            'ike_crypto_profiles',   # Crypto profiles are referenced by gateways
            'ipsec_crypto_profiles', # Crypto profiles are referenced by tunnels
            'remote_networks',
            'gp_gateways',
            'gp_portals',
            'agent_profiles',
            'bandwidth_allocations',
        ]
        
        # Delete in the specified order
        for infra_type in infra_delete_order:
            if infra_type not in infrastructure:
                continue
            
            infra_list = infrastructure[infra_type]
            if not isinstance(infra_list, list):
                continue
            
            # Wrap entire type processing in try-except to prevent crashes
            try:
                for infra_item in infra_list:
                    try:
                        infra_name = infra_item.get('name', 'Unknown')
                        item_key = (infra_type, infra_name)
                        
                        # Check if this item should be skipped due to dependency failure
                        if item_key in dependency_failed_items:
                            # Track as failed delete so Phase 2 also skips it
                            self.failed_deletes[(infra_type, infra_name, 'Infrastructure')] = 'Skipped - dependency failed'
                            self._add_result(
                                infra_type,
                                infra_name,
                                'Infrastructure',
                                'skipped',
                                'success',
                                'Skipped - dependent item failed to delete'
                            )
                            current_item += 1
                            continue
                        
                        # Check if exists in destination
                        exists = False
                        if destination_config and 'infrastructure' in destination_config:
                            dest_infra = destination_config['infrastructure'].get(infra_type, [])
                            if isinstance(dest_infra, list):
                                exists = any(i.get('name') == infra_name for i in dest_infra)
                            elif isinstance(dest_infra, dict):
                                exists = infra_name in dest_infra
                        
                        if exists:
                            try:
                                self._report_progress(
                                    f"Deleting {infra_type}: {infra_name}",
                                    current_item,
                                    total_items
                                )
                            except:
                                pass  # Ignore progress callback errors
                            
                            # Get infrastructure ID from destination config
                            try:
                                if isinstance(dest_infra, list):
                                    # Find the item in the list
                                    infra_obj = next((i for i in dest_infra if i.get('name') == infra_name), None)
                                    infra_id = infra_obj.get('id') if infra_obj else None
                                elif isinstance(dest_infra, dict):
                                    infra_id = dest_infra[infra_name].get('id')
                                else:
                                    infra_id = None
                                
                                if infra_id:
                                    self._delete_infrastructure_item(infra_type, infra_id)
                                    self._add_result(
                                        infra_type,
                                        infra_name,
                                        'Infrastructure',
                                        'deleted',
                                        'success',
                                        'Deleted successfully'
                                    )
                                else:
                                    # Track failed delete
                                    self.failed_deletes[(infra_type, infra_name, 'Infrastructure')] = 'ID not found'
                                    self._add_result(
                                        infra_type,
                                        infra_name,
                                        'Infrastructure',
                                        'deleted',
                                        'failed',
                                        'Infrastructure ID not found in destination config'
                                    )
                                    # Mark all items that depend on this one for skipping
                                    for dep_type in infra_dependencies.get(infra_type, []):
                                        if dep_type in infrastructure:
                                            for dep_item in infrastructure[dep_type]:
                                                dep_name = dep_item.get('name', 'Unknown')
                                                dependency_failed_items.add((dep_type, dep_name))
                                                logger.info(f"  → Marking {dep_type}: {dep_name} to skip (depends on failed {infra_type})")
                            except Exception as e:
                                # Track failed delete
                                self.failed_deletes[(infra_type, infra_name, 'Infrastructure')] = str(e)[:200]
                                
                                # Extract 409 reference details if available
                                error_msg = f'Failed to delete: {str(e)[:200]}'
                                if '409' in str(e):
                                    ref_details = self._extract_409_references(e)
                                    error_msg = f'Failed to delete (409 Conflict): {ref_details}'
                                    logger.error(f"  {infra_type}: {infra_name} - {ref_details}")
                                
                                self._add_result(
                                    infra_type,
                                    infra_name,
                                    'Infrastructure',
                                    'deleted',
                                    'failed',
                                    error_msg,
                                    error=e
                                )
                                # Mark all items that depend on this one for skipping
                                for dep_type in infra_dependencies.get(infra_type, []):
                                    if dep_type in infrastructure:
                                        for dep_item in infrastructure[dep_type]:
                                            dep_name = dep_item.get('name', 'Unknown')
                                            dependency_failed_items.add((dep_type, dep_name))
                                            logger.info(f"  → Marking {dep_type}: {dep_name} to skip (depends on failed {infra_type})")
                        current_item += 1
                    except Exception as item_error:
                        logger.error(f"Error processing infrastructure item: {str(item_error)[:200]}")
                        current_item += 1
                        continue
            except Exception as type_error:
                logger.error(f"Error processing infrastructure type {infra_type}: {str(type_error)[:200]}")
                continue
        
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
                    
                    # Get object ID from destination config
                    try:
                        obj_id = dest_objects[obj_name].get('id')
                        if obj_id:
                            self._delete_object(obj_type, obj_id)
                            self._add_result(
                                obj_type,
                                obj_name,
                                folder_name,
                                'deleted',
                                'success',
                                'Deleted successfully'
                            )
                        else:
                            # Track failed delete
                            self.failed_deletes[(obj_type, obj_name, folder_name)] = 'ID not found'
                            self._add_result(
                                obj_type,
                                obj_name,
                                folder_name,
                                'deleted',
                                'failed',
                                'Object ID not found in destination config'
                            )
                    except Exception as e:
                        # Track failed delete
                        self.failed_deletes[(obj_type, obj_name, folder_name)] = str(e)[:200]
                        
                        # Extract 409 reference details if available
                        error_msg = f'Failed to delete: {str(e)}'
                        if '409' in str(e):
                            ref_details = self._extract_409_references(e)
                            error_msg = f'Failed to delete (409 Conflict): {ref_details}'
                            logger.error(f"  {obj_type}: {obj_name} - {ref_details}")
                        
                        self._add_result(
                            obj_type,
                            obj_name,
                            folder_name,
                            'deleted',
                            'failed',
                            error_msg,
                            error=e
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
                # Folder exists - skip silently (folders are containers, not items to push/count)
                pass
            else:
                # Folder doesn't exist - would need to be created
                # TODO: Implement folder creation API call
                # For now, skip silently - folders are created automatically when items are added
                pass
            
            # Don't increment current_item or add results - folders are not counted as items
        
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
                    
                    # Check if this item failed to delete in Phase 1 (OVERWRITE mode)
                    if self._check_failed_delete(obj_type, obj_name, folder_name, current_item):
                        current_item += 1
                        continue
                    
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
                            
                            # Create renamed object
                            try:
                                # Update references to other renamed items BEFORE renaming this one
                                updated_obj = self._update_references_in_item(obj)
                                
                                renamed_obj = self._clean_item_for_api(updated_obj)
                                renamed_obj['name'] = new_name
                                
                                result = self._create_object(obj_type, renamed_obj, folder_name)
                                
                                self._add_result(
                                    obj_type,
                                    new_name,
                                    folder_name,
                                    'renamed',
                                    'success',
                                    f'Created as {new_name}'
                                )
                            except Exception as e:
                                self._add_result(
                                    obj_type,
                                    new_name,
                                    folder_name,
                                    'renamed',
                                    'failed',
                                    f'Failed to create: {str(e)}',
                                    error=e
                                )
                    else:
                        # Create new (or recreate after delete in OVERWRITE mode)
                        try:
                            cleaned_obj = self._clean_item_for_api(obj)
                            result = self._create_object(obj_type, cleaned_obj, folder_name)
                            
                            self._add_result(
                                obj_type,
                                obj_name,
                                folder_name,
                                'created',
                                'success',
                                'Created successfully'
                            )
                        except Exception as e:
                            # Check if this is an "already exists" error
                            if self._is_already_exists_error(e):
                                logger.warning(f"Item already exists (delete may have failed): {obj_name}")
                                self._add_result(
                                    obj_type,
                                    obj_name,
                                    folder_name,
                                    'skipped',
                                    'success',
                                    'Already exists (could not delete in Phase 1)'
                                )
                            else:
                                self._add_result(
                                    obj_type,
                                    obj_name,
                                    folder_name,
                                    'created',
                                    'failed',
                                    f'Failed to create: {str(e)}',
                                    error=e
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
                            
                            try:
                                renamed_prof = self._clean_item_for_api(prof)
                                renamed_prof['name'] = new_name
                                
                                result = self._create_profile(prof_type, renamed_prof, folder_name)
                                
                                self._add_result(
                                    prof_type,
                                    new_name,
                                    folder_name,
                                    'renamed',
                                    'success',
                                    f'Created as {new_name}'
                                )
                            except Exception as e:
                                self._add_result(
                                    prof_type,
                                    new_name,
                                    folder_name,
                                    'renamed',
                                    'failed',
                                    f'Failed to create: {str(e)}',
                                    error=e
                                )
                    else:
                        # Create new (or recreate after delete in OVERWRITE mode)
                        try:
                            cleaned_prof = self._clean_item_for_api(prof)
                            result = self._create_profile(prof_type, cleaned_prof, folder_name)
                            
                            self._add_result(
                                prof_type,
                                prof_name,
                                folder_name,
                                'created',
                                'success',
                                'Created successfully'
                            )
                        except Exception as e:
                            # Check if this is an "already exists" error
                            if self._is_already_exists_error(e):
                                logger.warning(f"Item already exists (delete may have failed): {prof_name}")
                                self._add_result(
                                    prof_type,
                                    prof_name,
                                    folder_name,
                                    'skipped',
                                    'success',
                                    'Already exists (could not delete in Phase 1)'
                                )
                            else:
                                self._add_result(
                                    prof_type,
                                    prof_name,
                                    folder_name,
                                    'created',
                                    'failed',
                                    f'Failed to create: {str(e)}',
                                    error=e
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
                            
                            try:
                                renamed_hip = self._clean_item_for_api(hip_item)
                                renamed_hip['name'] = new_name
                                
                                result = self._create_hip(hip_type, renamed_hip, folder_name)
                                
                                self._add_result(
                                    hip_type,
                                    new_name,
                                    folder_name,
                                    'renamed',
                                    'success',
                                    f'Created as {new_name}'
                                )
                            except Exception as e:
                                self._add_result(
                                    hip_type,
                                    new_name,
                                    folder_name,
                                    'renamed',
                                    'failed',
                                    f'Failed to create: {str(e)}',
                                    error=e
                                )
                    else:
                        # Create new (or recreate after delete in OVERWRITE mode)
                        try:
                            cleaned_hip = self._clean_item_for_api(hip_item)
                            result = self._create_hip(hip_type, cleaned_hip, folder_name)
                            
                            self._add_result(
                                hip_type,
                                hip_name,
                                folder_name,
                                'created',
                                'success',
                                'Created successfully'
                            )
                        except Exception as e:
                            # Check if this is an "already exists" error
                            if self._is_already_exists_error(e):
                                logger.warning(f"Item already exists (delete may have failed): {hip_name}")
                                self._add_result(
                                    hip_type,
                                    hip_name,
                                    folder_name,
                                    'skipped',
                                    'success',
                                    'Already exists (could not delete in Phase 1)'
                                )
                            else:
                                self._add_result(
                                    hip_type,
                                    hip_name,
                                    folder_name,
                                    'created',
                                    'failed',
                                    f'Failed to create: {str(e)}',
                                    error=e
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
        """
        Push infrastructure items.
        
        CRITICAL: Infrastructure has internal dependencies and must be created
        in the correct order (reverse of delete order):
        
        1. bandwidth_allocations
        2. mobile_users (agent_profiles, gp_portals, gp_gateways)
        3. service_connections
        4. remote_networks
        5. ipsec_crypto_profiles
        6. ike_crypto_profiles
        7. ike_gateways (use: ike_crypto_profiles)
        8. ipsec_tunnels (use: ike_gateways, ipsec_crypto_profiles)
        """
        # Define the correct create order for infrastructure (reverse of delete)
        infra_create_order = [
            # This should be the EXACT REVERSE of infra_delete_order
            # Create from bottom-up: dependencies first, then things that depend on them
            'bandwidth_allocations',
            'agent_profiles',
            'gp_portals',
            'gp_gateways',
            'remote_networks',
            'ipsec_crypto_profiles',   # Create crypto profiles BEFORE gateways/tunnels
            'ike_crypto_profiles',      # Create IKE crypto BEFORE IKE gateways
            'ike_gateways',             # Create gateways BEFORE tunnels
            'ipsec_tunnels',            # Create tunnels BEFORE service connections
            'service_connections',       # LAST! Service connections reference tunnels
        ]
        
        # Create in the specified order
        for infra_type in infra_create_order:
            if infra_type not in infrastructure:
                continue
            
            infra_list = infrastructure[infra_type]
            if not isinstance(infra_list, list):
                continue
            
            for item in infra_list:
                item_name = item.get('name', item.get('id', 'Unknown'))
                
                # Map infrastructure types to their required folders
                # Some infra types have specific folder requirements
                folder_map = {
                    'service_connections': 'Service Connections',
                    'remote_networks': 'Remote Networks',
                    'ipsec_tunnels': 'Service Connections',  # IPsec tunnels go in Service Connections folder
                    'ike_gateways': 'Service Connections',
                    'ike_crypto_profiles': 'Service Connections',
                    'ipsec_crypto_profiles': 'Service Connections',
                }
                
                # Use the item's folder if present, otherwise use the default for this type
                folder_name = item.get('folder') or folder_map.get(infra_type, 'Service Connections')
                
                self._report_progress(
                    f"Pushing {infra_type}: {item_name}",
                    current_item,
                    total_items
                )
                
                # Check if this item failed to delete in Phase 1 (OVERWRITE mode)
                if self._check_failed_delete(infra_type, item_name, folder_name, current_item):
                    current_item += 1
                    continue
                
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
                        
                        try:
                            # Update references to other renamed items BEFORE renaming this one
                            updated_item = self._update_references_in_item(item)
                            
                            renamed_item = self._clean_item_for_api(updated_item)
                            renamed_item['name'] = new_name
                            
                            result = self._create_infrastructure(infra_type, renamed_item, folder_name)
                            
                            self._add_result(
                                infra_type,
                                new_name,
                                folder_name,
                                'renamed',
                                'success',
                                f'Created as {new_name}'
                            )
                        except Exception as e:
                            self._add_result(
                                infra_type,
                                new_name,
                                folder_name,
                                'renamed',
                                'failed',
                                f'Failed to create: {str(e)}',
                                error=e
                            )
                else:
                    # Create new (or recreate after delete in OVERWRITE mode)
                    try:
                        cleaned_item = self._clean_item_for_api(item)
                        result = self._create_infrastructure(infra_type, cleaned_item, folder_name)
                        
                        self._add_result(
                            infra_type,
                            item_name,
                            folder_name,
                            'created',
                            'success',
                            'Created successfully'
                        )
                    except Exception as e:
                        # Check if this is an "already exists" error
                        # This can happen in OVERWRITE mode if delete failed
                        if self._is_already_exists_error(e):
                            logger.warning(f"Item already exists (delete may have failed): {item_name}")
                            self._add_result(
                                infra_type,
                                item_name,
                                folder_name,
                                'skipped',
                                'success',
                                'Already exists (could not delete in Phase 1)'
                            )
                        else:
                            self._add_result(
                                infra_type,
                                item_name,
                                folder_name,
                                'created',
                                'failed',
                                f'Failed to create: {str(e)}',
                                error=e
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
                        dest_rules = destination_config['security_rules'].get(folder_name, {})
                        # dest_rules is a dict: {rule_name: rule_obj}
                        exists = rule_name in dest_rules
                
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
                        
                        # Create renamed rule with updated references
                        try:
                            renamed_rule = self._clean_item_for_api(updated_rule)
                            renamed_rule['name'] = new_name
                            
                            result = self._create_security_rule(renamed_rule, folder_name)
                            
                            self._add_result(
                                'security_rule',
                                new_name,
                                folder_name,
                                'renamed',
                                'success',
                                f'Created as {new_name}'
                            )
                        except Exception as e:
                            self._add_result(
                                'security_rule',
                                new_name,
                                folder_name,
                                'renamed',
                                'failed',
                                f'Failed to create: {str(e)}',
                                error=e
                            )
                else:
                    # Create new (or recreate after delete in OVERWRITE mode)
                    try:
                        cleaned_rule = self._clean_item_for_api(updated_rule)
                        result = self._create_security_rule(cleaned_rule, folder_name)
                        
                        self._add_result(
                            'security_rule',
                            rule_name,
                            folder_name,
                            'created',
                            'success',
                            'Created successfully'
                        )
                    except Exception as e:
                        # Check if this is an "already exists" error
                        if self._is_already_exists_error(e):
                            logger.warning(f"Item already exists (delete may have failed): {rule_name}")
                            self._add_result(
                                'security_rule',
                                rule_name,
                                folder_name,
                                'skipped',
                                'success',
                                'Already exists (could not delete in Phase 1)'
                            )
                        else:
                            self._add_result(
                                'security_rule',
                                rule_name,
                                folder_name,
                                'created',
                                'failed',
                                f'Failed to create: {str(e)}',
                                error=e
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
