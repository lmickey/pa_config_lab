"""
Security rules capture for Prisma Access.

This module provides functions to capture security rules from folders
and snippets, including rule ordering, conditions, actions, and metadata.
"""

from typing import Dict, Any, List, Optional
from ..api_client import PrismaAccessAPIClient


class RuleCapture:
    """Capture security rules from Prisma Access."""

    def __init__(self, api_client: PrismaAccessAPIClient, suppress_output: bool = False):
        """
        Initialize rule capture.

        Args:
            api_client: PrismaAccessAPIClient instance
            suppress_output: Suppress print statements (for GUI usage)
        """
        self.api_client = api_client
        self.suppress_output = suppress_output

    def capture_rules_from_folder(self, folder_name: str) -> List[Dict[str, Any]]:
        """
        Capture all security rules from a specific folder.

        Only captures rules that were actually created in the specified folder
        (based on the rule's 'folder' property). Rules from parent folders
        are not included here but should be tracked as dependencies.

        Args:
            folder_name: Name of the folder

        Returns:
            List of normalized security rule dictionaries
        """
        try:
            # Get all rules visible from this folder
            all_visible_rules = self.api_client.get_all_security_rules(
                folder=folder_name
            )

            # Normalize all visible rules
            normalized_rules = []
            for rule in all_visible_rules:
                normalized = self._normalize_rule(rule, folder_name)
                normalized_rules.append(normalized)

            # Filter to only rules created in this specific folder
            # Rules from parent folders will be tracked as dependencies
            filtered_rules = [
                rule
                for rule in normalized_rules
                if rule.get("folder", "").strip() == folder_name.strip()
            ]

            # Sort by position/priority
            # Handle mixed int/str positions by converting to int or using a default
            def get_position(rule):
                pos = rule.get("position", 999999)
                if isinstance(pos, (int, float)):
                    return pos
                elif isinstance(pos, str):
                    try:
                        return int(pos)
                    except (ValueError, TypeError):
                        return 999999
                else:
                    return 999999

            filtered_rules.sort(key=get_position)

            return filtered_rules

        except Exception as e:
            # Check if folder doesn't exist (400 error) or server error (500)
            error_str = str(e).lower()
            if "doesn't exist" in error_str or "folder" in error_str and ("400" in error_str or "not exist" in error_str or "invalid" in error_str):
                if not self.suppress_output:
                    print(f"⚠ Folder '{folder_name}' does not exist or is invalid - skipping")
                return []
            elif "500" in error_str or "503" in error_str or "502" in error_str:
                # Server errors - API is having issues, skip gracefully
                if not self.suppress_output:
                    print(f"⚠ API server error for rules in folder '{folder_name}' - skipping")
                return []
            
            if not self.suppress_output:
                print(f"Error capturing rules from folder {folder_name}: {e}")
            return []

    def capture_parent_level_rules(self, folder_name: str) -> List[Dict[str, Any]]:
        """
        Capture rules from parent folders that are visible to the specified folder.

        These rules are dependencies for the folder but are not stored in the
        folder's configuration. They should be tracked as dependencies.

        Args:
            folder_name: Folder name to check parent-level rules for

        Returns:
            List of normalized security rule dictionaries from parent folders
        """
        if not folder_name:
            return []

        try:
            # Get all rules visible from this folder
            all_visible_rules = self.api_client.get_all_security_rules(
                folder=folder_name
            )

            # Normalize all visible rules
            normalized_rules = []
            for rule in all_visible_rules:
                normalized = self._normalize_rule(rule, folder_name)
                normalized_rules.append(normalized)

            # Filter to only rules NOT created in this folder (i.e., from parent folders)
            parent_rules = [
                rule
                for rule in normalized_rules
                if rule.get("folder", "").strip() != folder_name.strip()
            ]

            # Sort by position/priority
            def get_position(rule):
                pos = rule.get("position", 999999)
                if isinstance(pos, (int, float)):
                    return pos
                elif isinstance(pos, str):
                    try:
                        return int(pos)
                    except (ValueError, TypeError):
                        return 999999
                else:
                    return 999999

            parent_rules.sort(key=get_position)

            return parent_rules

        except Exception as e:
            if not self.suppress_output:
                print(f"Error capturing parent-level rules from folder {folder_name}: {e}")
            return []

    def capture_rules_from_snippet(self, snippet_name: str) -> List[Dict[str, Any]]:
        """
        Capture all security rules from a specific snippet.

        Args:
            snippet_name: Name of the snippet

        Returns:
            List of normalized security rule dictionaries
        """
        try:
            # Get snippet details
            snippet_data = self.api_client.get_security_policy_snippet(snippet_name)

            if not snippet_data:
                return []

            # Extract rules from snippet
            rules = snippet_data.get("security_rules", [])
            if isinstance(rules, dict) and "data" in rules:
                rules = rules["data"]
            elif not isinstance(rules, list):
                rules = []

            # Normalize rules
            normalized_rules = []
            for rule in rules:
                normalized = self._normalize_rule(rule, snippet_name, is_snippet=True)
                normalized_rules.append(normalized)

            # Sort by position/priority
            # Handle mixed int/str positions by converting to int or using a default
            def get_position(rule):
                pos = rule.get("position", 999999)
                if isinstance(pos, (int, float)):
                    return pos
                elif isinstance(pos, str):
                    try:
                        return int(pos)
                    except (ValueError, TypeError):
                        return 999999
                else:
                    return 999999

            normalized_rules.sort(key=get_position)

            return normalized_rules

        except Exception as e:
            if not self.suppress_output:
                print(f"Error capturing rules from snippet {snippet_name}: {e}")
            return []

    def capture_all_rules(
        self, folder_names: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Capture all security rules from multiple folders.

        Args:
            folder_names: List of folder names (None = all folders)

        Returns:
            Dictionary mapping folder names to their rules
        """
        if folder_names is None:
            # Get all folders
            from .folder_capture import FolderCapture

            folder_capture = FolderCapture(self.api_client)
            folder_names = folder_capture.list_folders_for_capture(
                include_defaults=True
            )

        all_rules = {}

        # Reduced verbosity - only print summary
        for folder_name in folder_names:
            rules = self.capture_rules_from_folder(folder_name)
            all_rules[folder_name] = rules

        # Print brief summary only
        total_rules = sum(len(rules) for rules in all_rules.values())
        if total_rules > 0 and not self.suppress_output:
            print(f"  ✓ Captured {total_rules} rules")

        return all_rules

    def _normalize_rule(
        self, rule_data: Dict[str, Any], context: str, is_snippet: bool = False
    ) -> Dict[str, Any]:
        """
        Normalize security rule data to standard format.

        Args:
            rule_data: Raw rule data from API
            context: Folder or snippet name
            is_snippet: Whether rule is from a snippet

        Returns:
            Normalized rule dictionary
        """
        normalized = {
            "id": rule_data.get("id", rule_data.get("name", "")),
            "name": rule_data.get("name", ""),
            "description": rule_data.get("description", ""),
            "position": rule_data.get("position", rule_data.get("rule_index", 999999)),
            "enabled": rule_data.get("enabled", True),
            "context": context,
            "is_snippet": is_snippet,
            "folder": rule_data.get("folder", context if not is_snippet else ""),
            # Rule conditions
            "source": self._extract_list_field(rule_data, "source"),
            "destination": self._extract_list_field(rule_data, "destination"),
            "application": self._extract_list_field(rule_data, "application"),
            "service": self._extract_list_field(rule_data, "service"),
            "category": self._extract_list_field(rule_data, "category"),
            "source_user": self._extract_list_field(rule_data, "source_user"),
            "source_hip": self._extract_list_field(rule_data, "source_hip"),
            "destination_hip": self._extract_list_field(rule_data, "destination_hip"),
            # Rule actions
            "action": rule_data.get("action", "allow"),
            "log_setting": rule_data.get("log_setting", ""),
            "log_start": rule_data.get("log_start", False),
            "log_end": rule_data.get("log_end", False),
            # Profiles
            "profile_setting": rule_data.get("profile_setting", {}),
            "security_profile": self._extract_list_field(rule_data, "security_profile"),
            "authentication_profile": self._extract_list_field(
                rule_data, "authentication_profile"
            ),
            "decryption_profile": self._extract_list_field(
                rule_data, "decryption_profile"
            ),
            # Tags and metadata
            "tags": self._extract_list_field(rule_data, "tags"),
            "metadata": {
                "created": rule_data.get("created", ""),
                "updated": rule_data.get("updated", ""),
                "created_by": rule_data.get("created_by", ""),
                "updated_by": rule_data.get("updated_by", ""),
            },
        }

        # Preserve any additional fields
        for key, value in rule_data.items():
            if key not in normalized and key not in ["metadata"]:
                normalized[key] = value

        return normalized

    def _extract_list_field(self, data: Dict[str, Any], field_name: str) -> List[str]:
        """
        Extract a list field from rule data, handling various formats.

        Args:
            data: Rule data dictionary
            field_name: Field name to extract

        Returns:
            List of values
        """
        value = data.get(field_name, [])

        if isinstance(value, list):
            # Extract names/values from list items
            result = []
            for item in value:
                if isinstance(item, dict):
                    # Extract name or value field
                    result.append(item.get("name", item.get("value", str(item))))
                else:
                    result.append(str(item))
            return result
        elif isinstance(value, dict):
            # Single item as dict
            return [value.get("name", value.get("value", str(value)))]
        elif value:
            # Single string value
            return [str(value)]
        else:
            return []


def capture_rules_from_folder(
    api_client: PrismaAccessAPIClient, folder_name: str
) -> List[Dict[str, Any]]:
    """
    Convenience function to capture rules from a folder.

    Args:
        api_client: PrismaAccessAPIClient instance
        folder_name: Folder name

    Returns:
        List of normalized security rules
    """
    capture = RuleCapture(api_client)
    return capture.capture_rules_from_folder(folder_name)
