"""
Backward compatibility layer for pickle-based configuration files.

This module provides functions to load and convert legacy pickle-based
configuration files to the new JSON format.
"""

import pickle
import os
import json
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import getpass

from .json_storage import derive_key, save_config_json
from ..schema.config_schema_v2 import create_empty_config_v2


def load_pickle_config(
    file_path: str, cipher: Optional[Fernet] = None
) -> Optional[Dict[str, Any]]:
    """
    Load a legacy pickle-based configuration file.

    Args:
        file_path: Path to pickle configuration file
        cipher: Optional Fernet cipher for decryption

    Returns:
        Configuration dictionary or None if error
    """
    try:
        if cipher is None:
            password = getpass.getpass("Enter password for decryption: ")
            cipher = derive_key(password)

        # Read encrypted file
        with open(file_path, "rb") as f:
            encrypted_data = f.read()

        # Decrypt
        decrypted_data = cipher.decrypt(encrypted_data)

        # Load from pickle
        config = pickle.loads(decrypted_data)

        return config

    except FileNotFoundError:
        print(f"Configuration file not found: {file_path}")
        return None
    except Exception as e:
        print(f"Error loading pickle configuration: {e}")
        return None


def convert_pickle_to_json(
    pickle_file_path: str,
    json_file_path: Optional[str] = None,
    cipher: Optional[Fernet] = None,
    preserve_legacy: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Convert a pickle-based configuration to JSON format.

    Args:
        pickle_file_path: Path to source pickle file
        json_file_path: Path to destination JSON file (auto-generated if None)
        cipher: Optional Fernet cipher (will prompt if None)
        preserve_legacy: Whether to preserve fwData/paData in v2 format

    Returns:
        Converted configuration dictionary or None if error
    """
    # Load pickle config
    pickle_config = load_pickle_config(pickle_file_path, cipher)
    if not pickle_config:
        return None

    # Convert to v2 format
    v2_config = convert_to_v2_format(pickle_config, preserve_legacy=preserve_legacy)

    # Save to JSON if path provided
    if json_file_path:
        # Use same cipher for encryption
        if cipher is None:
            password = getpass.getpass("Enter password for encryption: ")
            cipher = derive_key(password)

        save_config_json(v2_config, json_file_path, cipher=cipher, encrypt=True)
        print(f"Converted configuration saved to: {json_file_path}")

    return v2_config


def convert_to_v2_format(
    legacy_config: Dict[str, Any], preserve_legacy: bool = True
) -> Dict[str, Any]:
    """
    Convert legacy configuration format to v2.0 format.

    Args:
        legacy_config: Legacy configuration dictionary
        preserve_legacy: Whether to preserve fwData/paData in v2 format

    Returns:
        v2.0 configuration dictionary
    """
    from datetime import datetime

    # Create new v2 config structure
    v2_config = create_empty_config_v2(
        source_type=legacy_config.get("paData", {}).get("paManagedBy", "scm"),
        description="Migrated from legacy format",
    )

    # Extract source tenant if available
    if "paData" in legacy_config and "paTSGID" in legacy_config["paData"]:
        v2_config["metadata"]["source_tenant"] = legacy_config["paData"]["paTSGID"]

    # Preserve legacy data if requested
    if preserve_legacy:
        if "fwData" in legacy_config:
            v2_config["fwData"] = legacy_config["fwData"]
        if "paData" in legacy_config:
            v2_config["paData"] = legacy_config["paData"]

    # Migrate infrastructure settings from paData
    if "paData" in legacy_config:
        pa_data = legacy_config["paData"]

        # Infrastructure subnet
        if "paInfraSubnet" in pa_data:
            v2_config["infrastructure"]["shared_infrastructure_settings"][
                "infrastructure_subnet"
            ] = pa_data["paInfraSubnet"]

        # BGP AS
        if "paInfraBGPAS" in pa_data:
            v2_config["infrastructure"]["shared_infrastructure_settings"][
                "infra_bgp_as"
            ] = pa_data["paInfraBGPAS"]

        # Mobile user subnet
        if "paMobUserSubnet" in pa_data:
            v2_config["infrastructure"]["mobile_agent"]["ip_pools"] = [
                {"ip_pool": [pa_data["paMobUserSubnet"]]}
            ]

        # Portal hostname
        if "paPortalHostname" in pa_data:
            v2_config["infrastructure"]["mobile_agent"]["portal_name"] = pa_data[
                "paPortalHostname"
            ]

        # Service connection data
        if "scName" in pa_data or "scLocation" in pa_data:
            sc_config = {}
            if "scName" in pa_data:
                sc_config["name"] = pa_data["scName"]
            if "scLocation" in pa_data:
                sc_config["region"] = [pa_data["scLocation"]]
            if "scSubnet" in pa_data and pa_data["scSubnet"]:
                sc_config["subnets"] = [pa_data["scSubnet"]]
            if "scTunnelName" in pa_data:
                sc_config["ipsec_tunnel"] = pa_data["scTunnelName"]

            if sc_config:
                v2_config["infrastructure"]["service_connections"].append(sc_config)

    # Add migration note
    v2_config["metadata"][
        "migration_note"
    ] = f"Migrated from legacy format on {datetime.utcnow().isoformat()}Z"

    return v2_config


def detect_config_format(file_path: str) -> str:
    """
    Detect the format of a configuration file.

    Args:
        file_path: Path to configuration file

    Returns:
        Format string: 'pickle', 'json', or 'unknown'
    """
    if not os.path.exists(file_path):
        return "unknown"

    # Check file extension
    _, ext = os.path.splitext(file_path)

    if ext == ".bin":
        # Likely pickle format
        return "pickle"
    elif ext == ".json":
        # Likely JSON format
        return "json"
    else:
        # Try to detect by reading file
        try:
            # Try as binary (pickle)
            with open(file_path, "rb") as f:
                data = f.read(100)
                # Check if it's encrypted (likely pickle)
                if len(data) > 0:
                    # Try to decode as UTF-8
                    try:
                        data.decode("utf-8")
                        # If successful, might be JSON
                        with open(file_path, "r", encoding="utf-8") as f2:
                            json.loads(f2.read(100))
                        return "json"
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        return "pickle"
        except Exception:
            pass

    return "unknown"


def load_config_auto(
    file_path: str, cipher: Optional[Fernet] = None
) -> Optional[Dict[str, Any]]:
    """
    Automatically detect and load configuration file (pickle or JSON).

    Args:
        file_path: Path to configuration file
        cipher: Optional Fernet cipher (will prompt if needed)

    Returns:
        Configuration dictionary or None if error
    """
    file_format = detect_config_format(file_path)

    if file_format == "pickle":
        from .pickle_compat import load_pickle_config

        return load_pickle_config(file_path, cipher)
    elif file_format == "json":
        from .json_storage import load_config_json

        # Try encrypted first, then unencrypted
        config = load_config_json(file_path, cipher, encrypted=True)
        if config is None:
            config = load_config_json(file_path, cipher, encrypted=False)
        return config
    else:
        print(f"Unknown configuration file format: {file_path}")
        return None
