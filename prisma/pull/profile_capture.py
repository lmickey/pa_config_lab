"""
Profiles capture for Prisma Access.

This module provides functions to capture:
- Authentication profiles
- Security profiles (antivirus, anti-spyware, vulnerability, etc.)
- Decryption profiles (SSL forward proxy, SSL inbound inspection, etc.)
"""

from typing import Dict, Any, List, Optional
from ..api_client import PrismaAccessAPIClient


class ProfileCapture:
    """Capture profiles from Prisma Access."""

    def __init__(self, api_client: PrismaAccessAPIClient):
        """
        Initialize profile capture.

        Args:
            api_client: PrismaAccessAPIClient instance
        """
        self.api_client = api_client

    def capture_authentication_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Capture authentication profiles.

        Args:
            folder: Folder name (None = all folders)

        Returns:
            List of normalized authentication profiles
        """
        # Skip reserved folders
        RESERVED_FOLDERS = {"Service Connections", "Colo Connect"}
        if folder and folder in RESERVED_FOLDERS:
            return []
        
        try:
            profiles = self.api_client.get_authentication_profiles(folder=folder)
            return [self._normalize_authentication_profile(prof) for prof in profiles]
        except Exception as e:
            # Check if this is a "folder doesn't exist" or pattern validation error
            error_str = str(e).lower()
            if "doesn't exist" in error_str or "400" in error_str or "pattern" in error_str:
                print(f"  ⚠ Folder '{folder}' cannot be used for authentication profiles - skipping")
                return []
            print(f"Error capturing authentication profiles: {e}")
            return []

    def capture_security_profiles(
        self, profile_type: str, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Capture security profiles of a specific type.

        Args:
            profile_type: Type of security profile (anti_spyware, dns_security, etc.)
            folder: Folder name (None = all folders)

        Returns:
            List of normalized security profiles
        """
        # Skip reserved folders
        RESERVED_FOLDERS = {"Service Connections", "Colo Connect"}
        if folder and folder in RESERVED_FOLDERS:
            return []
        
        try:
            # Map profile types to API client methods
            # These match the endpoints marked "include in test" in Master-API-Entpoint-List.txt
            profile_method_map = {
                "anti_spyware": "get_anti_spyware_profiles",
                "dns_security": "get_dns_security_profiles",
                "file_blocking": "get_file_blocking_profiles",
                "http_header": "get_http_header_profiles",
                "profile_groups": "get_profile_groups",
                "url_access": "get_url_access_profiles",
                "vulnerability_protection": "get_vulnerability_protection_profiles",
                "wildfire_anti_virus": "get_wildfire_anti_virus_profiles",
            }

            method_name = profile_method_map.get(profile_type)
            if not method_name:
                print(f"Unknown profile type: {profile_type}")
                return []

            # Call the appropriate API client method
            method = getattr(self.api_client, method_name, None)
            if not method:
                print(f"API client method {method_name} not implemented")
                return []

            profiles = method(folder=folder) if folder else method()
            return [
                self._normalize_security_profile(prof, profile_type)
                for prof in profiles
            ]

        except Exception as e:
            # Check if this is a "folder doesn't exist", pattern validation, or server error
            error_str = str(e).lower()
            if "doesn't exist" in error_str or "400" in error_str or "pattern" in error_str:
                print(f"  ⚠ Folder '{folder}' cannot be used for {profile_type} profiles - skipping")
                return []
            elif "500" in error_str or "503" in error_str or "502" in error_str:
                # Server errors - API is having issues, skip gracefully
                print(f"  ⚠ API server error for {profile_type} profiles in folder '{folder}' - skipping")
                return []
            print(f"Error capturing {profile_type} profiles: {e}")
            return []

    def capture_all_security_profiles(
        self, folder: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Capture all security profile types.

        Args:
            folder: Folder name (None = all folders)

        Returns:
            Dictionary mapping profile types to lists of profiles
        """
        # Profile types to capture (based on master API endpoints list - only those marked "include in test")
        profile_types = [
            "anti_spyware",  # anti-spyware-profiles
            "dns_security",  # dns-security-profiles
            "file_blocking",  # file-blocking-profiles
            "http_header",  # http-header-profiles
            "profile_groups",  # profile-groups
            "url_access",  # url-access-profiles
            "vulnerability_protection",  # vulnerability-protection-profiles
            "wildfire_anti_virus",  # wildfire-anti-virus-profiles
        ]

        # Reduced verbosity - don't print individual profile type captures
        all_profiles = {}
        for profile_type in profile_types:
            profiles = self.capture_security_profiles(profile_type, folder)
            all_profiles[profile_type] = profiles

        return all_profiles

    def capture_decryption_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Capture decryption profiles.

        Args:
            folder: Folder name (None = all folders)

        Returns:
            List of normalized decryption profiles
        """
        # Skip reserved folders
        RESERVED_FOLDERS = {"Service Connections", "Colo Connect"}
        if folder and folder in RESERVED_FOLDERS:
            return []
        
        try:
            # Decryption profiles endpoint (marked "include in test")
            profiles = (
                self.api_client.get_decryption_profiles(folder=folder)
                if folder
                else self.api_client.get_decryption_profiles()
            )
            return [
                self._normalize_decryption_profile(prof, "decryption")
                for prof in profiles
            ]

        except Exception as e:
            # Check if this is a "folder doesn't exist" or pattern validation error
            error_str = str(e).lower()
            if "doesn't exist" in error_str or "400" in error_str or "pattern" in error_str:
                print(f"  ⚠ Folder '{folder}' cannot be used for decryption profiles - skipping")
                return []
            print(f"Error capturing decryption profiles: {e}")
            return []

    def capture_all_profiles(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Capture all profile types from a folder.

        Only captures profiles that were actually created in the specified folder
        (based on the profile's 'folder' property). Profiles from parent folders
        are not included here but should be tracked as dependencies.

        Args:
            folder: Folder name (None = all folders)

        Returns:
            Dictionary with all profile types
        """
        # Reserved/infrastructure folders that cannot have security profiles
        RESERVED_FOLDERS = {
            "Service Connections",  # Infrastructure only - cannot have security policies
            "Colo Connect",         # Infrastructure only - cannot have security policies
            # "Remote Networks",    # CAN have security policies - commented out
            # "Mobile Users",       # CAN have security policies - commented out
            # "Mobile_User_Template",
        }
        
        # Return empty profiles if this is a reserved folder
        if folder and folder in RESERVED_FOLDERS:
            print(f"  ℹ Skipping reserved infrastructure folder: {folder} (cannot have security profiles)")
            return {
                "authentication_profiles": [],
                "security_profiles": {},
                "decryption_profiles": [],
            }
        
        # Capture all profiles visible from this folder
        all_visible_profiles = {
            "authentication_profiles": self.capture_authentication_profiles(folder),
            "security_profiles": self.capture_all_security_profiles(folder),
            "decryption_profiles": self.capture_decryption_profiles(folder),
        }

        # Filter to only profiles created in this specific folder
        # Profiles from parent folders will be tracked as dependencies
        all_profiles = {}
        if folder:
            # Filter authentication profiles
            all_profiles["authentication_profiles"] = [
                prof
                for prof in all_visible_profiles["authentication_profiles"]
                if prof.get("folder", "").strip() == folder.strip()
            ]

            # Filter security profiles (nested dict)
            all_profiles["security_profiles"] = {}
            for profile_type, prof_list in all_visible_profiles[
                "security_profiles"
            ].items():
                filtered_profiles = [
                    prof
                    for prof in prof_list
                    if prof.get("folder", "").strip() == folder.strip()
                ]
                if filtered_profiles:
                    all_profiles["security_profiles"][profile_type] = filtered_profiles

            # Filter decryption profiles
            all_profiles["decryption_profiles"] = [
                prof
                for prof in all_visible_profiles["decryption_profiles"]
                if prof.get("folder", "").strip() == folder.strip()
            ]
        else:
            # If no folder specified, include all profiles
            all_profiles = all_visible_profiles

        # Print brief summary only
        auth_count = len(all_profiles.get("authentication_profiles", []))
        sec_count = sum(
            len(profs) for profs in all_profiles.get("security_profiles", {}).values()
        )
        # Decryption profiles is now a list, not a dict
        dec_profiles = all_profiles.get("decryption_profiles", [])
        dec_count = (
            len(dec_profiles)
            if isinstance(dec_profiles, list)
            else sum(len(profs) for profs in dec_profiles.values())
        )
        total = auth_count + sec_count + dec_count

        if total > 0:
            print(f"  ✓ Captured {total} profiles")

        return all_profiles

    def capture_parent_level_profiles(
        self, folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture profiles from parent folders that are visible to the specified folder.

        These profiles are dependencies for the folder but are not stored in the
        folder's configuration. They should be tracked as dependencies.

        Args:
            folder: Folder name to check parent-level profiles for

        Returns:
            Dictionary mapping profile types to lists of parent-level profiles
        """
        if not folder:
            return {}

        # Capture all profiles visible from this folder
        all_visible_profiles = {
            "authentication_profiles": self.capture_authentication_profiles(folder),
            "security_profiles": self.capture_all_security_profiles(folder),
            "decryption_profiles": self.capture_decryption_profiles(folder),
        }

        # Filter to only profiles NOT created in this folder (i.e., from parent folders)
        parent_profiles = {}

        # Filter authentication profiles
        parent_auth_profiles = [
            prof
            for prof in all_visible_profiles["authentication_profiles"]
            if prof.get("folder", "").strip() != folder.strip()
        ]
        if parent_auth_profiles:
            parent_profiles["authentication_profiles"] = parent_auth_profiles

        # Filter security profiles (nested dict)
        parent_sec_profiles = {}
        for profile_type, prof_list in all_visible_profiles[
            "security_profiles"
        ].items():
            parent_level_profiles = [
                prof
                for prof in prof_list
                if prof.get("folder", "").strip() != folder.strip()
            ]
            if parent_level_profiles:
                parent_sec_profiles[profile_type] = parent_level_profiles
        if parent_sec_profiles:
            parent_profiles["security_profiles"] = parent_sec_profiles

        # Filter decryption profiles
        parent_dec_profiles = [
            prof
            for prof in all_visible_profiles["decryption_profiles"]
            if prof.get("folder", "").strip() != folder.strip()
        ]
        if parent_dec_profiles:
            parent_profiles["decryption_profiles"] = parent_dec_profiles

        return parent_profiles

    def _normalize_authentication_profile(
        self, prof_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize authentication profile."""
        return {
            "id": prof_data.get("id", prof_data.get("name", "")),
            "name": prof_data.get("name", ""),
            "description": prof_data.get("description", ""),
            "type": prof_data.get("type", ""),
            "method": prof_data.get("method", {}),
            "folder": prof_data.get("folder", ""),
            "tags": self._extract_list_field(prof_data, "tags"),
            "metadata": self._extract_metadata(prof_data),
        }

    def _normalize_security_profile(
        self, prof_data: Dict[str, Any], profile_type: str
    ) -> Dict[str, Any]:
        """Normalize security profile."""
        return {
            "id": prof_data.get("id", prof_data.get("name", "")),
            "name": prof_data.get("name", ""),
            "description": prof_data.get("description", ""),
            "type": profile_type,
            "settings": prof_data.get("settings", {}),
            "folder": prof_data.get("folder", ""),
            "tags": self._extract_list_field(prof_data, "tags"),
            "metadata": self._extract_metadata(prof_data),
        }

    def _normalize_decryption_profile(
        self, prof_data: Dict[str, Any], profile_type: str
    ) -> Dict[str, Any]:
        """Normalize decryption profile."""
        return {
            "id": prof_data.get("id", prof_data.get("name", "")),
            "name": prof_data.get("name", ""),
            "description": prof_data.get("description", ""),
            "type": profile_type,
            "settings": prof_data.get("settings", {}),
            "folder": prof_data.get("folder", ""),
            "tags": self._extract_list_field(prof_data, "tags"),
            "metadata": self._extract_metadata(prof_data),
        }

    def _extract_list_field(self, data: Dict[str, Any], field_name: str) -> List[str]:
        """Extract a list field, handling various formats."""
        value = data.get(field_name, [])

        if isinstance(value, list):
            result = []
            for item in value:
                if isinstance(item, dict):
                    result.append(item.get("name", item.get("value", str(item))))
                else:
                    result.append(str(item))
            return result
        elif isinstance(value, dict):
            return [value.get("name", value.get("value", str(value)))]
        elif value:
            return [str(value)]
        else:
            return []

    def _extract_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata fields."""
        return {
            "created": data.get("created", ""),
            "updated": data.get("updated", ""),
            "created_by": data.get("created_by", ""),
            "updated_by": data.get("updated_by", ""),
        }


def capture_profiles_from_folder(
    api_client: PrismaAccessAPIClient, folder: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to capture all profiles from a folder.

    Args:
        api_client: PrismaAccessAPIClient instance
        folder: Folder name (None = all folders)

    Returns:
        Dictionary with all profile types
    """
    capture = ProfileCapture(api_client)
    return capture.capture_all_profiles(folder=folder)
