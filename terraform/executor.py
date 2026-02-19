"""
Terraform Executor - Runs Terraform commands.

Provides a Python interface for executing Terraform operations:
- init: Initialize Terraform working directory
- plan: Create execution plan
- apply: Apply changes to infrastructure
- destroy: Destroy managed infrastructure
- output: Get output values
"""

import json
import subprocess
import os
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TerraformStatus(str, Enum):
    """Terraform operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PENDING = "pending"


@dataclass
class TerraformResult:
    """Result of a Terraform operation."""
    status: TerraformStatus
    command: str
    return_code: int
    stdout: str = ""
    stderr: str = ""
    outputs: Dict[str, Any] = field(default_factory=dict)
    changes: Dict[str, int] = field(default_factory=dict)  # add, change, destroy counts
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if operation was successful."""
        return self.status == TerraformStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'status': self.status.value,
            'command': self.command,
            'return_code': self.return_code,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'outputs': self.outputs,
            'changes': self.changes,
            'error_message': self.error_message,
        }


class TerraformExecutor:
    """
    Executes Terraform commands in a working directory.

    Provides methods for init, plan, apply, destroy, and output
    with progress callbacks and output parsing.
    """

    def __init__(
        self,
        working_dir: str,
        terraform_path: Optional[str] = None,
        auto_approve: bool = False,
    ):
        """
        Initialize Terraform executor.

        Args:
            working_dir: Directory containing Terraform files
            terraform_path: Path to terraform binary (default: auto-detect)
            auto_approve: If True, skip interactive approval for apply/destroy
        """
        self.working_dir = Path(working_dir)
        self.terraform_path = terraform_path or self._find_terraform()
        self.auto_approve = auto_approve

        if not self.working_dir.exists():
            raise ValueError(f"Working directory does not exist: {working_dir}")

    def _find_terraform(self) -> str:
        """Find terraform binary in PATH."""
        terraform = shutil.which("terraform")
        if terraform:
            return terraform

        # Check common locations
        common_paths = [
            "/usr/local/bin/terraform",
            "/usr/bin/terraform",
            os.path.expanduser("~/.local/bin/terraform"),
            os.path.expanduser("~/bin/terraform"),
        ]
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        raise FileNotFoundError(
            "Terraform binary not found. Install from https://www.terraform.io/downloads"
        )

    def _run_command(
        self,
        args: List[str],
        capture_output: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[int] = None,
    ) -> TerraformResult:
        """
        Run a terraform command.

        Args:
            args: Command arguments (without 'terraform' prefix)
            capture_output: Whether to capture stdout/stderr
            progress_callback: Optional callback for progress updates
            timeout: Optional timeout in seconds

        Returns:
            TerraformResult with command output
        """
        cmd = [self.terraform_path] + args
        command_str = " ".join(cmd)

        logger.info(f"Running: {command_str}")
        logger.info(f"Working directory: {self.working_dir}")
        logger.debug(f"Terraform binary: {self.terraform_path}")

        try:
            if progress_callback and not capture_output:
                # Stream output for progress
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self.working_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                stdout_lines = []
                for line in iter(process.stdout.readline, ''):
                    stdout_lines.append(line)
                    progress_callback(line.rstrip())

                process.wait(timeout=timeout)
                stdout = ''.join(stdout_lines)
                stderr = ''
                return_code = process.returncode

            else:
                # Capture all output
                result = subprocess.run(
                    cmd,
                    cwd=str(self.working_dir),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                stdout = result.stdout
                stderr = result.stderr
                return_code = result.returncode

            status = TerraformStatus.SUCCESS if return_code == 0 else TerraformStatus.FAILED

            if return_code != 0:
                error_message = stderr or stdout or "Unknown error"
                logger.error(f"Command failed with return code {return_code}: {command_str}")
                if stderr:
                    logger.error(f"STDERR:\n{stderr}")
                if stdout:
                    logger.error(f"STDOUT:\n{stdout}")
                # Log working directory contents for debugging
                try:
                    tf_files = [f.name for f in self.working_dir.iterdir() if f.suffix in ('.tf', '.tfvars', '.json')]
                    logger.debug(f"Terraform files in working directory: {tf_files}")
                except Exception:
                    pass
            else:
                error_message = None
                logger.debug(f"Command succeeded (return code 0)")
                if stdout:
                    # Log first 500 chars of stdout for context
                    preview = stdout[:500] + ('...' if len(stdout) > 500 else '')
                    logger.debug(f"STDOUT preview: {preview}")

            return TerraformResult(
                status=status,
                command=command_str,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                error_message=error_message,
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {command_str}")
            return TerraformResult(
                status=TerraformStatus.FAILED,
                command=command_str,
                return_code=-1,
                error_message=f"Command timed out after {timeout} seconds",
            )
        except FileNotFoundError:
            logger.error(f"Terraform binary not found at: {self.terraform_path}")
            return TerraformResult(
                status=TerraformStatus.FAILED,
                command=command_str,
                return_code=-1,
                error_message=f"Terraform binary not found at: {self.terraform_path}",
            )
        except Exception as e:
            logger.error(f"Command failed with exception: {command_str}: {e}", exc_info=True)
            return TerraformResult(
                status=TerraformStatus.FAILED,
                command=command_str,
                return_code=-1,
                error_message=str(e),
            )

    def version(self) -> TerraformResult:
        """Get Terraform version."""
        return self._run_command(["version", "-json"])

    def cleanup_locks(self) -> bool:
        """
        Clean up any stale lock files before running terraform commands.

        This helps resolve issues where a previous terraform process didn't
        exit cleanly and left lock files behind.

        Returns:
            True if cleanup was successful or no cleanup needed
        """
        import time

        lock_file = self.working_dir / ".terraform.tfstate.lock.info"
        state_file = self.working_dir / "terraform.tfstate"

        # Remove terraform lock info file if it exists
        if lock_file.exists():
            try:
                lock_file.unlink()
                logger.info(f"Removed stale lock file: {lock_file}")
            except Exception as e:
                logger.warning(f"Failed to remove lock file: {e}")

        # Check if state file is accessible (not locked by another process)
        if state_file.exists():
            for attempt in range(3):
                try:
                    # Try to open the file for reading to check if it's locked
                    with open(state_file, 'r') as f:
                        f.read(1)  # Read just 1 byte to test access
                    return True
                except PermissionError:
                    logger.warning(f"State file locked, waiting... (attempt {attempt + 1}/3)")
                    time.sleep(2)
                except Exception as e:
                    logger.debug(f"State file check error: {e}")
                    return True  # File might not exist yet, which is fine

            logger.error("State file remains locked after retries")
            return False

        return True

    def init(
        self,
        upgrade: bool = False,
        backend_config: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> TerraformResult:
        """
        Initialize Terraform working directory.

        Args:
            upgrade: Upgrade modules and plugins
            backend_config: Backend configuration values
            progress_callback: Optional callback for progress updates

        Returns:
            TerraformResult
        """
        args = ["init"]

        if upgrade:
            args.append("-upgrade")

        if backend_config:
            for key, value in backend_config.items():
                args.extend(["-backend-config", f"{key}={value}"])

        # Add -input=false for non-interactive
        args.append("-input=false")

        result = self._run_command(args, capture_output=not progress_callback, progress_callback=progress_callback)
        logger.info(f"Terraform init: {result.status.value}")
        if not result.success:
            logger.error(f"Terraform init failed - stderr: {result.stderr}")
            logger.error(f"Terraform init failed - stdout: {result.stdout}")
        else:
            logger.info(f"Terraform init succeeded in {self.working_dir}")
        return result

    def validate(self) -> TerraformResult:
        """
        Validate Terraform configuration.

        Returns:
            TerraformResult with validation status
        """
        args = ["validate", "-json"]
        result = self._run_command(args)

        if result.stdout:
            try:
                validation = json.loads(result.stdout)
                if not validation.get('valid', False):
                    result.status = TerraformStatus.FAILED
                    diagnostics = validation.get('diagnostics', [])
                    errors = [d.get('summary', '') for d in diagnostics if d.get('severity') == 'error']
                    result.error_message = "; ".join(errors) if errors else "Validation failed"
            except json.JSONDecodeError:
                pass

        logger.info(f"Terraform validate: {result.status.value}")
        return result

    def plan(
        self,
        var_file: Optional[str] = None,
        out: Optional[str] = None,
        destroy: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> TerraformResult:
        """
        Create Terraform execution plan.

        Args:
            var_file: Path to variables file (e.g., terraform.tfvars.json)
            out: Path to save plan file
            destroy: Plan for destruction
            progress_callback: Optional callback for progress updates

        Returns:
            TerraformResult with plan details
        """
        args = ["plan", "-input=false"]

        if var_file:
            args.extend(["-var-file", var_file])

        if out:
            args.extend(["-out", out])

        if destroy:
            args.append("-destroy")

        if var_file:
            logger.info(f"Using var file: {var_file}")

        result = self._run_command(args, capture_output=not progress_callback, progress_callback=progress_callback)

        # Parse plan output for change counts
        if result.success:
            result.changes = self._parse_plan_changes(result.stdout)

        logger.info(f"Terraform plan: {result.status.value}, changes: {result.changes}")
        if not result.success:
            logger.error(f"Terraform plan failed - stderr: {result.stderr}")
            logger.error(f"Terraform plan failed - stdout: {result.stdout}")
        return result

    def apply(
        self,
        plan_file: Optional[str] = None,
        var_file: Optional[str] = None,
        auto_approve: Optional[bool] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[int] = 1800,  # 30 min default
    ) -> TerraformResult:
        """
        Apply Terraform changes.

        Args:
            plan_file: Path to saved plan file
            var_file: Path to variables file
            auto_approve: Override instance auto_approve setting
            progress_callback: Optional callback for progress updates
            timeout: Timeout in seconds (default 30 min)

        Returns:
            TerraformResult with apply status
        """
        args = ["apply", "-input=false"]

        approve = auto_approve if auto_approve is not None else self.auto_approve
        if approve:
            args.append("-auto-approve")

        if plan_file:
            args.append(plan_file)
        elif var_file:
            args.extend(["-var-file", var_file])

        result = self._run_command(
            args,
            capture_output=not progress_callback,
            progress_callback=progress_callback,
            timeout=timeout,
        )

        # Get outputs after successful apply
        if result.success:
            outputs_result = self.output()
            if outputs_result.success:
                result.outputs = outputs_result.outputs

        logger.info(f"Terraform apply: {result.status.value}")
        return result

    def destroy(
        self,
        var_file: Optional[str] = None,
        auto_approve: Optional[bool] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[int] = 1800,
    ) -> TerraformResult:
        """
        Destroy Terraform-managed infrastructure.

        Args:
            var_file: Path to variables file
            auto_approve: Override instance auto_approve setting
            progress_callback: Optional callback for progress updates
            timeout: Timeout in seconds

        Returns:
            TerraformResult
        """
        args = ["destroy", "-input=false"]

        approve = auto_approve if auto_approve is not None else self.auto_approve
        if approve:
            args.append("-auto-approve")

        if var_file:
            args.extend(["-var-file", var_file])

        result = self._run_command(
            args,
            capture_output=not progress_callback,
            progress_callback=progress_callback,
            timeout=timeout,
        )

        logger.info(f"Terraform destroy: {result.status.value}")
        return result

    def output(self, name: Optional[str] = None) -> TerraformResult:
        """
        Get Terraform output values.

        Args:
            name: Specific output name (or None for all)

        Returns:
            TerraformResult with outputs dict
        """
        args = ["output", "-json"]
        if name:
            args.append(name)

        result = self._run_command(args)

        if result.success and result.stdout:
            try:
                outputs_raw = json.loads(result.stdout)
                # Extract values from terraform output format
                if name:
                    result.outputs = {name: outputs_raw}
                else:
                    result.outputs = {
                        k: v.get('value') if isinstance(v, dict) else v
                        for k, v in outputs_raw.items()
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse outputs: {e}")

        return result

    def show(self, plan_file: Optional[str] = None) -> TerraformResult:
        """
        Show Terraform state or plan.

        Args:
            plan_file: Optional plan file to show

        Returns:
            TerraformResult with state/plan details
        """
        args = ["show", "-json"]
        if plan_file:
            args.append(plan_file)

        return self._run_command(args)

    def state_list(self) -> TerraformResult:
        """
        List resources in Terraform state.

        Returns:
            TerraformResult with resource list in stdout
        """
        return self._run_command(["state", "list"])

    def state_rm(self, resource_address: str) -> TerraformResult:
        """
        Remove a resource from Terraform state (does not destroy the actual resource).

        Args:
            resource_address: The resource address to remove (e.g. 'azurerm_storage_account.bootstrap')

        Returns:
            TerraformResult with operation output
        """
        return self._run_command(["state", "rm", resource_address])

    def _parse_plan_changes(self, output: str) -> Dict[str, int]:
        """
        Parse plan output for change counts.

        Args:
            output: Plan stdout

        Returns:
            Dict with 'add', 'change', 'destroy' counts
        """
        changes = {'add': 0, 'change': 0, 'destroy': 0}

        # Look for "Plan: X to add, Y to change, Z to destroy"
        import re
        match = re.search(
            r'Plan:\s*(\d+)\s*to add,\s*(\d+)\s*to change,\s*(\d+)\s*to destroy',
            output
        )
        if match:
            changes['add'] = int(match.group(1))
            changes['change'] = int(match.group(2))
            changes['destroy'] = int(match.group(3))

        return changes

    def is_initialized(self) -> bool:
        """Check if working directory is initialized."""
        terraform_dir = self.working_dir / ".terraform"
        return terraform_dir.is_dir()

    def has_state(self) -> bool:
        """Check if state file exists."""
        state_file = self.working_dir / "terraform.tfstate"
        return state_file.is_file()


def check_terraform_installed() -> bool:
    """
    Check if Terraform is installed and accessible.

    Returns:
        True if terraform is available
    """
    try:
        result = subprocess.run(
            ["terraform", "version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_terraform_version() -> Optional[str]:
    """
    Get installed Terraform version.

    Returns:
        Version string or None if not installed
    """
    try:
        result = subprocess.run(
            ["terraform", "version", "-json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('terraform_version')
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None
