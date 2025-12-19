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
    
    def __init__(self, api_client: PrismaAccessAPIClient):
        """
        Initialize object capture.
        
        Args:
            api_client: PrismaAccessAPIClient instance
        """
        self.api_client = api_client
    
    def capture_addresses(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Capture address objects.
        
        Args:
            folder: Folder name (None = all folders)
            
        Returns:
            List of normalized address objects
        """
        try:
            addresses = self.api_client.get_all_addresses(folder=folder)
            return [self._normalize_address(addr) for addr in addresses]
        except Exception as e:
            print(f"Error capturing addresses: {e}")
            # Log to centralized error logger
            try:
                from ...error_logger import error_logger
                error_logger.log_capture_error(
                    "capture_addresses",
                    folder if folder else "default",
                    e,
                    {"folder": folder}
                )
            except Exception:
                pass  # Don't fail if logging fails
            return []
    
    def capture_address_groups(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Capture address groups.
        
        Args:
            folder: Folder name (None = all folders)
            
        Returns:
            List of normalized address groups
        """
        try:
            groups = self.api_client.get_all_address_groups(folder=folder)
            return [self._normalize_address_group(grp) for grp in groups]
        except Exception as e:
            print(f"Error capturing address groups: {e}")
            try:
                from ...error_logger import error_logger
                error_logger.log_capture_error(
                    "capture_address_groups",
                    folder if folder else "default",
                    e,
                    {"folder": folder}
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
        try:
            services = self.api_client.get_services(folder=folder)
            return [self._normalize_service(svc) for svc in services]
        except Exception as e:
            print(f"Error capturing services: {e}")
            try:
                from ...error_logger import error_logger
                error_logger.log_capture_error(
                    "capture_services",
                    folder if folder else "default",
                    e,
                    {"folder": folder}
                )
            except Exception:
                pass
            return []
    
    def capture_service_groups(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Capture service groups.
        
        Args:
            folder: Folder name (None = all folders)
            
        Returns:
            List of normalized service groups
        """
        try:
            # Note: Service groups endpoint may need to be added to API client
            # For now, using a placeholder
            groups = []  # self.api_client.get_service_groups(folder=folder)
            return [self._normalize_service_group(grp) for grp in groups]
        except Exception as e:
            print(f"Error capturing service groups: {e}")
            try:
                from ...error_logger import error_logger
                error_logger.log_capture_error(
                    "capture_service_groups",
                    folder if folder else "default",
                    e,
                    {"folder": folder}
                )
            except Exception:
                pass
            return []
    
    def capture_applications(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Capture application objects.
        
        Args:
            folder: Folder name (None = all folders)
            
        Returns:
            List of normalized application objects
        """
        try:
            applications = self.api_client.get_applications(folder=folder)
            return [self._normalize_application(app) for app in applications]
        except Exception as e:
            print(f"Error capturing applications: {e}")
            try:
                from ...error_logger import error_logger
                error_logger.log_capture_error(
                    "capture_applications",
                    folder if folder else "default",
                    e,
                    {"folder": folder}
                )
            except Exception:
                pass
            return []
    
    def capture_all_objects(self, folder: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Capture all object types from a folder.
        
        Args:
            folder: Folder name (None = all folders)
            
        Returns:
            Dictionary mapping object types to lists of objects
        """
        # Reduced verbosity - only print summary, not individual captures
        all_objects = {
            'address_objects': self.capture_addresses(folder),
            'address_groups': self.capture_address_groups(folder),
            'service_objects': self.capture_services(folder),
            'service_groups': self.capture_service_groups(folder),
            'applications': self.capture_applications(folder),
            'application_groups': [],  # To be implemented
            'application_filters': [],  # To be implemented
            'url_filtering_categories': [],  # To be implemented
            'external_dynamic_lists': [],  # To be implemented
            'fqdn_objects': []  # To be implemented
        }
        
        # Print brief summary only
        total = sum(len(objs) for objs in all_objects.values())
        if total > 0:
            print(f"  ✓ Captured {total} objects")
        
        return all_objects
    
    def _normalize_address(self, addr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize address object."""
        return {
            'id': addr_data.get('id', addr_data.get('name', '')),
            'name': addr_data.get('name', ''),
            'description': addr_data.get('description', ''),
            'type': addr_data.get('type', 'ip_netmask'),
            'value': addr_data.get('value', addr_data.get('ip_netmask', '')),
            'folder': addr_data.get('folder', ''),
            'tags': self._extract_list_field(addr_data, 'tags'),
            'metadata': self._extract_metadata(addr_data)
        }
    
    def _normalize_address_group(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize address group."""
        return {
            'id': group_data.get('id', group_data.get('name', '')),
            'name': group_data.get('name', ''),
            'description': group_data.get('description', ''),
            'addresses': self._extract_list_field(group_data, 'addresses'),
            'address_groups': self._extract_list_field(group_data, 'address_groups'),
            'dynamic_match': group_data.get('dynamic_match', ''),
            'folder': group_data.get('folder', ''),
            'tags': self._extract_list_field(group_data, 'tags'),
            'metadata': self._extract_metadata(group_data)
        }
    
    def _normalize_service(self, svc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize service object."""
        return {
            'id': svc_data.get('id', svc_data.get('name', '')),
            'name': svc_data.get('name', ''),
            'description': svc_data.get('description', ''),
            'protocol': svc_data.get('protocol', ''),
            'port': svc_data.get('port', ''),
            'source_port': svc_data.get('source_port', ''),
            'folder': svc_data.get('folder', ''),
            'tags': self._extract_list_field(svc_data, 'tags'),
            'metadata': self._extract_metadata(svc_data)
        }
    
    def _normalize_service_group(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize service group."""
        return {
            'id': group_data.get('id', group_data.get('name', '')),
            'name': group_data.get('name', ''),
            'description': group_data.get('description', ''),
            'services': self._extract_list_field(group_data, 'services'),
            'service_groups': self._extract_list_field(group_data, 'service_groups'),
            'folder': group_data.get('folder', ''),
            'tags': self._extract_list_field(group_data, 'tags'),
            'metadata': self._extract_metadata(group_data)
        }
    
    def _normalize_application(self, app_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize application object."""
        return {
            'id': app_data.get('id', app_data.get('name', '')),
            'name': app_data.get('name', ''),
            'description': app_data.get('description', ''),
            'category': app_data.get('category', ''),
            'subcategory': app_data.get('subcategory', ''),
            'technology': app_data.get('technology', ''),
            'risk': app_data.get('risk', ''),
            'folder': app_data.get('folder', ''),
            'tags': self._extract_list_field(app_data, 'tags'),
            'metadata': self._extract_metadata(app_data)
        }
    
    def _extract_list_field(self, data: Dict[str, Any], field_name: str) -> List[str]:
        """Extract a list field, handling various formats."""
        value = data.get(field_name, [])
        
        if isinstance(value, list):
            result = []
            for item in value:
                if isinstance(item, dict):
                    result.append(item.get('name', item.get('value', str(item))))
                else:
                    result.append(str(item))
            return result
        elif isinstance(value, dict):
            return [value.get('name', value.get('value', str(value)))]
        elif value:
            return [str(value)]
        else:
            return []
    
    def _extract_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata fields."""
        return {
            'created': data.get('created', ''),
            'updated': data.get('updated', ''),
            'created_by': data.get('created_by', ''),
            'updated_by': data.get('updated_by', '')
        }


def capture_objects_from_folder(
    api_client: PrismaAccessAPIClient,
    folder: Optional[str] = None
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
