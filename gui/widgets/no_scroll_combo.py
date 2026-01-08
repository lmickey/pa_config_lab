"""
No-Scroll ComboBox Widget.

A QComboBox that ignores mouse wheel events to prevent accidental
selection changes when scrolling through a window.
"""

from PyQt6.QtWidgets import QComboBox
from PyQt6.QtCore import Qt


class NoScrollComboBox(QComboBox):
    """
    A QComboBox that ignores mouse wheel scroll events.
    
    This prevents users from accidentally changing dropdown selections
    when scrolling through a window with the mouse wheel.
    
    Selection changes require:
    - Clicking on the dropdown
    - Using keyboard navigation (Tab, arrow keys, Enter)
    """
    
    def wheelEvent(self, event):
        """Ignore wheel events to prevent accidental selection changes."""
        # Don't process the wheel event - let it propagate to parent
        event.ignore()
