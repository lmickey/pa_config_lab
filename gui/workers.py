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
        connection_name: Optional[str] = None,
    ):
        """
        Initialize the pull worker.

        Args:
            api_client: Authenticated PrismaAccessAPIClient
            options: Dictionary of what to pull (folders, snippets, rules, objects, profiles, infrastructure, etc.)
            filter_defaults: Whether to filter default configurations
            connection_name: Friendly name of the connected tenant (for metadata)
        """
        super().__init__()
        self.api_client = api_client
        self.options = options
        self.filter_defaults = filter_defaults
        self.connection_name = connection_name
        self.config = None
        self._is_running = True

    def run(self):
        """Run the pull operation."""
        try:
            from prisma.pull.pull_orchestrator import PullOrchestrator

            self.progress.emit("Initializing pull operation...", 5)

            # Create orchestrator with workflow config
            from config.workflows import WorkflowConfig
            workflow_config = WorkflowConfig(
                include_defaults=not self.filter_defaults,  # Invert: filter_defaults means exclude them
                validate_before_pull=True,
            )
            orchestrator = PullOrchestrator(self.api_client, config=workflow_config)
            
            # Set progress callback so orchestrator can emit detailed progress
            orchestrator.set_progress_callback(lambda msg, pct: self.progress.emit(msg, pct))

            # Determine if infrastructure should be pulled
            include_infrastructure = any([
                self.options.get("include_remote_networks", False),
                self.options.get("include_service_connections", False),
                self.options.get("include_ipsec_tunnels", False),
                self.options.get("include_mobile_users", False),
                self.options.get("include_regions", False),
            ])

            # Extract selected folders/snippets from new tree widget format
            # Format: [{'name': str, 'data': dict, 'components': [str]}]
            selected_folders = self.options.get("selected_folders", [])
            selected_snippets = self.options.get("selected_snippets", [])
            
            # Build folder filter: which folders/components to STORE (not query)
            # API queries always run against bottom folders for efficiency
            # UI selection controls what config gets stored from the results
            folder_filter = {}
            if selected_folders:
                for f in selected_folders:
                    if isinstance(f, dict):
                        # Get the API name from data, or use display name
                        data = f.get('data', {})
                        api_name = data.get('name') if isinstance(data, dict) else f.get('name')
                        if api_name:
                            folder_filter[api_name] = f.get('components', [])
                    elif isinstance(f, str):
                        folder_filter[f] = []  # All components
            
            # Extract snippet names (snippets must be queried individually, no filtering optimization)
            snippet_names = None
            if selected_snippets:
                snippet_names = []
                for s in selected_snippets:
                    if isinstance(s, dict):
                        name = s.get('name')
                        # Skip placeholder items
                        if name and not name.startswith('('):
                            snippet_names.append(name)
                    elif isinstance(s, str):
                        snippet_names.append(s)
            
            # Pull configuration using orchestrator
            # Always use bottom folders for API efficiency - folder_filter controls storage
            # Snippets and infrastructure must be queried individually (no optimization)
            result = orchestrator.pull_all(
                include_folders=bool(folder_filter),
                include_snippets=bool(snippet_names),
                include_infrastructure=include_infrastructure,
                use_bottom_folders=True,  # Always query bottom folders for efficiency
                folder_list=None,  # Don't override - use bottom folders
                snippet_list=snippet_names if snippet_names else None,
                folder_filter=folder_filter,  # Controls what folder items get stored
            )

            if not self._is_running:
                return

            # Extract Configuration object from result
            configuration = result.configuration
            
            if not configuration:
                raise Exception("Pull operation returned no configuration")

            self.progress.emit("Finalizing configuration...", 80)
            
            # Set additional metadata on the Configuration object
            if self.connection_name:
                configuration.saved_credentials_ref = self.connection_name
                # Also store as source_tenant for display purposes
                if not hasattr(configuration, 'source_tenant') or not configuration.source_tenant:
                    configuration.source_tenant = self.connection_name
            
            # Convert Configuration object to dict format for GUI
            from gui.config_adapter import ConfigAdapter
            config = ConfigAdapter.to_dict(configuration)
            
            # Explicitly delete the Configuration object to free memory immediately
            # The dict representation is all we need for the GUI
            del configuration

            if not self._is_running:
                return

            self.progress.emit("Pull operation complete!", 100)

            # Build stats from workflow result
            stats = {
                'items_processed': result.items_processed,
                'items_created': result.items_created,
                'items_skipped': result.items_skipped,
                'errors': [e.to_dict() for e in result.errors],
                'warnings': [w.to_dict() for w in result.warnings],
            }
            
            # Add folder/snippet counts from config dict
            stats['folders_captured'] = len(config.get('folders', {}))
            stats['snippets_captured'] = len(config.get('snippets', {}))
            
            # Count infrastructure items (sum of all item types)
            infra_data = config.get('infrastructure', {})
            if isinstance(infra_data, dict):
                if 'items' in infra_data and isinstance(infra_data['items'], list):
                    # Legacy format
                    stats['infrastructure_captured'] = len(infra_data['items'])
                else:
                    # New format - sum all item type lists
                    stats['infrastructure_captured'] = sum(
                        len(items) for items in infra_data.values() if isinstance(items, list)
                    )
            else:
                stats['infrastructure_captured'] = 0
            
            # Format stats message with error handling
            try:
                message = self._format_stats_message(stats)
            except Exception as e:
                # Fallback to simple message if stats formatting fails
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error formatting stats message: {e}")
                message = "Pull completed successfully!"

            # Store config and signal completion
            # IMPORTANT: Store the DICT, not the Configuration object
            # This avoids memory issues when transferring between threads
            self.config = config
            
            # Emit signal with error handling
            try:
                self.finished.emit(True, message, None)  # Pass None instead of config to avoid threading issues
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error emitting finished signal: {e}")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            # Don't print from worker thread - causes segfault
            if self._is_running:
                self.error.emit(f"Pull operation failed: {str(e)}\n\n{error_details}")
                self.finished.emit(False, str(e), None)

    def _format_stats_message(self, stats: Dict[str, Any]) -> str:
        """Format statistics into a readable message."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            lines = ["Pull completed successfully!\n"]

            # Core components - use .get() with defaults for safety
            try:
                if stats.get("folders_captured", 0) > 0:
                    lines.append(f"Folders: {stats['folders_captured']}")
            except Exception as e:
                logger.warning(f"Error formatting folders stat: {e}")
                
            try:
                if stats.get("snippets_captured", 0) > 0:
                    lines.append(f"Snippets: {stats['snippets_captured']}")
            except Exception as e:
                logger.warning(f"Error formatting snippets stat: {e}")
                
            try:
                if stats.get("rules_captured", 0) > 0:
                    lines.append(f"Security Rules: {stats['rules_captured']}")
            except Exception as e:
                logger.warning(f"Error formatting rules stat: {e}")
                
            try:
                if stats.get("objects_captured", 0) > 0:
                    lines.append(f"Objects: {stats['objects_captured']}")
            except Exception as e:
                logger.warning(f"Error formatting objects stat: {e}")
                
            try:
                if stats.get("profiles_captured", 0) > 0:
                    lines.append(f"Profiles: {stats['profiles_captured']}")
            except Exception as e:
                logger.warning(f"Error formatting profiles stat: {e}")
            
            try:
                if stats.get("infrastructure_captured", 0) > 0:
                    lines.append(f"Infrastructure: {stats['infrastructure_captured']}")
            except Exception as e:
                logger.warning(f"Error formatting infrastructure stat: {e}")

            # Infrastructure components (detailed - NEW)
            try:
                if stats.get("remote_networks", 0) > 0:
                    lines.append(f"Remote Networks: {stats['remote_networks']}")
            except Exception as e:
                logger.warning(f"Error formatting remote_networks stat: {e}")
                
            try:
                if stats.get("service_connections", 0) > 0:
                    lines.append(f"Service Connections: {stats['service_connections']}")
            except Exception as e:
                logger.warning(f"Error formatting service_connections stat: {e}")
                
            try:
                if stats.get("gp_gateways", 0) > 0:
                    lines.append(f"GP Gateways: {stats['gp_gateways']}")
            except Exception as e:
                logger.warning(f"Error formatting gp_gateways stat: {e}")
                
            try:
                if stats.get("bandwidth_allocations", 0) > 0:
                    lines.append(f"Bandwidth Allocations: {stats['bandwidth_allocations']}")
            except Exception as e:
                logger.warning(f"Error formatting bandwidth_allocations stat: {e}")

            # Errors
            try:
                errors = stats.get("errors", [])
                if errors and len(errors) > 0:
                    lines.append(f"\n⚠ Warnings/Errors: {len(errors)}")
            except Exception as e:
                logger.warning(f"Error formatting errors stat: {e}")

            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Critical error in _format_stats_message: {e}")
            return "Pull completed successfully!"
    
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


class SelectivePushWorker(QThread):
    """Background worker for selective push operations."""

    # Signals
    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(bool, str, object)  # success, message, results
    error = pyqtSignal(str)  # error message

    def __init__(
        self,
        api_client,
        selected_items: Dict[str, Any],
        destination_config: Optional[Dict[str, Any]],
        conflict_resolution: str = "SKIP",
    ):
        """
        Initialize the selective push worker.

        Args:
            api_client: Authenticated PrismaAccessAPIClient for destination
            selected_items: Dictionary of selected items to push
            destination_config: Optional destination config for conflict detection
            conflict_resolution: How to handle conflicts (SKIP, OVERWRITE, RENAME)
        """
        super().__init__()
        self.api_client = api_client
        self.selected_items = selected_items
        self.destination_config = destination_config
        self.conflict_resolution = conflict_resolution
        self.results = None

    def run(self):
        """Run the selective push operation."""
        try:
            from prisma.push.selective_push_orchestrator import SelectivePushOrchestrator

            # Create orchestrator
            orchestrator = SelectivePushOrchestrator(
                self.api_client,
                self.conflict_resolution
            )

            # Set progress callback with error handling
            def progress_callback(message: str, current: int, total: int):
                try:
                    self.progress.emit(message, current, total)
                except Exception:
                    # Silently ignore signal errors
                    pass

            orchestrator.set_progress_callback(progress_callback)

            # Push selected items
            result = orchestrator.push_selected_items(
                self.selected_items,
                self.destination_config
            )

            self.results = result

            if result.get('success'):
                # Format success message
                summary = result['results']['summary']
                message = (
                    f"Push completed!\n\n"
                    f"Total: {summary['total']}\n"
                    f"Created: {summary['created']}\n"
                    f"Updated: {summary['updated']}\n"
                    f"Skipped: {summary['skipped']}\n"
                    f"Failed: {summary['failed']}"
                )
                try:
                    self.finished.emit(True, message, result)
                except Exception as e:
                    # If emit fails, try error signal
                    try:
                        self.error.emit(f"Signal error: {str(e)}")
                    except:
                        pass
            else:
                error_msg = result.get('message', 'Push failed')
                try:
                    self.error.emit(error_msg)
                    self.finished.emit(False, error_msg, result)
                except Exception:
                    pass

        except Exception as e:
            import traceback
            import sys
            # Write to stderr instead of print (safer in threads)
            traceback.print_exc(file=sys.stderr)
            try:
                self.error.emit(f"Push operation failed: {str(e)}")
                self.finished.emit(False, str(e), None)
            except Exception:
                # Last resort - just exit
                pass


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
