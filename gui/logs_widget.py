"""
Logs widget for displaying activity and operations.

This module provides a log viewer with filtering and export capabilities.
"""

from typing import Optional
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QComboBox,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor


class LogsWidget(QWidget):
    """Widget for viewing application logs and activity."""

    def __init__(self, parent=None):
        """Initialize the logs widget."""
        super().__init__(parent)

        self.max_log_entries = 1000
        self.log_entries = []

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title and controls
        header_layout = QHBoxLayout()

        title = QLabel("<h2>Activity Logs</h2>")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Filter combo
        header_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Info", "Success", "Warning", "Error"])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        header_layout.addWidget(self.filter_combo)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_logs)
        header_layout.addWidget(clear_btn)

        # Export button
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export_logs)
        header_layout.addWidget(export_btn)

        layout.addLayout(header_layout)

        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Monospace font for logs
        font = QFont("Courier New", 9)
        self.log_text.setFont(font)

        self.log_text.setPlaceholderText(
            "Activity logs will appear here...\n\n"
            "Logs show:\n"
            "- Connection events\n"
            "- Pull operations\n"
            "- Push operations\n"
            "- Errors and warnings"
        )

        layout.addWidget(self.log_text)

        # Stats bar
        self.stats_label = QLabel("0 log entries")
        self.stats_label.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(self.stats_label)

        # Add initial log
        self.log("Application started", "info")

    def log(self, message: str, level: str = "info"):
        """
        Add a log entry.

        Args:
            message: Log message
            level: Log level (info, success, warning, error)
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = {
                "timestamp": timestamp,
                "level": level.lower(),
                "message": message,
            }

            self.log_entries.append(entry)

            # Limit log entries
            if len(self.log_entries) > self.max_log_entries:
                self.log_entries.pop(0)

            # Format and display
            self._display_entry(entry)

            # Update stats
            self._update_stats()
        except RuntimeError:
            # Widget was deleted or not accessible - silently ignore
            pass
        except Exception:
            # Any other error - silently ignore to prevent crashes
            pass

    def _display_entry(self, entry: dict):
        """Display a log entry with appropriate formatting."""
        level = entry["level"]
        timestamp = entry["timestamp"]
        message = entry["message"]

        # Color coding
        color_map = {
            "info": "#666666",
            "success": "#008800",
            "warning": "#ff8800",
            "error": "#cc0000",
        }
        color = color_map.get(level, "#000000")

        # Icon
        icon_map = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗",
        }
        icon = icon_map.get(level, "•")

        # Format entry
        formatted = (
            f'<span style="color: gray;">[{timestamp}]</span> '
            f'<span style="color: {color}; font-weight: bold;">{icon} {level.upper()}</span> '
            f"<span>{message}</span>"
        )

        # Append to display (with error handling for shutdown/threading issues)
        try:
            if not self.log_text:
                return
            self.log_text.append(formatted)

            # Auto-scroll to bottom
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
        except RuntimeError:
            # Widget was deleted or not accessible - silently ignore
            pass

    def _update_stats(self):
        """Update statistics label."""
        try:
            if not self.stats_label:
                return
                
            total = len(self.log_entries)

            # Count by level
            counts = {"info": 0, "success": 0, "warning": 0, "error": 0}
            for entry in self.log_entries:
                level = entry["level"]
                if level in counts:
                    counts[level] += 1

            self.stats_label.setText(
                f"Total: {total} | "
                f"Info: {counts['info']} | "
                f"Success: {counts['success']} | "
                f"Warnings: {counts['warning']} | "
                f"Errors: {counts['error']}"
            )
        except RuntimeError:
            # Widget was deleted or not accessible - silently ignore
            pass

    def _apply_filter(self, filter_type: str):
        """Apply log filter."""
        filter_lower = filter_type.lower()

        # Clear display
        self.log_text.clear()

        # Re-display filtered entries
        for entry in self.log_entries:
            if filter_lower == "all" or entry["level"] == filter_lower:
                self._display_entry(entry)

    def clear_logs(self):
        """Clear all logs."""
        reply = QMessageBox.question(
            self,
            "Clear Logs",
            "Are you sure you want to clear all logs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.log_entries.clear()
            self.log_text.clear()
            self._update_stats()
            self.log("Logs cleared", "info")

    def _export_logs(self):
        """Export logs to a file."""
        if not self.log_entries:
            QMessageBox.information(self, "No Logs", "There are no logs to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            f"pa_config_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)",
        )

        if file_path:
            try:
                with open(file_path, "w") as f:
                    f.write("Prisma Access Configuration Manager - Activity Log\n")
                    f.write("=" * 80 + "\n\n")

                    for entry in self.log_entries:
                        f.write(
                            f"[{entry['timestamp']}] {entry['level'].upper()}: "
                            f"{entry['message']}\n"
                        )

                QMessageBox.information(
                    self, "Success", f"Logs exported to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Export Failed", f"Failed to export logs:\n{str(e)}"
                )
