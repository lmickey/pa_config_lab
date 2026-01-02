#!/usr/bin/env python3
"""
Sanitize production configuration examples.

This script takes raw production configurations and sanitizes them for
inclusion in test examples by:
- Replacing real IPs with RFC 5737 test IPs
- Replacing real FQDNs with example.com/example.net
- Replacing passwords/secrets with placeholder
- Replacing real names with generic names
- Preserving structure and relationships

Usage:
    python scripts/sanitize_examples.py
    python scripts/sanitize_examples.py --input tests/examples/production/raw --output tests/examples/production
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ExampleSanitizer:
    """Sanitizes production configuration examples"""
    
    # RFC 5737 TEST-NET IP ranges for sanitization
    TEST_IPS = {
        '10.': '203.0.113.',     # TEST-NET-3
        '172.': '198.51.100.',   # TEST-NET-2
        '192.168.': '192.0.2.',  # TEST-NET-1
    }
    
    # Common password/secret fields
    SECRET_FIELDS = [
        'password', 'secret', 'api_key', 'token', 'private_key',
        'passphrase', 'shared_secret', 'pre_shared_key', 'psk'
    ]
    
    def __init__(self):
        self.ip_mapping = {}
        self.fqdn_mapping = {}
        self.name_mapping = {}
        self.stats = {
            'files_processed': 0,
            'ips_sanitized': 0,
            'fqdns_sanitized': 0,
            'secrets_sanitized': 0,
            'names_sanitized': 0
        }
    
    def sanitize_file(self, input_path: Path, output_path: Path):
        """Sanitize a single file"""
        try:
            with open(input_path, 'r') as f:
                data = json.load(f)
            
            # Sanitize the configuration
            sanitized = self._sanitize_dict(data)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save sanitized version
            with open(output_path, 'w') as f:
                json.dump(sanitized, f, indent=2)
            
            self.stats['files_processed'] += 1
            
        except Exception as e:
            print(f"Error sanitizing {input_path}: {e}")
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize a dictionary recursively"""
        result = {}
        
        for key, value in data.items():
            # Check if this is a secret field
            if key.lower() in self.SECRET_FIELDS:
                result[key] = "********"
                self.stats['secrets_sanitized'] += 1
            elif isinstance(value, dict):
                result[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                result[key] = self._sanitize_list(value)
            elif isinstance(value, str):
                result[key] = self._sanitize_string(value, key)
            else:
                result[key] = value
        
        return result
    
    def _sanitize_list(self, data: List[Any]) -> List[Any]:
        """Sanitize a list recursively"""
        result = []
        
        for item in data:
            if isinstance(item, dict):
                result.append(self._sanitize_dict(item))
            elif isinstance(item, list):
                result.append(self._sanitize_list(item))
            elif isinstance(item, str):
                result.append(self._sanitize_string(item, None))
            else:
                result.append(item)
        
        return result
    
    def _sanitize_string(self, value: str, key: Optional[str] = None) -> str:
        """Sanitize a string value"""
        # Sanitize IPs
        value = self._sanitize_ip(value)
        
        # Sanitize FQDNs
        value = self._sanitize_fqdn(value)
        
        # Sanitize names (if key indicates it's a name field)
        if key and key.lower() in ['name', 'username', 'user', 'owner']:
            value = self._sanitize_name(value)
        
        return value
    
    def _sanitize_ip(self, value: str) -> str:
        """Sanitize IP addresses"""
        # Pattern for IPv4 addresses
        ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
        
        def replace_ip(match):
            original_ip = match.group(1)
            
            # Skip if already a test IP
            if original_ip.startswith(('203.0.113.', '198.51.100.', '192.0.2.')):
                return original_ip
            
            # Check if we've seen this IP before
            if original_ip in self.ip_mapping:
                return self.ip_mapping[original_ip]
            
            # Generate new test IP
            octets = original_ip.split('.')
            if octets[0] == '10':
                test_ip = f"203.0.113.{octets[3]}"
            elif octets[0] == '172':
                test_ip = f"198.51.100.{octets[3]}"
            elif octets[0] == '192':
                test_ip = f"192.0.2.{octets[3]}"
            else:
                # Public IP - use TEST-NET-1
                test_ip = f"192.0.2.{len(self.ip_mapping) + 1}"
            
            self.ip_mapping[original_ip] = test_ip
            self.stats['ips_sanitized'] += 1
            
            return test_ip
        
        return re.sub(ip_pattern, replace_ip, value)
    
    def _sanitize_fqdn(self, value: str) -> str:
        """Sanitize FQDNs"""
        # Pattern for FQDNs
        fqdn_pattern = r'\b([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
        
        def replace_fqdn(match):
            original_fqdn = match.group(0)
            
            # Skip if already example domain
            if 'example.com' in original_fqdn or 'example.net' in original_fqdn:
                return original_fqdn
            
            # Skip common service domains
            skip_domains = ['paloaltonetworks.com', 'api.sase.paloaltonetworks.com', 'google.com', 'microsoft.com']
            if any(domain in original_fqdn for domain in skip_domains):
                return original_fqdn
            
            # Check if we've seen this FQDN before
            if original_fqdn in self.fqdn_mapping:
                return self.fqdn_mapping[original_fqdn]
            
            # Generate new example FQDN
            parts = original_fqdn.split('.')
            if len(parts) == 2:
                # domain.com -> exampleN.com
                test_fqdn = f"example{len(self.fqdn_mapping) + 1}.com"
            else:
                # subdomain.domain.com -> subdomainN.example.com
                test_fqdn = f"{parts[0]}{len(self.fqdn_mapping) + 1}.example.com"
            
            self.fqdn_mapping[original_fqdn] = test_fqdn
            self.stats['fqdns_sanitized'] += 1
            
            return test_fqdn
        
        return re.sub(fqdn_pattern, replace_fqdn, value)
    
    def _sanitize_name(self, value: str) -> str:
        """Sanitize names while preserving pattern"""
        # Skip if already looks generic
        if value.lower().startswith(('test-', 'example-', 'generic-', 'internal-')):
            return value
        
        # Check if we've seen this name before
        if value in self.name_mapping:
            return self.name_mapping[value]
        
        # Generate generic name preserving structure
        # Keep hyphens, underscores, spaces
        if '-' in value:
            separator = '-'
        elif '_' in value:
            separator = '_'
        elif ' ' in value:
            separator = ' '
        else:
            # No separator, just make it generic
            generic_name = f"generic-item-{len(self.name_mapping) + 1}"
            self.name_mapping[value] = generic_name
            self.stats['names_sanitized'] += 1
            return generic_name
        
        # Preserve structure with separator
        parts = value.split(separator)
        generic_parts = [f"item{i+1}" for i in range(len(parts))]
        generic_name = separator.join(generic_parts)
        
        self.name_mapping[value] = generic_name
        self.stats['names_sanitized'] += 1
        
        return generic_name
    
    def sanitize_directory(self, input_dir: Path, output_dir: Path):
        """Sanitize all files in a directory"""
        print("=" * 60)
        print("SANITIZING PRODUCTION EXAMPLES")
        print("=" * 60)
        print(f"Input:  {input_dir}")
        print(f"Output: {output_dir}")
        print()
        
        # Find all JSON files
        json_files = list(input_dir.rglob('*.json'))
        print(f"Found {len(json_files)} files to sanitize")
        print()
        
        # Process each file
        for json_file in json_files:
            # Determine output path (preserve directory structure)
            rel_path = json_file.relative_to(input_dir)
            output_path = output_dir / rel_path
            
            print(f"Processing: {rel_path}", end=" ", flush=True)
            self.sanitize_file(json_file, output_path)
            print("✓")
        
        # Print summary
        print()
        print("=" * 60)
        print("SANITIZATION SUMMARY")
        print("=" * 60)
        print(f"Files processed:   {self.stats['files_processed']}")
        print(f"IPs sanitized:     {self.stats['ips_sanitized']}")
        print(f"FQDNs sanitized:   {self.stats['fqdns_sanitized']}")
        print(f"Secrets sanitized: {self.stats['secrets_sanitized']}")
        print(f"Names sanitized:   {self.stats['names_sanitized']}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Sanitize production configuration examples",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('tests/examples/production/raw'),
        help='Input directory with raw examples'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('tests/examples/production'),
        help='Output directory for sanitized examples'
    )
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"Error: Input directory does not exist: {args.input}")
        return 1
    
    # Create sanitizer
    sanitizer = ExampleSanitizer()
    
    # Sanitize all files
    sanitizer.sanitize_directory(args.input, args.output)
    
    print()
    print("✓ Sanitization complete!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
