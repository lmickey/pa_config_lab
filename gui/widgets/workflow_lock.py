"""
Workflow Lock Manager - Prevents workflow switching during operations.

This module provides a mechanism to lock workflow navigation during
long-running operations like validation and push to prevent data loss
and ensure operations complete properly.
"""

from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QWidget,
    QMessageBox,
)
from PyQt6.QtCore import QObject, pyqtSignal
import logging

logger = logging.getLogger(__name__)


class WorkflowLockManager(QObject):
    """
    Manages workflow locking during operations.
    
    This singleton-like manager can be used to:
    - Lock workflow navigation during operations
    - Show appropriate warnings when user tries to switch
    - Provide cancel callbacks for operations
    
    Usage:
        # In a workflow widget
        self.lock_manager = WorkflowLockManager.instance()
        
        # Before starting operation
        self.lock_manager.acquire_lock(
            owner=self,
            operation_name="Validation",
            cancel_callback=self._cancel_validation
        )
        
        # After operation completes
        self.lock_manager.release_lock(self)
        
        # In main window's workflow switch handler
        if self.lock_manager.is_locked():
            if not self.lock_manager.request_switch(parent_widget):
                return  # Switch cancelled
    """
    
    _instance: Optional['WorkflowLockManager'] = None
    
    # Signals
    lock_acquired = pyqtSignal(str)  # operation_name
    lock_released = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._locked = False
        self._owner: Optional[QWidget] = None
        self._operation_name: str = ""
        self._cancel_callback: Optional[Callable[[], bool]] = None
    
    @classmethod
    def instance(cls) -> 'WorkflowLockManager':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = WorkflowLockManager()
        return cls._instance
    
    def acquire_lock(
        self,
        owner: QWidget,
        operation_name: str,
        cancel_callback: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Acquire a lock for an operation.
        
        Args:
            owner: The widget that owns this lock
            operation_name: Name of the operation (e.g., "Validation", "Push")
            cancel_callback: Optional callback to cancel the operation.
                            Should return True if cancellation was successful.
        
        Returns:
            True if lock was acquired, False if already locked by another owner
        """
        if self._locked and self._owner != owner:
            logger.warning(f"Cannot acquire lock - already held by {self._operation_name}")
            return False
        
        self._locked = True
        self._owner = owner
        self._operation_name = operation_name
        self._cancel_callback = cancel_callback
        
        logger.debug(f"Workflow lock acquired for: {operation_name}")
        self.lock_acquired.emit(operation_name)
        return True
    
    def release_lock(self, owner: Optional[QWidget] = None) -> bool:
        """
        Release the lock.
        
        Args:
            owner: The widget releasing the lock (must match owner who acquired)
        
        Returns:
            True if lock was released, False if owner didn't match
        """
        if not self._locked:
            return True
        
        if owner is not None and self._owner != owner:
            logger.warning("Cannot release lock - owner mismatch")
            return False
        
        self._locked = False
        self._owner = None
        self._operation_name = ""
        self._cancel_callback = None
        
        logger.debug("Workflow lock released")
        self.lock_released.emit()
        return True
    
    def is_locked(self) -> bool:
        """Check if workflow is currently locked."""
        return self._locked
    
    def get_operation_name(self) -> str:
        """Get the name of the current operation holding the lock."""
        return self._operation_name
    
    def request_switch(self, parent: QWidget) -> bool:
        """
        Request to switch workflow while locked.
        
        Shows a warning dialog and optionally allows cancellation.
        
        Args:
            parent: Parent widget for the dialog
        
        Returns:
            True if switch is allowed (lock released or no lock),
            False if switch was denied
        """
        if not self._locked:
            return True
        
        # Build message
        message = (
            f"A {self._operation_name} operation is currently in progress.\n\n"
            "Switching workflows now may cause incomplete results or data loss.\n\n"
        )
        
        if self._cancel_callback:
            message += "Would you like to cancel the current operation and switch?"
            buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            default_button = QMessageBox.StandardButton.No
        else:
            message += "Please wait for the operation to complete."
            buttons = QMessageBox.StandardButton.Ok
            default_button = QMessageBox.StandardButton.Ok
        
        reply = QMessageBox.warning(
            parent,
            f"{self._operation_name} In Progress",
            message,
            buttons,
            default_button
        )
        
        if self._cancel_callback and reply == QMessageBox.StandardButton.Yes:
            # Try to cancel
            try:
                cancelled = self._cancel_callback()
                if cancelled:
                    self.release_lock()
                    return True
                else:
                    QMessageBox.information(
                        parent,
                        "Cannot Cancel",
                        "The operation could not be cancelled at this time.\n"
                        "Please wait for it to complete."
                    )
                    return False
            except Exception as e:
                logger.error(f"Error during cancel callback: {e}")
                return False
        
        return False
    
    def force_release(self):
        """
        Force release the lock (use with caution).
        
        This should only be used for error recovery.
        """
        if self._locked:
            logger.warning(f"Force releasing lock from {self._operation_name}")
            self._locked = False
            self._owner = None
            self._operation_name = ""
            self._cancel_callback = None
            self.lock_released.emit()
