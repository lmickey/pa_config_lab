"""
Policy and rule model classes.

This module contains ConfigItem subclasses for all policy/rule types including:
- Security rules (firewall policies)
- NAT rules (source/destination NAT)
- Decryption rules (SSL/TLS decryption policies)
- Authentication rules
- QoS policy rules
- Policy-Based Forwarding (PBF) rules
"""

from typing import List, Dict, Any, Optional
import logging
from config.models.base import RuleItem

logger = logging.getLogger(__name__)


class SecurityRule(RuleItem):
    """
    Represents a security policy rule.
    
    API Endpoint: /sse/config/v1/security-rules
    
    Security rules control traffic flow based on source, destination,
    service, application, and other criteria.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/security-rules"
    item_type = "security_rule"
    
    @property
    def from_zones(self) -> List[str]:
        """Get list of source zones"""
        return self.raw_config.get('from', [])
    
    @property
    def to_zones(self) -> List[str]:
        """Get list of destination zones"""
        return self.raw_config.get('to', [])
    
    @property
    def source(self) -> List[str]:
        """Get list of source addresses/objects"""
        return self.raw_config.get('source', [])
    
    @property
    def destination(self) -> List[str]:
        """Get list of destination addresses/objects"""
        return self.raw_config.get('destination', [])
    
    @property
    def service(self) -> List[str]:
        """Get list of services"""
        return self.raw_config.get('service', [])
    
    @property
    def application(self) -> List[str]:
        """Get list of applications"""
        return self.raw_config.get('application', [])
    
    @property
    def action(self) -> Optional[str]:
        """Get rule action (allow, deny, drop, reset-client, reset-server, reset-both)"""
        return self.raw_config.get('action')
    
    @property
    def profile_setting(self) -> Optional[Dict[str, Any]]:
        """Get security profile settings"""
        return self.raw_config.get('profile_setting')
    
    @property
    def log_setting(self) -> Optional[str]:
        """Get log forwarding profile"""
        return self.raw_config.get('log_setting')
    
    def _compute_dependencies(self) -> List[tuple]:
        """Security rules depend on addresses, services, applications, and profiles"""
        deps = []
        
        # Source and destination addresses (skip 'any')
        for addr in self.source:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        for addr in self.destination:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        # Services (skip 'any' and 'application-default')
        for svc in self.service:
            if svc not in ['any', 'application-default']:
                deps.append(('service_object', svc))
        
        # Applications (skip 'any')
        for app in self.application:
            if app not in ['any']:
                deps.append(('application_object', app))
        
        # Profile groups
        if self.profile_setting:
            if isinstance(self.profile_setting, dict):
                groups = self.profile_setting.get('group', [])
                if isinstance(groups, list):
                    for group in groups:
                        deps.append(('profile_group', group))
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate security rule"""
        errors = []
        
        # Must have action
        if not self.action:
            errors.append("Security rule must have an action")
        
        # Action must be valid
        valid_actions = ['allow', 'deny', 'drop', 'reset-client', 'reset-server', 'reset-both']
        if self.action and self.action not in valid_actions:
            errors.append(f"Invalid action: {self.action}")
        
        # Must have at least basic criteria
        if not self.from_zones or not self.to_zones:
            errors.append("Security rule must have from and to zones")
        
        return errors


class NATRule(RuleItem):
    """
    Represents a NAT policy rule.
    
    API Endpoint: /sse/config/v1/nat-rules
    
    NAT rules define source and destination NAT translations.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/nat-rules"
    item_type = "nat_rule"
    
    @property
    def source(self) -> List[str]:
        """Get list of source addresses"""
        return self.raw_config.get('source', [])
    
    @property
    def destination(self) -> List[str]:
        """Get list of destination addresses"""
        return self.raw_config.get('destination', [])
    
    @property
    def service(self) -> Optional[str]:
        """Get service"""
        return self.raw_config.get('service')
    
    @property
    def source_translation(self) -> Optional[Dict[str, Any]]:
        """Get source NAT configuration"""
        return self.raw_config.get('source_translation')
    
    @property
    def destination_translation(self) -> Optional[Dict[str, Any]]:
        """Get destination NAT configuration"""
        return self.raw_config.get('destination_translation')
    
    def _compute_dependencies(self) -> List[tuple]:
        """NAT rules depend on addresses and services"""
        deps = []
        
        # Source and destination addresses (skip 'any')
        for addr in self.source:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        for addr in self.destination:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        # Service (skip 'any')
        if self.service and self.service not in ['any']:
            deps.append(('service_object', self.service))
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate NAT rule"""
        errors = []
        
        # Must have at least source or destination translation
        if not self.source_translation and not self.destination_translation:
            errors.append("NAT rule must have source or destination translation")
        
        return errors


class DecryptionRule(RuleItem):
    """
    Represents a decryption policy rule.
    
    API Endpoint: /sse/config/v1/decryption-rules
    
    Decryption rules determine which traffic to decrypt.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/decryption-rules"
    item_type = "decryption_rule"
    
    @property
    def from_zones(self) -> List[str]:
        """Get list of source zones"""
        return self.raw_config.get('from', [])
    
    @property
    def to_zones(self) -> List[str]:
        """Get list of destination zones"""
        return self.raw_config.get('to', [])
    
    @property
    def source(self) -> List[str]:
        """Get list of source addresses"""
        return self.raw_config.get('source', [])
    
    @property
    def destination(self) -> List[str]:
        """Get list of destination addresses"""
        return self.raw_config.get('destination', [])
    
    @property
    def action(self) -> Optional[str]:
        """Get decryption action (decrypt, no-decrypt)"""
        return self.raw_config.get('action')
    
    @property
    def decryption_profile(self) -> Optional[str]:
        """Get decryption profile reference"""
        profile = self.raw_config.get('profile')
        if isinstance(profile, str):
            return profile
        return None
    
    def _compute_dependencies(self) -> List[tuple]:
        """Decryption rules depend on addresses and decryption profiles"""
        deps = []
        
        # Source and destination addresses (skip 'any')
        for addr in self.source:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        for addr in self.destination:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        # Decryption profile
        if self.decryption_profile:
            deps.append(('decryption_profile', self.decryption_profile))
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate decryption rule"""
        errors = []
        
        # Must have action
        if not self.action:
            errors.append("Decryption rule must have an action")
        
        # Action must be valid
        valid_actions = ['decrypt', 'no-decrypt']
        if self.action and self.action not in valid_actions:
            errors.append(f"Invalid decryption action: {self.action}")
        
        return errors


class AuthenticationRule(RuleItem):
    """
    Represents an authentication policy rule.
    
    API Endpoint: /sse/config/v1/authentication-rules
    
    Authentication rules enforce authentication requirements.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/authentication-rules"
    item_type = "authentication_rule"
    
    @property
    def from_zones(self) -> List[str]:
        """Get list of source zones"""
        return self.raw_config.get('from', [])
    
    @property
    def to_zones(self) -> List[str]:
        """Get list of destination zones"""
        return self.raw_config.get('to', [])
    
    @property
    def source(self) -> List[str]:
        """Get list of source addresses"""
        return self.raw_config.get('source', [])
    
    @property
    def destination(self) -> List[str]:
        """Get list of destination addresses"""
        return self.raw_config.get('destination', [])
    
    @property
    def authentication_profile(self) -> Optional[str]:
        """Get authentication profile reference"""
        return self.raw_config.get('authentication_enforcement')
    
    def _compute_dependencies(self) -> List[tuple]:
        """Authentication rules depend on addresses and auth profiles"""
        deps = []
        
        # Source and destination addresses (skip 'any')
        for addr in self.source:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        for addr in self.destination:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        # Authentication profile
        if self.authentication_profile:
            deps.append(('authentication_profile', self.authentication_profile))
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate authentication rule"""
        errors = []
        
        # Should have authentication enforcement
        if not self.authentication_profile:
            errors.append("Authentication rule should have authentication enforcement")
        
        return errors


class QoSPolicyRule(RuleItem):
    """
    Represents a Quality of Service policy rule.
    
    API Endpoint: /sse/config/v1/qos-policy-rules
    
    QoS rules apply QoS profiles to traffic.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/qos-policy-rules"
    item_type = "qos_policy_rule"
    
    @property
    def from_zones(self) -> List[str]:
        """Get list of source zones"""
        return self.raw_config.get('from', [])
    
    @property
    def to_zones(self) -> List[str]:
        """Get list of destination zones"""
        return self.raw_config.get('to', [])
    
    @property
    def source(self) -> List[str]:
        """Get list of source addresses"""
        return self.raw_config.get('source', [])
    
    @property
    def destination(self) -> List[str]:
        """Get list of destination addresses"""
        return self.raw_config.get('destination', [])
    
    @property
    def application(self) -> List[str]:
        """Get list of applications"""
        return self.raw_config.get('application', [])
    
    @property
    def qos_profile(self) -> Optional[str]:
        """Get QoS profile reference"""
        action = self.raw_config.get('action')
        if isinstance(action, dict):
            return action.get('class')
        return None
    
    def _compute_dependencies(self) -> List[tuple]:
        """QoS rules depend on addresses, applications, and QoS profiles"""
        deps = []
        
        # Source and destination addresses (skip 'any')
        for addr in self.source:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        for addr in self.destination:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        # Applications (skip 'any')
        for app in self.application:
            if app not in ['any']:
                deps.append(('application_object', app))
        
        # QoS profile
        if self.qos_profile:
            deps.append(('qos_profile', self.qos_profile))
        
        return deps


class PBFRule(RuleItem):
    """
    Represents a Policy-Based Forwarding rule.
    
    API Endpoint: /sse/config/v1/pbf-rules
    
    PBF rules forward traffic based on policy instead of routing table.
    Note: PBF rules have implicit dependencies on Service Connections.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/pbf-rules"
    item_type = "pbf_rule"
    
    @property
    def from_zones(self) -> List[str]:
        """Get list of source zones"""
        return self.raw_config.get('from', [])
    
    @property
    def source(self) -> List[str]:
        """Get list of source addresses"""
        return self.raw_config.get('source', [])
    
    @property
    def destination(self) -> List[str]:
        """Get list of destination addresses"""
        return self.raw_config.get('destination', [])
    
    @property
    def application(self) -> List[str]:
        """Get list of applications"""
        return self.raw_config.get('application', [])
    
    @property
    def service(self) -> List[str]:
        """Get list of services"""
        return self.raw_config.get('service', [])
    
    @property
    def action(self) -> Optional[Dict[str, Any]]:
        """Get PBF action (forward, no-pbf, discard)"""
        return self.raw_config.get('action')
    
    def _compute_dependencies(self) -> List[tuple]:
        """PBF rules depend on addresses, services, and applications"""
        deps = []
        
        # Source and destination addresses (skip 'any')
        for addr in self.source:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        for addr in self.destination:
            if addr not in ['any']:
                deps.append(('address_object', addr))
        
        # Services (skip 'any')
        for svc in self.service:
            if svc not in ['any']:
                deps.append(('service_object', svc))
        
        # Applications (skip 'any')
        for app in self.application:
            if app not in ['any']:
                deps.append(('application_object', app))
        
        # Note: PBF rules have implicit dependencies on Service Connections
        # but these are infrastructure-level dependencies tracked separately
        
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate PBF rule"""
        errors = []
        
        # Must have action
        if not self.action:
            errors.append("PBF rule must have an action")
        
        return errors
