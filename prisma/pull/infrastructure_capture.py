"""
Infrastructure capture module for Prisma Access configuration.

This module provides comprehensive capture functionality for Prisma Access
infrastructure components including:
- Remote Networks
- Service Connections
- IPsec Tunnels and IKE Gateways
- Crypto Profiles (IKE and IPsec)
- Mobile User Infrastructure (GlobalProtect)
- HIP Objects and Profiles
- Bandwidth Allocations and Regions
"""

from typing import Dict, Any, List, Optional, Callable
import logging

from ..api_client import PrismaAccessAPIClient


class InfrastructureCapture:
    """Capture Prisma Access infrastructure components."""

    def __init__(self, api_client: PrismaAccessAPIClient, suppress_output: bool = False):
        """
        Initialize infrastructure capture.

        Args:
            api_client: PrismaAccessAPIClient instance
            suppress_output: Suppress logging output (for GUI usage)
        """
        self.api_client = api_client
        self.suppress_output = suppress_output
        self.logger = logging.getLogger(__name__)
    
    def _log(self, level: str, message: str):
        """Thread-safe logging wrapper that respects suppress_output flag."""
        if not self.suppress_output:
            getattr(self.logger, level)(message)

    def _validate_endpoint_availability(self, endpoint_name: str, func) -> bool:
        """
        Validate if an endpoint is available before using it.

        Args:
            endpoint_name: Name of endpoint for logging
            func: Function that makes the API call

        Returns:
            True if endpoint is available, False otherwise
        """
        try:
            # Try to call with limit=1 to test availability
            func(limit=1)
            return True
        except Exception as e:
            # Check if it's a 404 (endpoint not found)
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                if e.response.status_code == 404:
                    self._log("warning", 
                        f"Endpoint '{endpoint_name}' not available (404), skipping..."
                    )
                    return False
            # Re-raise other errors
            raise

    def capture_remote_networks(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Capture remote network configurations.

        Remote networks represent branch offices and data centers connected
        to Prisma Access via IPsec tunnels.

        Args:
            folder: Optional folder to filter results

        Returns:
            List of remote network configuration dictionaries
        """
        try:
            self._log("info", "Capturing remote networks...")
            remote_networks = self.api_client.get_all_remote_networks(folder=folder)
            self._log("info", f"Captured {len(remote_networks)} remote network(s)")
            return remote_networks
        except Exception as e:
            # Check if endpoint not available (404)
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                if e.response.status_code == 404:
                    self._log("warning", 
                        "Remote Networks endpoint not available, skipping..."
                    )
                    return []
            # Re-raise other errors
            self._log("error", f"Error capturing remote networks: {e}")
            raise

    def capture_service_connections(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Capture service connection configurations.

        Service connections provide connectivity between Prisma Access and
        on-premises data centers or cloud environments.

        Args:
            folder: Optional folder to filter results

        Returns:
            List of service connection configuration dictionaries
        """
        try:
            self._log("info", "Capturing service connections...")
            service_connections = self.api_client.get_all_service_connections(
                folder=folder
            )
            self._log("info", 
                f"Captured {len(service_connections)} service connection(s)"
            )
            return service_connections
        except Exception as e:
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                if e.response.status_code == 404:
                    self._log("warning", 
                        "Service Connections endpoint not available, skipping..."
                    )
                    return []
            self._log("error", f"Error capturing service connections: {e}")
            raise

    def capture_ipsec_tunnels(
        self, folders: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Capture IPsec tunnel configurations and related components.

        This captures:
        - IPsec tunnels
        - IKE gateways
        - IKE crypto profiles
        - IPsec crypto profiles

        Note: IPsec tunnels REQUIRE a folder parameter. They are typically found in:
        - "Service Connections" folder
        - "Remote Networks" folder

        Args:
            folders: List of folders to check (defaults to ["Service Connections", "Remote Networks"])

        Returns:
            Dictionary containing all tunnel-related configurations:
            {
                "ipsec_tunnels": [...],
                "ike_gateways": [...],
                "ike_crypto_profiles": [...],
                "ipsec_crypto_profiles": [...]
            }
        """
        # Default to checking both Service Connections and Remote Networks folders
        if folders is None:
            folders = ["Service Connections", "Remote Networks"]
        
        result = {
            "ipsec_tunnels": [],
            "ike_gateways": [],
            "ike_crypto_profiles": [],
            "ipsec_crypto_profiles": [],
        }

        # Capture from each folder
        for folder in folders:
            try:
                # Capture IPsec tunnels
                self._log("info", f"Capturing IPsec tunnels from folder: {folder}...")
                tunnels = self.api_client.get_all_ipsec_tunnels(folder=folder)
                result["ipsec_tunnels"].extend(tunnels)
                self._log("info", f"  Found {len(tunnels)} IPsec tunnel(s)")

                # Capture IKE gateways
                self._log("info", f"Capturing IKE gateways from folder: {folder}...")
                gateways = self.api_client.get_all_ike_gateways(folder=folder)
                result["ike_gateways"].extend(gateways)
                self._log("info", f"  Found {len(gateways)} IKE gateway(s)")

                # Capture IKE crypto profiles
                self._log("info", f"Capturing IKE crypto profiles from folder: {folder}...")
                ike_profiles = self.api_client.get_all_ike_crypto_profiles(folder=folder)
                result["ike_crypto_profiles"].extend(ike_profiles)
                self._log("info", f"  Found {len(ike_profiles)} IKE crypto profile(s)")

                # Capture IPsec crypto profiles
                self._log("info", f"Capturing IPsec crypto profiles from folder: {folder}...")
                ipsec_profiles = self.api_client.get_all_ipsec_crypto_profiles(folder=folder)
                result["ipsec_crypto_profiles"].extend(ipsec_profiles)
                self._log("info", f"  Found {len(ipsec_profiles)} IPsec crypto profile(s)")

            except Exception as e:
                error_str = str(e).lower()
                # Check for common errors that should be skipped
                if "doesn't exist" in error_str or "404" in error_str:
                    self._log("info", f"  Folder '{folder}' not available for tunnels - skipping")
                    continue
                elif "400" in error_str and "pattern" in error_str:
                    self._log("info", f"  Folder '{folder}' cannot have tunnels - skipping")
                    continue
                else:
                    self._log("error", f"Error capturing tunnels from folder '{folder}': {e}")
                    # Continue to next folder instead of raising

        # Log totals
        self._log("info", f"Total IPsec tunnels captured: {len(result['ipsec_tunnels'])}")
        self._log("info", f"Total IKE gateways captured: {len(result['ike_gateways'])}")
        self._log("info", f"Total IKE crypto profiles captured: {len(result['ike_crypto_profiles'])}")
        self._log("info", f"Total IPsec crypto profiles captured: {len(result['ipsec_crypto_profiles'])}")

        return result

    def capture_mobile_user_infrastructure(self, folder: str = "Mobile Users") -> Dict[str, Any]:
        """
        Capture mobile user infrastructure configurations.

        This captures all mobile agent settings including profiles, versions,
        authentication, global settings, infrastructure settings, locations, and tunnel profiles.

        Args:
            folder: Folder to query (defaults to "Mobile Users")

        Returns:
            Dictionary containing mobile user infrastructure:
            {
                "agent_profiles": {...},
                "agent_versions": {...},
                "authentication_settings": {...},
                "enable": {...},
                "global_settings": {...},
                "infrastructure_settings": {...},
                "locations": {...},
                "tunnel_profiles": {...}
            }
        """
        result = {
            "agent_profiles": {},
            "agent_versions": {},
            "authentication_settings": {},
            "enable": {},
            "global_settings": {},
            "infrastructure_settings": {},
            "locations": {},
            "tunnel_profiles": {},
        }

        try:
            # Skip the enable check entirely - it causes hangs and segfaults in GUI mode
            # Just try to capture each component and let individual calls fail gracefully
            # Each call already has try-except handling
            
            # Capture mobile agent profiles
            self._log("info", f"Capturing mobile agent profiles from {folder}...")
            try:
                response = self.api_client.get_mobile_agent_profiles(folder=folder)
                # Extract 'data' if paginated response, otherwise use as-is
                result["agent_profiles"] = response.get("data", response) if isinstance(response, dict) else response
                self._log("info", "  ✓ Captured agent profiles")
            except Exception as e:
                self._log("warning", f"  ⚠ Error capturing agent profiles: {e}")

            # Capture mobile agent versions
            self._log("info", f"Capturing mobile agent versions from {folder}...")
            try:
                response = self.api_client.get_mobile_agent_versions(folder=folder)
                # Extract 'data' if paginated response, otherwise use as-is
                result["agent_versions"] = response.get("data", response) if isinstance(response, dict) else response
                self._log("info", "  ✓ Captured agent versions")
            except Exception as e:
                self._log("warning", f"  ⚠ Error capturing agent versions: {e}")

            # Capture authentication settings
            self._log("info", f"Capturing mobile agent auth settings from {folder}...")
            try:
                response = self.api_client.get_mobile_agent_auth_settings(folder=folder)
                # Extract 'data' if paginated response, otherwise use as-is
                result["authentication_settings"] = response.get("data", response) if isinstance(response, dict) else response
                self._log("info", "  ✓ Captured authentication settings")
            except Exception as e:
                self._log("warning", f"  ⚠ Error capturing auth settings: {e}")

            # Capture global settings
            self._log("info", f"Capturing mobile agent global settings from {folder}...")
            try:
                response = self.api_client.get_mobile_agent_global_settings(folder=folder)
                # Extract 'data' if paginated response, otherwise use as-is
                result["global_settings"] = response.get("data", response) if isinstance(response, dict) else response
                self._log("info", "  ✓ Captured global settings")
            except Exception as e:
                self._log("warning", f"  ⚠ Error capturing global settings: {e}")

            # Capture infrastructure settings
            self._log("info", f"Capturing mobile agent infrastructure settings from {folder}...")
            try:
                response = self.api_client.get_mobile_agent_infra_settings(folder=folder)
                # Extract 'data' if paginated response, otherwise use as-is
                result["infrastructure_settings"] = response.get("data", response) if isinstance(response, dict) else response
                self._log("info", "  ✓ Captured infrastructure settings")
            except Exception as e:
                self._log("warning", f"  ⚠ Error capturing infrastructure settings: {e}")

            # Capture locations
            self._log("info", f"Capturing mobile agent locations from {folder}...")
            try:
                response = self.api_client.get_mobile_agent_locations(folder=folder)
                # Extract 'data' if paginated response, otherwise use as-is
                result["locations"] = response.get("data", response) if isinstance(response, dict) else response
                self._log("info", "  ✓ Captured locations")
            except Exception as e:
                self._log("warning", f"  ⚠ Error capturing locations: {e}")

            # Capture tunnel profiles
            self._log("info", f"Capturing mobile agent tunnel profiles from {folder}...")
            try:
                response = self.api_client.get_mobile_agent_tunnel_profiles(folder=folder)
                # Extract 'data' if paginated response, otherwise use as-is
                result["tunnel_profiles"] = response.get("data", response) if isinstance(response, dict) else response
                self._log("info", "  ✓ Captured tunnel profiles")
            except Exception as e:
                self._log("warning", f"  ⚠ Error capturing tunnel profiles: {e}")

        except Exception as e:
            self._log("error", f"Error capturing mobile user infrastructure: {e}")
            # Don't raise - return partial results

        return result

    def capture_hip_objects_and_profiles(
        self, folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture HIP (Host Information Profile) objects and profiles.

        Note: HIP endpoints may not be available in all environments.
        This method uses graceful error handling.

        Args:
            folder: Optional folder to filter results

        Returns:
            Dictionary containing HIP configurations:
            {
                "hip_objects": [...],
                "hip_profiles": [...]
            }
        """
        result = {
            "hip_objects": [],
            "hip_profiles": [],
        }

        try:
            # Capture HIP objects
            self._log("info", "Capturing HIP objects...")
            try:
                hip_objects = self.api_client.get_all_hip_objects(folder=folder)
                
                # Filter by folder if specified (API may return all folders)
                if folder:
                    hip_objects = [obj for obj in hip_objects if obj.get("folder") == folder]
                
                result["hip_objects"] = hip_objects
                self._log("info", f"Captured {len(result['hip_objects'])} HIP object(s)")
            except Exception as e:
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    if e.response.status_code == 404:
                        self._log("warning", "HIP objects endpoint not available")
                else:
                    self._log("warning", f"Error capturing HIP objects: {e}")

            # Capture HIP profiles
            self._log("info", "Capturing HIP profiles...")
            try:
                hip_profiles = self.api_client.get_all_hip_profiles(folder=folder)
                
                # Filter by folder if specified (API may return all folders)
                if folder:
                    hip_profiles = [prof for prof in hip_profiles if prof.get("folder") == folder]
                
                result["hip_profiles"] = hip_profiles
                self._log("info", 
                    f"Captured {len(result['hip_profiles'])} HIP profile(s)"
                )
            except Exception as e:
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    if e.response.status_code == 404:
                        self._log("warning", "HIP profiles endpoint not available")
                else:
                    self._log("warning", f"Error capturing HIP profiles: {e}")

        except Exception as e:
            self._log("error", f"Error capturing HIP objects and profiles: {e}")
            # Don't raise - return partial results

        return result

    def capture_regions_and_bandwidth(self) -> Dict[str, Any]:
        """
        Capture region and bandwidth allocation configurations.

        This captures bandwidth allocations which provide information about 
        Prisma Access regional deployments. Locations (regions) are static
        and not included as they don't change per-tenant.

        Returns:
            Dictionary containing bandwidth allocations:
            {
                "bandwidth_allocations": [...]
            }
        """
        result = {
            "bandwidth_allocations": [],
        }

        try:
            # Note: Locations (regions) are static and not captured
            # They are the same across all tenants and don't need to be in configs
            
            # Capture bandwidth allocations
            self._log("info", "Capturing bandwidth allocations...")
            try:
                result[
                    "bandwidth_allocations"
                ] = self.api_client.get_all_bandwidth_allocations()
                self._log("info", 
                    f"Captured {len(result['bandwidth_allocations'])} bandwidth allocation(s)"
                )
            except Exception as e:
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    if e.response.status_code == 404:
                        self._log("warning", 
                            "Bandwidth allocations endpoint not available"
                        )
                else:
                    self._log("warning", f"Error capturing bandwidth allocations: {e}")

        except Exception as e:
            self._log("error", f"Error capturing regions and bandwidth: {e}")
            # Don't raise - return partial results

        return result

    def capture_all_infrastructure(
        self,
        folder: Optional[str] = None,
        include_remote_networks: bool = True,
        include_service_connections: bool = True,
        include_ipsec_tunnels: bool = True,
        include_mobile_users: bool = True,
        include_hip: bool = True,
        include_regions: bool = True,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Capture all infrastructure components with selective inclusion.

        Args:
            folder: Optional folder to filter results (where applicable)
            include_remote_networks: Whether to capture remote networks
            include_service_connections: Whether to capture service connections
            include_ipsec_tunnels: Whether to capture IPsec tunnels and crypto
            include_mobile_users: Whether to capture mobile user infrastructure
            include_hip: Whether to capture HIP objects and profiles
            include_regions: Whether to capture regions and bandwidth
            progress_callback: Optional callback function(message, current, total)

        Returns:
            Complete infrastructure configuration dictionary
        """
        infrastructure = {}
        
        # Count enabled components for progress tracking
        enabled_components = []
        if include_remote_networks:
            enabled_components.append(("Remote Networks", lambda: self.capture_remote_networks(folder=folder)))
        if include_service_connections:
            enabled_components.append(("Service Connections", lambda: self.capture_service_connections(folder=folder)))
        if include_ipsec_tunnels:
            enabled_components.append(("IPsec Tunnels & Crypto", lambda: self.capture_ipsec_tunnels(folders=["Service Connections", "Remote Networks"])))
        if include_mobile_users:
            enabled_components.append(("Mobile User Settings", lambda: self.capture_mobile_user_infrastructure()))
        if include_hip:
            enabled_components.append(("HIP Objects & Profiles", lambda: self.capture_hip_objects_and_profiles(folder="Mobile Users")))
        if include_regions:
            enabled_components.append(("Bandwidth Allocations", lambda: self.capture_regions_and_bandwidth()))
        
        total_components = len(enabled_components)
        
        for idx, (component_name, capture_func) in enumerate(enabled_components, 1):
            if progress_callback:
                progress_callback(
                    f"Infrastructure: {component_name} ({idx}/{total_components})",
                    idx,
                    total_components
                )
            
            # Execute the capture function
            result = capture_func()
            
            # Handle different result types
            if component_name == "IPsec Tunnels & Crypto":
                # This returns a dict with multiple keys to merge
                infrastructure.update(result)
            elif component_name == "Mobile User Settings":
                infrastructure["mobile_users"] = result
            elif component_name == "HIP Objects & Profiles":
                infrastructure["hip"] = result
            elif component_name == "Bandwidth Allocations":
                infrastructure["regions"] = result
            elif component_name == "Remote Networks":
                infrastructure["remote_networks"] = result
            elif component_name == "Service Connections":
                infrastructure["service_connections"] = result

        return infrastructure
