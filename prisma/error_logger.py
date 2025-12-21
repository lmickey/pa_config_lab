"""
Centralized error logging for Prisma Access API operations.

This module provides a centralized error logging system that writes
detailed error information to a file with clear delimiters between runs.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
import traceback


class ErrorLogger:
    """Centralized error logger for API operations."""

    _log_file = "api_errors.log"
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ErrorLogger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._log_file = ErrorLogger._log_file
        self._current_run_start = None

    def start_run(self, test_name: Optional[str] = None):
        """
        Start a new test run session.

        Args:
            test_name: Optional name of the test being run
        """
        self._current_run_start = datetime.now()

        # Clear the log file for new run (overwrite)
        with open(self._log_file, "w") as f:
            f.write("=" * 100 + "\n")
            f.write(f"API ERROR LOG - Test Run Started\n")
            if test_name:
                f.write(f"Test: {test_name}\n")
            f.write(
                f"Timestamp: {self._current_run_start.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write("=" * 100 + "\n\n")

    def log_api_error(
        self,
        method: str,
        url: str,
        status_code: int,
        status_text: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        request_body: Optional[Any] = None,
        response_body: Optional[Any] = None,
        error: Optional[Exception] = None,
    ):
        """
        Log an API error with full details.

        Args:
            method: HTTP method
            url: Request URL
            status_code: HTTP status code
            status_text: HTTP status text
            headers: Request headers (will be masked for security)
            params: Query parameters
            request_body: Request body data
            response_body: Response body
            error: Exception object if available
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format message for GUI
        from gui.gui_logger import ErrorLoggerGUIAdapter
        
        # Check if this is a non-existent folder or restricted folder error
        if response_body and isinstance(response_body, dict):
            errors = response_body.get('_errors', [])
            for err in errors:
                details = err.get('details', {})
                if isinstance(details, dict):
                    msg = details.get('message', '')
                    if "doesn't exist" in msg or "fails to match the required pattern" in msg:
                        # Skip logging for non-existent/restricted folders - these are expected
                        return
                elif isinstance(details, list):
                    for detail in details:
                        if "fails to match the required pattern" in detail:
                            # Skip restricted folder errors
                            return

        # Log summary to GUI
        error_summary = f"API {status_code}: {method} {url}"
        if response_body and isinstance(response_body, dict):
            errors = response_body.get('_errors', [])
            if errors and len(errors) > 0:
                error_msg = errors[0].get('message', status_text)
                error_summary = f"{error_summary} - {error_msg}"
        
        ErrorLoggerGUIAdapter.log_api_error(error_summary)

        # Still write detailed log to file for debugging
        with open(self._log_file, "a") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"API ERROR - {timestamp}\n")
            f.write("=" * 80 + "\n")

            f.write(f"Method: {method}\n")
            f.write(f"URL: {url}\n")
            f.write(f"Status Code: {status_code}\n")
            f.write(f"Status Text: {status_text}\n\n")

            if headers:
                f.write("Headers:\n")
                for key, value in headers.items():
                    if "token" in key.lower() or "authorization" in key.lower():
                        # Mask sensitive tokens
                        if len(value) > 30:
                            masked = value[:20] + "..." + value[-10:]
                        else:
                            masked = "***REDACTED***"
                        f.write(f"  {key}: {masked}\n")
                    else:
                        f.write(f"  {key}: {value}\n")
                f.write("\n")

            if response_body:
                f.write("Response Body:\n")
                if isinstance(response_body, dict):
                    f.write(json.dumps(response_body, indent=2))
                else:
                    response_text = str(response_body)
                    if len(response_text) > 2000:
                        f.write(response_text[:2000])
                        f.write(
                            f"\n... (truncated, total length: {len(response_text)} chars)"
                        )
                    else:
                        f.write(response_text)
                f.write("\n\n")

            f.write("=" * 80 + "\n\n")

    def log_capture_error(
        self,
        operation: str,
        context: str,
        error: Exception,
        additional_info: Optional[Dict[str, Any]] = None,
    ):
        """
        Log an error from a capture operation.

        Args:
            operation: Name of the operation (e.g., "capture_rules_from_folder")
            context: Context information (e.g., folder name)
            error: Exception object
            additional_info: Optional additional information to log
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self._log_file, "a") as f:
            f.write("\n" + "-" * 100 + "\n")
            f.write(f"CAPTURE ERROR - {timestamp}\n")
            f.write("-" * 100 + "\n\n")

            f.write(f"Operation: {operation}\n")
            f.write(f"Context: {context}\n")
            f.write(f"Error Type: {type(error).__name__}\n")
            f.write(f"Error Message: {str(error)}\n\n")

            if additional_info:
                f.write("Additional Information:\n")
                for key, value in additional_info.items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")

            f.write("Traceback:\n")
            f.write(
                "".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                )
            )
            f.write("\n")
            f.write("-" * 100 + "\n\n")

    def end_run(self, summary: Optional[str] = None):
        """
        End the current test run session.

        Args:
            summary: Optional summary message
        """
        end_time = datetime.now()
        duration = None
        if self._current_run_start:
            duration = end_time - self._current_run_start

        with open(self._log_file, "a") as f:
            f.write("\n" + "=" * 100 + "\n")
            f.write(f"Test Run Ended\n")
            f.write(f"Timestamp: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if duration:
                f.write(f"Duration: {duration.total_seconds():.2f} seconds\n")
            if summary:
                f.write(f"Summary: {summary}\n")
            f.write("=" * 100 + "\n\n")

    def get_log_path(self) -> str:
        """Get the path to the error log file."""
        return os.path.abspath(self._log_file)

    def read_log(self) -> str:
        """Read the entire error log file."""
        try:
            with open(self._log_file, "r") as f:
                return f.read()
        except FileNotFoundError:
            return "No error log file found."

    def clear_log(self):
        """Clear the error log file."""
        with open(self._log_file, "w") as f:
            f.write("")


# Global instance
error_logger = ErrorLogger()
