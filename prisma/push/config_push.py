"""
Main push functionality for Prisma Access configuration.

This module provides the primary interface for pushing configurations
to Prisma Access SCM tenants.
"""

from typing import Dict, Any, List, Optional
from .push_orchestrator import PushOrchestrator
from .conflict_resolver import ConflictResolution


def push_configuration(
    api_client,
    config: Dict[str, Any],
    folder_names: Optional[List[str]] = None,
    snippet_names: Optional[List[str]] = None,
    dry_run: bool = False,
    conflict_strategy: str = "skip",
    validate: bool = True,
) -> Dict[str, Any]:
    """
    Push Prisma Access configuration to target tenant.

    Args:
        api_client: PrismaAccessAPIClient instance for target tenant
        config: Configuration dictionary to push
        folder_names: Optional list of folder names to push (None = all)
        snippet_names: Optional list of snippet names to push (None = all)
        dry_run: If True, validate and detect conflicts but don't push
        conflict_strategy: Strategy for resolving conflicts ("skip", "overwrite", "rename")
        validate: Whether to validate configuration before push

    Returns:
        Push results dictionary
    """
    orchestrator = PushOrchestrator(api_client)

    # Set up progress reporting
    def progress_callback(message: str, current: int, total: int):
        if total > 0:
            percent = (current / total) * 100
            print(f"[{percent:.1f}%] {message}")
        else:
            print(message)

    orchestrator.set_progress_callback(progress_callback)

    # Convert conflict strategy string to enum
    strategy_map = {
        "skip": ConflictResolution.SKIP,
        "overwrite": ConflictResolution.OVERWRITE,
        "rename": ConflictResolution.RENAME,
        "merge": ConflictResolution.MERGE,
    }
    resolution_strategy = strategy_map.get(
        conflict_strategy.lower(), ConflictResolution.SKIP
    )

    # Push configuration
    result = orchestrator.push_configuration(
        config,
        folder_names=folder_names,
        snippet_names=snippet_names,
        dry_run=dry_run,
        conflict_strategy=resolution_strategy,
    )

    # Print summary
    stats = result.get("stats", {})
    print("\n" + "=" * 60)
    print("Push Summary")
    print("=" * 60)
    if dry_run:
        print("Mode: DRY RUN (no changes made)")
    print(f"Folders pushed: {stats.get('folders_pushed', 0)}")
    print(f"Rules pushed: {stats.get('rules_pushed', 0)}")
    print(f"Objects pushed: {stats.get('objects_pushed', 0)}")
    print(f"Profiles pushed: {stats.get('profiles_pushed', 0)}")
    print(f"Snippets pushed: {stats.get('snippets_pushed', 0)}")
    print(f"Conflicts detected: {stats.get('conflicts_detected', 0)}")
    print(f"Conflicts resolved: {stats.get('conflicts_resolved', 0)}")
    print(f"Errors: {stats.get('errors', 0)}")
    if "elapsed_seconds" in stats:
        print(f"Elapsed time: {stats.get('elapsed_seconds', 0):.2f} seconds")
    print("=" * 60)

    return result
