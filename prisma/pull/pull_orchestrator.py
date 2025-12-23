"""
Pull orchestration for Prisma Access configuration capture.

This module orchestrates the complete pull process, coordinating all
capture modules and providing progress tracking and error handling.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time

from ..api_client import PrismaAccessAPIClient
from .folder_capture import FolderCapture
from .rule_capture import RuleCapture
from .object_capture import ObjectCapture
from .profile_capture import ProfileCapture
from .snippet_capture import SnippetCapture
from config.defaults.default_detector import DefaultDetector
from ..dependencies.dependency_resolver import DependencyResolver


class PullOrchestrator:
    """Orchestrate the complete configuration pull process."""

    def __init__(self, api_client: PrismaAccessAPIClient, detect_defaults: bool = True, suppress_output: bool = False):
        """
        Initialize pull orchestrator.

        Args:
            api_client: PrismaAccessAPIClient instance
            detect_defaults: Whether to detect defaults during capture (default: True)
            suppress_output: Suppress print statements (for GUI usage)
        """
        self.api_client = api_client
        self.suppress_output = suppress_output
        self.folder_capture = FolderCapture(api_client, suppress_output=suppress_output)
        self.rule_capture = RuleCapture(api_client, suppress_output=suppress_output)
        self.object_capture = ObjectCapture(api_client, suppress_output=suppress_output)
        self.profile_capture = ProfileCapture(api_client, suppress_output=suppress_output)
        self.snippet_capture = SnippetCapture(api_client, suppress_output=suppress_output)

        # Initialize default detector
        self.default_detector = DefaultDetector() if detect_defaults else None

        # Initialize dependency resolver
        self.dependency_resolver = DependencyResolver()

        self.progress_callback: Optional[Callable[[str, int, int], None]] = None
        self.error_handler: Optional[Callable[[str, Exception], None]] = None

        self.stats = {
            "folders_captured": 0,
            "rules_captured": 0,
            "objects_captured": 0,
            "profiles_captured": 0,
            "snippets_captured": 0,
            "defaults_detected": 0,
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
            if not self.suppress_output:
                print(f"[{current}/{total}] {message}")

    def _handle_error(self, message: str, error: Exception):
        """Handle error if handler is set."""
        self.stats["errors"].append({"message": message, "error": str(error)})

        if self.error_handler:
            self.error_handler(message, error)
        else:
            if not self.suppress_output:
                print(f"Error: {message} - {error}")

    def pull_folder_configuration(
        self,
        folder_name: str,
        include_objects: bool = True,
        include_profiles: bool = True,
        include_rules: bool = True,
        application_names: Optional[List[str]] = None,
        folder_index: int = 0,
        total_folders: int = 0,
    ) -> Dict[str, Any]:
        """
        Pull complete configuration for a single folder.

        Args:
            folder_name: Name of the folder
            include_objects: Whether to capture objects
            include_profiles: Whether to capture profiles
            include_rules: Whether to capture security rules
            application_names: Optional list of custom application names to capture
            folder_index: Current folder index (for progress reporting)
            total_folders: Total number of folders (for progress reporting)

        Returns:
            Complete folder configuration dictionary
        """
        # Get parent folder info if available
        # Try to get from folder list to check parent
        parent_folder = None
        try:
            folders = self.folder_capture.list_folders_for_capture(
                include_defaults=True
            )
            # Try to find this folder in the list to get parent info
            for folder_info in folders:
                if (
                    isinstance(folder_info, dict)
                    and folder_info.get("name") == folder_name
                ):
                    parent_folder = folder_info.get("parent")
                    break
        except Exception:
            pass

        folder_config = {
            "name": folder_name,
            "path": f"/config/security-policy/folders/{folder_name}",
            "is_default": self.folder_capture._is_default_folder(
                folder_name, parent_folder=parent_folder
            ),
            "parent": parent_folder,
            "security_rules": [],
            "objects": {},
            "profiles": {},
            "hip": {},  # HIP objects and profiles (folder-level)
        }

        try:
            # Calculate sub-tasks for this folder
            total_tasks = 0
            if include_rules:
                total_tasks += 1
            if include_objects:
                total_tasks += 1
            if include_profiles:
                total_tasks += 1
            
            current_task = 0
            
            # Capture security rules (reduced verbosity - progress callback handles output)
            if include_rules:
                current_task += 1
                if total_folders > 0:
                    self._report_progress(
                        f"Folder {folder_index}/{total_folders}: {folder_name} - Capturing rules ({current_task}/{total_tasks})",
                        folder_index - 1 + (current_task / total_tasks),
                        total_folders
                    )
                else:
                    self._report_progress(f"Capturing rules from {folder_name}", current_task, total_tasks)
                
                # Capture rules created in this folder (filtered by folder property)
                rules = self.rule_capture.capture_rules_from_folder(folder_name)

                # Capture parent-level rules that are visible but not created in this folder
                # These are dependencies that need to exist in parent folders
                parent_level_rules = self.rule_capture.capture_parent_level_rules(
                    folder_name=folder_name
                )

                # Detect defaults in rules
                if self.default_detector:
                    rules = self.default_detector.detect_defaults_in_rules(rules)

                folder_config["security_rules"] = rules
                self.stats["rules_captured"] += len(rules)

                # Track parent-level dependencies
                # Initialize parent_dependencies if not already initialized
                if "parent_dependencies" not in folder_config:
                    folder_config["parent_dependencies"] = {}

                # Track parent-level rules as dependencies
                if parent_level_rules:
                    folder_config["parent_dependencies"]["security_rules"] = [
                        {
                            "name": rule.get("name", ""),
                            "folder": rule.get("folder", ""),
                            "type": "security_rule",
                        }
                        for rule in parent_level_rules
                    ]

            # Capture objects (reduced verbosity)
            if include_objects:
                current_task += 1
                if total_folders > 0:
                    self._report_progress(
                        f"Folder {folder_index}/{total_folders}: {folder_name} - Capturing objects ({current_task}/{total_tasks})",
                        folder_index - 1 + (current_task / total_tasks),
                        total_folders
                    )
                else:
                    self._report_progress(f"Capturing objects from {folder_name}", current_task, total_tasks)
                
                # Capture objects created in this folder (filtered by folder property)
                objects = self.object_capture.capture_all_objects(
                    folder=folder_name, application_names=application_names
                )

                # Capture parent-level objects that are visible but not created in this folder
                # These are dependencies that need to exist in parent folders
                parent_level_objects = self.object_capture.capture_parent_level_objects(
                    folder=folder_name
                )

                # Detect defaults in objects (but not applications - user specifies custom apps)
                if self.default_detector:
                    # Don't detect defaults in applications - user has specified custom ones
                    # Still detect defaults in other object types
                    objects_without_apps = {
                        k: v for k, v in objects.items() if k != "applications"
                    }
                    if objects_without_apps:
                        objects_without_apps = (
                            self.default_detector.detect_defaults_in_objects(
                                objects_without_apps
                            )
                        )
                        # Merge back (applications are already custom)
                        for k, v in objects_without_apps.items():
                            objects[k] = v

                folder_config["objects"] = objects

                # Track parent-level dependencies
                # Initialize parent_dependencies if not already initialized
                if "parent_dependencies" not in folder_config:
                    folder_config["parent_dependencies"] = {}

                # These objects are referenced by this folder but created in parent folders
                if parent_level_objects:
                    for obj_type, obj_list in parent_level_objects.items():
                        if obj_list:
                            # Store a summary of parent dependencies (folder and name)
                            folder_config["parent_dependencies"][obj_type] = [
                                {
                                    "name": obj.get("name", ""),
                                    "folder": obj.get("folder", ""),
                                    "type": obj_type,
                                }
                                for obj in obj_list
                            ]

                self.stats["objects_captured"] += sum(
                    len(objs) for objs in objects.values()
                )

            # Capture profiles (reduced verbosity)
            if include_profiles:
                current_task += 1
                if total_folders > 0:
                    self._report_progress(
                        f"Folder {folder_index}/{total_folders}: {folder_name} - Capturing profiles ({current_task}/{total_tasks})",
                        folder_index - 1 + (current_task / total_tasks),
                        total_folders
                    )
                else:
                    self._report_progress(f"Capturing profiles from {folder_name}", current_task, total_tasks)
                # Capture profiles created in this folder (filtered by folder property)
                profiles = self.profile_capture.capture_all_profiles(folder=folder_name)

                # Capture parent-level profiles that are visible but not created in this folder
                # These are dependencies that need to exist in parent folders
                parent_level_profiles = (
                    self.profile_capture.capture_parent_level_profiles(
                        folder=folder_name
                    )
                )

                # Detect defaults in profiles
                if self.default_detector:
                    profiles = self.default_detector.detect_defaults_in_profiles(
                        profiles
                    )

                folder_config["profiles"] = profiles

                # Track parent-level dependencies
                # Initialize parent_dependencies if not already initialized
                if "parent_dependencies" not in folder_config:
                    folder_config["parent_dependencies"] = {}

                # Track parent-level profiles as dependencies
                if parent_level_profiles:
                    # Handle authentication profiles
                    if "authentication_profiles" in parent_level_profiles:
                        folder_config["parent_dependencies"][
                            "authentication_profiles"
                        ] = [
                            {
                                "name": prof.get("name", ""),
                                "folder": prof.get("folder", ""),
                                "type": "authentication_profile",
                            }
                            for prof in parent_level_profiles["authentication_profiles"]
                        ]

                    # Handle security profiles (nested dict)
                    if "security_profiles" in parent_level_profiles:
                        sec_profiles_list = []
                        for profile_type, prof_list in parent_level_profiles[
                            "security_profiles"
                        ].items():
                            for prof in prof_list:
                                sec_profiles_list.append(
                                    {
                                        "name": prof.get("name", ""),
                                        "folder": prof.get("folder", ""),
                                        "type": f"security_profile_{profile_type}",
                                    }
                                )
                        if sec_profiles_list:
                            folder_config["parent_dependencies"][
                                "security_profiles"
                            ] = sec_profiles_list

                    # Handle decryption profiles
                    if "decryption_profiles" in parent_level_profiles:
                        folder_config["parent_dependencies"]["decryption_profiles"] = [
                            {
                                "name": prof.get("name", ""),
                                "folder": prof.get("folder", ""),
                                "type": "decryption_profile",
                            }
                            for prof in parent_level_profiles["decryption_profiles"]
                        ]

                # Count profiles
                auth_count = len(profiles.get("authentication_profiles", []))
                sec_count = sum(
                    len(profs)
                    for profs in profiles.get("security_profiles", {}).values()
                )
            
            # Capture HIP (Host Information Profile) objects and profiles
            # Skip for "Remote Networks" folder - HIP doesn't apply there
            if folder_name != "Remote Networks":
                try:
                    from .infrastructure_capture import InfrastructureCapture
                    infra_capture = InfrastructureCapture(self.api_client, suppress_output=self.suppress_output)
                    hip_data = infra_capture.capture_hip_objects_and_profiles(folder=folder_name)
                    folder_config["hip"] = hip_data
                except Exception as e:
                    # HIP capture is optional - don't fail if it errors
                    if not self.suppress_output:
                        print(f"  ⚠ Warning: Could not capture HIP for folder {folder_name}: {e}")
                    folder_config["hip"] = {"hip_objects": [], "hip_profiles": []}
                # Decryption profiles is now a list, not a dict
                dec_profiles = profiles.get("decryption_profiles", [])
                dec_count = (
                    len(dec_profiles)
                    if isinstance(dec_profiles, list)
                    else sum(len(profs) for profs in dec_profiles.values())
                )
                self.stats["profiles_captured"] += auth_count + sec_count + dec_count

            # Detect defaults in folder configuration
            if self.default_detector:
                folder_config = self.default_detector.detect_defaults_in_folder(
                    folder_config
                )
                # Count defaults detected
                defaults_count = self._count_defaults_in_folder(folder_config)
                self.stats["defaults_detected"] += defaults_count

            self.stats["folders_captured"] += 1

        except Exception as e:
            self._handle_error(f"Error pulling folder {folder_name}", e)

        return folder_config

    def _count_defaults_in_folder(self, folder: Dict[str, Any]) -> int:
        """Count defaults detected in a folder configuration."""
        count = 0

        if folder.get("is_default", False):
            count += 1

        # Count default rules
        rules = folder.get("security_rules", [])
        if isinstance(rules, list):
            count += sum(1 for r in rules if r.get("is_default", False))

        # Count default objects
        objects = folder.get("objects", {})
        if isinstance(objects, dict):
            for obj_list in objects.values():
                if isinstance(obj_list, list):
                    count += sum(1 for o in obj_list if o.get("is_default", False))

        # Count default profiles
        profiles = folder.get("profiles", {})
        if isinstance(profiles, dict):
            # Auth profiles
            auth_profiles = profiles.get("authentication_profiles", [])
            if isinstance(auth_profiles, list):
                count += sum(1 for p in auth_profiles if p.get("is_default", False))

            # Security profiles
            sec_profiles = profiles.get("security_profiles", {})
            if isinstance(sec_profiles, dict):
                for profile_list in sec_profiles.values():
                    if isinstance(profile_list, list):
                        count += sum(
                            1 for p in profile_list if p.get("is_default", False)
                        )

            # Decryption profiles
            dec_profiles = profiles.get("decryption_profiles", [])
            if isinstance(dec_profiles, list):
                count += sum(1 for p in dec_profiles if p.get("is_default", False))

        return count

    def pull_all_folders(
        self,
        folder_names: Optional[List[str]] = None,
        selected_components: Optional[Dict[str, List[str]]] = None,
        include_defaults: bool = False,
        include_objects: bool = True,
        include_profiles: bool = True,
        application_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Pull configuration for all folders.

        Args:
            folder_names: List of folder names (None = all folders)
            selected_components: Dict mapping folder names to component types to pull
                                e.g., {"Mobile Users": ["objects", "rules"]}
                                If None, pulls all components for selected folders
            include_defaults: Whether to include default folders
            include_objects: Whether to capture objects
            include_profiles: Whether to capture profiles
            application_names: Optional list of custom application names to capture

        Returns:
            List of complete folder configurations
        """
        if folder_names is None:
            folder_names = self.folder_capture.list_folders_for_capture(
                include_defaults=include_defaults
            )

        total_folders = len(folder_names)
        folder_configs = []

        for idx, folder_name in enumerate(folder_names, 1):
            # Determine which components to pull for this folder
            if selected_components and folder_name in selected_components:
                components = selected_components[folder_name]
                include_objs = "objects" in components
                include_profs = "profiles" in components
                include_ruls = "rules" in components
            else:
                # Pull all components by default
                include_objs = include_objects
                include_profs = include_profiles
                include_ruls = True  # Always pull rules unless explicitly excluded
            
            folder_config = self.pull_folder_configuration(
                folder_name,
                include_objects=include_objs,
                include_profiles=include_profs,
                include_rules=include_ruls,
                application_names=application_names,
                folder_index=idx,
                total_folders=total_folders,
            )
            folder_configs.append(folder_config)

        return folder_configs

    def pull_snippets(
        self, snippet_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Pull snippet configurations.

        Args:
            snippet_names: Optional list of snippet names/IDs to pull (None = all)
                          Can be list of strings (names) or list of dicts with 'id' and 'name'

        Returns:
            List of snippet configurations with defaults detected
        """
        try:
            # Check if snippet_names contains dicts with IDs (new format)
            if snippet_names and isinstance(snippet_names[0], dict):
                # Pull only selected snippets by ID (efficient)
                snippets = []
                for snippet_info in snippet_names:
                    snippet_id = snippet_info.get('id')
                    snippet_name = snippet_info.get('name')
                    if snippet_id:
                        snippet_config = self.snippet_capture.capture_snippet_configuration(
                            snippet_id, snippet_name
                        )
                        if snippet_config:
                            snippets.append(snippet_config)
            else:
                # Legacy: Pull all and filter by name (slow)
                snippets = self.snippet_capture.capture_all_snippets()
                
                # Filter to specific snippets if requested
                if snippet_names:
                    snippets = [s for s in snippets if s.get("name", "") in snippet_names]

            # Detect defaults in snippets
            if self.default_detector:
                detected_snippets = []
                for snippet in snippets:
                    detected_snippet = self.default_detector.detect_defaults_in_snippet(
                        snippet
                    )
                    detected_snippets.append(detected_snippet)
                snippets = detected_snippets

            self.stats["snippets_captured"] = len(snippets)
            return snippets
        except Exception as e:
            self._handle_error("Error pulling snippets", e)
            return []

    def pull_complete_configuration(
        self,
        folder_names: Optional[List[str]] = None,
        snippet_names: Optional[List[str]] = None,
        selected_components: Optional[Dict[str, List[str]]] = None,
        include_defaults: bool = False,
        include_snippets: bool = True,
        include_objects: bool = True,
        include_profiles: bool = True,
        application_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Pull complete Prisma Access configuration.

        Args:
            folder_names: List of folder names (None = all folders)
            snippet_names: Optional list of snippet names to pull (None = all)
            selected_components: Dict mapping folder names to component types to pull
                                e.g., {"Mobile Users": ["objects", "rules"], "Shared": ["profiles"]}
                                If None, pulls all components for selected folders
            include_defaults: Whether to include default folders
            include_snippets: Whether to capture snippets
            include_objects: Whether to capture objects
            include_profiles: Whether to capture profiles
            application_names: Optional list of custom application names to capture (None = no applications)

        Returns:
            Complete configuration dictionary in v2 format
        """
        from config.schema.config_schema_v2 import create_empty_config_v2

        # Initialize configuration
        config = create_empty_config_v2(
            source_tenant=self.api_client.tsg_id,
            source_type="scm",
            description="Complete configuration pull",
        )

        # Reset stats
        self.stats = {
            "folders_captured": 0,
            "rules_captured": 0,
            "objects_captured": 0,
            "profiles_captured": 0,
            "snippets_captured": 0,
            "defaults_detected": 0,
            "errors": [],
        }

        start_time = time.time()

        try:
            # Pull folders (10-55% in worker)
            self._report_progress("Pulling folder configurations", 10, 100)
            folder_configs = self.pull_all_folders(
                folder_names=folder_names,
                selected_components=selected_components,
                include_defaults=include_defaults,
                include_objects=include_objects,
                include_profiles=include_profiles,
                application_names=application_names,
            )
            config["security_policies"]["folders"] = folder_configs

            # Pull snippets (skip if snippet_names is explicitly empty list)
            if include_snippets and (snippet_names is None or len(snippet_names) > 0):
                self._report_progress("Pulling snippet configurations", 60, 100)
                snippet_configs = self.pull_snippets(snippet_names=snippet_names)
                config["security_policies"]["snippets"] = snippet_configs

                # Count defaults in snippets
                if self.default_detector:
                    defaults_in_snippets = sum(
                        1 for s in snippet_configs if s.get("is_default", False)
                    )
                    self.stats["defaults_detected"] += defaults_in_snippets

            # Pull shared infrastructure settings (if needed)
            self._report_progress("Pulling shared infrastructure settings", 65, 100)
            try:
                infra_settings = self.api_client.get_shared_infrastructure_settings()
                config["infrastructure"][
                    "shared_infrastructure_settings"
                ] = infra_settings
            except Exception as e:
                self._handle_error("Error pulling shared infrastructure settings", e)

            elapsed_time = time.time() - start_time

            # Add pull metadata
            config["metadata"]["pull_stats"] = {
                "folders": self.stats["folders_captured"],
                "rules": self.stats["rules_captured"],
                "objects": self.stats["objects_captured"],
                "profiles": self.stats["profiles_captured"],
                "snippets": self.stats["snippets_captured"],
                "defaults_detected": self.stats.get("defaults_detected", 0),
                "errors": len(self.stats["errors"]),
                "elapsed_seconds": elapsed_time,
            }

            # Add default detection report if detector was used
            if self.default_detector:
                detection_report = self.default_detector.get_detection_report()
                config["metadata"]["default_detection"] = detection_report

            # Build dependency graph and add dependency report
            dependency_report = self.dependency_resolver.get_dependency_report(config)
            config["metadata"]["dependency_report"] = dependency_report

            # Add dependency validation to stats
            if not dependency_report["validation"]["valid"]:
                missing_count = len(
                    dependency_report["validation"]["missing_dependencies"]
                )
                if missing_count > 0:
                    self.stats["errors"].append(
                        {
                            "message": f"Missing dependencies detected: {missing_count} objects have missing dependencies",
                            "type": "dependency_validation",
                        }
                    )

            # Don't report "Pull complete" here - worker will report final status at 80%

        except Exception as e:
            self._handle_error("Error during complete pull", e)

        return config

    def get_pull_report(self) -> Dict[str, Any]:
        """
        Get pull statistics and report.

        Returns:
            Pull report dictionary
        """
        report = {
            "stats": self.stats.copy(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Add default detection report if detector was used
        if self.default_detector:
            detection_report = self.default_detector.get_detection_report()
            report["default_detection"] = detection_report

        return report

    def validate_dependencies(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate dependencies in configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Validation results dictionary
        """
        return self.dependency_resolver.validate_dependencies(config)

    def get_dependency_report(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get dependency report for configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Dependency report dictionary
        """
        return self.dependency_resolver.get_dependency_report(config)
