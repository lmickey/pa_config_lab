"""
Workflow result classes.

Standardized result format for all workflow operations,
providing consistent tracking of success/failure, counts,
errors, and warnings.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class WorkflowError:
    """
    Represents an error that occurred during workflow execution.
    
    Attributes:
        code: Error code
        message: Error message
        item_type: Type of item that caused error (optional)
        item_name: Name of item that caused error (optional)
        details: Additional error details
        timestamp: When error occurred
    """
    code: str
    message: str
    item_type: str = ''
    item_name: str = ''
    operation: str = ''
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            'code': self.code,
            'message': self.message,
            'item_type': self.item_type,
            'item_name': self.item_name,
            'operation': self.operation,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class WorkflowWarning:
    """
    Represents a warning that occurred during workflow execution.
    
    Attributes:
        code: Warning code
        message: Warning message
        item_type: Type of item related to warning (optional)
        item_name: Name of item related to warning (optional)
        details: Additional warning details
        timestamp: When warning occurred
    """
    code: str
    message: str
    item_type: str = ''
    item_name: str = ''
    operation: str = ''
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert warning to dictionary."""
        return {
            'code': self.code,
            'message': self.message,
            'item_type': self.item_type,
            'item_name': self.item_name,
            'operation': self.operation,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class WorkflowResult:
    """
    Standardized result format for workflow operations.
    
    Tracks success/failure, item counts, errors, and warnings
    for all workflow operations (pull, push, validate, etc.).
    
    Attributes:
        success: Overall workflow success
        operation: Operation performed (e.g., 'pull', 'push', 'validate')
        items_processed: Total items processed
        items_created: Number of items created
        items_updated: Number of items updated
        items_deleted: Number of items deleted
        items_skipped: Number of items skipped
        items_failed: Number of items that failed
        errors: List of errors that occurred
        warnings: List of warnings that occurred
        start_time: When workflow started
        end_time: When workflow completed
        metadata: Additional workflow metadata
    """
    
    success: bool = True
    cancelled: bool = False  # Whether operation was cancelled by user
    operation: str = ''
    items_processed: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_deleted: int = 0
    items_skipped: int = 0
    items_failed: int = 0
    errors: List[WorkflowError] = field(default_factory=list)
    warnings: List[WorkflowWarning] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    could_not_overwrite: set = field(default_factory=set)  # (item_type, item_name) tuples
    configuration: Optional[Any] = None  # Configuration object (for pull operations)
    
    def add_error(
        self,
        error: Optional['WorkflowError'] = None,
        item_type: str = '',
        item_name: str = '',
        operation: str = '',
        error_type: str = '',
        message: str = '',
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an error to the result.
        
        Can be called with either a WorkflowError object or individual parameters.
        
        Args:
            error: WorkflowError object (if provided, other args ignored)
            item_type: Type of item that caused error
            item_name: Name of item that caused error
            operation: Operation being performed
            error_type: Type of error (used as 'code' for WorkflowError)
            message: Error message
            details: Additional error details
        """
        if error:
            self.errors.append(error)
        else:
            error = WorkflowError(
                code=error_type,  # error_type maps to code
                item_type=item_type,
                item_name=item_name,
                operation=operation,
                message=message,
                details=details
            )
            self.errors.append(error)
        self.items_failed += 1
        self.success = False
    
    def add_warning(
        self,
        warning: Optional['WorkflowWarning'] = None,
        item_type: str = '',
        item_name: str = '',
        operation: str = '',
        warning_type: str = '',
        message: str = '',
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a warning to the result.
        
        Can be called with either a WorkflowWarning object or individual parameters.
        
        Args:
            warning: WorkflowWarning object (if provided, other args ignored)
            item_type: Type of item related to warning
            item_name: Name of item related to warning
            operation: Operation being performed
            warning_type: Type of warning (used as 'code' for WorkflowWarning)
            message: Warning message
            details: Additional warning details
        """
        if warning:
            self.warnings.append(warning)
        else:
            warning = WorkflowWarning(
                code=warning_type,  # warning_type maps to code
                item_type=item_type,
                item_name=item_name,
                operation=operation,
                message=message,
                details=details
            )
            self.warnings.append(warning)
    
    def mark_complete(self) -> None:
        """Mark workflow as complete."""
        self.end_time = datetime.now()
    
    @property
    def duration(self) -> Optional[float]:
        """
        Get workflow duration in seconds.
        
        Returns:
            Duration in seconds, or None if not complete
        """
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if any warnings occurred."""
        return len(self.warnings) > 0
    
    @property
    def error_count(self) -> int:
        """Get number of errors."""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """Get number of warnings."""
        return len(self.warnings)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of workflow results.
        
        Returns:
            Dictionary with summary information
        """
        return {
            'success': self.success,
            'operation': self.operation,
            'duration': self.duration,
            'items': {
                'processed': self.items_processed,
                'created': self.items_created,
                'updated': self.items_updated,
                'deleted': self.items_deleted,
                'skipped': self.items_skipped,
                'failed': self.items_failed,
            },
            'errors': self.error_count,
            'warnings': self.warning_count,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary.
        
        Returns:
            Dictionary representation of result
        """
        return {
            'success': self.success,
            'operation': self.operation,
            'items_processed': self.items_processed,
            'items_created': self.items_created,
            'items_updated': self.items_updated,
            'items_deleted': self.items_deleted,
            'items_skipped': self.items_skipped,
            'items_failed': self.items_failed,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'metadata': self.metadata,
        }
    
    def save_to_file(self, path: str) -> None:
        """
        Save result to JSON file.
        
        Args:
            path: Path to save result to
        """
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def print_summary(self) -> None:
        """Print formatted summary of results."""
        print(f"\n{'='*60}")
        print(f"WORKFLOW RESULT: {self.operation.upper()}")
        print(f"{'='*60}")
        print(f"Status: {'✅ SUCCESS' if self.success else '❌ FAILED'}")
        
        if self.duration:
            print(f"Duration: {self.duration:.2f}s")
        
        print(f"\nItems:")
        print(f"  Processed: {self.items_processed}")
        if self.items_created > 0:
            print(f"  Created:   {self.items_created}")
        if self.items_updated > 0:
            print(f"  Updated:   {self.items_updated}")
        if self.items_deleted > 0:
            print(f"  Deleted:   {self.items_deleted}")
        if self.items_skipped > 0:
            print(f"  Skipped:   {self.items_skipped}")
        if self.items_failed > 0:
            print(f"  Failed:    {self.items_failed}")
        
        if self.has_warnings:
            print(f"\n⚠️  Warnings: {self.warning_count}")
        
        if self.has_errors:
            print(f"\n❌ Errors: {self.error_count}")
            for error in self.errors[:5]:  # Show first 5
                print(f"  - {error.item_type} '{error.item_name}': {error.message}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")
        
        print(f"{'='*60}\n")
