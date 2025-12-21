"""
Settings dialog for application preferences.

This module provides a dialog for configuring application settings
and preferences.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QTabWidget,
    QWidget,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QGroupBox,
    QMessageBox,
)
from PyQt6.QtCore import QSettings


class SettingsDialog(QDialog):
    """Dialog for application settings and preferences."""

    def __init__(self, parent=None):
        """Initialize the settings dialog."""
        super().__init__(parent)

        self.settings = QSettings("PrismaAccess", "ConfigManager")

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>Application Settings</h2>")
        layout.addWidget(title)

        # Tabs
        tabs = QTabWidget()

        # General tab
        tabs.addTab(self._create_general_tab(), "General")

        # API tab
        tabs.addTab(self._create_api_tab(), "API")

        # Advanced tab
        tabs.addTab(self._create_advanced_tab(), "Advanced")

        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_and_close)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _create_general_tab(self) -> QWidget:
        """Create general settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # UI preferences
        ui_group = QGroupBox("User Interface")
        ui_layout = QFormLayout()

        self.remember_window_check = QCheckBox("Remember window size and position")
        self.remember_window_check.setChecked(True)
        ui_layout.addRow("Window:", self.remember_window_check)

        self.auto_expand_check = QCheckBox("Auto-expand configuration tree")
        self.auto_expand_check.setChecked(False)
        ui_layout.addRow("Tree View:", self.auto_expand_check)

        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)

        # File preferences
        file_group = QGroupBox("File Operations")
        file_layout = QFormLayout()

        self.auto_validate_check = QCheckBox("Auto-validate on load/save")
        self.auto_validate_check.setChecked(True)
        file_layout.addRow("Validation:", self.auto_validate_check)

        self.backup_check = QCheckBox("Create backup before overwriting")
        self.backup_check.setChecked(True)
        file_layout.addRow("Backup:", self.backup_check)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        layout.addStretch()
        return widget

    def _create_api_tab(self) -> QWidget:
        """Create API settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Connection settings
        conn_group = QGroupBox("Connection")
        conn_layout = QFormLayout()

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 300)
        self.timeout_spin.setValue(60)
        self.timeout_spin.setSuffix(" seconds")
        conn_layout.addRow("Request Timeout:", self.timeout_spin)

        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        # Rate limiting
        rate_group = QGroupBox("Rate Limiting")
        rate_layout = QFormLayout()

        self.rate_limit_spin = QSpinBox()
        self.rate_limit_spin.setRange(10, 1000)
        self.rate_limit_spin.setValue(100)
        self.rate_limit_spin.setSuffix(" requests/minute")
        rate_layout.addRow("Max Requests:", self.rate_limit_spin)

        rate_group.setLayout(rate_layout)
        layout.addWidget(rate_group)

        # Cache settings
        cache_group = QGroupBox("Caching")
        cache_layout = QFormLayout()

        self.cache_ttl_spin = QSpinBox()
        self.cache_ttl_spin.setRange(0, 3600)
        self.cache_ttl_spin.setValue(300)
        self.cache_ttl_spin.setSuffix(" seconds")
        cache_layout.addRow("Cache TTL:", self.cache_ttl_spin)

        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)

        layout.addStretch()
        return widget

    def _create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Logging
        log_group = QGroupBox("Logging")
        log_layout = QFormLayout()

        self.max_logs_spin = QSpinBox()
        self.max_logs_spin.setRange(100, 10000)
        self.max_logs_spin.setValue(1000)
        self.max_logs_spin.setSuffix(" entries")
        log_layout.addRow("Max Log Entries:", self.max_logs_spin)

        self.log_level_check = QCheckBox("Enable debug logging")
        self.log_level_check.setChecked(False)
        log_layout.addRow("Debug Mode:", self.log_level_check)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Performance
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout()

        self.max_tree_items_spin = QSpinBox()
        self.max_tree_items_spin.setRange(100, 10000)
        self.max_tree_items_spin.setValue(1000)
        self.max_tree_items_spin.setSuffix(" items")
        perf_layout.addRow("Max Tree Items:", self.max_tree_items_spin)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        layout.addStretch()

        # Reset button
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        reset_layout.addWidget(reset_btn)
        layout.addLayout(reset_layout)

        return widget

    def _load_settings(self):
        """Load current settings."""
        # General
        self.remember_window_check.setChecked(
            self.settings.value("general/remember_window", True, type=bool)
        )
        self.auto_expand_check.setChecked(
            self.settings.value("general/auto_expand", False, type=bool)
        )
        self.auto_validate_check.setChecked(
            self.settings.value("general/auto_validate", True, type=bool)
        )
        self.backup_check.setChecked(
            self.settings.value("general/backup", True, type=bool)
        )

        # API
        self.timeout_spin.setValue(self.settings.value("api/timeout", 60, type=int))
        self.rate_limit_spin.setValue(
            self.settings.value("api/rate_limit", 100, type=int)
        )
        self.cache_ttl_spin.setValue(
            self.settings.value("api/cache_ttl", 300, type=int)
        )

        # Advanced
        self.max_logs_spin.setValue(
            self.settings.value("advanced/max_logs", 1000, type=int)
        )
        self.log_level_check.setChecked(
            self.settings.value("advanced/debug", False, type=bool)
        )
        self.max_tree_items_spin.setValue(
            self.settings.value("advanced/max_tree_items", 1000, type=int)
        )

    def _save_settings(self):
        """Save settings."""
        # General
        self.settings.setValue(
            "general/remember_window", self.remember_window_check.isChecked()
        )
        self.settings.setValue(
            "general/auto_expand", self.auto_expand_check.isChecked()
        )
        self.settings.setValue(
            "general/auto_validate", self.auto_validate_check.isChecked()
        )
        self.settings.setValue("general/backup", self.backup_check.isChecked())

        # API
        self.settings.setValue("api/timeout", self.timeout_spin.value())
        self.settings.setValue("api/rate_limit", self.rate_limit_spin.value())
        self.settings.setValue("api/cache_ttl", self.cache_ttl_spin.value())

        # Advanced
        self.settings.setValue("advanced/max_logs", self.max_logs_spin.value())
        self.settings.setValue("advanced/debug", self.log_level_check.isChecked())
        self.settings.setValue(
            "advanced/max_tree_items", self.max_tree_items_spin.value()
        )

    def _save_and_close(self):
        """Save settings and close dialog."""
        self._save_settings()
        QMessageBox.information(
            self,
            "Settings Saved",
            "Settings saved successfully.\n\n"
            "Some changes may require restarting the application.",
        )
        self.accept()

    def _reset_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all settings to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Clear all settings
            self.settings.clear()

            # Reload defaults
            self._load_settings()

            QMessageBox.information(
                self, "Settings Reset", "All settings have been reset to defaults."
            )
