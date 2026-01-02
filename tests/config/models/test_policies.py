"""
Tests for config.models.policies module.

Tests all policy and rule model classes.
"""

import pytest
from config.models.policies import (
    SecurityRule,
    DecryptionRule,
    AuthenticationRule,
    QoSPolicyRule,
)
from tests.examples.loader import Examples


class TestSecurityRule:
    """Tests for SecurityRule class"""
    
    def test_create_security_rule(self):
        """Test creating security rule"""
        config = Examples.security_rule_full()
        rule = SecurityRule(config)
        
        assert rule.name == 'allow-internal-apps'
        assert rule.folder == 'Mobile Users'
        assert rule.action == 'allow'
        assert rule.position == 5
        assert rule.is_enabled
        assert rule.has_dependencies
    
    def test_security_rule_zones(self):
        """Test security rule zone properties"""
        config = Examples.security_rule_minimal()
        rule = SecurityRule(config)
        
        assert len(rule.from_zones) > 0
        assert len(rule.to_zones) > 0
        assert 'any' in rule.from_zones or 'any' in rule.to_zones
    
    def test_security_rule_dependencies(self):
        """Test security rule dependency detection"""
        config = Examples.security_rule_with_dependencies()
        rule = SecurityRule(config)
        
        deps = rule.get_dependencies()
        
        # Should detect address, service, application dependencies
        assert len(deps) > 0
        
        # Check for specific dependency types
        dep_types = [d[0] for d in deps]
        assert 'address_object' in dep_types or 'service_object' in dep_types or 'application_object' in dep_types
    
    def test_security_rule_profile_group(self):
        """Test security rule with profile group"""
        config = Examples.security_rule_allow_apps()
        rule = SecurityRule(config)
        
        assert rule.profile_setting is not None
        
        deps = rule.get_dependencies()
        dep_types = [d[0] for d in deps]
        
        # Should detect profile group dependency
        assert 'profile_group' in dep_types
    
    def test_security_rule_disabled(self):
        """Test disabled security rule"""
        config = Examples.security_rule_disabled()
        rule = SecurityRule(config)
        
        assert not rule.is_enabled
    
    def test_security_rule_validation(self):
        """Test security rule validation"""
        # Valid rule
        config = Examples.security_rule_minimal()
        rule = SecurityRule(config)
        errors = rule.validate()
        assert len(errors) == 0
        
        # Invalid rule (no action)
        config_invalid = {
            'name': 'invalid-rule',
            'folder': 'Mobile Users',
            'from': ['any'],
            'to': ['any']
        }
        rule_invalid = SecurityRule(config_invalid)
        errors = rule_invalid.validate()
        assert len(errors) > 0
        assert any('action' in error.lower() for error in errors)


class TestDecryptionRule:
    """Tests for DecryptionRule class"""
    
    def test_create_decryption_rule_decrypt(self):
        """Test creating decryption rule with decrypt action"""
        config = Examples.decryption_rule_minimal()
        rule = DecryptionRule(config)
        
        assert rule.name == 'decrypt-outbound'
        assert rule.action == 'decrypt'
        assert rule.decryption_profile == 'strict-decryption'
        assert rule.has_dependencies
    
    def test_create_decryption_rule_no_decrypt(self):
        """Test creating decryption rule with no-decrypt action"""
        config = Examples.decryption_rule_no_decrypt()
        rule = DecryptionRule(config)
        
        assert rule.name == 'no-decrypt-financial'
        assert rule.action == 'no-decrypt'
    
    def test_decryption_rule_dependencies(self):
        """Test decryption rule dependency detection"""
        config = Examples.decryption_rule_minimal()
        rule = DecryptionRule(config)
        
        deps = rule.get_dependencies()
        
        # Should detect decryption profile dependency
        dep_types = [d[0] for d in deps]
        assert 'decryption_profile' in dep_types
    
    def test_decryption_rule_validation(self):
        """Test decryption rule validation"""
        # Valid rule
        config = Examples.decryption_rule_minimal()
        rule = DecryptionRule(config)
        errors = rule.validate()
        assert len(errors) == 0
        
        # Invalid rule (invalid action)
        config_invalid = {
            'name': 'invalid-decrypt',
            'folder': 'Mobile Users',
            'from': ['any'],
            'to': ['any'],
            'action': 'invalid-action'
        }
        rule_invalid = DecryptionRule(config_invalid)
        errors = rule_invalid.validate()
        assert len(errors) > 0
        assert any('action' in error.lower() for error in errors)


class TestAuthenticationRule:
    """Tests for AuthenticationRule class"""
    
    def test_create_authentication_rule(self):
        """Test creating authentication rule"""
        config = Examples.authentication_rule()
        rule = AuthenticationRule(config)
        
        assert rule.name == 'require-saml-auth'
        assert rule.authentication_profile == 'okta-saml'
        assert rule.has_dependencies
    
    def test_authentication_rule_dependencies(self):
        """Test authentication rule dependency detection"""
        config = Examples.authentication_rule()
        rule = AuthenticationRule(config)
        
        deps = rule.get_dependencies()
        
        # Should detect auth profile and address dependencies
        dep_types = [d[0] for d in deps]
        assert 'authentication_profile' in dep_types


class TestQoSPolicyRule:
    """Tests for QoSPolicyRule class"""
    
    def test_create_qos_rule(self):
        """Test creating QoS rule"""
        config = Examples.qos_rule()
        rule = QoSPolicyRule(config)
        
        assert rule.name == 'prioritize-voice'
        assert len(rule.application) > 0
        assert rule.qos_profile == 'voice-priority'
        assert rule.has_dependencies
    
    def test_qos_rule_dependencies(self):
        """Test QoS rule dependency detection"""
        config = Examples.qos_rule()
        rule = QoSPolicyRule(config)
        
        deps = rule.get_dependencies()
        
        # Should detect QoS profile and application dependencies
        dep_types = [d[0] for d in deps]
        assert 'qos_profile' in dep_types
        assert 'application_object' in dep_types


class TestRuleProperties:
    """Test common RuleItem properties"""
    
    def test_rule_position(self):
        """Test rule position property"""
        config = Examples.security_rule_full()
        rule = SecurityRule(config)
        
        assert rule.position == 5
    
    def test_rule_enabled_state(self):
        """Test rule enabled/disabled state"""
        # Enabled rule
        config_enabled = Examples.security_rule_minimal()
        rule_enabled = SecurityRule(config_enabled)
        assert rule_enabled.is_enabled
        
        # Disabled rule
        config_disabled = Examples.security_rule_disabled()
        rule_disabled = SecurityRule(config_disabled)
        assert not rule_disabled.is_enabled


class TestPolicySerialization:
    """Test serialization/deserialization of policy models"""
    
    def test_security_rule_serialization(self):
        """Test security rule serialization"""
        config = Examples.security_rule_full()
        rule = SecurityRule(config)
        
        # Serialize
        data = rule.to_dict()
        
        assert 'name' in data
        assert 'folder' in data
        assert 'action' in data
        assert 'id' not in data
        
        # Deserialize
        rule2 = SecurityRule.from_dict(data)
        
        assert rule2.name == rule.name
        assert rule2.action == rule.action
    
    def test_decryption_rule_serialization(self):
        """Test decryption rule serialization"""
        config = Examples.decryption_rule_minimal()
        rule = DecryptionRule(config)
        rule.push_strategy = 'rename'
        
        # Serialize
        data = rule.to_dict()
        
        assert data['push_strategy'] == 'rename'
        assert 'action' in data
        
        # Deserialize
        rule2 = DecryptionRule.from_dict(data)
        
        assert rule2.push_strategy == 'rename'


class TestPolicyDeletion:
    """Test deletion tracking for policy models"""
    
    def test_mark_rule_for_deletion(self):
        """Test marking rule for deletion"""
        config = Examples.security_rule_minimal()
        rule = SecurityRule(config)
        
        assert not rule.deleted
        assert rule.delete_success is None
        
        rule.mark_for_deletion()
        
        assert rule.deleted
        assert rule.delete_success is None
    
    def test_unmark_rule_for_deletion(self):
        """Test unmarking rule for deletion"""
        config = Examples.decryption_rule_minimal()
        rule = DecryptionRule(config)
        
        rule.mark_for_deletion()
        rule.delete_success = False
        
        rule.unmark_for_deletion()
        
        assert not rule.deleted
        assert rule.delete_success is None


class TestPolicyWithTags:
    """Test tag support on policies"""
    
    def test_security_rule_with_tags(self):
        """Test security rule with tags"""
        config = Examples.security_rule_allow_apps()
        rule = SecurityRule(config)
        
        assert rule.has_tags
        tags = rule.get_tags()
        assert len(tags) == 2
        assert 'collaboration' in tags
        assert 'approved' in tags


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
