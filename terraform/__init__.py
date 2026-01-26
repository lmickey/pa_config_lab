"""
Terraform integration for POV cloud deployments.

Provides:
- TerraformGenerator: Generates Terraform files from CloudConfig
- TerraformExecutor: Executes Terraform commands (init, plan, apply, destroy)
- BootstrapConfig: Configuration for firewall bootstrap packages
- BootstrapGenerator: Generates init-cfg.txt and bootstrap.xml
- Jinja2 templates for Azure resources
- check_terraform_installed: Utility to verify Terraform is available
"""

import shutil
from pathlib import Path

from .generator import TerraformGenerator
from .executor import TerraformExecutor, TerraformResult
from .bootstrap import BootstrapConfig, BootstrapGenerator, generate_firewall_bootstrap


def check_terraform_installed() -> bool:
    """
    Check if Terraform is installed and available in PATH.

    Returns:
        True if terraform binary is found, False otherwise
    """
    # Check in PATH
    if shutil.which("terraform"):
        return True

    # Check common installation locations
    common_paths = [
        "/usr/local/bin/terraform",
        "/usr/bin/terraform",
        "/opt/homebrew/bin/terraform",
        str(Path.home() / "bin" / "terraform"),
        str(Path.home() / ".local" / "bin" / "terraform"),
        # Windows paths
        "C:\\Program Files\\Terraform\\terraform.exe",
        "C:\\terraform\\terraform.exe",
        str(Path.home() / "AppData" / "Local" / "Programs" / "Terraform" / "terraform.exe"),
    ]

    for path in common_paths:
        if Path(path).exists():
            return True

    return False


def get_terraform_version() -> str:
    """
    Get the installed Terraform version.

    Returns:
        Version string, or "not installed" if not found
    """
    import subprocess

    terraform_path = shutil.which("terraform")
    if not terraform_path:
        return "not installed"

    try:
        result = subprocess.run(
            [terraform_path, "version", "-json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            return data.get("terraform_version", "unknown")
    except Exception:
        pass

    # Fallback to non-JSON version
    try:
        result = subprocess.run(
            [terraform_path, "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Parse first line: "Terraform v1.5.0"
            first_line = result.stdout.strip().split('\n')[0]
            if first_line.startswith("Terraform"):
                return first_line.replace("Terraform ", "")
    except Exception:
        pass

    return "unknown"


__all__ = [
    'TerraformGenerator',
    'TerraformExecutor',
    'TerraformResult',
    'BootstrapConfig',
    'BootstrapGenerator',
    'generate_firewall_bootstrap',
    'check_terraform_installed',
    'get_terraform_version',
]
