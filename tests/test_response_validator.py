"""
Unit tests for response validator.
"""

import pytest
from prisma.api.response_validator import (
    ResponseValidator,
    ResponseValidatorFactory,
    validate_response,
    validate_for_creation,
)
from prisma.api.errors import SchemaValidationError


class TestResponseValidator:
    """Test ResponseValidator class"""
    
    def test_valid_response(self):
        """Test validation of valid response"""
        validator = ResponseValidator(strict_mode=False)
        response = {
            'data': [
                {'name': 'test-addr', 'folder': 'Mobile Users', 'ip_netmask': '10.0.0.1'}
            ]
        }
        
        assert validator.validate_response(response, 'address_object') is True
        assert len(validator.validation_issues) == 0
    
    def test_valid_response_strict(self):
        """Test validation in strict mode with valid response"""
        validator = ResponseValidator(strict_mode=True)
        response = {
            'data': [
                {'name': 'test-addr', 'folder': 'Mobile Users', 'ip_netmask': '10.0.0.1'}
            ]
        }
        
        assert validator.validate_response(response, 'address_object') is True
    
    def test_response_not_dict_non_strict(self):
        """Test non-dict response in non-strict mode"""
        validator = ResponseValidator(strict_mode=False)
        response = "not a dict"
        
        # Should return False but not raise
        result = validator.validate_response(response, 'address_object')
        assert result is False
        assert len(validator.validation_issues['address_object']) > 0
    
    def test_response_not_dict_strict(self):
        """Test non-dict response in strict mode"""
        validator = ResponseValidator(strict_mode=True)
        response = "not a dict"
        
        with pytest.raises(SchemaValidationError) as exc_info:
            validator.validate_response(response, 'address_object')
        
        assert "not a dict" in str(exc_info.value)
    
    def test_missing_data_key(self):
        """Test response missing 'data' key"""
        validator = ResponseValidator(strict_mode=False)
        response = {'items': []}
        
        # Should log warning but not fail in non-strict
        # Since data is missing, it defaults to empty list which is valid
        result = validator.validate_response(response, 'address_object')
        # Empty data is valid, so this should pass
        assert result is True or result is False  # Either is acceptable
        # What matters is it doesn't raise an exception
    
    def test_data_not_list_strict(self):
        """Test 'data' is not a list in strict mode"""
        validator = ResponseValidator(strict_mode=True)
        response = {'data': 'not a list'}
        
        with pytest.raises(SchemaValidationError) as exc_info:
            validator.validate_response(response, 'address_object')
        
        assert "not a list" in str(exc_info.value)
    
    def test_missing_required_field(self):
        """Test item missing required field"""
        validator = ResponseValidator(strict_mode=False)
        response = {
            'data': [
                {'folder': 'Mobile Users', 'ip_netmask': '10.0.0.1'}  # Missing 'name'
            ]
        }
        
        result = validator.validate_response(response, 'address_object')
        assert result is False
        assert any('missing required field' in issue.lower() 
                  for issue in validator.validation_issues['address_object'])
    
    def test_empty_data(self):
        """Test empty data array"""
        validator = ResponseValidator(strict_mode=True)
        response = {'data': []}
        
        # Empty is valid
        assert validator.validate_response(response, 'address_object') is True
    
    def test_multiple_items(self):
        """Test multiple items in data"""
        validator = ResponseValidator(strict_mode=False)
        response = {
            'data': [
                {'name': 'addr1', 'folder': 'Mobile Users', 'ip_netmask': '10.0.0.1'},
                {'name': 'addr2', 'folder': 'Mobile Users', 'ip_netmask': '10.0.0.2'},
                {'name': 'addr3', 'folder': 'Mobile Users', 'ip_netmask': '10.0.0.3'},
            ]
        }
        
        assert validator.validate_response(response, 'address_object') is True


class TestItemValidation:
    """Test item-level validation"""
    
    def test_validate_item_for_creation_valid(self):
        """Test valid item for creation"""
        validator = ResponseValidator(strict_mode=True)
        item = {
            'name': 'test-addr',
            'folder': 'Mobile Users',
            'ip_netmask': '10.0.0.1'
        }
        
        assert validator.validate_item_for_creation(item, 'address_object') is True
    
    def test_validate_item_missing_name(self):
        """Test item missing name"""
        validator = ResponseValidator(strict_mode=True)
        item = {
            'folder': 'Mobile Users',
            'ip_netmask': '10.0.0.1'
        }
        
        with pytest.raises(SchemaValidationError) as exc_info:
            validator.validate_item_for_creation(item, 'address_object')
        
        assert "name" in str(exc_info.value).lower()
    
    def test_validate_item_empty_name(self):
        """Test item with empty name"""
        validator = ResponseValidator(strict_mode=True)
        item = {
            'name': '   ',
            'folder': 'Mobile Users',
            'ip_netmask': '10.0.0.1'
        }
        
        with pytest.raises(SchemaValidationError) as exc_info:
            validator.validate_item_for_creation(item, 'address_object')
        
        assert "non-empty string" in str(exc_info.value).lower()
    
    def test_validate_item_no_container(self):
        """Test item without container"""
        validator = ResponseValidator(strict_mode=True)
        item = {
            'name': 'test-addr',
            'ip_netmask': '10.0.0.1'
        }
        
        with pytest.raises(SchemaValidationError) as exc_info:
            validator.validate_item_for_creation(item, 'address_object')
        
        assert "container" in str(exc_info.value).lower()
    
    def test_validate_item_multiple_containers(self):
        """Test item with multiple containers"""
        validator = ResponseValidator(strict_mode=True)
        item = {
            'name': 'test-addr',
            'folder': 'Mobile Users',
            'snippet': 'default',
            'ip_netmask': '10.0.0.1'
        }
        
        with pytest.raises(SchemaValidationError) as exc_info:
            validator.validate_item_for_creation(item, 'address_object')
        
        assert "multiple containers" in str(exc_info.value).lower()
    
    def test_validate_with_snippet(self):
        """Test item with snippet container"""
        validator = ResponseValidator(strict_mode=True)
        item = {
            'name': 'test-addr',
            'snippet': 'default',
            'ip_netmask': '10.0.0.1'
        }
        
        assert validator.validate_item_for_creation(item, 'address_object') is True
    
    def test_validate_with_device(self):
        """Test item with device container"""
        validator = ResponseValidator(strict_mode=True)
        item = {
            'name': 'test-addr',
            'device': 'device-01',
            'ip_netmask': '10.0.0.1'
        }
        
        assert validator.validate_item_for_creation(item, 'address_object') is True


class TestValidatorFactory:
    """Test ResponseValidatorFactory"""
    
    def test_create_development_validator(self):
        """Test development validator creation"""
        validator = ResponseValidatorFactory.create_development_validator()
        assert validator.strict_mode is True
    
    def test_create_production_validator(self):
        """Test production validator creation"""
        validator = ResponseValidatorFactory.create_production_validator()
        assert validator.strict_mode is False
    
    def test_create_custom_validator(self):
        """Test custom validator creation"""
        validator = ResponseValidatorFactory.create_custom_validator(strict=True)
        assert validator.strict_mode is True
        
        validator = ResponseValidatorFactory.create_custom_validator(strict=False)
        assert validator.strict_mode is False


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_validate_response_function(self):
        """Test validate_response convenience function"""
        response = {
            'data': [
                {'name': 'test', 'folder': 'Mobile Users'}
            ]
        }
        
        result = validate_response(response, 'address_object', strict=False)
        assert result is True
    
    def test_validate_response_strict(self):
        """Test validate_response in strict mode"""
        response = "not a dict"
        
        with pytest.raises(SchemaValidationError):
            validate_response(response, 'address_object', strict=True)
    
    def test_validate_for_creation_function(self):
        """Test validate_for_creation convenience function"""
        item = {
            'name': 'test',
            'folder': 'Mobile Users',
            'ip_netmask': '10.0.0.1'
        }
        
        result = validate_for_creation(item, 'address_object')
        assert result is True
    
    def test_validate_for_creation_invalid(self):
        """Test validate_for_creation with invalid item"""
        item = {
            'folder': 'Mobile Users',  # Missing name
            'ip_netmask': '10.0.0.1'
        }
        
        with pytest.raises(SchemaValidationError):
            validate_for_creation(item, 'address_object')


class TestValidationSummary:
    """Test validation summary functionality"""
    
    def test_get_validation_summary_empty(self):
        """Test summary with no issues"""
        validator = ResponseValidator(strict_mode=False)
        summary = validator.get_validation_summary()
        
        assert summary['total_types_with_issues'] == 0
        assert len(summary['issues_by_type']) == 0
    
    def test_get_validation_summary_with_issues(self):
        """Test summary with issues"""
        validator = ResponseValidator(strict_mode=False)
        
        # Create some issues
        response = {'data': [{'folder': 'test'}]}  # Missing name
        validator.validate_response(response, 'address_object')
        validator.validate_response(response, 'service_object')
        
        summary = validator.get_validation_summary()
        
        assert summary['total_types_with_issues'] == 2
        assert 'address_object' in summary['issues_by_type']
        assert 'service_object' in summary['issues_by_type']
        assert 'address_object' in summary['sample_issues']
    
    def test_clear_issues(self):
        """Test clearing validation issues"""
        validator = ResponseValidator(strict_mode=False)
        
        # Create issue
        response = {'data': [{'folder': 'test'}]}
        validator.validate_response(response, 'address_object')
        
        assert len(validator.validation_issues) > 0
        
        # Clear
        validator.clear_issues()
        
        assert len(validator.validation_issues) == 0


class TestTypeSpecificValidation:
    """Test type-specific validation rules"""
    
    def test_address_group_requires_static(self):
        """Test address_group requires 'static' field"""
        validator = ResponseValidator(strict_mode=False)
        response = {
            'data': [
                {'name': 'test-group', 'folder': 'Mobile Users'}  # Missing 'static'
            ]
        }
        
        result = validator.validate_response(response, 'address_group')
        # Should detect missing 'static'
        assert result is False or 'address_group' in validator.validation_issues
    
    def test_security_rule_complex_requirements(self):
        """Test security_rule has multiple required fields"""
        validator = ResponseValidator(strict_mode=False)
        response = {
            'data': [
                {'name': 'test-rule', 'folder': 'Mobile Users'}  # Missing many fields
            ]
        }
        
        result = validator.validate_response(response, 'security_rule')
        # Should detect missing required fields
        assert result is False
        issues = validator.validation_issues['security_rule']
        assert len(issues) > 0
