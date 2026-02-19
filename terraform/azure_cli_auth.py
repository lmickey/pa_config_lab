"""
Azure CLI Authentication Utilities.

Validates and refreshes Azure CLI authentication tokens
for Terraform operations that rely on the CLI auth chain.

The azurerm Terraform provider defaults to Azure CLI authentication
when no explicit credentials are provided. This module ensures the
CLI session is valid before Terraform runs.
"""

import subprocess
import logging
import json
import shutil
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def check_azure_cli_installed() -> bool:
    """
    Check if Azure CLI (az) is installed and accessible.

    Returns:
        True if az binary is found in PATH
    """
    return shutil.which("az") is not None


def validate_cli_token(
    subscription_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Validate that the Azure CLI has a valid, non-expired token.

    Runs `az account get-access-token` to check if the current
    CLI session can produce a valid token for the given subscription.

    Args:
        subscription_id: Target Azure subscription ID
        tenant_id: Target Azure tenant/directory ID

    Returns:
        Tuple of (is_valid, message).
        is_valid is True if CLI token is valid and usable.
        message contains status info or error details.
    """
    if not check_azure_cli_installed():
        return False, "Azure CLI (az) is not installed or not in PATH"

    cmd = ["az", "account", "get-access-token", "--query", "accessToken", "-o", "tsv"]
    if subscription_id:
        cmd.extend(["--subscription", subscription_id])
    if tenant_id:
        cmd.extend(["--tenant", tenant_id])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.info("Azure CLI token is valid")
            return True, "Azure CLI token is valid"
        else:
            error = result.stderr.strip() or "Unknown error"
            logger.warning(f"Azure CLI token validation failed: {error}")
            return False, error
    except subprocess.TimeoutExpired:
        return False, "Azure CLI token check timed out"
    except FileNotFoundError:
        return False, "Azure CLI (az) binary not found"
    except Exception as e:
        return False, f"Token validation error: {e}"


def login_cli(
    tenant_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Perform interactive Azure CLI login.

    Opens a browser for authentication. This MUST be called
    from the main thread since it requires user interaction.

    Args:
        tenant_id: Target tenant for login
        subscription_id: Subscription to set as default after login

    Returns:
        Tuple of (success, message)
    """
    cmd = ["az", "login"]
    if tenant_id:
        cmd.extend(["--tenant", tenant_id])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 min for user to complete browser login
        )
        if result.returncode != 0:
            error = result.stderr.strip() or "Login failed"
            return False, f"Azure CLI login failed: {error}"

        # If subscription specified, set it as the active subscription
        if subscription_id:
            set_result = subprocess.run(
                ["az", "account", "set", "--subscription", subscription_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if set_result.returncode != 0:
                logger.warning(
                    f"Failed to set subscription {subscription_id}: "
                    f"{set_result.stderr.strip()}"
                )

        return True, "Azure CLI login successful"

    except subprocess.TimeoutExpired:
        return False, "Azure CLI login timed out (2 minutes)"
    except Exception as e:
        return False, f"Azure CLI login error: {e}"
