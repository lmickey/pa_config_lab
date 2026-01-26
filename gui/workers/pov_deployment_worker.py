"""
POV Deployment Workers.

Background workers for POV deployment operations:
- Terraform generation and execution
- Firewall configuration push
- Panorama configuration push
- Full deployment coordination
"""

import logging
import os
from typing import Dict, Any, Optional, Callable
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class TerraformWorker(QThread):
    """Background worker for Terraform operations."""

    progress = pyqtSignal(str, int)  # message, percentage
    phase_changed = pyqtSignal(str)  # phase name
    finished = pyqtSignal(bool, str, dict)  # success, message, outputs
    error = pyqtSignal(str)
    log_message = pyqtSignal(str)  # detailed log output

    def __init__(
        self,
        operation: str,
        config: Dict[str, Any],
        output_dir: str,
        credentials: Optional[Dict[str, str]] = None,
        auto_approve: bool = False,
    ):
        """
        Initialize Terraform worker.

        Args:
            operation: Operation to perform ('generate', 'init', 'plan', 'apply', 'destroy')
            config: CloudConfig dict or object
            output_dir: Directory for Terraform files
            credentials: Optional credentials dict
            auto_approve: Auto-approve Terraform apply
        """
        super().__init__()
        self.operation = operation
        self.config = config
        self.output_dir = output_dir
        self.credentials = credentials or {}
        self.auto_approve = auto_approve
        self._cancelled = False

    def cancel(self):
        """Cancel the operation."""
        self._cancelled = True

    def run(self):
        """Run the Terraform operation."""
        try:
            if self.operation == "generate":
                self._generate()
            elif self.operation == "init":
                self._init()
            elif self.operation == "plan":
                self._plan()
            elif self.operation == "apply":
                self._apply()
            elif self.operation == "destroy":
                self._destroy()
            elif self.operation == "full":
                self._full_deployment()
            else:
                self.error.emit(f"Unknown operation: {self.operation}")
                self.finished.emit(False, f"Unknown operation: {self.operation}", {})

        except Exception as e:
            logger.exception(f"Terraform operation failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(False, str(e), {})

    def _generate(self):
        """Generate Terraform configuration."""
        from terraform import TerraformGenerator

        self.phase_changed.emit("generating")
        self.progress.emit("Generating Terraform configuration...", 10)

        try:
            generator = TerraformGenerator(
                cloud_config=self.config,
                output_dir=self.output_dir,
            )

            self.progress.emit("Creating Terraform files...", 30)
            result = generator.generate()

            self.progress.emit("Generating bootstrap configuration...", 60)

            files_created = result.get('files', [])
            self.log_message.emit(f"Generated {len(files_created)} Terraform files")
            for f in files_created:
                self.log_message.emit(f"  - {f}")

            self.progress.emit("Terraform configuration ready", 100)
            self.finished.emit(True, f"Generated {len(files_created)} files", result)

        except Exception as e:
            self.error.emit(f"Generation failed: {e}")
            self.finished.emit(False, str(e), {})

    def _init(self):
        """Run terraform init."""
        from terraform import TerraformExecutor, check_terraform_installed

        self.phase_changed.emit("initializing")
        self.progress.emit("Checking Terraform installation...", 10)

        if not check_terraform_installed():
            self.error.emit("Terraform is not installed or not in PATH")
            self.finished.emit(False, "Terraform not found", {})
            return

        terraform_dir = os.path.join(self.output_dir, "terraform")
        executor = TerraformExecutor(terraform_dir)

        self.progress.emit("Running terraform init...", 30)
        result = executor.init()

        if result.success:
            self.progress.emit("Terraform initialized", 100)
            self.finished.emit(True, "Terraform initialized successfully", {})
        else:
            self.error.emit(result.error_message or "Init failed")
            self.finished.emit(False, result.error_message or "Init failed", {})

    def _plan(self):
        """Run terraform plan."""
        from terraform import TerraformExecutor

        self.phase_changed.emit("planning")
        self.progress.emit("Running terraform plan...", 20)

        terraform_dir = os.path.join(self.output_dir, "terraform")
        executor = TerraformExecutor(terraform_dir)

        # Create var file if credentials provided
        var_file = self._create_var_file()

        result = executor.plan(var_file=var_file)

        if result.success:
            self.progress.emit("Plan complete", 100)
            self.log_message.emit(result.stdout or "")
            self.finished.emit(True, "Plan completed successfully", {})
        else:
            self.error.emit(result.error_message or "Plan failed")
            self.finished.emit(False, result.error_message or "Plan failed", {})

    def _apply(self):
        """Run terraform apply."""
        from terraform import TerraformExecutor

        self.phase_changed.emit("applying")
        self.progress.emit("Running terraform apply...", 10)

        terraform_dir = os.path.join(self.output_dir, "terraform")
        executor = TerraformExecutor(terraform_dir)

        var_file = self._create_var_file()

        self.progress.emit("Deploying infrastructure...", 30)
        result = executor.apply(var_file=var_file, auto_approve=self.auto_approve)

        if self._cancelled:
            self.finished.emit(False, "Operation cancelled", {})
            return

        if result.success:
            self.progress.emit("Getting outputs...", 90)
            output_result = executor.output()
            outputs = output_result.outputs if output_result.success else {}

            self.progress.emit("Deployment complete", 100)
            self.finished.emit(True, "Infrastructure deployed successfully", outputs)
        else:
            self.error.emit(result.error_message or "Apply failed")
            self.finished.emit(False, result.error_message or "Apply failed", {})

    def _destroy(self):
        """Run terraform destroy."""
        from terraform import TerraformExecutor

        self.phase_changed.emit("destroying")
        self.progress.emit("Running terraform destroy...", 10)

        terraform_dir = os.path.join(self.output_dir, "terraform")
        executor = TerraformExecutor(terraform_dir)

        result = executor.destroy(auto_approve=True)

        if result.success:
            self.progress.emit("Infrastructure destroyed", 100)
            self.finished.emit(True, "Infrastructure destroyed successfully", {})
        else:
            self.error.emit(result.error_message or "Destroy failed")
            self.finished.emit(False, result.error_message or "Destroy failed", {})

    def _full_deployment(self):
        """Run full Terraform deployment (generate, init, plan, apply)."""
        # Generate
        self.phase_changed.emit("generating")
        self.progress.emit("Generating Terraform configuration...", 5)
        self._generate_only()

        if self._cancelled:
            return

        # Init
        self.phase_changed.emit("initializing")
        self.progress.emit("Initializing Terraform...", 25)
        if not self._init_only():
            return

        if self._cancelled:
            return

        # Plan
        self.phase_changed.emit("planning")
        self.progress.emit("Planning deployment...", 45)
        if not self._plan_only():
            return

        if self._cancelled:
            return

        # Apply
        self.phase_changed.emit("applying")
        self.progress.emit("Deploying infrastructure...", 65)
        self._apply()

    def _generate_only(self) -> bool:
        """Generate Terraform config without emitting finished."""
        from terraform import TerraformGenerator

        try:
            generator = TerraformGenerator(
                cloud_config=self.config,
                output_dir=self.output_dir,
            )
            generator.generate()
            return True
        except Exception as e:
            self.error.emit(f"Generation failed: {e}")
            self.finished.emit(False, str(e), {})
            return False

    def _init_only(self) -> bool:
        """Run init without emitting finished."""
        from terraform import TerraformExecutor, check_terraform_installed

        if not check_terraform_installed():
            self.error.emit("Terraform not installed")
            self.finished.emit(False, "Terraform not found", {})
            return False

        terraform_dir = os.path.join(self.output_dir, "terraform")
        executor = TerraformExecutor(terraform_dir)
        result = executor.init()

        if not result.success:
            self.error.emit(result.error_message or "Init failed")
            self.finished.emit(False, result.error_message or "Init failed", {})
            return False

        return True

    def _plan_only(self) -> bool:
        """Run plan without emitting finished."""
        from terraform import TerraformExecutor

        terraform_dir = os.path.join(self.output_dir, "terraform")
        executor = TerraformExecutor(terraform_dir)
        var_file = self._create_var_file()

        result = executor.plan(var_file=var_file)

        if not result.success:
            self.error.emit(result.error_message or "Plan failed")
            self.finished.emit(False, result.error_message or "Plan failed", {})
            return False

        return True

    def _create_var_file(self) -> Optional[str]:
        """Create terraform.tfvars from credentials."""
        if not self.credentials:
            return None

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


class DeviceConfigWorker(QThread):
    """Background worker for device configuration (firewall/panorama)."""

    progress = pyqtSignal(str, int)  # message, percentage
    phase_changed = pyqtSignal(str)  # phase name
    finished = pyqtSignal(bool, str, dict)  # success, message, result
    error = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(
        self,
        device_type: str,  # 'firewall' or 'panorama'
        config: Dict[str, Any],
        deployment: Dict[str, Any],
        management_ip: str,
        credentials: Dict[str, str],
        license_auth_code: Optional[str] = None,
    ):
        """
        Initialize device configuration worker.

        Args:
            device_type: Type of device ('firewall' or 'panorama')
            config: Device configuration dict
            deployment: Deployment configuration dict
            management_ip: Device management IP
            credentials: Auth credentials
            license_auth_code: Optional license code (Panorama)
        """
        super().__init__()
        self.device_type = device_type
        self.config = config
        self.deployment = deployment
        self.management_ip = management_ip
        self.credentials = credentials
        self.license_auth_code = license_auth_code
        self._cancelled = False

    def cancel(self):
        """Cancel the operation."""
        self._cancelled = True

    def run(self):
        """Run device configuration."""
        try:
            if self.device_type == "firewall":
                self._configure_firewall()
            elif self.device_type == "panorama":
                self._configure_panorama()
            else:
                self.error.emit(f"Unknown device type: {self.device_type}")
                self.finished.emit(False, f"Unknown device type", {})

        except Exception as e:
            logger.exception(f"Device configuration failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(False, str(e), {})

    def _configure_firewall(self):
        """Configure firewall using push orchestrator."""
        from firewall.push import FirewallPushOrchestrator

        self.phase_changed.emit("firewall")
        self.progress.emit("Connecting to firewall...", 10)

        def progress_callback(phase, message):
            self.log_message.emit(f"[{phase.value}] {message}")

        # Create mock config object if dict
        fw_config = self._create_firewall_config(self.config)

        orchestrator = FirewallPushOrchestrator(
            firewall_config=fw_config,
            deployment=self._create_deployment_config(self.deployment),
            management_ip=self.management_ip,
            credentials=self.credentials,
        )

        self.progress.emit("Pushing configuration...", 30)
        result = orchestrator.push(progress_callback=progress_callback)

        if self._cancelled:
            self.finished.emit(False, "Operation cancelled", {})
            return

        if result.success:
            self.progress.emit("Firewall configured", 100)
            self.finished.emit(True, "Firewall configured successfully", result.to_dict())
        else:
            self.error.emit(result.message)
            self.finished.emit(False, result.message, result.to_dict())

    def _configure_panorama(self):
        """Configure Panorama using push orchestrator."""
        from panorama.push import PanoramaPushOrchestrator

        self.phase_changed.emit("panorama")
        self.progress.emit("Connecting to Panorama...", 10)

        def progress_callback(phase, message):
            self.log_message.emit(f"[{phase.value}] {message}")

        pano_config = self._create_panorama_config(self.config)

        orchestrator = PanoramaPushOrchestrator(
            panorama_config=pano_config,
            deployment=self._create_deployment_config(self.deployment),
            management_ip=self.management_ip,
            credentials=self.credentials,
            license_auth_code=self.license_auth_code,
        )

        self.progress.emit("Pushing configuration...", 30)
        result = orchestrator.push(progress_callback=progress_callback)

        if self._cancelled:
            self.finished.emit(False, "Operation cancelled", {})
            return

        if result.success:
            self.progress.emit("Panorama configured", 100)
            self.finished.emit(True, "Panorama configured successfully", result.to_dict())
        else:
            self.error.emit(result.message)
            self.finished.emit(False, result.message, result.to_dict())

    def _create_firewall_config(self, config_dict: Dict[str, Any]):
        """Create firewall config object from dict."""
        from dataclasses import dataclass, field
        from typing import List

        @dataclass
        class DeviceSettings:
            hostname: str = ""
            dns_primary: str = "8.8.8.8"
            dns_secondary: str = "8.8.4.4"
            ntp_primary: str = "time.google.com"
            ntp_secondary: str = ""

        @dataclass
        class Interface:
            name: str = ""

        @dataclass
        class FirewallConfig:
            name: str = ""
            device: DeviceSettings = None
            interfaces: List[Interface] = None

            def __post_init__(self):
                if self.device is None:
                    self.device = DeviceSettings()
                if self.interfaces is None:
                    self.interfaces = []

        # Parse config dict
        device_dict = config_dict.get('device', {})
        device = DeviceSettings(
            hostname=device_dict.get('hostname', config_dict.get('name', '')),
            dns_primary=device_dict.get('dns_primary', '8.8.8.8'),
            dns_secondary=device_dict.get('dns_secondary', '8.8.4.4'),
            ntp_primary=device_dict.get('ntp_primary', 'time.google.com'),
            ntp_secondary=device_dict.get('ntp_secondary', ''),
        )

        interfaces = [
            Interface(name=iface.get('name', f'ethernet1/{i+1}'))
            for i, iface in enumerate(config_dict.get('interfaces', []))
        ]

        if not interfaces:
            interfaces = [Interface(name="ethernet1/1"), Interface(name="ethernet1/2")]

        return FirewallConfig(
            name=config_dict.get('name', 'firewall'),
            device=device,
            interfaces=interfaces,
        )

    def _create_panorama_config(self, config_dict: Dict[str, Any]):
        """Create Panorama config object from dict."""
        from dataclasses import dataclass, field
        from typing import List

        @dataclass
        class DeviceSettings:
            hostname: str = ""
            dns_primary: str = "8.8.8.8"
            dns_secondary: str = "8.8.4.4"
            ntp_primary: str = "time.google.com"
            ntp_secondary: str = ""

        @dataclass
        class PanoramaConfig:
            name: str = ""
            device: DeviceSettings = None
            templates: List[str] = None
            device_groups: List[str] = None
            plugins: List[str] = None

            def __post_init__(self):
                if self.device is None:
                    self.device = DeviceSettings()
                if self.templates is None:
                    self.templates = []
                if self.device_groups is None:
                    self.device_groups = []
                if self.plugins is None:
                    self.plugins = []

        device_dict = config_dict.get('device', {})
        device = DeviceSettings(
            hostname=device_dict.get('hostname', config_dict.get('name', 'panorama')),
            dns_primary=device_dict.get('dns_primary', '8.8.8.8'),
            dns_secondary=device_dict.get('dns_secondary', '8.8.4.4'),
            ntp_primary=device_dict.get('ntp_primary', 'time.google.com'),
            ntp_secondary=device_dict.get('ntp_secondary', ''),
        )

        return PanoramaConfig(
            name=config_dict.get('name', 'panorama'),
            device=device,
            templates=config_dict.get('templates', []),
            device_groups=config_dict.get('device_groups', []),
            plugins=config_dict.get('plugins', []),
        )

    def _create_deployment_config(self, deployment_dict: Dict[str, Any]):
        """Create deployment config object from dict."""
        from dataclasses import dataclass, field
        from typing import List

        @dataclass
        class Subnet:
            name: str
            prefix: str

        @dataclass
        class VirtualNetwork:
            subnets: List[Subnet] = None

            def __post_init__(self):
                if self.subnets is None:
                    self.subnets = []

        @dataclass
        class Deployment:
            name: str = ""
            virtual_network: VirtualNetwork = None

            def __post_init__(self):
                if self.virtual_network is None:
                    self.virtual_network = VirtualNetwork()

        subnets = [
            Subnet(name=s.get('name', ''), prefix=s.get('prefix', ''))
            for s in deployment_dict.get('virtual_network', {}).get('subnets', [])
        ]

        if not subnets:
            subnets = [
                Subnet(name='trust', prefix='10.100.2.0/24'),
                Subnet(name='untrust', prefix='10.100.1.0/24'),
            ]

        return Deployment(
            name=deployment_dict.get('name', 'deployment'),
            virtual_network=VirtualNetwork(subnets=subnets),
        )


class FullDeploymentWorker(QThread):
    """Background worker for full POV deployment."""

    progress = pyqtSignal(str, int)  # message, percentage
    phase_changed = pyqtSignal(str)  # phase name
    finished = pyqtSignal(bool, str, dict)  # success, message, result
    error = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(
        self,
        config: Dict[str, Any],
        output_dir: str,
        credentials: Dict[str, str],
        skip_terraform: bool = False,
        terraform_outputs: Optional[Dict[str, Any]] = None,
        auto_approve: bool = False,
    ):
        """
        Initialize full deployment worker.

        Args:
            config: Full CloudConfig dict
            output_dir: Output directory for files
            credentials: All credentials
            skip_terraform: Skip Terraform phases
            terraform_outputs: Pre-existing Terraform outputs
            auto_approve: Auto-approve Terraform
        """
        super().__init__()
        self.config = config
        self.output_dir = output_dir
        self.credentials = credentials
        self.skip_terraform = skip_terraform
        self.terraform_outputs = terraform_outputs
        self.auto_approve = auto_approve
        self._cancelled = False

    def cancel(self):
        """Cancel the deployment."""
        self._cancelled = True

    def run(self):
        """Run full deployment."""
        try:
            from deployment import DeploymentCoordinator

            def progress_callback(phase, message):
                self.phase_changed.emit(phase.value)
                self.log_message.emit(f"[{phase.value}] {message}")

            coordinator = DeploymentCoordinator(
                config=self.config,
                output_dir=self.output_dir,
                credentials=self.credentials,
                auto_approve=self.auto_approve,
            )

            self.progress.emit("Starting deployment...", 5)

            result = coordinator.deploy(
                skip_terraform=self.skip_terraform,
                terraform_output=self.terraform_outputs,
                progress_callback=progress_callback,
            )

            if self._cancelled:
                self.finished.emit(False, "Deployment cancelled", {})
                return

            if result.success:
                self.progress.emit("Deployment complete", 100)
                self.finished.emit(True, result.message, result.to_dict())
            else:
                self.error.emit(result.message)
                self.finished.emit(False, result.message, result.to_dict())

        except Exception as e:
            logger.exception(f"Full deployment failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(False, str(e), {})
