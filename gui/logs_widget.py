"""
Logs widget for displaying activity and operations.

This module provides a log viewer with filtering, search, and export capabilities.
"""

from typing import Optional, List
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
    QLineEdit,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QTextDocument


class LogsWidget(QWidget):
    """Widget for viewing application logs and activity."""

    def __init__(self, parent=None):
        """Initialize the logs widget."""
        super().__init__(parent)

        self.max_log_entries = 1000
        self.log_entries = []
        
        # Search state
        self._search_matches: List[int] = []  # List of cursor positions for matches
        self._current_match_index: int = -1
        self._search_text: str = ""
        
        # Search debounce timer (waits for user to stop typing)
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._execute_search)
        self._pending_search_text: str = ""
        self._min_search_chars: int = 3
        self._search_debounce_ms: int = 250

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title and controls row
        header_layout = QHBoxLayout()

        title = QLabel("<h2>Activity Logs</h2>")
        header_layout.addWidget(title)

        header_layout.addStretch()
        
        # Search input
        header_layout.addWidget(QLabel("Search:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search...")
        self.search_input.setFixedWidth(180)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._search_next)
        header_layout.addWidget(self.search_input)
        
        # Previous match button
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedWidth(30)
        self.prev_btn.setToolTip("Previous match")
        self.prev_btn.clicked.connect(self._search_prev)
        self.prev_btn.setEnabled(False)
        header_layout.addWidget(self.prev_btn)
        
        # Next match button
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedWidth(30)
        self.next_btn.setToolTip("Next match")
        self.next_btn.clicked.connect(self._search_next)
        self.next_btn.setEnabled(False)
        header_layout.addWidget(self.next_btn)
        
        # Match counter label
        self.match_label = QLabel("")
        self.match_label.setFixedWidth(70)
        self.match_label.setStyleSheet("color: #666; font-weight: bold;")
        header_layout.addWidget(self.match_label)
        
        # Separator
        separator = QLabel("|")
        separator.setStyleSheet("color: #ccc; margin: 0 5px;")
        header_layout.addWidget(separator)

        # Filter combo - ordered from most verbose to least, each level includes levels above
        header_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        # Order: most restrictive (Error) to most verbose (Debug)
        # Each selection shows that level AND all more severe levels above it
        self.filter_combo.addItems([
            "Error",      # Only errors
            "Warning",    # Warning + Error
            "Normal",     # Normal + Warning + Error
            "Info",       # Info + Normal + Warning + Error
            "Detail",     # Detail + Info + Normal + Warning + Error
            "Debug",      # Everything
        ])
        self.filter_combo.setCurrentText("Debug")  # Default to show all
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
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
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # Word wrap at widget edge

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

        # Color coding - includes custom log levels
        color_map = {
            "debug": "#999999",    # Light gray - verbose debugging
            "detail": "#888888",   # Gray - API URLs, keys, values
            "info": "#666666",     # Dark gray - per-item processing
            "normal": "#333333",   # Near black - high-level summaries
            "success": "#008800",  # Green - success messages
            "warning": "#ff8800",  # Orange - warnings
            "error": "#cc0000",    # Red - errors
        }
        color = color_map.get(level, "#000000")

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
            counts = {"debug": 0, "detail": 0, "info": 0, "normal": 0, "success": 0, "warning": 0, "error": 0}
            for entry in self.log_entries:
                level = entry["level"]
                if level in counts:
                    counts[level] += 1

            # Combine success with normal for display (they're the same priority)
            normal_total = counts['normal'] + counts['success']
            
            self.stats_label.setText(
                f"Total: {total} | "
                f"Error: {counts['error']} | "
                f"Warn: {counts['warning']} | "
                f"Normal: {normal_total} | "
                f"Info: {counts['info']} | "
                f"Detail: {counts['detail']} | "
                f"Debug: {counts['debug']}"
            )
        except RuntimeError:
            # Widget was deleted or not accessible - silently ignore
            pass

    def _on_filter_changed(self, filter_type: str):
        """Handle filter combo change - apply filter and re-search."""
        self._apply_filter(filter_type, preserve_search=True)
    
    def _apply_filter(self, filter_type: str, preserve_search: bool = True):
        """
        Apply log filter.
        
        Filtering is cumulative - selecting a level shows that level
        and all more severe levels above it:
        - Error: only errors
        - Warning: warning + error
        - Normal: normal + warning + error (includes success)
        - Info: info + normal + warning + error
        - Detail: detail + info + normal + warning + error
        - Debug: everything
        
        Args:
            filter_type: The filter level to apply
            preserve_search: If True, re-apply search highlights after filtering
        """
        filter_lower = filter_type.lower()
        
        # Define log level hierarchy (lower value = more severe)
        level_hierarchy = {
            'error': 1,
            'warning': 2,
            'normal': 3,
            'success': 3,  # Success is same priority as Normal
            'info': 4,
            'detail': 5,
            'debug': 6,
        }
        
        # Get the threshold for the selected filter
        filter_threshold = level_hierarchy.get(filter_lower, 6)  # Default to show all

        # Clear display
        self.log_text.clear()

        # Re-display filtered entries (show entries at or above threshold severity)
        for entry in self.log_entries:
            entry_level = level_hierarchy.get(entry["level"], 6)
            if entry_level <= filter_threshold:
                self._display_entry(entry)
        
        # Re-apply search if there was an active search
        if preserve_search and self._search_text:
            # Re-run search on new content (bypass debounce since we already have valid search)
            saved_search = self._search_text
            self._pending_search_text = saved_search
            self._search_text = ""  # Clear to avoid recursion
            self._execute_search()

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
    
    def _on_search_text_changed(self, text: str):
        """
        Handle search text changes with debouncing.
        
        Waits for user to stop typing (250ms pause) before searching,
        and requires minimum 3 characters to initiate search.
        """
        self._pending_search_text = text
        
        # Stop any pending search timer
        self._search_timer.stop()
        
        # If text is empty, clear immediately (no debounce needed)
        if not text:
            self._search_text = ""
            self._search_matches.clear()
            self._current_match_index = -1
            self._clear_highlights()
            self.match_label.setText("")
            self.match_label.setToolTip("")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return
        
        # If text is below minimum length, show hint but don't search
        if len(text) < self._min_search_chars:
            self.match_label.setText(f"{self._min_search_chars - len(text)} more...")
            self.match_label.setToolTip(f"Type at least {self._min_search_chars} characters to search")
            self.match_label.setStyleSheet("color: #999; font-weight: bold;")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return
        
        # Show "searching..." indicator and start debounce timer
        self.match_label.setText("...")
        self.match_label.setToolTip("Searching...")
        self.match_label.setStyleSheet("color: #999; font-weight: bold;")
        self._search_timer.start(self._search_debounce_ms)
    
    def _execute_search(self):
        """Execute the actual search after debounce delay."""
        text = self._pending_search_text
        
        # Double-check minimum length (in case timer fired after text changed)
        if len(text) < self._min_search_chars:
            return
        
        self._search_text = text
        self._search_matches.clear()
        self._current_match_index = -1
        
        # Clear existing highlights
        self._clear_highlights()
        
        # Find all matches in current view
        document = self.log_text.document()
        cursor = QTextCursor(document)
        
        # Highlight format for matches
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor(255, 255, 0))  # Yellow highlight
        
        # Find all occurrences
        while True:
            cursor = document.find(text, cursor, QTextDocument.FindFlag(0))
            if cursor.isNull():
                break
            
            # Store the position
            self._search_matches.append(cursor.selectionStart())
            
            # Apply highlight
            cursor.mergeCharFormat(highlight_format)
        
        # Update UI
        match_count = len(self._search_matches)
        if match_count > 0:
            self._current_match_index = 0
            self._go_to_match(0)
            self.match_label.setText(f"1 / {match_count}")
            self.match_label.setToolTip("")
            self.match_label.setStyleSheet("color: #666; font-weight: bold;")  # Reset to normal style
            self.prev_btn.setEnabled(match_count > 1)
            self.next_btn.setEnabled(match_count > 1)
        else:
            # No matches in current filter - check if matches exist in other levels
            suggestion = self._check_matches_in_other_levels(text)
            self.match_label.setText("0 found")
            if suggestion:
                self.match_label.setToolTip(suggestion)
                self.match_label.setStyleSheet("color: #cc6600; font-weight: bold;")  # Orange to indicate suggestion
            else:
                self.match_label.setToolTip("No matches found in any log level")
                self.match_label.setStyleSheet("color: #666; font-weight: bold;")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
    
    def _check_matches_in_other_levels(self, search_text: str) -> str:
        """
        Check if search text exists in log entries at other filter levels.
        
        Args:
            search_text: The text to search for
            
        Returns:
            Suggestion string if matches found in other levels, empty string otherwise
        """
        if not search_text:
            return ""
        
        search_lower = search_text.lower()
        current_filter = self.filter_combo.currentText().lower()
        
        # Level hierarchy for comparison
        level_hierarchy = {
            'error': 1,
            'warning': 2,
            'normal': 3,
            'success': 3,
            'info': 4,
            'detail': 5,
            'debug': 6,
        }
        
        current_threshold = level_hierarchy.get(current_filter, 6)
        
        # Count matches at each level that's currently filtered out
        matches_by_level = {}
        
        for entry in self.log_entries:
            entry_level = entry["level"]
            entry_threshold = level_hierarchy.get(entry_level, 6)
            
            # Only check entries that are filtered out
            if entry_threshold > current_threshold:
                # Check if search text is in the message
                if search_lower in entry["message"].lower():
                    level_name = entry_level.capitalize()
                    if level_name not in matches_by_level:
                        matches_by_level[level_name] = 0
                    matches_by_level[level_name] += 1
        
        if not matches_by_level:
            return ""
        
        # Build suggestion message
        total_hidden = sum(matches_by_level.values())
        level_details = ", ".join(f"{count} in {level}" for level, count in sorted(matches_by_level.items(), key=lambda x: level_hierarchy.get(x[0].lower(), 6)))
        
        # Find the minimum filter level needed to see all matches
        min_level_needed = current_filter
        for level_name in matches_by_level.keys():
            level_threshold = level_hierarchy.get(level_name.lower(), 6)
            if level_threshold > level_hierarchy.get(min_level_needed.lower(), 6):
                min_level_needed = level_name
        
        return f"{total_hidden} match(es) hidden by filter ({level_details}). Try changing filter to '{min_level_needed}' or lower."
    
    def _clear_highlights(self):
        """Clear all search highlights from the text by re-rendering."""
        # Re-apply the filter which rebuilds the display without highlights
        # Use preserve_search=False to avoid recursion
        current_filter = self.filter_combo.currentText()
        self._apply_filter(current_filter, preserve_search=False)
    
    def _search_next(self):
        """Go to next search match."""
        if not self._search_matches:
            return
        
        self._current_match_index = (self._current_match_index + 1) % len(self._search_matches)
        self._go_to_match(self._current_match_index)
        self._update_match_label()
    
    def _search_prev(self):
        """Go to previous search match."""
        if not self._search_matches:
            return
        
        self._current_match_index = (self._current_match_index - 1) % len(self._search_matches)
        self._go_to_match(self._current_match_index)
        self._update_match_label()
    
    def _go_to_match(self, index: int):
        """Navigate to a specific match and highlight it distinctly, centering in view."""
        if index < 0 or index >= len(self._search_matches):
            return
        
        position = self._search_matches[index]
        
        # Move cursor to match position
        cursor = self.log_text.textCursor()
        cursor.setPosition(position)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, len(self._search_text))
        
        # Highlight current match with orange (distinct from yellow for other matches)
        current_format = QTextCharFormat()
        current_format.setBackground(QColor(255, 165, 0))  # Orange for current match
        cursor.mergeCharFormat(current_format)
        
        # Set cursor
        self.log_text.setTextCursor(cursor)
        
        # Center the match in the viewport (scroll so match is in middle)
        # Get the cursor's block (line) number
        block = cursor.block()
        block_number = block.blockNumber()
        
        # Get the scrollbar and viewport info
        scrollbar = self.log_text.verticalScrollBar()
        
        # Calculate target scroll position to center the line
        # Get approximate line height from font metrics
        font_metrics = self.log_text.fontMetrics()
        line_height = font_metrics.lineSpacing()
        viewport_height = self.log_text.viewport().height()
        visible_lines = viewport_height // line_height if line_height > 0 else 20
        
        # Calculate scroll position to put match in center
        target_line = max(0, block_number - (visible_lines // 2))
        scrollbar.setValue(target_line * line_height)
        
        # Re-highlight all matches but make current one orange
        self._rehighlight_matches()
    
    def _rehighlight_matches(self):
        """Re-highlight all matches, with current match in orange."""
        if not self._search_text:
            return
        
        document = self.log_text.document()
        
        # Yellow for non-current matches
        yellow_format = QTextCharFormat()
        yellow_format.setBackground(QColor(255, 255, 0))
        
        # Orange for current match
        orange_format = QTextCharFormat()
        orange_format.setBackground(QColor(255, 165, 0))
        
        for i, position in enumerate(self._search_matches):
            cursor = QTextCursor(document)
            cursor.setPosition(position)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, len(self._search_text))
            
            if i == self._current_match_index:
                cursor.mergeCharFormat(orange_format)
            else:
                cursor.mergeCharFormat(yellow_format)
    
    def _update_match_label(self):
        """Update the match counter label."""
        if self._search_matches:
            self.match_label.setText(f"{self._current_match_index + 1} / {len(self._search_matches)}")
        else:
            self.match_label.setText("0 matches")
