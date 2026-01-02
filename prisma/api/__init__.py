"""
Generic API utilities for Prisma Access SCM API.

This package contains generic API helper functions and utilities
that are workflow-agnostic.
"""

from .pagination import PaginationHelper
from .caching import APICache
from .error_handling import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    ValidationError,
    RateLimitError,
    ServerError,
    handle_api_error,
    log_api_error,
    extract_error_details,
)

__all__ = [
    'PaginationHelper',
    'APICache',
    'APIError',
    'AuthenticationError',
    'AuthorizationError',
    'NotFoundError',
    'ConflictError',
    'ValidationError',
    'RateLimitError',
    'ServerError',
    'handle_api_error',
    'log_api_error',
    'extract_error_details',
]
