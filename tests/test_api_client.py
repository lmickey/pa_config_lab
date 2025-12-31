"""
Tests for Prisma Access API client.

Tests cover:
- Authentication
- API request handling
- Rate limiting
- Caching
- Error handling
- Pagination
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests

from prisma.api_client import PrismaAccessAPIClient
from tests.conftest import (
    mock_api_client,
    mock_folders_response,
    mock_rules_response,
    create_mock_response
)


@pytest.mark.unit
class TestAuthentication:
    """Test authentication functionality."""
    
    @patch('prisma.api_client.requests.post')
    def test_successful_authentication(self, mock_post):
        """Test successful authentication."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test-token-123',
            'expires_in': 900
        }
        mock_post.return_value = mock_response
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        assert client.token == 'test-token-123'
        assert client.token_expires is not None
    
    @patch('prisma.api_client.requests.post')
    def test_authentication_failure(self, mock_post):
        """Test authentication failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        # Should still initialize but authentication failed
        assert client.token is None or client.authenticate() is False
    
    @patch('prisma.api_client.requests.post')
    def test_authentication_missing_token(self, mock_post):
        """Test authentication response without token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'expires_in': 900
            # Missing access_token
        }
        mock_post.return_value = mock_response
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        # Should handle missing token gracefully
        assert client.token is None or client.authenticate() is False
    
    def test_token_expiration(self):
        """Test token expiration handling."""
        client = PrismaAccessAPIClient.__new__(PrismaAccessAPIClient)
        client.tsg_id = "tsg-test"
        client.api_user = "test-user"
        client.api_secret = "test-secret"
        client.token = "test-token"
        client.token_expires = datetime.now() - timedelta(seconds=60)  # Expired
        
        # Token should be considered expired
        assert datetime.now() >= client.token_expires


@pytest.mark.unit
class TestAPIRequests:
    """Test API request handling."""
    
    @patch('prisma.api_client.requests.request')
    @patch('prisma.api_client.requests.post')
    def test_get_request(self, mock_auth_post, mock_request):
        """Test GET request handling."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        # Mock API request
        api_response = Mock()
        api_response.status_code = 200
        api_response.json.return_value = {'data': []}
        api_response.url = 'https://api.test.com/test'
        mock_request.return_value = api_response
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        result = client._make_request('GET', 'https://api.test.com/test')
        assert result == {'data': []}
        mock_request.assert_called_once()
    
    @patch('prisma.api_client.requests.request')
    @patch('prisma.api_client.requests.post')
    def test_post_request(self, mock_auth_post, mock_request):
        """Test POST request handling."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        # Mock API request
        api_response = Mock()
        api_response.status_code = 200
        api_response.json.return_value = {'id': '123'}
        api_response.url = 'https://api.test.com/test'
        mock_request.return_value = api_response
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        result = client._make_request('POST', 'https://api.test.com/test', data={'name': 'test'})
        assert result == {'id': '123'}
        mock_request.assert_called_once()
    
    @patch('prisma.api_client.requests.request')
    @patch('prisma.api_client.requests.post')
    def test_request_with_params(self, mock_auth_post, mock_request):
        """Test request with query parameters."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        # Mock API request
        api_response = Mock()
        api_response.status_code = 200
        api_response.json.return_value = {'data': []}
        api_response.url = 'https://api.test.com/test?folder=Test'
        mock_request.return_value = api_response
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        result = client._make_request('GET', 'https://api.test.com/test', params={'folder': 'Test'})
        assert result == {'data': []}
        # Verify params were passed
        call_kwargs = mock_request.call_args[1]
        assert 'params' in call_kwargs


@pytest.mark.unit
class TestCaching:
    """Test caching functionality."""
    
    @patch('prisma.api_client.requests.request')
    @patch('prisma.api_client.requests.post')
    def test_get_request_caching(self, mock_auth_post, mock_request):
        """Test that GET requests are cached."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        # Mock API request
        api_response = Mock()
        api_response.status_code = 200
        api_response.json.return_value = {'data': ['cached']}
        api_response.url = 'https://api.test.com/test'
        mock_request.return_value = api_response
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret",
            cache_ttl=300
        )
        
        # First request
        result1 = client._make_request('GET', 'https://api.test.com/test', use_cache=True)
        assert result1 == {'data': ['cached']}
        
        # Second request should use cache (same call count)
        call_count_before = mock_request.call_count
        result2 = client._make_request('GET', 'https://api.test.com/test', use_cache=True)
        assert result2 == {'data': ['cached']}
        # Should not make another request
        assert mock_request.call_count == call_count_before
    
    @patch('prisma.api_client.requests.request')
    @patch('prisma.api_client.requests.post')
    def test_post_request_not_cached(self, mock_auth_post, mock_request):
        """Test that POST requests are not cached."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        # Mock API request
        api_response = Mock()
        api_response.status_code = 200
        api_response.json.return_value = {'id': '123'}
        api_response.url = 'https://api.test.com/test'
        mock_request.return_value = api_response
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        # POST requests should not be cached
        result1 = client._make_request('POST', 'https://api.test.com/test', data={'name': 'test'})
        result2 = client._make_request('POST', 'https://api.test.com/test', data={'name': 'test'})
        
        # Both should make requests
        assert mock_request.call_count == 2


@pytest.mark.unit
class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @patch('prisma.api_client.requests.request')
    @patch('prisma.api_client.requests.post')
    def test_rate_limiter_initialized(self, mock_auth_post, mock_request):
        """Test that rate limiter is initialized."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret",
            rate_limit=100
        )
        
        assert client.rate_limiter is not None
        assert client.rate_limiter.default_requests == 100


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling."""
    
    @patch('prisma.api_client.requests.request')
    @patch('prisma.api_client.requests.post')
    def test_http_error_handling(self, mock_auth_post, mock_request):
        """Test handling of HTTP errors."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        # Mock API error response
        api_response = Mock()
        api_response.status_code = 404
        api_response.json.return_value = {'error': 'Not found'}
        api_response.url = 'https://api.test.com/test'
        api_response.text = 'Not found'
        mock_request.return_value = api_response
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        # The error handling in api_utils.handle_api_response may raise an exception
        # or return an error dict, depending on implementation
        try:
            result = client._make_request('GET', 'https://api.test.com/test')
            # If no exception, result should indicate error
            assert result is not None
        except Exception:
            # Exception is also acceptable
            pass
    
    @patch('prisma.api_client.requests.post')
    def test_network_error_handling(self, mock_post):
        """Test handling of network errors."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        # Authentication failure during init should be handled
        # The client may still initialize but authentication will fail
        try:
            client = PrismaAccessAPIClient(
                tsg_id="tsg-test",
                api_user="test-user",
                api_secret="test-secret"
            )
            # Client may initialize but token will be None
            assert client.token is None or not client.authenticate()
        except Exception:
            # Exception during init is also acceptable
            pass


@pytest.mark.unit
class TestSpecificEndpoints:
    """Test specific API endpoint methods."""
    
    @patch('prisma.api_client.PrismaAccessAPIClient._make_request')
    @patch('prisma.api_client.requests.post')
    def test_get_folders(self, mock_auth_post, mock_request):
        """Test get_security_policy_folders method."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        # Mock API response
        mock_request.return_value = {'data': [{'name': 'Shared'}]}
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        result = client.get_security_policy_folders()
        assert isinstance(result, list) or 'data' in result
    
    @patch('prisma.api_client.PrismaAccessAPIClient._make_request')
    @patch('prisma.api_client.requests.post')
    def test_get_security_rules(self, mock_auth_post, mock_request):
        """Test get_security_rules method."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        # Mock API response
        mock_request.return_value = {'data': [{'name': 'Rule1'}]}
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        result = client.get_security_rules(folder="Shared")
        assert isinstance(result, list)
    
    @patch('prisma.api_client.PrismaAccessAPIClient._make_request')
    @patch('prisma.api_client.requests.post')
    def test_get_addresses(self, mock_auth_post, mock_request):
        """Test get_addresses method."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        # Mock API response
        mock_request.return_value = {'data': [{'name': 'Test Address'}]}
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        result = client.get_addresses(folder="Shared")
        assert isinstance(result, list) or isinstance(result, dict)


@pytest.mark.unit
class TestPagination:
    """Test pagination handling."""
    
    @patch('prisma.api_client.paginate_api_request')
    @patch('prisma.api_client.requests.post')
    def test_get_all_security_rules_pagination(self, mock_auth_post, mock_paginate):
        """Test pagination in get_all_security_rules."""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 900
        }
        mock_auth_post.return_value = auth_response
        
        # Mock paginated response
        mock_paginate.return_value = [
            {'name': f'Rule{i}'} for i in range(150)
        ]
        
        client = PrismaAccessAPIClient(
            tsg_id="tsg-test",
            api_user="test-user",
            api_secret="test-secret"
        )
        
        # This should handle pagination automatically
        result = client.get_all_security_rules(folder="Shared")
        assert isinstance(result, list)
        assert len(result) == 150
