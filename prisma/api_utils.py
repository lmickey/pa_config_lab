"""
Utility functions for Prisma Access API operations.

This module provides helper functions for API requests, error handling,
pagination, rate limiting, and caching.

Security: Includes advanced rate limiting with per-endpoint limits.
"""

import time
import requests
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """Thread-safe rate limiter with per-endpoint limits."""

    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """
        Initialize advanced rate limiter.

        Args:
            max_requests: Default max requests per time window
            time_window: Default time window in seconds
        """
        self.default_requests = max_requests
        self.default_window = time_window
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.endpoint_limits: Dict[str, tuple] = {}
        self.lock = Lock()

    def set_endpoint_limit(self, endpoint_pattern: str, max_requests: int, window: int):
        """
        Set specific rate limit for an endpoint pattern.

        Args:
            endpoint_pattern: Pattern to match in endpoint URL
            max_requests: Maximum requests for this endpoint
            window: Time window in seconds

        Example:
            >>> rate_limiter.set_endpoint_limit("/security-rules", 50, 60)
        """
        self.endpoint_limits[endpoint_pattern] = (max_requests, window)

    def wait_if_needed(self, endpoint: Optional[str] = None):
        """
        Wait if rate limit would be exceeded for endpoint.

        Args:
            endpoint: Optional endpoint URL for per-endpoint limiting
        """
        with self.lock:
            # Determine limits for this endpoint
            max_requests = self.default_requests
            window = self.default_window

            if endpoint:
                for pattern, (req, win) in self.endpoint_limits.items():
                    if pattern in endpoint:
                        max_requests, window = req, win
                        break

            key = endpoint or "default"
            now = time.time()

            # Remove old requests outside window
            self.requests[key] = [
                req_time for req_time in self.requests[key] if now - req_time < window
            ]

            # Check if at limit
            if len(self.requests[key]) >= max_requests:
                oldest = min(self.requests[key])
                wait_time = window - (now - oldest) + 1
                if wait_time > 0:
                    # Log rate limit to GUI
                    import logging
                    logging.info(f"Rate limit reached, waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    now = time.time()
                    self.requests[key] = [
                        req_time
                        for req_time in self.requests[key]
                        if now - req_time < window
                    ]

            # Record this request
            self.requests[key].append(time.time())

    def reset(self, endpoint: Optional[str] = None):
        """
        Reset rate limiter for endpoint or all endpoints.

        Args:
            endpoint: Optional specific endpoint to reset
        """
        with self.lock:
            if endpoint:
                if endpoint in self.requests:
                    self.requests[endpoint].clear()
            else:
                self.requests.clear()


class APICache:
    """Simple in-memory cache for API responses."""

    def __init__(self, ttl: int = 300):
        """
        Initialize cache.

        Args:
            ttl: Time to live in seconds (default 5 minutes)
        """
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """Set cached value."""
        self.cache[key] = (value, datetime.now())

    def clear(self):
        """Clear all cached values."""
        self.cache.clear()

    def invalidate(self, key: str):
        """Invalidate specific cache key."""
        if key in self.cache:
            del self.cache[key]


def handle_api_response(
    response: requests.Response, request_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle API response and extract data with error handling.

    Processes HTTP responses from Prisma Access API, handles errors, and extracts
    response data. Logs errors to centralized error logger if available.

    Args:
        response: Requests response object from API call
        request_details: Optional dictionary with request information (url, headers, params, data)
                        for error logging. Should include 'method', 'url', 'headers', 'params', 'data'

    Returns:
        Response data dictionary. May contain 'data', 'items', or direct list/object depending on API format.

    Raises:
        requests.HTTPError: If response indicates an error (non-2xx status) and error cannot be handled gracefully

    Example:
        >>> response = requests.get(url, headers=headers)
        >>> data = handle_api_response(response, {'method': 'GET', 'url': url})
        >>> print(data.get('data', []))
    """
    # If error status, log and print detailed debugging information
    if not response.ok:
        # Log to file using centralized error logger
        try:
            from .error_logger import error_logger

            # Extract response body
            response_body = None
            try:
                response_body = response.json()
            except ValueError:
                response_body = (
                    response.text[:2000]
                    if len(response.text) <= 2000
                    else response.text[:2000] + "... (truncated)"
                )

            error_logger.log_api_error(
                method=(
                    request_details.get("method", "UNKNOWN")
                    if request_details
                    else "UNKNOWN"
                ),
                url=(
                    request_details.get("url", response.url)
                    if request_details
                    else response.url
                ),
                status_code=response.status_code,
                status_text=response.reason,
                headers=request_details.get("headers") if request_details else None,
                params=request_details.get("params") if request_details else None,
                request_body=(
                    request_details.get("data") or request_details.get("json")
                    if request_details
                    else None
                ),
                response_body=response_body,
            )
        except Exception as log_error:
            # Don't fail if logging fails
            print(f"Warning: Failed to log error to file: {log_error}")

        # Skip console printing to avoid thread crashes
        # All error details are already logged to activity.log above
        # Console printing from background threads causes segfaults

    response.raise_for_status()

    try:
        return response.json()
    except ValueError:
        # Not JSON, return text
        return {"text": response.text}


def retry_on_failure(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    retryable_statuses: List[int] = [429, 500, 502, 503, 504],
):
    """
    Decorator for retrying API calls on failure with exponential backoff.

    Automatically retries the decorated function when it raises HTTPError with
    retryable status codes or other exceptions. Uses exponential backoff to avoid
    overwhelming the API server.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Base backoff time in seconds (default: 1.0)
        retryable_statuses: List of HTTP status codes that should trigger retry
                          (default: [429, 500, 502, 503, 504])

    Returns:
        Decorator function

    Example:
        >>> @retry_on_failure(max_retries=5, backoff_factor=2.0)
        ... def api_call():
        ...     return requests.get(url)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.HTTPError as e:
                    last_exception = e
                    if e.response.status_code not in retryable_statuses:
                        raise

                    if attempt < max_retries:
                        wait_time = backoff_factor * (2**attempt)
                        time.sleep(wait_time)
                    else:
                        raise
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2**attempt)
                        time.sleep(wait_time)
                    else:
                        raise

            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def paginate_api_request(
    api_func: Callable, limit: int = 100, max_items: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Paginate through API requests automatically to retrieve all items.

    Makes multiple API calls with increasing offset values until all items
    are retrieved or max_items limit is reached.

    Args:
        api_func: Function that accepts offset and limit parameters, returns response
                 with 'data' list or direct list
        limit: Maximum items per page (default: 100)
        max_items: Maximum total items to retrieve (None = retrieve all)

    Returns:
        List of all items across all pages, combined into a single list

    Example:
        >>> def get_rules(offset=0, limit=100):
        ...     return api_client.get_security_rules(offset=offset, limit=limit)
        >>> all_rules = paginate_api_request(get_rules, limit=50)
    """
    all_items = []
    offset = 0

    while True:
        response = api_func(offset=offset, limit=limit)

        # Extract data from response
        if isinstance(response, dict) and "data" in response:
            items = response["data"]
        elif isinstance(response, list):
            items = response
        else:
            items = []

        if not items:
            break

        all_items.extend(items)

        # Check if we've reached max_items
        if max_items and len(all_items) >= max_items:
            all_items = all_items[:max_items]
            break

        # Check if there are more items
        if len(items) < limit:
            break

        offset += limit

    return all_items


def build_headers(token: str, content_type: str = "application/json") -> Dict[str, str]:
    """
    Build standard API headers.

    Args:
        token: Authentication token
        content_type: Content type header

    Returns:
        Headers dictionary
    """
    return {
        "Content-Type": content_type,
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }


def extract_folder_from_path(path: str) -> Optional[str]:
    """
    Extract folder name from API path.

    Args:
        path: API path string

    Returns:
        Folder name or None
    """
    # Example: "/config/security-policy/folders/Shared" -> "Shared"
    parts = path.split("/")
    if "folders" in parts:
        idx = parts.index("folders")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return None


def extract_id_from_response(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract ID from API response item.

    Args:
        item: API response item dictionary

    Returns:
        ID string or None
    """
    # Try common ID fields
    for field in ["id", "name", "uuid"]:
        if field in item:
            return str(item[field])
    return None
