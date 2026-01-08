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
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QTextCursor
import logging


class ResultsPanel(QWidget):
    """
    Reusable results panel with copy and view details buttons.
    
    Features:
    - Text area for displaying results
    - Copy to clipboard button
    - View full details button (opens activity log)
    - Consistent styling and behavior
    """
    
    def __init__(
        self,
        parent=None,
        title: str = "Results",
        log_file: str = "logs/activity.log",
        placeholder: str = "Operation results will appear here..."
    ):
        """
        Initialize the results panel.
        
        Args:
            parent: Parent widget
            title: Title for the full details dialog
            log_file: Path to activity log file
            placeholder: Placeholder text for results area
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.title = title
        self.log_file = log_file
        
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
        
        # View details button
        self.view_details_btn = QPushButton("📄 View Full Details")
        self.view_details_btn.setToolTip("Open detailed log viewer")
        self.view_details_btn.setStyleSheet(small_grey_style)
        self.view_details_btn.clicked.connect(self._view_full_details)
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
    
    def _view_full_details(self):
        """Open a dialog to view full activity log details with search/filter."""
        try:
            from gui.logs_widget import LogsWidget
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"{self.title} - Activity Log")
            dialog.resize(1100, 750)
            
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(8, 8, 8, 8)
            
            # Use the full-featured LogsWidget with search and filter
            logs_widget = LogsWidget(dialog)
            
            # Load log entries from file
            try:
                with open(self.log_file, 'r') as f:
                    for line in f.readlines()[-1000:]:  # Last 1000 lines
                        line = line.strip()
                        if line:
                            # Try to parse log level from line
                            level = "info"
                            if " - DEBUG - " in line:
                                level = "debug"
                            elif " - WARNING - " in line:
                                level = "warning"
                            elif " - ERROR - " in line:
                                level = "error"
                            elif " - CRITICAL - " in line:
                                level = "error"
                            
                            logs_widget.log(line, level)
            except Exception as read_err:
                self.logger.error(f"Error reading {self.log_file}: {read_err}")
                logs_widget.log(f"Error reading {self.log_file}: {read_err}", "error")
            
            layout.addWidget(logs_widget)
            
            # Close button at bottom
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
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
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            dialog.exec()
        except Exception as e:
            self.logger.error(f"Failed to open details viewer: {e}")
            QMessageBox.warning(self, "View Details Failed", f"Failed to open details viewer: {e}")
