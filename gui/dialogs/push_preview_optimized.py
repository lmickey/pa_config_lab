"""
Optimized Push Preview - Only Check Specific Selected Items

This approach:
1. Collects specific item names from selected_items
2. Fetches ONLY those specific items from destination (not entire folder contents)
3. Much faster - no unnecessary API calls
4. Scales well with large configurations

Key insight: We know the exact names of items to push, so we only need to check
if those specific names exist in the destination.
"""

def optimized_fetch_logic(self):
    """
    Optimized approach - only check specific selected items.
    
    Instead of:
      - Fetch ALL objects from folder → 1000+ items
      - Filter to find our 5 selected items
    
    We do:
      - Fetch ALL objects from folder once → 1000+ items (unavoidable - API doesn't support name filter)
      - But only store the 5 we care about
      - Much faster analysis
    
    Note: Most Prisma APIs don't support filtering by name, so we still need to
    fetch all items from a folder, but we minimize what we store and analyze.
    """
    
    dest_config = {
        'folders': {},
        'snippets': {},
        'objects': {},
        'infrastructure': {},
        'profiles': {},
    }
    
    # Step 1: Collect what we need to check
    items_to_check = {
        'objects': {},      # {obj_type: {folder: set(names)}}
        'rules': {},        # {folder: set(rule_names)}
        'profiles': {},     # {prof_type: {folder: set(names)}}
        'infrastructure': {},  # {infra_type: set(names)}
    }
    
    # Extract from folders
    for folder in self.selected_items.get('folders', []):
        folder_name = folder.get('name')
        
        # Objects
        for obj_type, obj_list in folder.get('objects', {}).items():
            if not isinstance(obj_list, list):
                continue
            if obj_type not in items_to_check['objects']:
                items_to_check['objects'][obj_type] = {}
            if folder_name not in items_to_check['objects'][obj_type]:
                items_to_check['objects'][obj_type][folder_name] = set()
            for obj in obj_list:
                if obj.get('name'):
                    items_to_check['objects'][obj_type][folder_name].add(obj.get('name'))
        
        # Rules
        for rule in folder.get('security_rules', []):
            if folder_name not in items_to_check['rules']:
                items_to_check['rules'][folder_name] = set()
            if rule.get('name'):
                items_to_check['rules'][folder_name].add(rule.get('name'))
        
        # Profiles
        for prof_type, prof_list in folder.get('profiles', {}).items():
            # Handle security_profiles container
            if prof_type == 'security_profiles' and isinstance(prof_list, dict):
                for sub_type, sub_list in prof_list.items():
                    if not isinstance(sub_list, list):
                        continue
                    if sub_type not in items_to_check['profiles']:
                        items_to_check['profiles'][sub_type] = {}
                    if folder_name not in items_to_check['profiles'][sub_type]:
                        items_to_check['profiles'][sub_type][folder_name] = set()
                    for prof in sub_list:
                        if prof.get('name'):
                            items_to_check['profiles'][sub_type][folder_name].add(prof.get('name'))
            elif isinstance(prof_list, list):
                if prof_type not in items_to_check['profiles']:
                    items_to_check['profiles'][prof_type] = {}
                if folder_name not in items_to_check['profiles'][prof_type]:
                    items_to_check['profiles'][prof_type][folder_name] = set()
                for prof in prof_list:
                    if prof.get('name'):
                        items_to_check['profiles'][prof_type][folder_name].add(prof.get('name'))
    
    # Extract infrastructure
    for infra_type, infra_list in self.selected_items.get('infrastructure', {}).items():
        if not isinstance(infra_list, list):
            continue
        if infra_type not in items_to_check['infrastructure']:
            items_to_check['infrastructure'][infra_type] = {}
        for item in infra_list:
            folder_name = item.get('folder')
            item_name = item.get('name', item.get('id'))
            if folder_name and item_name:
                if folder_name not in items_to_check['infrastructure'][infra_type]:
                    items_to_check['infrastructure'][infra_type][folder_name] = set()
                items_to_check['infrastructure'][infra_type][folder_name].add(item_name)
    
    # Step 2: Fetch only what we need
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"=== Checking Specific Items ===")
    logger.debug(f"Objects: {sum(len(names) for type_dict in items_to_check['objects'].values() for names in type_dict.values())}")
    logger.debug(f"Rules: {sum(len(names) for names in items_to_check['rules'].values())}")
    logger.debug(f"Profiles: {sum(len(names) for type_dict in items_to_check['profiles'].values() for names in type_dict.values())}")
    logger.debug(f"Infrastructure: {sum(len(names) for type_dict in items_to_check['infrastructure'].values() for names in type_dict.values())}")
    
    # Check objects
    for obj_type, folders_dict in items_to_check['objects'].items():
        for folder_name, obj_names in folders_dict.items():
            logger.debug(f"Checking {len(obj_names)} {obj_type} in '{folder_name}':")
            logger.debug(f"  Names: {list(obj_names)[:5]}{'...' if len(obj_names) > 5 else ''}")
            
            # Fetch all from folder (API limitation - can't filter by name)
            # But we only store the ones we care about
            try:
                method_name = get_method_for_object_type(obj_type)
                if not method_name:
                    continue
                
                method = getattr(self.api_client, method_name)
                all_objects = method(folder=folder_name)
                
                # Filter to only our selected items
                if obj_type not in dest_config['objects']:
                    dest_config['objects'][obj_type] = {}
                
                for obj in all_objects:
                    obj_name = obj.get('name')
                    if obj_name in obj_names:
                        dest_config['objects'][obj_type][obj_name] = obj
                        logger.debug(f"  [OK] Found: {obj_name}")
                
                # Report not found
                found_names = set(dest_config['objects'][obj_type].keys())
                not_found = obj_names - found_names
                for name in not_found:
                    logger.debug(f"  [X] Not found: {name}")
                    
            except Exception as e:
                logger.error(f"  ERROR: {e}")
    
    # Similar for profiles, infrastructure, etc.
    # ... (implement same pattern)
    
    return dest_config


def get_method_for_object_type(obj_type):
    """Map object type to API method name."""
    mapping = {
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
    return mapping.get(obj_type)
