"""
Bootstrap Configuration Generator for PAN-OS Firewalls.

Generates bootstrap packages for VM-Series firewalls including:
- init-cfg.txt: Initial device settings
- bootstrap.xml: Day 0 configuration with interfaces, zones, policies
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

logger = logging.getLogger(__name__)


@dataclass
class InterfaceConfig:
    """Network interface configuration."""
    name: str  # e.g., "ethernet1/1"
    zone: str  # e.g., "untrust"
    ip_address: Optional[str] = None  # CIDR notation or "dhcp-client"
    dhcp: bool = True
    comment: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'zone': self.zone,
            'ip_address': self.ip_address,
            'dhcp': self.dhcp,
            'comment': self.comment,
        }


@dataclass
class ZoneConfig:
    """Security zone configuration."""
    name: str
    interfaces: List[str] = field(default_factory=list)
    zone_protection_profile: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'interfaces': self.interfaces,
            'zone_protection_profile': self.zone_protection_profile,
        }


@dataclass
class BootstrapConfig:
    """
    Bootstrap configuration for a VM-Series firewall.

    Contains all settings needed for a functional day-0 configuration:
    - Device settings (hostname, DNS, NTP)
    - Network interfaces
    - Security zones
    - Virtual router with default route
    - Basic security policy (trust->untrust)
    - NAT policy (outbound PAT)
    """

    # Device identification
    hostname: str

    # Admin credentials (from deployment)
    admin_username: str = "admin"
    admin_password: Optional[str] = None  # Will be set during generation

    # DNS settings
    dns_primary: str = "8.8.8.8"
    dns_secondary: str = "8.8.4.4"

    # NTP settings
    ntp_primary: str = "time.google.com"
    ntp_secondary: str = "time.windows.com"

    # Timezone
    timezone: str = "US/Pacific"

    # Network configuration
    interfaces: List[InterfaceConfig] = field(default_factory=list)
    zones: List[ZoneConfig] = field(default_factory=list)

    # Virtual router
    virtual_router_name: str = "default"
    default_gateway: Optional[str] = None  # IP of next hop for default route

    # Trust network CIDR (for NAT source)
    trust_network: str = "10.100.2.0/24"

    # Panorama settings (optional)
    panorama_server: Optional[str] = None
    panorama_server_2: Optional[str] = None

    # Template settings
    template_name: Optional[str] = None
    template_stack: Optional[str] = None
    device_group: Optional[str] = None

    # Auth code for licensing
    auth_code: Optional[str] = None

    def __post_init__(self):
        """Set up default interfaces and zones if not provided."""
        if not self.interfaces:
            self.interfaces = [
                InterfaceConfig(
                    name="ethernet1/1",
                    zone="untrust",
                    dhcp=True,
                    comment="Untrust interface - Internet facing"
                ),
                InterfaceConfig(
                    name="ethernet1/2",
                    zone="trust",
                    dhcp=True,
                    comment="Trust interface - Internal network"
                ),
            ]

        if not self.zones:
            self.zones = [
                ZoneConfig(name="trust", interfaces=["ethernet1/2"]),
                ZoneConfig(name="untrust", interfaces=["ethernet1/1"]),
            ]

    @classmethod
    def from_cloud_firewall(cls, firewall, deployment, credentials: Dict[str, Any] = None) -> 'BootstrapConfig':
        """
        Create BootstrapConfig from a CloudFirewall instance.

        Args:
            firewall: CloudFirewall instance
            deployment: CloudDeployment instance
            credentials: Optional credentials dict

        Returns:
            BootstrapConfig instance
        """
        # Get trust subnet for the firewall
        trust_subnet = None
        for subnet in deployment.virtual_network.subnets:
            if 'trust' in subnet.name and firewall.firewall_type in subnet.name:
                trust_subnet = subnet.prefix
                break
        if not trust_subnet:
            # Use default trust subnet
            for subnet in deployment.virtual_network.subnets:
                if subnet.name == deployment.get_subnet_name('trust'):
                    trust_subnet = subnet.prefix
                    break

        config = cls(
            hostname=firewall.hostname,
            admin_username=credentials.get('username', 'admin') if credentials else 'admin',
            admin_password=credentials.get('password') if credentials else None,
            trust_network=trust_subnet or "10.100.2.0/24",
        )

        # Set device settings from firewall config
        if firewall.device:
            if firewall.device.dns_primary:
                config.dns_primary = firewall.device.dns_primary
            if firewall.device.dns_secondary:
                config.dns_secondary = firewall.device.dns_secondary
            if firewall.device.ntp_primary:
                config.ntp_primary = firewall.device.ntp_primary
            if firewall.device.timezone:
                config.timezone = firewall.device.timezone

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'hostname': self.hostname,
            'admin_username': self.admin_username,
            'dns_primary': self.dns_primary,
            'dns_secondary': self.dns_secondary,
            'ntp_primary': self.ntp_primary,
            'ntp_secondary': self.ntp_secondary,
            'timezone': self.timezone,
            'interfaces': [i.to_dict() for i in self.interfaces],
            'zones': [z.to_dict() for z in self.zones],
            'virtual_router_name': self.virtual_router_name,
            'default_gateway': self.default_gateway,
            'trust_network': self.trust_network,
            'panorama_server': self.panorama_server,
        }


class BootstrapGenerator:
    """
    Generates bootstrap files for PAN-OS firewalls.

    Creates:
    - init-cfg.txt: Initial boot configuration
    - bootstrap.xml: Day 0 PAN-OS configuration
    """

    def __init__(self, config: BootstrapConfig):
        """
        Initialize bootstrap generator.

        Args:
            config: BootstrapConfig with all settings
        """
        self.config = config

    def generate_init_cfg(self) -> str:
        """
        Generate init-cfg.txt content.

        This file configures initial settings before PAN-OS boots:
        - Management type (static/dhcp)
        - Panorama settings
        - Hostname
        - DNS

        Returns:
            init-cfg.txt content as string
        """
        lines = [
            f"type=dhcp-client",  # Management interface uses DHCP from Azure
            f"hostname={self.config.hostname}",
            f"dns-primary={self.config.dns_primary}",
            f"dns-secondary={self.config.dns_secondary}",
        ]

        # Panorama settings
        if self.config.panorama_server:
            lines.append(f"panorama-server={self.config.panorama_server}")
            if self.config.panorama_server_2:
                lines.append(f"panorama-server-2={self.config.panorama_server_2}")
            if self.config.template_stack:
                lines.append(f"tplname={self.config.template_stack}")
            if self.config.device_group:
                lines.append(f"dgname={self.config.device_group}")

        # Auth code if provided
        if self.config.auth_code:
            lines.append(f"authcodes={self.config.auth_code}")

        return "\n".join(lines) + "\n"

    def generate_bootstrap_xml(self) -> str:
        """
        Generate bootstrap.xml with day-0 configuration.

        Includes:
        - Device settings (DNS, NTP, timezone)
        - Interfaces (ethernet1/1, ethernet1/2)
        - Zones (trust, untrust)
        - Virtual router with default route
        - Security policy (trust->untrust allow 80/443)
        - NAT policy (outbound PAT)

        Returns:
            bootstrap.xml content as string
        """
        # Create root config element
        config = ET.Element("config")
        config.set("version", "10.2.0")

        # Add mgt-config (not in running config, but needed for bootstrap)
        mgt_config = ET.SubElement(config, "mgt-config")
        users = ET.SubElement(mgt_config, "users")
        admin_user = ET.SubElement(users, "entry", name=self.config.admin_username)
        ET.SubElement(admin_user, "permissions").text = "superuser"
        ET.SubElement(admin_user, "phash").text = self._hash_password(self.config.admin_password)

        # Devices container
        devices = ET.SubElement(config, "devices")
        localhost = ET.SubElement(devices, "entry", name="localhost.localdomain")

        # Device settings
        self._add_device_settings(localhost)

        # Network configuration
        network = ET.SubElement(localhost, "network")
        self._add_interfaces(network)
        self._add_virtual_router(network)

        # Zone configuration
        vsys_container = ET.SubElement(localhost, "vsys")
        vsys1 = ET.SubElement(vsys_container, "entry", name="vsys1")
        self._add_zones(vsys1)

        # Security and NAT policies
        rulebase = ET.SubElement(vsys1, "rulebase")
        self._add_security_policy(rulebase)
        self._add_nat_policy(rulebase)

        # Format XML with proper indentation
        return self._prettify_xml(config)

    def _hash_password(self, password: str) -> str:
        """
        Create password hash for PAN-OS.

        Note: In production, use proper PAN-OS password hashing.
        For bootstrap, we typically use a known hash or the password
        is set via init-cfg.txt admin settings.
        """
        if not password:
            # Default hash for 'admin' - firewall will prompt for change
            return "$1$dgvdpkqv$XJKZWkUGsWLkW8UUOIPPu/"
        # For real implementation, use passlib with des_crypt
        # This is a placeholder - actual hash would be generated properly
        return f"$1$placeholder${password[:8]}"

    def _add_device_settings(self, parent: ET.Element):
        """Add device settings (hostname, DNS, NTP, timezone)."""
        deviceconfig = ET.SubElement(parent, "deviceconfig")
        system = ET.SubElement(deviceconfig, "system")

        # Hostname
        ET.SubElement(system, "hostname").text = self.config.hostname

        # Timezone
        timezone = ET.SubElement(system, "timezone")
        ET.SubElement(timezone, "timezone").text = self.config.timezone

        # DNS
        dns_setting = ET.SubElement(system, "dns-setting")
        servers = ET.SubElement(dns_setting, "servers")
        ET.SubElement(servers, "primary").text = self.config.dns_primary
        ET.SubElement(servers, "secondary").text = self.config.dns_secondary

        # NTP
        ntp = ET.SubElement(system, "ntp-servers")
        primary_ntp = ET.SubElement(ntp, "primary-ntp-server")
        ET.SubElement(primary_ntp, "ntp-server-address").text = self.config.ntp_primary
        secondary_ntp = ET.SubElement(ntp, "secondary-ntp-server")
        ET.SubElement(secondary_ntp, "ntp-server-address").text = self.config.ntp_secondary

    def _add_interfaces(self, network: ET.Element):
        """Add interface configuration."""
        interface = ET.SubElement(network, "interface")
        ethernet = ET.SubElement(interface, "ethernet")

        for iface in self.config.interfaces:
            # Parse interface name (e.g., "ethernet1/1" -> slot 1, port 1)
            entry = ET.SubElement(ethernet, "entry", name=iface.name)
            layer3 = ET.SubElement(entry, "layer3")

            if iface.dhcp:
                dhcp_client = ET.SubElement(layer3, "dhcp-client")
                ET.SubElement(dhcp_client, "enable").text = "yes"
                ET.SubElement(dhcp_client, "create-default-route").text = "yes" if iface.zone == "untrust" else "no"
            elif iface.ip_address:
                ip_elem = ET.SubElement(layer3, "ip")
                ET.SubElement(ip_elem, "entry", name=iface.ip_address)

            if iface.comment:
                ET.SubElement(entry, "comment").text = iface.comment

    def _add_zones(self, vsys: ET.Element):
        """Add security zone configuration."""
        zone_container = ET.SubElement(vsys, "zone")

        for zone in self.config.zones:
            entry = ET.SubElement(zone_container, "entry", name=zone.name)
            network = ET.SubElement(entry, "network")
            layer3 = ET.SubElement(network, "layer3")

            for iface in zone.interfaces:
                ET.SubElement(layer3, "member").text = iface

            if zone.zone_protection_profile:
                ET.SubElement(network, "zone-protection-profile").text = zone.zone_protection_profile

    def _add_virtual_router(self, network: ET.Element):
        """Add virtual router with default route."""
        vr_container = ET.SubElement(network, "virtual-router")
        vr = ET.SubElement(vr_container, "entry", name=self.config.virtual_router_name)

        # Add interfaces to virtual router
        interface = ET.SubElement(vr, "interface")
        for iface in self.config.interfaces:
            ET.SubElement(interface, "member").text = iface.name

        # Add default route if gateway specified
        if self.config.default_gateway:
            routing_table = ET.SubElement(vr, "routing-table")
            ip = ET.SubElement(routing_table, "ip")
            static_routes = ET.SubElement(ip, "static-route")
            default_route = ET.SubElement(static_routes, "entry", name="default")
            ET.SubElement(default_route, "destination").text = "0.0.0.0/0"
            nexthop = ET.SubElement(default_route, "nexthop")
            ET.SubElement(nexthop, "ip-address").text = self.config.default_gateway

    def _add_security_policy(self, rulebase: ET.Element):
        """Add basic security policy: trust->untrust allow 80/443."""
        security = ET.SubElement(rulebase, "security")
        rules = ET.SubElement(security, "rules")

        # Allow outbound web traffic
        rule = ET.SubElement(rules, "entry", name="allow-outbound-web")

        # From zone
        from_elem = ET.SubElement(rule, "from")
        ET.SubElement(from_elem, "member").text = "trust"

        # To zone
        to_elem = ET.SubElement(rule, "to")
        ET.SubElement(to_elem, "member").text = "untrust"

        # Source
        source = ET.SubElement(rule, "source")
        ET.SubElement(source, "member").text = "any"

        # Destination
        destination = ET.SubElement(rule, "destination")
        ET.SubElement(destination, "member").text = "any"

        # Source user
        source_user = ET.SubElement(rule, "source-user")
        ET.SubElement(source_user, "member").text = "any"

        # Application
        application = ET.SubElement(rule, "application")
        ET.SubElement(application, "member").text = "any"

        # Service (HTTP/HTTPS)
        service = ET.SubElement(rule, "service")
        ET.SubElement(service, "member").text = "service-http"
        ET.SubElement(service, "member").text = "service-https"

        # Action
        ET.SubElement(rule, "action").text = "allow"

        # Logging
        ET.SubElement(rule, "log-start").text = "no"
        ET.SubElement(rule, "log-end").text = "yes"

        # Description
        ET.SubElement(rule, "description").text = "Allow outbound HTTP/HTTPS from trust zone"

    def _add_nat_policy(self, rulebase: ET.Element):
        """Add outbound PAT NAT policy."""
        nat = ET.SubElement(rulebase, "nat")
        rules = ET.SubElement(nat, "rules")

        # Outbound PAT rule
        rule = ET.SubElement(rules, "entry", name="outbound-pat")

        # From zone
        from_elem = ET.SubElement(rule, "from")
        ET.SubElement(from_elem, "member").text = "trust"

        # To zone
        to_elem = ET.SubElement(rule, "to")
        ET.SubElement(to_elem, "member").text = "untrust"

        # Source
        source = ET.SubElement(rule, "source")
        ET.SubElement(source, "member").text = self.config.trust_network

        # Destination
        destination = ET.SubElement(rule, "destination")
        ET.SubElement(destination, "member").text = "any"

        # Service
        service = ET.SubElement(rule, "service").text = "any"

        # Source translation (dynamic IP and port)
        source_translation = ET.SubElement(rule, "source-translation")
        dynamic_ip_and_port = ET.SubElement(source_translation, "dynamic-ip-and-port")
        interface_address = ET.SubElement(dynamic_ip_and_port, "interface-address")
        ET.SubElement(interface_address, "interface").text = "ethernet1/1"

        # Description
        ET.SubElement(rule, "description").text = "Outbound PAT for trust network internet access"

    def _prettify_xml(self, elem: ET.Element) -> str:
        """Format XML with proper indentation."""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def generate(self, output_dir: str) -> Dict[str, str]:
        """
        Generate all bootstrap files.

        Args:
            output_dir: Directory to write bootstrap files

        Returns:
            Dict mapping filename to file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files_created = {}

        # Create bootstrap directory structure
        config_dir = output_path / "config"
        config_dir.mkdir(exist_ok=True)

        license_dir = output_path / "license"
        license_dir.mkdir(exist_ok=True)

        content_dir = output_path / "content"
        content_dir.mkdir(exist_ok=True)

        software_dir = output_path / "software"
        software_dir.mkdir(exist_ok=True)

        # Generate init-cfg.txt
        init_cfg_path = config_dir / "init-cfg.txt"
        init_cfg_content = self.generate_init_cfg()
        with open(init_cfg_path, 'w') as f:
            f.write(init_cfg_content)
        files_created['init-cfg.txt'] = str(init_cfg_path)
        logger.info(f"Generated {init_cfg_path}")

        # Generate bootstrap.xml
        bootstrap_xml_path = config_dir / "bootstrap.xml"
        bootstrap_xml_content = self.generate_bootstrap_xml()
        with open(bootstrap_xml_path, 'w') as f:
            f.write(bootstrap_xml_content)
        files_created['bootstrap.xml'] = str(bootstrap_xml_path)
        logger.info(f"Generated {bootstrap_xml_path}")

        # Generate authcodes file if provided
        if self.config.auth_code:
            authcodes_path = license_dir / "authcodes"
            with open(authcodes_path, 'w') as f:
                f.write(self.config.auth_code + "\n")
            files_created['authcodes'] = str(authcodes_path)
            logger.info(f"Generated {authcodes_path}")

        return files_created


def generate_firewall_bootstrap(
    firewall,
    deployment,
    output_dir: str,
    credentials: Dict[str, Any] = None,
) -> Dict[str, str]:
    """
    Convenience function to generate bootstrap for a CloudFirewall.

    Args:
        firewall: CloudFirewall instance
        deployment: CloudDeployment instance
        output_dir: Directory to write bootstrap files
        credentials: Optional credentials dict

    Returns:
        Dict mapping filename to file path
    """
    config = BootstrapConfig.from_cloud_firewall(firewall, deployment, credentials)
    generator = BootstrapGenerator(config)
    return generator.generate(output_dir)
