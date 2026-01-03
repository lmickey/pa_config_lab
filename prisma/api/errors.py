"""
Structured error types for Prisma Access API Client.

Provides specific exception classes for different error scenarios,
making error handling more precise and actionable.
"""

from typing import Optional, Dict, Any


class PrismaAPIError(Exception):
    """Base exception for all Prisma API errors"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize API error.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code from API
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        """String representation of error"""
        parts = [self.message]
        if self.error_code:
            parts.append(f" (Error Code: {self.error_code})")
        if self.details:
            parts.append(f" - Details: {self.details}")
        return "".join(parts)


class AuthenticationError(PrismaAPIError):
    """Authentication failed - invalid credentials or token"""
    pass


class AuthorizationError(PrismaAPIError):
    """Authorization failed - valid credentials but insufficient permissions"""
    pass


class NetworkError(PrismaAPIError):
    """Network-related error - connection, timeout, etc."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.status_code = status_code
    
    @property
    def is_retryable(self) -> bool:
        """Check if this error is retryable"""
        # Retry on 5xx errors or network timeouts
        if self.status_code:
            return 500 <= self.status_code < 600
        return True  # Default to retryable for network issues


class RateLimitError(PrismaAPIError):
    """Rate limit exceeded"""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after  # Seconds until retry allowed
    
    def __str__(self) -> str:
        base = super().__str__()
        if self.retry_after:
            return f"{base} - Retry after {self.retry_after} seconds"
        return base


class ValidationError(PrismaAPIError):
    """Request validation failed - invalid data"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
    
    def __str__(self) -> str:
        base = super().__str__()
        if self.field:
            return f"{base} - Field: '{self.field}'"
        return base


class ResourceNotFoundError(PrismaAPIError):
    """Requested resource not found"""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.resource_name = resource_name
    
    def __str__(self) -> str:
        base = super().__str__()
        if self.resource_type and self.resource_name:
            return f"{base} - {self.resource_type}: '{self.resource_name}'"
        return base


class ResourceConflictError(PrismaAPIError):
    """Resource conflict - name already exists, concurrent modification, etc."""
    
    def __init__(
        self,
        message: str,
        conflicting_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.conflicting_name = conflicting_name


class ResponseParsingError(PrismaAPIError):
    """Failed to parse API response"""
    
    def __init__(
        self,
        message: str,
        raw_response: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.raw_response = raw_response


class SchemaValidationError(ValidationError):
    """Response doesn't match expected schema"""
    pass


def parse_api_error(
    response: Any,
    status_code: int,
    url: Optional[str] = None
) -> PrismaAPIError:
    """
    Parse API error response and return appropriate exception.
    
    Args:
        response: Response object or dict
        status_code: HTTP status code
        url: Optional request URL for context
    
    Returns:
        Appropriate PrismaAPIError subclass
    """
    # Try to extract error message
    message = "API request failed"
    error_code = None
    details = {}
    
    try:
        if hasattr(response, 'json'):
            data = response.json()
        elif isinstance(response, dict):
            data = response
        else:
            data = {'message': str(response)}
        
        # SCM API error format: {'error': {'message': '...', 'code': '...'}}
        if 'error' in data and isinstance(data['error'], dict):
            error_info = data['error']
            message = error_info.get('message', message)
            error_code = error_info.get('code')
            details = {k: v for k, v in error_info.items() 
                      if k not in ['message', 'code']}
        elif 'message' in data:
            message = data['message']
        elif '_errors' in data:
            # SCM API validation errors format
            errors = data['_errors']
            if isinstance(errors, list) and errors:
                message = errors[0].get('message', message)
            details = {'errors': errors}
    
    except Exception:
        # If parsing fails, use generic message
        pass
    
    # Add URL to details if provided
    if url:
        details['url'] = url
    
    # Determine exception type based on status code
    if status_code == 401:
        return AuthenticationError(message, error_code=error_code, details=details)
    
    elif status_code == 403:
        return AuthorizationError(message, error_code=error_code, details=details)
    
    elif status_code == 404:
        return ResourceNotFoundError(message, error_code=error_code, details=details)
    
    elif status_code == 409:
        # Extract conflicting name if available
        conflicting_name = details.get('name') or details.get('conflicting_name')
        return ResourceConflictError(
            message,
            conflicting_name=conflicting_name,
            error_code=error_code,
            details=details
        )
    
    elif status_code == 422:
        # Validation error
        field = details.get('field')
        value = details.get('value')
        return ValidationError(
            message,
            field=field,
            value=value,
            error_code=error_code,
            details=details
        )
    
    elif status_code == 429:
        # Rate limit
        retry_after = None
        if hasattr(response, 'headers'):
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except ValueError:
                    pass
        return RateLimitError(
            message,
            retry_after=retry_after,
            error_code=error_code,
            details=details
        )
    
    elif 500 <= status_code < 600:
        # Server error
        return NetworkError(
            message,
            status_code=status_code,
            error_code=error_code,
            details=details
        )
    
    elif 400 <= status_code < 500:
        # Other client error
        return ValidationError(message, error_code=error_code, details=details)
    
    else:
        # Generic error
        return PrismaAPIError(message, error_code, details)


__all__ = [
    'PrismaAPIError',
    'AuthenticationError',
    'AuthorizationError',
    'NetworkError',
    'RateLimitError',
    'ValidationError',
    'ResourceNotFoundError',
    'ResourceConflictError',
    'ResponseParsingError',
    'SchemaValidationError',
    'parse_api_error',
]
