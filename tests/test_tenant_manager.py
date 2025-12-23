"""
Unit tests for TenantManager.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from config.tenant_manager import TenantManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def manager(temp_dir):
    """Create a TenantManager instance for testing."""
    return TenantManager(base_dir=temp_dir)


class TestTenantManagerBasics:
    """Test basic tenant manager operations."""
    
    def test_initialization(self, temp_dir):
        """Test manager initialization creates directory."""
        manager = TenantManager(base_dir=temp_dir)
        assert Path(temp_dir).exists()
        assert manager.tenants_file.parent.exists()
    
    def test_empty_list(self, manager):
        """Test listing tenants when none exist."""
        tenants = manager.list_tenants()
        assert tenants == []
    
    def test_add_tenant(self, manager):
        """Test adding a new tenant."""
        success, message, tenant_id = manager.add_tenant(
            name="Test Tenant",
            tsg_id="1234567890",
            client_id="sa-test@iam.panserviceaccount.com",
            client_secret="test-secret-123",
            description="Test description",
            validate=False  # Skip validation in tests
        )
        
        assert success is True
        assert "added successfully" in message.lower()
        assert tenant_id is not None
    
    def test_add_tenant_validation(self, manager):
        """Test tenant validation on add."""
        # Empty name
        success, message, _ = manager.add_tenant("", "123", "client@test.com", "secret", validate=False)
        assert success is False
        assert "name is required" in message.lower()
        
        # Empty TSG
        success, message, _ = manager.add_tenant("Test", "", "client@test.com", "secret", validate=False)
        assert success is False
        assert "tsg" in message.lower()
        
        # Empty client ID
        success, message, _ = manager.add_tenant("Test", "123", "", "secret", validate=False)
        assert success is False
        assert "client" in message.lower()
        
        # Empty client secret
        success, message, _ = manager.add_tenant("Test", "123", "client@test.com", "", validate=False)
        assert success is False
        assert "secret is required" in message.lower()


class TestTenantCRUD:
    """Test CRUD operations."""
    
    def test_add_and_get(self, manager):
        """Test adding and retrieving a tenant."""
        success, _, tenant_id = manager.add_tenant(
            "Production",
            "1234567890",
            "sa-prod@iam.panserviceaccount.com",
            "prod-secret-123",
            "Production environment",
            validate=False
        )
        
        assert success is True
        
        tenant = manager.get_tenant(tenant_id)
        assert tenant is not None
        assert tenant["name"] == "Production"
        assert tenant["tsg_id"] == "1234567890"
        assert tenant["client_id"] == "sa-prod@iam.panserviceaccount.com"
        assert tenant["client_secret"] == "prod-secret-123"
        assert tenant["description"] == "Production environment"
        assert tenant["id"] == tenant_id
        assert "created" in tenant
        assert tenant["last_used"] is None
    
    def test_update_tenant(self, manager):
        """Test updating a tenant."""
        # Add tenant
        _, _, tenant_id = manager.add_tenant("Test", "123", "client@test.com", "secret", validate=False)
        
        # Update
        success, message = manager.update_tenant(
            tenant_id,
            name="Updated Test",
            description="New description",
            validate=False
        )
        
        assert success is True
        assert "updated successfully" in message.lower()
        
        # Verify
        tenant = manager.get_tenant(tenant_id)
        assert tenant["name"] == "Updated Test"
        assert tenant["description"] == "New description"
        assert tenant["tsg_id"] == "123"  # Unchanged
        assert tenant["client_secret"] == "secret"  # Unchanged
    
    def test_delete_tenant(self, manager):
        """Test deleting a tenant."""
        # Add tenant
        _, _, tenant_id = manager.add_tenant("Test", "123", "client@test.com", "secret", validate=False)
        
        # Verify exists
        assert manager.get_tenant(tenant_id) is not None
        
        # Delete
        success, message = manager.delete_tenant(tenant_id)
        assert success is True
        assert "deleted successfully" in message.lower()
        
        # Verify gone
        assert manager.get_tenant(tenant_id) is None
    
    def test_delete_nonexistent(self, manager):
        """Test deleting a non-existent tenant."""
        success, message = manager.delete_tenant("fake-id")
        assert success is False
        assert "not found" in message.lower()


class TestTenantList:
    """Test listing and searching tenants."""
    
    def test_list_multiple(self, manager):
        """Test listing multiple tenants."""
        # Add tenants
        manager.add_tenant("Zebra", "111", "zebra@test.com", "secret1", validate=False)
        manager.add_tenant("Alpha", "222", "alpha@test.com", "secret2", validate=False)
        manager.add_tenant("Beta", "333", "beta@test.com", "secret3", validate=False)
        
        # List (should be sorted by name)
        tenants = manager.list_tenants(sort_by="name")
        assert len(tenants) == 3
        assert tenants[0]["name"] == "Alpha"
        assert tenants[1]["name"] == "Beta"
        assert tenants[2]["name"] == "Zebra"
    
    def test_search_tenants(self, manager):
        """Test searching tenants."""
        # Add tenants
        manager.add_tenant("Production", "1234567890", "prod@test.com", "secret1", "Prod env", validate=False)
        manager.add_tenant("Development", "9876543210", "dev@test.com", "secret2", "Dev env", validate=False)
        manager.add_tenant("Testing", "5555555555", "test@test.com", "secret3", "Test env", validate=False)
        
        # Search by name
        results = manager.search_tenants("prod")
        assert len(results) == 1
        assert results[0]["name"] == "Production"
        
        # Search by TSG
        results = manager.search_tenants("9876")
        assert len(results) == 1
        assert results[0]["name"] == "Development"
        
        # Search by description
        results = manager.search_tenants("test env")
        assert len(results) == 1
        assert results[0]["name"] == "Testing"
        
        # Search returns all if empty
        results = manager.search_tenants("")
        assert len(results) == 3
    
    def test_get_by_name(self, manager):
        """Test getting tenant by name."""
        manager.add_tenant("Production", "123", "prod@test.com", "secret", validate=False)
        
        tenant = manager.get_tenant_by_name("Production")
        assert tenant is not None
        assert tenant["name"] == "Production"
        
        # Case insensitive
        tenant = manager.get_tenant_by_name("production")
        assert tenant is not None
        
        # Not found
        tenant = manager.get_tenant_by_name("NonExistent")
        assert tenant is None


class TestTenantDuplicates:
    """Test duplicate handling."""
    
    def test_duplicate_name(self, manager):
        """Test that duplicate names are rejected."""
        manager.add_tenant("Test", "123", "client1@test.com", "secret1", validate=False)
        
        success, message, _ = manager.add_tenant("Test", "456", "client2@test.com", "secret2", validate=False)
        assert success is False
        assert "already exists" in message.lower()
    
    def test_duplicate_name_case_insensitive(self, manager):
        """Test that duplicate names are case-insensitive."""
        manager.add_tenant("Test", "123", "client1@test.com", "secret1", validate=False)
        
        success, message, _ = manager.add_tenant("TEST", "456", "client2@test.com", "secret2", validate=False)
        assert success is False
        assert "already exists" in message.lower()
    
    def test_update_to_duplicate_name(self, manager):
        """Test that updating to duplicate name is rejected."""
        _, _, id1 = manager.add_tenant("Test1", "123", "client1@test.com", "secret1", validate=False)
        _, _, id2 = manager.add_tenant("Test2", "456", "client2@test.com", "secret2", validate=False)
        
        success, message = manager.update_tenant(id2, name="Test1")
        assert success is False
        assert "already exists" in message.lower()


class TestTenantUsage:
    """Test usage tracking."""
    
    def test_mark_used(self, manager):
        """Test marking tenant as used."""
        _, _, tenant_id = manager.add_tenant("Test", "123", "client@test.com", "secret", validate=False)
        
        # Initially not used
        tenant = manager.get_tenant(tenant_id)
        assert tenant["last_used"] is None
        
        # Mark as used
        success = manager.mark_used(tenant_id)
        assert success is True
        
        # Verify timestamp
        tenant = manager.get_tenant(tenant_id)
        assert tenant["last_used"] is not None
    
    def test_sort_by_last_used(self, manager):
        """Test sorting by last used."""
        import time
        
        _, _, id1 = manager.add_tenant("First", "111", "first@test.com", "secret1", validate=False)
        time.sleep(0.1)
        _, _, id2 = manager.add_tenant("Second", "222", "second@test.com", "secret2", validate=False)
        
        # Mark first as used
        manager.mark_used(id1)
        time.sleep(0.1)
        # Mark second as used
        manager.mark_used(id2)
        
        # Sort by last used
        tenants = manager.list_tenants(sort_by="last_used")
        assert tenants[0]["name"] == "Second"  # Most recent
        assert tenants[1]["name"] == "First"


class TestTenantPersistence:
    """Test data persistence."""
    
    def test_persistence(self, temp_dir):
        """Test that tenants persist across manager instances."""
        # Create manager and add tenant
        manager1 = TenantManager(base_dir=temp_dir)
        _, _, tenant_id = manager1.add_tenant("Test", "123", "client@test.com", "secret", validate=False)
        
        # Create new manager instance
        manager2 = TenantManager(base_dir=temp_dir)
        
        # Verify tenant exists
        tenant = manager2.get_tenant(tenant_id)
        assert tenant is not None
        assert tenant["name"] == "Test"
    
    def test_encryption(self, temp_dir):
        """Test that file is encrypted."""
        manager = TenantManager(base_dir=temp_dir)
        manager.add_tenant("Test", "123", "client@test.com", "secret", validate=False)
        
        # Read raw file
        tenants_file = Path(temp_dir) / "tenants.json"
        with open(tenants_file, 'rb') as f:
            raw_data = f.read()
        
        # Should not contain plaintext
        assert b"Test" not in raw_data
        assert b"123" not in raw_data


class TestTenantImportExport:
    """Test import/export functionality."""
    
    def test_export(self, manager, temp_dir):
        """Test exporting tenants."""
        # Add tenants
        manager.add_tenant("Test1", "111", "client1@test.com", "secret1", validate=False)
        manager.add_tenant("Test2", "222", "client2@test.com", "secret2", validate=False)
        
        # Export
        export_file = Path(temp_dir) / "export.json"
        success, message = manager.export_tenants(str(export_file))
        
        assert success is True
        assert export_file.exists()
        
        # Verify file is valid JSON
        import json
        with open(export_file) as f:
            data = json.load(f)
        
        assert "tenants" in data
        assert len(data["tenants"]) == 2
    
    def test_import_merge(self, temp_dir):
        """Test importing tenants with merge."""
        # Create manager with existing tenant
        manager = TenantManager(base_dir=temp_dir)
        manager.add_tenant("Existing", "999", "existing@test.com", "secret", validate=False)
        
        # Create import file
        import json
        import_file = Path(temp_dir) / "import.json"
        import_data = {
            "version": "1.0",
            "tenants": [
                {
                    "id": "import-1",
                    "name": "Imported1",
                    "tsg_id": "111",
                    "client_id": "import1@test.com",
                    "description": "",
                    "created": "2024-01-01T00:00:00",
                    "last_used": None
                },
                {
                    "id": "import-2",
                    "name": "Existing",  # Duplicate
                    "tsg_id": "222",
                    "client_id": "dupe@test.com",
                    "description": "",
                    "created": "2024-01-01T00:00:00",
                    "last_used": None
                }
            ]
        }
        with open(import_file, 'w') as f:
            json.dump(import_data, f)
        
        # Import with merge
        success, message = manager.import_tenants(str(import_file), merge=True)
        
        assert success is True
        assert "1 tenant" in message  # 1 added
        assert "1 duplicate" in message  # 1 skipped
        
        # Verify
        tenants = manager.list_tenants()
        assert len(tenants) == 2  # Original + 1 imported
        names = {t["name"] for t in tenants}
        assert "Existing" in names
        assert "Imported1" in names
    
    def test_import_replace(self, temp_dir):
        """Test importing tenants with replace."""
        # Create manager with existing tenant
        manager = TenantManager(base_dir=temp_dir)
        manager.add_tenant("Existing", "999", "existing@test.com", "secret", validate=False)
        
        # Create import file
        import json
        import_file = Path(temp_dir) / "import.json"
        import_data = {
            "version": "1.0",
            "tenants": [
                {
                    "id": "import-1",
                    "name": "Imported",
                    "tsg_id": "111",
                    "client_id": "import@test.com",
                    "description": "",
                    "created": "2024-01-01T00:00:00",
                    "last_used": None
                }
            ]
        }
        with open(import_file, 'w') as f:
            json.dump(import_data, f)
        
        # Import with replace
        success, message = manager.import_tenants(str(import_file), merge=False)
        
        assert success is True
        
        # Verify - should only have imported tenant
        tenants = manager.list_tenants()
        assert len(tenants) == 1
        assert tenants[0]["name"] == "Imported"
