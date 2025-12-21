"""
Main pull functionality for Prisma Access configuration.

This module provides the primary interface for pulling configurations
from Prisma Access SCM tenants.
"""

from typing import Dict, Any, List, Optional
from ..api_client import PrismaAccessAPIClient
from .pull_orchestrator import PullOrchestrator
from config.storage.json_storage import save_config_json, derive_key
from config.schema.config_schema_v2 import create_empty_config_v2


def pull_configuration(
    api_client: PrismaAccessAPIClient,
    folder_names: Optional[List[str]] = None,
    snippet_names: Optional[List[str]] = None,
    include_defaults: bool = False,
    include_snippets: bool = True,
    include_objects: bool = True,
    include_profiles: bool = True,
    detect_defaults: bool = True,
    filter_defaults: bool = False,
    save_to_file: Optional[str] = None,
    encrypt: bool = True,
    cipher: Optional[Any] = None,
    application_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Pull complete Prisma Access configuration.

    Args:
        api_client: PrismaAccessAPIClient instance
        folder_names: List of folder names to pull (None = all)
        snippet_names: List of snippet names to pull (None = all, only used if include_snippets=True)
        include_defaults: Whether to include default folders
        include_snippets: Whether to capture snippets
        include_objects: Whether to capture objects
        include_profiles: Whether to capture profiles
        detect_defaults: Whether to detect and mark defaults (default: True)
        filter_defaults: Whether to filter out defaults from result (default: False)
        save_to_file: Optional file path to save configuration
        encrypt: Whether to encrypt saved file
        cipher: Optional cipher for encryption
        application_names: Optional list of custom application names to capture (None = no applications)
                           Note: Applications are rarely custom - only specify user-created applications

    Returns:
        Complete configuration dictionary
    """
    orchestrator = PullOrchestrator(api_client, detect_defaults=detect_defaults)

    # Set up progress reporting
    def progress_callback(message: str, current: int, total: int):
        if total > 0:
            percent = (current / total) * 100
            print(f"[{percent:.1f}%] {message}")
        else:
            print(message)

    orchestrator.set_progress_callback(progress_callback)

    # Pull configuration
    config = orchestrator.pull_complete_configuration(
        folder_names=folder_names,
        snippet_names=snippet_names,
        include_defaults=include_defaults,
        include_snippets=include_snippets,
        include_objects=include_objects,
        include_profiles=include_profiles,
        application_names=application_names,
    )

    # Filter defaults if requested
    if filter_defaults and orchestrator.default_detector:
        from config.defaults.default_detector import DefaultDetector

        detector = DefaultDetector()
        config = detector.filter_defaults(config, include_defaults=False)

    # Save to file if requested
    if save_to_file:
        if encrypt and cipher is None:
            import getpass

            password = getpass.getpass("Enter password for encryption: ")
            cipher = derive_key(password)

        save_config_json(config, save_to_file, cipher=cipher, encrypt=encrypt)
        print(f"\nConfiguration saved to: {save_to_file}")

    # Print summary
    stats = config.get("metadata", {}).get("pull_stats", {})
    print("\n" + "=" * 60)
    print("Pull Summary")
    print("=" * 60)
    print(f"Folders captured: {stats.get('folders', 0)}")
    print(f"Security rules: {stats.get('rules', 0)}")
    print(f"Objects: {stats.get('objects', 0)}")
    print(f"Profiles: {stats.get('profiles', 0)}")
    print(f"Snippets: {stats.get('snippets', 0)}")
    if detect_defaults:
        defaults_count = stats.get("defaults_detected", 0)
        print(f"Defaults detected: {defaults_count}")
    print(f"Errors: {stats.get('errors', 0)}")
    print(f"Elapsed time: {stats.get('elapsed_seconds', 0):.2f} seconds")
    print("=" * 60)

    return config


def pull_folders_only(
    api_client: PrismaAccessAPIClient,
    folder_names: Optional[List[str]] = None,
    include_defaults: bool = False,
) -> List[Dict[str, Any]]:
    """
    Pull only folder configurations (no objects or profiles).

    Args:
        api_client: PrismaAccessAPIClient instance
        folder_names: List of folder names (None = all)
        include_defaults: Whether to include default folders

    Returns:
        List of folder configurations
    """
    orchestrator = PullOrchestrator(api_client)
    return orchestrator.pull_all_folders(
        folder_names=folder_names,
        include_defaults=include_defaults,
        include_objects=False,
        include_profiles=False,
    )


def pull_snippets_only(api_client: PrismaAccessAPIClient) -> List[Dict[str, Any]]:
    """
    Pull only snippet configurations.

    Args:
        api_client: PrismaAccessAPIClient instance

    Returns:
        List of snippet configurations
    """
    orchestrator = PullOrchestrator(api_client)
    return orchestrator.pull_snippets()
