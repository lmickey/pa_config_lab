"""
Deployment Coordinator.

Orchestrates the full deployment workflow:
1. Generate Terraform configuration
2. Execute Terraform (init, plan, apply)
3. Wait for infrastructure to be ready
4. Push configuration to Panorama
5. Push configuration to Firewalls
"""

import logging
import os
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.models.cloud import CloudConfig, CloudDeployment
from terraform import TerraformGenerator, TerraformExecutor, TerraformResult
from firewall.push import FirewallPushOrchestrator, PushResult as FirewallPushResult
from panorama.push import PanoramaPushOrchestrator, PushResult as PanoramaPushResult

logger = logging.getLogger(__name__)


class DeploymentPhase(str, Enum):
    """Deployment phases."""
    INITIALIZING = "initializing"
    GENERATING_TERRAFORM = "generating_terraform"
    TERRAFORM_INIT = "terraform_init"
    TERRAFORM_PLAN = "terraform_plan"
    TERRAFORM_APPLY = "terraform_apply"
    WAITING_FOR_INFRASTRUCTURE = "waiting_for_infrastructure"
    CONFIGURING_PANORAMA = "configuring_panorama"
    CONFIGURING_FIREWALLS = "configuring_firewalls"
    REGISTERING_FIREWALLS = "registering_firewalls"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"


class DeploymentStatus(str, Enum):
    """Deployment status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    status: DeploymentStatus
    phase: DeploymentPhase
    deployment_name: str
    message: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    phases_completed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    terraform_output: Dict[str, Any] = field(default_factory=dict)
    panorama_result: Optional[PanoramaPushResult] = None
    firewall_results: Dict[str, FirewallPushResult] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == DeploymentStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'phase': self.phase.value,
            'deployment_name': self.deployment_name,
            'message': self.message,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'phases_completed': self.phases_completed,
            'errors': self.errors,
            'terraform_output': self.terraform_output,
            'panorama_result': self.panorama_result.to_dict() if self.panorama_result else None,
            'firewall_results': {
                name: result.to_dict()
                for name, result in self.firewall_results.items()
            },
        }


class DeploymentCoordinator:
    """
    Coordinates the full deployment workflow.

    Manages the lifecycle of deploying a POV environment:
    1. Infrastructure provisioning with Terraform
    2. Panorama configuration
    3. Firewall configuration
    4. Validation and verification
    """

    def __init__(
        self,
        config: CloudConfig,
        output_dir: str,
        credentials: Dict[str, str],
        auto_approve: bool = False,
    ):
        """
        Initialize deployment coordinator.

        Args:
            config: CloudConfig with full deployment specification
            output_dir: Directory for Terraform and output files
            credentials: Dict with 'username', 'password', and optionally
                        'panorama_license', 'subscription_id', 'client_id',
                        'client_secret', 'tenant_id'
            auto_approve: Skip confirmation for Terraform apply
        """
        self.config = config
        self.output_dir = output_dir
        self.credentials = credentials
        self.auto_approve = auto_approve

        self._result: Optional[DeploymentResult] = None
        self._progress_callback: Optional[Callable[[DeploymentPhase, str], None]] = None
        self._terraform_executor: Optional[TerraformExecutor] = None

    def deploy(
        self,
        skip_terraform: bool = False,
        terraform_output: Dict[str, Any] = None,
        parallel_firewalls: bool = True,
        progress_callback: Callable[[DeploymentPhase, str], None] = None,
    ) -> DeploymentResult:
        """
        Execute the full deployment.

        Args:
            skip_terraform: Skip Terraform phases (use existing infrastructure)
            terraform_output: Pre-existing Terraform output (if skip_terraform)
            parallel_firewalls: Configure firewalls in parallel
            progress_callback: Optional callback for progress updates

        Returns:
            DeploymentResult with deployment status
        """
        self._progress_callback = progress_callback
        deployment_name = self.config.deployment.name if self.config.deployment else "deployment"

        self._result = DeploymentResult(
            status=DeploymentStatus.IN_PROGRESS,
            phase=DeploymentPhase.INITIALIZING,
            deployment_name=deployment_name,
            started_at=datetime.utcnow().isoformat(),
        )

        try:
            # Phase 1: Initialize
            self._update_phase(DeploymentPhase.INITIALIZING, "Initializing deployment")

            if not skip_terraform:
                # Phase 2: Generate Terraform
                self._update_phase(
                    DeploymentPhase.GENERATING_TERRAFORM,
                    "Generating Terraform configuration"
                )
                if not self._generate_terraform():
                    return self._fail("Failed to generate Terraform configuration")

                # Phase 3: Terraform init
                self._update_phase(DeploymentPhase.TERRAFORM_INIT, "Running terraform init")
                if not self._terraform_init():
                    return self._fail("Terraform init failed")

                # Phase 4: Terraform plan
                self._update_phase(DeploymentPhase.TERRAFORM_PLAN, "Running terraform plan")
                if not self._terraform_plan():
                    return self._fail("Terraform plan failed")

                # Phase 5: Terraform apply
                self._update_phase(DeploymentPhase.TERRAFORM_APPLY, "Running terraform apply")
                if not self._terraform_apply():
                    return self._fail("Terraform apply failed")

                # Get Terraform output
                self._result.terraform_output = self._get_terraform_output()
            else:
                # Use provided output
                if terraform_output:
                    self._result.terraform_output = terraform_output
                else:
                    return self._fail("skip_terraform requires terraform_output")

            # Phase 6: Wait for infrastructure
            self._update_phase(
                DeploymentPhase.WAITING_FOR_INFRASTRUCTURE,
                "Waiting for infrastructure to be ready"
            )
            # Infrastructure readiness is handled by push orchestrators

            # Phase 7: Configure Panorama (if present)
            if self.config.panorama:
                self._update_phase(
                    DeploymentPhase.CONFIGURING_PANORAMA,
                    "Configuring Panorama"
                )
                if not self._configure_panorama():
                    # Panorama failure is not fatal if firewalls can work standalone
                    self._result.errors.append("Panorama configuration failed")

            # Phase 8: Configure Firewalls
            if self.config.firewalls:
                self._update_phase(
                    DeploymentPhase.CONFIGURING_FIREWALLS,
                    f"Configuring {len(self.config.firewalls)} firewall(s)"
                )
                if not self._configure_firewalls(parallel=parallel_firewalls):
                    # Check if all firewalls failed
                    all_failed = all(
                        not result.success
                        for result in self._result.firewall_results.values()
                    )
                    if all_failed:
                        return self._fail("All firewall configurations failed")
                    else:
                        self._result.status = DeploymentStatus.PARTIAL
                        self._result.errors.append("Some firewall configurations failed")

            # Phase 9: Register firewalls with Panorama (if applicable)
            if self.config.panorama and self.config.firewalls:
                self._update_phase(
                    DeploymentPhase.REGISTERING_FIREWALLS,
                    "Registering firewalls with Panorama"
                )
                self._register_firewalls_with_panorama()

            # Phase 10: Verify
            self._update_phase(DeploymentPhase.VERIFYING, "Verifying deployment")
            self._verify()

            # Success (or partial)
            if self._result.status == DeploymentStatus.IN_PROGRESS:
                self._result.status = DeploymentStatus.SUCCESS

            self._update_phase(DeploymentPhase.COMPLETE, "Deployment complete")
            self._result.completed_at = datetime.utcnow().isoformat()
            self._result.message = self._generate_summary()

            return self._result

        except Exception as e:
            logger.exception(f"Deployment failed with unexpected error: {e}")
            return self._fail(f"Unexpected error: {e}")

    def destroy(self) -> DeploymentResult:
        """
        Destroy the deployed infrastructure.

        Returns:
            DeploymentResult with destruction status
        """
        deployment_name = self.config.deployment.name if self.config.deployment else "deployment"

        self._result = DeploymentResult(
            status=DeploymentStatus.IN_PROGRESS,
            phase=DeploymentPhase.INITIALIZING,
            deployment_name=deployment_name,
            started_at=datetime.utcnow().isoformat(),
        )

        try:
            terraform_dir = os.path.join(self.output_dir, "terraform")
            if not os.path.exists(terraform_dir):
                return self._fail("Terraform directory not found")

            self._terraform_executor = TerraformExecutor(terraform_dir)

            result = self._terraform_executor.destroy(auto_approve=True)

            if result.success:
                self._result.status = DeploymentStatus.SUCCESS
                self._result.message = "Infrastructure destroyed successfully"
            else:
                return self._fail(f"Terraform destroy failed: {result.error}")

            self._result.completed_at = datetime.utcnow().isoformat()
            return self._result

        except Exception as e:
            logger.exception(f"Destroy failed: {e}")
            return self._fail(f"Destroy failed: {e}")

    def _update_phase(self, phase: DeploymentPhase, message: str):
        """Update current phase and notify callback."""
        self._result.phase = phase
        self._result.phases_completed.append(phase.value)
        logger.info(f"[Deployment] {message}")

        if self._progress_callback:
            self._progress_callback(phase, message)

    def _fail(self, message: str) -> DeploymentResult:
        """Mark deployment as failed."""
        self._result.status = DeploymentStatus.FAILED
        self._result.phase = DeploymentPhase.FAILED
        self._result.message = message
        self._result.errors.append(message)
        self._result.completed_at = datetime.utcnow().isoformat()
        logger.error(f"[Deployment] Failed: {message}")
        return self._result

    def _generate_terraform(self) -> bool:
        """Generate Terraform configuration files."""
        try:
            generator = TerraformGenerator(
                config=self.config,
                output_dir=self.output_dir,
            )
            result = generator.generate()

            terraform_dir = os.path.join(self.output_dir, "terraform")
            self._terraform_executor = TerraformExecutor(terraform_dir)

            return len(result.get('files', [])) > 0

        except Exception as e:
            self._result.errors.append(f"Terraform generation error: {e}")
            logger.error(f"Failed to generate Terraform: {e}")
            return False

    def _terraform_init(self) -> bool:
        """Run terraform init."""
        try:
            result = self._terraform_executor.init()
            if not result.success:
                self._result.errors.append(f"Terraform init error: {result.error}")
            return result.success
        except Exception as e:
            self._result.errors.append(f"Terraform init error: {e}")
            return False

    def _terraform_plan(self) -> bool:
        """Run terraform plan."""
        try:
            # Create tfvars from credentials
            var_file = self._create_tfvars()

            result = self._terraform_executor.plan(var_file=var_file)
            if not result.success:
                self._result.errors.append(f"Terraform plan error: {result.error}")
            return result.success
        except Exception as e:
            self._result.errors.append(f"Terraform plan error: {e}")
            return False

    def _terraform_apply(self) -> bool:
        """Run terraform apply."""
        try:
            var_file = self._create_tfvars()

            result = self._terraform_executor.apply(
                var_file=var_file,
                auto_approve=self.auto_approve,
            )
            if not result.success:
                self._result.errors.append(f"Terraform apply error: {result.error}")
            return result.success
        except Exception as e:
            self._result.errors.append(f"Terraform apply error: {e}")
            return False

    def _create_tfvars(self) -> Optional[str]:
        """Create terraform.tfvars from credentials."""
        try:
            tfvars_path = os.path.join(
                self.output_dir, "terraform", "credentials.tfvars"
            )

            lines = []
            if 'admin_password' in self.credentials:
                lines.append(f'admin_password = "{self.credentials["admin_password"]}"')
            if 'subscription_id' in self.credentials:
                lines.append(f'subscription_id = "{self.credentials["subscription_id"]}"')

            if lines:
                with open(tfvars_path, 'w') as f:
                    f.write('\n'.join(lines))
                return tfvars_path
            return None

        except Exception as e:
            logger.error(f"Failed to create tfvars: {e}")
            return None

    def _get_terraform_output(self) -> Dict[str, Any]:
        """Get Terraform output values."""
        try:
            result = self._terraform_executor.output()
            if result.success and result.output:
                return result.output
            return {}
        except Exception as e:
            logger.error(f"Failed to get Terraform output: {e}")
            return {}

    def _configure_panorama(self) -> bool:
        """Configure Panorama using push orchestrator."""
        try:
            panorama_ip = self._result.terraform_output.get(
                'panorama_management_ip',
                self._result.terraform_output.get('panorama_ip')
            )

            if not panorama_ip:
                self._result.errors.append("Panorama IP not found in Terraform output")
                return False

            orchestrator = PanoramaPushOrchestrator(
                panorama_config=self.config.panorama,
                deployment=self.config.deployment,
                management_ip=panorama_ip,
                credentials={
                    'username': self.credentials.get('username', 'admin'),
                    'password': self.credentials.get('password', self.credentials.get('admin_password')),
                },
                license_auth_code=self.credentials.get('panorama_license'),
            )

            result = orchestrator.push(
                progress_callback=lambda phase, msg: logger.info(f"[Panorama] {msg}")
            )
            self._result.panorama_result = result

            return result.success

        except Exception as e:
            self._result.errors.append(f"Panorama configuration error: {e}")
            logger.error(f"Failed to configure Panorama: {e}")
            return False

    def _configure_firewalls(self, parallel: bool = True) -> bool:
        """Configure firewalls using push orchestrators."""
        try:
            all_success = True

            # Get firewall IPs from Terraform output
            firewall_ips = self._result.terraform_output.get('firewall_management_ips', {})

            if parallel and len(self.config.firewalls) > 1:
                # Configure firewalls in parallel
                with ThreadPoolExecutor(max_workers=min(5, len(self.config.firewalls))) as executor:
                    futures = {}

                    for fw in self.config.firewalls:
                        fw_ip = firewall_ips.get(fw.name)
                        if not fw_ip:
                            # Try alternative naming
                            fw_ip = self._result.terraform_output.get(f'{fw.name}_management_ip')

                        if fw_ip:
                            future = executor.submit(
                                self._configure_single_firewall,
                                fw,
                                fw_ip,
                            )
                            futures[future] = fw.name
                        else:
                            self._result.errors.append(f"No IP found for firewall {fw.name}")
                            all_success = False

                    for future in as_completed(futures):
                        fw_name = futures[future]
                        try:
                            result = future.result()
                            self._result.firewall_results[fw_name] = result
                            if not result.success:
                                all_success = False
                        except Exception as e:
                            self._result.errors.append(f"Firewall {fw_name} error: {e}")
                            all_success = False
            else:
                # Configure firewalls sequentially
                for fw in self.config.firewalls:
                    fw_ip = firewall_ips.get(fw.name)
                    if not fw_ip:
                        fw_ip = self._result.terraform_output.get(f'{fw.name}_management_ip')

                    if fw_ip:
                        result = self._configure_single_firewall(fw, fw_ip)
                        self._result.firewall_results[fw.name] = result
                        if not result.success:
                            all_success = False
                    else:
                        self._result.errors.append(f"No IP found for firewall {fw.name}")
                        all_success = False

            return all_success

        except Exception as e:
            self._result.errors.append(f"Firewall configuration error: {e}")
            logger.error(f"Failed to configure firewalls: {e}")
            return False

    def _configure_single_firewall(self, firewall_config, management_ip: str) -> FirewallPushResult:
        """Configure a single firewall."""
        orchestrator = FirewallPushOrchestrator(
            firewall_config=firewall_config,
            deployment=self.config.deployment,
            management_ip=management_ip,
            credentials={
                'username': self.credentials.get('username', 'admin'),
                'password': self.credentials.get('password', self.credentials.get('admin_password')),
            },
        )

        return orchestrator.push(
            progress_callback=lambda phase, msg: logger.info(f"[{firewall_config.name}] {msg}")
        )

    def _register_firewalls_with_panorama(self) -> bool:
        """Register firewalls with Panorama (placeholder for future implementation)."""
        # This would use the Panorama API to:
        # 1. Add firewalls as managed devices
        # 2. Assign to device groups
        # 3. Assign template stacks
        # 4. Push policies to devices

        logger.info("Firewall registration with Panorama - not yet implemented")
        return True

    def _verify(self) -> bool:
        """Verify deployment state."""
        try:
            verified = True

            # Check Panorama result
            if self._result.panorama_result and not self._result.panorama_result.success:
                verified = False

            # Check firewall results
            for name, result in self._result.firewall_results.items():
                if not result.success:
                    verified = False

            return verified

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False

    def _generate_summary(self) -> str:
        """Generate deployment summary message."""
        lines = [f"Deployment '{self._result.deployment_name}' completed"]

        if self._result.terraform_output:
            lines.append(f"  Infrastructure provisioned successfully")

        if self._result.panorama_result:
            status = "successfully" if self._result.panorama_result.success else "with errors"
            lines.append(f"  Panorama configured {status}")

        if self._result.firewall_results:
            success_count = sum(1 for r in self._result.firewall_results.values() if r.success)
            total = len(self._result.firewall_results)
            lines.append(f"  Firewalls configured: {success_count}/{total}")

        if self._result.errors:
            lines.append(f"  Errors: {len(self._result.errors)}")

        return '\n'.join(lines)


def deploy_pov(
    config: CloudConfig,
    output_dir: str,
    credentials: Dict[str, str],
    auto_approve: bool = False,
    progress_callback: Callable[[DeploymentPhase, str], None] = None,
) -> DeploymentResult:
    """
    Convenience function to deploy a POV environment.

    Args:
        config: CloudConfig with deployment specification
        output_dir: Directory for output files
        credentials: Authentication credentials
        auto_approve: Skip Terraform confirmation
        progress_callback: Optional progress callback

    Returns:
        DeploymentResult with deployment status
    """
    coordinator = DeploymentCoordinator(
        config=config,
        output_dir=output_dir,
        credentials=credentials,
        auto_approve=auto_approve,
    )
    return coordinator.deploy(progress_callback=progress_callback)
