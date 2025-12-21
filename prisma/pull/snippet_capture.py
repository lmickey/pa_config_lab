"""
Snippet configuration capture for Prisma Access.

This module provides functions to discover and capture snippet configurations,
including snippet-specific security rules, objects, and profiles.
"""

from typing import Dict, Any, List, Optional
from ..api_client import PrismaAccessAPIClient
from .rule_capture import RuleCapture
from .object_capture import ObjectCapture
from .profile_capture import ProfileCapture
from config.defaults.default_configs import DefaultConfigs


class SnippetCapture:
    """Capture snippets from Prisma Access."""

    def __init__(self, api_client: PrismaAccessAPIClient):
        """
        Initialize snippet capture.

        Args:
            api_client: PrismaAccessAPIClient instance
        """
        self.api_client = api_client
        self.rule_capture = RuleCapture(api_client)
        self.object_capture = ObjectCapture(api_client)
        self.profile_capture = ProfileCapture(api_client)

    def discover_snippets(self) -> List[Dict[str, Any]]:
        """
        Discover all security policy snippets.

        Returns:
            List of snippet dictionaries with metadata
        """
        try:
            snippets = self.api_client.get_security_policy_snippets()

            # Normalize snippet data
            normalized_snippets = []
            for snippet in snippets:
                normalized = self._normalize_snippet(snippet)
                normalized_snippets.append(normalized)

            return normalized_snippets

        except Exception as e:
            print(f"Error discovering snippets: {e}")
            return []

    def get_snippet_details(self, snippet_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific snippet by ID.

        Args:
            snippet_id: ID of the snippet (not name)

        Returns:
            Snippet details dictionary or None if not found
        """
        try:
            snippet_data = self.api_client.get_security_policy_snippet(snippet_id)

            # Add detailed logging for debugging
            if not snippet_data:
                print(f"  ⚠ WARNING: Empty response for snippet ID {snippet_id}")
                print(
                    f"    API URL: {self.api_client._make_request.__self__.__class__.__module__}"
                )
                print(f"    Response was empty or None")
                return None

            # Check if response looks valid (should have 'id' or 'name' field)
            if not isinstance(snippet_data, dict):
                print(
                    f"  ⚠ WARNING: Unexpected response type for snippet ID {snippet_id}"
                )
                print(f"    Expected: dict")
                print(f"    Got: {type(snippet_data).__name__}")
                print(f"    Response: {snippet_data}")
                return None

            if "id" not in snippet_data and "name" not in snippet_data:
                print(f"  ⚠ WARNING: Response doesn't look like a snippet object")
                print(f"    Snippet ID: {snippet_id}")
                print(f"    Response keys: {list(snippet_data.keys())}")
                print(f"    Response preview: {str(snippet_data)[:200]}")
                # Still try to normalize it - might be valid but missing expected fields
                # return None

            normalized = self._normalize_snippet(snippet_data)
            return normalized

        except Exception as e:
            print(f"  ✗ FAILED: Error getting snippet details for ID {snippet_id}")
            print(f"    Error type: {type(e).__name__}")
            print(f"    Error message: {str(e)}")
            from prisma.error_logger import error_logger

            error_logger.log_capture_error(
                "get_snippet_details",
                snippet_id,
                e,
                {
                    "snippet_id": snippet_id,
                    "api_url": f"https://api.strata.paloaltonetworks.com/config/setup/v1/snippets/{snippet_id}",
                },
            )
            import traceback

            print("\n    Full traceback:")
            traceback.print_exc()
            return None

    def capture_snippet_configuration(
        self, snippet_id: str, snippet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture complete configuration for a snippet by ID.

        Args:
            snippet_id: ID of the snippet (required for API access)
            snippet_name: Optional name of the snippet (for display/logging)

        Returns:
            Complete snippet configuration dictionary
        """
        # Reduced verbosity - only print errors, not success details
        # Get snippet details using ID
        snippet_info = self.get_snippet_details(snippet_id)
        if not snippet_info:
            display_name = snippet_name or snippet_id
            print(
                f"  ✗ FAILED: Could not retrieve snippet details for {display_name} (ID: {snippet_id})"
            )
            print(
                f"    API URL: https://api.strata.paloaltonetworks.com/config/setup/v1/snippets/{snippet_id}"
            )
            print(f"    Check error log for detailed API request/response information")
            return {}

        # Snippets are high-level configuration parameters (like folders), not containers
        # They don't contain rules, objects, or profiles - those are associated with folders
        # The snippet detail response contains:
        # - id, name, last_update, created_in, folders (list), shared_in
        # So we just return the snippet info as-is without trying to capture nested data

        # No verbose output for successful captures - errors are already logged

        return snippet_info

    def capture_all_snippets(self) -> List[Dict[str, Any]]:
        """
        Capture all snippets with their complete configurations.

        Returns:
            List of complete snippet configurations
        """
        snippets = self.discover_snippets()

        captured_snippets = []
        for snippet in snippets:
            snippet_id = snippet.get("id", "")
            snippet_name = snippet.get("name", "")

            if snippet_id:
                # Use ID for API access, name for display/logging
                config = self.capture_snippet_configuration(snippet_id, snippet_name)
                if config:
                    captured_snippets.append(config)
            else:
                print(f"  ⚠ WARNING: Snippet '{snippet_name}' has no ID, skipping")

        return captured_snippets

    def _normalize_snippet(self, snippet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize snippet data to standard format.

        Args:
            snippet_data: Raw snippet data from API (direct JSON object from /snippets/:id endpoint)

        Returns:
            Normalized snippet dictionary
        """
        # Expected fields from snippet-detail.txt:
        # - id, name, last_update, created_in, folders (list), shared_in
        normalized = {
            "name": snippet_data.get("name", ""),
            "id": snippet_data.get("id", ""),
            "path": snippet_data.get(
                "path",
                f"/config/security-policy/snippets/{snippet_data.get('name', '')}",
            ),
            "description": snippet_data.get("description", ""),
            "is_default": self._is_default_snippet(snippet_data.get("name", "")),
            "folders": snippet_data.get(
                "folders", []
            ),  # List of folder objects with id and name
            "shared_in": snippet_data.get("shared_in", ""),
            "last_update": snippet_data.get("last_update", ""),
            "created_in": snippet_data.get("created_in", ""),
            "metadata": {
                "created": snippet_data.get(
                    "created_in", snippet_data.get("created", "")
                ),
                "updated": snippet_data.get(
                    "last_update", snippet_data.get("updated", "")
                ),
                "created_by": snippet_data.get("created_by", ""),
                "updated_by": snippet_data.get("updated_by", ""),
            },
            # Placeholders for captured data (snippets are high-level config, not containers)
            "security_rules": [],
            "objects": {},
            "profiles": {},
        }

        # Preserve any additional fields from the API response
        for key, value in snippet_data.items():
            if key not in normalized and key not in ["metadata"]:
                normalized[key] = value

        return normalized

    def _is_default_snippet(self, snippet_name: str) -> bool:
        """
        Check if snippet is a default snippet.

        Uses the comprehensive default configuration database.

        Args:
            snippet_name: Snippet name

        Returns:
            True if default snippet, False otherwise
        """
        return DefaultConfigs.is_default_snippet(snippet_name)

    def map_snippet_relationships(self) -> Dict[str, List[str]]:
        """
        Map snippet relationships to folders.

        Returns:
            Dictionary mapping snippet names to list of associated folders
        """
        snippets = self.discover_snippets()
        relationships = {}

        for snippet in snippets:
            snippet_name = snippet.get("name", "")
            folder = snippet.get("folder", "")

            if snippet_name:
                if snippet_name not in relationships:
                    relationships[snippet_name] = []

                if folder:
                    relationships[snippet_name].append(folder)

        return relationships


def capture_snippets(api_client: PrismaAccessAPIClient) -> List[Dict[str, Any]]:
    """
    Convenience function to capture all snippets.

    Args:
        api_client: PrismaAccessAPIClient instance

    Returns:
        List of complete snippet configurations
    """
    capture = SnippetCapture(api_client)
    return capture.capture_all_snippets()
