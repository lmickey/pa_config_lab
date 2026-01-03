"""
Pytest configuration and fixtures for model tests.

This file is auto-generated from production examples.
"""

import pytest
import json
from pathlib import Path


# Fixture directory
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def load_fixtures(category: str, type_name: str = None):
    """
    Load fixtures for a category or specific type.
    
    Args:
        category: Category name (objects, profiles, policies, infrastructure)
        type_name: Optional specific type name
    
    Returns:
        List of fixture dictionaries or dict of all types
    """
    if type_name:
        fixture_file = FIXTURE_DIR / category / f"{type_name}.json"
        if fixture_file.exists():
            with open(fixture_file, 'r') as f:
                return json.load(f)
        return []
    else:
        fixture_file = FIXTURE_DIR / category / f"all_{category}.json"
        if fixture_file.exists():
            with open(fixture_file, 'r') as f:
                return json.load(f)
        return {}


# Category fixtures
@pytest.fixture
def all_object_fixtures():
    """Load all object fixtures"""
    return load_fixtures('objects')


@pytest.fixture
def all_profile_fixtures():
    """Load all profile fixtures"""
    return load_fixtures('profiles')


@pytest.fixture
def all_policy_fixtures():
    """Load all policy fixtures"""
    return load_fixtures('policies')


@pytest.fixture
def all_infrastructure_fixtures():
    """Load all infrastructure fixtures"""
    return load_fixtures('infrastructure')


# Individual type fixtures (generated below)

@pytest.fixture
def tag_fixtures():
    """Load tag fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'tag')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def address_object_fixtures():
    """Load address_object fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'address_object')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def address_group_fixtures():
    """Load address_group fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'address_group')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def service_object_fixtures():
    """Load service_object fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'service_object')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def service_group_fixtures():
    """Load service_group fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'service_group')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def application_object_fixtures():
    """Load application_object fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'application_object')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def application_group_fixtures():
    """Load application_group fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'application_group')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def application_filter_fixtures():
    """Load application_filter fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'application_filter')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def schedule_fixtures():
    """Load schedule fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'schedule')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def authentication_profile_fixtures():
    """Load authentication_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'authentication_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def decryption_profile_fixtures():
    """Load decryption_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'decryption_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def url_filtering_profile_fixtures():
    """Load url_filtering_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'url_filtering_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def antivirus_profile_fixtures():
    """Load antivirus_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'antivirus_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def anti_spyware_profile_fixtures():
    """Load anti_spyware_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'anti_spyware_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def vulnerability_profile_fixtures():
    """Load vulnerability_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'vulnerability_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def file_blocking_profile_fixtures():
    """Load file_blocking_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'file_blocking_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def wildfire_profile_fixtures():
    """Load wildfire_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'wildfire_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def profile_group_fixtures():
    """Load profile_group fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'profile_group')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def hip_profile_fixtures():
    """Load hip_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'hip_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def hip_object_fixtures():
    """Load hip_object fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'hip_object')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def http_header_profile_fixtures():
    """Load http_header_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'http_header_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def certificate_profile_fixtures():
    """Load certificate_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'certificate_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def ocsp_responder_fixtures():
    """Load ocsp_responder fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'ocsp_responder')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def scep_profile_fixtures():
    """Load scep_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'scep_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def qos_profile_fixtures():
    """Load qos_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'qos_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def security_rule_fixtures():
    """Load security_rule fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'security_rule')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def decryption_rule_fixtures():
    """Load decryption_rule fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'decryption_rule')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def authentication_rule_fixtures():
    """Load authentication_rule fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'authentication_rule')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def qos_policy_rule_fixtures():
    """Load qos_policy_rule fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'qos_policy_rule')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def ike_crypto_profile_fixtures():
    """Load ike_crypto_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'ike_crypto_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def ipsec_crypto_profile_fixtures():
    """Load ipsec_crypto_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'ipsec_crypto_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def ike_gateway_fixtures():
    """Load ike_gateway fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'ike_gateway')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def ipsec_tunnel_fixtures():
    """Load ipsec_tunnel fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'ipsec_tunnel')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def service_connection_fixtures():
    """Load service_connection fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'service_connection')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def agent_profile_fixtures():
    """Load agent_profile fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'agent_profile')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def portal_fixtures():
    """Load portal fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'portal')
        if fixtures:
            return fixtures
    return []

@pytest.fixture
def gateway_fixtures():
    """Load gateway fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, 'gateway')
        if fixtures:
            return fixtures
    return []
