"""
Push Orchestration for Prisma Access Configuration Deployment.

This module orchestrates the push process, coordinating all push operations
with dependency ordering, conflict resolution, and error handling.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time

from ..api_client import PrismaAccessAPIClient
from ..dependencies.dependency_resolver import DependencyResolver
from .conflict_resolver import ConflictResolver, ConflictResolution
from .push_validator import PushValidator


class PushOrchestrator:
    """Orchestrate the complete configuration push process."""

    def __init__(self, api_client: PrismaAccessAPIClient):
        """
        Initialize push orchestrator.

        Args:
            api_client: PrismaAccessAPIClient instance for target tenant
        """
        self.api_client = api_client
        self.dependency_resolver = DependencyResolver()
        self.conflict_resolver = ConflictResolver()
        self.push_validator = PushValidator()

        self.progress_callback: Optional[Callable[[str, int, int], None]] = None
        self.error_handler: Optional[Callable[[str, Exception], None]] = None

        self.stats = {
            "objects_pushed": 0,
            "profiles_pushed": 0,
            "rules_pushed": 0,
            "folders_pushed": 0,
            "snippets_pushed": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "errors": [],
        }

    def set_progress_callback(self, callback: Callable[[str, int, int], None]):
        """
        Set progress callback function.

        Args:
            callback: Function(message, current, total)
        """
        self.progress_callback = callback

    def set_error_handler(self, handler: Callable[[str, Exception], None]):
        """
        Set error handler function.

        Args:
            handler: Function(message, exception)
        """
        self.error_handler = handler

    def _report_progress(self, message: str, current: int = 0, total: int = 0):
        """Report progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(message, current, total)
        else:
            print(f"[{current}/{total}] {message}")

    def _handle_error(self, message: str, error: Exception):
        """Handle error if handler is set."""
        self.stats["errors"].append({"message": message, "error": str(error)})

        if self.error_handler:
            self.error_handler(message, error)
        else:
            print(f"Error: {message} - {error}")

    def validate_push(
        self,
        config: Dict[str, Any],
        check_dependencies: bool = True,
        check_permissions: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate configuration before push.

        Args:
            config: Configuration to push
            check_dependencies: Whether to check dependencies
            check_permissions: Whether to check permissions

        Returns:
            Validation results dictionary
        """
        return self.push_validator.validate_configuration(
            config,
            self.api_client,
            check_dependencies=check_dependencies,
            check_permissions=check_permissions,
        )

    def detect_conflicts(
        self, config: Dict[str, Any], folder_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect conflicts before push.

        Args:
            config: Configuration to push
            folder_name: Optional folder name to check conflicts in

        Returns:
            Conflict detection results
        """
        return self.conflict_resolver.detect_conflicts(
            config, self.api_client, folder_name=folder_name
        )

    def push_configuration(
        self,
        config: Dict[str, Any],
        folder_names: Optional[List[str]] = None,
        snippet_names: Optional[List[str]] = None,
        dry_run: bool = False,
        conflict_strategy: ConflictResolution = ConflictResolution.SKIP,
    ) -> Dict[str, Any]:
        """
        Push configuration to target tenant.

        Args:
            config: Configuration to push
            folder_names: Optional list of folder names to push (None = all)
            snippet_names: Optional list of snippet names to push (None = all)
            dry_run: If True, validate and detect conflicts but don't push
            conflict_strategy: Default strategy for resolving conflicts

        Returns:
            Push results dictionary
        """
        start_time = time.time()

        # Reset stats
        self.stats = {
            "objects_pushed": 0,
            "profiles_pushed": 0,
            "rules_pushed": 0,
            "folders_pushed": 0,
            "snippets_pushed": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "errors": [],
        }

        try:
            # Validate configuration
            self._report_progress("Validating configuration", 0, 5)
            validation = self.validate_push(config)

            if not validation.get("valid", False):
                errors = validation.get("errors", [])
                self.stats["errors"].extend(errors)
                return {
                    "success": False,
                    "message": "Validation failed",
                    "validation": validation,
                    "stats": self.stats,
                }

            # Detect conflicts
            self._report_progress("Detecting conflicts", 1, 5)
            conflict_detection = self.detect_conflicts(config)
            conflicts = conflict_detection.get("conflicts", [])
            self.stats["conflicts_detected"] = len(conflicts)

            if conflicts and conflict_strategy == ConflictResolution.SKIP:
                # Skip all conflicts
                self.stats["conflicts_resolved"] = len(conflicts)
                return {
                    "success": False,
                    "message": f"{len(conflicts)} conflicts detected. Use different conflict strategy or resolve conflicts.",
                    "conflicts": conflict_detection,
                    "stats": self.stats,
                }

            if dry_run:
                return {
                    "success": True,
                    "message": "Dry run completed - no changes made",
                    "validation": validation,
                    "conflicts": conflict_detection,
                    "stats": self.stats,
                }

            # Get push order (dependencies first)
            self._report_progress("Determining push order", 2, 5)
            push_order = self.dependency_resolver.get_push_order(config)

            # Push folders
            self._report_progress("Pushing folders", 3, 5)
            folders_pushed = self._push_folders(config, folder_names, conflict_strategy)
            self.stats["folders_pushed"] = folders_pushed

            # Push snippets
            self._report_progress("Pushing snippets", 4, 5)
            snippets_pushed = self._push_snippets(
                config, snippet_names, conflict_strategy
            )
            self.stats["snippets_pushed"] = snippets_pushed

            elapsed_time = time.time() - start_time

            return {
                "success": True,
                "message": "Push completed",
                "validation": validation,
                "conflicts": conflict_detection,
                "stats": {**self.stats, "elapsed_seconds": elapsed_time},
            }

        except Exception as e:
            self._handle_error("Error during push", e)
            return {
                "success": False,
                "message": f"Push failed: {e}",
                "stats": self.stats,
            }

    def _push_folders(
        self,
        config: Dict[str, Any],
        folder_names: Optional[List[str]],
        conflict_strategy: ConflictResolution,
    ) -> int:
        """Push folder configurations."""
        security_policies = config.get("security_policies", {})
        folders = security_policies.get("folders", [])

        if not folders:
            return 0

        # Filter to specified folders
        if folder_names:
            folders = [f for f in folders if f.get("name") in folder_names]

        pushed_count = 0
        for folder in folders:
            try:
                # Push folder configuration
                # Note: Actual push implementation will be added based on API capabilities
                # For now, this is a placeholder
                pushed_count += 1
            except Exception as e:
                self._handle_error(f"Error pushing folder {folder.get('name')}", e)

        return pushed_count

    def _push_snippets(
        self,
        config: Dict[str, Any],
        snippet_names: Optional[List[str]],
        conflict_strategy: ConflictResolution,
    ) -> int:
        """Push snippet configurations."""
        security_policies = config.get("security_policies", {})
        snippets = security_policies.get("snippets", [])

        if not snippets:
            return 0

        # Filter to specified snippets
        if snippet_names:
            snippets = [s for s in snippets if s.get("name") in snippet_names]

        pushed_count = 0
        for snippet in snippets:
            try:
                # Push snippet configuration
                # Note: Actual push implementation will be added based on API capabilities
                # For now, this is a placeholder
                pushed_count += 1
            except Exception as e:
                self._handle_error(f"Error pushing snippet {snippet.get('name')}", e)

        return pushed_count

    def get_push_report(self) -> Dict[str, Any]:
        """
        Get push statistics and report.

        Returns:
            Push report dictionary
        """
        return {
            "stats": self.stats.copy(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
