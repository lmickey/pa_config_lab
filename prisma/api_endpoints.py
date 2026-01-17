"""
Prisma Access API endpoint definitions.

This module centralizes all Prisma Access API endpoint URLs and provides
helper functions for constructing API requests.

Note: Prisma Access uses two different API bases:
- Strata API: For folders and some infrastructure endpoints
- SASE API: For security policies, objects, profiles, etc.
"""

# Base URLs for Prisma Access APIs
# Note: Folders endpoint uses /setup/v1/ path, not /v1/
STRATA_BASE_URL = "https://api.strata.paloaltonetworks.com/config/v1"
STRATA_SETUP_BASE_URL = "https://api.strata.paloaltonetworks.com/config/setup/v1"
SASE_BASE_URL = "https://api.sase.paloaltonetworks.com/sse/config/v1"

# Authentication endpoint
AUTH_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"


# Folder restrictions for API endpoints
# Some endpoints don't support certain folders (will return 400 errors)
# Format: endpoint_type -> list of EXCLUDED folders (folders that DON'T work)
FOLDER_EXCLUSIONS = {
    # These endpoints explicitly exclude "Service Connections" folder
    'http_header_profile': ['Service Connections'],
    'profile_group': ['Service Connections'],
    'security_rule': ['Service Connections'],
    'decryption_rule': ['Service Connections'],
    'authentication_rule': ['Service Connections'],

    # QoS-related items are ONLY allowed in specific folders
    # (handled via FOLDER_ONLY restrictions below)
}

# Folder-only restrictions - endpoints that ONLY work in specific folders
# Format: endpoint_type -> list of ALLOWED folders (only these work)
FOLDER_ONLY = {
    'qos_profile': ['Remote Networks', 'Service Connections'],
    'qos_policy_rule': ['Remote Networks', 'Service Connections'],
    'ike_crypto_profile': ['Remote Networks', 'Service Connections'],
    'ipsec_crypto_profile': ['Remote Networks', 'Service Connections'],
    'ike_gateway': ['Remote Networks', 'Service Connections'],
    'ipsec_tunnel': ['Remote Networks', 'Service Connections'],
    'agent_profile': ['Mobile Users'],
}

# Snippet restrictions - endpoints that don't support snippets at all
# These will return 400 errors if queried with a snippet parameter
SNIPPET_EXCLUSIONS = [
    # Currently no known exclusions - all tested endpoints support snippets
]


def is_folder_allowed(item_type: str, folder: str) -> bool:
    """
    Check if a folder is allowed for a given item type.

    Args:
        item_type: The type of item (e.g., 'security_rule', 'qos_profile')
        folder: The folder name to check

    Returns:
        True if the folder is allowed, False otherwise
    """
    # Check exclusions first
    if item_type in FOLDER_EXCLUSIONS:
        if folder in FOLDER_EXCLUSIONS[item_type]:
            return False

    # Check folder-only restrictions
    if item_type in FOLDER_ONLY:
        if folder not in FOLDER_ONLY[item_type]:
            return False

    return True


def is_snippet_allowed(item_type: str) -> bool:
    """
    Check if snippets are supported for a given item type.

    Args:
        item_type: The type of item (e.g., 'http_header_profile')

    Returns:
        True if snippets are supported, False otherwise
    """
    return item_type not in SNIPPET_EXCLUSIONS


class APIEndpoints:
    """Centralized API endpoint definitions."""

    # Infrastructure endpoints (SASE API)
    SHARED_INFRASTRUCTURE_SETTINGS = f"{SASE_BASE_URL}/shared-infrastructure-settings"
    MOBILE_AGENT_INFRASTRUCTURE = (
        f"{SASE_BASE_URL}/mobile-agent/infrastructure-settings"
    )

    # Service Connections and Remote Networks (SASE API)
    SERVICE_CONNECTIONS = f"{SASE_BASE_URL}/service-connections"
    REMOTE_NETWORKS = f"{SASE_BASE_URL}/remote-networks"

    @staticmethod
    def service_connection(connection_id: str) -> str:
        """Get endpoint for specific service connection."""
        return f"{APIEndpoints.SERVICE_CONNECTIONS}/{connection_id}"

    @staticmethod
    def remote_network(network_id: str) -> str:
        """Get endpoint for specific remote network."""
        return f"{APIEndpoints.REMOTE_NETWORKS}/{network_id}"

    # Security Policy - Folders (Strata API)
    # Note: Folders endpoint uses /setup/v1/ path
    SECURITY_POLICY_FOLDERS = f"{STRATA_SETUP_BASE_URL}/folders"

    @staticmethod
    def security_policy_folder(folder_name: str) -> str:
        """Get endpoint for specific folder."""
        return f"{APIEndpoints.SECURITY_POLICY_FOLDERS}/{folder_name}"

    # Security Policy - Security Rules (SASE API)
    SECURITY_RULES = f"{SASE_BASE_URL}/security-rules"

    @staticmethod
    def security_rule(rule_id: str) -> str:
        """Get endpoint for specific security rule."""
        return f"{APIEndpoints.SECURITY_RULES}/{rule_id}"

    # Security Policy - Snippets (Strata API - uses /setup/v1/ path like folders)
    SECURITY_POLICY_SNIPPETS = f"{STRATA_SETUP_BASE_URL}/snippets"

    @staticmethod
    def security_policy_snippet(snippet_id: str) -> str:
        """Get endpoint for specific snippet by ID."""
        return f"{APIEndpoints.SECURITY_POLICY_SNIPPETS}/{snippet_id}"

    # Objects - Addresses (SASE API)
    ADDRESSES = f"{SASE_BASE_URL}/addresses"

    @staticmethod
    def address(address_id: str) -> str:
        """Get endpoint for specific address object."""
        return f"{APIEndpoints.ADDRESSES}/{address_id}"

    # Objects - Address Groups (SASE API)
    ADDRESS_GROUPS = f"{SASE_BASE_URL}/address-groups"

    @staticmethod
    def address_group(group_id: str) -> str:
        """Get endpoint for specific address group."""
        return f"{APIEndpoints.ADDRESS_GROUPS}/{group_id}"

    # Objects - Services (SASE API)
    SERVICES = f"{SASE_BASE_URL}/services"

    @staticmethod
    def service(service_id: str) -> str:
        """Get endpoint for specific service object."""
        return f"{APIEndpoints.SERVICES}/{service_id}"

    # Objects - Service Groups (SASE API)
    SERVICE_GROUPS = f"{SASE_BASE_URL}/service-groups"

    @staticmethod
    def service_group(group_id: str) -> str:
        """Get endpoint for specific service group."""
        return f"{APIEndpoints.SERVICE_GROUPS}/{group_id}"

    # Objects - Applications (SASE API)
    APPLICATIONS = f"{SASE_BASE_URL}/applications"

    @staticmethod
    def application(app_id: str) -> str:
        """Get endpoint for specific application."""
        return f"{APIEndpoints.APPLICATIONS}/{app_id}"

    # Objects - Application Groups (SASE API)
    APPLICATION_GROUPS = f"{SASE_BASE_URL}/application-groups"

    @staticmethod
    def application_group(group_id: str) -> str:
        """Get endpoint for specific application group."""
        return f"{APIEndpoints.APPLICATION_GROUPS}/{group_id}"

    # Objects - Application Filters (SASE API)
    APPLICATION_FILTERS = f"{SASE_BASE_URL}/application-filters"

    @staticmethod
    def application_filter(filter_id: str) -> str:
        """Get endpoint for specific application filter."""
        return f"{APIEndpoints.APPLICATION_FILTERS}/{filter_id}"

    # Objects - URL Categories (SASE API)
    URL_CATEGORIES = f"{SASE_BASE_URL}/url-categories"

    @staticmethod
    def url_category(category_id: str) -> str:
        """Get endpoint for specific URL category."""
        return f"{APIEndpoints.URL_CATEGORIES}/{category_id}"

    # Objects - External Dynamic Lists (SASE API)
    EXTERNAL_DYNAMIC_LISTS = f"{SASE_BASE_URL}/external-dynamic-lists"

    @staticmethod
    def external_dynamic_list(list_id: str) -> str:
        """Get endpoint for specific external dynamic list."""
        return f"{APIEndpoints.EXTERNAL_DYNAMIC_LISTS}/{list_id}"

    # Objects - Schedules (SASE API)
    SCHEDULES = f"{SASE_BASE_URL}/schedules"

    @staticmethod
    def schedule(schedule_id: str) -> str:
        """Get endpoint for specific schedule."""
        return f"{APIEndpoints.SCHEDULES}/{schedule_id}"

    # Objects - FQDN (SASE API)
    FQDN = f"{SASE_BASE_URL}/fqdn"

    @staticmethod
    def fqdn_object(fqdn_id: str) -> str:
        """Get endpoint for specific FQDN object."""
        return f"{APIEndpoints.FQDN}/{fqdn_id}"

    # Profiles - Authentication (SASE API)
    AUTHENTICATION_PROFILES = f"{SASE_BASE_URL}/authentication-profiles"

    @staticmethod
    def authentication_profile(profile_id: str) -> str:
        """Get endpoint for specific authentication profile."""
        return f"{APIEndpoints.AUTHENTICATION_PROFILES}/{profile_id}"
    
    # Rules - Authentication Rules (SASE API)
    AUTHENTICATION_RULES = f"{SASE_BASE_URL}/authentication-rules"
    
    @staticmethod
    def authentication_rule(rule_id: str) -> str:
        """Get endpoint for specific authentication rule."""
        return f"{APIEndpoints.AUTHENTICATION_RULES}/{rule_id}"
    
    # Rules - Decryption Rules (SASE API)
    DECRYPTION_RULES = f"{SASE_BASE_URL}/decryption-rules"

    @staticmethod
    def decryption_rule(rule_id: str) -> str:
        """Get endpoint for specific decryption rule."""
        return f"{APIEndpoints.DECRYPTION_RULES}/{rule_id}"

    # Rules - QoS Policy Rules (SASE API)
    QOS_POLICY_RULES = f"{SASE_BASE_URL}/qos-policy-rules"

    @staticmethod
    def qos_policy_rule(rule_id: str) -> str:
        """Get endpoint for specific QoS policy rule."""
        return f"{APIEndpoints.QOS_POLICY_RULES}/{rule_id}"

    # Objects - Tags (SASE API)
    TAGS = f"{SASE_BASE_URL}/tags"

    @staticmethod
    def tag(tag_id: str) -> str:
        """Get endpoint for specific tag."""
        return f"{APIEndpoints.TAGS}/{tag_id}"

    # Objects - Regions (Address Regions) (SASE API)
    REGIONS = f"{SASE_BASE_URL}/regions"

    @staticmethod
    def region(region_id: str) -> str:
        """Get endpoint for specific region."""
        return f"{APIEndpoints.REGIONS}/{region_id}"

    # Local Users and Groups (SASE API)
    LOCAL_USERS = f"{SASE_BASE_URL}/local-users"
    LOCAL_USER_GROUPS = f"{SASE_BASE_URL}/local-user-groups"

    @staticmethod
    def local_user(user_id: str) -> str:
        """Get endpoint for specific local user."""
        return f"{APIEndpoints.LOCAL_USERS}/{user_id}"

    @staticmethod
    def local_user_group(group_id: str) -> str:
        """Get endpoint for specific local user group."""
        return f"{APIEndpoints.LOCAL_USER_GROUPS}/{group_id}"

    # Profiles - Security Profiles (SASE API)
    # Note: These endpoints use the format /{profile-type}-profiles (not /security-profiles/{type})
    ANTI_SPYWARE_PROFILES = f"{SASE_BASE_URL}/anti-spyware-profiles"
    DNS_SECURITY_PROFILES = f"{SASE_BASE_URL}/dns-security-profiles"
    FILE_BLOCKING_PROFILES = f"{SASE_BASE_URL}/file-blocking-profiles"
    HTTP_HEADER_PROFILES = f"{SASE_BASE_URL}/http-header-profiles"
    PROFILE_GROUPS = f"{SASE_BASE_URL}/profile-groups"
    URL_ACCESS_PROFILES = f"{SASE_BASE_URL}/url-access-profiles"
    VULNERABILITY_PROTECTION_PROFILES = (
        f"{SASE_BASE_URL}/vulnerability-protection-profiles"
    )
    WILDFIRE_ANTI_VIRUS_PROFILES = f"{SASE_BASE_URL}/wildfire-anti-virus-profiles"

    # Profiles - Decryption Profiles (SASE API)
    DECRYPTION_PROFILES = f"{SASE_BASE_URL}/decryption-profiles"

    # Profiles - Certificate Profiles (SASE API)
    CERTIFICATE_PROFILES = f"{SASE_BASE_URL}/certificate-profiles"

    # Profiles - QoS Profiles (SASE API)
    QOS_PROFILES = f"{SASE_BASE_URL}/qos-profiles"

    @staticmethod
    def qos_profile(profile_id: str) -> str:
        """Get endpoint for specific QoS profile."""
        return f"{APIEndpoints.QOS_PROFILES}/{profile_id}"

    # Profiles - Profile Groups (SASE API)
    PROFILE_GROUPS = f"{SASE_BASE_URL}/profile-groups"

    @staticmethod
    def anti_spyware_profile(profile_id: str) -> str:
        """Get endpoint for specific anti-spyware profile."""
        return f"{APIEndpoints.ANTI_SPYWARE_PROFILES}/{profile_id}"

    @staticmethod
    def dns_security_profile(profile_id: str) -> str:
        """Get endpoint for specific DNS security profile."""
        return f"{APIEndpoints.DNS_SECURITY_PROFILES}/{profile_id}"

    @staticmethod
    def file_blocking_profile(profile_id: str) -> str:
        """Get endpoint for specific file blocking profile."""
        return f"{APIEndpoints.FILE_BLOCKING_PROFILES}/{profile_id}"

    @staticmethod
    def http_header_profile(profile_id: str) -> str:
        """Get endpoint for specific HTTP header profile."""
        return f"{APIEndpoints.HTTP_HEADER_PROFILES}/{profile_id}"

    @staticmethod
    def profile_group(profile_id: str) -> str:
        """Get endpoint for specific profile group."""
        return f"{APIEndpoints.PROFILE_GROUPS}/{profile_id}"

    @staticmethod
    def url_access_profile(profile_id: str) -> str:
        """Get endpoint for specific URL access profile."""
        return f"{APIEndpoints.URL_ACCESS_PROFILES}/{profile_id}"

    @staticmethod
    def vulnerability_protection_profile(profile_id: str) -> str:
        """Get endpoint for specific vulnerability protection profile."""
        return f"{APIEndpoints.VULNERABILITY_PROTECTION_PROFILES}/{profile_id}"

    @staticmethod
    def wildfire_anti_virus_profile(profile_id: str) -> str:
        """Get endpoint for specific WildFire antivirus profile."""
        return f"{APIEndpoints.WILDFIRE_ANTI_VIRUS_PROFILES}/{profile_id}"

    @staticmethod
    def decryption_profile(profile_id: str) -> str:
        """Get endpoint for specific decryption profile."""
        return f"{APIEndpoints.DECRYPTION_PROFILES}/{profile_id}"
    
    @staticmethod
    def profile_group(group_id: str) -> str:
        """Get endpoint for specific profile group."""
        return f"{APIEndpoints.PROFILE_GROUPS}/{group_id}"

    # Network - IKE Crypto Profiles (SASE API)
    IKE_CRYPTO_PROFILES = f"{SASE_BASE_URL}/ike-crypto-profiles"

    @staticmethod
    def ike_crypto_profile(profile_id: str) -> str:
        """Get endpoint for specific IKE crypto profile."""
        return f"{APIEndpoints.IKE_CRYPTO_PROFILES}/{profile_id}"

    # Network - IPSec Crypto Profiles (SASE API)
    IPSEC_CRYPTO_PROFILES = f"{SASE_BASE_URL}/ipsec-crypto-profiles"

    @staticmethod
    def ipsec_crypto_profile(profile_id: str) -> str:
        """Get endpoint for specific IPSec crypto profile."""
        return f"{APIEndpoints.IPSEC_CRYPTO_PROFILES}/{profile_id}"

    # Network - IKE Gateways (SASE API)
    IKE_GATEWAYS = f"{SASE_BASE_URL}/ike-gateways"

    @staticmethod
    def ike_gateway(gateway_id: str) -> str:
        """Get endpoint for specific IKE gateway."""
        return f"{APIEndpoints.IKE_GATEWAYS}/{gateway_id}"

    # Network - IPSec Tunnels (SASE API)
    IPSEC_TUNNELS = f"{SASE_BASE_URL}/ipsec-tunnels"

    @staticmethod
    def ipsec_tunnel(tunnel_id: str) -> str:
        """Get endpoint for specific IPSec tunnel."""
        return f"{APIEndpoints.IPSEC_TUNNELS}/{tunnel_id}"

    # Mobile User Infrastructure (SASE API)
    # Mobile Agent Configuration - GlobalProtect settings are split across multiple endpoints
    MOBILE_AGENT_PROFILES = f"{SASE_BASE_URL}/mobile-agent/agent-profiles"
    MOBILE_AGENT_VERSIONS = f"{SASE_BASE_URL}/mobile-agent/agent-versions"
    MOBILE_AGENT_AUTH_SETTINGS = f"{SASE_BASE_URL}/mobile-agent/authentication-settings"
    MOBILE_AGENT_ENABLE = f"{SASE_BASE_URL}/mobile-agent/enable"
    MOBILE_AGENT_GLOBAL_SETTINGS = f"{SASE_BASE_URL}/mobile-agent/global-settings"
    MOBILE_AGENT_INFRA_SETTINGS = f"{SASE_BASE_URL}/mobile-agent/infrastructure-settings"
    MOBILE_AGENT_LOCATIONS = f"{SASE_BASE_URL}/mobile-agent/locations"
    MOBILE_AGENT_TUNNEL_PROFILES = f"{SASE_BASE_URL}/mobile-agent/tunnel-profiles"

    # HIP (Host Information Profile) Objects and Profiles (SASE API)
    # Note: These endpoints may vary by environment - validation needed
    HIP_OBJECTS = f"{SASE_BASE_URL}/hip-objects"
    HIP_PROFILES = f"{SASE_BASE_URL}/hip-profiles"

    @staticmethod
    def hip_object(object_id: str) -> str:
        """Get endpoint for specific HIP object."""
        return f"{APIEndpoints.HIP_OBJECTS}/{object_id}"

    @staticmethod
    def hip_profile(profile_id: str) -> str:
        """Get endpoint for specific HIP profile."""
        return f"{APIEndpoints.HIP_PROFILES}/{profile_id}"

    # Auto Tag Actions (Infrastructure - no folder parameter)
    AUTO_TAG_ACTIONS = f"{SASE_BASE_URL}/auto-tag-actions"

    @staticmethod
    def auto_tag_action(action_id: str) -> str:
        """Get endpoint for specific auto tag action."""
        return f"{APIEndpoints.AUTO_TAG_ACTIONS}/{action_id}"

    # Regions and Bandwidth Allocations (SASE API)
    BANDWIDTH_ALLOCATIONS = f"{SASE_BASE_URL}/bandwidth-allocations"
    LOCATIONS = f"{SASE_BASE_URL}/locations"

    @staticmethod
    def bandwidth_allocation(allocation_id: str) -> str:
        """Get endpoint for specific bandwidth allocation."""
        return f"{APIEndpoints.BANDWIDTH_ALLOCATIONS}/{allocation_id}"

    # Configuration Management (SASE API)
    CONFIG_VERSIONS = f"{SASE_BASE_URL}/config-versions"
    CONFIG_PUSH = f"{SASE_BASE_URL}/config-versions/candidate:push"
    JOBS = f"{SASE_BASE_URL}/jobs"

    @staticmethod
    def job(job_id: str) -> str:
        """Get endpoint for specific job."""
        return f"{APIEndpoints.JOBS}/{job_id}"


def build_folder_query(folder: str) -> str:
    """
    Build query string for folder parameter with proper URL encoding.

    Args:
        folder: Folder name (e.g., "Mobile Users" -> "Mobile%20Users")

    Returns:
        Query string with URL-encoded folder name (uses %20 for spaces)
    """
    from urllib.parse import quote

    # Use quote() instead of quote_plus() to get %20 instead of + for spaces
    encoded_folder = quote(folder, safe="")
    return f"?folder={encoded_folder}"


def build_snippet_query(snippet: str) -> str:
    """
    Build query string for snippet parameter with proper URL encoding.

    Args:
        snippet: Snippet name (e.g., "Shared Internet" -> "Shared%20Internet")

    Returns:
        Query string with URL-encoded snippet name (uses %20 for spaces)
    """
    from urllib.parse import quote

    # Use quote() instead of quote_plus() to get %20 instead of + for spaces
    encoded_snippet = quote(snippet, safe="")
    return f"?snippet={encoded_snippet}"


def build_pagination_query(limit: int = 100, offset: int = 0) -> str:
    """
    Build query string for pagination.

    Args:
        limit: Number of items per page
        offset: Offset for pagination

    Returns:
        Query string
    """
    return f"&limit={limit}&offset={offset}"
