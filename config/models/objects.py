"""
Object model classes for network objects.

This module contains ConfigItem subclasses for network objects including:
- Tags
- Address objects (IP addresses, ranges, FQDNs)
- Address groups (static and dynamic)
- Service objects (TCP/UDP services)
- Service groups
- Application objects
- Application groups
- Application filters
- Schedules
"""

from typing import List, Dict, Any, Optional
import logging
from config.models.base import ConfigItem, ObjectItem

logger = logging.getLogger(__name__)


class Tag(ConfigItem):
    """
    Represents a tag object.
    
    API Endpoint: /sse/config/v1/tags
    
    Tags are special - they can have BOTH folder AND snippet set simultaneously,
    unlike other configuration items where folder and snippet are mutually exclusive.
    
    Attributes:
        - color: Tag color (optional)
        - comments: Tag comments (optional)
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/tags"
    item_type = "tag"
    
    def __init__(self, raw_config: Dict[str, Any]):
        """
        Initialize Tag object.
        
        Override __init__ to allow both folder and snippet to be set,
        as tags are the exception to the mutual exclusivity rule.
        """
        # Store raw config first
        self.raw_config = raw_config.copy()
        self.name = raw_config.get('name', '')
        self.id = raw_config.get('id')
        
        # Tags can have both folder AND snippet - this is valid!
        self.folder = raw_config.get('folder')
        self.snippet = raw_config.get('snippet')
        
        # At least one must be set
        if not self.folder and not self.snippet:
            raise ValueError(f"Tag must have at least folder or snippet set for {self.name}")
        
        self.is_default = raw_config.get('is_default', False)
        self.push_strategy = 'create'
        self.metadata = raw_config.get('metadata', {})
        if not self.metadata:
            self.metadata = self._extract_metadata(raw_config)
        
        self.deleted = False
        self.delete_success: Optional[bool] = None
        self._dependencies_cache: Optional[List[tuple]] = None
        self._parent_cache = None
        self._children_cache = None
    
    @property
    def color(self) -> Optional[str]:
        """Get tag color"""
        return self.raw_config.get('color')
    
    @property
    def comments(self) -> Optional[str]:
        """Get tag comments"""
        return self.raw_config.get('comments')
    
    def get_location(self) -> str:
        """
        Get location string for tag.
        
        Since tags can have both folder and snippet, we return a combined string.
        """
        if self.folder and self.snippet:
            return f"{self.folder} (snippet: {self.snippet})"
        elif self.folder:
            return self.folder
        else:
            return self.snippet
    
    def _validate_specific(self) -> List[str]:
        """Validate tag object"""
        errors = []
        
        # At least one of folder or snippet must be set
        if not self.folder and not self.snippet:
            errors.append("Tag must have at least folder or snippet set")
        
        # Color must be from valid set if specified
        valid_colors = [
            'Red', 'Green', 'Blue', 'Yellow', 'Copper', 'Orange', 'Purple',
            'Gray', 'Light Green', 'Cyan', 'Light Gray', 'Blue Gray',
            'Lime', 'Black', 'Gold', 'Brown', 'Olive', 'Maroon',
            'Red-Orange', 'Yellow-Orange', 'Forest Green', 'Turquoise Blue',
            'Azure Blue', 'Cerulean Blue', 'Midnight Blue', 'Medium Blue',
            'Cobalt Blue', 'Violet Blue', 'Blue Violet', 'Medium Violet',
            'Medium Rose', 'Lavender', 'Orchid', 'Thistle', 'Peach',
            'Salmon', 'Magenta', 'Red Violet', 'Mahogany', 'Burnt Sienna',
            'Chestnut'
        ]
        
        if self.color and self.color not in valid_colors:
            errors.append(f"Invalid color '{self.color}'. Must be one of the predefined colors.")
        
        return errors


class AddressObject(ObjectItem):
    """
    Represents an address object (IP address, FQDN, IP range, etc.)
    
    API Endpoint: /sse/config/v1/addresses
    
    Examples:
        - IP/Netmask: 192.168.1.0/24
        - FQDN: example.com
        - IP Range: 10.0.0.1-10.0.0.100
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/addresses"
    item_type = "address_object"
    
    @property
    def address_type(self) -> Optional[str]:
        """Get the type of address (ip_netmask, fqdn, ip_range, ip_wildcard)"""
        for addr_type in ['ip_netmask', 'fqdn', 'ip_range', 'ip_wildcard']:
            if addr_type in self.raw_config:
                return addr_type
        return None
    
    @property
    def address_value(self) -> Optional[str]:
        """Get the actual address value"""
        addr_type = self.address_type
        if addr_type:
            return self.raw_config.get(addr_type)
        return None
    
    def _validate_specific(self) -> List[str]:
        """Validate address object"""
        errors = []
        
        # Must have exactly one address type
        addr_types = [t for t in ['ip_netmask', 'fqdn', 'ip_range', 'ip_wildcard'] 
                     if t in self.raw_config]
        
        if len(addr_types) == 0:
            errors.append("Address object must have one address type (ip_netmask, fqdn, ip_range, or ip_wildcard)")
        elif len(addr_types) > 1:
            errors.append(f"Address object must have exactly one address type, found: {addr_types}")
        
        # Validate the address value exists
        if addr_types and not self.raw_config.get(addr_types[0]):
            errors.append(f"Address value for {addr_types[0]} cannot be empty")
        
        return errors


class AddressGroup(ObjectItem):
    """
    Represents an address group (collection of address objects)
    
    API Endpoint: /sse/config/v1/address-groups
    
    Types:
        - Static: Explicit list of addresses
        - Dynamic: Filter-based membership
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/address-groups"
    item_type = "address_group"
    
    @property
    def is_static(self) -> bool:
        """Check if this is a static address group"""
        return 'static' in self.raw_config
    
    @property
    def is_dynamic(self) -> bool:
        """Check if this is a dynamic address group"""
        return 'dynamic' in self.raw_config
    
    @property
    def members(self) -> List[str]:
        """Get list of member addresses (for static groups)"""
        if self.is_static:
            return self.raw_config.get('static', [])
        return []
    
    @property
    def filter(self) -> Optional[str]:
        """Get dynamic filter (for dynamic groups)"""
        if self.is_dynamic:
            dynamic = self.raw_config.get('dynamic', {})
            return dynamic.get('filter') if isinstance(dynamic, dict) else None
        return None
    
    @property
    def has_dependencies(self) -> bool:
        """Override has_dependencies - only static groups have dependencies"""
        return self.is_static and len(self.members) > 0
    
    def _compute_dependencies(self) -> List[tuple]:
        """Address groups depend on their member addresses (static only)"""
        deps = []
        if self.is_static:
            for member in self.members:
                deps.append(('address_object', member))
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate address group"""
        errors = []
        
        # Must be either static or dynamic, but not both
        if not self.is_static and not self.is_dynamic:
            errors.append("Address group must be either static or dynamic")
        elif self.is_static and self.is_dynamic:
            errors.append("Address group cannot be both static and dynamic")
        
        # Static groups must have at least one member
        if self.is_static and len(self.members) == 0:
            errors.append("Static address group must have at least one member")
        
        # Dynamic groups must have a filter
        if self.is_dynamic and not self.filter:
            errors.append("Dynamic address group must have a filter")
        
        return errors


class ServiceObject(ObjectItem):
    """
    Represents a service object (TCP/UDP port definition)
    
    API Endpoint: /sse/config/v1/services
    
    Protocols:
        - TCP: port, source_port
        - UDP: port, source_port
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/services"
    item_type = "service_object"
    
    @property
    def protocol_type(self) -> Optional[str]:
        """Get the protocol type (tcp or udp)"""
        if 'protocol' in self.raw_config:
            protocol = self.raw_config['protocol']
            if isinstance(protocol, dict):
                if 'tcp' in protocol:
                    return 'tcp'
                elif 'udp' in protocol:
                    return 'udp'
        return None
    
    @property
    def port(self) -> Optional[str]:
        """Get the destination port(s)"""
        protocol_type = self.protocol_type
        if protocol_type and 'protocol' in self.raw_config:
            protocol_config = self.raw_config['protocol'].get(protocol_type, {})
            return protocol_config.get('port')
        return None
    
    @property
    def source_port(self) -> Optional[str]:
        """Get the source port(s)"""
        protocol_type = self.protocol_type
        if protocol_type and 'protocol' in self.raw_config:
            protocol_config = self.raw_config['protocol'].get(protocol_type, {})
            return protocol_config.get('source_port')
        return None
    
    def _validate_specific(self) -> List[str]:
        """Validate service object"""
        errors = []
        
        # Must have protocol configuration
        if 'protocol' not in self.raw_config:
            errors.append("Service object must have protocol configuration")
            return errors
        
        protocol = self.raw_config['protocol']
        if not isinstance(protocol, dict):
            errors.append("Protocol must be a dictionary")
            return errors
        
        # Must have either tcp or udp
        if 'tcp' not in protocol and 'udp' not in protocol:
            errors.append("Service object must specify either tcp or udp protocol")
        
        # Validate port is specified
        protocol_type = self.protocol_type
        if protocol_type:
            protocol_config = protocol.get(protocol_type, {})
            if not protocol_config.get('port'):
                errors.append(f"Service object must specify destination port for {protocol_type}")
        
        return errors


class ServiceGroup(ObjectItem):
    """
    Represents a service group (collection of service objects)
    
    API Endpoint: /sse/config/v1/service-groups
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/service-groups"
    item_type = "service_group"
    
    @property
    def members(self) -> List[str]:
        """Get list of member services"""
        return self.raw_config.get('members', [])
    
    def _compute_dependencies(self) -> List[tuple]:
        """Service groups depend on their member services"""
        deps = []
        for member in self.members:
            deps.append(('service_object', member))
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate service group"""
        errors = []
        
        # Must have at least one member
        if len(self.members) == 0:
            errors.append("Service group must have at least one member")
        
        return errors


class ApplicationObject(ObjectItem):
    """
    Represents a custom application object
    
    API Endpoint: /sse/config/v1/applications
    
    Attributes:
        - category: Application category
        - subcategory: Application subcategory
        - technology: Technology type
        - risk: Risk level (1-5)
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/applications"
    item_type = "application_object"
    
    @property
    def category(self) -> Optional[str]:
        """Get application category"""
        return self.raw_config.get('category')
    
    @property
    def subcategory(self) -> Optional[str]:
        """Get application subcategory"""
        return self.raw_config.get('subcategory')
    
    @property
    def technology(self) -> Optional[str]:
        """Get technology type"""
        return self.raw_config.get('technology')
    
    @property
    def risk(self) -> Optional[int]:
        """Get risk level (1-5)"""
        return self.raw_config.get('risk')
    
    def _validate_specific(self) -> List[str]:
        """Validate application object"""
        errors = []
        
        # Required fields
        if not self.category:
            errors.append("Application must have a category")
        
        if not self.subcategory:
            errors.append("Application must have a subcategory")
        
        if not self.technology:
            errors.append("Application must have a technology")
        
        # Risk must be 1-5 if specified
        if self.risk is not None and (self.risk < 1 or self.risk > 5):
            errors.append(f"Application risk must be between 1 and 5, got {self.risk}")
        
        return errors


class ApplicationGroup(ObjectItem):
    """
    Represents an application group (collection of applications)
    
    API Endpoint: /sse/config/v1/application-groups
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/application-groups"
    item_type = "application_group"
    
    @property
    def members(self) -> List[str]:
        """Get list of member applications"""
        return self.raw_config.get('members', [])
    
    def _compute_dependencies(self) -> List[tuple]:
        """Application groups depend on their member applications"""
        deps = []
        for member in self.members:
            deps.append(('application_object', member))
        return deps
    
    def _validate_specific(self) -> List[str]:
        """Validate application group"""
        errors = []
        
        # Must have at least one member
        if len(self.members) == 0:
            errors.append("Application group must have at least one member")
        
        return errors


class ApplicationFilter(ObjectItem):
    """
    Represents an application filter (dynamic application selection)
    
    API Endpoint: /sse/config/v1/application-filters
    
    Uses tags, categories, subcategories, technology, and risk to dynamically
    select applications.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/application-filters"
    item_type = "application_filter"
    
    @property
    def category(self) -> List[str]:
        """Get list of categories to match"""
        return self.raw_config.get('category', [])
    
    @property
    def subcategory(self) -> List[str]:
        """Get list of subcategories to match"""
        return self.raw_config.get('subcategory', [])
    
    @property
    def technology(self) -> List[str]:
        """Get list of technologies to match"""
        return self.raw_config.get('technology', [])
    
    @property
    def risk(self) -> List[int]:
        """Get list of risk levels to match"""
        return self.raw_config.get('risk', [])
    
    @property
    def tagging(self) -> Optional[Dict[str, Any]]:
        """Get tagging configuration"""
        return self.raw_config.get('tagging')
    
    def _validate_specific(self) -> List[str]:
        """Validate application filter"""
        errors = []
        
        # Must have at least one filter criterion
        has_criteria = (
            len(self.category) > 0 or
            len(self.subcategory) > 0 or
            len(self.technology) > 0 or
            len(self.risk) > 0 or
            self.tagging is not None
        )
        
        if not has_criteria:
            errors.append("Application filter must have at least one filter criterion")
        
        # Validate risk values if specified
        for risk_val in self.risk:
            if risk_val < 1 or risk_val > 5:
                errors.append(f"Application filter risk must be between 1 and 5, got {risk_val}")
        
        return errors


class Schedule(ObjectItem):
    """
    Represents a schedule object (time-based access control)
    
    API Endpoint: /sse/config/v1/schedules
    
    Defines recurring or one-time time windows for policy enforcement.
    """
    
    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/schedules"
    item_type = "schedule"
    
    @property
    def schedule_type(self) -> Optional[str]:
        """Get schedule type (recurring or non-recurring)"""
        if 'schedule_type' in self.raw_config:
            sched = self.raw_config['schedule_type']
            if isinstance(sched, dict):
                if 'recurring' in sched:
                    return 'recurring'
                elif 'non_recurring' in sched:
                    return 'non_recurring'
        return None
    
    @property
    def recurring_config(self) -> Optional[Dict[str, Any]]:
        """Get recurring schedule configuration"""
        if self.schedule_type == 'recurring' and 'schedule_type' in self.raw_config:
            return self.raw_config['schedule_type'].get('recurring')
        return None
    
    @property
    def non_recurring_config(self) -> Optional[List[str]]:
        """Get non-recurring schedule configuration (list of date ranges)"""
        if self.schedule_type == 'non_recurring' and 'schedule_type' in self.raw_config:
            return self.raw_config['schedule_type'].get('non_recurring')
        return None
    
    def _validate_specific(self) -> List[str]:
        """Validate schedule object"""
        errors = []
        
        # Must have schedule_type
        if 'schedule_type' not in self.raw_config:
            errors.append("Schedule must have schedule_type")
            return errors
        
        sched_type = self.schedule_type
        if not sched_type:
            errors.append("Schedule must be either recurring or non_recurring")
        
        # Validate based on type
        if sched_type == 'recurring' and not self.recurring_config:
            errors.append("Recurring schedule must have recurring configuration")
        
        if sched_type == 'non_recurring' and not self.non_recurring_config:
            errors.append("Non-recurring schedule must have date range list")

        return errors


class Region(ObjectItem):
    """
    Represents an address region.

    API Endpoint: /sse/config/v1/regions

    Regions define geographic areas using latitude/longitude coordinates
    for location-based policy decisions.
    """

    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/regions"
    item_type = "region"

    @property
    def geo_location(self) -> Optional[Dict[str, Any]]:
        """Get geographic location configuration"""
        return self.raw_config.get('geo_location')

    @property
    def address(self) -> Optional[List[str]]:
        """Get list of addresses in this region"""
        return self.raw_config.get('address', [])

    def _validate_specific(self) -> List[str]:
        """Validate region object"""
        errors = []
        # Regions may have various configuration options
        return errors


class LocalUser(ObjectItem):
    """
    Represents a local user.

    API Endpoint: /sse/config/v1/local-users

    Local users are used for local authentication without external identity providers.
    """

    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/local-users"
    item_type = "local_user"

    @property
    def disabled(self) -> bool:
        """Check if user is disabled"""
        return self.raw_config.get('disabled', False)

    def _validate_specific(self) -> List[str]:
        """Validate local user"""
        errors = []
        return errors


class LocalUserGroup(ObjectItem):
    """
    Represents a local user group.

    API Endpoint: /sse/config/v1/local-user-groups

    Local user groups organize local users for authentication rules.
    """

    api_endpoint = "https://api.sase.paloaltonetworks.com/sse/config/v1/local-user-groups"
    item_type = "local_user_group"

    @property
    def members(self) -> List[str]:
        """Get list of member users"""
        return self.raw_config.get('members', [])

    def _compute_dependencies(self) -> List[tuple]:
        """Local user groups depend on their member users"""
        deps = []
        for member in self.members:
            deps.append(('local_user', member))
        return deps

    def _validate_specific(self) -> List[str]:
        """Validate local user group"""
        errors = []
        return errors
