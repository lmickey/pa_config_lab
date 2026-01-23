"""
Panorama API Client for Panorama management servers.

Wraps the pan-os-python library to provide a clean interface for:
- Connection and authentication
- Device management
- Template and device group operations
- Plugin management
- Commit operations
"""

import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    from panos.panorama import Panorama, DeviceGroup, Template, TemplateStack
    from panos.firewall import Firewall
    from panos.errors import PanDeviceError, PanConnectionTimeout, PanURLError
    from panos.device import SystemSettings
    PANOS_AVAILABLE = True
except ImportError:
    PANOS_AVAILABLE = False

logger = logging.getLogger(__name__)


class PanoramaConnectionError(Exception):
    """Error connecting to Panorama."""
    pass


class PanoramaAPIError(Exception):
    """Error during Panorama API operation."""
    pass


class LicenseStatus(str, Enum):
    """Panorama license status."""
    UNLICENSED = "unlicensed"
    LICENSED = "licensed"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


@dataclass
class PanoramaInfo:
    """Panorama device information."""
    hostname: str
    serial: str
    model: str
    sw_version: str
    uptime: str
    license_status: LicenseStatus = LicenseStatus.UNKNOWN
    plugins_installed: List[str] = field(default_factory=list)
    management_ip: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'hostname': self.hostname,
            'serial': self.serial,
            'model': self.model,
            'sw_version': self.sw_version,
            'uptime': self.uptime,
            'license_status': self.license_status.value,
            'plugins_installed': self.plugins_installed,
            'management_ip': self.management_ip,
        }


@dataclass
class CommitResult:
    """Result of a commit operation."""
    success: bool
    job_id: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'job_id': self.job_id,
            'message': self.message,
            'details': self.details,
        }


class PanoramaAPIClient:
    """
    PAN-OS Panorama API client.

    Provides methods for connecting to and managing Panorama
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
        Initialize Panorama API client.

        Args:
            hostname: Panorama management IP or hostname
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

        self._panorama: Optional[Panorama] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to Panorama."""
        return self._connected and self._panorama is not None

    def connect(self, verify_ssl: bool = False) -> bool:
        """
        Connect to Panorama.

        Args:
            verify_ssl: Verify SSL certificate (default False for self-signed)

        Returns:
            True if connection successful

        Raises:
            PanoramaConnectionError: If connection fails
        """
        logger.info(f"Connecting to Panorama at {self.hostname}")

        try:
            self._panorama = Panorama(
                hostname=self.hostname,
                api_username=self.username,
                api_password=self.password,
                api_key=self.api_key,
                port=self.port,
                timeout=self.timeout,
            )

            # Test connection by refreshing system info
            self._panorama.refresh_system_info()
            self._connected = True

            logger.info(f"Connected to {self._panorama.hostname} ({self._panorama.serial})")
            return True

        except PanConnectionTimeout as e:
            self._connected = False
            raise PanoramaConnectionError(f"Connection timeout: {e}")
        except PanURLError as e:
            self._connected = False
            raise PanoramaConnectionError(f"Connection error: {e}")
        except PanDeviceError as e:
            self._connected = False
            raise PanoramaConnectionError(f"Device error: {e}")
        except Exception as e:
            self._connected = False
            raise PanoramaConnectionError(f"Unexpected error: {e}")

    def disconnect(self):
        """Disconnect from Panorama."""
        self._panorama = None
        self._connected = False
        logger.info(f"Disconnected from {self.hostname}")

    def _ensure_connected(self):
        """Ensure we're connected to Panorama."""
        if not self.is_connected:
            raise PanoramaConnectionError("Not connected to Panorama. Call connect() first.")

    # ========== Device Information ==========

    def get_device_info(self) -> PanoramaInfo:
        """
        Get Panorama device information.

        Returns:
            PanoramaInfo with system details
        """
        self._ensure_connected()

        self._panorama.refresh_system_info()

        return PanoramaInfo(
            hostname=self._panorama.hostname or "",
            serial=self._panorama.serial or "",
            model=self._panorama.model or "",
            sw_version=self._panorama.version or "",
            uptime=getattr(self._panorama, 'uptime', "") or "",
            management_ip=self.hostname,
        )

    def is_ready(self, timeout: int = 300, interval: int = 10) -> bool:
        """
        Wait for Panorama to be ready (autocommit complete).

        Args:
            timeout: Maximum wait time in seconds
            interval: Check interval in seconds

        Returns:
            True if Panorama is ready
        """
        logger.info(f"Waiting for Panorama to be ready (timeout: {timeout}s)")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if not self.is_connected:
                    self.connect()

                self._panorama.refresh_system_info()
                logger.info("Panorama is ready")
                return True

            except Exception as e:
                logger.debug(f"Panorama not ready yet: {e}")
                time.sleep(interval)

        logger.warning(f"Panorama not ready after {timeout}s")
        return False

    # ========== License Operations ==========

    def check_license_status(self) -> LicenseStatus:
        """
        Check Panorama license status.

        Returns:
            LicenseStatus enum value
        """
        self._ensure_connected()

        try:
            result = self._panorama.op("request license info")
            # Parse license info from result
            # This is simplified - actual parsing would be more complex
            result_str = str(result).lower()

            if 'valid' in result_str or 'active' in result_str:
                return LicenseStatus.LICENSED
            elif 'expired' in result_str:
                return LicenseStatus.EXPIRED
            elif 'not found' in result_str or 'unlicensed' in result_str:
                return LicenseStatus.UNLICENSED
            else:
                return LicenseStatus.UNKNOWN

        except Exception as e:
            logger.error(f"Failed to check license: {e}")
            return LicenseStatus.UNKNOWN

    def install_license(self, auth_code: str) -> bool:
        """
        Install a license using an auth code.

        Args:
            auth_code: License authorization code

        Returns:
            True if license installed successfully
        """
        self._ensure_connected()

        try:
            self._panorama.op(f"request license fetch auth-code {auth_code}")
            logger.info("License installed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to install license: {e}")
            return False

    # ========== Plugin Operations ==========

    def get_installed_plugins(self) -> List[str]:
        """
        Get list of installed plugins.

        Returns:
            List of plugin names
        """
        self._ensure_connected()

        try:
            result = self._panorama.op("show plugins packages")
            # Parse plugin list from result
            # This is simplified - actual parsing would be more complex
            return []
        except Exception as e:
            logger.error(f"Failed to get plugins: {e}")
            return []

    def install_plugin(self, plugin_name: str, version: str = "latest") -> bool:
        """
        Install a Panorama plugin.

        Args:
            plugin_name: Plugin name (e.g., "cloud_services")
            version: Plugin version or "latest"

        Returns:
            True if plugin installed successfully
        """
        self._ensure_connected()

        try:
            # Download plugin
            if version == "latest":
                self._panorama.op(f"request plugins download file {plugin_name}")
            else:
                self._panorama.op(f"request plugins download file {plugin_name}-{version}")

            # Install plugin
            self._panorama.op(f"request plugins install {plugin_name}")

            logger.info(f"Plugin {plugin_name} installed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to install plugin {plugin_name}: {e}")
            return False

    # ========== Device Group Operations ==========

    def create_device_group(self, name: str, description: str = "") -> bool:
        """
        Create a device group.

        Args:
            name: Device group name
            description: Optional description

        Returns:
            True if created successfully
        """
        self._ensure_connected()

        try:
            dg = DeviceGroup(name=name, description=description)
            self._panorama.add(dg)
            dg.apply()
            logger.info(f"Created device group: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create device group: {e}")
            return False

    def get_device_groups(self) -> List[str]:
        """
        Get list of device groups.

        Returns:
            List of device group names
        """
        self._ensure_connected()

        try:
            dgs = DeviceGroup.refreshall(self._panorama)
            return [dg.name for dg in dgs]
        except Exception as e:
            logger.error(f"Failed to get device groups: {e}")
            return []

    # ========== Template Operations ==========

    def create_template(self, name: str, description: str = "") -> bool:
        """
        Create a template.

        Args:
            name: Template name
            description: Optional description

        Returns:
            True if created successfully
        """
        self._ensure_connected()

        try:
            template = Template(name=name, description=description)
            self._panorama.add(template)
            template.apply()
            logger.info(f"Created template: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            return False

    def create_template_stack(
        self,
        name: str,
        templates: List[str],
        description: str = "",
    ) -> bool:
        """
        Create a template stack.

        Args:
            name: Template stack name
            templates: List of template names (in order)
            description: Optional description

        Returns:
            True if created successfully
        """
        self._ensure_connected()

        try:
            stack = TemplateStack(name=name, templates=templates, description=description)
            self._panorama.add(stack)
            stack.apply()
            logger.info(f"Created template stack: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create template stack: {e}")
            return False

    def get_templates(self) -> List[str]:
        """
        Get list of templates.

        Returns:
            List of template names
        """
        self._ensure_connected()

        try:
            templates = Template.refreshall(self._panorama)
            return [t.name for t in templates]
        except Exception as e:
            logger.error(f"Failed to get templates: {e}")
            return []

    # ========== Managed Device Operations ==========

    def get_managed_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of managed devices (firewalls).

        Returns:
            List of device info dicts
        """
        self._ensure_connected()

        try:
            devices = self._panorama.refresh_devices()
            return [
                {
                    'serial': d.serial,
                    'hostname': d.hostname,
                    'connected': d.connected,
                }
                for d in devices
            ]
        except Exception as e:
            logger.error(f"Failed to get managed devices: {e}")
            return []

    # ========== Device Settings ==========

    def set_hostname(self, hostname: str):
        """
        Set the Panorama hostname.

        Args:
            hostname: New hostname
        """
        self._ensure_connected()

        settings = SystemSettings()
        settings.hostname = hostname
        self._panorama.add(settings)
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
        self._panorama.add(settings)
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
        self._panorama.add(settings)
        settings.apply()

        logger.info(f"Set NTP servers: {primary}, {secondary}")

    # ========== Commit Operations ==========

    def commit(
        self,
        description: str = "",
        sync: bool = True,
        timeout: int = 300,
    ) -> CommitResult:
        """
        Commit configuration changes to Panorama.

        Args:
            description: Commit description
            sync: Wait for commit to complete
            timeout: Commit timeout in seconds

        Returns:
            CommitResult with commit status
        """
        self._ensure_connected()

        logger.info(f"Starting Panorama commit{' (sync)' if sync else ''}")

        try:
            if sync:
                result = self._panorama.commit(
                    sync=True,
                    timeout=timeout,
                    description=description,
                )
                return CommitResult(
                    success=True,
                    message="Commit successful",
                )
            else:
                result = self._panorama.commit(
                    sync=False,
                    description=description,
                )
                return CommitResult(
                    success=True,
                    job_id=str(result) if result else None,
                    message="Commit started",
                )

        except PanDeviceError as e:
            logger.error(f"Commit failed: {e}")
            return CommitResult(
                success=False,
                message=str(e),
            )

    def commit_all(
        self,
        device_groups: List[str] = None,
        templates: List[str] = None,
        sync: bool = True,
        timeout: int = 600,
    ) -> CommitResult:
        """
        Push configuration to managed devices.

        Args:
            device_groups: Device groups to push (or all)
            templates: Templates to push (or all)
            sync: Wait for commit to complete
            timeout: Commit timeout in seconds

        Returns:
            CommitResult with commit status
        """
        self._ensure_connected()

        logger.info("Starting commit-all to managed devices")

        try:
            # This would use commit_all or push_to_devices in pan-os-python
            # Simplified implementation
            result = self._panorama.commit_all(
                sync=sync,
                timeout=timeout,
            )
            return CommitResult(
                success=True,
                message="Commit-all successful",
            )
        except Exception as e:
            logger.error(f"Commit-all failed: {e}")
            return CommitResult(
                success=False,
                message=str(e),
            )

    # ========== Operational Commands ==========

    def op_command(self, cmd: str) -> str:
        """
        Execute an operational command.

        Args:
            cmd: Operational command

        Returns:
            Command output
        """
        self._ensure_connected()

        result = self._panorama.op(cmd)
        return str(result)

    # ========== Context Manager ==========

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False


def wait_for_panorama(
    hostname: str,
    username: str = "admin",
    password: str = None,
    timeout: int = 600,
    interval: int = 30,
) -> Optional[PanoramaAPIClient]:
    """
    Wait for Panorama to become accessible.

    Args:
        hostname: Panorama management IP
        username: Admin username
        password: Admin password
        timeout: Maximum wait time in seconds
        interval: Check interval in seconds

    Returns:
        PanoramaAPIClient if successful, None if timeout
    """
    logger.info(f"Waiting for Panorama {hostname} to be accessible (timeout: {timeout}s)")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            client = PanoramaAPIClient(hostname, username, password)
            client.connect()
            logger.info(f"Panorama {hostname} is accessible")
            return client
        except PanoramaConnectionError as e:
            logger.debug(f"Panorama not accessible yet: {e}")
            time.sleep(interval)

    logger.warning(f"Panorama {hostname} not accessible after {timeout}s")
    return None
