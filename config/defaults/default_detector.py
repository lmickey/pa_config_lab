"""
Default Configuration Detector for Prisma Access.

This module provides detection logic to identify default configurations
by comparing captured configurations against the default configuration database.
"""

from typing import Dict, Any, List
from .default_configs import DefaultConfigs


class DefaultDetector:
    """Detect default configurations in captured data."""

    def __init__(self, strict_mode: bool = False):
        """
        Initialize default detector.

        Args:
            strict_mode: If True, only exact matches are considered defaults.
                        If False, pattern matching is used (default).
        """
        self.strict_mode = strict_mode
        self.default_configs = DefaultConfigs()
        self.detection_stats = {
            "folders": 0,
            "snippets": 0,
            "rules": 0,
            "objects": 0,
            "profiles": 0,
            "auth_profiles": 0,
            "decryption_profiles": 0,
        }

    def detect_defaults_in_folder(self, folder: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect defaults in a folder configuration.

        Args:
            folder: Folder configuration dictionary

        Returns:
            Folder dictionary with is_default flags set appropriately
        """
        if not folder:
            return folder

        # Check folder name
        folder_name = folder.get("name", "")
        is_default_folder = self.default_configs.is_default_folder(folder_name)

        if is_default_folder:
            self.detection_stats["folders"] += 1

        folder["is_default"] = is_default_folder

        # Detect defaults in folder contents
        if "security_rules" in folder:
            folder["security_rules"] = self.detect_defaults_in_rules(
                folder["security_rules"]
            )

        if "objects" in folder:
            folder["objects"] = self.detect_defaults_in_objects(folder["objects"])

        if "profiles" in folder:
            folder["profiles"] = self.detect_defaults_in_profiles(folder["profiles"])

        return folder

    def detect_defaults_in_snippet(self, snippet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect defaults in a snippet configuration.

        Args:
            snippet: Snippet configuration dictionary

        Returns:
            Snippet dictionary with is_default flag set appropriately
        """
        if not snippet:
            return snippet

        snippet_name = snippet.get("name", "")
        is_default_snippet = self.default_configs.is_default_snippet(snippet_name)

        if is_default_snippet:
            self.detection_stats["snippets"] += 1

        snippet["is_default"] = is_default_snippet

        # Note: Snippets are metadata containers, not config containers
        # They don't contain rules/objects/profiles directly

        return snippet

    def detect_defaults_in_rules(
        self, rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect defaults in a list of security rules.

        Args:
            rules: List of rule dictionaries

        Returns:
            List of rules with is_default flags set
        """
        if not rules:
            return rules

        detected_rules = []
        for rule in rules:
            is_default = self.default_configs.is_default_rule(rule)
            if is_default:
                self.detection_stats["rules"] += 1

            rule["is_default"] = is_default
            detected_rules.append(rule)

        return detected_rules

    def detect_defaults_in_objects(
        self, objects: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect defaults in objects dictionary.

        Args:
            objects: Dictionary mapping object types to lists of objects

        Returns:
            Objects dictionary with is_default flags set
        """
        if not objects:
            return objects

        detected_objects = {}

        for obj_type, obj_list in objects.items():
            if not obj_list:
                detected_objects[obj_type] = []
                continue

            detected_list = []
            for obj in obj_list:
                obj_name = obj.get("name", "")

                # Map object type for detection
                detection_type = None
                if obj_type in ["address_objects", "address_groups"]:
                    detection_type = "address"
                elif obj_type in ["service_objects", "service_groups"]:
                    detection_type = "service"
                elif obj_type == "applications":
                    # Applications are user-specified custom apps only
                    # Don't detect defaults - user has already specified which ones to capture
                    obj["is_default"] = False
                    detected_list.append(obj)
                    continue

                # Pass full object data to check for snippet associations (for non-applications)
                is_default = self.default_configs.is_default_object(
                    obj_name, detection_type, object_data=obj
                )
                if is_default:
                    self.detection_stats["objects"] += 1

                obj["is_default"] = is_default
                detected_list.append(obj)

            detected_objects[obj_type] = detected_list

        return detected_objects

    def detect_defaults_in_profiles(self, profiles: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect defaults in profiles dictionary.

        Args:
            profiles: Dictionary with authentication_profiles, security_profiles, decryption_profiles

        Returns:
            Profiles dictionary with is_default flags set
        """
        if not profiles:
            return profiles

        detected_profiles = {}

        # Detect authentication profiles
        if "authentication_profiles" in profiles:
            auth_profiles = profiles["authentication_profiles"]
            if isinstance(auth_profiles, list):
                detected_auth = []
                for profile in auth_profiles:
                    profile_name = profile.get("name", "")
                    is_default = self.default_configs.is_default_auth_profile(
                        profile_name
                    )
                    if is_default:
                        self.detection_stats["auth_profiles"] += 1

                    profile["is_default"] = is_default
                    detected_auth.append(profile)
                detected_profiles["authentication_profiles"] = detected_auth

        # Detect security profiles
        if "security_profiles" in profiles:
            security_profiles = profiles["security_profiles"]
            if isinstance(security_profiles, dict):
                detected_sec = {}
                for profile_type, profile_list in security_profiles.items():
                    if not isinstance(profile_list, list):
                        detected_sec[profile_type] = profile_list
                        continue

                    detected_list = []
                    for profile in profile_list:
                        profile_name = profile.get("name", "")
                        is_default = self.default_configs.is_default_profile_name(
                            profile_name, profile_type
                        )
                        if is_default:
                            self.detection_stats["profiles"] += 1

                        profile["is_default"] = is_default
                        detected_list.append(profile)

                    detected_sec[profile_type] = detected_list
                detected_profiles["security_profiles"] = detected_sec

        # Detect decryption profiles
        if "decryption_profiles" in profiles:
            decryption_profiles = profiles["decryption_profiles"]
            if isinstance(decryption_profiles, list):
                detected_dec = []
                for profile in decryption_profiles:
                    profile_name = profile.get("name", "")
                    is_default = self.default_configs.is_default_decryption_profile(
                        profile_name
                    )
                    if is_default:
                        self.detection_stats["decryption_profiles"] += 1

                    profile["is_default"] = is_default
                    detected_dec.append(profile)
                detected_profiles["decryption_profiles"] = detected_dec

        return detected_profiles

    def detect_defaults_in_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect defaults in complete configuration dictionary.

        Args:
            config: Complete configuration dictionary (v2.0 schema)

        Returns:
            Configuration dictionary with is_default flags set throughout
        """
        if not config:
            return config

        # Detect defaults in security policies
        if "security_policies" in config:
            security_policies = config["security_policies"]

            # Detect defaults in folders
            if "folders" in security_policies:
                folders = security_policies["folders"]
                if isinstance(folders, list):
                    detected_folders = []
                    for folder in folders:
                        detected_folder = self.detect_defaults_in_folder(folder)
                        detected_folders.append(detected_folder)
                    security_policies["folders"] = detected_folders

            # Detect defaults in snippets
            if "snippets" in security_policies:
                snippets = security_policies["snippets"]
                if isinstance(snippets, list):
                    detected_snippets = []
                    for snippet in snippets:
                        detected_snippet = self.detect_defaults_in_snippet(snippet)
                        detected_snippets.append(detected_snippet)
                    security_policies["snippets"] = detected_snippets

        return config

    def filter_defaults(
        self, config: Dict[str, Any], include_defaults: bool = False
    ) -> Dict[str, Any]:
        """
        Filter out default configurations from config.

        Args:
            config: Configuration dictionary with is_default flags
            include_defaults: If True, include defaults. If False, exclude them.

        Returns:
            Filtered configuration dictionary
        """
        if not config:
            return config

        # First detect defaults if not already done
        config = self.detect_defaults_in_config(config)

        if include_defaults:
            return config

        # Filter out defaults
        if "security_policies" in config:
            security_policies = config["security_policies"]

            # Filter folders
            if "folders" in security_policies:
                folders = security_policies["folders"]
                if isinstance(folders, list):
                    filtered_folders = []
                    for folder in folders:
                        if not folder.get("is_default", False):
                            # Also filter defaults within folder
                            filtered_folder = self._filter_folder_defaults(folder)
                            filtered_folders.append(filtered_folder)
                    security_policies["folders"] = filtered_folders

            # Filter snippets
            if "snippets" in security_policies:
                snippets = security_policies["snippets"]
                if isinstance(snippets, list):
                    filtered_snippets = [
                        s for s in snippets if not s.get("is_default", False)
                    ]
                    security_policies["snippets"] = filtered_snippets

        return config

    def _filter_folder_defaults(self, folder: Dict[str, Any]) -> Dict[str, Any]:
        """Filter defaults from within a folder."""
        filtered_folder = folder.copy()

        # Filter rules
        if "security_rules" in filtered_folder:
            rules = filtered_folder["security_rules"]
            if isinstance(rules, list):
                filtered_folder["security_rules"] = [
                    r for r in rules if not r.get("is_default", False)
                ]

        # Filter objects
        if "objects" in filtered_folder:
            objects = filtered_folder["objects"]
            if isinstance(objects, dict):
                filtered_objects = {}
                for obj_type, obj_list in objects.items():
                    if isinstance(obj_list, list):
                        filtered_objects[obj_type] = [
                            o for o in obj_list if not o.get("is_default", False)
                        ]
                    else:
                        filtered_objects[obj_type] = obj_list
                filtered_folder["objects"] = filtered_objects

        # Filter profiles
        if "profiles" in filtered_folder:
            profiles = filtered_folder["profiles"]
            if isinstance(profiles, dict):
                filtered_profiles = {}

                # Filter auth profiles
                if "authentication_profiles" in profiles:
                    auth_profiles = profiles["authentication_profiles"]
                    if isinstance(auth_profiles, list):
                        filtered_profiles["authentication_profiles"] = [
                            p for p in auth_profiles if not p.get("is_default", False)
                        ]

                # Filter security profiles
                if "security_profiles" in profiles:
                    sec_profiles = profiles["security_profiles"]
                    if isinstance(sec_profiles, dict):
                        filtered_sec = {}
                        for profile_type, profile_list in sec_profiles.items():
                            if isinstance(profile_list, list):
                                filtered_sec[profile_type] = [
                                    p
                                    for p in profile_list
                                    if not p.get("is_default", False)
                                ]
                            else:
                                filtered_sec[profile_type] = profile_list
                        filtered_profiles["security_profiles"] = filtered_sec

                # Filter decryption profiles
                if "decryption_profiles" in profiles:
                    dec_profiles = profiles["decryption_profiles"]
                    if isinstance(dec_profiles, list):
                        filtered_profiles["decryption_profiles"] = [
                            p for p in dec_profiles if not p.get("is_default", False)
                        ]

                filtered_folder["profiles"] = filtered_profiles

        return filtered_folder

    def get_detection_report(self) -> Dict[str, Any]:
        """
        Get report of detected defaults.

        Returns:
            Dictionary with detection statistics
        """
        return {
            "stats": self.detection_stats.copy(),
            "summary": {
                "total_defaults": sum(self.detection_stats.values()),
                "by_category": self.detection_stats.copy(),
            },
        }

    def reset_stats(self):
        """Reset detection statistics."""
        self.detection_stats = {
            "folders": 0,
            "snippets": 0,
            "rules": 0,
            "objects": 0,
            "profiles": 0,
            "auth_profiles": 0,
            "decryption_profiles": 0,
        }
