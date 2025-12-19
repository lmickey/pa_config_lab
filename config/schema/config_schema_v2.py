"""
JSON Schema definitions for Prisma Access comprehensive configuration (v2.0).

This module defines the structure for storing comprehensive Prisma Access
configurations including security policies, objects, profiles, and infrastructure.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json


# Base schema structure for v2.0 configuration
CONFIG_SCHEMA_V2 = {
    "type": "object",
    "required": ["metadata", "infrastructure", "security_policies"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["version", "created"],
            "properties": {
                "version": {
                    "type": "string",
                    "pattern": "^2\\.\\d+\\.\\d+$",
                    "description": "Schema version (e.g., '2.0.0')"
                },
                "created": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO 8601 timestamp when config was created"
                },
                "source_tenant": {
                    "type": "string",
                    "description": "Source TSG ID or tenant identifier"
                },
                "source_type": {
                    "type": "string",
                    "enum": ["scm", "panorama"],
                    "description": "Source management type"
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of this configuration"
                },
                "updated": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO 8601 timestamp when config was last updated"
                }
            }
        },
        "infrastructure": {
            "type": "object",
            "properties": {
                "shared_infrastructure_settings": {
                    "type": "object",
                    "description": "Shared infrastructure settings"
                },
                "mobile_agent": {
                    "type": "object",
                    "description": "Mobile agent configuration"
                },
                "service_connections": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Service connection configurations"
                },
                "remote_networks": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Remote network configurations"
                }
            }
        },
        "security_policies": {
            "type": "object",
            "required": ["folders", "snippets"],
            "properties": {
                "folders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "path"],
                        "properties": {
                            "name": {"type": "string"},
                            "path": {"type": "string"},
                            "is_default": {"type": "boolean", "default": False},
                            "security_rules": {
                                "type": "array",
                                "items": {"type": "object"}
                            },
                            "objects": {
                                "type": "object",
                                "properties": {
                                    "address_objects": {"type": "array", "items": {"type": "object"}},
                                    "address_groups": {"type": "array", "items": {"type": "object"}},
                                    "service_objects": {"type": "array", "items": {"type": "object"}},
                                    "service_groups": {"type": "array", "items": {"type": "object"}},
                                    "application_filters": {"type": "array", "items": {"type": "object"}},
                                    "application_groups": {"type": "array", "items": {"type": "object"}},
                                    "application_signatures": {"type": "array", "items": {"type": "object"}},
                                    "url_filtering_categories": {"type": "array", "items": {"type": "object"}},
                                    "external_dynamic_lists": {"type": "array", "items": {"type": "object"}},
                                    "fqdn_objects": {"type": "array", "items": {"type": "object"}}
                                }
                            },
                            "profiles": {
                                "type": "object",
                                "properties": {
                                    "authentication_profiles": {"type": "array", "items": {"type": "object"}},
                                    "security_profiles": {
                                        "type": "object",
                                        "properties": {
                                            "antivirus": {"type": "array", "items": {"type": "object"}},
                                            "anti_spyware": {"type": "array", "items": {"type": "object"}},
                                            "vulnerability": {"type": "array", "items": {"type": "object"}},
                                            "url_filtering": {"type": "array", "items": {"type": "object"}},
                                            "file_blocking": {"type": "array", "items": {"type": "object"}},
                                            "wildfire": {"type": "array", "items": {"type": "object"}},
                                            "data_filtering": {"type": "array", "items": {"type": "object"}}
                                        }
                                    },
                                    "decryption_profiles": {
                                        "type": "object",
                                        "properties": {
                                            "ssl_forward_proxy": {"type": "array", "items": {"type": "object"}},
                                            "ssl_inbound_inspection": {"type": "array", "items": {"type": "object"}},
                                            "ssl_ssh_proxy": {"type": "array", "items": {"type": "object"}}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "snippets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "path"],
                        "properties": {
                            "name": {"type": "string"},
                            "path": {"type": "string"},
                            "is_default": {"type": "boolean", "default": False},
                            "security_rules": {"type": "array", "items": {"type": "object"}},
                            "objects": {"type": "object"},
                            "profiles": {"type": "object"}
                        }
                    }
                }
            }
        },
        "authentication": {
            "type": "object",
            "properties": {
                "authentication_profiles": {"type": "array", "items": {"type": "object"}},
                "authentication_sequences": {"type": "array", "items": {"type": "object"}},
                "saml_profiles": {"type": "array", "items": {"type": "object"}},
                "kerberos_profiles": {"type": "array", "items": {"type": "object"}}
            }
        },
        "network": {
            "type": "object",
            "properties": {
                "ike_crypto_profiles": {"type": "array", "items": {"type": "object"}},
                "ipsec_crypto_profiles": {"type": "array", "items": {"type": "object"}},
                "ike_gateways": {"type": "array", "items": {"type": "object"}},
                "ipsec_tunnels": {"type": "array", "items": {"type": "object"}},
                "service_connections": {"type": "array", "items": {"type": "object"}},
                "remote_networks": {"type": "array", "items": {"type": "object"}}
            }
        },
        "defaults": {
            "type": "object",
            "properties": {
                "detected_defaults": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "name": {"type": "string"},
                            "path": {"type": "string"},
                            "reason": {"type": "string"}
                        }
                    }
                },
                "excluded_configs": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        # Legacy compatibility: Keep fwData and paData for backward compatibility
        "fwData": {
            "type": "object",
            "description": "Legacy firewall data (for backward compatibility)"
        },
        "paData": {
            "type": "object",
            "description": "Legacy Prisma Access data (for backward compatibility)"
        }
    }
}


def create_empty_config_v2(
    source_tenant: Optional[str] = None,
    source_type: str = "scm",
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an empty v2.0 configuration structure.
    
    Args:
        source_tenant: Source tenant identifier (TSG ID)
        source_type: Source type ('scm' or 'panorama')
        description: Optional description
        
    Returns:
        Empty configuration dictionary with proper structure
    """
    now = datetime.utcnow().isoformat() + "Z"
    
    config = {
        "metadata": {
            "version": "2.0.0",
            "created": now,
            "updated": now,
            "source_type": source_type
        },
        "infrastructure": {
            "shared_infrastructure_settings": {},
            "mobile_agent": {},
            "service_connections": [],
            "remote_networks": []
        },
        "security_policies": {
            "folders": [],
            "snippets": []
        },
        "authentication": {
            "authentication_profiles": [],
            "authentication_sequences": [],
            "saml_profiles": [],
            "kerberos_profiles": []
        },
        "network": {
            "ike_crypto_profiles": [],
            "ipsec_crypto_profiles": [],
            "ike_gateways": [],
            "ipsec_tunnels": [],
            "service_connections": [],
            "remote_networks": []
        },
        "defaults": {
            "detected_defaults": [],
            "excluded_configs": []
        }
    }
    
    if source_tenant:
        config["metadata"]["source_tenant"] = source_tenant
    
    if description:
        config["metadata"]["description"] = description
    
    return config


def get_schema_version() -> str:
    """Get the current schema version."""
    return "2.0.0"


def validate_config_structure(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Basic structure validation (full validation requires jsonschema library).
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(config, dict):
        return False, "Configuration must be a dictionary"
    
    # Check required top-level keys
    required_keys = ["metadata", "infrastructure", "security_policies"]
    for key in required_keys:
        if key not in config:
            return False, f"Missing required key: {key}"
    
    # Validate metadata
    metadata = config.get("metadata", {})
    if "version" not in metadata:
        return False, "Missing metadata.version"
    
    if "created" not in metadata:
        return False, "Missing metadata.created"
    
    # Validate security_policies structure
    security_policies = config.get("security_policies", {})
    if "folders" not in security_policies:
        return False, "Missing security_policies.folders"
    if "snippets" not in security_policies:
        return False, "Missing security_policies.snippets"
    
    if not isinstance(security_policies["folders"], list):
        return False, "security_policies.folders must be a list"
    if not isinstance(security_policies["snippets"], list):
        return False, "security_policies.snippets must be a list"
    
    return True, None
