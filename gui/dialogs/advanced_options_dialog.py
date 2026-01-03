"""
Advanced Options Dialog for Pull Configuration.

Simple popup dialog for advanced pull settings like filtering defaults.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
)
from PyQt6.QtCore import QSettings


class AdvancedOptionsDialog(QDialog):
    """Dialog for advanced pull configuration options."""
    
    def __init__(self, parent=None):
        """Initialize the advanced options dialog."""
        super().__init__(parent)
        
        self.settings = QSettings("PrismaAccess", "ConfigManager")
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Advanced Options")
        self.setMinimumWidth(350)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<b>Advanced Pull Options</b>")
        layout.addWidget(title)
        
        # Filter defaults option
        self.filter_defaults_check = QCheckBox("Filter default configurations")
        self.filter_defaults_check.setToolTip(
            "When enabled, system default configurations (predefined snippets, "
            "default profiles, etc.) will be excluded from the pull.\n\n"
            "This is recommended to capture only your custom configurations."
        )
        layout.addWidget(self.filter_defaults_check)
        
        # Info label
        info = QLabel(
            "<i>Filtering defaults is recommended to avoid pulling "
            "thousands of built-in system configurations.</i>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-size: 11px; margin-top: 10px;")
        layout.addWidget(info)
        
        # Spacer
        layout.addSpacing(20)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_settings(self):
        """Load settings from QSettings."""
        filter_defaults = self.settings.value("pull/filter_defaults", True, type=bool)
        self.filter_defaults_check.setChecked(filter_defaults)
    
    def _save_and_accept(self):
        """Save settings and close dialog."""
        self.settings.setValue("pull/filter_defaults", self.filter_defaults_check.isChecked())
        self.accept()
    
    def get_filter_defaults(self) -> bool:
        """Get the filter defaults setting."""
        return self.filter_defaults_check.isChecked()
