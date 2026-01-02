"""
Utility module for loading example configurations in tests.

This provides convenient helpers to load example JSON files without
manually constructing file paths in every test.
"""

import json
from pathlib import Path
from typing import Dict, Any, List


EXAMPLES_DIR = Path(__file__).parent / "config" / "models"


def load_example(category: str, filename: str) -> Dict[str, Any]:
    """
    Load an example configuration file.
    
    Args:
        category: The category directory (objects, policies, profiles, infrastructure)
        filename: The JSON filename (with or without .json extension)
    
    Returns:
        Parsed JSON configuration as dictionary
    
    Example:
        >>> config = load_example('objects', 'address_minimal.json')
        >>> config = load_example('objects', 'address_minimal')  # .json is optional
    """
    if not filename.endswith('.json'):
        filename = f"{filename}.json"
    
    file_path = EXAMPLES_DIR / category / filename
    
    if not file_path.exists():
        raise FileNotFoundError(
            f"Example file not found: {file_path}\n"
            f"Available categories: objects, policies, profiles, infrastructure"
        )
    
    with open(file_path, 'r') as f:
        return json.load(f)


def load_object_example(filename: str) -> Dict[str, Any]:
    """Load an object example (address, service, application, etc.)"""
    return load_example('objects', filename)


def load_policy_example(filename: str) -> Dict[str, Any]:
    """Load a policy example (security rules, NAT, etc.)"""
    return load_example('policies', filename)


def load_profile_example(filename: str) -> Dict[str, Any]:
    """Load a profile example (auth, decryption, URL, HIP, etc.)"""
    return load_example('profiles', filename)


def load_infrastructure_example(filename: str) -> Dict[str, Any]:
    """Load an infrastructure example (IKE, IPsec, Service Connections, etc.)"""
    return load_example('infrastructure', filename)


def list_examples(category: str) -> List[str]:
    """
    List all available example files in a category.
    
    Args:
        category: The category directory (objects, policies, profiles, infrastructure)
    
    Returns:
        List of filenames (without .json extension)
    
    Example:
        >>> examples = list_examples('objects')
        >>> print(examples)
        ['address_minimal', 'address_full', 'address_snippet', ...]
    """
    category_path = EXAMPLES_DIR / category
    
    if not category_path.exists():
        raise ValueError(
            f"Category not found: {category}\n"
            f"Available categories: objects, policies, profiles, infrastructure"
        )
    
    return [f.stem for f in category_path.glob('*.json')]


def get_all_examples(category: str) -> Dict[str, Dict[str, Any]]:
    """
    Load all example configurations from a category.
    
    Args:
        category: The category directory
    
    Returns:
        Dictionary mapping filename (without extension) to parsed config
    
    Example:
        >>> all_objects = get_all_examples('objects')
        >>> address = all_objects['address_minimal']
    """
    examples = {}
    for filename in list_examples(category):
        examples[filename] = load_example(category, filename)
    return examples


# Convenience: Pre-defined common examples
class Examples:
    """
    Namespace class for commonly used examples.
    
    Usage:
        >>> from tests.examples.loader import Examples
        >>> config = Examples.address_minimal()
        >>> config = Examples.security_rule_full()
    """
    
    # Objects - Addresses
    @staticmethod
    def address_minimal() -> Dict[str, Any]:
        return load_object_example('address_minimal')
    
    @staticmethod
    def address_full() -> Dict[str, Any]:
        return load_object_example('address_full')
    
    @staticmethod
    def address_snippet() -> Dict[str, Any]:
        return load_object_example('address_snippet')
    
    @staticmethod
    def address_fqdn() -> Dict[str, Any]:
        return load_object_example('address_fqdn')
    
    @staticmethod
    def address_range() -> Dict[str, Any]:
        return load_object_example('address_range')
    
    @staticmethod
    def address_group() -> Dict[str, Any]:
        return load_object_example('address_group_minimal')
    
    @staticmethod
    def address_group_dynamic() -> Dict[str, Any]:
        return load_object_example('address_group_dynamic')
    
    # Objects - Services
    @staticmethod
    def service() -> Dict[str, Any]:
        return load_object_example('service_minimal')
    
    @staticmethod
    def service_group() -> Dict[str, Any]:
        return load_object_example('service_group_minimal')
    
    # Objects - Applications
    @staticmethod
    def application() -> Dict[str, Any]:
        return load_object_example('application_minimal')
    
    @staticmethod
    def application_group() -> Dict[str, Any]:
        return load_object_example('application_group_minimal')
    
    @staticmethod
    def application_filter() -> Dict[str, Any]:
        return load_object_example('application_filter_minimal')
    
    # Objects - Schedules
    @staticmethod
    def schedule() -> Dict[str, Any]:
        return load_object_example('schedule_minimal')
    
    @staticmethod
    def schedule_non_recurring() -> Dict[str, Any]:
        return load_object_example('schedule_non_recurring')
    
    # Policies
    @staticmethod
    def security_rule_minimal() -> Dict[str, Any]:
        return load_policy_example('security_rule_minimal')
    
    @staticmethod
    def security_rule_full() -> Dict[str, Any]:
        return load_policy_example('security_rule_full')
    
    @staticmethod
    def security_rule_disabled() -> Dict[str, Any]:
        return load_policy_example('security_rule_disabled')
    
    @staticmethod
    def security_rule_with_dependencies() -> Dict[str, Any]:
        return load_policy_example('security_rule_with_dependencies')
    
    # Profiles
    @staticmethod
    def auth_profile() -> Dict[str, Any]:
        return load_profile_example('authentication_profile_minimal')
    
    @staticmethod
    def decryption_profile() -> Dict[str, Any]:
        return load_profile_example('decryption_profile_minimal')
    
    @staticmethod
    def url_filtering_profile() -> Dict[str, Any]:
        return load_profile_example('url_filtering_profile_minimal')
    
    @staticmethod
    def profile_group() -> Dict[str, Any]:
        return load_profile_example('profile_group_minimal')
    
    @staticmethod
    def hip_profile() -> Dict[str, Any]:
        return load_profile_example('hip_profile_minimal')
    
    # Infrastructure
    @staticmethod
    def ike_crypto_profile() -> Dict[str, Any]:
        return load_infrastructure_example('ike_crypto_profile_minimal')
    
    @staticmethod
    def ipsec_crypto_profile() -> Dict[str, Any]:
        return load_infrastructure_example('ipsec_crypto_profile_minimal')
    
    @staticmethod
    def ike_gateway() -> Dict[str, Any]:
        return load_infrastructure_example('ike_gateway_minimal')
    
    @staticmethod
    def ipsec_tunnel() -> Dict[str, Any]:
        return load_infrastructure_example('ipsec_tunnel_minimal')
    
    @staticmethod
    def service_connection_minimal() -> Dict[str, Any]:
        return load_infrastructure_example('service_connection_minimal')
    
    @staticmethod
    def service_connection_full() -> Dict[str, Any]:
        return load_infrastructure_example('service_connection_full')
    
    @staticmethod
    def agent_profile() -> Dict[str, Any]:
        return load_infrastructure_example('agent_profile_minimal')


if __name__ == '__main__':
    # Quick test/demo
    print("Example Configuration Loader")
    print("=" * 50)
    
    for category in ['objects', 'policies', 'profiles', 'infrastructure']:
        examples = list_examples(category)
        print(f"\n{category.upper()} ({len(examples)} examples):")
        for ex in examples:
            print(f"  - {ex}")
    
    print("\n" + "=" * 50)
    print("Testing Examples class:")
    print(f"  Address: {Examples.address_minimal()['name']}")
    print(f"  Security Rule: {Examples.security_rule_full()['name']}")
    print(f"  Service Connection: {Examples.service_connection_minimal()['name']}")
