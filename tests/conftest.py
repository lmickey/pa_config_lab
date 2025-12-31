"""
Pytest configuration and fixtures for Prisma Access Configuration Capture tests.

This module provides:
- Test fixtures for API client mocking
- Test data generators
- Mock API responses
- Common test utilities
- Dynamic coverage threshold adjustment based on credentials
"""

import os
import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List, Optional
from datetime import datetime
import secrets
from cryptography.fernet import Fernet
from config.storage.json_storage import derive_key


def pytest_configure(config):
    """
    Configure pytest based on environment.
    
    Dynamically adjusts coverage threshold based on whether API credentials
    are available (which means integration tests can run).
    """
    # Check if API credentials are available
    has_credentials = all([
        os.getenv("PRISMA_TSG_ID"),
        os.getenv("PRISMA_API_USER"),
        os.getenv("PRISMA_API_SECRET")
    ])
    
    # Store credential status for use in tests
    config._has_api_credentials = has_credentials
    
    # Adjust coverage threshold based on credentials
    # Modify the option after pytest-cov has added it
    # Note: This may not work if pytest-cov reads the value before this hook runs
    if has_credentials:
        target_threshold = 70
        if hasattr(config.option, 'cov_fail_under'):
            original = getattr(config.option, 'cov_fail_under', None)
            # Force override threshold when credentials are available
            setattr(config.option, 'cov_fail_under', target_threshold)
            # Also try setting in the underlying dict
            if hasattr(config.option, '__dict__'):
                config.option.__dict__['cov_fail_under'] = target_threshold
            print(f"\n[Coverage] Credentials detected - coverage threshold set to {target_threshold}% (was {original})")
    else:
        target_threshold = 55
        if hasattr(config.option, 'cov_fail_under'):
            original = getattr(config.option, 'cov_fail_under', None)
            if original != target_threshold:
                setattr(config.option, 'cov_fail_under', target_threshold)
                if hasattr(config.option, '__dict__'):
                    config.option.__dict__['cov_fail_under'] = target_threshold
            print(f"\n[Coverage] No credentials detected - coverage threshold is {target_threshold}%")


def pytest_configure(config):
    """
    Configure pytest based on environment.
    
    Stores credential status for use in tests.
    """
    # Check if API credentials are available
    has_credentials = all([
        os.getenv("PRISMA_TSG_ID"),
        os.getenv("PRISMA_API_USER"),
        os.getenv("PRISMA_API_SECRET")
    ])
    
    # Store credential status for use in tests
    config._has_api_credentials = has_credentials


@pytest.fixture(scope="session")
def has_api_credentials(pytestconfig):
    """Fixture to check if API credentials are available."""
    return getattr(pytestconfig, '_has_api_credentials', False)


# ============================================================================
# Mock API Client Fixtures
# ============================================================================

@pytest.fixture
def mock_api_client():
    """Create a mock PrismaAccessAPIClient."""
    client = Mock()
    client.tsg_id = "tsg-test-1234567890"
    client.api_user = "test-client-id"
    client.api_secret = "test-client-secret"
    client.token = "mock-access-token"
    client.token_expires = datetime.now()
    return client


@pytest.fixture
def mock_authenticated_api_client(mock_api_client):
    """Create a mock API client with successful authentication."""
    mock_api_client.authenticate.return_value = True
    return mock_api_client


# ============================================================================
# Test Data Generators
# ============================================================================

def generate_folder_data(name: str = "Test Folder", is_default: bool = False) -> Dict[str, Any]:
    """Generate mock folder data."""
    return {
        "id": f"folder-{name.lower().replace(' ', '-')}",
        "name": name,
        "path": f"/config/security-policy/folders/{name}",
        "is_default": is_default,
        "parent_folder": None
    }


def generate_rule_data(
    name: str = "Test Rule",
    folder: str = "Test Folder",
    position: int = 1
) -> Dict[str, Any]:
    """Generate mock security rule data."""
    return {
        "id": f"rule-{name.lower().replace(' ', '-')}",
        "name": name,
        "description": f"Test rule: {name}",
        "position": position,
        "enabled": True,
        "folder": folder,
        "source": ["any"],
        "destination": ["any"],
        "application": ["any"],
        "service": ["application-default"],
        "action": "allow",
        "log_setting": "",
        "log_start": False,
        "log_end": False,
        "profile_setting": {},
        "security_profile": [],
        "authentication_profile": [],
        "decryption_profile": [],
        "tags": [],
        "created": "2024-01-01T00:00:00Z",
        "updated": "2024-01-01T00:00:00Z"
    }


def generate_address_object_data(
    name: str = "Test Address",
    folder: str = "Test Folder",
    value: str = "192.168.1.1"
) -> Dict[str, Any]:
    """Generate mock address object data."""
    return {
        "id": f"addr-{name.lower().replace(' ', '-')}",
        "name": name,
        "description": f"Test address: {name}",
        "type": "ip_netmask",
        "value": value,
        "folder": folder,
        "tags": [],
        "created": "2024-01-01T00:00:00Z",
        "updated": "2024-01-01T00:00:00Z"
    }


def generate_address_group_data(
    name: str = "Test Address Group",
    folder: str = "Test Folder",
    addresses: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Generate mock address group data."""
    if addresses is None:
        addresses = ["Test Address"]
    
    return {
        "id": f"addrgrp-{name.lower().replace(' ', '-')}",
        "name": name,
        "description": f"Test address group: {name}",
        "static": addresses,
        "dynamic": [],
        "folder": folder,
        "tags": [],
        "created": "2024-01-01T00:00:00Z",
        "updated": "2024-01-01T00:00:00Z"
    }


def generate_profile_data(
    name: str = "Test Profile",
    profile_type: str = "authentication",
    folder: str = "Test Folder"
) -> Dict[str, Any]:
    """Generate mock profile data."""
    base_data = {
        "id": f"prof-{name.lower().replace(' ', '-')}",
        "name": name,
        "description": f"Test profile: {name}",
        "folder": folder,
        "tags": [],
        "created": "2024-01-01T00:00:00Z",
        "updated": "2024-01-01T00:00:00Z"
    }
    
    if profile_type == "authentication":
        base_data.update({
            "type": "authentication",
            "method": {}
        })
    elif profile_type.startswith("security_"):
        base_data.update({
            "type": profile_type.replace("security_", ""),
            "settings": {}
        })
    elif profile_type == "decryption":
        base_data.update({
            "type": "decryption",
            "settings": {}
        })
    
    return base_data


def generate_snippet_data(
    name: str = "Test Snippet",
    is_default: bool = False
) -> Dict[str, Any]:
    """Generate mock snippet data."""
    return {
        "id": f"snippet-{name.lower().replace(' ', '-')}",
        "name": name,
        "path": f"/config/security-policy/snippets/{name}",
        "description": f"Test snippet: {name}",
        "is_default": is_default,
        "folders": [],
        "shared_in": "local",
        "last_update": "2024-01-01T00:00:00Z",
        "created_in": "2024-01-01T00:00:00Z"
    }


# ============================================================================
# Mock API Response Fixtures
# ============================================================================

@pytest.fixture
def mock_folders_response():
    """Mock response for folders API."""
    return {
        "data": [
            generate_folder_data("Shared", is_default=True),
            generate_folder_data("Mobile Users", is_default=False),
            generate_folder_data("Test Folder", is_default=False)
        ]
    }


@pytest.fixture
def mock_rules_response():
    """Mock response for security rules API."""
    return {
        "data": [
            generate_rule_data("Allow All", "Shared", position=1),
            generate_rule_data("Block Malicious", "Shared", position=2),
            generate_rule_data("Test Rule", "Mobile Users", position=1)
        ]
    }


@pytest.fixture
def mock_addresses_response():
    """Mock response for address objects API."""
    return {
        "data": [
            generate_address_object_data("Test Address", "Shared", "192.168.1.1"),
            generate_address_object_data("Server IP", "Mobile Users", "10.0.0.1")
        ]
    }


@pytest.fixture
def mock_address_groups_response():
    """Mock response for address groups API."""
    return {
        "data": [
            generate_address_group_data("Test Group", "Shared", ["Test Address"]),
            generate_address_group_data("Servers", "Mobile Users", ["Server IP"])
        ]
    }


@pytest.fixture
def mock_profiles_response():
    """Mock response for profiles API."""
    return {
        "data": [
            generate_profile_data("Default Auth", "authentication", "Shared"),
            generate_profile_data("Test Auth", "authentication", "Mobile Users"),
            generate_profile_data("Default AV", "security_antivirus", "Shared")
        ]
    }


@pytest.fixture
def mock_snippets_response():
    """Mock response for snippets API."""
    return {
        "data": [
            generate_snippet_data("predefined-snippet", is_default=True),
            generate_snippet_data("custom-snippet", is_default=False)
        ]
    }


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sample_config_v2():
    """Generate a sample v2.0 configuration."""
    return {
        "metadata": {
            "version": "2.0.0",
            "created": "2024-01-01T00:00:00Z",
            "source_tenant": "tsg-test-1234567890",
            "source_type": "scm",
            "pull_stats": {
                "folders": 2,
                "rules": 3,
                "objects": 4,
                "profiles": 2,
                "snippets": 1,
                "errors": 0,
                "elapsed_seconds": 5.5
            }
        },
        "infrastructure": {
            "shared_infrastructure_settings": {},
            "mobile_agent": {},
            "service_connections": [],
            "remote_networks": []
        },
        "security_policies": {
            "folders": [
                {
                    "name": "Shared",
                    "path": "/config/security-policy/folders/Shared",
                    "is_default": True,
                    "security_rules": [
                        generate_rule_data("Allow All", "Shared", 1)
                    ],
                    "objects": {
                        "address_objects": [
                            generate_address_object_data("Test Address", "Shared")
                        ],
                        "address_groups": [],
                        "service_objects": [],
                        "service_groups": [],
                        "applications": []
                    },
                    "profiles": {
                        "authentication_profiles": [
                            generate_profile_data("Default Auth", "authentication", "Shared")
                        ],
                        "security_profiles": {},
                        "decryption_profiles": {}  # Schema expects object, not list
                    },
                    "parent_dependencies": {}
                }
            ],
            "snippets": [
                generate_snippet_data("custom-snippet", is_default=False)
            ]
        }
    }


# ============================================================================
# Utility Functions
# ============================================================================

def create_mock_response(data: Any, status_code: int = 200) -> Mock:
    """Create a mock HTTP response."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = data
    response.text = str(data)
    response.ok = status_code < 400
    return response


@pytest.fixture
def temp_password():
    """Generate a temporary password for encryption/decryption tests."""
    return secrets.token_urlsafe(32)


@pytest.fixture
def temp_cipher(temp_password):
    """Generate a temporary Fernet cipher for encryption/decryption tests."""
    cipher, salt = derive_key(temp_password)
    return cipher


def create_mock_api_client_with_responses(responses: Dict[str, Any]) -> Mock:
    """
    Create a mock API client with predefined responses.
    
    Args:
        responses: Dictionary mapping method names to response data
        
    Returns:
        Mock API client
    """
    client = Mock()
    
    # Set up authentication
    client.authenticate.return_value = True
    client.token = "mock-token"
    
    # Set up method responses
    for method_name, response_data in responses.items():
        if hasattr(client, method_name):
            method = getattr(client, method_name)
            if isinstance(response_data, Exception):
                method.side_effect = response_data
            else:
                method.return_value = response_data
    
    return client
