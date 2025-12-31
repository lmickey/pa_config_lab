"""
Manual Configuration Dialog for POV Setup.

This module provides a dialog for manually entering POV configuration parameters,
including firewall settings and optionally Panorama settings.
"""

import ipaddress
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QTabWidget,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator


class ManualConfigDialog(QDialog):
    """Dialog for manual configuration entry."""

    def __init__(self, management_type: str = "scm", parent=None):
        """
        Initialize manual config dialog.

        Args:
            management_type: "scm" or "panorama"
            parent: Parent widget
        """
        super().__init__(parent)
        self.management_type = management_type
        self.config_data = {}

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Manual Configuration Entry")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>Manual Configuration Entry</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Description
        mgmt_text = "Panorama Managed" if self.management_type == "panorama" else "SCM Managed"
        desc = QLabel(
            f"<b>Management Type:</b> {mgmt_text}<br>"
            "Enter the required configuration parameters for your POV environment.<br>"
            "<b>All fields are required.</b>"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; padding: 10px; background-color: #f5f5f5; border-radius: 5px;")
        layout.addWidget(desc)

        # Tabs for different sections
        tabs = QTabWidget()

        # Firewall tab
        self._create_firewall_tab(tabs)

        # Panorama tab (only for panorama management)
        if self.management_type == "panorama":
            self._create_panorama_tab(tabs)

        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Configuration")
        save_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px 15px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        save_btn.clicked.connect(self._validate_and_accept)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_firewall_tab(self, tabs: QTabWidget):
        """Create firewall configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Firewall Management
        mgmt_group = QGroupBox("Firewall Management")
        mgmt_layout = QFormLayout()

        self.fw_url_input = QLineEdit()
        self.fw_url_input.setPlaceholderText("192.168.1.1 or https://192.168.1.1")
        mgmt_layout.addRow("Management URL*:", self.fw_url_input)

        self.fw_user_input = QLineEdit()
        self.fw_user_input.setPlaceholderText("admin")
        mgmt_layout.addRow("Management User*:", self.fw_user_input)

        self.fw_pass_input = QLineEdit()
        self.fw_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.fw_pass_input.setPlaceholderText("Password")
        mgmt_layout.addRow("Management Password*:", self.fw_pass_input)

        mgmt_group.setLayout(mgmt_layout)
        layout.addWidget(mgmt_group)

        # Untrust Interface
        untrust_group = QGroupBox("Untrust Interface (WAN)")
        untrust_layout = QFormLayout()

        self.untrust_int_input = QLineEdit()
        self.untrust_int_input.setPlaceholderText("ethernet1/1")
        untrust_layout.addRow("Interface Name*:", self.untrust_int_input)

        self.untrust_ip_input = QLineEdit()
        self.untrust_ip_input.setPlaceholderText("203.0.113.10/24")
        self.untrust_ip_input.textChanged.connect(self._on_untrust_ip_changed)
        untrust_layout.addRow("IP Address/CIDR*:", self.untrust_ip_input)

        self.untrust_network_label = QLabel("(Calculated from IP)")
        self.untrust_network_label.setStyleSheet("color: gray; font-style: italic;")
        untrust_layout.addRow("Network:", self.untrust_network_label)

        self.untrust_gateway_input = QLineEdit()
        self.untrust_gateway_input.setPlaceholderText("203.0.113.1")
        untrust_layout.addRow("Default Gateway*:", self.untrust_gateway_input)

        untrust_group.setLayout(untrust_layout)
        layout.addWidget(untrust_group)

        # Trust Interface
        trust_group = QGroupBox("Trust Interface (LAN)")
        trust_layout = QFormLayout()

        self.trust_int_input = QLineEdit()
        self.trust_int_input.setPlaceholderText("ethernet1/2")
        trust_layout.addRow("Interface Name*:", self.trust_int_input)

        self.trust_ip_input = QLineEdit()
        self.trust_ip_input.setPlaceholderText("10.0.0.1/24")
        self.trust_ip_input.textChanged.connect(self._on_trust_ip_changed)
        trust_layout.addRow("IP Address/CIDR*:", self.trust_ip_input)

        self.trust_network_label = QLabel("(Calculated from IP)")
        self.trust_network_label.setStyleSheet("color: gray; font-style: italic;")
        trust_layout.addRow("Network:", self.trust_network_label)

        trust_group.setLayout(trust_layout)
        layout.addWidget(trust_group)

        layout.addStretch()

        tabs.addTab(tab, "Firewall Configuration")

    def _create_panorama_tab(self, tabs: QTabWidget):
        """Create Panorama configuration tab (only for panorama management)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Info
        info = QLabel(
            "<b>Panorama Management Settings</b><br>"
            "Since this deployment is Panorama Managed, provide the Panorama connection details."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #FF9800; padding: 10px; background-color: #FFF3E0; border-radius: 5px;")
        layout.addWidget(info)

        # Panorama Management
        pano_group = QGroupBox("Panorama Connection")
        pano_layout = QFormLayout()

        self.pano_url_input = QLineEdit()
        self.pano_url_input.setPlaceholderText("panorama.example.com or 192.168.1.100")
        pano_layout.addRow("Panorama URL*:", self.pano_url_input)

        self.pano_user_input = QLineEdit()
        self.pano_user_input.setPlaceholderText("admin")
        pano_layout.addRow("Panorama User*:", self.pano_user_input)

        self.pano_pass_input = QLineEdit()
        self.pano_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pano_pass_input.setPlaceholderText("Password")
        pano_layout.addRow("Panorama Password*:", self.pano_pass_input)

        pano_group.setLayout(pano_layout)
        layout.addWidget(pano_group)

        # Device Group (optional but helpful)
        dg_group = QGroupBox("Device Group (Optional)")
        dg_layout = QFormLayout()

        self.device_group_input = QLineEdit()
        self.device_group_input.setPlaceholderText("POV-Device-Group")
        dg_layout.addRow("Device Group:", self.device_group_input)

        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("POV-Template")
        dg_layout.addRow("Template:", self.template_input)

        dg_group.setLayout(dg_layout)
        layout.addWidget(dg_group)

        layout.addStretch()

        tabs.addTab(tab, "Panorama Configuration")

    def _on_untrust_ip_changed(self, text: str):
        """Calculate network from untrust IP."""
        self._calculate_network(text, self.untrust_network_label)

    def _on_trust_ip_changed(self, text: str):
        """Calculate network from trust IP."""
        self._calculate_network(text, self.trust_network_label)

    def _calculate_network(self, ip_cidr: str, label: QLabel):
        """Calculate and display network from IP/CIDR."""
        try:
            if "/" in ip_cidr:
                network = ipaddress.ip_network(ip_cidr, strict=False)
                label.setText(str(network))
                label.setStyleSheet("color: green; font-weight: bold;")
            else:
                label.setText("(Enter IP with /CIDR)")
                label.setStyleSheet("color: gray; font-style: italic;")
        except ValueError:
            label.setText("(Invalid IP format)")
            label.setStyleSheet("color: red; font-style: italic;")

    def _validate_and_accept(self):
        """Validate all fields and accept if valid."""
        errors = []

        # Validate firewall fields
        if not self.fw_url_input.text().strip():
            errors.append("Firewall Management URL is required")
        if not self.fw_user_input.text().strip():
            errors.append("Firewall Management User is required")
        if not self.fw_pass_input.text().strip():
            errors.append("Firewall Management Password is required")

        # Validate untrust interface
        if not self.untrust_int_input.text().strip():
            errors.append("Untrust Interface Name is required")
        if not self.untrust_ip_input.text().strip():
            errors.append("Untrust IP Address is required")
        else:
            # Validate IP format
            try:
                ipaddress.ip_interface(self.untrust_ip_input.text().strip())
            except ValueError:
                errors.append("Untrust IP Address is invalid (use format: 203.0.113.10/24)")
        if not self.untrust_gateway_input.text().strip():
            errors.append("Untrust Default Gateway is required")
        else:
            # Validate gateway IP
            try:
                ipaddress.ip_address(self.untrust_gateway_input.text().strip())
            except ValueError:
                errors.append("Untrust Default Gateway is invalid")

        # Validate trust interface
        if not self.trust_int_input.text().strip():
            errors.append("Trust Interface Name is required")
        if not self.trust_ip_input.text().strip():
            errors.append("Trust IP Address is required")
        else:
            # Validate IP format
            try:
                ipaddress.ip_interface(self.trust_ip_input.text().strip())
            except ValueError:
                errors.append("Trust IP Address is invalid (use format: 10.0.0.1/24)")

        # Validate Panorama fields if applicable
        if self.management_type == "panorama":
            if not self.pano_url_input.text().strip():
                errors.append("Panorama URL is required for Panorama Managed deployments")
            if not self.pano_user_input.text().strip():
                errors.append("Panorama User is required for Panorama Managed deployments")
            if not self.pano_pass_input.text().strip():
                errors.append("Panorama Password is required for Panorama Managed deployments")

        # Show errors if any
        if errors:
            QMessageBox.warning(
                self,
                "Validation Errors",
                "Please correct the following errors:\n\n" + "\n".join(f"• {e}" for e in errors)
            )
            return

        # Build configuration data
        self._build_config_data()

        # Accept dialog
        self.accept()

    def _build_config_data(self):
        """Build configuration data from form inputs."""
        # Calculate networks
        untrust_ip = ipaddress.ip_interface(self.untrust_ip_input.text().strip())
        trust_ip = ipaddress.ip_interface(self.trust_ip_input.text().strip())

        # Firewall data
        self.config_data = {
            "fwData": {
                "mgmtUrl": self.fw_url_input.text().strip(),
                "mgmtUser": self.fw_user_input.text().strip(),
                "mgmtPass": self.fw_pass_input.text().strip(),
                "untrustInt": self.untrust_int_input.text().strip(),
                "untrustAddr": str(untrust_ip),
                "untrustSubnet": str(untrust_ip.network),
                "untrustDFGW": self.untrust_gateway_input.text().strip(),
                "trustInt": self.trust_int_input.text().strip(),
                "trustAddr": str(trust_ip),
                "trustSubnet": str(trust_ip.network),
            },
            "source": "manual_entry",
            "management_type": self.management_type,
        }

        # Add Panorama data if applicable
        if self.management_type == "panorama":
            self.config_data["panoramaData"] = {
                "panoramaUrl": self.pano_url_input.text().strip(),
                "panoramaUser": self.pano_user_input.text().strip(),
                "panoramaPass": self.pano_pass_input.text().strip(),
            }

            # Add optional device group/template if provided
            if self.device_group_input.text().strip():
                self.config_data["panoramaData"]["deviceGroup"] = self.device_group_input.text().strip()
            if self.template_input.text().strip():
                self.config_data["panoramaData"]["template"] = self.template_input.text().strip()

    def get_config(self) -> Dict[str, Any]:
        """Get the configuration data."""
        return self.config_data
