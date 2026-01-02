"""
Tests for config.models.base module.

Tests the base ConfigItem class and specialized base classes.
"""

import pytest
from config.models.base import ConfigItem, ObjectItem, PolicyItem, ProfileItem, RuleItem
from tests.examples.loader import Examples, load_object_example, load_policy_example


class MockAddressObject(ObjectItem):
    """Mock implementation of AddressObject for testing"""
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/addresses"
    item_type = "address_object"


class MockSecurityRule(RuleItem):
    """Mock implementation of SecurityRule for testing"""
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/security-rules"
    item_type = "security_rule"


class TestConfigItem:
    """Tests for ConfigItem base class"""
    
    def test_create_with_folder(self):
        """Test creating item with folder"""
        raw_config = {
            'name': 'test-address',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.1.0/24'
        }
        
        item = MockAddressObject(raw_config)
        
        assert item.name == 'test-address'
        assert item.folder == 'Mobile Users'
        assert item.snippet is None
        assert item.get_location() == 'Mobile Users'
        assert item.is_in_folder()
        assert not item.is_in_snippet()
    
    def test_create_with_snippet(self):
        """Test creating item with snippet"""
        raw_config = {
            'name': 'test-address',
            'snippet': 'test-snippet',
            'ip_netmask': '10.0.0.0/8'
        }
        
        item = MockAddressObject(raw_config)
        
        assert item.name == 'test-address'
        assert item.folder is None
        assert item.snippet == 'test-snippet'
        assert item.get_location() == 'test-snippet'
        assert not item.is_in_folder()
        assert item.is_in_snippet()
    
    def test_create_without_location_raises_error(self):
        """Test that creating item without folder/snippet raises error"""
        raw_config = {
            'name': 'test-address',
            'ip_netmask': '192.168.1.0/24'
        }
        
        with pytest.raises(ValueError, match="Either folder or snippet must be set"):
            MockAddressObject(raw_config)
    
    def test_create_with_both_locations_raises_error(self):
        """Test that creating item with both folder and snippet raises error"""
        raw_config = {
            'name': 'test-address',
            'folder': 'Mobile Users',
            'snippet': 'test-snippet',
            'ip_netmask': '192.168.1.0/24'
        }
        
        with pytest.raises(ValueError, match="Cannot set both folder and snippet"):
            MockAddressObject(raw_config)
    
    def test_has_dependencies_property(self):
        """Test has_dependencies property"""
        # Item without dependencies
        raw_config = {
            'name': 'simple-address',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.1.0/24'
        }
        item = MockAddressObject(raw_config)
        assert not item.has_dependencies
        
        # Rule with dependencies
        rule_config = {
            'name': 'test-rule',
            'folder': 'Mobile Users',
            'source': ['internal-network'],
            'destination': ['any'],
            'service': ['tcp-443']
        }
        rule = MockSecurityRule(rule_config)
        assert rule.has_dependencies
    
    def test_rename(self):
        """Test renaming an item"""
        raw_config = {
            'name': 'old-name',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.1.0/24'
        }
        
        item = MockAddressObject(raw_config)
        assert item.name == 'old-name'
        
        item.rename('new-name')
        
        assert item.name == 'new-name'
        assert item.raw_config['name'] == 'new-name'
    
    def test_mark_for_deletion(self):
        """Test marking item for deletion"""
        raw_config = {
            'name': 'test-address',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.1.0/24'
        }
        
        item = MockAddressObject(raw_config)
        assert not item.deleted
        assert item.delete_success is None
        
        item.mark_for_deletion()
        
        assert item.deleted
        assert item.delete_success is None  # Not attempted yet
    
    def test_unmark_for_deletion(self):
        """Test unmarking item for deletion"""
        raw_config = {
            'name': 'test-address',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.1.0/24'
        }
        
        item = MockAddressObject(raw_config)
        item.mark_for_deletion()
        item.delete_success = False
        
        item.unmark_for_deletion()
        
        assert not item.deleted
        assert item.delete_success is None
    
    def test_to_dict_serialization(self):
        """Test serialization to dictionary"""
        raw_config = {
            'name': 'test-address',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.1.0/24',
            'id': 'abc123'  # Should be removed
        }
        
        item = MockAddressObject(raw_config)
        item.push_strategy = 'overwrite'
        
        data = item.to_dict()
        
        assert data['name'] == 'test-address'
        assert data['folder'] == 'Mobile Users'
        assert data['push_strategy'] == 'overwrite'
        assert data['is_default'] == False
        assert data['deleted'] == False
        assert 'id' not in data  # ID should be removed
    
    def test_from_dict_deserialization(self):
        """Test deserialization from dictionary"""
        data = {
            'name': 'test-address',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.1.0/24',
            'push_strategy': 'rename',
            'deleted': True,
            'delete_success': True
        }
        
        item = MockAddressObject.from_dict(data)
        
        assert item.name == 'test-address'
        assert item.folder == 'Mobile Users'
        assert item.push_strategy == 'rename'
        assert item.deleted == True
        assert item.delete_success == True
    
    def test_validate(self):
        """Test validation"""
        # Valid item
        raw_config = {
            'name': 'test-address',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.1.0/24'
        }
        item = MockAddressObject(raw_config)
        errors = item.validate()
        assert len(errors) == 0
        
        # Invalid item (no name)
        raw_config = {
            'name': '',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.1.0/24'
        }
        item = MockAddressObject(raw_config)
        item.name = ''  # Force empty name
        errors = item.validate()
        assert len(errors) > 0
        assert any('Name is required' in error for error in errors)


class TestRuleItem:
    """Tests for RuleItem base class"""
    
    def test_is_enabled_property(self):
        """Test is_enabled property"""
        # Enabled rule (no disabled field)
        rule_config = {
            'name': 'test-rule',
            'folder': 'Mobile Users',
            'action': 'allow'
        }
        rule = MockSecurityRule(rule_config)
        assert rule.is_enabled
        
        # Disabled rule
        rule_config = {
            'name': 'disabled-rule',
            'folder': 'Mobile Users',
            'action': 'allow',
            'disabled': True
        }
        rule = MockSecurityRule(rule_config)
        assert not rule.is_enabled
        
        # Explicitly enabled rule
        rule_config = {
            'name': 'enabled-rule',
            'folder': 'Mobile Users',
            'action': 'allow',
            'disabled': False
        }
        rule = MockSecurityRule(rule_config)
        assert rule.is_enabled


class TestExampleLoader:
    """Tests using example configurations from tests/examples/"""
    
    def test_load_address_example(self):
        """Test loading address object from examples"""
        config = Examples.address_minimal()
        
        # Should be able to create object from example
        item = MockAddressObject(config)
        
        assert item.name == 'internal-network'
        assert item.folder == 'Mobile Users'
        assert item.raw_config['ip_netmask'] == '192.168.1.0/24'
    
    def test_load_security_rule_example(self):
        """Test loading security rule from examples"""
        config = Examples.security_rule_full()
        
        # Should be able to create rule from example
        rule = MockSecurityRule(config)
        
        assert rule.name == 'allow-internal-apps'
        assert rule.folder == 'Mobile Users'
        assert rule.position == 5
        assert rule.is_enabled
        assert rule.has_dependencies  # Has source, destination, service, application
    
    def test_load_snippet_based_example(self):
        """Test loading snippet-based configuration"""
        config = Examples.address_snippet()
        
        item = MockAddressObject(config)
        
        assert item.name == 'web-servers'
        assert item.snippet == 'production-snippet'
        assert item.folder is None
        assert item.is_in_snippet()
        assert not item.is_in_folder()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
