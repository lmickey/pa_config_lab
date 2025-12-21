"""
Background worker threads for long-running operations.

This module provides QThread-based workers for API operations
that need to run in the background without blocking the UI.
"""

from typing import Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal


class PullWorker(QThread):
    """Background worker for pulling configurations from Prisma Access."""

    # Signals
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(bool, str, object)  # success, message, config
    error = pyqtSignal(str)  # error message

    def __init__(
        self,
        api_client,
        options: Dict[str, bool],
        filter_defaults: bool = False,
    ):
        """
        Initialize the pull worker.

        Args:
            api_client: Authenticated PrismaAccessAPIClient
            options: Dictionary of what to pull (folders, snippets, rules, etc.)
            filter_defaults: Whether to filter default configurations
        """
        super().__init__()
        self.api_client = api_client
        self.options = options
        self.filter_defaults = filter_defaults
        self.config = None

    def run(self):
        """Run the pull operation."""
        try:
            from prisma.pull.pull_orchestrator import PullOrchestrator
            from config.defaults.default_detector import DefaultDetector

            self.progress.emit("Initializing pull operation...", 5)

            # Create orchestrator
            orchestrator = PullOrchestrator(self.api_client)
            
            # Set up progress callback to emit signals
            def progress_callback(message: str, current: int, total: int):
                if total > 0:
                    percentage = int(10 + (current / total) * 70)  # 10-80% range
                else:
                    percentage = 50
                self.progress.emit(message, percentage)
            
            orchestrator.set_progress_callback(progress_callback)

            self.progress.emit("Pulling configuration from Prisma Access...", 10)

            # Pull configuration
            config = orchestrator.pull_complete_configuration(
                folder_names=None,  # Pull all folders
                snippet_names=None,  # Pull all snippets
                include_defaults=not self.filter_defaults,
                include_snippets=self.options.get("snippets", True),
                include_objects=self.options.get("objects", True),
                include_profiles=self.options.get("profiles", True),
                application_names=None,  # No custom applications by default
            )

            self.progress.emit("Configuration pulled successfully", 80)

            # Filter defaults if requested
            if self.filter_defaults and config:
                self.progress.emit("Detecting and filtering defaults...", 85)
                detector = DefaultDetector()
                
                # Detect defaults in config (modifies config in place)
                config = detector.detect_defaults_in_config(config)
                
                # Get statistics
                total_defaults = sum(detector.detection_stats.values())
                
                self.progress.emit(
                    f"Filtered {total_defaults} default items", 95
                )

            self.progress.emit("Pull operation complete!", 100)

            # Get statistics
            stats = orchestrator.stats
            message = self._format_stats_message(stats)

            self.config = config
            self.finished.emit(True, message, config)

        except Exception as e:
            self.error.emit(f"Pull operation failed: {str(e)}")
            self.finished.emit(False, str(e), None)

    def _format_stats_message(self, stats: Dict[str, Any]) -> str:
        """Format statistics into a readable message."""
        lines = ["Pull completed successfully!\n"]

        if "folders" in stats:
            lines.append(f"Folders: {stats['folders']}")
        if "snippets" in stats:
            lines.append(f"Snippets: {stats['snippets']}")
        if "security_rules" in stats:
            lines.append(f"Security Rules: {stats['security_rules']}")
        if "addresses" in stats:
            lines.append(f"Addresses: {stats['addresses']}")
        if "address_groups" in stats:
            lines.append(f"Address Groups: {stats['address_groups']}")
        if "services" in stats:
            lines.append(f"Services: {stats['services']}")
        if "service_groups" in stats:
            lines.append(f"Service Groups: {stats['service_groups']}")
        if "applications" in stats:
            lines.append(f"Applications: {stats['applications']}")
        if "application_groups" in stats:
            lines.append(f"Application Groups: {stats['application_groups']}")

        return "\n".join(lines)


class PushWorker(QThread):
    """Background worker for pushing configurations to Prisma Access."""

    # Signals
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(bool, str, object)  # success, message, result
    error = pyqtSignal(str)  # error message
    conflicts_detected = pyqtSignal(list)  # list of conflicts

    def __init__(
        self,
        api_client,
        config: Dict[str, Any],
        conflict_resolution: str = "SKIP",
        dry_run: bool = False,
    ):
        """
        Initialize the push worker.

        Args:
            api_client: Authenticated PrismaAccessAPIClient
            config: Configuration to push
            conflict_resolution: How to handle conflicts (SKIP, OVERWRITE, RENAME)
            dry_run: If True, simulate push without making changes
        """
        super().__init__()
        self.api_client = api_client
        self.config = config
        self.conflict_resolution = conflict_resolution
        self.dry_run = dry_run
        self.result = None

    def run(self):
        """Run the push operation."""
        try:
            from prisma.push.push_orchestrator import PushOrchestrator
            from prisma.push.conflict_resolver import ConflictResolution

            self.progress.emit("Initializing push operation...", 5)

            # Create orchestrator
            orchestrator = PushOrchestrator(self.api_client)

            # Convert conflict resolution string to enum
            resolution_map = {
                "SKIP": ConflictResolution.SKIP,
                "OVERWRITE": ConflictResolution.OVERWRITE,
                "RENAME": ConflictResolution.RENAME,
            }
            resolution = resolution_map.get(
                self.conflict_resolution, ConflictResolution.SKIP
            )

            mode = "Dry run" if self.dry_run else "Pushing"
            self.progress.emit(f"{mode} configuration to Prisma Access...", 10)

            # Push configuration
            result = orchestrator.push_configuration(
                self.config, conflict_resolution=resolution, dry_run=self.dry_run
            )

            # Check for conflicts
            if result.get("conflicts"):
                self.conflicts_detected.emit(result["conflicts"])

            if result.get("success"):
                self.progress.emit("Push operation complete!", 100)
                message = self._format_result_message(result, self.dry_run)
                self.result = result
                self.finished.emit(True, message, result)
            else:
                error_msg = result.get("message", "Push failed")
                self.error.emit(error_msg)
                self.finished.emit(False, error_msg, result)

        except Exception as e:
            self.error.emit(f"Push operation failed: {str(e)}")
            self.finished.emit(False, str(e), None)

    def _format_result_message(self, result: Dict[str, Any], dry_run: bool) -> str:
        """Format result into a readable message."""
        if dry_run:
            lines = ["Dry run completed successfully!\n"]
            lines.append("No changes were made.\n")
        else:
            lines = ["Push completed successfully!\n"]

        if "validation" in result:
            validation = result["validation"]
            if validation.get("valid"):
                lines.append("✓ Configuration validated")

        if "conflicts" in result and result["conflicts"]:
            lines.append(f"\n⚠ {len(result['conflicts'])} conflicts detected")

        return "\n".join(lines)


class DefaultDetectionWorker(QThread):
    """Background worker for detecting default configurations."""

    # Signals
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str, object)  # success, message, report
    error = pyqtSignal(str)

    def __init__(self, config: Dict[str, Any]):
        """Initialize the default detection worker."""
        super().__init__()
        self.config = config
        self.report = None

    def run(self):
        """Run default detection."""
        try:
            from config.defaults.default_detector import DefaultDetector

            self.progress.emit("Analyzing configuration...", 10)

            detector = DefaultDetector()

            self.progress.emit("Detecting default items...", 30)

            report = detector.detect_defaults_in_config(self.config)

            self.progress.emit("Analysis complete!", 100)

            message = self._format_report(report)
            self.report = report
            self.finished.emit(True, message, report)

        except Exception as e:
            self.error.emit(f"Default detection failed: {str(e)}")
            self.finished.emit(False, str(e), None)

    def _format_report(self, report: Dict[str, Any]) -> str:
        """Format detection report."""
        summary = report.get("summary", {})
        lines = ["Default Detection Complete!\n"]
        lines.append(f"Total defaults found: {summary.get('total_defaults', 0)}")
        lines.append(
            f"Default snippets: {summary.get('defaults_by_type', {}).get('snippet', 0)}"
        )
        lines.append(
            f"Default rules: {summary.get('defaults_by_type', {}).get('security_rule', 0)}"
        )
        return "\n".join(lines)


class DependencyAnalysisWorker(QThread):
    """Background worker for analyzing configuration dependencies."""

    # Signals
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str, object)  # success, message, analysis
    error = pyqtSignal(str)

    def __init__(self, config: Dict[str, Any]):
        """Initialize the dependency analysis worker."""
        super().__init__()
        self.config = config
        self.analysis = None

    def run(self):
        """Run dependency analysis."""
        try:
            from prisma.dependencies.dependency_resolver import DependencyResolver

            self.progress.emit("Building dependency graph...", 20)

            resolver = DependencyResolver()
            resolver.build_graph_from_config(self.config)

            self.progress.emit("Analyzing dependencies...", 50)

            order = resolver.get_push_order()
            report = resolver.generate_dependency_report()

            self.progress.emit("Validating dependencies...", 80)

            missing = resolver.validate_missing_dependencies()

            self.progress.emit("Analysis complete!", 100)

            self.analysis = {
                "order": order,
                "report": report,
                "missing": missing,
            }

            message = self._format_analysis(report, missing)
            self.finished.emit(True, message, self.analysis)

        except Exception as e:
            self.error.emit(f"Dependency analysis failed: {str(e)}")
            self.finished.emit(False, str(e), None)

    def _format_analysis(self, report: Dict[str, Any], missing: Dict[str, Any]) -> str:
        """Format analysis results."""
        lines = ["Dependency Analysis Complete!\n"]
        lines.append(f"Total nodes: {report.get('total_nodes', 0)}")
        lines.append(f"Total edges: {report.get('total_edges', 0)}")

        if missing.get("has_missing"):
            lines.append(f"\n⚠ Missing dependencies: {missing.get('total_missing', 0)}")

        return "\n".join(lines)
