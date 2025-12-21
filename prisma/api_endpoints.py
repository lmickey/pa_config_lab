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
