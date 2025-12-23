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

    def __init__(self, api_client: PrismaAccessAPIClient, suppress_output: bool = False):
        """
        Initialize snippet capture.

        Args:
            api_client: PrismaAccessAPIClient instance
            suppress_output: Suppress print statements (for GUI usage)
        """
        self.api_client = api_client
        self.suppress_output = suppress_output
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
                # Store original keys before normalization for filtering purposes
                original_keys = set(snippet.keys())
                
                normalized = self._normalize_snippet(snippet)
                
                # Store original keys for later filtering
                normalized["_original_keys"] = original_keys
                
                normalized_snippets.append(normalized)

            return normalized_snippets

        except Exception as e:
            # Don't print from worker thread - causes segfault
            pass
            return []
    
    def discover_snippets_with_folders(self, debug: bool = False) -> List[Dict[str, Any]]:
        """
        Discover snippets with their folder associations.
        
        Returns snippets with enhanced metadata including:
        - Associated folders
        - Folder names (resolved from IDs)
        - Snippet type/purpose
        
        Filtering logic:
        - Skip snippets with ONLY "id" and "name" fields (system/internal snippets)
        - Keep all others (use display_name if exists, otherwise use name)
        
        Type detection:
        - Predefined: type='predefined' OR type='readonly'
        - Custom: Has enable_prefix field OR no type field
        
        Sorts: custom snippets first, then alphabetically by name.
        
        Args:
            debug: If True, print debug information (only use from main thread)
        
        Returns:
            List of snippets with folder associations
        """
        snippets = self.discover_snippets()
        
        # Filter out snippets with only id and name (system/internal snippets)
        filtered_snippets = []
        skipped_snippets = []
        
        for snippet in snippets:
            snippet_name = snippet.get("name", "")
            
            # Get original keys from API response (before normalization)
            original_keys = snippet.get("_original_keys", set())
            
            # Skip if snippet only has id and name in the original API response
            if original_keys == {"id", "name"} or original_keys == {"name", "id"}:
                skipped_snippets.append(snippet_name)
                continue
            
            # Use display_name if it exists and is not empty, otherwise use name
            display_name = snippet.get("display_name", "").strip()
            if not display_name:
                snippet["display_name"] = snippet_name  # Fallback to name
            
            # Enhance with folder information
            folder_list = snippet.get("folders", [])
            if folder_list:
                # Extract folder names from folder objects
                # Folders can be: [{"id": "...", "name": "..."}] or just ["folder-name"]
                folder_names = []
                for folder in folder_list:
                    if isinstance(folder, dict):
                        folder_name = folder.get("name", "")
                        if folder_name:
                            folder_names.append(folder_name)
                    elif isinstance(folder, str):
                        folder_names.append(folder)
                
                snippet["folder_names"] = folder_names
            else:
                snippet["folder_names"] = []
            
            filtered_snippets.append(snippet)
        
        # Sort: custom first (type not in ['predefined', 'readonly']), then alphabetically by name
        def sort_key(s):
            snippet_type = s.get("type", "")
            is_predefined = snippet_type in ["predefined", "readonly"]
            name = s.get("name", "").lower()
            # Return tuple: (is_predefined, name)
            # False sorts before True, so custom (False) comes first
            return (is_predefined, name)
        
        filtered_snippets.sort(key=sort_key)
        
        # Store debug info in metadata for later retrieval
        if filtered_snippets:
            # Add metadata to first snippet for debugging purposes
            debug_info = {
                "total_from_api": len(snippets),
                "filtered_out": len(skipped_snippets),
                "skipped_names": skipped_snippets,
                "kept": len(filtered_snippets)
            }
            # Store in a way that won't interfere with normal processing
            filtered_snippets[0]["_discovery_debug"] = debug_info
        
        return filtered_snippets

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
                if not self.suppress_output:
                    print(f"  ⚠ WARNING: Empty response for snippet ID {snippet_id}")
                    print(
                        f"    API URL: {self.api_client._make_request.__self__.__class__.__module__}"
                    )
                    print(f"    Response was empty or None")
                return None

            # Check if response looks valid (should have 'id' or 'name' field)
            if not isinstance(snippet_data, dict):
                if not self.suppress_output:
                    print(
                        f"  ⚠ WARNING: Unexpected response type for snippet ID {snippet_id}"
                    )
                    print(f"    Expected: dict")
                    print(f"    Got: {type(snippet_data).__name__}")
                    print(f"    Response: {snippet_data}")
                return None

            if "id" not in snippet_data and "name" not in snippet_data:
                if not self.suppress_output:
                    print(f"  ⚠ WARNING: Response doesn't look like a snippet object")
                    print(f"    Snippet ID: {snippet_id}")
                    print(f"    Response keys: {list(snippet_data.keys())}")
                    print(f"    Response preview: {str(snippet_data)[:200]}")
                # Still try to normalize it - might be valid but missing expected fields
                # return None

            normalized = self._normalize_snippet(snippet_data)
            return normalized

        except Exception as e:
            if not self.suppress_output:
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
            
            if not self.suppress_output:
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
            if not self.suppress_output:
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
                if not self.suppress_output:
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
        # - id, name, display_name, type, last_update, created_in, folders (list), shared_in
        # - enable_prefix (custom snippets)
        
        # Determine if snippet is predefined based on type field
        # Predefined types: "predefined" or "readonly"
        snippet_type = snippet_data.get("type", "")
        is_predefined = snippet_type in ["predefined", "readonly"]
        
        normalized = {
            "name": snippet_data.get("name", ""),
            "id": snippet_data.get("id", ""),
            "display_name": snippet_data.get("display_name", ""),
            "type": snippet_type,
            "path": snippet_data.get(
                "path",
                f"/config/security-policy/snippets/{snippet_data.get('name', '')}",
            ),
            "description": snippet_data.get("description", ""),
            "is_default": is_predefined,  # Use type field instead of name pattern
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
