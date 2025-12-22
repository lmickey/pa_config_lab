#!/usr/bin/env python3
"""
Phase 5 Test Suite: Push Functionality - Full Integration Test

This test performs a complete pull → save → push workflow:
1. Pull configuration from source tenant
2. Save to backup file
3. Push configuration to destination tenant

Requires two sets of tenant credentials (source and destination).
"""

import sys
import json
import getpass
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path


def multi_select_prompt(items: List[str], item_type: str, allow_multiple: bool = True, allow_none: bool = True) -> Optional[List[str]]:
    """
    Prompt user to select items from a list.
    
    Args:
        items: List of item names
        item_type: Type of items (e.g., "folder", "snippet")
        allow_multiple: Whether to allow multiple selections
        allow_none: Whether to allow selecting none (returns None)
        
    Returns:
        List of selected item names, or None if none selected
    """
    if not items:
        return []
    
    print(f"\nAvailable {item_type}s:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")
    
    if allow_multiple:
        print(f"\nEnter {item_type} numbers to select (comma-separated):")
        print("  - Press Enter for all")
        if allow_none:
            print("  - Enter '0' or 'none' for none")
    else:
        print(f"\nEnter {item_type} number to select:")
        if allow_none:
            print("  - Enter '0' or 'none' for none")
    
    try:
        selection = input("Selection: ").strip().lower()
        
        if not selection:
            # Select all if empty
            return items
        
        # Check for "none" option
        if allow_none and (selection == '0' or selection == 'none'):
            return None
        
        # Parse selections
        indices = []
        for part in selection.split(','):
            part = part.strip()
            try:
                idx = int(part)
                if idx == 0 and allow_none:
                    return None
                if 1 <= idx <= len(items):
                    indices.append(idx - 1)
                else:
                    print(f"  Invalid number: {idx}. Please enter numbers between 1 and {len(items)}")
                    return []
            except ValueError:
                if part.lower() == 'none' and allow_none:
                    return None
                print(f"  Invalid input: '{part}'. Please enter numbers separated by commas")
                return []
        
        # Return selected items
        selected = [items[i] for i in indices]
        return selected
        
    except (KeyboardInterrupt, EOFError):
        print("\n\nSelection cancelled")
        return []


def get_folders_and_snippets(api_client) -> tuple:
    """
    Get list of folders and snippets from tenant.
    
    Returns:
        Tuple of (folders list, snippets list)
    """
    folders = []
    snippets = []
    
    try:
        from prisma.pull.folder_capture import FolderCapture
        folder_capture = FolderCapture(api_client)
        folders = folder_capture.list_folders_for_capture(include_defaults=True)
    except Exception as e:
        print(f"  ⚠ Warning: Could not list folders: {e}")
    
    try:
        from prisma.pull.snippet_capture import SnippetCapture
        snippet_capture = SnippetCapture(api_client)
        snippet_list = snippet_capture.discover_snippets()
        snippets = [s.get('name', '') for s in snippet_list if s.get('name')]
    except Exception as e:
        print(f"  ⚠ Warning: Could not list snippets: {e}")
    
    return folders, snippets


def generate_backup_filename(source_tsg: str) -> str:
    """
    Generate automated backup filename with timestamp.
    
    Args:
        source_tsg: Source TSG ID
        
    Returns:
        Filename string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_tsg{source_tsg}_{timestamp}.json"
    return filename


def test_full_pull_push_workflow():
    """Test complete pull → save → push workflow."""
    print("\n" + "=" * 60)
    print("Phase 5: Full Pull → Save → Push Workflow")
    print("=" * 60)
    
    try:
        from prisma.api_client import PrismaAccessAPIClient
        from load_settings import prisma_access_auth
        from prisma.pull.config_pull import pull_configuration
        from prisma.push.config_push import push_configuration
        from config.storage.json_storage import save_config_json, load_config_json, derive_key
        import os
        
        # Choose source: file or tenant
        print("\n" + "-" * 60)
        print("CONFIGURATION SOURCE")
        print("-" * 60)
        print("Select configuration source:")
        print("  1. Load from saved backup file")
        print("  2. Pull from tenant")
        
        source_choice = input("Enter choice (1 or 2): ").strip()
        
        config = None
        backup_filename = None
        
        if source_choice == "1":
            # Load from file
            print("\n" + "-" * 60)
            print("LOAD FROM BACKUP FILE")
            print("-" * 60)
            filename = input("Enter backup filename: ").strip()
            
            if not filename:
                print("  ✗ No filename provided")
                return False
            
            if not os.path.exists(filename):
                print(f"  ✗ File not found: {filename}")
                return False
            
            print(f"Loading configuration from: {filename}")
            
            # Try to detect if encrypted
            # Better detection: encrypted files won't start with valid JSON characters
            encrypted = None
            try:
                with open(filename, 'rb') as f:
                    data = f.read()
                
                # Try to decode as UTF-8
                try:
                    decoded = data.decode('utf-8').strip()
                    # Check if it starts with valid JSON characters
                    if decoded.startswith('{') or decoded.startswith('['):
                        # Try to parse as JSON to confirm
                        try:
                            json.loads(decoded)
                            encrypted = False
                        except json.JSONDecodeError:
                            # Can decode but not valid JSON - likely encrypted
                            encrypted = True
                    else:
                        # Doesn't start with JSON - likely encrypted (Fernet starts with 'gAAAAA')
                        encrypted = True
                except UnicodeDecodeError:
                    # Can't decode as UTF-8 - definitely encrypted
                    encrypted = True
            except Exception as e:
                print(f"  ⚠ Warning: Could not determine encryption status: {e}")
                encrypted = None  # Let load_config_json auto-detect
            
            try:
                cipher = None
                if encrypted:
                    decrypt_password = getpass.getpass("Enter password to decrypt backup: ")
                    cipher = derive_key(decrypt_password)
                    # Pass encrypted=True explicitly when we know it's encrypted
                    config = load_config_json(filename, cipher=cipher, encrypted=True)
                elif encrypted is False:
                    # File is not encrypted
                    config = load_config_json(filename, cipher=None, encrypted=False)
                else:
                    # Auto-detect encryption
                    config = load_config_json(filename, cipher=None, encrypted=None)
                if not config:
                    print("  ✗ Failed to load configuration")
                    return False
                print("  ✓ Configuration loaded successfully")
                backup_filename = filename
                loaded_config = config  # Set loaded_config for consistency
            except Exception as e:
                print(f"  ✗ Failed to load configuration: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        elif source_choice == "2":
            # Pull from tenant
            print("\n" + "-" * 60)
            print("SOURCE TENANT (Configuration to Pull)")
            print("-" * 60)
            source_tsg = input("Enter Source TSG ID: ").strip()
            source_api_user = input("Enter Source API Client ID: ").strip()
            source_api_secret = getpass.getpass("Enter Source API Client Secret: ")
            
            if not all([source_tsg, source_api_user, source_api_secret]):
                print("  ✗ Missing source tenant credentials")
                return False
            
            # Initialize source API client
            print("\nInitializing source API client...")
            try:
                token = prisma_access_auth(source_tsg, source_api_user, source_api_secret)
                if not token:
                    print("  ✗ Failed to authenticate with source tenant")
                    return False
                source_client = PrismaAccessAPIClient(source_tsg, source_api_user, source_api_secret)
                print("  ✓ Source API client initialized")
            except Exception as e:
                print(f"  ✗ Failed to initialize source API client: {e}")
                return False
            
            # Get folders and snippets from source
            print("\nDiscovering folders and snippets from source tenant...")
            source_folders, source_snippets = get_folders_and_snippets(source_client)
            
            if not source_folders and not source_snippets:
                print("  ✗ No folders or snippets found in source tenant")
                return False
            
            print(f"  ✓ Found {len(source_folders)} folders and {len(source_snippets)} snippets")
            
            # Select folders to pull
            selected_folders = None
            if source_folders:
                selected_folders = multi_select_prompt(source_folders, "folder", allow_multiple=True, allow_none=True)
                if selected_folders is None:
                    print("  ℹ No folders selected (will skip folders)")
                    selected_folders = []
                elif selected_folders:
                    print(f"  ✓ Selected {len(selected_folders)} folder(s)")
            
            # Select snippets to pull
            selected_snippets = None
            if source_snippets:
                selected_snippets = multi_select_prompt(source_snippets, "snippet", allow_multiple=True, allow_none=True)
                if selected_snippets is None:
                    print("  ℹ No snippets selected (will skip snippets)")
                    selected_snippets = []
                elif selected_snippets:
                    print(f"  ✓ Selected {len(selected_snippets)} snippet(s)")
            
            if not selected_folders and not selected_snippets:
                print("  ✗ No folders or snippets selected")
                return False
            
            # Pull configuration from source
            print("\n" + "-" * 60)
            print("PULLING CONFIGURATION FROM SOURCE")
            print("-" * 60)
            print(f"Pulling configuration from source tenant (TSG: {source_tsg})...")
            print(f"Folders: {', '.join(selected_folders) if selected_folders else 'None'}")
            print(f"Snippets: {', '.join(selected_snippets) if selected_snippets else 'None'}")
            
            # Ask about custom applications
            application_names = None
            print("\n" + "-" * 60)
            print("CUSTOM APPLICATIONS")
            print("-" * 60)
            has_custom_apps = input("Do you have any custom applications to capture? (y/n, default=n): ").strip().lower()
            
            if has_custom_apps == 'y':
                from cli.application_search import interactive_application_search
                print("\nNote: Applications are rarely custom. Most applications are predefined.")
                print("Only specify applications that you have created or customized.")
                application_names = interactive_application_search(source_client, folder=None)
                
                if application_names:
                    print(f"\n✓ Will capture {len(application_names)} custom application(s):")
                    for app_name in application_names:
                        print(f"  - {app_name}")
                else:
                    print("\n  ℹ No custom applications selected")
            else:
                print("  ✓ Skipping applications (assuming all are predefined)")
            
            try:
                config = pull_configuration(
                    source_client,
                    folder_names=selected_folders if selected_folders else None,
                    snippet_names=selected_snippets if selected_snippets else None,
                    include_defaults=False,
                    include_snippets=True,
                    include_objects=True,
                    include_profiles=True,
                    detect_defaults=True,
                    filter_defaults=False,
                    application_names=application_names
                )
                print("  ✓ Configuration pulled successfully")
                loaded_config = config  # Set loaded_config for consistency
            except Exception as e:
                print(f"  ✗ Failed to pull configuration: {e}")
                import traceback
                traceback.print_exc()
                return False
            
            # Save configuration to backup file
            print("\n" + "-" * 60)
            print("SAVING CONFIGURATION BACKUP")
            print("-" * 60)
            backup_filename = generate_backup_filename(source_tsg)
            print(f"Saving configuration to: {backup_filename}")
            
            try:
                # Ask for encryption password
                encrypt_password = getpass.getpass("Enter password for backup encryption (or press Enter for no encryption): ")
                cipher = None
                encrypt = bool(encrypt_password)
                
                if encrypt:
                    cipher = derive_key(encrypt_password)
                
                save_config_json(config, backup_filename, cipher=cipher, encrypt=encrypt)
                print(f"  ✓ Configuration saved to: {backup_filename}")
            except Exception as e:
                print(f"  ✗ Failed to save configuration: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("  ✗ Invalid choice")
            return False
        
        if not config:
            print("  ✗ No configuration loaded")
            return False
        
        # Use consistent variable name
        loaded_config = config
        
        # Show what's in the configuration
        print("\n" + "-" * 60)
        print("CONFIGURATION CONTENTS")
        print("-" * 60)
        security_policies = loaded_config.get('security_policies', {})
        folders = security_policies.get('folders', [])
        snippets = security_policies.get('snippets', [])
        
        folder_names = [f.get('name', 'Unknown') for f in folders]
        snippet_names = [s.get('name', 'Unknown') for s in snippets]
        
        print(f"Folders in backup: {len(folder_names)}")
        for i, name in enumerate(folder_names, 1):
            print(f"  {i}. {name}")
        
        print(f"\nSnippets in backup: {len(snippet_names)}")
        for i, name in enumerate(snippet_names, 1):
            print(f"  {i}. {name}")
        
        # Get destination tenant credentials
        print("\n" + "-" * 60)
        print("DESTINATION TENANT (Configuration to Push)")
        print("-" * 60)
        dest_tsg = input("Enter Destination TSG ID: ").strip()
        dest_api_user = input("Enter Destination API Client ID: ").strip()
        dest_api_secret = getpass.getpass("Enter Destination API Client Secret: ")
        
        if not all([dest_tsg, dest_api_user, dest_api_secret]):
            print("  ✗ Missing destination tenant credentials")
            return False
        
        # Initialize destination API client
        print("\nInitializing destination API client...")
        try:
            token = prisma_access_auth(dest_tsg, dest_api_user, dest_api_secret)
            if not token:
                print("  ✗ Failed to authenticate with destination tenant")
                return False
            dest_client = PrismaAccessAPIClient(dest_tsg, dest_api_user, dest_api_secret)
            print("  ✓ Destination API client initialized")
        except Exception as e:
            print(f"  ✗ Failed to initialize destination API client: {e}")
            return False
        
        # Select what to push
        print("\n" + "-" * 60)
        print("SELECT ITEMS TO PUSH")
        print("-" * 60)
        
        push_folders = None
        if folder_names:
            push_folders = multi_select_prompt(folder_names, "folder", allow_multiple=True, allow_none=True)
            if push_folders is None:
                print("  ℹ No folders selected (will skip folders)")
                push_folders = []
            elif push_folders:
                print(f"  ✓ Selected {len(push_folders)} folder(s) to push")
        
        push_snippets = None
        if snippet_names:
            push_snippets = multi_select_prompt(snippet_names, "snippet", allow_multiple=True, allow_none=True)
            if push_snippets is None:
                print("  ℹ No snippets selected (will skip snippets)")
                push_snippets = []
            elif push_snippets:
                print(f"  ✓ Selected {len(push_snippets)} snippet(s) to push")
        
        if (push_folders is None or len(push_folders) == 0) and (push_snippets is None or len(push_snippets) == 0):
            print("  ⚠ No items selected to push")
            response = input("  Continue with dry-run only? (y/n): ").strip().lower()
            if response != 'y':
                print("  Push cancelled")
                return True
        
        # Ask for conflict strategy
        print("\nConflict Resolution Strategy:")
        print("  1. Skip (don't push conflicting items)")
        print("  2. Overwrite (replace existing)")
        print("  3. Rename (create with new name)")
        conflict_choice = input("Select strategy (1-3, default=1): ").strip() or "1"
        
        strategy_map = {"1": "skip", "2": "overwrite", "3": "rename"}
        conflict_strategy = strategy_map.get(conflict_choice, "skip")
        
        # Ask for dry-run
        dry_run_response = input("\nPerform dry-run first? (y/n, default=y): ").strip().lower() or "y"
        dry_run = dry_run_response == 'y'
        
        # Push configuration to destination
        print("\n" + "-" * 60)
        print("PUSHING CONFIGURATION TO DESTINATION")
        print("-" * 60)
        print(f"Pushing configuration to destination tenant (TSG: {dest_tsg})...")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE PUSH'}")
        print(f"Conflict Strategy: {conflict_strategy}")
        
        try:
            result = push_configuration(
                dest_client,
                loaded_config,
                folder_names=push_folders,
                snippet_names=push_snippets,
                dry_run=dry_run,
                conflict_strategy=conflict_strategy
            )
            
            if result.get('success'):
                print("\n  ✓ Push completed successfully")
                if dry_run:
                    print("  ⚠ This was a dry-run - no changes were made")
                else:
                    print("  ✓ Configuration has been pushed to destination tenant")
            else:
                print(f"\n  ✗ Push failed: {result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"  ✗ Failed to push configuration: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n" + "=" * 60)
        print("WORKFLOW COMPLETE")
        print("=" * 60)
        if backup_filename:
            print(f"Backup file: {backup_filename}")
        if source_choice == "2":
            print(f"Source TSG: {source_tsg}")
        print(f"Destination TSG: {dest_tsg}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE PUSH'}")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\nWorkflow cancelled by user")
        return False
    except Exception as e:
        print(f"\n  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run Phase 5 full integration test."""
    print("=" * 60)
    print("Phase 5: Push Functionality - Full Integration Test")
    print("=" * 60)
    print("\nThis test performs a complete workflow:")
    print("  1. Pull configuration from SOURCE tenant")
    print("  2. Save configuration to backup file")
    print("  3. Push configuration to DESTINATION tenant")
    print("\nYou will need credentials for BOTH tenants.")
    
    try:
        result = test_full_pull_push_workflow()
        
        if result:
            print("\n✓ Full workflow test completed successfully!")
            return 0
        else:
            print("\n✗ Full workflow test failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        return 1
    except Exception as e:
        print(f"\n✗ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
