"""
Application search functionality for CLI.

Provides search capability to find applications by name (3 character minimum).
"""

from typing import List, Optional, Dict, Any


def search_applications(
    api_client, search_term: str, folder: Optional[str] = None, min_length: int = 3
) -> List[Dict[str, Any]]:
    """
    Search for applications by name.

    Args:
        api_client: PrismaAccessAPIClient instance
        search_term: Search term (minimum length enforced)
        folder: Optional folder name to search in
        min_length: Minimum search term length (default: 3)

    Returns:
        List of matching application dictionaries
    """
    if len(search_term) < min_length:
        return []

    try:
        # Get all applications
        if folder:
            applications = api_client.get_all_applications(folder=folder)
        else:
            # Search across all folders
            from prisma.pull.folder_capture import FolderCapture

            folder_capture = FolderCapture(api_client)
            folders = folder_capture.list_folders_for_capture(include_defaults=True)

            applications = []
            seen_ids = set()
            for folder_name in folders:
                try:
                    folder_apps = api_client.get_all_applications(folder=folder_name)
                    for app in folder_apps:
                        app_id = app.get("id")
                        if app_id and app_id not in seen_ids:
                            seen_ids.add(app_id)
                            applications.append(app)
                except Exception:
                    continue

        # Filter by search term (case-insensitive)
        search_lower = search_term.lower()
        matches = [
            app for app in applications if search_lower in app.get("name", "").lower()
        ]

        return matches

    except Exception as e:
        print(f"  ⚠ Error searching applications: {e}")
        return []


def interactive_application_search(
    api_client, folder: Optional[str] = None
) -> List[str]:
    """
    Interactive application search and selection.

    Args:
        api_client: PrismaAccessAPIClient instance
        folder: Optional folder name to search in

    Returns:
        List of selected application names
    """
    selected_apps = []

    print("\n" + "-" * 60)
    print("CUSTOM APPLICATION SEARCH")
    print("-" * 60)
    print("Search for applications by name (minimum 3 characters)")
    print("Enter application names to add, or 'done' when finished")
    print("Enter 'list' to see recent matches, 'clear' to start over")

    while True:
        search_term = input("\nSearch term (or 'done'/'list'/'clear'): ").strip()

        if not search_term:
            continue

        if search_term.lower() == "done":
            break

        if search_term.lower() == "clear":
            selected_apps = []
            print("  ✓ Cleared selection")
            continue

        if search_term.lower() == "list":
            if selected_apps:
                print(f"\nCurrently selected ({len(selected_apps)} applications):")
                for i, app_name in enumerate(selected_apps, 1):
                    print(f"  {i}. {app_name}")
            else:
                print("\nNo applications selected yet")
            continue

        if len(search_term) < 3:
            print(
                f"  ⚠ Search term must be at least 3 characters (you entered {len(search_term)})"
            )
            continue

        # Search for applications
        print(f"\nSearching for applications matching '{search_term}'...")
        matches = search_applications(api_client, search_term, folder=folder)

        if not matches:
            print(f"  No applications found matching '{search_term}'")
            continue

        # Show matches
        print(f"\nFound {len(matches)} matching application(s):")
        for i, app in enumerate(matches[:20], 1):  # Show first 20
            app_name = app.get("name", "Unknown")
            app_id = app.get("id", "Unknown")
            already_selected = app_name in selected_apps
            status = " [ALREADY SELECTED]" if already_selected else ""
            print(f"  {i}. {app_name} (ID: {app_id[:20]}...){status}")

        if len(matches) > 20:
            print(f"  ... and {len(matches) - 20} more matches")

        # Ask which to add
        selection = input(
            "\nEnter number(s) to add (comma-separated), or press Enter to skip: "
        ).strip()

        if selection:
            try:
                indices = []
                for part in selection.split(","):
                    part = part.strip()
                    idx = int(part)
                    if 1 <= idx <= min(20, len(matches)):
                        indices.append(idx - 1)

                for idx in indices:
                    app_name = matches[idx].get("name", "")
                    if app_name and app_name not in selected_apps:
                        selected_apps.append(app_name)
                        print(f"  ✓ Added: {app_name}")
                    elif app_name in selected_apps:
                        print(f"  ⚠ Already selected: {app_name}")
            except ValueError:
                print("  ⚠ Invalid selection")

    return selected_apps
