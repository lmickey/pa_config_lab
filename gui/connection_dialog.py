"""
Connection dialog for Prisma Access API authentication.

This module provides a dialog for entering Prisma Access credentials
and establishing API connections.
"""

from typing import Optional, Tuple
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
    QProgressDialog,
)
from PyQt6.QtCore import Qt, QSettings, QThread, pyqtSignal
from PyQt6.QtGui import QIcon


class AuthenticationWorker(QThread):
    """Background worker for API authentication."""

    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(str)  # status message

    def __init__(self, tsg_id: str, api_user: str, api_secret: str):
        """Initialize the authentication worker."""
        super().__init__()
        self.tsg_id = tsg_id
        self.api_user = api_user
        self.api_secret = api_secret
        self.api_client = None

    def run(self):
        """Run the authentication process."""
        try:
            self.progress.emit("Initializing API client...")

            from prisma.api_client import PrismaAccessAPIClient

            self.progress.emit("Connecting to Prisma Access...")

            # Create API client
            self.api_client = PrismaAccessAPIClient(
                tsg_id=self.tsg_id, api_user=self.api_user, api_secret=self.api_secret
            )

            self.progress.emit("Authenticating...")

            # Authentication happens in __init__
            # Note: api_client uses 'token' attribute, not 'access_token'
            if self.api_client.token:
                self.progress.emit("Authentication successful!")
                self.finished.emit(True, f"Connected to tenant: {self.tsg_id}")
            else:
                self.finished.emit(False, "Authentication failed: No token received")

        except Exception as e:
            self.finished.emit(False, f"Authentication error: {str(e)}")


class ConnectionDialog(QDialog):
    """Dialog for connecting to Prisma Access."""

    def __init__(self, parent=None):
        """Initialize the connection dialog."""
        super().__init__(parent)

        self.settings = QSettings("PrismaAccess", "ConfigManager")
        self.api_client = None
        self.worker = None

        self._init_ui()
        self._load_saved_credentials()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Connect to Prisma Access")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>Prisma Access Connection</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Info
        info = QLabel(
            "Enter your Prisma Access SCM API credentials to connect.\n"
            "You can find these in the Prisma Access Hub."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin: 10px;")
        layout.addWidget(info)

        # Form
        form_layout = QFormLayout()

        self.tsg_id_input = QLineEdit()
        self.tsg_id_input.setPlaceholderText("e.g., 1234567890")
        form_layout.addRow("TSG ID:", self.tsg_id_input)

        self.api_user_input = QLineEdit()
        self.api_user_input.setPlaceholderText("API Client ID")
        form_layout.addRow("API User (Client ID):", self.api_user_input)

        self.api_secret_input = QLineEdit()
        self.api_secret_input.setPlaceholderText("API Client Secret")
        self.api_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("API Secret:", self.api_secret_input)

        layout.addLayout(form_layout)

        # Remember credentials checkbox
        self.remember_checkbox = QCheckBox("Remember credentials (stored securely)")
        layout.addWidget(self.remember_checkbox)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.connect_button = QPushButton("Connect")
        self.connect_button.setDefault(True)
        self.connect_button.clicked.connect(self._on_connect)
        button_layout.addWidget(self.connect_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def _load_saved_credentials(self):
        """Load saved credentials from settings."""
        if self.settings.value("remember_credentials", False, type=bool):
            self.tsg_id_input.setText(self.settings.value("tsg_id", ""))
            self.api_user_input.setText(self.settings.value("api_user", ""))
            # Note: API secret not saved for security
            self.remember_checkbox.setChecked(True)

    def _save_credentials(self):
        """Save credentials to settings if remember is checked."""
        if self.remember_checkbox.isChecked():
            self.settings.setValue("remember_credentials", True)
            self.settings.setValue("tsg_id", self.tsg_id_input.text())
            self.settings.setValue("api_user", self.api_user_input.text())
            # Note: API secret intentionally not saved
        else:
            self.settings.setValue("remember_credentials", False)
            self.settings.remove("tsg_id")
            self.settings.remove("api_user")

    def _on_connect(self):
        """Handle connect button click."""
        # Validate inputs
        tsg_id = self.tsg_id_input.text().strip()
        api_user = self.api_user_input.text().strip()
        api_secret = self.api_secret_input.text().strip()

        if not tsg_id:
            QMessageBox.warning(self, "Missing Information", "Please enter TSG ID.")
            self.tsg_id_input.setFocus()
            return

        if not api_user:
            QMessageBox.warning(
                self, "Missing Information", "Please enter API User (Client ID)."
            )
            self.api_user_input.setFocus()
            return

        if not api_secret:
            QMessageBox.warning(self, "Missing Information", "Please enter API Secret.")
            self.api_secret_input.setFocus()
            return

        # Save credentials if requested
        self._save_credentials()

        # Disable UI during connection
        self.connect_button.setEnabled(False)
        self.tsg_id_input.setEnabled(False)
        self.api_user_input.setEnabled(False)
        self.api_secret_input.setEnabled(False)

        # Create progress dialog
        self.progress_dialog = QProgressDialog(
            "Connecting to Prisma Access...", None, 0, 0, self
        )
        self.progress_dialog.setWindowTitle("Connecting")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()

        # Start authentication in background
        self.worker = AuthenticationWorker(tsg_id, api_user, api_secret)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_authentication_finished)
        self.worker.start()

    def _on_progress(self, message: str):
        """Handle progress updates."""
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.setLabelText(message)

    def _on_authentication_finished(self, success: bool, message: str):
        """Handle authentication completion."""
        # Close progress dialog
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()
            delattr(self, "progress_dialog")

        # Re-enable UI
        self.connect_button.setEnabled(True)
        self.tsg_id_input.setEnabled(True)
        self.api_user_input.setEnabled(True)
        self.api_secret_input.setEnabled(True)

        if success:
            # Store API client
            self.api_client = self.worker.api_client

            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Connection Failed", message)

    def get_api_client(self):
        """Get the authenticated API client."""
        return self.api_client
