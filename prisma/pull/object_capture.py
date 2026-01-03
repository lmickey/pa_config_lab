"""
Objects capture for Prisma Access.

This module provides functions to capture all object types including:
- Address objects and groups
- Service objects and groups
- Application filters, groups, and signatures
- URL filtering categories
- External dynamic lists
- FQDN objects
"""

from typing import Dict, Any, List, Optional
from ..api_client import PrismaAccessAPIClient


class ObjectCapture:
    """Capture objects from Prisma Access."""

    def __init__(self, api_client: PrismaAccessAPIClient, suppress_output: bool = False):
        """
        Initialize object capture.

        Args:
            api_client: PrismaAccessAPIClient instance
            suppress_output: Suppress print statements (for GUI usage)
        """
        self.api_client = api_client
        self.suppress_output = suppress_output

    def capture_addresses(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Capture address objects.

        Args:
            folder: Folder name (None = all folders)

        Returns:
            List of normalized address objects
        """
        # Skip reserved folders
        RESERVED_FOLDERS = {"Service Connections", "Colo Connect"}
        if folder and folder in RESERVED_FOLDERS:
            return []
        
        try:
            addresses = self.api_client.get_all_addresses(folder=folder)
            return [self._normalize_address(addr) for addr in addresses]
        except Exception as e:
            # Check if this is a "folder doesn't exist", pattern validation, or server error
            error_str = str(e).lower()
            if "doesn't exist" in error_str or "400" in error_str or "pattern" in error_str:
                if not self.suppress_output:
                    logger.warning(f"  ⚠ Folder '{folder}' cannot be used for addresses - skipping")
                return []
            elif "500" in error_str or "503" in error_str or "502" in error_str:
                # Server errors - API is having issues, skip gracefully
                if not self.suppress_output:
                    logger.warning(f"  ⚠ API server error for addresses in folder '{folder}' - skipping")
                return []
            if not self.suppress_output:
                logger.error(f"Error capturing addresses: {e}")
            # Log to centralized error logger
            try:
                from ...error_logger import error_logger

                error_logger.log_capture_error(
                    "capture_addresses",
                    folder if folder else "default",
                    e,
                    {"folder": folder},
                )
            except Exception:
                pass  # Don't fail if logging fails
            return []

    def capture_address_groups(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Capture address groups.

        Args:
            folder: Folder name (None = all folders)

        Returns:
            List of normalized address groups
        """
        # Skip reserved folders
        RESERVED_FOLDERS = {"Service Connections", "Colo Connect"}
        if folder and folder in RESERVED_FOLDERS:
            return []
        
        try:
            groups = self.api_client.get_all_address_groups(folder=folder)
            return [self._normalize_address_group(grp) for grp in groups]
        except Exception as e:
            if not self.suppress_output:
                logger.error(f"Error capturing address groups: {e}")
            try:
                from ...error_logger import error_logger

                error_logger.log_capture_error(
                    "capture_address_groups",
                    folder if folder else "default",
                    e,
                    {"folder": folder},
                )
            except Exception:
                pass
            return []

    def capture_services(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Capture service objects.

        Args:
            folder: Folder name (None = all folders)

        Returns:
            List of normalized service objects
        """
        # Skip reserved folders
        RESERVED_FOLDERS = {"Service Connections", "Colo Connect"}
        if folder and folder in RESERVED_FOLDERS:
            return []
        
        try:
            services = self.api_client.get_services(folder=folder)
            return [self._normalize_service(svc) for svc in services]
        except Exception as e:
            # Check if this is a "folder doesn't exist", pattern validation, or server error
            error_str = str(e).lower()
            if "doesn't exist" in error_str or "400" in error_str or "pattern" in error_str:
                if not self.suppress_output:
                    logger.warning(f"  ⚠ Folder '{folder}' cannot be used for services - skipping")
                return []
            elif "500" in error_str or "503" in error_str or "502" in error_str:
                # Server errors - API is having issues, skip gracefully
                if not self.suppress_output:
                    logger.warning(f"  ⚠ API server error for services in folder '{folder}' - skipping")
                return []
            if not self.suppress_output:
                logger.error(f"Error capturing services: {e}")
            try:
                from ...error_logger import error_logger

                error_logger.log_capture_error(
                    "capture_services",
                    folder if folder else "default",
                    e,
                    {"folder": folder},
                )
            except Exception:
                pass
            return []

    def capture_service_groups(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Capture service groups.

        Args:
            folder: Folder name (None = all folders)

        Returns:
            List of normalized service groups
        """
        # Skip reserved folders
        RESERVED_FOLDERS = {"Service Connections", "Colo Connect"}
        if folder and folder in RESERVED_FOLDERS:
            return []
        
        try:
            # Note: Service groups endpoint may need to be added to API client
            # For now, using a placeholder
            groups = []  # self.api_client.get_service_groups(folder=folder)
            return [self._normalize_service_group(grp) for grp in groups]
        except Exception as e:
            if not self.suppress_output:
                logger.error(f"Error capturing service groups: {e}")
            try:
                from ...error_logger import error_logger

                error_logger.log_capture_error(
                    "capture_service_groups",
                    folder if folder else "default",
                    e,
                    {"folder": folder},
                )
            except Exception:
                pass
            return []

    def capture_applications(
        self,
        folder: Optional[str] = None,
        application_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Capture application objects.

        Args:
            folder: Folder name (None = all folders)
            application_names: Optional list of specific application names to capture (None = all)

        Returns:
            List of normalized application objects
        """
        # Skip reserved folders
        RESERVED_FOLDERS = {"Service Connections", "Colo Connect"}
        if folder and folder in RESERVED_FOLDERS:
            return []
        
        try:
            if application_names:
                # Only capture specified applications
                all_applications = self.api_client.get_all_applications(folder=folder)
                # Filter to requested applications (case-insensitive)
                app_names_lower = [name.lower() for name in application_names]
                filtered_apps = [
                    app
                    for app in all_applications
                    if app.get("name", "").lower() in app_names_lower
                ]
                return [self._normalize_application(app) for app in filtered_apps]
            else:
                # No applications to capture (user said no custom apps)
                return []
        except Exception as e:
            if not self.suppress_output:
                logger.error(f"Error capturing applications: {e}")
            try:
                from ...error_logger import error_logger

                error_logger.log_capture_error(
                    "capture_applications",
                    folder if folder else "default",
                    e,
                    {"folder": folder, "application_names": application_names},
                )
            except Exception:
                pass
            return []

    def capture_all_objects(
        self,
        folder: Optional[str] = None,
        application_names: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Capture all object types from a folder.

        Only captures objects that were actually created in the specified folder
        (based on the object's 'folder' property). Objects from parent folders
        are not included here but should be tracked as dependencies.

        Args:
            folder: Folder name (None = all folders)
            application_names: Optional list of specific application names to capture

        Returns:
            Dictionary mapping object types to lists of objects
        """
        # Reserved/infrastructure folders that cannot have security objects
        RESERVED_FOLDERS = {
            "Service Connections",  # Infrastructure only - cannot have security policies
            "Colo Connect",         # Infrastructure only - cannot have security policies
            # "Remote Networks",    # CAN have security policies - commented out
            # "Mobile Users",       # CAN have security policies - commented out
            # "Mobile_User_Template",
        }
        
        # Return empty objects if this is a reserved folder
        if folder and folder in RESERVED_FOLDERS:
            if not self.suppress_output:
                logger.info(f"  ℹ Skipping reserved infrastructure folder: {folder} (cannot have security objects)")
            return {
                "address_objects": [],
                "address_groups": [],
                "service_objects": [],
                "service_groups": [],
                "applications": [],
                "application_groups": [],
                "application_filters": [],
                "url_filtering_categories": [],
                "external_dynamic_lists": [],
                "fqdn_objects": [],
            }
        
        # Capture all objects visible from this folder
        all_visible_objects = {
            "address_objects": self.capture_addresses(folder),
            "address_groups": self.capture_address_groups(folder),
            "service_objects": self.capture_services(folder),
            "service_groups": self.capture_service_groups(folder),
            "applications": self.capture_applications(
                folder, application_names=application_names
            ),
            "application_groups": [],  # To be implemented
            "application_filters": [],  # To be implemented
            "url_filtering_categories": [],  # To be implemented
            "external_dynamic_lists": [],  # To be implemented
            "fqdn_objects": [],  # To be implemented
        }

        # Filter to only objects created in this specific folder
        # Objects from parent folders will be tracked as dependencies
        all_objects = {}
        for obj_type, obj_list in all_visible_objects.items():
            if folder:
                # Only include objects where the folder property matches
                # This ensures objects are only stored at their creation level
                filtered_objects = [
                    obj
                    for obj in obj_list
                    if obj.get("folder", "").strip() == folder.strip()
                ]
                all_objects[obj_type] = filtered_objects
            else:
                # If no folder specified, include all objects
                all_objects[obj_type] = obj_list

        # Print brief summary only
        total = sum(len(objs) for objs in all_objects.values())
        if total > 0 and not self.suppress_output:
            logger.info(f"  ✓ Captured {total} objects")

        return all_objects

    def capture_parent_level_objects(
        self, folder: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Capture objects from parent folders that are visible to the specified folder.

        These objects are dependencies for the folder but are not stored in the
        folder's configuration. They should be tracked as dependencies.

        Args:
            folder: Folder name to check parent-level objects for

        Returns:
            Dictionary mapping object types to lists of parent-level objects
        """
        if not folder:
            return {}

        # Capture all objects visible from this folder
        all_visible_objects = {
            "address_objects": self.capture_addresses(folder),
            "address_groups": self.capture_address_groups(folder),
            "service_objects": self.capture_services(folder),
            "service_groups": self.capture_service_groups(folder),
            "applications": self.capture_applications(folder, application_names=None),
        }

        # Filter to only objects NOT created in this folder (i.e., from parent folders)
        parent_objects = {}
        for obj_type, obj_list in all_visible_objects.items():
            parent_level_objects = [
                obj
                for obj in obj_list
                if obj.get("folder", "").strip() != folder.strip()
            ]
            if parent_level_objects:
                parent_objects[obj_type] = parent_level_objects

        return parent_objects

    def _normalize_address(self, addr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve full address object data for push."""
        # Make a deep copy to preserve all fields
        normalized = addr_data.copy()
        
        # Remove only the 'id' field
        normalized.pop('id', None)
        
        # Ensure required fields exist
        normalized.setdefault('name', '')
        normalized.setdefault('folder', '')
        
        # Add metadata for tracking
        if 'metadata' not in normalized:
            normalized['metadata'] = self._extract_metadata(addr_data)
        
        return normalized

    def _normalize_address_group(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve full address group data for push."""
        # Make a deep copy to preserve all fields
        normalized = group_data.copy()
        
        # Remove only the 'id' field
        normalized.pop('id', None)
        
        # Ensure required fields exist
        normalized.setdefault('name', '')
        normalized.setdefault('folder', '')
        
        # Add metadata for tracking
        if 'metadata' not in normalized:
            normalized['metadata'] = self._extract_metadata(group_data)
        
        return normalized

    def _normalize_service(self, svc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve full service object data for push."""
        # Make a deep copy to preserve all fields
        normalized = svc_data.copy()
        
        # Remove only the 'id' field
        normalized.pop('id', None)
        
        # Ensure required fields exist
        normalized.setdefault('name', '')
        normalized.setdefault('folder', '')
        
        # Add metadata for tracking
        if 'metadata' not in normalized:
            normalized['metadata'] = self._extract_metadata(svc_data)
        
        return normalized

    def _normalize_service_group(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve full service group data for push."""
        # Make a deep copy to preserve all fields
        normalized = group_data.copy()
        
        # Remove only the 'id' field
        normalized.pop('id', None)
        
        # Ensure required fields exist
        normalized.setdefault('name', '')
        normalized.setdefault('folder', '')
        
        # Add metadata for tracking
        if 'metadata' not in normalized:
            normalized['metadata'] = self._extract_metadata(group_data)
        
        return normalized

    def _normalize_application(self, app_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve full application object data for push."""
        # Make a deep copy to preserve all fields
        normalized = app_data.copy()
        
        # Remove only the 'id' field
        normalized.pop('id', None)
        
        # Ensure required fields exist
        normalized.setdefault('name', '')
        normalized.setdefault('folder', '')
        
        # Add metadata for tracking
        if 'metadata' not in normalized:
            normalized['metadata'] = self._extract_metadata(app_data)
        
        return normalized

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


def capture_objects_from_folder(
    api_client: PrismaAccessAPIClient, folder: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Convenience function to capture all objects from a folder.

    Args:
        api_client: PrismaAccessAPIClient instance
        folder: Folder name (None = all folders)

    Returns:
        Dictionary mapping object types to lists of objects
    """
    capture = ObjectCapture(api_client)
    return capture.capture_all_objects(folder=folder)
