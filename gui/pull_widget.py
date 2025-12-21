"""
Pull configuration widget for the GUI.

This module provides the UI for pulling configurations from Prisma Access,
including options selection, progress tracking, and results display.
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.workers import PullWorker


class PullConfigWidget(QWidget):
    """Widget for pulling configurations from Prisma Access."""

    # Signal emitted when pull completes successfully
    pull_completed = pyqtSignal(object)  # config

    def __init__(self, parent=None):
        """Initialize the pull widget."""
        super().__init__(parent)

        self.api_client = None
        self.worker = None
        self.pulled_config = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>Pull Configuration</h2>")
        layout.addWidget(title)

        info = QLabel(
            "Pull configuration from the connected Prisma Access tenant.\n"
            "Select which components to retrieve."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)

        # Scroll area for options
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Options group
        options_group = QGroupBox("Configuration Components")
        options_layout = QVBoxLayout()

        self.folders_check = QCheckBox("Security Policy Folders")
        self.folders_check.setChecked(True)
        self.folders_check.setToolTip("Pull folder structure and organization")
        options_layout.addWidget(self.folders_check)

        self.snippets_check = QCheckBox("Configuration Snippets")
        self.snippets_check.setChecked(True)
        self.snippets_check.setToolTip("Pull configuration snippets")
        options_layout.addWidget(self.snippets_check)

        self.rules_check = QCheckBox("Security Rules")
        self.rules_check.setChecked(True)
        self.rules_check.setToolTip("Pull security policy rules")
        options_layout.addWidget(self.rules_check)

        self.objects_check = QCheckBox("Security Objects")
        self.objects_check.setChecked(True)
        self.objects_check.setToolTip(
            "Pull addresses, address groups, services, service groups, etc."
        )
        options_layout.addWidget(self.objects_check)

        self.profiles_check = QCheckBox("Security Profiles")
        self.profiles_check.setChecked(True)
        self.profiles_check.setToolTip(
            "Pull security profiles (AV, AS, vulnerability, etc.)"
        )
        options_layout.addWidget(self.profiles_check)

        options_group.setLayout(options_layout)
        scroll_layout.addWidget(options_group)

        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QVBoxLayout()

        self.filter_defaults_check = QCheckBox("Filter Default Configurations")
        self.filter_defaults_check.setChecked(False)
        self.filter_defaults_check.setToolTip(
            "Automatically detect and exclude default configurations"
        )
        advanced_layout.addWidget(self.filter_defaults_check)

        advanced_group.setLayout(advanced_layout)
        scroll_layout.addWidget(advanced_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self._select_none)
        button_layout.addWidget(self.select_none_btn)

        button_layout.addStretch()

        self.pull_btn = QPushButton("Pull Configuration")
        self.pull_btn.setMinimumWidth(150)
        self.pull_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.pull_btn.clicked.connect(self._start_pull)
        button_layout.addWidget(self.pull_btn)

        layout.addLayout(button_layout)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Ready to pull")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Results section
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        self.results_text.setPlaceholderText("Pull results will appear here...")
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        layout.addStretch()

    def set_api_client(self, api_client):
        """Set the API client for pull operations."""
        self.api_client = api_client
        self.pull_btn.setEnabled(api_client is not None)

        if api_client:
            self.progress_label.setText(
                f"Connected to {api_client.tsg_id} - Ready to pull"
            )
            self.progress_label.setStyleSheet("color: green;")
        else:
            self.progress_label.setText("Not connected")
            self.progress_label.setStyleSheet("color: gray;")

    def _select_all(self):
        """Select all checkboxes."""
        self.folders_check.setChecked(True)
        self.snippets_check.setChecked(True)
        self.rules_check.setChecked(True)
        self.objects_check.setChecked(True)
        self.profiles_check.setChecked(True)

    def _select_none(self):
        """Deselect all checkboxes."""
        self.folders_check.setChecked(False)
        self.snippets_check.setChecked(False)
        self.rules_check.setChecked(False)
        self.objects_check.setChecked(False)
        self.profiles_check.setChecked(False)

    def _start_pull(self):
        """Start the pull operation."""
        # Check if API client is set
        if not self.api_client:
            # Show connection prompt
            reply = QMessageBox.question(
                self,
                "Connect to Prisma Access",
                "You need to connect to Prisma Access before pulling configuration.\n\n"
                "Would you like to connect now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Import and show connection dialog
                from gui.connection_dialog import ConnectionDialog
                
                dialog = ConnectionDialog(self)
                if dialog.exec():
                    # Get the API client from the dialog
                    self.api_client = dialog.get_api_client()
                    
                    if not self.api_client:
                        QMessageBox.warning(
                            self,
                            "Connection Failed",
                            "Failed to connect to Prisma Access. Please try again."
                        )
                        return
                    
                    # Connection successful
                    QMessageBox.information(
                        self,
                        "Connected",
                        "Successfully connected to Prisma Access.\n\nYou can now pull the configuration."
                    )
                else:
                    # User cancelled connection
                    return
            else:
                # User declined to connect
                return
        
        # Validate that we have an API client now
        if not self.api_client:
            QMessageBox.warning(
                self, "Not Connected", "Please connect to Prisma Access first."
            )
            return

        # Validate at least one option is selected
        if not any(
            [
                self.folders_check.isChecked(),
                self.snippets_check.isChecked(),
                self.rules_check.isChecked(),
                self.objects_check.isChecked(),
                self.profiles_check.isChecked(),
            ]
        ):
            QMessageBox.warning(
                self,
                "No Options Selected",
                "Please select at least one configuration component to pull.",
            )
            return

        # Gather options
        options = {
            "folders": self.folders_check.isChecked(),
            "snippets": self.snippets_check.isChecked(),
            "rules": self.rules_check.isChecked(),
            "objects": self.objects_check.isChecked(),
            "profiles": self.profiles_check.isChecked(),
        }

        filter_defaults = self.filter_defaults_check.isChecked()

        # Disable UI during pull
        self._set_ui_enabled(False)

        # Show progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Preparing to pull configuration...")

        # Clear previous results
        self.results_text.clear()

        # Create and start worker
        self.worker = PullWorker(self.api_client, options, filter_defaults)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_pull_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, message: str, percentage: int):
        """Handle progress updates."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(percentage)
        
        # Also append to results window for visibility
        self.results_text.append(f"[{percentage}%] {message}")

    def _on_error(self, error_message: str):
        """Handle error from worker."""
        self.results_text.append(f"\n❌ ERROR: {error_message}")

    def _on_pull_finished(self, success: bool, message: str, config: Optional[Dict]):
        """Handle pull completion."""
        # Re-enable UI
        self._set_ui_enabled(True)

        if success:
            self.progress_label.setText("Pull completed successfully!")
            self.progress_label.setStyleSheet("color: green;")
            
            # Append stats to results
            self.results_text.append(f"\n{'='*50}")
            self.results_text.append("✓ Pull completed successfully!")
            self.results_text.append(f"\n{message}")
            
            self.pulled_config = config

            # Emit signal
            self.pull_completed.emit(config)

            QMessageBox.information(
                self, "Success", "Configuration pulled successfully!"
            )
        else:
            self.progress_label.setText("Pull failed")
            self.progress_label.setStyleSheet("color: red;")
            
            # Show error in results
            self.results_text.append(f"\n{'='*50}")
            self.results_text.append(f"✗ Pull failed!")
            self.results_text.append(f"\nError: {message}")
            
            QMessageBox.warning(self, "Pull Failed", f"Pull operation failed:\n\n{message}")

    def _set_ui_enabled(self, enabled: bool):
        """Enable or disable UI controls."""
        self.folders_check.setEnabled(enabled)
        self.snippets_check.setEnabled(enabled)
        self.rules_check.setEnabled(enabled)
        self.objects_check.setEnabled(enabled)
        self.profiles_check.setEnabled(enabled)
        self.filter_defaults_check.setEnabled(enabled)
        self.select_all_btn.setEnabled(enabled)
        self.select_none_btn.setEnabled(enabled)
        self.pull_btn.setEnabled(enabled)

    def get_pulled_config(self) -> Optional[Dict[str, Any]]:
        """Get the pulled configuration."""
        return self.pulled_config
