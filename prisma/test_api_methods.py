#!/usr/bin/env python3
"""
API Method Validation Script

This script validates that all required API methods exist in the PrismaAccessAPIClient
and match the endpoints defined in api_endpoints.py.

Run this before making changes to ensure all methods are implemented.
"""

import sys
from typing import Dict, List, Tuple

# Expected API methods that should exist
# Format: (method_name, endpoint_constant, description)
REQUIRED_METHODS = [
    # Objects
    ("get_all_addresses", "ADDRESSES", "Address objects"),
    ("get_all_address_groups", "ADDRESS_GROUPS", "Address groups"),
    ("get_all_services", "SERVICES", "Service objects"),
    ("get_all_service_groups", "SERVICE_GROUPS", "Service groups"),
    ("get_all_applications", "APPLICATIONS", "Applications"),
    ("get_all_application_groups", "APPLICATION_GROUPS", "Application groups"),
    ("get_all_application_filters", "APPLICATION_FILTERS", "Application filters"),
    ("get_all_external_dynamic_lists", "EXTERNAL_DYNAMIC_LISTS", "External dynamic lists"),
    ("get_all_fqdn_objects", "FQDN", "FQDN objects"),
    ("get_all_url_categories", "URL_CATEGORIES", "URL filtering categories"),
    
    # Infrastructure
    ("get_all_remote_networks", "REMOTE_NETWORKS", "Remote networks"),
    ("get_all_service_connections", "SERVICE_CONNECTIONS", "Service connections"),
    ("get_all_ipsec_tunnels", "IPSEC_TUNNELS", "IPsec tunnels"),
    ("get_all_ike_gateways", "IKE_GATEWAYS", "IKE gateways"),
    ("get_all_ike_crypto_profiles", "IKE_CRYPTO_PROFILES", "IKE crypto profiles"),
    ("get_all_ipsec_crypto_profiles", "IPSEC_CRYPTO_PROFILES", "IPsec crypto profiles"),
    
    # Mobile Users
    ("get_mobile_agent_profiles", "MOBILE_AGENT_PROFILES", "Mobile agent profiles"),
    ("get_mobile_agent_versions", "MOBILE_AGENT_VERSIONS", "Mobile agent versions"),
    ("get_mobile_agent_auth_settings", "MOBILE_AGENT_AUTH_SETTINGS", "Mobile agent auth settings"),
    
    # Profiles
    ("get_all_authentication_profiles", "AUTHENTICATION_PROFILES", "Authentication profiles"),
    ("get_all_decryption_profiles", "DECRYPTION_PROFILES", "Decryption profiles"),
    ("get_all_anti_spyware_profiles", "ANTI_SPYWARE_PROFILES", "Anti-spyware profiles"),
    ("get_all_dns_security_profiles", "DNS_SECURITY_PROFILES", "DNS security profiles"),
    ("get_all_file_blocking_profiles", "FILE_BLOCKING_PROFILES", "File blocking profiles"),
    ("get_all_url_access_profiles", "URL_ACCESS_PROFILES", "URL access profiles"),
    ("get_all_vulnerability_profiles", "VULNERABILITY_PROTECTION_PROFILES", "Vulnerability protection profiles"),
    ("get_all_wildfire_profiles", "WILDFIRE_ANTI_VIRUS_PROFILES", "WildFire antivirus profiles"),
    ("get_all_profile_groups", "PROFILE_GROUPS", "Profile groups"),
    
    # HIP
    ("get_all_hip_objects", "HIP_OBJECTS", "HIP objects"),
    ("get_all_hip_profiles", "HIP_PROFILES", "HIP profiles"),
    
    # Security Policy
    ("get_security_policy_folders", "SECURITY_POLICY_FOLDERS", "Security policy folders"),
    ("get_security_policy_snippets", "SECURITY_POLICY_SNIPPETS", "Security policy snippets"),
    ("get_all_security_rules", "SECURITY_RULES", "Security rules"),
]


def validate_api_methods() -> Tuple[List[str], List[str]]:
    """
    Validate that all required API methods exist.
    
    Returns:
        Tuple of (missing_methods, existing_methods)
    """
    try:
        from prisma.api_client import PrismaAccessAPIClient
        from prisma.api_endpoints import APIEndpoints
    except ImportError as e:
        print(f"❌ ERROR: Failed to import modules: {e}")
        sys.exit(1)
    
    missing = []
    existing = []
    
    print("=" * 80)
    print("API METHOD VALIDATION")
    print("=" * 80)
    print()
    
    for method_name, endpoint_const, description in REQUIRED_METHODS:
        # Check if method exists
        has_method = hasattr(PrismaAccessAPIClient, method_name)
        
        # Check if endpoint exists
        has_endpoint = hasattr(APIEndpoints, endpoint_const)
        
        status = "✅" if has_method else "❌"
        endpoint_status = "✅" if has_endpoint else "⚠️"
        
        print(f"{status} {method_name:45} {endpoint_status} {endpoint_const:35} {description}")
        
        if has_method:
            existing.append(method_name)
        else:
            missing.append((method_name, endpoint_const, description))
    
    return missing, existing


def print_summary(missing: List[Tuple[str, str, str]], existing: List[str]):
    """Print validation summary."""
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Existing methods: {len(existing)}")
    print(f"❌ Missing methods:  {len(missing)}")
    print()
    
    if missing:
        print("MISSING METHODS:")
        print("-" * 80)
        for method_name, endpoint_const, description in missing:
            print(f"  • {method_name}")
            print(f"    Endpoint: APIEndpoints.{endpoint_const}")
            print(f"    Description: {description}")
            print()


def generate_method_templates(missing: List[Tuple[str, str, str]]):
    """Generate code templates for missing methods."""
    if not missing:
        return
    
    print("=" * 80)
    print("CODE TEMPLATES FOR MISSING METHODS")
    print("=" * 80)
    print()
    
    for method_name, endpoint_const, description in missing:
        # Determine if it's a get_all_ method or special method
        if method_name.startswith("get_all_"):
            # Standard paginated get_all method
            base_name = method_name.replace("get_all_", "get_")
            singular = base_name.replace("get_", "")
            
            print(f"    def {base_name}(")
            print(f"        self, folder: Optional[str] = None, limit: int = 100, offset: int = 0")
            print(f"    ) -> List[Dict[str, Any]]:")
            print(f'        """')
            print(f'        Get {description}.')
            print(f'        ')
            print(f'        Args:')
            print(f'            folder: Optional folder name to filter results')
            print(f'            limit: Maximum number of results per page')
            print(f'            offset: Pagination offset')
            print(f'            ')
            print(f'        Returns:')
            print(f'            List of {description}')
            print(f'        """')
            print(f"        url = APIEndpoints.{endpoint_const}")
            print(f"        params = {{}}")
            print(f"        if folder:")
            print(f"            url += build_folder_query(folder)")
            print(f"        if limit != 100:")
            print(f'            params["limit"] = limit')
            print(f"        if offset > 0:")
            print(f'            params["offset"] = offset')
            print(f"        response = self._make_request(\"GET\", url, params=params if params else None)")
            print(f'        return response.get("data", [])')
            print()
            print(f"    def {method_name}(")
            print(f"        self, folder: Optional[str] = None")
            print(f"    ) -> List[Dict[str, Any]]:")
            print(f'        """Get all {description} with automatic pagination."""')
            print(f"        def api_func(offset=0, limit=100):")
            print(f"            return self.{base_name}(folder=folder, limit=limit, offset=offset)")
            print(f"        return paginate_api_request(api_func)")
            print()
        else:
            # Special method (like mobile agent methods)
            print(f"    def {method_name}(self, folder: Optional[str] = None) -> Dict[str, Any]:")
            print(f'        """')
            print(f'        Get {description}.')
            print(f'        ')
            print(f'        Args:')
            print(f'            folder: Folder name')
            print(f'        ')
            print(f'        Returns:')
            print(f'            {description} configuration dict')
            print(f'        """')
            print(f"        endpoint = APIEndpoints.{endpoint_const}")
            print(f"        params = {{}}")
            print(f"        if folder:")
            print(f'            params["folder"] = folder')
            print(f"        response = self._make_request(\"GET\", endpoint, params=params if params else None)")
            print(f"        return response if isinstance(response, dict) else {{}}")
            print()


def main():
    """Main validation function."""
    missing, existing = validate_api_methods()
    print_summary(missing, existing)
    
    if missing:
        print()
        generate_method_templates(missing)
        print()
        print("=" * 80)
        print("⚠️  WARNING: Missing methods detected!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Copy the generated method templates above")
        print("2. Add them to prisma/api_client.py")
        print("3. Run this script again to verify")
        print()
        sys.exit(1)
    else:
        print()
        print("=" * 80)
        print("✅ ALL REQUIRED API METHODS EXIST!")
        print("=" * 80)
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
