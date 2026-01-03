"""
Unit tests for Prisma API error handling.
"""

import pytest
from prisma.api.errors import (
    PrismaAPIError,
    AuthenticationError,
    AuthorizationError,
    NetworkError,
    RateLimitError,
    ValidationError,
    ResourceNotFoundError,
    ResourceConflictError,
    ResponseParsingError,
    parse_api_error,
)


class TestErrorClasses:
    """Test error class instantiation and properties"""
    
    def test_base_error(self):
        """Test base PrismaAPIError"""
        error = PrismaAPIError(
            "Test error",
            error_code="TEST001",
            details={'key': 'value'}
        )
        assert str(error) == "Test error (Error Code: TEST001) - Details: {'key': 'value'}"
        assert error.message == "Test error"
        assert error.error_code == "TEST001"
        assert error.details == {'key': 'value'}
    
    def test_authentication_error(self):
        """Test AuthenticationError"""
        error = AuthenticationError("Invalid credentials")
        assert isinstance(error, PrismaAPIError)
        assert "Invalid credentials" in str(error)
    
    def test_network_error_retryable(self):
        """Test NetworkError retryability"""
        error_500 = NetworkError("Server error", status_code=500)
        assert error_500.is_retryable is True
        
        error_503 = NetworkError("Service unavailable", status_code=503)
        assert error_503.is_retryable is True
        
        error_400 = NetworkError("Bad request", status_code=400)
        assert error_400.is_retryable is False
    
    def test_rate_limit_error(self):
        """Test RateLimitError with retry_after"""
        error = RateLimitError("Rate limit exceeded", retry_after=60)
        assert error.retry_after == 60
        assert "Retry after 60 seconds" in str(error)
    
    def test_validation_error(self):
        """Test ValidationError with field"""
        error = ValidationError("Invalid value", field="name", value="test@")
        assert error.field == "name"
        assert error.value == "test@"
        assert "Field: 'name'" in str(error)
    
    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError"""
        error = ResourceNotFoundError(
            "Not found",
            resource_type="address_object",
            resource_name="test-addr"
        )
        assert error.resource_type == "address_object"
        assert error.resource_name == "test-addr"
        assert "address_object: 'test-addr'" in str(error)
    
    def test_resource_conflict_error(self):
        """Test ResourceConflictError"""
        error = ResourceConflictError("Name already exists", conflicting_name="test-obj")
        assert error.conflicting_name == "test-obj"


class TestParseAPIError:
    """Test parse_api_error function"""
    
    def test_401_returns_authentication_error(self):
        """Test 401 status code"""
        response = {'error': {'message': 'Invalid token', 'code': 'AUTH001'}}
        error = parse_api_error(response, 401)
        
        assert isinstance(error, AuthenticationError)
        assert "Invalid token" in str(error)
        assert error.error_code == 'AUTH001'
    
    def test_403_returns_authorization_error(self):
        """Test 403 status code"""
        response = {'error': {'message': 'Insufficient permissions'}}
        error = parse_api_error(response, 403)
        
        assert isinstance(error, AuthorizationError)
        assert "Insufficient permissions" in str(error)
    
    def test_404_returns_not_found_error(self):
        """Test 404 status code"""
        response = {'error': {'message': 'Resource not found'}}
        error = parse_api_error(response, 404)
        
        assert isinstance(error, ResourceNotFoundError)
        assert "Resource not found" in str(error)
    
    def test_409_returns_conflict_error(self):
        """Test 409 status code"""
        response = {'error': {'message': 'Name already exists', 'name': 'test-obj'}}
        error = parse_api_error(response, 409)
        
        assert isinstance(error, ResourceConflictError)
        assert error.conflicting_name == 'test-obj'
    
    def test_422_returns_validation_error(self):
        """Test 422 status code"""
        response = {
            'error': {
                'message': 'Validation failed',
                'field': 'ip_netmask',
                'value': 'invalid'
            }
        }
        error = parse_api_error(response, 422)
        
        assert isinstance(error, ValidationError)
        assert error.field == 'ip_netmask'
        assert error.value == 'invalid'
    
    def test_429_returns_rate_limit_error(self):
        """Test 429 status code"""
        response = {'error': {'message': 'Rate limit exceeded'}}
        
        # Mock response with headers
        class MockResponse:
            def __init__(self):
                self.headers = {'Retry-After': '60'}
            
            def json(self):
                return response
        
        error = parse_api_error(MockResponse(), 429)
        
        assert isinstance(error, RateLimitError)
        assert error.retry_after == 60
    
    def test_500_returns_network_error(self):
        """Test 500 status code"""
        response = {'error': {'message': 'Internal server error'}}
        error = parse_api_error(response, 500)
        
        assert isinstance(error, NetworkError)
        assert error.is_retryable is True
    
    def test_scm_errors_format(self):
        """Test SCM API _errors format"""
        response = {
            '_errors': [
                {'message': 'Invalid field', 'field': 'name'},
                {'message': 'Missing required field', 'field': 'folder'}
            ]
        }
        error = parse_api_error(response, 422)
        
        assert isinstance(error, ValidationError)
        assert "Invalid field" in str(error)
        assert 'errors' in error.details
    
    def test_url_in_details(self):
        """Test URL is added to error details"""
        response = {'error': {'message': 'Error'}}
        error = parse_api_error(response, 500, url='/api/addresses')
        
        assert error.details['url'] == '/api/addresses'
    
    def test_malformed_response(self):
        """Test handling of malformed response"""
        # Should not raise exception, should return generic error
        error = parse_api_error("Invalid JSON", 500)
        
        assert isinstance(error, NetworkError)
        assert "API request failed" in str(error) or "Invalid JSON" in str(error)


class TestErrorInheritance:
    """Test error class inheritance"""
    
    def test_all_errors_inherit_from_base(self):
        """Test all error classes inherit from PrismaAPIError"""
        errors = [
            AuthenticationError("test"),
            AuthorizationError("test"),
            NetworkError("test"),
            RateLimitError("test"),
            ValidationError("test"),
            ResourceNotFoundError("test"),
            ResourceConflictError("test"),
            ResponseParsingError("test"),
        ]
        
        for error in errors:
            assert isinstance(error, PrismaAPIError)
            assert isinstance(error, Exception)
    
    def test_error_catching(self):
        """Test catching errors by base class"""
        try:
            raise AuthenticationError("Test")
        except PrismaAPIError as e:
            assert isinstance(e, AuthenticationError)
        else:
            pytest.fail("Should have caught AuthenticationError as PrismaAPIError")
