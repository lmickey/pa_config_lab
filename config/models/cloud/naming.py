"""
Naming convention utilities for cloud resources.

All resource names follow the pattern:
  {customer}-{region}-{management_type}-rg  (resource group)
  {resource_group}-{resource_type}          (individual resources)
"""

import re
from typing import Optional


def sanitize_name(name: str, max_length: int = 63) -> str:
    """
    Sanitize name for Azure resource naming.

    Azure naming rules:
    - Alphanumeric and hyphens only
    - Cannot start or end with hyphen
    - Various length limits (typically 63 chars)

    Args:
        name: Raw name to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized name
    """
    # Convert to lowercase
    name = name.lower()

    # Replace underscores and spaces with hyphens
    name = re.sub(r'[_\s]+', '-', name)

    # Remove any character that's not alphanumeric or hyphen
    name = re.sub(r'[^a-z0-9-]', '', name)

    # Remove leading/trailing hyphens
    name = name.strip('-')

    # Collapse multiple hyphens
    name = re.sub(r'-+', '-', name)

    # Truncate to max length
    if len(name) > max_length:
        name = name[:max_length].rstrip('-')

    return name


def generate_resource_group_name(
    customer: str,
    location: str,
    management_type: str
) -> str:
    """
    Generate resource group name.

    Format: {customer}-{location}-{management_type}-rg

    Args:
        customer: Customer name
        location: Azure region (e.g., eastus)
        management_type: scm or pan

    Returns:
        Resource group name
    """
    customer = sanitize_name(customer, 20)
    location = sanitize_name(location, 20)
    management_type = sanitize_name(management_type, 5)

    return f"{customer}-{location}-{management_type}-rg"


def generate_resource_name(
    resource_group: str,
    resource_type: str,
    index: Optional[int] = None
) -> str:
    """
    Generate individual resource name.

    Format: {resource_group}-{resource_type}[{index}]

    Args:
        resource_group: Resource group name
        resource_type: Type identifier (fw, panorama, server, etc.)
        index: Optional numeric index for multiple resources

    Returns:
        Resource name
    """
    name = f"{resource_group}-{resource_type}"
    if index is not None:
        name = f"{name}{index}"
    return sanitize_name(name)


def generate_vm_username(resource_group: str) -> str:
    """
    Generate VM admin username.

    Format: {resource_group}_admin (with sanitization)

    Args:
        resource_group: Resource group name

    Returns:
        Admin username
    """
    # Replace hyphens with underscores for username
    base = resource_group.replace('-', '_')
    return f"{base}_admin"[:20]  # Azure username max 20 chars
