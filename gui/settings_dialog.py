"""
Settings dialog for application preferences.

This module provides a dialog for configuring application settings
and preferences.
"""

import logging
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
    QComboBox,
)
from PyQt6.QtCore import QSettings

from config.logging_config import NORMAL, DETAIL, set_log_level, enable_debug_mode, disable_debug_mode


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

        # Infrastructure tab
        tabs.addTab(self._create_infrastructure_tab(), "Infrastructure")

        # Encryption tab
        tabs.addTab(self._create_encryption_tab(), "Encryption")

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

    def _create_infrastructure_tab(self) -> QWidget:
        """Create infrastructure settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Device Management
        device_group = QGroupBox("Device Management")
        device_layout = QFormLayout()

        self.device_retries_spin = QSpinBox()
        self.device_retries_spin.setRange(1, 20)
        self.device_retries_spin.setValue(3)
        self.device_retries_spin.setSuffix(" retries")
        self.device_retries_spin.setToolTip(
            "Number of connection attempts before failing when connecting to firewalls/Panorama"
        )
        device_layout.addRow("Connection Retries:", self.device_retries_spin)

        self.device_retry_interval_spin = QSpinBox()
        self.device_retry_interval_spin.setRange(5, 120)
        self.device_retry_interval_spin.setValue(30)
        self.device_retry_interval_spin.setSuffix(" seconds")
        self.device_retry_interval_spin.setToolTip(
            "Time to wait between connection retry attempts"
        )
        device_layout.addRow("Retry Interval:", self.device_retry_interval_spin)

        self.device_timeout_spin = QSpinBox()
        self.device_timeout_spin.setRange(60, 1800)
        self.device_timeout_spin.setValue(600)
        self.device_timeout_spin.setSuffix(" seconds")
        self.device_timeout_spin.setToolTip(
            "Maximum total time to wait for device to become accessible"
        )
        device_layout.addRow("Total Timeout:", self.device_timeout_spin)

        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        # Terraform
        tf_group = QGroupBox("Terraform")
        tf_layout = QFormLayout()

        self.tf_auto_approve_check = QCheckBox("Auto-approve Terraform apply")
        self.tf_auto_approve_check.setChecked(True)
        self.tf_auto_approve_check.setToolTip(
            "Automatically approve Terraform changes without manual confirmation"
        )
        tf_layout.addRow("", self.tf_auto_approve_check)

        tf_group.setLayout(tf_layout)
        layout.addWidget(tf_group)

        # Info
        info_label = QLabel(
            "<i>Note: Device management settings apply to firewall and Panorama "
            "connections during POV deployment. Increase retries if devices take "
            "longer to boot in your cloud environment.</i>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-top: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()
        return widget

    def _create_encryption_tab(self) -> QWidget:
        """Create encryption settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Password Policy
        policy_group = QGroupBox("Password Policy")
        policy_layout = QFormLayout()

        self.min_length_spin = QSpinBox()
        self.min_length_spin.setRange(4, 32)
        self.min_length_spin.setValue(8)
        self.min_length_spin.setSuffix(" characters")
        policy_layout.addRow("Minimum Length:", self.min_length_spin)

        self.require_uppercase_check = QCheckBox("Require uppercase letter (A-Z)")
        self.require_uppercase_check.setChecked(True)
        policy_layout.addRow("", self.require_uppercase_check)

        self.require_lowercase_check = QCheckBox("Require lowercase letter (a-z)")
        self.require_lowercase_check.setChecked(True)
        policy_layout.addRow("", self.require_lowercase_check)

        self.require_digit_check = QCheckBox("Require digit (0-9)")
        self.require_digit_check.setChecked(True)
        policy_layout.addRow("", self.require_digit_check)

        self.require_special_check = QCheckBox("Require special character (!@#$%^&*...)")
        self.require_special_check.setChecked(True)
        policy_layout.addRow("", self.require_special_check)

        self.disallow_common_check = QCheckBox("Disallow common passwords")
        self.disallow_common_check.setChecked(True)
        policy_layout.addRow("", self.disallow_common_check)

        policy_group.setLayout(policy_layout)
        layout.addWidget(policy_group)

        # Encryption Options
        encrypt_group = QGroupBox("Encryption Options")
        encrypt_layout = QFormLayout()

        self.default_encrypt_check = QCheckBox("Encrypt saved configurations by default")
        self.default_encrypt_check.setChecked(True)
        encrypt_layout.addRow("", self.default_encrypt_check)

        self.show_strength_check = QCheckBox("Show password strength indicator")
        self.show_strength_check.setChecked(True)
        encrypt_layout.addRow("", self.show_strength_check)

        encrypt_group.setLayout(encrypt_layout)
        layout.addWidget(encrypt_group)

        # Info
        info_label = QLabel(
            "<i>Note: Configurations are encrypted using AES-256 with PBKDF2 key derivation. "
            "Lost passwords cannot be recovered.</i>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-top: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()
        return widget

    def _create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Logging
        log_group = QGroupBox("Logging")
        log_layout = QFormLayout()

        # Log level dropdown
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItem("Error - Failures only", logging.ERROR)
        self.log_level_combo.addItem("Warning - Issues that need attention", logging.WARNING)
        self.log_level_combo.addItem("Normal - High-level summaries", NORMAL)
        self.log_level_combo.addItem("Info - Per-item processing", logging.INFO)
        self.log_level_combo.addItem("Detail - API URLs, keys, values", DETAIL)
        self.log_level_combo.addItem("Debug - Everything (troubleshooting)", logging.DEBUG)
        self.log_level_combo.setCurrentIndex(2)  # Default to NORMAL
        log_layout.addRow("Log Level:", self.log_level_combo)

        # Note: Max log entries setting removed - logs are unlimited in memory
        # since they're already rotated per session and retained based on
        # rotation count and age settings below.

        # Log retention
        log_retention_label = QLabel("<b>Log Retention:</b>")
        log_layout.addRow(log_retention_label)

        self.log_rotation_spin = QSpinBox()
        self.log_rotation_spin.setRange(1, 30)
        self.log_rotation_spin.setValue(7)
        self.log_rotation_spin.setSuffix(" files")
        log_layout.addRow("  Keep Rotations:", self.log_rotation_spin)

        self.log_age_spin = QSpinBox()
        self.log_age_spin.setRange(1, 90)
        self.log_age_spin.setValue(30)
        self.log_age_spin.setSuffix(" days")
        log_layout.addRow("  Keep Age:", self.log_age_spin)

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

        # Infrastructure
        self.device_retries_spin.setValue(
            self.settings.value("infrastructure/device_retries", 3, type=int)
        )
        self.device_retry_interval_spin.setValue(
            self.settings.value("infrastructure/device_retry_interval", 30, type=int)
        )
        self.device_timeout_spin.setValue(
            self.settings.value("infrastructure/device_timeout", 600, type=int)
        )
        self.tf_auto_approve_check.setChecked(
            self.settings.value("infrastructure/tf_auto_approve", True, type=bool)
        )

        # Encryption
        self.min_length_spin.setValue(
            self.settings.value("encryption/min_length", 8, type=int)
        )
        self.require_uppercase_check.setChecked(
            self.settings.value("encryption/require_uppercase", True, type=bool)
        )
        self.require_lowercase_check.setChecked(
            self.settings.value("encryption/require_lowercase", True, type=bool)
        )
        self.require_digit_check.setChecked(
            self.settings.value("encryption/require_digit", True, type=bool)
        )
        self.require_special_check.setChecked(
            self.settings.value("encryption/require_special", True, type=bool)
        )
        self.disallow_common_check.setChecked(
            self.settings.value("encryption/disallow_common", True, type=bool)
        )
        self.default_encrypt_check.setChecked(
            self.settings.value("encryption/default_encrypt", True, type=bool)
        )
        self.show_strength_check.setChecked(
            self.settings.value("encryption/show_strength", True, type=bool)
        )

        # Advanced - Logging
        log_level = self.settings.value("advanced/log_level", NORMAL, type=int)
        # Find index of matching log level
        for i in range(self.log_level_combo.count()):
            if self.log_level_combo.itemData(i) == log_level:
                self.log_level_combo.setCurrentIndex(i)
                break
        
        self.log_rotation_spin.setValue(
            self.settings.value("advanced/log_rotation", 7, type=int)
        )
        self.log_age_spin.setValue(
            self.settings.value("advanced/log_age", 30, type=int)
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

        # Infrastructure
        self.settings.setValue("infrastructure/device_retries", self.device_retries_spin.value())
        self.settings.setValue("infrastructure/device_retry_interval", self.device_retry_interval_spin.value())
        self.settings.setValue("infrastructure/device_timeout", self.device_timeout_spin.value())
        self.settings.setValue("infrastructure/tf_auto_approve", self.tf_auto_approve_check.isChecked())

        # Encryption
        self.settings.setValue("encryption/min_length", self.min_length_spin.value())
        self.settings.setValue(
            "encryption/require_uppercase", self.require_uppercase_check.isChecked()
        )
        self.settings.setValue(
            "encryption/require_lowercase", self.require_lowercase_check.isChecked()
        )
        self.settings.setValue(
            "encryption/require_digit", self.require_digit_check.isChecked()
        )
        self.settings.setValue(
            "encryption/require_special", self.require_special_check.isChecked()
        )
        self.settings.setValue(
            "encryption/disallow_common", self.disallow_common_check.isChecked()
        )
        self.settings.setValue(
            "encryption/default_encrypt", self.default_encrypt_check.isChecked()
        )
        self.settings.setValue(
            "encryption/show_strength", self.show_strength_check.isChecked()
        )

        # Advanced - Logging
        log_level = self.log_level_combo.currentData()
        self.settings.setValue("advanced/log_level", log_level)
        self.settings.setValue("advanced/log_rotation", self.log_rotation_spin.value())
        self.settings.setValue("advanced/log_age", self.log_age_spin.value())
        self.settings.setValue(
            "advanced/max_tree_items", self.max_tree_items_spin.value()
        )
        
        # Apply log level immediately
        set_log_level(log_level)
        if log_level == logging.DEBUG:
            enable_debug_mode()
        else:
            disable_debug_mode()

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
