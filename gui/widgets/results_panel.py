"""
Reusable results panel widget with copy and view details functionality.

This module provides a standardized results display that can be used
across different operations (pull, push, etc.) with consistent UI.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QMessageBox,
    QDialog,
    QLabel,
    QApplication,
)
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QTextCursor
import logging


class ResultsPanel(QWidget):
    """
    Reusable results panel with copy and view details buttons.
    
    Features:
    - Text area for displaying results
    - Copy to clipboard button
    - View activity log button (can open dialog or emit signal for embedded viewer)
    - Consistent styling and behavior
    """
    
    # Signal emitted when "View Activity Log" is clicked (for embedded viewer mode)
    view_activity_log_requested = pyqtSignal()
    
    def __init__(
        self,
        parent=None,
        title: str = "Results",
        log_file: str = "logs/activity.log",
        placeholder: str = "Operation results will appear here...",
        use_embedded_log_viewer: bool = False
    ):
        """
        Initialize the results panel.
        
        Args:
            parent: Parent widget
            title: Title for the full details dialog
            log_file: Path to activity log file
            placeholder: Placeholder text for results area
            use_embedded_log_viewer: If True, emit signal instead of opening dialog
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.title = title
        self.log_file = log_file
        self.use_embedded_log_viewer = use_embedded_log_viewer
        
        self._init_ui(placeholder)
    
    def _init_ui(self, placeholder: str):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Results text area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText(placeholder)
        self.results_text.setStyleSheet(
            "QTextEdit { "
            "font-family: 'Courier New', monospace; "
            "font-size: 10pt; "
            "background-color: #f5f5f5; "
            "border: 1px solid #ddd; "
            "padding: 5px; "
            "}"
        )
        layout.addWidget(self.results_text)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        # Small grey button style for utility buttons
        small_grey_style = (
            "QPushButton { "
            "  background-color: #757575; color: white; padding: 4px 10px; "
            "  font-size: 11px; border-radius: 3px; "
            "  border: 1px solid #616161; border-bottom: 2px solid #424242; "
            "}"
            "QPushButton:hover { background-color: #616161; border-bottom: 2px solid #212121; }"
            "QPushButton:pressed { background-color: #616161; border-bottom: 1px solid #424242; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #9E9E9E; border: 1px solid #9E9E9E; border-bottom: 2px solid #757575; }"
        )
        
        # Copy results button
        self.copy_results_btn = QPushButton("📋 Copy Results")
        self.copy_results_btn.setToolTip("Copy all results to clipboard")
        self.copy_results_btn.setStyleSheet(small_grey_style)
        self.copy_results_btn.clicked.connect(self._copy_results)
        self.copy_results_btn.setEnabled(False)
        buttons_layout.addWidget(self.copy_results_btn)
        
        # View activity log button
        self.view_details_btn = QPushButton("📄 View Activity Log")
        self.view_details_btn.setToolTip("View detailed activity log")
        self.view_details_btn.setStyleSheet(small_grey_style)
        self.view_details_btn.clicked.connect(self._on_view_activity_log_clicked)
        self.view_details_btn.setEnabled(False)
        buttons_layout.addWidget(self.view_details_btn)
        
        layout.addLayout(buttons_layout)
    
    def append_text(self, text: str):
        """
        Append text to results area.
        
        Args:
            text: Text to append
        """
        self.results_text.append(text)
        
        # Enable buttons once there's content
        if not self.copy_results_btn.isEnabled():
            self.copy_results_btn.setEnabled(True)
            self.view_details_btn.setEnabled(True)
    
    def set_text(self, text: str):
        """
        Set (replace) text in results area.
        
        Args:
            text: Text to set
        """
        self.results_text.setPlainText(text)
        
        # Enable buttons once there's content
        if not self.copy_results_btn.isEnabled():
            self.copy_results_btn.setEnabled(True)
            self.view_details_btn.setEnabled(True)
    
    def clear(self):
        """Clear results text and disable buttons."""
        self.results_text.clear()
        self.copy_results_btn.setEnabled(False)
        self.view_details_btn.setEnabled(False)
        # Reset background color
        self.results_text.setStyleSheet(
            "QTextEdit { "
            "font-family: 'Courier New', monospace; "
            "font-size: 10pt; "
            "background-color: #f5f5f5; "
            "border: 1px solid #ddd; "
            "padding: 5px; "
            "}"
        )

    def set_success(self, success: bool):
        """
        Set the success state, updating the visual styling.
        
        Args:
            success: True for success (green tint), False for failure (red tint)
        """
        if success:
            bg_color = "#e8f5e9"  # Light green
            border_color = "#4CAF50"
        else:
            bg_color = "#ffebee"  # Light red
            border_color = "#f44336"
        
        self.results_text.setStyleSheet(
            f"QTextEdit {{ "
            f"font-family: 'Courier New', monospace; "
            f"font-size: 10pt; "
            f"background-color: {bg_color}; "
            f"border: 1px solid {border_color}; "
            f"padding: 5px; "
            f"}}"
        )
    
    def get_text(self) -> str:
        """
        Get current results text.
        
        Returns:
            Plain text from results area
        """
        return self.results_text.toPlainText()
    
    def _copy_results(self):
        """Copy results text to clipboard."""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.results_text.toPlainText())
            
            # Show brief feedback
            original_text = self.copy_results_btn.text()
            self.copy_results_btn.setText("✓ Copied!")
            self.copy_results_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            
            # Reset after 2 seconds
            QTimer.singleShot(2000, lambda: (
                self.copy_results_btn.setText(original_text),
                self.copy_results_btn.setStyleSheet("")
            ))
        except Exception as e:
            self.logger.error(f"Failed to copy results: {e}")
            QMessageBox.warning(self, "Copy Failed", f"Failed to copy results: {e}")
    
    def _on_view_activity_log_clicked(self):
        """Handle view activity log button click."""
        if self.use_embedded_log_viewer:
            # Emit signal for parent to handle with embedded viewer
            self.view_activity_log_requested.emit()
        else:
            # Open dialog (fallback behavior)
            self._open_activity_log_dialog()
    
    def _open_activity_log_dialog(self):
        """Open a dialog to view full activity log details with search/filter and live refresh."""
        try:
            from gui.logs_widget import LogsWidget
            from PyQt6.QtCore import QTimer
            import os

            dialog = QDialog(self)
            dialog.setWindowTitle(f"{self.title} - Activity Log (Live)")
            dialog.resize(1100, 750)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(8, 8, 8, 8)

            # Use the full-featured LogsWidget with search and filter
            logs_widget = LogsWidget(dialog)

            # Track file position for incremental reads
            last_position = [0]  # Use list to allow modification in nested function
            last_line_count = [0]

            def parse_log_level(line):
                """Parse log level from line."""
                if " - DEBUG - " in line:
                    return "debug"
                elif " - WARNING - " in line:
                    return "warning"
                elif " - ERROR - " in line or " - CRITICAL - " in line:
                    return "error"
                elif " - DETAIL - " in line:
                    return "detail"
                return "info"

            def load_initial_logs():
                """Load initial log entries from file."""
                try:
                    if os.path.exists(self.log_file):
                        with open(self.log_file, 'r') as f:
                            lines = f.readlines()
                            # Load last 500 lines initially
                            start_idx = max(0, len(lines) - 500)
                            for line in lines[start_idx:]:
                                line = line.strip()
                                if line:
                                    logs_widget.log(line, parse_log_level(line))
                            last_line_count[0] = len(lines)
                            f.seek(0, 2)  # Seek to end
                            last_position[0] = f.tell()
                except Exception as e:
                    self.logger.error(f"Error loading initial logs: {e}")

            def refresh_logs():
                """Check for new log entries and append them."""
                try:
                    if not os.path.exists(self.log_file):
                        return

                    current_size = os.path.getsize(self.log_file)

                    # If file was truncated/rotated, reload from beginning
                    if current_size < last_position[0]:
                        last_position[0] = 0
                        last_line_count[0] = 0

                    if current_size > last_position[0]:
                        with open(self.log_file, 'r') as f:
                            f.seek(last_position[0])
                            new_content = f.read()
                            last_position[0] = f.tell()

                            for line in new_content.splitlines():
                                line = line.strip()
                                if line:
                                    logs_widget.log(line, parse_log_level(line))

                            # Auto-scroll to bottom if user hasn't scrolled up
                            scrollbar = logs_widget.log_text.verticalScrollBar()
                            if scrollbar.value() >= scrollbar.maximum() - 50:
                                scrollbar.setValue(scrollbar.maximum())
                except Exception as e:
                    pass  # Silently ignore refresh errors

            # Load initial content
            load_initial_logs()

            layout.addWidget(logs_widget)

            # Status bar showing live refresh
            status_layout = QHBoxLayout()
            status_label = QLabel("🔄 Live refresh enabled (1 second interval)")
            status_label.setStyleSheet("color: #666; font-size: 11px;")
            status_layout.addWidget(status_label)
            status_layout.addStretch()

            close_btn = QPushButton("Close")
            close_btn.setMinimumWidth(100)
            close_btn.clicked.connect(dialog.close)
            close_btn.setStyleSheet(
                "QPushButton { "
                "  background-color: #757575; color: white; padding: 8px 16px; "
                "  font-size: 12px; border-radius: 4px; "
                "  border: 1px solid #616161; border-bottom: 2px solid #424242; "
                "}"
                "QPushButton:hover { background-color: #616161; border-bottom: 2px solid #212121; }"
                "QPushButton:pressed { background-color: #616161; border-bottom: 1px solid #424242; }"
            )
            status_layout.addWidget(close_btn)

            layout.addLayout(status_layout)

            # Set up refresh timer (1 second interval)
            refresh_timer = QTimer(dialog)
            refresh_timer.timeout.connect(refresh_logs)
            refresh_timer.start(1000)  # Refresh every 1 second

            # Stop timer when dialog closes
            dialog.finished.connect(refresh_timer.stop)

            dialog.exec()
        except Exception as e:
            self.logger.error(f"Failed to open details viewer: {e}")
            QMessageBox.warning(self, "View Details Failed", f"Failed to open details viewer: {e}")
