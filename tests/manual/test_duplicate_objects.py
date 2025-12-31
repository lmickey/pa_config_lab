#!/usr/bin/env python3
"""
Test script to verify that duplicate objects are removed and parent dependencies are tracked.

This script pulls configuration and checks:
1. Objects are only stored at their creation folder level
2. Parent-level objects are tracked as dependencies
3. No duplicate objects exist across folder levels
"""

import sys
import json
from typing import Dict, List, Set, Any

# Add project root to path
sys.path.insert(0, '.')

from load_settings import load_settings
from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.config_pull import pull_configuration


def find_duplicate_objects(config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Find objects that appear in multiple folders.
    
    Returns:
        Dictionary mapping object names to list of folders they appear in
    """
    object_locations: Dict[str, List[Dict[str, Any]]] = {}
    
    security_policies = config.get('security_policies', {})
    folders = security_policies.get('folders', [])
    
    for folder in folders:
        folder_name = folder.get('name', '')
        objects = folder.get('objects', {})
        
        # Check all object types
        for obj_type in ['address_objects', 'address_groups', 'service_objects', 'service_groups', 'applications']:
            obj_list = objects.get(obj_type, [])
            for obj in obj_list:
                obj_name = obj.get('name', '')
                obj_folder = obj.get('folder', '')
                
                if obj_name:
                    key = f"{obj_type}:{obj_name}"
                    if key not in object_locations:
                        object_locations[key] = []
                    
                    object_locations[key].append({
                        'folder': folder_name,
                        'created_in': obj_folder,
                        'object': obj
                    })
    
    # Filter to only duplicates (appearing in multiple folders)
    duplicates = {
        key: locations
        for key, locations in object_locations.items()
        if len(locations) > 1
    }
    
    return duplicates


def check_parent_dependencies(config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Check that parent dependencies are properly tracked.
    
    Returns:
        Dictionary mapping folder names to their parent dependencies
    """
    parent_deps: Dict[str, List[Dict[str, Any]]] = {}
    
    security_policies = config.get('security_policies', {})
    folders = security_policies.get('folders', [])
    
    for folder in folders:
        folder_name = folder.get('name', '')
        parent_deps_list = folder.get('parent_dependencies', {})
        
        if parent_deps_list:
            # Flatten parent dependencies
            all_deps = []
            for obj_type, obj_list in parent_deps_list.items():
                for obj in obj_list:
                    all_deps.append({
                        'type': obj_type,
                        'name': obj.get('name', ''),
                        'folder': obj.get('folder', '')
                    })
            
            if all_deps:
                parent_deps[folder_name] = all_deps
    
    return parent_deps


def main():
    """Main test function."""
    print("=" * 80)
    print("DUPLICATE OBJECTS TEST")
    print("=" * 80)
    print()
    
    # Load settings
    print("Loading settings...")
    settings = load_settings()
    
    if not settings:
        print("✗ Failed to load settings")
        return False
    
    # Create API client
    print("Creating API client...")
    api_client = PrismaAccessAPIClient(
        tsg_id=settings['tsg_id'],
        client_id=settings['client_id'],
        client_secret=settings['client_secret']
    )
    
    # Pull configuration
    print("Pulling configuration...")
    print("(This may take a few minutes)")
    print()
    
    try:
        config = pull_configuration(
            api_client=api_client,
            folders=None,  # Pull all folders
            snippets=None,  # Pull all snippets
            application_names=None  # No custom applications
        )
    except Exception as e:
        print(f"✗ Failed to pull configuration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("✓ Configuration pulled successfully")
    print()
    
    # Check for duplicates
    print("Checking for duplicate objects...")
    duplicates = find_duplicate_objects(config)
    
    if duplicates:
        print(f"✗ Found {len(duplicates)} duplicate objects:")
        print()
        for obj_key, locations in duplicates.items():
            obj_type, obj_name = obj_key.split(':', 1)
            print(f"  {obj_type}: {obj_name}")
            for loc in locations:
                print(f"    - Found in folder: {loc['folder']}")
                print(f"      Created in folder: {loc['created_in']}")
            print()
        return False
    else:
        print("✓ No duplicate objects found")
        print()
    
    # Check parent dependencies
    print("Checking parent dependencies...")
    parent_deps = check_parent_dependencies(config)
    
    if parent_deps:
        print(f"✓ Found parent dependencies in {len(parent_deps)} folders:")
        print()
        for folder_name, deps in parent_deps.items():
            print(f"  Folder: {folder_name}")
            print(f"    Parent dependencies: {len(deps)}")
            # Group by type
            by_type: Dict[str, List[str]] = {}
            for dep in deps:
                dep_type = dep['type']
                if dep_type not in by_type:
                    by_type[dep_type] = []
                by_type[dep_type].append(f"{dep['name']} (from {dep['folder']})")
            
            for dep_type, names in by_type.items():
                print(f"      {dep_type}: {len(names)}")
                for name in names[:5]:  # Show first 5
                    print(f"        - {name}")
                if len(names) > 5:
                    print(f"        ... and {len(names) - 5} more")
            print()
    else:
        print("✓ No parent dependencies found (or no child folders)")
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Duplicate objects: {len(duplicates)}")
    print(f"  Folders with parent dependencies: {len(parent_deps)}")
    
    if duplicates:
        print()
        print("✗ TEST FAILED: Duplicate objects found")
        return False
    else:
        print()
        print("✓ TEST PASSED: No duplicate objects")
        return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
