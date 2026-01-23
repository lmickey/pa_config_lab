"""
WorkflowState model - Deployment workflow state tracking.

Enables pause/resume of deployments by tracking:
- Current phase
- Phase status and timestamps
- Terraform outputs
- User notes
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class PhaseStatus(str, Enum):
    """Workflow phase status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowPhase(str, Enum):
    """Deployment workflow phases"""
    CONFIG_COMPLETE = "config_complete"
    TERRAFORM_RUNNING = "terraform_running"
    TERRAFORM_COMPLETE = "terraform_complete"
    LICENSING_PENDING = "licensing_pending"
    FIREWALL_CONFIG = "firewall_config"
    PANORAMA_CONFIG = "panorama_config"
    SCM_CONFIG = "scm_config"
    COMPLETE = "complete"


@dataclass
class PhaseState:
    """State for a single workflow phase"""
    status: PhaseStatus = PhaseStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    awaiting: List[str] = field(default_factory=list)  # What we're waiting for

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error': self.error,
            'outputs': self.outputs.copy(),
            'awaiting': self.awaiting.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PhaseState':
        return cls(
            status=PhaseStatus(data.get('status', 'pending')),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            error=data.get('error'),
            outputs=data.get('outputs', {}),
            awaiting=data.get('awaiting', []),
        )


class WorkflowState:
    """
    Deployment workflow state manager.

    Tracks the progress of a POV deployment through all phases,
    enabling pause/resume functionality.
    """

    item_type = "workflow_state"

    def __init__(self, raw_config: Dict[str, Any] = None):
        raw_config = raw_config or {}
        self.raw_config = raw_config.copy()

        # Current phase
        self.current_phase: str = raw_config.get('current_phase', WorkflowPhase.CONFIG_COMPLETE.value)
        self.last_updated: str = raw_config.get('last_updated', datetime.utcnow().isoformat())

        # Phase states
        phases_data = raw_config.get('phases', {})
        self.phases: Dict[str, PhaseState] = {}

        # Initialize all phases
        for phase in WorkflowPhase:
            if phase.value in phases_data:
                self.phases[phase.value] = PhaseState.from_dict(phases_data[phase.value])
            else:
                self.phases[phase.value] = PhaseState()

        # User notes
        self.notes: str = raw_config.get('notes', '')

    # ========== Phase Management ==========

    def start_phase(self, phase: WorkflowPhase):
        """
        Mark a phase as started.

        Args:
            phase: Phase to start
        """
        state = self.phases[phase.value]
        state.status = PhaseStatus.IN_PROGRESS
        state.started_at = datetime.utcnow().isoformat()
        self.current_phase = phase.value
        self._update_timestamp()
        logger.info(f"Started phase: {phase.value}")

    def complete_phase(self, phase: WorkflowPhase, outputs: Dict[str, Any] = None):
        """
        Mark a phase as complete.

        Args:
            phase: Phase to complete
            outputs: Optional outputs from this phase (e.g., IPs from Terraform)
        """
        state = self.phases[phase.value]
        state.status = PhaseStatus.COMPLETE
        state.completed_at = datetime.utcnow().isoformat()
        if outputs:
            state.outputs = outputs
        self._update_timestamp()
        logger.info(f"Completed phase: {phase.value}")

    def fail_phase(self, phase: WorkflowPhase, error: str):
        """
        Mark a phase as failed.

        Args:
            phase: Phase that failed
            error: Error message
        """
        state = self.phases[phase.value]
        state.status = PhaseStatus.FAILED
        state.error = error
        self._update_timestamp()
        logger.error(f"Phase {phase.value} failed: {error}")

    def pause_for(self, phase: WorkflowPhase, awaiting: List[str]):
        """
        Pause workflow awaiting external action.

        Args:
            phase: Current phase
            awaiting: List of things we're waiting for
        """
        state = self.phases[phase.value]
        state.status = PhaseStatus.IN_PROGRESS
        state.awaiting = awaiting
        self.current_phase = phase.value
        self._update_timestamp()
        logger.info(f"Paused at phase {phase.value}, awaiting: {awaiting}")

    def skip_phase(self, phase: WorkflowPhase):
        """
        Skip a phase (e.g., Panorama config when using SCM).

        Args:
            phase: Phase to skip
        """
        state = self.phases[phase.value]
        state.status = PhaseStatus.SKIPPED
        self._update_timestamp()
        logger.info(f"Skipped phase: {phase.value}")

    def _update_timestamp(self):
        """Update last_updated timestamp"""
        self.last_updated = datetime.utcnow().isoformat()

    # ========== Query Methods ==========

    def get_phase_state(self, phase: WorkflowPhase) -> PhaseState:
        """Get state for a specific phase"""
        return self.phases[phase.value]

    def get_current_phase_state(self) -> PhaseState:
        """Get current phase state"""
        return self.phases[self.current_phase]

    @property
    def is_paused(self) -> bool:
        """Check if workflow is paused awaiting action"""
        current = self.get_current_phase_state()
        return current.status == PhaseStatus.IN_PROGRESS and len(current.awaiting) > 0

    @property
    def is_complete(self) -> bool:
        """Check if workflow is fully complete"""
        return self.current_phase == WorkflowPhase.COMPLETE.value

    @property
    def is_failed(self) -> bool:
        """Check if any phase has failed"""
        for state in self.phases.values():
            if state.status == PhaseStatus.FAILED:
                return True
        return False

    @property
    def terraform_outputs(self) -> Dict[str, Any]:
        """Get Terraform outputs (stored in terraform_complete phase)"""
        return self.phases[WorkflowPhase.TERRAFORM_COMPLETE.value].outputs

    def get_completed_phases(self) -> List[str]:
        """Get list of completed phase names"""
        return [
            name for name, state in self.phases.items()
            if state.status == PhaseStatus.COMPLETE
        ]

    def get_pending_phases(self) -> List[str]:
        """Get list of pending phase names"""
        return [
            name for name, state in self.phases.items()
            if state.status == PhaseStatus.PENDING
        ]

    # ========== Serialization ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'item_type': self.item_type,
            'current_phase': self.current_phase,
            'last_updated': self.last_updated,
            'phases': {
                name: state.to_dict()
                for name, state in self.phases.items()
            },
            'notes': self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowState':
        """Deserialize from dictionary"""
        return cls(data)

    # ========== Resume Information ==========

    def get_resume_summary(self) -> Dict[str, Any]:
        """
        Get summary for resume prompt dialog.

        Returns:
            Dictionary with phase status summary
        """
        summary = {
            'current_phase': self.current_phase,
            'last_updated': self.last_updated,
            'is_paused': self.is_paused,
            'awaiting': self.get_current_phase_state().awaiting if self.is_paused else [],
            'notes': self.notes,
            'phases': [],
        }

        # Build ordered phase list with status
        phase_order = [
            (WorkflowPhase.CONFIG_COMPLETE, "Configuration saved"),
            (WorkflowPhase.TERRAFORM_COMPLETE, "Terraform deployment"),
            (WorkflowPhase.LICENSING_PENDING, "Licensing"),
            (WorkflowPhase.FIREWALL_CONFIG, "Firewall configuration"),
            (WorkflowPhase.PANORAMA_CONFIG, "Panorama configuration"),
            (WorkflowPhase.SCM_CONFIG, "SCM configuration"),
            (WorkflowPhase.COMPLETE, "Complete"),
        ]

        for phase, label in phase_order:
            state = self.phases[phase.value]
            summary['phases'].append({
                'phase': phase.value,
                'label': label,
                'status': state.status.value,
                'is_current': phase.value == self.current_phase,
            })

        return summary

    def __repr__(self) -> str:
        return f"<WorkflowState(current='{self.current_phase}', paused={self.is_paused})>"
