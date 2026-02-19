"""
Azure CLI Authentication Utilities.

Validates and refreshes Azure CLI authentication tokens
for Terraform operations that rely on the CLI auth chain.

The azurerm Terraform provider defaults to Azure CLI authentication
when no explicit credentials are provided. This module ensures the
CLI session is valid before Terraform runs.
"""

import os
import sys
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Cached path to the az binary once found
_az_path: Optional[str] = None


def _find_azure_cli() -> Optional[str]:
    """
    Find the Azure CLI binary, handling Windows (az.cmd) and Unix (az).

    On Windows, the CLI installs as az.cmd which shutil.which("az") may miss.
    We check multiple names and common install locations.

    Returns:
        Full path to az executable, or None if not found.
    """
    global _az_path
    if _az_path is not None:
        return _az_path

    is_windows = sys.platform == "win32"

    # Names to search in PATH
    names = ["az.cmd", "az.exe", "az"] if is_windows else ["az"]

    for name in names:
        found = shutil.which(name)
        if found:
            logger.info(f"Found Azure CLI at: {found}")
            _az_path = found
            return _az_path

    # Check common install locations on Windows
    if is_windows:
        common_paths = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "Microsoft SDKs" / "Azure" / "CLI2" / "wbin" / "az.cmd",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
            / "Microsoft SDKs" / "Azure" / "CLI2" / "wbin" / "az.cmd",
            Path.home() / "AppData" / "Local" / "Programs" / "Azure CLI" / "az.cmd",
            # Scoop / Chocolatey / winget installs
            Path.home() / "scoop" / "shims" / "az.cmd",
        ]
        for path in common_paths:
            if path.exists():
                logger.info(f"Found Azure CLI at: {path}")
                _az_path = str(path)
                return _az_path
    else:
        # Common Unix locations
        common_paths = [
            "/usr/local/bin/az",
            "/usr/bin/az",
            "/opt/homebrew/bin/az",
            str(Path.home() / "bin" / "az"),
            str(Path.home() / ".local" / "bin" / "az"),
        ]
        for path_str in common_paths:
            if os.path.isfile(path_str) and os.access(path_str, os.X_OK):
                logger.info(f"Found Azure CLI at: {path_str}")
                _az_path = path_str
                return _az_path

    logger.warning("Azure CLI not found in PATH or common install locations")
    return None


def _run_az_command(
    args: list,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """
    Run an Azure CLI command using the discovered az path.

    On Windows, uses shell=True to handle .cmd files properly.

    Args:
        args: Command arguments after 'az' (e.g. ["account", "show"])
        timeout: Timeout in seconds

    Returns:
        subprocess.CompletedProcess result

    Raises:
        FileNotFoundError: If az CLI is not installed
        subprocess.TimeoutExpired: If command exceeds timeout
    """
    az_path = _find_azure_cli()
    if not az_path:
        raise FileNotFoundError("Azure CLI (az) not found")

    cmd = [az_path] + args
    is_windows = sys.platform == "win32"

    logger.debug(f"Running: {' '.join(cmd)}")

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=is_windows,  # Required on Windows for .cmd files
    )


def check_azure_cli_installed() -> bool:
    """
    Check if Azure CLI (az) is installed and accessible.

    Returns:
        True if az binary is found in PATH or common install locations
    """
    found = _find_azure_cli()
    if found:
        logger.debug(f"Azure CLI check: found at {found}")
    else:
        logger.debug("Azure CLI check: not found")
    return found is not None


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

    args = ["account", "get-access-token", "--query", "accessToken", "-o", "tsv"]
    if subscription_id:
        args.extend(["--subscription", subscription_id])
    if tenant_id:
        args.extend(["--tenant", tenant_id])

    logger.info(
        f"Validating CLI token (subscription={subscription_id or 'default'}, "
        f"tenant={tenant_id or 'default'})"
    )

    try:
        result = _run_az_command(args, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            logger.info("Azure CLI token is valid")
            return True, "Azure CLI token is valid"
        else:
            error = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            logger.warning(f"Azure CLI token validation failed (rc={result.returncode}): {error}")
            return False, error
    except FileNotFoundError as e:
        logger.error(f"Azure CLI not found: {e}")
        return False, f"Azure CLI (az) not found: {e}"
    except subprocess.TimeoutExpired:
        logger.warning("Azure CLI token check timed out after 15s")
        return False, "Azure CLI token check timed out"
    except Exception as e:
        logger.error(f"Token validation error: {e}", exc_info=True)
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
    args = ["login"]
    if tenant_id:
        args.extend(["--tenant", tenant_id])

    logger.info(f"Starting Azure CLI login (tenant={tenant_id or 'default'})")

    try:
        result = _run_az_command(args, timeout=120)  # 2 min for browser login

        if result.returncode != 0:
            error = result.stderr.strip() or result.stdout.strip() or "Login failed"
            logger.error(f"Azure CLI login failed (rc={result.returncode}): {error}")
            return False, f"Azure CLI login failed: {error}"

        logger.info("Azure CLI login command succeeded")

        # If subscription specified, set it as the active subscription
        if subscription_id:
            logger.info(f"Setting active subscription: {subscription_id}")
            try:
                set_result = _run_az_command(
                    ["account", "set", "--subscription", subscription_id],
                    timeout=10,
                )
                if set_result.returncode != 0:
                    set_error = set_result.stderr.strip() or set_result.stdout.strip()
                    logger.warning(f"Failed to set subscription: {set_error}")
                else:
                    logger.info("Active subscription set successfully")
            except Exception as e:
                logger.warning(f"Failed to set subscription: {e}")

        return True, "Azure CLI login successful"

    except FileNotFoundError as e:
        logger.error(f"Azure CLI not found for login: {e}")
        return False, f"Azure CLI not found: {e}"
    except subprocess.TimeoutExpired:
        logger.warning("Azure CLI login timed out after 120s")
        return False, "Azure CLI login timed out (2 minutes)"
    except Exception as e:
        logger.error(f"Azure CLI login error: {e}", exc_info=True)
        return False, f"Azure CLI login error: {e}"
