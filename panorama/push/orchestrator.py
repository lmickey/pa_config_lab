"""
Panorama Push Orchestrator.

Orchestrates the process of pushing configuration to a Panorama
management server after deployment. Handles:
- Waiting for Panorama to be ready
- Installing license and plugins
- Creating device groups and templates
- Committing changes
"""

import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from panorama.api_client import (
    PanoramaAPIClient,
    PanoramaConnectionError,
    PanoramaAPIError,
    CommitResult as APICommitResult,
    LicenseStatus,
    wait_for_panorama,
)
from config.models.cloud import CloudPanorama, CloudDeployment

logger = logging.getLogger(__name__)


class PushPhase(str, Enum):
    """Push operation phases."""
    WAITING = "waiting"
    CONNECTING = "connecting"
    LICENSING = "licensing"
    INSTALLING_PLUGINS = "installing_plugins"
    CONFIGURING_DEVICE = "configuring_device"
    CREATING_TEMPLATES = "creating_templates"
    CREATING_DEVICE_GROUPS = "creating_device_groups"
    COMMITTING = "committing"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"


class PushStatus(str, Enum):
    """Push operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class PushResult:
    """Result of a push operation."""
    status: PushStatus
    phase: PushPhase
    panorama_name: str
    message: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    phases_completed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    commit_result: Optional[APICommitResult] = None
    templates_created: List[str] = field(default_factory=list)
    device_groups_created: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status == PushStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'phase': self.phase.value,
            'panorama_name': self.panorama_name,
            'message': self.message,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'phases_completed': self.phases_completed,
            'errors': self.errors,
            'commit_result': self.commit_result.to_dict() if self.commit_result else None,
            'templates_created': self.templates_created,
            'device_groups_created': self.device_groups_created,
        }


class PanoramaPushOrchestrator:
    """
    Orchestrates pushing configuration to a Panorama.

    Takes a CloudPanorama configuration and pushes the initial settings
    to the actual Panorama device via the PAN-OS API.
    """

    def __init__(
        self,
        panorama_config: CloudPanorama,
        deployment: CloudDeployment,
        management_ip: str,
        credentials: Dict[str, str],
        license_auth_code: Optional[str] = None,
    ):
        """
        Initialize push orchestrator.

        Args:
            panorama_config: CloudPanorama configuration
            deployment: CloudDeployment settings
            management_ip: Panorama management IP address
            credentials: Dict with 'username' and 'password'
            license_auth_code: Optional license authorization code
        """
        self.panorama_config = panorama_config
        self.deployment = deployment
        self.management_ip = management_ip
        self.credentials = credentials
        self.license_auth_code = license_auth_code

        self._client: Optional[PanoramaAPIClient] = None
        self._result: Optional[PushResult] = None
        self._progress_callback: Optional[Callable[[PushPhase, str], None]] = None

    def push(
        self,
        wait_timeout: int = 900,
        commit_timeout: int = 300,
        progress_callback: Callable[[PushPhase, str], None] = None,
    ) -> PushResult:
        """
        Push configuration to Panorama.

        Args:
            wait_timeout: Timeout for waiting for Panorama to be ready
            commit_timeout: Timeout for commit operation
            progress_callback: Optional callback for progress updates

        Returns:
            PushResult with operation status
        """
        self._progress_callback = progress_callback
        self._result = PushResult(
            status=PushStatus.IN_PROGRESS,
            phase=PushPhase.WAITING,
            panorama_name=self.panorama_config.name,
            started_at=datetime.utcnow().isoformat(),
        )

        try:
            # Phase 1: Wait for Panorama to be accessible
            self._update_phase(PushPhase.WAITING, "Waiting for Panorama to be accessible")
            if not self._wait_for_panorama(wait_timeout):
                return self._fail("Panorama not accessible after timeout")

            # Phase 2: Connect
            self._update_phase(PushPhase.CONNECTING, "Connecting to Panorama")
            if not self._connect():
                return self._fail("Failed to connect to Panorama")

            # Phase 3: License (optional)
            if self.license_auth_code:
                self._update_phase(PushPhase.LICENSING, "Installing license")
                if not self._install_license():
                    # License failure is not fatal, continue
                    self._result.errors.append("License installation failed")

            # Phase 4: Install plugins
            self._update_phase(PushPhase.INSTALLING_PLUGINS, "Installing plugins")
            self._install_plugins()

            # Phase 5: Configure device settings
            self._update_phase(PushPhase.CONFIGURING_DEVICE, "Configuring device settings")
            if not self._configure_device():
                return self._fail("Failed to configure device settings")

            # Phase 6: Create templates
            self._update_phase(PushPhase.CREATING_TEMPLATES, "Creating templates")
            if not self._create_templates():
                return self._fail("Failed to create templates")

            # Phase 7: Create device groups
            self._update_phase(PushPhase.CREATING_DEVICE_GROUPS, "Creating device groups")
            if not self._create_device_groups():
                return self._fail("Failed to create device groups")

            # Phase 8: Commit
            self._update_phase(PushPhase.COMMITTING, "Committing configuration")
            commit_result = self._commit(commit_timeout)
            self._result.commit_result = commit_result
            if not commit_result.success:
                return self._fail(f"Commit failed: {commit_result.message}")

            # Phase 9: Verify
            self._update_phase(PushPhase.VERIFYING, "Verifying configuration")
            if not self._verify():
                return self._fail("Configuration verification failed")

            # Success
            self._update_phase(PushPhase.COMPLETE, "Configuration push complete")
            self._result.status = PushStatus.SUCCESS
            self._result.completed_at = datetime.utcnow().isoformat()
            self._result.message = "Configuration successfully pushed"

            return self._result

        except Exception as e:
            logger.exception(f"Push failed with unexpected error: {e}")
            return self._fail(f"Unexpected error: {e}")

        finally:
            if self._client:
                self._client.disconnect()

    def _update_phase(self, phase: PushPhase, message: str):
        """Update current phase and notify callback."""
        self._result.phase = phase
        self._result.phases_completed.append(phase.value)
        logger.info(f"[{self.panorama_config.name}] {message}")

        if self._progress_callback:
            self._progress_callback(phase, message)

    def _fail(self, message: str) -> PushResult:
        """Mark push as failed."""
        self._result.status = PushStatus.FAILED
        self._result.phase = PushPhase.FAILED
        self._result.message = message
        self._result.errors.append(message)
        self._result.completed_at = datetime.utcnow().isoformat()
        logger.error(f"[{self.panorama_config.name}] Push failed: {message}")
        return self._result

    def _wait_for_panorama(self, timeout: int) -> bool:
        """Wait for Panorama to be accessible."""
        self._client = wait_for_panorama(
            hostname=self.management_ip,
            username=self.credentials.get('username', 'admin'),
            password=self.credentials.get('password'),
            timeout=timeout,
        )
        return self._client is not None

    def _connect(self) -> bool:
        """Connect to Panorama."""
        try:
            if not self._client:
                self._client = PanoramaAPIClient(
                    hostname=self.management_ip,
                    username=self.credentials.get('username', 'admin'),
                    password=self.credentials.get('password'),
                )
                self._client.connect()
            return True
        except PanoramaConnectionError as e:
            self._result.errors.append(f"Connection error: {e}")
            return False

    def _install_license(self) -> bool:
        """Install license using auth code."""
        try:
            if self.license_auth_code:
                return self._client.install_license(self.license_auth_code)
            return True
        except Exception as e:
            self._result.errors.append(f"License error: {e}")
            logger.error(f"Failed to install license: {e}")
            return False

    def _install_plugins(self) -> bool:
        """Install required plugins."""
        try:
            plugins = getattr(self.panorama_config, 'plugins', [])
            for plugin in plugins:
                logger.info(f"Installing plugin: {plugin}")
                self._client.install_plugin(plugin)
            return True
        except Exception as e:
            self._result.errors.append(f"Plugin error: {e}")
            logger.error(f"Failed to install plugins: {e}")
            return False

    def _configure_device(self) -> bool:
        """Configure device settings (hostname, DNS, NTP)."""
        try:
            device = self.panorama_config.device

            # Set hostname
            if device.hostname:
                self._client.set_hostname(device.hostname)

            # Set DNS
            if device.dns_primary:
                self._client.set_dns_servers(
                    device.dns_primary,
                    device.dns_secondary,
                )

            # Set NTP
            if device.ntp_primary:
                self._client.set_ntp_servers(
                    device.ntp_primary,
                    device.ntp_secondary,
                )

            return True

        except Exception as e:
            self._result.errors.append(f"Device config error: {e}")
            logger.error(f"Failed to configure device: {e}")
            return False

    def _create_templates(self) -> bool:
        """Create templates and template stacks."""
        try:
            templates = getattr(self.panorama_config, 'templates', [])

            # Create base templates
            for template_name in templates:
                if self._client.create_template(
                    name=template_name,
                    description=f"Template created by pa_config_lab"
                ):
                    self._result.templates_created.append(template_name)
                    logger.info(f"Created template: {template_name}")

            # Create template stack if templates exist
            if templates:
                stack_name = f"{self.panorama_config.name}-stack"
                if self._client.create_template_stack(
                    name=stack_name,
                    templates=templates,
                    description=f"Template stack for {self.panorama_config.name}"
                ):
                    self._result.templates_created.append(stack_name)
                    logger.info(f"Created template stack: {stack_name}")

            return True

        except Exception as e:
            self._result.errors.append(f"Template creation error: {e}")
            logger.error(f"Failed to create templates: {e}")
            return False

    def _create_device_groups(self) -> bool:
        """Create device groups."""
        try:
            device_groups = getattr(self.panorama_config, 'device_groups', [])

            for dg_name in device_groups:
                if self._client.create_device_group(
                    name=dg_name,
                    description=f"Device group created by pa_config_lab"
                ):
                    self._result.device_groups_created.append(dg_name)
                    logger.info(f"Created device group: {dg_name}")

            return True

        except Exception as e:
            self._result.errors.append(f"Device group creation error: {e}")
            logger.error(f"Failed to create device groups: {e}")
            return False

    def _commit(self, timeout: int) -> APICommitResult:
        """Commit configuration changes."""
        try:
            return self._client.commit(
                description="Initial configuration by pa_config_lab",
                sync=True,
                timeout=timeout,
            )
        except Exception as e:
            return APICommitResult(
                success=False,
                message=str(e),
            )

    def _verify(self) -> bool:
        """Verify configuration was applied correctly."""
        try:
            # Get device info to verify connection still works
            info = self._client.get_device_info()
            logger.info(f"Verified: {info.hostname} ({info.sw_version})")

            # Verify templates were created
            templates = self._client.get_templates()
            for expected in self._result.templates_created:
                if expected not in templates and not expected.endswith('-stack'):
                    logger.warning(f"Template {expected} not found in verification")

            # Verify device groups were created
            device_groups = self._client.get_device_groups()
            for expected in self._result.device_groups_created:
                if expected not in device_groups:
                    logger.warning(f"Device group {expected} not found in verification")

            return True

        except Exception as e:
            self._result.errors.append(f"Verification error: {e}")
            logger.error(f"Failed to verify configuration: {e}")
            return False


def push_to_panorama(
    panorama_config: CloudPanorama,
    deployment: CloudDeployment,
    management_ip: str,
    credentials: Dict[str, str],
    license_auth_code: Optional[str] = None,
    progress_callback: Callable[[PushPhase, str], None] = None,
) -> PushResult:
    """
    Convenience function to push configuration to Panorama.

    Args:
        panorama_config: CloudPanorama configuration
        deployment: CloudDeployment settings
        management_ip: Panorama management IP
        credentials: Dict with 'username' and 'password'
        license_auth_code: Optional license auth code
        progress_callback: Optional progress callback

    Returns:
        PushResult with operation status
    """
    orchestrator = PanoramaPushOrchestrator(
        panorama_config=panorama_config,
        deployment=deployment,
        management_ip=management_ip,
        credentials=credentials,
        license_auth_code=license_auth_code,
    )
    return orchestrator.push(progress_callback=progress_callback)
