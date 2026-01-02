"""
Tests for config.models.infrastructure module.

Tests all infrastructure model classes for Remote Networks and Mobile Users.
"""

import pytest
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
from tests.examples.loader import Examples


class TestIKECryptoProfile:
    """Tests for IKECryptoProfile class"""
    
    def test_create_ike_crypto_profile(self):
        """Test creating IKE crypto profile"""
        config = Examples.ike_crypto_minimal()
        profile = IKECryptoProfile(config)
        
        assert profile.name == 'default-ikev2'
        assert profile.folder == 'Remote Networks'
        assert len(profile.encryption) == 2
        assert 'aes-256-cbc' in profile.encryption
        assert len(profile.authentication) == 2
        assert len(profile.dh_group) == 2
        assert profile.lifetime is not None
    
    def test_ike_crypto_profile_strong(self):
        """Test strong crypto profile"""
        config = Examples.ike_crypto_strong()
        profile = IKECryptoProfile(config)
        
        assert profile.name == 'strong-ike-crypto'
        assert 'aes-256-gcm' in profile.encryption
        assert 'sha512' in profile.authentication
        assert 'group20' in profile.dh_group
    
    def test_ike_crypto_profile_requires_folder(self):
        """Test that IKE crypto profile requires folder"""
        config_invalid = {
            'name': 'test-ike',
            'snippet': 'test-snippet',
            'encryption': ['aes-256-cbc'],
            'authentication': ['sha256'],
            'dh_group': ['group14']
        }
        
        with pytest.raises(ValueError, match="Infrastructure items must have folder"):
            IKECryptoProfile(config_invalid)
    
    def test_ike_crypto_profile_validation(self):
        """Test IKE crypto profile validation"""
        # Valid profile
        config = Examples.ike_crypto_minimal()
        profile = IKECryptoProfile(config)
        errors = profile.validate()
        assert len(errors) == 0
        
        # Invalid profile (missing encryption)
        config_invalid = {
            'name': 'invalid-ike',
            'folder': 'Remote Networks',
            'authentication': ['sha256'],
            'dh_group': ['group14']
        }
        profile_invalid = IKECryptoProfile(config_invalid)
        errors = profile_invalid.validate()
        assert len(errors) > 0
        assert any('encryption' in error.lower() for error in errors)


class TestIPsecCryptoProfile:
    """Tests for IPsecCryptoProfile class"""
    
    def test_create_ipsec_crypto_profile(self):
        """Test creating IPsec crypto profile"""
        config = Examples.ipsec_crypto_minimal()
        profile = IPsecCryptoProfile(config)
        
        assert profile.name == 'default-ipsec'
        assert profile.folder == 'Remote Networks'
        assert len(profile.esp_encryption) == 2
        assert 'aes-256-cbc' in profile.esp_encryption
        assert len(profile.esp_authentication) == 2
        assert profile.dh_group is None
    
    def test_ipsec_crypto_profile_with_pfs(self):
        """Test IPsec crypto profile with Perfect Forward Secrecy"""
        config = Examples.ipsec_crypto_pfs()
        profile = IPsecCryptoProfile(config)
        
        assert profile.name == 'ipsec-with-pfs'
        assert profile.dh_group == 'group14'
        assert 'aes-256-gcm' in profile.esp_encryption
    
    def test_ipsec_crypto_profile_requires_folder(self):
        """Test that IPsec crypto profile requires folder"""
        config_invalid = {
            'name': 'test-ipsec',
            'snippet': 'test-snippet',
            'esp': {
                'encryption': ['aes-256-cbc'],
                'authentication': ['sha256']
            }
        }
        
        with pytest.raises(ValueError, match="Infrastructure items must have folder"):
            IPsecCryptoProfile(config_invalid)
    
    def test_ipsec_crypto_profile_validation(self):
        """Test IPsec crypto profile validation"""
        # Valid profile
        config = Examples.ipsec_crypto_minimal()
        profile = IPsecCryptoProfile(config)
        errors = profile.validate()
        assert len(errors) == 0
        
        # Invalid profile (missing ESP encryption)
        config_invalid = {
            'name': 'invalid-ipsec',
            'folder': 'Remote Networks',
            'esp': {
                'authentication': ['sha256']
            }
        }
        profile_invalid = IPsecCryptoProfile(config_invalid)
        errors = profile_invalid.validate()
        assert len(errors) > 0
        assert any('encryption' in error.lower() for error in errors)


class TestIKEGateway:
    """Tests for IKEGateway class"""
    
    def test_create_ike_gateway_minimal(self):
        """Test creating minimal IKE gateway"""
        config = Examples.ike_gateway_minimal()
        gateway = IKEGateway(config)
        
        assert gateway.name == 'branch-office-ike'
        assert gateway.folder == 'Remote Networks'
        assert gateway.peer_address is not None
        assert gateway.peer_address['ip'] == '203.0.113.10'
        assert gateway.authentication is not None
        assert gateway.ike_crypto_profile_name == 'default-ikev2'
        assert gateway.has_dependencies
    
    def test_create_ike_gateway_certificate(self):
        """Test creating IKE gateway with certificate auth"""
        config = Examples.ike_gateway_certificate()
        gateway = IKEGateway(config)
        
        assert gateway.name == 'hq-ike-gateway'
        assert gateway.peer_address['fqdn'] == 'vpn.headquarters.example.com'
        assert 'certificate' in gateway.authentication
        assert gateway.ike_crypto_profile_name == 'strong-ike-crypto'
    
    def test_ike_gateway_dependencies(self):
        """Test IKE gateway dependency detection"""
        config = Examples.ike_gateway_minimal()
        gateway = IKEGateway(config)
        
        deps = gateway.get_dependencies()
        
        # Should detect IKE crypto profile dependency
        assert len(deps) == 1
        assert deps[0] == ('ike_crypto_profile', 'default-ikev2')
    
    def test_ike_gateway_requires_folder(self):
        """Test that IKE gateway requires folder"""
        config_invalid = {
            'name': 'test-gateway',
            'snippet': 'test-snippet',
            'peer_address': {'ip': '1.2.3.4'},
            'authentication': {'pre_shared_key': {'key': 'test'}},
            'protocol': {'ikev2': {}}
        }
        
        with pytest.raises(ValueError, match="Infrastructure items must have folder"):
            IKEGateway(config_invalid)
    
    def test_ike_gateway_validation(self):
        """Test IKE gateway validation"""
        # Valid gateway
        config = Examples.ike_gateway_minimal()
        gateway = IKEGateway(config)
        errors = gateway.validate()
        assert len(errors) == 0
        
        # Invalid gateway (missing peer address)
        config_invalid = {
            'name': 'invalid-gateway',
            'folder': 'Remote Networks',
            'authentication': {'pre_shared_key': {'key': 'test'}},
            'protocol': {'ikev2': {}}
        }
        gateway_invalid = IKEGateway(config_invalid)
        errors = gateway_invalid.validate()
        assert len(errors) > 0
        assert any('peer address' in error.lower() for error in errors)


class TestIPsecTunnel:
    """Tests for IPsecTunnel class"""
    
    def test_create_ipsec_tunnel_minimal(self):
        """Test creating minimal IPsec tunnel"""
        config = Examples.ipsec_tunnel_minimal()
        tunnel = IPsecTunnel(config)
        
        assert tunnel.name == 'branch-tunnel'
        assert tunnel.folder == 'Remote Networks'
        assert tunnel.ike_gateway_name == 'branch-office-ike'
        assert tunnel.ipsec_crypto_profile_name == 'default-ipsec'
        assert tunnel.anti_replay is True
        assert tunnel.has_dependencies
    
    def test_create_ipsec_tunnel_full(self):
        """Test creating full IPsec tunnel with proxy IDs"""
        config = Examples.ipsec_tunnel_full()
        tunnel = IPsecTunnel(config)
        
        assert tunnel.name == 'hq-tunnel'
        assert tunnel.ike_gateway_name == 'hq-ike-gateway'
        assert tunnel.ipsec_crypto_profile_name == 'ipsec-with-pfs'
        assert tunnel.tunnel_monitor is not None
    
    def test_ipsec_tunnel_dependencies(self):
        """Test IPsec tunnel dependency detection"""
        config = Examples.ipsec_tunnel_minimal()
        tunnel = IPsecTunnel(config)
        
        deps = tunnel.get_dependencies()
        
        # Should detect both IKE gateway and IPsec crypto profile
        assert len(deps) == 2
        dep_types = [d[0] for d in deps]
        assert 'ike_gateway' in dep_types
        assert 'ipsec_crypto_profile' in dep_types
    
    def test_ipsec_tunnel_requires_folder(self):
        """Test that IPsec tunnel requires folder"""
        config_invalid = {
            'name': 'test-tunnel',
            'snippet': 'test-snippet',
            'auto_key': {
                'ike_gateway': 'test-gw',
                'ipsec_crypto_profile': 'test-crypto'
            }
        }
        
        with pytest.raises(ValueError, match="Infrastructure items must have folder"):
            IPsecTunnel(config_invalid)
    
    def test_ipsec_tunnel_validation(self):
        """Test IPsec tunnel validation"""
        # Valid tunnel
        config = Examples.ipsec_tunnel_minimal()
        tunnel = IPsecTunnel(config)
        errors = tunnel.validate()
        assert len(errors) == 0
        
        # Invalid tunnel (missing IKE gateway)
        config_invalid = {
            'name': 'invalid-tunnel',
            'folder': 'Remote Networks',
            'auto_key': {
                'ipsec_crypto_profile': 'test-crypto'
            }
        }
        tunnel_invalid = IPsecTunnel(config_invalid)
        errors = tunnel_invalid.validate()
        assert len(errors) > 0
        assert any('ike gateway' in error.lower() for error in errors)


class TestServiceConnection:
    """Tests for ServiceConnection class"""
    
    def test_create_service_connection_minimal(self):
        """Test creating minimal service connection"""
        config = Examples.service_connection_minimal()
        sc = ServiceConnection(config)
        
        assert sc.name == 'branch-connection'
        assert sc.folder == 'Remote Networks'
        assert sc.ipsec_tunnel_name == 'branch-tunnel'
        assert len(sc.subnets) == 2
        assert '10.20.0.0/16' in sc.subnets
        assert sc.has_dependencies
    
    def test_create_service_connection_with_bgp(self):
        """Test creating service connection with BGP"""
        config = Examples.service_connection_bgp()
        sc = ServiceConnection(config)
        
        assert sc.name == 'hq-bgp-connection'
        assert sc.bgp_peer is not None
        assert sc.bgp_peer['peer_as'] == '65001'
        assert sc.qos is not None
    
    def test_create_service_connection_with_nat(self):
        """Test creating service connection with NAT properties"""
        config = Examples.service_connection_nat()
        sc = ServiceConnection(config)
        
        assert sc.name == 'branch-with-nat'
        assert sc.nat_pool == '10.100.1.0/24'
        assert sc.source_nat is not None
        assert sc.source_nat['enable'] is True
        assert sc.backup_sc == 'branch-backup-connection'
    
    def test_service_connection_dependencies(self):
        """Test service connection dependency chain"""
        config = Examples.service_connection_minimal()
        sc = ServiceConnection(config)
        
        deps = sc.get_dependencies()
        
        # Should detect IPsec tunnel dependency
        assert len(deps) == 1
        assert deps[0] == ('ipsec_tunnel', 'branch-tunnel')
    
    def test_service_connection_with_backup_dependency(self):
        """Test service connection with backup SC dependency"""
        config = Examples.service_connection_nat()
        sc = ServiceConnection(config)
        
        deps = sc.get_dependencies()
        
        # Should detect both IPsec tunnel and backup SC
        assert len(deps) == 2
        dep_types = [d[0] for d in deps]
        assert 'ipsec_tunnel' in dep_types
        assert 'service_connection' in dep_types
    
    def test_service_connection_requires_folder(self):
        """Test that service connection requires folder"""
        config_invalid = {
            'name': 'test-sc',
            'snippet': 'test-snippet',
            'ipsec_tunnel': 'test-tunnel',
            'subnets': ['10.0.0.0/8']
        }
        
        with pytest.raises(ValueError, match="Infrastructure items must have folder"):
            ServiceConnection(config_invalid)
    
    def test_service_connection_validation(self):
        """Test service connection validation"""
        # Valid SC
        config = Examples.service_connection_minimal()
        sc = ServiceConnection(config)
        errors = sc.validate()
        assert len(errors) == 0
        
        # Invalid SC (missing IPsec tunnel)
        config_invalid = {
            'name': 'invalid-sc',
            'folder': 'Remote Networks',
            'subnets': ['10.0.0.0/8']
        }
        sc_invalid = ServiceConnection(config_invalid)
        errors = sc_invalid.validate()
        assert len(errors) > 0
        assert any('ipsec tunnel' in error.lower() for error in errors)


class TestAgentProfile:
    """Tests for AgentProfile class"""
    
    def test_create_agent_profile_minimal(self):
        """Test creating minimal agent profile"""
        config = Examples.agent_profile_minimal()
        profile = AgentProfile(config)
        
        assert profile.name == 'default-agent'
        assert profile.folder == 'Mobile Users'
        assert profile.connect_method == 'on-demand'
        assert profile.authentication is not None
    
    def test_create_agent_profile_always_on(self):
        """Test creating always-on agent profile"""
        config = Examples.agent_profile_always_on()
        profile = AgentProfile(config)
        
        assert profile.name == 'always-on-agent'
        assert profile.connect_method == 'user-logon'
        assert profile.split_tunneling is not None
        assert profile.split_tunneling['enable'] is True
    
    def test_agent_profile_requires_folder(self):
        """Test that agent profile requires folder"""
        config_invalid = {
            'name': 'test-agent',
            'snippet': 'test-snippet',
            'connect_method': 'on-demand'
        }
        
        with pytest.raises(ValueError, match="Infrastructure items must have folder"):
            AgentProfile(config_invalid)
    
    def test_agent_profile_validation(self):
        """Test agent profile validation"""
        # Valid profile
        config = Examples.agent_profile_minimal()
        profile = AgentProfile(config)
        errors = profile.validate()
        assert len(errors) == 0


class TestPortal:
    """Tests for Portal class"""
    
    def test_create_portal(self):
        """Test creating portal"""
        config = Examples.portal_minimal()
        portal = Portal(config)
        
        assert portal.name == 'gp-portal'
        assert portal.folder == 'Mobile Users'
        assert portal.authentication is not None
        assert 'saml' in portal.authentication
    
    def test_portal_requires_folder(self):
        """Test that portal requires folder"""
        config_invalid = {
            'name': 'test-portal',
            'snippet': 'test-snippet',
            'authentication': {'saml': {}}
        }
        
        with pytest.raises(ValueError, match="Infrastructure items must have folder"):
            Portal(config_invalid)
    
    def test_portal_with_certificate_profile(self):
        """Test portal with certificate profile dependency"""
        config = Examples.portal_minimal()
        config['certificate_profile'] = 'ssl-cert-profile'
        portal = Portal(config)
        
        assert portal.certificate_profile == 'ssl-cert-profile'
        assert portal.has_dependencies
        
        deps = portal.get_dependencies()
        assert len(deps) == 1
        assert deps[0] == ('certificate_profile', 'ssl-cert-profile')


class TestGateway:
    """Tests for Gateway class"""
    
    def test_create_gateway(self):
        """Test creating gateway"""
        config = Examples.gateway_minimal()
        gateway = Gateway(config)
        
        assert gateway.name == 'gp-gateway'
        assert gateway.folder == 'Mobile Users'
        assert gateway.authentication is not None
        assert gateway.tunnel_settings is not None
    
    def test_gateway_requires_folder(self):
        """Test that gateway requires folder"""
        config_invalid = {
            'name': 'test-gateway',
            'snippet': 'test-snippet',
            'authentication': {'saml': {}}
        }
        
        with pytest.raises(ValueError, match="Infrastructure items must have folder"):
            Gateway(config_invalid)
    
    def test_gateway_with_certificate_profile(self):
        """Test gateway with certificate profile dependency"""
        config = Examples.gateway_minimal()
        config['certificate_profile'] = 'ssl-cert-profile'
        gateway = Gateway(config)
        
        assert gateway.certificate_profile == 'ssl-cert-profile'
        assert gateway.has_dependencies
        
        deps = gateway.get_dependencies()
        assert len(deps) == 1
        assert deps[0] == ('certificate_profile', 'ssl-cert-profile')


class TestInfrastructureDependencyChains:
    """Test deep dependency chains in infrastructure"""
    
    def test_full_dependency_chain(self):
        """Test the full Service Connection → IPsec Tunnel → IKE Gateway → Crypto chain"""
        # Create the full chain
        ike_crypto = IKECryptoProfile(Examples.ike_crypto_minimal())
        ike_gateway = IKEGateway(Examples.ike_gateway_minimal())
        ipsec_crypto = IPsecCryptoProfile(Examples.ipsec_crypto_minimal())
        ipsec_tunnel = IPsecTunnel(Examples.ipsec_tunnel_minimal())
        service_connection = ServiceConnection(Examples.service_connection_minimal())
        
        # Verify each level of dependencies
        assert ike_crypto.has_dependencies is False
        assert ipsec_crypto.has_dependencies is False
        
        assert ike_gateway.has_dependencies is True
        ike_gw_deps = ike_gateway.get_dependencies()
        assert ('ike_crypto_profile', 'default-ikev2') in ike_gw_deps
        
        assert ipsec_tunnel.has_dependencies is True
        tunnel_deps = ipsec_tunnel.get_dependencies()
        assert ('ike_gateway', 'branch-office-ike') in tunnel_deps
        assert ('ipsec_crypto_profile', 'default-ipsec') in tunnel_deps
        
        assert service_connection.has_dependencies is True
        sc_deps = service_connection.get_dependencies()
        assert ('ipsec_tunnel', 'branch-tunnel') in sc_deps


class TestInfrastructureSerialization:
    """Test serialization/deserialization of infrastructure models"""
    
    def test_service_connection_serialization(self):
        """Test service connection serialization"""
        config = Examples.service_connection_bgp()
        sc = ServiceConnection(config)
        
        # Serialize
        data = sc.to_dict()
        
        assert 'name' in data
        assert 'folder' in data
        assert 'ipsec_tunnel' in data
        assert 'bgp_peer' in data
        assert 'id' not in data
        
        # Deserialize
        sc2 = ServiceConnection.from_dict(data)
        
        assert sc2.name == sc.name
        assert sc2.ipsec_tunnel_name == sc.ipsec_tunnel_name


class TestInfrastructureDeletion:
    """Test deletion tracking for infrastructure models"""
    
    def test_mark_ipsec_tunnel_for_deletion(self):
        """Test marking IPsec tunnel for deletion"""
        config = Examples.ipsec_tunnel_minimal()
        tunnel = IPsecTunnel(config)
        
        assert not tunnel.deleted
        assert tunnel.delete_success is None
        
        tunnel.mark_for_deletion()
        
        assert tunnel.deleted
        assert tunnel.delete_success is None
    
    def test_unmark_service_connection_for_deletion(self):
        """Test unmarking service connection for deletion"""
        config = Examples.service_connection_minimal()
        sc = ServiceConnection(config)
        
        sc.mark_for_deletion()
        sc.delete_success = False
        
        sc.unmark_for_deletion()
        
        assert not sc.deleted
        assert sc.delete_success is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
