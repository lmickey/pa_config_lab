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
    Tag,
    AddressObject,
    AddressGroup,
    ServiceObject,
    ServiceGroup,
    ApplicationObject,
    ApplicationGroup,
    ApplicationFilter,
    Schedule,
)

from .profiles import (
    AuthenticationProfile,
    DecryptionProfile,
    URLFilteringProfile,
    AntivirusProfile,
    AntiSpywareProfile,
    VulnerabilityProfile,
    FileBlockingProfile,
    WildfireProfile,
    ProfileGroup,
    HIPProfile,
    HIPObject,
    HTTPHeaderProfile,
    CertificateProfile,
    OCSPResponder,
    SCEPProfile,
    QoSProfile,
)

from .policies import (
    SecurityRule,
    NATRule,
    DecryptionRule,
    AuthenticationRule,
    QoSPolicyRule,
    PBFRule,
)

__all__ = [
    # Base classes
    'ConfigItem',
    'PolicyItem',
    'ObjectItem',
    'ProfileItem',
    'RuleItem',
    # Object models
    'Tag',
    'AddressObject',
    'AddressGroup',
    'ServiceObject',
    'ServiceGroup',
    'ApplicationObject',
    'ApplicationGroup',
    'ApplicationFilter',
    'Schedule',
    # Profile models
    'AuthenticationProfile',
    'DecryptionProfile',
    'URLFilteringProfile',
    'AntivirusProfile',
    'AntiSpywareProfile',
    'VulnerabilityProfile',
    'FileBlockingProfile',
    'WildfireProfile',
    'ProfileGroup',
    'HIPProfile',
    'HIPObject',
    'HTTPHeaderProfile',
    'CertificateProfile',
    'OCSPResponder',
    'SCEPProfile',
    'QoSProfile',
    # Policy/Rule models
    'SecurityRule',
    'NATRule',
    'DecryptionRule',
    'AuthenticationRule',
    'QoSPolicyRule',
    'PBFRule',
]
