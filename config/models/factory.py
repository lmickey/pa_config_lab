"""
Factory for creating ConfigItem instances.

This module provides a factory pattern for instantiating the correct ConfigItem
subclass from raw configuration data or API responses.
"""

from typing import Dict, Any, List, Optional, Type, Callable
import logging
from config.models.base import ConfigItem
from config.models.objects import (
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
from config.models.profiles import (
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
from config.models.policies import (
    SecurityRule,
    DecryptionRule,
    AuthenticationRule,
    QoSPolicyRule,
)
from config.models.infrastructure import (
    IKECryptoProfile,
    IPsecCryptoProfile,
    IKEGateway,
    IPsecTunnel,
    ServiceConnection,
    AgentProfile,
    Portal,
    Gateway,
)

logger = logging.getLogger(__name__)


class ConfigItemFactory:
    """
    Factory for creating ConfigItem instances from raw data.
    
    Provides methods to:
    - Create items from dict with explicit type
    - Create items from API responses
    - Auto-detect item type from data structure
    - Register custom item types
    """
    
    # Type registry mapping item_type strings to ConfigItem classes
    _type_registry: Dict[str, Type[ConfigItem]] = {
        # Objects
        'tag': Tag,
        'address_object': AddressObject,
        'address_group': AddressGroup,
        'service_object': ServiceObject,
        'service_group': ServiceGroup,
        'application_object': ApplicationObject,
        'application_group': ApplicationGroup,
        'application_filter': ApplicationFilter,
        'schedule': Schedule,
        
        # Profiles
        'authentication_profile': AuthenticationProfile,
        'decryption_profile': DecryptionProfile,
        'url_filtering_profile': URLFilteringProfile,
        'antivirus_profile': AntivirusProfile,
        'anti_spyware_profile': AntiSpywareProfile,
        'vulnerability_profile': VulnerabilityProfile,
        'file_blocking_profile': FileBlockingProfile,
        'wildfire_profile': WildfireProfile,
        'profile_group': ProfileGroup,
        'hip_profile': HIPProfile,
        'hip_object': HIPObject,
        'http_header_profile': HTTPHeaderProfile,
        'certificate_profile': CertificateProfile,
        'ocsp_responder': OCSPResponder,
        'scep_profile': SCEPProfile,
        'qos_profile': QoSProfile,
        
        # Policies/Rules
        'security_rule': SecurityRule,
        'decryption_rule': DecryptionRule,
        'authentication_rule': AuthenticationRule,
        'qos_policy_rule': QoSPolicyRule,
        
        # Infrastructure
        'ike_crypto_profile': IKECryptoProfile,
        'ipsec_crypto_profile': IPsecCryptoProfile,
        'ike_gateway': IKEGateway,
        'ipsec_tunnel': IPsecTunnel,
        'service_connection': ServiceConnection,
        'agent_profile': AgentProfile,
        'portal': Portal,
        'gateway': Gateway,
    }
    
    # API endpoint to item_type mapping
    _endpoint_mapping: Dict[str, str] = {
        '/sse/config/v1/tags': 'tag',
        '/sse/config/v1/addresses': 'address_object',
        '/sse/config/v1/address-groups': 'address_group',
        '/sse/config/v1/services': 'service_object',
        '/sse/config/v1/service-groups': 'service_group',
        '/sse/config/v1/applications': 'application_object',
        '/sse/config/v1/application-groups': 'application_group',
        '/sse/config/v1/application-filters': 'application_filter',
        '/sse/config/v1/schedules': 'schedule',
        
        '/sse/config/v1/authentication-profiles': 'authentication_profile',
        '/sse/config/v1/decryption-profiles': 'decryption_profile',
        '/sse/config/v1/url-filtering-profiles': 'url_filtering_profile',
        '/sse/config/v1/anti-spyware-profiles': 'anti_spyware_profile',
        '/sse/config/v1/vulnerability-protection-profiles': 'vulnerability_profile',
        '/sse/config/v1/wildfire-anti-virus-profiles': 'antivirus_profile',
        '/sse/config/v1/file-blocking-profiles': 'file_blocking_profile',
        '/sse/config/v1/wildfire-profiles': 'wildfire_profile',
        '/sse/config/v1/profile-groups': 'profile_group',
        '/sse/config/v1/hip-profiles': 'hip_profile',
        '/sse/config/v1/hip-objects': 'hip_object',
        '/sse/config/v1/http-header-profiles': 'http_header_profile',
        '/sse/config/v1/certificate-profiles': 'certificate_profile',
        '/sse/config/v1/ocsp-responder': 'ocsp_responder',
        '/sse/config/v1/scep-profiles': 'scep_profile',
        '/sse/config/v1/qos-profiles': 'qos_profile',
        
        '/sse/config/v1/security-rules': 'security_rule',
        '/sse/config/v1/decryption-rules': 'decryption_rule',
        '/sse/config/v1/authentication-rules': 'authentication_rule',
        '/sse/config/v1/qos-policy-rules': 'qos_policy_rule',
        
        '/sse/config/v1/ike-crypto-profiles': 'ike_crypto_profile',
        '/sse/config/v1/ipsec-crypto-profiles': 'ipsec_crypto_profile',
        '/sse/config/v1/ike-gateways': 'ike_gateway',
        '/sse/config/v1/ipsec-tunnels': 'ipsec_tunnel',
        '/sse/config/v1/service-connections': 'service_connection',
        '/sse/config/v1/mobile-agent/agent-profiles': 'agent_profile',
        '/sse/config/v1/mobile-agent/portals': 'portal',
        '/sse/config/v1/mobile-agent/gateways': 'gateway',
    }
    
    @classmethod
    def register_type(cls, item_type: str, item_class: Type[ConfigItem]) -> None:
        """
        Register a custom ConfigItem type.
        
        Args:
            item_type: String identifier for the type
            item_class: ConfigItem subclass
        """
        cls._type_registry[item_type] = item_class
        logger.debug(f"Registered type '{item_type}' -> {item_class.__name__}")
    
    @classmethod
    def register_endpoint(cls, endpoint: str, item_type: str) -> None:
        """
        Register an API endpoint to item_type mapping.
        
        Args:
            endpoint: API endpoint path
            item_type: Item type string
        """
        cls._endpoint_mapping[endpoint] = item_type
        logger.debug(f"Registered endpoint '{endpoint}' -> '{item_type}'")
    
    @classmethod
    def create_from_dict(cls, item_type: str, raw_config: Dict[str, Any]) -> ConfigItem:
        """
        Create a ConfigItem from a dict with explicit type.
        
        Args:
            item_type: Type of item to create
            raw_config: Raw configuration dictionary
            
        Returns:
            ConfigItem instance
            
        Raises:
            ValueError: If item_type is unknown
        """
        if item_type not in cls._type_registry:
            raise ValueError(f"Unknown item type: {item_type}")
        
        item_class = cls._type_registry[item_type]
        
        try:
            item = item_class(raw_config)
            logger.debug(f"Created {item_type} '{item.name}' from dict")
            return item
        except Exception as e:
            logger.error(f"Error creating {item_type} from dict: {e}")
            raise
    
    @classmethod
    def create_from_api_response(cls, endpoint: str, response: Dict[str, Any]) -> List[ConfigItem]:
        """
        Create ConfigItem instances from API response.
        
        API responses typically have format:
        {
            "data": [...],
            "total": N,
            "limit": M,
            "offset": O
        }
        
        Args:
            endpoint: API endpoint that returned this response
            response: API response dictionary
            
        Returns:
            List of ConfigItem instances
            
        Raises:
            ValueError: If endpoint is unknown or response format invalid
        """
        # Determine item type from endpoint
        item_type = None
        for ep, itype in cls._endpoint_mapping.items():
            if ep in endpoint:
                item_type = itype
                break
        
        if not item_type:
            raise ValueError(f"Unknown endpoint: {endpoint}")
        
        # Extract data array from response
        if isinstance(response, dict):
            data = response.get('data', [])
        elif isinstance(response, list):
            data = response
        else:
            raise ValueError(f"Invalid response format: expected dict or list, got {type(response)}")
        
        # Create items
        items = []
        for raw_config in data:
            try:
                item = cls.create_from_dict(item_type, raw_config)
                items.append(item)
            except Exception as e:
                logger.warning(f"Skipping item due to error: {e}")
                continue
        
        logger.info(f"Created {len(items)} {item_type} items from API response")
        return items
    
    @classmethod
    def auto_detect_type(cls, raw_config: Dict[str, Any]) -> Optional[str]:
        """
        Auto-detect item type from raw configuration structure.
        
        Uses heuristics to identify type:
        - Presence of specific keys
        - Value patterns
        - Structure patterns
        
        Args:
            raw_config: Raw configuration dictionary
            
        Returns:
            Detected item_type string or None if unknown
        """
        # Check for explicit item_type field
        if 'item_type' in raw_config:
            return raw_config['item_type']
        
        # Tags - have color, may have both folder and snippet
        if 'color' in raw_config and ('folder' in raw_config or 'snippet' in raw_config):
            return 'tag'
        
        # Address objects - have ip-netmask, ip-range, or fqdn in 'type' field
        if 'type' in raw_config:
            addr_types = ['ip-netmask', 'ip-range', 'fqdn', 'ip-wildcard']
            if raw_config['type'] in addr_types:
                return 'address_object'
        
        # Address groups - have static or dynamic members (check BEFORE general address check)
        if 'static' in raw_config or 'dynamic' in raw_config:
            return 'address_group'
        
        # Address objects can also have just 'value' or 'fqdn' or 'ip_netmask' field
        if any(key in raw_config for key in ['value', 'fqdn', 'ip_netmask', 'ip_range', 'ip_wildcard']):
            # Has address-like fields but not protocol/esp (which would be service/ipsec crypto)
            if 'protocol' not in raw_config and 'esp' not in raw_config:
                # Make sure it's not a group (groups have members)
                if 'members' not in raw_config:
                    return 'address_object'
        
        # Service objects - have protocol
        if 'protocol' in raw_config:
            proto = raw_config['protocol']
            if isinstance(proto, dict) and ('tcp' in proto or 'udp' in proto):
                return 'service_object'
        
        # Service groups - have members list
        if 'members' in raw_config and isinstance(raw_config.get('members'), list):
            # Could be service group or application group
            # Check for application-specific patterns
            if any(key in raw_config for key in ['category', 'subcategory', 'technology']):
                return 'application_group'
            return 'service_group'
        
        # Security rules - have action, from, to
        if 'action' in raw_config and 'from' in raw_config and 'to' in raw_config:
            action = raw_config['action']
            if action in ['allow', 'deny', 'drop', 'reset-client', 'reset-server', 'reset-both']:
                return 'security_rule'
        
        # Authentication profiles - have method
        if 'method' in raw_config:
            method = raw_config['method']
            if isinstance(method, dict):
                auth_methods = ['saml_idp', 'ldap', 'radius', 'kerberos', 'local_database', 'cloud']
                if any(m in method for m in auth_methods):
                    return 'authentication_profile'
        
        # Profile groups - have virus_and_wildfire_analysis, spyware, etc.
        if any(key in raw_config for key in ['virus_and_wildfire_analysis', 'spyware', 'vulnerability']):
            return 'profile_group'
        
        # IKE crypto profiles - have encryption, authentication, dh_group (Phase 1)
        if all(key in raw_config for key in ['encryption', 'authentication', 'dh_group']):
            return 'ike_crypto_profile'
        
        # IPsec crypto profiles - have esp (Phase 2)
        if 'esp' in raw_config:
            esp = raw_config['esp']
            if isinstance(esp, dict) and 'encryption' in esp:
                return 'ipsec_crypto_profile'
        
        # IKE gateways - have peer_address, authentication, protocol
        if all(key in raw_config for key in ['peer_address', 'authentication', 'protocol']):
            if 'protocol_common' in raw_config:
                return 'ike_gateway'
        
        # IPsec tunnels - have auto_key with ike_gateway and ipsec_crypto_profile
        if 'auto_key' in raw_config:
            auto_key = raw_config['auto_key']
            if isinstance(auto_key, dict) and 'ike_gateway' in auto_key:
                return 'ipsec_tunnel'
        
        # Service connections - have ipsec_tunnel and subnets
        if 'ipsec_tunnel' in raw_config and 'subnets' in raw_config:
            return 'service_connection'
        
        # Agent profiles - have connect_method
        if 'connect_method' in raw_config:
            return 'agent_profile'
        
        # Portals/Gateways - have authentication
        if 'authentication' in raw_config:
            # Check for gateway-specific keys first (more specific)
            if 'tunnel_settings' in raw_config:
                return 'gateway'
            # Check for portal-specific keys
            if 'client_download' in raw_config:
                return 'portal'
            # If just authentication without other specific keys, could be portal
            # (portals can have just authentication in minimal configs)
            # Check if not other types (agent profile also has authentication)
            if 'connect_method' not in raw_config:
                # Likely a portal (minimal config)
                return 'portal'
        
        logger.warning(f"Could not auto-detect type for item: {raw_config.get('name', 'unknown')}")
        return None
    
    @classmethod
    def create_with_auto_detect(cls, raw_config: Dict[str, Any]) -> Optional[ConfigItem]:
        """
        Create a ConfigItem with auto-detected type.
        
        Args:
            raw_config: Raw configuration dictionary
            
        Returns:
            ConfigItem instance or None if type cannot be detected
        """
        item_type = cls.auto_detect_type(raw_config)
        
        if not item_type:
            logger.error(f"Cannot auto-detect type for item: {raw_config.get('name', 'unknown')}")
            return None
        
        try:
            return cls.create_from_dict(item_type, raw_config)
        except Exception as e:
            logger.error(f"Error creating item with auto-detected type '{item_type}': {e}")
            return None
    
    @classmethod
    def get_registered_types(cls) -> List[str]:
        """Get list of all registered item types"""
        return list(cls._type_registry.keys())
    
    @classmethod
    def get_registered_endpoints(cls) -> Dict[str, str]:
        """Get dict of all registered endpoints and their types"""
        return cls._endpoint_mapping.copy()
    
    @classmethod
    def is_type_registered(cls, item_type: str) -> bool:
        """Check if an item type is registered"""
        return item_type in cls._type_registry
    
    @classmethod
    def get_class_for_type(cls, item_type: str) -> Optional[Type[ConfigItem]]:
        """Get the ConfigItem class for a given type"""
        return cls._type_registry.get(item_type)
