"""
Panorama API integration for Panorama management servers.

Provides:
- PanoramaAPIClient: PAN-OS XML API client for Panorama management
- PanoramaPushOrchestrator: Push configuration to Panorama
"""

from .api_client import (
    PanoramaAPIClient,
    PanoramaConnectionError,
    PanoramaAPIError,
    PanoramaInfo,
    CommitResult,
    LicenseStatus,
    wait_for_panorama,
)
from .push import (
    PanoramaPushOrchestrator,
    PushResult,
    PushPhase,
    PushStatus,
    push_to_panorama,
)

__all__ = [
    # API Client
    'PanoramaAPIClient',
    'PanoramaConnectionError',
    'PanoramaAPIError',
    'PanoramaInfo',
    'CommitResult',
    'LicenseStatus',
    'wait_for_panorama',
    # Push Orchestrator
    'PanoramaPushOrchestrator',
    'PushResult',
    'PushPhase',
    'PushStatus',
    'push_to_panorama',
]
