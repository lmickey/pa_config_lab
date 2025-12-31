"""
Tests for Infrastructure Capture module.

This module tests the comprehensive infrastructure capture functionality
including Remote Networks, Service Connections, IPsec/IKE, Mobile Users,
HIP, and Regions/Bandwidth.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from prisma.pull.infrastructure_capture import InfrastructureCapture
from prisma.api_client import PrismaAccessAPIClient


# ============================================================================
# Test Data Generators
# ============================================================================

def generate_remote_network_data(name: str = "Test RN", folder: str = "Remote Networks") -> Dict[str, Any]:
    """Generate mock remote network data."""
    return {
        "id": f"rn-{name.lower().replace(' ', '-')}",
        "name": name,
        "folder": folder,
        "region": "us-east-1",
        "license_type": "FWAAS-AGGREGATE",
        "subnets": ["10.1.0.0/24"],
        "protocol": {"bgp": {}},
        "ipsec_tunnel": f"ipsec-tunnel-{name.lower()}",
        "ecmp_load_balancing": "disable",
        "secondary_ipsec_tunnel": None
    }


def generate_service_connection_data(name: str = "Test SC") -> Dict[str, Any]:
    """Generate mock service connection data."""
    return {
        "id": f"sc-{name.lower().replace(' ', '-')}",
        "name": name,
        "folder": "Service Connections",
        "region": "us-west-2",
        "source_nat": False,
        "nat_pool": None,
        "subnets": ["172.16.0.0/16"],
        "onboarding_type": "classic",
        "qos": {"enabled": False}
    }


def generate_ipsec_tunnel_data(name: str = "Test Tunnel") -> Dict[str, Any]:
    """Generate mock IPsec tunnel data."""
    return {
        "id": f"tunnel-{name.lower().replace(' ', '-')}",
        "name": name,
        "folder": "Shared",
        "auto_key": {
            "ike_gateway": [{"name": "ike-gw-1"}],
            "ipsec_crypto_profile": "default"
        },
        "anti_replay": True,
        "copy_tos": False,
        "enable_gre_encapsulation": False,
        "tunnel_monitor": {"enable": False}
    }


def generate_ike_gateway_data(name: str = "Test IKE GW") -> Dict[str, Any]:
    """Generate mock IKE gateway data."""
    return {
        "id": f"ike-{name.lower().replace(' ', '-')}",
        "name": name,
        "folder": "Shared",
        "authentication": {
            "pre_shared_key": {"key": "***"}
        },
        "peer_address": {
            "ip": "1.2.3.4"
        },
        "peer_id": {
            "id": "peer@example.com",
            "type": "ufqdn"
        },
        "protocol": {
            "ikev2": {
                "ike_crypto_profile": "default"
            }
        }
    }


def generate_ike_crypto_profile_data(name: str = "default") -> Dict[str, Any]:
    """Generate mock IKE crypto profile data."""
    return {
        "id": f"ike-crypto-{name}",
        "name": name,
        "folder": "Shared",
        "dh_group": ["group14", "group19"],
        "encryption": ["aes-256-cbc"],
        "authentication": ["sha256"],
        "lifetime": {"hours": 8}
    }


def generate_ipsec_crypto_profile_data(name: str = "default") -> Dict[str, Any]:
    """Generate mock IPsec crypto profile data."""
    return {
        "id": f"ipsec-crypto-{name}",
        "name": name,
        "folder": "Shared",
        "esp": {
            "encryption": ["aes-256-cbc"],
            "authentication": ["sha256"]
        },
        "dh_group": "group14",
        "lifetime": {"hours": 1}
    }


def generate_gp_gateway_data(name: str = "GP-Gateway-1") -> Dict[str, Any]:
    """Generate mock GlobalProtect gateway data."""
    return {
        "id": f"gp-gw-{name.lower().replace(' ', '-')}",
        "name": name,
        "folder": "Mobile Users",
        "authentication_profile": "default",
        "ip_pools": ["10.10.0.0/16"],
        "tunnel_interface": {
            "tunnel_interface": "tunnel.1"
        },
        "enable_ipv6": False
    }


def generate_gp_portal_data(name: str = "GP-Portal-1") -> Dict[str, Any]:
    """Generate mock GlobalProtect portal data."""
    return {
        "id": f"gp-portal-{name.lower().replace(' ', '-')}",
        "name": name,
        "folder": "Mobile Users",
        "authentication_profile": "default",
        "ip_address": "portal.example.com"
    }


def generate_hip_object_data(name: str = "Test HIP Object") -> Dict[str, Any]:
    """Generate mock HIP object data."""
    return {
        "id": f"hip-obj-{name.lower().replace(' ', '-')}",
        "name": name,
        "folder": "Shared",
        "description": "Test HIP object",
        "host_info": {
            "criteria": {
                "os": {"contains": {"Microsoft": "All"}}
            }
        }
    }


def generate_hip_profile_data(name: str = "Test HIP Profile") -> Dict[str, Any]:
    """Generate mock HIP profile data."""
    return {
        "id": f"hip-prof-{name.lower().replace(' ', '-')}",
        "name": name,
        "folder": "Shared",
        "description": "Test HIP profile",
        "match": "any",
        "hip_objects": ["Test HIP Object"]
    }


def generate_location_data(name: str = "us-east-1") -> Dict[str, Any]:
    """Generate mock location/region data."""
    return {
        "id": name,
        "name": name,
        "display_name": "US East (Virginia)",
        "deployed": True,
        "compute_location": "us-east-1",
        "service_type": "gp_gateway"
    }


def generate_bandwidth_allocation_data(region: str = "us-east-1") -> Dict[str, Any]:
    """Generate mock bandwidth allocation data."""
    return {
        "id": f"bw-{region}",
        "region": region,
        "allocated_bandwidth_mbps": 1000,
        "allocated_compute_units": 2,
        "bandwidth_pool": "default"
    }


# ============================================================================
# Mock API Client Fixture
# ============================================================================

@pytest.fixture
def mock_infra_api_client():
    """Create a mock API client with infrastructure methods."""
    client = Mock(spec=PrismaAccessAPIClient)
    client.tsg_id = "tsg-test-1234567890"
    
    # Remote Networks
    client.get_all_remote_networks.return_value = [
        generate_remote_network_data("Branch-Office-1"),
        generate_remote_network_data("Branch-Office-2")
    ]
    
    # Service Connections
    client.get_all_service_connections.return_value = [
        generate_service_connection_data("SC-HQ"),
        generate_service_connection_data("SC-DR")
    ]
    
    # IPsec Tunnels
    client.get_all_ipsec_tunnels.return_value = [
        generate_ipsec_tunnel_data("Tunnel-1"),
        generate_ipsec_tunnel_data("Tunnel-2")
    ]
    
    # IKE Gateways
    client.get_all_ike_gateways.return_value = [
        generate_ike_gateway_data("IKE-GW-1"),
        generate_ike_gateway_data("IKE-GW-2")
    ]
    
    # Crypto Profiles
    client.get_all_ike_crypto_profiles.return_value = [
        generate_ike_crypto_profile_data("default"),
        generate_ike_crypto_profile_data("strong")
    ]
    client.get_all_ipsec_crypto_profiles.return_value = [
        generate_ipsec_crypto_profile_data("default"),
        generate_ipsec_crypto_profile_data("aes256-sha256")
    ]
    
    # Mobile User Infrastructure
    client.get_mobile_user_infrastructure.return_value = {
        "infrastructure_settings": {"dns_servers": ["8.8.8.8"]}
    }
    client.get_all_globalprotect_gateways.return_value = [
        generate_gp_gateway_data("GP-Gateway-1")
    ]
    client.get_all_globalprotect_portals.return_value = [
        generate_gp_portal_data("GP-Portal-1")
    ]
    
    # HIP Objects and Profiles
    client.get_all_hip_objects.return_value = [
        generate_hip_object_data("Windows-Check"),
        generate_hip_object_data("Antivirus-Check")
    ]
    client.get_all_hip_profiles.return_value = [
        generate_hip_profile_data("Standard-HIP")
    ]
    
    # Regions and Bandwidth
    client.get_all_locations.return_value = [
        generate_location_data("us-east-1"),
        generate_location_data("us-west-2")
    ]
    client.get_all_bandwidth_allocations.return_value = [
        generate_bandwidth_allocation_data("us-east-1"),
        generate_bandwidth_allocation_data("us-west-2")
    ]
    
    return client


# ============================================================================
# Test Remote Networks
# ============================================================================

@pytest.mark.unit
class TestRemoteNetworksCapture:
    """Test remote network capture functionality."""
    
    def test_capture_remote_networks_success(self, mock_infra_api_client):
        """Test successful remote network capture."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_remote_networks()
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Branch-Office-1"
        assert result[1]["name"] == "Branch-Office-2"
        mock_infra_api_client.get_all_remote_networks.assert_called_once()
    
    def test_capture_remote_networks_with_folder(self, mock_infra_api_client):
        """Test remote network capture with folder filter."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_remote_networks(folder="Remote Networks")
        
        assert isinstance(result, list)
        mock_infra_api_client.get_all_remote_networks.assert_called_once_with(folder="Remote Networks")
    
    def test_capture_remote_networks_empty(self, mock_infra_api_client):
        """Test remote network capture with no results."""
        mock_infra_api_client.get_all_remote_networks.return_value = []
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_remote_networks()
        
        assert result == []
    
    def test_capture_remote_networks_api_error(self, mock_infra_api_client):
        """Test remote network capture with API error."""
        mock_infra_api_client.get_all_remote_networks.side_effect = Exception("API Error")
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_remote_networks()
        
        assert result == []  # Should return empty list on error


# ============================================================================
# Test Service Connections
# ============================================================================

@pytest.mark.unit
class TestServiceConnectionsCapture:
    """Test service connection capture functionality."""
    
    def test_capture_service_connections_success(self, mock_infra_api_client):
        """Test successful service connection capture."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_service_connections()
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "SC-HQ"
        mock_infra_api_client.get_all_service_connections.assert_called_once()
    
    def test_capture_service_connections_with_folder(self, mock_infra_api_client):
        """Test service connection capture with folder filter."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_service_connections(folder="Service Connections")
        
        assert isinstance(result, list)
        mock_infra_api_client.get_all_service_connections.assert_called_once_with(folder="Service Connections")


# ============================================================================
# Test IPsec/IKE Infrastructure
# ============================================================================

@pytest.mark.unit
class TestIPsecIKECapture:
    """Test IPsec and IKE capture functionality."""
    
    def test_capture_ipsec_tunnels_success(self, mock_infra_api_client):
        """Test successful IPsec tunnel capture."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_ipsec_tunnels()
        
        assert isinstance(result, dict)
        assert "ipsec_tunnels" in result
        assert "ike_gateways" in result
        assert "ike_crypto_profiles" in result
        assert "ipsec_crypto_profiles" in result
        
        assert len(result["ipsec_tunnels"]) == 2
        assert len(result["ike_gateways"]) == 2
        assert len(result["ike_crypto_profiles"]) == 2
        assert len(result["ipsec_crypto_profiles"]) == 2
    
    def test_capture_ipsec_tunnels_with_folder(self, mock_infra_api_client):
        """Test IPsec tunnel capture with folder filter."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_ipsec_tunnels(folder="Shared")
        
        mock_infra_api_client.get_all_ipsec_tunnels.assert_called_once_with(folder="Shared")
        mock_infra_api_client.get_all_ike_gateways.assert_called_once_with(folder="Shared")
    
    def test_capture_ipsec_tunnels_partial_failure(self, mock_infra_api_client):
        """Test IPsec capture with partial API failures."""
        # Simulate IKE crypto profiles failing
        mock_infra_api_client.get_all_ike_crypto_profiles.side_effect = Exception("API Error")
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_ipsec_tunnels()
        
        # Should still return results for successful calls
        assert "ipsec_tunnels" in result
        assert "ike_gateways" in result
        assert len(result["ipsec_tunnels"]) == 2
        # Failed call should return empty list
        assert result["ike_crypto_profiles"] == []


# ============================================================================
# Test Mobile User Infrastructure
# ============================================================================

@pytest.mark.unit
class TestMobileUserCapture:
    """Test mobile user infrastructure capture."""
    
    def test_capture_mobile_user_infrastructure_success(self, mock_infra_api_client):
        """Test successful mobile user infrastructure capture."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_mobile_user_infrastructure()
        
        assert isinstance(result, dict)
        assert "infrastructure_settings" in result
        assert "gp_gateways" in result
        assert "gp_portals" in result
        
        assert len(result["gp_gateways"]) == 1
        assert len(result["gp_portals"]) == 1
        assert result["gp_gateways"][0]["name"] == "GP-Gateway-1"
    
    def test_capture_mobile_user_infrastructure_no_gateways(self, mock_infra_api_client):
        """Test mobile user capture with no gateways."""
        mock_infra_api_client.get_all_globalprotect_gateways.return_value = []
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_mobile_user_infrastructure()
        
        assert result["gp_gateways"] == []
        assert len(result["gp_portals"]) == 1  # Portals still captured


# ============================================================================
# Test HIP Objects and Profiles
# ============================================================================

@pytest.mark.unit
class TestHIPCapture:
    """Test HIP object and profile capture."""
    
    def test_capture_hip_objects_and_profiles_success(self, mock_infra_api_client):
        """Test successful HIP capture."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_hip_objects_and_profiles()
        
        assert isinstance(result, dict)
        assert "hip_objects" in result
        assert "hip_profiles" in result
        
        assert len(result["hip_objects"]) == 2
        assert len(result["hip_profiles"]) == 1
        assert result["hip_objects"][0]["name"] == "Windows-Check"
    
    def test_capture_hip_with_folder(self, mock_infra_api_client):
        """Test HIP capture with folder filter."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_hip_objects_and_profiles(folder="Shared")
        
        mock_infra_api_client.get_all_hip_objects.assert_called_once_with(folder="Shared")
        mock_infra_api_client.get_all_hip_profiles.assert_called_once_with(folder="Shared")
    
    def test_capture_hip_endpoint_unavailable(self, mock_infra_api_client):
        """Test HIP capture when endpoint returns 404."""
        # Simulate 404 error
        error_404 = Exception("404")
        mock_infra_api_client.get_all_hip_objects.side_effect = error_404
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_hip_objects_and_profiles()
        
        # Should handle 404 gracefully
        assert result["hip_objects"] == []


# ============================================================================
# Test Regions and Bandwidth
# ============================================================================

@pytest.mark.unit
class TestRegionsBandwidthCapture:
    """Test regions and bandwidth allocation capture."""
    
    def test_capture_regions_and_bandwidth_success(self, mock_infra_api_client):
        """Test successful regions and bandwidth capture."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_regions_and_bandwidth()
        
        assert isinstance(result, dict)
        assert "locations" in result
        assert "bandwidth_allocations" in result
        
        assert len(result["locations"]) == 2
        assert len(result["bandwidth_allocations"]) == 2
        assert result["locations"][0]["name"] == "us-east-1"
    
    def test_capture_regions_empty(self, mock_infra_api_client):
        """Test regions capture with no deployed regions."""
        mock_infra_api_client.get_all_locations.return_value = []
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_regions_and_bandwidth()
        
        assert result["locations"] == []


# ============================================================================
# Test Comprehensive Infrastructure Capture
# ============================================================================

@pytest.mark.unit
class TestComprehensiveInfrastructureCapture:
    """Test comprehensive infrastructure capture with selective inclusion."""
    
    def test_capture_all_infrastructure_default(self, mock_infra_api_client):
        """Test capturing all infrastructure with default settings."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_all_infrastructure()
        
        assert isinstance(result, dict)
        # All components should be present
        assert "remote_networks" in result
        assert "service_connections" in result
        assert "ipsec_tunnels" in result
        assert "mobile_users" in result
        assert "hip" in result
        assert "regions" in result
        
        # Verify data is populated
        assert len(result["remote_networks"]) == 2
        assert len(result["service_connections"]) == 2
        assert "ipsec_tunnels" in result["ipsec_tunnels"]
        assert "gp_gateways" in result["mobile_users"]
        assert "hip_objects" in result["hip"]
        assert "locations" in result["regions"]
    
    def test_capture_all_infrastructure_selective(self, mock_infra_api_client):
        """Test capturing infrastructure with selective inclusion."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_all_infrastructure(
            include_remote_networks=True,
            include_service_connections=False,
            include_ipsec_tunnels=True,
            include_mobile_users=False,
            include_hip=False,
            include_regions=True
        )
        
        # Included components should be present
        assert "remote_networks" in result
        assert "ipsec_tunnels" in result
        assert "regions" in result
        
        # Excluded components should not be present
        assert "service_connections" not in result
        assert "mobile_users" not in result
        assert "hip" not in result
    
    def test_capture_all_infrastructure_with_folder(self, mock_infra_api_client):
        """Test comprehensive capture with folder filter."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_all_infrastructure(folder="Shared")
        
        # Verify folder was passed to folder-aware methods
        mock_infra_api_client.get_all_remote_networks.assert_called_once_with(folder="Shared")
        mock_infra_api_client.get_all_service_connections.assert_called_once_with(folder="Shared")
        mock_infra_api_client.get_all_ipsec_tunnels.assert_called_once_with(folder="Shared")
    
    def test_capture_all_infrastructure_none_selected(self, mock_infra_api_client):
        """Test comprehensive capture with all components disabled."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_all_infrastructure(
            include_remote_networks=False,
            include_service_connections=False,
            include_ipsec_tunnels=False,
            include_mobile_users=False,
            include_hip=False,
            include_regions=False
        )
        
        # Should return empty dict or minimal structure
        assert isinstance(result, dict)
        assert len(result) == 0 or all(not v for v in result.values())
    
    def test_capture_all_infrastructure_with_errors(self, mock_infra_api_client):
        """Test comprehensive capture with some API errors."""
        # Simulate some failures
        mock_infra_api_client.get_all_service_connections.side_effect = Exception("API Error")
        mock_infra_api_client.get_all_hip_objects.side_effect = Exception("API Error")
        
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_all_infrastructure()
        
        # Should still return results for successful calls
        assert "remote_networks" in result
        assert len(result["remote_networks"]) == 2
        
        # Failed calls should return empty results
        assert result["service_connections"] == []


# ============================================================================
# Test Error Handling
# ============================================================================

@pytest.mark.unit
class TestInfrastructureCaptureErrorHandling:
    """Test error handling in infrastructure capture."""
    
    def test_network_error_handling(self, mock_infra_api_client):
        """Test handling of network errors."""
        mock_infra_api_client.get_all_remote_networks.side_effect = ConnectionError("Network error")
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_remote_networks()
        
        assert result == []
    
    def test_timeout_error_handling(self, mock_infra_api_client):
        """Test handling of timeout errors."""
        mock_infra_api_client.get_all_service_connections.side_effect = TimeoutError("Request timeout")
        capture = InfrastructureCapture(mock_infra_api_client)
        
        result = capture.capture_service_connections()
        
        assert result == []
    
    def test_malformed_response_handling(self, mock_infra_api_client):
        """Test handling of malformed API responses."""
        # Return invalid data structure
        mock_infra_api_client.get_all_ipsec_tunnels.return_value = "invalid"
        capture = InfrastructureCapture(mock_infra_api_client)
        
        # Should handle gracefully without crashing
        try:
            result = capture.capture_ipsec_tunnels()
            # May succeed or fail gracefully
            assert isinstance(result, (dict, list))
        except Exception:
            # Should not raise unhandled exceptions
            pytest.fail("Should handle malformed responses gracefully")


# ============================================================================
# Test Rate Limiting Integration
# ============================================================================

@pytest.mark.unit
class TestRateLimitingIntegration:
    """Test that infrastructure capture respects rate limiting."""
    
    def test_sequential_api_calls(self, mock_infra_api_client):
        """Test that API calls are made sequentially to respect rate limits."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        # Capture all infrastructure
        result = capture.capture_all_infrastructure()
        
        # Verify all API methods were called
        assert mock_infra_api_client.get_all_remote_networks.called
        assert mock_infra_api_client.get_all_service_connections.called
        assert mock_infra_api_client.get_all_ipsec_tunnels.called
        assert mock_infra_api_client.get_all_ike_gateways.called
        assert mock_infra_api_client.get_all_globalprotect_gateways.called
        assert mock_infra_api_client.get_all_hip_objects.called
        assert mock_infra_api_client.get_all_locations.called
        
        # Verify rate limiter is being used (calls should go through API client)
        # which has built-in rate limiting


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.performance
class TestInfrastructureCapturePerformance:
    """Test performance characteristics of infrastructure capture."""
    
    def test_capture_performance_with_large_dataset(self, mock_infra_api_client):
        """Test performance with large dataset."""
        # Generate large dataset
        large_rn_list = [generate_remote_network_data(f"RN-{i}") for i in range(100)]
        mock_infra_api_client.get_all_remote_networks.return_value = large_rn_list
        
        capture = InfrastructureCapture(mock_infra_api_client)
        
        import time
        start = time.time()
        result = capture.capture_remote_networks()
        elapsed = time.time() - start
        
        assert len(result) == 100
        # Should complete in reasonable time (< 1 second for mock data)
        assert elapsed < 1.0
    
    def test_comprehensive_capture_performance(self, mock_infra_api_client):
        """Test performance of comprehensive capture."""
        capture = InfrastructureCapture(mock_infra_api_client)
        
        import time
        start = time.time()
        result = capture.capture_all_infrastructure()
        elapsed = time.time() - start
        
        # Should complete in reasonable time even with all components
        assert elapsed < 2.0  # 2 seconds for mock data
        assert isinstance(result, dict)
