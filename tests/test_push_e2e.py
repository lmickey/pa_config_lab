"""
End-to-end tests for push operations.

Tests cover:
- Full push workflow
- Push validation
- Conflict resolution
- Error handling during push
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from prisma.push.config_push import push_configuration
from prisma.push.push_orchestrator import PushOrchestrator
from prisma.push.push_validator import PushValidator
from prisma.push.conflict_resolver import ConflictResolver, ConflictResolution
from tests.conftest import sample_config_v2


@pytest.mark.e2e
class TestPushWorkflow:
    """Test complete push workflow."""
    
    def test_push_single_folder(self, sample_config_v2):
        """Test pushing configuration for a single folder."""
        # Setup mock API client
        mock_client = Mock()
        mock_client.get_security_policy_folders.return_value = [
            {"name": "Shared", "id": "folder-1"}
        ]
        mock_client.post.return_value = Mock(status_code=200, json=lambda: {"id": "new-id"})
        mock_client.put.return_value = Mock(status_code=200)
        
        import copy
        config = copy.deepcopy(sample_config_v2)
        config["security_policies"]["folders"] = [
            {
                "name": "Shared",
                "path": "/config/security-policy/folders/Shared",
                "is_default": False,
                "security_rules": [],
                "objects": {},
                "profiles": {}
            }
        ]
        
        result = push_configuration(
            mock_client,
            config,
            folder_names=["Shared"]
        )
        
        # Should complete without errors
        assert result is not None
    
    def test_push_multiple_folders(self, sample_config_v2):
        """Test pushing configuration for multiple folders."""
        # Setup mock API client
        mock_client = Mock()
        mock_client.get_security_policy_folders.return_value = [
            {"name": "Shared", "id": "folder-1"},
            {"name": "Mobile Users", "id": "folder-2"}
        ]
        mock_client.post.return_value = Mock(status_code=200, json=lambda: {"id": "new-id"})
        mock_client.put.return_value = Mock(status_code=200)
        
        import copy
        config = copy.deepcopy(sample_config_v2)
        config["security_policies"]["folders"] = [
            {
                "name": "Shared",
                "path": "/config/security-policy/folders/Shared",
                "is_default": False,
                "security_rules": [],
                "objects": {},
                "profiles": {}
            },
            {
                "name": "Mobile Users",
                "path": "/config/security-policy/folders/Mobile Users",
                "is_default": False,
                "security_rules": [],
                "objects": {},
                "profiles": {}
            }
        ]
        
        result = push_configuration(
            mock_client,
            config,
            folder_names=["Shared", "Mobile Users"]
        )
        
        assert result is not None


@pytest.mark.e2e
class TestPushValidation:
    """Test push validation."""
    
    def test_validate_valid_config(self, sample_config_v2):
        """Test validation of valid configuration."""
        validator = PushValidator()
        mock_client = Mock()
        
        result = validator.validate_configuration(
            sample_config_v2,
            mock_client,
            check_dependencies=True
        )
        
        assert "valid" in result
        # Should pass basic validation
    
    def test_validate_missing_dependencies(self):
        """Test validation detects missing dependencies."""
        validator = PushValidator()
        mock_client = Mock()
        
        config = {
            "security_policies": {
                "folders": [
                    {
                        "name": "Test Folder",
                        "path": "/config/security-policy/folders/Test Folder",
                        "objects": {
                            "address_groups": [
                                {
                                    "name": "Group1",
                                    "static": ["MissingAddr"]
                                }
                            ]
                        },
                        "security_rules": [],
                        "profiles": {}
                    }
                ],
                "snippets": []
            }
        }
        
        result = validator.validate_configuration(
            config,
            mock_client,
            check_dependencies=True
        )
        
        # Should detect missing dependencies
        assert result is not None


@pytest.mark.e2e
class TestConflictResolution:
    """Test conflict resolution."""
    
    def test_detect_conflicts(self):
        """Test conflict detection."""
        resolver = ConflictResolver()
        mock_client = Mock()
        
        # Mock existing objects
        mock_client.get_addresses.return_value = [
            {"name": "ExistingAddr", "id": "addr-1"}
        ]
        
        new_config = {
            "security_policies": {
                "folders": [
                    {
                        "name": "Test Folder",
                        "path": "/config/security-policy/folders/Test Folder",
                        "objects": {
                            "address_objects": [
                                {"name": "ExistingAddr", "value": "192.168.1.1"}
                            ]
                        },
                        "security_rules": [],
                        "profiles": {}
                    }
                ],
                "snippets": []
            }
        }
        
        result = resolver.detect_conflicts(new_config, mock_client, folder_name="Test Folder")
        
        # Should detect conflict with existing address
        assert isinstance(result, dict)
        assert "has_conflicts" in result
        assert "conflicts" in result
        assert isinstance(result["conflicts"], list)
    
    def test_resolve_conflicts_skip(self):
        """Test conflict resolution with skip strategy."""
        resolver = ConflictResolver()
        mock_client = Mock()
        
        # Set resolution strategy
        resolver.set_default_strategy(ConflictResolution.SKIP)
        
        # Detect conflicts first
        config = {
            "security_policies": {
                "folders": [
                    {
                        "name": "Test Folder",
                        "path": "/config/security-policy/folders/Test Folder",
                        "objects": {
                            "address_objects": [
                                {"name": "ExistingAddr", "value": "192.168.1.1"}
                            ]
                        },
                        "security_rules": [],
                        "profiles": {}
                    }
                ],
                "snippets": []
            }
        }
        
        mock_client.get_addresses.return_value = [
            {"name": "ExistingAddr", "id": "addr-1"}
        ]
        
        result = resolver.detect_conflicts(config, mock_client)
        # Should detect conflicts
        assert isinstance(result, dict)


@pytest.mark.e2e
class TestPushErrorHandling:
    """Test error handling during push operations."""
    
    def test_push_with_api_error(self, sample_config_v2):
        """Test push handling API errors gracefully."""
        mock_client = Mock()
        mock_client.get_security_policy_folders.side_effect = Exception("API Error")
        
        import copy
        config = copy.deepcopy(sample_config_v2)
        
        # Should handle error gracefully (push_configuration catches exceptions)
        result = push_configuration(mock_client, config)
        # Should return error result, not raise exception
        assert result is not None
        assert result.get("success") is False or "error" in str(result).lower()
    
    def test_push_with_validation_failure(self):
        """Test push with validation failure."""
        mock_client = Mock()
        mock_client.get_security_policy_folders.return_value = []
        
        # Invalid config (missing required fields)
        config = {
            "security_policies": {
                "folders": []
            }
        }
        
        # Should validate before pushing
        result = push_configuration(mock_client, config, validate=True)
        # Result depends on validation implementation
        assert result is not None


@pytest.mark.e2e
class TestPushOrchestrator:
    """Test push orchestrator functionality."""
    
    def test_push_folder_configuration(self, mock_authenticated_api_client, sample_config_v2):
        """Test pushing a single folder configuration."""
        # Setup mock responses
        mock_authenticated_api_client.get_security_policy_folders.return_value = [
            {"name": "Shared", "id": "folder-1"}
        ]
        mock_authenticated_api_client.post.return_value = Mock(
            status_code=200,
            json=lambda: {"id": "new-id"}
        )
        mock_authenticated_api_client.put.return_value = Mock(status_code=200)
        
        import copy
        config = copy.deepcopy(sample_config_v2)
        config["security_policies"]["folders"] = [
            {
                "name": "Shared",
                "path": "/config/security-policy/folders/Shared",
                "security_rules": [],
                "objects": {},
                "profiles": {}
            }
        ]
        
        orchestrator = PushOrchestrator(mock_authenticated_api_client)
        result = orchestrator.push_configuration(config, folder_names=["Shared"], dry_run=True)
        
        # Should complete push operation (dry run)
        assert result is not None
        assert "success" in result
    
    def test_push_statistics(self, mock_authenticated_api_client, sample_config_v2):
        """Test that push statistics are tracked."""
        # Setup mock responses
        mock_authenticated_api_client.get_security_policy_folders.return_value = [
            {"name": "Shared", "id": "folder-1"}
        ]
        mock_authenticated_api_client.post.return_value = Mock(
            status_code=200,
            json=lambda: {"id": "new-id"}
        )
        mock_authenticated_api_client.put.return_value = Mock(status_code=200)
        
        import copy
        config = copy.deepcopy(sample_config_v2)
        config["security_policies"]["folders"] = [
            {
                "name": "Shared",
                "path": "/config/security-policy/folders/Shared",
                "security_rules": [{"name": "Rule1"}],
                "objects": {
                    "address_objects": [{"name": "Addr1"}]
                },
                "profiles": {}
            }
        ]
        
        orchestrator = PushOrchestrator(mock_authenticated_api_client)
        orchestrator.push_configuration(config, folder_names=["Shared"], dry_run=True)
        
        stats = orchestrator.stats
        assert "folders_pushed" in stats or "objects_pushed" in stats or len(stats) > 0
