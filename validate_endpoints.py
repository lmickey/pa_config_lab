#!/usr/bin/env python3
"""
API Endpoint Validator - Test all Prisma Access API endpoints
Usage: 
  python3 validate_endpoints.py <tsg_id> <client_id>  # Prompts for secret
  python3 validate_endpoints.py --use-saved           # Uses saved credentials from config.json
"""

import sys
import os
import getpass
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '.')

from prisma.api_client import PrismaAccessAPIClient


class EndpointValidator:
    """Test all API endpoints and report which ones are incorrect."""
    
    def __init__(self, tsg_id: str, client_id: str, client_secret: str):
        """Initialize validator with credentials."""
        self.tsg_id = tsg_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_client = None
        self.results = {
            "success": [],
            "failed": [],
            "not_found": [],
            "forbidden": [],
            "not_implemented": [],
            "other_error": []
        }
        
    def connect(self) -> bool:
        """Authenticate and connect to API."""
        try:
            print(f"\n🔐 Authenticating...")
            print(f"   TSG ID: {self.tsg_id}")
            print(f"   Client ID: {self.client_id}")
            print(f"   Client Secret: {'*' * min(len(self.client_secret), 40)} ({len(self.client_secret)} chars)")
            
            # PrismaAccessAPIClient expects: (tsg_id, api_user, api_secret)
            self.api_client = PrismaAccessAPIClient(
                tsg_id=self.tsg_id,
                api_user=self.client_id,
                api_secret=self.client_secret
            )
            print("✅ Authentication successful!\n")
            return True
        except Exception as e:
            print(f"\n❌ Authentication failed: {e}")
            print("\n💡 Troubleshooting tips:")
            print("   1. Verify your client ID is correct (should end with @...iam.panserviceaccount.com)")
            print("   2. Make sure the client secret has no extra spaces or newlines")
            print("   3. Check that the TSG ID is correct")
            print("   4. Verify the service account has not been revoked or expired")
            print("   5. Try using --use-saved to load credentials from the GUI")
            return False
    
    def test_endpoint(self, name: str, method_name: str, test_params: Dict[str, Any] = None) -> Tuple[str, str, str, Dict[str, Any]]:
        """
        Test a single API endpoint.
        
        Returns: (status, http_code, message, details)
        """
        if test_params is None:
            test_params = {}
        
        details = {
            "base_url": "https://api.sase.paloaltonetworks.com",
            "endpoint": "Unknown",
            "method": "GET",
            "query_params": {},
            "body": None,
            "sample_response": None
        }
            
        try:
            method = getattr(self.api_client, method_name, None)
            if not method:
                return ("not_implemented", "N/A", f"Method {method_name} not found in API client", details)
            
            # Try to capture the actual API call details
            # We'll need to temporarily patch the request method
            original_request = self.api_client._make_request if hasattr(self.api_client, '_make_request') else None
            captured_details = {}
            
            def capture_request(method_type, endpoint, **kwargs):
                captured_details['method'] = method_type
                captured_details['endpoint'] = endpoint
                captured_details['query_params'] = kwargs.get('params', {})
                captured_details['body'] = kwargs.get('json', kwargs.get('data'))
                # Call original
                if original_request:
                    return original_request(method_type, endpoint, **kwargs)
                raise Exception("No _make_request method")
            
            # Patch temporarily
            if hasattr(self.api_client, '_make_request'):
                self.api_client._make_request = capture_request
            
            # Call the method
            result = method(**test_params)
            
            # Restore original
            if original_request:
                self.api_client._make_request = original_request
            
            # Update details from captured info
            if captured_details:
                details.update(captured_details)
            
            # Check if result is valid
            if result is None:
                return ("failed", "200?", "Method returned None", details)
            
            if isinstance(result, list):
                count = len(result)
                # Get sample of first few items
                sample = []
                for item in result[:3]:
                    if isinstance(item, dict):
                        # Get first few fields
                        sample_item = {}
                        for key in list(item.keys())[:5]:
                            sample_item[key] = item[key]
                        sample.append(sample_item)
                    else:
                        sample.append(str(item)[:100])
                details['sample_response'] = sample
                return ("success", "200", f"Returned {count} items", details)
            elif isinstance(result, dict):
                if "_errors" in result:
                    return ("failed", "400", f"API returned errors: {result['_errors']}", details)
                # Sample first few keys
                sample = {}
                for key in list(result.keys())[:5]:
                    sample[key] = result[key]
                details['sample_response'] = sample
                return ("success", "200", "Returned dict", details)
            else:
                details['sample_response'] = str(result)[:200]
                return ("success", "200", f"Returned {type(result).__name__}", details)
                
        except Exception as e:
            error_str = str(e)
            
            # Try to extract URL from error
            if "URL:" in error_str:
                try:
                    url_part = error_str.split("URL:")[1].split()[0]
                    details['endpoint'] = url_part.replace(details['base_url'], '')
                except:
                    pass
            
            # Parse error type
            if "404" in error_str or "Not Found" in error_str:
                return ("not_found", "404", error_str, details)
            elif "403" in error_str or "Forbidden" in error_str:
                return ("forbidden", "403", error_str, details)
            elif "401" in error_str or "Unauthorized" in error_str:
                return ("auth_error", "401", error_str, details)
            elif "400" in error_str or "Bad Request" in error_str:
                return ("bad_request", "400", error_str, details)
            else:
                return ("other_error", "???", error_str, details)
    
    def run_all_tests(self):
        """Test all API endpoints."""
        
        print("=" * 80)
        print("API ENDPOINT VALIDATION")
        print("=" * 80)
        print(f"TSG ID: {self.tsg_id}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 80)
        print()
        
        # Define all endpoints to test
        endpoints = [
            # Security Policies
            ("Security Rules", "get_security_rules", {"folder": "Shared"}),
            ("Security Policy Folders", "get_security_policy_folders", {}),
            
            # Objects
            ("Address Objects", "get_all_addresses", {"folder": "Shared"}),
            ("Address Groups", "get_all_address_groups", {"folder": "Shared"}),
            ("Service Objects", "get_services", {"folder": "Shared"}),
            ("Applications", "get_all_applications", {"folder": "Shared", "limit": 10}),
            
            # Profiles - Authentication
            ("Authentication Profiles", "get_authentication_profiles", {"folder": "Shared"}),
            
            # Profiles - Security
            ("Anti-Spyware Profiles", "get_anti_spyware_profiles", {"folder": "Shared"}),
            ("DNS Security Profiles", "get_dns_security_profiles", {"folder": "Shared"}),
            ("File Blocking Profiles", "get_file_blocking_profiles", {"folder": "Shared"}),
            ("HTTP Header Profiles", "get_http_header_profiles", {"folder": "Shared"}),
            ("Profile Groups", "get_profile_groups", {"folder": "Shared"}),
            ("URL Access Profiles", "get_url_access_profiles", {"folder": "Shared"}),
            ("Vulnerability Protection Profiles", "get_vulnerability_protection_profiles", {"folder": "Shared"}),
            ("Wildfire Anti-Virus Profiles", "get_wildfire_anti_virus_profiles", {"folder": "Shared"}),
            
            # Profiles - Decryption
            ("Decryption Profiles", "get_decryption_profiles", {"folder": "Shared"}),
            
            # Snippets
            ("Snippets", "get_all_snippets", {}),
            
            # Infrastructure - Remote Networks
            ("Remote Networks", "get_all_remote_networks", {}),
            # ("Remote Network Connections", "get_remote_network_connections", {}),  # Not implemented yet
            ("IPsec Tunnels", "get_all_ipsec_tunnels", {"folder": "Service Connections"}),
            ("IKE Gateways", "get_all_ike_gateways", {"folder": "Service Connections"}),
            ("IKE Crypto Profiles", "get_all_ike_crypto_profiles", {"folder": "Service Connections"}),
            ("IPsec Crypto Profiles", "get_all_ipsec_crypto_profiles", {"folder": "Service Connections"}),
            
            # Infrastructure - Service Connections
            ("Service Connections", "get_all_service_connections", {}),
            # ("Service Connection Groups", "get_all_service_connection_groups", {}),  # Not implemented yet
            
            # Infrastructure - Mobile Users (Mobile Agent Configuration)
            ("Mobile Agent Profiles", "get_mobile_agent_profiles", {"folder": "Mobile Users"}),
            ("Mobile Agent Versions", "get_mobile_agent_versions", {"folder": "Mobile Users"}),
            ("Mobile Agent Auth Settings", "get_mobile_agent_auth_settings", {"folder": "Mobile Users"}),
            ("Mobile Agent Enable", "get_mobile_agent_enable", {"folder": "Mobile Users"}),
            ("Mobile Agent Global Settings", "get_mobile_agent_global_settings", {"folder": "Mobile Users"}),
            ("Mobile Agent Infra Settings", "get_mobile_agent_infra_settings", {"folder": "Mobile Users"}),
            ("Mobile Agent Locations", "get_mobile_agent_locations", {"folder": "Mobile Users"}),
            ("Mobile Agent Tunnel Profiles", "get_mobile_agent_tunnel_profiles", {"folder": "Mobile Users"}),
            
            # Infrastructure - HIP
            ("HIP Objects", "get_all_hip_objects", {"folder": "Mobile Users"}),
            ("HIP Profiles", "get_all_hip_profiles", {"folder": "Mobile Users"}),
            
            # Infrastructure - Regions & Bandwidth
            ("Bandwidth Allocations", "get_all_bandwidth_allocations", {}),
            ("Locations", "get_all_locations", {"limit": 10}),
            
            # Infrastructure - Settings
            ("Shared Infrastructure Settings", "get_shared_infrastructure_settings", {}),
        ]
        
        print(f"\n📋 Testing {len(endpoints)} API endpoints...\n")
        
        # Test each endpoint
        for idx, (name, method_name, params) in enumerate(endpoints, 1):
            print(f"\n{'='*80}")
            print(f"[{idx:2d}/{len(endpoints)}] {name}")
            print(f"{'='*80}")
            
            status, code, message, details = self.test_endpoint(name, method_name, params)
            
            # Print detailed information
            print(f"Method:       {method_name}")
            print(f"Base URL:     {details.get('base_url', 'N/A')}")
            print(f"Endpoint:     {details.get('endpoint', 'N/A')}")
            print(f"HTTP Method:  {details.get('method', 'GET')}")
            if details.get('query_params'):
                print(f"Query Params: {details['query_params']}")
            if details.get('body'):
                print(f"Request Body: {details['body']}")
            
            # Store result
            result_entry = {
                "name": name,
                "method": method_name,
                "params": params,
                "status": status,
                "code": code,
                "message": message,
                "details": details
            }
            
            # Print status and sample response
            if status == "success":
                self.results["success"].append(result_entry)
                print(f"Status:       ✅ {code} - {message}")
                
                # Print sample response
                if details.get('sample_response'):
                    print(f"\nSample Response:")
                    sample = details['sample_response']
                    if isinstance(sample, list):
                        for i, item in enumerate(sample, 1):
                            print(f"  Item {i}: {json.dumps(item, indent=4)}")
                    else:
                        print(f"  {json.dumps(sample, indent=4)}")
                        
            elif status == "not_found":
                self.results["not_found"].append(result_entry)
                print(f"Status:       ❌ {code} - Endpoint not found or incorrect URL")
                print(f"Error:        {message[:200]}")
            elif status == "forbidden":
                self.results["forbidden"].append(result_entry)
                print(f"Status:       ⚠️  {code} - Forbidden (may need permissions)")
            elif status == "not_implemented":
                print(f"Status:       ⚠️  Method not implemented in api_client.py")
            else:
                self.results["other_error"].append(result_entry)
                print(f"Status:       ❌ {code}")
                print(f"Error:        {message[:200]}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total = sum(len(v) for v in self.results.values())
        success_count = len(self.results["success"])
        
        print(f"\n✅ Successful:      {success_count}/{total}")
        print(f"❌ Not Found:       {len(self.results['not_found'])}/{total}")
        print(f"⚠️  Forbidden:       {len(self.results['forbidden'])}/{total}")
        print(f"⚠️  Not Implemented: {len(self.results['not_implemented'])}/{total}")
        print(f"❌ Other Error:     {len(self.results['other_error'])}/{total}")
        
        # Show failed endpoints in detail
        if self.results["not_found"]:
            print("\n" + "=" * 80)
            print("❌ ENDPOINTS NOT FOUND (404) - These need URL correction:")
            print("=" * 80)
            for entry in self.results["not_found"]:
                print(f"\n📍 {entry['name']}")
                print(f"   Method:   {entry['method']}")
                print(f"   Endpoint: {entry['details'].get('endpoint', 'Unknown')}")
                print(f"   Error:    {entry['message'][:200]}")
        
        if self.results["other_error"]:
            print("\n" + "=" * 80)
            print("❌ ENDPOINTS WITH ERRORS:")
            print("=" * 80)
            for entry in self.results["other_error"]:
                print(f"\n📍 {entry['name']}")
                print(f"   Method: {entry['method']}")
                print(f"   Status: {entry['code']}")
                print(f"   Error: {entry['message'][:200]}")
        
        if self.results["forbidden"]:
            print("\n" + "=" * 80)
            print("⚠️  FORBIDDEN ENDPOINTS (may require additional permissions):")
            print("=" * 80)
            for entry in self.results["forbidden"]:
                print(f"   • {entry['name']}")
        
        if self.results["not_implemented"]:
            print("\n" + "=" * 80)
            print("⚠️  NOT IMPLEMENTED METHODS (need to be added to api_client.py):")
            print("=" * 80)
            for entry in self.results["not_implemented"]:
                print(f"\n📍 {entry['name']}")
                print(f"   Method: {entry['method']}")
                print(f"   Action: Add this method to prisma/api_client.py")
        
        # Save full report
        self.save_report()
    
    def save_report(self):
        """Save detailed report to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"endpoint_validation_{timestamp}.json"
        
        report = {
            "tsg_id": self.tsg_id,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": sum(len(v) for v in self.results.values()),
                "success": len(self.results["success"]),
                "not_found": len(self.results["not_found"]),
                "forbidden": len(self.results["forbidden"]),
                "not_implemented": len(self.results["not_implemented"]),
                "other_error": len(self.results["other_error"])
            },
            "results": self.results
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Full report saved to: {filename}")


def load_saved_credentials():
    """Load credentials from config.json."""
    config_file = "config.json"
    if not os.path.exists(config_file):
        print(f"❌ Config file not found: {config_file}")
        print("   Run the GUI first to save credentials, or provide them manually.")
        return None
    
    try:
        with open(config_file, 'r') as f:
            content = f.read().strip()
            if not content:
                print(f"❌ Config file is empty: {config_file}")
                return None
            config = json.loads(content)
        
        tsg_id = config.get("tsg_id")
        client_id = config.get("client_id")
        client_secret = config.get("client_secret")
        
        if not all([tsg_id, client_id, client_secret]):
            print("❌ Incomplete credentials in config.json")
            print(f"   Found: tsg_id={bool(tsg_id)}, client_id={bool(client_id)}, client_secret={bool(client_secret)}")
            return None
        
        print(f"✅ Loaded credentials from {config_file}")
        return tsg_id, client_id, client_secret
    
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        print(f"   File may be corrupted or empty")
        return None
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None


def main():
    """Main entry point."""
    # Check for --use-saved flag
    if len(sys.argv) == 2 and sys.argv[1] == "--use-saved":
        print("\n🔐 Prisma Access API Endpoint Validator")
        print("=" * 80)
        print("Loading saved credentials from config.json...")
        
        creds = load_saved_credentials()
        if not creds:
            sys.exit(1)
        
        tsg_id, client_id, client_secret = creds
    
    elif len(sys.argv) == 3:
        # Parse arguments
        tsg_id = sys.argv[1]
        client_id = sys.argv[2]
        
        # Prompt for secret
        print("\n🔐 Prisma Access API Endpoint Validator")
        print("=" * 80)
        print(f"TSG ID: {tsg_id}")
        print(f"Client ID: {client_id}")
        print()
        client_secret = getpass.getpass("Enter client secret: ")
        
        if not client_secret:
            print("❌ Client secret is required")
            sys.exit(1)
        
        # Strip any whitespace
        client_secret = client_secret.strip()
    
    else:
        print("Usage:")
        print("  python3 validate_endpoints.py <tsg_id> <client_id>  # Prompts for secret")
        print("  python3 validate_endpoints.py --use-saved           # Uses saved credentials")
        print("\nExample:")
        print("  python3 validate_endpoints.py 1234567890 myapp@12345.iam.panserviceaccount.com")
        sys.exit(1)
    
    # Create validator
    validator = EndpointValidator(tsg_id, client_id, client_secret)
    
    # Connect
    if not validator.connect():
        sys.exit(1)
    
    # Run all tests
    validator.run_all_tests()
    
    print("\n✅ Validation complete!")
    print("\nPlease review the endpoints marked as '404 Not Found' - these need URL corrections.")
    print("Share the generated JSON report for detailed analysis.\n")


if __name__ == "__main__":
    main()
