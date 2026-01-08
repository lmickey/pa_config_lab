#!/usr/bin/env python3
"""
Setup Credentials - Save Prisma Access credentials for testing
Usage: python3 setup_credentials.py
"""

import json
import getpass
import os


def main():
    print("\n🔐 Prisma Access Credentials Setup")
    print("=" * 80)
    print("This will save your credentials to config.json for testing.")
    print("=" * 80)
    print()
    
    # Get credentials
    tsg_id = input("Enter TSG ID: ").strip()
    if not tsg_id:
        print("❌ TSG ID is required")
        return
    
    client_id = input("Enter Client ID (e.g., myapp@12345.iam.panserviceaccount.com): ").strip()
    if not client_id:
        print("❌ Client ID is required")
        return
    
    client_secret = getpass.getpass("Enter Client Secret: ").strip()
    if not client_secret:
        print("❌ Client Secret is required")
        return
    
    # Validate format
    if "@" not in client_id or "iam.panserviceaccount.com" not in client_id:
        print("⚠️  Warning: Client ID format looks unusual. Should end with @...iam.panserviceaccount.com")
        confirm = input("Continue anyway? (y/N): ").lower()
        if confirm != 'y':
            print("Aborted.")
            return
    
    # Create config
    config = {
        "tsg_id": tsg_id,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    # Backup existing config if it exists
    if os.path.exists("config.json"):
        backup_file = "config.json.backup"
        print(f"\n📦 Backing up existing config.json to {backup_file}")
        with open("config.json", 'r') as f:
            old_config = f.read()
        with open(backup_file, 'w') as f:
            f.write(old_config)
    
    # Save new config
    with open("config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n✅ Credentials saved to config.json")
    print("\nYou can now run:")
    print("  python3 validate_endpoints.py --use-saved")
    print()


if __name__ == "__main__":
    main()
