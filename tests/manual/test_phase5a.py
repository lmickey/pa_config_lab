#!/usr/bin/env python3
"""
Phase 5a: Configuration Viewer - Default Detection Verification

This script allows viewing saved configuration files and verifying
that defaults are properly detected and can be filtered.
"""

import sys
import json
import getpass
from typing import Dict, Any, List, Optional
from pathlib import Path


def load_config_file(filename: str) -> Optional[Dict[str, Any]]:
    """Load configuration from file."""
    from config.storage.json_storage import load_config_json, derive_key
    
    if not Path(filename).exists():
        print(f"  ✗ File not found: {filename}")
        return None
    
    print(f"Loading configuration from: {filename}")
    
    # Detect encryption
    encrypted = None
    try:
        with open(filename, 'rb') as f:
            data = f.read()
        try:
            decoded = data.decode('utf-8').strip()
            if decoded.startswith('{') or decoded.startswith('['):
                try:
                    json.loads(decoded)
                    encrypted = False
                except json.JSONDecodeError:
                    encrypted = True
            else:
                encrypted = True
        except UnicodeDecodeError:
            encrypted = True
    except Exception as e:
        print(f"  ⚠ Warning: Could not determine encryption status: {e}")
        encrypted = None
    
    try:
        cipher = None
        if encrypted:
            decrypt_password = getpass.getpass("Enter password to decrypt backup: ")
            cipher = derive_key(decrypt_password)
            config = load_config_json(filename, cipher=cipher, encrypted=True)
        elif encrypted is False:
            config = load_config_json(filename, cipher=None, encrypted=False)
        else:
            config = load_config_json(filename, cipher=None, encrypted=None)
        
        if not config:
            print("  ✗ Failed to load configuration")
            return None
        
        print("  ✓ Configuration loaded successfully")
        return config
        
    except Exception as e:
        print(f"  ✗ Failed to load configuration: {e}")
        import traceback
        traceback.print_exc()
        return None


def count_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """Count defaults in configuration."""
    stats = {
        'folders': {'total': 0, 'defaults': 0, 'custom': 0},
        'snippets': {'total': 0, 'defaults': 0, 'custom': 0},
        'rules': {'total': 0, 'defaults': 0, 'custom': 0},
        'objects': {'total': 0, 'defaults': 0, 'custom': 0},
        'profiles': {'total': 0, 'defaults': 0, 'custom': 0}
    }
    
    security_policies = config.get('security_policies', {})
    
    # Count folders
    folders = security_policies.get('folders', [])
    for folder in folders:
        stats['folders']['total'] += 1
        if folder.get('is_default', False):
            stats['folders']['defaults'] += 1
        else:
            stats['folders']['custom'] += 1
        
        # Count rules in folder
        rules = folder.get('security_rules', [])
        for rule in rules:
            stats['rules']['total'] += 1
            if rule.get('is_default', False):
                stats['rules']['defaults'] += 1
            else:
                stats['rules']['custom'] += 1
        
        # Count objects in folder
        objects = folder.get('objects', {})
        for obj_type, obj_list in objects.items():
            if isinstance(obj_list, list):
                for obj in obj_list:
                    stats['objects']['total'] += 1
                    if obj.get('is_default', False):
                        stats['objects']['defaults'] += 1
                    else:
                        stats['objects']['custom'] += 1
        
        # Count profiles in folder
        profiles = folder.get('profiles', {})
        for profile_type, profile_list in profiles.items():
            if isinstance(profile_list, list):
                for profile in profile_list:
                    stats['profiles']['total'] += 1
                    if profile.get('is_default', False):
                        stats['profiles']['defaults'] += 1
                    else:
                        stats['profiles']['custom'] += 1
    
    # Count snippets
    snippets = security_policies.get('snippets', [])
    for snippet in snippets:
        stats['snippets']['total'] += 1
        if snippet.get('is_default', False):
            stats['snippets']['defaults'] += 1
        else:
            stats['snippets']['custom'] += 1
    
    return stats


def print_defaults_summary(stats: Dict[str, Any]):
    """Print summary of defaults."""
    print("\n" + "=" * 60)
    print("DEFAULTS SUMMARY")
    print("=" * 60)
    
    for category, counts in stats.items():
        total = counts['total']
        defaults = counts['defaults']
        custom = counts['custom']
        
        if total > 0:
            default_pct = (defaults / total * 100) if total > 0 else 0
            print(f"\n{category.upper()}:")
            print(f"  Total: {total}")
            print(f"  Defaults: {defaults} ({default_pct:.1f}%)")
            print(f"  Custom: {custom} ({100-default_pct:.1f}%)")
    
    # Overall totals
    total_all = sum(s['total'] for s in stats.values())
    defaults_all = sum(s['defaults'] for s in stats.values())
    custom_all = sum(s['custom'] for s in stats.values())
    
    print("\n" + "-" * 60)
    print("OVERALL TOTALS:")
    print(f"  Total items: {total_all}")
    print(f"  Defaults: {defaults_all} ({defaults_all/total_all*100:.1f}%)" if total_all > 0 else "  Defaults: 0")
    print(f"  Custom: {custom_all} ({custom_all/total_all*100:.1f}%)" if total_all > 0 else "  Custom: 0")
    print("=" * 60)


def list_defaults(config: Dict[str, Any], category: str = 'all'):
    """List default items in configuration."""
    security_policies = config.get('security_policies', {})
    
    print("\n" + "=" * 60)
    print(f"DEFAULT ITEMS: {category.upper()}")
    print("=" * 60)
    
    if category in ['all', 'folders']:
        folders = security_policies.get('folders', [])
        default_folders = [f for f in folders if f.get('is_default', False)]
        if default_folders:
            print(f"\nDefault Folders ({len(default_folders)}):")
            for folder in default_folders:
                print(f"  - {folder.get('name', 'Unknown')}")
        else:
            print("\nNo default folders found")
    
    if category in ['all', 'snippets']:
        snippets = security_policies.get('snippets', [])
        default_snippets = [s for s in snippets if s.get('is_default', False)]
        if default_snippets:
            print(f"\nDefault Snippets ({len(default_snippets)}):")
            for snippet in default_snippets:
                print(f"  - {snippet.get('name', 'Unknown')}")
        else:
            print("\nNo default snippets found")
    
    if category in ['all', 'rules']:
        folders = security_policies.get('folders', [])
        default_rules = []
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            rules = folder.get('security_rules', [])
            for rule in rules:
                if rule.get('is_default', False):
                    default_rules.append((folder_name, rule.get('name', 'Unknown')))
        
        if default_rules:
            print(f"\nDefault Rules ({len(default_rules)}):")
            for folder_name, rule_name in default_rules[:20]:  # Show first 20
                print(f"  - [{folder_name}] {rule_name}")
            if len(default_rules) > 20:
                print(f"  ... and {len(default_rules) - 20} more")
        else:
            print("\nNo default rules found")
    
    if category in ['all', 'objects']:
        folders = security_policies.get('folders', [])
        default_objects = []
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            objects = folder.get('objects', {})
            for obj_type, obj_list in objects.items():
                if isinstance(obj_list, list):
                    for obj in obj_list:
                        if obj.get('is_default', False):
                            default_objects.append((folder_name, obj_type, obj.get('name', 'Unknown')))
        
        if default_objects:
            print(f"\nDefault Objects ({len(default_objects)}):")
            for folder_name, obj_type, obj_name in default_objects[:20]:  # Show first 20
                print(f"  - [{folder_name}] {obj_type}: {obj_name}")
            if len(default_objects) > 20:
                print(f"  ... and {len(default_objects) - 20} more")
        else:
            print("\nNo default objects found")
    
    if category in ['all', 'profiles']:
        folders = security_policies.get('folders', [])
        default_profiles = []
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            profiles = folder.get('profiles', {})
            for profile_type, profile_list in profiles.items():
                if isinstance(profile_list, list):
                    for profile in profile_list:
                        if profile.get('is_default', False):
                            default_profiles.append((folder_name, profile_type, profile.get('name', 'Unknown')))
        
        if default_profiles:
            print(f"\nDefault Profiles ({len(default_profiles)}):")
            for folder_name, profile_type, profile_name in default_profiles[:20]:  # Show first 20
                print(f"  - [{folder_name}] {profile_type}: {profile_name}")
            if len(default_profiles) > 20:
                print(f"  ... and {len(default_profiles) - 20} more")
        else:
            print("\nNo default profiles found")
    
    print("=" * 60)


def list_custom_items(config: Dict[str, Any], category: str = 'all'):
    """List custom (non-default) items in configuration."""
    security_policies = config.get('security_policies', {})
    
    print("\n" + "=" * 60)
    print(f"CUSTOM ITEMS: {category.upper()}")
    print("=" * 60)
    
    if category in ['all', 'folders']:
        folders = security_policies.get('folders', [])
        custom_folders = [f for f in folders if not f.get('is_default', False)]
        if custom_folders:
            print(f"\nCustom Folders ({len(custom_folders)}):")
            for folder in custom_folders:
                print(f"  - {folder.get('name', 'Unknown')}")
        else:
            print("\nNo custom folders found")
    
    if category in ['all', 'snippets']:
        snippets = security_policies.get('snippets', [])
        custom_snippets = [s for s in snippets if not s.get('is_default', False)]
        if custom_snippets:
            print(f"\nCustom Snippets ({len(custom_snippets)}):")
            for snippet in custom_snippets:
                print(f"  - {snippet.get('name', 'Unknown')}")
        else:
            print("\nNo custom snippets found")
    
    if category in ['all', 'rules']:
        folders = security_policies.get('folders', [])
        custom_rules = []
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            rules = folder.get('security_rules', [])
            for rule in rules:
                if not rule.get('is_default', False):
                    custom_rules.append((folder_name, rule.get('name', 'Unknown')))
        
        if custom_rules:
            print(f"\nCustom Rules ({len(custom_rules)}):")
            for folder_name, rule_name in custom_rules[:20]:  # Show first 20
                print(f"  - [{folder_name}] {rule_name}")
            if len(custom_rules) > 20:
                print(f"  ... and {len(custom_rules) - 20} more")
        else:
            print("\nNo custom rules found")
    
    if category in ['all', 'objects']:
        folders = security_policies.get('folders', [])
        custom_objects = []
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            objects = folder.get('objects', {})
            for obj_type, obj_list in objects.items():
                if isinstance(obj_list, list):
                    for obj in obj_list:
                        if not obj.get('is_default', False):
                            custom_objects.append((folder_name, obj_type, obj.get('name', 'Unknown')))
        
        if custom_objects:
            print(f"\nCustom Objects ({len(custom_objects)}):")
            for folder_name, obj_type, obj_name in custom_objects[:20]:  # Show first 20
                print(f"  - [{folder_name}] {obj_type}: {obj_name}")
            if len(custom_objects) > 20:
                print(f"  ... and {len(custom_objects) - 20} more")
        else:
            print("\nNo custom objects found")
    
    if category in ['all', 'profiles']:
        folders = security_policies.get('folders', [])
        custom_profiles = []
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            profiles = folder.get('profiles', {})
            for profile_type, profile_list in profiles.items():
                if isinstance(profile_list, list):
                    for profile in profile_list:
                        if not profile.get('is_default', False):
                            custom_profiles.append((folder_name, profile_type, profile.get('name', 'Unknown')))
        
        if custom_profiles:
            print(f"\nCustom Profiles ({len(custom_profiles)}):")
            for folder_name, profile_type, profile_name in custom_profiles[:20]:  # Show first 20
                print(f"  - [{folder_name}] {profile_type}: {profile_name}")
            if len(custom_profiles) > 20:
                print(f"  ... and {len(custom_profiles) - 20} more")
        else:
            print("\nNo custom profiles found")
    
    print("=" * 60)


def main():
    """Main viewer function."""
    print("=" * 60)
    print("Phase 5a: Configuration Viewer - Default Detection Verification")
    print("=" * 60)
    
    # Get filename
    filename = input("\nEnter configuration filename: ").strip()
    if not filename:
        print("  ✗ No filename provided")
        return 1
    
    # Load configuration
    config = load_config_file(filename)
    if not config:
        return 1
    
    # Count defaults
    stats = count_defaults(config)
    
    # Print summary
    print_defaults_summary(stats)
    
    # Interactive menu
    while True:
        print("\n" + "=" * 60)
        print("VIEW OPTIONS")
        print("=" * 60)
        print("1. List all default items")
        print("2. List all custom items")
        print("3. List defaults by category")
        print("4. List custom items by category")
        print("5. Show configuration metadata")
        print("6. Export filtered configuration (defaults only)")
        print("7. Export filtered configuration (custom only)")
        print("8. Exit")
        
        choice = input("\nEnter choice (1-8): ").strip()
        
        if choice == '1':
            list_defaults(config, 'all')
        elif choice == '2':
            list_custom_items(config, 'all')
        elif choice == '3':
            print("\nSelect category:")
            print("  1. Folders")
            print("  2. Snippets")
            print("  3. Rules")
            print("  4. Objects")
            print("  5. Profiles")
            cat_choice = input("Enter choice (1-5): ").strip()
            cat_map = {'1': 'folders', '2': 'snippets', '3': 'rules', '4': 'objects', '5': 'profiles'}
            if cat_choice in cat_map:
                list_defaults(config, cat_map[cat_choice])
        elif choice == '4':
            print("\nSelect category:")
            print("  1. Folders")
            print("  2. Snippets")
            print("  3. Rules")
            print("  4. Objects")
            print("  5. Profiles")
            cat_choice = input("Enter choice (1-5): ").strip()
            cat_map = {'1': 'folders', '2': 'snippets', '3': 'rules', '4': 'objects', '5': 'profiles'}
            if cat_choice in cat_map:
                list_custom_items(config, cat_map[cat_choice])
        elif choice == '5':
            metadata = config.get('metadata', {})
            print("\n" + "=" * 60)
            print("CONFIGURATION METADATA")
            print("=" * 60)
            print(json.dumps(metadata, indent=2))
            print("=" * 60)
        elif choice == '6':
            from config.defaults.default_detector import DefaultDetector
            detector = DefaultDetector()
            filtered = detector.filter_defaults(config, include_defaults=True, include_custom=False)
            output_file = filename.replace('.json', '_defaults_only.json')
            from config.storage.json_storage import save_config_json
            save_config_json(filtered, output_file, encrypt=False)
            print(f"\n✓ Exported defaults-only configuration to: {output_file}")
        elif choice == '7':
            from config.defaults.default_detector import DefaultDetector
            detector = DefaultDetector()
            filtered = detector.filter_defaults(config, include_defaults=False, include_custom=True)
            output_file = filename.replace('.json', '_custom_only.json')
            from config.storage.json_storage import save_config_json
            save_config_json(filtered, output_file, encrypt=False)
            print(f"\n✓ Exported custom-only configuration to: {output_file}")
        elif choice == '8':
            print("\nExiting...")
            break
        else:
            print("  ✗ Invalid choice")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
