"""
Integration tests for Phase 4: Dependency Resolution.

These tests use real API responses when credentials are available.
They can be skipped if credentials are not provided via environment variables.
"""

import os
import pytest

# Skip integration tests if credentials not available
pytestmark = pytest.mark.integration


@pytest.fixture
def api_credentials():
    """Get API credentials from environment variables."""
    tsg = os.getenv("PRISMA_TSG_ID")
    api_user = os.getenv("PRISMA_API_USER")
    api_secret = os.getenv("PRISMA_API_SECRET")
    
    if not all([tsg, api_user, api_secret]):
        pytest.skip("API credentials not provided (set PRISMA_TSG_ID, PRISMA_API_USER, PRISMA_API_SECRET)")
    
    return {
        "tsg": tsg,
        "api_user": api_user,
        "api_secret": api_secret
    }


@pytest.fixture
def authenticated_api_client(api_credentials):
    """Create authenticated API client."""
    from prisma.api_client import PrismaAccessAPIClient
    
    client = PrismaAccessAPIClient(
        tsg_id=api_credentials["tsg"],
        api_user=api_credentials["api_user"],
        api_secret=api_credentials["api_secret"]
    )
    
    # Verify authentication
    if not client.authenticate():
        pytest.skip("Failed to authenticate with API")
    
    return client


class TestDependencyGraph:
    """Test dependency graph functionality."""
    
    def test_graph_creation(self):
        """Test creating dependency graph."""
        from prisma.dependencies.dependency_graph import DependencyGraph
        
        graph = DependencyGraph()
        assert graph is not None
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
    
    def test_add_nodes_and_dependencies(self):
        """Test adding nodes and dependencies."""
        from prisma.dependencies.dependency_graph import DependencyGraph
        
        graph = DependencyGraph()
        graph.add_node("addr1", "address_object", {})
        graph.add_node("group1", "address_group", {})
        graph.add_dependency("group1", "addr1", "address_group", "address_object")
        
        assert "addr1" in graph.nodes
        assert "group1" in graph.nodes
        assert ("group1", "addr1") in graph.edges


class TestDependencyResolver:
    """Test dependency resolver functionality."""
    
    def test_resolver_initialization(self):
        """Test dependency resolver initialization."""
        from prisma.dependencies.dependency_resolver import DependencyResolver
        
        resolver = DependencyResolver()
        assert resolver is not None
    
    def test_build_dependency_graph(self):
        """Test building dependency graph from config."""
        from prisma.dependencies.dependency_resolver import DependencyResolver
        from tests.conftest import generate_address_object_data, generate_address_group_data
        
        resolver = DependencyResolver()
        config = {
            "security_policies": {
                "folders": [
                    {
                        "name": "Test Folder",
                        "path": "/config/security-policy/folders/Test Folder",
                        "objects": {
                            "address_objects": [
                                generate_address_object_data("Addr1", "Test Folder")
                            ],
                            "address_groups": [
                                generate_address_group_data("Group1", "Test Folder", ["Addr1"])
                            ]
                        },
                        "security_rules": [],
                        "profiles": {}
                    }
                ],
                "snippets": []
            }
        }
        
        resolver.build_dependency_graph(config)
        assert len(resolver.graph.nodes) > 0
        assert len(resolver.graph.edges) > 0
    
    def test_validate_dependencies(self):
        """Test dependency validation."""
        from prisma.dependencies.dependency_resolver import DependencyResolver
        from tests.conftest import generate_address_object_data, generate_address_group_data
        
        resolver = DependencyResolver()
        config = {
            "security_policies": {
                "folders": [
                    {
                        "name": "Test Folder",
                        "path": "/config/security-policy/folders/Test Folder",
                        "objects": {
                            "address_objects": [
                                generate_address_object_data("Addr1", "Test Folder")
                            ],
                            "address_groups": [
                                generate_address_group_data("Group1", "Test Folder", ["Addr1"])
                            ]
                        },
                        "security_rules": [],
                        "profiles": {}
                    }
                ],
                "snippets": []
            }
        }
        
        result = resolver.validate_dependencies(config)
        assert "valid" in result
        assert result["valid"] is True


class TestIntegrationWithPull:
    """Test integration with pull functionality."""
    
    def test_pull_with_dependency_resolution(self, authenticated_api_client):
        """Test pulling configuration with dependency resolution."""
        from prisma.pull.config_pull import pull_configuration
        from prisma.dependencies.dependency_resolver import DependencyResolver
        
        folders = authenticated_api_client.get_security_policy_folders()
        if not folders:
            pytest.skip("No folders available")
        
        folder_name = folders[0].get("name", "Shared")
        config = pull_configuration(
            authenticated_api_client,
            folder_names=[folder_name],
            include_snippets=False
        )
        
        assert config is not None
        
        # Validate dependencies
        resolver = DependencyResolver()
        validation = resolver.validate_dependencies(config)
        assert "valid" in validation
        
        # Get resolution order
        order = resolver.get_resolution_order(config)
        assert isinstance(order, list)
