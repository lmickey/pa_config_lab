#!/usr/bin/env python3
"""
Phase 5c: Application API Details Viewer

This script logs into a tenant and retrieves the full API information
for a specific application, displaying the raw JSON output.
"""

import sys
import json
import getpass
from typing import Dict, Any, Optional, List


def get_application_by_name(api_client, app_name: str, folder: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Find an application by name.
    
    Args:
        api_client: PrismaAccessAPIClient instance
        app_name: Application name to find
        folder: Optional folder name to search in
        
    Returns:
        Application dictionary if found, None otherwise
    """
    try:
        # Get all applications
        if folder:
            applications = api_client.get_all_applications(folder=folder)
        else:
            # Try to get from all folders
            applications = []
            from prisma.pull.folder_capture import FolderCapture
            folder_capture = FolderCapture(api_client)
            folders = folder_capture.list_folders_for_capture(include_defaults=True)
            
            for folder_name in folders:
                try:
                    folder_apps = api_client.get_all_applications(folder=folder_name)
                    applications.extend(folder_apps)
                except Exception:
                    continue
        
        # Find application by name (case-insensitive)
        app_name_lower = app_name.lower()
        for app in applications:
            if app.get('name', '').lower() == app_name_lower:
                return app
        
        return None
        
    except Exception as e:
        print(f"  ✗ Error searching for application: {e}")
        return None


def get_application_by_id(api_client, app_id: str) -> Optional[Dict[str, Any]]:
    """
    Get application details by ID.
    
    Args:
        api_client: PrismaAccessAPIClient instance
        app_id: Application ID
        
    Returns:
        Application dictionary if found, None otherwise
    """
    try:
        from prisma.api_endpoints import APIEndpoints
        
        url = APIEndpoints.application(app_id)
        response = api_client._make_request('GET', url)
        
        # Handle different response formats
        if isinstance(response, dict):
            if 'data' in response:
                return response['data']
            else:
                return response
        else:
            return response
            
    except Exception as e:
        print(f"  ✗ Error fetching application by ID: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_applications_page(api_client, folder: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple:
    """
    Get a paginated page of applications.
    
    Args:
        api_client: PrismaAccessAPIClient instance
        folder: Optional folder name
        page: Page number (1-based)
        page_size: Number of items per page
        
    Returns:
        Tuple of (applications_list, has_more, total_count)
    """
    try:
        offset = (page - 1) * page_size
        
        if folder:
            # Get single page from specific folder
            applications = api_client.get_applications(folder=folder, limit=page_size, offset=offset)
            # Check if there are more (if we got a full page, there might be more)
            has_more = len(applications) == page_size
            return applications, has_more, None
        else:
            # For all folders, we need to aggregate
            # This is more complex, so we'll get from first folder for now
            from prisma.pull.folder_capture import FolderCapture
            folder_capture = FolderCapture(api_client)
            folders = folder_capture.list_folders_for_capture(include_defaults=True)
            
            if not folders:
                return [], False, 0
            
            # Get from first folder for pagination
            # Note: This only paginates within one folder
            # For true multi-folder pagination, we'd need to aggregate first
            applications = api_client.get_applications(folder=folders[0], limit=page_size, offset=offset)
            has_more = len(applications) == page_size
            
            return applications, has_more, None
        
    except Exception as e:
        print(f"  ✗ Error getting applications page: {e}")
        import traceback
        traceback.print_exc()
        return [], False, 0


def main():
    """Main function."""
    print("=" * 60)
    print("Phase 5c: Application API Details Viewer")
    print("=" * 60)
    
    try:
        from prisma.api_client import PrismaAccessAPIClient
        from load_settings import prisma_access_auth
        
        # Get tenant credentials
        print("\n" + "-" * 60)
        print("TENANT AUTHENTICATION")
        print("-" * 60)
        tsg = input("Enter TSG ID: ").strip()
        api_user = input("Enter API Client ID: ").strip()
        api_secret = getpass.getpass("Enter API Client Secret: ")
        
        if not all([tsg, api_user, api_secret]):
            print("  ✗ Missing credentials")
            return 1
        
        # Initialize API client
        print("\nInitializing API client...")
        try:
            token = prisma_access_auth(tsg, api_user, api_secret)
            if not token:
                print("  ✗ Failed to authenticate")
                return 1
            api_client = PrismaAccessAPIClient(tsg, api_user, api_secret)
            print("  ✓ API client initialized")
        except Exception as e:
            print(f"  ✗ Failed to initialize API client: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # Get folder (optional)
        print("\n" + "-" * 60)
        print("FOLDER SELECTION (Optional)")
        print("-" * 60)
        folder_choice = input("Search in specific folder? (y/n): ").strip().lower()
        folder = None
        
        if folder_choice == 'y':
            from prisma.pull.folder_capture import FolderCapture
            folder_capture = FolderCapture(api_client)
            folders = folder_capture.list_folders_for_capture(include_defaults=True)
            
            if folders:
                print("\nAvailable folders:")
                for i, folder_name in enumerate(folders, 1):
                    print(f"  {i}. {folder_name}")
                
                folder_idx = input("\nEnter folder number (or press Enter for all): ").strip()
                if folder_idx:
                    try:
                        idx = int(folder_idx) - 1
                        if 0 <= idx < len(folders):
                            folder = folders[idx]
                            print(f"  ✓ Selected folder: {folder}")
                    except ValueError:
                        print("  ⚠ Invalid selection, searching all folders")
        
        # Main application viewing loop
        while True:
            # Get application name or ID
            print("\n" + "-" * 60)
            print("APPLICATION SELECTION")
            print("-" * 60)
            print("Options:")
            print("  1. Enter application name")
            print("  2. Enter application ID")
            print("  3. List available applications")
            print("  4. Exit")
            
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == '4':
                print("\nExiting...")
                return 0
            
            app = None
            app_id = None
            app_name = None
            
            if choice == '1':
                app_name = input("Enter application name: ").strip()
                if not app_name:
                    print("  ✗ No application name provided")
                    continue
                
                print(f"\nSearching for application: {app_name}")
                app = get_application_by_name(api_client, app_name, folder=folder)
                
                if app:
                    app_id = app.get('id') or app.get('fqid') or app.get('_id')
                    print(f"  ✓ Found application: {app.get('name', 'Unknown')}")
                    if app_id:
                        print(f"    ID: {app_id}")
                else:
                    print(f"  ✗ Application '{app_name}' not found")
                    continue
            
            elif choice == '2':
                app_id = input("Enter application ID: ").strip()
                if not app_id:
                    print("  ✗ No application ID provided")
                    continue
                
                print(f"\nFetching application by ID: {app_id}")
                app = get_application_by_id(api_client, app_id)
                
                if app:
                    app_name = app.get('name', 'Unknown')
                    print(f"  ✓ Found application: {app_name}")
                else:
                    print(f"  ✗ Application with ID '{app_id}' not found")
                    continue
            
            elif choice == '3':
                # Paginated application listing
                page = 1
                page_size = 20
                selected_app = None
                
                while True:
                    print(f"\nLoading page {page}...")
                    applications, has_more, total = get_applications_page(api_client, folder=folder, page=page, page_size=page_size)
                    
                    if not applications:
                        if page == 1:
                            print("  ✗ No applications found")
                            break
                        else:
                            print("  ⚠ No more applications")
                            if selected_app:
                                app = selected_app
                                break
                            else:
                                print("  Returning to previous page...")
                                page -= 1
                                continue
                    
                    print(f"\nPage {page} ({len(applications)} applications):")
                    for i, app_item in enumerate(applications, 1):
                        app_name_item = app_item.get('name', 'Unknown')
                        # Try different ID field names
                        app_id_item = app_item.get('id') or app_item.get('fqid') or app_item.get('_id') or 'Unknown'
                        if app_id_item != 'Unknown' and isinstance(app_id_item, str):
                            app_id_display = app_id_item[:20] + '...' if len(app_id_item) > 20 else app_id_item
                        else:
                            app_id_display = 'Unknown'
                        global_idx = (page - 1) * page_size + i
                        print(f"  {global_idx}. {app_name_item} (ID: {app_id_display})")
                    
                    print("\nOptions:")
                    print("  - Enter application number to view details")
                    if has_more:
                        print("  - Enter 'n' for next page")
                    if page > 1:
                        print("  - Enter 'p' for previous page")
                    print("  - Enter 'q' to quit")
                    
                    selection = input("\nSelection: ").strip().lower()
                    
                    if selection == 'q':
                        print("  Cancelled")
                        break
                    elif selection == 'n' and has_more:
                        page += 1
                        continue
                    elif selection == 'p' and page > 1:
                        page -= 1
                        continue
                    elif selection.isdigit():
                        try:
                            global_idx = int(selection)
                            # Calculate which page this is on
                            target_page = ((global_idx - 1) // page_size) + 1
                            local_idx = ((global_idx - 1) % page_size)
                            
                            if target_page != page:
                                # Need to load the correct page
                                page = target_page
                                continue
                            
                            if 0 <= local_idx < len(applications):
                                selected_app = applications[local_idx]
                                app = selected_app
                                app_id = app.get('id') or app.get('fqid') or app.get('_id')
                                app_name = app.get('name', 'Unknown')
                                print(f"\n  ✓ Selected: {app_name}")
                                break
                            else:
                                print("  ✗ Invalid selection")
                                continue
                        except ValueError:
                            print("  ✗ Invalid selection")
                            continue
                    else:
                        print("  ✗ Invalid selection")
                        continue
                
                if not app:
                    print("  ✗ No application selected")
                    continue
            
            else:
                print("  ✗ Invalid choice")
                continue
            
            # If we got here, we have an app selected
            if not app:
                continue
            
            # Get full application details
            if not app_id:
                # Try different ID field names
                app_id = app.get('id') or app.get('fqid') or app.get('_id')
            
            if not app_id:
                print("  ⚠ Could not determine application ID")
                print("  Available fields in application object:")
                for key in app.keys():
                    print(f"    - {key}: {type(app[key]).__name__}")
                print("\n  Showing available data from list response:")
                print("=" * 60)
                print(json.dumps(app, indent=2, ensure_ascii=False))
                print("=" * 60)
                
                # Ask if user wants to continue or try another
                continue_choice = input("\nTry another application? (y/n): ").strip().lower()
                if continue_choice == 'y':
                    continue
                else:
                    return 0
            
            print("\n" + "-" * 60)
            print("FETCHING FULL APPLICATION DETAILS")
            print("-" * 60)
            print(f"Application: {app_name}")
            print(f"ID: {app_id}")
            
            # Fetch full details by ID
            full_app = get_application_by_id(api_client, app_id)
            
            if not full_app:
                print("  ✗ Failed to fetch full application details")
                print("  Showing partial details from search result:")
                full_app = app
            
            # Display raw JSON
            print("\n" + "=" * 60)
            print("RAW JSON OUTPUT")
            print("=" * 60)
            print(json.dumps(full_app, indent=2, ensure_ascii=False))
            print("=" * 60)
            
            # Show key fields
            print("\n" + "-" * 60)
            print("KEY FIELDS SUMMARY")
            print("-" * 60)
            print(f"Name: {full_app.get('name', 'N/A')}")
            print(f"ID: {full_app.get('id', 'N/A')}")
            print(f"Folder: {full_app.get('folder', 'N/A')}")
            
            if 'description' in full_app:
                print(f"Description: {full_app.get('description', 'N/A')}")
            
            if 'category' in full_app:
                print(f"Category: {full_app.get('category', 'N/A')}")
            
            if 'subcategory' in full_app:
                print(f"Subcategory: {full_app.get('subcategory', 'N/A')}")
            
            if 'technology' in full_app:
                print(f"Technology: {full_app.get('technology', 'N/A')}")
            
            if 'risk' in full_app:
                print(f"Risk: {full_app.get('risk', 'N/A')}")
            
            if 'parent_app' in full_app:
                print(f"Parent App: {full_app.get('parent_app', 'N/A')}")
            
            if 'timeout' in full_app:
                print(f"Timeout: {full_app.get('timeout', 'N/A')}")
            
            if 'tcp_half_closed_timeout' in full_app:
                print(f"TCP Half Closed Timeout: {full_app.get('tcp_half_closed_timeout', 'N/A')}")
            
            if 'tcp_time_wait_timeout' in full_app:
                print(f"TCP Time Wait Timeout: {full_app.get('tcp_time_wait_timeout', 'N/A')}")
            
            if 'udp_timeout' in full_app:
                print(f"UDP Timeout: {full_app.get('udp_timeout', 'N/A')}")
            
            print("-" * 60)
            
            # Option to save to file
            save_choice = input("\nSave JSON to file? (y/n): ").strip().lower()
            if save_choice == 'y':
                safe_name = app_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                if app_id:
                    filename = f"app_{safe_name}_{app_id[:8]}.json"
                else:
                    filename = f"app_{safe_name}.json"
                with open(filename, 'w') as f:
                    json.dump(full_app, f, indent=2, ensure_ascii=False)
                print(f"  ✓ Saved to: {filename}")
            
            # Ask if user wants to view another application
            another_choice = input("\nView another application? (y/n): ").strip().lower()
            if another_choice != 'y':
                return 0
            # Otherwise continue the loop to select another application
        
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        return 1
    except Exception as e:
        print(f"\n  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
