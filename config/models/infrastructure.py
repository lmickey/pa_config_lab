"""
Infrastructure model classes for Remote Networks and Mobile Users.

This module contains ConfigItem subclasses for infrastructure components:
- IKE and IPsec crypto profiles
- IKE gateways and IPsec tunnels
- Service connections (Remote Networks)
- Agent profiles, portals, and gateways (Mobile Users/GlobalProtect)

Infrastructure items have deep dependency chains:
Service Connection → IPsec Tunnel → IKE Gateway → Crypto Profiles
"""

from typing import List, Dict, Any, Optional
import logging
from config.models.base import ConfigItem

logger = logging.getLogger(__name__)


class IKECryptoProfile(ConfigItem):
    """
    Represents an IKE (Phase 1) crypto profile.
    
    API Endpoint: /sse/config/v1/ike-crypto-profiles
    
    IKE crypto profiles define encryption, authentication, and DH group
    settings for Phase 1 (IKE SA) negotiations.
    
    Note: Infrastructure items must have folder set (not snippet).
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/ike-crypto-profiles"
    item_type = "ike_crypto_profile"
    
    def __init__(self, raw_config: Dict[str, Any]):
        """Initialize IKE crypto profile - must have folder"""
        # Infrastructure requires folder, not snippet
        if 'snippet' in raw_config and not raw_config.get('folder'):
            raise ValueError("Infrastructure items must have folder set, not snippet")
        super().__init__(raw_config)
    
    @property
    def encryption(self) -> List[str]:
        """Get encryption algorithms"""
        return self.raw_config.get('encryption', [])
    
    @property
    def authentication(self) -> List[str]:
        """Get authentication algorithms"""
        return self.raw_config.get('authentication', [])
    
    @property
    def dh_group(self) -> List[str]:
        """Get Diffie-Hellman groups"""
        return self.raw_config.get('dh_group', [])
    
    @property
    def lifetime(self) -> Optional[Dict[str, Any]]:
        """Get IKE SA lifetime"""
        return self.raw_config.get('lifetime')
    
    def _validate_specific(self) -> List[str]:
        """Validate IKE crypto profile"""
        errors = []
        
        # Must have folder (infrastructure requirement)
        if not self.folder:
            errors.append("IKE crypto profile must have folder set")
        
        # Must have encryption
        if not self.encryption:
            errors.append("IKE crypto profile must have at least one encryption algorithm")
        
        # Must have authentication
        if not self.authentication:
            errors.append("IKE crypto profile must have at least one authentication algorithm")
        
        # Must have DH group
        if not self.dh_group:
            errors.append("IKE crypto profile must have at least one DH group")
        
        return errors


class IPsecCryptoProfile(ConfigItem):
    """
    Represents an IPsec (Phase 2) crypto profile.
    
    API Endpoint: /sse/config/v1/ipsec-crypto-profiles
    
    IPsec crypto profiles define encryption and authentication settings
    for Phase 2 (IPsec SA) negotiations.
    
    Note: Infrastructure items must have folder set (not snippet).
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/ipsec-crypto-profiles"
    item_type = "ipsec_crypto_profile"
    
    def __init__(self, raw_config: Dict[str, Any]):
        """Initialize IPsec crypto profile - must have folder"""
        # Infrastructure requires folder, not snippet
        if 'snippet' in raw_config and not raw_config.get('folder'):
            raise ValueError("Infrastructure items must have folder set, not snippet")
        super().__init__(raw_config)
    
    @property
    def esp_encryption(self) -> List[str]:
        """Get ESP encryption algorithms"""
        esp = self.raw_config.get('esp', {})
        return esp.get('encryption', []) if isinstance(esp, dict) else []
    
    @property
    def esp_authentication(self) -> List[str]:
        """Get ESP authentication algorithms"""
        esp = self.raw_config.get('esp', {})
        return esp.get('authentication', []) if isinstance(esp, dict) else []
    
    @property
    def dh_group(self) -> Optional[str]:
        """Get Perfect Forward Secrecy DH group"""
        return self.raw_config.get('dh_group')
    
    @property
    def lifetime(self) -> Optional[Dict[str, Any]]:
        """Get IPsec SA lifetime"""
        return self.raw_config.get('lifetime')
    
    def _validate_specific(self) -> List[str]:
        """Validate IPsec crypto profile"""
        errors = []
        
        # Must have folder (infrastructure requirement)
        if not self.folder:
            errors.append("IPsec crypto profile must have folder set")
        
        # Must have ESP configuration
        if not self.esp_encryption:
            errors.append("IPsec crypto profile must have at least one ESP encryption algorithm")
        
        if not self.esp_authentication:
            errors.append("IPsec crypto profile must have at least one ESP authentication algorithm")
        
        return errors


class IKEGateway(ConfigItem):
    """
    Represents an IKE Gateway.
    
    API Endpoint: /sse/config/v1/ike-gateways
    
    IKE gateways define peer configuration, authentication, and protocol
    settings for establishing IKE SAs.
    
    Dependencies: IKECryptoProfile
    Note: Infrastructure items must have folder set (not snippet).
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/ike-gateways"
    item_type = "ike_gateway"
    
    def __init__(self, raw_config: Dict[str, Any]):
        """Initialize IKE gateway - must have folder"""
        # Infrastructure requires folder, not snippet
        if 'snippet' in raw_config and not raw_config.get('folder'):
            raise ValueError("Infrastructure items must have folder set, not snippet")
        super().__init__(raw_config)
    
    @property
    def peer_address(self) -> Optional[Dict[str, Any]]:
        """Get peer address configuration"""
        return self.raw_config.get('peer_address')
    
    @property
    def authentication(self) -> Optional[Dict[str, Any]]:
        """Get authentication configuration"""
        return self.raw_config.get('authentication')
    
    @property
    def protocol(self) -> Optional[Dict[str, Any]]:
        """Get protocol configuration (IKEv1/IKEv2)"""
        return self.raw_config.get('protocol')
    
    @property
    def protocol_common(self) -> Optional[Dict[str, Any]]:
        """Get protocol common settings"""
        return self.raw_config.get('protocol_common')
    
    @property
    def ike_crypto_profile_name(self) -> Optional[str]:
        """Get IKE crypto profile reference"""
        if self.protocol_common and isinstance(self.protocol_common, dict):
            crypto = self.protocol_common.get('ike_crypto_profile')
            if isinstance(crypto, str):
                return crypto
        return None
    
    @property
    def has_dependencies(self) -> bool:
        """Override to correctly detect IKE gateway dependencies"""
        return self.ike_crypto_profile_name is not None
    
    def _compute_dependencies(self) -> List[tuple]:
        """IKE gateways depend on IKE crypto profiles"""
        deps = []
        
        # IKE crypto profile dependency
        if self.ike_crypto_profile_name:
            deps.append(('ike_crypto_profile', self.ike_crypto_profile_name))
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate IKE gateway"""
        errors = []
        
        # Must have folder (infrastructure requirement)
        if not self.folder:
            errors.append("IKE gateway must have folder set")
        
        # Must have peer address
        if not self.peer_address:
            errors.append("IKE gateway must have peer address")
        
        # Must have authentication
        if not self.authentication:
            errors.append("IKE gateway must have authentication configuration")
        
        # Must have protocol configuration
        if not self.protocol:
            errors.append("IKE gateway must have protocol configuration")
        
        return errors


class IPsecTunnel(ConfigItem):
    """
    Represents an IPsec Tunnel.
    
    API Endpoint: /sse/config/v1/ipsec-tunnels
    
    IPsec tunnels define tunnel configuration including crypto profiles
    and anti-replay settings.
    
    Dependencies: IKEGateway (which depends on IKECryptoProfile), IPsecCryptoProfile
    Note: Infrastructure items must have folder set (not snippet).
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/ipsec-tunnels"
    item_type = "ipsec_tunnel"
    
    def __init__(self, raw_config: Dict[str, Any]):
        """Initialize IPsec tunnel - must have folder"""
        # Infrastructure requires folder, not snippet
        if 'snippet' in raw_config and not raw_config.get('folder'):
            raise ValueError("Infrastructure items must have folder set, not snippet")
        super().__init__(raw_config)
    
    @property
    def ike_gateway_name(self) -> Optional[str]:
        """Get IKE gateway reference"""
        auto_key = self.raw_config.get('auto_key', {})
        if isinstance(auto_key, dict):
            return auto_key.get('ike_gateway')
        return None
    
    @property
    def ipsec_crypto_profile_name(self) -> Optional[str]:
        """Get IPsec crypto profile reference"""
        auto_key = self.raw_config.get('auto_key', {})
        if isinstance(auto_key, dict):
            return auto_key.get('ipsec_crypto_profile')
        return None
    
    @property
    def anti_replay(self) -> Optional[bool]:
        """Get anti-replay setting"""
        return self.raw_config.get('anti_replay')
    
    @property
    def tunnel_monitor(self) -> Optional[Dict[str, Any]]:
        """Get tunnel monitoring configuration"""
        return self.raw_config.get('tunnel_monitor')
    
    @property
    def has_dependencies(self) -> bool:
        """Override to correctly detect IPsec tunnel dependencies"""
        return self.ike_gateway_name is not None or self.ipsec_crypto_profile_name is not None
    
    def _compute_dependencies(self) -> List[tuple]:
        """IPsec tunnels depend on IKE gateway and IPsec crypto profile"""
        deps = []
        
        # IKE gateway dependency (which has its own dependencies)
        if self.ike_gateway_name:
            deps.append(('ike_gateway', self.ike_gateway_name))
        
        # IPsec crypto profile dependency
        if self.ipsec_crypto_profile_name:
            deps.append(('ipsec_crypto_profile', self.ipsec_crypto_profile_name))
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate IPsec tunnel"""
        errors = []
        
        # Must have folder (infrastructure requirement)
        if not self.folder:
            errors.append("IPsec tunnel must have folder set")
        
        # Must have auto_key configuration
        if not self.raw_config.get('auto_key'):
            errors.append("IPsec tunnel must have auto_key configuration")
        
        # Must have IKE gateway
        if not self.ike_gateway_name:
            errors.append("IPsec tunnel must have IKE gateway reference")
        
        # Must have IPsec crypto profile
        if not self.ipsec_crypto_profile_name:
            errors.append("IPsec tunnel must have IPsec crypto profile reference")
        
        return errors


class ServiceConnection(ConfigItem):
    """
    Represents a Service Connection (Remote Network).
    
    API Endpoint: /sse/config/v1/service-connections
    
    Service connections define remote network connectivity including
    IPsec tunnels, BGP configuration, and routing.
    
    Dependencies: IPsecTunnel (which depends on IKEGateway and IPsecCryptoProfile)
    Note: Infrastructure items must have folder set (not snippet).
    
    May include NAT configuration properties (hard-coded, not rule-based).
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/service-connections"
    item_type = "service_connection"
    
    def __init__(self, raw_config: Dict[str, Any]):
        """Initialize service connection - must have folder"""
        # Infrastructure requires folder, not snippet
        if 'snippet' in raw_config and not raw_config.get('folder'):
            raise ValueError("Infrastructure items must have folder set, not snippet")
        super().__init__(raw_config)
    
    @property
    def ipsec_tunnel_name(self) -> Optional[str]:
        """Get IPsec tunnel reference"""
        return self.raw_config.get('ipsec_tunnel')
    
    @property
    def bgp_peer(self) -> Optional[Dict[str, Any]]:
        """Get BGP peer configuration"""
        return self.raw_config.get('bgp_peer')
    
    @property
    def subnets(self) -> List[str]:
        """Get subnets to advertise"""
        return self.raw_config.get('subnets', [])
    
    @property
    def backup_sc(self) -> Optional[str]:
        """Get backup service connection"""
        return self.raw_config.get('backup_sc')
    
    @property
    def nat_pool(self) -> Optional[str]:
        """Get NAT pool configuration (if applicable)"""
        return self.raw_config.get('nat_pool')
    
    @property
    def source_nat(self) -> Optional[Dict[str, Any]]:
        """Get source NAT configuration (if applicable)"""
        return self.raw_config.get('source_nat')
    
    @property
    def qos(self) -> Optional[Dict[str, Any]]:
        """Get QoS configuration"""
        return self.raw_config.get('qos')
    
    @property
    def has_dependencies(self) -> bool:
        """Override to correctly detect service connection dependencies"""
        return self.ipsec_tunnel_name is not None or self.backup_sc is not None
    
    def _compute_dependencies(self) -> List[tuple]:
        """Service connections depend on IPsec tunnels"""
        deps = []
        
        # IPsec tunnel dependency (which has its own dependency chain)
        if self.ipsec_tunnel_name:
            deps.append(('ipsec_tunnel', self.ipsec_tunnel_name))
        
        # Backup service connection dependency
        if self.backup_sc:
            deps.append(('service_connection', self.backup_sc))
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate service connection"""
        errors = []
        
        # Must have folder (infrastructure requirement)
        if not self.folder:
            errors.append("Service connection must have folder set")
        
        # Must have IPsec tunnel
        if not self.ipsec_tunnel_name:
            errors.append("Service connection must have IPsec tunnel reference")
        
        return errors


class AgentProfile(ConfigItem):
    """
    Represents a GlobalProtect Agent Profile (Mobile Users).
    
    API Endpoint: /sse/config/v1/mobile-agent/agent-profiles
    
    Agent profiles define GlobalProtect client settings including
    authentication, app settings, and connection preferences.
    
    Note: Infrastructure items must have folder set (not snippet).
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/mobile-agent/agent-profiles"
    item_type = "agent_profile"
    
    def __init__(self, raw_config: Dict[str, Any]):
        """Initialize agent profile - must have folder"""
        # Infrastructure requires folder, not snippet
        if 'snippet' in raw_config and not raw_config.get('folder'):
            raise ValueError("Infrastructure items must have folder set, not snippet")
        super().__init__(raw_config)
    
    @property
    def authentication(self) -> Optional[Dict[str, Any]]:
        """Get authentication configuration"""
        return self.raw_config.get('authentication')
    
    @property
    def app_settings(self) -> Optional[Dict[str, Any]]:
        """Get application settings"""
        return self.raw_config.get('app_settings')
    
    @property
    def connect_method(self) -> Optional[str]:
        """Get connect method (on-demand, user-logon, pre-logon)"""
        return self.raw_config.get('connect_method')
    
    @property
    def split_tunneling(self) -> Optional[Dict[str, Any]]:
        """Get split tunneling configuration"""
        return self.raw_config.get('split_tunneling')
    
    def _validate_specific(self) -> List[str]:
        """Validate agent profile"""
        errors = []
        
        # Must have folder (infrastructure requirement)
        if not self.folder:
            errors.append("Agent profile must have folder set")
        
        return errors


class Portal(ConfigItem):
    """
    Represents a GlobalProtect Portal (Mobile Users).
    
    API Endpoint: /sse/config/v1/mobile-agent/portals
    
    Portals define the GlobalProtect portal configuration including
    authentication and client download settings.
    
    Note: Infrastructure items must have folder set (not snippet).
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/mobile-agent/portals"
    item_type = "portal"
    
    def __init__(self, raw_config: Dict[str, Any]):
        """Initialize portal - must have folder"""
        # Infrastructure requires folder, not snippet
        if 'snippet' in raw_config and not raw_config.get('folder'):
            raise ValueError("Infrastructure items must have folder set, not snippet")
        super().__init__(raw_config)
    
    @property
    def authentication(self) -> Optional[Dict[str, Any]]:
        """Get authentication configuration"""
        return self.raw_config.get('authentication')
    
    @property
    def client_download(self) -> Optional[Dict[str, Any]]:
        """Get client download configuration"""
        return self.raw_config.get('client_download')
    
    @property
    def certificate_profile(self) -> Optional[str]:
        """Get certificate profile reference"""
        return self.raw_config.get('certificate_profile')
    
    @property
    def has_dependencies(self) -> bool:
        """Override to correctly detect portal dependencies"""
        return self.certificate_profile is not None
    
    def _compute_dependencies(self) -> List[tuple]:
        """Portals may depend on certificate profiles"""
        deps = []
        
        # Certificate profile dependency
        if self.certificate_profile:
            deps.append(('certificate_profile', self.certificate_profile))
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate portal"""
        errors = []
        
        # Must have folder (infrastructure requirement)
        if not self.folder:
            errors.append("Portal must have folder set")
        
        return errors


class Gateway(ConfigItem):
    """
    Represents a GlobalProtect Gateway (Mobile Users).
    
    API Endpoint: /sse/config/v1/mobile-agent/gateways
    
    Gateways define GlobalProtect gateway configuration including
    authentication, client settings, and tunnel settings.
    
    Note: Infrastructure items must have folder set (not snippet).
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/mobile-agent/gateways"
    item_type = "gateway"
    
    def __init__(self, raw_config: Dict[str, Any]):
        """Initialize gateway - must have folder"""
        # Infrastructure requires folder, not snippet
        if 'snippet' in raw_config and not raw_config.get('folder'):
            raise ValueError("Infrastructure items must have folder set, not snippet")
        super().__init__(raw_config)
    
    @property
    def authentication(self) -> Optional[Dict[str, Any]]:
        """Get authentication configuration"""
        return self.raw_config.get('authentication')
    
    @property
    def client_settings(self) -> Optional[Dict[str, Any]]:
        """Get client settings"""
        return self.raw_config.get('client_settings')
    
    @property
    def tunnel_settings(self) -> Optional[Dict[str, Any]]:
        """Get tunnel settings"""
        return self.raw_config.get('tunnel_settings')
    
    @property
    def certificate_profile(self) -> Optional[str]:
        """Get certificate profile reference"""
        return self.raw_config.get('certificate_profile')
    
    @property
    def has_dependencies(self) -> bool:
        """Override to correctly detect gateway dependencies"""
        return self.certificate_profile is not None
    
    def _compute_dependencies(self) -> List[tuple]:
        """Gateways may depend on certificate profiles"""
        deps = []
        
        # Certificate profile dependency
        if self.certificate_profile:
            deps.append(('certificate_profile', self.certificate_profile))
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate gateway"""
        errors = []

        # Must have folder (infrastructure requirement)
        if not self.folder:
            errors.append("Gateway must have folder set")

        return errors


class AutoTagAction(ConfigItem):
    """
    Represents an auto-tag action.

    API Endpoint: /sse/config/v1/auto-tag-actions

    Auto-tag actions automatically apply tags to traffic based on
    specified criteria. This is a global infrastructure setting
    that doesn't require folder or snippet parameters.
    """

    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/auto-tag-actions"
    item_type = "auto_tag_action"

    def __init__(self, raw_config: Dict[str, Any]):
        """
        Initialize auto-tag action.

        Auto-tag actions are global infrastructure settings and may not
        have folder/snippet - we need to handle this specially.
        """
        self.raw_config = raw_config.copy()
        self.name = raw_config.get('name', '')
        self.id = raw_config.get('id')

        # Auto-tag actions may not have folder/snippet - set defaults
        self.folder = raw_config.get('folder', 'Shared')
        self.snippet = raw_config.get('snippet')

        self.is_default = raw_config.get('is_default', False)
        self.push_strategy = 'create'
        self.metadata = raw_config.get('metadata', {})
        if not self.metadata:
            self.metadata = self._extract_metadata(raw_config)

        self.deleted = False
        self.delete_success: Optional[bool] = None
        self._dependencies_cache: Optional[List[tuple]] = None
        self._parent_cache = None
        self._children_cache = None

    @property
    def actions(self) -> List[Dict[str, Any]]:
        """Get list of tag actions"""
        return self.raw_config.get('actions', [])

    @property
    def filter(self) -> Optional[str]:
        """Get filter expression"""
        return self.raw_config.get('filter')

    @property
    def log_type(self) -> Optional[str]:
        """Get log type for auto-tagging"""
        return self.raw_config.get('log_type')

    @property
    def quarantine(self) -> bool:
        """Check if quarantine is enabled"""
        return self.raw_config.get('quarantine', False)

    def _validate_specific(self) -> List[str]:
        """Validate auto-tag action"""
        errors = []
        return errors
