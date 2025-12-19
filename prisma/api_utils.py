"""
Utility functions for Prisma Access API operations.

This module provides helper functions for API requests, error handling,
pagination, rate limiting, and caching.
"""

import time
import requests
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from functools import wraps


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        
        # Remove old requests outside time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        # If at limit, wait until oldest request expires
        if len(self.requests) >= self.max_requests:
            oldest_request = min(self.requests)
            wait_time = self.time_window - (now - oldest_request) + 1
            if wait_time > 0:
                time.sleep(wait_time)
                # Clean up again after waiting
                now = time.time()
                self.requests = [req_time for req_time in self.requests 
                               if now - req_time < self.time_window]
        
        # Record this request
        self.requests.append(time.time())


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


def handle_api_response(response: requests.Response, request_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Handle API response and extract data.
    
    Args:
        response: Requests response object
        request_details: Optional dict with request info (url, headers, params, data) for error logging
        
    Returns:
        Response data dictionary
        
    Raises:
        requests.HTTPError: If response indicates error
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
                response_body = response.text[:2000] if len(response.text) <= 2000 else response.text[:2000] + "... (truncated)"
            
            error_logger.log_api_error(
                method=request_details.get('method', 'UNKNOWN') if request_details else 'UNKNOWN',
                url=request_details.get('url', response.url) if request_details else response.url,
                status_code=response.status_code,
                status_text=response.reason,
                headers=request_details.get('headers') if request_details else None,
                params=request_details.get('params') if request_details else None,
                request_body=request_details.get('data') or request_details.get('json') if request_details else None,
                response_body=response_body
            )
        except Exception as log_error:
            # Don't fail if logging fails
            print(f"Warning: Failed to log error to file: {log_error}")
        
        # Also print to console
        print("\n" + "="*80)
        print("API ERROR - Request Details:")
        print("="*80)
        
        if request_details:
            print(f"Method: {request_details.get('method', 'UNKNOWN')}")
            print(f"URL: {request_details.get('url', 'UNKNOWN')}")
            
            # Print headers (mask sensitive tokens)
            headers = request_details.get('headers', {})
            if headers:
                print("\nHeaders:")
                for key, value in headers.items():
                    if 'token' in key.lower() or 'authorization' in key.lower():
                        # Show first 20 chars and last 10 chars of token
                        if len(value) > 30:
                            masked = value[:20] + "..." + value[-10:]
                        else:
                            masked = "***REDACTED***"
                        print(f"  {key}: {masked}")
                    else:
                        print(f"  {key}: {value}")
            
            # Print query parameters
            params = request_details.get('params')
            if params:
                print(f"\nQuery Parameters:")
                for key, value in params.items():
                    print(f"  {key}: {value}")
            
            # Print request body
            data = request_details.get('data')
            json_data = request_details.get('json')
            if data:
                print(f"\nRequest Body (form-data):")
                if isinstance(data, dict):
                    for key, value in data.items():
                        if 'password' in key.lower() or 'secret' in key.lower():
                            print(f"  {key}: ***REDACTED***")
                        else:
                            print(f"  {key}: {value}")
                else:
                    print(f"  {data}")
            elif json_data:
                print(f"\nRequest Body (JSON):")
                import json
                print(f"  {json.dumps(json_data, indent=2)}")
        
        print("\n" + "-"*80)
        print("Response Details:")
        print("-"*80)
        print(f"Status Code: {response.status_code}")
        print(f"Status Text: {response.reason}")
        print(f"Final Request URL (after redirects/merging): {response.url}")
        
        # Try to get response body
        try:
            response_json = response.json()
            print(f"\nResponse Body (JSON):")
            import json
            print(json.dumps(response_json, indent=2))
        except ValueError:
            print(f"\nResponse Body (Text):")
            print(response.text[:1000])  # Limit to first 1000 chars
            if len(response.text) > 1000:
                print(f"... (truncated, total length: {len(response.text)} chars)")
        
        print("="*80 + "\n")
    
    response.raise_for_status()
    
    try:
        return response.json()
    except ValueError:
        # Not JSON, return text
        return {"text": response.text}


def retry_on_failure(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    retryable_statuses: List[int] = [429, 500, 502, 503, 504]
):
    """
    Decorator for retrying API calls on failure.
    
    Args:
        max_retries: Maximum number of retries
        backoff_factor: Backoff multiplier
        retryable_statuses: HTTP status codes that should trigger retry
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
                        wait_time = backoff_factor * (2 ** attempt)
                        time.sleep(wait_time)
                    else:
                        raise
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2 ** attempt)
                        time.sleep(wait_time)
                    else:
                        raise
            
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def paginate_api_request(
    api_func: Callable,
    limit: int = 100,
    max_items: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Paginate through API requests automatically.
    
    Args:
        api_func: Function that takes offset and limit, returns response with 'data' list
        limit: Items per page
        max_items: Maximum items to retrieve (None = all)
        
    Returns:
        List of all items across all pages
    """
    all_items = []
    offset = 0
    
    while True:
        response = api_func(offset=offset, limit=limit)
        
        # Extract data from response
        if isinstance(response, dict) and 'data' in response:
            items = response['data']
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
        "Authorization": f"Bearer {token}"
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
    for field in ['id', 'name', 'uuid']:
        if field in item:
            return str(item[field])
    return None
