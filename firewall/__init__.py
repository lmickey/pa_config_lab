"""
Firewall API integration for PAN-OS firewalls.

Provides:
- FirewallAPIClient: PAN-OS XML API client for firewall management
- FirewallPushOrchestrator: Push configuration to firewalls
"""

from .api_client import (
    FirewallAPIClient,
    FirewallConnectionError,
    FirewallAPIError,
    DeviceInfo,
    CommitResult,
    CommitStatus,
    wait_for_firewall,
)
from .push import (
    FirewallPushOrchestrator,
    PushResult,
    PushPhase,
    PushStatus,
    push_to_firewall,
)

__all__ = [
    # API Client
    'FirewallAPIClient',
    'FirewallConnectionError',
    'FirewallAPIError',
    'DeviceInfo',
    'CommitResult',
    'CommitStatus',
    'wait_for_firewall',
    # Push Orchestrator
    'FirewallPushOrchestrator',
    'PushResult',
    'PushPhase',
    'PushStatus',
    'push_to_firewall',
]
