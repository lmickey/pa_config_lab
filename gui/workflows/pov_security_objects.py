"""
Security object generator for POV Builder.

Automatically generates address objects, address groups, and clones security profiles
based on POV configuration from earlier tabs.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SecurityObjectGenerator:
    """Generates security objects from POV configuration."""

    def __init__(
        self,
        customer_prefix: str,
        cloud_resource_configs: Dict[str, Any],
        use_case_configs: Dict[str, Any],
    ):
        """
        Initialize the security object generator.

        Args:
            customer_prefix: Sanitized customer name for object naming
            cloud_resource_configs: Configuration from Tabs 1-2
            use_case_configs: Use case configuration from Tab 3
        """
        self.prefix = customer_prefix
        self.cloud_configs = cloud_resource_configs
        self.use_cases = use_case_configs

    def generate_all(self) -> Dict[str, Any]:
        """
        Generate all security objects based on POV configuration.

        Returns:
            Dictionary with address_objects and address_groups
        """
        address_objects = self._generate_address_objects()
        address_groups = self._generate_address_groups(address_objects)

        return {
            'address_objects': address_objects,
            'address_groups': address_groups,
        }

    def _generate_address_objects(self) -> List[Dict[str, Any]]:
        """Generate address objects from infrastructure config."""
        objects = []

        # Infrastructure network (from Tab 1)
        infra = self.cloud_configs.get('infrastructure', {})
        network = infra.get('network', {})
        infra_subnet = network.get('infrastructure_subnet', '')

        if infra_subnet:
            objects.append({
                'name': f'{self.prefix}-infrastructure-network',
                'folder': 'Shared',
                'ip_netmask': infra_subnet,
                'description': f'{self.prefix} Prisma Access infrastructure network',
                'tag': [f'{self.prefix}-pov', 'infrastructure'],
            })

        # ZTNA networks (from Tab 1 infrastructure config)
        ztna = infra.get('ztna', {})

        app_networks = ztna.get('application_networks', [])
        for i, net in enumerate(app_networks):
            if net:
                objects.append({
                    'name': f'{self.prefix}-ztna-app-network-{i+1}',
                    'folder': 'Shared',
                    'ip_netmask': net,
                    'description': f'{self.prefix} ZTNA application network',
                    'tag': [f'{self.prefix}-pov', 'ztna'],
                })

        controller_networks = ztna.get('controller_networks', [])
        for i, net in enumerate(controller_networks):
            if net:
                objects.append({
                    'name': f'{self.prefix}-ztna-controller-network-{i+1}',
                    'folder': 'Shared',
                    'ip_netmask': net,
                    'description': f'{self.prefix} ZTNA controller network',
                    'tag': [f'{self.prefix}-pov', 'ztna'],
                })

        # Mobile Users - GlobalProtect IP pools
        # These are dynamically assigned by PA, but we create a placeholder
        # that can be updated with actual pool ranges
        mobile_users = self.use_cases.get('mobile_users', {})
        if mobile_users.get('enabled'):
            # Default GP pool ranges (can be customized)
            objects.append({
                'name': f'{self.prefix}-mobile-users-pool',
                'folder': 'Mobile Users',
                'ip_netmask': '10.100.0.0/16',  # Default placeholder
                'description': f'{self.prefix} Mobile Users GlobalProtect IP pool',
                'tag': [f'{self.prefix}-pov', 'mobile-users'],
            })

        return objects

    def _generate_address_groups(
        self,
        address_objects: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate address groups combining the address objects."""
        groups = []

        # Collect all generated address names
        all_addresses = [obj['name'] for obj in address_objects]

        # Create combined group for all internal networks
        if all_addresses:
            groups.append({
                'name': f'{self.prefix}-all-internal-networks',
                'folder': 'Shared',
                'static': all_addresses,
                'description': f'{self.prefix} all internal POV networks',
                'tag': [f'{self.prefix}-pov'],
            })

        return groups


class ProfileCloner:
    """Clones security profiles from connected tenant."""

    # Profile types to clone with their API method names
    PROFILE_TYPES = [
        ('anti_spyware', 'get_anti_spyware_profiles'),
        ('vulnerability', 'get_vulnerability_protection_profiles'),
        ('file_blocking', 'get_file_blocking_profiles'),
        ('wildfire', 'get_wildfire_anti_virus_profiles'),
        ('dns_security', 'get_dns_security_profiles'),
    ]

    # Default profiles that can be cloned (in order of preference)
    CLONABLE_DEFAULTS = ['best-practice', 'strict', 'default']

    def __init__(
        self,
        api_client,
        customer_prefix: str,
        source_profile: str = 'best-practice',
    ):
        """
        Initialize the profile cloner.

        Args:
            api_client: Connected SCM API client
            customer_prefix: Sanitized customer name for object naming
            source_profile: Name of default profile to clone from
        """
        self.api_client = api_client
        self.prefix = customer_prefix
        self.source_profile = source_profile

    def clone_all_profiles(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Clone all security profile types from the connected tenant.

        Returns:
            Dictionary mapping profile type to list of cloned profiles
        """
        cloned = {}

        for profile_type, method_name in self.PROFILE_TYPES:
            try:
                profiles = self._clone_profile_type(profile_type, method_name)
                cloned[profile_type] = profiles
                if profiles:
                    logger.info(f"Cloned {len(profiles)} {profile_type} profile(s)")
            except Exception as e:
                logger.warning(f"Failed to clone {profile_type} profiles: {e}")
                cloned[profile_type] = []

        return cloned

    def _clone_profile_type(
        self,
        profile_type: str,
        method_name: str
    ) -> List[Dict[str, Any]]:
        """Clone a specific profile type."""
        # Get the API method
        method = getattr(self.api_client, method_name, None)
        if not method:
            logger.warning(f"API method {method_name} not found")
            return []

        try:
            # Fetch profiles from Shared folder
            profiles = method(folder='Shared')
        except Exception as e:
            logger.warning(f"Could not fetch {profile_type} profiles: {e}")
            return []

        if not profiles:
            logger.info(f"No {profile_type} profiles found in tenant")
            return []

        # Find the source profile (try each default in order)
        source = None
        for default_name in self.CLONABLE_DEFAULTS:
            for p in profiles:
                if p.get('name') == default_name:
                    source = p
                    break
            if source:
                break

        if not source:
            # Try partial match
            for p in profiles:
                name = p.get('name', '').lower()
                if 'best' in name or 'practice' in name:
                    source = p
                    break

        if not source:
            logger.info(f"No clonable default profile found for {profile_type}")
            return []

        # Clone with new name
        cloned = self._prepare_profile_for_clone(source, profile_type)
        return [cloned] if cloned else []

    def _prepare_profile_for_clone(
        self,
        source: Dict[str, Any],
        profile_type: str
    ) -> Dict[str, Any]:
        """Prepare a profile for cloning by renaming and cleaning."""
        # Deep copy to avoid modifying original
        import copy
        cloned = copy.deepcopy(source)

        # Remove fields that shouldn't be pushed
        cloned.pop('id', None)
        cloned.pop('is_default', None)
        cloned.pop('snippet', None)

        # Rename with customer prefix
        original_name = cloned.get('name', profile_type)
        cloned['name'] = f'{self.prefix}-{profile_type}'

        # Update description
        orig_desc = cloned.get('description', '')
        cloned['description'] = f'{self.prefix} POV - cloned from {original_name}. {orig_desc}'.strip()

        # Set target folder
        cloned['folder'] = 'Shared'

        return cloned

    def create_profile_group(
        self,
        cloned_profiles: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Create a profile group referencing the cloned profiles.

        Args:
            cloned_profiles: Output from clone_all_profiles()

        Returns:
            Profile group configuration
        """
        group = {
            'name': f'{self.prefix}-security-profile-group',
            'folder': 'Shared',
            'description': f'{self.prefix} POV security profile group',
        }

        # Map profile type to group field name
        type_to_field = {
            'anti_spyware': 'spyware',
            'vulnerability': 'vulnerability',
            'file_blocking': 'file_blocking',
            'wildfire': 'wildfire_analysis',
            'dns_security': 'dns_security',
        }

        for profile_type, profiles in cloned_profiles.items():
            if profiles and profile_type in type_to_field:
                field = type_to_field[profile_type]
                group[field] = [p['name'] for p in profiles]

        return group


def generate_staged_objects(
    customer_prefix: str,
    cloud_resource_configs: Dict[str, Any],
    use_case_configs: Dict[str, Any],
    api_client=None,
) -> Dict[str, Any]:
    """
    Convenience function to generate all staged security objects.

    Args:
        customer_prefix: Sanitized customer name
        cloud_resource_configs: Configuration from Tabs 1-2
        use_case_configs: Use case configuration from Tab 3
        api_client: Optional connected API client for profile cloning

    Returns:
        Complete staged_objects dictionary
    """
    # Generate address objects and groups
    generator = SecurityObjectGenerator(
        customer_prefix=customer_prefix,
        cloud_resource_configs=cloud_resource_configs,
        use_case_configs=use_case_configs,
    )
    staged = generator.generate_all()

    # Clone profiles if tenant connected
    if api_client:
        try:
            cloner = ProfileCloner(
                api_client=api_client,
                customer_prefix=customer_prefix,
            )
            cloned_profiles = cloner.clone_all_profiles()
            profile_group = cloner.create_profile_group(cloned_profiles)

            staged['profiles'] = cloned_profiles
            staged['profile_groups'] = [profile_group] if any(cloned_profiles.values()) else []
        except Exception as e:
            logger.warning(f"Failed to clone profiles: {e}")
            staged['profiles'] = {}
            staged['profile_groups'] = []
    else:
        staged['profiles'] = {}
        staged['profile_groups'] = []

    return staged
