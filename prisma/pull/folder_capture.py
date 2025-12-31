"""
Folder discovery and enumeration for Prisma Access security policies.

This module provides functions to discover, list, and retrieve metadata
for security policy folders in Prisma Access SCM.
"""

from typing import Dict, Any, List, Optional, Set
from ..api_client import PrismaAccessAPIClient
from ..api_endpoints import APIEndpoints
from config.defaults.default_configs import DefaultConfigs


# Reserved/system folders that cannot have security policies
INFRASTRUCTURE_ONLY_FOLDERS: Set[str] = {
    "Service Connections",  # Infrastructure only - cannot have security policies
    "Colo Connect",         # Infrastructure only - cannot have security policies
}

# Folders that are not Prisma Access specific (filter from config migration)
NON_PRISMA_ACCESS_FOLDERS: Set[str] = {
    "all",          # Global/shared container - not Prisma Access specific
    "ngfw-shared",  # NGFW-shared - not part of Prisma Access service
}

# Combined exclusion list for config migration
MIGRATION_EXCLUDED_FOLDERS: Set[str] = INFRASTRUCTURE_ONLY_FOLDERS | NON_PRISMA_ACCESS_FOLDERS


class FolderCapture:
    """Capture security policy folders from Prisma Access."""

    def __init__(self, api_client: PrismaAccessAPIClient, suppress_output: bool = False):
        """
        Initialize folder capture.

        Args:
            api_client: PrismaAccessAPIClient instance
            suppress_output: Suppress print statements (for GUI usage)
        """
        self.api_client = api_client
        self.suppress_output = suppress_output

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
            if not self.suppress_output:
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
            if not self.suppress_output:
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
        Preserve full folder data for push.

        Args:
            folder_data: Raw folder data from API

        Returns:
            Normalized folder dictionary with all original data preserved
        """
        # Make a deep copy to preserve all fields
        normalized = folder_data.copy()
        
        # Remove only the 'id' field
        normalized.pop('id', None)
        
        # Ensure required fields exist
        folder_name = normalized.get("name", "")
        parent_folder = normalized.get("parent", None)
        normalized.setdefault('name', '')
        
        # Add our tracking fields (non-intrusive)
        normalized['is_default'] = self._is_default_folder(
            folder_name, parent_folder=parent_folder
        )
        
        # Add metadata for tracking if not present
        if 'metadata' not in normalized:
            normalized['metadata'] = {
                "created": folder_data.get("created", ""),
                "updated": folder_data.get("updated", ""),
                "created_by": folder_data.get("created_by", ""),
                "updated_by": folder_data.get("updated_by", ""),
            }

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

    def discover_folders_for_migration(
        self, include_defaults: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Discover folders suitable for Prisma Access configuration migration.
        
        Automatically filters out:
        - Infrastructure-only folders (Service Connections, Colo Connect)
        - Non-Prisma Access folders (all, ngfw)
        - Default folders (if include_defaults=False)
        
        Args:
            include_defaults: Whether to include default folders
            
        Returns:
            List of filtered folders suitable for migration
        """
        # Get all folders
        all_folders = self.discover_folders()
        
        # Filter for migration
        filtered = filter_folders_for_migration(all_folders)
        
        # Optionally filter defaults
        if not include_defaults:
            filtered = [
                f for f in filtered 
                if not f.get("is_default", False)
            ]
        
        return filtered

    def list_folders_for_capture(self, include_defaults: bool = False) -> List[str]:
        """
        Get list of folder names to capture.

        Args:
            include_defaults: Whether to include default folders

        Returns:
            List of folder names
        """
        # Use the new migration-aware discovery
        folders = self.discover_folders_for_migration(include_defaults=include_defaults)
        
        # Extract folder names
        folder_names = [folder.get("name", "") for folder in folders]
        
        return folder_names


def filter_folders_for_migration(folders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter folders for Prisma Access configuration migration.
    
    Excludes:
    - Infrastructure-only folders (Service Connections, Colo Connect)
    - Non-Prisma Access folders (all, ngfw)
    
    Args:
        folders: List of discovered folders
        
    Returns:
        Filtered list of folders suitable for Prisma Access migration
    """
    filtered = []
    filtered_out = []
    
    for folder in folders:
        folder_name = folder.get("name", "")
        
        # Skip excluded folders (case-insensitive)
        if folder_name in MIGRATION_EXCLUDED_FOLDERS:
            filtered_out.append(folder_name)
            continue
        
        # Also check case-insensitive
        if folder_name.lower() in {name.lower() for name in MIGRATION_EXCLUDED_FOLDERS}:
            filtered_out.append(folder_name)
            continue
        
        # Keep this folder
        filtered.append(folder)
    
    # Log filtered folders if any (this is a module-level function, so check if suppress_output should be passed)
    # Note: This function is called from outside the class, so we can't check self.suppress_output
    # For now, keep this print as it's informational and not in a worker thread context
    
    return filtered


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
