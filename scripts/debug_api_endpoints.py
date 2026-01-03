#!/usr/bin/env python3
"""
Debug script to test specific API endpoints that are returning 403/400 errors.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma.api_client import PrismaAccessAPIClient
from config.tenant_manager import TenantManager

def main():
    print("\n" + "="*70)
    print("DEBUG: Testing Problematic Endpoints")
    print("="*70)
    
    # Load credentials
    print("\n1. Loading credentials...")
    tenant_manager = TenantManager()
    tenants = tenant_manager.list_tenants()
    tenant = tenants[0]
    print(f"   Using tenant: {tenant['name']}")
    
    # Create API client
    print("\n2. Creating API client...")
    api_client = PrismaAccessAPIClient(
        tsg_id=tenant['tsg_id'],
        api_user=tenant['client_id'],
        api_secret=tenant['client_secret']
    )
    
    if not api_client.authenticate():
        print("❌ Authentication failed")
        return 1
    print("   ✅ Authenticated")
    
    # Test endpoints
    print("\n3. Testing endpoints...\n")
    
    endpoints_to_test = [
        ("URL Filtering Profiles", "https://api.sase.paloaltonetworks.com/sse/config/v1/url-filtering-profiles?folder=Mobile%20Users"),
        ("Wildfire Antivirus Profiles", "https://api.sase.paloaltonetworks.com/sse/config/v1/wildfire-antivirus-profiles?folder=Mobile%20Users"),
        ("Antivirus Profiles", "https://api.sase.paloaltonetworks.com/sse/config/v1/antivirus-profiles?folder=Mobile%20Users"),
        ("QoS Profiles (Mobile Users)", "https://api.sase.paloaltonetworks.com/sse/config/v1/qos-profiles?folder=Mobile%20Users"),
        ("QoS Profiles (Remote Networks)", "https://api.sase.paloaltonetworks.com/sse/config/v1/qos-profiles?folder=Remote%20Networks"),
    ]
    
    for name, url in endpoints_to_test:
        print(f"\n{name}:")
        print(f"  URL: {url}")
        
        try:
            # Make raw request to see actual response
            import requests
            headers = api_client._get_headers()
            response = requests.get(url, headers=headers, timeout=30)
            
            print(f"  Status Code: {response.status_code}")
            
            if response.ok:
                data = response.json()
                if isinstance(data, dict) and 'data' in data:
                    print(f"  ✅ Success: {len(data['data'])} items")
                else:
                    print(f"  ✅ Success: {data}")
            else:
                print(f"  ❌ Failed")
                print(f"  Response: {response.text[:200]}")
                
                # Try to parse error details
                try:
                    error_data = response.json()
                    if 'errors' in error_data:
                        for error in error_data['errors']:
                            print(f"  Error Code: {error.get('code', 'N/A')}")
                            print(f"  Message: {error.get('message', 'N/A')}")
                            if 'details' in error:
                                print(f"  Details: {error['details']}")
                except:
                    pass
                    
        except Exception as e:
            print(f"  ❌ Exception: {e}")
    
    print("\n" + "="*70)
    print("Debug complete!")
    print("="*70 + "\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
