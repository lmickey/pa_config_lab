"""
Integration tests for Phase 2: Pull Functionality.

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


class TestFolderCapture:
    """Test folder capture functionality."""
    
    def test_list_folders(self, authenticated_api_client):
        """Test listing folders."""
        from prisma.pull.folder_capture import FolderCapture
        
        folder_capture = FolderCapture(authenticated_api_client)
        folders = folder_capture.list_folders_for_capture(include_defaults=True)
        
        assert isinstance(folders, list)
        assert len(folders) > 0
    
    def test_build_folder_hierarchy(self, authenticated_api_client):
        """Test building folder hierarchy."""
        from prisma.pull.folder_capture import FolderCapture
        
        folder_capture = FolderCapture(authenticated_api_client)
        hierarchy = folder_capture.get_folder_hierarchy()
        
        assert isinstance(hierarchy, dict)
        assert "folders" in hierarchy or len(hierarchy) > 0


class TestRuleCapture:
    """Test rule capture functionality."""
    
    def test_capture_rules_from_folder(self, authenticated_api_client):
        """Test capturing rules from a folder."""
        from prisma.pull.rule_capture import RuleCapture
        
        rule_capture = RuleCapture(authenticated_api_client)
        
        # Get a folder to test with
        folders = authenticated_api_client.get_security_policy_folders()
        if not folders:
            pytest.skip("No folders available")
        
        folder_name = folders[0].get("name", "Shared")
        rules = rule_capture.capture_rules_from_folder(folder_name)
        
        assert isinstance(rules, list)
        # Rules should have required fields
        if rules:
            assert "name" in rules[0] or "id" in rules[0]


class TestObjectCapture:
    """Test object capture functionality."""
    
    def test_capture_addresses(self, authenticated_api_client):
        """Test capturing address objects."""
        from prisma.pull.object_capture import ObjectCapture
        
        object_capture = ObjectCapture(authenticated_api_client)
        
        folders = authenticated_api_client.get_security_policy_folders()
        if not folders:
            pytest.skip("No folders available")
        
        folder_name = folders[0].get("name", "Shared")
        addresses = object_capture.capture_addresses(folder_name)
        
        assert isinstance(addresses, list)
    
    def test_capture_address_groups(self, authenticated_api_client):
        """Test capturing address groups."""
        from prisma.pull.object_capture import ObjectCapture
        
        object_capture = ObjectCapture(authenticated_api_client)
        
        folders = authenticated_api_client.get_security_policy_folders()
        if not folders:
            pytest.skip("No folders available")
        
        folder_name = folders[0].get("name", "Shared")
        groups = object_capture.capture_address_groups(folder_name)
        
        assert isinstance(groups, list)


class TestProfileCapture:
    """Test profile capture functionality."""
    
    def test_capture_authentication_profiles(self, authenticated_api_client):
        """Test capturing authentication profiles."""
        from prisma.pull.profile_capture import ProfileCapture
        
        profile_capture = ProfileCapture(authenticated_api_client)
        
        folders = authenticated_api_client.get_security_policy_folders()
        if not folders:
            pytest.skip("No folders available")
        
        folder_name = folders[0].get("name", "Shared")
        profiles = profile_capture.capture_authentication_profiles(folder_name)
        
        assert isinstance(profiles, list)
    
    def test_capture_security_profiles(self, authenticated_api_client):
        """Test capturing security profiles."""
        from prisma.pull.profile_capture import ProfileCapture
        
        profile_capture = ProfileCapture(authenticated_api_client)
        
        folders = authenticated_api_client.get_security_policy_folders()
        if not folders:
            pytest.skip("No folders available")
        
        folder_name = folders[0].get("name", "Shared")
        profiles = profile_capture.capture_all_security_profiles(folder_name)
        
        assert isinstance(profiles, dict)


class TestSnippetCapture:
    """Test snippet capture functionality."""
    
    def test_discover_snippets(self, authenticated_api_client):
        """Test discovering snippets."""
        from prisma.pull.snippet_capture import SnippetCapture
        
        snippet_capture = SnippetCapture(authenticated_api_client)
        snippets = snippet_capture.discover_snippets()
        
        assert isinstance(snippets, list)


class TestPullOrchestrator:
    """Test pull orchestrator functionality."""
    
    def test_pull_single_folder(self, authenticated_api_client):
        """Test pulling configuration for a single folder."""
        from prisma.pull.pull_orchestrator import PullOrchestrator
        
        orchestrator = PullOrchestrator(authenticated_api_client)
        
        folders = authenticated_api_client.get_security_policy_folders()
        if not folders:
            pytest.skip("No folders available")
        
        folder_name = folders[0].get("name", "Shared")
        folder_config = orchestrator.pull_folder_configuration(folder_name)
        
        assert folder_config is not None
        assert folder_config.get("name") == folder_name
        assert "security_rules" in folder_config
        assert "objects" in folder_config
        assert "profiles" in folder_config
    
    def test_pull_statistics(self, authenticated_api_client):
        """Test that pull statistics are tracked."""
        from prisma.pull.pull_orchestrator import PullOrchestrator
        
        orchestrator = PullOrchestrator(authenticated_api_client)
        
        folders = authenticated_api_client.get_security_policy_folders()
        if not folders:
            pytest.skip("No folders available")
        
        folder_name = folders[0].get("name", "Shared")
        orchestrator.pull_folder_configuration(folder_name)
        
        stats = orchestrator.stats
        assert "folders_captured" in stats
        assert stats["folders_captured"] > 0


class TestConfigPull:
    """Test config pull functionality."""
    
    def test_pull_configuration(self, authenticated_api_client):
        """Test pulling full configuration."""
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
        assert "metadata" in config
        assert "security_policies" in config
        assert len(config["security_policies"]["folders"]) > 0


class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_pull_workflow(self, authenticated_api_client):
        """Test full pull workflow."""
        from prisma.pull.config_pull import pull_configuration
        from config.storage.json_storage import save_config_json
        import tempfile
        
        folders = authenticated_api_client.get_security_policy_folders()
        if not folders:
            pytest.skip("No folders available")
        
        folder_name = folders[0].get("name", "Shared")
        
        # Pull configuration
        config = pull_configuration(
            authenticated_api_client,
            folder_names=[folder_name],
            include_snippets=False
        )
        
        assert config is not None
        
        # Save configuration (unencrypted for tests)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            save_config_json(config, filepath, encrypt=False)
            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
