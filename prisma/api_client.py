"""
Enhanced Prisma Access API client.

This module provides a comprehensive API client for interacting with
Prisma Access SCM API, including authentication, request handling,
pagination, rate limiting, and caching.
"""

import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from urllib.parse import quote

from .api_endpoints import (
    APIEndpoints,
    AUTH_URL,
    build_folder_query,
)
from .api_utils import (
    RateLimiter,
    APICache,
    handle_api_response,
    retry_on_failure,
    paginate_api_request,
    build_headers,
)


def encode_folder_name(folder: str) -> str:
    """
    Encode folder name for API requests.

    The Prisma Access API expects %20 encoding for spaces, not + encoding.
    This function ensures folder names are properly encoded.

    Args:
        folder: Folder name (e.g., "Access Agent")

    Returns:
        URL-encoded folder name (e.g., "Access%20Agent")
    """
    return quote(folder, safe="")


class PrismaAccessAPIClient:
    """
    Enhanced API client for Prisma Access SCM.

    Features:
    - Automatic authentication and token refresh
    - Rate limiting
    - Response caching
    - Pagination handling
    - Error handling and retries
    """

    def __init__(
        self,
        tsg_id: str,
        api_user: str,
        api_secret: str,
        rate_limit: int = 45,  # Changed from 100 to 45 (90% of 50 req/min for safety buffer)
        cache_ttl: int = 300,
    ):
        """
        Initialize API client.

        Args:
            tsg_id: Tenant Service Group ID
            api_user: API client ID
            api_secret: API client secret
            rate_limit: Maximum requests per minute (default: 45 - 90% of 50 req/min limit)
            cache_ttl: Cache time-to-live in seconds
        """
        self.tsg_id = tsg_id
        self.api_user = api_user
        self.api_secret = api_secret

        self.token: Optional[str] = None
        self.token_expires: Optional[datetime] = None

        self.rate_limiter = RateLimiter(max_requests=rate_limit, time_window=60)
        self.cache = APICache(ttl=cache_ttl)

        # Authenticate on initialization
        self.authenticate()

    def authenticate(self) -> bool:
        """
        Authenticate and obtain access token using SCM Authentication Service.

        Uses basic auth with Client ID as username and Client Secret as password.
        Sends grant_type and scope as form data in request body.

        Returns:
            True if successful, False otherwise
        """
        try:
            scope = f"tsg_id:{self.tsg_id}"

            # Form data in request body (not query params)
            data = {"grant_type": "client_credentials", "scope": scope}

            # Headers for form-urlencoded content type
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            # Basic auth: Client ID as username, Client Secret as password
            response = requests.post(
                AUTH_URL,
                auth=(self.api_user, self.api_secret),
                data=data,  # Form data in body, not params
                headers=headers,
            )

            if response.status_code == 200:
                response_data = response.json()
                self.token = response_data.get("access_token")

                if not self.token:
                    print("Authentication succeeded but no access_token in response")
                    return False

                # Tokens expire in 15 minutes (900 seconds)
                expires_in = response_data.get("expires_in", 900)
                self.token_expires = datetime.now() + timedelta(
                    seconds=expires_in - 60
                )  # Refresh 1 min early

                return True
            else:
                print(
                    f"Authentication failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            print(f"Authentication error: {e}")
            return False

    def _ensure_token(self) -> bool:
        """Ensure we have a valid token."""
        if not self.token or (
            self.token_expires and datetime.now() >= self.token_expires
        ):
            return self.authenticate()
        return True

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        if not self._ensure_token():
            raise Exception("Failed to authenticate")

        return build_headers(self.token)

    @retry_on_failure(max_retries=3, backoff_factor=1.0)
    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Make API request with rate limiting and caching.

        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            data: Request body data
            use_cache: Whether to use cache for GET requests

        Returns:
            Response data
        """
        # Check cache for GET requests
        if method.upper() == "GET" and use_cache:
            cache_key = f"{method}:{url}:{params}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Rate limiting
        self.rate_limiter.wait_if_needed()

        # Make request
        headers = self._get_headers()

        # Prepare request details for error logging
        # Note: The actual final URL will be logged from response.url after the request
        request_details = {
            "method": method,
            "url": url,  # Base URL (final URL with merged params will be in response.url)
            "headers": headers,
            "params": params,
            "data": data if data and method.upper() != "GET" else None,
            "json": (
                data if data and method.upper() in ["POST", "PUT", "PATCH"] else None
            ),
        }

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data if data else None,
        )

        result = handle_api_response(response, request_details)

        # Cache GET requests
        if method.upper() == "GET" and use_cache:
            cache_key = f"{method}:{url}:{params}"
            self.cache.set(cache_key, result)

        return result

    # Infrastructure endpoints

    def get_shared_infrastructure_settings(self) -> Dict[str, Any]:
        """Get shared infrastructure settings."""
        return self._make_request("GET", APIEndpoints.SHARED_INFRASTRUCTURE_SETTINGS)

    def get_mobile_agent_infrastructure(self) -> List[Dict[str, Any]]:
        """Get mobile agent infrastructure settings."""
        response = self._make_request("GET", APIEndpoints.MOBILE_AGENT_INFRASTRUCTURE)
        if isinstance(response, list):
            return response
        return response.get("data", [])

    # Service Connections and Remote Networks

    def get_service_connections(
        self, folder: str = "Service Connections"
    ) -> List[Dict[str, Any]]:
        """Get service connections."""
        # Build query string manually to ensure %20 encoding (not +)
        url = APIEndpoints.SERVICE_CONNECTIONS + build_folder_query(folder)
        response = self._make_request("GET", url)
        return response.get("data", [])

    def get_remote_networks(
        self, folder: str = "Remote Networks"
    ) -> List[Dict[str, Any]]:
        """Get remote networks."""
        # Build query string manually to ensure %20 encoding (not +)
        url = APIEndpoints.REMOTE_NETWORKS + build_folder_query(folder)
        response = self._make_request("GET", url)
        return response.get("data", [])

    # Security Policy - Folders

    def get_security_policy_folders(self) -> List[Dict[str, Any]]:
        """
        Get all security policy folders from Strata API.

        Note: Strata API may return 404 if endpoint structure is different.
        In that case, folders should be discovered via alternative methods.
        """
        try:
            response = self._make_request("GET", APIEndpoints.SECURITY_POLICY_FOLDERS)

            # Strata API might return data directly as a list, or wrapped in 'data' key
            if isinstance(response, list):
                return response
            elif isinstance(response, dict):
                # Try common response formats
                if "data" in response:
                    return response["data"]
                elif "items" in response:
                    return response["items"]
                elif "folders" in response:
                    return response["folders"]
                else:
                    # Return empty list if format is unexpected
                    return []
            else:
                return []

        except Exception as e:
            # Don't raise - let alternative discovery methods handle it
            error_msg = str(e)
            if "404" in error_msg or "Not Found" in error_msg:
                # 404 is expected if endpoint doesn't exist - use alternative discovery
                pass
            elif "403" in error_msg or "Forbidden" in error_msg:
                # 403 means no permission - use alternative discovery
                pass
            # Re-raise other errors
            raise

    def get_security_policy_folder(self, folder_name: str) -> Dict[str, Any]:
        """Get specific security policy folder."""
        url = APIEndpoints.security_policy_folder(folder_name)
        response = self._make_request("GET", url)
        return response.get("data", {})

    # Security Policy - Security Rules

    def get_security_rules(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get security rules.

        Args:
            folder: Folder name (optional, will be URL encoded with %20)
            limit: Items per page
            offset: Offset for pagination

        Returns:
            List of security rules
        """
        url = APIEndpoints.SECURITY_RULES
        params = {}

        if folder:
            # Build query string manually to ensure %20 encoding (not +)
            # requests library uses + for spaces, but API expects %20
            url += build_folder_query(folder)

        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset

        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_security_rules(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all security rules with automatic pagination."""

        def api_func(offset=0, limit=100):
            return self.get_security_rules(folder=folder, limit=limit, offset=offset)

        return paginate_api_request(api_func)

    # Security Policy - Snippets

    def get_security_policy_snippets(self) -> List[Dict[str, Any]]:
        """Get all security policy snippets."""
        response = self._make_request("GET", APIEndpoints.SECURITY_POLICY_SNIPPETS)
        return response.get("data", [])

    def get_security_policy_snippet(self, snippet_id: str) -> Dict[str, Any]:
        """
        Get specific security policy snippet by ID.

        Args:
            snippet_id: Snippet ID (not name)

        Returns:
            Snippet data dictionary (response is direct JSON object, not wrapped in 'data')
        """
        url = APIEndpoints.security_policy_snippet(snippet_id)
        response = self._make_request("GET", url)

        # Snippet detail endpoint returns the snippet object directly, not wrapped in 'data'
        # Check if response is already a dict (direct response) or wrapped
        if isinstance(response, dict):
            # If it has 'data' key, use that; otherwise use response directly
            if "data" in response:
                return response["data"]
            else:
                # Response is the snippet object itself
                return response
        else:
            # Unexpected format
            return {}

    # Objects - Addresses

    def get_addresses(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get address objects."""
        url = APIEndpoints.ADDRESSES
        params = {}

        if folder:
            # Build query string manually to ensure %20 encoding (not +)
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset

        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_addresses(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all address objects with automatic pagination."""

        def api_func(offset=0, limit=100):
            return self.get_addresses(folder=folder, limit=limit, offset=offset)

        return paginate_api_request(api_func)

    # Objects - Address Groups

    def get_address_groups(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get address groups."""
        url = APIEndpoints.ADDRESS_GROUPS
        params = {}

        if folder:
            # Build query string manually to ensure %20 encoding (not +)
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset

        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_address_groups(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all address groups with automatic pagination."""

        def api_func(offset=0, limit=100):
            return self.get_address_groups(folder=folder, limit=limit, offset=offset)

        return paginate_api_request(api_func)

    # Service Groups
    def get_service_groups(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get service groups."""
        url = APIEndpoints.SERVICE_GROUPS
        params = {}

        if folder:
            # Build query string manually to ensure %20 encoding (not +)
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset

        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_service_groups(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all service groups with automatic pagination."""

        def api_func(offset=0, limit=100):
            return self.get_service_groups(folder=folder, limit=limit, offset=offset)

        return paginate_api_request(api_func)

    # Services
    def get_services(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get service objects."""
        url = APIEndpoints.SERVICES
        params = {}

        if folder:
            # Build query string manually to ensure %20 encoding (not +)
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset

        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_services(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all service objects with automatic pagination."""

        def api_func(offset=0, limit=100):
            return self.get_services(folder=folder, limit=limit, offset=offset)

        return paginate_api_request(api_func)

    # Applications
    def get_applications(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get application objects."""
        url = APIEndpoints.APPLICATIONS
        params = {}

        if folder:
            # Build query string manually to ensure %20 encoding (not +)
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset

        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_applications(
        self, folder: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all application objects with automatic pagination.
        
        Args:
            folder: Optional folder name to filter results
            limit: Optional maximum number of results to return (None = all results with pagination)
        
        Returns:
            List of application objects
        """
        if limit is not None:
            # If limit specified, just get that many results (no pagination)
            return self.get_applications(folder=folder, limit=limit, offset=0)
        
        # Otherwise use automatic pagination to get all results
        def api_func(offset=0, page_limit=100):
            return self.get_applications(folder=folder, limit=page_limit, offset=offset)

        return paginate_api_request(api_func)

    # Application Groups
    def get_application_groups(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get application groups.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of application groups
        """
        url = APIEndpoints.APPLICATION_GROUPS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_application_groups(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all application groups with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_application_groups(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    # Application Filters
    def get_application_filters(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get application filters.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of application filters
        """
        url = APIEndpoints.APPLICATION_FILTERS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_application_filters(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all application filters with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_application_filters(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    # External Dynamic Lists
    def get_external_dynamic_lists(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get external dynamic lists.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of external dynamic lists
        """
        url = APIEndpoints.EXTERNAL_DYNAMIC_LISTS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_external_dynamic_lists(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all external dynamic lists with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_external_dynamic_lists(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    # FQDN Objects
    def get_fqdn_objects(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get FQDN objects.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of FQDN objects
        """
        url = APIEndpoints.FQDN
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_fqdn_objects(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all FQDN objects with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_fqdn_objects(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    # URL Categories
    def get_url_categories(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get URL filtering categories.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of URL filtering categories
        """
        url = APIEndpoints.URL_CATEGORIES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_url_categories(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all URL filtering categories with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_url_categories(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    # Authentication Profiles
    def get_authentication_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get authentication profiles."""
        url = APIEndpoints.AUTHENTICATION_PROFILES
        params = {}

        if folder:
            # Build query string manually to ensure %20 encoding (not +)
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset

        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_authentication_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all authentication profiles with automatic pagination."""

        def api_func(offset=0, limit=100):
            return self.get_authentication_profiles(
                folder=folder, limit=limit, offset=offset
            )

        return paginate_api_request(api_func)

    # Security Profiles (based on Master-API-Entpoint-List.txt - only those marked "include in test")

    def get_anti_spyware_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get anti-spyware profiles."""
        url = APIEndpoints.ANTI_SPYWARE_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_dns_security_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get DNS security profiles."""
        url = APIEndpoints.DNS_SECURITY_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_file_blocking_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get file blocking profiles."""
        url = APIEndpoints.FILE_BLOCKING_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_http_header_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get HTTP header profiles."""
        url = APIEndpoints.HTTP_HEADER_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_profile_groups(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get profile groups."""
        url = APIEndpoints.PROFILE_GROUPS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_url_access_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get URL access profiles."""
        url = APIEndpoints.URL_ACCESS_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_vulnerability_protection_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get vulnerability protection profiles."""
        url = APIEndpoints.VULNERABILITY_PROTECTION_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_wildfire_anti_virus_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get WildFire antivirus profiles."""
        url = APIEndpoints.WILDFIRE_ANTI_VIRUS_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_decryption_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get decryption profiles."""
        url = APIEndpoints.DECRYPTION_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_decryption_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all decryption profiles with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_decryption_profiles(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    # Security Profiles
    def get_anti_spyware_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get anti-spyware profiles.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of anti-spyware profiles
        """
        url = APIEndpoints.ANTI_SPYWARE_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_anti_spyware_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all anti-spyware profiles with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_anti_spyware_profiles(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_dns_security_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get DNS security profiles.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of DNS security profiles
        """
        url = APIEndpoints.DNS_SECURITY_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_dns_security_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all DNS security profiles with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_dns_security_profiles(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_file_blocking_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get file blocking profiles.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of file blocking profiles
        """
        url = APIEndpoints.FILE_BLOCKING_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_file_blocking_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all file blocking profiles with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_file_blocking_profiles(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_url_access_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get URL access profiles.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of URL access profiles
        """
        url = APIEndpoints.URL_ACCESS_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_url_access_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all URL access profiles with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_url_access_profiles(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_vulnerability_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get vulnerability protection profiles.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of vulnerability protection profiles
        """
        url = APIEndpoints.VULNERABILITY_PROTECTION_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_vulnerability_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all vulnerability protection profiles with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_vulnerability_profiles(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_wildfire_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get WildFire antivirus profiles.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of WildFire antivirus profiles
        """
        url = APIEndpoints.WILDFIRE_ANTI_VIRUS_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_wildfire_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all WildFire antivirus profiles with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_wildfire_profiles(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_profile_groups(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get profile groups.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of profile groups
        """
        url = APIEndpoints.PROFILE_GROUPS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_profile_groups(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all profile groups with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_profile_groups(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    # ==================== Infrastructure Methods (NEW) ====================

    # Remote Networks
    def get_remote_networks(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get remote networks.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of remote network configurations
        """
        url = APIEndpoints.REMOTE_NETWORKS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_remote_networks(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all remote networks with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_remote_networks(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_remote_network(self, network_id: str) -> Dict[str, Any]:
        """
        Get specific remote network by ID.
        
        Args:
            network_id: Remote network ID
            
        Returns:
            Remote network configuration dict
        """
        url = APIEndpoints.remote_network(network_id)
        response = self._make_request("GET", url)
        return response

    # Service Connections (enhanced from existing basic support)
    def get_service_connections(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get service connections.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of service connection configurations
        """
        url = APIEndpoints.SERVICE_CONNECTIONS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_service_connections(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all service connections with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_service_connections(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_service_connection(self, connection_id: str) -> Dict[str, Any]:
        """
        Get specific service connection by ID.
        
        Args:
            connection_id: Service connection ID
            
        Returns:
            Service connection configuration dict
        """
        url = APIEndpoints.service_connection(connection_id)
        response = self._make_request("GET", url)
        return response

    # IPsec Tunnels
    def get_ipsec_tunnels(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get IPsec tunnels.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of IPsec tunnel configurations
        """
        url = APIEndpoints.IPSEC_TUNNELS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_ipsec_tunnels(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all IPsec tunnels with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_ipsec_tunnels(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_ipsec_tunnel(self, tunnel_id: str) -> Dict[str, Any]:
        """
        Get specific IPsec tunnel by ID.
        
        Args:
            tunnel_id: IPsec tunnel ID
            
        Returns:
            IPsec tunnel configuration dict
        """
        url = APIEndpoints.ipsec_tunnel(tunnel_id)
        response = self._make_request("GET", url)
        return response

    # IKE Gateways
    def get_ike_gateways(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get IKE gateways.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of IKE gateway configurations
        """
        url = APIEndpoints.IKE_GATEWAYS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_ike_gateways(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all IKE gateways with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_ike_gateways(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_ike_gateway(self, gateway_id: str) -> Dict[str, Any]:
        """
        Get specific IKE gateway by ID.
        
        Args:
            gateway_id: IKE gateway ID
            
        Returns:
            IKE gateway configuration dict
        """
        url = APIEndpoints.ike_gateway(gateway_id)
        response = self._make_request("GET", url)
        return response

    # IKE Crypto Profiles
    def get_ike_crypto_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get IKE crypto profiles.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of IKE crypto profile configurations
        """
        url = APIEndpoints.IKE_CRYPTO_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_ike_crypto_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all IKE crypto profiles with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_ike_crypto_profiles(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_ike_crypto_profile(self, profile_id: str) -> Dict[str, Any]:
        """
        Get specific IKE crypto profile by ID.
        
        Args:
            profile_id: IKE crypto profile ID
            
        Returns:
            IKE crypto profile configuration dict
        """
        url = APIEndpoints.ike_crypto_profile(profile_id)
        response = self._make_request("GET", url)
        return response

    # IPsec Crypto Profiles
    def get_ipsec_crypto_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get IPsec crypto profiles.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of IPsec crypto profile configurations
        """
        url = APIEndpoints.IPSEC_CRYPTO_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_ipsec_crypto_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all IPsec crypto profiles with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_ipsec_crypto_profiles(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_ipsec_crypto_profile(self, profile_id: str) -> Dict[str, Any]:
        """
        Get specific IPsec crypto profile by ID.
        
        Args:
            profile_id: IPsec crypto profile ID
            
        Returns:
            IPsec crypto profile configuration dict
        """
        url = APIEndpoints.ipsec_crypto_profile(profile_id)
        response = self._make_request("GET", url)
        return response

    # Mobile User Infrastructure
    def get_mobile_user_infrastructure(self) -> Dict[str, Any]:
        """
        Get mobile user infrastructure settings.
        
        Returns:
            Mobile user infrastructure configuration dict
        """
        url = APIEndpoints.MOBILE_AGENT_INFRASTRUCTURE
        response = self._make_request("GET", url)
        return response

    def get_globalprotect_gateways(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get GlobalProtect gateways.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of GlobalProtect gateway configurations
        """
        url = APIEndpoints.GLOBALPROTECT_GATEWAYS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_globalprotect_gateways(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all GlobalProtect gateways with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_globalprotect_gateways(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_globalprotect_portals(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get GlobalProtect portals.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of GlobalProtect portal configurations
        """
        url = APIEndpoints.GLOBALPROTECT_PORTALS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_globalprotect_portals(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all GlobalProtect portals with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_globalprotect_portals(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    # HIP Objects and Profiles
    def get_hip_objects(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get HIP (Host Information Profile) objects.
        
        Note: This endpoint may not be available in all environments.
        Graceful error handling recommended.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of HIP object configurations
        """
        url = APIEndpoints.HIP_OBJECTS
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_hip_objects(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all HIP objects with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_hip_objects(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_hip_profiles(
        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get HIP (Host Information Profile) profiles.
        
        Note: This endpoint may not be available in all environments.
        Graceful error handling recommended.
        
        Args:
            folder: Optional folder name to filter results
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of HIP profile configurations
        """
        url = APIEndpoints.HIP_PROFILES
        params = {}
        if folder:
            url += build_folder_query(folder)
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_hip_profiles(
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all HIP profiles with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_hip_profiles(folder=folder, limit=limit, offset=offset)
        return paginate_api_request(api_func)
    
    # Mobile Agent Configuration (replaces old GlobalProtect endpoints)
    def get_mobile_agent_profiles(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Get mobile agent profiles configuration.
        
        Args:
            folder: Folder name (typically "Mobile Users")
        
        Returns:
            Mobile agent profiles configuration dict
        """
        endpoint = APIEndpoints.MOBILE_AGENT_PROFILES
        params = {}
        if folder:
            params["folder"] = folder
        response = self._make_request("GET", endpoint, params=params if params else None)
        # _make_request already returns parsed data, not response object
        return response if isinstance(response, dict) else {}
    
    def get_mobile_agent_versions(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Get mobile agent versions configuration.
        
        Args:
            folder: Folder name (typically "Mobile Users")
        
        Returns:
            Mobile agent versions configuration dict
        """
        endpoint = APIEndpoints.MOBILE_AGENT_VERSIONS
        params = {}
        if folder:
            params["folder"] = folder
        response = self._make_request("GET", endpoint, params=params if params else None)
        # _make_request already returns parsed data, not response object
        return response if isinstance(response, dict) else {}
    
    def get_mobile_agent_auth_settings(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Get mobile agent authentication settings.
        
        Args:
            folder: Folder name (typically "Mobile Users")
        
        Returns:
            Mobile agent authentication settings dict
        """
        endpoint = APIEndpoints.MOBILE_AGENT_AUTH_SETTINGS
        params = {}
        if folder:
            params["folder"] = folder
        response = self._make_request("GET", endpoint, params=params if params else None)
        # _make_request already returns parsed data, not response object
        return response if isinstance(response, dict) else {}
    
    def get_mobile_agent_enable(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Get mobile agent enable/disable configuration.
        
        Args:
            folder: Folder name (typically "Mobile Users")
        
        Returns:
            Mobile agent enable configuration dict
        """
        endpoint = APIEndpoints.MOBILE_AGENT_ENABLE
        params = {}
        if folder:
            params["folder"] = folder
        response = self._make_request("GET", endpoint, params=params if params else None)
        # _make_request already returns parsed data, not response object
        return response if isinstance(response, dict) else {}
    
    def get_mobile_agent_global_settings(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Get mobile agent global settings.
        
        Args:
            folder: Folder name (typically "Mobile Users")
        
        Returns:
            Mobile agent global settings dict
        """
        endpoint = APIEndpoints.MOBILE_AGENT_GLOBAL_SETTINGS
        params = {}
        if folder:
            params["folder"] = folder
        response = self._make_request("GET", endpoint, params=params if params else None)
        # _make_request already returns parsed data, not response object
        return response if isinstance(response, dict) else {}
    
    def get_mobile_agent_infra_settings(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Get mobile agent infrastructure settings.
        
        Args:
            folder: Folder name (typically "Mobile Users")
        
        Returns:
            Mobile agent infrastructure settings dict or list
        """
        endpoint = APIEndpoints.MOBILE_AGENT_INFRA_SETTINGS
        params = {}
        if folder:
            params["folder"] = folder
        response = self._make_request("GET", endpoint, params=params if params else None)
        # _make_request already returns parsed data, could be dict or list
        return response
    
    def get_mobile_agent_locations(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Get mobile agent locations configuration.
        
        Args:
            folder: Folder name (typically "Mobile Users")
        
        Returns:
            Mobile agent locations dict
        """
        endpoint = APIEndpoints.MOBILE_AGENT_LOCATIONS
        params = {}
        if folder:
            params["folder"] = folder
        response = self._make_request("GET", endpoint, params=params if params else None)
        # _make_request already returns parsed data, not response object
        return response if isinstance(response, dict) else {}
    
    def get_mobile_agent_tunnel_profiles(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Get mobile agent tunnel profiles.
        
        Args:
            folder: Folder name (typically "Mobile Users")
        
        Returns:
            Mobile agent tunnel profiles dict
        """
        endpoint = APIEndpoints.MOBILE_AGENT_TUNNEL_PROFILES
        params = {}
        if folder:
            params["folder"] = folder
        response = self._make_request("GET", endpoint, params=params if params else None)
        # _make_request already returns parsed data, not response object
        return response if isinstance(response, dict) else {}

    # Bandwidth Allocations and Locations (for regions/subnets)
    def get_bandwidth_allocations(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get bandwidth allocations (region information).
        
        Args:
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of bandwidth allocation configurations
        """
        url = APIEndpoints.BANDWIDTH_ALLOCATIONS
        params = {}
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        return response.get("data", [])

    def get_all_bandwidth_allocations(self) -> List[Dict[str, Any]]:
        """Get all bandwidth allocations with automatic pagination."""
        def api_func(offset=0, limit=100):
            return self.get_bandwidth_allocations(limit=limit, offset=offset)
        return paginate_api_request(api_func)

    def get_locations(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get locations (enabled regions).
        
        Args:
            limit: Maximum number of results per page
            offset: Pagination offset
            
        Returns:
            List of location configurations
        """
        url = APIEndpoints.LOCATIONS
        params = {}
        if limit != 100:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset
        response = self._make_request("GET", url, params=params if params else None)
        # Response could be a list directly or a dict with 'data' key
        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            return response.get("data", [])
        return []

    def get_all_locations(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all locations with automatic pagination.
        
        Args:
            limit: Optional maximum number of results to return (None = all results with pagination)
        
        Returns:
            List of location configurations
        """
        if limit is not None:
            # If limit specified, just get that many results (no pagination)
            return self.get_locations(limit=limit, offset=0)
        
        # Otherwise use automatic pagination to get all results
        def api_func(offset=0, limit=100):
            return self.get_locations(limit=limit, offset=offset)
        return paginate_api_request(api_func)

    # ==================== End Infrastructure Methods ====================

    # ==================== CREATE/UPDATE/DELETE Methods ====================
    
    # Folders
    
    def create_folder(self, name: str, parent: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new folder.
        
        Args:
            name: Folder name
            parent: Parent folder name (optional)
            
        Returns:
            Created folder object
        """
        data = {"name": name}
        if parent:
            data["parent"] = parent
        
        return self._make_request("POST", APIEndpoints.SECURITY_POLICY_FOLDERS, data=data, use_cache=False)
    
    # Address Objects
    
    def create_address(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """
        Create an address object.
        
        Args:
            data: Address object data (must include 'name' and address definition)
            folder: Folder name
            
        Returns:
            Created address object
        """
        url = APIEndpoints.ADDRESSES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_address(self, address_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an address object.
        
        Args:
            address_id: Address object ID
            data: Updated address object data
            
        Returns:
            Updated address object
        """
        url = APIEndpoints.address(address_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_address(self, address_id: str) -> Dict[str, Any]:
        """
        Delete an address object.
        
        Args:
            address_id: Address object ID
            
        Returns:
            Deletion response
        """
        url = APIEndpoints.address(address_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Address Groups
    
    def create_address_group(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create an address group."""
        url = APIEndpoints.ADDRESS_GROUPS + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_address_group(self, group_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an address group."""
        url = APIEndpoints.address_group(group_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_address_group(self, group_id: str) -> Dict[str, Any]:
        """Delete an address group."""
        url = APIEndpoints.address_group(group_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Service Objects
    
    def create_service(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a service object."""
        url = APIEndpoints.SERVICES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_service(self, service_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a service object."""
        url = APIEndpoints.service(service_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_service(self, service_id: str) -> Dict[str, Any]:
        """Delete a service object."""
        url = APIEndpoints.service(service_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Service Groups
    
    def create_service_group(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a service group."""
        url = APIEndpoints.SERVICE_GROUPS + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_service_group(self, group_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a service group."""
        url = APIEndpoints.service_group(group_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_service_group(self, group_id: str) -> Dict[str, Any]:
        """Delete a service group."""
        url = APIEndpoints.service_group(group_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Security Rules
    
    def create_security_rule(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """
        Create a security rule.
        
        Args:
            data: Security rule data
            folder: Folder name
            
        Returns:
            Created security rule
        """
        url = APIEndpoints.SECURITY_RULES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_security_rule(self, rule_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a security rule."""
        url = APIEndpoints.security_rule(rule_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_security_rule(self, rule_id: str) -> Dict[str, Any]:
        """Delete a security rule."""
        url = APIEndpoints.security_rule(rule_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Snippets
    
    def create_snippet(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a snippet."""
        return self._make_request("POST", APIEndpoints.SECURITY_POLICY_SNIPPETS, data=data, use_cache=False)
    
    def update_snippet(self, snippet_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a snippet."""
        url = APIEndpoints.security_policy_snippet(snippet_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_snippet(self, snippet_id: str) -> Dict[str, Any]:
        """Delete a snippet."""
        url = APIEndpoints.security_policy_snippet(snippet_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Security Profiles
    
    def create_anti_spyware_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create an anti-spyware profile."""
        url = APIEndpoints.ANTI_SPYWARE_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_anti_spyware_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an anti-spyware profile."""
        url = APIEndpoints.anti_spyware_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_anti_spyware_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete an anti-spyware profile."""
        url = APIEndpoints.anti_spyware_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    def create_dns_security_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a DNS security profile."""
        url = APIEndpoints.DNS_SECURITY_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_dns_security_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a DNS security profile."""
        url = APIEndpoints.dns_security_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_dns_security_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a DNS security profile."""
        url = APIEndpoints.dns_security_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    def create_file_blocking_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a file blocking profile."""
        url = APIEndpoints.FILE_BLOCKING_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_file_blocking_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a file blocking profile."""
        url = APIEndpoints.file_blocking_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_file_blocking_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a file blocking profile."""
        url = APIEndpoints.file_blocking_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    def create_url_access_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a URL access profile."""
        url = APIEndpoints.URL_ACCESS_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_url_access_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a URL access profile."""
        url = APIEndpoints.url_access_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_url_access_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a URL access profile."""
        url = APIEndpoints.url_access_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    def create_vulnerability_protection_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a vulnerability protection profile."""
        url = APIEndpoints.VULNERABILITY_PROTECTION_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_vulnerability_protection_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a vulnerability protection profile."""
        url = APIEndpoints.vulnerability_protection_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_vulnerability_protection_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a vulnerability protection profile."""
        url = APIEndpoints.vulnerability_protection_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    def create_wildfire_anti_virus_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a WildFire anti-virus profile."""
        url = APIEndpoints.WILDFIRE_ANTI_VIRUS_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_wildfire_anti_virus_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a WildFire anti-virus profile."""
        url = APIEndpoints.wildfire_anti_virus_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_wildfire_anti_virus_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a WildFire anti-virus profile."""
        url = APIEndpoints.wildfire_anti_virus_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    def create_decryption_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a decryption profile."""
        url = APIEndpoints.DECRYPTION_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_decryption_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a decryption profile."""
        url = APIEndpoints.decryption_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_decryption_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a decryption profile."""
        url = APIEndpoints.decryption_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    def create_authentication_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create an authentication profile."""
        url = APIEndpoints.AUTHENTICATION_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_authentication_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an authentication profile."""
        url = APIEndpoints.authentication_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_authentication_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete an authentication profile."""
        url = APIEndpoints.authentication_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # HIP Objects and Profiles
    
    def create_hip_object(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a HIP object."""
        url = APIEndpoints.HIP_OBJECTS + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_hip_object(self, object_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a HIP object."""
        url = APIEndpoints.hip_object(object_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_hip_object(self, object_id: str) -> Dict[str, Any]:
        """Delete a HIP object."""
        url = APIEndpoints.hip_object(object_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    def create_hip_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a HIP profile."""
        url = APIEndpoints.HIP_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_hip_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a HIP profile."""
        url = APIEndpoints.hip_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_hip_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a HIP profile."""
        url = APIEndpoints.hip_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Infrastructure - Remote Networks
    
    def create_remote_network(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a remote network."""
        url = APIEndpoints.REMOTE_NETWORKS + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_remote_network(self, network_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a remote network."""
        url = APIEndpoints.remote_network(network_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_remote_network(self, network_id: str) -> Dict[str, Any]:
        """Delete a remote network."""
        url = APIEndpoints.remote_network(network_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Infrastructure - Service Connections
    
    def create_service_connection(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create a service connection."""
        url = APIEndpoints.SERVICE_CONNECTIONS + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_service_connection(self, connection_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a service connection."""
        url = APIEndpoints.service_connection(connection_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_service_connection(self, connection_id: str) -> Dict[str, Any]:
        """Delete a service connection."""
        url = APIEndpoints.service_connection(connection_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Infrastructure - IPsec Tunnels
    
    def create_ipsec_tunnel(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create an IPsec tunnel."""
        url = APIEndpoints.IPSEC_TUNNELS + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_ipsec_tunnel(self, tunnel_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an IPsec tunnel."""
        url = APIEndpoints.ipsec_tunnel(tunnel_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_ipsec_tunnel(self, tunnel_id: str) -> Dict[str, Any]:
        """Delete an IPsec tunnel."""
        url = APIEndpoints.ipsec_tunnel(tunnel_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Infrastructure - IKE Gateways
    
    def create_ike_gateway(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create an IKE gateway."""
        url = APIEndpoints.IKE_GATEWAYS + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_ike_gateway(self, gateway_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an IKE gateway."""
        url = APIEndpoints.ike_gateway(gateway_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_ike_gateway(self, gateway_id: str) -> Dict[str, Any]:
        """Delete an IKE gateway."""
        url = APIEndpoints.ike_gateway(gateway_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # Infrastructure - Crypto Profiles
    
    def create_ike_crypto_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create an IKE crypto profile."""
        url = APIEndpoints.IKE_CRYPTO_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_ike_crypto_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an IKE crypto profile."""
        url = APIEndpoints.ike_crypto_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_ike_crypto_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete an IKE crypto profile."""
        url = APIEndpoints.ike_crypto_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    def create_ipsec_crypto_profile(self, data: Dict[str, Any], folder: str) -> Dict[str, Any]:
        """Create an IPsec crypto profile."""
        url = APIEndpoints.IPSEC_CRYPTO_PROFILES + build_folder_query(folder)
        return self._make_request("POST", url, data=data, use_cache=False)
    
    def update_ipsec_crypto_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an IPsec crypto profile."""
        url = APIEndpoints.ipsec_crypto_profile(profile_id)
        return self._make_request("PUT", url, data=data, use_cache=False)
    
    def delete_ipsec_crypto_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete an IPsec crypto profile."""
        url = APIEndpoints.ipsec_crypto_profile(profile_id)
        return self._make_request("DELETE", url, use_cache=False)
    
    # ==================== End CREATE/UPDATE/DELETE Methods ====================

    def clear_cache(self):
        """Clear API response cache."""
        self.cache.clear()
