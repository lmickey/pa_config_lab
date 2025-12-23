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
        options: Dict[str, Any],
        filter_defaults: bool = False,
    ):
        """
        Initialize the pull worker.

        Args:
            api_client: Authenticated PrismaAccessAPIClient
            options: Dictionary of what to pull (folders, snippets, rules, objects, profiles, infrastructure, etc.)
            filter_defaults: Whether to filter default configurations
        """
        super().__init__()
        self.api_client = api_client
        self.options = options
        self.filter_defaults = filter_defaults
        self.config = None
        self._is_running = True

    def run(self):
        """Run the pull operation."""
        try:
            from prisma.pull.pull_orchestrator import PullOrchestrator
            from prisma.pull.infrastructure_capture import InfrastructureCapture
            from config.defaults.default_detector import DefaultDetector

            self.progress.emit("Initializing pull operation...", 5)

            # Create orchestrator (suppress output to avoid segfaults from print in threads)
            orchestrator = PullOrchestrator(self.api_client, suppress_output=True)
            
            # Set up progress callback to emit signals
            def progress_callback(message: str, current: float, total: float):
                if not self._is_running:
                    return
                if total == 100:
                    # Orchestrator is passing explicit percentage (current = percentage)
                    percentage = int(current)
                elif total > 0:
                    # Orchestrator is passing fraction - calculate percentage
                    # Map to 10-55% range (leave room for snippets at 60% and infrastructure at 65%+)
                    percentage = int(10 + (current / total) * 45)
                else:
                    percentage = 50
                self.progress.emit(message, percentage)
            
            orchestrator.set_progress_callback(progress_callback)

            self.progress.emit("Pulling configuration from Prisma Access...", 10)

            # Pull configuration
            config = orchestrator.pull_complete_configuration(
                folder_names=self.options.get("selected_folders", None),  # NEW: Selected folders
                snippet_names=self.options.get("selected_snippets", None),  # NEW: Selected snippets
                selected_components=self.options.get("selected_components", None),  # NEW: Component selection
                include_defaults=not self.filter_defaults,
                include_snippets=self.options.get("snippets", True),
                include_objects=self.options.get("objects", True),
                include_profiles=self.options.get("profiles", True),
                application_names=self.options.get("application_names", None),  # NEW: Custom applications
            )

            if not self._is_running:
                return

            # Pull infrastructure if any infrastructure options are enabled
            infra_enabled = any([
                self.options.get("include_remote_networks", False),
                self.options.get("include_service_connections", False),
                self.options.get("include_ipsec_tunnels", False),
                self.options.get("include_mobile_users", False),
                self.options.get("include_hip", False),
                self.options.get("include_regions", False),
            ])

            if infra_enabled and config:
                self.progress.emit("Pulling infrastructure components...", 68)
                
                try:
                    infra_capture = InfrastructureCapture(self.api_client, suppress_output=True)
                    
                    # Set up infrastructure progress callback
                    def infra_progress_callback(message: str, current: int, total: int):
                        if not self._is_running:
                            return
                        if total > 0:
                            percentage = int(68 + (current / total) * 10)  # 68-78% range
                        else:
                            percentage = 73
                        self.progress.emit(message, percentage)
                    
                    infra_data = infra_capture.capture_all_infrastructure(
                        folder=None,
                        include_remote_networks=self.options.get("include_remote_networks", True),
                        include_service_connections=self.options.get("include_service_connections", True),
                        include_ipsec_tunnels=self.options.get("include_ipsec_tunnels", True),
                        include_mobile_users=self.options.get("include_mobile_users", True),
                        include_hip=self.options.get("include_hip", True),
                        include_regions=self.options.get("include_regions", True),
                        progress_callback=infra_progress_callback,
                    )
                    
                    if not self._is_running:
                        return
                    
                    # Merge infrastructure data into config
                    # Infrastructure capture returns a flat dict with all components
                    if "remote_networks" in infra_data:
                        config["infrastructure"]["remote_networks"] = infra_data["remote_networks"]
                    if "service_connections" in infra_data:
                        config["infrastructure"]["service_connections"] = infra_data["service_connections"]
                    
                    # Tunnel-related components are at top level in infra_data
                    if "ipsec_tunnels" in infra_data:
                        config["infrastructure"]["ipsec_tunnels"] = infra_data["ipsec_tunnels"]
                    if "ike_gateways" in infra_data:
                        config["infrastructure"]["ike_gateways"] = infra_data["ike_gateways"]
                    if "ike_crypto_profiles" in infra_data:
                        config["infrastructure"]["ike_crypto_profiles"] = infra_data["ike_crypto_profiles"]
                    if "ipsec_crypto_profiles" in infra_data:
                        config["infrastructure"]["ipsec_crypto_profiles"] = infra_data["ipsec_crypto_profiles"]
                    
                    # Mobile users and HIP are nested dicts
                    if "mobile_users" in infra_data:
                        config["mobile_users"] = infra_data["mobile_users"]
                    if "hip" in infra_data:
                        config["hip"] = infra_data["hip"]
                    if "regions" in infra_data:
                        config["regions"] = infra_data["regions"]
                        
                except Exception as e:
                    # Log error but continue - infrastructure is optional
                    self.progress.emit(f"Warning: Infrastructure pull had errors: {str(e)}", 78)

            if not self._is_running:
                return

            self.progress.emit("Finalizing configuration...", 80)

            # Filter defaults if requested
            if self.filter_defaults and config:
                self.progress.emit("Detecting and filtering defaults...", 85)
                detector = DefaultDetector()
                
                # Detect defaults in config (modifies config in place)
                config = detector.detect_defaults_in_config(config)
                
                # Get statistics
                total_defaults = sum(detector.detection_stats.values())
                
                if self._is_running:
                    self.progress.emit(
                        f"Filtered {total_defaults} default items", 95
                    )

            if not self._is_running:
                return

            self.progress.emit("Pull operation complete!", 100)

            # Get statistics
            stats = orchestrator.stats
            
            # Add infrastructure stats if we pulled it
            if infra_enabled:
                if config.get("infrastructure", {}).get("remote_networks"):
                    stats["remote_networks"] = len(config["infrastructure"]["remote_networks"])
                if config.get("infrastructure", {}).get("service_connections"):
                    stats["service_connections"] = len(config["infrastructure"]["service_connections"])
                if config.get("mobile_users", {}).get("gp_gateways"):
                    stats["gp_gateways"] = len(config["mobile_users"]["gp_gateways"])
                if config.get("regions", {}).get("bandwidth_allocations"):
                    stats["bandwidth_allocations"] = len(config["regions"]["bandwidth_allocations"])
            
            message = self._format_stats_message(stats)

            # Store config and signal completion
            # IMPORTANT: Don't pass large config object in signal - causes Qt threading issues
            self.config = config
            self.finished.emit(True, message, None)  # Pass None instead of config to avoid threading issues

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            # Don't print from worker thread - causes segfault
            if self._is_running:
                self.error.emit(f"Pull operation failed: {str(e)}\n\n{error_details}")
                self.finished.emit(False, str(e), None)

    def _format_stats_message(self, stats: Dict[str, Any]) -> str:
        """Format statistics into a readable message."""
        lines = ["Pull completed successfully!\n"]

        # Core components
        if stats.get("folders_captured", 0) > 0:
            lines.append(f"Folders: {stats['folders_captured']}")
        if stats.get("snippets_captured", 0) > 0:
            lines.append(f"Snippets: {stats['snippets_captured']}")
        if stats.get("rules_captured", 0) > 0:
            lines.append(f"Security Rules: {stats['rules_captured']}")
        if stats.get("objects_captured", 0) > 0:
            lines.append(f"Objects: {stats['objects_captured']}")
        if stats.get("profiles_captured", 0) > 0:
            lines.append(f"Profiles: {stats['profiles_captured']}")

        # Infrastructure components (NEW)
        if stats.get("remote_networks", 0) > 0:
            lines.append(f"Remote Networks: {stats['remote_networks']}")
        if stats.get("service_connections", 0) > 0:
            lines.append(f"Service Connections: {stats['service_connections']}")
        if stats.get("gp_gateways", 0) > 0:
            lines.append(f"GP Gateways: {stats['gp_gateways']}")
        if stats.get("bandwidth_allocations", 0) > 0:
            lines.append(f"Bandwidth Allocations: {stats['bandwidth_allocations']}")

        # Errors
        errors = stats.get("errors", [])
        if errors and len(errors) > 0:
            lines.append(f"\n⚠ Warnings/Errors: {len(errors)}")

        return "\n".join(lines)
    
    def stop(self):
        """Stop the worker thread gracefully."""
        self._is_running = False


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


class DiscoveryWorker(QThread):
    """Background worker for discovering folders and snippets from tenant."""
    
    # Signals
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(list, list)  # folders, snippets
    error = pyqtSignal(str)  # error message
    
    def __init__(self, api_client):
        """
        Initialize the discovery worker.
        
        Args:
            api_client: Authenticated PrismaAccessAPIClient
        """
        super().__init__()
        self.api_client = api_client
    
    def run(self):
        """Run folder and snippet discovery."""
        try:
            from prisma.pull.folder_capture import FolderCapture, filter_folders_for_migration
            from prisma.pull.snippet_capture import SnippetCapture
            
            self.progress.emit("Discovering folders...", 20)
            
            # Discover folders
            folder_capture = FolderCapture(self.api_client)
            all_folders = folder_capture.discover_folders()
            
            self.progress.emit("Filtering folders for migration...", 40)
            
            # Filter for migration (remove "all", "ngfw", etc.)
            filtered_folders = filter_folders_for_migration(all_folders)
            
            self.progress.emit("Discovering snippets...", 60)
            
            # Discover snippets
            snippet_capture = SnippetCapture(self.api_client)
            snippets = snippet_capture.discover_snippets_with_folders()
            
            self.progress.emit("Discovery complete!", 100)
            
            # Emit success
            self.finished.emit(filtered_folders, snippets)
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            self.error.emit(error_msg)
