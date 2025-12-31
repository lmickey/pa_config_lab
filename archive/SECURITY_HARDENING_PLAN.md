# Security Hardening Plan

**Priority:** Critical  
**Target Date:** Before Production Deployment  
**Estimated Effort:** 2-3 weeks  

## Overview

This document outlines critical security improvements needed before the system can be deployed in production environments or integrated into GUI applications.

---

## 1. Cryptographic Improvements

### 1.1 Strengthen Key Derivation Function (KDF)

**Priority:** 🔴 CRITICAL  
**Effort:** 4-6 hours  
**Current Issue:** Using simple SHA-256 for password hashing is vulnerable to brute-force attacks

**Implementation:**

```python
# File: config/storage/json_storage.py

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import os

def derive_key_secure(password: str, salt: bytes = None) -> tuple[Fernet, bytes]:
    """
    Derive a Fernet key from a password using PBKDF2HMAC.
    
    Args:
        password: Password string
        salt: Optional salt (will be generated if not provided)
        
    Returns:
        Tuple of (Fernet cipher instance, salt bytes)
    """
    if salt is None:
        salt = os.urandom(16)  # 128-bit salt
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # NIST 2024 recommendation
        backend=default_backend()
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
    return Fernet(key), salt


def save_config_json(
    config: Dict[str, Any],
    file_path: str,
    cipher: Optional[Fernet] = None,
    encrypt: bool = True,
    pretty: bool = True
) -> bool:
    """
    Save configuration to JSON file with improved encryption.
    """
    if encrypt:
        if cipher is None:
            password = getpass.getpass("Enter password for encryption: ")
            cipher, salt = derive_key_secure(password)
        
        json_str = json.dumps(config, indent=2 if pretty else None, ensure_ascii=False)
        encrypted_data = cipher.encrypt(json_str.encode('utf-8'))
        
        # Save salt + encrypted data
        with open(file_path, 'wb') as f:
            f.write(salt)  # First 16 bytes are salt
            f.write(encrypted_data)
    else:
        # Unencrypted save
        json_str = json.dumps(config, indent=2 if pretty else None, ensure_ascii=False)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
    
    return True


def load_config_json(
    file_path: str,
    cipher: Optional[Fernet] = None,
    encrypted: Optional[bool] = None
) -> Optional[Dict[str, Any]]:
    """
    Load configuration from JSON file with improved decryption.
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # Check if encrypted
    if encrypted or (encrypted is None and not data.startswith(b'{')):
        # Extract salt (first 16 bytes)
        salt = data[:16]
        encrypted_data = data[16:]
        
        if cipher is None:
            password = getpass.getpass("Enter password for decryption: ")
            cipher, _ = derive_key_secure(password, salt=salt)
        
        try:
            decrypted_data = cipher.decrypt(encrypted_data)
            config = json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            print(f"Error decrypting configuration: {e}")
            return None
    else:
        # Unencrypted
        config = json.loads(data.decode('utf-8'))
    
    return config
```

**Migration Path:**
1. Add new functions alongside existing ones
2. Add a version marker to encrypted files (e.g., `PBKDF2v1`)
3. Update to auto-detect and upgrade old files
4. Deprecate old `derive_key()` function after migration

---

## 2. Input Validation

### 2.1 Comprehensive JSON Validation

**Priority:** 🔴 CRITICAL  
**Effort:** 8-12 hours

**Implementation:**

```python
# File: config/storage/json_storage_secure.py

from jsonschema import validate, ValidationError
from typing import Dict, Any
import json

class ConfigurationValidator:
    """Secure configuration validator with comprehensive checks."""
    
    MAX_CONFIG_SIZE = 100_000_000  # 100MB
    MAX_STRING_LENGTH = 10_000
    MAX_ARRAY_LENGTH = 50_000
    MAX_NESTING_DEPTH = 20
    
    @staticmethod
    def validate_json_structure(data: str) -> Dict[str, Any]:
        """
        Validate JSON structure and size limits.
        
        Raises:
            ValueError: If validation fails
        """
        # Check size
        if len(data) > ConfigurationValidator.MAX_CONFIG_SIZE:
            raise ValueError(f"Configuration exceeds maximum size ({ConfigurationValidator.MAX_CONFIG_SIZE} bytes)")
        
        # Parse JSON
        try:
            config = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        
        # Validate against schema
        try:
            from config.schema.config_schema_v2 import CONFIG_SCHEMA_V2
            validate(instance=config, schema=CONFIG_SCHEMA_V2)
        except ValidationError as e:
            raise ValueError(f"Configuration schema validation failed: {e}")
        
        # Check nesting depth
        max_depth = ConfigurationValidator._get_max_depth(config)
        if max_depth > ConfigurationValidator.MAX_NESTING_DEPTH:
            raise ValueError(f"Configuration exceeds maximum nesting depth ({ConfigurationValidator.MAX_NESTING_DEPTH})")
        
        # Validate string lengths
        ConfigurationValidator._validate_strings(config)
        
        # Validate array lengths
        ConfigurationValidator._validate_arrays(config)
        
        return config
    
    @staticmethod
    def _get_max_depth(obj: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth."""
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(ConfigurationValidator._get_max_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(ConfigurationValidator._get_max_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth
    
    @staticmethod
    def _validate_strings(obj: Any, path: str = "root"):
        """Validate all string lengths in configuration."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(key, str) and len(key) > ConfigurationValidator.MAX_STRING_LENGTH:
                    raise ValueError(f"String key too long at {path}.{key}")
                ConfigurationValidator._validate_strings(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                ConfigurationValidator._validate_strings(item, f"{path}[{i}]")
        elif isinstance(obj, str):
            if len(obj) > ConfigurationValidator.MAX_STRING_LENGTH:
                raise ValueError(f"String value too long at {path}")
    
    @staticmethod
    def _validate_arrays(obj: Any, path: str = "root"):
        """Validate all array lengths in configuration."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                ConfigurationValidator._validate_arrays(value, f"{path}.{key}")
        elif isinstance(obj, list):
            if len(obj) > ConfigurationValidator.MAX_ARRAY_LENGTH:
                raise ValueError(f"Array too long at {path} ({len(obj)} items)")
            for i, item in enumerate(obj):
                ConfigurationValidator._validate_arrays(item, f"{path}[{i}]")


def load_config_json_secure(file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Load configuration with comprehensive security validation.
    """
    # Load file
    config = load_config_json(file_path, **kwargs)
    
    if config is None:
        return None
    
    # Additional security validation
    json_str = json.dumps(config)
    validated_config = ConfigurationValidator.validate_json_structure(json_str)
    
    return validated_config
```

### 2.2 File Path Validation

**Priority:** 🔴 CRITICAL  
**Effort:** 2-3 hours

**Implementation:**

```python
# File: config/storage/path_validator.py

import pathlib
import os
from typing import Union

class PathValidator:
    """Validate file paths to prevent path traversal attacks."""
    
    DEFAULT_BASE_DIR = os.path.expanduser("~/.pa_config_lab")
    
    @staticmethod
    def validate_config_path(
        file_path: Union[str, pathlib.Path],
        base_dir: Union[str, pathlib.Path] = None,
        must_exist: bool = False,
        must_be_file: bool = True
    ) -> pathlib.Path:
        """
        Validate and normalize a configuration file path.
        
        Args:
            file_path: Path to validate
            base_dir: Base directory to restrict to (default: ~/.pa_config_lab)
            must_exist: If True, path must exist
            must_be_file: If True, path must be a file (not directory)
            
        Returns:
            Validated and resolved pathlib.Path
            
        Raises:
            ValueError: If path is invalid or unsafe
        """
        if base_dir is None:
            base_dir = PathValidator.DEFAULT_BASE_DIR
        
        # Ensure base directory exists
        base = pathlib.Path(base_dir).resolve()
        if not base.exists():
            base.mkdir(parents=True, exist_ok=True)
        
        # Resolve target path
        if isinstance(file_path, str):
            file_path = pathlib.Path(file_path)
        
        # Handle relative vs absolute paths
        if file_path.is_absolute():
            target = file_path.resolve()
        else:
            target = (base / file_path).resolve()
        
        # Check for path traversal
        try:
            target.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Invalid file path: '{file_path}' resolves outside base directory '{base}'. "
                "Path traversal detected."
            )
        
        # Check existence
        if must_exist and not target.exists():
            raise ValueError(f"Path does not exist: {target}")
        
        # Check if file
        if must_be_file and target.exists() and not target.is_file():
            raise ValueError(f"Path is not a file: {target}")
        
        return target
    
    @staticmethod
    def validate_directory_path(
        dir_path: Union[str, pathlib.Path],
        base_dir: Union[str, pathlib.Path] = None,
        create: bool = False
    ) -> pathlib.Path:
        """
        Validate a directory path.
        
        Args:
            dir_path: Directory path to validate
            base_dir: Base directory to restrict to
            create: If True, create directory if it doesn't exist
            
        Returns:
            Validated pathlib.Path
        """
        target = PathValidator.validate_config_path(
            dir_path, base_dir, must_exist=False, must_be_file=False
        )
        
        if create and not target.exists():
            target.mkdir(parents=True, exist_ok=True)
        
        return target
```

---

## 3. API Security

### 3.1 Request Size Limits

**Priority:** 🟡 HIGH  
**Effort:** 3-4 hours

**Implementation:**

```python
# File: prisma/api_client_secure.py

class PrismaAccessAPIClient:
    """Enhanced API client with security improvements."""
    
    MAX_RESPONSE_SIZE = 50_000_000  # 50MB
    STREAMING_THRESHOLD = 10_000_000  # 10MB
    
    def _make_request_secure(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        timeout: int = 60,
        stream_large: bool = True
    ) -> Dict[str, Any]:
        """
        Make API request with size limit enforcement.
        """
        # ... existing auth and rate limiting ...
        
        # Make request with streaming for large responses
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
            stream=stream_large
        )
        
        # Check content length header
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > self.MAX_RESPONSE_SIZE:
            raise ValueError(
                f"Response too large: {content_length} bytes "
                f"(max: {self.MAX_RESPONSE_SIZE})"
            )
        
        # If streaming, check size as we read
        if stream_large:
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > self.MAX_RESPONSE_SIZE:
                    raise ValueError(
                        f"Response exceeds maximum size: {self.MAX_RESPONSE_SIZE}"
                    )
            response._content = content
        
        # ... existing response handling ...
```

### 3.2 Rate Limiting Improvements

**Priority:** 🟡 HIGH  
**Effort:** 4-6 hours

**Implementation:**

```python
# File: prisma/api_utils_secure.py

import time
from collections import defaultdict
from typing import Dict, Optional
from threading import Lock

class AdvancedRateLimiter:
    """Thread-safe rate limiter with per-endpoint limits."""
    
    def __init__(self, default_requests: int = 100, default_window: int = 60):
        """
        Initialize advanced rate limiter.
        
        Args:
            default_requests: Default max requests per window
            default_window: Default time window in seconds
        """
        self.default_requests = default_requests
        self.default_window = default_window
        self.requests: Dict[str, list] = defaultdict(list)
        self.endpoint_limits: Dict[str, tuple] = {}
        self.lock = Lock()
    
    def set_endpoint_limit(self, endpoint_pattern: str, max_requests: int, window: int):
        """Set specific rate limit for an endpoint pattern."""
        self.endpoint_limits[endpoint_pattern] = (max_requests, window)
    
    def wait_if_needed(self, endpoint: Optional[str] = None):
        """Wait if rate limit would be exceeded for endpoint."""
        with self.lock:
            # Determine limits for this endpoint
            max_requests = self.default_requests
            window = self.default_window
            
            if endpoint:
                for pattern, (req, win) in self.endpoint_limits.items():
                    if pattern in endpoint:
                        max_requests, window = req, win
                        break
            
            key = endpoint or 'default'
            now = time.time()
            
            # Remove old requests outside window
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < window
            ]
            
            # Check if at limit
            if len(self.requests[key]) >= max_requests:
                oldest = min(self.requests[key])
                wait_time = window - (now - oldest) + 1
                if wait_time > 0:
                    time.sleep(wait_time)
                    now = time.time()
                    self.requests[key] = [
                        req_time for req_time in self.requests[key]
                        if now - req_time < window
                    ]
            
            # Record this request
            self.requests[key].append(time.time())
```

---

## 4. Session Management

### 4.1 Token Lifecycle Management

**Priority:** 🟡 MEDIUM  
**Effort:** 3-4 hours

**Implementation:**

```python
# File: prisma/session_manager.py

from datetime import datetime, timedelta
from typing import Optional
import atexit

class SessionManager:
    """Manage API session lifecycle and cleanup."""
    
    def __init__(self, api_client):
        """
        Initialize session manager.
        
        Args:
            api_client: PrismaAccessAPIClient instance
        """
        self.api_client = api_client
        self.session_start = datetime.now()
        self.max_session_duration = timedelta(hours=8)
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
    
    def is_session_expired(self) -> bool:
        """Check if session has exceeded maximum duration."""
        return datetime.now() - self.session_start > self.max_session_duration
    
    def refresh_if_needed(self):
        """Refresh session if expired."""
        if self.is_session_expired():
            self.cleanup()
            self.api_client.authenticate()
            self.session_start = datetime.now()
    
    def cleanup(self):
        """Cleanup session data."""
        # Clear cached tokens
        if hasattr(self.api_client, 'access_token'):
            self.api_client.access_token = None
        
        # Clear cache
        if hasattr(self.api_client, 'cache'):
            self.api_client.cache.clear()
        
        # Clear rate limiter history
        if hasattr(self.api_client, 'rate_limiter'):
            self.api_client.rate_limiter.requests.clear()
```

---

## 5. Logging Security

### 5.1 Sensitive Data Sanitization

**Priority:** 🟡 MEDIUM  
**Effort:** 4-5 hours

**Implementation:**

```python
# File: prisma/secure_logger.py

import re
from typing import Any, Dict

class SecureLogger:
    """Logger with automatic sensitive data sanitization."""
    
    SENSITIVE_PATTERNS = {
        'password': re.compile(r'(password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', re.IGNORECASE),
        'api_key': re.compile(r'(api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', re.IGNORECASE),
        'secret': re.compile(r'(secret|token)["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', re.IGNORECASE),
        'authorization': re.compile(r'(authorization|bearer)[:\s]+([^\s,}]+)', re.IGNORECASE),
        'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    }
    
    @staticmethod
    def sanitize(data: Any) -> Any:
        """
        Sanitize sensitive data before logging.
        
        Args:
            data: Data to sanitize (string, dict, list)
            
        Returns:
            Sanitized data
        """
        if isinstance(data, str):
            return SecureLogger._sanitize_string(data)
        elif isinstance(data, dict):
            return {k: SecureLogger.sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [SecureLogger.sanitize(item) for item in data]
        else:
            return data
    
    @staticmethod
    def _sanitize_string(text: str) -> str:
        """Sanitize a string value."""
        for pattern_name, pattern in SecureLogger.SENSITIVE_PATTERNS.items():
            text = pattern.sub(r'\1=***REDACTED***', text)
        return text
    
    @staticmethod
    def safe_log(message: str, data: Any = None) -> str:
        """
        Create a safe log message with sanitized data.
        
        Args:
            message: Log message
            data: Optional data to include
            
        Returns:
            Sanitized log message
        """
        if data:
            sanitized_data = SecureLogger.sanitize(data)
            return f"{message}: {sanitized_data}"
        return message
```

---

## 6. Implementation Timeline

### Week 1: Critical Security Fixes
- **Days 1-2:** Implement PBKDF2 key derivation
- **Days 3-4:** Add comprehensive JSON validation
- **Day 5:** Implement file path validation

### Week 2: API Security & Testing
- **Days 1-2:** Add request size limits and streaming
- **Days 3-4:** Improve rate limiting
- **Day 5:** Add security tests

### Week 3: Session Management & Documentation
- **Days 1-2:** Implement session management
- **Days 3-4:** Add secure logging
- **Day 5:** Update documentation

---

## 7. Testing Plan

### Security Test Suite

```python
# File: tests/test_security.py

import pytest
from config.storage.json_storage_secure import ConfigurationValidator
from config.storage.path_validator import PathValidator

class TestSecurity:
    """Security-focused test suite."""
    
    def test_key_derivation_strength(self):
        """Test that key derivation uses strong parameters."""
        from config.storage.json_storage import derive_key_secure
        cipher, salt = derive_key_secure("test_password")
        
        assert len(salt) == 16  # 128-bit salt
        assert cipher is not None
    
    def test_path_traversal_prevention(self):
        """Test that path traversal attacks are blocked."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            PathValidator.validate_config_path("../../etc/passwd")
    
    def test_json_size_limit(self):
        """Test that oversized JSON is rejected."""
        large_json = '{"data": "' + 'x' * 200_000_000 + '"}'
        
        with pytest.raises(ValueError, match="exceeds maximum size"):
            ConfigurationValidator.validate_json_structure(large_json)
    
    def test_json_depth_limit(self):
        """Test that deeply nested JSON is rejected."""
        # Create deeply nested JSON
        nested = '{"a":' * 30 + '{}' + '}' * 30
        
        with pytest.raises(ValueError, match="exceeds maximum nesting depth"):
            ConfigurationValidator.validate_json_structure(nested)
    
    def test_sensitive_data_sanitization(self):
        """Test that sensitive data is sanitized in logs."""
        from prisma.secure_logger import SecureLogger
        
        data = {
            "password": "super_secret",
            "api_key": "sk-1234567890",
            "username": "admin"
        }
        
        sanitized = SecureLogger.sanitize(data)
        
        assert "super_secret" not in str(sanitized)
        assert "sk-1234567890" not in str(sanitized)
        assert "admin" in str(sanitized)  # Non-sensitive data preserved
```

---

## 8. Rollout Strategy

### Phase 1: Development (Week 1)
1. Implement critical security fixes in development branch
2. Run security test suite
3. Code review

### Phase 2: Testing (Week 2)
4. Integration testing with existing functionality
5. Performance testing
6. Security scanning (bandit, safety)

### Phase 3: Migration (Week 3)
7. Create migration scripts for existing configurations
8. Update documentation
9. Deploy to staging environment

### Phase 4: Production (Week 4)
10. Gradual rollout to production
11. Monitor for issues
12. Complete migration of legacy data

---

## 9. Success Criteria

- [ ] All security tests passing
- [ ] No high-severity findings from bandit/safety
- [ ] Key derivation using PBKDF2 with 480,000 iterations
- [ ] All file operations use path validation
- [ ] JSON validation on all loaded configurations
- [ ] Request size limits enforced
- [ ] Sensitive data sanitized in logs
- [ ] Session cleanup working correctly
- [ ] Migration path tested for legacy configurations
- [ ] Documentation updated

---

## 10. Post-Implementation

### Ongoing Security Maintenance

1. **Regular Dependency Updates**
   - Weekly: Check for security updates
   - Monthly: Full dependency audit with `safety`

2. **Code Security Scanning**
   - Pre-commit: Run `bandit` on changed files
   - PR: Full security scan
   - Weekly: Automated security scans

3. **Penetration Testing**
   - Quarterly: Internal security review
   - Annually: External penetration test

4. **Security Monitoring**
   - Log analysis for suspicious patterns
   - Monitor authentication failures
   - Track unauthorized access attempts

---

## Conclusion

This security hardening plan addresses critical vulnerabilities and implements defense-in-depth security measures. Implementation should be completed **before GUI development** to ensure the GUI layer builds on a secure foundation.

**Total Estimated Effort:** 2-3 weeks  
**Priority:** Critical  
**Dependencies:** None (can start immediately)
