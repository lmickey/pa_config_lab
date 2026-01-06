"""
Response Schema Validator for Prisma Access API.

Validates API responses before parsing to catch schema issues early
and provide better debugging information.
"""

from typing import Dict, Any, List, Optional, Set, Callable
from collections import defaultdict
import logging

from .errors import SchemaValidationError, ResponseParsingError


logger = logging.getLogger(__name__)


class ResponseValidator:
    """Validates API response structure and content"""
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, raise exceptions on validation failures.
                        If False, log warnings and continue.
        """
        self.strict_mode = strict_mode
        self.validation_issues = defaultdict(list)
    
    def validate_response(
        self,
        response: Any,
        expected_type: str,
        endpoint: Optional[str] = None
    ) -> bool:
        """
        Validate API response structure.
        
        Args:
            response: Raw API response (dict or list)
            expected_type: Expected config item type (e.g., 'address_object')
            endpoint: Optional endpoint for context
        
        Returns:
            True if valid (or in non-strict mode)
        
        Raises:
            SchemaValidationError: If strict_mode=True and validation fails
        """
        issues = []
        
        # 1. Validate response is dict or has expected structure
        if not isinstance(response, dict):
            issue = f"Response is not a dict: {type(response).__name__}"
            issues.append(issue)
            if self.strict_mode:
                raise SchemaValidationError(
                    issue,
                    details={'endpoint': endpoint, 'type': expected_type}
                )
        
        # 2. Check for 'data' key (SCM standard format)
        if isinstance(response, dict) and 'data' not in response:
            issue = "Response missing 'data' key"
            issues.append(issue)
            # Not critical - some endpoints return different formats
            logger.debug(f"{issue} for {expected_type} at {endpoint}")
        
        # 3. Validate data is a list
        data = response.get('data', []) if isinstance(response, dict) else []
        if not isinstance(data, list):
            issue = f"Response 'data' is not a list: {type(data).__name__}"
            issues.append(issue)
            if self.strict_mode:
                raise SchemaValidationError(
                    issue,
                    details={'endpoint': endpoint, 'type': expected_type}
                )
        
        # 4. Validate items in data
        if data:
            for i, item in enumerate(data):
                item_issues = self._validate_item(item, expected_type, i)
                issues.extend(item_issues)
        
        # Log issues
        if issues:
            self.validation_issues[expected_type].extend(issues)
            if self.strict_mode:
                raise SchemaValidationError(
                    f"Validation failed: {len(issues)} issues found",
                    details={
                        'endpoint': endpoint,
                        'type': expected_type,
                        'issues': issues[:10]  # Limit to first 10
                    }
                )
            else:
                # Use debug level - many responses legitimately don't have 'data' key
                # (e.g., single-item responses, application lookups)
                logger.debug(
                    f"Response validation issues for {expected_type}: "
                    f"{len(issues)} issues (first: {issues[0] if issues else 'none'})"
                )
        
        return len(issues) == 0
    
    def _validate_item(
        self,
        item: Dict[str, Any],
        expected_type: str,
        index: int
    ) -> List[str]:
        """Validate individual item structure"""
        issues = []
        
        # Item must be a dict
        if not isinstance(item, dict):
            issues.append(f"Item {index} is not a dict: {type(item).__name__}")
            return issues
        
        # Check for required fields
        required_fields = self._get_required_fields(expected_type)
        for field in required_fields:
            if field not in item:
                issues.append(f"Item {index} missing required field: {field}")
        
        # Check for container (folder, snippet, or device)
        containers = [k for k in ['folder', 'snippet', 'device'] if k in item]
        if not containers:
            # Not critical - some items might not have containers
            logger.debug(f"Item {index} has no container (folder/snippet/device)")
        
        return issues
    
    def _get_required_fields(self, item_type: str) -> Set[str]:
        """Get required fields for item type"""
        # All items should have 'name'
        required = {'name'}
        
        # Type-specific requirements
        type_requirements = {
            'address_object': {'name'},
            'address_group': {'name', 'static'},
            'service_object': {'name', 'protocol'},
            'security_rule': {'name', 'from', 'source', 'application', 'action'},
            # Note: 'to' and 'destination' are optional in API responses (can be 'any')
            # Add more as needed
        }
        
        return type_requirements.get(item_type, required)
    
    def validate_item_for_creation(
        self,
        item_dict: Dict[str, Any],
        item_type: str
    ) -> bool:
        """
        Validate item before sending to API for creation.
        
        Args:
            item_dict: Item dictionary to validate
            item_type: Type of item
        
        Returns:
            True if valid
        
        Raises:
            SchemaValidationError: If validation fails
        """
        issues = []
        
        # Check required fields
        required_fields = self._get_required_fields(item_type)
        for field in required_fields:
            if field not in item_dict:
                issues.append(f"Missing required field: {field}")
        
        # Check for name
        if 'name' in item_dict:
            name = item_dict['name']
            if not isinstance(name, str) or not name.strip():
                issues.append("Name must be a non-empty string")
        
        # Check container
        containers = [k for k in ['folder', 'snippet', 'device'] if k in item_dict]
        if len(containers) == 0:
            issues.append("Must specify exactly one container (folder, snippet, or device)")
        elif len(containers) > 1:
            issues.append(f"Cannot specify multiple containers: {containers}")
        
        # Raise if issues found
        if issues:
            raise SchemaValidationError(
                f"Item validation failed: {len(issues)} issues",
                details={'type': item_type, 'issues': issues}
            )
        
        return True
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validation issues encountered"""
        return {
            'total_types_with_issues': len(self.validation_issues),
            'issues_by_type': {
                type_name: len(issues)
                for type_name, issues in self.validation_issues.items()
            },
            'sample_issues': {
                type_name: issues[:3]  # First 3 issues per type
                for type_name, issues in self.validation_issues.items()
            }
        }
    
    def clear_issues(self):
        """Clear recorded validation issues"""
        self.validation_issues.clear()


class ResponseValidatorFactory:
    """Factory for creating validators with different configurations"""
    
    @staticmethod
    def create_development_validator() -> ResponseValidator:
        """Create validator for development (strict mode)"""
        return ResponseValidator(strict_mode=True)
    
    @staticmethod
    def create_production_validator() -> ResponseValidator:
        """Create validator for production (non-strict mode)"""
        return ResponseValidator(strict_mode=False)
    
    @staticmethod
    def create_custom_validator(strict: bool = False) -> ResponseValidator:
        """Create validator with custom settings"""
        return ResponseValidator(strict_mode=strict)


# Convenience functions
def validate_response(
    response: Any,
    expected_type: str,
    strict: bool = False,
    endpoint: Optional[str] = None
) -> bool:
    """
    Validate API response (convenience function).
    
    Args:
        response: API response
        expected_type: Expected type
        strict: Strict mode (raise on errors)
        endpoint: Optional endpoint
    
    Returns:
        True if valid
    """
    validator = ResponseValidator(strict_mode=strict)
    return validator.validate_response(response, expected_type, endpoint)


def validate_for_creation(
    item_dict: Dict[str, Any],
    item_type: str
) -> bool:
    """
    Validate item before creation (convenience function).
    
    Args:
        item_dict: Item dictionary
        item_type: Type of item
    
    Returns:
        True if valid
    
    Raises:
        SchemaValidationError: If validation fails
    """
    validator = ResponseValidator(strict_mode=True)
    return validator.validate_item_for_creation(item_dict, item_type)


__all__ = [
    'ResponseValidator',
    'ResponseValidatorFactory',
    'validate_response',
    'validate_for_creation',
]
