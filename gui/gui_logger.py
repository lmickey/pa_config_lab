"""
Centralized GUI logging handler.

This module provides a logging handler that redirects all application
logging to the GUI logs widget.
"""

import sys
import logging
from datetime import datetime
from typing import Optional
from io import StringIO


class GUILogHandler(logging.Handler):
    """Custom logging handler that sends logs to GUI widget and file."""
    
    def __init__(self, logs_widget=None, log_file="activity.log"):
        """
        Initialize GUI log handler.
        
        Args:
            logs_widget: LogsWidget instance to send logs to
            log_file: Path to log file for persistent logging
        """
        super().__init__()
        self.logs_widget = logs_widget
        self.log_file = log_file
        self.setFormatter(logging.Formatter('%(message)s'))
        
        # Clear the log file on initialization (overwrite mode)
        try:
            with open(self.log_file, 'w') as f:
                f.write(f"=== Activity Log Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        except Exception as e:
            print(f"Warning: Could not initialize log file {self.log_file}: {e}")
    
    def emit(self, record):
        """
        Emit a log record to the GUI and file.
        
        Args:
            record: LogRecord to emit
        """
        try:
            msg = self.format(record)
            
            # Map logging levels to GUI levels
            level_map = {
                logging.DEBUG: 'info',
                logging.INFO: 'info',
                logging.WARNING: 'warning',
                logging.ERROR: 'error',
                logging.CRITICAL: 'error',
            }
            
            gui_level = level_map.get(record.levelno, 'info')
            
            # Send to GUI logs widget
            if self.logs_widget:
                self.logs_widget.log(msg, gui_level)
            
            # Write to log file with timestamp
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with open(self.log_file, 'a') as f:
                    f.write(f"[{timestamp}] {msg}\n")
            except Exception:
                pass  # Silently fail if file logging fails
            
        except Exception:
            # Silently fail if logging fails
            pass


class PrintRedirector:
    """Redirect print statements to GUI log and file."""
    
    def __init__(self, logs_widget=None, level='info', log_file="activity.log"):
        """
        Initialize print redirector.
        
        Args:
            logs_widget: LogsWidget instance
            level: Log level for print statements
            log_file: Path to log file
        """
        self.logs_widget = logs_widget
        self.level = level
        self.log_file = log_file
        self.buffer = StringIO()
        
    def write(self, text):
        """
        Write text to GUI log and file.
        
        Args:
            text: Text to write
        """
        # Filter out empty strings and just newlines
        text = text.strip()
        if not text:
            return
        
        # Check if this is an error message
        level = self.level
        if any(keyword in text.lower() for keyword in ['error', 'failed', 'exception', 'traceback']):
            level = 'error'
        elif any(keyword in text.lower() for keyword in ['warning', 'warn']):
            level = 'warning'
        elif any(keyword in text.lower() for keyword in ['success', 'completed', 'done']):
            level = 'success'
        
        # Send to GUI
        if self.logs_widget:
            self.logs_widget.log(text, level)
        
        # Write to file
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.log_file, 'a') as f:
                f.write(f"[{timestamp}] {text}\n")
        except Exception:
            pass  # Silently fail if file logging fails
    
    def flush(self):
        """Flush the buffer (required for file-like objects)."""
        pass


class ErrorLoggerGUIAdapter:
    """Adapter to send ErrorLogger output to GUI."""
    
    _instance = None
    _logs_widget = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ErrorLoggerGUIAdapter, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def set_logs_widget(cls, logs_widget):
        """
        Set the logs widget for all error logging.
        
        Args:
            logs_widget: LogsWidget instance
        """
        cls._logs_widget = logs_widget
    
    @classmethod
    def log_api_error(cls, message: str):
        """
        Log an API error to GUI.
        
        Args:
            message: Error message
        """
        if cls._logs_widget:
            cls._logs_widget.log(message, 'error')
    
    @classmethod
    def log_info(cls, message: str):
        """
        Log info message to GUI.
        
        Args:
            message: Info message
        """
        if cls._logs_widget:
            cls._logs_widget.log(message, 'info')
    
    @classmethod
    def log_warning(cls, message: str):
        """
        Log warning message to GUI.
        
        Args:
            message: Warning message
        """
        if cls._logs_widget:
            cls._logs_widget.log(message, 'warning')
    
    @classmethod
    def log_success(cls, message: str):
        """
        Log success message to GUI.
        
        Args:
            message: Success message
        """
        if cls._logs_widget:
            cls._logs_widget.log(message, 'success')


def setup_gui_logging(logs_widget):
    """
    Set up GUI logging system.
    
    This function:
    1. Redirects Python logging to GUI
    2. Redirects stdout/stderr to GUI
    3. Sets up error logger adapter
    
    Args:
        logs_widget: LogsWidget instance
    
    Returns:
        Tuple of (original_stdout, original_stderr) for restoration if needed
    """
    # Save original stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Set up logging handler
    gui_handler = GUILogHandler(logs_widget)
    gui_handler.setLevel(logging.DEBUG)
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(gui_handler)
    root_logger.setLevel(logging.INFO)
    
    # Redirect stdout (print statements)
    sys.stdout = PrintRedirector(logs_widget, level='info')
    
    # Redirect stderr (error messages)
    sys.stderr = PrintRedirector(logs_widget, level='error')
    
    # Set up error logger adapter
    ErrorLoggerGUIAdapter.set_logs_widget(logs_widget)
    
    logs_widget.log("GUI logging system initialized", "success")
    
    return original_stdout, original_stderr


def restore_standard_output(original_stdout, original_stderr):
    """
    Restore standard output streams.
    
    Args:
        original_stdout: Original stdout
        original_stderr: Original stderr
    """
    sys.stdout = original_stdout
    sys.stderr = original_stderr
