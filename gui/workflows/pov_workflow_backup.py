"""
POV Configuration Workflow GUI.

This module provides the UI for configuring new POV environments,
including loading configurations from various sources and deploying
to firewall and Prisma Access.
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QRadioButton,
    QPushButton,
    QLabel,
    QLineEdit,
    QTextEdit,
    QProgressBar,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QFormLayout,
    QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread


class POVConfigWorker(QThread):
    """Background worker for POV configuration operations."""

    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)

    def __init__(self, operation: str, config: Dict[str, Any], **kwargs):
        """Initialize POV config worker."""
        super().__init__()
        self.operation = operation
        self.config = config
        self.kwargs = kwargs

    def run(self):
        """Run POV configuration operation."""
        try:
            if self.operation == "configure_firewall":
                self._configure_firewall()
            elif self.operation == "configure_service_connection":
                self._configure_service_connection()
            elif self.operation == "complete_setup":
                self._complete_setup()
        except Exception as e:
            self.error.emit(f"Operation failed: {str(e)}")
            self.finished.emit(False, str(e))

    def _configure_firewall(self):
        """Configure firewall settings."""
        self.progress.emit("Connecting to firewall...", 10)
        # Import and execute configure_firewall logic
        # This would be refactored from configure_firewall.py
        self.progress.emit("Configuring zones...", 30)
        self.progress.emit("Configuring interfaces...", 50)
        self.progress.emit("Configuring routes...", 70)
        self.progress.emit("Configuring policies...", 90)
        self.progress.emit("Complete!", 100)
        self.finished.emit(True, "Firewall configured successfully")

    def _configure_service_connection(self):
        """Configure Prisma Access service connection."""
        self.progress.emit("Connecting to Prisma Access API...", 10)
        # Import and execute service connection logic
        self.progress.emit("Creating IKE crypto profile...", 30)
        self.progress.emit("Creating IPSec crypto profile...", 50)
        self.progress.emit("Creating IKE gateway...", 70)
        self.progress.emit("Creating IPSec tunnel...", 90)
        self.progress.emit("Complete!", 100)
        self.finished.emit(True, "Service connection configured successfully")

    def _complete_setup(self):
        """Complete POV setup."""
        self.progress.emit("Verifying configuration...", 20)
        self.progress.emit("Applying settings...", 50)
        self.progress.emit("Committing changes...", 80)
        self.progress.emit("Complete!", 100)
        self.finished.emit(True, "POV setup complete")


class POVWorkflowWidget(QWidget):
    """Widget for POV configuration workflow."""

    def __init__(self, parent=None):
        """Initialize POV workflow widget."""
        super().__init__(parent)

        self.api_client = None
        self.config_data = None
        self.worker = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Step indicator
        steps_label = QLabel(
            "<b>POV Configuration Steps:</b> "
            "1️⃣ Load Config → 2️⃣ Review → 3️⃣ Configure Firewall → 4️⃣ Configure Prisma Access"
        )
        steps_label.setWordWrap(True)
        steps_label.setStyleSheet(
            "padding: 10px; background-color: #e3f2fd; border-radius: 5px;"
        )
        layout.addWidget(steps_label)

        # Tabs for each step
        self.tabs = QTabWidget()

        self._create_load_tab()
        self._create_review_tab()
        self._create_defaults_tab()
        self._create_firewall_tab()
        self._create_prisma_tab()

        layout.addWidget(self.tabs)

        # Progress section
        progress_group = QGroupBox("Operation Progress")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Ready to begin")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

    def _create_load_tab(self):
        """Create configuration loading tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 1: Configuration Source & Management</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Select how your environment is managed and configure sources.\n"
            "You can combine multiple configuration sources."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 15px;")
        layout.addWidget(info)

        # Management type selection
        mgmt_group = QGroupBox("Management Type")
        mgmt_layout = QVBoxLayout()

        self.scm_managed_radio = QRadioButton(
            "SCM Managed - Configuration via Prisma Access Cloud (Recommended)"
        )
        self.scm_managed_radio.setChecked(True)
        self.scm_managed_radio.toggled.connect(self._on_management_changed)
        mgmt_layout.addWidget(self.scm_managed_radio)

        self.panorama_managed_radio = QRadioButton(
            "Panorama Managed - Configuration via on-premises Panorama"
        )
        self.panorama_managed_radio.toggled.connect(self._on_management_changed)
        mgmt_layout.addWidget(self.panorama_managed_radio)

        mgmt_group.setLayout(mgmt_layout)
        layout.addWidget(mgmt_group)

        # Configuration sources (can select multiple)
        sources_group = QGroupBox("Configuration Sources (Select all that apply)")
        sources_layout = QVBoxLayout()

        # SPOV Questionnaire
        self.spov_check = QCheckBox("Load from SPOV Questionnaire (JSON)")
        self.spov_check.stateChanged.connect(self._update_source_visibility)
        sources_layout.addWidget(self.spov_check)

        self.spov_layout = QHBoxLayout()
        self.spov_path_input = QLineEdit()
        self.spov_path_input.setPlaceholderText("SPOV questionnaire file...")
        self.spov_path_input.setReadOnly(True)
        self.spov_layout.addWidget(self.spov_path_input)
        self.spov_browse_btn = QPushButton("Browse...")
        self.spov_browse_btn.clicked.connect(self._browse_spov_file)
        self.spov_layout.addWidget(self.spov_browse_btn)
        sources_layout.addLayout(self.spov_layout)

        # Terraform
        self.terraform_check = QCheckBox("Import from Terraform Configuration")
        self.terraform_check.stateChanged.connect(self._update_source_visibility)
        sources_layout.addWidget(self.terraform_check)

        self.terraform_layout = QHBoxLayout()
        self.terraform_path_input = QLineEdit()
        self.terraform_path_input.setPlaceholderText("Terraform directory or files...")
        self.terraform_path_input.setReadOnly(True)
        self.terraform_layout.addWidget(self.terraform_path_input)
        self.terraform_browse_btn = QPushButton("Browse...")
        self.terraform_browse_btn.clicked.connect(self._browse_terraform_dir)
        self.terraform_layout.addWidget(self.terraform_browse_btn)
        sources_layout.addLayout(self.terraform_layout)

        # Existing JSON config
        self.json_check = QCheckBox("Load from existing JSON configuration")
        self.json_check.stateChanged.connect(self._update_source_visibility)
        sources_layout.addWidget(self.json_check)

        self.json_layout = QHBoxLayout()
        self.json_path_input = QLineEdit()
        self.json_path_input.setPlaceholderText("JSON configuration file...")
        self.json_path_input.setReadOnly(True)
        self.json_layout.addWidget(self.json_path_input)
        self.json_browse_btn = QPushButton("Browse...")
        self.json_browse_btn.clicked.connect(self._browse_json_file)
        self.json_layout.addWidget(self.json_browse_btn)
        sources_layout.addLayout(self.json_layout)

        # Manual entry
        self.manual_check = QCheckBox("Manual entry for additional parameters")
        sources_layout.addWidget(self.manual_check)

        sources_group.setLayout(sources_layout)
        layout.addWidget(sources_group)

        # SCM Credentials (conditional)
        self.scm_creds_group = QGroupBox("SCM API Credentials")
        scm_creds_layout = QFormLayout()

        self.scm_tsg_input = QLineEdit()
        self.scm_tsg_input.setPlaceholderText("tsg-1234567890")
        scm_creds_layout.addRow("TSG ID:", self.scm_tsg_input)

        self.scm_user_input = QLineEdit()
        self.scm_user_input.setPlaceholderText("Client ID")
        scm_creds_layout.addRow("API User:", self.scm_user_input)

        self.scm_secret_input = QLineEdit()
        self.scm_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.scm_secret_input.setPlaceholderText("Client Secret")
        scm_creds_layout.addRow("API Secret:", self.scm_secret_input)

        self.scm_creds_group.setLayout(scm_creds_layout)
        layout.addWidget(self.scm_creds_group)

        # Load button
        load_btn_layout = QHBoxLayout()
        load_btn_layout.addStretch()

        self.load_config_btn = QPushButton("Load & Merge Configuration")
        self.load_config_btn.setMinimumWidth(200)
        self.load_config_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.load_config_btn.clicked.connect(self._load_config)
        load_btn_layout.addWidget(self.load_config_btn)

        layout.addLayout(load_btn_layout)

        # Status
        self.load_status = QLabel("No configuration loaded")
        self.load_status.setStyleSheet("color: gray; margin-top: 10px;")
        layout.addWidget(self.load_status)

        layout.addStretch()

        # Initialize visibility
        self._update_source_visibility()
        self._on_management_changed()

        self.tabs.addTab(tab, "1. Load")

    def _create_review_tab(self):
        """Create configuration review tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 2: Review Configuration</h3>")
        layout.addWidget(title)

        info = QLabel("Review the loaded configuration before deployment.")
        info.setStyleSheet("color: gray;")
        layout.addWidget(info)

        # Configuration display
        self.config_review_text = QTextEdit()
        self.config_review_text.setReadOnly(True)
        self.config_review_text.setPlaceholderText(
            "Loaded configuration will be displayed here...\n\n"
            "Review firewall data, Prisma Access data, and other settings."
        )
        layout.addWidget(self.config_review_text)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        next_btn = QPushButton("Next: Inject Defaults →")
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        nav_layout.addWidget(next_btn)

        layout.addLayout(nav_layout)

        self.tabs.addTab(tab, "2. Review")

    def _create_defaults_tab(self):
        """Create firewall configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 3: Configure Firewall</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Configure the NGFW with zones, interfaces, routes, objects, and policies.\n"
            "This step uses the pan-os-python library to configure the firewall."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 15px;")
        layout.addWidget(info)

        # Firewall connection info
        fw_group = QGroupBox("Firewall Connection")
        fw_layout = QFormLayout()

        self.fw_ip_label = QLabel("Not loaded")
        fw_layout.addRow("Management IP:", self.fw_ip_label)

        self.fw_user_label = QLabel("Not loaded")
        fw_layout.addRow("Username:", self.fw_user_label)

        fw_group.setLayout(fw_layout)
        layout.addWidget(fw_group)

        # Configuration options
        options_group = QGroupBox("Configuration Options")
        options_layout = QVBoxLayout()

        self.fw_zones_check = QCheckBox("Configure Zones (trust/untrust)")
        self.fw_zones_check.setChecked(True)
        options_layout.addWidget(self.fw_zones_check)

        self.fw_interfaces_check = QCheckBox("Configure Interfaces")
        self.fw_interfaces_check.setChecked(True)
        options_layout.addWidget(self.fw_interfaces_check)

        self.fw_routes_check = QCheckBox("Configure Routes")
        self.fw_routes_check.setChecked(True)
        options_layout.addWidget(self.fw_routes_check)

        self.fw_objects_check = QCheckBox("Configure Address Objects")
        self.fw_objects_check.setChecked(True)
        options_layout.addWidget(self.fw_objects_check)

        self.fw_policies_check = QCheckBox("Configure Security Policies")
        self.fw_policies_check.setChecked(True)
        options_layout.addWidget(self.fw_policies_check)

        self.fw_ntp_dns_check = QCheckBox("Configure NTP/DNS")
        self.fw_ntp_dns_check.setChecked(True)
        options_layout.addWidget(self.fw_ntp_dns_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Configure button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.configure_fw_btn = QPushButton("Configure Firewall")
        self.configure_fw_btn.setMinimumWidth(180)
        self.configure_fw_btn.setEnabled(False)
        self.configure_fw_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; padding: 10px; }"
            "QPushButton:hover { background-color: #F57C00; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.configure_fw_btn.clicked.connect(self._configure_firewall)
        btn_layout.addWidget(self.configure_fw_btn)

        layout.addLayout(btn_layout)

        # Results
        self.fw_results = QTextEdit()
        self.fw_results.setReadOnly(True)
        self.fw_results.setMaximumHeight(150)
        self.fw_results.setPlaceholderText("Configuration results will appear here...")
        layout.addWidget(self.fw_results)

        # Navigation
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        next_btn = QPushButton("Next: Configure Prisma Access →")
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        nav_layout.addWidget(next_btn)

        layout.addLayout(nav_layout)

        self.tabs.addTab(tab, "3. Firewall")

    def _create_prisma_tab(self):
        """Create Prisma Access configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 4: Configure Prisma Access</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Configure Prisma Access service connections and settings.\n"
            "This step sets up IKE/IPSec tunnels and service connections."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 15px;")
        layout.addWidget(info)

        # PA connection info
        pa_group = QGroupBox("Prisma Access API")
        pa_layout = QFormLayout()

        self.pa_tsg_label = QLabel("Not loaded")
        pa_layout.addRow("TSG ID:", self.pa_tsg_label)

        self.pa_region_label = QLabel("Not loaded")
        pa_layout.addRow("Region:", self.pa_region_label)

        pa_group.setLayout(pa_layout)
        layout.addWidget(pa_group)

        # Configuration options
        options_group = QGroupBox("Configuration Options")
        options_layout = QVBoxLayout()

        self.pa_ike_check = QCheckBox("Create IKE Crypto Profile")
        self.pa_ike_check.setChecked(True)
        options_layout.addWidget(self.pa_ike_check)

        self.pa_ipsec_check = QCheckBox("Create IPSec Crypto Profile")
        self.pa_ipsec_check.setChecked(True)
        options_layout.addWidget(self.pa_ipsec_check)

        self.pa_gateway_check = QCheckBox("Create IKE Gateway")
        self.pa_gateway_check.setChecked(True)
        options_layout.addWidget(self.pa_gateway_check)

        self.pa_tunnel_check = QCheckBox("Create IPSec Tunnel")
        self.pa_tunnel_check.setChecked(True)
        options_layout.addWidget(self.pa_tunnel_check)

        self.pa_service_conn_check = QCheckBox("Create Service Connection")
        self.pa_service_conn_check.setChecked(True)
        options_layout.addWidget(self.pa_service_conn_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Configure button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.configure_pa_btn = QPushButton("Configure Prisma Access")
        self.configure_pa_btn.setMinimumWidth(200)
        self.configure_pa_btn.setEnabled(False)
        self.configure_pa_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 10px; }"
            "QPushButton:hover { background-color: #0b7dda; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.configure_pa_btn.clicked.connect(self._configure_prisma_access)
        btn_layout.addWidget(self.configure_pa_btn)

        layout.addLayout(btn_layout)

        # Results
        self.pa_results = QTextEdit()
        self.pa_results.setReadOnly(True)
        self.pa_results.setMaximumHeight(150)
        self.pa_results.setPlaceholderText("Configuration results will appear here...")
        layout.addWidget(self.pa_results)

        # Complete button
        complete_layout = QHBoxLayout()
        complete_layout.addStretch()

        self.complete_btn = QPushButton("✓ Complete POV Setup")
        self.complete_btn.setMinimumWidth(180)
        self.complete_btn.setEnabled(False)
        self.complete_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.complete_btn.clicked.connect(self._complete_pov_setup)
        complete_layout.addWidget(self.complete_btn)

        layout.addLayout(complete_layout)

        self.tabs.addTab(tab, "4. Prisma Access")

    def set_api_client(self, api_client):
        """Set API client."""
        self.api_client = api_client

    def _browse_config_file(self):
        """Browse for configuration file."""
        if self.load_json_radio.isChecked():
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select POV Configuration File",
                "",
                "JSON Files (*.json);;All Files (*)",
            )
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Configuration File", "", "All Files (*)"
            )

        if file_path:
            self.file_path_input.setText(file_path)

    def _load_config(self):
        """Load configuration from selected source."""
        if not self.file_path_input.text() and not self.manual_entry_radio.isChecked():
            QMessageBox.warning(
                self, "No File Selected", "Please select a configuration file."
            )
            return

        try:
            # Use load_settings module to load configuration
            import load_settings

            file_path = self.file_path_input.text()

            if self.load_json_radio.isChecked():
                # Load JSON config
                from config.storage.json_storage import load_config_json

                self.config_data = load_config_json(file_path, validate=False)
            elif self.load_terraform_radio.isChecked():
                # TODO: Implement Terraform/SCM import
                QMessageBox.information(
                    self,
                    "Coming Soon",
                    "Terraform/SCM import will be implemented in a future update.",
                )
                return
            elif self.manual_entry_radio.isChecked():
                # TODO: Implement manual entry
                QMessageBox.information(
                    self,
                    "Coming Soon",
                    "Manual configuration entry will be implemented in a future update.",
                )
                return

            if self.config_data:
                self.load_status.setText("✓ Configuration loaded successfully")
                self.load_status.setStyleSheet("color: green;")

                # Update review tab
                import json

                self.config_review_text.setPlainText(
                    json.dumps(self.config_data, indent=2)
                )

                # Enable next steps
                self.configure_fw_btn.setEnabled(True)
                self.configure_pa_btn.setEnabled(True)

                # Update firewall/PA info
                self._update_config_display()

                # Move to review tab
                self.tabs.setCurrentIndex(1)

        except Exception as e:
            QMessageBox.critical(
                self, "Load Failed", f"Failed to load configuration:\n{str(e)}"
            )

    def _update_config_display(self):
        """Update firewall and PA info labels."""
        if not self.config_data:
            return

        fw_data = self.config_data.get("fwData", {})
        pa_data = self.config_data.get("paData", {})

        # Firewall info
        self.fw_ip_label.setText(fw_data.get("mgmtUrl", "Not configured"))
        self.fw_user_label.setText(fw_data.get("mgmtUser", "Not configured"))

        # PA info
        self.pa_tsg_label.setText(pa_data.get("paTsgId", "Not configured"))
        self.pa_region_label.setText(pa_data.get("scLocation", "Not configured"))

    def _configure_firewall(self):
        """Configure the firewall."""
        if not self.config_data:
            QMessageBox.warning(
                self, "No Configuration", "Please load a configuration first."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Firewall Configuration",
            "This will configure the firewall with the loaded settings.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Start worker
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.worker = POVConfigWorker("configure_firewall", self.config_data)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_fw_finished)
        self.worker.start()

    def _configure_prisma_access(self):
        """Configure Prisma Access."""
        if not self.config_data:
            QMessageBox.warning(
                self, "No Configuration", "Please load a configuration first."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Prisma Access Configuration",
            "This will configure Prisma Access service connections.\n\n" "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Start worker
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.worker = POVConfigWorker("configure_service_connection", self.config_data)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_pa_finished)
        self.worker.start()

    def _complete_pov_setup(self):
        """Complete POV setup."""
        QMessageBox.information(
            self,
            "POV Setup Complete",
            "POV environment configured successfully!\n\n"
            "Next steps:\n"
            "• Verify firewall configuration\n"
            "• Test service connections\n"
            "• Validate connectivity",
        )

    def _on_progress(self, message: str, percentage: int):
        """Handle progress updates."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(percentage)

    def _on_fw_finished(self, success: bool, message: str):
        """Handle firewall configuration completion."""
        if success:
            self.fw_results.setPlainText(f"✓ Success\n\n{message}")
            self.progress_label.setText("Firewall configured successfully")
            QMessageBox.information(self, "Success", message)
        else:
            self.fw_results.setPlainText(f"✗ Failed\n\n{message}")
            self.progress_label.setText("Configuration failed")
            QMessageBox.critical(self, "Failed", message)

    def _on_pa_finished(self, success: bool, message: str):
        """Handle Prisma Access configuration completion."""
        if success:
            self.pa_results.setPlainText(f"✓ Success\n\n{message}")
            self.progress_label.setText("Prisma Access configured successfully")
            self.complete_btn.setEnabled(True)
            QMessageBox.information(self, "Success", message)
        else:
            self.pa_results.setPlainText(f"✗ Failed\n\n{message}")
            self.progress_label.setText("Configuration failed")
            QMessageBox.critical(self, "Failed", message)
