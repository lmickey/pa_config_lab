"""
Error handling utilities for Prisma Access SCM API.

Provides structured error handling and logging for API interactions.
"""

from typing import Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response
        self.endpoint = endpoint
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        if self.endpoint:
            parts.append(f"[{self.endpoint}]")
        return " ".join(parts)


class AuthenticationError(APIError):
    """Authentication failed"""
    pass


class AuthorizationError(APIError):
    """Not authorized to access resource"""
    pass


class NotFoundError(APIError):
    """Resource not found"""
    pass


class ConflictError(APIError):
    """Resource conflict (e.g., already exists, in use)"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
        referenced_by: Optional[list] = None
    ):
        super().__init__(message, status_code, response, endpoint)
        self.referenced_by = referenced_by or []
    
    def get_references(self) -> list:
        """
        Extract references from error response.
        
        For 409 conflicts, the API often includes details about what references
        the item being deleted/modified.
        
        Returns:
            List of reference dicts with 'type' and 'name' keys
        """
        if self.referenced_by:
            return self.referenced_by
        
        if not self.response:
            return []
        
        # Try to extract from response details
        references = []
        
        # Check common patterns in 409 responses
        if isinstance(self.response, dict):
            details = self.response.get('details', {})
            if isinstance(details, dict):
                # Look for reference information
                for key in ['references', 'used_by', 'dependencies']:
                    if key in details:
                        refs = details[key]
                        if isinstance(refs, list):
                            references.extend(refs)
        
        return references


class ValidationError(APIError):
    """Validation failed"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
        validation_errors: Optional[list] = None
    ):
        super().__init__(message, status_code, response, endpoint)
        self.validation_errors = validation_errors or []
    
    def get_validation_errors(self) -> list:
        """
        Extract validation errors from response.
        
        Returns:
            List of validation error dicts
        """
        if self.validation_errors:
            return self.validation_errors
        
        if not self.response:
            return []
        
        errors = []
        
        # Try to extract from response
        if isinstance(self.response, dict):
            # Common patterns
            for key in ['errors', 'validation_errors', 'details']:
                if key in self.response:
                    val_errors = self.response[key]
                    if isinstance(val_errors, list):
                        errors.extend(val_errors)
                    elif isinstance(val_errors, dict):
                        errors.append(val_errors)
        
        return errors


class RateLimitError(APIError):
    """Rate limit exceeded"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(message, status_code, response, endpoint)
        self.retry_after = retry_after


class ServerError(APIError):
    """Server error (5xx)"""
    pass


def handle_api_error(
    status_code: int,
    response: Any,
    endpoint: str,
    log_errors: bool = True
) -> APIError:
    """
    Create appropriate exception based on status code.
    
    Args:
        status_code: HTTP status code
        response: Response body (dict or string)
        endpoint: API endpoint
        log_errors: Whether to log to api_errors.log
        
    Returns:
        Appropriate APIError subclass instance
    """
    # Parse response if string
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            response = {'message': response}
    
    # Extract error message
    if isinstance(response, dict):
        message = response.get('message') or response.get('error') or str(response)
    else:
        message = str(response)
    
    # Create appropriate exception
    error: APIError
    
    if status_code == 401:
        error = AuthenticationError(message, status_code, response, endpoint)
    elif status_code == 403:
        error = AuthorizationError(message, status_code, response, endpoint)
    elif status_code == 404:
        error = NotFoundError(message, status_code, response, endpoint)
    elif status_code == 409:
        error = ConflictError(message, status_code, response, endpoint)
    elif status_code == 422:
        error = ValidationError(message, status_code, response, endpoint)
    elif status_code == 429:
        retry_after = None
        if isinstance(response, dict):
            retry_after = response.get('retry_after')
        error = RateLimitError(message, status_code, response, endpoint, retry_after)
    elif status_code >= 500:
        error = ServerError(message, status_code, response, endpoint)
    else:
        error = APIError(message, status_code, response, endpoint)
    
    # Log error
    if log_errors:
        log_api_error(error)
    
    return error


def log_api_error(error: APIError) -> None:
    """
    Log API error to api_errors.log with detailed information.
    
    Args:
        error: APIError instance
    """
    # Log to api_errors.log
    error_logger = logging.getLogger('api_errors')
    
    error_data = {
        'type': type(error).__name__,
        'message': error.message,
        'status_code': error.status_code,
        'endpoint': error.endpoint,
        'response': error.response
    }
    
    # Add type-specific data
    if isinstance(error, ConflictError):
        error_data['references'] = error.get_references()
    elif isinstance(error, ValidationError):
        error_data['validation_errors'] = error.get_validation_errors()
    elif isinstance(error, RateLimitError):
        error_data['retry_after'] = error.retry_after
    
    error_logger.error(json.dumps(error_data, indent=2))
    
    # Also log to main logger
    logger.error(f"{error.message} - {error.endpoint} (HTTP {error.status_code})")


def extract_error_details(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract detailed error information from API response.
    
    Args:
        response: API error response
        
    Returns:
        Dict with extracted error details
    """
    details = {
        'message': None,
        'error_type': None,
        'details': None,
        'references': [],
        'validation_errors': []
    }
    
    if not isinstance(response, dict):
        return details
    
    # Extract message
    details['message'] = response.get('message') or response.get('error')
    
    # Extract error type
    details['error_type'] = response.get('error_type') or response.get('type')
    
    # Extract details section
    if 'details' in response:
        details['details'] = response['details']
        
        # Try to extract references from details
        if isinstance(response['details'], dict):
            for key in ['references', 'used_by', 'dependencies']:
                if key in response['details']:
                    refs = response['details'][key]
                    if isinstance(refs, list):
                        details['references'].extend(refs)
    
    # Extract validation errors
    for key in ['errors', 'validation_errors']:
        if key in response:
            val_errors = response[key]
            if isinstance(val_errors, list):
                details['validation_errors'].extend(val_errors)
            elif isinstance(val_errors, dict):
                details['validation_errors'].append(val_errors)
    
    return details
