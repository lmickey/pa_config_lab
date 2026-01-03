"""
Password Dialog for decrypting configurations.

Simple dialog that prompts for a password to decrypt a configuration file.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class PasswordDialog(QDialog):
    """Dialog for entering decryption password."""
    
    MAX_ATTEMPTS = 3
    
    def __init__(
        self,
        config_name: str,
        parent=None,
        attempts_remaining: int = MAX_ATTEMPTS
    ):
        """
        Initialize password dialog.
        
        Args:
            config_name: Name of configuration being decrypted
            parent: Parent widget
            attempts_remaining: Number of attempts remaining
        """
        super().__init__(parent)
        
        self.config_name = config_name
        self.attempts_remaining = attempts_remaining
        self.password = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Enter Password")
        self.setMinimumWidth(400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h3>Decrypt Configuration</h3>")
        layout.addWidget(title)
        
        # Config name
        name_label = QLabel(f"<b>Configuration:</b> {self.config_name}")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        layout.addSpacing(10)
        
        # Password field
        form_layout = QFormLayout()
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Enter password")
        self.password_edit.returnPressed.connect(self._decrypt)
        form_layout.addRow("Password:", self.password_edit)
        
        layout.addLayout(form_layout)
        
        # Show password checkbox
        self.show_password_check = QCheckBox("Show password")
        self.show_password_check.toggled.connect(self._toggle_password_visibility)
        layout.addWidget(self.show_password_check)
        
        # Attempts warning
        if self.attempts_remaining < self.MAX_ATTEMPTS:
            attempts_label = QLabel(
                f"<span style='color: #c00;'>"
                f"⚠ {self.attempts_remaining} attempt(s) remaining"
                f"</span>"
            )
            layout.addWidget(attempts_label)
        
        # Error message
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #c00;")
        self.error_label.hide()
        layout.addWidget(self.error_label)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.decrypt_btn = QPushButton("Decrypt && Load")
        self.decrypt_btn.setDefault(True)
        self.decrypt_btn.clicked.connect(self._decrypt)
        button_layout.addWidget(self.decrypt_btn)
        
        layout.addLayout(button_layout)
        
        # Focus password field
        self.password_edit.setFocus()
    
    def _toggle_password_visibility(self, show: bool):
        """Toggle password visibility."""
        if show:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
    
    def _decrypt(self):
        """Accept the password."""
        password = self.password_edit.text()
        
        if not password:
            self.error_label.setText("Password is required")
            self.error_label.show()
            return
        
        self.password = password
        self.accept()
    
    def get_password(self) -> Optional[str]:
        """Get the entered password."""
        return self.password
    
    def show_error(self, message: str):
        """Show an error message."""
        self.error_label.setText(message)
        self.error_label.show()
        self.password_edit.clear()
        self.password_edit.setFocus()
