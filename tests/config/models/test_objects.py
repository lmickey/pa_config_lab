"""
Tests for config.models.objects module.

Tests all network object model classes.
"""

import pytest
from config.models.objects import (
    AddressObject,
    AddressGroup,
    ServiceObject,
    ServiceGroup,
    ApplicationObject,
    ApplicationGroup,
    ApplicationFilter,
    Schedule,
)
from tests.examples.loader import Examples


class TestAddressObject:
    """Tests for AddressObject class"""
    
    def test_create_address_netmask(self):
        """Test creating address with IP/netmask"""
        config = Examples.address_minimal()
        address = AddressObject(config)
        
        assert address.name == 'internal-network'
        assert address.folder == 'Mobile Users'
        assert address.address_type == 'ip_netmask'
        assert address.address_value == '192.168.1.0/24'
        assert not address.has_dependencies
    
    def test_create_address_fqdn(self):
        """Test creating address with FQDN"""
        config = Examples.address_fqdn()
        address = AddressObject(config)
        
        assert address.name == 'example-domain'
        assert address.address_type == 'fqdn'
        assert address.address_value == 'example.com'
    
    def test_create_address_range(self):
        """Test creating address with IP range"""
        config = Examples.address_range()
        address = AddressObject(config)
        
        assert address.name == 'datacenter-range'
        assert address.address_type == 'ip_range'
        assert address.address_value == '10.0.0.1-10.0.0.254'
    
    def test_address_in_snippet(self):
        """Test address can be in snippet"""
        config = Examples.address_snippet()
        address = AddressObject(config)
        
        assert address.snippet == 'production-snippet'
        assert address.folder is None
        assert address.is_in_snippet()
        assert not address.is_in_folder()
    
    def test_address_validation_missing_type(self):
        """Test validation catches missing address type"""
        config = {
            'name': 'invalid-address',
            'folder': 'Mobile Users'
        }
        
        address = AddressObject(config)
        errors = address.validate()
        
        assert len(errors) > 0
        assert any('address type' in error.lower() for error in errors)
    
    def test_address_validation_multiple_types(self):
        """Test validation catches multiple address types"""
        config = {
            'name': 'invalid-address',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.1.0/24',
            'fqdn': 'example.com'
        }
        
        address = AddressObject(config)
        errors = address.validate()
        
        assert len(errors) > 0
        assert any('exactly one' in error.lower() for error in errors)
    
    def test_address_rename(self):
        """Test renaming address object"""
        config = Examples.address_minimal()
        address = AddressObject(config)
        
        old_name = address.name
        address.rename('new-internal-network')
        
        assert address.name == 'new-internal-network'
        assert address.name != old_name
        assert address.raw_config['name'] == 'new-internal-network'


class TestAddressGroup:
    """Tests for AddressGroup class"""
    
    def test_create_static_group(self):
        """Test creating static address group"""
        config = Examples.address_group()
        group = AddressGroup(config)
        
        assert group.name == 'trusted-networks'
        assert group.is_static
        assert not group.is_dynamic
        assert len(group.members) == 2
        assert 'internal-network' in group.members
        assert group.has_dependencies
    
    def test_create_dynamic_group(self):
        """Test creating dynamic address group"""
        config = Examples.address_group_dynamic()
        group = AddressGroup(config)
        
        assert group.name == 'production-servers'
        assert group.is_dynamic
        assert not group.is_static
        assert group.filter == "'production' and 'server'"
        assert not group.has_dependencies  # Dynamic groups don't have explicit dependencies
    
    def test_static_group_dependencies(self):
        """Test static group dependency detection"""
        config = Examples.address_group()
        group = AddressGroup(config)
        
        deps = group.get_dependencies()
        
        assert len(deps) == 2
        assert ('address_object', 'internal-network') in deps
        assert ('address_object', 'vpn-subnets') in deps
    
    def test_address_group_validation_empty_static(self):
        """Test validation catches empty static group"""
        config = {
            'name': 'empty-group',
            'folder': 'Mobile Users',
            'static': []
        }
        
        group = AddressGroup(config)
        errors = group.validate()
        
        assert len(errors) > 0
        assert any('at least one member' in error.lower() for error in errors)
    
    def test_address_group_validation_no_type(self):
        """Test validation catches group with no type"""
        config = {
            'name': 'invalid-group',
            'folder': 'Mobile Users'
        }
        
        group = AddressGroup(config)
        errors = group.validate()
        
        assert len(errors) > 0
        assert any('either static or dynamic' in error.lower() for error in errors)


class TestServiceObject:
    """Tests for ServiceObject class"""
    
    def test_create_tcp_service(self):
        """Test creating TCP service"""
        config = Examples.service()
        service = ServiceObject(config)
        
        assert service.name == 'tcp-8443'
        assert service.protocol_type == 'tcp'
        assert service.port == '8443'
        assert not service.has_dependencies
    
    def test_service_with_source_port(self):
        """Test service with source port"""
        config = {
            'name': 'custom-service',
            'folder': 'Mobile Users',
            'protocol': {
                'tcp': {
                    'port': '443',
                    'source_port': '1024-65535'
                }
            }
        }
        
        service = ServiceObject(config)
        
        assert service.port == '443'
        assert service.source_port == '1024-65535'
    
    def test_udp_service(self):
        """Test creating UDP service"""
        config = {
            'name': 'udp-53',
            'folder': 'Mobile Users',
            'protocol': {
                'udp': {
                    'port': '53'
                }
            }
        }
        
        service = ServiceObject(config)
        
        assert service.protocol_type == 'udp'
        assert service.port == '53'
    
    def test_service_validation_no_protocol(self):
        """Test validation catches missing protocol"""
        config = {
            'name': 'invalid-service',
            'folder': 'Mobile Users'
        }
        
        service = ServiceObject(config)
        errors = service.validate()
        
        assert len(errors) > 0
        assert any('protocol' in error.lower() for error in errors)
    
    def test_service_validation_no_port(self):
        """Test validation catches missing port"""
        config = {
            'name': 'invalid-service',
            'folder': 'Mobile Users',
            'protocol': {
                'tcp': {}
            }
        }
        
        service = ServiceObject(config)
        errors = service.validate()
        
        assert len(errors) > 0
        assert any('port' in error.lower() for error in errors)


class TestServiceGroup:
    """Tests for ServiceGroup class"""
    
    def test_create_service_group(self):
        """Test creating service group"""
        config = Examples.service_group()
        group = ServiceGroup(config)
        
        assert group.name == 'web-services'
        assert len(group.members) == 3
        assert 'tcp-443' in group.members
        assert group.has_dependencies
    
    def test_service_group_dependencies(self):
        """Test service group dependency detection"""
        config = Examples.service_group()
        group = ServiceGroup(config)
        
        deps = group.get_dependencies()
        
        assert len(deps) == 3
        assert ('service_object', 'tcp-80') in deps
        assert ('service_object', 'tcp-443') in deps
        assert ('service_object', 'tcp-8443') in deps
    
    def test_service_group_validation_empty(self):
        """Test validation catches empty service group"""
        config = {
            'name': 'empty-group',
            'folder': 'Mobile Users',
            'members': []
        }
        
        group = ServiceGroup(config)
        errors = group.validate()
        
        assert len(errors) > 0
        assert any('at least one member' in error.lower() for error in errors)


class TestApplicationObject:
    """Tests for ApplicationObject class"""
    
    def test_create_application(self):
        """Test creating application object"""
        config = Examples.application()
        app = ApplicationObject(config)
        
        assert app.name == 'custom-web-app'
        assert app.category == 'general-internet'
        assert app.subcategory == 'internet-utility'
        assert app.technology == 'browser-based'
        assert app.risk == 3
        assert not app.has_dependencies
    
    def test_application_validation_missing_category(self):
        """Test validation catches missing category"""
        config = {
            'name': 'invalid-app',
            'folder': 'Mobile Users',
            'subcategory': 'test',
            'technology': 'client-server'
        }
        
        app = ApplicationObject(config)
        errors = app.validate()
        
        assert len(errors) > 0
        assert any('category' in error.lower() for error in errors)
    
    def test_application_validation_invalid_risk(self):
        """Test validation catches invalid risk level"""
        config = {
            'name': 'invalid-app',
            'folder': 'Mobile Users',
            'category': 'general-internet',
            'subcategory': 'test',
            'technology': 'client-server',
            'risk': 10  # Invalid: must be 1-5
        }
        
        app = ApplicationObject(config)
        errors = app.validate()
        
        assert len(errors) > 0
        assert any('risk' in error.lower() and '1' in error and '5' in error for error in errors)


class TestApplicationGroup:
    """Tests for ApplicationGroup class"""
    
    def test_create_application_group(self):
        """Test creating application group"""
        config = Examples.application_group()
        group = ApplicationGroup(config)
        
        assert group.name == 'collaboration-apps'
        assert len(group.members) == 3
        assert 'zoom' in group.members
        assert group.has_dependencies
    
    def test_application_group_dependencies(self):
        """Test application group dependency detection"""
        config = Examples.application_group()
        group = ApplicationGroup(config)
        
        deps = group.get_dependencies()
        
        assert len(deps) == 3
        assert ('application_object', 'ms-teams') in deps
        assert ('application_object', 'zoom') in deps
        assert ('application_object', 'webex') in deps


class TestApplicationFilter:
    """Tests for ApplicationFilter class"""
    
    def test_create_application_filter(self):
        """Test creating application filter"""
        config = Examples.application_filter()
        filter_obj = ApplicationFilter(config)
        
        assert filter_obj.name == 'high-risk-apps'
        assert len(filter_obj.category) == 2
        assert 'file-sharing' in filter_obj.category
        assert len(filter_obj.risk) == 2
        assert 4 in filter_obj.risk
        assert 5 in filter_obj.risk
    
    def test_application_filter_validation_no_criteria(self):
        """Test validation catches filter with no criteria"""
        config = {
            'name': 'empty-filter',
            'folder': 'Mobile Users'
        }
        
        filter_obj = ApplicationFilter(config)
        errors = filter_obj.validate()
        
        assert len(errors) > 0
        assert any('at least one' in error.lower() for error in errors)
    
    def test_application_filter_validation_invalid_risk(self):
        """Test validation catches invalid risk in filter"""
        config = {
            'name': 'invalid-filter',
            'folder': 'Mobile Users',
            'risk': [1, 6]  # 6 is invalid
        }
        
        filter_obj = ApplicationFilter(config)
        errors = filter_obj.validate()
        
        assert len(errors) > 0
        assert any('risk' in error.lower() for error in errors)


class TestSchedule:
    """Tests for Schedule class"""
    
    def test_create_recurring_schedule(self):
        """Test creating recurring schedule"""
        config = Examples.schedule()
        schedule = Schedule(config)
        
        assert schedule.name == 'business-hours'
        assert schedule.schedule_type == 'recurring'
        assert schedule.recurring_config is not None
        assert schedule.non_recurring_config is None
        assert not schedule.has_dependencies
    
    def test_create_non_recurring_schedule(self):
        """Test creating non-recurring schedule"""
        config = Examples.schedule_non_recurring()
        schedule = Schedule(config)
        
        assert schedule.name == 'holiday-blackout'
        assert schedule.schedule_type == 'non_recurring'
        assert schedule.non_recurring_config is not None
        assert schedule.recurring_config is None
        assert len(schedule.non_recurring_config) == 2
    
    def test_schedule_validation_no_type(self):
        """Test validation catches schedule with no type"""
        config = {
            'name': 'invalid-schedule',
            'folder': 'Mobile Users'
        }
        
        schedule = Schedule(config)
        errors = schedule.validate()
        
        assert len(errors) > 0
        assert any('schedule_type' in error.lower() for error in errors)
    
    def test_schedule_validation_recurring_no_config(self):
        """Test validation catches recurring schedule without config"""
        config = {
            'name': 'invalid-schedule',
            'folder': 'Mobile Users',
            'schedule_type': {
                'recurring': None
            }
        }
        
        schedule = Schedule(config)
        errors = schedule.validate()
        
        assert len(errors) > 0
        assert any('recurring' in error.lower() for error in errors)


class TestObjectSerialization:
    """Test serialization/deserialization of object models"""
    
    def test_address_serialization(self):
        """Test address object serialization"""
        config = Examples.address_full()
        address = AddressObject(config)
        
        # Serialize
        data = address.to_dict()
        
        assert 'name' in data
        assert 'folder' in data
        assert 'ip_netmask' in data
        assert 'id' not in data  # ID should be removed
        
        # Deserialize
        address2 = AddressObject.from_dict(data)
        
        assert address2.name == address.name
        assert address2.folder == address.folder
    
    def test_address_group_serialization(self):
        """Test address group serialization"""
        config = Examples.address_group()
        group = AddressGroup(config)
        group.push_strategy = 'rename'
        group.mark_for_deletion()
        
        # Serialize
        data = group.to_dict()
        
        assert data['push_strategy'] == 'rename'
        assert data['deleted'] == True
        assert 'static' in data
        
        # Deserialize
        group2 = AddressGroup.from_dict(data)
        
        assert group2.push_strategy == 'rename'
        assert group2.deleted == True
        assert group2.is_static


class TestObjectDeletion:
    """Test deletion tracking for object models"""
    
    def test_mark_for_deletion(self):
        """Test marking object for deletion"""
        config = Examples.address_minimal()
        address = AddressObject(config)
        
        assert not address.deleted
        assert address.delete_success is None
        
        address.mark_for_deletion()
        
        assert address.deleted
        assert address.delete_success is None
    
    def test_unmark_for_deletion(self):
        """Test unmarking object for deletion"""
        config = Examples.service()
        service = ServiceObject(config)
        
        service.mark_for_deletion()
        service.delete_success = False
        
        service.unmark_for_deletion()
        
        assert not service.deleted
        assert service.delete_success is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
