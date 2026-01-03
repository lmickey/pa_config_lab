"""
Logging configuration for Prisma Access Configuration Lab.

Provides centralized logging configuration with support for:
- Multiple log levels (ERROR, WARNING, NORMAL, INFO, DEBUG)
- Debug mode for detailed diagnostics
- Structured log formatting
- Activity logging
- Performance tracking
- Log rotation and retention
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timedelta
import shutil


# Custom NORMAL log level (between WARNING and INFO)
NORMAL = 25
logging.addLevelName(NORMAL, 'NORMAL')

# Default log level
DEFAULT_LOG_LEVEL = NORMAL

# Debug mode flag (can be toggled at runtime)
_debug_mode = False

# Log format templates
STANDARD_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEBUG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
SIMPLE_FORMAT = "%(levelname)s - %(message)s"


def normal(self, message, *args, **kwargs):
    """Log a message at NORMAL level."""
    if self.isEnabledFor(NORMAL):
        self._log(NORMAL, message, args, **kwargs)

# Add normal() method to Logger class
logging.Logger.normal = normal


class DebugModeFilter(logging.Filter):
    """Filter that allows debug messages only when debug mode is enabled."""
    
    def filter(self, record):
        """Filter log records based on debug mode."""
        # Always allow non-DEBUG messages
        if record.levelno != logging.DEBUG:
            return True
        # For DEBUG messages, check if debug mode is enabled
        return _debug_mode


def rotate_logs(log_file: Path, keep_count: int = 7) -> None:
    """
    Rotate log files on startup.
    
    Renames current log to activity-1.log, and shifts existing rotations up.
    Deletes oldest log if keep_count is exceeded.
    
    Args:
        log_file: Path to the log file
        keep_count: Number of log file copies to keep (default: 7)
    """
    if not log_file.exists():
        return
    
    # Rotate existing logs (highest to lowest)
    for i in range(keep_count - 1, 0, -1):
        old_file = log_file.parent / f"{log_file.stem}-{i}{log_file.suffix}"
        new_file = log_file.parent / f"{log_file.stem}-{i+1}{log_file.suffix}"
        
        if old_file.exists():
            if new_file.exists():
                new_file.unlink()  # Delete if exists
            old_file.rename(new_file)
    
    # Move current log to -1
    archived = log_file.parent / f"{log_file.stem}-1{log_file.suffix}"
    if archived.exists():
        archived.unlink()
    log_file.rename(archived)


def prune_logs(
    log_directory: Path,
    log_pattern: str = "activity*.log",
    keep_count: Optional[int] = None,
    keep_days: Optional[int] = None
) -> int:
    """
    Prune old log files based on count or age.
    
    Args:
        log_directory: Directory containing log files
        log_pattern: Glob pattern for log files (default: "activity*.log")
        keep_count: Keep only this many most recent logs (by modification time)
        keep_days: Keep only logs modified within this many days
        
    Returns:
        Number of logs deleted
    """
    if not log_directory.exists():
        return 0
    
    log_files = sorted(
        log_directory.glob(log_pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True  # Newest first
    )
    
    deleted_count = 0
    
    # Prune by count
    if keep_count is not None:
        for log_file in log_files[keep_count:]:
            log_file.unlink()
            deleted_count += 1
    
    # Prune by age
    if keep_days is not None:
        cutoff = datetime.now() - timedelta(days=keep_days)
        for log_file in log_files:
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                log_file.unlink()
                deleted_count += 1
    
    return deleted_count


def setup_logging(
    level: int = DEFAULT_LOG_LEVEL,
    log_file: Optional[Path] = None,
    console: bool = True,
    debug: bool = False,
    rotate: bool = True,
    keep_rotations: int = 7
):
    """
    Set up logging configuration.
    
    Args:
        level: Log level (logging.ERROR, WARNING, NORMAL, INFO, DEBUG)
        log_file: Optional file path for log output
        console: Whether to log to console
        debug: Enable debug mode
        rotate: Whether to rotate logs on startup (default: True)
        keep_rotations: Number of log rotations to keep (default: 7)
    """
    global _debug_mode
    _debug_mode = debug
    
    # Rotate logs before opening new file
    if log_file and rotate:
        rotate_logs(log_file, keep_count=keep_rotations)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    if debug:
        formatter = logging.Formatter(DEBUG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
    else:
        formatter = logging.Formatter(STANDARD_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
    
    # Add console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(DebugModeFilter())
        root_logger.addHandler(console_handler)
    
    # Add file handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG if debug else level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(DebugModeFilter())
        root_logger.addHandler(file_handler)
    
    # Log initial message
    level_name = 'DEBUG' if debug else logging.getLevelName(level)
    root_logger.info(f"Logging initialized (level={level_name}, debug={debug})")


def enable_debug_mode():
    """Enable debug mode logging."""
    global _debug_mode
    _debug_mode = True
    logging.getLogger().setLevel(logging.DEBUG)
    # Also update all handlers to DEBUG level
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.DEBUG)
    logging.info("Debug mode ENABLED")


def disable_debug_mode():
    """Disable debug mode logging."""
    global _debug_mode
    _debug_mode = False
    logging.getLogger().setLevel(DEFAULT_LOG_LEVEL)
    logging.info("Debug mode DISABLED")


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return _debug_mode


def set_log_level(level: int):
    """
    Set logging level at runtime.
    
    Args:
        level: Log level (logging.ERROR, WARNING, NORMAL, INFO, DEBUG)
    """
    logging.getLogger().setLevel(level)
    for handler in logging.getLogger().handlers:
        handler.setLevel(level)
    logging.info(f"Log level changed to {logging.getLevelName(level)}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class ActivityLogger:
    """
    Logger for user activity and workflow operations.
    
    Provides structured logging for:
    - User actions
    - Workflow operations
    - API calls
    - Configuration changes
    """
    
    def __init__(self, name: str = "activity"):
        """Initialize activity logger."""
        self.logger = logging.getLogger(f"activity.{name}")
    
    def log_action(
        self,
        action: str,
        item_type: Optional[str] = None,
        item_name: Optional[str] = None,
        details: Optional[str] = None
    ):
        """
        Log a user action.
        
        Args:
            action: Action performed (create, update, delete, etc.)
            item_type: Type of item affected
            item_name: Name of item affected
            details: Additional details
        """
        message_parts = [f"Action: {action}"]
        
        if item_type and item_name:
            message_parts.append(f"{item_type} '{item_name}'")
        elif item_type:
            message_parts.append(f"{item_type}")
        
        if details:
            message_parts.append(f"- {details}")
        
        self.logger.info(" ".join(message_parts))
    
    def log_workflow_start(self, workflow: str, details: Optional[str] = None):
        """Log workflow start."""
        message = f"Workflow START: {workflow}"
        if details:
            message += f" - {details}"
        self.logger.info(message)
    
    def log_workflow_complete(
        self,
        workflow: str,
        success: bool,
        duration: Optional[float] = None,
        summary: Optional[str] = None
    ):
        """Log workflow completion."""
        status = "SUCCESS" if success else "FAILED"
        message = f"Workflow {status}: {workflow}"
        
        if duration:
            message += f" (duration: {duration:.2f}s)"
        
        if summary:
            message += f" - {summary}"
        
        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)
    
    def log_api_call(
        self,
        method: str,
        endpoint: str,
        status_code: Optional[int] = None,
        duration: Optional[float] = None
    ):
        """Log API call."""
        message = f"API {method} {endpoint}"
        
        if status_code:
            message += f" → {status_code}"
        
        if duration:
            message += f" ({duration:.3f}s)"
        
        if status_code and status_code >= 400:
            self.logger.warning(message)
        else:
            self.logger.debug(message)
    
    def log_config_change(
        self,
        action: str,
        item_type: str,
        item_name: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None
    ):
        """Log configuration change."""
        message = f"Config {action}: {item_type} '{item_name}'"
        
        if old_value is not None and new_value is not None:
            message += f" ({old_value} → {new_value})"
        elif new_value is not None:
            message += f" = {new_value}"
        
        self.logger.info(message)


# Initialize default logging on import
setup_logging()
