"""
Integration tests for Phase 3: Default Configuration Detection.

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


class TestDefaultConfigs:
    """Test default configuration database."""
    
    def test_is_default_folder(self):
        """Test folder default detection."""
        from config.defaults.default_configs import DefaultConfigs
        
        assert DefaultConfigs.is_default_folder("Shared") is True
        assert DefaultConfigs.is_default_folder("default") is True
        assert DefaultConfigs.is_default_folder("My Custom Folder") is False
        assert DefaultConfigs.is_default_folder("Service Connections") is True
    
    def test_is_default_snippet(self):
        """Test snippet default detection."""
        from config.defaults.default_configs import DefaultConfigs
        
        assert DefaultConfigs.is_default_snippet("default") is True
        assert DefaultConfigs.is_default_snippet("predefined-snippet") is True
        assert DefaultConfigs.is_default_snippet("my-custom-snippet") is False
    
    def test_is_default_profile_name(self):
        """Test profile default detection."""
        from config.defaults.default_configs import DefaultConfigs
        
        assert DefaultConfigs.is_default_profile_name("default") is True
        assert DefaultConfigs.is_default_profile_name("best-practice") is True
        assert DefaultConfigs.is_default_profile_name("My Custom Profile") is False
    
    def test_is_default_object(self):
        """Test object default detection."""
        from config.defaults.default_configs import DefaultConfigs
        
        assert DefaultConfigs.is_default_object("any") is True
        assert DefaultConfigs.is_default_object("any-tcp") is True
        assert DefaultConfigs.is_default_object("My Custom Object") is False
    
    def test_is_default_rule(self):
        """Test rule default detection."""
        from config.defaults.default_configs import DefaultConfigs
        
        default_rule = {
            'name': 'default-deny',
            'action': 'deny',
            'source': ['any'],
            'destination': ['any'],
            'application': ['any'],
            'service': ['any']
        }
        assert DefaultConfigs.is_default_rule(default_rule) is True
        
        custom_rule = {
            'name': 'Allow Web Traffic',
            'action': 'allow',
            'source': ['10.0.0.0/8'],
            'destination': ['any'],
            'application': ['web-browsing'],
            'service': ['service-https']
        }
        assert DefaultConfigs.is_default_rule(custom_rule) is False


class TestDefaultDetector:
    """Test default detector functionality."""
    
    def test_detector_initialization(self):
        """Test default detector initialization."""
        from config.defaults.default_detector import DefaultDetector
        
        detector = DefaultDetector()
        assert detector is not None
    
    def test_detect_defaults_in_config(self):
        """Test detecting defaults in configuration."""
        from config.defaults.default_detector import DefaultDetector
        from config.schema.config_schema_v2 import create_empty_config_v2
        
        detector = DefaultDetector()
        config = create_empty_config_v2(source_tenant="tsg-test", source_type="scm")
        
        # Add some default items
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
        
        defaults = detector.detect_defaults_in_config(config)
        assert isinstance(defaults, dict)


class TestDefaultFiltering:
    """Test default filtering functionality."""
    
    def test_filter_defaults(self):
        """Test filtering defaults from configuration."""
        from config.defaults.default_detector import DefaultDetector
        from config.schema.config_schema_v2 import create_empty_config_v2
        
        detector = DefaultDetector()
        config = create_empty_config_v2(source_tenant="tsg-test", source_type="scm")
        
        # Add default folder
        config["security_policies"]["folders"] = [
            {
                "name": "Shared",
                "path": "/config/security-policy/folders/Shared",
                "is_default": True,
                "security_rules": [],
                "objects": {},
                "profiles": {}
            }
        ]
        
        filtered = detector.filter_defaults(config)
        # Default folders should be filtered out
        assert len(filtered["security_policies"]["folders"]) == 0


class TestIntegrationWithPull:
    """Test integration with pull functionality."""
    
    def test_pull_with_default_detection(self, authenticated_api_client):
        """Test pulling configuration with default detection."""
        from prisma.pull.config_pull import pull_configuration
        
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
        
        # Check that default detection is applied
        for folder in config.get("security_policies", {}).get("folders", []):
            assert "is_default" in folder
