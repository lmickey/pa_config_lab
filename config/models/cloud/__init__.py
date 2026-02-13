"""
Cloud infrastructure configuration models.

Provides models for Azure deployments, firewalls, Panorama, and supporting VMs.
"""

from .base import CloudItem
from .naming import (
    sanitize_name,
    generate_resource_group_name,
    generate_resource_name,
    generate_vm_username,
)
from .deployment import CloudDeployment, SubnetConfig, VirtualNetworkConfig
from .firewall import (
    CloudFirewall,
    VMSettings,
    VMImageConfig,
    NetworkInterfaceConfig,
    DeviceConfig,
)
from .ion_device import (
    IONDevice,
    IONVMSettings,
    IONImageConfig,
    IONInterfaceConfig,
)
from .panorama import CloudPanorama, LicensingStatus, PluginConfig
from .supporting_vms import (
    SupportingVM,
    ServerVM,
    ClientVM,
    ZTNAConnectorVM,
    ServiceConfig,
    GlobalProtectConfig,
    OSType,
)
from .workflow_state import WorkflowState, PhaseState, PhaseStatus, WorkflowPhase
from .cloud_config import CloudConfig

__all__ = [
    # Base
    'CloudItem',

    # Naming
    'sanitize_name',
    'generate_resource_group_name',
    'generate_resource_name',
    'generate_vm_username',

    # Deployment
    'CloudDeployment',
    'SubnetConfig',
    'VirtualNetworkConfig',

    # Firewall
    'CloudFirewall',
    'VMSettings',
    'VMImageConfig',
    'NetworkInterfaceConfig',
    'DeviceConfig',

    # ION Device
    'IONDevice',
    'IONVMSettings',
    'IONImageConfig',
    'IONInterfaceConfig',

    # Panorama
    'CloudPanorama',
    'LicensingStatus',
    'PluginConfig',

    # Supporting VMs
    'SupportingVM',
    'ServerVM',
    'ClientVM',
    'ZTNAConnectorVM',
    'ServiceConfig',
    'GlobalProtectConfig',
    'OSType',

    # Workflow
    'WorkflowState',
    'PhaseState',
    'PhaseStatus',
    'WorkflowPhase',

    # Container
    'CloudConfig',
]
