"""
Tests for config.models.profiles module.

Tests all security and configuration profile model classes.
"""

import pytest
from config.models.profiles import (
    AuthenticationProfile,
    DecryptionProfile,
    URLFilteringProfile,
    AntivirusProfile,
    AntiSpywareProfile,
    VulnerabilityProfile,
    FileBlockingProfile,
    WildfireProfile,
    ProfileGroup,
    HIPProfile,
    HIPObject,
    HTTPHeaderProfile,
    CertificateProfile,
    OCSPResponder,
    SCEPProfile,
    QoSProfile,
)
from tests.examples.loader import Examples


class TestAuthenticationProfile:
    """Tests for AuthenticationProfile class"""
    
    def test_create_saml_profile(self):
        """Test creating SAML authentication profile"""
        config = Examples.auth_profile_saml()
        profile = AuthenticationProfile(config)
        
        assert profile.name == 'okta-saml'
        assert profile.folder == 'Mobile Users'
        assert profile.method_type == 'saml_idp'
        assert not profile.is_cie_profile
        assert not profile.has_dependencies
    
    def test_create_ldap_profile(self):
        """Test creating LDAP authentication profile"""
        config = Examples.auth_profile_ldap()
        profile = AuthenticationProfile(config)
        
        assert profile.name == 'ad-ldap'
        assert profile.method_type == 'ldap'
        assert not profile.is_cie_profile
    
    def test_create_cie_profile(self):
        """Test creating CIE authentication profile"""
        config = Examples.auth_profile_cie()
        profile = AuthenticationProfile(config)
        
        assert profile.name == 'cie-authentication'
        assert profile.method_type == 'cloud'
        assert profile.is_cie_profile  # Should be detected for exclusion
    
    def test_auth_profile_validation_no_method(self):
        """Test validation catches missing method"""
        config = {
            'name': 'invalid-profile',
            'folder': 'Mobile Users'
        }
        
        profile = AuthenticationProfile(config)
        errors = profile.validate()
        
        assert len(errors) > 0
        assert any('method' in error.lower() for error in errors)


class TestDecryptionProfile:
    """Tests for DecryptionProfile class"""
    
    def test_create_decryption_profile(self):
        """Test creating decryption profile"""
        config = Examples.decryption_profile_full()
        profile = DecryptionProfile(config)
        
        assert profile.name == 'strict-decryption'
        assert profile.ssl_protocol_settings is not None
        assert profile.min_version == 'tls1-2'
        assert profile.max_version == 'max'
        assert not profile.has_dependencies
    
    def test_decryption_profile_validation_invalid_version(self):
        """Test validation catches invalid SSL version"""
        config = {
            'name': 'invalid-decrypt',
            'folder': 'Mobile Users',
            'ssl_protocol_settings': {
                'min_version': 'invalid-version'
            }
        }
        
        profile = DecryptionProfile(config)
        errors = profile.validate()
        
        assert len(errors) > 0
        assert any('min_version' in error.lower() for error in errors)


class TestURLFilteringProfile:
    """Tests for URLFilteringProfile class"""
    
    def test_create_url_filtering_profile(self):
        """Test creating URL filtering profile"""
        config = Examples.url_filtering_profile_full()
        profile = URLFilteringProfile(config)
        
        assert profile.name == 'corporate-url-policy'
        assert profile.action is not None
        assert len(profile.blocked_categories) == 4
        assert 'malware' in profile.blocked_categories
        assert len(profile.alerted_categories) == 3
        assert 'hacking' in profile.alerted_categories
    
    def test_url_filtering_no_action(self):
        """Test URL filtering profile without action"""
        config = {
            'name': 'minimal-url',
            'folder': 'Mobile Users'
        }
        
        profile = URLFilteringProfile(config)
        assert len(profile.blocked_categories) == 0
        assert len(profile.alerted_categories) == 0


class TestSecurityProfiles:
    """Tests for basic security profiles (AV, AS, Vuln, FB, WF)"""
    
    def test_create_antivirus_profile(self):
        """Test creating antivirus profile"""
        config = Examples.antivirus_profile()
        profile = AntivirusProfile(config)
        
        assert profile.name == 'default-av'
        assert profile.folder == 'Shared'
        assert not profile.has_dependencies
    
    def test_create_anti_spyware_profile(self):
        """Test creating anti-spyware profile"""
        config = Examples.anti_spyware_profile()
        profile = AntiSpywareProfile(config)
        
        assert profile.name == 'strict-spyware'
        assert profile.folder == 'Mobile Users'
    
    def test_create_vulnerability_profile(self):
        """Test creating vulnerability profile"""
        config = Examples.vulnerability_profile()
        profile = VulnerabilityProfile(config)
        
        assert profile.name == 'strict-vulnerability'
        assert profile.folder == 'Mobile Users'
    
    def test_create_file_blocking_profile(self):
        """Test creating file blocking profile"""
        config = Examples.file_blocking_profile()
        profile = FileBlockingProfile(config)
        
        assert profile.name == 'block-executables'
        assert profile.folder == 'Mobile Users'
    
    def test_create_wildfire_profile(self):
        """Test creating Wildfire profile"""
        config = Examples.wildfire_profile()
        profile = WildfireProfile(config)
        
        assert profile.name == 'default-wildfire'
        assert profile.folder == 'Shared'


class TestProfileGroup:
    """Tests for ProfileGroup class"""
    
    def test_create_profile_group(self):
        """Test creating profile group"""
        config = Examples.profile_group_custom()
        group = ProfileGroup(config)
        
        assert group.name == 'strict-security'
        assert len(group.virus_profiles) == 1
        assert len(group.spyware_profiles) == 1
        assert len(group.vulnerability_profiles) == 1
        assert len(group.url_filtering_profiles) == 1
        assert len(group.file_blocking_profiles) == 1
        assert len(group.wildfire_profiles) == 1
        assert group.has_dependencies
    
    def test_profile_group_dependencies(self):
        """Test profile group dependency detection"""
        config = Examples.profile_group_custom()
        group = ProfileGroup(config)
        
        deps = group.get_dependencies()
        
        assert len(deps) == 6
        assert ('antivirus_profile', 'strict-av') in deps
        assert ('anti_spyware_profile', 'strict-spyware') in deps
        assert ('vulnerability_profile', 'strict-vulnerability') in deps
        assert ('url_filtering_profile', 'corporate-url-policy') in deps
        assert ('file_blocking_profile', 'block-executables') in deps
        assert ('wildfire_profile', 'default-wildfire') in deps
    
    def test_profile_group_validation_empty(self):
        """Test validation catches empty profile group"""
        config = {
            'name': 'empty-group',
            'folder': 'Mobile Users'
        }
        
        group = ProfileGroup(config)
        errors = group.validate()
        
        assert len(errors) > 0
        assert any('at least one' in error.lower() for error in errors)
    
    def test_profile_group_from_best_practice(self):
        """Test profile group from best-practice example"""
        config = Examples.profile_group()
        group = ProfileGroup(config)
        
        assert group.name == 'best-practice'
        assert group.folder == 'Shared'
        assert group.is_default == True


class TestHIPProfiles:
    """Tests for HIP profiles and objects"""
    
    def test_create_hip_profile(self):
        """Test creating HIP profile"""
        config = Examples.hip_profile()
        profile = HIPProfile(config)
        
        assert profile.name == 'corporate-device'
        assert profile.folder == 'Mobile Users'
        assert profile.match_type == 'all'
    
    def test_create_hip_object(self):
        """Test creating HIP object"""
        config = Examples.hip_object()
        obj = HIPObject(config)
        
        assert obj.name == 'windows-compliant'
        assert obj.folder == 'Mobile Users'


class TestHTTPHeaderProfile:
    """Tests for HTTP Header Profile"""
    
    def test_create_http_header_profile(self):
        """Test creating HTTP header profile"""
        config = Examples.http_header_profile()
        profile = HTTPHeaderProfile(config)
        
        assert profile.name == 'security-headers'
        assert len(profile.headers) == 2
        
        # Check headers
        header_names = [h['name'] for h in profile.headers]
        assert 'X-Frame-Options' in header_names
        assert 'Strict-Transport-Security' in header_names


class TestCertificateProfiles:
    """Tests for certificate-related profiles"""
    
    def test_create_certificate_profile(self):
        """Test creating certificate profile"""
        config = Examples.certificate_profile()
        profile = CertificateProfile(config)
        
        assert profile.name == 'default-cert-profile'
        assert profile.folder == 'Shared'
    
    def test_create_ocsp_responder(self):
        """Test creating OCSP responder"""
        config = Examples.ocsp_responder()
        responder = OCSPResponder(config)
        
        assert responder.name == 'ocsp-primary'
        assert responder.host_name == 'ocsp.example.com'
    
    def test_create_scep_profile(self):
        """Test creating SCEP profile"""
        config = Examples.scep_profile()
        profile = SCEPProfile(config)
        
        assert profile.name == 'scep-enrollment'
        assert profile.ca_identity == 'CN=CA,O=Example,C=US'


class TestQoSProfile:
    """Tests for QoS Profile"""
    
    def test_create_qos_profile(self):
        """Test creating QoS profile"""
        config = Examples.qos_profile()
        profile = QoSProfile(config)
        
        assert profile.name == 'voice-priority'
        assert profile.class_bandwidth_type is not None


class TestProfileSerialization:
    """Test serialization/deserialization of profile models"""
    
    def test_auth_profile_serialization(self):
        """Test authentication profile serialization"""
        config = Examples.auth_profile_saml()
        profile = AuthenticationProfile(config)
        
        # Serialize
        data = profile.to_dict()
        
        assert 'name' in data
        assert 'folder' in data
        assert 'method' in data
        assert 'id' not in data
        
        # Deserialize
        profile2 = AuthenticationProfile.from_dict(data)
        
        assert profile2.name == profile.name
        assert profile2.method_type == profile.method_type
    
    def test_profile_group_serialization(self):
        """Test profile group serialization"""
        config = Examples.profile_group_custom()
        group = ProfileGroup(config)
        group.push_strategy = 'overwrite'
        
        # Serialize
        data = group.to_dict()
        
        assert data['push_strategy'] == 'overwrite'
        assert 'virus' in data
        
        # Deserialize
        group2 = ProfileGroup.from_dict(data)
        
        assert group2.push_strategy == 'overwrite'
        assert len(group2.virus_profiles) == len(group.virus_profiles)


class TestProfileDeletion:
    """Test deletion tracking for profile models"""
    
    def test_mark_profile_for_deletion(self):
        """Test marking profile for deletion"""
        config = Examples.decryption_profile()
        profile = DecryptionProfile(config)
        
        assert not profile.deleted
        assert profile.delete_success is None
        
        profile.mark_for_deletion()
        
        assert profile.deleted
        assert profile.delete_success is None
    
    def test_unmark_profile_for_deletion(self):
        """Test unmarking profile for deletion"""
        config = Examples.url_filtering_profile()
        profile = URLFilteringProfile(config)
        
        profile.mark_for_deletion()
        profile.delete_success = False
        
        profile.unmark_for_deletion()
        
        assert not profile.deleted
        assert profile.delete_success is None


class TestProfileWithTags:
    """Test tag support on profiles"""
    
    def test_profile_with_tags(self):
        """Test profile with tags"""
        config = Examples.auth_profile_saml()
        config['tag'] = ['production', 'saml']
        
        profile = AuthenticationProfile(config)
        
        assert profile.has_tags
        tags = profile.get_tags()
        assert len(tags) == 2
        assert 'production' in tags
        assert 'saml' in tags


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
