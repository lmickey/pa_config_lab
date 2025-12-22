"""
Tests for folder and snippet selection functionality.

This module tests the folder filtering, selection dialog, and discovery worker
for the Prisma Access configuration migration feature.
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock

from prisma.pull.folder_capture import (
    FolderCapture,
    filter_folders_for_migration,
    MIGRATION_EXCLUDED_FOLDERS,
    INFRASTRUCTURE_ONLY_FOLDERS,
    NON_PRISMA_ACCESS_FOLDERS,
)


class TestFolderFiltering:
    """Test folder filtering for Prisma Access migration."""
    
    def test_filter_all_folder(self):
        """
        Test that 'all' folder is filtered out.
        
        Given: A list of folders including 'all'
        When: filter_folders_for_migration() is called
        Then: 'all' folder is excluded from results
        """
        folders = [
            {"name": "all", "id": "1", "is_default": True},
            {"name": "Mobile Users", "id": "2", "is_default": False},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Mobile Users"
        
        # Verify 'all' was filtered out
        folder_names = [f["name"] for f in filtered]
        assert "all" not in folder_names
    
    def test_filter_ngfw_shared_folder(self):
        """
        Test that 'ngfw-shared' folder is filtered out.
        
        Given: A list of folders including 'ngfw-shared'
        When: filter_folders_for_migration() is called
        Then: 'ngfw-shared' folder is excluded from results
        """
        folders = [
            {"name": "ngfw-shared", "id": "1", "is_default": True},
            {"name": "Remote Networks", "id": "2", "is_default": False},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Remote Networks"
        
        # Verify 'ngfw-shared' was filtered out
        folder_names = [f["name"] for f in filtered]
        assert "ngfw-shared" not in folder_names
    
    def test_filter_infrastructure_folders(self):
        """
        Test that infrastructure-only folders are filtered out.
        
        Given: Folders including 'Service Connections', 'Colo Connect'
        When: filter_folders_for_migration() is called
        Then: Infrastructure folders are excluded
        """
        folders = [
            {"name": "Service Connections", "id": "1", "is_default": True},
            {"name": "Colo Connect", "id": "2", "is_default": True},
            {"name": "Mobile Users", "id": "3", "is_default": False},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Mobile Users"
        
        # Verify infrastructure folders were filtered out
        folder_names = [f["name"] for f in filtered]
        assert "Service Connections" not in folder_names
        assert "Colo Connect" not in folder_names
    
    def test_filter_case_insensitive(self):
        """
        Test that filtering is case-insensitive.
        
        Given: Folders named 'ALL', 'NGFW-SHARED' (uppercase)
        When: filter_folders_for_migration() is called
        Then: Folders are still filtered out
        """
        folders = [
            {"name": "ALL", "id": "1", "is_default": True},
            {"name": "NGFW-SHARED", "id": "2", "is_default": True},
            {"name": "Mobile Users", "id": "3", "is_default": False},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Mobile Users"
        
        # Verify uppercase versions were filtered out
        folder_names = [f["name"] for f in filtered]
        assert "ALL" not in folder_names
        assert "NGFW-SHARED" not in folder_names
    
    def test_keep_prisma_access_folders(self):
        """
        Test that Prisma Access folders are kept.
        
        Given: PA folders like 'Shared', 'Mobile Users', 'Remote Networks'
        When: filter_folders_for_migration() is called
        Then: All PA folders are included in results
        """
        folders = [
            {"name": "Shared", "id": "1", "is_default": True},
            {"name": "Mobile Users", "id": "2", "is_default": False},
            {"name": "Remote Networks", "id": "3", "is_default": False},
            {"name": "Custom-Folder-1", "id": "4", "is_default": False},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 4
        folder_names = [f["name"] for f in filtered]
        assert "Shared" in folder_names
        assert "Mobile Users" in folder_names
        assert "Remote Networks" in folder_names
        assert "Custom-Folder-1" in folder_names
    
    def test_filter_all_excluded_folders(self):
        """
        Test filtering when all folders should be excluded.
        
        Given: Only excluded folders
        When: filter_folders_for_migration() is called
        Then: Empty list is returned
        """
        folders = [
            {"name": "all", "id": "1", "is_default": True},
            {"name": "ngfw-shared", "id": "2", "is_default": True},
            {"name": "Service Connections", "id": "3", "is_default": True},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 0
    
    def test_filter_empty_list(self):
        """
        Test filtering with empty folder list.
        
        Given: Empty folder list
        When: filter_folders_for_migration() is called
        Then: Empty list is returned
        """
        folders = []
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 0
    
    def test_excluded_folders_constants(self):
        """
        Test that exclusion constants are properly defined.
        
        Verify that the exclusion sets contain expected folders.
        """
        # Check infrastructure-only folders
        assert "Service Connections" in INFRASTRUCTURE_ONLY_FOLDERS
        assert "Colo Connect" in INFRASTRUCTURE_ONLY_FOLDERS
        
        # Check non-PA folders
        assert "all" in NON_PRISMA_ACCESS_FOLDERS
        assert "ngfw-shared" in NON_PRISMA_ACCESS_FOLDERS
        
        # Check combined set
        assert "Service Connections" in MIGRATION_EXCLUDED_FOLDERS
        assert "Colo Connect" in MIGRATION_EXCLUDED_FOLDERS
        assert "all" in MIGRATION_EXCLUDED_FOLDERS
        assert "ngfw-shared" in MIGRATION_EXCLUDED_FOLDERS
        
        # Verify it's the union
        assert len(MIGRATION_EXCLUDED_FOLDERS) == len(INFRASTRUCTURE_ONLY_FOLDERS) + len(NON_PRISMA_ACCESS_FOLDERS)


class TestFolderCaptureDiscoveryForMigration:
    """Test FolderCapture.discover_folders_for_migration() method."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        return Mock()
    
    @pytest.fixture
    def mock_folders(self):
        """Create mock folder data."""
        return [
            {"name": "all", "id": "1", "is_default": True},
            {"name": "ngfw-shared", "id": "2", "is_default": True},
            {"name": "Shared", "id": "3", "is_default": True},
            {"name": "Mobile Users", "id": "4", "is_default": False},
            {"name": "Remote Networks", "id": "5", "is_default": False},
        ]
    
    def test_discover_folders_for_migration_filters_correctly(self, mock_api_client, mock_folders):
        """
        Test that discover_folders_for_migration() filters correctly.
        
        Given: API client with mock folders
        When: discover_folders_for_migration() is called
        Then: Returns filtered folders excluding non-PA folders
        """
        capture = FolderCapture(mock_api_client)
        
        # Mock discover_folders to return test data
        capture.discover_folders = Mock(return_value=mock_folders)
        
        # Call method
        result = capture.discover_folders_for_migration(include_defaults=True)
        
        # Verify filtering
        assert len(result) == 3  # Shared, Mobile Users, Remote Networks
        folder_names = [f["name"] for f in result]
        assert "Shared" in folder_names
        assert "Mobile Users" in folder_names
        assert "Remote Networks" in folder_names
        assert "all" not in folder_names
        assert "ngfw" not in folder_names
    
    def test_discover_folders_for_migration_exclude_defaults(self, mock_api_client, mock_folders):
        """
        Test discover_folders_for_migration() with include_defaults=False.
        
        Given: Folders including defaults
        When: discover_folders_for_migration(include_defaults=False)
        Then: Default folders are excluded
        """
        capture = FolderCapture(mock_api_client)
        capture.discover_folders = Mock(return_value=mock_folders)
        
        # Call with include_defaults=False
        result = capture.discover_folders_for_migration(include_defaults=False)
        
        # Verify only non-default folders are included
        assert len(result) == 2  # Mobile Users, Remote Networks
        folder_names = [f["name"] for f in result]
        assert "Mobile Users" in folder_names
        assert "Remote Networks" in folder_names
        assert "Shared" not in folder_names  # Default folder excluded
    
    def test_discover_folders_for_migration_include_defaults(self, mock_api_client, mock_folders):
        """
        Test discover_folders_for_migration() with include_defaults=True.
        
        Given: Folders including defaults
        When: discover_folders_for_migration(include_defaults=True)
        Then: Default folders are included
        """
        capture = FolderCapture(mock_api_client)
        capture.discover_folders = Mock(return_value=mock_folders)
        
        # Call with include_defaults=True
        result = capture.discover_folders_for_migration(include_defaults=True)
        
        # Verify default folders are included
        assert len(result) == 3  # Shared, Mobile Users, Remote Networks
        folder_names = [f["name"] for f in result]
        assert "Shared" in folder_names  # Default folder included
        assert "Mobile Users" in folder_names
        assert "Remote Networks" in folder_names


class TestListFoldersForCapture:
    """Test list_folders_for_capture() method."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        return Mock()
    
    def test_list_folders_for_capture_uses_migration_filtering(self, mock_api_client):
        """
        Test that list_folders_for_capture() uses migration filtering.
        
        Given: FolderCapture instance
        When: list_folders_for_capture() is called
        Then: Uses discover_folders_for_migration() internally
        """
        capture = FolderCapture(mock_api_client)
        
        # Mock discover_folders_for_migration
        mock_folders = [
            {"name": "Mobile Users", "id": "1", "is_default": False},
            {"name": "Remote Networks", "id": "2", "is_default": False},
        ]
        capture.discover_folders_for_migration = Mock(return_value=mock_folders)
        
        # Call method
        result = capture.list_folders_for_capture(include_defaults=False)
        
        # Verify it called discover_folders_for_migration
        capture.discover_folders_for_migration.assert_called_once_with(include_defaults=False)
        
        # Verify result is list of names
        assert result == ["Mobile Users", "Remote Networks"]
    
    def test_list_folders_for_capture_returns_names_only(self, mock_api_client):
        """
        Test that list_folders_for_capture() returns only folder names.
        
        Given: FolderCapture with mock folders
        When: list_folders_for_capture() is called
        Then: Returns list of folder names (strings)
        """
        capture = FolderCapture(mock_api_client)
        
        mock_folders = [
            {"name": "Folder1", "id": "1", "is_default": False},
            {"name": "Folder2", "id": "2", "is_default": False},
        ]
        capture.discover_folders_for_migration = Mock(return_value=mock_folders)
        
        result = capture.list_folders_for_capture()
        
        # Verify result is list of strings
        assert isinstance(result, list)
        assert all(isinstance(name, str) for name in result)
        assert result == ["Folder1", "Folder2"]


class TestSnippetDiscoveryWithFolders:
    """Test snippet discovery with folder associations."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        return Mock()
    
    def test_discover_snippets_with_folders_extracts_names(self, mock_api_client):
        """
        Test that discover_snippets_with_folders() extracts folder names.
        
        Given: Snippets with folder associations (dict format)
        When: discover_snippets_with_folders() is called
        Then: Snippets include folder_names field with extracted names
        """
        from prisma.pull.snippet_capture import SnippetCapture
        
        capture = SnippetCapture(mock_api_client)
        
        # Mock discover_snippets to return test data
        mock_snippets = [
            {
                "name": "snippet-1",
                "id": "s1",
                "folders": [
                    {"id": "f1", "name": "Mobile Users"}
                ],
            },
            {
                "name": "snippet-2",
                "id": "s2",
                "folders": [
                    {"id": "f2", "name": "Shared"},
                    {"id": "f3", "name": "Mobile Users"}
                ],
            },
        ]
        capture.discover_snippets = Mock(return_value=mock_snippets)
        
        # Call method
        result = capture.discover_snippets_with_folders()
        
        # Verify folder_names were extracted
        assert len(result) == 2
        assert result[0]["folder_names"] == ["Mobile Users"]
        assert result[1]["folder_names"] == ["Shared", "Mobile Users"]
    
    def test_discover_snippets_with_folders_handles_string_folders(self, mock_api_client):
        """
        Test that discover_snippets_with_folders() handles string folder names.
        
        Given: Snippets with folder names as strings (not dicts)
        When: discover_snippets_with_folders() is called
        Then: String folder names are preserved
        """
        from prisma.pull.snippet_capture import SnippetCapture
        
        capture = SnippetCapture(mock_api_client)
        
        mock_snippets = [
            {
                "name": "snippet-1",
                "id": "s1",
                "folders": ["Mobile Users", "Shared"],
            },
        ]
        capture.discover_snippets = Mock(return_value=mock_snippets)
        
        result = capture.discover_snippets_with_folders()
        
        assert result[0]["folder_names"] == ["Mobile Users", "Shared"]
    
    def test_discover_snippets_with_folders_handles_no_folders(self, mock_api_client):
        """
        Test that discover_snippets_with_folders() handles snippets with no folders.
        
        Given: Snippets with empty or missing folders field
        When: discover_snippets_with_folders() is called
        Then: folder_names is empty list
        """
        from prisma.pull.snippet_capture import SnippetCapture
        
        capture = SnippetCapture(mock_api_client)
        
        mock_snippets = [
            {"name": "snippet-1", "id": "s1", "folders": []},
            {"name": "snippet-2", "id": "s2"},  # No folders field
        ]
        capture.discover_snippets = Mock(return_value=mock_snippets)
        
        result = capture.discover_snippets_with_folders()
        
        assert result[0]["folder_names"] == []
        assert result[1]["folder_names"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
