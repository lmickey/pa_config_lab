"""
Tests for config.models.factory module.

Tests the ConfigItemFactory for creating ConfigItem instances from raw data.
"""

import pytest
from config.models.factory import ConfigItemFactory
from config.models.objects import AddressObject, Tag, ServiceObject, AddressGroup
from config.models.policies import SecurityRule
from config.models.profiles import AuthenticationProfile, ProfileGroup
from config.models.infrastructure import IKECryptoProfile, IPsecTunnel, ServiceConnection
from tests.examples.loader import Examples


class TestFactoryRegistry:
    """Tests for factory type registration"""
    
    def test_registered_types_exist(self):
        """Test that factory has registered types"""
        types = ConfigItemFactory.get_registered_types()
        
        assert len(types) > 0
        assert 'address_object' in types
        assert 'security_rule' in types
        assert 'ike_crypto_profile' in types
    
    def test_registered_endpoints_exist(self):
        """Test that factory has registered endpoints"""
        endpoints = ConfigItemFactory.get_registered_endpoints()
        
        assert len(endpoints) > 0
        assert '/sse/config/v1/addresses' in endpoints
        assert '/sse/config/v1/security-rules' in endpoints
    
    def test_is_type_registered(self):
        """Test checking if type is registered"""
        assert ConfigItemFactory.is_type_registered('address_object')
        assert ConfigItemFactory.is_type_registered('security_rule')
        assert not ConfigItemFactory.is_type_registered('unknown_type')
    
    def test_get_class_for_type(self):
        """Test getting class for type"""
        cls = ConfigItemFactory.get_class_for_type('address_object')
        
        assert cls == AddressObject
    
    def test_register_custom_type(self):
        """Test registering a custom type"""
        # Register a custom type (using existing class for test)
        ConfigItemFactory.register_type('custom_address', AddressObject)
        
        assert ConfigItemFactory.is_type_registered('custom_address')
        assert ConfigItemFactory.get_class_for_type('custom_address') == AddressObject
    
    def test_register_custom_endpoint(self):
        """Test registering a custom endpoint"""
        ConfigItemFactory.register_endpoint('/custom/endpoint', 'address_object')
        
        endpoints = ConfigItemFactory.get_registered_endpoints()
        assert '/custom/endpoint' in endpoints


class TestCreateFromDict:
    """Tests for create_from_dict method"""
    
    def test_create_address_object(self):
        """Test creating address object from dict"""
        config = Examples.address_minimal()
        
        item = ConfigItemFactory.create_from_dict('address_object', config)
        
        assert isinstance(item, AddressObject)
        assert item.name == 'internal-network'
    
    def test_create_security_rule(self):
        """Test creating security rule from dict"""
        config = Examples.security_rule_minimal()
        
        item = ConfigItemFactory.create_from_dict('security_rule', config)
        
        assert isinstance(item, SecurityRule)
        assert item.action == 'allow'
    
    def test_create_ike_crypto_profile(self):
        """Test creating IKE crypto profile from dict"""
        config = Examples.ike_crypto_minimal()
        
        item = ConfigItemFactory.create_from_dict('ike_crypto_profile', config)
        
        assert isinstance(item, IKECryptoProfile)
        assert len(item.encryption) > 0
    
    def test_create_tag(self):
        """Test creating tag from dict"""
        config = Examples.tag_minimal()
        
        item = ConfigItemFactory.create_from_dict('tag', config)
        
        assert isinstance(item, Tag)
        assert item.color is not None
    
    def test_create_with_unknown_type(self):
        """Test creating with unknown type raises error"""
        config = Examples.address_minimal()
        
        with pytest.raises(ValueError, match="Unknown item type"):
            ConfigItemFactory.create_from_dict('unknown_type', config)
    
    def test_create_with_invalid_config(self):
        """Test creating with invalid config raises error"""
        config = {
            'name': 'test',
            # Missing required fields
        }
        
        with pytest.raises(Exception):
            ConfigItemFactory.create_from_dict('address_object', config)


class TestCreateFromAPIResponse:
    """Tests for create_from_api_response method"""
    
    def test_create_from_address_api_response(self):
        """Test creating addresses from API response"""
        response = Examples.api_response_addresses()
        
        items = ConfigItemFactory.create_from_api_response('/sse/config/v1/addresses', response)
        
        assert len(items) == 2
        assert all(isinstance(item, AddressObject) for item in items)
        assert items[0].name == 'internal-network'
        assert items[1].name == 'web-servers'
    
    def test_create_from_security_rule_api_response(self):
        """Test creating security rules from API response"""
        response = Examples.api_response_security_rules()
        
        items = ConfigItemFactory.create_from_api_response('/sse/config/v1/security-rules', response)
        
        assert len(items) == 1
        assert isinstance(items[0], SecurityRule)
        assert items[0].name == 'allow-internal'
    
    def test_create_from_api_response_with_defaults(self):
        """Test creating items from API response with defaults"""
        response = Examples.api_response_with_defaults()
        
        items = ConfigItemFactory.create_from_api_response('/sse/config/v1/addresses', response)
        
        assert len(items) == 2
        assert items[0].is_default is True
        assert items[1].is_default is False
    
    def test_create_from_list_response(self):
        """Test creating from API response that is a list"""
        response = [
            {
                'name': 'addr1',
                'folder': 'Mobile Users',
                'value': '10.0.0.1',
                'type': 'ip-netmask'
            }
        ]
        
        items = ConfigItemFactory.create_from_api_response('/sse/config/v1/addresses', response)
        
        assert len(items) == 1
        assert isinstance(items[0], AddressObject)
    
    def test_create_from_unknown_endpoint(self):
        """Test creating from unknown endpoint raises error"""
        response = {'data': []}
        
        with pytest.raises(ValueError, match="Unknown endpoint"):
            ConfigItemFactory.create_from_api_response('/unknown/endpoint', response)
    
    def test_create_from_invalid_response_format(self):
        """Test creating from invalid response format raises error"""
        response = "invalid"
        
        with pytest.raises(ValueError, match="Invalid response format"):
            ConfigItemFactory.create_from_api_response('/sse/config/v1/addresses', response)
    
    def test_create_from_response_with_errors(self):
        """Test creating from response with some invalid items"""
        response = {
            'data': [
                {
                    'name': 'valid-addr',
                    'folder': 'Mobile Users',
                    'value': '10.0.0.1',
                    'type': 'ip-netmask'
                },
                {
                    'name': 'invalid-addr',
                    # Missing required fields
                }
            ]
        }
        
        items = ConfigItemFactory.create_from_api_response('/sse/config/v1/addresses', response)
        
        # Should skip invalid item and only create valid one
        assert len(items) == 1
        assert items[0].name == 'valid-addr'


class TestAutoDetectType:
    """Tests for auto_detect_type method"""
    
    def test_detect_tag(self):
        """Test auto-detecting tag"""
        config = Examples.tag_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'tag'
    
    def test_detect_address_object(self):
        """Test auto-detecting address object"""
        config = Examples.address_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'address_object'
    
    def test_detect_address_group(self):
        """Test auto-detecting address group"""
        config = Examples.address_group()  # Use existing method
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'address_group'
    
    def test_detect_service_object(self):
        """Test auto-detecting service object"""
        config = Examples.service()  # Use existing method
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'service_object'
    
    def test_detect_security_rule(self):
        """Test auto-detecting security rule"""
        config = Examples.security_rule_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'security_rule'
    
    def test_detect_authentication_profile(self):
        """Test auto-detecting authentication profile"""
        config = Examples.auth_profile_saml()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'authentication_profile'
    
    def test_detect_profile_group(self):
        """Test auto-detecting profile group"""
        config = Examples.profile_group_custom()  # Use existing method
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'profile_group'
    
    def test_detect_ike_crypto_profile(self):
        """Test auto-detecting IKE crypto profile"""
        config = Examples.ike_crypto_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'ike_crypto_profile'
    
    def test_detect_ipsec_crypto_profile(self):
        """Test auto-detecting IPsec crypto profile"""
        config = Examples.ipsec_crypto_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'ipsec_crypto_profile'
    
    def test_detect_ike_gateway(self):
        """Test auto-detecting IKE gateway"""
        config = Examples.ike_gateway_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'ike_gateway'
    
    def test_detect_ipsec_tunnel(self):
        """Test auto-detecting IPsec tunnel"""
        config = Examples.ipsec_tunnel_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'ipsec_tunnel'
    
    def test_detect_service_connection(self):
        """Test auto-detecting service connection"""
        config = Examples.service_connection_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'service_connection'
    
    def test_detect_agent_profile(self):
        """Test auto-detecting agent profile"""
        config = Examples.agent_profile_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'agent_profile'
    
    def test_detect_portal(self):
        """Test auto-detecting portal"""
        config = Examples.portal_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'portal'
    
    def test_detect_gateway(self):
        """Test auto-detecting gateway"""
        config = Examples.gateway_minimal()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'gateway'
    
    def test_detect_explicit_item_type(self):
        """Test detecting when item_type is explicitly set"""
        config = {
            'name': 'test',
            'folder': 'Mobile Users',
            'item_type': 'address_object',
            'value': '10.0.0.1',
            'type': 'ip-netmask'
        }
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type == 'address_object'
    
    def test_detect_unknown_type(self):
        """Test detecting unknown type returns None"""
        config = Examples.unknown_item_type()
        
        item_type = ConfigItemFactory.auto_detect_type(config)
        
        assert item_type is None


class TestCreateWithAutoDetect:
    """Tests for create_with_auto_detect method"""
    
    def test_create_address_with_auto_detect(self):
        """Test creating address with auto-detection"""
        config = Examples.address_minimal()
        
        item = ConfigItemFactory.create_with_auto_detect(config)
        
        assert item is not None
        assert isinstance(item, AddressObject)
        assert item.name == 'internal-network'
    
    def test_create_security_rule_with_auto_detect(self):
        """Test creating security rule with auto-detection"""
        config = Examples.security_rule_minimal()
        
        item = ConfigItemFactory.create_with_auto_detect(config)
        
        assert item is not None
        assert isinstance(item, SecurityRule)
    
    def test_create_infrastructure_with_auto_detect(self):
        """Test creating infrastructure items with auto-detection"""
        config = Examples.ike_crypto_minimal()
        
        item = ConfigItemFactory.create_with_auto_detect(config)
        
        assert item is not None
        assert isinstance(item, IKECryptoProfile)
    
    def test_create_unknown_type_returns_none(self):
        """Test creating with unknown type returns None"""
        config = Examples.unknown_item_type()
        
        item = ConfigItemFactory.create_with_auto_detect(config)
        
        assert item is None


class TestFactoryWithAllTypes:
    """Test factory with all registered types"""
    
    def test_create_all_object_types(self):
        """Test creating all object types"""
        object_types = [
            ('tag', Examples.tag_minimal()),
            ('address_object', Examples.address_minimal()),
            ('address_group', Examples.address_group()),  # Use existing method
            ('service_object', Examples.service()),  # Use existing method
            ('service_group', Examples.service_group()),  # Use existing method
            ('application_group', Examples.application_group()),  # Use existing method
        ]
        
        for item_type, config in object_types:
            item = ConfigItemFactory.create_from_dict(item_type, config)
            assert item is not None
            assert item.item_type == item_type
    
    def test_create_all_profile_types(self):
        """Test creating all profile types"""
        profile_types = [
            ('authentication_profile', Examples.auth_profile_saml()),
            ('decryption_profile', Examples.decryption_profile_full()),
            ('profile_group', Examples.profile_group_custom()),  # Use existing method
            ('hip_profile', Examples.hip_profile()),  # Use existing method
        ]
        
        for item_type, config in profile_types:
            item = ConfigItemFactory.create_from_dict(item_type, config)
            assert item is not None
            assert item.item_type == item_type
    
    def test_create_all_policy_types(self):
        """Test creating all policy types"""
        policy_types = [
            ('security_rule', Examples.security_rule_minimal()),
            ('decryption_rule', Examples.decryption_rule_minimal()),
            ('authentication_rule', Examples.authentication_rule()),
            ('qos_policy_rule', Examples.qos_rule()),
        ]
        
        for item_type, config in policy_types:
            item = ConfigItemFactory.create_from_dict(item_type, config)
            assert item is not None
            assert item.item_type == item_type
    
    def test_create_all_infrastructure_types(self):
        """Test creating all infrastructure types"""
        infra_types = [
            ('ike_crypto_profile', Examples.ike_crypto_minimal()),
            ('ipsec_crypto_profile', Examples.ipsec_crypto_minimal()),
            ('ike_gateway', Examples.ike_gateway_minimal()),
            ('ipsec_tunnel', Examples.ipsec_tunnel_minimal()),
            ('service_connection', Examples.service_connection_minimal()),
            ('agent_profile', Examples.agent_profile_minimal()),
            ('portal', Examples.portal_minimal()),
            ('gateway', Examples.gateway_minimal()),
        ]
        
        for item_type, config in infra_types:
            item = ConfigItemFactory.create_from_dict(item_type, config)
            assert item is not None
            assert item.item_type == item_type


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
