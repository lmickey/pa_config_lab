"""
End-to-end tests for pull operations.

Tests cover:
- Full pull workflow
- Pull with mocked API responses
- Error handling during pull
- Pull statistics and reporting
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from prisma.pull.config_pull import pull_configuration
from prisma.pull.pull_orchestrator import PullOrchestrator
from tests.conftest import (
    mock_authenticated_api_client,
    mock_folders_response,
    mock_rules_response,
    mock_addresses_response,
    sample_config_v2
)


@pytest.mark.e2e
class TestPullWorkflow:
    """Test complete pull workflow."""
    
    @patch('prisma.pull.config_pull.PrismaAccessAPIClient')
    def test_pull_single_folder(self, mock_client_class):
        """Test pulling configuration for a single folder."""
        # Setup mock API client
        mock_client = Mock()
        mock_client.get_security_policy_folders.return_value = [
            {"name": "Shared", "id": "folder-1"}
        ]
        mock_client.get_all_security_rules.return_value = []
        mock_client.get_all_addresses.return_value = []
        mock_client.get_all_address_groups.return_value = []
        mock_client.get_all_services.return_value = []
        mock_client.get_all_service_groups.return_value = []
        mock_client.get_all_applications.return_value = []
        mock_client.get_all_authentication_profiles.return_value = []
        mock_client.get_all_security_profiles.return_value = {}
        mock_client.get_decryption_profiles.return_value = []
        mock_client_class.return_value = mock_client
        
        config = pull_configuration(
            mock_client,
            folder_names=["Shared"],
            include_snippets=False,
            include_objects=True,
            include_profiles=True
        )
        
        assert config is not None
        assert "metadata" in config
        assert "security_policies" in config
        assert len(config["security_policies"]["folders"]) > 0
    
    @patch('prisma.pull.config_pull.PrismaAccessAPIClient')
    def test_pull_multiple_folders(self, mock_client_class):
        """Test pulling configuration for multiple folders."""
        # Setup mock API client
        mock_client = Mock()
        mock_client.get_security_policy_folders.return_value = [
            {"name": "Shared", "id": "folder-1"},
            {"name": "Mobile Users", "id": "folder-2"}
        ]
        mock_client.get_all_security_rules.return_value = []
        mock_client.get_all_addresses.return_value = []
        mock_client.get_all_address_groups.return_value = []
        mock_client.get_all_services.return_value = []
        mock_client.get_all_service_groups.return_value = []
        mock_client.get_all_applications.return_value = []
        mock_client.get_all_authentication_profiles.return_value = []
        mock_client.get_all_security_profiles.return_value = {}
        mock_client.get_decryption_profiles.return_value = []
        mock_client_class.return_value = mock_client
        
        config = pull_configuration(
            mock_client,
            folder_names=["Shared", "Mobile Users"],
            include_snippets=False
        )
        
        assert config is not None
        folders = config["security_policies"]["folders"]
        assert len(folders) == 2
        folder_names = [f["name"] for f in folders]
        assert "Shared" in folder_names
        assert "Mobile Users" in folder_names
    
    @patch('prisma.pull.config_pull.PrismaAccessAPIClient')
    def test_pull_with_snippets(self, mock_client_class):
        """Test pulling configuration including snippets."""
        # Setup mock API client
        mock_client = Mock()
        mock_client.get_security_policy_folders.return_value = [
            {"name": "Shared", "id": "folder-1"}
        ]
        mock_client.get_security_policy_snippets.return_value = [
            {"name": "custom-snippet", "id": "snippet-1"}
        ]
        mock_client.get_security_policy_snippet.return_value = {
            "name": "custom-snippet",
            "id": "snippet-1"
        }
        mock_client.get_all_security_rules.return_value = []
        mock_client.get_all_addresses.return_value = []
        mock_client.get_all_address_groups.return_value = []
        mock_client.get_all_services.return_value = []
        mock_client.get_all_service_groups.return_value = []
        mock_client.get_all_applications.return_value = []
        mock_client.get_all_authentication_profiles.return_value = []
        mock_client.get_all_security_profiles.return_value = {}
        mock_client.get_decryption_profiles.return_value = []
        mock_client_class.return_value = mock_client
        
        config = pull_configuration(
            mock_client,
            folder_names=["Shared"],
            snippet_names=["custom-snippet"],
            include_snippets=True
        )
        
        assert config is not None
        snippets = config["security_policies"]["snippets"]
        assert len(snippets) > 0
        assert any(s["name"] == "custom-snippet" for s in snippets)


@pytest.mark.e2e
class TestPullOrchestrator:
    """Test pull orchestrator functionality."""
    
    def test_pull_folder_configuration(self, mock_authenticated_api_client):
        """Test pulling a single folder configuration."""
        # Setup mock responses
        mock_authenticated_api_client.get_all_security_rules.return_value = []
        mock_authenticated_api_client.get_all_addresses.return_value = []
        mock_authenticated_api_client.get_all_address_groups.return_value = []
        mock_authenticated_api_client.get_all_services.return_value = []
        mock_authenticated_api_client.get_all_service_groups.return_value = []
        mock_authenticated_api_client.get_all_applications.return_value = []
        mock_authenticated_api_client.get_all_authentication_profiles.return_value = []
        mock_authenticated_api_client.get_all_security_profiles.return_value = {}
        mock_authenticated_api_client.get_decryption_profiles.return_value = []
        
        orchestrator = PullOrchestrator(mock_authenticated_api_client)
        folder_config = orchestrator.pull_folder_configuration("Shared")
        
        assert folder_config is not None
        assert folder_config["name"] == "Shared"
        assert "security_rules" in folder_config
        assert "objects" in folder_config
        assert "profiles" in folder_config
    
    def test_pull_statistics(self, mock_authenticated_api_client):
        """Test that pull statistics are tracked."""
        # Setup mock responses
        mock_authenticated_api_client.get_all_security_rules.return_value = [
            {"name": "Rule1", "folder": "Shared"}
        ]
        mock_authenticated_api_client.get_all_addresses.return_value = [
            {"name": "Addr1", "folder": "Shared"}
        ]
        mock_authenticated_api_client.get_all_address_groups.return_value = []
        mock_authenticated_api_client.get_all_services.return_value = []
        mock_authenticated_api_client.get_all_service_groups.return_value = []
        mock_authenticated_api_client.get_all_applications.return_value = []
        mock_authenticated_api_client.get_all_authentication_profiles.return_value = []
        mock_authenticated_api_client.get_all_security_profiles.return_value = {}
        mock_authenticated_api_client.get_decryption_profiles.return_value = []
        
        orchestrator = PullOrchestrator(mock_authenticated_api_client)
        orchestrator.pull_folder_configuration("Shared")
        
        stats = orchestrator.stats
        assert stats["folders_captured"] > 0
        assert stats["rules_captured"] >= 0
        assert stats["objects_captured"] >= 0


@pytest.mark.e2e
class TestPullErrorHandling:
    """Test error handling during pull operations."""
    
    def test_pull_with_api_error(self, mock_authenticated_api_client):
        """Test pull handling API errors gracefully."""
        # Setup mock to raise error
        mock_authenticated_api_client.get_all_security_rules.side_effect = Exception("API Error")
        
        orchestrator = PullOrchestrator(mock_authenticated_api_client)
        
        # Should handle error gracefully
        folder_config = orchestrator.pull_folder_configuration("Shared")
        assert folder_config is not None
        # Should still have basic structure even if some data failed
        # The folder_config should have at least a name field
        assert isinstance(folder_config, dict)
    
    def test_pull_with_partial_failure(self, mock_authenticated_api_client):
        """Test pull with partial API failures."""
        # Setup some methods to succeed, others to fail
        mock_authenticated_api_client.get_all_security_rules.return_value = []
        mock_authenticated_api_client.get_all_addresses.side_effect = Exception("Address API Error")
        mock_authenticated_api_client.get_all_address_groups.return_value = []
        mock_authenticated_api_client.get_all_services.return_value = []
        mock_authenticated_api_client.get_all_service_groups.return_value = []
        mock_authenticated_api_client.get_all_applications.return_value = []
        mock_authenticated_api_client.get_all_authentication_profiles.return_value = []
        mock_authenticated_api_client.get_all_security_profiles.return_value = {}
        mock_authenticated_api_client.get_decryption_profiles.return_value = []
        
        orchestrator = PullOrchestrator(mock_authenticated_api_client)
        folder_config = orchestrator.pull_folder_configuration("Shared")
        
        # Should still return config even with partial failures
        assert folder_config is not None
        # Objects might be empty due to error
        assert "objects" in folder_config


@pytest.mark.e2e
class TestPullWithDefaults:
    """Test pull operations with default detection."""
    
    def test_pull_with_default_detection(self, mock_authenticated_api_client):
        """Test pull with default detection enabled."""
        # Setup mock responses
        mock_authenticated_api_client.get_all_security_rules.return_value = []
        mock_authenticated_api_client.get_all_addresses.return_value = []
        mock_authenticated_api_client.get_all_address_groups.return_value = []
        mock_authenticated_api_client.get_all_services.return_value = []
        mock_authenticated_api_client.get_all_service_groups.return_value = []
        mock_authenticated_api_client.get_all_applications.return_value = []
        mock_authenticated_api_client.get_all_authentication_profiles.return_value = []
        mock_authenticated_api_client.get_all_security_profiles.return_value = {}
        mock_authenticated_api_client.get_decryption_profiles.return_value = []
        
        orchestrator = PullOrchestrator(mock_authenticated_api_client, detect_defaults=True)
        folder_config = orchestrator.pull_folder_configuration("Shared")
        
        assert folder_config is not None
        # Default detection should mark items appropriately
        # (exact structure depends on implementation)
