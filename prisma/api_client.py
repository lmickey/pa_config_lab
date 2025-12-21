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
        rate_limit: int = 100,
        cache_ttl: int = 300,
    ):
        """
        Initialize API client.

        Args:
            tsg_id: Tenant Service Group ID
            api_user: API client ID
            api_secret: API client secret
            rate_limit: Maximum requests per minute
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
        self, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all application objects with automatic pagination."""

        def api_func(offset=0, limit=100):
            return self.get_applications(folder=folder, limit=limit, offset=offset)

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

    def clear_cache(self):
        """Clear API response cache."""
        self.cache.clear()
