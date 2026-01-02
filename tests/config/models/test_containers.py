"""
Tests for config.models.containers module.

Tests all container classes: FolderConfig, SnippetConfig, InfrastructureConfig, Configuration
"""

import pytest
from config.models.containers import FolderConfig, SnippetConfig, InfrastructureConfig, Configuration
from config.models.objects import AddressObject, Tag
from config.models.policies import SecurityRule
from config.models.profiles import ProfileGroup
from config.models.infrastructure import (
    IKECryptoProfile,
    IPsecCryptoProfile,
    IKEGateway,
    IPsecTunnel,
    ServiceConnection,
    AgentProfile,
    Portal,
    Gateway,
)
from tests.examples.loader import Examples


class TestFolderConfig:
    """Tests for FolderConfig class"""
    
    def test_create_folder(self):
        """Test creating a folder"""
        folder = FolderConfig("Mobile Users")
        
        assert folder.name == "Mobile Users"
        assert folder.parent is None
        assert len(folder) == 0
    
    def test_create_folder_with_parent(self):
        """Test creating a folder with parent"""
        folder = FolderConfig("Service Connections", parent="Remote Networks")
        
        assert folder.name == "Service Connections"
        assert folder.parent == "Remote Networks"
    
    def test_add_item_to_folder(self):
        """Test adding an item to a folder"""
        folder = FolderConfig("Mobile Users")
        addr = AddressObject({
            'name': 'test-address',
            'folder': 'Mobile Users',
            'value': '10.0.0.0/8',
            'type': 'ip-netmask'
        })
        
        folder.add_item(addr)
        
        assert len(folder) == 1
        assert addr in folder.items
    
    def test_add_item_wrong_folder(self):
        """Test adding an item with wrong folder raises error"""
        folder = FolderConfig("Mobile Users")
        addr = AddressObject({
            'name': 'test-address',
            'folder': 'Remote Networks',  # Wrong folder!
            'value': '10.0.0.0/8',
            'type': 'ip-netmask'
        })
        
        with pytest.raises(ValueError, match="does not match folder name"):
            folder.add_item(addr)
    
    def test_remove_item_from_folder(self):
        """Test removing an item from a folder"""
        folder = FolderConfig("Mobile Users")
        addr = AddressObject({
            'name': 'test-address',
            'folder': 'Mobile Users',
            'value': '10.0.0.0/8',
            'type': 'ip-netmask'
        })
        
        folder.add_item(addr)
        assert len(folder) == 1
        
        folder.remove_item(addr)
        assert len(folder) == 0
    
    def test_get_item_by_name(self):
        """Test getting an item by name"""
        folder = FolderConfig("Mobile Users")
        addr = AddressObject({
            'name': 'test-address',
            'folder': 'Mobile Users',
            'value': '10.0.0.0/8',
            'type': 'ip-netmask'
        })
        folder.add_item(addr)
        
        found = folder.get_item('test-address')
        
        assert found == addr
    
    def test_get_item_by_name_and_type(self):
        """Test getting an item by name and type"""
        folder = FolderConfig("Mobile Users")
        addr = AddressObject({
            'name': 'test',
            'folder': 'Mobile Users',
            'value': '10.0.0.0/8',
            'type': 'ip-netmask'
        })
        folder.add_item(addr)
        
        # Should find with correct type
        found = folder.get_item('test', 'address_object')
        assert found == addr
        
        # Should not find with wrong type
        not_found = folder.get_item('test', 'security_rule')
        assert not_found is None
    
    def test_get_items_by_type(self):
        """Test getting all items of a specific type"""
        folder = FolderConfig("Mobile Users")
        
        addr1 = AddressObject({'name': 'addr1', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        addr2 = AddressObject({'name': 'addr2', 'folder': 'Mobile Users', 'value': '10.0.0.2', 'type': 'ip-netmask'})
        rule = SecurityRule({'name': 'rule1', 'folder': 'Mobile Users', 'from': ['any'], 'to': ['any'], 'action': 'allow'})
        
        folder.add_item(addr1)
        folder.add_item(addr2)
        folder.add_item(rule)
        
        addresses = folder.get_items_by_type('address_object')
        assert len(addresses) == 2
        
        rules = folder.get_items_by_type('security_rule')
        assert len(rules) == 1
    
    def test_filter_defaults(self):
        """Test filtering out default items"""
        folder = FolderConfig("Mobile Users")
        
        addr1 = AddressObject({'name': 'custom', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        addr2 = AddressObject({'name': 'default', 'folder': 'Mobile Users', 'value': '10.0.0.2', 'type': 'ip-netmask', 'is_default': True})
        
        folder.add_item(addr1)
        folder.add_item(addr2)
        
        non_defaults = folder.filter_defaults()
        
        assert len(non_defaults) == 1
        assert non_defaults[0].name == 'custom'
    
    def test_filter_enabled(self):
        """Test filtering for enabled items"""
        folder = FolderConfig("Mobile Users")
        
        rule1 = SecurityRule({'name': 'enabled-rule', 'folder': 'Mobile Users', 'from': ['any'], 'to': ['any'], 'action': 'allow'})
        rule2 = SecurityRule({'name': 'disabled-rule', 'folder': 'Mobile Users', 'from': ['any'], 'to': ['any'], 'action': 'allow', 'disabled': True})
        addr = AddressObject({'name': 'addr', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        
        folder.add_item(rule1)
        folder.add_item(rule2)
        folder.add_item(addr)
        
        enabled = folder.filter_enabled()
        
        # Should include enabled rule and address (non-rules always considered enabled)
        assert len(enabled) == 2
        assert rule1 in enabled
        assert addr in enabled
        assert rule2 not in enabled
    
    def test_mark_all_for_deletion(self):
        """Test marking all items for deletion"""
        folder = FolderConfig("Mobile Users")
        
        addr = AddressObject({'name': 'addr', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        rule = SecurityRule({'name': 'rule', 'folder': 'Mobile Users', 'from': ['any'], 'to': ['any'], 'action': 'allow'})
        
        folder.add_item(addr)
        folder.add_item(rule)
        
        folder.mark_all_for_deletion()
        
        assert addr.deleted
        assert rule.deleted
    
    def test_validate_all(self):
        """Test validating all items in folder"""
        folder = FolderConfig("Mobile Users")
        
        # Valid item
        addr = AddressObject({'name': 'valid', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        
        # Invalid item (missing required fields)
        rule = SecurityRule({'name': 'invalid', 'folder': 'Mobile Users', 'from': ['any'], 'to': ['any']})  # Missing action
        
        folder.add_item(addr)
        folder.add_item(rule)
        
        errors = folder.validate_all()
        
        # Should have errors for invalid rule
        assert 'invalid' in errors
        assert len(errors['invalid']) > 0


class TestSnippetConfig:
    """Tests for SnippetConfig class"""
    
    def test_create_snippet(self):
        """Test creating a snippet"""
        snippet = SnippetConfig("production-snippet")
        
        assert snippet.name == "production-snippet"
        assert snippet.snippet_type is None
        assert len(snippet) == 0
    
    def test_create_snippet_with_type(self):
        """Test creating a snippet with type"""
        snippet = SnippetConfig("default", snippet_type="predefined")
        
        assert snippet.name == "default"
        assert snippet.snippet_type == "predefined"
    
    def test_add_item_to_snippet(self):
        """Test adding an item to a snippet"""
        snippet = SnippetConfig("production-snippet")
        tag = Tag({
            'name': 'production',
            'snippet': 'production-snippet',
            'color': 'Red'
        })
        
        snippet.add_item(tag)
        
        assert len(snippet) == 1
        assert tag in snippet.items
    
    def test_add_item_wrong_snippet(self):
        """Test adding an item with wrong snippet raises error"""
        snippet = SnippetConfig("production-snippet")
        tag = Tag({
            'name': 'test',
            'snippet': 'other-snippet',  # Wrong snippet!
            'color': 'Red'
        })
        
        with pytest.raises(ValueError, match="does not match snippet name"):
            snippet.add_item(tag)
    
    def test_snippet_operations(self):
        """Test various snippet operations"""
        snippet = SnippetConfig("test-snippet")
        
        tag = Tag({'name': 'tag1', 'snippet': 'test-snippet', 'color': 'Red'})
        addr = AddressObject({'name': 'addr1', 'snippet': 'test-snippet', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        
        snippet.add_item(tag)
        snippet.add_item(addr)
        
        # Test get all items
        all_items = snippet.get_all_items()
        assert len(all_items) == 2
        
        # Test get by type
        tags = snippet.get_items_by_type('tag')
        assert len(tags) == 1
        
        # Test remove
        snippet.remove_item(tag)
        assert len(snippet) == 1


class TestInfrastructureConfig:
    """Tests for InfrastructureConfig class"""
    
    def test_create_infrastructure_config(self):
        """Test creating infrastructure config"""
        infra = InfrastructureConfig()
        
        assert len(infra) == 0
    
    def test_add_remote_network_item(self):
        """Test adding Remote Networks item"""
        infra = InfrastructureConfig()
        
        ike_crypto = IKECryptoProfile({
            'name': 'test-ike-crypto',
            'folder': 'Remote Networks',
            'encryption': ['aes-256-cbc'],
            'authentication': ['sha256'],
            'dh_group': ['group14']
        })
        
        infra.add_item(ike_crypto)
        
        assert len(infra) == 1
        assert ike_crypto in infra.items
    
    def test_add_mobile_user_item(self):
        """Test adding Mobile Users item"""
        infra = InfrastructureConfig()
        
        agent = AgentProfile({
            'name': 'default-agent',
            'folder': 'Mobile Users',
            'connect_method': 'on-demand'
        })
        
        infra.add_item(agent)
        
        assert len(infra) == 1
        assert agent in infra.items
    
    def test_add_item_without_folder_raises_error(self):
        """Test that adding item without folder raises error"""
        infra = InfrastructureConfig()
        
        # Try to create infrastructure item without folder (should fail in __init__)
        with pytest.raises(ValueError, match="Infrastructure items must have folder"):
            IKECryptoProfile({
                'name': 'test',
                'snippet': 'test-snippet',  # Infrastructure can't use snippet!
                'encryption': ['aes-256-cbc'],
                'authentication': ['sha256'],
                'dh_group': ['group14']
            })
    
    def test_add_non_infrastructure_item_raises_error(self):
        """Test that adding non-infrastructure item raises error"""
        infra = InfrastructureConfig()
        
        addr = AddressObject({
            'name': 'test',
            'folder': 'Mobile Users',
            'value': '10.0.0.1',
            'type': 'ip-netmask'
        })
        
        with pytest.raises(ValueError, match="is not an infrastructure type"):
            infra.add_item(addr)
    
    def test_get_remote_network_items(self):
        """Test getting Remote Networks items"""
        infra = InfrastructureConfig()
        
        ike_crypto = IKECryptoProfile({
            'name': 'ike-crypto',
            'folder': 'Remote Networks',
            'encryption': ['aes-256-cbc'],
            'authentication': ['sha256'],
            'dh_group': ['group14']
        })
        
        agent = AgentProfile({
            'name': 'agent',
            'folder': 'Mobile Users',
            'connect_method': 'on-demand'
        })
        
        infra.add_item(ike_crypto)
        infra.add_item(agent)
        
        rn_items = infra.get_remote_network_items()
        
        assert len(rn_items) == 1
        assert ike_crypto in rn_items
        assert agent not in rn_items
    
    def test_get_mobile_user_items(self):
        """Test getting Mobile Users items"""
        infra = InfrastructureConfig()
        
        ike_crypto = IKECryptoProfile({
            'name': 'ike-crypto',
            'folder': 'Remote Networks',
            'encryption': ['aes-256-cbc'],
            'authentication': ['sha256'],
            'dh_group': ['group14']
        })
        
        agent = AgentProfile({
            'name': 'agent',
            'folder': 'Mobile Users',
            'connect_method': 'on-demand'
        })
        
        infra.add_item(ike_crypto)
        infra.add_item(agent)
        
        mu_items = infra.get_mobile_user_items()
        
        assert len(mu_items) == 1
        assert agent in mu_items
        assert ike_crypto not in mu_items
    
    def test_get_service_connections(self):
        """Test getting service connections"""
        infra = InfrastructureConfig()
        
        sc = ServiceConnection({
            'name': 'test-sc',
            'folder': 'Remote Networks',
            'ipsec_tunnel': 'test-tunnel',
            'subnets': ['10.0.0.0/8']
        })
        
        infra.add_item(sc)
        
        scs = infra.get_service_connections()
        
        assert len(scs) == 1
        assert sc in scs
    
    def test_get_crypto_profiles(self):
        """Test getting all crypto profiles"""
        infra = InfrastructureConfig()
        
        ike_crypto = IKECryptoProfile({
            'name': 'ike-crypto',
            'folder': 'Remote Networks',
            'encryption': ['aes-256-cbc'],
            'authentication': ['sha256'],
            'dh_group': ['group14']
        })
        
        ipsec_crypto = IPsecCryptoProfile({
            'name': 'ipsec-crypto',
            'folder': 'Remote Networks',
            'esp': {
                'encryption': ['aes-256-cbc'],
                'authentication': ['sha256']
            }
        })
        
        infra.add_item(ike_crypto)
        infra.add_item(ipsec_crypto)
        
        cryptos = infra.get_crypto_profiles()
        
        assert len(cryptos) == 2
        assert ike_crypto in cryptos
        assert ipsec_crypto in cryptos
    
    def test_resolve_dependency_chain(self):
        """Test resolving full infrastructure dependency chain"""
        infra = InfrastructureConfig()
        
        # Create full dependency chain: SC → Tunnel → Gateway → Crypto
        ike_crypto = IKECryptoProfile(Examples.ike_crypto_minimal())
        ike_gateway = IKEGateway(Examples.ike_gateway_minimal())
        ipsec_crypto = IPsecCryptoProfile(Examples.ipsec_crypto_minimal())
        ipsec_tunnel = IPsecTunnel(Examples.ipsec_tunnel_minimal())
        sc = ServiceConnection(Examples.service_connection_minimal())
        
        infra.add_item(ike_crypto)
        infra.add_item(ipsec_crypto)
        infra.add_item(ike_gateway)
        infra.add_item(ipsec_tunnel)
        infra.add_item(sc)
        
        # Resolve chain for service connection
        chain = infra.resolve_dependency_chain(sc)
        
        # Chain should contain: crypto profiles, gateway, tunnel (in order)
        assert len(chain) >= 3
        assert ipsec_tunnel in chain
        assert ike_gateway in chain


class TestConfiguration:
    """Tests for Configuration class"""
    
    def test_create_configuration(self):
        """Test creating empty configuration"""
        config = Configuration()
        
        assert len(config.folders) == 0
        assert len(config.snippets) == 0
        assert len(config.infrastructure) == 0
        assert len(config) == 0
    
    def test_add_folder_to_configuration(self):
        """Test adding a folder to configuration"""
        config = Configuration()
        folder = FolderConfig("Mobile Users")
        
        config.add_folder(folder)
        
        assert "Mobile Users" in config.folders
        assert config.get_folder("Mobile Users") == folder
    
    def test_add_snippet_to_configuration(self):
        """Test adding a snippet to configuration"""
        config = Configuration()
        snippet = SnippetConfig("production-snippet")
        
        config.add_snippet(snippet)
        
        assert "production-snippet" in config.snippets
        assert config.get_snippet("production-snippet") == snippet
    
    def test_get_all_items(self):
        """Test getting all items across all containers"""
        config = Configuration()
        
        # Add folder with items
        folder = FolderConfig("Mobile Users")
        addr = AddressObject({'name': 'addr1', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        folder.add_item(addr)
        config.add_folder(folder)
        
        # Add snippet with items
        snippet = SnippetConfig("test-snippet")
        tag = Tag({'name': 'tag1', 'snippet': 'test-snippet', 'color': 'Red'})
        snippet.add_item(tag)
        config.add_snippet(snippet)
        
        # Add infrastructure
        ike_crypto = IKECryptoProfile({
            'name': 'ike-crypto',
            'folder': 'Remote Networks',
            'encryption': ['aes-256-cbc'],
            'authentication': ['sha256'],
            'dh_group': ['group14']
        })
        config.infrastructure.add_item(ike_crypto)
        
        all_items = config.get_all_items()
        
        assert len(all_items) == 3
        assert addr in all_items
        assert tag in all_items
        assert ike_crypto in all_items
    
    def test_get_item_by_name(self):
        """Test getting an item by name across all containers"""
        config = Configuration()
        
        folder = FolderConfig("Mobile Users")
        addr = AddressObject({'name': 'test-address', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        folder.add_item(addr)
        config.add_folder(folder)
        
        found = config.get_item('test-address')
        
        assert found == addr
    
    def test_get_item_by_name_and_location(self):
        """Test getting an item by name and specific location"""
        config = Configuration()
        
        # Add same name in different locations
        folder1 = FolderConfig("Mobile Users")
        addr1 = AddressObject({'name': 'test', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        folder1.add_item(addr1)
        config.add_folder(folder1)
        
        folder2 = FolderConfig("Remote Networks")
        addr2 = AddressObject({'name': 'test', 'folder': 'Remote Networks', 'value': '192.168.0.1', 'type': 'ip-netmask'})
        folder2.add_item(addr2)
        config.add_folder(folder2)
        
        # Get from specific location
        found = config.get_item('test', location='Remote Networks')
        
        assert found == addr2
    
    def test_get_items_by_type(self):
        """Test getting all items of specific type across all containers"""
        config = Configuration()
        
        # Add addresses in folder
        folder = FolderConfig("Mobile Users")
        addr1 = AddressObject({'name': 'addr1', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        addr2 = AddressObject({'name': 'addr2', 'folder': 'Mobile Users', 'value': '10.0.0.2', 'type': 'ip-netmask'})
        folder.add_item(addr1)
        folder.add_item(addr2)
        config.add_folder(folder)
        
        # Add address in snippet
        snippet = SnippetConfig("test-snippet")
        addr3 = AddressObject({'name': 'addr3', 'snippet': 'test-snippet', 'value': '10.0.0.3', 'type': 'ip-netmask'})
        snippet.add_item(addr3)
        config.add_snippet(snippet)
        
        addresses = config.get_items_by_type('address_object')
        
        assert len(addresses) == 3
    
    def test_filter_defaults(self):
        """Test filtering defaults across all containers"""
        config = Configuration()
        
        folder = FolderConfig("Mobile Users")
        addr1 = AddressObject({'name': 'custom', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        addr2 = AddressObject({'name': 'default', 'folder': 'Mobile Users', 'value': '10.0.0.2', 'type': 'ip-netmask', 'is_default': True})
        folder.add_item(addr1)
        folder.add_item(addr2)
        config.add_folder(folder)
        
        non_defaults = config.filter_defaults()
        
        assert len(non_defaults) == 1
        assert non_defaults[0].name == 'custom'
    
    def test_validate_all(self):
        """Test validating all items in all containers"""
        config = Configuration()
        
        folder = FolderConfig("Mobile Users")
        
        # Valid item
        addr = AddressObject({'name': 'valid', 'folder': 'Mobile Users', 'value': '10.0.0.1', 'type': 'ip-netmask'})
        
        # Invalid item
        rule = SecurityRule({'name': 'invalid', 'folder': 'Mobile Users', 'from': ['any'], 'to': ['any']})  # Missing action
        
        folder.add_item(addr)
        folder.add_item(rule)
        config.add_folder(folder)
        
        all_errors = config.validate_all()
        
        assert 'folder:Mobile Users' in all_errors
        assert 'invalid' in all_errors['folder:Mobile Users']
    
    def test_resolve_dependencies_cross_container(self):
        """Test resolving dependencies across containers"""
        config = Configuration()
        
        # Add address in folder
        folder = FolderConfig("Mobile Users")
        addr = AddressObject({'name': 'internal-net', 'folder': 'Mobile Users', 'value': '10.0.0.0/8', 'type': 'ip-netmask'})
        folder.add_item(addr)
        config.add_folder(folder)
        
        # Add rule in snippet that depends on address
        snippet = SnippetConfig("test-snippet")
        rule = SecurityRule({
            'name': 'test-rule',
            'snippet': 'test-snippet',
            'from': ['any'],
            'to': ['any'],
            'source': ['internal-net'],  # Depends on address
            'destination': ['any'],
            'action': 'allow'
        })
        snippet.add_item(rule)
        config.add_snippet(snippet)
        
        deps = config.resolve_dependencies(rule)
        
        # Should find dependency across containers
        assert len(deps) == 1
        assert deps[0] == addr


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
