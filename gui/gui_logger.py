"""
Centralized GUI logging handler.

This module provides a logging handler that redirects all application
logging to the GUI logs widget using thread-safe Qt signals.
"""

import sys
import logging
from datetime import datetime
from typing import Optional
from io import StringIO
from PyQt6.QtCore import QObject, pyqtSignal
from config.logging_config import NORMAL, DETAIL


class LogSignalEmitter(QObject):
    """QObject that emits signals for thread-safe logging."""
    log_signal = pyqtSignal(str, str)  # message, level


class GUILogHandler(logging.Handler):
    """Custom logging handler that sends logs to GUI widget and file using thread-safe signals."""
    
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
        
        # Create signal emitter for thread-safe logging
        self.signal_emitter = LogSignalEmitter()
        
        # Connect signal to logs widget if provided
        if self.logs_widget:
            from PyQt6.QtCore import Qt
            self.signal_emitter.log_signal.connect(
                self.logs_widget.log,
                Qt.ConnectionType.QueuedConnection  # Thread-safe queued connection
            )
        
        # Clear the log file on initialization (overwrite mode)
        try:
            with open(self.log_file, 'w') as f:
                f.write(f"=== Activity Log Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        except Exception:
            # Silently fail - can't log before logging is set up
            pass
    
    def emit(self, record):
        """
        Emit a log record to the GUI and file using thread-safe signals.
        
        Args:
            record: LogRecord to emit
        """
        try:
            msg = self.format(record)
            
            # Map logging levels to GUI levels
            # Custom levels: NORMAL=25, DETAIL=15
            level_map = {
                logging.DEBUG: 'debug',
                DETAIL: 'detail',  # 15
                logging.INFO: 'info',
                NORMAL: 'normal',  # 25
                logging.WARNING: 'warning',
                logging.ERROR: 'error',
                logging.CRITICAL: 'error',
            }
            
            gui_level = level_map.get(record.levelno, 'info')
            
            # Prepend level name to message for activity log visibility
            level_name = logging.getLevelName(record.levelno)
            msg = f"[{level_name}] {msg}"
            
            # Send to GUI logs widget via SIGNAL (thread-safe)
            if self.logs_widget:
                self.signal_emitter.log_signal.emit(msg, gui_level)
            
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
    """Redirect print statements to GUI log and file using thread-safe signals."""
    
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
        
        # Create signal emitter for thread-safe logging
        self.signal_emitter = LogSignalEmitter()
        
        # Connect signal to logs widget if provided
        if self.logs_widget:
            from PyQt6.QtCore import Qt
            self.signal_emitter.log_signal.connect(
                self.logs_widget.log,
                Qt.ConnectionType.QueuedConnection  # Thread-safe queued connection
            )
        
    def write(self, text):
        """
        Write text to GUI log and file using thread-safe signals.
        
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
        
        # Send to GUI via SIGNAL (thread-safe)
        if self.logs_widget:
            self.signal_emitter.log_signal.emit(text, level)
        
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
    """Adapter to send ErrorLogger output to GUI using thread-safe signals."""
    
    _instance = None
    _logs_widget = None
    _signal_emitter = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ErrorLoggerGUIAdapter, cls).__new__(cls)
            cls._signal_emitter = LogSignalEmitter()
        return cls._instance
    
    @classmethod
    def set_logs_widget(cls, logs_widget):
        """
        Set the logs widget for all error logging.
        
        Args:
            logs_widget: LogsWidget instance
        """
        cls._logs_widget = logs_widget
        
        # Connect signal to logs widget
        if cls._logs_widget and cls._signal_emitter:
            from PyQt6.QtCore import Qt
            cls._signal_emitter.log_signal.connect(
                cls._logs_widget.log,
                Qt.ConnectionType.QueuedConnection  # Thread-safe queued connection
            )
    
    @classmethod
    def log_api_error(cls, message: str):
        """
        Log an API error to GUI using thread-safe signal.
        
        Args:
            message: Error message
        """
        if cls._logs_widget and cls._signal_emitter:
            cls._signal_emitter.log_signal.emit(message, 'error')
    
    @classmethod
    def log_info(cls, message: str):
        """
        Log info message to GUI using thread-safe signal.
        
        Args:
            message: Info message
        """
        if cls._logs_widget and cls._signal_emitter:
            cls._signal_emitter.log_signal.emit(message, 'info')
    
    @classmethod
    def log_warning(cls, message: str):
        """
        Log warning message to GUI using thread-safe signal.
        
        Args:
            message: Warning message
        """
        if cls._logs_widget and cls._signal_emitter:
            cls._signal_emitter.log_signal.emit(message, 'warning')
    
    @classmethod
    def log_success(cls, message: str):
        """
        Log success message to GUI using thread-safe signal.
        
        Args:
            message: Success message
        """
        if cls._logs_widget and cls._signal_emitter:
            cls._signal_emitter.log_signal.emit(message, 'success')


def setup_gui_logging(logs_widget):
    """
    Set up GUI logging system.
    
    This function:
    1. Redirects Python logging to GUI
    2. Redirects stdout/stderr to GUI
    3. Sets up error logger adapter
    4. Respects saved log level from settings
    
    Args:
        logs_widget: LogsWidget instance
    
    Returns:
        Tuple of (original_stdout, original_stderr) for restoration if needed
    """
    from config.logging_config import set_log_level, enable_debug_mode, disable_debug_mode
    
    # Save original stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Get saved log level from settings (default to NORMAL)
    from PyQt6.QtCore import QSettings
    settings = QSettings("PrismaAccess", "ConfigManager")
    saved_level = settings.value("advanced/log_level", NORMAL, type=int)
    
    # Set up logging handler - handler accepts all levels, filtering happens at logger level
    gui_handler = GUILogHandler(logs_widget)
    gui_handler.setLevel(logging.DEBUG)  # Handler accepts everything, logger filters
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(gui_handler)
    
    # Apply the saved log level (this also handles debug mode flag)
    set_log_level(saved_level)
    if saved_level == logging.DEBUG:
        enable_debug_mode()
    else:
        disable_debug_mode()
    
    # Redirect stdout (print statements)
    sys.stdout = PrintRedirector(logs_widget, level='info')
    
    # Redirect stderr (error messages)
    sys.stderr = PrintRedirector(logs_widget, level='error')
    
    # Set up error logger adapter
    ErrorLoggerGUIAdapter.set_logs_widget(logs_widget)
    
    level_name = logging.getLevelName(saved_level)
    logs_widget.log(f"GUI logging initialized (level: {level_name})", "success")
    
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
