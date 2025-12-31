"""
Secure logging with automatic sensitive data sanitization.

This module provides logging utilities that automatically redact
sensitive information such as passwords, API keys, tokens, and
personally identifiable information (PII).
"""

import re
from typing import Any, Dict, Union


class SecureLogger:
    """Logger with automatic sensitive data sanitization."""

    # Patterns for sensitive data detection
    SENSITIVE_PATTERNS = {
        "password": re.compile(
            r"(password|passwd|pwd)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)",
            re.IGNORECASE,
        ),
        "api_key": re.compile(
            r"(api[_-]?key|apikey)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)",
            re.IGNORECASE,
        ),
        "secret": re.compile(
            r"(secret|token|auth)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)",
            re.IGNORECASE,
        ),
        "authorization": re.compile(
            r"(authorization|bearer)[:|\s]+([^\s,}]+)", re.IGNORECASE
        ),
        "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    }

    # Keys that should always be redacted
    SENSITIVE_KEYS = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "auth_token",
        "authorization",
        "api_secret",
        "client_secret",
        "private_key",
        "encryption_key",
    }

    @staticmethod
    def sanitize(data: Any, redact_email: bool = False) -> Any:
        """
        Sanitize sensitive data before logging.

        Args:
            data: Data to sanitize (string, dict, list, or other)
            redact_email: Whether to redact email addresses

        Returns:
            Sanitized data with sensitive information masked

        Example:
            >>> SecureLogger.sanitize({"password": "secret123"})
            {'password': '***REDACTED***'}
        """
        if isinstance(data, str):
            return SecureLogger._sanitize_string(data, redact_email)
        elif isinstance(data, dict):
            return SecureLogger._sanitize_dict(data, redact_email)
        elif isinstance(data, list):
            return [SecureLogger.sanitize(item, redact_email) for item in data]
        elif isinstance(data, tuple):
            return tuple(SecureLogger.sanitize(item, redact_email) for item in data)
        else:
            return data

    @staticmethod
    def _sanitize_string(text: str, redact_email: bool = False) -> str:
        """Sanitize a string value."""
        # Apply regex patterns
        for pattern_name, pattern in SecureLogger.SENSITIVE_PATTERNS.items():
            if pattern_name == "email" and not redact_email:
                continue

            if pattern_name in ["password", "api_key", "secret", "authorization"]:
                # Keep the key name, redact the value
                text = pattern.sub(r"\1=***REDACTED***", text)
            else:
                # Redact entire match
                text = pattern.sub("***REDACTED***", text)

        return text

    @staticmethod
    def _sanitize_dict(
        data: Dict[str, Any], redact_email: bool = False
    ) -> Dict[str, Any]:
        """Sanitize a dictionary."""
        sanitized = {}

        for key, value in data.items():
            # Check if key is sensitive
            key_lower = key.lower().replace("-", "_").replace(" ", "_")

            if key_lower in SecureLogger.SENSITIVE_KEYS:
                # Redact entire value
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, (dict, list, tuple)):
                # Recursively sanitize nested structures
                sanitized[key] = SecureLogger.sanitize(value, redact_email)
            elif isinstance(value, str):
                # Sanitize string values
                sanitized[key] = SecureLogger._sanitize_string(value, redact_email)
            else:
                sanitized[key] = value

        return sanitized

    @staticmethod
    def safe_log(message: str, data: Any = None, redact_email: bool = False) -> str:
        """
        Create a safe log message with sanitized data.

        Args:
            message: Log message
            data: Optional data to include (will be sanitized)
            redact_email: Whether to redact email addresses

        Returns:
            Sanitized log message

        Example:
            >>> SecureLogger.safe_log("User login", {"username": "admin", "password": "secret"})
            "User login: {'username': 'admin', 'password': '***REDACTED***'}"
        """
        if data is not None:
            sanitized_data = SecureLogger.sanitize(data, redact_email)
            return f"{message}: {sanitized_data}"
        return message

    @staticmethod
    def mask_token(token: str, prefix_len: int = 20, suffix_len: int = 10) -> str:
        """
        Mask a token, showing only prefix and suffix.

        Args:
            token: Token to mask
            prefix_len: Number of characters to show at start
            suffix_len: Number of characters to show at end

        Returns:
            Masked token

        Example:
            >>> SecureLogger.mask_token("sk-1234567890abcdefghijklmnop")
            "sk-12345678901234567890...lmnop"
        """
        if not token or len(token) <= prefix_len + suffix_len:
            return "***REDACTED***"

        prefix = token[:prefix_len]
        suffix = token[-suffix_len:]
        return f"{prefix}...{suffix}"

    @staticmethod
    def is_sensitive_key(key: str) -> bool:
        """
        Check if a key name indicates sensitive data.

        Args:
            key: Key name to check

        Returns:
            True if key is sensitive
        """
        key_lower = key.lower().replace("-", "_").replace(" ", "_")
        return key_lower in SecureLogger.SENSITIVE_KEYS
