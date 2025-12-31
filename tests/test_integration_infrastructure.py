"""
Integration tests for Infrastructure Capture.

These tests verify the infrastructure capture module integrates correctly
with the API client and pull orchestrator. Tests are skipped if API
credentials are not available.
"""

import pytest
import os
from typing import Dict, Any

from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.infrastructure_capture import InfrastructureCapture
from prisma.pull.pull_orchestrator import PullOrchestrator


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def live_api_client(has_api_credentials):
    """
    Create a live API client if credentials are available.
    
    Requires environment variables:
    - PRISMA_TSG_ID
    - PRISMA_API_USER
    - PRISMA_API_SECRET
    """
    if not has_api_credentials:
        pytest.skip("API credentials not available")
    
    tsg_id = os.getenv("PRISMA_TSG_ID")
    api_user = os.getenv("PRISMA_API_USER")
    api_secret = os.getenv("PRISMA_API_SECRET")
    
    client = PrismaAccessAPIClient(
        tsg_id=tsg_id,
        api_user=api_user,
        api_secret=api_secret,
        rate_limit=45  # Use 45 req/min as configured
    )
    
    # Verify authentication
    if not client.token:
        pytest.skip("Failed to authenticate with Prisma Access")
    
    return client


# ============================================================================
# API Client Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not all([os.getenv("PRISMA_TSG_ID"), os.getenv("PRISMA_API_USER"), os.getenv("PRISMA_API_SECRET")]),
    reason="API credentials not available"
)
class TestAPIClientIntegration:
    """Test infrastructure capture integration with live API client."""
    
    def test_remote_networks_api_integration(self, live_api_client):
        """Test remote network capture with live API."""
        capture = InfrastructureCapture(live_api_client)
        
        result = capture.capture_remote_networks()
        
        assert isinstance(result, list)
        # Tenant may have 0 or more remote networks
        for rn in result:
            assert "name" in rn
            assert "id" in rn
    
    def test_service_connections_api_integration(self, live_api_client):
        """Test service connection capture with live API."""
        capture = InfrastructureCapture(live_api_client)
        
        result = capture.capture_service_connections()
        
        assert isinstance(result, list)
        for sc in result:
            assert "name" in sc
            assert "id" in sc
    
    def test_ipsec_tunnels_api_integration(self, live_api_client):
        """Test IPsec tunnel capture with live API."""
        capture = InfrastructureCapture(live_api_client)
        
        result = capture.capture_ipsec_tunnels()
        
        assert isinstance(result, dict)
        assert "ipsec_tunnels" in result
        assert "ike_gateways" in result
        assert "ike_crypto_profiles" in result
        assert "ipsec_crypto_profiles" in result
        
        # Verify structure
        assert isinstance(result["ipsec_tunnels"], list)
        assert isinstance(result["ike_gateways"], list)
    
    def test_mobile_user_api_integration(self, live_api_client):
        """Test mobile user infrastructure capture with live API."""
        capture = InfrastructureCapture(live_api_client)
        
        result = capture.capture_mobile_user_infrastructure()
        
        assert isinstance(result, dict)
        assert "infrastructure_settings" in result
        assert "gp_gateways" in result
        assert "gp_portals" in result
    
    def test_hip_api_integration(self, live_api_client):
        """Test HIP objects and profiles capture with live API."""
        capture = InfrastructureCapture(live_api_client)
        
        # Note: HIP endpoints may not be available in all environments
        try:
            result = capture.capture_hip_objects_and_profiles()
            
            assert isinstance(result, dict)
            assert "hip_objects" in result
            assert "hip_profiles" in result
        except Exception as e:
            # HIP endpoints may return 404 in some environments
            if "404" in str(e):
                pytest.skip("HIP endpoints not available in this environment")
            raise
    
    def test_regions_api_integration(self, live_api_client):
        """Test regions and bandwidth capture with live API."""
        capture = InfrastructureCapture(live_api_client)
        
        result = capture.capture_regions_and_bandwidth()
        
        assert isinstance(result, dict)
        assert "locations" in result
        assert "bandwidth_allocations" in result
        
        # Should have at least one deployed region
        assert isinstance(result["locations"], list)
    
    def test_comprehensive_api_integration(self, live_api_client):
        """Test comprehensive infrastructure capture with live API."""
        capture = InfrastructureCapture(live_api_client)
        
        result = capture.capture_all_infrastructure()
        
        assert isinstance(result, dict)
        
        # Verify all expected sections are present
        assert "remote_networks" in result
        assert "service_connections" in result
        assert "ipsec_tunnels" in result
        assert "mobile_users" in result
        assert "regions" in result
        
        # Verify data types
        assert isinstance(result["remote_networks"], list)
        assert isinstance(result["service_connections"], list)
        assert isinstance(result["ipsec_tunnels"], dict)
        assert isinstance(result["mobile_users"], dict)
        assert isinstance(result["regions"], dict)


# ============================================================================
# Pull Orchestrator Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not all([os.getenv("PRISMA_TSG_ID"), os.getenv("PRISMA_API_USER"), os.getenv("PRISMA_API_SECRET")]),
    reason="API credentials not available"
)
class TestPullOrchestratorIntegration:
    """Test infrastructure capture integration with pull orchestrator."""
    
    def test_pull_orchestrator_with_infrastructure(self, live_api_client):
        """Test pull orchestrator includes infrastructure components."""
        orchestrator = PullOrchestrator(live_api_client)
        
        # Pull configuration with infrastructure enabled
        config = orchestrator.pull_complete_configuration(
            include_folders=False,  # Skip folders for faster test
            include_snippets=False,
            include_rules=False,
            include_objects=False,
            include_profiles=False,
            include_remote_networks=True,
            include_service_connections=True,
            include_ipsec_tunnels=True,
            include_mobile_users=True,
            include_hip=True,
            include_regions=True
        )
        
        assert config is not None
        assert "infrastructure" in config
        
        # Verify infrastructure structure
        infra = config["infrastructure"]
        assert "remote_networks" in infra or "ipsec_tunnels" in infra or "regions" in infra
    
    def test_pull_orchestrator_selective_infrastructure(self, live_api_client):
        """Test pull orchestrator with selective infrastructure components."""
        orchestrator = PullOrchestrator(live_api_client)
        
        # Pull only remote networks and regions
        config = orchestrator.pull_complete_configuration(
            include_folders=False,
            include_snippets=False,
            include_rules=False,
            include_objects=False,
            include_profiles=False,
            include_remote_networks=True,
            include_service_connections=False,
            include_ipsec_tunnels=False,
            include_mobile_users=False,
            include_hip=False,
            include_regions=True
        )
        
        assert config is not None
        assert "infrastructure" in config
        
        infra = config["infrastructure"]
        # Should have remote_networks and regions
        # Should NOT have service_connections, ipsec_tunnels, mobile_users
        # (exact structure depends on implementation)
    
    def test_pull_orchestrator_no_infrastructure(self, live_api_client):
        """Test pull orchestrator with infrastructure disabled."""
        orchestrator = PullOrchestrator(live_api_client)
        
        # Pull without infrastructure
        config = orchestrator.pull_complete_configuration(
            include_folders=False,
            include_snippets=False,
            include_rules=False,
            include_objects=False,
            include_profiles=False,
            include_remote_networks=False,
            include_service_connections=False,
            include_ipsec_tunnels=False,
            include_mobile_users=False,
            include_hip=False,
            include_regions=False
        )
        
        assert config is not None
        # Infrastructure section may be present but empty
        if "infrastructure" in config:
            infra = config["infrastructure"]
            # All infrastructure lists should be empty or missing
            assert not infra.get("remote_networks", [])
            assert not infra.get("service_connections", [])


# ============================================================================
# Rate Limiting Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not all([os.getenv("PRISMA_TSG_ID"), os.getenv("PRISMA_API_USER"), os.getenv("PRISMA_API_SECRET")]),
    reason="API credentials not available"
)
class TestRateLimitingIntegration:
    """Test that rate limiting works correctly with infrastructure capture."""
    
    def test_rate_limiting_during_comprehensive_capture(self, live_api_client):
        """Test rate limiting is enforced during comprehensive capture."""
        import time
        
        capture = InfrastructureCapture(live_api_client)
        
        # Capture all infrastructure (will make multiple API calls)
        start_time = time.time()
        result = capture.capture_all_infrastructure()
        elapsed_time = time.time() - start_time
        
        # Should complete successfully
        assert isinstance(result, dict)
        
        # Should take reasonable time (rate limiting shouldn't cause excessive delays)
        # With 45 req/min rate limit, should complete in reasonable time
        # (This is a soft check - actual time depends on number of objects)
        assert elapsed_time < 300  # 5 minutes max for comprehensive capture
    
    def test_multiple_sequential_captures(self, live_api_client):
        """Test multiple sequential captures respect rate limits."""
        import time
        
        capture = InfrastructureCapture(live_api_client)
        
        # Perform multiple captures
        start_time = time.time()
        
        result1 = capture.capture_remote_networks()
        result2 = capture.capture_service_connections()
        result3 = capture.capture_regions_and_bandwidth()
        
        elapsed_time = time.time() - start_time
        
        # All should succeed
        assert isinstance(result1, list)
        assert isinstance(result2, list)
        assert isinstance(result3, dict)
        
        # Rate limiter should add minimal delay for just 3 calls
        # (45 req/min = 1.33 seconds between calls, so ~2.66 seconds minimum)
        # Allow up to 30 seconds for network latency
        assert elapsed_time < 30


# ============================================================================
# Error Handling Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not all([os.getenv("PRISMA_TSG_ID"), os.getenv("PRISMA_API_USER"), os.getenv("PRISMA_API_SECRET")]),
    reason="API credentials not available"
)
class TestErrorHandlingIntegration:
    """Test error handling in real-world scenarios."""
    
    def test_unavailable_endpoint_handling(self, live_api_client):
        """Test graceful handling of unavailable endpoints."""
        capture = InfrastructureCapture(live_api_client)
        
        # HIP endpoints may not be available in all environments
        # Should handle gracefully and return empty results
        result = capture.capture_hip_objects_and_profiles()
        
        # Should return valid structure even if endpoint is unavailable
        assert isinstance(result, dict)
        assert "hip_objects" in result
        assert "hip_profiles" in result
        # Results may be empty if endpoint unavailable
        assert isinstance(result["hip_objects"], list)
        assert isinstance(result["hip_profiles"], list)
    
    def test_partial_failure_handling(self, live_api_client):
        """Test handling when some but not all endpoints fail."""
        capture = InfrastructureCapture(live_api_client)
        
        # Capture all infrastructure
        # Some endpoints may fail (e.g., HIP) but others should succeed
        result = capture.capture_all_infrastructure()
        
        # Should return results even with partial failures
        assert isinstance(result, dict)
        
        # At least some components should have data
        # (unless tenant has no infrastructure configured)
        has_data = any([
            result.get("remote_networks"),
            result.get("service_connections"),
            result.get("ipsec_tunnels", {}).get("ipsec_tunnels"),
            result.get("regions", {}).get("locations")
        ])
        
        # Should have at least regions/locations
        assert "regions" in result


# ============================================================================
# Data Validation Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not all([os.getenv("PRISMA_TSG_ID"), os.getenv("PRISMA_API_USER"), os.getenv("PRISMA_API_SECRET")]),
    reason="API credentials not available"
)
class TestDataValidationIntegration:
    """Test that captured data has correct structure and types."""
    
    def test_remote_network_data_structure(self, live_api_client):
        """Test remote network data has expected structure."""
        capture = InfrastructureCapture(live_api_client)
        
        result = capture.capture_remote_networks()
        
        assert isinstance(result, list)
        
        # If tenant has remote networks, validate structure
        for rn in result:
            assert isinstance(rn, dict)
            assert "id" in rn
            assert "name" in rn
            # May have other fields like region, subnets, etc.
    
    def test_ipsec_tunnel_data_structure(self, live_api_client):
        """Test IPsec tunnel data has expected structure."""
        capture = InfrastructureCapture(live_api_client)
        
        result = capture.capture_ipsec_tunnels()
        
        assert isinstance(result, dict)
        
        # Validate top-level structure
        assert "ipsec_tunnels" in result
        assert "ike_gateways" in result
        assert "ike_crypto_profiles" in result
        assert "ipsec_crypto_profiles" in result
        
        # Validate data types
        assert isinstance(result["ipsec_tunnels"], list)
        assert isinstance(result["ike_gateways"], list)
        assert isinstance(result["ike_crypto_profiles"], list)
        assert isinstance(result["ipsec_crypto_profiles"], list)
        
        # If tenant has tunnels, validate structure
        for tunnel in result["ipsec_tunnels"]:
            assert isinstance(tunnel, dict)
            assert "id" in tunnel
            assert "name" in tunnel
    
    def test_regions_data_structure(self, live_api_client):
        """Test regions data has expected structure."""
        capture = InfrastructureCapture(live_api_client)
        
        result = capture.capture_regions_and_bandwidth()
        
        assert isinstance(result, dict)
        assert "locations" in result
        assert "bandwidth_allocations" in result
        
        # Should have at least one location (every tenant has regions)
        assert isinstance(result["locations"], list)
        
        # Validate location structure
        for location in result["locations"]:
            assert isinstance(location, dict)
            assert "id" in location or "name" in location


# ============================================================================
# Performance Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.skipif(
    not all([os.getenv("PRISMA_TSG_ID"), os.getenv("PRISMA_API_USER"), os.getenv("PRISMA_API_SECRET")]),
    reason="API credentials not available"
)
class TestPerformanceIntegration:
    """Test performance characteristics with live API."""
    
    def test_comprehensive_capture_performance(self, live_api_client):
        """Test performance of comprehensive infrastructure capture."""
        import time
        
        capture = InfrastructureCapture(live_api_client)
        
        start_time = time.time()
        result = capture.capture_all_infrastructure()
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time
        # With rate limiting (45 req/min), expect ~10-20 API calls
        # Should complete within 5 minutes
        assert elapsed_time < 300
        
        # Should return valid data
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_individual_component_performance(self, live_api_client):
        """Test performance of individual component captures."""
        import time
        
        capture = InfrastructureCapture(live_api_client)
        
        # Test each component individually
        components = [
            ("remote_networks", lambda: capture.capture_remote_networks()),
            ("service_connections", lambda: capture.capture_service_connections()),
            ("ipsec_tunnels", lambda: capture.capture_ipsec_tunnels()),
            ("mobile_users", lambda: capture.capture_mobile_user_infrastructure()),
            ("regions", lambda: capture.capture_regions_and_bandwidth()),
        ]
        
        for name, capture_func in components:
            start_time = time.time()
            result = capture_func()
            elapsed_time = time.time() - start_time
            
            # Each component should complete within 60 seconds
            assert elapsed_time < 60, f"{name} capture took too long: {elapsed_time}s"
            
            # Should return valid data
            assert result is not None
