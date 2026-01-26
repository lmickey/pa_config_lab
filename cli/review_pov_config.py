#!/usr/bin/env python3
"""
POV Configuration Review Tool

Evaluates a saved POV state file and presents the full configuration,
highlighting any missing dependencies.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple


class POVConfigReviewer:
    """Reviews POV configuration and identifies dependencies."""

    def __init__(self, state_path: str):
        self.state_path = Path(state_path)
        self.state = self._load_state()
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def _load_state(self) -> Dict[str, Any]:
        """Load state from JSON file."""
        with open(self.state_path) as f:
            return json.load(f)

    def review(self) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """Review configuration and return (config, issues, warnings)."""
        self._check_management_type()
        self._check_infrastructure()
        self._check_cloud_resources()
        self._check_use_cases()
        self._check_dependencies()

        return self._build_full_config(), self.issues, self.warnings

    def _check_management_type(self):
        """Check management type configuration."""
        mgmt = self.state.get('management_type', 'scm')
        if mgmt == 'panorama':
            # Check for Panorama device
            existing = self.state.get('cloud_resource_configs', {}).get('existing_devices', [])
            has_panorama = any(d.get('device_type') == 'Panorama' for d in existing)
            if not has_panorama:
                self.issues.append("Panorama Managed selected but no Panorama configured")

    def _check_infrastructure(self):
        """Check infrastructure configuration."""
        infra = self.state.get('cloud_resource_configs', {}).get('infrastructure', {})
        if not infra.get('configured'):
            self.warnings.append("Infrastructure not explicitly configured (using defaults)")

        # Check DNS
        dns = infra.get('dns', {})
        if not dns.get('primary'):
            self.warnings.append("No primary DNS configured")

        # Check internal DNS
        internal_dns = infra.get('internal_dns', {})
        if internal_dns.get('forward_domains'):
            domain_count = len(internal_dns.get('forward_domains', []))
            if domain_count > 0:
                print(f"  Internal DNS: {domain_count} forward domains configured")

    def _check_cloud_resources(self):
        """Check cloud resources configuration."""
        deploy_config = self.state.get('deployment_config', {})
        if not deploy_config.get('deploy_cloud_resources'):
            self.warnings.append("Cloud deployment disabled - no Azure resources will be deployed")

        # Check locations
        locations = self.state.get('cloud_resource_configs', {}).get('locations', {})
        datacenters = locations.get('datacenters', [])
        branches = locations.get('branches', [])

        if not datacenters and not branches:
            self.warnings.append("No locations (datacenters/branches) configured")

    def _check_use_cases(self):
        """Check use case configurations."""
        use_cases = self.state.get('use_case_configs', {})

        # Mobile Users
        mobile = use_cases.get('mobile_users', {})
        if mobile.get('enabled'):
            if not mobile.get('locations'):
                self.issues.append("Mobile Users enabled but no PA locations selected")
            if not mobile.get('portal_name'):
                self.warnings.append("Mobile Users: No portal name configured")

        # Private App
        private_app = use_cases.get('private_app', {})
        if private_app.get('enabled'):
            if not private_app.get('connections'):
                self.warnings.append("Private App enabled but no connections configured")

        # Remote Branch
        remote_branch = use_cases.get('remote_branch', {})
        if remote_branch.get('enabled'):
            if not remote_branch.get('bandwidth_allocations'):
                self.issues.append("Remote Branch enabled but no bandwidth allocated")

        # ADEM
        adem = use_cases.get('aiops_adem', {})
        if adem.get('enabled'):
            if not adem.get('tests'):
                self.warnings.append("ADEM enabled but no test targets configured")

        # Custom Policies
        custom_policies = use_cases.get('custom_policies', {})
        if custom_policies.get('enabled'):
            policies = custom_policies.get('policies', [])
            if not policies:
                self.warnings.append("Custom Security Policies enabled but no policies defined")

    def _check_dependencies(self):
        """Check cross-component dependencies."""
        use_cases = self.state.get('use_case_configs', {})
        cloud_configs = self.state.get('cloud_resource_configs', {})

        # Prisma Browser requires Explicit Proxy
        browser = use_cases.get('prisma_browser', {})
        mobile = use_cases.get('mobile_users', {})
        if browser.get('enabled') and browser.get('route_traffic') not in (None, 'None'):
            if not mobile.get('explicit_proxy'):
                self.issues.append("Prisma Browser routing requires Explicit Proxy (not enabled)")

        # Private App requires locations
        private_app = use_cases.get('private_app', {})
        locations = cloud_configs.get('locations', {})
        if private_app.get('enabled'):
            if not locations.get('datacenters') and not locations.get('branches'):
                self.warnings.append("Private App enabled but no locations (datacenters/branches) configured")

        # Remote Branch requires branches
        remote_branch = use_cases.get('remote_branch', {})
        if remote_branch.get('enabled'):
            if not locations.get('branches'):
                self.issues.append("Remote Branch enabled but no branches configured in Cloud Resources")

    def _build_full_config(self) -> Dict[str, Any]:
        """Build the full configuration summary."""
        return {
            'metadata': {
                'customer': self.state.get('customer'),
                'saved_at': self.state.get('saved_at'),
                'management_type': self.state.get('management_type'),
                'last_tab': self.state.get('last_tab'),
            },
            'infrastructure': self.state.get('cloud_resource_configs', {}).get('infrastructure', {}),
            'cloud_resources': {
                'deployment': self.state.get('cloud_resource_configs', {}).get('cloud_deployment', {}),
                'security': self.state.get('cloud_resource_configs', {}).get('cloud_security', {}),
                'locations': self.state.get('cloud_resource_configs', {}).get('locations', {}),
                'devices': self.state.get('cloud_resource_configs', {}).get('trust_devices', {}),
            },
            'use_cases': self.state.get('use_case_configs', {}),
            'existing_systems': self.state.get('cloud_resource_configs', {}).get('existing_devices', []),
        }

    def print_report(self):
        """Print formatted review report."""
        config, issues, warnings = self.review()

        print("=" * 60)
        print("POV Configuration Review")
        print("=" * 60)
        print(f"\nCustomer: {config['metadata'].get('customer', 'Not set')}")
        print(f"Management: {(config['metadata'].get('management_type') or 'scm').upper()}")
        print(f"Last Tab: {config['metadata'].get('last_tab', 'N/A')}")
        print(f"Saved: {config['metadata'].get('saved_at', 'N/A')}")

        # Infrastructure
        print("\n--- Infrastructure ---")
        infra = config['infrastructure']
        print(f"  Configured: {infra.get('configured', False)}")
        print(f"  Source: {infra.get('source', 'N/A')}")
        if infra.get('network'):
            print(f"  Subnet: {infra['network'].get('infrastructure_subnet', 'N/A')}")
            print(f"  BGP AS: {infra['network'].get('infrastructure_bgp_as', 'N/A')}")
        if infra.get('dns'):
            print(f"  Primary DNS: {infra['dns'].get('primary', 'N/A')}")
        if infra.get('internal_dns', {}).get('forward_domains'):
            domains = infra['internal_dns']['forward_domains']
            print(f"  Internal DNS Domains: {len(domains)}")
            for d in domains[:3]:  # Show first 3
                print(f"    - {d}")
            if len(domains) > 3:
                print(f"    ... and {len(domains) - 3} more")

        # Cloud Resources
        print("\n--- Cloud Resources ---")
        deploy = self.state.get('deployment_config', {})
        print(f"  Deploy Enabled: {deploy.get('deploy_cloud_resources', False)}")
        locations = config['cloud_resources']['locations']
        datacenters = locations.get('datacenters', [])
        branches = locations.get('branches', [])
        print(f"  Datacenters: {len(datacenters)}")
        for dc in datacenters[:3]:
            print(f"    - {dc.get('name', 'Unknown')}")
        if len(datacenters) > 3:
            print(f"    ... and {len(datacenters) - 3} more")
        print(f"  Branches: {len(branches)}")
        for br in branches[:3]:
            print(f"    - {br.get('name', 'Unknown')}")
        if len(branches) > 3:
            print(f"    ... and {len(branches) - 3} more")

        # Existing Systems
        existing = config.get('existing_systems', [])
        if existing:
            print("\n--- Existing Systems ---")
            for device in existing:
                dtype = device.get('device_type', 'Unknown')
                ip = device.get('mgmt_ip', 'No IP')
                placeholder = " (placeholder)" if device.get('placeholder') else ""
                print(f"  - {dtype}: {ip}{placeholder}")

        # Use Cases
        print("\n--- Use Cases ---")
        use_case_names = {
            'mobile_users': 'Mobile Users (GlobalProtect)',
            'prisma_browser': 'Prisma Access Browser',
            'private_app': 'Private App Access',
            'remote_branch': 'Remote Branch (IPSec)',
            'aiops_adem': 'AIOPS-ADEM',
            'app_accel': 'App Acceleration',
            'rbi': 'Remote Browser Isolation',
            'custom_policies': 'Custom Security Policies',
        }
        for key, name in use_case_names.items():
            uc = config['use_cases'].get(key, {})
            status = "+" if uc.get('enabled') else "-"
            print(f"  {status} {name}")

            # Show details for enabled use cases
            if uc.get('enabled'):
                if key == 'mobile_users':
                    locs = uc.get('locations', [])
                    if locs:
                        print(f"      Locations: {', '.join(locs[:5])}")
                    portal = uc.get('portal_name')
                    if portal:
                        print(f"      Portal: {portal}.gpcloudservice.com")
                elif key == 'private_app':
                    conns = uc.get('connections', [])
                    if conns:
                        print(f"      Connections: {len(conns)}")
                elif key == 'remote_branch':
                    bw = uc.get('bandwidth_allocations', [])
                    if bw:
                        total = sum(a.get('bandwidth', 0) for a in bw)
                        print(f"      Bandwidth: {total} Mbps across {len(bw)} allocations")
                elif key == 'aiops_adem':
                    tests = uc.get('tests', [])
                    if tests:
                        print(f"      Test targets: {len(tests)}")
                        for t in tests[:3]:
                            print(f"        - {t.get('target', 'Unknown')}")
                elif key == 'custom_policies':
                    policies = uc.get('policies', [])
                    if policies:
                        print(f"      Policies: {len(policies)}")
                        for p in policies[:3]:
                            print(f"        - {p}")
                        if len(policies) > 3:
                            print(f"        ... and {len(policies) - 3} more")

        # Staged Security Objects
        custom_policies = config['use_cases'].get('custom_policies', {})
        staged = custom_policies.get('staged_objects', {})
        if staged:
            print("\n--- Staged Security Objects ---")

            # Address objects
            addr_objs = staged.get('address_objects', [])
            if addr_objs:
                print(f"  Address Objects: {len(addr_objs)}")
                for obj in addr_objs[:5]:
                    name = obj.get('name', 'Unknown')
                    value = obj.get('ip_netmask', obj.get('fqdn', 'N/A'))
                    print(f"    - {name}: {value}")
                if len(addr_objs) > 5:
                    print(f"    ... and {len(addr_objs) - 5} more")

            # Address groups
            addr_groups = staged.get('address_groups', [])
            if addr_groups:
                print(f"  Address Groups: {len(addr_groups)}")
                for grp in addr_groups:
                    name = grp.get('name', 'Unknown')
                    members = grp.get('static', [])
                    print(f"    - {name} ({len(members)} members)")

            # Security profiles
            profiles = staged.get('profiles', {})
            total_profiles = sum(len(v) for v in profiles.values())
            if total_profiles > 0:
                print(f"  Security Profiles: {total_profiles}")
                for ptype, plist in profiles.items():
                    for p in plist:
                        print(f"    - {p.get('name', 'Unknown')} ({ptype})")

            # Profile groups
            profile_groups = staged.get('profile_groups', [])
            if profile_groups:
                print(f"  Profile Groups: {len(profile_groups)}")
                for pg in profile_groups:
                    print(f"    - {pg.get('name', 'Unknown')}")

            # Metadata
            prefix = custom_policies.get('customer_prefix', '')
            source = custom_policies.get('source_tenant', '')
            generated = custom_policies.get('generated_at', '')
            if prefix:
                print(f"  Customer Prefix: {prefix}")
            if source:
                print(f"  Profiles Cloned From: {source}")
            if generated:
                print(f"  Generated: {generated}")

        # Issues
        if issues:
            print("\n--- ISSUES (Must Fix) ---")
            for issue in issues:
                print(f"  X {issue}")

        # Warnings
        if warnings:
            print("\n--- WARNINGS ---")
            for warning in warnings:
                print(f"  ! {warning}")

        if not issues and not warnings:
            print("\n+ Configuration looks complete!")

        print()


def find_latest_state_file() -> Path:
    """Find the most recent POV state file."""
    state_dir = Path.home() / '.claude' / 'pov_states'
    if not state_dir.exists():
        return None

    state_files = list(state_dir.glob('pov_state_*.json'))
    if not state_files:
        return None

    return max(state_files, key=lambda p: p.stat().st_mtime)


def main():
    if len(sys.argv) < 2:
        # Find most recent state file
        state_file = find_latest_state_file()
        if not state_file:
            print("Usage: python review_pov_config.py <state_file.json>")
            print("\nNo state files found in ~/.claude/pov_states/")
            print("Run the POV Builder GUI and save a configuration first.")
            sys.exit(1)

        print(f"Using most recent: {state_file}\n")
    else:
        state_file = Path(sys.argv[1])
        if not state_file.exists():
            print(f"Error: State file not found: {state_file}")
            sys.exit(1)

    reviewer = POVConfigReviewer(str(state_file))
    reviewer.print_report()


if __name__ == '__main__':
    main()
