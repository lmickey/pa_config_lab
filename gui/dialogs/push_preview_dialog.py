"""
Push preview dialog for reviewing changes before push.

This dialog fetches destination configurations and shows real conflicts
and new items that will be pushed.
"""

import logging
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QLabel,
    QDialogButtonBox,
    QTabWidget,
    QWidget,
    QTextEdit,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Get logger for validation messages
logger = logging.getLogger(__name__)


class ConfigFetchWorker(QThread):
    """Worker thread to fetch destination configurations."""
    
    progress = pyqtSignal(str, int)  # message, percentage
    detail = pyqtSignal(str)  # detailed log message for results panel
    finished = pyqtSignal(object)  # destination_config
    error = pyqtSignal(str)  # error message
    
    # Folders that should be skipped during validation (system/blocked folders)
    SKIP_FOLDERS = {
        'colo connect', 'colo-connect',
        'service connections', 'service-connections',
        'ngfw-shared',
        'remote networks', 'remote-networks',
    }
    
    def _should_skip_folder(self, folder_name: str) -> bool:
        """Check if a folder should be skipped during validation."""
        if not folder_name:
            return True
        return folder_name.lower() in self.SKIP_FOLDERS
    
    def __init__(self, api_client, selected_items):
        super().__init__()
        self.api_client = api_client
        self.selected_items = selected_items
    
    def _count_validation_steps(self) -> tuple:
        """
        Count total validation steps for progress bar.

        Counts all emit_progress calls that will be made during validation.

        Returns:
            tuple: (total_steps, step_descriptions)
        """
        steps = []

        folders = self.selected_items.get('folders', [])
        snippets = self.selected_items.get('snippets', [])

        # Check if ALL items are going to new snippets
        all_items_to_new_snippets = True

        for snippet in snippets:
            dest_info = snippet.get('_destination', {})
            if not dest_info.get('is_new_snippet') and not dest_info.get('is_rename_snippet'):
                all_items_to_new_snippets = False
                break

        if all_items_to_new_snippets:
            for folder in folders:
                dest_info = folder.get('_destination', {})
                if not dest_info.get('is_new_snippet') and not dest_info.get('is_rename_snippet'):
                    all_items_to_new_snippets = False
                    break

        # If no folders or snippets, can't be "all to new snippets"
        if not folders and not snippets:
            all_items_to_new_snippets = False

        # Step 1: Folders list fetch
        if folders and not all_items_to_new_snippets:
            needs_folders = any(
                not f.get('_destination', {}).get('is_new_snippet') and
                not f.get('_destination', {}).get('is_rename_snippet')
                for f in folders
            )
            if needs_folders:
                steps.append("Fetching destination folders")

        # Step 2: Snippets list fetch
        if snippets or self._has_new_snippets():
            steps.append("Fetching destination snippets")

        # Step 3: Object types - one step per unique object type
        obj_types = set()
        for folder in folders:
            for obj_type in folder.get('objects', {}).keys():
                obj_types.add(obj_type)
        for snippet in snippets:
            for obj_type in snippet.get('objects', {}).keys():
                obj_types.add(obj_type)
        for obj_type in obj_types:
            steps.append(f"Checking {obj_type} objects")

        # Step 4: Infrastructure types - one step per infrastructure type
        infra = self.selected_items.get('infrastructure', {})
        for infra_type in infra.keys():
            if infra.get(infra_type):
                steps.append(f"Checking {infra_type} infrastructure")

        # Step 5: Profile types - one step per unique profile type
        profile_types = set()
        for folder in folders:
            for profile_type in folder.get('profiles', {}).keys():
                profile_types.add(profile_type)
        for snippet in snippets:
            for profile_type in snippet.get('profiles', {}).keys():
                profile_types.add(profile_type)
        for profile_type in profile_types:
            steps.append(f"Checking {profile_type} profiles")

        # Step 6: HIP items - one step if any HIP items exist
        has_hip = False
        for folder in folders:
            if folder.get('hip'):
                has_hip = True
                break
        if not has_hip:
            for snippet in snippets:
                if snippet.get('hip'):
                    has_hip = True
                    break
        if has_hip:
            steps.append("Checking HIP objects and profiles")

        # Step 7: Security rules - one step if any rules exist
        has_rules = any(f.get('security_rules') for f in folders) or \
                   any(s.get('security_rules') for s in snippets)
        if has_rules:
            steps.append("Fetching all security rules (global uniqueness check)")

        # Step 8: Reference dependencies - always check if we have any items
        if folders or snippets:
            steps.append("Reference Dependencies check")

        return len(steps) if steps else 1, steps
    
    def _has_new_snippets(self) -> bool:
        """Check if any items are going to new snippets."""
        for snippet in self.selected_items.get('snippets', []):
            dest_info = snippet.get('_destination', {})
            if dest_info.get('is_new_snippet') or dest_info.get('is_rename_snippet'):
                return True
        for folder in self.selected_items.get('folders', []):
            dest_info = folder.get('_destination', {})
            if dest_info.get('is_new_snippet') or dest_info.get('is_rename_snippet'):
                return True
        return False
    
    def run(self):
        """Fetch configurations from destination tenant."""
        try:
            # DISABLED: print(f"\n=== ConfigFetchWorker.run() starting ===")
            # DISABLED: print(f"API Client: {self.api_client}")
            # DISABLED: print(f"Selected items keys: {list(self.selected_items.keys())}")
            for key, value in self.selected_items.items():
                if isinstance(value, dict):
                    pass
                    # DISABLED-THREAD: print(f"  {key}: {list(value.keys())} ({sum(len(v) for v in value.values() if isinstance(v, list))} items)")
                elif isinstance(value, list):
                    # DISABLED-THREAD: print(f"  {key}: {len(value)} items")
                    # Show folder details
                    if key == 'folders' and len(value) > 0:
                        for folder in value[:2]:  # Show first 2 folders
                            # DISABLED-THREAD: print(f"    Folder: {folder.get('name')}")
                            if 'objects' in folder:
                                pass
                                # DISABLED-THREAD: print(f"      objects: {list(folder.get('objects', {}).keys())}")
                            if 'security_rules' in folder:
                                pass
                                # DISABLED-THREAD: print(f"      security_rules: {len(folder.get('security_rules', []))} items")
                            if 'profiles' in folder:
                                pass
                                # DISABLED-THREAD: print(f"      profiles: {list(folder.get('profiles', {}).keys())}")
                            if 'hip' in folder:
                                pass
                                # DISABLED-THREAD: print(f"      hip: {list(folder.get('hip', {}).keys())}")
                else:
                    pass
                    # DISABLED-THREAD: print(f"  {key}: {value}")
            
            dest_config = {
                'folders': {},
                'snippets': {},
                'objects': {},
                'infrastructure': {},
                'all_rule_names': {},  # Global rule name tracking
                'new_snippets': set(),  # Track snippets being created
            }
            
            # Count steps for accurate progress
            total_steps, step_descriptions = self._count_validation_steps()
            current_step = 0
            
            def emit_progress(message: str, detail: str = None):
                """Emit progress update with optional detail message."""
                nonlocal current_step
                current_step += 1
                percentage = int((current_step / max(total_steps, 1)) * 100)
                self.progress.emit(f"[{percentage}%] {message}", min(percentage, 99))
                # Log to activity log
                logger.normal(f"[Validation] {message}")
                if detail:
                    self.detail.emit(detail)
                    if detail.strip():  # Don't log empty lines
                        logger.normal(f"[Validation] {detail}")
            
            def emit_detail(message: str, level: str = "normal"):
                """Emit detail message only (no progress increment).
                
                Args:
                    message: The message to emit
                    level: Log level - "normal", "warning", or "error"
                """
                self.detail.emit(message)
                # Log to activity log (skip separator lines and empty lines)
                if message.strip() and not message.startswith("="):
                    if level == "warning":
                        logger.warning(f"[Validation] {message}")
                    elif level == "error":
                        logger.error(f"[Validation] {message}")
                    else:
                        logger.normal(f"[Validation] {message}")
            
            # Log start
            emit_detail("=" * 60)
            emit_detail("VALIDATION STARTED")
            emit_detail("=" * 60)
            emit_detail("")
            
            # Analyze selection to determine what validation is needed
            folders = self.selected_items.get('folders', [])
            snippets = self.selected_items.get('snippets', [])
            
            # Identify new snippets being created (for validation skip logic)
            new_snippet_names = []
            all_items_to_new_snippets = True  # Track if ALL items go to new snippets
            
            for snippet in snippets:
                dest_info = snippet.get('_destination', {})
                if dest_info.get('is_new_snippet') or dest_info.get('is_rename_snippet'):
                    new_name = dest_info.get('new_snippet_name', '')
                    if new_name:
                        dest_config['new_snippets'].add(new_name)
                        new_snippet_names.append(new_name)
                else:
                    # This snippet is NOT going to a new snippet
                    all_items_to_new_snippets = False
            
            # Also check folders for new snippet destinations
            for folder in folders:
                dest_info = folder.get('_destination', {})
                if dest_info.get('is_new_snippet') or dest_info.get('is_rename_snippet'):
                    new_name = dest_info.get('new_snippet_name', '')
                    if new_name and new_name not in dest_config['new_snippets']:
                        dest_config['new_snippets'].add(new_name)
                        new_snippet_names.append(new_name)
                else:
                    # This folder is NOT going to a new snippet
                    all_items_to_new_snippets = False
            
            # If no folders or snippets selected, nothing to validate
            if not folders and not snippets:
                all_items_to_new_snippets = False
            
            if new_snippet_names:
                emit_detail(f"📝 New snippets to create: {', '.join(new_snippet_names)}")
                if all_items_to_new_snippets:
                    emit_detail(f"   ✓ All items destined for new snippets - minimal validation needed")
                emit_detail("")
            
            # Determine if we need folder validation
            # Only fetch folders if we have folder items that are NOT going to new snippets
            needs_folder_validation = False
            for folder in folders:
                dest_info = folder.get('_destination', {})
                if not dest_info.get('is_new_snippet') and not dest_info.get('is_rename_snippet'):
                    needs_folder_validation = True
                    break
            
            if needs_folder_validation:
                emit_progress("Folders - Fetching destination folder list", 
                             f"📁 Fetching folders from destination tenant...")
                try:
                    existing_folders = self.api_client.get_security_policy_folders()
                    folder_names = [f.get('name', '') for f in existing_folders if f.get('name')]
                    emit_detail(f"   Found {len(folder_names)} folders in destination")
                    
                    for folder in existing_folders:
                        folder_name = folder.get('name')
                        if folder_name:
                            dest_config['folders'][folder_name] = folder
                    
                except Exception as e:
                    emit_detail(f"   ⚠️ Error fetching folders: {e}", level="warning")
            elif folders:
                emit_detail(f"📁 Skipping folder list fetch - all folder items going to new snippets")
                emit_detail("")
            
            # Fetch snippets - ALWAYS fetch if we have snippet items or new snippets to create
            # This is needed to check for name conflicts
            if snippets or new_snippet_names:
                emit_progress("Snippets - Fetching destination snippet list",
                             f"📄 Fetching snippets from destination tenant...")
                try:
                    existing_snippets = self.api_client.get_security_policy_snippets()
                    
                    # Count custom vs system snippets
                    custom_count = 0
                    for snippet in existing_snippets:
                        snippet_name = snippet.get('name')
                        snippet_type = snippet.get('type', '')
                        if snippet_name:
                            dest_config['snippets'][snippet_name] = snippet
                            if snippet_type not in ('predefined', 'readonly'):
                                custom_count += 1
                    
                    emit_detail(f"   Found {len(existing_snippets)} snippets ({custom_count} custom)")
                    
                    # Check which of our new snippet names conflict
                    for new_name in new_snippet_names:
                        if new_name in dest_config['snippets']:
                            emit_detail(f"   ⚠️  '{new_name}' already exists - will use conflict strategy", level="warning")
                        else:
                            emit_detail(f"   ✓ '{new_name}' - name available, will be created")
                    
                    # Check snippet items that are NOT going to new snippets
                    # Show what DESTINATION snippets will be updated
                    destination_snippet_names = set()
                    for snippet in snippets:
                        dest_info = snippet.get('_destination', {})
                        is_new = dest_info.get('is_new_snippet') or dest_info.get('is_rename_snippet')
                        if not is_new:
                            # Get the destination snippet name (from _destination.folder or source name)
                            dest_folder = dest_info.get('folder', '')
                            source_name = snippet.get('name', '')
                            # Use destination folder if set, otherwise use source name (inherit case)
                            dest_snippet_name = dest_folder if dest_folder else source_name
                            destination_snippet_names.add(dest_snippet_name)
                    
                    # Also check individual items for their destinations
                    for snippet in snippets:
                        snippet_objects = snippet.get('objects', {})
                        for obj_type, obj_list in snippet_objects.items():
                            if isinstance(obj_list, list):
                                for obj in obj_list:
                                    if isinstance(obj, dict):
                                        obj_dest = obj.get('_destination', {})
                                        obj_dest_folder = obj_dest.get('folder', '')
                                        if obj_dest_folder and obj_dest.get('is_existing_snippet'):
                                            destination_snippet_names.add(obj_dest_folder)
                    
                    # Report destination snippets
                    for dest_name in destination_snippet_names:
                        if dest_name in dest_config['snippets']:
                            emit_detail(f"   • Destination '{dest_name}' exists - will update")
                        else:
                            emit_detail(f"   + Destination '{dest_name}' not found - will be created")
                    
                    emit_detail("")
                except Exception as e:
                    emit_detail(f"   ❌ Error fetching snippets: {e}", level="error")
            
            # Skip object validation if ALL items are going to new snippets
            # (no conflicts possible in a new snippet)
            if all_items_to_new_snippets:
                emit_detail("📦 Skipping object conflict checks - all items going to new snippets")
                emit_detail("")
            else:
                # Fetch objects (both top-level and from folders)
                objects = self.selected_items.get('objects', {})
                
                # Also collect object types and DESTINATION folders/snippets from selections
                # IMPORTANT: Use the DESTINATION location, not the source location
                object_folders = {}  # Track which destination folders to check
                object_snippets = {}  # Track which destination snippets to check
                
                for folder in folders:
                    folder_name = folder.get('name')
                    dest_info = folder.get('_destination', {})
                    
                    # Skip if this folder is going to a new snippet (no conflicts possible)
                    if dest_info.get('is_new_snippet') or dest_info.get('is_rename_snippet'):
                        continue
                    
                    # Determine the actual destination - could be folder, existing snippet, or inherit
                    dest_location = dest_info.get('folder', folder_name)  # Default to source folder name
                    is_existing_snippet = dest_info.get('is_existing_snippet', False)
                    
                    # Also check if destination folder name is in the existing snippets list
                    if not is_existing_snippet and dest_location in dest_config.get('snippets', {}):
                        is_existing_snippet = True
                    
                    folder_objects = folder.get('objects', {})
                    for obj_type, obj_list in folder_objects.items():
                        if obj_type not in objects:
                            objects[obj_type] = []

                        # Check EACH object's destination (may override container)
                        if isinstance(obj_list, list):
                            for obj in obj_list:
                                if not isinstance(obj, dict):
                                    continue
                                obj_dest_info = obj.get('_destination', {})

                                # Skip if this item goes to a new snippet
                                if obj_dest_info.get('is_new_snippet') or obj_dest_info.get('is_rename_snippet'):
                                    continue

                                # Get item's destination (or fall back to container)
                                obj_dest_folder = obj_dest_info.get('folder', '')
                                obj_is_existing_snippet = obj_dest_info.get('is_existing_snippet', False)

                                # Determine actual destination to check
                                if obj_dest_folder:
                                    # Item has its own destination
                                    dest_to_check = obj_dest_folder
                                    # Check if it's an existing snippet
                                    if not obj_is_existing_snippet and dest_to_check in dest_config.get('snippets', {}):
                                        obj_is_existing_snippet = True
                                else:
                                    # Fall back to container destination
                                    dest_to_check = dest_location
                                    obj_is_existing_snippet = is_existing_snippet

                                if dest_to_check:
                                    if obj_is_existing_snippet:
                                        # Destination is an existing snippet
                                        if obj_type not in object_snippets:
                                            object_snippets[obj_type] = set()
                                        object_snippets[obj_type].add(dest_to_check)
                                    else:
                                        # Destination is a folder
                                        if obj_type not in object_folders:
                                            object_folders[obj_type] = set()
                                        object_folders[obj_type].add(dest_to_check)
                
                for snippet in snippets:
                    snippet_name = snippet.get('name')
                    container_dest_info = snippet.get('_destination', {})
                    
                    # Skip if this snippet container is going to a new snippet (no conflicts possible)
                    if container_dest_info.get('is_new_snippet') or container_dest_info.get('is_rename_snippet'):
                        continue
                    
                    # Container-level destination (fallback)
                    container_dest_location = container_dest_info.get('folder') or snippet_name
                    container_is_existing_snippet = container_dest_info.get('is_existing_snippet', False)
                    if not container_is_existing_snippet and container_dest_location in dest_config.get('snippets', {}):
                        container_is_existing_snippet = True
                    
                    snippet_objects = snippet.get('objects', {})
                    for obj_type, obj_list in snippet_objects.items():
                        if obj_type not in objects:
                            objects[obj_type] = []
                        if obj_type not in object_snippets:
                            object_snippets[obj_type] = set()
                        
                        # Check EACH object's destination (may override container)
                        if isinstance(obj_list, list):
                            for obj in obj_list:
                                if not isinstance(obj, dict):
                                    continue
                                obj_dest_info = obj.get('_destination', {})
                                
                                # Skip if this item goes to a new snippet
                                if obj_dest_info.get('is_new_snippet') or obj_dest_info.get('is_rename_snippet'):
                                    continue
                                
                                # Get item's destination (or fall back to container)
                                obj_dest_folder = obj_dest_info.get('folder', '')
                                obj_is_existing_snippet = obj_dest_info.get('is_existing_snippet', False)
                                
                                # Determine actual destination to check
                                if obj_dest_folder:
                                    # Item has its own destination
                                    dest_to_check = obj_dest_folder
                                    # Check if it's an existing snippet
                                    if not obj_is_existing_snippet and dest_to_check in dest_config.get('snippets', {}):
                                        obj_is_existing_snippet = True
                                elif container_dest_location:
                                    # Fall back to container destination
                                    dest_to_check = container_dest_location
                                    obj_is_existing_snippet = container_is_existing_snippet
                                else:
                                    dest_to_check = snippet_name
                                
                                if dest_to_check:
                                    if obj_is_existing_snippet:
                                        object_snippets[obj_type].add(dest_to_check)
                                    else:
                                        # Destination is a folder, not a snippet
                                        if obj_type not in object_folders:
                                            object_folders[obj_type] = set()
                                        object_folders[obj_type].add(dest_to_check)
                
                if objects:
                    emit_detail("📦 Checking objects in destination...")
                    
                    # Map object types to API client methods
                    # Handle both singular and plural forms
                    object_method_map = {
                        'address_objects': 'get_all_addresses',
                        'address_object': 'get_all_addresses',
                        'address_groups': 'get_all_address_groups',
                        'address_group': 'get_all_address_groups',
                        'service_objects': 'get_all_services',
                        'service_object': 'get_all_services',
                        'service_groups': 'get_all_service_groups',
                        'service_group': 'get_all_service_groups',
                        'applications': 'get_all_applications',
                        'application': 'get_all_applications',
                        'application_groups': 'get_all_application_groups',
                        'application_group': 'get_all_application_groups',
                        'application_filters': 'get_all_application_filters',
                        'application_filter': 'get_all_application_filters',
                        'external_dynamic_lists': 'get_all_external_dynamic_lists',
                        'external_dynamic_list': 'get_all_external_dynamic_lists',
                        'fqdn_objects': 'get_all_fqdn_objects',
                        'fqdn_object': 'get_all_fqdn_objects',
                        'url_filtering_categories': 'get_all_url_categories',
                        'url_filtering_category': 'get_all_url_categories',
                        'url_category': 'get_all_url_categories',
                        # Security profiles (singular forms used in config models)
                        'wildfire_profile': 'get_all_wildfire_profiles',
                        'wildfire_profiles': 'get_all_wildfire_profiles',
                        'anti_spyware_profile': 'get_all_anti_spyware_profiles',
                        'vulnerability_profile': 'get_all_vulnerability_profiles',
                        'url_filtering_profile': 'get_all_url_access_profiles',
                        'file_blocking_profile': 'get_all_file_blocking_profiles',
                        'decryption_profile': 'get_all_decryption_profiles',
                        'dns_security_profile': 'get_all_dns_security_profiles',
                        'http_header_profile': 'get_all_http_header_profiles',
                        'certificate_profile': 'get_all_certificate_profiles',
                        # HIP profiles and objects
                        'hip_profile': 'get_all_hip_profiles',
                        'hip_object': 'get_all_hip_objects',
                        # Rules (authentication rules have global uniqueness like security rules)
                        'authentication_rule': 'get_all_authentication_rules',
                        'decryption_rule': 'get_all_decryption_rules',
                        # Schedules
                        'schedule': 'get_all_schedules',
                        # Tags
                        'tag': 'get_all_tags',
                    }
                    
                    # Friendly names for object types
                    type_display_names = {
                        'address_objects': 'Address Objects',
                        'address_object': 'Address Objects',
                        'address_groups': 'Address Groups',
                        'address_group': 'Address Groups',
                        'service_objects': 'Service Objects',
                        'service_object': 'Service Objects',
                        'service_groups': 'Service Groups',
                        'service_group': 'Service Groups',
                        'applications': 'Applications',
                        'application': 'Applications',
                        'application_groups': 'Application Groups',
                        'application_group': 'Application Groups',
                        'application_filters': 'Application Filters',
                        'application_filter': 'Application Filters',
                        'external_dynamic_lists': 'External Dynamic Lists',
                        'external_dynamic_list': 'External Dynamic Lists',
                        'fqdn_objects': 'FQDN Objects',
                        'fqdn_object': 'FQDN Objects',
                        'url_filtering_categories': 'URL Categories',
                        'url_filtering_category': 'URL Categories',
                        'url_category': 'URL Categories',
                        # Security profiles
                        'wildfire_profile': 'WildFire Profiles',
                        'wildfire_profiles': 'WildFire Profiles',
                        'anti_spyware_profile': 'Anti-Spyware Profiles',
                        'vulnerability_profile': 'Vulnerability Profiles',
                        'url_filtering_profile': 'URL Filtering Profiles',
                        'file_blocking_profile': 'File Blocking Profiles',
                        'decryption_profile': 'Decryption Profiles',
                        'dns_security_profile': 'DNS Security Profiles',
                        # HIP
                        'hip_profile': 'HIP Profiles',
                        'hip_object': 'HIP Objects',
                        # Rules
                        'authentication_rule': 'Authentication Rules',
                        'decryption_rule': 'Decryption Rules',
                        # Schedules
                        'schedule': 'Schedules',
                        # Tags
                        'tag': 'Tags',
                    }
                    
                    for obj_type, obj_list in objects.items():
                        if not isinstance(obj_list, list):
                            continue
                        
                        display_name = type_display_names.get(obj_type, obj_type)
                        method_name = object_method_map.get(obj_type)
                        
                        if method_name and hasattr(self.api_client, method_name):
                            emit_progress(f"Objects - Checking {display_name}",
                                         f"   Fetching {display_name}...")
                            try:
                                # Determine which folders/snippets to query for this object type
                                folders_to_check = object_folders.get(obj_type, set())
                                snippets_to_check = object_snippets.get(obj_type, set())
                                
                                # Fetch from each folder/snippet
                                all_existing_objects = []
                                method = getattr(self.api_client, method_name)
                                
                                if folders_to_check:
                                    for folder in folders_to_check:
                                        try:
                                            folder_objects = method(folder=folder)
                                            if isinstance(folder_objects, list):
                                                all_existing_objects.extend(folder_objects)
                                        except Exception:
                                            pass  # Silently skip folders that error
                                
                                if snippets_to_check:
                                    emit_detail(f"   Checking snippets: {list(snippets_to_check)}")
                                    for snippet_name in snippets_to_check:
                                        try:
                                            snippet_objects = method(snippet=snippet_name)
                                            if isinstance(snippet_objects, list):
                                                all_existing_objects.extend(snippet_objects)
                                                emit_detail(f"   Found {len(snippet_objects)} in snippet '{snippet_name}'")
                                                
                                                # ALSO store by snippet for snippet-scoped lookups
                                                if 'snippet_objects' not in dest_config:
                                                    dest_config['snippet_objects'] = {}
                                                if snippet_name not in dest_config['snippet_objects']:
                                                    dest_config['snippet_objects'][snippet_name] = {}
                                                if obj_type not in dest_config['snippet_objects'][snippet_name]:
                                                    dest_config['snippet_objects'][snippet_name][obj_type] = {}
                                                
                                                for obj in snippet_objects:
                                                    if isinstance(obj, dict) and obj.get('name'):
                                                        dest_config['snippet_objects'][snippet_name][obj_type][obj.get('name')] = obj
                                        except Exception as e:
                                            emit_detail(f"   Error checking snippet '{snippet_name}': {e}", level='warning')
                                
                                if not folders_to_check and not snippets_to_check:
                                    # No specific location, try without folder/snippet parameter
                                    all_existing_objects = method()
                                
                                existing_objects = all_existing_objects
                                
                                if not isinstance(existing_objects, list):
                                    existing_objects = []
                            
                                if obj_type not in dest_config['objects']:
                                    dest_config['objects'][obj_type] = {}
                                
                                for obj in existing_objects:
                                    if not isinstance(obj, dict):
                                        continue
                                    obj_name = obj.get('name')
                                    if obj_name:
                                        dest_config['objects'][obj_type][obj_name] = obj
                                
                                # Report what we found
                                found_count = len(dest_config['objects'][obj_type])
                                emit_detail(f"   Found {found_count} {display_name} in destination")
                                    
                            except AttributeError as e:
                                emit_detail(f"   ⚠️  Could not check {display_name}: API method not available", level="warning")
                            except TypeError as e:
                                emit_detail(f"   ⚠️  Could not check {display_name}: {e}", level="warning")
                            except Exception as e:
                                emit_detail(f"   ⚠️  Error checking {display_name}: {e}", level="warning")
                        else:
                            emit_detail(f"   ⚠️  No API method for {display_name}", level="warning")
                    
                    emit_detail("")
            
            # Fetch infrastructure components
            infrastructure = self.selected_items.get('infrastructure', {})
            if infrastructure:
                # Will emit per-type progress below
                
                # Map infrastructure types to API client methods
                infra_method_map = {
                    'remote_networks': 'get_all_remote_networks',
                    'service_connections': 'get_all_service_connections',
                    'ipsec_tunnels': 'get_all_ipsec_tunnels',
                    'ike_gateways': 'get_all_ike_gateways',
                    'ike_crypto_profiles': 'get_all_ike_crypto_profiles',
                    'ipsec_crypto_profiles': 'get_all_ipsec_crypto_profiles',
                    'agent_profiles': 'get_mobile_agent_profiles',  # Returns dict, not list
                }
                
                for infra_type, infra_list in infrastructure.items():
                    if not isinstance(infra_list, list):
                        # DISABLED-THREAD: print(f"  Skipping {infra_type} - not a list (type: {type(infra_list)})")
                        continue
                    
                    # DISABLED-THREAD: print(f"  Checking {infra_type}: {len(infra_list)} items")
                    method_name = infra_method_map.get(infra_type)
                    if method_name and hasattr(self.api_client, method_name):
                        try:
                            # Determine which folder(s) to query
                            # Infrastructure items typically belong to specific folders
                            folders_to_check = set()
                            for item in infra_list:
                                item_folder = item.get('folder')
                                if item_folder:
                                    folders_to_check.add(item_folder)
                            
                            # DISABLED-THREAD: print(f"    Folders to check: {list(folders_to_check) if folders_to_check else 'all'}")
                            
                            # Fetch from each folder (or all if no folder specified)
                            all_existing_items = []
                            method = getattr(self.api_client, method_name)
                            
                            if folders_to_check:
                                # Query each folder separately
                                for folder in folders_to_check:
                                    # DISABLED-THREAD: print(f"    Calling API method: {method_name}(folder='{folder}')")
                                    try:
                                        folder_items = method(folder=folder)
                                        # DISABLED-THREAD: print(f"      Response type: {type(folder_items)}")
                                        if isinstance(folder_items, list):
                                            all_existing_items.extend(folder_items)
                                        elif isinstance(folder_items, dict):
                                            # For dict responses (like agent_profiles), store as-is
                                            # We'll process it below
                                            all_existing_items = folder_items
                                            break  # Dict response, no need to continue
                                    except Exception as folder_err:
                                        pass
                                        # DISABLED-THREAD: print(f"      ERROR for folder '{folder}': {folder_err}")
                            else:
                                # No folder specified, try without folder parameter
                                # DISABLED-THREAD: print(f"    Calling API method: {method_name}()")
                                all_existing_items = method()
                            
                            existing_items = all_existing_items
                            
                            # Handle both list and dict responses
                            if isinstance(existing_items, dict):
                                # Some APIs return dict (e.g., agent_profiles)
                                # Extract the profiles list from the dict
                                # DISABLED-THREAD: print(f"    Response is dict with keys: {list(existing_items.keys())}")
                                
                                # Try to find a profiles list in the dict
                                if 'profiles' in existing_items:
                                    existing_items = existing_items['profiles']
                                    # DISABLED-THREAD: print(f"    Extracted 'profiles' list: {len(existing_items) if isinstance(existing_items, list) else 'not a list'}")
                                    if isinstance(existing_items, list) and len(existing_items) > 0:
                                        pass
                                        # DISABLED-THREAD: print(f"    First profile: {existing_items[0].get('name') if isinstance(existing_items[0], dict) else existing_items[0]}")
                                elif 'data' in existing_items:
                                    existing_items = existing_items['data']
                                    # DISABLED-THREAD: print(f"    Extracted 'data': {len(existing_items) if isinstance(existing_items, list) else 'not a list'}")
                                else:
                                    # Store the whole dict
                                    # DISABLED-THREAD: print(f"    Storing entire dict response")
                                    # DISABLED-THREAD: print(f"    Dict content sample: {str(existing_items)[:200]}")
                                    dest_config['infrastructure'][infra_type] = existing_items
                                    existing_items = []  # Skip item iteration below
                            
                            if not isinstance(existing_items, list):
                                # DISABLED-THREAD: print(f"    WARNING: Expected list, got {type(existing_items)}")
                                existing_items = []
                            
                            # DISABLED-THREAD: print(f"    Found {len(existing_items)} existing items")
                            
                            if infra_type not in dest_config['infrastructure']:
                                dest_config['infrastructure'][infra_type] = {}
                            
                            for item in existing_items:
                                if not isinstance(item, dict):
                                    # DISABLED-THREAD: print(f"      WARNING: Item is not a dict: {type(item)}")
                                    continue
                                item_name = item.get('name', item.get('id'))
                                if item_name:
                                    dest_config['infrastructure'][infra_type][item_name] = item
                                    if len(dest_config['infrastructure'][infra_type]) <= 5:  # Only print first 5
                                        pass
                                        # DISABLED-THREAD: print(f"      - {item_name}")
                            
                            if len(dest_config['infrastructure'][infra_type]) > 5:
                                pass
                                # DISABLED-THREAD: print(f"      ... and {len(dest_config['infrastructure'][infra_type]) - 5} more")
                                
                        except AttributeError as e:
                            pass
                            # DISABLED-THREAD: print(f"    ERROR: Method {method_name} not found: {e}")
                        except TypeError as e:
                            # DISABLED-THREAD: print(f"    ERROR: Type error calling {method_name}: {e}")
                            import traceback
                            # DISABLED-THREAD: traceback.print_exc()
                        except Exception as e:
                            # Continue even if fetch fails (endpoint might not be available)
                            # DISABLED-THREAD: print(f"    ERROR fetching {infra_type}: {type(e).__name__}: {e}")
                            import traceback
                            # DISABLED-THREAD: traceback.print_exc()
                    else:
                        pass
                    
                    emit_progress(f"Checking {infra_type} infrastructure...")
            
            # Fetch profiles from folders and snippets
            # Check per-item destinations to determine where to fetch from
            profile_folders = {}  # Track which folders to check for profile types
            profile_snippets = {}  # Track which snippets to check for profile types

            def add_profile_destination(prof_type, prof_item, container_dest_location, container_is_new_snippet, container_is_existing_snippet):
                """Helper to add profile destination based on per-item or container destination."""
                dest = prof_item.get('_destination', {}) if isinstance(prof_item, dict) else {}

                # Skip if item goes to a new snippet
                if dest.get('is_new_snippet') or dest.get('is_rename_snippet'):
                    return

                # Get item's destination (or fall back to container)
                item_dest_folder = dest.get('folder', '')
                item_is_existing_snippet = dest.get('is_existing_snippet', False)

                if item_dest_folder:
                    dest_to_check = item_dest_folder
                    if not item_is_existing_snippet and dest_to_check in dest_config.get('snippets', {}):
                        item_is_existing_snippet = True
                elif not container_is_new_snippet:
                    dest_to_check = container_dest_location
                    item_is_existing_snippet = container_is_existing_snippet
                else:
                    return  # Container is new snippet, skip

                if dest_to_check:
                    if item_is_existing_snippet:
                        if prof_type not in profile_snippets:
                            profile_snippets[prof_type] = set()
                        profile_snippets[prof_type].add(dest_to_check)
                    else:
                        if prof_type not in profile_folders:
                            profile_folders[prof_type] = set()
                        profile_folders[prof_type].add(dest_to_check)

            for folder in self.selected_items.get('folders', []):
                folder_name = folder.get('name')
                container_dest_info = folder.get('_destination', {})

                # Determine container destination
                container_is_new_snippet = container_dest_info.get('is_new_snippet') or container_dest_info.get('is_rename_snippet')
                container_dest_location = container_dest_info.get('folder', folder_name)
                container_is_existing_snippet = container_dest_info.get('is_existing_snippet', False)
                if not container_is_existing_snippet and container_dest_location in dest_config.get('snippets', {}):
                    container_is_existing_snippet = True

                folder_profiles = folder.get('profiles', {})
                for profile_type, profile_list in folder_profiles.items():
                    # Skip security_profiles container - it's not a real profile type
                    if profile_type == 'security_profiles':
                        # security_profiles is a container with sub-types
                        # Expand it into individual profile types
                        if isinstance(profile_list, dict):
                            for sub_type, sub_list in profile_list.items():
                                if isinstance(sub_list, list):
                                    for prof in sub_list:
                                        add_profile_destination(sub_type, prof, container_dest_location, container_is_new_snippet, container_is_existing_snippet)
                        continue

                    if isinstance(profile_list, list):
                        for prof in profile_list:
                            add_profile_destination(profile_type, prof, container_dest_location, container_is_new_snippet, container_is_existing_snippet)

            # Also check profiles in snippets
            for snippet in self.selected_items.get('snippets', []):
                snippet_name = snippet.get('name')
                container_dest_info = snippet.get('_destination', {})

                container_is_new_snippet = container_dest_info.get('is_new_snippet') or container_dest_info.get('is_rename_snippet')
                container_dest_location = container_dest_info.get('folder') or snippet_name
                container_is_existing_snippet = container_dest_info.get('is_existing_snippet', False)
                if not container_is_existing_snippet and container_dest_location in dest_config.get('snippets', {}):
                    container_is_existing_snippet = True

                snippet_profiles = snippet.get('profiles', {})
                for profile_type, profile_list in snippet_profiles.items():
                    if profile_type == 'security_profiles':
                        if isinstance(profile_list, dict):
                            for sub_type, sub_list in profile_list.items():
                                if isinstance(sub_list, list):
                                    for prof in sub_list:
                                        add_profile_destination(sub_type, prof, container_dest_location, container_is_new_snippet, container_is_existing_snippet)
                        continue

                    if isinstance(profile_list, list):
                        for prof in profile_list:
                            add_profile_destination(profile_type, prof, container_dest_location, container_is_new_snippet, container_is_existing_snippet)
            
            if profile_folders or profile_snippets:
                # Will emit per-type progress below
                # DISABLED-THREAD: print(f"  Profile types to check: {list(profile_folders.keys())}")

                # Map profile types to API methods
                profile_method_map = {
                    'authentication_profiles': 'get_all_authentication_profiles',
                    'decryption_profiles': 'get_all_decryption_profiles',
                    'anti_spyware_profiles': 'get_all_anti_spyware_profiles',
                    'dns_security_profiles': 'get_all_dns_security_profiles',
                    'file_blocking_profiles': 'get_all_file_blocking_profiles',
                    'url_access_profiles': 'get_all_url_access_profiles',
                    'vulnerability_profiles': 'get_all_vulnerability_profiles',
                    'wildfire_profiles': 'get_all_wildfire_profiles',
                    'http_header_profiles': 'get_all_http_header_profiles',
                    'certificate_profiles': 'get_all_certificate_profiles',
                    'profile_groups': 'get_all_profile_groups',
                    'security_profiles': None,  # Security profiles is a container, not a single type
                }

                if 'profiles' not in dest_config:
                    dest_config['profiles'] = {}

                all_profile_types = set(profile_folders.keys()) | set(profile_snippets.keys())
                for profile_type in all_profile_types:
                    folders_set = profile_folders.get(profile_type, set())
                    snippets_set = profile_snippets.get(profile_type, set())
                    method_name = profile_method_map.get(profile_type)

                    if method_name and hasattr(self.api_client, method_name):
                        try:
                            all_profiles = []
                            method = getattr(self.api_client, method_name)

                            # Fetch from folders
                            for folder in folders_set:
                                # DISABLED-THREAD: print(f"    Calling API method: {method_name}(folder='{folder}')")
                                try:
                                    folder_profiles = method(folder=folder)
                                    if isinstance(folder_profiles, list):
                                        all_profiles.extend(folder_profiles)
                                        # DISABLED-THREAD: print(f"      Found {len(folder_profiles)} items in folder '{folder}'")
                                except Exception as folder_err:
                                    pass
                                    # DISABLED-THREAD: print(f"      ERROR for folder '{folder}': {folder_err}")

                            # Fetch from snippets and store in snippet_objects
                            if snippets_set:
                                emit_detail(f"   Checking snippets for {profile_type}: {list(snippets_set)}")
                                for snippet_name in snippets_set:
                                    try:
                                        snippet_profiles = method(snippet=snippet_name)
                                        if isinstance(snippet_profiles, list):
                                            all_profiles.extend(snippet_profiles)
                                            emit_detail(f"   Found {len(snippet_profiles)} in snippet '{snippet_name}'")

                                            # Store in snippet_objects for snippet-scoped lookups
                                            if 'snippet_objects' not in dest_config:
                                                dest_config['snippet_objects'] = {}
                                            if snippet_name not in dest_config['snippet_objects']:
                                                dest_config['snippet_objects'][snippet_name] = {}
                                            if profile_type not in dest_config['snippet_objects'][snippet_name]:
                                                dest_config['snippet_objects'][snippet_name][profile_type] = {}

                                            for item in snippet_profiles:
                                                if isinstance(item, dict) and item.get('name'):
                                                    dest_config['snippet_objects'][snippet_name][profile_type][item.get('name')] = item
                                    except Exception as e:
                                        emit_detail(f"   Error checking snippet '{snippet_name}': {e}", level='warning')

                            if profile_type not in dest_config['profiles']:
                                dest_config['profiles'][profile_type] = {}

                            for profile in all_profiles:
                                if isinstance(profile, dict):
                                    profile_name = profile.get('name')
                                    if profile_name:
                                        dest_config['profiles'][profile_type][profile_name] = profile

                            # DISABLED-THREAD: print(f"    Total {profile_type}: {len(dest_config['profiles'][profile_type])} items")

                        except Exception as e:
                            # DISABLED-THREAD: print(f"    ERROR fetching {profile_type}: {type(e).__name__}: {e}")
                            import traceback
                            # DISABLED-THREAD: traceback.print_exc()
                    else:
                        pass

                    emit_progress(f"Checking {profile_type} profiles...")
            
            # Fetch HIP items from folders and snippets
            # Check per-item destinations to determine if we need to fetch from folders or snippets
            hip_folders = {}  # Track which folders to check for HIP types
            hip_snippets = {}  # Track which snippets to check for HIP types

            for folder in self.selected_items.get('folders', []):
                folder_name = folder.get('name')
                container_dest_info = folder.get('_destination', {})

                # Skip if container is going to a new snippet (no conflicts possible)
                container_is_new_snippet = container_dest_info.get('is_new_snippet') or container_dest_info.get('is_rename_snippet')
                container_dest_location = container_dest_info.get('folder', folder_name)
                container_is_existing_snippet = container_dest_info.get('is_existing_snippet', False)
                if not container_is_existing_snippet and container_dest_location in dest_config.get('snippets', {}):
                    container_is_existing_snippet = True

                folder_hip = folder.get('hip', {})
                for hip_type, hip_list in folder_hip.items():
                    if not isinstance(hip_list, list):
                        continue

                    for hip_item in hip_list:
                        dest = hip_item.get('_destination', {})

                        # Skip if item goes to a new snippet
                        if dest.get('is_new_snippet') or dest.get('is_rename_snippet'):
                            continue

                        # Get item's destination (or fall back to container)
                        item_dest_folder = dest.get('folder', '')
                        item_is_existing_snippet = dest.get('is_existing_snippet', False)

                        if item_dest_folder:
                            dest_to_check = item_dest_folder
                            if not item_is_existing_snippet and dest_to_check in dest_config.get('snippets', {}):
                                item_is_existing_snippet = True
                        elif not container_is_new_snippet:
                            dest_to_check = container_dest_location
                            item_is_existing_snippet = container_is_existing_snippet
                        else:
                            continue  # Container is new snippet, skip

                        if dest_to_check:
                            if item_is_existing_snippet:
                                if hip_type not in hip_snippets:
                                    hip_snippets[hip_type] = set()
                                hip_snippets[hip_type].add(dest_to_check)
                            else:
                                if hip_type not in hip_folders:
                                    hip_folders[hip_type] = set()
                                hip_folders[hip_type].add(dest_to_check)

            # Also track HIP items in snippets with per-item destinations
            for snippet in self.selected_items.get('snippets', []):
                snippet_name = snippet.get('name')
                container_dest_info = snippet.get('_destination', {})

                # Skip if container is going to a new snippet (no conflicts possible)
                container_is_new_snippet = container_dest_info.get('is_new_snippet') or container_dest_info.get('is_rename_snippet')
                container_dest_location = container_dest_info.get('folder') or snippet_name
                container_is_existing_snippet = container_dest_info.get('is_existing_snippet', False)
                if not container_is_existing_snippet and container_dest_location in dest_config.get('snippets', {}):
                    container_is_existing_snippet = True

                snippet_hip = snippet.get('hip', {})
                for hip_type, hip_list in snippet_hip.items():
                    if not isinstance(hip_list, list):
                        continue

                    for hip_item in hip_list:
                        dest = hip_item.get('_destination', {})

                        # Skip if item goes to a new snippet
                        if dest.get('is_new_snippet') or dest.get('is_rename_snippet'):
                            continue

                        # Get item's destination (or fall back to container)
                        item_dest_folder = dest.get('folder', '')
                        item_is_existing_snippet = dest.get('is_existing_snippet', False)

                        if item_dest_folder:
                            dest_to_check = item_dest_folder
                            if not item_is_existing_snippet and dest_to_check in dest_config.get('snippets', {}):
                                item_is_existing_snippet = True
                        elif not container_is_new_snippet:
                            dest_to_check = container_dest_location
                            item_is_existing_snippet = container_is_existing_snippet
                        else:
                            continue  # Container is new snippet, skip

                        if dest_to_check:
                            if item_is_existing_snippet:
                                if hip_type not in hip_snippets:
                                    hip_snippets[hip_type] = set()
                                hip_snippets[hip_type].add(dest_to_check)
                            else:
                                if hip_type not in hip_folders:
                                    hip_folders[hip_type] = set()
                                hip_folders[hip_type].add(dest_to_check)

            if hip_folders or hip_snippets:
                emit_progress("HIP - Checking HIP objects and profiles", "")
                emit_detail("🔒 Checking HIP objects and profiles...")

                if 'hip' not in dest_config:
                    dest_config['hip'] = {}

                # Map HIP types to API methods
                hip_method_map = {
                    'hip_profile': 'get_all_hip_profiles',
                    'hip_object': 'get_all_hip_objects',
                }

                all_hip_types = set(hip_folders.keys()) | set(hip_snippets.keys())
                for hip_type in all_hip_types:
                    folders_set = hip_folders.get(hip_type, set())
                    snippets_set = hip_snippets.get(hip_type, set())
                    method_name = hip_method_map.get(hip_type)
                    if method_name and hasattr(self.api_client, method_name):
                        try:
                            all_hip_items = []
                            method = getattr(self.api_client, method_name)

                            # Fetch from folders
                            for folder in folders_set:
                                try:
                                    folder_items = method(folder=folder)
                                    if isinstance(folder_items, list):
                                        all_hip_items.extend(folder_items)
                                except Exception:
                                    pass  # Silently skip folders that error

                            # Fetch from snippets and store in snippet_objects
                            if snippets_set:
                                emit_detail(f"   Checking snippets for {hip_type}: {list(snippets_set)}")
                                for snippet_name in snippets_set:
                                    try:
                                        snippet_items = method(snippet=snippet_name)
                                        if isinstance(snippet_items, list):
                                            all_hip_items.extend(snippet_items)
                                            emit_detail(f"   Found {len(snippet_items)} {hip_type} in snippet '{snippet_name}'")

                                            # Store in snippet_objects for snippet-scoped lookups
                                            if 'snippet_objects' not in dest_config:
                                                dest_config['snippet_objects'] = {}
                                            if snippet_name not in dest_config['snippet_objects']:
                                                dest_config['snippet_objects'][snippet_name] = {}
                                            if hip_type not in dest_config['snippet_objects'][snippet_name]:
                                                dest_config['snippet_objects'][snippet_name][hip_type] = {}

                                            for item in snippet_items:
                                                if isinstance(item, dict) and item.get('name'):
                                                    dest_config['snippet_objects'][snippet_name][hip_type][item.get('name')] = item
                                    except Exception as e:
                                        emit_detail(f"   Error checking snippet '{snippet_name}': {e}", level='warning')

                            # Store in dest_config['objects'] for consistent lookup
                            if hip_type not in dest_config['objects']:
                                dest_config['objects'][hip_type] = {}

                            for item in all_hip_items:
                                if isinstance(item, dict):
                                    item_name = item.get('name')
                                    if item_name:
                                        dest_config['objects'][hip_type][item_name] = item

                            emit_detail(f"   Found {len(dest_config['objects'][hip_type])} {hip_type}(s) in destination")
                        except Exception as e:
                            emit_detail(f"   ⚠️ Error checking {hip_type}: {e}", level='warning')
                    else:
                        emit_detail(f"   ⚠️ No API method for {hip_type}", level='warning')

                emit_detail("")
            
            # Fetch ALL security rules from tenant
            # IMPORTANT: Security rule names must be GLOBALLY UNIQUE across all folders/snippets
            # We must check all rules in the entire tenant, not just the target folder
            has_rules_to_push = False
            for folder in self.selected_items.get('folders', []):
                if folder.get('security_rules'):
                    has_rules_to_push = True
                    break
            for snippet in self.selected_items.get('snippets', []):
                if snippet.get('security_rules'):
                    has_rules_to_push = True
                    break
            
            if has_rules_to_push:
                # Even for new snippets, we need to check rule names for global uniqueness
                # New snippets can be created, but user should be warned if rule names
                # conflict with existing rules (they'll have issues when associating the snippet)
                if all_items_to_new_snippets:
                    emit_detail("🔒 Security Rules - Checking for name conflicts (new snippet)...")
                    emit_detail("   (Checking globally - rule names must be unique when snippet is associated)")
                    emit_detail("")
                    
                if True:  # Always check rule names for global uniqueness
                    emit_progress("Security Rules - Checking global uniqueness",
                                 "")
                    emit_detail("🔒 Security Rules - Checking for name conflicts...")
                    emit_detail("   (Security rules must be globally unique across all folders/snippets)")
                    emit_detail("")
                    
                    if 'security_rules' not in dest_config:
                        dest_config['security_rules'] = {}
                    
                    # Fetch rules from ALL folders (not just target folders)
                    # Skip system/blocked folders that will always error
                    try:
                        all_folders = self.api_client.get_security_policy_folders()
                        valid_folders = [f for f in all_folders if not self._should_skip_folder(f.get('name', ''))]
                        emit_detail(f"   Checking {len(valid_folders)} folders for existing rules...")
                        
                        folder_rule_count = 0
                        for i, folder in enumerate(valid_folders):
                            folder_name = folder.get('name', '')
                            try:
                                rules = self.api_client.get_all_security_rules(folder=folder_name)
                                if isinstance(rules, list):
                                    if folder_name not in dest_config['security_rules']:
                                        dest_config['security_rules'][folder_name] = {}
                                    for rule in rules:
                                        if isinstance(rule, dict):
                                            rule_name = rule.get('name')
                                            if rule_name:
                                                dest_config['security_rules'][folder_name][rule_name] = rule
                                                dest_config['all_rule_names'][rule_name] = {
                                                    'folder': folder_name,
                                                    'snippet': None
                                                }
                                                folder_rule_count += 1
                                # Update progress periodically
                                if (i + 1) % 3 == 0 or i == len(valid_folders) - 1:
                                    emit_detail(f"   📁 Checked {i + 1}/{len(valid_folders)} folders ({folder_rule_count} rules found)")
                                    logger.debug(f"[Validation] all_rule_names count after folder {folder_name}: {len(dest_config['all_rule_names'])}")
                            except Exception as e:
                                logger.warning(f"[Validation] Error checking folder {folder_name}: {e}")
                    except Exception as e:
                        emit_detail(f"   ⚠️  Error enumerating folders: {e}", level="warning")
                    
                    # Also fetch rules from snippets
                    try:
                        all_snippets = self.api_client.get_security_policy_snippets()
                        # Filter to editable snippets only
                        editable_snippets = [s for s in all_snippets 
                                            if s.get('type', '') not in ('predefined', 'readonly')]
                        emit_detail(f"   Checking {len(editable_snippets)} snippets for existing rules...")
                        
                        snippet_rule_count = 0
                        for i, snippet in enumerate(editable_snippets):
                            snippet_name = snippet.get('name', '')
                            if not snippet_name:
                                continue
                            try:
                                rules = self.api_client.get_all_security_rules(snippet=snippet_name)
                                if isinstance(rules, list):
                                    for rule in rules:
                                        if isinstance(rule, dict):
                                            rule_name = rule.get('name')
                                            if rule_name:
                                                dest_config['all_rule_names'][rule_name] = {
                                                    'folder': None,
                                                    'snippet': snippet_name
                                                }
                                                snippet_rule_count += 1
                                # Update progress periodically
                                if (i + 1) % 5 == 0 or i == len(editable_snippets) - 1:
                                    emit_detail(f"   📄 Checked {i + 1}/{len(editable_snippets)} snippets ({snippet_rule_count} rules found)")
                            except Exception as e:
                                pass  # Silently skip snippets that error
                    except Exception as e:
                        emit_detail(f"   ⚠️  Error enumerating snippets: {e}", level="warning")
                    
                    total_rules = len(dest_config['all_rule_names'])
                    emit_detail(f"   ✓ Found {total_rules} total security rules in destination")
                    # Debug: log first few rule names
                    rule_names_sample = list(dest_config['all_rule_names'].keys())[:10]
                    logger.debug(f"[Validation] Sample rule names: {rule_names_sample}")
                    emit_detail("")
            
            # Check for reference dependencies (security rules referencing objects we're pushing)
            # This is critical for OVERWRITE mode - we can't delete objects that are referenced by rules
            emit_progress("Reference Dependencies - Checking rule references", "")
            emit_detail("🔗 Checking if destination rules reference items being pushed...")
            
            dest_config['reference_conflicts'] = []
            dest_config['all_dest_rules'] = {}  # Store all rules with their full data
            
            # Collect objects being pushed AND their destination locations
            # We only need to check for rule conflicts in the DESTINATION locations
            objects_being_pushed = {
                'application_group': set(),
                'application_filter': set(),
                'address': set(),
                'address_group': set(),
                'service': set(),
                'service_group': set(),
            }
            
            # Track which destinations we need to check for rule conflicts
            destination_snippets = set()
            destination_folders = set()
            
            # Get default strategy from selected_items
            default_strategy = self.selected_items.get('default_strategy', 'skip').lower()
            
            def get_item_strategy(obj: dict) -> str:
                """Get effective strategy for an item (from _destination or default)."""
                dest = obj.get('_destination', {})
                return dest.get('strategy', default_strategy).lower()
            
            # Collect from folders - only items with OVERWRITE strategy
            for folder in self.selected_items.get('folders', []):
                folder_objects = folder.get('objects', {})
                for obj_type, obj_list in folder_objects.items():
                    if isinstance(obj_list, list):
                        for obj in obj_list:
                            if isinstance(obj, dict):
                                obj_name = obj.get('name', '')
                                obj_strategy = get_item_strategy(obj)
                                if obj_name and obj_type in objects_being_pushed and obj_strategy == 'overwrite':
                                    objects_being_pushed[obj_type].add(obj_name)
                                    # Track destination
                                    dest_info = obj.get('_destination', {})
                                    dest_folder = dest_info.get('folder', '') or folder.get('name', '')
                                    if dest_info.get('is_existing_snippet'):
                                        destination_snippets.add(dest_folder)
                                    else:
                                        destination_folders.add(dest_folder)
            
            # Collect from snippets - only items with OVERWRITE strategy
            for snippet in self.selected_items.get('snippets', []):
                snippet_name = snippet.get('name', '')
                snippet_objects = snippet.get('objects', {})
                for obj_type, obj_list in snippet_objects.items():
                    if isinstance(obj_list, list):
                        for obj in obj_list:
                            if isinstance(obj, dict):
                                obj_name = obj.get('name', '')
                                obj_strategy = get_item_strategy(obj)
                                if obj_name and obj_type in objects_being_pushed and obj_strategy == 'overwrite':
                                    objects_being_pushed[obj_type].add(obj_name)
                                    # Track destination
                                    dest_info = obj.get('_destination', {})
                                    dest_folder = dest_info.get('folder', '') or snippet_name
                                    if dest_info.get('is_existing_snippet', True):  # Default to snippet for snippet items
                                        destination_snippets.add(dest_folder)
                                    else:
                                        destination_folders.add(dest_folder)
            
            # Log what we're checking
            total_objects = sum(len(v) for v in objects_being_pushed.values())
            if total_objects > 0:
                emit_detail(f"   Checking references to {total_objects} objects being overwritten:")
                for obj_type, names in objects_being_pushed.items():
                    if names:
                        emit_detail(f"     - {obj_type}: {len(names)} items")
                
                emit_detail(f"   Destination locations to check for rules:")
                if destination_snippets:
                    emit_detail(f"     - Snippets: {', '.join(destination_snippets)}")
                if destination_folders:
                    emit_detail(f"     - Folders: {', '.join(destination_folders)}")
                
                # Only fetch rules from DESTINATION locations (not all folders/snippets)
                try:
                    # Get rules from destination folders only
                    for folder_name in destination_folders:
                        try:
                            rules = self.api_client.get_all_security_rules(folder=folder_name)
                            if isinstance(rules, list):
                                for rule in rules:
                                    if isinstance(rule, dict) and rule.get('name'):
                                        rule_name = rule.get('name')
                                        dest_config['all_dest_rules'][rule_name] = {
                                            'data': rule,
                                            'location': folder_name,
                                            'location_type': 'folder'
                                        }
                        except Exception as e:
                            emit_detail(f"     ⚠️ Folder '{folder_name}': error fetching rules - {e}")
                    
                    # Get rules from destination snippets only
                    for snippet_name in destination_snippets:
                        try:
                            rules = self.api_client.get_all_security_rules(snippet=snippet_name)
                            if isinstance(rules, list) and rules:
                                emit_detail(f"     📄 '{snippet_name}': found {len(rules)} rules")
                                for rule in rules:
                                    if isinstance(rule, dict) and rule.get('name'):
                                        rule_name = rule.get('name')
                                        dest_config['all_dest_rules'][rule_name] = {
                                            'data': rule,
                                            'location': snippet_name,
                                            'location_type': 'snippet'
                                        }
                        except Exception as e:
                            emit_detail(f"     ⚠️ Snippet '{snippet_name}': error fetching rules - {e}")
                    
                    emit_detail(f"   Loaded {len(dest_config['all_dest_rules'])} rules from destination locations")
                    
                    # Check each rule for references to objects being overwritten
                    for rule_name, rule_info in dest_config['all_dest_rules'].items():
                        rule_data = rule_info['data']
                        rule_location = rule_info['location']
                        rule_loc_type = rule_info['location_type']
                        
                        # Check application field (references app groups and filters)
                        rule_applications = rule_data.get('application', [])
                        
                        if isinstance(rule_applications, list):
                            for app_ref in rule_applications:
                                # Check if this is an application group being overwritten
                                if app_ref in objects_being_pushed['application_group']:
                                    emit_detail(f"   ⚠️ Rule '{rule_name}' references app_group '{app_ref}'")
                                    dest_config['reference_conflicts'].append({
                                        'rule_name': rule_name,
                                        'rule_location': rule_location,
                                        'rule_location_type': rule_loc_type,
                                        'referenced_object': app_ref,
                                        'referenced_type': 'application_group',
                                        'reference_field': 'application',
                                        'rule_id': rule_data.get('id'),
                                    })
                                # Check if this is an application filter being pushed
                                if app_ref in objects_being_pushed['application_filter']:
                                    dest_config['reference_conflicts'].append({
                                        'rule_name': rule_name,
                                        'rule_location': rule_location,
                                        'rule_location_type': rule_loc_type,
                                        'referenced_object': app_ref,
                                        'referenced_type': 'application_filter',
                                        'reference_field': 'application',
                                        'rule_id': rule_data.get('id'),
                                    })
                        
                        # Check source field (references address objects/groups)
                        rule_sources = rule_data.get('source', {})
                        if isinstance(rule_sources, dict):
                            source_addresses = rule_sources.get('address', [])
                            if isinstance(source_addresses, list):
                                for addr_ref in source_addresses:
                                    if addr_ref in objects_being_pushed['address']:
                                        dest_config['reference_conflicts'].append({
                                            'rule_name': rule_name,
                                            'rule_location': rule_location,
                                            'rule_location_type': rule_loc_type,
                                            'referenced_object': addr_ref,
                                            'referenced_type': 'address',
                                            'reference_field': 'source.address',
                                            'rule_id': rule_data.get('id'),
                                        })
                                    if addr_ref in objects_being_pushed['address_group']:
                                        dest_config['reference_conflicts'].append({
                                            'rule_name': rule_name,
                                            'rule_location': rule_location,
                                            'rule_location_type': rule_loc_type,
                                            'referenced_object': addr_ref,
                                            'referenced_type': 'address_group',
                                            'reference_field': 'source.address',
                                            'rule_id': rule_data.get('id'),
                                        })
                        
                        # Check destination field (references address objects/groups)
                        rule_destinations = rule_data.get('destination', {})
                        if isinstance(rule_destinations, dict):
                            dest_addresses = rule_destinations.get('address', [])
                            if isinstance(dest_addresses, list):
                                for addr_ref in dest_addresses:
                                    if addr_ref in objects_being_pushed['address']:
                                        dest_config['reference_conflicts'].append({
                                            'rule_name': rule_name,
                                            'rule_location': rule_location,
                                            'rule_location_type': rule_loc_type,
                                            'referenced_object': addr_ref,
                                            'referenced_type': 'address',
                                            'reference_field': 'destination.address',
                                            'rule_id': rule_data.get('id'),
                                        })
                                    if addr_ref in objects_being_pushed['address_group']:
                                        dest_config['reference_conflicts'].append({
                                            'rule_name': rule_name,
                                            'rule_location': rule_location,
                                            'rule_location_type': rule_loc_type,
                                            'referenced_object': addr_ref,
                                            'referenced_type': 'address_group',
                                            'reference_field': 'destination.address',
                                            'rule_id': rule_data.get('id'),
                                        })
                        
                        # Check service field (references service objects/groups)
                        rule_services = rule_data.get('service', [])
                        if isinstance(rule_services, list):
                            for svc_ref in rule_services:
                                if svc_ref in objects_being_pushed['service']:
                                    dest_config['reference_conflicts'].append({
                                        'rule_name': rule_name,
                                        'rule_location': rule_location,
                                        'rule_location_type': rule_loc_type,
                                        'referenced_object': svc_ref,
                                        'referenced_type': 'service',
                                        'reference_field': 'service',
                                        'rule_id': rule_data.get('id'),
                                    })
                                if svc_ref in objects_being_pushed['service_group']:
                                    dest_config['reference_conflicts'].append({
                                        'rule_name': rule_name,
                                        'rule_location': rule_location,
                                        'rule_location_type': rule_loc_type,
                                        'referenced_object': svc_ref,
                                        'referenced_type': 'service_group',
                                        'reference_field': 'service',
                                        'rule_id': rule_data.get('id'),
                                    })
                    
                    # Report findings
                    if dest_config['reference_conflicts']:
                        emit_detail(f"   ⚠️  Found {len(dest_config['reference_conflicts'])} reference conflicts!")
                        
                        # Group by referenced object for cleaner output
                        refs_by_object = {}
                        for conflict in dest_config['reference_conflicts']:
                            obj_key = f"{conflict['referenced_type']}:{conflict['referenced_object']}"
                            if obj_key not in refs_by_object:
                                refs_by_object[obj_key] = []
                            refs_by_object[obj_key].append(conflict['rule_name'])
                        
                        for obj_key, rule_names in refs_by_object.items():
                            obj_type, obj_name = obj_key.split(':', 1)
                            emit_detail(f"     - {obj_type} '{obj_name}' referenced by: {', '.join(rule_names)}")
                    else:
                        emit_detail("   ✓ No reference conflicts found")
                    
                except Exception as e:
                    emit_detail(f"   ⚠️  Error checking references: {e}", level="warning")
            else:
                emit_detail("   No objects being pushed - skipping reference check")
            
            emit_detail("")
                
            # Final summary
            emit_detail("=" * 60)
            emit_detail("VALIDATION FETCH COMPLETE")
            emit_detail("=" * 60)
            emit_detail(f"Folders: {len(dest_config['folders'])}")
            emit_detail(f"Snippets: {len(dest_config['snippets'])}")
            emit_detail(f"Object types: {len(dest_config['objects'])}")
            emit_detail(f"Rules checked for conflicts: {len(dest_config.get('all_dest_rules', {}))}")
            emit_detail(f"Reference conflicts found: {len(dest_config.get('reference_conflicts', []))}")
            emit_detail(f"New snippets to create: {len(dest_config['new_snippets'])}")
            emit_detail("")
            
            self.progress.emit("[100%] Validation complete", 100)
            # Don't print from background thread - causes segfaults
            self.finished.emit(dest_config)
            
        except Exception as e:
            # Don't print from background thread - causes segfaults
            # Just emit error signal
            self.error.emit(f"Error fetching destination config: {str(e)}")


class PushPreviewDialog(QDialog):
    """Dialog for previewing push operation before execution."""
    
    def __init__(self, api_client, selected_items: Dict[str, Any], destination_name: str, conflict_resolution: str, parent=None):
        """Initialize the push preview dialog.
        
        Args:
            api_client: API client for destination tenant
            selected_items: Dictionary of selected components to push
            destination_name: Name of destination tenant
            conflict_resolution: Conflict resolution strategy (SKIP, OVERWRITE, RENAME)
            parent: Parent widget
        """
        super().__init__(parent)
        self.api_client = api_client
        self.selected_items = selected_items
        self.destination_name = destination_name
        self.conflict_resolution = conflict_resolution
        self.destination_config = None
        self.worker = None
        
        self.setWindowTitle("Push Preview - Analyzing...")
        self.resize(900, 650)
        
        self._init_ui()
        self._start_fetch()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"<h2>Push Preview: {self.destination_name}</h2>")
        layout.addWidget(header)
        
        info = QLabel(
            f"Analyzing destination tenant for conflicts...<br>"
            f"<b>Conflict Resolution:</b> {self.conflict_resolution}"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Progress section (shown during fetch)
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        
        self.progress_label = QLabel("Fetching destination configurations...")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_widget)
        
        # Tabs for conflict analysis (hidden until fetch complete)
        self.tabs = QTabWidget()
        self.tabs.setVisible(False)
        
        # Conflicts tab
        conflicts_widget = QWidget()
        conflicts_layout = QVBoxLayout(conflicts_widget)
        
        self.conflicts_tree = QTreeWidget()
        self.conflicts_tree.setHeaderLabels(["Component", "Type", "Action"])
        self.conflicts_tree.setColumnWidth(0, 400)
        self.conflicts_tree.setColumnWidth(1, 150)
        conflicts_layout.addWidget(self.conflicts_tree)
        
        self.tabs.addTab(conflicts_widget, "⚠️ Conflicts")
        
        # New items tab
        new_items_widget = QWidget()
        new_items_layout = QVBoxLayout(new_items_widget)
        
        self.new_items_tree = QTreeWidget()
        self.new_items_tree.setHeaderLabels(["Component", "Type", "Action"])
        self.new_items_tree.setColumnWidth(0, 400)
        self.new_items_tree.setColumnWidth(1, 150)
        new_items_layout.addWidget(self.new_items_tree)
        
        self.tabs.addTab(new_items_widget, "✨ New Items")
        
        layout.addWidget(self.tabs)
        
        # Action summary at bottom
        self.action_label = QLabel()
        self.action_label.setStyleSheet(
            "padding: 10px; background-color: #FFF3E0; border-radius: 5px; font-weight: bold;"
        )
        self.action_label.setWordWrap(True)
        self.action_label.setVisible(False)
        layout.addWidget(self.action_label)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # Style the OK button to be more prominent
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("✓ Proceed with Push")
        self.ok_button.setEnabled(False)  # Disabled until analysis complete
        self.ok_button.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 8px 16px; font-weight: bold; "
            "  border-radius: 5px; border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { background-color: #45a049; border-bottom: 3px solid #1B5E20; }"
            "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
            "QPushButton:disabled { background-color: #BDBDBD; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("✗ Cancel")
        
        layout.addWidget(self.button_box)
    
    def _start_fetch(self):
        """Start fetching destination configurations."""
        self.worker = ConfigFetchWorker(self.api_client, self.selected_items)
        self.worker.progress.connect(self._on_fetch_progress, Qt.ConnectionType.QueuedConnection)
        self.worker.finished.connect(self._on_fetch_finished, Qt.ConnectionType.QueuedConnection)
        self.worker.error.connect(self._on_fetch_error, Qt.ConnectionType.QueuedConnection)
        self.worker.start()
    
    def _on_fetch_progress(self, message: str, percentage: int):
        """Handle fetch progress updates."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(percentage)
    
    def _on_fetch_error(self, error: str):
        """Handle fetch errors."""
        self.progress_label.setText(f"Error: {error}")
        self.progress_label.setStyleSheet("color: red;")
        # Still allow proceeding even if fetch fails
        self.ok_button.setEnabled(True)
    
    def _on_fetch_finished(self, destination_config: Dict):
        """Handle fetch completion and analyze conflicts."""
        self.destination_config = destination_config
        
        # Update progress to show completion
        self.progress_label.setText("✓ Destination configuration loaded - Analyzing conflicts...")
        self.progress_label.setStyleSheet("color: green; font-weight: bold;")
        self.progress_bar.setValue(100)
        
        # Brief delay to show completion message
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self._show_analysis)
    
    def _show_analysis(self):
        """Show the analysis results after brief delay."""
        # Hide progress, show tabs
        self.progress_widget.setVisible(False)
        self.tabs.setVisible(True)
        self.action_label.setVisible(True)
        
        # Update window title
        self.setWindowTitle("Push Preview - Analysis Complete")
        
        # Analyze conflicts (this will enable/disable button based on results)
        self._analyze_and_populate()
    
    def _analyze_and_populate(self):
        """Analyze conflicts and populate trees."""
        conflicts = []
        new_items = []
        
        # Built-in folders that should not be created
        BUILTIN_FOLDERS = {
            'Prisma Access',
            'Mobile Users', 
            'Remote Networks',
            'Service Connections',
            'Mobile Users Container',
            'Mobile Users Explicit Proxy'
        }
        
        # Analyze folders
        for folder in self.selected_items.get('folders', []):
            name = folder.get('name', 'Unknown')
            
            # Check if folder itself needs to be created (skip built-in folders)
            if name not in BUILTIN_FOLDERS:
                if name in self.destination_config.get('folders', {}):
                    conflicts.append(('folder', name, folder))
                else:
                    new_items.append(('folder', name, folder))
            
            # ALWAYS analyze folder contents (even for built-in folders)
            # Objects from folder
            folder_objects = folder.get('objects', {})
            # DISABLED: print(f"\nDEBUG: Analyzing folder '{name}' objects:")
            for obj_type, obj_list in folder_objects.items():
                if not isinstance(obj_list, list):
                    continue
                # DISABLED-THREAD: print(f"  {obj_type}: {len(obj_list)} selected items")
                if len(obj_list) > 0 and len(obj_list) <= 10:
                    pass
                    # DISABLED-THREAD: print(f"    Names: {[obj.get('name') for obj in obj_list]}")
                dest_objects = self.destination_config.get('objects', {}).get(obj_type, {})
                for obj in obj_list:
                    obj_name = obj.get('name', 'Unknown')
                    if obj_name in dest_objects:
                        conflicts.append((f"{obj_type} (from {name})", obj_name, obj))
                        # DISABLED-THREAD: print(f"    ✓ Conflict: {obj_name}")
                    else:
                        new_items.append((f"{obj_type} (from {name})", obj_name, obj))
                        # DISABLED-THREAD: print(f"    ✗ New: {obj_name}")
            
            # Rules from folder
            folder_rules = folder.get('security_rules', [])
            if folder_rules:
                # Check if rules exist in destination for this folder
                dest_rules = self.destination_config.get('security_rules', {}).get(name, {})
                for rule in folder_rules:
                    rule_name = rule.get('name', 'Unknown')
                    if rule_name in dest_rules:
                        conflicts.append((f"security_rule (from {name})", rule_name, rule))
                    else:
                        new_items.append((f"security_rule (from {name})", rule_name, rule))
            
            # Profiles from folder
            folder_profiles = folder.get('profiles', {})
            for prof_type, prof_list in folder_profiles.items():
                # Handle security_profiles container
                if prof_type == 'security_profiles' and isinstance(prof_list, dict):
                    # Expand into sub-types
                    for sub_type, sub_list in prof_list.items():
                        if not isinstance(sub_list, list):
                            continue
                        dest_profiles = self.destination_config.get('profiles', {}).get(sub_type, {})
                        for prof in sub_list:
                            prof_name = prof.get('name', 'Unknown')
                            if prof_name in dest_profiles:
                                conflicts.append((f"{sub_type} (from {name})", prof_name, prof))
                            else:
                                new_items.append((f"{sub_type} (from {name})", prof_name, prof))
                elif isinstance(prof_list, list):
                    # Check if profiles exist in destination
                    dest_profiles = self.destination_config.get('profiles', {}).get(prof_type, {})
                    for prof in prof_list:
                        prof_name = prof.get('name', 'Unknown')
                        if prof_name in dest_profiles:
                            conflicts.append((f"{prof_type} (from {name})", prof_name, prof))
                        else:
                            new_items.append((f"{prof_type} (from {name})", prof_name, prof))
            
            # HIP from folder
            folder_hip = folder.get('hip', {})
            for hip_type, hip_list in folder_hip.items():
                if not isinstance(hip_list, list):
                    continue
                # Check if HIP items exist in destination
                dest_hip = self.destination_config.get('hip', {}).get(hip_type, {})
                for hip_item in hip_list:
                    hip_name = hip_item.get('name', 'Unknown')
                    if hip_name in dest_hip:
                        conflicts.append((f"{hip_type} (from {name})", hip_name, hip_item))
                    else:
                        new_items.append((f"{hip_type} (from {name})", hip_name, hip_item))
        
        # Analyze snippets
        for snippet in self.selected_items.get('snippets', []):
            name = snippet.get('name', 'Unknown')
            if name in self.destination_config.get('snippets', {}):
                conflicts.append(('snippet', name, snippet))
            else:
                new_items.append(('snippet', name, snippet))
        
        # Analyze objects
        for obj_type, obj_list in self.selected_items.get('objects', {}).items():
            if not isinstance(obj_list, list):
                continue
            dest_objects = self.destination_config.get('objects', {}).get(obj_type, {})
            for obj in obj_list:
                name = obj.get('name', 'Unknown')
                if name in dest_objects:
                    conflicts.append((obj_type, name, obj))
                else:
                    new_items.append((obj_type, name, obj))
        
        # Analyze infrastructure
        for infra_type, infra_list in self.selected_items.get('infrastructure', {}).items():
            if not isinstance(infra_list, list):
                continue
            dest_infra = self.destination_config.get('infrastructure', {}).get(infra_type, {})
            for item in infra_list:
                name = item.get('name', item.get('id', 'Unknown'))
                if name in dest_infra:
                    conflicts.append((infra_type, name, item))
                else:
                    new_items.append((infra_type, name, item))
        
        # Populate conflicts tree
        self.conflicts_tree.clear()
        if not conflicts:
            no_conflicts = QTreeWidgetItem(self.conflicts_tree, ["✓ No Conflicts Detected", "", ""])
            no_conflicts.setForeground(0, Qt.GlobalColor.darkGreen)
            font = no_conflicts.font(0)
            font.setBold(True)
            no_conflicts.setFont(0, font)
        else:
            # Group by type
            conflict_groups = {}
            for item_type, name, item in conflicts:
                if item_type not in conflict_groups:
                    conflict_groups[item_type] = []
                conflict_groups[item_type].append((name, item))
            
            for item_type, items in conflict_groups.items():
                action = self.conflict_resolution
                type_item = QTreeWidgetItem(
                    self.conflicts_tree,
                    [item_type.replace('_', ' ').title(), "Conflict", f"{len(items)} items - {action}"]
                )
                type_item.setExpanded(True)
                
                for name, item in items:
                    action_text = {
                        'SKIP': 'Will be skipped',
                        'OVERWRITE': 'Will be overwritten',
                        'RENAME': 'Will be renamed'
                    }.get(self.conflict_resolution, 'Unknown')
                    
                    item_widget = QTreeWidgetItem(type_item, [name, item_type, action_text])
                    
                    # Color code by action
                    if self.conflict_resolution == 'OVERWRITE':
                        item_widget.setForeground(2, Qt.GlobalColor.red)
                    elif self.conflict_resolution == 'RENAME':
                        item_widget.setForeground(2, Qt.GlobalColor.blue)
                    else:
                        item_widget.setForeground(2, Qt.GlobalColor.gray)
        
        # Populate new items tree
        self.new_items_tree.clear()
        if not new_items:
            no_new = QTreeWidgetItem(self.new_items_tree, ["No new items to create", "", ""])
            no_new.setForeground(0, Qt.GlobalColor.gray)
        else:
            # Group by type
            new_groups = {}
            for item_type, name, item in new_items:
                if item_type not in new_groups:
                    new_groups[item_type] = []
                new_groups[item_type].append((name, item))
            
            for item_type, items in new_groups.items():
                type_item = QTreeWidgetItem(
                    self.new_items_tree,
                    [item_type.replace('_', ' ').title(), "New", f"{len(items)} items"]
                )
                type_item.setExpanded(True)
                
                for name, item in items:
                    item_widget = QTreeWidgetItem(type_item, [name, item_type, "Will be created"])
                    item_widget.setForeground(2, Qt.GlobalColor.darkGreen)
        
        # Update action label
        total = len(conflicts) + len(new_items)
        conflict_text = f"{len(conflicts)} conflict{'s' if len(conflicts) != 1 else ''}" if conflicts else "no conflicts"
        new_text = f"{len(new_items)} new item{'s' if len(new_items) != 1 else ''}" if new_items else "no new items"
        
        # Check if all items will be skipped (conflicts exist but no new items, and resolution is SKIP)
        if conflicts and not new_items and self.conflict_resolution == 'SKIP':
            # All items are conflicts and will be skipped - nothing to push
            self.action_label.setText(
                f"⚠️ All selected items already exist and will be skipped. "
                f"Update your selection or change conflict resolution to continue."
            )
            self.action_label.setStyleSheet(
                "padding: 10px; background-color: #FFF9C4; border: 2px solid #FBC02D; "
                "border-radius: 5px; font-weight: bold; color: #F57F17;"
            )
            # Disable the push button
            self.ok_button.setEnabled(False)
        else:
            # Normal case - show summary and enable push
            self.action_label.setText(
                f"📊 Ready to push: {conflict_text}, {new_text} ({total} total items)"
            )
            self.action_label.setStyleSheet(
                "padding: 10px; background-color: #FFF3E0; border-radius: 5px; font-weight: bold;"
            )
            # Button was already enabled in _on_fetch_complete, keep it enabled
            self.ok_button.setEnabled(True)
