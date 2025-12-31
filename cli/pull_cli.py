#!/usr/bin/env python3
"""
Command-Line Interface for Prisma Access Configuration Pull Operations.

This module provides a CLI for pulling configurations from Prisma Access tenants.
"""

import sys
import argparse
import json
import getpass
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.config_pull import pull_configuration
from prisma.pull.folder_capture import FolderCapture
from prisma.pull.snippet_capture import SnippetCapture
from load_settings import prisma_access_auth
from .application_search import interactive_application_search


def multi_select_prompt(
    items: list, item_type: str = "item", allow_multiple: bool = True
) -> list:
    """
    Prompt user to select items from a list (multi-select).

    Args:
        items: List of items to choose from
        item_type: Type of items (e.g., "folder", "snippet")
        allow_multiple: Whether to allow multiple selections

    Returns:
        List of selected items
    """
    if not items:
        return []

    print(f"\nAvailable {item_type}s:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")

    if allow_multiple:
        print(f"\nEnter {item_type} numbers to select (comma-separated, e.g., 1,3,5):")
        print("  Or press Enter to select all")
    else:
        print(f"\nEnter {item_type} number to select:")

    while True:
        try:
            selection = input("Selection: ").strip()

            if not selection and allow_multiple:
                # Select all
                return items

            if not selection:
                print("  Please enter a selection")
                continue

            # Parse selections
            indices = []
            for part in selection.split(","):
                part = part.strip()
                try:
                    idx = int(part)
                    if 1 <= idx <= len(items):
                        indices.append(idx - 1)  # Convert to 0-based
                    else:
                        print(
                            f"  Invalid number: {idx}. Please enter numbers between 1 and {len(items)}"
                        )
                        break
                except ValueError:
                    print(
                        f"  Invalid input: '{part}'. Please enter numbers separated by commas"
                    )
                    break
            else:
                # All indices were valid
                if indices:
                    selected = [items[i] for i in indices]
                    return selected
                else:
                    print("  No valid selections made")
        except KeyboardInterrupt:
            print("\n\nSelection cancelled")
            return []
        except Exception as e:
            print(f"  Error: {e}")
            continue


def get_folders_and_snippets(api_client: PrismaAccessAPIClient) -> tuple:
    """
    Get lists of available folders and snippets.

    Args:
        api_client: PrismaAccessAPIClient instance

    Returns:
        Tuple of (folders_list, snippets_list) where snippets_list contains dicts with 'name' and 'is_default'
    """
    folders = []
    snippets = []

    try:
        folder_capture = FolderCapture(api_client)
        folders = folder_capture.list_folders_for_capture(include_defaults=True)
    except Exception as e:
        print(f"  ⚠ Warning: Could not list folders: {e}")

    try:
        snippet_capture = SnippetCapture(api_client)
        snippet_list = snippet_capture.discover_snippets()
        # Return snippet dicts with metadata (including is_default)
        snippets = [s for s in snippet_list if s.get("name")]
    except Exception as e:
        print(f"  ⚠ Warning: Could not list snippets: {e}")

    return folders, snippets


def select_snippets_with_defaults_option(snippets: list) -> list:
    """
    Prompt user to select snippets with option to include defaults.

    Args:
        snippets: List of snippet dictionaries with 'name' and 'is_default' fields

    Returns:
        List of selected snippet names (including defaults if option 1 selected)
    """
    if not snippets:
        return []

    # Separate defaults and custom snippets
    default_snippets = [s for s in snippets if s.get("is_default", False)]
    custom_snippets = [s for s in snippets if not s.get("is_default", False)]

    # Display menu
    print("\nSnippets:")
    default_count = len(default_snippets)
    if default_count > 0:
        print(
            f"  1. Include defaults ({default_count} default snippet{'s' if default_count != 1 else ''})"
        )
    else:
        print("  1. Include defaults (no defaults available)")

    # List custom snippets starting at option 2
    for i, snippet in enumerate(custom_snippets, 2):
        print(f"  {i}. {snippet.get('name', '')} (custom)")

    if not custom_snippets:
        print("  (No custom snippets available)")

    print(f"\nEnter snippet numbers to select (comma-separated, e.g., 1,3,5):")
    print("  Or press Enter to skip snippets")

    while True:
        try:
            selection = input("Selection: ").strip()

            if not selection:
                return []

            # Parse selections
            indices = []
            for part in selection.split(","):
                part = part.strip()
                try:
                    idx = int(part)
                    max_option = 1 + len(custom_snippets)  # Option 1 + custom snippets
                    if 1 <= idx <= max_option:
                        indices.append(idx)
                    else:
                        print(
                            f"  Invalid number: {idx}. Please enter numbers between 1 and {max_option}"
                        )
                        break
                except ValueError:
                    print(
                        f"  Invalid input: '{part}'. Please enter numbers separated by commas"
                    )
                    break
            else:
                # All indices were valid
                if indices:
                    selected_names = []

                    # Check if option 1 (include defaults) was selected
                    include_defaults = 1 in indices
                    if include_defaults:
                        selected_names.extend(
                            [s.get("name", "") for s in default_snippets]
                        )

                    # Add selected custom snippets (indices 2+)
                    for idx in indices:
                        if idx > 1:  # Skip option 1, already handled
                            custom_idx = (
                                idx - 2
                            )  # Convert to 0-based index for custom_snippets
                            if 0 <= custom_idx < len(custom_snippets):
                                selected_names.append(
                                    custom_snippets[custom_idx].get("name", "")
                                )

                    return selected_names
                else:
                    print("  No valid selections made")
        except KeyboardInterrupt:
            print("\n\nSelection cancelled")
            return []
        except Exception as e:
            print(f"  Error: {e}")
            continue


def format_pull_summary(config: dict):
    """Format and print pull summary."""
    stats = config.get("metadata", {}).get("pull_stats", {})

    print("\n" + "=" * 60)
    print("Pull Summary")
    print("=" * 60)
    print(f"Folders captured: {stats.get('folders', 0)}")
    print(f"Security rules: {stats.get('rules', 0)}")
    print(f"Objects: {stats.get('objects', 0)}")
    print(f"Profiles: {stats.get('profiles', 0)}")
    print(f"Snippets: {stats.get('snippets', 0)}")

    if "defaults_detected" in stats:
        print(f"Defaults detected: {stats.get('defaults_detected', 0)}")

    if "dependency_report" in config.get("metadata", {}):
        dep_report = config["metadata"]["dependency_report"]
        validation = dep_report.get("validation", {})
        if not validation.get("valid", True):
            missing = validation.get("missing_dependencies", {})
            print(
                f"\n⚠ Dependency Warnings: {len(missing)} objects have missing dependencies"
            )
        else:
            print(f"\n✓ All dependencies resolved")

    print(f"Errors: {stats.get('errors', 0)}")
    print(f"Elapsed time: {stats.get('elapsed_seconds', 0):.2f} seconds")
    print("=" * 60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Pull Prisma Access configuration from SCM tenant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pull all configuration (will prompt for client secret)
  %(prog)s --tsg TSG_ID --client-id CLIENT_ID

  # Pull specific folders only
  %(prog)s --tsg TSG_ID --client-id CLIENT_ID --folders "Mobile Users" "Shared"

  # Pull and save to file
  %(prog)s --tsg TSG_ID --client-id CLIENT_ID --output config.json

  # Pull without defaults
  %(prog)s --tsg TSG_ID --client-id CLIENT_ID --exclude-defaults

  # Pull and filter out defaults
  %(prog)s --tsg TSG_ID --client-id CLIENT_ID --filter-defaults
        """,
    )

    # Required arguments
    parser.add_argument("--tsg", required=True, help="TSG ID")
    parser.add_argument("--client-id", required=True, help="API Client ID")
    # Note: Client secret will be prompted securely, not passed as argument

    # Pull options
    parser.add_argument(
        "--folders",
        nargs="+",
        help="Specific folders to pull (if not specified, will prompt for selection)",
    )
    parser.add_argument(
        "--snippets",
        nargs="+",
        help="Specific snippets to pull (if not specified and --no-snippets not set, will prompt for selection)",
    )
    parser.add_argument(
        "--include-defaults", action="store_true", help="Include default folders"
    )
    parser.add_argument(
        "--exclude-defaults",
        action="store_true",
        help="Exclude default folders (default)",
    )
    parser.add_argument(
        "--no-snippets", action="store_true", help="Do not pull snippets"
    )
    parser.add_argument("--no-objects", action="store_true", help="Do not pull objects")
    parser.add_argument(
        "--no-profiles", action="store_true", help="Do not pull profiles"
    )

    # Default detection options
    parser.add_argument(
        "--detect-defaults",
        action="store_true",
        default=True,
        help="Detect defaults (default: True)",
    )
    parser.add_argument(
        "--no-detect-defaults",
        dest="detect_defaults",
        action="store_false",
        help="Do not detect defaults",
    )
    parser.add_argument(
        "--filter-defaults", action="store_true", help="Filter out defaults from result"
    )

    # Output options
    parser.add_argument("--output", "-o", help="Output file path (JSON format)")
    parser.add_argument(
        "--no-encrypt", action="store_true", help="Do not encrypt output file"
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty print JSON output"
    )

    # Dependency options
    parser.add_argument(
        "--validate-dependencies",
        action="store_true",
        default=True,
        help="Validate dependencies (default: True)",
    )
    parser.add_argument(
        "--no-validate-dependencies",
        dest="validate_dependencies",
        action="store_false",
        help="Do not validate dependencies",
    )

    args = parser.parse_args()

    try:
        # Prompt for client secret securely
        client_secret = getpass.getpass("Enter API Client Secret: ")
        if not client_secret:
            print("✗ Client secret is required")
            return 1

        # Authenticate
        print("Authenticating...")
        token = prisma_access_auth(args.tsg, args.client_id, client_secret)
        if not token:
            print("✗ Authentication failed")
            return 1

        # Initialize API client
        print("Initializing API client...")
        api_client = PrismaAccessAPIClient(args.tsg, args.client_id, client_secret)
        print("✓ API client initialized")

        # Determine which folders and snippets to pull
        folders_to_pull = args.folders
        snippets_to_pull = args.snippets
        include_snippets = not args.no_snippets

        # Ask about custom applications (default to no)
        application_names = None
        if not args.no_objects:
            print("\n" + "-" * 60)
            print("CUSTOM APPLICATIONS")
            print("-" * 60)
            has_custom_apps = (
                input(
                    "Do you have any custom applications to capture? (y/n, default=n): "
                )
                .strip()
                .lower()
            )

            if has_custom_apps == "y":
                print(
                    "\nNote: Applications are rarely custom. Most applications are predefined."
                )
                print("Only specify applications that you have created or customized.")
                application_names = interactive_application_search(
                    api_client, folder=None
                )

                if application_names:
                    print(
                        f"\n✓ Will capture {len(application_names)} custom application(s):"
                    )
                    for app_name in application_names:
                        print(f"  - {app_name}")
                else:
                    print("\n  ℹ No custom applications selected")
            else:
                print("  ✓ Skipping applications (assuming all are predefined)")

        # If folders not specified, prompt for selection
        if not folders_to_pull:
            print("\nDiscovering available folders and snippets...")
            available_folders, available_snippets = get_folders_and_snippets(api_client)

            # If snippets are enabled and not specified, show combined list
            if include_snippets and not snippets_to_pull and available_snippets:
                print("\n" + "=" * 60)
                print("Select Folders and Snippets")
                print("=" * 60)

                # Show folders first
                print("\nFolders:")
                for i, folder in enumerate(available_folders, 1):
                    print(f"  {i}. {folder}")

                # Show snippets separately (will be handled by select_snippets_with_defaults_option)
                print("\nSnippets will be selected separately after folders")

                print(
                    f"\nEnter folder numbers to select (comma-separated, e.g., 1,3,5):"
                )
                print("  Or press Enter to select all folders")

                while True:
                    try:
                        selection = input("Selection: ").strip()

                        if not selection:
                            # Select all folders by default
                            folders_to_pull = available_folders
                            print("\n" + "=" * 60)
                            print("Select Snippets")
                            print("=" * 60)
                            snippets_to_pull = select_snippets_with_defaults_option(
                                available_snippets
                            )
                            break

                        # Parse selections
                        indices = []
                        for part in selection.split(","):
                            part = part.strip()
                            try:
                                idx = int(part)
                                if 1 <= idx <= len(available_folders):
                                    indices.append(idx - 1)
                                else:
                                    print(
                                        f"  Invalid number: {idx}. Please enter numbers between 1 and {len(available_folders)}"
                                    )
                                    break
                            except ValueError:
                                print(
                                    f"  Invalid input: '{part}'. Please enter numbers separated by commas"
                                )
                                break
                        else:
                            # All indices were valid
                            if indices:
                                folders_to_pull = [
                                    available_folders[idx] for idx in indices
                                ]

                                # Prompt for snippets separately
                                if include_snippets and available_snippets:
                                    print("\n" + "=" * 60)
                                    print("Select Snippets")
                                    print("=" * 60)
                                    snippets_to_pull = (
                                        select_snippets_with_defaults_option(
                                            available_snippets
                                        )
                                    )

                                break
                    except KeyboardInterrupt:
                        print("\n\nSelection cancelled")
                        return 1
                    except Exception as e:
                        print(f"  Error: {e}")
                        continue
            else:
                # Only folders, or snippets disabled
                print("\n" + "=" * 60)
                print("Select Folders")
                print("=" * 60)
                folders_to_pull = multi_select_prompt(
                    available_folders, "folder", allow_multiple=True
                )

                # If snippets enabled but not specified, prompt separately
                if include_snippets and not snippets_to_pull and available_snippets:
                    print("\n" + "=" * 60)
                    print("Select Snippets")
                    print("=" * 60)
                    snippets_to_pull = select_snippets_with_defaults_option(
                        available_snippets
                    )

        # If snippets specified but folders not, still need to handle snippets
        elif include_snippets and not snippets_to_pull:
            print("\nDiscovering available snippets...")
            _, available_snippets = get_folders_and_snippets(api_client)
            if available_snippets:
                print("\n" + "=" * 60)
                print("Select Snippets")
                print("=" * 60)
                snippets_to_pull = select_snippets_with_defaults_option(
                    available_snippets
                )

        if not folders_to_pull:
            print("✗ No folders selected")
            return 1

        print(f"\nSelected folders: {', '.join(folders_to_pull)}")
        if snippets_to_pull:
            print(f"Selected snippets: {', '.join(snippets_to_pull)}")
        elif include_snippets:
            print("No snippets selected")

        # Prepare pull options
        include_defaults = args.include_defaults

        # Pull configuration
        print("\nPulling configuration...")
        config = pull_configuration(
            api_client,
            folder_names=folders_to_pull,
            snippet_names=snippets_to_pull if include_snippets else None,
            include_defaults=include_defaults,
            include_snippets=include_snippets,
            include_objects=not args.no_objects,
            include_profiles=not args.no_profiles,
            detect_defaults=args.detect_defaults,
            filter_defaults=args.filter_defaults,
            save_to_file=None,  # Handle saving separately
            application_names=application_names,
        )

        # Print summary
        format_pull_summary(config)

        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            encrypt = not args.no_encrypt

            if args.pretty:
                # Pretty print JSON
                with open(output_path, "w") as f:
                    json.dump(config, f, indent=2, sort_keys=True)
                print(f"\n✓ Configuration saved to: {output_path} (pretty JSON)")
            else:
                # Use standard save function (supports encryption)
                from config.storage.json_storage import save_config_json

                if encrypt:
                    password = getpass.getpass("Enter password for encryption: ")
                    from config.storage.json_storage import derive_key

                    cipher, salt = derive_key(password)
                else:
                    cipher = None
                    salt = None

                save_config_json(
                    config, str(output_path), cipher=cipher, salt=salt, encrypt=encrypt
                )
                print(f"\n✓ Configuration saved to: {output_path}")

        # Show dependency report if validation enabled
        if args.validate_dependencies and "dependency_report" in config.get(
            "metadata", {}
        ):
            dep_report = config["metadata"]["dependency_report"]
            validation = dep_report.get("validation", {})

            if not validation.get("valid", True):
                print("\n" + "=" * 60)
                print("Dependency Validation Report")
                print("=" * 60)
                missing = validation.get("missing_dependencies", {})
                print(f"⚠ {len(missing)} objects have missing dependencies:")
                for obj_name, missing_deps in list(missing.items())[
                    :10
                ]:  # Show first 10
                    print(f"  - {obj_name}: missing {', '.join(missing_deps[:3])}")
                    if len(missing_deps) > 3:
                        print(f"    ... and {len(missing_deps) - 3} more")
                if len(missing) > 10:
                    print(f"  ... and {len(missing) - 10} more objects")
                print("=" * 60)
            else:
                stats = dep_report.get("statistics", {})
                print(f"\n✓ Dependency validation passed")
                print(f"  Total dependencies: {stats.get('total_edges', 0)}")
                print(f"  Total objects: {stats.get('total_nodes', 0)}")

        return 0

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
