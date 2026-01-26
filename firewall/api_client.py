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
    )
    from panos.policies import Rulebase, SecurityRule, NatRule
    from panos.objects import AddressObject, ServiceObject, Tag
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
