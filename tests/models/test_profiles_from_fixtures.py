"""
Unit tests for profiles models using production fixtures.

This file is auto-generated from production examples.
Tests cover:
- Model instantiation from real configs
- Validation
- Serialization
- Round-trip (load -> serialize -> load)
"""

import pytest
from config.models.profiles import *


class TestProfilesFromFixtures:
    """Profiles model tests using production fixtures"""
    

    # ========== ANTI_SPYWARE_PROFILE Tests ==========
    
    def test_anti_spyware_profile_load_all(self, anti_spyware_profile_fixtures):
        """Test all anti_spyware_profile examples can be loaded from fixtures"""
        assert len(anti_spyware_profile_fixtures) == 10, "Expected 10 fixtures"
        
        for i, fixture in enumerate(anti_spyware_profile_fixtures):
            # Load model
            obj = AntiSpywareProfile.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_anti_spyware_profile_validate_all(self, anti_spyware_profile_fixtures):
        """Test all anti_spyware_profile examples pass validation"""
        for i, fixture in enumerate(anti_spyware_profile_fixtures):
            obj = AntiSpywareProfile.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_anti_spyware_profile_serialize_all(self, anti_spyware_profile_fixtures):
        """Test all anti_spyware_profile examples can be serialized"""
        for i, fixture in enumerate(anti_spyware_profile_fixtures):
            obj = AntiSpywareProfile.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_anti_spyware_profile_roundtrip_all(self, anti_spyware_profile_fixtures):
        """Test all anti_spyware_profile examples survive round-trip serialization"""
        for i, fixture in enumerate(anti_spyware_profile_fixtures):
            # Load
            obj1 = AntiSpywareProfile.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = AntiSpywareProfile.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"

    # ========== AUTHENTICATION_PROFILE Tests ==========
    
    def test_authentication_profile_load_all(self, authentication_profile_fixtures):
        """Test all authentication_profile examples can be loaded from fixtures"""
        assert len(authentication_profile_fixtures) == 10, "Expected 10 fixtures"
        
        for i, fixture in enumerate(authentication_profile_fixtures):
            # Load model
            obj = AuthenticationProfile.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_authentication_profile_validate_all(self, authentication_profile_fixtures):
        """Test all authentication_profile examples pass validation"""
        for i, fixture in enumerate(authentication_profile_fixtures):
            obj = AuthenticationProfile.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_authentication_profile_serialize_all(self, authentication_profile_fixtures):
        """Test all authentication_profile examples can be serialized"""
        for i, fixture in enumerate(authentication_profile_fixtures):
            obj = AuthenticationProfile.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_authentication_profile_roundtrip_all(self, authentication_profile_fixtures):
        """Test all authentication_profile examples survive round-trip serialization"""
        for i, fixture in enumerate(authentication_profile_fixtures):
            # Load
            obj1 = AuthenticationProfile.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = AuthenticationProfile.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"

    # ========== CERTIFICATE_PROFILE Tests ==========
    
    def test_certificate_profile_load_all(self, certificate_profile_fixtures):
        """Test all certificate_profile examples can be loaded from fixtures"""
        assert len(certificate_profile_fixtures) == 6, "Expected 6 fixtures"
        
        for i, fixture in enumerate(certificate_profile_fixtures):
            # Load model
            obj = CertificateProfile.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_certificate_profile_validate_all(self, certificate_profile_fixtures):
        """Test all certificate_profile examples pass validation"""
        for i, fixture in enumerate(certificate_profile_fixtures):
            obj = CertificateProfile.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_certificate_profile_serialize_all(self, certificate_profile_fixtures):
        """Test all certificate_profile examples can be serialized"""
        for i, fixture in enumerate(certificate_profile_fixtures):
            obj = CertificateProfile.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_certificate_profile_roundtrip_all(self, certificate_profile_fixtures):
        """Test all certificate_profile examples survive round-trip serialization"""
        for i, fixture in enumerate(certificate_profile_fixtures):
            # Load
            obj1 = CertificateProfile.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = CertificateProfile.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"

    # ========== DECRYPTION_PROFILE Tests ==========
    
    def test_decryption_profile_load_all(self, decryption_profile_fixtures):
        """Test all decryption_profile examples can be loaded from fixtures"""
        assert len(decryption_profile_fixtures) == 10, "Expected 10 fixtures"
        
        for i, fixture in enumerate(decryption_profile_fixtures):
            # Load model
            obj = DecryptionProfile.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_decryption_profile_validate_all(self, decryption_profile_fixtures):
        """Test all decryption_profile examples pass validation"""
        for i, fixture in enumerate(decryption_profile_fixtures):
            obj = DecryptionProfile.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_decryption_profile_serialize_all(self, decryption_profile_fixtures):
        """Test all decryption_profile examples can be serialized"""
        for i, fixture in enumerate(decryption_profile_fixtures):
            obj = DecryptionProfile.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_decryption_profile_roundtrip_all(self, decryption_profile_fixtures):
        """Test all decryption_profile examples survive round-trip serialization"""
        for i, fixture in enumerate(decryption_profile_fixtures):
            # Load
            obj1 = DecryptionProfile.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = DecryptionProfile.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"

    # ========== FILE_BLOCKING_PROFILE Tests ==========
    
    def test_file_blocking_profile_load_all(self, file_blocking_profile_fixtures):
        """Test all file_blocking_profile examples can be loaded from fixtures"""
        assert len(file_blocking_profile_fixtures) == 10, "Expected 10 fixtures"
        
        for i, fixture in enumerate(file_blocking_profile_fixtures):
            # Load model
            obj = FileBlockingProfile.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_file_blocking_profile_validate_all(self, file_blocking_profile_fixtures):
        """Test all file_blocking_profile examples pass validation"""
        for i, fixture in enumerate(file_blocking_profile_fixtures):
            obj = FileBlockingProfile.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_file_blocking_profile_serialize_all(self, file_blocking_profile_fixtures):
        """Test all file_blocking_profile examples can be serialized"""
        for i, fixture in enumerate(file_blocking_profile_fixtures):
            obj = FileBlockingProfile.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_file_blocking_profile_roundtrip_all(self, file_blocking_profile_fixtures):
        """Test all file_blocking_profile examples survive round-trip serialization"""
        for i, fixture in enumerate(file_blocking_profile_fixtures):
            # Load
            obj1 = FileBlockingProfile.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = FileBlockingProfile.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"

    # ========== HIP_OBJECT Tests ==========
    
    def test_hip_object_load_all(self, hip_object_fixtures):
        """Test all hip_object examples can be loaded from fixtures"""
        assert len(hip_object_fixtures) == 10, "Expected 10 fixtures"
        
        for i, fixture in enumerate(hip_object_fixtures):
            # Load model
            obj = HIPObject.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_hip_object_validate_all(self, hip_object_fixtures):
        """Test all hip_object examples pass validation"""
        for i, fixture in enumerate(hip_object_fixtures):
            obj = HIPObject.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_hip_object_serialize_all(self, hip_object_fixtures):
        """Test all hip_object examples can be serialized"""
        for i, fixture in enumerate(hip_object_fixtures):
            obj = HIPObject.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_hip_object_roundtrip_all(self, hip_object_fixtures):
        """Test all hip_object examples survive round-trip serialization"""
        for i, fixture in enumerate(hip_object_fixtures):
            # Load
            obj1 = HIPObject.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = HIPObject.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"

    # ========== HIP_PROFILE Tests ==========
    
    def test_hip_profile_load_all(self, hip_profile_fixtures):
        """Test all hip_profile examples can be loaded from fixtures"""
        assert len(hip_profile_fixtures) == 10, "Expected 10 fixtures"
        
        for i, fixture in enumerate(hip_profile_fixtures):
            # Load model
            obj = HIPProfile.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_hip_profile_validate_all(self, hip_profile_fixtures):
        """Test all hip_profile examples pass validation"""
        for i, fixture in enumerate(hip_profile_fixtures):
            obj = HIPProfile.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_hip_profile_serialize_all(self, hip_profile_fixtures):
        """Test all hip_profile examples can be serialized"""
        for i, fixture in enumerate(hip_profile_fixtures):
            obj = HIPProfile.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_hip_profile_roundtrip_all(self, hip_profile_fixtures):
        """Test all hip_profile examples survive round-trip serialization"""
        for i, fixture in enumerate(hip_profile_fixtures):
            # Load
            obj1 = HIPProfile.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = HIPProfile.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"

    # ========== HTTP_HEADER_PROFILE Tests ==========
    
    def test_http_header_profile_load_all(self, http_header_profile_fixtures):
        """Test all http_header_profile examples can be loaded from fixtures"""
        assert len(http_header_profile_fixtures) == 5, "Expected 5 fixtures"
        
        for i, fixture in enumerate(http_header_profile_fixtures):
            # Load model
            obj = HTTPHeaderProfile.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_http_header_profile_validate_all(self, http_header_profile_fixtures):
        """Test all http_header_profile examples pass validation"""
        for i, fixture in enumerate(http_header_profile_fixtures):
            obj = HTTPHeaderProfile.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_http_header_profile_serialize_all(self, http_header_profile_fixtures):
        """Test all http_header_profile examples can be serialized"""
        for i, fixture in enumerate(http_header_profile_fixtures):
            obj = HTTPHeaderProfile.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_http_header_profile_roundtrip_all(self, http_header_profile_fixtures):
        """Test all http_header_profile examples survive round-trip serialization"""
        for i, fixture in enumerate(http_header_profile_fixtures):
            # Load
            obj1 = HTTPHeaderProfile.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = HTTPHeaderProfile.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"

    # ========== PROFILE_GROUP Tests ==========
    
    def test_profile_group_load_all(self, profile_group_fixtures):
        """Test all profile_group examples can be loaded from fixtures"""
        assert len(profile_group_fixtures) == 10, "Expected 10 fixtures"
        
        for i, fixture in enumerate(profile_group_fixtures):
            # Load model
            obj = ProfileGroup.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_profile_group_validate_all(self, profile_group_fixtures):
        """Test all profile_group examples pass validation"""
        for i, fixture in enumerate(profile_group_fixtures):
            obj = ProfileGroup.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_profile_group_serialize_all(self, profile_group_fixtures):
        """Test all profile_group examples can be serialized"""
        for i, fixture in enumerate(profile_group_fixtures):
            obj = ProfileGroup.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_profile_group_roundtrip_all(self, profile_group_fixtures):
        """Test all profile_group examples survive round-trip serialization"""
        for i, fixture in enumerate(profile_group_fixtures):
            # Load
            obj1 = ProfileGroup.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = ProfileGroup.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"

    # ========== QOS_PROFILE Tests ==========
    
    def test_qos_profile_load_all(self, qos_profile_fixtures):
        """Test all qos_profile examples can be loaded from fixtures"""
        assert len(qos_profile_fixtures) == 2, "Expected 2 fixtures"
        
        for i, fixture in enumerate(qos_profile_fixtures):
            # Load model
            obj = QoSProfile.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_qos_profile_validate_all(self, qos_profile_fixtures):
        """Test all qos_profile examples pass validation"""
        for i, fixture in enumerate(qos_profile_fixtures):
            obj = QoSProfile.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_qos_profile_serialize_all(self, qos_profile_fixtures):
        """Test all qos_profile examples can be serialized"""
        for i, fixture in enumerate(qos_profile_fixtures):
            obj = QoSProfile.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_qos_profile_roundtrip_all(self, qos_profile_fixtures):
        """Test all qos_profile examples survive round-trip serialization"""
        for i, fixture in enumerate(qos_profile_fixtures):
            # Load
            obj1 = QoSProfile.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = QoSProfile.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"

    # ========== VULNERABILITY_PROFILE Tests ==========
    
    def test_vulnerability_profile_load_all(self, vulnerability_profile_fixtures):
        """Test all vulnerability_profile examples can be loaded from fixtures"""
        assert len(vulnerability_profile_fixtures) == 10, "Expected 10 fixtures"
        
        for i, fixture in enumerate(vulnerability_profile_fixtures):
            # Load model
            obj = VulnerabilityProfile.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {i}"
            assert obj.name, f"Fixture {i} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {i} missing location"
    
    def test_vulnerability_profile_validate_all(self, vulnerability_profile_fixtures):
        """Test all vulnerability_profile examples pass validation"""
        for i, fixture in enumerate(vulnerability_profile_fixtures):
            obj = VulnerabilityProfile.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {i} validation failed: {e}")
    
    def test_vulnerability_profile_serialize_all(self, vulnerability_profile_fixtures):
        """Test all vulnerability_profile examples can be serialized"""
        for i, fixture in enumerate(vulnerability_profile_fixtures):
            obj = VulnerabilityProfile.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {i} serialization not a dict"
            assert 'name' in data, f"Fixture {i} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {i} name mismatch"
    
    def test_vulnerability_profile_roundtrip_all(self, vulnerability_profile_fixtures):
        """Test all vulnerability_profile examples survive round-trip serialization"""
        for i, fixture in enumerate(vulnerability_profile_fixtures):
            # Load
            obj1 = VulnerabilityProfile.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = VulnerabilityProfile.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {i} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {i} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {i} snippet mismatch"
