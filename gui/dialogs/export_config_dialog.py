"""
Export Configuration Dialog.

Provides a dialog for exporting configurations to custom locations
with optional encryption.
"""

import os
import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QGroupBox,
    QMessageBox,
    QFileDialog,
    QRadioButton,
    QButtonGroup,
    QProgressBar,
)
from PyQt6.QtCore import QSettings, Qt

from config.utils.encryption import (
    PasswordValidator,
    PasswordPolicy,
    FILE_EXTENSION_ENCRYPTED,
    FILE_EXTENSION_PLAIN,
)

if TYPE_CHECKING:
    from config.models.containers import Configuration

logger = logging.getLogger(__name__)


class ExportConfigDialog(QDialog):
    """Dialog for exporting configuration to custom location."""
    
    def __init__(
        self,
        config: 'Configuration',
        parent=None,
        config_name: str = "Configuration",
    ):
        """
        Initialize export configuration dialog.
        
        Args:
            config: Configuration object to export
            parent: Parent widget
            config_name: Name of the configuration
        """
        super().__init__(parent)
        
        self.config = config
        self.config_name = config_name
        self.settings = QSettings("PrismaAccess", "ConfigManager")
        self.exported_file_path = None
        
        # Load password policy from settings
        self.password_policy = self._load_password_policy()
        self.password_validator = PasswordValidator(self.password_policy)
        
        self._init_ui()
        self._connect_signals()
    
    def _load_password_policy(self) -> PasswordPolicy:
        """Load password policy from settings."""
        return PasswordPolicy(
            min_length=self.settings.value("encryption/min_length", 8, type=int),
            require_uppercase=self.settings.value("encryption/require_uppercase", True, type=bool),
            require_lowercase=self.settings.value("encryption/require_lowercase", True, type=bool),
            require_digit=self.settings.value("encryption/require_digit", True, type=bool),
            require_special=self.settings.value("encryption/require_special", True, type=bool),
            disallow_common_passwords=self.settings.value("encryption/disallow_common", True, type=bool),
        )
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Export Configuration")
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Export Configuration</h2>")
        layout.addWidget(title)
        
        # Info
        info_label = QLabel(f"<b>Configuration:</b> {self.config_name}")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # Export location
        location_group = QGroupBox("Export Location")
        location_layout = QHBoxLayout()
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select export location...")
        self.path_edit.setReadOnly(True)
        location_layout.addWidget(self.path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_location)
        location_layout.addWidget(browse_btn)
        
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)
        
        # Options
        options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout()
        
        # Format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Format:")
        format_layout.addWidget(format_label)
        
        self.format_group = QButtonGroup()
        
        self.encrypted_radio = QRadioButton("Encrypted (.pac)")
        self.encrypted_radio.setChecked(True)
        self.format_group.addButton(self.encrypted_radio)
        format_layout.addWidget(self.encrypted_radio)
        
        self.plain_radio = QRadioButton("Plain JSON (.json)")
        self.format_group.addButton(self.plain_radio)
        format_layout.addWidget(self.plain_radio)
        
        format_layout.addStretch()
        options_layout.addLayout(format_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Encryption (shown when encrypted format selected)
        self.encrypt_group = QGroupBox("Encryption")
        encrypt_layout = QFormLayout()
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Enter encryption password")
        encrypt_layout.addRow("Password:", self.password_edit)
        
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit.setPlaceholderText("Confirm encryption password")
        encrypt_layout.addRow("Confirm:", self.confirm_edit)
        
        # Password strength indicator
        if self.settings.value("encryption/show_strength", True, type=bool):
            strength_layout = QHBoxLayout()
            self.strength_bar = QProgressBar()
            self.strength_bar.setMaximum(100)
            self.strength_bar.setTextVisible(False)
            self.strength_bar.setMaximumHeight(8)
            strength_layout.addWidget(self.strength_bar)
            
            self.strength_label = QLabel("Enter password")
            self.strength_label.setStyleSheet("color: #666; font-size: 11px;")
            strength_layout.addWidget(self.strength_label)
            
            encrypt_layout.addRow("Strength:", strength_layout)
        
        self.encrypt_group.setLayout(encrypt_layout)
        layout.addWidget(self.encrypt_group)
        
        # Warning for plain export
        self.plain_warning = QLabel(
            "<span style='color: #c00;'>"
            "⚠ Warning: Plain JSON files are not encrypted and can be read by anyone. "
            "Do not use for sensitive configurations."
            "</span>"
        )
        self.plain_warning.setWordWrap(True)
        self.plain_warning.hide()
        layout.addWidget(self.plain_warning)
        
        # Validation message
        self.validation_label = QLabel()
        self.validation_label.setStyleSheet("color: #c00;")
        self.validation_label.setWordWrap(True)
        self.validation_label.hide()
        layout.addWidget(self.validation_label)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.setDefault(True)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_config)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.path_edit.textChanged.connect(self._validate_form)
        self.password_edit.textChanged.connect(self._update_password_strength)
        self.confirm_edit.textChanged.connect(self._validate_form)
        self.encrypted_radio.toggled.connect(self._on_format_changed)
        self.plain_radio.toggled.connect(self._on_format_changed)
    
    def _on_format_changed(self):
        """Handle format selection change."""
        encrypted = self.encrypted_radio.isChecked()
        self.encrypt_group.setVisible(encrypted)
        self.plain_warning.setVisible(not encrypted)
        self._validate_form()
    
    def _browse_location(self):
        """Browse for export location."""
        # Determine default extension
        if self.encrypted_radio.isChecked():
            default_ext = FILE_EXTENSION_ENCRYPTED
            filter_str = f"Encrypted Configuration (*{FILE_EXTENSION_ENCRYPTED})"
        else:
            default_ext = FILE_EXTENSION_PLAIN
            filter_str = f"JSON Configuration (*{FILE_EXTENSION_PLAIN})"
        
        # Suggest filename
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in self.config_name)
        safe_name = safe_name.strip()[:50] or "config"
        default_name = f"{safe_name}{default_ext}"
        
        # Get last export directory
        last_dir = self.settings.value("export/last_directory", "")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Configuration",
            os.path.join(last_dir, default_name) if last_dir else default_name,
            f"{filter_str};;All Files (*)"
        )
        
        if file_path:
            # Ensure correct extension
            if self.encrypted_radio.isChecked() and not file_path.endswith(FILE_EXTENSION_ENCRYPTED):
                file_path += FILE_EXTENSION_ENCRYPTED
            elif self.plain_radio.isChecked() and not file_path.endswith(FILE_EXTENSION_PLAIN):
                file_path += FILE_EXTENSION_PLAIN
            
            self.path_edit.setText(file_path)
            
            # Save directory for next time
            self.settings.setValue("export/last_directory", os.path.dirname(file_path))
    
    def _update_password_strength(self):
        """Update password strength indicator."""
        if not hasattr(self, 'strength_bar'):
            return
        
        password = self.password_edit.text()
        
        if not password:
            self.strength_bar.setValue(0)
            self.strength_label.setText("Enter password")
            self.strength_bar.setStyleSheet("")
            self._validate_form()
            return
        
        label, score = self.password_validator.get_strength(password)
        self.strength_bar.setValue(score)
        self.strength_label.setText(label)
        
        # Color based on strength
        if score < 30:
            color = "#dc3545"  # Red
        elif score < 50:
            color = "#ffc107"  # Yellow
        elif score < 70:
            color = "#17a2b8"  # Blue
        else:
            color = "#28a745"  # Green
        
        self.strength_bar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        
        self._validate_form()
    
    def _validate_form(self):
        """Validate form and update export button state."""
        errors = []
        
        # Path required
        if not self.path_edit.text().strip():
            errors.append("Export location is required")
        
        # Password validation for encrypted format
        if self.encrypted_radio.isChecked():
            password = self.password_edit.text()
            confirm = self.confirm_edit.text()
            
            if not password:
                errors.append("Password is required for encrypted export")
            else:
                is_valid, pwd_errors = self.password_validator.validate(password)
                if not is_valid:
                    errors.extend(pwd_errors)
            
            if password and confirm and password != confirm:
                errors.append("Passwords do not match")
        
        if errors:
            self.validation_label.setText(errors[0])
            self.validation_label.show()
            self.export_btn.setEnabled(False)
        else:
            self.validation_label.hide()
            self.export_btn.setEnabled(bool(self.path_edit.text().strip()))
    
    def _export_config(self):
        """Export the configuration."""
        file_path = self.path_edit.text().strip()
        encrypted = self.encrypted_radio.isChecked()
        password = self.password_edit.text() if encrypted else None
        
        try:
            # Check if file exists
            if os.path.exists(file_path):
                reply = QMessageBox.question(
                    self,
                    "File Exists",
                    f"The file already exists:\n\n{file_path}\n\nOverwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Use Configuration.save_to_file() with optional encryption
            self.config.save_to_file(
                file_path,
                compress=False,
                description=f"Exported from {self.config_name}",
                password=password,
                friendly_name=self.config_name
            )
            
            self.exported_file_path = file_path
            
            logger.info(f"Configuration exported: {file_path}")
            
            QMessageBox.information(
                self,
                "Export Complete",
                f"Configuration exported successfully!\n\n"
                f"File: {os.path.basename(file_path)}\n"
                f"Format: {'Encrypted' if encrypted else 'Plain JSON'}"
            )
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export configuration:\n\n{str(e)}"
            )
    
    def get_exported_path(self) -> Optional[str]:
        """Get the path where configuration was exported."""
        return self.exported_file_path
