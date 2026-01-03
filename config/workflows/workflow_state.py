"""
Workflow state tracking.

Provides state management for workflow operations including:
- Current operation tracking
- Intermediate results storage
- Progress monitoring
- Future: Pause/resume capability
- Future: Rollback on error
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OperationState:
    """
    State of a single operation within a workflow.
    
    Attributes:
        operation: Operation name
        status: Current status
        start_time: When operation started
        end_time: When operation completed
        items_processed: Number of items processed
        current_item: Current item being processed
        error: Error message if failed
    """
    operation: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    items_processed: int = 0
    current_item: Optional[str] = None
    error: Optional[str] = None
    
    def start(self) -> None:
        """Mark operation as started."""
        self.status = WorkflowStatus.RUNNING
        self.start_time = datetime.now()
    
    def complete(self) -> None:
        """Mark operation as completed."""
        self.status = WorkflowStatus.COMPLETED
        self.end_time = datetime.now()
    
    def fail(self, error: str) -> None:
        """
        Mark operation as failed.
        
        Args:
            error: Error message
        """
        self.status = WorkflowStatus.FAILED
        self.end_time = datetime.now()
        self.error = error
    
    @property
    def duration(self) -> Optional[float]:
        """Get operation duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class WorkflowState:
    """
    Tracks state of workflow execution.
    
    Provides monitoring and control of workflow operations,
    including progress tracking and future pause/resume capability.
    """
    
    def __init__(self, workflow_id: str, operation: str):
        """
        Initialize workflow state.
        
        Args:
            workflow_id: Unique identifier for workflow
            operation: Type of workflow (e.g., 'pull', 'push', 'validate')
        """
        self.workflow_id = workflow_id
        self.operation = operation
        self.status = WorkflowStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Operation tracking
        self.operations: List[OperationState] = []
        self.current_operation: Optional[OperationState] = None
        
        # Progress tracking
        self.total_items: int = 0
        self.processed_items: int = 0
        
        # Results storage
        self.intermediate_results: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        
        logger.info(f"Initialized workflow state: {workflow_id} ({operation})")
    
    def start(self) -> None:
        """Start workflow execution."""
        self.status = WorkflowStatus.RUNNING
        self.start_time = datetime.now()
        logger.info(f"Workflow {self.workflow_id} started")
    
    def complete(self) -> None:
        """Mark workflow as completed."""
        self.status = WorkflowStatus.COMPLETED
        self.end_time = datetime.now()
        logger.info(f"Workflow {self.workflow_id} completed in {self.duration:.2f}s")
    
    def fail(self, error: str) -> None:
        """
        Mark workflow as failed.
        
        Args:
            error: Error message
        """
        self.status = WorkflowStatus.FAILED
        self.end_time = datetime.now()
        logger.error(f"Workflow {self.workflow_id} failed: {error}")
    
    def cancel(self) -> None:
        """Cancel workflow execution."""
        self.status = WorkflowStatus.CANCELLED
        self.end_time = datetime.now()
        logger.warning(f"Workflow {self.workflow_id} cancelled")
    
    def pause(self) -> None:
        """Pause workflow execution (future feature)."""
        if self.status == WorkflowStatus.RUNNING:
            self.status = WorkflowStatus.PAUSED
            logger.info(f"Workflow {self.workflow_id} paused")
    
    def resume(self) -> None:
        """Resume workflow execution (future feature)."""
        if self.status == WorkflowStatus.PAUSED:
            self.status = WorkflowStatus.RUNNING
            logger.info(f"Workflow {self.workflow_id} resumed")
    
    def start_operation(self, operation: str) -> None:
        """
        Start a new operation.
        
        Args:
            operation: Operation name
        """
        op_state = OperationState(operation=operation)
        op_state.start()
        self.operations.append(op_state)
        self.current_operation = op_state
        logger.debug(f"Started operation: {operation}")
    
    def complete_operation(self) -> None:
        """Complete current operation."""
        if self.current_operation:
            self.current_operation.complete()
            logger.debug(f"Completed operation: {self.current_operation.operation}")
            self.current_operation = None
    
    def fail_operation(self, error: str) -> None:
        """
        Fail current operation.
        
        Args:
            error: Error message
        """
        if self.current_operation:
            self.current_operation.fail(error)
            logger.error(f"Operation {self.current_operation.operation} failed: {error}")
            self.current_operation = None
    
    def update_progress(
        self,
        processed: Optional[int] = None,
        total: Optional[int] = None,
        current_item: Optional[str] = None
    ) -> None:
        """
        Update workflow progress.
        
        Args:
            processed: Number of items processed
            total: Total number of items
            current_item: Current item being processed
        """
        if processed is not None:
            self.processed_items = processed
        
        if total is not None:
            self.total_items = total
        
        if current_item is not None and self.current_operation:
            self.current_operation.current_item = current_item
    
    def increment_progress(self) -> None:
        """Increment processed items counter."""
        self.processed_items += 1
        if self.current_operation:
            self.current_operation.items_processed += 1
    
    def store_result(self, key: str, value: Any) -> None:
        """
        Store intermediate result.
        
        Args:
            key: Result key
            value: Result value
        """
        self.intermediate_results[key] = value
    
    def get_result(self, key: str) -> Optional[Any]:
        """
        Get intermediate result.
        
        Args:
            key: Result key
            
        Returns:
            Result value or None if not found
        """
        return self.intermediate_results.get(key)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set metadata value.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str) -> Optional[Any]:
        """
        Get metadata value.
        
        Args:
            key: Metadata key
            
        Returns:
            Metadata value or None if not found
        """
        return self.metadata.get(key)
    
    @property
    def duration(self) -> Optional[float]:
        """Get workflow duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None
    
    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def is_running(self) -> bool:
        """Check if workflow is currently running."""
        return self.status == WorkflowStatus.RUNNING
    
    @property
    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return self.status == WorkflowStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if workflow has failed."""
        return self.status == WorkflowStatus.FAILED
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get workflow state summary.
        
        Returns:
            Dictionary with state summary
        """
        return {
            'workflow_id': self.workflow_id,
            'operation': self.operation,
            'status': self.status.value,
            'duration': self.duration,
            'progress': {
                'processed': self.processed_items,
                'total': self.total_items,
                'percentage': self.progress_percentage,
            },
            'operations': len(self.operations),
            'current_operation': self.current_operation.operation if self.current_operation else None,
        }
    
    def print_status(self) -> None:
        """Print current workflow status."""
        print(f"\n{'='*60}")
        print(f"WORKFLOW STATUS: {self.workflow_id}")
        print(f"{'='*60}")
        print(f"Operation: {self.operation}")
        print(f"Status: {self.status.value}")
        
        if self.duration:
            print(f"Duration: {self.duration:.2f}s")
        
        if self.total_items > 0:
            print(f"\nProgress: {self.processed_items}/{self.total_items} ({self.progress_percentage:.1f}%)")
        
        if self.current_operation:
            print(f"Current: {self.current_operation.operation}")
            if self.current_operation.current_item:
                print(f"  Item: {self.current_operation.current_item}")
        
        print(f"{'='*60}\n")
