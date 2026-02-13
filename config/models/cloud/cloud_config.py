"""
CloudConfig container - Aggregates all cloud infrastructure.

Top-level container that holds:
- CloudDeployment settings
- List of CloudFirewall instances
- Optional CloudPanorama
- Supporting VMs (servers, clients, ZTNA connectors)
- WorkflowState
"""

from typing import Optional, Dict, Any, List
import json
import logging

from .deployment import CloudDeployment
from .firewall import CloudFirewall
from .ion_device import IONDevice
from .panorama import CloudPanorama
from .supporting_vms import ServerVM, ClientVM, ZTNAConnectorVM, SupportingVM
from .workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class CloudConfig:
    """
    Cloud infrastructure configuration container.

    Aggregates all cloud resources with convenience methods for
    adding, removing, and querying resources.
    """

    item_type = "cloud_config"

    def __init__(self, raw_config: Dict[str, Any] = None):
        raw_config = raw_config or {}
        self.raw_config = raw_config.copy()

        # Deployment settings
        deployment_data = raw_config.get('deployment', {})
        self.deployment: Optional[CloudDeployment] = (
            CloudDeployment(deployment_data) if deployment_data else None
        )

        # Firewalls
        firewalls_data = raw_config.get('firewalls', [])
        self.firewalls: List[CloudFirewall] = [
            CloudFirewall.from_dict(f, self.deployment) for f in firewalls_data
        ]

        # ION devices
        ion_data = raw_config.get('ion_devices', [])
        self.ion_devices: List[IONDevice] = [
            IONDevice.from_dict(d, self.deployment) for d in ion_data
        ]

        # Panorama (optional)
        panorama_data = raw_config.get('panorama')
        self.panorama: Optional[CloudPanorama] = (
            CloudPanorama.from_dict(panorama_data, self.deployment)
            if panorama_data else None
        )

        # Supporting VMs
        supporting_data = raw_config.get('supporting_vms', {})

        servers_data = supporting_data.get('servers', [])
        self.servers: List[ServerVM] = [
            ServerVM.from_dict(s, self.deployment) for s in servers_data
        ]

        clients_data = supporting_data.get('clients', [])
        self.clients: List[ClientVM] = [
            ClientVM.from_dict(c, self.deployment) for c in clients_data
        ]

        ztna_data = supporting_data.get('ztna_connectors', [])
        self.ztna_connectors: List[ZTNAConnectorVM] = [
            ZTNAConnectorVM.from_dict(z, self.deployment) for z in ztna_data
        ]

        # Workflow state
        workflow_data = raw_config.get('workflow_state', {})
        self.workflow_state = WorkflowState(workflow_data)

    # ========== Deployment Management ==========

    def set_deployment(self, deployment: CloudDeployment):
        """
        Set deployment configuration.

        Updates all resources with new deployment context.
        """
        self.deployment = deployment

        # Update all resources with new deployment (use set_deployment if available)
        for fw in self.firewalls:
            fw.set_deployment(deployment)
        for ion in self.ion_devices:
            ion.set_deployment(deployment)
        if self.panorama:
            self.panorama.set_deployment(deployment)
        for vm in self.all_supporting_vms:
            vm.deployment = deployment

        logger.info(f"Set deployment: {deployment.resource_group}")

    # ========== Firewall Management ==========

    def add_firewall(self, firewall: CloudFirewall):
        """Add a firewall"""
        # Auto-assign index if multiple of same type
        same_type = [f for f in self.firewalls if f.firewall_type == firewall.firewall_type]
        if same_type:
            firewall.index = len(same_type) + 1
            # Update existing firewalls to have indices
            if len(same_type) == 1 and same_type[0].index is None:
                same_type[0].index = 1

        # For branch firewalls, ensure dedicated subnet exists
        if firewall.firewall_type == CloudFirewall.TYPE_BRANCH and self.deployment:
            branch_id = f"branch{firewall.index or 1}"
            self.deployment.add_branch_subnet(branch_id)

        # Set deployment (this also creates default interfaces if needed)
        if self.deployment:
            firewall.set_deployment(self.deployment)

        self.firewalls.append(firewall)
        logger.info(f"Added firewall: {firewall.name}")

    def remove_firewall(self, name: str) -> bool:
        """Remove a firewall by name"""
        for i, fw in enumerate(self.firewalls):
            if fw.name == name:
                self.firewalls.pop(i)
                logger.info(f"Removed firewall: {name}")
                return True
        return False

    def get_firewall(self, name: str) -> Optional[CloudFirewall]:
        """Get firewall by name"""
        for fw in self.firewalls:
            if fw.name == name:
                return fw
        return None

    def get_firewalls_by_type(self, firewall_type: str) -> List[CloudFirewall]:
        """Get all firewalls of a specific type"""
        return [f for f in self.firewalls if f.firewall_type == firewall_type]

    # ========== ION Device Management ==========

    def add_ion_device(self, ion: IONDevice):
        """Add an ION device"""
        same_type = [d for d in self.ion_devices if d.ion_type == ion.ion_type]
        if same_type:
            ion.index = len(same_type) + 1
            if len(same_type) == 1 and same_type[0].index is None:
                same_type[0].index = 1

        if self.deployment:
            ion.set_deployment(self.deployment)

        self.ion_devices.append(ion)
        logger.info(f"Added ION device: {ion.name}")

    def remove_ion_device(self, name: str) -> bool:
        """Remove an ION device by name"""
        for i, ion in enumerate(self.ion_devices):
            if ion.name == name:
                self.ion_devices.pop(i)
                logger.info(f"Removed ION device: {name}")
                return True
        return False

    def get_ion_devices(self) -> List[IONDevice]:
        """Get all ION devices"""
        return list(self.ion_devices)

    # ========== Panorama Management ==========

    def set_panorama(self, panorama: CloudPanorama):
        """Set Panorama configuration"""
        if self.deployment:
            panorama.set_deployment(self.deployment)
        self.panorama = panorama
        logger.info(f"Set Panorama: {panorama.name}")

    def remove_panorama(self):
        """Remove Panorama"""
        self.panorama = None
        logger.info("Removed Panorama")

    # ========== Supporting VM Management ==========

    @property
    def all_supporting_vms(self) -> List[SupportingVM]:
        """Get all supporting VMs"""
        return self.servers + self.clients + self.ztna_connectors

    def add_server(self, server: ServerVM):
        """Add a server VM"""
        server.deployment = self.deployment
        if len(self.servers) > 0:
            server.index = len(self.servers) + 1
            if self.servers[0].index is None:
                self.servers[0].index = 1
        self.servers.append(server)
        logger.info(f"Added server: {server.name}")

    def add_client(self, client: ClientVM):
        """Add a client VM"""
        client.deployment = self.deployment
        # Index by OS type
        same_os = [c for c in self.clients if c.os_type == client.os_type]
        if same_os:
            client.index = len(same_os) + 1
            if same_os[0].index is None:
                same_os[0].index = 1
        self.clients.append(client)
        logger.info(f"Added client: {client.name}")

    def add_ztna_connector(self, ztna: ZTNAConnectorVM):
        """Add a ZTNA connector"""
        ztna.deployment = self.deployment
        if len(self.ztna_connectors) > 0:
            ztna.index = len(self.ztna_connectors) + 1
            if self.ztna_connectors[0].index is None:
                self.ztna_connectors[0].index = 1
        self.ztna_connectors.append(ztna)
        logger.info(f"Added ZTNA connector: {ztna.name}")

    # ========== Validation ==========

    def validate(self) -> List[str]:
        """
        Validate entire cloud configuration.

        Returns:
            List of error messages
        """
        errors = []

        # Require deployment
        if not self.deployment:
            errors.append("Deployment configuration is required")
            return errors  # Can't validate further without deployment

        # Validate deployment
        errors.extend(self.deployment.validate())

        # Validate firewalls
        for fw in self.firewalls:
            fw_errors = fw.validate()
            errors.extend([f"Firewall '{fw.name}': {e}" for e in fw_errors])

        # Validate ION devices
        for ion in self.ion_devices:
            ion_errors = ion.validate()
            errors.extend([f"ION '{ion.name}': {e}" for e in ion_errors])

        # Validate Panorama if present
        if self.panorama:
            pan_errors = self.panorama.validate()
            errors.extend([f"Panorama: {e}" for e in pan_errors])

        # Validate supporting VMs
        for vm in self.all_supporting_vms:
            vm_errors = vm.validate()
            errors.extend([f"VM '{vm.name}': {e}" for e in vm_errors])

        # Cross-validation
        if not self.firewalls and not self.ion_devices and not self.panorama:
            errors.append("At least one firewall, ION device, or Panorama must be configured")

        return errors

    # ========== Serialization ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'item_type': self.item_type,
            'deployment': self.deployment.to_dict() if self.deployment else None,
            'firewalls': [f.to_dict() for f in self.firewalls],
            'ion_devices': [d.to_dict() for d in self.ion_devices],
            'panorama': self.panorama.to_dict() if self.panorama else None,
            'supporting_vms': {
                'servers': [s.to_dict() for s in self.servers],
                'clients': [c.to_dict() for c in self.clients],
                'ztna_connectors': [z.to_dict() for z in self.ztna_connectors],
            },
            'workflow_state': self.workflow_state.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CloudConfig':
        """Deserialize from dictionary"""
        return cls(data)

    def to_terraform_vars(self) -> Dict[str, Any]:
        """
        Generate complete Terraform variable set.

        Returns:
            Dictionary for terraform.tfvars.json
        """
        if not self.deployment:
            return {}

        vars = self.deployment.to_terraform_vars()

        # Add firewall configs
        vars['firewalls'] = {}
        for fw in self.firewalls:
            vars['firewalls'][fw.name] = fw.to_terraform_vars()

        # Add ION device configs
        vars['ion_devices'] = {}
        for ion in self.ion_devices:
            vars['ion_devices'][ion.name] = ion.to_terraform_vars()

        # Add Panorama if present
        if self.panorama:
            vars['panorama'] = self.panorama.to_terraform_vars()
            vars['create_panorama'] = True
        else:
            vars['create_panorama'] = False

        # Add supporting VMs
        vars['servers'] = {s.name: s.to_terraform_vars() for s in self.servers}
        vars['clients'] = {c.name: c.to_terraform_vars() for c in self.clients}
        vars['ztna_connectors'] = {z.name: z.to_terraform_vars() for z in self.ztna_connectors}

        return vars

    # ========== Summary ==========

    def get_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary for UI display.

        Returns:
            Summary dictionary
        """
        return {
            'resource_group': self.deployment.resource_group if self.deployment else None,
            'location': self.deployment.location if self.deployment else None,
            'management_type': self.deployment.management_type if self.deployment else None,
            'firewall_count': len(self.firewalls),
            'ion_device_count': len(self.ion_devices),
            'datacenter_firewalls': len(self.get_firewalls_by_type('datacenter')),
            'branch_firewalls': len(self.get_firewalls_by_type('branch')),
            'has_panorama': self.panorama is not None,
            'server_count': len(self.servers),
            'client_count': len(self.clients),
            'ztna_connector_count': len(self.ztna_connectors),
            'workflow_phase': self.workflow_state.current_phase,
            'is_paused': self.workflow_state.is_paused,
        }

    def __repr__(self) -> str:
        rg = self.deployment.resource_group if self.deployment else "no-deployment"
        return f"<CloudConfig(rg='{rg}', firewalls={len(self.firewalls)}, ions={len(self.ion_devices)})>"
