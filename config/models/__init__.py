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

__all__ = [
    'ConfigItem',
    'PolicyItem',
    'ObjectItem',
    'ProfileItem',
    'RuleItem',
]
