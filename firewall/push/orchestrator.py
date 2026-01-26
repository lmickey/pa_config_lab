"""
Firewall Push Orchestrator.

Orchestrates the process of pushing configuration to a PAN-OS firewall
after deployment. Handles:
- Waiting for firewall to be ready
- Applying day-0 configuration
- Committing changes
- Verifying configuration
"""

import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from firewall.api_client import (
    FirewallAPIClient,
    FirewallConnectionError,
    FirewallAPIError,
    CommitResult,
    CommitStatus,
    wait_for_firewall,
)
from config.models.cloud import CloudFirewall, CloudDeployment

logger = logging.getLogger(__name__)


class PushPhase(str, Enum):
    """Push operation phases."""
    WAITING = "waiting"
    CONNECTING = "connecting"
    CONFIGURING_DEVICE = "configuring_device"
    CONFIGURING_NETWORK = "configuring_network"
    CONFIGURING_ZONES = "configuring_zones"
    CONFIGURING_POLICY = "configuring_policy"
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
    firewall_name: str
    message: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    phases_completed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    commit_result: Optional[CommitResult] = None

    @property
    def success(self) -> bool:
        return self.status == PushStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'phase': self.phase.value,
            'firewall_name': self.firewall_name,
            'message': self.message,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'phases_completed': self.phases_completed,
            'errors': self.errors,
            'commit_result': self.commit_result.to_dict() if self.commit_result else None,
        }


class FirewallPushOrchestrator:
    """
    Orchestrates pushing configuration to a firewall.

    Takes a CloudFirewall configuration and pushes the day-0 settings
    to the actual firewall device via the PAN-OS API.
    """

    def __init__(
        self,
        firewall_config: CloudFirewall,
        deployment: CloudDeployment,
        management_ip: str,
        credentials: Dict[str, str],
    ):
        """
        Initialize push orchestrator.

        Args:
            firewall_config: CloudFirewall configuration
            deployment: CloudDeployment settings
            management_ip: Firewall management IP address
            credentials: Dict with 'username' and 'password'
        """
        self.firewall_config = firewall_config
        self.deployment = deployment
        self.management_ip = management_ip
        self.credentials = credentials

        self._client: Optional[FirewallAPIClient] = None
        self._result: Optional[PushResult] = None
        self._progress_callback: Optional[Callable[[PushPhase, str], None]] = None

    def push(
        self,
        wait_timeout: int = 600,
        commit_timeout: int = 300,
        max_retries: int = 0,
        retry_interval: int = 30,
        progress_callback: Callable[[PushPhase, str], None] = None,
    ) -> PushResult:
        """
        Push configuration to the firewall.

        Args:
            wait_timeout: Timeout for waiting for firewall to be ready
            commit_timeout: Timeout for commit operation
            max_retries: Maximum connection retry attempts (0 = no limit)
            retry_interval: Seconds between retry attempts
            progress_callback: Optional callback for progress updates

        Returns:
            PushResult with operation status
        """
        self._max_retries = max_retries
        self._retry_interval = retry_interval
        self._progress_callback = progress_callback
        self._result = PushResult(
            status=PushStatus.IN_PROGRESS,
            phase=PushPhase.WAITING,
            firewall_name=self.firewall_config.name,
            started_at=datetime.utcnow().isoformat(),
        )

        try:
            # Phase 1: Wait for firewall to be accessible
            self._update_phase(PushPhase.WAITING, "Waiting for firewall to be accessible")
            if not self._wait_for_firewall(wait_timeout):
                return self._fail("Firewall not accessible after timeout")

            # Phase 2: Connect
            self._update_phase(PushPhase.CONNECTING, "Connecting to firewall")
            if not self._connect():
                return self._fail("Failed to connect to firewall")

            # Phase 3: Configure device settings
            self._update_phase(PushPhase.CONFIGURING_DEVICE, "Configuring device settings")
            if not self._configure_device():
                return self._fail("Failed to configure device settings")

            # Phase 4: Configure network (interfaces)
            self._update_phase(PushPhase.CONFIGURING_NETWORK, "Configuring network interfaces")
            if not self._configure_network():
                return self._fail("Failed to configure network")

            # Phase 5: Configure zones
            self._update_phase(PushPhase.CONFIGURING_ZONES, "Configuring security zones")
            if not self._configure_zones():
                return self._fail("Failed to configure zones")

            # Phase 6: Configure security policy
            self._update_phase(PushPhase.CONFIGURING_POLICY, "Configuring security policy")
            if not self._configure_policy():
                return self._fail("Failed to configure policy")

            # Phase 7: Commit
            self._update_phase(PushPhase.COMMITTING, "Committing configuration")
            commit_result = self._commit(commit_timeout)
            self._result.commit_result = commit_result
            if not commit_result.success:
                return self._fail(f"Commit failed: {commit_result.message}")

            # Phase 8: Verify
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
        logger.info(f"[{self.firewall_config.name}] {message}")

        if self._progress_callback:
            self._progress_callback(phase, message)

    def _fail(self, message: str) -> PushResult:
        """Mark push as failed."""
        self._result.status = PushStatus.FAILED
        self._result.phase = PushPhase.FAILED
        self._result.message = message
        self._result.errors.append(message)
        self._result.completed_at = datetime.utcnow().isoformat()
        logger.error(f"[{self.firewall_config.name}] Push failed: {message}")
        return self._result

    def _wait_for_firewall(self, timeout: int) -> bool:
        """Wait for firewall to be accessible."""
        self._client = wait_for_firewall(
            hostname=self.management_ip,
            username=self.credentials.get('username', 'admin'),
            password=self.credentials.get('password'),
            timeout=timeout,
            interval=getattr(self, '_retry_interval', 30),
            max_retries=getattr(self, '_max_retries', 0),
        )
        return self._client is not None

    def _connect(self) -> bool:
        """Connect to the firewall."""
        try:
            if not self._client:
                self._client = FirewallAPIClient(
                    hostname=self.management_ip,
                    username=self.credentials.get('username', 'admin'),
                    password=self.credentials.get('password'),
                )
                self._client.connect()
            return True
        except FirewallConnectionError as e:
            self._result.errors.append(f"Connection error: {e}")
            return False

    def _configure_device(self) -> bool:
        """Configure device settings (hostname, DNS, NTP)."""
        try:
            device = self.firewall_config.device

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

    def _configure_network(self) -> bool:
        """Configure network interfaces."""
        try:
            # Configure each interface
            for interface in self.firewall_config.interfaces:
                zone = None
                if 'trust' in interface.name.lower() or interface.name == 'ethernet1/2':
                    zone = 'trust'
                elif 'untrust' in interface.name.lower() or interface.name == 'ethernet1/1':
                    zone = 'untrust'

                self._client.configure_interface(
                    name=interface.name,
                    mode="layer3",
                    dhcp=True,  # Use DHCP from Azure
                    zone=zone,
                    comment=f"Configured by pa_config_lab",
                )

            return True

        except Exception as e:
            self._result.errors.append(f"Network config error: {e}")
            logger.error(f"Failed to configure network: {e}")
            return False

    def _configure_zones(self) -> bool:
        """Configure security zones."""
        try:
            # Create trust zone
            self._client.create_zone(
                name="trust",
                interfaces=["ethernet1/2"],
            )

            # Create untrust zone
            self._client.create_zone(
                name="untrust",
                interfaces=["ethernet1/1"],
            )

            return True

        except Exception as e:
            self._result.errors.append(f"Zone config error: {e}")
            logger.error(f"Failed to configure zones: {e}")
            return False

    def _configure_policy(self) -> bool:
        """Configure security and NAT policies."""
        try:
            # Create basic outbound security rule
            self._client.create_security_rule(
                name="allow-outbound-web",
                source_zone=["trust"],
                destination_zone=["untrust"],
                source=["any"],
                destination=["any"],
                application=["any"],
                service=["service-http", "service-https"],
                action="allow",
                log_end=True,
                description="Allow outbound HTTP/HTTPS from trust zone",
            )

            # Create outbound NAT rule
            # Get trust subnet for source
            trust_subnet = self._get_trust_subnet()

            self._client.create_nat_rule(
                name="outbound-pat",
                source_zone=["trust"],
                destination_zone="untrust",
                source=[trust_subnet] if trust_subnet else ["any"],
                destination=["any"],
                service="any",
                source_translation_type="dynamic-ip-and-port",
                source_translation_interface="ethernet1/1",
                description="Outbound PAT for trust network",
            )

            return True

        except Exception as e:
            self._result.errors.append(f"Policy config error: {e}")
            logger.error(f"Failed to configure policy: {e}")
            return False

    def _get_trust_subnet(self) -> Optional[str]:
        """Get the trust subnet CIDR from deployment."""
        for subnet in self.deployment.virtual_network.subnets:
            if 'trust' in subnet.name and 'branch' not in subnet.name:
                return subnet.prefix
        return None

    def _commit(self, timeout: int) -> CommitResult:
        """Commit configuration changes."""
        try:
            return self._client.commit(
                description="Initial configuration by pa_config_lab",
                sync=True,
                timeout=timeout,
            )
        except Exception as e:
            return CommitResult(
                status=CommitStatus.FAILED,
                message=str(e),
            )

    def _verify(self) -> bool:
        """Verify configuration was applied correctly."""
        try:
            # Get device info to verify connection still works
            info = self._client.get_device_info()
            logger.info(f"Verified: {info.hostname} ({info.sw_version})")

            # Could add more verification here:
            # - Check interfaces are up
            # - Check zones exist
            # - Check policies exist

            return True

        except Exception as e:
            self._result.errors.append(f"Verification error: {e}")
            logger.error(f"Failed to verify configuration: {e}")
            return False


def push_to_firewall(
    firewall_config: CloudFirewall,
    deployment: CloudDeployment,
    management_ip: str,
    credentials: Dict[str, str],
    progress_callback: Callable[[PushPhase, str], None] = None,
) -> PushResult:
    """
    Convenience function to push configuration to a firewall.

    Args:
        firewall_config: CloudFirewall configuration
        deployment: CloudDeployment settings
        management_ip: Firewall management IP
        credentials: Dict with 'username' and 'password'
        progress_callback: Optional progress callback

    Returns:
        PushResult with operation status
    """
    orchestrator = FirewallPushOrchestrator(
        firewall_config=firewall_config,
        deployment=deployment,
        management_ip=management_ip,
        credentials=credentials,
    )
    return orchestrator.push(progress_callback=progress_callback)
