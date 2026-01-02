"""
Configuration models for Prisma Access.

This package contains object-oriented models for all configuration items,
replacing the dictionary-based approach with proper classes.
"""

from .base import (
    ConfigItem,
    PolicyItem,
    ObjectItem,
    ProfileItem,
    RuleItem,
)

from .objects import (
    AddressObject,
    AddressGroup,
    ServiceObject,
    ServiceGroup,
    ApplicationObject,
    ApplicationGroup,
    ApplicationFilter,
    Schedule,
)

__all__ = [
    # Base classes
    'ConfigItem',
    'PolicyItem',
    'ObjectItem',
    'ProfileItem',
    'RuleItem',
    # Object models
    'AddressObject',
    'AddressGroup',
    'ServiceObject',
    'ServiceGroup',
    'ApplicationObject',
    'ApplicationGroup',
    'ApplicationFilter',
    'Schedule',
]
