"""
Conflict Detection and Resolution for Prisma Access Push Operations.

This module provides functionality to detect conflicts when pushing configurations
to a target tenant (e.g., objects with the same name already exist).
"""

from typing import Dict, Any, List, Optional, Set
from enum import Enum


class ConflictResolution(Enum):
    """Conflict resolution strategies."""

    SKIP = "skip"  # Don't push the conflicting item
    OVERWRITE = "overwrite"  # Replace existing with new
    RENAME = "rename"  # Create with new name
    MERGE = "merge"  # Combine configurations (future)


class ConflictResolver:
    """Detect and resolve conflicts when pushing configurations."""

    def __init__(self):
        """Initialize conflict resolver."""
        self.conflicts: List[Dict[str, Any]] = []
        self.resolution_strategy: Dict[str, ConflictResolution] = {}

    def detect_conflicts(
        self,
        source_config: Dict[str, Any],
        target_api_client: Any,  # PrismaAccessAPIClient
        folder_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect conflicts between source configuration and target tenant.

        Args:
            source_config: Configuration to push (from source)
            target_api_client: API client for target tenant
            folder_name: Optional folder name to check conflicts in

        Returns:
            Dictionary with conflict detection results
        """
        self.conflicts = []

        # Detect conflicts in folders
        if "security_policies" in source_config:
            security_policies = source_config["security_policies"]

            # Check folder conflicts
            if "folders" in security_policies:
                for folder in security_policies["folders"]:
                    folder_conflicts = self._detect_folder_conflicts(
                        folder, target_api_client
                    )
                    self.conflicts.extend(folder_conflicts)

            # Check snippet conflicts
            if "snippets" in security_policies:
                for snippet in security_policies["snippets"]:
                    snippet_conflicts = self._detect_snippet_conflicts(
                        snippet, target_api_client
                    )
                    self.conflicts.extend(snippet_conflicts)

        return {
            "has_conflicts": len(self.conflicts) > 0,
            "conflict_count": len(self.conflicts),
            "conflicts": self.conflicts,
            "by_type": self._group_conflicts_by_type(),
        }

    def _detect_folder_conflicts(
        self, folder: Dict[str, Any], api_client: Any
    ) -> List[Dict[str, Any]]:
        """Detect conflicts within a folder."""
        conflicts = []
        folder_name = folder.get("name", "")

        if not folder_name:
            return conflicts

        # Check for existing folder (folders are typically not conflicting - they're containers)
        # But we can check if objects/profiles/rules conflict

        # Check object conflicts
        objects = folder.get("objects", {})
        if objects:
            obj_conflicts = self._detect_object_conflicts(
                objects, api_client, folder_name
            )
            conflicts.extend(obj_conflicts)

        # Check profile conflicts
        profiles = folder.get("profiles", {})
        if profiles:
            profile_conflicts = self._detect_profile_conflicts(
                profiles, api_client, folder_name
            )
            conflicts.extend(profile_conflicts)

        # Check rule conflicts
        rules = folder.get("security_rules", [])
        if rules:
            rule_conflicts = self._detect_rule_conflicts(rules, api_client, folder_name)
            conflicts.extend(rule_conflicts)

        return conflicts

    def _detect_object_conflicts(
        self,
        objects: Dict[str, List[Dict[str, Any]]],
        api_client: Any,
        folder_name: str,
    ) -> List[Dict[str, Any]]:
        """Detect conflicts for objects."""
        conflicts = []

        # Check address objects
        address_objects = objects.get("address_objects", [])
        for addr_obj in address_objects:
            obj_name = addr_obj.get("name", "")
            if obj_name and self._object_exists(
                "address", obj_name, api_client, folder_name
            ):
                conflicts.append(
                    {
                        "type": "address_object",
                        "name": obj_name,
                        "folder": folder_name,
                        "conflict_type": "exists",
                    }
                )

        # Check address groups
        address_groups = objects.get("address_groups", [])
        for addr_group in address_groups:
            group_name = addr_group.get("name", "")
            if group_name and self._object_exists(
                "address_group", group_name, api_client, folder_name
            ):
                conflicts.append(
                    {
                        "type": "address_group",
                        "name": group_name,
                        "folder": folder_name,
                        "conflict_type": "exists",
                    }
                )

        # Check service objects
        service_objects = objects.get("service_objects", [])
        for svc_obj in service_objects:
            obj_name = svc_obj.get("name", "")
            if obj_name and self._object_exists(
                "service", obj_name, api_client, folder_name
            ):
                conflicts.append(
                    {
                        "type": "service_object",
                        "name": obj_name,
                        "folder": folder_name,
                        "conflict_type": "exists",
                    }
                )

        # Check service groups
        service_groups = objects.get("service_groups", [])
        for svc_group in service_groups:
            group_name = svc_group.get("name", "")
            if group_name and self._object_exists(
                "service_group", group_name, api_client, folder_name
            ):
                conflicts.append(
                    {
                        "type": "service_group",
                        "name": group_name,
                        "folder": folder_name,
                        "conflict_type": "exists",
                    }
                )

        # Check applications
        applications = objects.get("applications", [])
        for app in applications:
            app_name = app.get("name", "")
            if app_name and self._object_exists(
                "application", app_name, api_client, folder_name
            ):
                conflicts.append(
                    {
                        "type": "application",
                        "name": app_name,
                        "folder": folder_name,
                        "conflict_type": "exists",
                    }
                )

        return conflicts

    def _detect_profile_conflicts(
        self, profiles: Dict[str, Any], api_client: Any, folder_name: str
    ) -> List[Dict[str, Any]]:
        """Detect conflicts for profiles."""
        conflicts = []

        # Check authentication profiles
        auth_profiles = profiles.get("authentication_profiles", [])
        if isinstance(auth_profiles, list):
            for auth_profile in auth_profiles:
                profile_name = auth_profile.get("name", "")
                if profile_name and self._profile_exists(
                    "authentication", profile_name, api_client, folder_name
                ):
                    conflicts.append(
                        {
                            "type": "authentication_profile",
                            "name": profile_name,
                            "folder": folder_name,
                            "conflict_type": "exists",
                        }
                    )

        # Check security profiles
        security_profiles = profiles.get("security_profiles", {})
        if isinstance(security_profiles, dict):
            for profile_type, profile_list in security_profiles.items():
                if isinstance(profile_list, list):
                    for profile in profile_list:
                        profile_name = profile.get("name", "")
                        if profile_name and self._profile_exists(
                            f"security_{profile_type}",
                            profile_name,
                            api_client,
                            folder_name,
                        ):
                            conflicts.append(
                                {
                                    "type": f"security_profile_{profile_type}",
                                    "name": profile_name,
                                    "folder": folder_name,
                                    "conflict_type": "exists",
                                }
                            )

        # Check decryption profiles
        decryption_profiles = profiles.get("decryption_profiles", [])
        if isinstance(decryption_profiles, list):
            for dec_profile in decryption_profiles:
                profile_name = dec_profile.get("name", "")
                if profile_name and self._profile_exists(
                    "decryption", profile_name, api_client, folder_name
                ):
                    conflicts.append(
                        {
                            "type": "decryption_profile",
                            "name": profile_name,
                            "folder": folder_name,
                            "conflict_type": "exists",
                        }
                    )

        return conflicts

    def _detect_rule_conflicts(
        self, rules: List[Dict[str, Any]], api_client: Any, folder_name: str
    ) -> List[Dict[str, Any]]:
        """Detect conflicts for security rules."""
        conflicts = []

        # Get existing rules from target
        try:
            existing_rules = api_client.get_security_rules(folder=folder_name)
            existing_rule_names = {
                r.get("name", "") for r in existing_rules if r.get("name")
            }

            for rule in rules:
                rule_name = rule.get("name", "")
                if rule_name and rule_name in existing_rule_names:
                    conflicts.append(
                        {
                            "type": "security_rule",
                            "name": rule_name,
                            "folder": folder_name,
                            "conflict_type": "exists",
                        }
                    )
        except Exception:
            # If we can't check, assume no conflicts (will fail during push)
            pass

        return conflicts

    def _detect_snippet_conflicts(
        self, snippet: Dict[str, Any], api_client: Any
    ) -> List[Dict[str, Any]]:
        """Detect conflicts for snippets."""
        conflicts = []
        snippet_name = snippet.get("name", "")

        if snippet_name:
            # Check if snippet exists
            try:
                from ..pull.snippet_capture import SnippetCapture

                snippet_capture = SnippetCapture(api_client)
                existing_snippets = snippet_capture.discover_snippets()
                existing_names = {
                    s.get("name", "") for s in existing_snippets if s.get("name")
                }

                if snippet_name in existing_names:
                    conflicts.append(
                        {
                            "type": "snippet",
                            "name": snippet_name,
                            "folder": None,
                            "conflict_type": "exists",
                        }
                    )
            except Exception:
                pass

        return conflicts

    def _object_exists(
        self, obj_type: str, obj_name: str, api_client: Any, folder_name: str
    ) -> bool:
        """Check if an object exists in the target tenant."""
        try:
            if obj_type == "address":
                objects = api_client.get_addresses(folder=folder_name)
            elif obj_type == "address_group":
                objects = api_client.get_address_groups(folder=folder_name)
            elif obj_type == "service":
                objects = api_client.get_services(folder=folder_name)
            elif obj_type == "service_group":
                objects = api_client.get_service_groups(folder=folder_name)
            elif obj_type == "application":
                objects = api_client.get_applications(folder=folder_name)
            else:
                return False

            if isinstance(objects, list):
                return any(obj.get("name", "") == obj_name for obj in objects)
            elif isinstance(objects, dict) and "data" in objects:
                return any(
                    obj.get("name", "") == obj_name for obj in objects.get("data", [])
                )

            return False
        except Exception:
            # If check fails, assume doesn't exist (will fail during push if it does)
            return False

    def _profile_exists(
        self, profile_type: str, profile_name: str, api_client: Any, folder_name: str
    ) -> bool:
        """Check if a profile exists in the target tenant."""
        try:
            if profile_type == "authentication":
                profiles = api_client.get_authentication_profiles(folder=folder_name)
            elif profile_type.startswith("security_"):
                # Extract security profile type
                sec_type = profile_type.replace("security_", "")
                if sec_type == "anti_spyware":
                    profiles = api_client.get_anti_spyware_profiles(folder=folder_name)
                elif sec_type == "dns_security":
                    profiles = api_client.get_dns_security_profiles(folder=folder_name)
                elif sec_type == "file_blocking":
                    profiles = api_client.get_file_blocking_profiles(folder=folder_name)
                elif sec_type == "http_header":
                    profiles = api_client.get_http_header_profiles(folder=folder_name)
                elif sec_type == "profile_groups":
                    profiles = api_client.get_profile_groups(folder=folder_name)
                elif sec_type == "url_access":
                    profiles = api_client.get_url_access_profiles(folder=folder_name)
                elif sec_type == "vulnerability_protection":
                    profiles = api_client.get_vulnerability_protection_profiles(
                        folder=folder_name
                    )
                elif sec_type == "wildfire_anti_virus":
                    profiles = api_client.get_wildfire_anti_virus_profiles(
                        folder=folder_name
                    )
                else:
                    return False
            elif profile_type == "decryption":
                profiles = api_client.get_decryption_profiles(folder=folder_name)
            else:
                return False

            if isinstance(profiles, list):
                return any(p.get("name", "") == profile_name for p in profiles)
            elif isinstance(profiles, dict) and "data" in profiles:
                return any(
                    p.get("name", "") == profile_name for p in profiles.get("data", [])
                )

            return False
        except Exception:
            # If check fails, assume doesn't exist
            return False

    def _group_conflicts_by_type(self) -> Dict[str, int]:
        """Group conflicts by type."""
        by_type = {}
        for conflict in self.conflicts:
            conflict_type = conflict.get("type", "unknown")
            by_type[conflict_type] = by_type.get(conflict_type, 0) + 1
        return by_type

    def set_resolution_strategy(self, conflict_id: str, strategy: ConflictResolution):
        """
        Set resolution strategy for a specific conflict.

        Args:
            conflict_id: Unique identifier for the conflict
            strategy: Resolution strategy to use
        """
        self.resolution_strategy[conflict_id] = strategy

    def set_default_strategy(self, strategy: ConflictResolution):
        """
        Set default resolution strategy for all conflicts.

        Args:
            strategy: Default resolution strategy
        """
        self.default_strategy = strategy

    def get_conflict_report(self) -> Dict[str, Any]:
        """
        Get conflict detection report.

        Returns:
            Dictionary with conflict report
        """
        return {
            "has_conflicts": len(self.conflicts) > 0,
            "conflict_count": len(self.conflicts),
            "conflicts": self.conflicts,
            "by_type": self._group_conflicts_by_type(),
            "resolution_strategies": {
                k: v.value for k, v in self.resolution_strategy.items()
            },
        }
