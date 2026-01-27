"""
Firewall API Client for PAN-OS firewalls.

Wraps the pan-os-python library to provide a clean interface for:
- Connection and authentication
- Configuration operations (get, set, delete)
- Commit operations
- System operations (licensing, software)
"""

import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    from panos.firewall import Firewall
    from panos.panorama import Panorama
    from panos.errors import PanDeviceError, PanConnectionTimeout, PanURLError
    from panos.device import SystemSettings
    from panos.network import (
        EthernetInterface,
        Zone,
        VirtualRouter,
        StaticRoute,
        IkeGateway,
        IpsecTunnel,
        IpsecCryptoProfile,
        IkeCryptoProfile,
        TunnelInterface,
    )
    from panos.policies import Rulebase, SecurityRule, NatRule
    from panos.objects import AddressObject, AddressGroup, ServiceObject, Tag
    PANOS_AVAILABLE = True
except ImportError:
    PANOS_AVAILABLE = False

logger = logging.getLogger(__name__)


class FirewallConnectionError(Exception):
    """Error connecting to firewall."""
    pass


class FirewallAPIError(Exception):
    """Error during firewall API operation."""
    pass


class CommitStatus(str, Enum):
    """Commit operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class CommitResult:
    """Result of a commit operation."""
    status: CommitStatus
    job_id: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == CommitStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'job_id': self.job_id,
            'message': self.message,
            'details': self.details,
        }


@dataclass
class DeviceInfo:
    """Firewall device information."""
    hostname: str
    serial: str
    model: str
    sw_version: str
    app_version: str
    threat_version: str
    wildfire_version: str
    uptime: str
    is_licensed: bool = False
    management_ip: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'hostname': self.hostname,
            'serial': self.serial,
            'model': self.model,
            'sw_version': self.sw_version,
            'app_version': self.app_version,
            'threat_version': self.threat_version,
            'wildfire_version': self.wildfire_version,
            'uptime': self.uptime,
            'is_licensed': self.is_licensed,
            'management_ip': self.management_ip,
        }


class FirewallAPIClient:
    """
    PAN-OS Firewall API client.

    Provides methods for connecting to and managing VM-Series firewalls
    using the PAN-OS XML API via pan-os-python.
    """

    def __init__(
        self,
        hostname: str,
        username: str = "admin",
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        port: int = 443,
        timeout: int = 120,
    ):
        """
        Initialize firewall API client.

        Args:
            hostname: Firewall management IP or hostname
            username: Admin username
            password: Admin password (or use api_key)
            api_key: API key (alternative to password)
            port: HTTPS port (default 443)
            timeout: Connection timeout in seconds
        """
        if not PANOS_AVAILABLE:
            raise ImportError(
                "pan-os-python is required. Install with: pip install pan-os-python"
            )

        self.hostname = hostname
        self.username = username
        self.password = password
        self.api_key = api_key
        self.port = port
        self.timeout = timeout

        self._firewall: Optional[Firewall] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to firewall."""
        return self._connected and self._firewall is not None

    def connect(self, verify_ssl: bool = False) -> bool:
        """
        Connect to the firewall.

        Args:
            verify_ssl: Verify SSL certificate (default False for self-signed)

        Returns:
            True if connection successful

        Raises:
            FirewallConnectionError: If connection fails
        """
        logger.info(f"Connecting to firewall at {self.hostname}")

        try:
            self._firewall = Firewall(
                hostname=self.hostname,
                api_username=self.username,
                api_password=self.password,
                api_key=self.api_key,
                port=self.port,
                timeout=self.timeout,
            )

            # Test connection by refreshing system info
            self._firewall.refresh_system_info()
            self._connected = True

            logger.info(f"Connected to {self._firewall.hostname} ({self._firewall.serial})")
            return True

        except PanConnectionTimeout as e:
            self._connected = False
            raise FirewallConnectionError(f"Connection timeout: {e}")
        except PanURLError as e:
            self._connected = False
            raise FirewallConnectionError(f"Connection error: {e}")
        except PanDeviceError as e:
            self._connected = False
            raise FirewallConnectionError(f"Device error: {e}")
        except Exception as e:
            self._connected = False
            raise FirewallConnectionError(f"Unexpected error: {e}")

    def disconnect(self):
        """Disconnect from the firewall."""
        self._firewall = None
        self._connected = False
        logger.info(f"Disconnected from {self.hostname}")

    def _ensure_connected(self):
        """Ensure we're connected to the firewall."""
        if not self.is_connected:
            raise FirewallConnectionError("Not connected to firewall. Call connect() first.")

    # ========== Device Information ==========

    def get_device_info(self) -> DeviceInfo:
        """
        Get firewall device information.

        Returns:
            DeviceInfo with system details
        """
        self._ensure_connected()

        self._firewall.refresh_system_info()

        return DeviceInfo(
            hostname=getattr(self._firewall, 'hostname', '') or "",
            serial=getattr(self._firewall, 'serial', '') or "",
            model=getattr(self._firewall, 'model', '') or "",
            sw_version=getattr(self._firewall, 'version', '') or "",
            app_version=getattr(self._firewall, 'app_version', '') or "",
            threat_version=getattr(self._firewall, 'threat_version', '') or "",
            wildfire_version=getattr(self._firewall, 'wildfire_version', '') or "",
            uptime=getattr(self._firewall, 'uptime', '') or "",
            management_ip=self.hostname,
        )

    def is_ready(self, timeout: int = 300, interval: int = 10) -> bool:
        """
        Wait for firewall to be ready (autocommit complete).

        Args:
            timeout: Maximum wait time in seconds
            interval: Check interval in seconds

        Returns:
            True if firewall is ready
        """
        logger.info(f"Waiting for firewall to be ready (timeout: {timeout}s)")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if not self.is_connected:
                    self.connect()

                # Check if autocommit is complete by trying to get system info
                self._firewall.refresh_system_info()

                # Check for any pending jobs
                # A newly booted firewall may still be running autocommit
                jobs = self._firewall.op("show jobs all")
                # Parse and check if any jobs are still running
                # For now, assume ready if we can get system info
                logger.info("Firewall is ready")
                return True

            except Exception as e:
                logger.debug(f"Firewall not ready yet: {e}")
                time.sleep(interval)

        logger.warning(f"Firewall not ready after {timeout}s")
        return False

    # ========== Configuration Operations ==========

    def get_running_config(self) -> str:
        """
        Get the running configuration as XML.

        Returns:
            Running config XML string
        """
        self._ensure_connected()

        result = self._firewall.op("show config running")
        return result

    def get_candidate_config(self) -> str:
        """
        Get the candidate configuration as XML.

        Returns:
            Candidate config XML string
        """
        self._ensure_connected()

        result = self._firewall.op("show config candidate")
        return result

    def set_hostname(self, hostname: str):
        """
        Set the firewall hostname.

        Args:
            hostname: New hostname
        """
        self._ensure_connected()

        settings = SystemSettings()
        settings.hostname = hostname
        self._firewall.add(settings)
        settings.apply()

        logger.info(f"Set hostname to {hostname}")

    def set_dns_servers(self, primary: str, secondary: Optional[str] = None):
        """
        Set DNS servers.

        Args:
            primary: Primary DNS server IP
            secondary: Secondary DNS server IP
        """
        self._ensure_connected()

        settings = SystemSettings()
        settings.dns_primary = primary
        if secondary:
            settings.dns_secondary = secondary
        self._firewall.add(settings)
        settings.apply()

        logger.info(f"Set DNS servers: {primary}, {secondary}")

    def set_ntp_servers(self, primary: str, secondary: Optional[str] = None):
        """
        Set NTP servers.

        Args:
            primary: Primary NTP server
            secondary: Secondary NTP server
        """
        self._ensure_connected()

        settings = SystemSettings()
        settings.ntp_primary = primary
        if secondary:
            settings.ntp_secondary = secondary
        self._firewall.add(settings)
        settings.apply()

        logger.info(f"Set NTP servers: {primary}, {secondary}")

    # ========== Network Configuration ==========

    def configure_interface(
        self,
        name: str,
        mode: str = "layer3",
        ip_address: Optional[str] = None,
        zone: Optional[str] = None,
        virtual_router: str = "default",
        dhcp: bool = False,
        comment: str = "",
    ):
        """
        Configure an ethernet interface.

        Args:
            name: Interface name (e.g., "ethernet1/1")
            mode: Interface mode (layer3, layer2, virtual-wire)
            ip_address: IP address in CIDR notation
            zone: Security zone name
            virtual_router: Virtual router name
            dhcp: Use DHCP for IP
            comment: Interface comment
        """
        self._ensure_connected()

        interface = EthernetInterface(
            name=name,
            mode=mode,
            comment=comment,
        )

        if dhcp:
            interface.enable_dhcp = True
        elif ip_address:
            interface.ip = [ip_address]

        self._firewall.add(interface)
        interface.apply()

        # Add to zone if specified
        if zone:
            self._add_interface_to_zone(name, zone)

        # Add to virtual router
        self._add_interface_to_vr(name, virtual_router)

        logger.info(f"Configured interface {name}")

    def _add_interface_to_zone(self, interface: str, zone_name: str):
        """Add interface to a security zone."""
        zone = Zone(name=zone_name)
        zone.interface = [interface]
        self._firewall.add(zone)
        zone.apply()

    def _add_interface_to_vr(self, interface: str, vr_name: str):
        """Add interface to a virtual router."""
        vr = VirtualRouter(name=vr_name)
        vr.interface = [interface]
        self._firewall.add(vr)
        vr.apply()

    def create_zone(self, name: str, interfaces: List[str] = None):
        """
        Create a security zone.

        Args:
            name: Zone name
            interfaces: List of interfaces to add
        """
        self._ensure_connected()

        zone = Zone(name=name)
        if interfaces:
            zone.interface = interfaces
        self._firewall.add(zone)
        zone.apply()

        logger.info(f"Created zone {name}")

    def create_static_route(
        self,
        name: str,
        destination: str,
        nexthop: str,
        interface: Optional[str] = None,
        virtual_router: str = "default",
    ):
        """
        Create a static route.

        Args:
            name: Route name
            destination: Destination network (CIDR)
            nexthop: Next hop IP address
            interface: Egress interface
            virtual_router: Virtual router name
        """
        self._ensure_connected()

        vr = VirtualRouter(name=virtual_router)
        self._firewall.add(vr)

        route = StaticRoute(
            name=name,
            destination=destination,
            nexthop=nexthop,
        )
        if interface:
            route.interface = interface

        vr.add(route)
        route.apply()

        logger.info(f"Created static route {name}: {destination} via {nexthop}")

    # ========== Address Objects ==========

    def create_address_object(
        self,
        name: str,
        value: str,
        address_type: str = "ip-netmask",
        description: str = "",
        tags: List[str] = None,
    ):
        """
        Create an address object.

        Args:
            name: Object name
            value: Address value (IP, CIDR, FQDN depending on type)
            address_type: Type of address (ip-netmask, ip-range, fqdn)
            description: Optional description
            tags: Optional list of tags
        """
        self._ensure_connected()

        addr = AddressObject(name=name, description=description)

        if address_type == "ip-netmask":
            addr.value = value
        elif address_type == "ip-range":
            addr.type = "ip-range"
            addr.value = value
        elif address_type == "fqdn":
            addr.type = "fqdn"
            addr.value = value
        else:
            addr.value = value

        if tags:
            addr.tag = tags

        self._firewall.add(addr)
        addr.apply()

        logger.info(f"Created address object {name}: {value}")

    def create_address_group(
        self,
        name: str,
        static_members: List[str] = None,
        dynamic_filter: str = None,
        description: str = "",
        tags: List[str] = None,
    ):
        """
        Create an address group.

        Args:
            name: Group name
            static_members: List of address object names for static group
            dynamic_filter: Filter string for dynamic group (e.g., "'tag1' and 'tag2'")
            description: Optional description
            tags: Optional list of tags
        """
        self._ensure_connected()

        group = AddressGroup(name=name, description=description)

        if static_members:
            group.static_value = static_members
        elif dynamic_filter:
            group.dynamic_value = dynamic_filter

        if tags:
            group.tag = tags

        self._firewall.add(group)
        group.apply()

        logger.info(f"Created address group {name}")

    def create_service_object(
        self,
        name: str,
        protocol: str,
        destination_port: str,
        source_port: str = None,
        description: str = "",
        tags: List[str] = None,
    ):
        """
        Create a service object.

        Args:
            name: Object name
            protocol: tcp or udp
            destination_port: Destination port or range (e.g., "80", "8080-8090")
            source_port: Optional source port or range
            description: Optional description
            tags: Optional list of tags
        """
        self._ensure_connected()

        svc = ServiceObject(
            name=name,
            protocol=protocol,
            destination_port=destination_port,
            description=description,
        )

        if source_port:
            svc.source_port = source_port

        if tags:
            svc.tag = tags

        self._firewall.add(svc)
        svc.apply()

        logger.info(f"Created service object {name}: {protocol}/{destination_port}")

    # ========== Security Policy ==========

    def create_security_rule(
        self,
        name: str,
        source_zone: List[str],
        destination_zone: List[str],
        source: List[str] = None,
        destination: List[str] = None,
        application: List[str] = None,
        service: List[str] = None,
        action: str = "allow",
        log_start: bool = False,
        log_end: bool = True,
        description: str = "",
    ):
        """
        Create a security rule.

        Args:
            name: Rule name
            source_zone: Source zones
            destination_zone: Destination zones
            source: Source addresses (default: any)
            destination: Destination addresses (default: any)
            application: Applications (default: any)
            service: Services (default: application-default)
            action: allow, deny, drop
            log_start: Log at session start
            log_end: Log at session end
            description: Rule description
        """
        self._ensure_connected()

        rulebase = Rulebase()
        self._firewall.add(rulebase)

        rule = SecurityRule(
            name=name,
            fromzone=source_zone,
            tozone=destination_zone,
            source=source or ["any"],
            destination=destination or ["any"],
            application=application or ["any"],
            service=service or ["application-default"],
            action=action,
            log_start=log_start,
            log_end=log_end,
            description=description,
        )

        rulebase.add(rule)
        rule.apply()

        logger.info(f"Created security rule: {name}")

    def create_nat_rule(
        self,
        name: str,
        source_zone: List[str],
        destination_zone: str,
        source: List[str] = None,
        destination: List[str] = None,
        service: str = "any",
        source_translation_type: str = "dynamic-ip-and-port",
        source_translation_interface: str = None,
        description: str = "",
    ):
        """
        Create a NAT rule.

        Args:
            name: Rule name
            source_zone: Source zones
            destination_zone: Destination zone
            source: Source addresses
            destination: Destination addresses
            service: Service
            source_translation_type: dynamic-ip-and-port, dynamic-ip, static-ip
            source_translation_interface: Interface for dynamic IP/port
            description: Rule description
        """
        self._ensure_connected()

        rulebase = Rulebase()
        self._firewall.add(rulebase)

        rule = NatRule(
            name=name,
            fromzone=source_zone,
            tozone=destination_zone,
            source=source or ["any"],
            destination=destination or ["any"],
            service=service,
            description=description,
        )

        # Set source translation
        if source_translation_type == "dynamic-ip-and-port" and source_translation_interface:
            rule.source_translation_type = "dynamic-ip-and-port"
            rule.source_translation_interface = source_translation_interface

        rulebase.add(rule)
        rule.apply()

        logger.info(f"Created NAT rule: {name}")

    # ========== IPsec/IKE Configuration ==========

    def create_ike_crypto_profile(
        self,
        name: str,
        dh_group: List[str] = None,
        authentication: List[str] = None,
        encryption: List[str] = None,
        lifetime_hours: int = 8,
    ):
        """
        Create an IKE crypto profile.

        Args:
            name: Profile name
            dh_group: DH groups (e.g., ['group14', 'group19'])
            authentication: Auth algorithms (e.g., ['sha256', 'sha384'])
            encryption: Encryption algorithms (e.g., ['aes-256-cbc', 'aes-256-gcm'])
            lifetime_hours: SA lifetime in hours
        """
        self._ensure_connected()

        profile = IkeCryptoProfile(
            name=name,
            dh_group=dh_group or ['group14', 'group19'],
            authentication=authentication or ['sha256', 'sha384'],
            encryption=encryption or ['aes-256-cbc', 'aes-256-gcm'],
            lifetime_hours=lifetime_hours,
        )

        self._firewall.add(profile)
        profile.apply()

        logger.info(f"Created IKE crypto profile: {name}")

    def create_ipsec_crypto_profile(
        self,
        name: str,
        esp_encryption: List[str] = None,
        esp_authentication: List[str] = None,
        dh_group: str = "group14",
        lifetime_hours: int = 1,
    ):
        """
        Create an IPsec crypto profile.

        Args:
            name: Profile name
            esp_encryption: ESP encryption algorithms
            esp_authentication: ESP authentication algorithms
            dh_group: PFS DH group
            lifetime_hours: SA lifetime in hours
        """
        self._ensure_connected()

        profile = IpsecCryptoProfile(
            name=name,
            esp_encryption=esp_encryption or ['aes-256-cbc', 'aes-256-gcm'],
            esp_authentication=esp_authentication or ['sha256', 'sha384'],
            dh_group=dh_group,
            lifetime_hours=lifetime_hours,
        )

        self._firewall.add(profile)
        profile.apply()

        logger.info(f"Created IPsec crypto profile: {name}")

    def create_tunnel_interface(
        self,
        name: str,
        comment: str = "",
        virtual_router: str = "default",
        zone: str = None,
    ):
        """
        Create a tunnel interface.

        Args:
            name: Interface name (e.g., 'tunnel.1')
            comment: Interface comment
            virtual_router: Virtual router to assign
            zone: Security zone to assign
        """
        self._ensure_connected()

        # Extract tunnel number from name
        if name.startswith('tunnel.'):
            tunnel_num = name.split('.')[1]
        else:
            tunnel_num = name

        tunnel = TunnelInterface(
            name=f"tunnel.{tunnel_num}",
            comment=comment,
        )

        self._firewall.add(tunnel)
        tunnel.apply()

        # Add to virtual router if specified
        if virtual_router:
            vr = VirtualRouter(name=virtual_router)
            self._firewall.add(vr)
            vr.refresh()
            # Add tunnel interface to VR
            if tunnel.name not in (vr.interface or []):
                vr.interface = (vr.interface or []) + [tunnel.name]
                vr.apply()

        # Add to zone if specified
        if zone:
            z = Zone(name=zone)
            self._firewall.add(z)
            z.refresh()
            if tunnel.name not in (z.interface or []):
                z.interface = (z.interface or []) + [tunnel.name]
                z.apply()

        logger.info(f"Created tunnel interface: {tunnel.name}")
        return tunnel.name

    def create_ike_gateway(
        self,
        name: str,
        interface: str,
        peer_ip: str,
        pre_shared_key: str,
        local_id_type: str = None,
        local_id_value: str = None,
        peer_id_type: str = None,
        peer_id_value: str = None,
        ike_crypto_profile: str = "default",
        ikev2_only: bool = True,
        enable_nat_traversal: bool = True,
        enable_dead_peer_detection: bool = True,
    ):
        """
        Create an IKE gateway.

        Args:
            name: Gateway name
            interface: Local interface (e.g., 'ethernet1/1')
            peer_ip: Peer IP address or FQDN
            pre_shared_key: Pre-shared key for authentication
            local_id_type: Local ID type (ipaddr, fqdn, ufqdn, keyid)
            local_id_value: Local ID value
            peer_id_type: Peer ID type
            peer_id_value: Peer ID value
            ike_crypto_profile: IKE crypto profile name
            ikev2_only: Use IKEv2 only
            enable_nat_traversal: Enable NAT traversal
            enable_dead_peer_detection: Enable DPD
        """
        self._ensure_connected()

        gateway = IkeGateway(
            name=name,
            interface=interface,
            peer_ip_value=peer_ip,
            pre_shared_key=pre_shared_key,
            ikev2_crypto_profile=ike_crypto_profile if ikev2_only else None,
            ikev1_crypto_profile=None if ikev2_only else ike_crypto_profile,
            enable_passive_mode=False,
            enable_nat_traversal=enable_nat_traversal,
            enable_dead_peer_detection=enable_dead_peer_detection,
        )

        # Set local ID if specified
        if local_id_type and local_id_value:
            gateway.local_id_type = local_id_type
            gateway.local_id_value = local_id_value

        # Set peer ID if specified
        if peer_id_type and peer_id_value:
            gateway.peer_id_type = peer_id_type
            gateway.peer_id_value = peer_id_value

        self._firewall.add(gateway)
        gateway.apply()

        logger.info(f"Created IKE gateway: {name} -> {peer_ip}")

    def create_ipsec_tunnel(
        self,
        name: str,
        tunnel_interface: str,
        ike_gateway: str,
        ipsec_crypto_profile: str = "default",
        enable_tunnel_monitor: bool = False,
        tunnel_monitor_dest_ip: str = None,
    ):
        """
        Create an IPsec tunnel.

        Args:
            name: Tunnel name
            tunnel_interface: Tunnel interface (e.g., 'tunnel.1')
            ike_gateway: IKE gateway name
            ipsec_crypto_profile: IPsec crypto profile name
            enable_tunnel_monitor: Enable tunnel monitoring
            tunnel_monitor_dest_ip: Tunnel monitor destination IP
        """
        self._ensure_connected()

        tunnel = IpsecTunnel(
            name=name,
            tunnel_interface=tunnel_interface,
            ak_ike_gateway=ike_gateway,
            ak_ipsec_crypto_profile=ipsec_crypto_profile,
        )

        if enable_tunnel_monitor and tunnel_monitor_dest_ip:
            tunnel.enable_tunnel_monitor = True
            tunnel.tunnel_monitor_dest_ip = tunnel_monitor_dest_ip

        self._firewall.add(tunnel)
        tunnel.apply()

        logger.info(f"Created IPsec tunnel: {name} via {ike_gateway}")

    def configure_ipsec_to_prisma_access(
        self,
        name: str,
        pa_endpoint_ip: str,
        pre_shared_key: str,
        local_interface: str = "ethernet1/1",
        tunnel_number: int = 1,
        trust_zone: str = "trust",
        local_subnets: List[str] = None,
    ) -> Dict[str, str]:
        """
        Configure complete IPsec tunnel to Prisma Access.

        This is a convenience method that creates all necessary components:
        - IKE crypto profile
        - IPsec crypto profile
        - Tunnel interface
        - IKE gateway
        - IPsec tunnel
        - Static route to Prisma Access

        Args:
            name: Base name for all objects (e.g., 'PA-DC')
            pa_endpoint_ip: Prisma Access service endpoint IP
            pre_shared_key: Pre-shared key
            local_interface: Local interface for IKE (untrust interface)
            tunnel_number: Tunnel interface number
            trust_zone: Trust zone name
            local_subnets: Local subnets to route through tunnel

        Returns:
            Dict with created object names
        """
        self._ensure_connected()

        ike_crypto_name = f"{name}-ike-crypto"
        ipsec_crypto_name = f"{name}-ipsec-crypto"
        tunnel_if_name = f"tunnel.{tunnel_number}"
        ike_gw_name = f"{name}-ike-gw"
        ipsec_tunnel_name = f"{name}-ipsec"

        created = {
            'ike_crypto_profile': ike_crypto_name,
            'ipsec_crypto_profile': ipsec_crypto_name,
            'tunnel_interface': tunnel_if_name,
            'ike_gateway': ike_gw_name,
            'ipsec_tunnel': ipsec_tunnel_name,
        }

        # Step 1: Create IKE crypto profile
        logger.info(f"Creating IKE crypto profile: {ike_crypto_name}")
        self.create_ike_crypto_profile(
            name=ike_crypto_name,
            dh_group=['group19', 'group20'],
            authentication=['sha256', 'sha384'],
            encryption=['aes-256-cbc', 'aes-256-gcm'],
            lifetime_hours=8,
        )

        # Step 2: Create IPsec crypto profile
        logger.info(f"Creating IPsec crypto profile: {ipsec_crypto_name}")
        self.create_ipsec_crypto_profile(
            name=ipsec_crypto_name,
            esp_encryption=['aes-256-cbc', 'aes-256-gcm'],
            esp_authentication=['sha256', 'sha384'],
            dh_group='group19',
            lifetime_hours=1,
        )

        # Step 3: Create tunnel interface
        logger.info(f"Creating tunnel interface: {tunnel_if_name}")
        self.create_tunnel_interface(
            name=tunnel_if_name,
            comment=f"IPsec tunnel to Prisma Access ({name})",
            virtual_router="default",
            zone=trust_zone,  # Tunnel goes in trust zone typically
        )

        # Step 4: Create IKE gateway
        logger.info(f"Creating IKE gateway: {ike_gw_name}")
        self.create_ike_gateway(
            name=ike_gw_name,
            interface=local_interface,
            peer_ip=pa_endpoint_ip,
            pre_shared_key=pre_shared_key,
            ike_crypto_profile=ike_crypto_name,
            ikev2_only=True,
            enable_nat_traversal=True,
            enable_dead_peer_detection=True,
        )

        # Step 5: Create IPsec tunnel
        logger.info(f"Creating IPsec tunnel: {ipsec_tunnel_name}")
        self.create_ipsec_tunnel(
            name=ipsec_tunnel_name,
            tunnel_interface=tunnel_if_name,
            ike_gateway=ike_gw_name,
            ipsec_crypto_profile=ipsec_crypto_name,
        )

        # Step 6: Create static routes to Prisma Access if subnets specified
        if local_subnets:
            # Route to Prisma Access cloud (0.0.0.0/0 or specific ranges)
            # For now, create a default route through the tunnel
            logger.info(f"Creating static route to Prisma Access via {tunnel_if_name}")
            self.create_static_route(
                name=f"{name}-to-pa",
                destination="0.0.0.0/0",
                interface=tunnel_if_name,
                metric=100,  # Higher metric so it doesn't override default
            )

        logger.info(f"IPsec tunnel to Prisma Access configured: {name}")
        return created

    # ========== Commit Operations ==========

    def commit(
        self,
        description: str = "",
        sync: bool = True,
        timeout: int = 300,
        progress_callback: Callable[[int, str], None] = None,
    ) -> CommitResult:
        """
        Commit configuration changes.

        Args:
            description: Commit description
            sync: Wait for commit to complete
            timeout: Commit timeout in seconds
            progress_callback: Optional callback for progress updates (percent, message)

        Returns:
            CommitResult with commit status
        """
        self._ensure_connected()

        logger.info(f"Starting commit{' (sync)' if sync else ''}")

        try:
            if sync:
                # Synchronous commit with wait
                # Note: pan-os-python commit() doesn't accept timeout directly
                # The timeout is set on the device object via self._firewall.timeout
                original_timeout = getattr(self._firewall, 'timeout', None)
                if timeout:
                    self._firewall.timeout = timeout

                try:
                    result = self._firewall.commit(
                        sync=True,
                    )
                finally:
                    # Restore original timeout
                    if original_timeout is not None:
                        self._firewall.timeout = original_timeout

                # The result is typically None on success or raises on error
                return CommitResult(
                    status=CommitStatus.SUCCESS,
                    message="Commit successful",
                )
            else:
                # Async commit - returns job ID
                result = self._firewall.commit(
                    sync=False,
                )

                return CommitResult(
                    status=CommitStatus.IN_PROGRESS,
                    job_id=str(result) if result else None,
                    message="Commit started",
                )

        except PanDeviceError as e:
            logger.error(f"Commit failed: {e}")
            return CommitResult(
                status=CommitStatus.FAILED,
                message=str(e),
            )

    def get_commit_status(self, job_id: str) -> CommitResult:
        """
        Get status of an async commit job.

        Args:
            job_id: Commit job ID

        Returns:
            CommitResult with current status
        """
        self._ensure_connected()

        try:
            result = self._firewall.op(f"show jobs id {job_id}")
            # Parse result to determine status
            # This is simplified - actual parsing would be more complex
            return CommitResult(
                status=CommitStatus.IN_PROGRESS,
                job_id=job_id,
                message="Checking status",
                details={'raw': str(result)},
            )
        except Exception as e:
            return CommitResult(
                status=CommitStatus.FAILED,
                job_id=job_id,
                message=str(e),
            )

    # ========== Operational Commands ==========

    def op_command(self, cmd: str) -> str:
        """
        Execute an operational command.

        Args:
            cmd: Operational command (e.g., "show system info")

        Returns:
            Command output
        """
        self._ensure_connected()

        result = self._firewall.op(cmd)
        return str(result)

    def reboot(self):
        """Reboot the firewall."""
        self._ensure_connected()

        logger.warning(f"Rebooting firewall {self.hostname}")
        self._firewall.op("request restart system")

    # ========== Context Manager ==========

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False


def wait_for_firewall(
    hostname: str,
    username: str = "admin",
    password: str = None,
    timeout: int = 600,
    interval: int = 30,
    max_retries: int = 0,
) -> Optional[FirewallAPIClient]:
    """
    Wait for a firewall to become accessible.

    Useful after Terraform deployment to wait for the firewall to boot.

    Args:
        hostname: Firewall management IP
        username: Admin username
        password: Admin password
        timeout: Maximum wait time in seconds
        interval: Check interval in seconds
        max_retries: Maximum number of connection attempts (0 = no limit, use timeout only)

    Returns:
        FirewallAPIClient if successful, None if timeout or max retries exceeded
    """
    if max_retries > 0:
        logger.info(f"Waiting for firewall {hostname} to be accessible (max {max_retries} retries, interval {interval}s)")
    else:
        logger.info(f"Waiting for firewall {hostname} to be accessible (timeout: {timeout}s)")

    start_time = time.time()
    attempt = 0

    while time.time() - start_time < timeout:
        attempt += 1
        try:
            client = FirewallAPIClient(hostname, username, password)
            client.connect()
            logger.info(f"Firewall {hostname} is accessible (attempt {attempt})")
            return client
        except FirewallConnectionError as e:
            logger.debug(f"Firewall not accessible yet: {e}")

            # Check if max retries exceeded
            if max_retries > 0 and attempt >= max_retries:
                logger.warning(f"Firewall {hostname} not accessible after {max_retries} retries")
                return None

            time.sleep(interval)

    logger.warning(f"Firewall {hostname} not accessible after {timeout}s")
    return None
