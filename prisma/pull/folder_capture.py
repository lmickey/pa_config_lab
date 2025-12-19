"""
Folder discovery and enumeration for Prisma Access security policies.

This module provides functions to discover, list, and retrieve metadata
for security policy folders in Prisma Access SCM.
"""

from typing import Dict, Any, List, Optional
from ..api_client import PrismaAccessAPIClient
from ..api_endpoints import APIEndpoints


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
        Discover all security policy folders.
        
        In Prisma Access, folders can be accessed via:
        1. Security policy folders endpoint
        2. Direct object endpoints (service-connections, remote-networks)
        3. Mobile user container folders
        
        Returns:
            List of folder dictionaries with metadata
        """
        all_folders = []
        
        # Try security policy folders endpoint
        try:
            folders = self.api_client.get_security_policy_folders()
            if folders:
                for folder in folders:
                    normalized = self._normalize_folder(folder)
                    all_folders.append(normalized)
        except Exception as e:
            # If 403 or endpoint doesn't exist, try alternative methods
            if '403' in str(e) or 'Forbidden' in str(e):
                print(f"  Note: Security policy folders endpoint returned 403, trying alternative discovery...")
            else:
                print(f"  Warning: Error accessing security policy folders: {e}")
        
        # Discover folders from object endpoints
        # Service Connections folder
        try:
            sc_folders = self.api_client.get_service_connections(folder="Service Connections")
            if sc_folders is not None:
                # Check if Service Connections folder exists
                sc_folder = {
                    'name': 'Service Connections',
                    'id': 'Service Connections',
                    'path': '/config/service-connections',
                    'is_default': True,
                    'type': 'service_connections'
                }
                if not any(f.get('name') == 'Service Connections' for f in all_folders):
                    all_folders.append(self._normalize_folder(sc_folder))
        except Exception:
            pass
        
        # Remote Networks folder
        try:
            rn_folders = self.api_client.get_remote_networks(folder="Remote Networks")
            if rn_folders is not None:
                rn_folder = {
                    'name': 'Remote Networks',
                    'id': 'Remote Networks',
                    'path': '/config/remote-networks',
                    'is_default': True,
                    'type': 'remote_networks'
                }
                if not any(f.get('name') == 'Remote Networks' for f in all_folders):
                    all_folders.append(self._normalize_folder(rn_folder))
        except Exception:
            pass
        
        # Try to discover Mobile User Container and sub-folders
        # These might be accessed via mobile-agent endpoints
        try:
            mobile_folders = [
                {
                    'name': 'Mobile User Container',
                    'id': 'Mobile User Container',
                    'path': '/config/mobile-user-container',
                    'is_default': True,
                    'type': 'mobile_user_container'
                },
                {
                    'name': 'Access Agent',
                    'id': 'Access Agent',
                    'path': '/config/mobile-user-container/access-agent',
                    'is_default': True,
                    'type': 'access_agent',
                    'parent': 'Mobile User Container'
                },
                {
                    'name': 'GlobalProtect',
                    'id': 'GlobalProtect',
                    'path': '/config/mobile-user-container/globalprotect',
                    'is_default': True,
                    'type': 'globalprotect',
                    'parent': 'Mobile User Container'
                },
                {
                    'name': 'Explicit Proxy',
                    'id': 'Explicit Proxy',
                    'path': '/config/mobile-user-container/explicit-proxy',
                    'is_default': True,
                    'type': 'explicit_proxy',
                    'parent': 'Mobile User Container'
                }
            ]
            
            for folder in mobile_folders:
                if not any(f.get('name') == folder['name'] for f in all_folders):
                    all_folders.append(self._normalize_folder(folder))
        except Exception:
            pass
        
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
            folder_name = folder.get('name', '')
            hierarchy[folder_name] = {
                'name': folder_name,
                'path': folder.get('path', ''),
                'parent': folder.get('parent', None),
                'children': [],
                'level': self._calculate_folder_level(folder.get('path', ''))
            }
        
        # Build parent-child relationships
        for folder_name, folder_info in hierarchy.items():
            parent = folder_info.get('parent')
            if parent and parent in hierarchy:
                hierarchy[parent]['children'].append(folder_name)
        
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
        normalized = {
            'name': folder_data.get('name', ''),
            'id': folder_data.get('id', folder_data.get('name', '')),
            'path': folder_data.get('path', ''),
            'description': folder_data.get('description', ''),
            'parent': folder_data.get('parent', None),
            'is_default': self._is_default_folder(folder_data.get('name', '')),
            'metadata': {
                'created': folder_data.get('created', ''),
                'updated': folder_data.get('updated', ''),
                'created_by': folder_data.get('created_by', ''),
                'updated_by': folder_data.get('updated_by', '')
            }
        }
        
        # Preserve any additional fields
        for key, value in folder_data.items():
            if key not in normalized and key not in ['metadata']:
                normalized[key] = value
        
        return normalized
    
    def _is_default_folder(self, folder_name: str) -> bool:
        """
        Check if folder is a default folder.
        
        Args:
            folder_name: Folder name
            
        Returns:
            True if default folder, False otherwise
        """
        default_names = ['shared', 'Shared', 'default', 'Default']
        return folder_name in default_names or 'default' in folder_name.lower()
    
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
        parts = [p for p in path.split('/') if p and p != 'config' and p != 'security-policy' and p != 'folders']
        return len(parts)
    
    def list_folders_for_capture(self, include_defaults: bool = False) -> List[str]:
        """
        Get list of folder names to capture.
        
        Args:
            include_defaults: Whether to include default folders
            
        Returns:
            List of folder names
        """
        folders = self.discover_folders()
        
        folder_names = []
        for folder in folders:
            folder_name = folder.get('name', '')
            is_default = folder.get('is_default', False)
            
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
