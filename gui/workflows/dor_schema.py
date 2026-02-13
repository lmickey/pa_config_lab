"""
DoR (Definition of Requirements) Schema and Configuration Analysis.

This module provides:
- Empty DoR JSON schema creation
- Config-to-DoR answer mapping (extract answers from pulled Configuration)
- Feature detection using known default item names
- Manual answer merging
- Completeness validation
"""

from typing import Dict, Any, List, Optional, Set
import logging

logger = logging.getLogger(__name__)

# Feature detection map: maps DoR feature keys to profile types and known defaults
# Used to determine if a feature is configured beyond system defaults
DOR_FEATURE_MAP = {
    'dns_security': {
        'profile_type': 'dns_security_profile',
        'defaults': {'best-practice'},
        'label': 'DNS Security',
    },
    'url_filtering': {
        'profile_type': 'url_access_profile',
        'defaults': {'best-practice', 'Explicit Proxy - Unknown Users'},
        'label': 'URL Filtering',
    },
    'file_blocking': {
        'profile_type': 'file_blocking_profile',
        'defaults': {'best-practice'},
        'label': 'File Blocking / DLP',
    },
    'anti_spyware': {
        'profile_type': 'anti_spyware_profile',
        'defaults': {'best-practice'},
        'label': 'Anti-Spyware (IDP)',
    },
    'vulnerability_protection': {
        'profile_type': 'vulnerability_profile',
        'defaults': {'best-practice'},
        'label': 'Vulnerability Protection (IDP)',
    },
    'wildfire': {
        'profile_type': 'wildfire_profile',
        'defaults': {'best-practice'},
        'label': 'WildFire (Sandbox)',
    },
    'decryption': {
        'profile_type': 'decryption_profile',
        'defaults': {'best-practice', 'web-security-default'},
        'label': 'Decryption',
    },
    'hip': {
        'profile_type': 'hip_profile',
        'defaults': set(),
        'label': 'HIP Checks',
        'extra_types': ['hip_object'],
    },
    'profile_groups': {
        'profile_type': 'profile_group',
        'defaults': {'best-practice', 'Explicit Proxy - Unknown Users'},
        'label': 'Security Profile Groups',
    },
}

# Default snippet names from PullOrchestrator
DEFAULT_SNIPPETS = {
    'default', 'hip-default', 'optional-default',
    'Web Security Global', 'PA_predefined_embargo_rule',
    'best-practice', 'decrypt-bypass', 'Block-brute-force',
}


def detect_feature(config, feature_key: str) -> Dict[str, Any]:
    """
    Detect whether a security feature is configured beyond defaults.

    Args:
        config: Configuration object
        feature_key: Key from DOR_FEATURE_MAP

    Returns:
        Dict with detection results:
        - detected: bool - any items of this type exist
        - has_custom: bool - non-default items exist
        - custom_count: int - number of custom items
        - default_count: int - number of default items
        - custom_names: list - names of custom items
        - evidence: str - human-readable summary
    """
    if feature_key not in DOR_FEATURE_MAP:
        return {
            'detected': False, 'has_custom': False,
            'custom_count': 0, 'default_count': 0,
            'custom_names': [], 'evidence': 'Unknown feature key',
        }

    feature = DOR_FEATURE_MAP[feature_key]
    profile_type = feature['profile_type']
    defaults = feature['defaults']

    all_items = config.get_items_by_type(profile_type)

    # Also check extra types (e.g., hip_object for HIP feature)
    extra_types = feature.get('extra_types', [])
    for extra_type in extra_types:
        all_items.extend(config.get_items_by_type(extra_type))

    # Filter out items from default snippets
    non_default_snippet_items = []
    default_items = []
    for item in all_items:
        snippet = getattr(item, 'snippet', None)
        if snippet and snippet in DEFAULT_SNIPPETS:
            default_items.append(item)
        elif item.name in defaults:
            default_items.append(item)
        elif getattr(item, 'is_default', False):
            default_items.append(item)
        else:
            non_default_snippet_items.append(item)

    custom_names = [item.name for item in non_default_snippet_items]

    has_custom = len(non_default_snippet_items) > 0
    evidence_parts = []
    if has_custom:
        evidence_parts.append(f"{len(non_default_snippet_items)} custom: {', '.join(custom_names[:5])}")
    if default_items:
        evidence_parts.append(f"{len(default_items)} default")
    evidence = '; '.join(evidence_parts) if evidence_parts else 'No items found'

    return {
        'detected': len(all_items) > 0,
        'has_custom': has_custom,
        'custom_count': len(non_default_snippet_items),
        'default_count': len(default_items),
        'custom_names': custom_names,
        'evidence': evidence,
    }


def generate_dor_from_config(config) -> Dict[str, Any]:
    """
    Extract DoR answers from a pulled Configuration object.

    Analyzes the configuration to answer quantity, feature detection,
    and infrastructure detail questions automatically.

    Args:
        config: Configuration object (from pull)

    Returns:
        Dict with all config-answerable DoR data
    """
    answers = {
        'source': 'config_pull',
        'quantities': {},
        'features': {},
        'infrastructure': {},
        'security_rules': {},
    }

    # === Quantities ===
    quantities = answers['quantities']

    # Service connections
    scs = config.infrastructure.get_service_connections()
    quantities['service_connection_count'] = len(scs)
    quantities['service_connection_names'] = [sc.name for sc in scs]
    quantities['service_connection_locations'] = []
    for sc in scs:
        raw = getattr(sc, 'raw_config', {})
        region = raw.get('region', '')
        if region:
            quantities['service_connection_locations'].append({
                'name': sc.name,
                'region': region,
            })

    # Remote networks
    rns = config.infrastructure.get_items_by_type('remote_network')
    quantities['remote_network_count'] = len(rns)
    quantities['remote_network_names'] = [rn.name for rn in rns]
    quantities['remote_network_locations'] = []
    for rn in rns:
        raw = getattr(rn, 'raw_config', {})
        region = raw.get('region', '')
        if region:
            quantities['remote_network_locations'].append({
                'name': rn.name,
                'region': region,
            })

    # Datacenters (derived from service connections)
    quantities['datacenter_count'] = len(scs)

    # Security rules
    security_rules = config.get_items_by_type('security_rule')
    decryption_rules = config.get_items_by_type('decryption_rule')
    auth_rules = config.get_items_by_type('authentication_rule')
    qos_rules = config.get_items_by_type('qos_policy_rule')

    quantities['security_rule_count'] = len(security_rules)
    quantities['decryption_rule_count'] = len(decryption_rules)
    quantities['authentication_rule_count'] = len(auth_rules)
    quantities['qos_rule_count'] = len(qos_rules)

    # Objects
    address_objects = config.get_items_by_type('address_object')
    address_groups = config.get_items_by_type('address_group')
    service_objects = config.get_items_by_type('service_object')
    service_groups = config.get_items_by_type('service_group')
    edls = config.get_items_by_type('external_dynamic_list')
    custom_url_cats = config.get_items_by_type('custom_url_category')
    tags = config.get_items_by_type('tag')

    quantities['address_object_count'] = len(address_objects)
    quantities['address_group_count'] = len(address_groups)
    quantities['service_object_count'] = len(service_objects)
    quantities['service_group_count'] = len(service_groups)
    quantities['edl_count'] = len(edls)
    quantities['custom_url_category_count'] = len(custom_url_cats)
    quantities['tag_count'] = len(tags)

    # === Feature Detection ===
    for feature_key in DOR_FEATURE_MAP:
        answers['features'][feature_key] = detect_feature(config, feature_key)

    # === Infrastructure Details ===
    infra = answers['infrastructure']

    # IKE/IPsec crypto profiles
    ike_crypto = config.infrastructure.get_items_by_type('ike_crypto_profile')
    ipsec_crypto = config.infrastructure.get_items_by_type('ipsec_crypto_profile')
    infra['ike_crypto_profile_count'] = len(ike_crypto)
    infra['ipsec_crypto_profile_count'] = len(ipsec_crypto)

    # Extract crypto parameters
    infra['ike_crypto_profiles'] = []
    for profile in ike_crypto:
        raw = getattr(profile, 'raw_config', {})
        infra['ike_crypto_profiles'].append({
            'name': profile.name,
            'folder': profile.folder,
            'dh_group': raw.get('dh_group', []),
            'encryption': raw.get('encryption', []),
            'hash': raw.get('hash', []),
            'lifetime_hours': raw.get('lifetime', {}).get('hours'),
        })

    infra['ipsec_crypto_profiles'] = []
    for profile in ipsec_crypto:
        raw = getattr(profile, 'raw_config', {})
        esp = raw.get('esp', {})
        infra['ipsec_crypto_profiles'].append({
            'name': profile.name,
            'folder': profile.folder,
            'encryption': esp.get('encryption', []),
            'authentication': esp.get('authentication', []),
            'dh_group': raw.get('dh_group'),
            'lifetime_hours': raw.get('lifetime', {}).get('hours'),
        })

    # IKE gateways
    ike_gws = config.infrastructure.get_ike_gateways()
    infra['ike_gateway_count'] = len(ike_gws)
    infra['ike_gateways'] = []
    for gw in ike_gws:
        raw = getattr(gw, 'raw_config', {})
        auth = raw.get('authentication', {})
        peer = raw.get('peer_address', {})
        infra['ike_gateways'].append({
            'name': gw.name,
            'folder': gw.folder,
            'peer_address': peer.get('ip') or peer.get('fqdn', ''),
            'auth_type': 'pre-shared-key' if 'pre_shared_key' in auth else 'certificate',
            'ike_version': raw.get('protocol', {}).get('version', ''),
        })

    # IPsec tunnels
    tunnels = config.infrastructure.get_ipsec_tunnels()
    infra['ipsec_tunnel_count'] = len(tunnels)
    infra['ipsec_tunnels'] = []
    for tunnel in tunnels:
        raw = getattr(tunnel, 'raw_config', {})
        auto_key = raw.get('auto_key', {})
        infra['ipsec_tunnels'].append({
            'name': tunnel.name,
            'folder': tunnel.folder,
            'ike_gateway': auto_key.get('ike_gateway', [{}])[0].get('name', '') if auto_key.get('ike_gateway') else '',
            'ipsec_crypto_profile': auto_key.get('ipsec_crypto_profile', ''),
        })

    # Agent profiles (Mobile Users)
    agent_profiles = config.infrastructure.get_items_by_type('agent_profile')
    infra['agent_profile_count'] = len(agent_profiles)
    infra['agent_profile_names'] = [ap.name for ap in agent_profiles]

    # Certificate profiles
    cert_profiles = config.get_items_by_type('certificate_profile')
    infra['certificate_profile_count'] = len(cert_profiles)
    infra['certificate_profile_names'] = [cp.name for cp in cert_profiles]

    # Authentication profiles (if they exist as items)
    auth_profiles = config.get_items_by_type('authentication_profile')
    infra['authentication_profile_count'] = len(auth_profiles)

    # === Security Rule Summary ===
    rules_summary = answers['security_rules']

    # Count rules by folder
    rules_by_folder = {}
    for rule in security_rules:
        folder = rule.folder or rule.snippet or 'Unknown'
        rules_by_folder.setdefault(folder, 0)
        rules_by_folder[folder] += 1
    rules_summary['rules_by_location'] = rules_by_folder

    # Check for profile groups in rules
    rules_with_profiles = 0
    for rule in security_rules:
        raw = getattr(rule, 'raw_config', {})
        if raw.get('profile_setting'):
            rules_with_profiles += 1
    rules_summary['rules_with_profile_groups'] = rules_with_profiles
    rules_summary['total_rules'] = len(security_rules)

    # Folders and snippets summary
    answers['folders'] = list(config.folders.keys())
    answers['snippets'] = list(config.snippets.keys())
    answers['total_items'] = len(config.get_all_items())

    return answers


def create_empty_dor_schema() -> Dict[str, Any]:
    """
    Create an empty DoR JSON schema with all sections.

    Returns:
        Dict with the full hierarchical DoR structure, all fields empty/None.
    """
    return {
        'version': '1.0',
        'metadata': {
            'tenant_name': None,
            'tenant_url': None,
            'serial_number': None,
            'generated_at': None,
            'generated_by': 'pa_config_lab',
        },

        # Environment / Business Context (Tab 2)
        'environment': {
            'domain': 'SASE',
            'customer_problems': None,
            'why_current_tech_insufficient': None,
            'desired_business_outcomes': None,
            'identified_use_cases': [],
            'critical_capabilities': [],
            'delivery_model': None,  # Internal/Co-Delivery/MSSP/Delivery Assurance
            'service_sales_team_member': None,
            'current_state_network_design': None,
            'additional_current_future_state': None,
            'eval_to_prod_or_net_new': None,
            'innovation_preview_features': None,
        },

        # License Info (Tab 3 - auto-populated from pull)
        'license': {
            'license_data': None,  # Auto-populated from license-types API
            'license_notes': None,  # Manual override/notes
            'panorama_managed': None,  # Auto-detected from pull
            'multi_tenant_requested': False,
            'number_of_tenants': None,
            'license_info_raw': None,  # Raw license API response
        },

        # Mobile Users (Tab 3 - gated)
        'mobile_users': {
            'in_scope': False,
            'licensed_remote_workers': None,
            'total_mobile_users': None,
            'third_party_users': None,
            'geographic_distribution': None,
            'device_assignment': None,  # managed/BYOD/both
            'os_platforms': [],
            'agent_connect_method': None,
            'always_on': None,
            'bypass_tunnel_traffic': None,
            'hip_check_details': None,
        },

        # Remote Networks (Tab 3 - gated)
        'remote_networks': {
            'in_scope': False,
            'total_offices': None,
            'locations': None,
            'cpe_device': None,
            'largest_branch_users': None,
            'circuit_size': None,
            'bandwidth_per_site': None,
        },

        # ZTNA Connectors (Tab 3 - gated)
        'ztna_connectors': {
            'in_scope': False,
            'details': None,
        },

        # Service Connections (Tab 3 - partial from config)
        'service_connections': {
            'sc_nat_feature': None,
            'bgp_attributes_symmetric': None,
            'china_cbl': None,
            'premium_internet': None,
        },

        # Detection & Response (Tab 3)
        'detection_response': {
            'siem': None,
            'edr': None,
            'ndr': None,
            'cdr': None,
            'soar': None,
            'tim': None,
            'ueba': None,
            'epp_edr': None,
            'tip': None,
            'itdr': None,
            'asm': None,
        },

        # Cloud Security (Tab 3)
        'cloud_security': {
            'cspm': None,
            'ciem': None,
            'dspm': None,
            'asm': None,
            'cwp': None,
            'api_security': None,
            'ai_spm': None,
        },

        # Third-Party Access (Tab 3)
        'third_party_access': {
            'who': None,
            'how_many': None,
            'managed_unmanaged': None,
            'connection_method': None,
        },

        # Applications (Tab 3)
        'applications': {
            'genai_apps': None,
            'saas_apps': None,
            'private_app_protocols': None,
            'hosting': None,
        },

        # Data Security (Tab 3)
        'data_security': {
            'compliance_requirements': None,
            'exfiltration_channels': None,
            'classification_strategy': None,
            'dlp_policy': None,
        },

        # Authentication / CIE (Tab 3)
        'authentication': {
            'auth_methods_detected': None,  # Auto-populated from pulled auth profiles
            'saml_idp_vendor': None,
            'metadata_url': None,
            'username_attribute': None,
            'auth_info_raw': None,  # Raw auth/CIE data from pull
        },

        # Config-derived data (auto-populated from pull)
        'config_analysis': None,  # Filled by generate_dor_from_config()
    }


def merge_manual_answers(schema: Dict[str, Any], manual: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge manual form answers into the DoR schema.

    Args:
        schema: DoR schema (from create_empty_dor_schema or loaded state)
        manual: Manual answers from form tabs, keyed by section

    Returns:
        Updated schema dict with manual answers merged in
    """
    for section_key, section_data in manual.items():
        if section_key in schema and isinstance(section_data, dict) and isinstance(schema[section_key], dict):
            schema[section_key].update(section_data)
        else:
            schema[section_key] = section_data

    return schema


def validate_dor_completeness(data: Dict[str, Any]) -> List[str]:
    """
    Validate DoR data completeness and return list of missing required fields.

    Args:
        data: Complete DoR data dict

    Returns:
        List of human-readable missing field descriptions
    """
    missing = []

    # Required environment fields
    env = data.get('environment', {})
    if not env.get('delivery_model'):
        missing.append('Environment: Delivery model not specified')
    if not env.get('identified_use_cases'):
        missing.append('Environment: No use cases identified')

    # License info
    lic = data.get('license', {})
    if not lic.get('license_data'):
        missing.append('License: License data not populated (pull from tenant or enter manually)')

    # Mobile Users (only if in scope)
    mu = data.get('mobile_users', {})
    if mu.get('in_scope'):
        if not mu.get('total_mobile_users'):
            missing.append('Mobile Users: Total user count not specified')
        if not mu.get('os_platforms'):
            missing.append('Mobile Users: OS platforms not specified')

    # Remote Networks (only if in scope)
    rn = data.get('remote_networks', {})
    if rn.get('in_scope'):
        if not rn.get('total_offices'):
            missing.append('Remote Networks: Total offices not specified')

    # Config analysis should be present
    if not data.get('config_analysis'):
        missing.append('Config Analysis: No tenant configuration pulled')

    # Metadata
    meta = data.get('metadata', {})
    if not meta.get('tenant_name'):
        missing.append('Metadata: Tenant name not specified')

    return missing
