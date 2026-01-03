"""
Profile model classes for security and configuration profiles.

This module contains ConfigItem subclasses for all profile types including:
- Authentication profiles (SAML, LDAP, etc.)
- Decryption profiles
- URL filtering profiles
- Antivirus profiles
- Anti-spyware profiles
- Vulnerability profiles
- File blocking profiles
- Wildfire analysis profiles
- Profile groups (security profile bundles)
- HIP profiles (Host Information Profiles)
- HIP objects (match criteria)
- HTTP header profiles
- Certificate profiles
- OCSP responders
- SCEP profiles
- QoS profiles
"""

from typing import List, Dict, Any, Optional
import logging
from config.models.base import ProfileItem

logger = logging.getLogger(__name__)


class AuthenticationProfile(ProfileItem):
    """
    Represents an authentication profile.
    
    API Endpoint: /sse/config/v1/authentication-profiles
    
    Types:
        - SAML IdP
        - LDAP
        - RADIUS
        - Kerberos
        - Local Database
        - Cloud Identity Engine (CIE) - should be excluded from push
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/authentication-profiles"
    item_type = "authentication_profile"
    
    @property
    def method_type(self) -> Optional[str]:
        """Get authentication method type"""
        if 'method' in self.raw_config:
            method = self.raw_config['method']
            if isinstance(method, dict):
                for method_type in ['saml_idp', 'ldap', 'radius', 'kerberos', 'local_database', 'cloud']:
                    if method_type in method:
                        return method_type
        return None
    
    @property
    def is_cie_profile(self) -> bool:
        """Check if this is a Cloud Identity Engine profile (should be excluded)"""
        method_type = self.method_type
        if method_type == 'cloud':
            return True
        # Also check for CIE-specific indicators
        if 'cloud_authentication_service' in self.raw_config.get('method', {}):
            return True
        return False
    
    def _validate_specific(self) -> List[str]:
        """Validate authentication profile"""
        errors = []
        
        # Must have method configuration
        if 'method' not in self.raw_config:
            errors.append("Authentication profile must have method configuration")
            return errors
        
        method = self.raw_config['method']
        if not isinstance(method, dict):
            errors.append("Method must be a dictionary")
            return errors
        
        # Must have at least one authentication method
        if not self.method_type:
            errors.append("Authentication profile must specify an authentication method")
        
        return errors


class DecryptionProfile(ProfileItem):
    """
    Represents a decryption profile.
    
    API Endpoint: /sse/config/v1/decryption-profiles
    
    Configures SSL/TLS decryption settings including protocol versions,
    cipher suites, and decryption behavior.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/decryption-profiles"
    item_type = "decryption_profile"
    
    @property
    def ssl_protocol_settings(self) -> Optional[Dict[str, Any]]:
        """Get SSL protocol settings"""
        return self.raw_config.get('ssl_protocol_settings')
    
    @property
    def min_version(self) -> Optional[str]:
        """Get minimum SSL/TLS version"""
        settings = self.ssl_protocol_settings
        if settings and isinstance(settings, dict):
            return settings.get('min_version')
        return None
    
    @property
    def max_version(self) -> Optional[str]:
        """Get maximum SSL/TLS version"""
        settings = self.ssl_protocol_settings
        if settings and isinstance(settings, dict):
            return settings.get('max_version')
        return None
    
    def _validate_specific(self) -> List[str]:
        """Validate decryption profile"""
        errors = []
        
        # Validate SSL protocol settings if present
        if self.ssl_protocol_settings:
            valid_versions = ['sslv3', 'tls1-0', 'tls1-1', 'tls1-2', 'tls1-3', 'max']
            
            if self.min_version and self.min_version not in valid_versions:
                errors.append(f"Invalid min_version: {self.min_version}")
            
            if self.max_version and self.max_version not in valid_versions:
                errors.append(f"Invalid max_version: {self.max_version}")
        
        return errors


# URLFilteringProfile removed - deprecated/non-functional endpoint
# AntivirusProfile removed - endpoint doesn't exist (use AntiSpywareProfile instead)


class AntiSpywareProfile(ProfileItem):
    """
    Represents an anti-spyware profile.
    
    API Endpoint: /sse/config/v1/anti-spyware-profiles
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/anti-spyware-profiles"
    item_type = "anti_spyware_profile"


class VulnerabilityProfile(ProfileItem):
    """
    Represents a vulnerability protection profile.
    
    API Endpoint: /sse/config/v1/vulnerability-protection-profiles
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/vulnerability-protection-profiles"
    item_type = "vulnerability_profile"


class FileBlockingProfile(ProfileItem):
    """
    Represents a file blocking profile.
    
    API Endpoint: /sse/config/v1/file-blocking-profiles
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/file-blocking-profiles"
    item_type = "file_blocking_profile"


class WildfireProfile(ProfileItem):
    """
    Represents a Wildfire anti-virus profile.
    
    API Endpoint: /config/security/v1/wildfire-anti-virus-profiles
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/config/security/v1/wildfire-anti-virus-profiles"
    item_type = "wildfire_profile"


class ProfileGroup(ProfileItem):
    """
    Represents a security profile group (bundle of security profiles).
    
    API Endpoint: /sse/config/v1/profile-groups
    
    Groups together virus, spyware, vulnerability, URL filtering,
    file blocking, and Wildfire profiles.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/profile-groups"
    item_type = "profile_group"
    
    @property
    def virus_profiles(self) -> List[str]:
        """Get list of antivirus profile references"""
        return self.raw_config.get('virus', [])
    
    @property
    def spyware_profiles(self) -> List[str]:
        """Get list of anti-spyware profile references"""
        return self.raw_config.get('spyware', [])
    
    @property
    def vulnerability_profiles(self) -> List[str]:
        """Get list of vulnerability profile references"""
        return self.raw_config.get('vulnerability', [])
    
    @property
    def url_filtering_profiles(self) -> List[str]:
        """Get list of URL filtering profile references"""
        return self.raw_config.get('url_filtering', [])
    
    @property
    def file_blocking_profiles(self) -> List[str]:
        """Get list of file blocking profile references"""
        return self.raw_config.get('file_blocking', [])
    
    @property
    def wildfire_profiles(self) -> List[str]:
        """Get list of Wildfire profile references"""
        return self.raw_config.get('wildfire_analysis', [])
    
    @property
    def has_dependencies(self) -> bool:
        """Override has_dependencies - profile groups depend on member profiles"""
        return (
            len(self.virus_profiles) > 0 or
            len(self.spyware_profiles) > 0 or
            len(self.vulnerability_profiles) > 0 or
            len(self.url_filtering_profiles) > 0 or
            len(self.file_blocking_profiles) > 0 or
            len(self.wildfire_profiles) > 0
        )
    
    def _compute_dependencies(self) -> List[tuple]:
        """Profile groups depend on their member profiles"""
        deps = []
        
        # Note: virus_profiles field exists in API but we don't have a model class
        # (antivirus endpoint doesn't exist - these are likely WildFire AV profiles)
        for profile in self.virus_profiles:
            deps.append(('wildfire_profile', profile))
        
        for profile in self.spyware_profiles:
            deps.append(('anti_spyware_profile', profile))
        
        for profile in self.vulnerability_profiles:
            deps.append(('vulnerability_profile', profile))
        
        # Note: url_filtering_profiles field exists in API but endpoint is deprecated
        # Keeping reference for data integrity but won't create dependency
        # for profile in self.url_filtering_profiles:
        #     deps.append(('url_filtering_profile', profile))
        
        for profile in self.file_blocking_profiles:
            deps.append(('file_blocking_profile', profile))
        
        for profile in self.wildfire_profiles:
            deps.append(('wildfire_profile', profile))
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate profile group"""
        errors = []
        
        # Should have at least one profile type
        has_profiles = (
            len(self.virus_profiles) > 0 or
            len(self.spyware_profiles) > 0 or
            len(self.vulnerability_profiles) > 0 or
            len(self.url_filtering_profiles) > 0 or
            len(self.file_blocking_profiles) > 0 or
            len(self.wildfire_profiles) > 0
        )
        
        if not has_profiles:
            errors.append("Profile group should have at least one security profile")
        
        return errors


class HIPProfile(ProfileItem):
    """
    Represents a Host Information Profile (HIP).
    
    API Endpoint: /sse/config/v1/hip-profiles
    
    Defines device compliance requirements.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/hip-profiles"
    item_type = "hip_profile"
    
    @property
    def match_type(self) -> Optional[str]:
        """Get match type (all or any)"""
        return self.raw_config.get('match')


class HIPObject(ProfileItem):
    """
    Represents a HIP object (match criteria).
    
    API Endpoint: /sse/config/v1/hip-objects
    
    Defines specific HIP match conditions (OS, patch, encryption, etc.).
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/hip-objects"
    item_type = "hip_object"


class HTTPHeaderProfile(ProfileItem):
    """
    Represents an HTTP header insertion profile.
    
    API Endpoint: /sse/config/v1/http-header-profiles
    
    Defines custom HTTP headers to insert into requests/responses.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/http-header-profiles"
    item_type = "http_header_profile"
    
    @property
    def headers(self) -> List[Dict[str, str]]:
        """Get list of HTTP headers"""
        return self.raw_config.get('header', [])


class CertificateProfile(ProfileItem):
    """
    Represents a certificate profile.
    
    API Endpoint: /sse/config/v1/certificate-profiles
    
    Defines certificate validation settings.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/certificate-profiles"
    item_type = "certificate_profile"


class OCSPResponder(ProfileItem):
    """
    Represents an OCSP responder configuration.
    
    API Endpoint: /sse/config/v1/ocsp-responder
    
    Configures Online Certificate Status Protocol responders.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/ocsp-responder"
    item_type = "ocsp_responder"
    
    @property
    def host_name(self) -> Optional[str]:
        """Get OCSP responder hostname"""
        return self.raw_config.get('host_name')


class SCEPProfile(ProfileItem):
    """
    Represents a SCEP profile.
    
    API Endpoint: /sse/config/v1/scep-profiles
    
    Configures Simple Certificate Enrollment Protocol.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/scep-profiles"
    item_type = "scep_profile"
    
    @property
    def ca_identity(self) -> Optional[str]:
        """Get CA identity"""
        return self.raw_config.get('ca_identity')


class QoSProfile(ProfileItem):
    """
    Represents a Quality of Service profile.
    
    API Endpoint: /sse/config/v1/qos-profiles
    
    Defines QoS bandwidth and priority settings.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/qos-profiles"
    item_type = "qos_profile"
    
    @property
    def class_bandwidth_type(self) -> Optional[Dict[str, Any]]:
        """Get class bandwidth type configuration"""
        return self.raw_config.get('class_bandwidth_type')
