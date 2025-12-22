#!/usr/bin/env python3
"""
Snippet Verification Script - Retrieve and validate all snippets from Prisma Access

Usage: 
  python3 verify_snippets.py <tsg_id> <client_id>  # Prompts for secret
  python3 verify_snippets.py --use-saved           # Uses saved credentials from config.json
"""

import sys
import os
import getpass
import json
from typing import Dict, List, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '.')

from prisma.api_client import PrismaAccessAPIClient


class SnippetVerifier:
    """Retrieve and verify all snippets from the tenant."""
    
    def __init__(self, tsg_id: str, client_id: str, client_secret: str):
        """Initialize verifier with credentials."""
        self.tsg_id = tsg_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_client = None
        
    def connect(self) -> bool:
        """Authenticate and connect to API."""
        try:
            print(f"\n🔐 Authenticating...")
            print(f"   TSG ID: {self.tsg_id}")
            print(f"   Client ID: {self.client_id}")
            print(f"   Client Secret: {'*' * min(len(self.client_secret), 40)} ({len(self.client_secret)} chars)")
            
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
            print("   1. Verify your client ID is correct")
            print("   2. Make sure the client secret has no extra spaces or newlines")
            print("   3. Check that the TSG ID is correct")
            print("   4. Try using --use-saved to load credentials from the GUI")
            return False
    
    def get_snippets(self) -> Dict[str, Any]:
        """
        Retrieve all snippets from the tenant.
        
        Returns:
            Dictionary with snippet data and metadata
        """
        print("📋 Retrieving snippets from tenant...\n")
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "tsg_id": self.tsg_id,
            "snippets": [],
            "snippet_count": 0,
            "errors": [],
            "raw_api_response": None
        }
        
        try:
            # Get snippets using the API client
            print("   Calling get_security_policy_snippets()...")
            snippets = self.api_client.get_security_policy_snippets()
            
            result["raw_api_response"] = snippets
            result["snippet_count"] = len(snippets) if isinstance(snippets, list) else 0
            
            print(f"   ✅ Retrieved {result['snippet_count']} snippet(s)\n")
            
            # Process each snippet
            if isinstance(snippets, list):
                for idx, snippet in enumerate(snippets, 1):
                    snippet_info = {
                        "index": idx,
                        "raw_data": snippet,
                        "parsed": {}
                    }
                    
                    # Try to parse common fields
                    if isinstance(snippet, dict):
                        # Check if display_name exists in the raw data
                        has_display_name_field = "display_name" in snippet
                        display_name_value = snippet.get("display_name", "N/A")
                        
                        # Check snippet keys to determine if it should be skipped
                        snippet_keys = set(snippet.keys())
                        is_minimal_snippet = snippet_keys == {"id", "name"} or snippet_keys == {"name", "id"}
                        
                        snippet_info["parsed"] = {
                            "name": snippet.get("name", "N/A"),
                            "display_name": display_name_value,
                            "has_display_name_field": has_display_name_field,
                            "display_name_is_empty": display_name_value == "" or display_name_value == "N/A",
                            "type": snippet.get("type", "N/A"),
                            "enable_prefix": snippet.get("enable_prefix", "N/A"),
                            "id": snippet.get("id", "N/A"),
                            "description": snippet.get("description", ""),
                            "folders": snippet.get("folders", []),
                            "shared_in": snippet.get("shared_in", ""),
                            "created_in": snippet.get("created_in", ""),
                            "last_update": snippet.get("last_update", ""),
                            "all_keys": list(snippet_keys),
                            "is_minimal_snippet": is_minimal_snippet,
                        }
                        
                        # Extract folder names
                        folder_list = snippet.get("folders", [])
                        folder_names = []
                        if folder_list:
                            for folder in folder_list:
                                if isinstance(folder, dict):
                                    folder_name = folder.get("name", "")
                                    if folder_name:
                                        folder_names.append(folder_name)
                                elif isinstance(folder, str):
                                    folder_names.append(folder)
                        snippet_info["parsed"]["folder_names"] = folder_names
                        
                        display_name = snippet_info['parsed']['display_name']
                        snippet_type = snippet_info['parsed']['type']
                        is_minimal = snippet_info['parsed']['is_minimal_snippet']
                        has_enable_prefix = snippet_info['parsed']['enable_prefix'] != "N/A"
                        
                        # Determine if it will be skipped
                        if is_minimal:
                            status = "✗ SKIP (only id+name)"
                        else:
                            status = "✓ KEEP"
                        
                        # Determine type label
                        if snippet_type in ["predefined", "readonly"]:
                            type_label = "predefined"
                        elif has_enable_prefix or snippet_type == "N/A":
                            type_label = "custom"
                        else:
                            type_label = "unknown"
                        
                        # Display name to show
                        show_name = display_name if display_name != "N/A" else snippet_info['parsed']['name']
                        
                        print(f"   {idx}. {show_name}")
                        print(f"      Status: {status}")
                        print(f"      Name: {snippet_info['parsed']['name']}")
                        print(f"      Type: {snippet_type} ({type_label})")
                        if has_enable_prefix:
                            print(f"      Enable Prefix: {snippet_info['parsed']['enable_prefix']}")
                        print(f"      Keys: {', '.join(sorted(snippet_info['parsed']['all_keys']))}")
                        print(f"      ID: {snippet_info['parsed']['id']}")
                        if folder_names:
                            print(f"      Folders: {', '.join(folder_names)}")
                        else:
                            print(f"      Folders: (none)")
                        print()
                    
                    result["snippets"].append(snippet_info)
            else:
                result["errors"].append(f"Unexpected response type: {type(snippets).__name__}")
                print(f"   ⚠️  WARNING: Expected list, got {type(snippets).__name__}")
                
        except Exception as e:
            error_msg = f"Error retrieving snippets: {str(e)}"
            result["errors"].append(error_msg)
            print(f"   ❌ {error_msg}\n")
            import traceback
            result["errors"].append(traceback.format_exc())
        
        return result
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save results to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"snippet_verification_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {filename}")
            print(f"   File size: {os.path.getsize(filename):,} bytes")
            return filename
        except Exception as e:
            print(f"\n❌ Error saving results: {e}")
            return None


def load_saved_credentials() -> tuple:
    """Load credentials from config.json."""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        tsg_id = config.get('tsg_id', '')
        client_id = config.get('client_id', '')
        client_secret = config.get('client_secret', '')
        
        if not all([tsg_id, client_id, client_secret]):
            print("❌ Error: config.json is missing required credentials")
            print("   Please run setup_credentials.py first or provide credentials as arguments")
            return None, None, None
        
        return tsg_id, client_id, client_secret
    except FileNotFoundError:
        print("❌ Error: config.json not found")
        print("   Please run setup_credentials.py first or provide credentials as arguments")
        return None, None, None
    except json.JSONDecodeError:
        print("❌ Error: config.json is not valid JSON")
        return None, None, None


def main():
    """Main entry point."""
    print("=" * 70)
    print("Prisma Access Snippet Verifier")
    print("=" * 70)
    
    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--use-saved':
        print("\n📂 Loading credentials from config.json...")
        tsg_id, client_id, client_secret = load_saved_credentials()
        if not all([tsg_id, client_id, client_secret]):
            sys.exit(1)
    elif len(sys.argv) >= 3:
        tsg_id = sys.argv[1]
        client_id = sys.argv[2]
        client_secret = getpass.getpass("Enter client secret: ")
    else:
        print("\nUsage:")
        print("  python3 verify_snippets.py <tsg_id> <client_id>  # Prompts for secret")
        print("  python3 verify_snippets.py --use-saved           # Uses saved credentials")
        sys.exit(1)
    
    # Create verifier and connect
    verifier = SnippetVerifier(tsg_id, client_id, client_secret)
    if not verifier.connect():
        sys.exit(1)
    
    # Get snippets
    results = verifier.get_snippets()
    
    # Save results
    filename = verifier.save_results(results)
    
    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total snippets found: {results['snippet_count']}")
    print(f"Errors encountered: {len(results['errors'])}")
    
    if results['errors']:
        print("\n⚠️  Errors:")
        for error in results['errors']:
            print(f"   - {error}")
    
    print("\n✅ Verification complete!")
    print(f"📄 Review the full output in: {filename}")
    print("\nThe file contains:")
    print("   - Raw API response data")
    print("   - Parsed snippet information")
    print("   - Folder associations")
    print("   - Any errors encountered")
    print("=" * 70)


if __name__ == '__main__':
    main()
