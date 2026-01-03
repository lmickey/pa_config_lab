"""
Push preview dialog for reviewing changes before push.

This dialog fetches destination configurations and shows real conflicts
and new items that will be pushed.
"""

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


class ConfigFetchWorker(QThread):
    """Worker thread to fetch destination configurations."""
    
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(object)  # destination_config
    error = pyqtSignal(str)  # error message
    
    def __init__(self, api_client, selected_items):
        super().__init__()
        self.api_client = api_client
        self.selected_items = selected_items
    
    def _count_validation_items(self) -> int:
        """
        Count total items that need validation.
        
        Returns accurate count for progress bar calculation.
        Each category counts as 1 fetch operation for progress.
        """
        count = 0
        
        # Count folders
        folders = self.selected_items.get('folders', [])
        if folders:
            count += 1  # 1 fetch for all folders
            
            # Count objects in folders
            for folder in folders:
                objects = folder.get('objects', {})
                for obj_type, obj_list in objects.items():
                    if obj_list:
                        count += 1  # 1 fetch per object type
                
                # Count profiles in folders
                profiles = folder.get('profiles', {})
                for prof_type, prof_list in profiles.items():
                    if prof_list:
                        count += 1  # 1 fetch per profile type
                
                # Count HIP in folders
                hip = folder.get('hip', {})
                for hip_type, hip_list in hip.items():
                    if hip_list:
                        count += 1  # 1 fetch per HIP type
                
                # Count security rules
                if folder.get('security_rules'):
                    count += 1  # 1 fetch for rules
        
        # Count snippets
        if self.selected_items.get('snippets'):
            count += 1  # 1 fetch for snippets
        
        # Count infrastructure
        infrastructure = self.selected_items.get('infrastructure', {})
        for infra_type, infra_list in infrastructure.items():
            if infra_list:
                count += 1  # 1 fetch per infrastructure type
        
        return max(count, 1)  # Ensure at least 1 for division
    
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
                'infrastructure': {}
            }
            
            # Count total items accurately for progress calculation
            total_items = self._count_validation_items()
            
            # DISABLED: print(f"Total items to check: {total_items}")
            current = 0
            
            # Fetch folders and their contents
            folders = self.selected_items.get('folders', [])
            if folders:
                self.progress.emit(f"Checking folders...", int((current / max(total_items, 1)) * 100))
                try:
                    # DISABLED-THREAD: print(f"  Fetching folders using get_security_policy_folders()")
                    existing_folders = self.api_client.get_security_policy_folders()
                    # DISABLED-THREAD: print(f"    Found {len(existing_folders)} existing folders")
                    for folder in existing_folders:
                        folder_name = folder.get('name')
                        if folder_name:
                            dest_config['folders'][folder_name] = folder
                            if len(dest_config['folders']) <= 5:
                                pass
                                # DISABLED-THREAD: print(f"      - {folder_name}")
                    
                    if len(dest_config['folders']) > 5:
                        pass
                        # DISABLED-THREAD: print(f"      ... and {len(dest_config['folders']) - 5} more")
                    
                    # Also fetch objects/rules/profiles from folders for conflict checking
                    # DISABLED-THREAD: print(f"  Fetching folder contents for conflict checking...")
                    for folder in folders:
                        folder_name = folder.get('name', 'Unknown')
                        # DISABLED-THREAD: print(f"    Folder: {folder_name}")
                        
                        # Fetch objects from this folder
                        folder_objects = folder.get('objects', {})
                        if folder_objects:
                            # DISABLED-THREAD: print(f"      Fetching objects from folder: {list(folder_objects.keys())}")
                            for obj_type in folder_objects.keys():
                                if obj_type not in dest_config['objects']:
                                    dest_config['objects'][obj_type] = {}
                                # We'll fetch these in the objects section below
                        
                        # Note: Rules are folder-specific, so we don't fetch them globally
                        folder_rules = folder.get('security_rules', [])
                        if folder_rules:
                            pass
                            # DISABLED-THREAD: print(f"      Rules: {len(folder_rules)} items (folder-specific)")
                        
                        # Note: Profiles are folder-specific
                        folder_profiles = folder.get('profiles', {})
                        if folder_profiles:
                            pass
                            # DISABLED-THREAD: print(f"      Profiles: {list(folder_profiles.keys())} (folder-specific)")
                        
                        # Note: HIP is folder-specific
                        folder_hip = folder.get('hip', {})
                        if folder_hip:
                            pass
                            # DISABLED-THREAD: print(f"      HIP: {list(folder_hip.keys())} (folder-specific)")
                    
                except Exception as e:
                    # DISABLED-THREAD: print(f"    ERROR fetching folders: {e}")
                    import traceback
                    # DISABLED-THREAD: traceback.print_exc()
                current += 1  # Increment by 1 for folder fetch operation
            
            # Fetch snippets
            snippets = self.selected_items.get('snippets', [])
            if snippets:
                self.progress.emit(f"Checking snippets...", int((current / max(total_items, 1)) * 100))
                try:
                    # DISABLED-THREAD: print(f"  Fetching snippets using get_security_policy_snippets()")
                    existing_snippets = self.api_client.get_security_policy_snippets()
                    # DISABLED-THREAD: print(f"    Found {len(existing_snippets)} existing snippets")
                    for snippet in existing_snippets:
                        snippet_name = snippet.get('name')
                        if snippet_name:
                            dest_config['snippets'][snippet_name] = snippet
                            # DISABLED-THREAD: print(f"      - {snippet_name}")
                except Exception as e:
                    # DISABLED-THREAD: print(f"    ERROR fetching snippets: {e}")
                    import traceback
                    # DISABLED-THREAD: traceback.print_exc()
                current += 1  # Increment by 1 for snippet fetch operation
            
            # Fetch objects (both top-level and from folders)
            objects = self.selected_items.get('objects', {})
            
            # Also collect object types and folders from folder selections
            folders = self.selected_items.get('folders', [])
            object_folders = {}  # Track which folders contain which object types
            
            for folder in folders:
                folder_name = folder.get('name')
                folder_objects = folder.get('objects', {})
                for obj_type, obj_list in folder_objects.items():
                    if obj_type not in objects:
                        objects[obj_type] = []
                    # Track which folders have this object type
                    if obj_type not in object_folders:
                        object_folders[obj_type] = set()
                    if folder_name:
                        object_folders[obj_type].add(folder_name)
            
            if objects:
                self.progress.emit(f"Checking objects...", int((current / max(total_items, 1)) * 100))
                
                # Map object types to API client methods
                object_method_map = {
                    'address_objects': 'get_all_addresses',
                    'address_groups': 'get_all_address_groups',
                    'service_objects': 'get_all_services',
                    'service_groups': 'get_all_service_groups',
                    'applications': 'get_all_applications',
                    'application_groups': 'get_all_application_groups',
                    'application_filters': 'get_all_application_filters',
                    'external_dynamic_lists': 'get_all_external_dynamic_lists',
                    'fqdn_objects': 'get_all_fqdn_objects',
                    'url_filtering_categories': 'get_all_url_categories',
                }
                
                for obj_type, obj_list in objects.items():
                    if not isinstance(obj_list, list):
                        # DISABLED-THREAD: print(f"  Skipping {obj_type} - not a list (type: {type(obj_list)})")
                        continue
                    
                    # DISABLED-THREAD: print(f"  Checking {obj_type}: {len(obj_list)} items")
                    method_name = object_method_map.get(obj_type)
                    if method_name and hasattr(self.api_client, method_name):
                        try:
                            # Determine which folders to query for this object type
                            folders_to_check = object_folders.get(obj_type, set())
                            # DISABLED-THREAD: print(f"    Folders to check: {list(folders_to_check) if folders_to_check else 'all'}")
                            
                            # Fetch from each folder
                            all_existing_objects = []
                            method = getattr(self.api_client, method_name)
                            
                            if folders_to_check:
                                # Query each folder separately
                                for folder in folders_to_check:
                                    # DISABLED-THREAD: print(f"    Calling API method: {method_name}(folder='{folder}')")
                                    try:
                                        folder_objects = method(folder=folder)
                                        if isinstance(folder_objects, list):
                                            all_existing_objects.extend(folder_objects)
                                    except Exception as folder_err:
                                        pass
                                        # DISABLED-THREAD: print(f"      ERROR for folder '{folder}': {folder_err}")
                            else:
                                # No folder specified, try without folder parameter
                                # DISABLED-THREAD: print(f"    Calling API method: {method_name}()")
                                all_existing_objects = method()
                            
                            existing_objects = all_existing_objects
                            
                            if not isinstance(existing_objects, list):
                                # DISABLED-THREAD: print(f"    WARNING: Expected list, got {type(existing_objects)}")
                                existing_objects = []
                            
                            # DISABLED-THREAD: print(f"    Found {len(existing_objects)} existing items")
                            
                            if obj_type not in dest_config['objects']:
                                dest_config['objects'][obj_type] = {}
                            
                            for obj in existing_objects:
                                if not isinstance(obj, dict):
                                    # DISABLED-THREAD: print(f"      WARNING: Object is not a dict: {type(obj)}")
                                    continue
                                obj_name = obj.get('name')
                                if obj_name:
                                    dest_config['objects'][obj_type][obj_name] = obj
                                    if len(dest_config['objects'][obj_type]) <= 5:  # Only print first 5
                                        pass
                                        # DISABLED-THREAD: print(f"      - {obj_name}")
                            
                            if len(dest_config['objects'][obj_type]) > 5:
                                pass
                                # DISABLED-THREAD: print(f"      ... and {len(dest_config['objects'][obj_type]) - 5} more")
                                
                        except AttributeError as e:
                            pass
                            # DISABLED-THREAD: print(f"    ERROR: Method {method_name} not found: {e}")
                        except TypeError as e:
                            # DISABLED-THREAD: print(f"    ERROR: Type error calling {method_name}: {e}")
                            import traceback
                            # DISABLED-THREAD: traceback.print_exc()
                        except Exception as e:
                            # DISABLED-THREAD: print(f"    ERROR fetching {obj_type}: {type(e).__name__}: {e}")
                            import traceback
                            # DISABLED-THREAD: traceback.print_exc()
                    else:
                        pass
                        # DISABLED-THREAD: print(f"    ⚠️  WARNING: No API method for {obj_type} (mapped to: {method_name})")
                    
                    current += 1  # Increment by 1 for each object type fetch
            
            # Fetch infrastructure components
            infrastructure = self.selected_items.get('infrastructure', {})
            # DISABLED: print(f"\nInfrastructure to check: {list(infrastructure.keys()) if infrastructure else 'None'}")
            if infrastructure:
                self.progress.emit(f"Checking infrastructure...", int((current / max(total_items, 1)) * 100))
                
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
                        # DISABLED-THREAD: print(f"    ⚠️  WARNING: No API method for {infra_type} (mapped to: {method_name})")
                    
                    current += 1  # Increment by 1 for each infrastructure type fetch
            
            # Fetch profiles from folders
            # Profiles are folder-specific and need to be fetched per folder
            profile_folders = {}  # Track which folders contain which profile types
            for folder in self.selected_items.get('folders', []):
                folder_name = folder.get('name')
                folder_profiles = folder.get('profiles', {})
                for profile_type, profile_list in folder_profiles.items():
                    # Skip security_profiles container - it's not a real profile type
                    if profile_type == 'security_profiles':
                        # security_profiles is a container with sub-types
                        # Expand it into individual profile types
                        if isinstance(profile_list, dict):
                            for sub_type, sub_list in profile_list.items():
                                if sub_type not in profile_folders:
                                    profile_folders[sub_type] = set()
                                if folder_name:
                                    profile_folders[sub_type].add(folder_name)
                        continue
                    
                    if profile_type not in profile_folders:
                        profile_folders[profile_type] = set()
                    if folder_name:
                        profile_folders[profile_type].add(folder_name)
            
            if profile_folders:
                self.progress.emit(f"Checking profiles...", int((current / max(total_items, 1)) * 100))
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
                    'profile_groups': 'get_all_profile_groups',
                    'security_profiles': None,  # Security profiles is a container, not a single type
                }
                
                if 'profiles' not in dest_config:
                    dest_config['profiles'] = {}
                
                for profile_type, folders_set in profile_folders.items():
                    # DISABLED-THREAD: print(f"  Checking {profile_type} in folders: {list(folders_set)}")
                    method_name = profile_method_map.get(profile_type)
                    
                    if method_name and hasattr(self.api_client, method_name):
                        try:
                            all_profiles = []
                            method = getattr(self.api_client, method_name)
                            
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
                        # DISABLED-THREAD: print(f"    ⚠️  WARNING: No API method for {profile_type} (mapped to: {method_name})")
                    
                    current += 1  # Increment by 1 for each profile type fetch
            
            # Fetch HIP items from folders
            hip_folders = {}  # Track which folders contain which HIP types
            for folder in self.selected_items.get('folders', []):
                folder_name = folder.get('name')
                folder_hip = folder.get('hip', {})
                for hip_type, hip_list in folder_hip.items():
                    if not isinstance(hip_list, list):
                        continue
                    if hip_type not in hip_folders:
                        hip_folders[hip_type] = set()
                    if folder_name:
                        hip_folders[hip_type].add(folder_name)
            
            if hip_folders:
                # TEMPORARY: Skip HIP fetching - causing segfaults
                # TODO: Investigate root cause of HIP API segfault
                # DISABLED-THREAD: print(f"⚠️  Skipping HIP validation (known stability issue - will be fixed)")
                if 'hip' not in dest_config:
                    dest_config['hip'] = {}
                # Skip ALL HIP processing - commented out to prevent crashes
                # The entire HIP section is disabled below
            
            # Fetch security rules from folders
            rule_folders = set()  # Track which folders have rules
            for folder in self.selected_items.get('folders', []):
                folder_name = folder.get('name')
                folder_rules = folder.get('security_rules', [])
                if folder_rules and folder_name:
                    rule_folders.add(folder_name)
            
            if rule_folders:
                self.progress.emit(f"Checking security rules...", int((current / max(total_items, 1)) * 100))
                # DISABLED-THREAD: print(f"  Checking security rules in folders: {list(rule_folders)}")
                
                if 'security_rules' not in dest_config:
                    dest_config['security_rules'] = {}
                
                for folder_name in rule_folders:
                    # DISABLED-THREAD: print(f"    Calling API method: get_all_security_rules(folder='{folder_name}')")
                    try:
                        rules = self.api_client.get_all_security_rules(folder=folder_name)
                        if isinstance(rules, list):
                            # Store rules by folder
                            if folder_name not in dest_config['security_rules']:
                                dest_config['security_rules'][folder_name] = {}
                            for rule in rules:
                                if isinstance(rule, dict):
                                    rule_name = rule.get('name')
                                    if rule_name:
                                        dest_config['security_rules'][folder_name][rule_name] = rule
                            # DISABLED-THREAD: print(f"      Found {len(dest_config['security_rules'][folder_name])} rules in '{folder_name}'")
                    except Exception as e:
                        pass
                        # DISABLED-THREAD: print(f"      ERROR fetching rules from '{folder_name}': {e}")
                
                current += 1  # Increment by 1 for security rules fetch
            
            self.progress.emit("Analysis complete", 100)
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
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
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
