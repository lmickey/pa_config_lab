"""
Folder discovery and enumeration for Prisma Access security policies.

This module provides functions to discover, list, and retrieve metadata
for security policy folders in Prisma Access SCM.
"""

from typing import Dict, Any, List, Optional
from ..api_client import PrismaAccessAPIClient
from ..api_endpoints import APIEndpoints
from config.defaults.default_configs import DefaultConfigs


class FolderCapture:
    """Capture security policy folders from Prisma Access."""

    def __init__(self, api_client: PrismaAccessAPIClient):
        """
        Initialize folder capture.

        Args:
            api_client: PrismaAccessAPIClient instance
        """
        self.api_client = api_client

    def discover_folders(self) -> List[Dict[str, Any]]:
        """
        Discover all security policy folders from the API.

        Uses only the security policy folders endpoint - no hardcoded fallbacks.

        Returns:
            List of folder dictionaries with metadata
        """
        all_folders = []

        # Get folders from security policy folders endpoint
        try:
            folders = self.api_client.get_security_policy_folders()
            if folders:
                for folder in folders:
                    normalized = self._normalize_folder(folder)
                    all_folders.append(normalized)
        except Exception as e:
            # Log error but don't add fallback folders
            if "403" in str(e) or "Forbidden" in str(e):
                print(
                    f"  ⚠ Warning: Security policy folders endpoint returned 403 Forbidden"
                )
                print(f"    Cannot discover folders without proper permissions")
            else:
                print(f"  ⚠ Warning: Error accessing security policy folders: {e}")

        return all_folders

    def get_folder_details(self, folder_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific folder.

        Args:
            folder_name: Name of the folder

        Returns:
            Folder details dictionary or None if not found
        """
        try:
            folder_data = self.api_client.get_security_policy_folder(folder_name)

            if folder_data:
                normalized = self._normalize_folder(folder_data)
                return normalized

            return None

        except Exception as e:
            print(f"Error getting folder details for {folder_name}: {e}")
            return None

    def get_folder_hierarchy(self) -> Dict[str, Any]:
        """
        Get folder hierarchy and relationships.

        Returns:
            Dictionary mapping folder names to their hierarchy information
        """
        folders = self.discover_folders()

        hierarchy = {}
        for folder in folders:
            folder_name = folder.get("name", "")
            hierarchy[folder_name] = {
                "name": folder_name,
                "path": folder.get("path", ""),
                "parent": folder.get("parent", None),
                "children": [],
                "level": self._calculate_folder_level(folder.get("path", "")),
            }

        # Build parent-child relationships
        for folder_name, folder_info in hierarchy.items():
            parent = folder_info.get("parent")
            if parent and parent in hierarchy:
                hierarchy[parent]["children"].append(folder_name)

        return hierarchy

    def _normalize_folder(self, folder_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize folder data to standard format.

        Args:
            folder_data: Raw folder data from API

        Returns:
            Normalized folder dictionary
        """
        # Extract common fields
        folder_name = folder_data.get("name", "")
        parent_folder = folder_data.get("parent", None)

        normalized = {
            "name": folder_name,
            "id": folder_data.get("id", folder_data.get("name", "")),
            "path": folder_data.get("path", ""),
            "description": folder_data.get("description", ""),
            "parent": parent_folder,
            "is_default": self._is_default_folder(
                folder_name, parent_folder=parent_folder
            ),
            "metadata": {
                "created": folder_data.get("created", ""),
                "updated": folder_data.get("updated", ""),
                "created_by": folder_data.get("created_by", ""),
                "updated_by": folder_data.get("updated_by", ""),
            },
        }

        # Preserve any additional fields
        for key, value in folder_data.items():
            if key not in normalized and key not in ["metadata"]:
                normalized[key] = value

        return normalized

    def _is_default_folder(
        self, folder_name: str, parent_folder: Optional[str] = None
    ) -> bool:
        """
        Check if folder is a default folder.

        Uses the comprehensive default configuration database.

        Args:
            folder_name: Folder name
            parent_folder: Optional parent folder name

        Returns:
            True if default folder, False otherwise
        """
        return DefaultConfigs.is_default_folder(
            folder_name, parent_folder=parent_folder
        )

    def _calculate_folder_level(self, path: str) -> int:
        """
        Calculate folder level from path.

        Args:
            path: Folder path (e.g., "/config/security-policy/folders/Shared")

        Returns:
            Folder level (0 = root, 1 = first level, etc.)
        """
        if not path:
            return 0

        # Count folder separators in path
        parts = [
            p
            for p in path.split("/")
            if p and p != "config" and p != "security-policy" and p != "folders"
        ]
        return len(parts)

    def list_folders_for_capture(self, include_defaults: bool = False) -> List[str]:
        """
        Get list of folder names to capture.

        Args:
            include_defaults: Whether to include default folders

        Returns:
            List of folder names
        """
        # Reserved/system folders that cannot have security policies
        RESERVED_FOLDERS = {
            "Service Connections",  # Infrastructure only - cannot have security policies
            "Colo Connect",         # Infrastructure only - cannot have security policies
            # "Remote Networks",    # CAN have security policies - commented out
            # "Mobile Users",       # CAN have security policies - commented out
            # "Mobile_User_Template",
            # "Shared",             # Shared is default but can be used
        }
        
        folders = self.discover_folders()

        folder_names = []
        for folder in folders:
            folder_name = folder.get("name", "")
            is_default = folder.get("is_default", False)
            
            # Skip reserved infrastructure-only folders
            if folder_name in RESERVED_FOLDERS:
                print(f"  ℹ Skipping reserved folder: {folder_name} (infrastructure only, cannot have security policies)")
                continue

            if include_defaults or not is_default:
                folder_names.append(folder_name)

        return folder_names


def capture_folders(api_client: PrismaAccessAPIClient) -> List[Dict[str, Any]]:
    """
    Convenience function to capture all folders.

    Args:
        api_client: PrismaAccessAPIClient instance

    Returns:
        List of normalized folder dictionaries
    """
    capture = FolderCapture(api_client)
    return capture.discover_folders()
