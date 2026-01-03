"""
Save Configuration Dialog.

Provides a dialog for saving configurations with friendly names,
descriptions, and password-based encryption.
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
    QTextEdit,
    QPushButton,
    QLabel,
    QGroupBox,
    QMessageBox,
    QProgressBar,
)
from PyQt6.QtCore import QSettings, Qt

from config.utils.encryption import (
    PasswordValidator,
    PasswordPolicy,
    generate_filename,
)

if TYPE_CHECKING:
    from config.models.containers import Configuration

logger = logging.getLogger(__name__)


class SaveConfigDialog(QDialog):
    """Dialog for saving configuration with encryption."""
    
    SAVED_FOLDER = "saved"
    
    def __init__(
        self,
        config: 'Configuration',
        parent=None,
        default_name: str = "",
    ):
        """
        Initialize save configuration dialog.
        
        Args:
            config: Configuration object to save
            parent: Parent widget
            default_name: Default configuration name
        """
        super().__init__(parent)
        
        self.config = config
        self.settings = QSettings("PrismaAccess", "ConfigManager")
        self.saved_file_path = None
        
        # Load password policy from settings
        self.password_policy = self._load_password_policy()
        self.password_validator = PasswordValidator(self.password_policy)
        
        self._init_ui(default_name)
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
    
    def _init_ui(self, default_name: str):
        """Initialize the user interface."""
        self.setWindowTitle("Save Configuration")
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Save Configuration</h2>")
        layout.addWidget(title)
        
        # Configuration Info
        info_group = QGroupBox("Configuration Details")
        info_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter a friendly name for this configuration")
        if default_name:
            self.name_edit.setText(default_name)
        info_layout.addRow("Name:", self.name_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Optional description...")
        self.description_edit.setMaximumHeight(80)
        info_layout.addRow("Description:", self.description_edit)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Encryption
        encrypt_group = QGroupBox("Encryption")
        encrypt_layout = QFormLayout()
        
        # Enable encryption checkbox
        self.enable_encrypt_check = QCheckBox("Enable Encryption")
        self.enable_encrypt_check.setChecked(
            self.settings.value("encryption/default_encrypt", True, type=bool)
        )
        self.enable_encrypt_check.setToolTip("Encrypt the configuration file with a password")
        self.enable_encrypt_check.stateChanged.connect(self._on_encryption_toggled)
        encrypt_layout.addRow("", self.enable_encrypt_check)
        
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
        
        # Password requirements
        requirements_label = QLabel(self.password_validator.get_requirements_text())
        requirements_label.setStyleSheet("color: #666; font-size: 11px;")
        requirements_label.setWordWrap(True)
        encrypt_layout.addRow("", requirements_label)
        
        encrypt_group.setLayout(encrypt_layout)
        layout.addWidget(encrypt_group)
        
        # File Info
        file_group = QGroupBox("Save Location")
        file_layout = QVBoxLayout()
        
        self.file_preview_label = QLabel()
        self.file_preview_label.setStyleSheet("color: #666; font-size: 11px;")
        self.file_preview_label.setWordWrap(True)
        file_layout.addWidget(self.file_preview_label)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Update file preview
        self._update_file_preview()
        
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
        
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.name_edit.textChanged.connect(self._update_file_preview)
        self.password_edit.textChanged.connect(self._update_password_strength)
        self.confirm_edit.textChanged.connect(self._validate_passwords)
        
        # Initialize encryption fields state
        self._on_encryption_toggled()
    
    def _on_encryption_toggled(self):
        """Handle encryption checkbox state change."""
        enabled = self.enable_encrypt_check.isChecked()
        self.password_edit.setEnabled(enabled)
        self.confirm_edit.setEnabled(enabled)
        if hasattr(self, 'strength_bar'):
            self.strength_bar.setEnabled(enabled)
            self.strength_label.setEnabled(enabled)
        
        if not enabled:
            self.password_edit.clear()
            self.confirm_edit.clear()
            if hasattr(self, 'strength_bar'):
                self.strength_bar.setValue(0)
                self.strength_label.setText("Encryption disabled")
        
        self._update_file_preview()
    
    def _update_file_preview(self):
        """Update the filename preview."""
        name = self.name_edit.text().strip() or "config"
        encrypted = self.enable_encrypt_check.isChecked()
        filename = generate_filename(name, encrypted=encrypted)
        
        # Get absolute path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        saved_path = os.path.join(base_path, self.SAVED_FOLDER, filename)
        
        self.file_preview_label.setText(
            f"<b>File:</b> {filename}<br>"
            f"<b>Location:</b> {saved_path}"
        )
    
    def _update_password_strength(self):
        """Update password strength indicator."""
        if not hasattr(self, 'strength_bar'):
            return
        
        password = self.password_edit.text()
        
        if not password:
            self.strength_bar.setValue(0)
            self.strength_label.setText("Enter password")
            self.strength_bar.setStyleSheet("")
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
        
        self._validate_passwords()
    
    def _validate_passwords(self):
        """Validate password fields."""
        password = self.password_edit.text()
        confirm = self.confirm_edit.text()
        
        # Clear validation message if empty
        if not password and not confirm:
            self.validation_label.hide()
            return
        
        # Check if passwords match
        if confirm and password != confirm:
            self.validation_label.setText("Passwords do not match")
            self.validation_label.show()
            return
        
        # Validate password policy
        is_valid, errors = self.password_validator.validate(password)
        if not is_valid:
            self.validation_label.setText(errors[0])  # Show first error
            self.validation_label.show()
            return
        
        self.validation_label.hide()
    
    def _validate_all(self) -> bool:
        """Validate all fields before saving."""
        errors = []
        
        # Name required
        name = self.name_edit.text().strip()
        if not name:
            errors.append("Configuration name is required")
        
        # Password validation only if encryption is enabled
        if self.enable_encrypt_check.isChecked():
            password = self.password_edit.text()
            if not password:
                errors.append("Password is required when encryption is enabled")
            else:
                # Validate password policy
                is_valid, pwd_errors = self.password_validator.validate(password)
                if not is_valid:
                    errors.extend(pwd_errors)
            
            # Passwords must match
            confirm = self.confirm_edit.text()
            if password != confirm:
                errors.append("Passwords do not match")
        
        if errors:
            self.validation_label.setText("\n".join(errors))
            self.validation_label.show()
            return False
        
        return True
    
    def _save_config(self):
        """Save the configuration."""
        if not self._validate_all():
            return
        
        name = self.name_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        encrypted = self.enable_encrypt_check.isChecked()
        password = self.password_edit.text() if encrypted else None
        
        try:
            # Ensure saved folder exists
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            saved_path = os.path.join(base_path, self.SAVED_FOLDER)
            os.makedirs(saved_path, exist_ok=True)
            
            # Generate filename
            filename = generate_filename(name, encrypted=encrypted)
            file_path = os.path.join(saved_path, filename)
            
            # Save using Configuration.save_to_file() with optional encryption
            self.config.save_to_file(
                file_path,
                compress=False,
                description=description,
                password=password,
                friendly_name=name
            )
            
            self.saved_file_path = file_path
            
            logger.info(f"Configuration saved: {file_path}")
            
            # Add to recent configurations
            self._add_to_recent(file_path, name)
            
            QMessageBox.information(
                self,
                "Configuration Saved",
                f"Configuration saved successfully!\n\n"
                f"Name: {name}\n"
                f"File: {filename}"
            )
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save configuration:\n\n{str(e)}"
            )
    
    def _add_to_recent(self, file_path: str, name: str):
        """Add configuration to recent list."""
        recent = self.settings.value("recent_configs", [], type=list)
        
        # Create entry
        entry = {
            "path": file_path,
            "name": name,
            "date": datetime.now().isoformat(),
        }
        
        # Remove existing entry for same path
        recent = [r for r in recent if r.get("path") != file_path]
        
        # Add to front
        recent.insert(0, entry)
        
        # Keep only last 10
        recent = recent[:10]
        
        self.settings.setValue("recent_configs", recent)
    
    def get_saved_path(self) -> Optional[str]:
        """Get the path where configuration was saved."""
        return self.saved_file_path
