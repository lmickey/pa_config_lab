"""
POV Configuration Dialogs.

Dialogs for configuring Cloud Resources and Use Cases in the POV workflow.
"""

from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QGroupBox,
    QFormLayout,
    QTabWidget,
    QWidget,
    QTextEdit,
    QScrollArea,
    QFrame,
    QGridLayout,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# BASE DIALOG CLASS
# =============================================================================

class POVConfigDialog(QDialog):
    """Base class for POV configuration dialogs."""

    def __init__(self, title: str, config: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self.config = config or {}
        self.result_config = {}

        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize the user interface. Override in subclasses."""
        self.layout = QVBoxLayout(self)

        # Title
        self.title_label = QLabel(f"<h3>{self.windowTitle()}</h3>")
        self.layout.addWidget(self.title_label)

        # Content area (override in subclasses)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.layout.addWidget(self.content_widget, 1)

        # Buttons
        self._add_buttons()

    def _add_buttons(self):
        """Add standard dialog buttons."""
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 8px 20px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        save_btn.clicked.connect(self._save_and_accept)
        buttons_layout.addWidget(save_btn)

        self.layout.addLayout(buttons_layout)

    def _load_config(self):
        """Load configuration into UI elements. Override in subclasses."""
        pass

    def _save_config(self) -> Dict[str, Any]:
        """Save UI state to configuration. Override in subclasses."""
        return {}

    def _save_and_accept(self):
        """Save configuration and accept dialog."""
        self.result_config = self._save_config()
        logger.info(f"Saved configuration: {self.windowTitle()}")
        self.accept()

    def get_config(self) -> Dict[str, Any]:
        """Get the resulting configuration."""
        return self.result_config


# =============================================================================
# CLOUD RESOURCES DIALOGS
# =============================================================================

class CloudDeploymentDialog(POVConfigDialog):
    """Dialog for Cloud Deployment & Sizing configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Cloud Deployment & Sizing", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Cloud Deployment & Sizing</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure Azure resource group, deployment locations, and VM sizing.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Resource Group section
        rg_group = QGroupBox("Resource Group")
        rg_layout = QFormLayout()

        self.customer_name = QLineEdit()
        self.customer_name.setPlaceholderText("e.g., acme")
        rg_layout.addRow("Customer Name:", self.customer_name)

        self.location = QComboBox()
        self.location.addItems([
            "eastus", "eastus2", "westus", "westus2", "centralus",
            "northeurope", "westeurope", "uksouth", "ukwest",
            "australiaeast", "southeastasia", "japaneast"
        ])
        rg_layout.addRow("Azure Location:", self.location)

        self.rg_preview = QLabel("")
        self.rg_preview.setStyleSheet("color: #666; font-style: italic;")
        rg_layout.addRow("Resource Group:", self.rg_preview)

        # Update preview when values change
        self.customer_name.textChanged.connect(self._update_rg_preview)
        self.location.currentTextChanged.connect(self._update_rg_preview)

        rg_group.setLayout(rg_layout)
        self.layout.addWidget(rg_group)

        # VM Sizing section
        vm_group = QGroupBox("VM Sizing")
        vm_layout = QFormLayout()

        self.fw_vm_size = QComboBox()
        self.fw_vm_size.addItems([
            "Standard_D3_v2 (4 vCPU, 14GB - Eval)",
            "Standard_D4_v2 (8 vCPU, 28GB - Small)",
            "Standard_D5_v2 (16 vCPU, 56GB - Medium)",
            "Standard_D8s_v4 (8 vCPU, 32GB - Production)",
            "Standard_D16s_v4 (16 vCPU, 64GB - Large)",
        ])
        vm_layout.addRow("Firewall VM Size:", self.fw_vm_size)

        self.panorama_vm_size = QComboBox()
        self.panorama_vm_size.addItems([
            "Standard_D4_v2 (8 vCPU, 28GB - Eval)",
            "Standard_D5_v2 (16 vCPU, 56GB - Production)",
        ])
        vm_layout.addRow("Panorama VM Size:", self.panorama_vm_size)

        self.trust_vm_size = QComboBox()
        self.trust_vm_size.addItems([
            "Standard_B2s (2 vCPU, 4GB - Minimal)",
            "Standard_D2s_v3 (2 vCPU, 8GB - Standard)",
            "Standard_D4s_v3 (4 vCPU, 16GB - Enhanced)",
        ])
        vm_layout.addRow("Trust Network VMs:", self.trust_vm_size)

        vm_group.setLayout(vm_layout)
        self.layout.addWidget(vm_group)

        # Network section
        net_group = QGroupBox("Virtual Network")
        net_layout = QFormLayout()

        self.vnet_cidr = QLineEdit()
        self.vnet_cidr.setPlaceholderText("10.100.0.0/16")
        self.vnet_cidr.setText("10.100.0.0/16")
        net_layout.addRow("VNet Address Space:", self.vnet_cidr)

        self.mgmt_subnet = QLineEdit()
        self.mgmt_subnet.setText("10.100.0.0/24")
        net_layout.addRow("Management Subnet:", self.mgmt_subnet)

        self.untrust_subnet = QLineEdit()
        self.untrust_subnet.setText("10.100.1.0/24")
        net_layout.addRow("Untrust Subnet:", self.untrust_subnet)

        self.trust_subnet = QLineEdit()
        self.trust_subnet.setText("10.100.2.0/24")
        net_layout.addRow("Trust Subnet:", self.trust_subnet)

        net_group.setLayout(net_layout)
        self.layout.addWidget(net_group)

        self.layout.addStretch()
        self._add_buttons()

    def _update_rg_preview(self):
        """Update resource group name preview."""
        customer = self.customer_name.text().lower().strip()
        loc = self.location.currentText()
        if customer and loc:
            self.rg_preview.setText(f"{customer}-{loc}-pov-rg")
        else:
            self.rg_preview.setText("(enter customer name)")

    def _load_config(self):
        if self.config:
            self.customer_name.setText(self.config.get('customer_name', ''))
            loc = self.config.get('location', 'eastus')
            idx = self.location.findText(loc)
            if idx >= 0:
                self.location.setCurrentIndex(idx)
            self.vnet_cidr.setText(self.config.get('vnet_cidr', '10.100.0.0/16'))
            self.mgmt_subnet.setText(self.config.get('mgmt_subnet', '10.100.0.0/24'))
            self.untrust_subnet.setText(self.config.get('untrust_subnet', '10.100.1.0/24'))
            self.trust_subnet.setText(self.config.get('trust_subnet', '10.100.2.0/24'))
        self._update_rg_preview()

    def _save_config(self) -> Dict[str, Any]:
        return {
            'customer_name': self.customer_name.text().lower().strip(),
            'location': self.location.currentText(),
            'fw_vm_size': self.fw_vm_size.currentText().split()[0],
            'panorama_vm_size': self.panorama_vm_size.currentText().split()[0],
            'trust_vm_size': self.trust_vm_size.currentText().split()[0],
            'vnet_cidr': self.vnet_cidr.text(),
            'mgmt_subnet': self.mgmt_subnet.text(),
            'untrust_subnet': self.untrust_subnet.text(),
            'trust_subnet': self.trust_subnet.text(),
        }


class DeviceConfigDialog(POVConfigDialog):
    """Dialog for Initial Device Configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Initial Device Configuration", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Initial Device Configuration</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure DNS/NTP, zones, interfaces, and device management settings.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # DNS/NTP section
        dns_group = QGroupBox("DNS & NTP Configuration")
        dns_layout = QFormLayout()

        self.dns_primary = QLineEdit()
        self.dns_primary.setText("8.8.8.8")
        dns_layout.addRow("Primary DNS:", self.dns_primary)

        self.dns_secondary = QLineEdit()
        self.dns_secondary.setText("8.8.4.4")
        dns_layout.addRow("Secondary DNS:", self.dns_secondary)

        self.ntp_primary = QLineEdit()
        self.ntp_primary.setText("pool.ntp.org")
        dns_layout.addRow("Primary NTP:", self.ntp_primary)

        self.ntp_secondary = QLineEdit()
        self.ntp_secondary.setText("time.google.com")
        dns_layout.addRow("Secondary NTP:", self.ntp_secondary)

        dns_group.setLayout(dns_layout)
        self.layout.addWidget(dns_group)

        # Zones section
        zones_group = QGroupBox("Security Zones")
        zones_layout = QFormLayout()

        self.trust_zone = QLineEdit()
        self.trust_zone.setText("trust")
        zones_layout.addRow("Trust Zone Name:", self.trust_zone)

        self.untrust_zone = QLineEdit()
        self.untrust_zone.setText("untrust")
        zones_layout.addRow("Untrust Zone Name:", self.untrust_zone)

        self.mgmt_zone = QLineEdit()
        self.mgmt_zone.setText("management")
        zones_layout.addRow("Management Zone:", self.mgmt_zone)

        zones_group.setLayout(zones_layout)
        self.layout.addWidget(zones_group)

        # Device Management section
        mgmt_group = QGroupBox("Device Management")
        mgmt_layout = QFormLayout()

        self.hostname_prefix = QLineEdit()
        self.hostname_prefix.setPlaceholderText("e.g., fw")
        self.hostname_prefix.setText("fw")
        mgmt_layout.addRow("Hostname Prefix:", self.hostname_prefix)

        self.admin_user = QLineEdit()
        self.admin_user.setText("admin")
        mgmt_layout.addRow("Admin Username:", self.admin_user)

        self.enable_ssh = QCheckBox("Enable SSH access")
        self.enable_ssh.setChecked(True)
        mgmt_layout.addRow("", self.enable_ssh)

        self.enable_https = QCheckBox("Enable HTTPS management")
        self.enable_https.setChecked(True)
        mgmt_layout.addRow("", self.enable_https)

        mgmt_group.setLayout(mgmt_layout)
        self.layout.addWidget(mgmt_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.dns_primary.setText(self.config.get('dns_primary', '8.8.8.8'))
            self.dns_secondary.setText(self.config.get('dns_secondary', '8.8.4.4'))
            self.ntp_primary.setText(self.config.get('ntp_primary', 'pool.ntp.org'))
            self.ntp_secondary.setText(self.config.get('ntp_secondary', 'time.google.com'))
            self.trust_zone.setText(self.config.get('trust_zone', 'trust'))
            self.untrust_zone.setText(self.config.get('untrust_zone', 'untrust'))
            self.hostname_prefix.setText(self.config.get('hostname_prefix', 'fw'))
            self.admin_user.setText(self.config.get('admin_user', 'admin'))
            self.enable_ssh.setChecked(self.config.get('enable_ssh', True))
            self.enable_https.setChecked(self.config.get('enable_https', True))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'dns_primary': self.dns_primary.text(),
            'dns_secondary': self.dns_secondary.text(),
            'ntp_primary': self.ntp_primary.text(),
            'ntp_secondary': self.ntp_secondary.text(),
            'trust_zone': self.trust_zone.text(),
            'untrust_zone': self.untrust_zone.text(),
            'mgmt_zone': self.mgmt_zone.text(),
            'hostname_prefix': self.hostname_prefix.text(),
            'admin_user': self.admin_user.text(),
            'enable_ssh': self.enable_ssh.isChecked(),
            'enable_https': self.enable_https.isChecked(),
        }


class PolicyObjectsDialog(POVConfigDialog):
    """Dialog for Policy and Objects configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Policy and Objects", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Policy and Objects</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure default objects, security policies, NAT, and decryption settings.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Default Objects section
        obj_group = QGroupBox("Default Objects")
        obj_layout = QVBoxLayout()

        self.create_rfc1918 = QCheckBox("Create RFC1918 address objects (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)")
        self.create_rfc1918.setChecked(True)
        obj_layout.addWidget(self.create_rfc1918)

        self.create_dns_objects = QCheckBox("Create DNS server address objects")
        self.create_dns_objects.setChecked(True)
        obj_layout.addWidget(self.create_dns_objects)

        self.create_app_groups = QCheckBox("Create common application groups (web-browsing, ssl, dns)")
        self.create_app_groups.setChecked(True)
        obj_layout.addWidget(self.create_app_groups)

        obj_group.setLayout(obj_layout)
        self.layout.addWidget(obj_group)

        # Security Policy section
        policy_group = QGroupBox("Outbound Internet Policy")
        policy_layout = QVBoxLayout()

        self.allow_outbound = QCheckBox("Create allow-outbound rule (trust to untrust)")
        self.allow_outbound.setChecked(True)
        policy_layout.addWidget(self.allow_outbound)

        self.block_quic = QCheckBox("Create block-quic rule (force HTTPS inspection)")
        self.block_quic.setChecked(True)
        policy_layout.addWidget(self.block_quic)

        self.log_at_session_end = QCheckBox("Enable logging at session end")
        self.log_at_session_end.setChecked(True)
        policy_layout.addWidget(self.log_at_session_end)

        policy_group.setLayout(policy_layout)
        self.layout.addWidget(policy_group)

        # NAT section
        nat_group = QGroupBox("NAT Configuration")
        nat_layout = QVBoxLayout()

        self.create_outbound_nat = QCheckBox("Create outbound NAT rule (trust to untrust)")
        self.create_outbound_nat.setChecked(True)
        nat_layout.addWidget(self.create_outbound_nat)

        nat_group.setLayout(nat_layout)
        self.layout.addWidget(nat_group)

        # Decryption section
        decrypt_group = QGroupBox("Decryption")
        decrypt_layout = QVBoxLayout()

        self.enable_decryption = QCheckBox("Enable SSL decryption for outbound traffic")
        self.enable_decryption.setChecked(False)
        decrypt_layout.addWidget(self.enable_decryption)

        self.exclude_financial = QCheckBox("Exclude financial/healthcare categories from decryption")
        self.exclude_financial.setChecked(True)
        decrypt_layout.addWidget(self.exclude_financial)

        decrypt_group.setLayout(decrypt_layout)
        self.layout.addWidget(decrypt_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.create_rfc1918.setChecked(self.config.get('create_rfc1918', True))
            self.create_dns_objects.setChecked(self.config.get('create_dns_objects', True))
            self.create_app_groups.setChecked(self.config.get('create_app_groups', True))
            self.allow_outbound.setChecked(self.config.get('allow_outbound', True))
            self.block_quic.setChecked(self.config.get('block_quic', True))
            self.log_at_session_end.setChecked(self.config.get('log_at_session_end', True))
            self.create_outbound_nat.setChecked(self.config.get('create_outbound_nat', True))
            self.enable_decryption.setChecked(self.config.get('enable_decryption', False))
            self.exclude_financial.setChecked(self.config.get('exclude_financial', True))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'create_rfc1918': self.create_rfc1918.isChecked(),
            'create_dns_objects': self.create_dns_objects.isChecked(),
            'create_app_groups': self.create_app_groups.isChecked(),
            'allow_outbound': self.allow_outbound.isChecked(),
            'block_quic': self.block_quic.isChecked(),
            'log_at_session_end': self.log_at_session_end.isChecked(),
            'create_outbound_nat': self.create_outbound_nat.isChecked(),
            'enable_decryption': self.enable_decryption.isChecked(),
            'exclude_financial': self.exclude_financial.isChecked(),
        }


class TrustDevicesDialog(POVConfigDialog):
    """Dialog for Trust Network Devices configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Trust Network Devices", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Trust Network Devices</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure VMs and systems deployed on the trust network for testing.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # User VM section
        user_group = QGroupBox("User VM (Client Testing)")
        user_layout = QFormLayout()

        self.deploy_user_vm = QCheckBox("Deploy User VM")
        self.deploy_user_vm.setChecked(True)
        user_layout.addRow("", self.deploy_user_vm)

        self.user_vm_os = QComboBox()
        self.user_vm_os.addItems(["Windows 11", "Windows 10", "Ubuntu 22.04", "Ubuntu 20.04"])
        user_layout.addRow("Operating System:", self.user_vm_os)

        self.user_vm_name = QLineEdit()
        self.user_vm_name.setText("user-vm")
        user_layout.addRow("VM Name:", self.user_vm_name)

        user_group.setLayout(user_layout)
        self.layout.addWidget(user_group)

        # Server VM section
        server_group = QGroupBox("Server VM (Application Testing)")
        server_layout = QFormLayout()

        self.deploy_server_vm = QCheckBox("Deploy Server VM")
        self.deploy_server_vm.setChecked(True)
        server_layout.addRow("", self.deploy_server_vm)

        self.server_vm_os = QComboBox()
        self.server_vm_os.addItems(["Ubuntu 22.04 LTS", "Ubuntu 20.04 LTS", "Windows Server 2022"])
        server_layout.addRow("Operating System:", self.server_vm_os)

        self.server_vm_name = QLineEdit()
        self.server_vm_name.setText("server-vm")
        server_layout.addRow("VM Name:", self.server_vm_name)

        self.install_web_server = QCheckBox("Install web server (nginx)")
        self.install_web_server.setChecked(True)
        server_layout.addRow("", self.install_web_server)

        server_group.setLayout(server_layout)
        self.layout.addWidget(server_group)

        # Panorama section
        panorama_group = QGroupBox("Panorama System")
        panorama_layout = QFormLayout()

        self.deploy_panorama = QCheckBox("Deploy Panorama")
        self.deploy_panorama.setChecked(False)
        panorama_layout.addRow("", self.deploy_panorama)

        self.panorama_mode = QComboBox()
        self.panorama_mode.addItems(["Management Only", "Log Collector", "Management + Log Collector"])
        panorama_layout.addRow("Panorama Mode:", self.panorama_mode)

        self.panorama_name = QLineEdit()
        self.panorama_name.setText("panorama")
        panorama_layout.addRow("Hostname:", self.panorama_name)

        panorama_group.setLayout(panorama_layout)
        self.layout.addWidget(panorama_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.deploy_user_vm.setChecked(self.config.get('deploy_user_vm', True))
            self.user_vm_name.setText(self.config.get('user_vm_name', 'user-vm'))
            self.deploy_server_vm.setChecked(self.config.get('deploy_server_vm', True))
            self.server_vm_name.setText(self.config.get('server_vm_name', 'server-vm'))
            self.install_web_server.setChecked(self.config.get('install_web_server', True))
            self.deploy_panorama.setChecked(self.config.get('deploy_panorama', False))
            self.panorama_name.setText(self.config.get('panorama_name', 'panorama'))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'deploy_user_vm': self.deploy_user_vm.isChecked(),
            'user_vm_os': self.user_vm_os.currentText(),
            'user_vm_name': self.user_vm_name.text(),
            'deploy_server_vm': self.deploy_server_vm.isChecked(),
            'server_vm_os': self.server_vm_os.currentText(),
            'server_vm_name': self.server_vm_name.text(),
            'install_web_server': self.install_web_server.isChecked(),
            'deploy_panorama': self.deploy_panorama.isChecked(),
            'panorama_mode': self.panorama_mode.currentText(),
            'panorama_name': self.panorama_name.text(),
        }


class ExternalConnectivityDialog(POVConfigDialog):
    """Dialog for External Connectivity (VPNs) configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("External Connectivity (VPNs)", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>External Connectivity (VPNs)</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure VPN tunnels and external connectivity options.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Remote Network Tunnel section
        rn_group = QGroupBox("Remote Network / Service Connection Tunnel")
        rn_layout = QFormLayout()

        self.enable_rn_tunnel = QCheckBox("Enable Remote Network IPSec Tunnel")
        self.enable_rn_tunnel.setChecked(False)
        rn_layout.addRow("", self.enable_rn_tunnel)

        self.rn_peer_ip = QLineEdit()
        self.rn_peer_ip.setPlaceholderText("Peer IP address")
        rn_layout.addRow("Peer IP:", self.rn_peer_ip)

        self.rn_local_id = QLineEdit()
        self.rn_local_id.setPlaceholderText("Local IKE ID")
        rn_layout.addRow("Local IKE ID:", self.rn_local_id)

        self.rn_peer_id = QLineEdit()
        self.rn_peer_id.setPlaceholderText("Peer IKE ID")
        rn_layout.addRow("Peer IKE ID:", self.rn_peer_id)

        rn_group.setLayout(rn_layout)
        self.layout.addWidget(rn_group)

        # Other VM section
        other_group = QGroupBox("Other VPN Endpoint VM")
        other_layout = QFormLayout()

        self.deploy_vpn_vm = QCheckBox("Deploy VPN endpoint VM (for testing)")
        self.deploy_vpn_vm.setChecked(False)
        other_layout.addRow("", self.deploy_vpn_vm)

        self.vpn_vm_type = QComboBox()
        self.vpn_vm_type.addItems(["StrongSwan (Ubuntu)", "OpenVPN (Ubuntu)", "Windows RRAS"])
        other_layout.addRow("VPN Software:", self.vpn_vm_type)

        other_group.setLayout(other_layout)
        self.layout.addWidget(other_group)

        # User-ID section
        userid_group = QGroupBox("User-ID Sync")
        userid_layout = QFormLayout()

        self.enable_userid = QCheckBox("Enable User-ID agent sync")
        self.enable_userid.setChecked(False)
        userid_layout.addRow("", self.enable_userid)

        self.userid_source = QComboBox()
        self.userid_source.addItems(["Active Directory", "Syslog", "XML API"])
        userid_layout.addRow("User-ID Source:", self.userid_source)

        userid_group.setLayout(userid_layout)
        self.layout.addWidget(userid_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.enable_rn_tunnel.setChecked(self.config.get('enable_rn_tunnel', False))
            self.rn_peer_ip.setText(self.config.get('rn_peer_ip', ''))
            self.rn_local_id.setText(self.config.get('rn_local_id', ''))
            self.rn_peer_id.setText(self.config.get('rn_peer_id', ''))
            self.deploy_vpn_vm.setChecked(self.config.get('deploy_vpn_vm', False))
            self.enable_userid.setChecked(self.config.get('enable_userid', False))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'enable_rn_tunnel': self.enable_rn_tunnel.isChecked(),
            'rn_peer_ip': self.rn_peer_ip.text(),
            'rn_local_id': self.rn_local_id.text(),
            'rn_peer_id': self.rn_peer_id.text(),
            'deploy_vpn_vm': self.deploy_vpn_vm.isChecked(),
            'vpn_vm_type': self.vpn_vm_type.currentText(),
            'enable_userid': self.enable_userid.isChecked(),
            'userid_source': self.userid_source.currentText(),
        }


class CloudSecurityDialog(POVConfigDialog):
    """Dialog for Cloud Security Configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Cloud Security Configuration", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Cloud Security Configuration</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure cloud security groups, firewall access, and credentials.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Management Access section
        mgmt_group = QGroupBox("Firewall Management Access")
        mgmt_layout = QFormLayout()

        self.mgmt_source_ips = QLineEdit()
        self.mgmt_source_ips.setPlaceholderText("Comma-separated IPs or CIDRs")
        self.mgmt_source_ips.setText("0.0.0.0/0")
        mgmt_layout.addRow("Allowed Source IPs:", self.mgmt_source_ips)

        self.allow_ssh = QCheckBox("Allow SSH (port 22)")
        self.allow_ssh.setChecked(True)
        mgmt_layout.addRow("", self.allow_ssh)

        self.allow_https = QCheckBox("Allow HTTPS (port 443)")
        self.allow_https.setChecked(True)
        mgmt_layout.addRow("", self.allow_https)

        mgmt_group.setLayout(mgmt_layout)
        self.layout.addWidget(mgmt_group)

        # NSG section
        nsg_group = QGroupBox("Network Security Groups")
        nsg_layout = QVBoxLayout()

        self.create_mgmt_nsg = QCheckBox("Create Management NSG")
        self.create_mgmt_nsg.setChecked(True)
        nsg_layout.addWidget(self.create_mgmt_nsg)

        self.create_untrust_nsg = QCheckBox("Create Untrust NSG (allow all inbound)")
        self.create_untrust_nsg.setChecked(True)
        nsg_layout.addWidget(self.create_untrust_nsg)

        self.create_trust_nsg = QCheckBox("Create Trust NSG (internal traffic)")
        self.create_trust_nsg.setChecked(True)
        nsg_layout.addWidget(self.create_trust_nsg)

        nsg_group.setLayout(nsg_layout)
        self.layout.addWidget(nsg_group)

        # Credentials section
        creds_group = QGroupBox("Access Credentials")
        creds_layout = QFormLayout()

        creds_info = QLabel(
            "Credentials will be auto-generated during deployment. "
            "You can specify custom values or leave blank for auto-generation."
        )
        creds_info.setWordWrap(True)
        creds_info.setStyleSheet("color: #666; font-size: 11px;")
        creds_layout.addRow(creds_info)

        self.custom_admin_password = QLineEdit()
        self.custom_admin_password.setPlaceholderText("Leave blank for auto-generated")
        self.custom_admin_password.setEchoMode(QLineEdit.EchoMode.Password)
        creds_layout.addRow("Admin Password:", self.custom_admin_password)

        self.store_in_keyvault = QCheckBox("Store credentials in Azure Key Vault")
        self.store_in_keyvault.setChecked(False)
        creds_layout.addRow("", self.store_in_keyvault)

        creds_group.setLayout(creds_layout)
        self.layout.addWidget(creds_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.mgmt_source_ips.setText(self.config.get('mgmt_source_ips', '0.0.0.0/0'))
            self.allow_ssh.setChecked(self.config.get('allow_ssh', True))
            self.allow_https.setChecked(self.config.get('allow_https', True))
            self.create_mgmt_nsg.setChecked(self.config.get('create_mgmt_nsg', True))
            self.create_untrust_nsg.setChecked(self.config.get('create_untrust_nsg', True))
            self.create_trust_nsg.setChecked(self.config.get('create_trust_nsg', True))
            self.store_in_keyvault.setChecked(self.config.get('store_in_keyvault', False))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'mgmt_source_ips': self.mgmt_source_ips.text(),
            'allow_ssh': self.allow_ssh.isChecked(),
            'allow_https': self.allow_https.isChecked(),
            'create_mgmt_nsg': self.create_mgmt_nsg.isChecked(),
            'create_untrust_nsg': self.create_untrust_nsg.isChecked(),
            'create_trust_nsg': self.create_trust_nsg.isChecked(),
            'custom_admin_password': self.custom_admin_password.text(),
            'store_in_keyvault': self.store_in_keyvault.isChecked(),
        }


# =============================================================================
# USE CASES DIALOGS
# =============================================================================

class MobileUsersDialog(POVConfigDialog):
    """Dialog for Mobile Users (GlobalProtect) configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Connect & Secure Mobile Users", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Connect & Secure Mobile Users</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure GlobalProtect VPN for remote employee access.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Enable section
        enable_group = QGroupBox("Use Case Status")
        enable_layout = QVBoxLayout()

        self.enable_use_case = QCheckBox("Enable Mobile Users Use Case")
        self.enable_use_case.setChecked(True)
        enable_layout.addWidget(self.enable_use_case)

        enable_group.setLayout(enable_layout)
        self.layout.addWidget(enable_group)

        # GlobalProtect section
        gp_group = QGroupBox("GlobalProtect Configuration")
        gp_layout = QFormLayout()

        self.portal_address = QLineEdit()
        self.portal_address.setPlaceholderText("portal.company.com")
        gp_layout.addRow("Portal Address:", self.portal_address)

        self.gateway_address = QLineEdit()
        self.gateway_address.setPlaceholderText("gateway.company.com")
        gp_layout.addRow("Gateway Address:", self.gateway_address)

        self.auth_profile = QComboBox()
        self.auth_profile.addItems(["Local Database", "SAML", "LDAP", "RADIUS"])
        gp_layout.addRow("Authentication:", self.auth_profile)

        gp_group.setLayout(gp_layout)
        self.layout.addWidget(gp_group)

        # Options section
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.always_on = QCheckBox("Enable Always-On VPN")
        self.always_on.setChecked(False)
        options_layout.addWidget(self.always_on)

        self.split_tunnel = QCheckBox("Enable Split Tunneling")
        self.split_tunnel.setChecked(True)
        options_layout.addWidget(self.split_tunnel)

        self.hip_check = QCheckBox("Enable HIP (Host Information Profile) checks")
        self.hip_check.setChecked(False)
        options_layout.addWidget(self.hip_check)

        options_group.setLayout(options_layout)
        self.layout.addWidget(options_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.enable_use_case.setChecked(self.config.get('enabled', True))
            self.portal_address.setText(self.config.get('portal_address', ''))
            self.gateway_address.setText(self.config.get('gateway_address', ''))
            self.always_on.setChecked(self.config.get('always_on', False))
            self.split_tunnel.setChecked(self.config.get('split_tunnel', True))
            self.hip_check.setChecked(self.config.get('hip_check', False))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'enabled': self.enable_use_case.isChecked(),
            'portal_address': self.portal_address.text(),
            'gateway_address': self.gateway_address.text(),
            'auth_profile': self.auth_profile.currentText(),
            'always_on': self.always_on.isChecked(),
            'split_tunnel': self.split_tunnel.isChecked(),
            'hip_check': self.hip_check.isChecked(),
        }


class ProxyUsersDialog(POVConfigDialog):
    """Dialog for Proxy Users (Explicit Proxy) configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Connect & Secure Proxy Users", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Connect & Secure Proxy Users</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure Explicit Proxy for browser-based secure access.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Enable section
        enable_group = QGroupBox("Use Case Status")
        enable_layout = QVBoxLayout()

        self.enable_use_case = QCheckBox("Enable Proxy Users Use Case")
        self.enable_use_case.setChecked(False)
        enable_layout.addWidget(self.enable_use_case)

        enable_group.setLayout(enable_layout)
        self.layout.addWidget(enable_group)

        # Proxy section
        proxy_group = QGroupBox("Explicit Proxy Configuration")
        proxy_layout = QFormLayout()

        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        self.proxy_port.setValue(8080)
        proxy_layout.addRow("Proxy Port:", self.proxy_port)

        self.auth_required = QCheckBox("Require Authentication")
        self.auth_required.setChecked(True)
        proxy_layout.addRow("", self.auth_required)

        self.pac_file = QCheckBox("Generate PAC file")
        self.pac_file.setChecked(True)
        proxy_layout.addRow("", self.pac_file)

        proxy_group.setLayout(proxy_layout)
        self.layout.addWidget(proxy_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.enable_use_case.setChecked(self.config.get('enabled', False))
            self.proxy_port.setValue(self.config.get('proxy_port', 8080))
            self.auth_required.setChecked(self.config.get('auth_required', True))
            self.pac_file.setChecked(self.config.get('pac_file', True))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'enabled': self.enable_use_case.isChecked(),
            'proxy_port': self.proxy_port.value(),
            'auth_required': self.auth_required.isChecked(),
            'pac_file': self.pac_file.isChecked(),
        }


class PrivateAppAccessDialog(POVConfigDialog):
    """Dialog for Private App Access (ZTNA) configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Private App Access", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Private App Access (ZTNA)</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure Zero Trust Network Access for private applications.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Enable section
        enable_group = QGroupBox("Use Case Status")
        enable_layout = QVBoxLayout()

        self.enable_use_case = QCheckBox("Enable Private App Access Use Case")
        self.enable_use_case.setChecked(False)
        enable_layout.addWidget(self.enable_use_case)

        enable_group.setLayout(enable_layout)
        self.layout.addWidget(enable_group)

        # ZTNA section
        ztna_group = QGroupBox("ZTNA Configuration")
        ztna_layout = QVBoxLayout()

        self.use_connector = QCheckBox("Deploy ZTNA Connector")
        self.use_connector.setChecked(True)
        ztna_layout.addWidget(self.use_connector)

        self.use_service_connection = QCheckBox("Use Service Connection")
        self.use_service_connection.setChecked(False)
        ztna_layout.addWidget(self.use_service_connection)

        ztna_group.setLayout(ztna_layout)
        self.layout.addWidget(ztna_group)

        # Apps section
        apps_group = QGroupBox("Sample Applications")
        apps_layout = QVBoxLayout()

        self.add_web_app = QCheckBox("Add sample web application")
        self.add_web_app.setChecked(True)
        apps_layout.addWidget(self.add_web_app)

        self.add_ssh_app = QCheckBox("Add sample SSH application")
        self.add_ssh_app.setChecked(True)
        apps_layout.addWidget(self.add_ssh_app)

        self.add_rdp_app = QCheckBox("Add sample RDP application")
        self.add_rdp_app.setChecked(False)
        apps_layout.addWidget(self.add_rdp_app)

        apps_group.setLayout(apps_layout)
        self.layout.addWidget(apps_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.enable_use_case.setChecked(self.config.get('enabled', False))
            self.use_connector.setChecked(self.config.get('use_connector', True))
            self.use_service_connection.setChecked(self.config.get('use_service_connection', False))
            self.add_web_app.setChecked(self.config.get('add_web_app', True))
            self.add_ssh_app.setChecked(self.config.get('add_ssh_app', True))
            self.add_rdp_app.setChecked(self.config.get('add_rdp_app', False))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'enabled': self.enable_use_case.isChecked(),
            'use_connector': self.use_connector.isChecked(),
            'use_service_connection': self.use_service_connection.isChecked(),
            'add_web_app': self.add_web_app.isChecked(),
            'add_ssh_app': self.add_ssh_app.isChecked(),
            'add_rdp_app': self.add_rdp_app.isChecked(),
        }


class RemoteBranchDialog(POVConfigDialog):
    """Dialog for Remote Branch configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Connect Remote Branch", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Connect Remote Branch</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure Remote Network IPSec connectivity for branch offices.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Enable section
        enable_group = QGroupBox("Use Case Status")
        enable_layout = QVBoxLayout()

        self.enable_use_case = QCheckBox("Enable Remote Branch Use Case")
        self.enable_use_case.setChecked(False)
        enable_layout.addWidget(self.enable_use_case)

        enable_group.setLayout(enable_layout)
        self.layout.addWidget(enable_group)

        # Branch section
        branch_group = QGroupBox("Branch Configuration")
        branch_layout = QFormLayout()

        self.branch_count = QSpinBox()
        self.branch_count.setRange(1, 10)
        self.branch_count.setValue(1)
        branch_layout.addRow("Number of Branches:", self.branch_count)

        self.branch_bandwidth = QComboBox()
        self.branch_bandwidth.addItems(["25 Mbps", "50 Mbps", "100 Mbps", "200 Mbps", "500 Mbps"])
        branch_layout.addRow("Bandwidth per Branch:", self.branch_bandwidth)

        branch_group.setLayout(branch_layout)
        self.layout.addWidget(branch_group)

        # Options section
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.sdwan_integration = QCheckBox("Enable SD-WAN integration")
        self.sdwan_integration.setChecked(False)
        options_layout.addWidget(self.sdwan_integration)

        self.bgp_routing = QCheckBox("Enable BGP routing")
        self.bgp_routing.setChecked(False)
        options_layout.addWidget(self.bgp_routing)

        options_group.setLayout(options_layout)
        self.layout.addWidget(options_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.enable_use_case.setChecked(self.config.get('enabled', False))
            self.branch_count.setValue(self.config.get('branch_count', 1))
            self.sdwan_integration.setChecked(self.config.get('sdwan_integration', False))
            self.bgp_routing.setChecked(self.config.get('bgp_routing', False))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'enabled': self.enable_use_case.isChecked(),
            'branch_count': self.branch_count.value(),
            'branch_bandwidth': self.branch_bandwidth.currentText(),
            'sdwan_integration': self.sdwan_integration.isChecked(),
            'bgp_routing': self.bgp_routing.isChecked(),
        }


class AIOpsADEMDialog(POVConfigDialog):
    """Dialog for AIOPS-ADEM configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("AIOPS-ADEM", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>AIOPS - Digital Experience Management</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure Autonomous Digital Experience Management for visibility and troubleshooting.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Enable section
        enable_group = QGroupBox("Use Case Status")
        enable_layout = QVBoxLayout()

        self.enable_use_case = QCheckBox("Enable AIOPS-ADEM Use Case")
        self.enable_use_case.setChecked(False)
        enable_layout.addWidget(self.enable_use_case)

        enable_group.setLayout(enable_layout)
        self.layout.addWidget(enable_group)

        # ADEM section
        adem_group = QGroupBox("ADEM Configuration")
        adem_layout = QVBoxLayout()

        self.endpoint_agent = QCheckBox("Enable Endpoint Agent monitoring")
        self.endpoint_agent.setChecked(True)
        adem_layout.addWidget(self.endpoint_agent)

        self.synthetic_tests = QCheckBox("Enable Synthetic Tests")
        self.synthetic_tests.setChecked(True)
        adem_layout.addWidget(self.synthetic_tests)

        self.application_tests = QCheckBox("Enable Application Tests")
        self.application_tests.setChecked(True)
        adem_layout.addWidget(self.application_tests)

        adem_group.setLayout(adem_layout)
        self.layout.addWidget(adem_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.enable_use_case.setChecked(self.config.get('enabled', False))
            self.endpoint_agent.setChecked(self.config.get('endpoint_agent', True))
            self.synthetic_tests.setChecked(self.config.get('synthetic_tests', True))
            self.application_tests.setChecked(self.config.get('application_tests', True))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'enabled': self.enable_use_case.isChecked(),
            'endpoint_agent': self.endpoint_agent.isChecked(),
            'synthetic_tests': self.synthetic_tests.isChecked(),
            'application_tests': self.application_tests.isChecked(),
        }


class AppAccelerationDialog(POVConfigDialog):
    """Dialog for App Acceleration configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("App Acceleration", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Application Acceleration</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure SaaS and private application optimization.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Enable section
        enable_group = QGroupBox("Use Case Status")
        enable_layout = QVBoxLayout()

        self.enable_use_case = QCheckBox("Enable App Acceleration Use Case")
        self.enable_use_case.setChecked(False)
        enable_layout.addWidget(self.enable_use_case)

        enable_group.setLayout(enable_layout)
        self.layout.addWidget(enable_group)

        # Acceleration section
        accel_group = QGroupBox("Acceleration Configuration")
        accel_layout = QVBoxLayout()

        self.saas_acceleration = QCheckBox("Enable SaaS application acceleration")
        self.saas_acceleration.setChecked(True)
        accel_layout.addWidget(self.saas_acceleration)

        self.private_acceleration = QCheckBox("Enable private application acceleration")
        self.private_acceleration.setChecked(True)
        accel_layout.addWidget(self.private_acceleration)

        accel_group.setLayout(accel_layout)
        self.layout.addWidget(accel_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.enable_use_case.setChecked(self.config.get('enabled', False))
            self.saas_acceleration.setChecked(self.config.get('saas_acceleration', True))
            self.private_acceleration.setChecked(self.config.get('private_acceleration', True))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'enabled': self.enable_use_case.isChecked(),
            'saas_acceleration': self.saas_acceleration.isChecked(),
            'private_acceleration': self.private_acceleration.isChecked(),
        }


class RBIDialog(POVConfigDialog):
    """Dialog for Remote Browser Isolation configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Remote Browser Isolation", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Remote Browser Isolation</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure browser isolation for high-risk browsing scenarios.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Enable section
        enable_group = QGroupBox("Use Case Status")
        enable_layout = QVBoxLayout()

        self.enable_use_case = QCheckBox("Enable Remote Browser Isolation Use Case")
        self.enable_use_case.setChecked(False)
        enable_layout.addWidget(self.enable_use_case)

        enable_group.setLayout(enable_layout)
        self.layout.addWidget(enable_group)

        # RBI section
        rbi_group = QGroupBox("RBI Configuration")
        rbi_layout = QVBoxLayout()

        self.isolate_uncategorized = QCheckBox("Isolate uncategorized websites")
        self.isolate_uncategorized.setChecked(True)
        rbi_layout.addWidget(self.isolate_uncategorized)

        self.isolate_risky = QCheckBox("Isolate risky URL categories")
        self.isolate_risky.setChecked(True)
        rbi_layout.addWidget(self.isolate_risky)

        self.block_downloads = QCheckBox("Block file downloads from isolated sessions")
        self.block_downloads.setChecked(False)
        rbi_layout.addWidget(self.block_downloads)

        rbi_group.setLayout(rbi_layout)
        self.layout.addWidget(rbi_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.enable_use_case.setChecked(self.config.get('enabled', False))
            self.isolate_uncategorized.setChecked(self.config.get('isolate_uncategorized', True))
            self.isolate_risky.setChecked(self.config.get('isolate_risky', True))
            self.block_downloads.setChecked(self.config.get('block_downloads', False))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'enabled': self.enable_use_case.isChecked(),
            'isolate_uncategorized': self.isolate_uncategorized.isChecked(),
            'isolate_risky': self.isolate_risky.isChecked(),
            'block_downloads': self.block_downloads.isChecked(),
        }


class PABrowserDialog(POVConfigDialog):
    """Dialog for Prisma Access Browser configuration."""

    def __init__(self, config: Dict[str, Any] = None, parent=None):
        super().__init__("Prisma Access Browser", config, parent)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        title = QLabel("<h3>Prisma Access Browser</h3>")
        self.layout.addWidget(title)

        info = QLabel("Configure enterprise browser with built-in security features.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        self.layout.addWidget(info)

        # Enable section
        enable_group = QGroupBox("Use Case Status")
        enable_layout = QVBoxLayout()

        self.enable_use_case = QCheckBox("Enable Prisma Access Browser Use Case")
        self.enable_use_case.setChecked(False)
        enable_layout.addWidget(self.enable_use_case)

        enable_group.setLayout(enable_layout)
        self.layout.addWidget(enable_group)

        # PAB section
        pab_group = QGroupBox("Browser Configuration")
        pab_layout = QVBoxLayout()

        self.enable_dlp = QCheckBox("Enable DLP (Data Loss Prevention)")
        self.enable_dlp.setChecked(True)
        pab_layout.addWidget(self.enable_dlp)

        self.enable_threat_prevention = QCheckBox("Enable Threat Prevention")
        self.enable_threat_prevention.setChecked(True)
        pab_layout.addWidget(self.enable_threat_prevention)

        self.enable_compliance = QCheckBox("Enable Compliance Controls")
        self.enable_compliance.setChecked(True)
        pab_layout.addWidget(self.enable_compliance)

        pab_group.setLayout(pab_layout)
        self.layout.addWidget(pab_group)

        self.layout.addStretch()
        self._add_buttons()

    def _load_config(self):
        if self.config:
            self.enable_use_case.setChecked(self.config.get('enabled', False))
            self.enable_dlp.setChecked(self.config.get('enable_dlp', True))
            self.enable_threat_prevention.setChecked(self.config.get('enable_threat_prevention', True))
            self.enable_compliance.setChecked(self.config.get('enable_compliance', True))

    def _save_config(self) -> Dict[str, Any]:
        return {
            'enabled': self.enable_use_case.isChecked(),
            'enable_dlp': self.enable_dlp.isChecked(),
            'enable_threat_prevention': self.enable_threat_prevention.isChecked(),
            'enable_compliance': self.enable_compliance.isChecked(),
        }


# =============================================================================
# DIALOG MAPPING
# =============================================================================

# Map attribute names to dialog classes for Cloud Resources
CLOUD_RESOURCE_DIALOGS = {
    'cloud_deployment': CloudDeploymentDialog,
    'device_config': DeviceConfigDialog,
    'policy_objects': PolicyObjectsDialog,
    # Note: trust_devices, locations, and cloud_security are now inline cards
    # Keep legacy dialogs for potential advanced configuration:
    'trust_devices': TrustDevicesDialog,
    'cloud_security': CloudSecurityDialog,
}

# Map attribute names to dialog classes for Use Cases
USE_CASE_DIALOGS = {
    'mobile_users': MobileUsersDialog,
    'proxy_users': ProxyUsersDialog,
    'private_app': PrivateAppAccessDialog,
    'remote_branch': RemoteBranchDialog,
    'aiops_adem': AIOpsADEMDialog,
    'app_accel': AppAccelerationDialog,
    'rbi': RBIDialog,
    'pab': PABrowserDialog,
}
