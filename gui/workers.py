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
        import logging
        logger = logging.getLogger(__name__)
        
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
            self._orchestrator = orchestrator  # Store reference for cancellation
            
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
            
            logger.debug(f"Selected folders raw: {selected_folders}")
            logger.debug(f"Selected snippets raw: {selected_snippets}")
            
            # Build folder filter: which folders/components to STORE (not query)
            # API queries always run against bottom folders for efficiency
            # UI selection controls what config gets stored from the results
            
            folder_filter = {}
            has_real_components = False  # Track if any real (non-custom) components selected
            
            if selected_folders:
                for f in selected_folders:
                    if isinstance(f, dict):
                        # Get the API name from data, or use display name
                        data = f.get('data', {})
                        api_name = data.get('name') if isinstance(data, dict) else f.get('name')
                        components = f.get('components', [])
                        logger.debug(f"Folder '{api_name}' has components: {components}")
                        if api_name:
                            folder_filter[api_name] = components
                            if components:  # Non-empty component list = real components selected
                                has_real_components = True
                    elif isinstance(f, str):
                        folder_filter[f] = []  # All components
                        has_real_components = True  # String format = all components
            
            # Extract snippet names (snippets must be queried individually, no filtering optimization)
            snippet_names = None
            snippet_components = {}  # Track snippet component selections
            if selected_snippets:
                snippet_names = []
                for s in selected_snippets:
                    if isinstance(s, dict):
                        name = s.get('name')
                        components = s.get('components', [])
                        # Skip placeholder items
                        if name and not name.startswith('('):
                            snippet_names.append(name)
                            snippet_components[name] = components
                            if components:
                                has_real_components = True
                    elif isinstance(s, str):
                        snippet_names.append(s)
                        has_real_components = True
            
            # Log the folder filter for debugging
            logger.info(f"Folder filter being sent to orchestrator: {folder_filter}")
            logger.info(f"Has real components to pull: {has_real_components}")
            logger.info(f"Include infrastructure: {include_infrastructure}")
            
            # Check if we need to run the orchestrator at all
            custom_applications = self.options.get('custom_applications', {})
            has_custom_apps = bool(custom_applications and any(custom_applications.values()))
            logger.info(f"Has custom apps: {has_custom_apps}, custom_applications keys: {list(custom_applications.keys())}")
            # Log the actual content
            for k, v in custom_applications.items():
                logger.info(f"  custom_applications['{k}']: {len(v) if v else 0} apps, first app: {v[0].get('name') if v else 'N/A'}")
            
            if not has_real_components and not include_infrastructure:
                # No real components selected - skip orchestrator entirely
                if has_custom_apps:
                    logger.info("Only custom applications selected - skipping API pull")
                    self.progress.emit("Creating configuration with custom applications...", 50)
                    
                    logger.debug("DEBUG: Importing containers module...")
                    # Create minimal configuration with just custom apps
                    from config.models.containers import Configuration, FolderConfig
                    logger.debug("DEBUG: Imported Configuration and FolderConfig")
                    
                    from datetime import datetime
                    logger.debug("DEBUG: Imported datetime")
                    
                    logger.debug(f"DEBUG: Creating Configuration with tsg_id={self.api_client.tsg_id if self.api_client else None}")
                    configuration = Configuration(
                        source_tsg=self.api_client.tsg_id if self.api_client else None,
                        load_type='From Pull (Custom Apps Only)',
                        saved_credentials_ref=self.connection_name
                    )
                    logger.debug("DEBUG: Configuration object created")
                    
                    configuration.source_tenant = self.connection_name
                    configuration.created_at = datetime.now().isoformat()
                    configuration.modified_at = datetime.now().isoformat()
                    configuration.config_version = 1
                    logger.debug("DEBUG: Configuration metadata set")
                    
                    # Add custom applications
                    custom_app_count = 0
                    logger.info(f"DEBUG: Processing {len(custom_applications)} folder(s) with custom apps")
                    
                    for folder_name, apps in custom_applications.items():
                        logger.info(f"DEBUG: Processing folder '{folder_name}' with {len(apps) if apps else 0} apps")
                        if not apps:
                            continue
                        
                        for app_data in apps:
                            try:
                                app_name = app_data.get('name', 'unknown')
                                # Get the app's actual folder from API response
                                actual_folder = app_data.get('folder', folder_name)
                                logger.info(f"DEBUG: Creating ApplicationObject for '{app_name}' in folder '{actual_folder}'")
                                
                                # Import here to catch import errors
                                from config.models.objects import ApplicationObject
                                
                                # Create folder if it doesn't exist
                                if actual_folder not in configuration.folders:
                                    logger.info(f"DEBUG: Creating FolderConfig for '{actual_folder}'")
                                    configuration.folders[actual_folder] = FolderConfig(name=actual_folder)
                                
                                # Check if from_api_response exists
                                if hasattr(ApplicationObject, 'from_api_response'):
                                    app_obj = ApplicationObject.from_api_response(app_data)
                                else:
                                    app_obj = ApplicationObject(raw_config=app_data)
                                
                                logger.info(f"DEBUG: ApplicationObject created, adding to folder '{actual_folder}'")
                                configuration.folders[actual_folder].add_item(app_obj)
                                custom_app_count += 1
                                logger.info(f"DEBUG: Added app '{app_name}' to folder '{actual_folder}'")
                            except Exception as e:
                                logger.warning(f"Failed to add custom app {app_data.get('name')}: {e}")
                                import traceback
                                logger.info(f"DEBUG: Traceback: {traceback.format_exc()}")
                    
                    logger.info(f"Created configuration with {custom_app_count} custom applications")
                    
                    # Skip to finalization (no WorkflowResult, create minimal stats)
                    result = None  # No orchestrator result
                    logger.debug("DEBUG: Custom apps only path complete, proceeding to finalization")
                else:
                    raise Exception("No configuration items selected to pull")
            else:
                # Pull configuration using orchestrator
                # Determine which folders to actually query based on selection
                # Only query folders that have real components selected (not just custom apps)
                folders_to_query = []
                for folder_name, components in folder_filter.items():
                    if components:  # Has real component types selected
                        folders_to_query.append(folder_name)
                
                logger.info(f"Folders to query (with real components): {folders_to_query}")
                
                # If no specific folders with real components, don't query any folders
                # (custom apps are handled separately)
                include_folders_in_pull = bool(folders_to_query) and has_real_components
                
                result = orchestrator.pull_all(
                    include_folders=include_folders_in_pull,
                    include_snippets=bool(snippet_names),
                    include_infrastructure=include_infrastructure,
                    use_bottom_folders=False,  # Use specific folder list instead
                    folder_list=folders_to_query if folders_to_query else None,
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
            
            # Add custom applications that were loaded via Find Applications dialog
            # (only if we went through the orchestrator path - custom apps only path handles this above)
            if result is not None:
                custom_applications = self.options.get('custom_applications', {})
                if custom_applications:
                    from config.models.containers import FolderConfig
                    from config.models.objects import ApplicationObject
                    
                    custom_app_count = 0
                    for folder_name, apps in custom_applications.items():
                        if not apps:
                            continue
                        
                        # Create folder if it doesn't exist
                        if folder_name not in configuration.folders:
                            configuration.folders[folder_name] = FolderConfig(name=folder_name)
                        
                        # Add each application
                        for app_data in apps:
                            try:
                                # Create ApplicationObject from the loaded app data
                                app_obj = ApplicationObject.from_api_response(app_data)
                                configuration.folders[folder_name].add_item(app_obj)
                                custom_app_count += 1
                            except Exception as e:
                                logger.warning(f"Failed to add custom app {app_data.get('name')}: {e}")
                    
                    if custom_app_count > 0:
                        logger.info(f"Added {custom_app_count} custom applications to configuration")
            
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
            if result is not None:
                stats = {
                    'items_processed': result.items_processed,
                    'items_created': result.items_created,
                    'items_skipped': result.items_skipped,
                    'errors': [e.to_dict() for e in result.errors],
                    'warnings': [w.to_dict() for w in result.warnings],
                }
            else:
                # Custom apps only - minimal stats
                custom_apps = self.options.get('custom_applications', {})
                total_apps = sum(len(apps) for apps in custom_apps.values())
                stats = {
                    'items_processed': total_apps,
                    'items_created': total_apps,
                    'items_skipped': 0,
                    'errors': [],
                    'warnings': [],
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
        # Also cancel the orchestrator if it's running
        if hasattr(self, '_orchestrator') and self._orchestrator:
            self._orchestrator.cancel()


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
