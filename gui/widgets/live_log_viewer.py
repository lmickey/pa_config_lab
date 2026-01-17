"""
Live Log Viewer Widget - Embeddable real-time activity log viewer.

This module provides a live log viewer that can be embedded in any workflow
to show real-time activity log updates during operations like validation and push.
It mirrors the functionality of the main LogsWidget but is designed for inline use.
"""

from typing import Optional, List, Callable
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QComboBox,
    QLineEdit,
    QApplication,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QTextDocument
import logging
import os


class LiveLogViewer(QWidget):
    """
    Embeddable live log viewer with filtering, search, and export capabilities.
    
    This widget can be added to any workflow to provide real-time log viewing
    during long-running operations. It connects to the Python logging system
    and displays new entries as they occur.
    
    Features:
    - Live log updates via QTimer polling
    - Search with highlighting
    - Filter by log level
    - Export to file
    - Copy to clipboard
    - Auto-scroll with manual override
    """
    
    # Signal emitted when close button is clicked
    close_requested = pyqtSignal()
    
    def __init__(
        self,
        parent=None,
        log_file: str = "logs/activity.log",
        title: str = "Live Activity Log",
        show_close_button: bool = True,
        poll_interval_ms: int = 500,
        compact: bool = False
    ):
        """
        Initialize the live log viewer.
        
        Args:
            parent: Parent widget
            log_file: Path to activity log file to monitor
            title: Title to display
            show_close_button: Whether to show a close button
            poll_interval_ms: How often to check for new log entries
            compact: If True, use more compact layout
        """
        super().__init__(parent)
        self.log_file = log_file
        self.title = title
        self.show_close_button = show_close_button
        self.poll_interval_ms = poll_interval_ms
        self.compact = compact
        
        # State
        self._last_file_position = 0
        self._log_entries: List[dict] = []
        self._auto_scroll = True
        self._is_live = False
        
        # Search state
        self._search_matches: List[int] = []
        self._current_match_index: int = -1
        self._search_text: str = ""
        
        # Search debounce timer
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._execute_search)
        self._pending_search_text: str = ""
        self._min_search_chars: int = 3
        self._search_debounce_ms: int = 250
        
        # Poll timer for live updates
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll_log_file)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4 if self.compact else 8)
        
        # Header row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)
        
        # Title with live indicator
        self.title_label = QLabel(f"<b>{self.title}</b>")
        header_layout.addWidget(self.title_label)
        
        # Live indicator
        self.live_indicator = QLabel("⚫")
        self.live_indicator.setToolTip("Not live")
        self.live_indicator.setStyleSheet("color: #999; font-size: 10px;")
        header_layout.addWidget(self.live_indicator)
        
        header_layout.addStretch()
        
        # Search controls
        if not self.compact:
            header_layout.addWidget(QLabel("Search:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search..." if self.compact else "Type to search...")
        self.search_input.setFixedWidth(120 if self.compact else 160)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._search_next)
        header_layout.addWidget(self.search_input)
        
        # Navigation buttons
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedWidth(24)
        self.prev_btn.setToolTip("Previous match")
        self.prev_btn.clicked.connect(self._search_prev)
        self.prev_btn.setEnabled(False)
        header_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedWidth(24)
        self.next_btn.setToolTip("Next match")
        self.next_btn.clicked.connect(self._search_next)
        self.next_btn.setEnabled(False)
        header_layout.addWidget(self.next_btn)
        
        # Match counter
        self.match_label = QLabel("")
        self.match_label.setFixedWidth(50 if self.compact else 60)
        self.match_label.setStyleSheet("color: #666; font-size: 10px;")
        header_layout.addWidget(self.match_label)
        
        # Separator
        sep = QLabel("|")
        sep.setStyleSheet("color: #ccc;")
        header_layout.addWidget(sep)
        
        # Filter combo
        if not self.compact:
            header_layout.addWidget(QLabel("Filter:"))
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Error",
            "Warning", 
            "Normal",
            "Info",
            "Detail",
            "Debug",
        ])
        self.filter_combo.setCurrentText("Normal")  # Default to show normal and above
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        self.filter_combo.setFixedWidth(70 if self.compact else 85)
        header_layout.addWidget(self.filter_combo)
        
        # Action buttons
        small_btn_style = (
            "QPushButton { padding: 2px 6px; font-size: 10px; }"
            "QPushButton:disabled { color: #999; }"
        )
        
        # Auto-scroll toggle
        self.auto_scroll_btn = QPushButton("⏬")
        self.auto_scroll_btn.setFixedWidth(24)
        self.auto_scroll_btn.setToolTip("Auto-scroll enabled (click to disable)")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.clicked.connect(self._toggle_auto_scroll)
        self.auto_scroll_btn.setStyleSheet(small_btn_style)
        header_layout.addWidget(self.auto_scroll_btn)
        
        # Copy button
        self.copy_btn = QPushButton("📋")
        self.copy_btn.setFixedWidth(24)
        self.copy_btn.setToolTip("Copy log to clipboard")
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        self.copy_btn.setStyleSheet(small_btn_style)
        header_layout.addWidget(self.copy_btn)
        
        # Export button
        self.export_btn = QPushButton("💾")
        self.export_btn.setFixedWidth(24)
        self.export_btn.setToolTip("Export log to file")
        self.export_btn.clicked.connect(self._export_logs)
        self.export_btn.setStyleSheet(small_btn_style)
        header_layout.addWidget(self.export_btn)
        
        # Close button (optional)
        if self.show_close_button:
            self.close_btn = QPushButton("✕")
            self.close_btn.setFixedWidth(24)
            self.close_btn.setToolTip("Close log viewer")
            self.close_btn.clicked.connect(self._on_close_clicked)
            self.close_btn.setStyleSheet(
                "QPushButton { padding: 2px 6px; font-size: 10px; color: #666; }"
                "QPushButton:hover { color: #c00; background-color: #fee; }"
            )
            header_layout.addWidget(self.close_btn)
        
        layout.addLayout(header_layout)
        
        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        # Monospace font
        font = QFont("Courier New", 9)
        self.log_text.setFont(font)
        
        self.log_text.setPlaceholderText(
            "Live activity log will appear here...\n\n"
            "Showing operations as they occur."
        )
        
        self.log_text.setStyleSheet(
            "QTextEdit { "
            "background-color: #1e1e1e; "
            "color: #d4d4d4; "
            "border: 1px solid #333; "
            "padding: 4px; "
            "}"
        )
        
        layout.addWidget(self.log_text)
        
        # Status bar
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)
        
        self.status_label = QLabel("0 entries")
        self.status_label.setStyleSheet("color: #888; font-size: 10px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.file_label = QLabel(f"📄 {os.path.basename(self.log_file)}")
        self.file_label.setStyleSheet("color: #888; font-size: 10px;")
        status_layout.addWidget(self.file_label)
        
        layout.addLayout(status_layout)
    
    def start_live(self):
        """Start live log monitoring."""
        if self._is_live:
            return
        
        self._is_live = True
        
        # Reset file position to end (only show new entries)
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    f.seek(0, 2)  # Seek to end
                    self._last_file_position = f.tell()
        except Exception:
            self._last_file_position = 0
        
        # Update live indicator
        self.live_indicator.setText("🔴")
        self.live_indicator.setToolTip("Live - monitoring for new entries")
        self.live_indicator.setStyleSheet("color: #e00; font-size: 10px;")
        
        # Start polling
        self._poll_timer.start(self.poll_interval_ms)
        
        # Add initial message
        self._add_entry({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": "info",
            "message": "🔴 Live monitoring started..."
        })
    
    def stop_live(self):
        """Stop live log monitoring."""
        if not self._is_live:
            return
        
        self._is_live = False
        self._poll_timer.stop()
        
        # Update live indicator
        self.live_indicator.setText("⚫")
        self.live_indicator.setToolTip("Stopped")
        self.live_indicator.setStyleSheet("color: #999; font-size: 10px;")
        
        # Add completion message
        self._add_entry({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": "info",
            "message": "⚫ Live monitoring stopped."
        })
    
    def load_recent(self, num_lines: int = 100):
        """
        Load recent log entries from file.
        
        Args:
            num_lines: Number of recent lines to load
        """
        try:
            if not os.path.exists(self.log_file):
                return
            
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-num_lines:] if len(lines) > num_lines else lines
                
                for line in recent_lines:
                    self._parse_and_add_line(line.strip())
                
                # Update file position
                self._last_file_position = f.tell()
        except Exception as e:
            self._add_entry({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "error",
                "message": f"Error loading log file: {e}"
            })
    
    def clear(self):
        """Clear all displayed log entries."""
        self._log_entries.clear()
        self.log_text.clear()
        self._update_status()
    
    def _poll_log_file(self):
        """Poll log file for new entries."""
        try:
            if not os.path.exists(self.log_file):
                return
            
            with open(self.log_file, 'r') as f:
                # Check if file was truncated/rotated
                f.seek(0, 2)
                current_size = f.tell()
                
                if current_size < self._last_file_position:
                    # File was truncated - start from beginning
                    self._last_file_position = 0
                
                # Read new content
                f.seek(self._last_file_position)
                new_content = f.read()
                self._last_file_position = f.tell()
                
                if new_content:
                    for line in new_content.splitlines():
                        if line.strip():
                            self._parse_and_add_line(line.strip())
        except Exception:
            pass  # Silently ignore poll errors
    
    def _parse_and_add_line(self, line: str):
        """Parse a log line and add it to the display."""
        if not line:
            return
        
        # Parse log level from line
        level = "info"
        if " - DEBUG - " in line or "[DEBUG]" in line:
            level = "debug"
        elif " - DETAIL - " in line or "[DETAIL]" in line:
            level = "detail"
        elif " - NORMAL - " in line or "[NORMAL]" in line:
            level = "normal"
        elif " - WARNING - " in line or "[WARNING]" in line:
            level = "warning"
        elif " - ERROR - " in line or "[ERROR]" in line:
            level = "error"
        elif " - INFO - " in line or "[INFO]" in line:
            level = "info"
        
        # Try to extract timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        if line and line[0].isdigit() and len(line) > 19:
            # Might have timestamp at start
            possible_ts = line[:19]
            try:
                datetime.strptime(possible_ts, "%Y-%m-%d %H:%M:%S")
                timestamp = line[11:19]  # Just time portion
                line = line[22:].strip() if len(line) > 22 else line
            except ValueError:
                pass
        
        # Strip common prefixes
        for prefix in [" - DEBUG - ", " - DETAIL - ", " - NORMAL - ", " - INFO - ", " - WARNING - ", " - ERROR - "]:
            if prefix in line:
                line = line.split(prefix, 1)[-1]
                break
        
        entry = {
            "timestamp": timestamp,
            "level": level,
            "message": line
        }
        
        self._add_entry(entry)
    
    def _add_entry(self, entry: dict):
        """Add a log entry and display it if it passes the filter."""
        self._log_entries.append(entry)
        
        # Check if entry passes current filter
        if self._should_display_entry(entry):
            self._display_entry(entry)
        
        self._update_status()
    
    def _should_display_entry(self, entry: dict) -> bool:
        """Check if an entry should be displayed based on current filter."""
        filter_lower = self.filter_combo.currentText().lower()
        
        level_hierarchy = {
            'error': 1,
            'warning': 2,
            'normal': 3,
            'success': 3,
            'info': 4,
            'detail': 5,
            'debug': 6,
        }
        
        filter_threshold = level_hierarchy.get(filter_lower, 6)
        entry_level = level_hierarchy.get(entry["level"], 6)
        
        return entry_level <= filter_threshold
    
    def _display_entry(self, entry: dict):
        """Display a log entry with appropriate formatting."""
        level = entry["level"]
        timestamp = entry["timestamp"]
        message = entry["message"]
        
        # Color coding for dark theme
        color_map = {
            "debug": "#6a9955",    # Green-gray
            "detail": "#808080",   # Gray
            "info": "#9cdcfe",     # Light blue
            "normal": "#d4d4d4",   # Light gray (default text)
            "success": "#4ec9b0",  # Cyan
            "warning": "#dcdcaa",  # Yellow
            "error": "#f44747",    # Red
        }
        color = color_map.get(level, "#d4d4d4")
        
        # Icon
        icon_map = {
            "debug": "🔍",
            "detail": "📋",
            "info": "ℹ",
            "normal": "●",
            "success": "✓",
            "warning": "⚠",
            "error": "✗",
        }
        icon = icon_map.get(level, "•")
        
        # Format entry
        formatted = (
            f'<span style="color: #888;">[{timestamp}]</span> '
            f'<span style="color: {color};">{icon}</span> '
            f'<span style="color: {color};">{message}</span>'
        )
        
        try:
            self.log_text.append(formatted)
            
            # Auto-scroll if enabled
            if self._auto_scroll:
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.log_text.setTextCursor(cursor)
        except RuntimeError:
            pass  # Widget deleted
    
    def _update_status(self):
        """Update the status bar."""
        total = len(self._log_entries)
        
        # Count by level
        counts = {"error": 0, "warning": 0}
        for entry in self._log_entries:
            level = entry["level"]
            if level in counts:
                counts[level] += 1
        
        status_parts = [f"{total} entries"]
        if counts["error"] > 0:
            status_parts.append(f"❌ {counts['error']} errors")
        if counts["warning"] > 0:
            status_parts.append(f"⚠ {counts['warning']} warnings")
        
        self.status_label.setText(" | ".join(status_parts))
    
    def _on_filter_changed(self, filter_type: str):
        """Handle filter change - re-render all entries."""
        self.log_text.clear()
        
        for entry in self._log_entries:
            if self._should_display_entry(entry):
                self._display_entry(entry)
        
        # Re-apply search if active
        if self._search_text:
            self._pending_search_text = self._search_text
            self._search_text = ""
            self._execute_search()
    
    def _toggle_auto_scroll(self):
        """Toggle auto-scroll behavior."""
        self._auto_scroll = self.auto_scroll_btn.isChecked()
        
        if self._auto_scroll:
            self.auto_scroll_btn.setToolTip("Auto-scroll enabled (click to disable)")
            # Scroll to end
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
        else:
            self.auto_scroll_btn.setToolTip("Auto-scroll disabled (click to enable)")
    
    def _copy_to_clipboard(self):
        """Copy log content to clipboard."""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.log_text.toPlainText())
            
            # Brief feedback
            original = self.copy_btn.text()
            self.copy_btn.setText("✓")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText(original))
        except Exception:
            pass
    
    def _export_logs(self):
        """Export logs to file."""
        if not self._log_entries:
            QMessageBox.information(self, "No Logs", "No log entries to export.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            f"operation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(f"Operation Log - Exported {datetime.now().isoformat()}\n")
                    f.write("=" * 70 + "\n\n")
                    
                    for entry in self._log_entries:
                        f.write(f"[{entry['timestamp']}] {entry['level'].upper()}: {entry['message']}\n")
                
                QMessageBox.information(self, "Success", f"Logs exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export logs:\n{e}")
    
    def _on_close_clicked(self):
        """Handle close button click."""
        self.stop_live()
        self.close_requested.emit()
    
    # Search methods (same pattern as LogsWidget)
    def _on_search_text_changed(self, text: str):
        """Handle search text changes with debouncing."""
        self._pending_search_text = text
        self._search_timer.stop()
        
        if not text:
            self._search_text = ""
            self._search_matches.clear()
            self._current_match_index = -1
            self._clear_search_highlights()
            self.match_label.setText("")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return
        
        if len(text) < self._min_search_chars:
            self.match_label.setText(f"{self._min_search_chars - len(text)}+")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return
        
        self.match_label.setText("...")
        self._search_timer.start(self._search_debounce_ms)
    
    def _execute_search(self):
        """Execute search after debounce."""
        text = self._pending_search_text
        
        if len(text) < self._min_search_chars:
            return
        
        self._search_text = text
        self._search_matches.clear()
        self._current_match_index = -1
        
        # Clear existing highlights by re-rendering
        self._on_filter_changed(self.filter_combo.currentText())
        
        # Find matches
        document = self.log_text.document()
        cursor = QTextCursor(document)
        
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor(255, 255, 0))
        highlight_format.setForeground(QColor(0, 0, 0))
        
        while True:
            cursor = document.find(text, cursor, QTextDocument.FindFlag(0))
            if cursor.isNull():
                break
            self._search_matches.append(cursor.selectionStart())
            cursor.mergeCharFormat(highlight_format)
        
        match_count = len(self._search_matches)
        if match_count > 0:
            self._current_match_index = 0
            self._go_to_match(0)
            self.match_label.setText(f"1/{match_count}")
            self.prev_btn.setEnabled(match_count > 1)
            self.next_btn.setEnabled(match_count > 1)
        else:
            self.match_label.setText("0")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
    
    def _clear_search_highlights(self):
        """Clear search highlights by re-rendering."""
        self._on_filter_changed(self.filter_combo.currentText())
    
    def _search_next(self):
        """Go to next match."""
        if not self._search_matches:
            return
        self._current_match_index = (self._current_match_index + 1) % len(self._search_matches)
        self._go_to_match(self._current_match_index)
        self.match_label.setText(f"{self._current_match_index + 1}/{len(self._search_matches)}")
    
    def _search_prev(self):
        """Go to previous match."""
        if not self._search_matches:
            return
        self._current_match_index = (self._current_match_index - 1) % len(self._search_matches)
        self._go_to_match(self._current_match_index)
        self.match_label.setText(f"{self._current_match_index + 1}/{len(self._search_matches)}")
    
    def _go_to_match(self, index: int):
        """Navigate to a specific match."""
        if index < 0 or index >= len(self._search_matches):
            return
        
        position = self._search_matches[index]
        cursor = self.log_text.textCursor()
        cursor.setPosition(position)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, len(self._search_text))
        
        # Highlight current match with different color
        current_format = QTextCharFormat()
        current_format.setBackground(QColor(255, 165, 0))  # Orange
        current_format.setForeground(QColor(0, 0, 0))
        cursor.mergeCharFormat(current_format)
        
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
