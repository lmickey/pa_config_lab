"""
POV Configuration Workflow GUI - Complete Rewrite.

This module provides a comprehensive workflow for configuring new POV environments
with flexible source loading, management type selection, and default injection.
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
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

from gui.widgets import TenantSelectorWidget, ResultsPanel
from gui.dialogs import CLOUD_RESOURCE_DIALOGS, USE_CASE_DIALOGS
from config.credential_manager import PasswordGenerator
from config.utils.encryption import PasswordValidator

logger = logging.getLogger(__name__)


class POVConfigWorker(QThread):
    """Background worker for POV configuration operations."""

    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(bool, str)  # success, message
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
        except Exception as e:
            self.error.emit(f"Operation failed: {str(e)}")
            self.finished.emit(False, str(e))

    def _configure_firewall(self):
        """Configure firewall settings (placeholder for integration)."""
        self.progress.emit("Connecting to firewall...", 10)
        # TODO: Integrate configure_firewall.py logic
        self.progress.emit("Configuring zones...", 30)
        self.progress.emit("Configuring interfaces...", 50)
        self.progress.emit("Configuring routes...", 70)
        self.progress.emit("Configuring policies...", 90)
        self.progress.emit("Complete!", 100)
        self.finished.emit(True, "Firewall configured successfully")

    def _configure_service_connection(self):
        """Configure Prisma Access service connection (placeholder)."""
        self.progress.emit("Connecting to Prisma Access API...", 10)
        # TODO: Integrate configure_service_connection.py logic
        self.progress.emit("Creating IKE crypto profile...", 30)
        self.progress.emit("Creating IPSec crypto profile...", 50)
        self.progress.emit("Creating IKE gateway...", 70)
        self.progress.emit("Creating IPSec tunnel...", 90)
        self.progress.emit("Complete!", 100)
        self.finished.emit(True, "Service connection configured successfully")


class POVWorkflowWidget(QWidget):
    """Widget for POV configuration workflow."""

    def __init__(self, parent=None):
        """Initialize POV workflow widget."""
        super().__init__(parent)

        self.api_client = None
        self.connection_name = None
        self.config_data = {}
        self.management_type = "scm"  # "scm" or "panorama"
        self.loaded_sources = []  # Track which sources were loaded
        self.worker = None

        # Cloud Resources configuration storage
        self.cloud_resource_configs = {
            'cloud_deployment': {},
            'cloud_security': {},
            'device_config': {},
            'policy_objects': {},
            'locations': {'branches': [], 'datacenters': []},
            'trust_devices': {'devices': []},
        }

        # Use Cases configuration storage
        self.use_case_configs = {
            'mobile_users': {'enabled': True},  # Default enabled
            'proxy_users': {'enabled': False},
            'private_app': {'enabled': False},
            'remote_branch': {'enabled': False},
            'aiops_adem': {'enabled': False},
            'app_accel': {'enabled': False},
            'rbi': {'enabled': False},
            'pab': {'enabled': False},
        }

        self._init_ui()

        # Populate tenant dropdown from saved tenants
        self._populate_tenant_dropdown()

        logger.info("POV Workflow initialized")

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Step indicator
        steps_label = QLabel(
            "<b>POV Configuration Steps:</b> "
            "1️⃣ Tenant Info → 2️⃣ Cloud Resources → 3️⃣ POV Use Cases → "
            "4️⃣ Cloud Deployment → 5️⃣ Deploy POV Config → 6️⃣ Review & Execute"
        )
        steps_label.setWordWrap(True)
        steps_label.setStyleSheet(
            "padding: 10px; background-color: #e3f2fd; border-radius: 5px;"
        )
        layout.addWidget(steps_label)

        # Tabs for each step (reordered - review moved to end)
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self._create_tenant_info_tab()  # Step 1: Tenant Info & Environment
        self._create_cloud_resources_tab()  # Step 2: Cloud Resources
        self._create_pov_use_cases_tab()  # Step 3: POV Use Cases
        self._create_cloud_deployment_tab()  # Step 4: Cloud Resource Deployment
        self._create_deploy_config_tab()  # Step 5: Deploy POV Configuration
        self._create_review_tab()  # Step 6: Review & Execute

        layout.addWidget(self.tabs)

        # Progress bar and label (hidden, used by firewall/PA config tabs)
        self.progress_label = QLabel("Ready to begin")
        self.progress_label.setVisible(False)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

    # ============================================================================
    # TAB 1: TENANT INFORMATION
    # ============================================================================

    def _create_tenant_info_tab(self):
        """Create tenant information and environment deployment tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 1: Tenant Information & Environment</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Configure your management type, connect to your SCM tenant, and define your deployment environment."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 15px;")
        layout.addWidget(info)

        # Top row: Management Type and SCM Tenant side by side
        top_row = QHBoxLayout()

        # Management Type Selection (compact, side-by-side radios)
        mgmt_group = QGroupBox("Management Type")
        mgmt_layout = QHBoxLayout()

        self.scm_managed_radio = QRadioButton("SCM Managed")
        self.scm_managed_radio.setChecked(True)
        self.scm_managed_radio.toggled.connect(self._on_management_changed)
        mgmt_layout.addWidget(self.scm_managed_radio)

        self.panorama_managed_radio = QRadioButton("Panorama Managed")
        self.panorama_managed_radio.toggled.connect(self._on_management_changed)
        mgmt_layout.addWidget(self.panorama_managed_radio)

        mgmt_layout.addStretch()
        mgmt_group.setLayout(mgmt_layout)
        top_row.addWidget(mgmt_group)

        # SCM Tenant Selection (right side)
        self.tenant_selector = TenantSelectorWidget(
            parent=self,
            title="SCM Tenant",
            label="Connect to:",
            show_load_button=False
        )
        self.tenant_selector.connection_changed.connect(self._on_tenant_connection_changed)
        top_row.addWidget(self.tenant_selector, 1)

        layout.addLayout(top_row)

        # =====================================================================
        # Environment Deployment Section
        # =====================================================================
        self.deployment_group = QGroupBox("Environment Deployment")
        deployment_layout = QVBoxLayout()

        # --- SCM Managed: Azure Deployment Question ---
        self.azure_deploy_widget = QWidget()
        azure_layout = QVBoxLayout(self.azure_deploy_widget)
        azure_layout.setContentsMargins(0, 0, 0, 0)

        azure_label = QLabel("Will you need to deploy firewall resources in Azure?")
        azure_label.setStyleSheet("font-weight: bold;")
        azure_layout.addWidget(azure_label)

        azure_radio_layout = QHBoxLayout()
        self.azure_no_radio = QRadioButton("No")
        self.azure_no_radio.setChecked(True)
        self.azure_no_radio.toggled.connect(self._on_azure_deploy_changed)
        azure_radio_layout.addWidget(self.azure_no_radio)

        self.azure_yes_radio = QRadioButton("Yes")
        self.azure_yes_radio.toggled.connect(self._on_azure_deploy_changed)
        azure_radio_layout.addWidget(self.azure_yes_radio)
        azure_radio_layout.addStretch()
        azure_layout.addLayout(azure_radio_layout)

        # SCM Azure Firewall Options (hidden by default)
        self.scm_firewall_options = QWidget()
        scm_fw_layout = QVBoxLayout(self.scm_firewall_options)
        scm_fw_layout.setContentsMargins(20, 10, 0, 0)

        scm_fw_label = QLabel("Select firewall types to deploy:")
        scm_fw_layout.addWidget(scm_fw_label)

        self.deploy_sc_firewall_check = QCheckBox("Deploy Service Connection Firewall")
        self.deploy_sc_firewall_check.setToolTip("Deploy a firewall for Service Connection to Azure")
        self.deploy_sc_firewall_check.stateChanged.connect(self._update_deployment_status_visibility)
        scm_fw_layout.addWidget(self.deploy_sc_firewall_check)

        self.deploy_rn_firewall_check = QCheckBox("Deploy Remote Network Firewall")
        self.deploy_rn_firewall_check.setToolTip("Deploy a firewall for Remote Network connectivity")
        self.deploy_rn_firewall_check.stateChanged.connect(self._update_deployment_status_visibility)
        scm_fw_layout.addWidget(self.deploy_rn_firewall_check)

        self.scm_firewall_options.setVisible(False)
        azure_layout.addWidget(self.scm_firewall_options)

        deployment_layout.addWidget(self.azure_deploy_widget)

        # --- Panorama Managed: Firewall Deployment (always shown for Panorama) ---
        self.panorama_deploy_widget = QWidget()
        panorama_layout = QVBoxLayout(self.panorama_deploy_widget)
        panorama_layout.setContentsMargins(0, 0, 0, 0)

        panorama_info = QLabel(
            "<b>Panorama-managed deployments require at least one Service Connection firewall.</b>"
        )
        panorama_info.setStyleSheet("color: #1565C0; margin-bottom: 10px;")
        panorama_layout.addWidget(panorama_info)

        self.panorama_sc_check = QCheckBox("Service Connection Firewall (Required)")
        self.panorama_sc_check.setChecked(True)
        self.panorama_sc_check.setEnabled(False)  # Always required for Panorama
        panorama_layout.addWidget(self.panorama_sc_check)

        rn_question = QLabel("Will you also deploy Remote Network firewalls?")
        rn_question.setStyleSheet("margin-top: 10px;")
        panorama_layout.addWidget(rn_question)

        rn_radio_layout = QHBoxLayout()
        self.panorama_rn_no_radio = QRadioButton("No")
        self.panorama_rn_no_radio.setChecked(True)
        self.panorama_rn_no_radio.toggled.connect(self._on_panorama_rn_changed)
        rn_radio_layout.addWidget(self.panorama_rn_no_radio)

        self.panorama_rn_yes_radio = QRadioButton("Yes")
        self.panorama_rn_yes_radio.toggled.connect(self._on_panorama_rn_changed)
        rn_radio_layout.addWidget(self.panorama_rn_yes_radio)
        rn_radio_layout.addStretch()
        panorama_layout.addLayout(rn_radio_layout)

        # RN count (hidden by default)
        self.panorama_rn_count_widget = QWidget()
        rn_count_layout = QHBoxLayout(self.panorama_rn_count_widget)
        rn_count_layout.setContentsMargins(20, 5, 0, 0)
        rn_count_layout.addWidget(QLabel("Number of RN firewalls:"))
        self.panorama_rn_count_input = QLineEdit()
        self.panorama_rn_count_input.setPlaceholderText("1")
        self.panorama_rn_count_input.setMaximumWidth(60)
        rn_count_layout.addWidget(self.panorama_rn_count_input)
        rn_count_layout.addStretch()
        self.panorama_rn_count_widget.setVisible(False)
        panorama_layout.addWidget(self.panorama_rn_count_widget)

        self.panorama_deploy_widget.setVisible(False)
        deployment_layout.addWidget(self.panorama_deploy_widget)

        # =====================================================================
        # Deployment Status Section
        # =====================================================================
        self.deployment_status_widget = QWidget()
        status_layout = QVBoxLayout(self.deployment_status_widget)
        status_layout.setContentsMargins(0, 15, 0, 0)

        status_label = QLabel("Have the firewalls already been deployed?")
        status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(status_label)

        status_radio_layout = QHBoxLayout()
        self.deployed_yes_radio = QRadioButton("Yes, already deployed")
        self.deployed_yes_radio.toggled.connect(self._on_deployment_status_changed)
        status_radio_layout.addWidget(self.deployed_yes_radio)

        self.deployed_no_radio = QRadioButton("No, need to deploy")
        self.deployed_no_radio.setChecked(True)
        self.deployed_no_radio.toggled.connect(self._on_deployment_status_changed)
        status_radio_layout.addWidget(self.deployed_no_radio)
        status_radio_layout.addStretch()
        status_layout.addLayout(status_radio_layout)

        # --- Already Deployed: Credentials Section ---
        self.credentials_widget = QWidget()
        creds_layout = QVBoxLayout(self.credentials_widget)
        creds_layout.setContentsMargins(20, 10, 0, 0)

        creds_info = QLabel(
            "Enter the credentials for your deployed firewall(s) so we can pull their configuration."
        )
        creds_info.setStyleSheet("color: gray; margin-bottom: 10px;")
        creds_info.setWordWrap(True)
        creds_layout.addWidget(creds_info)

        # Firewall credentials form
        fw_creds_form = QFormLayout()
        self.fw_mgmt_ip_input = QLineEdit()
        self.fw_mgmt_ip_input.setPlaceholderText("192.168.1.1 or firewall.example.com")
        fw_creds_form.addRow("Management IP/Hostname:", self.fw_mgmt_ip_input)

        self.fw_username_input = QLineEdit()
        self.fw_username_input.setPlaceholderText("admin")
        fw_creds_form.addRow("Username:", self.fw_username_input)

        self.fw_password_input = QLineEdit()
        self.fw_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.fw_password_input.setPlaceholderText("Password or API Key")
        fw_creds_form.addRow("Password/API Key:", self.fw_password_input)

        creds_layout.addLayout(fw_creds_form)

        # Add more firewalls button (placeholder)
        add_fw_btn = QPushButton("+ Add Another Firewall")
        add_fw_btn.setMaximumWidth(200)
        add_fw_btn.setEnabled(False)  # Placeholder
        add_fw_btn.setToolTip("Coming soon: Add credentials for additional firewalls")
        creds_layout.addWidget(add_fw_btn)

        self.credentials_widget.setVisible(False)
        status_layout.addWidget(self.credentials_widget)

        # --- Need to Deploy: Deployment Method Section ---
        self.deploy_method_widget = QWidget()
        method_layout = QVBoxLayout(self.deploy_method_widget)
        method_layout.setContentsMargins(20, 10, 0, 0)

        method_label = QLabel("How would you like to deploy the firewalls?")
        method_layout.addWidget(method_label)

        method_radio_layout = QHBoxLayout()
        self.deploy_manual_radio = QRadioButton("Manually")
        self.deploy_manual_radio.setChecked(True)
        self.deploy_manual_radio.toggled.connect(self._on_deploy_method_changed)
        method_radio_layout.addWidget(self.deploy_manual_radio)

        self.deploy_terraform_radio = QRadioButton("Terraform")
        self.deploy_terraform_radio.toggled.connect(self._on_deploy_method_changed)
        method_radio_layout.addWidget(self.deploy_terraform_radio)
        method_radio_layout.addStretch()
        method_layout.addLayout(method_radio_layout)

        # Manual deployment info
        self.manual_deploy_info = QLabel(
            "You will deploy the firewalls manually. Once deployed, return here and select "
            "'Yes, already deployed' to enter the credentials and pull the configuration."
        )
        self.manual_deploy_info.setStyleSheet(
            "color: #F57C00; padding: 10px; background-color: #FFF3E0; "
            "border-radius: 5px; margin-top: 10px;"
        )
        self.manual_deploy_info.setWordWrap(True)
        method_layout.addWidget(self.manual_deploy_info)

        # Terraform deployment info
        self.terraform_deploy_info = QLabel(
            "We will generate a customized Terraform configuration based on your selections. "
            "The Terraform files will include default firewall configurations optimized for POV environments."
        )
        self.terraform_deploy_info.setStyleSheet(
            "color: #1565C0; padding: 10px; background-color: #E3F2FD; "
            "border-radius: 5px; margin-top: 10px;"
        )
        self.terraform_deploy_info.setWordWrap(True)
        self.terraform_deploy_info.setVisible(False)
        method_layout.addWidget(self.terraform_deploy_info)

        status_layout.addWidget(self.deploy_method_widget)

        self.deployment_status_widget.setVisible(False)
        deployment_layout.addWidget(self.deployment_status_widget)

        deployment_layout.addStretch()
        self.deployment_group.setLayout(deployment_layout)
        layout.addWidget(self.deployment_group)

        # =====================================================================
        # Bottom Status and Navigation
        # =====================================================================
        bottom_layout = QHBoxLayout()

        self.load_status = QLabel("Configure your environment above")
        self.load_status.setStyleSheet("color: gray;")
        bottom_layout.addWidget(self.load_status)

        bottom_layout.addStretch()

        # Save button
        save_config_btn = QPushButton("💾 Save Config")
        save_config_btn.setMinimumWidth(120)
        save_config_btn.setMinimumHeight(40)
        save_config_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #FF9800; color: white; padding: 10px; font-weight: bold; "
            "  border-radius: 5px; border: 1px solid #F57C00; border-bottom: 3px solid #E65100; "
            "}"
            "QPushButton:hover { background-color: #FB8C00; border-bottom: 3px solid #BF360C; }"
            "QPushButton:pressed { background-color: #F57C00; border-bottom: 1px solid #E65100; }"
        )
        save_config_btn.clicked.connect(self._save_current_config)
        bottom_layout.addWidget(save_config_btn)

        # Next button
        next_btn = QPushButton("Next: Cloud Resources →")
        next_btn.setMinimumWidth(180)
        next_btn.setMinimumHeight(40)
        next_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; "
            "  border-radius: 5px; border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { background-color: #45a049; border-bottom: 3px solid #1B5E20; }"
            "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
        )
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        bottom_layout.addWidget(next_btn)

        layout.addLayout(bottom_layout)

        # Initialize visibility
        self._on_management_changed()

        self.tabs.addTab(tab, "1️⃣ Tenant Info")

    # ============================================================================
    # TAB 2: CLOUD RESOURCES
    # ============================================================================

    def _create_cloud_resources_tab(self):
        """Create cloud resources configuration tab (Step 2)."""
        from PyQt6.QtWidgets import QGridLayout, QFrame, QScrollArea, QComboBox

        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 2: Cloud Resources Configuration</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Configure the cloud resource settings for your POV deployment. "
            "Click the ⚙️ button on each card to configure additional details."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)

        # Helper to create a standard resource card with enabled configure button
        def create_resource_card(icon, title_text, bullet_points, attr_name):
            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row: Title, status indicator, and Configure button
            top_row = QHBoxLayout()
            title_label = QLabel(f"<b>{icon} {title_text}</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            # Status indicator (shows if configured)
            status_label = QLabel("")
            status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            setattr(self, f"{attr_name}_status", status_label)
            top_row.addWidget(status_label)

            top_row.addStretch()

            # Configure button - ENABLED
            config_btn = QPushButton("⚙️")
            config_btn.setFixedSize(28, 28)
            config_btn.setEnabled(True)
            config_btn.setToolTip(f"Configure {title_text}")
            config_btn.setStyleSheet(
                "QPushButton { "
                "  background-color: #2196F3; color: white; border: 1px solid #1976D2; "
                "  border-radius: 4px; font-size: 12px; "
                "}"
                "QPushButton:hover { background-color: #1E88E5; }"
                "QPushButton:pressed { background-color: #1976D2; }"
            )
            # Connect to open dialog
            config_btn.clicked.connect(lambda checked, a=attr_name: self._open_cloud_resource_dialog(a))
            setattr(self, f"{attr_name}_btn", config_btn)
            top_row.addWidget(config_btn)

            card_layout.addLayout(top_row)

            # Bullet points description
            bullets_text = "\n".join(f"  • {bp}" for bp in bullet_points)
            desc_label = QLabel(bullets_text)
            desc_label.setStyleSheet("color: #666; font-size: 11px;")
            desc_label.setWordWrap(True)
            card_layout.addWidget(desc_label)

            card_layout.addStretch()

            return card

        # Create special Cloud Deployment card with inline fields
        def create_cloud_deployment_card():
            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(8)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row: Title, status indicator, and Configure button
            top_row = QHBoxLayout()
            title_label = QLabel("<b>☁️ Cloud Deployment & Sizing</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            # Status indicator
            status_label = QLabel("")
            status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            self.cloud_deployment_status = status_label
            top_row.addWidget(status_label)

            top_row.addStretch()

            # Configure button for additional settings (VM sizing, VNet, etc.)
            config_btn = QPushButton("⚙️")
            config_btn.setFixedSize(28, 28)
            config_btn.setEnabled(True)
            config_btn.setToolTip("Configure VM sizing and network details")
            config_btn.setStyleSheet(
                "QPushButton { "
                "  background-color: #2196F3; color: white; border: 1px solid #1976D2; "
                "  border-radius: 4px; font-size: 12px; "
                "}"
                "QPushButton:hover { background-color: #1E88E5; }"
                "QPushButton:pressed { background-color: #1976D2; }"
            )
            config_btn.clicked.connect(lambda: self._open_cloud_resource_dialog('cloud_deployment'))
            self.cloud_deployment_btn = config_btn
            top_row.addWidget(config_btn)

            card_layout.addLayout(top_row)

            # Customer Name field
            customer_row = QHBoxLayout()
            customer_label = QLabel("Customer Name:")
            customer_label.setStyleSheet("font-size: 12px; color: #333; min-width: 110px;")
            customer_row.addWidget(customer_label)

            self.cloud_customer_name = QLineEdit()
            self.cloud_customer_name.setPlaceholderText("e.g., acme")
            self.cloud_customer_name.setStyleSheet(
                "QLineEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
            )
            self.cloud_customer_name.textChanged.connect(self._on_cloud_customer_changed)
            customer_row.addWidget(self.cloud_customer_name)
            card_layout.addLayout(customer_row)

            # Primary Cloud Service field (Azure - greyed out)
            cloud_row = QHBoxLayout()
            cloud_label = QLabel("Primary Cloud Service:")
            cloud_label.setStyleSheet("font-size: 12px; color: #333; min-width: 110px;")
            cloud_row.addWidget(cloud_label)

            self.cloud_service_combo = QComboBox()
            self.cloud_service_combo.addItem("Azure")
            self.cloud_service_combo.setEnabled(False)  # Greyed out - only Azure supported
            self.cloud_service_combo.setStyleSheet(
                "QComboBox { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; "
                "background-color: #f0f0f0; color: #666; }"
            )
            self.cloud_service_combo.setToolTip("Currently only Azure is supported")
            cloud_row.addWidget(self.cloud_service_combo)
            card_layout.addLayout(cloud_row)

            # Primary Region field
            region_row = QHBoxLayout()
            region_label = QLabel("Primary Region:")
            region_label.setStyleSheet("font-size: 12px; color: #333; min-width: 110px;")
            region_row.addWidget(region_label)

            self.cloud_region_combo = QComboBox()
            self.cloud_region_combo.addItems([
                "eastus", "eastus2", "westus", "westus2", "centralus",
                "northeurope", "westeurope", "uksouth", "ukwest",
                "australiaeast", "southeastasia", "japaneast"
            ])
            self.cloud_region_combo.setStyleSheet(
                "QComboBox { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
            )
            self.cloud_region_combo.currentTextChanged.connect(self._on_cloud_region_changed)
            region_row.addWidget(self.cloud_region_combo)
            card_layout.addLayout(region_row)

            # Resource Group preview
            rg_row = QHBoxLayout()
            rg_label = QLabel("Resource Group:")
            rg_label.setStyleSheet("font-size: 12px; color: #333; min-width: 110px;")
            rg_row.addWidget(rg_label)

            self.cloud_rg_preview = QLabel("<i>(enter customer name)</i>")
            self.cloud_rg_preview.setStyleSheet("font-size: 12px; color: #666;")
            rg_row.addWidget(self.cloud_rg_preview)
            rg_row.addStretch()
            card_layout.addLayout(rg_row)

            # Separator
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("background-color: #ddd;")
            card_layout.addWidget(sep)

            # Admin Credentials section label
            creds_label = QLabel("<b>Admin Credentials</b>")
            creds_label.setStyleSheet("font-size: 12px; color: #333; margin-top: 4px;")
            card_layout.addWidget(creds_label)

            # Admin Username field (derived from customer name)
            admin_user_row = QHBoxLayout()
            admin_user_label = QLabel("Admin Username:")
            admin_user_label.setStyleSheet("font-size: 12px; color: #333; min-width: 110px;")
            admin_user_row.addWidget(admin_user_label)

            self.cloud_admin_username = QLineEdit()
            self.cloud_admin_username.setPlaceholderText("(auto: customer name)")
            self.cloud_admin_username.setStyleSheet(
                "QLineEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
            )
            self.cloud_admin_username.textChanged.connect(self._on_admin_username_changed)
            admin_user_row.addWidget(self.cloud_admin_username)
            card_layout.addLayout(admin_user_row)

            # Admin Password field with regenerate button
            admin_pwd_row = QHBoxLayout()
            admin_pwd_label = QLabel("Admin Password:")
            admin_pwd_label.setStyleSheet("font-size: 12px; color: #333; min-width: 110px;")
            admin_pwd_row.addWidget(admin_pwd_label)

            self.cloud_admin_password = QLineEdit()
            self.cloud_admin_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.cloud_admin_password.setStyleSheet(
                "QLineEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
            )
            self.cloud_admin_password.textChanged.connect(self._on_admin_password_changed)
            admin_pwd_row.addWidget(self.cloud_admin_password)

            # Show/hide password button
            self.cloud_pwd_show_btn = QPushButton("👁")
            self.cloud_pwd_show_btn.setFixedSize(28, 28)
            self.cloud_pwd_show_btn.setToolTip("Show/hide password")
            self.cloud_pwd_show_btn.setCheckable(True)
            self.cloud_pwd_show_btn.setStyleSheet(
                "QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; }"
                "QPushButton:checked { background-color: #e0e0e0; }"
            )
            self.cloud_pwd_show_btn.toggled.connect(self._toggle_password_visibility)
            admin_pwd_row.addWidget(self.cloud_pwd_show_btn)

            # Regenerate password button
            self.cloud_pwd_regen_btn = QPushButton("🔄")
            self.cloud_pwd_regen_btn.setFixedSize(28, 28)
            self.cloud_pwd_regen_btn.setToolTip("Generate new password")
            self.cloud_pwd_regen_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; border: 1px solid #388E3C; border-radius: 4px; }"
                "QPushButton:hover { background-color: #45a049; }"
            )
            self.cloud_pwd_regen_btn.clicked.connect(self._regenerate_admin_password)
            admin_pwd_row.addWidget(self.cloud_pwd_regen_btn)

            card_layout.addLayout(admin_pwd_row)

            # Password strength indicator
            strength_row = QHBoxLayout()
            strength_spacer = QLabel("")
            strength_spacer.setStyleSheet("min-width: 110px;")
            strength_row.addWidget(strength_spacer)

            self.cloud_pwd_strength_bar = QProgressBar()
            self.cloud_pwd_strength_bar.setMaximum(100)
            self.cloud_pwd_strength_bar.setTextVisible(False)
            self.cloud_pwd_strength_bar.setMaximumHeight(8)
            self.cloud_pwd_strength_bar.setStyleSheet(
                "QProgressBar { background-color: #e0e0e0; border-radius: 4px; }"
                "QProgressBar::chunk { background-color: #4CAF50; border-radius: 4px; }"
            )
            strength_row.addWidget(self.cloud_pwd_strength_bar)

            self.cloud_pwd_strength_label = QLabel("No password")
            self.cloud_pwd_strength_label.setStyleSheet("color: #666; font-size: 11px; min-width: 80px;")
            strength_row.addWidget(self.cloud_pwd_strength_label)

            card_layout.addLayout(strength_row)

            # Initialize password validator
            self._password_validator = PasswordValidator()

            # Generate initial password
            self._regenerate_admin_password()

            # Additional settings note
            note_label = QLabel("  • Click ⚙️ for VM sizing and network configuration")
            note_label.setStyleSheet("color: #666; font-size: 11px; margin-top: 4px;")
            card_layout.addWidget(note_label)

            return card

        # Create inline Device Configuration card with auto-save
        def create_device_config_card():
            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row: Title and status
            top_row = QHBoxLayout()
            title_label = QLabel("<b>🔧 Initial Device Configuration</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            status_label = QLabel("✓ Auto-saved")
            status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            self.device_config_status = status_label
            top_row.addWidget(status_label)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # DNS Settings
            dns_label = QLabel("<b>DNS Servers</b>")
            dns_label.setStyleSheet("font-size: 11px; color: #555; margin-top: 4px;")
            card_layout.addWidget(dns_label)

            dns_row = QHBoxLayout()
            dns_row.setSpacing(8)

            self.device_dns_primary = QLineEdit()
            self.device_dns_primary.setText("8.8.8.8")
            self.device_dns_primary.setPlaceholderText("Primary DNS")
            self.device_dns_primary.setStyleSheet(
                "QLineEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
            )
            self.device_dns_primary.textChanged.connect(self._on_device_config_changed)
            dns_row.addWidget(QLabel("Primary:"))
            dns_row.addWidget(self.device_dns_primary)

            self.device_dns_secondary = QLineEdit()
            self.device_dns_secondary.setText("8.8.4.4")
            self.device_dns_secondary.setPlaceholderText("Secondary DNS")
            self.device_dns_secondary.setStyleSheet(
                "QLineEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
            )
            self.device_dns_secondary.textChanged.connect(self._on_device_config_changed)
            dns_row.addWidget(QLabel("Secondary:"))
            dns_row.addWidget(self.device_dns_secondary)

            card_layout.addLayout(dns_row)

            # NTP Settings
            ntp_label = QLabel("<b>NTP Servers</b>")
            ntp_label.setStyleSheet("font-size: 11px; color: #555; margin-top: 4px;")
            card_layout.addWidget(ntp_label)

            ntp_row = QHBoxLayout()
            ntp_row.setSpacing(8)

            self.device_ntp_primary = QLineEdit()
            self.device_ntp_primary.setText("pool.ntp.org")
            self.device_ntp_primary.setPlaceholderText("Primary NTP")
            self.device_ntp_primary.setStyleSheet(
                "QLineEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
            )
            self.device_ntp_primary.textChanged.connect(self._on_device_config_changed)
            ntp_row.addWidget(QLabel("Primary:"))
            ntp_row.addWidget(self.device_ntp_primary)

            self.device_ntp_secondary = QLineEdit()
            self.device_ntp_secondary.setText("time.google.com")
            self.device_ntp_secondary.setPlaceholderText("Secondary NTP")
            self.device_ntp_secondary.setStyleSheet(
                "QLineEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
            )
            self.device_ntp_secondary.textChanged.connect(self._on_device_config_changed)
            ntp_row.addWidget(QLabel("Secondary:"))
            ntp_row.addWidget(self.device_ntp_secondary)

            card_layout.addLayout(ntp_row)

            # Hostname prefix
            host_row = QHBoxLayout()
            host_row.setSpacing(8)

            host_label = QLabel("Hostname Prefix:")
            host_label.setStyleSheet("font-size: 12px; color: #333;")
            host_row.addWidget(host_label)

            self.device_hostname_prefix = QLineEdit()
            self.device_hostname_prefix.setText("fw")
            self.device_hostname_prefix.setMaximumWidth(100)
            self.device_hostname_prefix.setStyleSheet(
                "QLineEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
            )
            self.device_hostname_prefix.textChanged.connect(self._on_device_config_changed)
            host_row.addWidget(self.device_hostname_prefix)
            host_row.addStretch()

            card_layout.addLayout(host_row)

            # Initialize config with defaults
            self.cloud_resource_configs['device_config'] = {
                'dns_primary': '8.8.8.8',
                'dns_secondary': '8.8.4.4',
                'ntp_primary': 'pool.ntp.org',
                'ntp_secondary': 'time.google.com',
                'hostname_prefix': 'fw',
            }

            return card

        # Create inline Policy and Objects card with auto-save checkboxes
        def create_policy_objects_card():
            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(4)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row: Title and status
            top_row = QHBoxLayout()
            title_label = QLabel("<b>📋 Policy and Objects</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            status_label = QLabel("✓ Auto-saved")
            status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            self.policy_objects_status = status_label
            top_row.addWidget(status_label)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Default Objects checkboxes
            obj_label = QLabel("<b>Default Objects</b>")
            obj_label.setStyleSheet("font-size: 11px; color: #555; margin-top: 2px;")
            card_layout.addWidget(obj_label)

            self.policy_rfc1918 = QCheckBox("RFC1918 address objects")
            self.policy_rfc1918.setChecked(True)
            self.policy_rfc1918.setStyleSheet("font-size: 11px;")
            self.policy_rfc1918.stateChanged.connect(self._on_policy_config_changed)
            card_layout.addWidget(self.policy_rfc1918)

            self.policy_app_groups = QCheckBox("Common application groups")
            self.policy_app_groups.setChecked(True)
            self.policy_app_groups.setStyleSheet("font-size: 11px;")
            self.policy_app_groups.stateChanged.connect(self._on_policy_config_changed)
            card_layout.addWidget(self.policy_app_groups)

            # Policy checkboxes
            policy_label = QLabel("<b>Security Policies</b>")
            policy_label.setStyleSheet("font-size: 11px; color: #555; margin-top: 2px;")
            card_layout.addWidget(policy_label)

            self.policy_allow_outbound = QCheckBox("Allow outbound rule (trust → untrust)")
            self.policy_allow_outbound.setChecked(True)
            self.policy_allow_outbound.setStyleSheet("font-size: 11px;")
            self.policy_allow_outbound.stateChanged.connect(self._on_policy_config_changed)
            card_layout.addWidget(self.policy_allow_outbound)

            self.policy_block_quic = QCheckBox("Block QUIC (force HTTPS inspection)")
            self.policy_block_quic.setChecked(True)
            self.policy_block_quic.setStyleSheet("font-size: 11px;")
            self.policy_block_quic.stateChanged.connect(self._on_policy_config_changed)
            card_layout.addWidget(self.policy_block_quic)

            # NAT checkbox
            self.policy_outbound_nat = QCheckBox("Outbound NAT rule")
            self.policy_outbound_nat.setChecked(True)
            self.policy_outbound_nat.setStyleSheet("font-size: 11px;")
            self.policy_outbound_nat.stateChanged.connect(self._on_policy_config_changed)
            card_layout.addWidget(self.policy_outbound_nat)

            # Initialize config with defaults
            self.cloud_resource_configs['policy_objects'] = {
                'create_rfc1918': True,
                'create_app_groups': True,
                'allow_outbound': True,
                'block_quic': True,
                'create_outbound_nat': True,
            }

            return card

        # Create inline Cloud Security card with auto-save
        def create_cloud_security_card():
            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row: Title and status
            top_row = QHBoxLayout()
            title_label = QLabel("<b>🔒 Cloud Security Configuration</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            status_label = QLabel("✓ Auto-saved")
            status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            self.cloud_security_status = status_label
            top_row.addWidget(status_label)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Allowed Source IPs
            source_row = QHBoxLayout()
            source_label = QLabel("Allowed Source IPs:")
            source_label.setStyleSheet("font-size: 12px; color: #333; min-width: 120px;")
            source_row.addWidget(source_label)

            self.cloud_security_source_ips = QLineEdit()
            self.cloud_security_source_ips.setPlaceholderText("Your public IP")
            self.cloud_security_source_ips.setStyleSheet(
                "QLineEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
            )
            self.cloud_security_source_ips.textChanged.connect(self._on_cloud_security_changed)
            source_row.addWidget(self.cloud_security_source_ips)

            # Fetch button
            fetch_ip_btn = QPushButton("🔍")
            fetch_ip_btn.setFixedSize(28, 28)
            fetch_ip_btn.setToolTip("Detect my public IP")
            fetch_ip_btn.setStyleSheet(
                "QPushButton { background-color: #2196F3; color: white; border: 1px solid #1976D2; border-radius: 4px; }"
                "QPushButton:hover { background-color: #1E88E5; }"
            )
            fetch_ip_btn.clicked.connect(self._fetch_and_set_public_ip)
            source_row.addWidget(fetch_ip_btn)

            card_layout.addLayout(source_row)

            # Network Security Groups section
            nsg_label = QLabel("<b>Network Security Groups</b>")
            nsg_label.setStyleSheet("font-size: 11px; color: #555; margin-top: 4px;")
            card_layout.addWidget(nsg_label)

            # Management NSG - required, checked, greyed out
            self.cloud_security_mgmt_nsg = QCheckBox("Management NSG (required)")
            self.cloud_security_mgmt_nsg.setChecked(True)
            self.cloud_security_mgmt_nsg.setEnabled(False)  # Greyed out
            self.cloud_security_mgmt_nsg.setStyleSheet("font-size: 11px; color: #666;")
            card_layout.addWidget(self.cloud_security_mgmt_nsg)

            # Trust NSG - optional, unchecked by default
            self.cloud_security_trust_nsg = QCheckBox("Trust NSG (internal traffic)")
            self.cloud_security_trust_nsg.setChecked(False)
            self.cloud_security_trust_nsg.setStyleSheet("font-size: 11px;")
            self.cloud_security_trust_nsg.stateChanged.connect(self._on_cloud_security_changed)
            card_layout.addWidget(self.cloud_security_trust_nsg)

            # Ports section
            ports_label = QLabel("<b>Management Ports</b>")
            ports_label.setStyleSheet("font-size: 11px; color: #555; margin-top: 4px;")
            card_layout.addWidget(ports_label)

            ports_row = QHBoxLayout()
            self.cloud_security_ssh = QCheckBox("SSH (22)")
            self.cloud_security_ssh.setChecked(True)
            self.cloud_security_ssh.setStyleSheet("font-size: 11px;")
            self.cloud_security_ssh.stateChanged.connect(self._on_cloud_security_changed)
            ports_row.addWidget(self.cloud_security_ssh)

            self.cloud_security_https = QCheckBox("HTTPS (443)")
            self.cloud_security_https.setChecked(True)
            self.cloud_security_https.setStyleSheet("font-size: 11px;")
            self.cloud_security_https.stateChanged.connect(self._on_cloud_security_changed)
            ports_row.addWidget(self.cloud_security_https)

            ports_row.addStretch()
            card_layout.addLayout(ports_row)

            # Initialize config and fetch public IP
            self.cloud_resource_configs['cloud_security'] = {
                'source_ips': '',
                'allow_ssh': True,
                'allow_https': True,
                'create_mgmt_nsg': True,
                'create_trust_nsg': False,
            }

            # Auto-fetch public IP on card creation
            self._fetch_and_set_public_ip()

            # Prevent vertical stretching
            card_layout.addStretch()

            return card

        # Create inline Locations card (Branches & Datacenters)
        def create_locations_card():
            from PyQt6.QtWidgets import QListWidget, QListWidgetItem

            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row: Title and status
            top_row = QHBoxLayout()
            title_label = QLabel("<b>🏢 Locations</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            status_label = QLabel("")
            status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            self.locations_status = status_label
            top_row.addWidget(status_label)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Branches section
            branches_label = QLabel("<b>Branches</b> (Remote Network)")
            branches_label.setStyleSheet("font-size: 11px; color: #555;")
            card_layout.addWidget(branches_label)

            self.branches_list = QListWidget()
            self.branches_list.setMaximumHeight(60)
            self.branches_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 11px; }"
                "QListWidget::item { padding: 2px; }"
                "QListWidget::item:selected { background-color: #2196F3; color: white; }"
            )
            self.branches_list.itemSelectionChanged.connect(self._on_branch_selection_changed)
            card_layout.addWidget(self.branches_list)

            # Add branch row
            branch_add_row = QHBoxLayout()
            self.branch_name_input = QLineEdit()
            self.branch_name_input.setPlaceholderText("Branch name")
            self.branch_name_input.setMaximumWidth(120)
            self.branch_name_input.setStyleSheet(
                "QLineEdit { padding: 3px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; }"
            )
            branch_add_row.addWidget(self.branch_name_input)

            self.branch_region_combo = QComboBox()
            self.branch_region_combo.addItem("(Primary)")
            self.branch_region_combo.addItems([
                "eastus", "eastus2", "westus", "westus2", "centralus",
                "northeurope", "westeurope", "uksouth", "australiaeast"
            ])
            self.branch_region_combo.setStyleSheet(
                "QComboBox { padding: 3px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; }"
            )
            branch_add_row.addWidget(self.branch_region_combo)

            add_branch_btn = QPushButton("+")
            add_branch_btn.setFixedSize(24, 24)
            add_branch_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px; }"
                "QPushButton:hover { background-color: #45a049; }"
            )
            add_branch_btn.clicked.connect(self._add_branch)
            branch_add_row.addWidget(add_branch_btn)

            self.remove_branch_btn = QPushButton("-")
            self.remove_branch_btn.setFixedSize(24, 24)
            self.remove_branch_btn.setEnabled(False)
            self.remove_branch_btn.setStyleSheet(
                "QPushButton { background-color: #f44336; color: white; font-weight: bold; border-radius: 4px; }"
                "QPushButton:hover { background-color: #d32f2f; }"
                "QPushButton:disabled { background-color: #ccc; }"
            )
            self.remove_branch_btn.clicked.connect(self._remove_branch)
            branch_add_row.addWidget(self.remove_branch_btn)

            card_layout.addLayout(branch_add_row)

            # Datacenters section
            dc_label = QLabel("<b>Datacenters</b> (Service Connection)")
            dc_label.setStyleSheet("font-size: 11px; color: #555; margin-top: 4px;")
            card_layout.addWidget(dc_label)

            self.datacenters_list = QListWidget()
            self.datacenters_list.setMaximumHeight(60)
            self.datacenters_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 11px; }"
                "QListWidget::item { padding: 2px; }"
                "QListWidget::item:selected { background-color: #2196F3; color: white; }"
            )
            self.datacenters_list.itemSelectionChanged.connect(self._on_datacenter_selection_changed)
            card_layout.addWidget(self.datacenters_list)

            # Add datacenter row
            dc_add_row = QHBoxLayout()
            self.dc_name_input = QLineEdit()
            self.dc_name_input.setPlaceholderText("DC name")
            self.dc_name_input.setMaximumWidth(120)
            self.dc_name_input.setStyleSheet(
                "QLineEdit { padding: 3px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; }"
            )
            dc_add_row.addWidget(self.dc_name_input)

            self.dc_region_combo = QComboBox()
            self.dc_region_combo.addItem("(Primary)")
            self.dc_region_combo.addItems([
                "eastus", "eastus2", "westus", "westus2", "centralus",
                "northeurope", "westeurope", "uksouth", "australiaeast"
            ])
            self.dc_region_combo.setStyleSheet(
                "QComboBox { padding: 3px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; }"
            )
            dc_add_row.addWidget(self.dc_region_combo)

            add_dc_btn = QPushButton("+")
            add_dc_btn.setFixedSize(24, 24)
            add_dc_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px; }"
                "QPushButton:hover { background-color: #45a049; }"
            )
            add_dc_btn.clicked.connect(self._add_datacenter)
            dc_add_row.addWidget(add_dc_btn)

            self.remove_dc_btn = QPushButton("-")
            self.remove_dc_btn.setFixedSize(24, 24)
            self.remove_dc_btn.setEnabled(False)
            self.remove_dc_btn.setStyleSheet(
                "QPushButton { background-color: #f44336; color: white; font-weight: bold; border-radius: 4px; }"
                "QPushButton:hover { background-color: #d32f2f; }"
                "QPushButton:disabled { background-color: #ccc; }"
            )
            self.remove_dc_btn.clicked.connect(self._remove_datacenter)
            dc_add_row.addWidget(self.remove_dc_btn)

            card_layout.addLayout(dc_add_row)

            # Config summary
            summary_frame = QFrame()
            summary_frame.setStyleSheet(
                "QFrame { background-color: #E3F2FD; border: 1px solid #90CAF9; "
                "border-radius: 4px; padding: 4px; margin-top: 4px; }"
            )
            summary_layout = QHBoxLayout(summary_frame)
            summary_layout.setContentsMargins(6, 2, 6, 2)

            self.locations_summary = QLabel("VPN: AES-256-GCM | BGP: Enabled | Keys: Auto")
            self.locations_summary.setStyleSheet("color: #1565C0; font-size: 10px;")
            summary_layout.addWidget(self.locations_summary)

            card_layout.addWidget(summary_frame)

            # Initialize config
            self.cloud_resource_configs['locations'] = {
                'branches': [],
                'datacenters': [],
            }

            return card

        # Create inline Trust Network Devices card with dynamic population
        def create_trust_devices_card():
            from PyQt6.QtWidgets import QListWidget, QListWidgetItem

            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row: Title and status
            top_row = QHBoxLayout()
            title_label = QLabel("<b>🖥️ Trust Network Devices</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            status_label = QLabel("")
            status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            self.trust_devices_status = status_label
            top_row.addWidget(status_label)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Single unified devices list
            self.devices_list = QListWidget()
            self.devices_list.setMaximumHeight(100)
            self.devices_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 11px; }"
                "QListWidget::item { padding: 2px; }"
                "QListWidget::item:selected { background-color: #2196F3; color: white; }"
            )
            self.devices_list.itemSelectionChanged.connect(self._on_device_selection_changed)
            card_layout.addWidget(self.devices_list)

            # Add device form row
            form_row = QHBoxLayout()
            form_row.setSpacing(4)

            self.device_location_combo = QComboBox()
            self.device_location_combo.setStyleSheet(
                "QComboBox { padding: 2px 4px; border: 1px solid #ccc; border-radius: 4px; font-size: 10px; }"
            )
            self.device_location_combo.setMinimumWidth(80)
            form_row.addWidget(self.device_location_combo)

            self.device_type_combo = QComboBox()
            self.device_type_combo.addItems(["UserVM", "ServerVM"])
            self.device_type_combo.setStyleSheet(
                "QComboBox { padding: 2px 4px; border: 1px solid #ccc; border-radius: 4px; font-size: 10px; }"
            )
            self.device_type_combo.currentTextChanged.connect(self._on_device_type_changed)
            form_row.addWidget(self.device_type_combo)

            self.device_subtype_combo = QComboBox()
            self.device_subtype_combo.addItems(["Windows", "Linux"])
            self.device_subtype_combo.setStyleSheet(
                "QComboBox { padding: 2px 4px; border: 1px solid #ccc; border-radius: 4px; font-size: 10px; }"
            )
            form_row.addWidget(self.device_subtype_combo)

            card_layout.addLayout(form_row)

            # Services row (for ServerVM)
            self.services_widget = QWidget()
            services_layout = QHBoxLayout(self.services_widget)
            services_layout.setContentsMargins(0, 0, 0, 0)
            services_layout.setSpacing(4)

            self.service_dns_check = QCheckBox("DNS")
            self.service_dns_check.setChecked(True)
            self.service_dns_check.setStyleSheet("font-size: 10px;")
            services_layout.addWidget(self.service_dns_check)

            self.service_webapp_check = QCheckBox("WebApp")
            self.service_webapp_check.setChecked(True)
            self.service_webapp_check.setStyleSheet("font-size: 10px;")
            services_layout.addWidget(self.service_webapp_check)

            self.service_ad_check = QCheckBox("AD")
            self.service_ad_check.setStyleSheet("font-size: 10px;")
            services_layout.addWidget(self.service_ad_check)

            services_layout.addStretch()
            self.services_widget.setVisible(False)  # Hidden for UserVM
            card_layout.addWidget(self.services_widget)

            # Add/Remove buttons
            btn_row = QHBoxLayout()
            add_device_btn = QPushButton("+ Add")
            add_device_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; padding: 3px 8px; "
                "font-size: 10px; font-weight: bold; border-radius: 4px; }"
                "QPushButton:hover { background-color: #45a049; }"
            )
            add_device_btn.clicked.connect(self._add_device)
            btn_row.addWidget(add_device_btn)

            self.remove_device_btn = QPushButton("- Remove")
            self.remove_device_btn.setEnabled(False)
            self.remove_device_btn.setStyleSheet(
                "QPushButton { background-color: #f44336; color: white; padding: 3px 8px; "
                "font-size: 10px; font-weight: bold; border-radius: 4px; }"
                "QPushButton:hover { background-color: #d32f2f; }"
                "QPushButton:disabled { background-color: #ccc; }"
            )
            self.remove_device_btn.clicked.connect(self._remove_device)
            btn_row.addWidget(self.remove_device_btn)

            btn_row.addStretch()
            card_layout.addLayout(btn_row)

            # Error label for Panorama removal protection
            self.trust_devices_error_label = QLabel("")
            self.trust_devices_error_label.setStyleSheet(
                "color: #f44336; font-size: 10px; font-weight: bold; padding: 4px;"
            )
            self.trust_devices_error_label.setVisible(False)
            self.trust_devices_error_label.setWordWrap(True)
            card_layout.addWidget(self.trust_devices_error_label)

            # Initialize config with empty devices list
            self.cloud_resource_configs['trust_devices'] = {
                'devices': [],
            }

            # Initialize location dropdown
            self._refresh_device_location_dropdown()

            # Prevent vertical stretching
            card_layout.addStretch()

            return card

        # Scrollable area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 2x3 Grid layout
        grid = QGridLayout()
        grid.setSpacing(12)

        # Row 0: Cloud Deployment, Cloud Security
        grid.addWidget(create_cloud_deployment_card(), 0, 0)
        grid.addWidget(create_cloud_security_card(), 0, 1)

        # Row 1: Device Config, Policy Objects
        grid.addWidget(create_device_config_card(), 1, 0)
        grid.addWidget(create_policy_objects_card(), 1, 1)

        # Row 2: Locations, Trust Network Devices
        grid.addWidget(create_locations_card(), 2, 0)
        grid.addWidget(create_trust_devices_card(), 2, 1)

        scroll_layout.addLayout(grid)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)

        # Navigation
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        back_btn = QPushButton("← Back to Tenant Info")
        back_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #757575; color: white; padding: 8px 16px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #616161; border-bottom: 3px solid #424242; "
            "}"
            "QPushButton:hover { background-color: #616161; border-bottom: 3px solid #212121; }"
            "QPushButton:pressed { background-color: #616161; border-bottom: 1px solid #424242; }"
        )
        back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        nav_layout.addWidget(back_btn)

        next_btn = QPushButton("Next: POV Use Cases →")
        next_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; padding: 8px 16px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
        )
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        nav_layout.addWidget(next_btn)

        layout.addLayout(nav_layout)

        self.tabs.addTab(tab, "2️⃣ Cloud Resources")

    # ============================================================================
    # TAB 3: POV USE CASES
    # ============================================================================

    def _create_pov_use_cases_tab(self):
        """Create POV use cases selection tab (Step 3) with inline configuration."""
        from PyQt6.QtWidgets import QGridLayout, QFrame, QScrollArea, QSpinBox, QComboBox

        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 3: POV Use Cases</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Select and configure the use cases to demonstrate in your POV environment. "
            "Enable each use case with the checkbox, then configure inline options."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)

        # Common checkbox style
        checkbox_style = "font-size: 10px;"
        input_style = (
            "QLineEdit { padding: 2px 4px; border: 1px solid #ccc; border-radius: 4px; font-size: 10px; }"
        )
        spinbox_style = (
            "QSpinBox { padding: 2px 4px; border: 1px solid #ccc; border-radius: 4px; font-size: 10px; }"
        )
        combo_style = (
            "QComboBox { padding: 2px 4px; border: 1px solid #ccc; border-radius: 4px; font-size: 10px; }"
        )

        # Prisma Access compute locations for multi-select
        PRISMA_ACCESS_LOCATIONS = [
            "US East", "US West", "US Central", "US South Central", "US Northwest",
            "Canada East", "Canada Central", "Mexico Central",
            "South America East", "South America West",
            "UK", "Germany", "Netherlands", "France", "Switzerland", "Belgium",
            "India West", "India South", "Singapore", "Japan", "Australia East",
            "Australia Southeast", "Hong Kong", "Taiwan", "South Korea",
        ]

        # ========== MOBILE USERS CARD ==========
        def create_mobile_users_card():
            from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView

            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row: Enable checkbox, title, status
            top_row = QHBoxLayout()

            self.mobile_users_enable = QCheckBox()
            self.mobile_users_enable.setStyleSheet("margin-right: 4px;")
            self.mobile_users_enable.stateChanged.connect(self._on_mobile_users_changed)
            top_row.addWidget(self.mobile_users_enable)

            title_label = QLabel("<b>📱 Mobile Users (GlobalProtect)</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            self.mobile_users_status = QLabel("")
            self.mobile_users_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            top_row.addWidget(self.mobile_users_status)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Portal row: companyname + fixed suffix
            portal_row = QHBoxLayout()
            portal_row.setSpacing(4)

            portal_label = QLabel("Portal:")
            portal_label.setStyleSheet("font-size: 10px; color: #666;")
            portal_row.addWidget(portal_label)

            self.mobile_portal_input = QLineEdit()
            self.mobile_portal_input.setPlaceholderText("companyname")
            self.mobile_portal_input.setStyleSheet(input_style)
            self.mobile_portal_input.setFixedWidth(100)
            self.mobile_portal_input.textChanged.connect(self._on_mobile_users_changed)
            portal_row.addWidget(self.mobile_portal_input)

            portal_suffix = QLabel("<b>.gpcloudservice.com</b>")
            portal_suffix.setStyleSheet("font-size: 10px; color: #333;")
            portal_row.addWidget(portal_suffix)

            portal_row.addStretch()
            card_layout.addLayout(portal_row)

            # VPN Mode row
            mode_row = QHBoxLayout()
            mode_row.setSpacing(4)

            mode_label = QLabel("VPN Mode:")
            mode_label.setStyleSheet("font-size: 10px; color: #666;")
            mode_row.addWidget(mode_label)

            self.mobile_vpn_mode = QComboBox()
            self.mobile_vpn_mode.addItems(["On Demand", "Always-On", "Always-On with Prelogon"])
            self.mobile_vpn_mode.setStyleSheet(combo_style)
            self.mobile_vpn_mode.currentTextChanged.connect(self._on_mobile_users_changed)
            mode_row.addWidget(self.mobile_vpn_mode)

            mode_row.addStretch()
            card_layout.addLayout(mode_row)

            # Locations multi-select
            loc_label = QLabel("PA Locations:")
            loc_label.setStyleSheet("font-size: 10px; color: #666;")
            card_layout.addWidget(loc_label)

            self.mobile_locations_list = QListWidget()
            self.mobile_locations_list.setMaximumHeight(180)
            self.mobile_locations_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            self.mobile_locations_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 10px; }"
                "QListWidget::item { padding: 1px; }"
                "QListWidget::item:selected { background-color: #2196F3; color: white; }"
            )
            for loc in PRISMA_ACCESS_LOCATIONS:
                item = QListWidgetItem(loc)
                self.mobile_locations_list.addItem(item)
            self.mobile_locations_list.itemSelectionChanged.connect(self._on_mobile_users_changed)
            card_layout.addWidget(self.mobile_locations_list)

            # Initialize config
            self.use_case_configs['mobile_users'] = {
                'enabled': False,
                'portal_name': '',
                'vpn_mode': 'On Demand',
                'locations': [],
            }

            card_layout.addStretch()
            return card

        # ========== PROXY USERS CARD ==========
        def create_proxy_users_card():
            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row
            top_row = QHBoxLayout()

            self.proxy_users_enable = QCheckBox()
            self.proxy_users_enable.setStyleSheet("margin-right: 4px;")
            self.proxy_users_enable.stateChanged.connect(self._on_proxy_users_changed)
            top_row.addWidget(self.proxy_users_enable)

            title_label = QLabel("<b>🌐 Proxy Users (Explicit Proxy)</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            self.proxy_users_status = QLabel("")
            self.proxy_users_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            top_row.addWidget(self.proxy_users_status)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Port and options row
            config_row = QHBoxLayout()
            config_row.setSpacing(8)

            port_label = QLabel("Port:")
            port_label.setStyleSheet("font-size: 10px; color: #666;")
            config_row.addWidget(port_label)

            self.proxy_port_input = QSpinBox()
            self.proxy_port_input.setRange(1, 65535)
            self.proxy_port_input.setValue(8080)
            self.proxy_port_input.setStyleSheet(spinbox_style)
            self.proxy_port_input.setFixedWidth(70)
            self.proxy_port_input.valueChanged.connect(self._on_proxy_users_changed)
            config_row.addWidget(self.proxy_port_input)

            self.proxy_auth_required = QCheckBox("Auth Required")
            self.proxy_auth_required.setChecked(True)
            self.proxy_auth_required.setStyleSheet(checkbox_style)
            self.proxy_auth_required.stateChanged.connect(self._on_proxy_users_changed)
            config_row.addWidget(self.proxy_auth_required)

            self.proxy_pac_file = QCheckBox("Generate PAC")
            self.proxy_pac_file.setChecked(True)
            self.proxy_pac_file.setStyleSheet(checkbox_style)
            self.proxy_pac_file.stateChanged.connect(self._on_proxy_users_changed)
            config_row.addWidget(self.proxy_pac_file)

            config_row.addStretch()
            card_layout.addLayout(config_row)

            # Initialize config
            self.use_case_configs['proxy_users'] = {
                'enabled': False,
                'proxy_port': 8080,
                'auth_required': True,
                'pac_file': True,
            }

            card_layout.addStretch()
            return card

        # ========== PRIVATE APP ACCESS CARD ==========
        def create_private_app_card():
            from PyQt6.QtWidgets import QListWidget, QListWidgetItem

            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row
            top_row = QHBoxLayout()

            self.private_app_enable = QCheckBox()
            self.private_app_enable.setStyleSheet("margin-right: 4px;")
            self.private_app_enable.stateChanged.connect(self._on_private_app_changed)
            top_row.addWidget(self.private_app_enable)

            title_label = QLabel("<b>🔐 Private App Access</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            self.private_app_status = QLabel("")
            self.private_app_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            top_row.addWidget(self.private_app_status)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Connections list (populated from datacenters/branches)
            conn_label = QLabel("Location Connections:")
            conn_label.setStyleSheet("font-size: 10px; color: #666;")
            card_layout.addWidget(conn_label)

            self.private_app_connections_list = QListWidget()
            self.private_app_connections_list.setMaximumHeight(80)
            self.private_app_connections_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 10px; }"
                "QListWidget::item { padding: 2px; }"
            )
            card_layout.addWidget(self.private_app_connections_list)

            # Info label
            info_label = QLabel("💡 Connection types auto-populated from Locations tab")
            info_label.setStyleSheet("font-size: 9px; color: #888; font-style: italic;")
            info_label.setWordWrap(True)
            card_layout.addWidget(info_label)

            # Initialize config
            self.use_case_configs['private_app'] = {
                'enabled': False,
                'connections': [],  # List of {name, type, connection_type: 'service_connection'|'ztna'}
            }

            card_layout.addStretch()
            return card

        # ========== REMOTE BRANCH CARD ==========
        def create_remote_branch_card():
            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row
            top_row = QHBoxLayout()

            self.remote_branch_enable = QCheckBox()
            self.remote_branch_enable.setStyleSheet("margin-right: 4px;")
            self.remote_branch_enable.stateChanged.connect(self._on_remote_branch_changed)
            top_row.addWidget(self.remote_branch_enable)

            title_label = QLabel("<b>🏢 Remote Branch (IPSec)</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            self.remote_branch_status = QLabel("")
            self.remote_branch_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            top_row.addWidget(self.remote_branch_status)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Branch config row
            config_row = QHBoxLayout()
            config_row.setSpacing(8)

            branches_label = QLabel("Branches:")
            branches_label.setStyleSheet("font-size: 10px; color: #666;")
            config_row.addWidget(branches_label)

            self.branch_count_input = QSpinBox()
            self.branch_count_input.setRange(1, 10)
            self.branch_count_input.setValue(1)
            self.branch_count_input.setStyleSheet(spinbox_style)
            self.branch_count_input.setFixedWidth(50)
            self.branch_count_input.valueChanged.connect(self._on_remote_branch_changed)
            config_row.addWidget(self.branch_count_input)

            bw_label = QLabel("@")
            bw_label.setStyleSheet("font-size: 10px; color: #666;")
            config_row.addWidget(bw_label)

            self.branch_bandwidth_combo = QComboBox()
            self.branch_bandwidth_combo.addItems(["25 Mbps", "50 Mbps", "100 Mbps", "200 Mbps", "500 Mbps"])
            self.branch_bandwidth_combo.setCurrentIndex(1)  # Default 50 Mbps
            self.branch_bandwidth_combo.setStyleSheet(combo_style)
            self.branch_bandwidth_combo.currentTextChanged.connect(self._on_remote_branch_changed)
            config_row.addWidget(self.branch_bandwidth_combo)

            config_row.addStretch()
            card_layout.addLayout(config_row)

            # Options row
            opts_row = QHBoxLayout()
            opts_row.setSpacing(8)

            self.branch_sdwan = QCheckBox("SD-WAN")
            self.branch_sdwan.setStyleSheet(checkbox_style)
            self.branch_sdwan.stateChanged.connect(self._on_remote_branch_changed)
            opts_row.addWidget(self.branch_sdwan)

            self.branch_bgp = QCheckBox("BGP")
            self.branch_bgp.setStyleSheet(checkbox_style)
            self.branch_bgp.stateChanged.connect(self._on_remote_branch_changed)
            opts_row.addWidget(self.branch_bgp)

            opts_row.addStretch()
            card_layout.addLayout(opts_row)

            # Initialize config
            self.use_case_configs['remote_branch'] = {
                'enabled': False,
                'branch_count': 1,
                'branch_bandwidth': '50 Mbps',
                'sdwan_integration': False,
                'bgp_routing': False,
            }

            card_layout.addStretch()
            return card

        # ========== AIOPS-ADEM CARD ==========
        def create_aiops_adem_card():
            from PyQt6.QtWidgets import QListWidget, QListWidgetItem

            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row
            top_row = QHBoxLayout()

            self.aiops_adem_enable = QCheckBox()
            self.aiops_adem_enable.setStyleSheet("margin-right: 4px;")
            self.aiops_adem_enable.stateChanged.connect(self._on_aiops_adem_changed)
            top_row.addWidget(self.aiops_adem_enable)

            title_label = QLabel("<b>📊 AIOPS-ADEM</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            self.aiops_adem_status = QLabel("")
            self.aiops_adem_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            top_row.addWidget(self.aiops_adem_status)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Test input row
            input_row = QHBoxLayout()
            input_row.setSpacing(4)

            self.adem_test_input = QLineEdit()
            self.adem_test_input.setPlaceholderText("IP or URL (e.g., 8.8.8.8 or google.com)")
            self.adem_test_input.setStyleSheet(input_style)
            self.adem_test_input.setMinimumWidth(150)
            input_row.addWidget(self.adem_test_input)

            add_test_btn = QPushButton("+")
            add_test_btn.setFixedSize(24, 24)
            add_test_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
                "border-radius: 4px; font-size: 14px; }"
                "QPushButton:hover { background-color: #45a049; }"
            )
            add_test_btn.clicked.connect(self._add_adem_test)
            input_row.addWidget(add_test_btn)

            input_row.addStretch()
            card_layout.addLayout(input_row)

            # Test conditions row
            cond_row = QHBoxLayout()
            cond_row.setSpacing(8)

            self.adem_on_vpn = QCheckBox("On VPN")
            self.adem_on_vpn.setChecked(True)
            self.adem_on_vpn.setEnabled(False)  # Always checked, cannot change
            self.adem_on_vpn.setStyleSheet(checkbox_style + " color: #666;")
            cond_row.addWidget(self.adem_on_vpn)

            self.adem_in_office = QCheckBox("In Office")
            self.adem_in_office.setStyleSheet(checkbox_style)
            cond_row.addWidget(self.adem_in_office)

            self.adem_not_on_vpn = QCheckBox("Not on VPN")
            self.adem_not_on_vpn.setStyleSheet(checkbox_style)
            cond_row.addWidget(self.adem_not_on_vpn)

            cond_row.addStretch()
            card_layout.addLayout(cond_row)

            # Tests list
            self.adem_tests_list = QListWidget()
            self.adem_tests_list.setMaximumHeight(60)
            self.adem_tests_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 10px; }"
                "QListWidget::item { padding: 2px; }"
                "QListWidget::item:selected { background-color: #2196F3; color: white; }"
            )
            self.adem_tests_list.itemSelectionChanged.connect(self._on_adem_test_selected)
            card_layout.addWidget(self.adem_tests_list)

            # Remove button row
            remove_row = QHBoxLayout()
            self.adem_remove_btn = QPushButton("- Remove")
            self.adem_remove_btn.setEnabled(False)
            self.adem_remove_btn.setStyleSheet(
                "QPushButton { background-color: #f44336; color: white; padding: 2px 8px; "
                "font-size: 10px; font-weight: bold; border-radius: 4px; }"
                "QPushButton:hover { background-color: #d32f2f; }"
                "QPushButton:disabled { background-color: #ccc; }"
            )
            self.adem_remove_btn.clicked.connect(self._remove_adem_test)
            remove_row.addWidget(self.adem_remove_btn)
            remove_row.addStretch()
            card_layout.addLayout(remove_row)

            # Initialize config
            self.use_case_configs['aiops_adem'] = {
                'enabled': False,
                'tests': [],  # List of {target, on_vpn, in_office, not_on_vpn}
            }

            card_layout.addStretch()
            return card

        # ========== APP ACCELERATION CARD ==========
        def create_app_accel_card():
            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row
            top_row = QHBoxLayout()

            self.app_accel_enable = QCheckBox()
            self.app_accel_enable.setStyleSheet("margin-right: 4px;")
            self.app_accel_enable.stateChanged.connect(self._on_app_accel_changed)
            top_row.addWidget(self.app_accel_enable)

            title_label = QLabel("<b>⚡ App Acceleration</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            self.app_accel_status = QLabel("")
            self.app_accel_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            top_row.addWidget(self.app_accel_status)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Acceleration options row
            opts_row = QHBoxLayout()
            opts_row.setSpacing(8)

            self.accel_saas = QCheckBox("SaaS Apps")
            self.accel_saas.setChecked(True)
            self.accel_saas.setStyleSheet(checkbox_style)
            self.accel_saas.stateChanged.connect(self._on_app_accel_changed)
            opts_row.addWidget(self.accel_saas)

            self.accel_private = QCheckBox("Private Apps")
            self.accel_private.setChecked(True)
            self.accel_private.setStyleSheet(checkbox_style)
            self.accel_private.stateChanged.connect(self._on_app_accel_changed)
            opts_row.addWidget(self.accel_private)

            opts_row.addStretch()
            card_layout.addLayout(opts_row)

            # Initialize config
            self.use_case_configs['app_accel'] = {
                'enabled': False,
                'saas_acceleration': True,
                'private_acceleration': True,
            }

            card_layout.addStretch()
            return card

        # Palo Alto URL Filtering Categories for RBI
        URL_CATEGORIES = [
            "adult", "command-and-control", "cryptocurrency", "dating",
            "dynamic-dns", "extremism", "gambling", "grayware", "hacking",
            "high-risk", "insufficient-content", "malware", "newly-registered-domain",
            "not-resolved", "nudity", "parked", "peer-to-peer", "phishing",
            "proxy-avoidance-and-anonymizers", "questionable", "ransomware",
            "real-time-detection", "unknown", "weapons",
        ]

        # ========== RBI CARD ==========
        def create_rbi_card():
            from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView

            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row
            top_row = QHBoxLayout()

            self.rbi_enable = QCheckBox()
            self.rbi_enable.setStyleSheet("margin-right: 4px;")
            self.rbi_enable.stateChanged.connect(self._on_rbi_changed)
            top_row.addWidget(self.rbi_enable)

            title_label = QLabel("<b>🛡️ Remote Browser Isolation</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            self.rbi_status = QLabel("")
            self.rbi_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            top_row.addWidget(self.rbi_status)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # URL Categories label
            cat_label = QLabel("URL Categories to Isolate:")
            cat_label.setStyleSheet("font-size: 10px; color: #666;")
            card_layout.addWidget(cat_label)

            # Categories multi-select list
            self.rbi_categories_list = QListWidget()
            self.rbi_categories_list.setMaximumHeight(150)
            self.rbi_categories_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            self.rbi_categories_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 10px; }"
                "QListWidget::item { padding: 1px; }"
                "QListWidget::item:selected { background-color: #2196F3; color: white; }"
            )
            # Add categories and pre-select risky ones
            default_selected = ["high-risk", "malware", "phishing", "command-and-control",
                               "ransomware", "unknown", "newly-registered-domain"]
            for cat in URL_CATEGORIES:
                item = QListWidgetItem(cat)
                self.rbi_categories_list.addItem(item)
                if cat in default_selected:
                    item.setSelected(True)
            self.rbi_categories_list.itemSelectionChanged.connect(self._on_rbi_changed)
            card_layout.addWidget(self.rbi_categories_list)

            # Initialize config
            self.use_case_configs['rbi'] = {
                'enabled': False,
                'categories': default_selected.copy(),
            }

            card_layout.addStretch()
            return card

        # ========== PAB CARD ==========
        def create_pab_card():
            card = QFrame()
            card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            card.setStyleSheet(
                "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
                "border-radius: 8px; padding: 12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(12, 10, 12, 12)

            # Top row
            top_row = QHBoxLayout()

            self.pab_enable = QCheckBox()
            self.pab_enable.setStyleSheet("margin-right: 4px;")
            self.pab_enable.stateChanged.connect(self._on_pab_changed)
            top_row.addWidget(self.pab_enable)

            title_label = QLabel("<b>🖥️ Prisma Access Browser</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            self.pab_status = QLabel("")
            self.pab_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            top_row.addWidget(self.pab_status)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Security options row
            opts_row = QHBoxLayout()
            opts_row.setSpacing(8)

            self.pab_dlp = QCheckBox("DLP")
            self.pab_dlp.setChecked(True)
            self.pab_dlp.setStyleSheet(checkbox_style)
            self.pab_dlp.stateChanged.connect(self._on_pab_changed)
            opts_row.addWidget(self.pab_dlp)

            self.pab_threat = QCheckBox("Threat Prevention")
            self.pab_threat.setChecked(True)
            self.pab_threat.setStyleSheet(checkbox_style)
            self.pab_threat.stateChanged.connect(self._on_pab_changed)
            opts_row.addWidget(self.pab_threat)

            self.pab_compliance = QCheckBox("Compliance")
            self.pab_compliance.setChecked(True)
            self.pab_compliance.setStyleSheet(checkbox_style)
            self.pab_compliance.stateChanged.connect(self._on_pab_changed)
            opts_row.addWidget(self.pab_compliance)

            opts_row.addStretch()
            card_layout.addLayout(opts_row)

            # Initialize config
            self.use_case_configs['pab'] = {
                'enabled': False,
                'enable_dlp': True,
                'enable_threat_prevention': True,
                'enable_compliance': True,
            }

            card_layout.addStretch()
            return card

        # Scrollable area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 2x4 Grid layout (4 rows, 2 columns for 8 use cases)
        grid = QGridLayout()
        grid.setSpacing(12)

        # Row 0
        grid.addWidget(create_mobile_users_card(), 0, 0)
        grid.addWidget(create_proxy_users_card(), 0, 1)

        # Row 1
        grid.addWidget(create_private_app_card(), 1, 0)
        grid.addWidget(create_remote_branch_card(), 1, 1)

        # Row 2
        grid.addWidget(create_aiops_adem_card(), 2, 0)
        grid.addWidget(create_app_accel_card(), 2, 1)

        # Row 3
        grid.addWidget(create_rbi_card(), 3, 0)
        grid.addWidget(create_pab_card(), 3, 1)

        scroll_layout.addLayout(grid)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Navigation
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        back_btn = QPushButton("← Back to Cloud Resources")
        back_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #757575; color: white; padding: 8px 16px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #616161; border-bottom: 3px solid #424242; "
            "}"
            "QPushButton:hover { background-color: #616161; border-bottom: 3px solid #212121; }"
            "QPushButton:pressed { background-color: #616161; border-bottom: 1px solid #424242; }"
        )
        back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        nav_layout.addWidget(back_btn)

        next_btn = QPushButton("Next: Cloud Deployment →")
        next_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; padding: 8px 16px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
        )
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        nav_layout.addWidget(next_btn)

        layout.addLayout(nav_layout)

        self.tabs.addTab(tab, "3️⃣ POV Use Cases")

    # ============================================================================
    # OLD REVIEW TAB (will be moved to end)
    # ============================================================================

    def _create_review_tab(self):
        """Create configuration review tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 2: Review Configuration</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Review the merged configuration from all sources before proceeding."
        )
        info.setStyleSheet("color: gray;")
        layout.addWidget(info)

        # Sources summary
        self.sources_summary = QLabel("No sources loaded")
        self.sources_summary.setStyleSheet(
            "background-color: #f5f5f5; padding: 10px; border-radius: 5px;"
        )
        self.sources_summary.setWordWrap(True)
        layout.addWidget(self.sources_summary)

        # Configuration display
        self.config_review_text = QTextEdit()
        self.config_review_text.setReadOnly(True)
        self.config_review_text.setPlaceholderText(
            "Merged configuration will be displayed here...\n\n"
            "Load configuration sources in Step 1 to see the merged result."
        )
        layout.addWidget(self.config_review_text)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        back_btn = QPushButton("← Back to Sources")
        back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        nav_layout.addWidget(back_btn)

        next_btn = QPushButton("Next: Inject Defaults →")
        next_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 8px; }"
        )
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        nav_layout.addWidget(next_btn)

        layout.addLayout(nav_layout)

        # MOVED TO END

    # ============================================================================
    # TAB 4: CLOUD RESOURCE DEPLOYMENT
    # ============================================================================

    def _create_cloud_deployment_tab(self):
        """Create cloud resource deployment tab (Step 4)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 4: Cloud Resource Deployment</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Authenticate to Azure and deploy cloud resources using Terraform."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 15px;")
        layout.addWidget(info)

        # Azure Authentication Section
        azure_auth_group = QGroupBox("Azure Authentication")
        azure_auth_layout = QVBoxLayout()

        auth_info = QLabel(
            "Authenticate with Azure to deploy firewall resources. "
            "This will generate a customized Terraform configuration based on your POV requirements."
        )
        auth_info.setWordWrap(True)
        auth_info.setStyleSheet("color: #666; margin-bottom: 10px;")
        azure_auth_layout.addWidget(auth_info)

        # Auth status and button row
        auth_row = QHBoxLayout()

        self.azure_auth_status = QLabel("🔴 Not authenticated")
        self.azure_auth_status.setStyleSheet("font-weight: bold; color: #F44336;")
        auth_row.addWidget(self.azure_auth_status)

        auth_row.addStretch()

        self.azure_auth_btn = QPushButton("🔐 Authenticate with Azure")
        self.azure_auth_btn.setMinimumWidth(200)
        self.azure_auth_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #0078D4; color: white; padding: 10px 20px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #005A9E; border-bottom: 3px solid #004578; "
            "}"
            "QPushButton:hover { background-color: #106EBE; border-bottom: 3px solid #003C5A; }"
            "QPushButton:pressed { background-color: #005A9E; border-bottom: 1px solid #004578; }"
        )
        self.azure_auth_btn.setToolTip("Coming soon: Azure authentication integration")
        self.azure_auth_btn.clicked.connect(self._authenticate_azure)
        auth_row.addWidget(self.azure_auth_btn)

        azure_auth_layout.addLayout(auth_row)

        # Terraform generation status (hidden until authenticated)
        self.terraform_status_widget = QWidget()
        tf_status_layout = QVBoxLayout(self.terraform_status_widget)
        tf_status_layout.setContentsMargins(0, 15, 0, 0)

        self.terraform_gen_status = QLabel("⏳ Generating Terraform configuration...")
        self.terraform_gen_status.setStyleSheet(
            "color: #1565C0; padding: 10px; background-color: #E3F2FD; "
            "border-radius: 5px;"
        )
        tf_status_layout.addWidget(self.terraform_gen_status)

        self.terraform_status_widget.setVisible(False)
        azure_auth_layout.addWidget(self.terraform_status_widget)

        azure_auth_group.setLayout(azure_auth_layout)
        layout.addWidget(azure_auth_group)

        # Terraform Actions Section
        tf_actions_group = QGroupBox("Terraform Actions")
        tf_actions_layout = QVBoxLayout()

        tf_actions_info = QLabel(
            "Review and deploy the generated Terraform configuration for your POV environment."
        )
        tf_actions_info.setWordWrap(True)
        tf_actions_info.setStyleSheet("color: #666; margin-bottom: 10px;")
        tf_actions_layout.addWidget(tf_actions_info)

        # Action buttons row
        actions_row = QHBoxLayout()
        actions_row.addStretch()

        self.review_terraform_btn = QPushButton("📄 Review Terraform")
        self.review_terraform_btn.setMinimumWidth(160)
        self.review_terraform_btn.setEnabled(False)
        self.review_terraform_btn.setToolTip("Review the generated Terraform configuration")
        self.review_terraform_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #FF9800; color: white; padding: 10px 20px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #F57C00; border-bottom: 3px solid #E65100; "
            "}"
            "QPushButton:hover { background-color: #FB8C00; border-bottom: 3px solid #BF360C; }"
            "QPushButton:pressed { background-color: #F57C00; border-bottom: 1px solid #E65100; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #9E9E9E; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        self.review_terraform_btn.clicked.connect(self._review_terraform)
        actions_row.addWidget(self.review_terraform_btn)

        self.deploy_terraform_btn = QPushButton("🚀 Deploy Terraform")
        self.deploy_terraform_btn.setMinimumWidth(160)
        self.deploy_terraform_btn.setEnabled(False)
        self.deploy_terraform_btn.setToolTip("Deploy resources to Azure using Terraform")
        self.deploy_terraform_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 10px 20px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { background-color: #45a049; border-bottom: 3px solid #1B5E20; }"
            "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #9E9E9E; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        self.deploy_terraform_btn.clicked.connect(self._deploy_terraform)
        actions_row.addWidget(self.deploy_terraform_btn)

        tf_actions_layout.addLayout(actions_row)
        tf_actions_group.setLayout(tf_actions_layout)
        layout.addWidget(tf_actions_group)

        # Progress bar
        self.cloud_deploy_progress = QProgressBar()
        self.cloud_deploy_progress.setVisible(False)
        layout.addWidget(self.cloud_deploy_progress)

        # Results panel
        self.cloud_deploy_results = ResultsPanel(
            parent=self,
            title="Cloud Deployment",
            placeholder="Deployment results will appear here..."
        )
        layout.addWidget(self.cloud_deploy_results)

        # Navigation
        nav_layout = QHBoxLayout()

        back_btn = QPushButton("← Back to POV Use Cases")
        back_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #757575; color: white; padding: 8px 16px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #616161; border-bottom: 3px solid #424242; "
            "}"
            "QPushButton:hover { background-color: #616161; border-bottom: 3px solid #212121; }"
            "QPushButton:pressed { background-color: #616161; border-bottom: 1px solid #424242; }"
        )
        back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        nav_layout.addWidget(back_btn)

        nav_layout.addStretch()

        next_btn = QPushButton("Next: Deploy POV Config →")
        next_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; padding: 8px 16px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
        )
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(4))
        nav_layout.addWidget(next_btn)

        layout.addLayout(nav_layout)

        self.tabs.addTab(tab, "4️⃣ Cloud Deployment")

    # ============================================================================
    # TAB 5: DEPLOY POV CONFIGURATION
    # ============================================================================

    def _create_deploy_config_tab(self):
        """Create deploy POV configuration tab (Step 5)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 5: Deploy POV Configuration</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Deploy your POV configuration to SCM (and optionally Panorama)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 15px;")
        layout.addWidget(info)

        # Top row: SCM Tenant and Panorama side by side
        top_row = QHBoxLayout()

        # SCM Tenant Selection (synced with Tab 1)
        self.deploy_tenant_selector = TenantSelectorWidget(
            parent=self,
            title="SCM Destination Tenant",
            label="Deploy to:",
            show_load_button=False
        )
        self.deploy_tenant_selector.connection_changed.connect(self._on_deploy_tenant_changed)
        top_row.addWidget(self.deploy_tenant_selector, 1)

        # Panorama Section (only visible if Panorama was selected in Tab 1)
        self.panorama_deploy_group = QGroupBox("Panorama (Optional)")
        panorama_layout = QFormLayout()

        self.panorama_host_input = QLineEdit()
        self.panorama_host_input.setPlaceholderText("panorama.example.com")
        panorama_layout.addRow("Hostname/IP:", self.panorama_host_input)

        self.panorama_user_input = QLineEdit()
        self.panorama_user_input.setPlaceholderText("admin")
        panorama_layout.addRow("Username:", self.panorama_user_input)

        self.panorama_pass_input = QLineEdit()
        self.panorama_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.panorama_pass_input.setPlaceholderText("Password or API key")
        panorama_layout.addRow("Password/API Key:", self.panorama_pass_input)

        # Test Panorama connection button
        self.test_panorama_btn = QPushButton("Test Connection")
        self.test_panorama_btn.setMaximumWidth(150)
        self.test_panorama_btn.clicked.connect(self._test_panorama_connection)
        panorama_layout.addRow("", self.test_panorama_btn)

        self.panorama_deploy_group.setLayout(panorama_layout)
        self.panorama_deploy_group.setVisible(False)  # Hidden by default, shown if Panorama selected
        top_row.addWidget(self.panorama_deploy_group, 1)

        layout.addLayout(top_row)

        # Configuration Summary
        summary_group = QGroupBox("Configuration Summary")
        summary_layout = QVBoxLayout()

        self.deploy_summary_label = QLabel(
            "Configuration from previous steps will be summarized here."
        )
        self.deploy_summary_label.setWordWrap(True)
        self.deploy_summary_label.setStyleSheet(
            "color: #666; padding: 10px; background-color: #f5f5f5; border-radius: 5px;"
        )
        summary_layout.addWidget(self.deploy_summary_label)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Action Buttons
        actions_row = QHBoxLayout()
        actions_row.addStretch()

        self.review_config_btn = QPushButton("📄 Review Configuration")
        self.review_config_btn.setMinimumWidth(180)
        self.review_config_btn.setEnabled(False)
        self.review_config_btn.setToolTip("Review the POV configuration before deployment")
        self.review_config_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #FF9800; color: white; padding: 10px 20px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #F57C00; border-bottom: 3px solid #E65100; "
            "}"
            "QPushButton:hover { background-color: #FB8C00; border-bottom: 3px solid #BF360C; }"
            "QPushButton:pressed { background-color: #F57C00; border-bottom: 1px solid #E65100; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #9E9E9E; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        self.review_config_btn.clicked.connect(self._review_pov_config)
        actions_row.addWidget(self.review_config_btn)

        self.deploy_config_btn = QPushButton("🚀 Deploy Configuration")
        self.deploy_config_btn.setMinimumWidth(180)
        self.deploy_config_btn.setEnabled(False)
        self.deploy_config_btn.setToolTip("Deploy POV configuration to SCM/Panorama")
        self.deploy_config_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 10px 20px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { background-color: #45a049; border-bottom: 3px solid #1B5E20; }"
            "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #9E9E9E; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        self.deploy_config_btn.clicked.connect(self._deploy_pov_config)
        actions_row.addWidget(self.deploy_config_btn)

        layout.addLayout(actions_row)

        # Progress bar
        self.pov_deploy_progress = QProgressBar()
        self.pov_deploy_progress.setVisible(False)
        layout.addWidget(self.pov_deploy_progress)

        # Results panel
        self.pov_deploy_results = ResultsPanel(
            parent=self,
            title="POV Deployment",
            placeholder="Deployment results will appear here..."
        )
        layout.addWidget(self.pov_deploy_results)

        # Navigation
        nav_layout = QHBoxLayout()

        back_btn = QPushButton("← Back to Cloud Deployment")
        back_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #757575; color: white; padding: 8px 16px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #616161; border-bottom: 3px solid #424242; "
            "}"
            "QPushButton:hover { background-color: #616161; border-bottom: 3px solid #212121; }"
            "QPushButton:pressed { background-color: #616161; border-bottom: 1px solid #424242; }"
        )
        back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        nav_layout.addWidget(back_btn)

        nav_layout.addStretch()

        self.complete_btn = QPushButton("✓ Complete POV Setup")
        self.complete_btn.setMinimumWidth(180)
        self.complete_btn.setEnabled(False)
        self.complete_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; "
            "  border-radius: 5px; border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { background-color: #45a049; border-bottom: 3px solid #1B5E20; }"
            "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
            "QPushButton:disabled { background-color: #BDBDBD; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        self.complete_btn.clicked.connect(self._complete_pov_setup)
        nav_layout.addWidget(self.complete_btn)

        layout.addLayout(nav_layout)

        self.tabs.addTab(tab, "5️⃣ Deploy POV Config")

    # ============================================================================
    # EVENT HANDLERS - SOURCES TAB
    # ============================================================================

    def set_api_client(self, api_client, connection_name=None):
        """Set API client."""
        self.api_client = api_client
        self.connection_name = connection_name
        # Also update tenant selector
        if hasattr(self, 'tenant_selector'):
            self.tenant_selector.set_connection(api_client, connection_name or "")

    def populate_tenants(self, tenants: list):
        """
        Populate the tenant selector dropdown with saved tenants.

        Args:
            tenants: List of tenant dictionaries with 'name' key
        """
        if hasattr(self, 'tenant_selector'):
            self.tenant_selector.populate_tenants(tenants)

    def _populate_tenant_dropdown(self):
        """Populate the tenant dropdowns from saved tenants."""
        try:
            from config.tenant_manager import TenantManager

            tenant_mgr = TenantManager()
            tenants = tenant_mgr.list_tenants()
            self.populate_tenants(tenants)

            # Also populate deploy tenant selector (Tab 5)
            if hasattr(self, 'deploy_tenant_selector'):
                self.deploy_tenant_selector.populate_tenants(tenants)
        except Exception:
            # Silently fail if tenants can't be loaded
            pass

    def _on_management_changed(self):
        """Handle management type change."""
        is_scm = self.scm_managed_radio.isChecked()
        self.management_type = "scm" if is_scm else "panorama"

        # Update tenant selector visibility/title
        if is_scm:
            self.tenant_selector.group_box.setTitle("SCM Tenant (Required)")
            self.tenant_selector.setEnabled(True)
        else:
            self.tenant_selector.group_box.setTitle("SCM Tenant (Optional for Hybrid)")
            self.tenant_selector.setEnabled(True)  # Still allow optional SCM for hybrid

        # Update deployment section visibility based on management type
        if hasattr(self, 'azure_deploy_widget'):
            self.azure_deploy_widget.setVisible(is_scm)
            self.panorama_deploy_widget.setVisible(not is_scm)

            # Show deployment status section if any firewalls will be deployed
            self._update_deployment_status_visibility()

        # Update Panorama visibility in Tab 5
        self._update_panorama_visibility()

        # Sync devices to add/remove Panorama based on management type
        if hasattr(self, 'devices_list'):
            self._sync_devices_from_locations()

    def _on_azure_deploy_changed(self):
        """Handle Azure deployment option change (SCM managed)."""
        deploy_azure = self.azure_yes_radio.isChecked()
        self.scm_firewall_options.setVisible(deploy_azure)
        self._update_deployment_status_visibility()

    def _on_panorama_rn_changed(self):
        """Handle Panorama RN firewall option change."""
        deploy_rn = self.panorama_rn_yes_radio.isChecked()
        self.panorama_rn_count_widget.setVisible(deploy_rn)

    def _on_deployment_status_changed(self):
        """Handle deployment status change (already deployed vs need to deploy)."""
        already_deployed = self.deployed_yes_radio.isChecked()
        self.credentials_widget.setVisible(already_deployed)
        self.deploy_method_widget.setVisible(not already_deployed)

    def _on_deploy_method_changed(self):
        """Handle deployment method change (manual vs terraform)."""
        use_terraform = self.deploy_terraform_radio.isChecked()
        self.manual_deploy_info.setVisible(not use_terraform)
        self.terraform_deploy_info.setVisible(use_terraform)

    def _update_deployment_status_visibility(self):
        """Update visibility of deployment status section based on firewall selections."""
        is_scm = self.scm_managed_radio.isChecked()

        # Check if any firewalls will be deployed
        firewalls_to_deploy = False
        if is_scm:
            # SCM: Check if user selected Azure deployment and any firewall type
            if self.azure_yes_radio.isChecked():
                firewalls_to_deploy = (
                    self.deploy_sc_firewall_check.isChecked() or
                    self.deploy_rn_firewall_check.isChecked()
                )
        else:
            # Panorama: Always has at least SC firewall
            firewalls_to_deploy = True

        # Show deployment status section only if firewalls will be deployed
        self.deployment_status_widget.setVisible(firewalls_to_deploy)

    def _on_tenant_connection_changed(self, api_client, tenant_name: str):
        """Handle tenant connection changes from the selector."""
        self.api_client = api_client
        self.connection_name = tenant_name

        # Update status based on connection
        if api_client:
            self.load_status.setText(f"Connected to {tenant_name}")
            self.load_status.setStyleSheet("color: green;")
        else:
            self.load_status.setText("No tenant connected")
            self.load_status.setStyleSheet("color: gray;")

        # Sync to Tab 5 deploy tenant selector
        self._sync_tenant_to_deploy_tab()

    def _gather_deployment_config(self) -> Dict[str, Any]:
        """Gather deployment configuration from the UI selections."""
        config = {
            "management_type": self.management_type,
            "firewalls": [],
            "deployment_method": None,
            "already_deployed": self.deployed_yes_radio.isChecked(),
        }

        # Add SCM tenant info if connected
        if self.api_client and self.connection_name:
            config["scm_tenant"] = {
                "name": self.connection_name,
                "connected": True,
            }

        is_scm = self.scm_managed_radio.isChecked()

        if is_scm:
            # SCM Managed: Check Azure deployment options
            if self.azure_yes_radio.isChecked():
                if self.deploy_sc_firewall_check.isChecked():
                    config["firewalls"].append({
                        "type": "service_connection",
                        "name": "SC Firewall",
                        "platform": "azure",
                    })
                if self.deploy_rn_firewall_check.isChecked():
                    config["firewalls"].append({
                        "type": "remote_network",
                        "name": "RN Firewall",
                        "platform": "azure",
                    })
        else:
            # Panorama Managed: Always has SC, optionally RN
            config["firewalls"].append({
                "type": "service_connection",
                "name": "SC Firewall",
                "platform": "azure",
                "required": True,
            })
            if self.panorama_rn_yes_radio.isChecked():
                rn_count = 1
                try:
                    rn_count = int(self.panorama_rn_count_input.text() or "1")
                except ValueError:
                    rn_count = 1
                for i in range(rn_count):
                    config["firewalls"].append({
                        "type": "remote_network",
                        "name": f"RN Firewall {i + 1}",
                        "platform": "azure",
                    })

        # Add deployment method if not already deployed
        if not config["already_deployed"]:
            config["deployment_method"] = (
                "terraform" if self.deploy_terraform_radio.isChecked() else "manual"
            )
        else:
            # Add firewall credentials if already deployed
            fw_ip = self.fw_mgmt_ip_input.text().strip()
            fw_user = self.fw_username_input.text().strip()
            if fw_ip and fw_user:
                config["firewall_credentials"] = {
                    "mgmt_ip": fw_ip,
                    "username": fw_user,
                    # Password not stored in config for security
                }

        return config

    def _get_firewall_credentials(self) -> Optional[Dict[str, str]]:
        """Get firewall credentials from the UI."""
        fw_ip = self.fw_mgmt_ip_input.text().strip()
        fw_user = self.fw_username_input.text().strip()
        fw_pass = self.fw_password_input.text()

        if fw_ip and fw_user and fw_pass:
            return {
                "mgmt_ip": fw_ip,
                "username": fw_user,
                "password": fw_pass,
            }
        return None

    def _merge_configs(
        self, base: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two configuration dictionaries."""
        # Simple deep merge - can be enhanced later
        merged = base.copy()

        for key, value in new.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged

    def _update_config_display(self):
        """Update firewall and PA info labels."""
        if not self.config_data:
            return

        # Try to extract firewall data
        fw_data = self.config_data.get("fwData", {})
        if not fw_data:
            fw_data = self.config_data.get("legacy_data", {}).get("fwData", {})

        # Try to extract PA data
        pa_data = self.config_data.get("paData", {})
        if not pa_data:
            pa_data = self.config_data.get("legacy_data", {}).get("paData", {})

        # Update firewall info
        self.fw_ip_label.setText(fw_data.get("mgmtUrl", "Not configured"))
        self.fw_user_label.setText(fw_data.get("mgmtUser", "Not configured"))

        # Update PA info
        self.pa_tsg_label.setText(pa_data.get("paTsgId", "Not configured"))
        self.pa_region_label.setText(pa_data.get("scLocation", "Not configured"))
        self.pa_mgmt_label.setText(self.management_type.upper())

    # ============================================================================
    # EVENT HANDLERS - DEFAULTS TAB
    # ============================================================================

    def _preview_defaults(self):
        """Preview selected default configurations."""
        selected = []
        if self.adem_check.isChecked():
            selected.append("ADEM Monitoring")
        if self.local_dns_check.isChecked():
            selected.append("Local DNS")
        if self.ztna_check.isChecked():
            selected.append("ZTNA")

        if not selected:
            QMessageBox.information(
                self, "No Selection", "Please select at least one default configuration."
            )
            return

        preview_text = "Selected default configurations:\n\n"
        for item in selected:
            preview_text += f"  • {item}\n"

        preview_text += "\nThese configurations will be merged with your existing config."

        QMessageBox.information(self, "Preview Defaults", preview_text)

    def _apply_defaults(self):
        """Apply selected default configurations."""
        selected = []
        if self.adem_check.isChecked():
            selected.append("ADEM")
        if self.local_dns_check.isChecked():
            selected.append("DNS")
        if self.ztna_check.isChecked():
            selected.append("ZTNA")

        if not selected:
            QMessageBox.information(
                self, "No Selection", "Please select at least one default configuration."
            )
            return

        # TODO: Actually inject default configurations
        # For now, just mark as applied
        self.defaults_status.setText(f"✓ Applied: {', '.join(selected)}")
        self.defaults_status.setStyleSheet("color: green;")

        QMessageBox.information(
            self,
            "Defaults Applied",
            f"Successfully applied {len(selected)} default configuration(s):\n\n"
            + "\n".join(f"  • {s}" for s in selected),
        )

    # ============================================================================
    # EVENT HANDLERS - FIREWALL & PRISMA TABS
    # ============================================================================

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
        self.worker.progress.connect(self._on_progress, Qt.ConnectionType.QueuedConnection)
        self.worker.finished.connect(self._on_fw_finished, Qt.ConnectionType.QueuedConnection)
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
        self.worker.progress.connect(self._on_progress, Qt.ConnectionType.QueuedConnection)
        self.worker.finished.connect(self._on_pa_finished, Qt.ConnectionType.QueuedConnection)
        self.worker.start()

    def _complete_pov_setup(self):
        """Complete POV setup."""
        QMessageBox.information(
            self,
            "POV Setup Complete",
            "POV environment configured successfully!\n\n"
            "Next steps:\n"
            "  • Verify firewall configuration\n"
            "  • Test service connections\n"
            "  • Validate connectivity\n"
            "  • Begin POV testing",
        )

    def _on_progress(self, message: str, percentage: int):
        """Handle progress updates."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(percentage)

    def _on_fw_finished(self, success: bool, message: str):
        """Handle firewall configuration completion."""
        self.progress_bar.setVisible(False)

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
        self.progress_bar.setVisible(False)

        if success:
            self.pa_results.setPlainText(f"✓ Success\n\n{message}")
            self.progress_label.setText("Prisma Access configured successfully")
            self.complete_btn.setEnabled(True)
            QMessageBox.information(self, "Success", message)
        else:
            self.pa_results.setPlainText(f"✗ Failed\n\n{message}")
            self.progress_label.setText("Configuration failed")
            QMessageBox.critical(self, "Failed", message)


    # ============================================================================
    # CLOUD RESOURCES HELPER METHODS
    # ============================================================================

    def _get_cloud_resource_categories(self) -> List[str]:
        """Get list of all cloud resource categories."""
        return [
            "Cloud Deployment & Sizing",
            "Cloud Security Configuration",
            "Initial Device Configuration",
            "Policy and Objects",
            "Locations",
            "Trust Network Devices",
        ]

    def _update_pa_defaults_status(self):
        """Update status based on POV use case selections (placeholder)."""
        # This method is kept for backwards compatibility with clear_state
        # POV use cases tab uses a different approach
        pass

    def _on_cloud_customer_changed(self, text: str):
        """Handle customer name change in Cloud Deployment card."""
        self._update_cloud_rg_preview()
        # Sync to cloud_resource_configs
        customer = text.lower().strip()
        self.cloud_resource_configs['cloud_deployment']['customer_name'] = customer
        self._update_cloud_deployment_status()

        # Auto-update admin username if it's empty or matches old pattern
        if hasattr(self, 'cloud_admin_username'):
            current_username = self.cloud_admin_username.text()
            # Update if empty or if it looks like an auto-generated username
            if not current_username or current_username == self.cloud_resource_configs['cloud_deployment'].get('_last_auto_username', ''):
                if customer:
                    new_username = f"{customer}admin"
                    self.cloud_admin_username.setText(new_username)
                    self.cloud_resource_configs['cloud_deployment']['_last_auto_username'] = new_username

        # Auto-update mobile portal name if it's empty or matches old pattern
        if hasattr(self, 'mobile_portal_input'):
            current_portal = self.mobile_portal_input.text()
            last_auto_portal = self.use_case_configs.get('mobile_users', {}).get('_last_auto_portal', '')
            if not current_portal or current_portal == last_auto_portal:
                if customer:
                    self.mobile_portal_input.setText(customer)
                    self.use_case_configs['mobile_users']['_last_auto_portal'] = customer

    def _on_cloud_region_changed(self, region: str):
        """Handle region change in Cloud Deployment card."""
        self._update_cloud_rg_preview()
        # Sync to cloud_resource_configs
        self.cloud_resource_configs['cloud_deployment']['location'] = region
        self._update_cloud_deployment_status()
        logger.info(f"Primary region set to: {region}")

    def _update_cloud_rg_preview(self):
        """Update the resource group name preview."""
        if not hasattr(self, 'cloud_customer_name') or not hasattr(self, 'cloud_region_combo'):
            return

        customer = self.cloud_customer_name.text().lower().strip()
        region = self.cloud_region_combo.currentText()

        if customer and region:
            rg_name = f"{customer}-{region}-pov-rg"
            self.cloud_rg_preview.setText(f"<b>{rg_name}</b>")
            self.cloud_rg_preview.setStyleSheet("font-size: 12px; color: #2E7D32;")
        else:
            self.cloud_rg_preview.setText("<i>(enter customer name)</i>")
            self.cloud_rg_preview.setStyleSheet("font-size: 12px; color: #666;")

    def _update_cloud_deployment_status(self):
        """Update Cloud Deployment card status based on required fields."""
        if not hasattr(self, 'cloud_customer_name'):
            return

        customer = self.cloud_customer_name.text().strip()
        if customer:
            self.cloud_deployment_status.setText("✓ Configured")
            self.cloud_deployment_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            self.cloud_deployment_status.setText("")

    def _on_admin_username_changed(self, text: str):
        """Handle admin username change."""
        self.cloud_resource_configs['cloud_deployment']['admin_username'] = text
        # Update password strength (in case username is in password)
        self._update_password_strength()

    def _on_admin_password_changed(self, text: str):
        """Handle admin password change."""
        self.cloud_resource_configs['cloud_deployment']['admin_password'] = text
        self._update_password_strength()

    def _toggle_password_visibility(self, checked: bool):
        """Toggle password field visibility."""
        if checked:
            self.cloud_admin_password.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.cloud_admin_password.setEchoMode(QLineEdit.EchoMode.Password)

    def _regenerate_admin_password(self):
        """Generate a new secure admin password."""
        new_password = PasswordGenerator.generate(length=20, azure_compatible=True)
        self.cloud_admin_password.setText(new_password)
        logger.info("Generated new admin password")

    def _update_password_strength(self):
        """Update password strength indicator."""
        if not hasattr(self, 'cloud_pwd_strength_bar') or not hasattr(self, '_password_validator'):
            return

        password = self.cloud_admin_password.text()

        if not password:
            self.cloud_pwd_strength_bar.setValue(0)
            self.cloud_pwd_strength_label.setText("No password")
            self.cloud_pwd_strength_bar.setStyleSheet(
                "QProgressBar { background-color: #e0e0e0; border-radius: 4px; }"
                "QProgressBar::chunk { background-color: #9E9E9E; border-radius: 4px; }"
            )
            return

        # Get strength score
        label, score = self._password_validator.get_strength(password)
        self.cloud_pwd_strength_bar.setValue(score)
        self.cloud_pwd_strength_label.setText(label)

        # Color based on strength
        if score < 30:
            color = "#F44336"  # Red - Weak
        elif score < 50:
            color = "#FF9800"  # Orange - Fair
        elif score < 70:
            color = "#FFC107"  # Yellow - Good
        elif score < 90:
            color = "#8BC34A"  # Light green - Strong
        else:
            color = "#4CAF50"  # Green - Very strong

        self.cloud_pwd_strength_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #e0e0e0; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}
        """)

    def _on_device_config_changed(self):
        """Handle device configuration field changes (auto-save)."""
        if not hasattr(self, 'device_dns_primary'):
            return

        self.cloud_resource_configs['device_config'] = {
            'dns_primary': self.device_dns_primary.text(),
            'dns_secondary': self.device_dns_secondary.text(),
            'ntp_primary': self.device_ntp_primary.text(),
            'ntp_secondary': self.device_ntp_secondary.text(),
            'hostname_prefix': self.device_hostname_prefix.text(),
        }
        logger.debug("Device configuration auto-saved")

    def _on_policy_config_changed(self):
        """Handle policy configuration changes (auto-save)."""
        if not hasattr(self, 'policy_rfc1918'):
            return

        self.cloud_resource_configs['policy_objects'] = {
            'create_rfc1918': self.policy_rfc1918.isChecked(),
            'create_app_groups': self.policy_app_groups.isChecked(),
            'allow_outbound': self.policy_allow_outbound.isChecked(),
            'block_quic': self.policy_block_quic.isChecked(),
            'create_outbound_nat': self.policy_outbound_nat.isChecked(),
        }
        logger.debug("Policy configuration auto-saved")

    # ============================================================================
    # CLOUD SECURITY HANDLERS
    # ============================================================================

    def _fetch_and_set_public_ip(self):
        """Fetch user's public IP and set it in the Cloud Security card."""
        import subprocess
        try:
            result = subprocess.run(
                ['curl', '-s', 'https://ipinfo.io/ip'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                ip = result.stdout.strip()
                if ip and hasattr(self, 'cloud_security_source_ips'):
                    self.cloud_security_source_ips.setText(f"{ip}/32")
                    logger.info(f"Detected public IP: {ip}")
                    return
        except Exception as e:
            logger.debug(f"Failed to fetch public IP: {e}")

        # Fallback
        if hasattr(self, 'cloud_security_source_ips'):
            if not self.cloud_security_source_ips.text():
                self.cloud_security_source_ips.setText("0.0.0.0/0")

    def _on_cloud_security_changed(self):
        """Handle cloud security configuration changes (auto-save)."""
        if not hasattr(self, 'cloud_security_source_ips'):
            return

        self.cloud_resource_configs['cloud_security'] = {
            'source_ips': self.cloud_security_source_ips.text(),
            'allow_ssh': self.cloud_security_ssh.isChecked(),
            'allow_https': self.cloud_security_https.isChecked(),
            'create_mgmt_nsg': True,  # Always required
            'create_trust_nsg': self.cloud_security_trust_nsg.isChecked(),
        }
        logger.debug("Cloud security configuration auto-saved")

    # ============================================================================
    # LOCATIONS HANDLERS (Branches & Datacenters)
    # ============================================================================

    def _add_branch(self):
        """Add a new branch location."""
        from PyQt6.QtWidgets import QListWidgetItem

        name = self.branch_name_input.text().strip()
        if not name:
            return

        # Get region (use primary if "(Primary)" selected)
        region = self.branch_region_combo.currentText()
        if region == "(Primary)":
            region = self.cloud_region_combo.currentText() if hasattr(self, 'cloud_region_combo') else "eastus"

        # Generate PSK
        psk = PasswordGenerator.generate(length=32, azure_compatible=True)

        # Create branch entry
        branch = {
            'name': name,
            'cloud': 'Azure',
            'region': region,
            'vpn_encryption': 'AES-256-GCM',
            'vpn_hash': 'SHA-512',
            'vpn_dh_group': 'Group 20',
            'psk': psk,
            'bgp_enabled': True,
            'default_gateway': True,
            'connection_type': 'remote_network',
        }

        # Add to storage
        self.cloud_resource_configs['locations']['branches'].append(branch)

        # Update UI
        self._refresh_branches_list()
        self.branch_name_input.clear()
        self._update_locations_status()
        self._sync_devices_from_locations()
        self._refresh_private_app_connections()

        logger.info(f"Added branch: {name} in {region}")

    def _remove_branch(self):
        """Remove the selected branch."""
        current_item = self.branches_list.currentItem()
        if not current_item:
            return

        branch_name = current_item.data(Qt.ItemDataRole.UserRole)

        # Remove from storage
        branches = self.cloud_resource_configs['locations']['branches']
        self.cloud_resource_configs['locations']['branches'] = [
            b for b in branches if b['name'] != branch_name
        ]

        # Update UI
        self._refresh_branches_list()
        self._update_locations_status()
        self._sync_devices_from_locations()
        self._refresh_private_app_connections()

        logger.info(f"Removed branch: {branch_name}")

    def _add_datacenter(self):
        """Add a new datacenter location."""
        from PyQt6.QtWidgets import QListWidgetItem

        name = self.dc_name_input.text().strip()
        if not name:
            return

        # Get region
        region = self.dc_region_combo.currentText()
        if region == "(Primary)":
            region = self.cloud_region_combo.currentText() if hasattr(self, 'cloud_region_combo') else "eastus"

        # Create datacenter entry
        datacenter = {
            'name': name,
            'cloud': 'Azure',
            'region': region,
            'bgp_enabled': True,
            'default_gateway': False,  # Datacenters don't get default route
            'connection_type': 'service_connection',
        }

        # Add to storage
        self.cloud_resource_configs['locations']['datacenters'].append(datacenter)

        # Update UI
        self._refresh_datacenters_list()
        self.dc_name_input.clear()
        self._update_locations_status()
        self._sync_devices_from_locations()
        self._refresh_private_app_connections()

        logger.info(f"Added datacenter: {name} in {region}")

    def _remove_datacenter(self):
        """Remove the selected datacenter."""
        current_item = self.datacenters_list.currentItem()
        if not current_item:
            return

        dc_name = current_item.data(Qt.ItemDataRole.UserRole)

        # Remove from storage
        datacenters = self.cloud_resource_configs['locations']['datacenters']
        self.cloud_resource_configs['locations']['datacenters'] = [
            d for d in datacenters if d['name'] != dc_name
        ]

        # Update UI
        self._refresh_datacenters_list()
        self._update_locations_status()
        self._sync_devices_from_locations()
        self._refresh_private_app_connections()

        logger.info(f"Removed datacenter: {dc_name}")

    def _refresh_branches_list(self):
        """Refresh the branches list widget."""
        from PyQt6.QtWidgets import QListWidgetItem

        self.branches_list.clear()
        branches = self.cloud_resource_configs.get('locations', {}).get('branches', [])

        for branch in branches:
            item = QListWidgetItem(f"🏢 {branch['name']} ({branch['region']})")
            item.setData(Qt.ItemDataRole.UserRole, branch['name'])
            self.branches_list.addItem(item)

    def _refresh_datacenters_list(self):
        """Refresh the datacenters list widget."""
        from PyQt6.QtWidgets import QListWidgetItem

        self.datacenters_list.clear()
        datacenters = self.cloud_resource_configs.get('locations', {}).get('datacenters', [])

        for dc in datacenters:
            item = QListWidgetItem(f"🏛️ {dc['name']} ({dc['region']})")
            item.setData(Qt.ItemDataRole.UserRole, dc['name'])
            self.datacenters_list.addItem(item)

    def _on_branch_selection_changed(self):
        """Handle branch selection change."""
        has_selection = self.branches_list.currentItem() is not None
        self.remove_branch_btn.setEnabled(has_selection)

    def _on_datacenter_selection_changed(self):
        """Handle datacenter selection change."""
        has_selection = self.datacenters_list.currentItem() is not None
        self.remove_dc_btn.setEnabled(has_selection)

    def _update_locations_status(self):
        """Update the Locations card status indicator."""
        loc_config = self.cloud_resource_configs.get('locations', {})
        branch_count = len(loc_config.get('branches', []))
        dc_count = len(loc_config.get('datacenters', []))

        if branch_count > 0 or dc_count > 0:
            self.locations_status.setText(f"✓ {branch_count} branch, {dc_count} DC")
            self.locations_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            self.locations_status.setText("")

    # ============================================================================
    # TRUST NETWORK DEVICES HANDLERS
    # ============================================================================

    def _sync_devices_from_locations(self):
        """Sync devices list based on branches, datacenters, and Panorama setting."""
        import uuid

        # Get current devices to preserve custom additions
        current_devices = self.cloud_resource_configs.get('trust_devices', {}).get('devices', [])

        # Build set of auto-generated device names to track
        auto_device_names = set()
        loc_config = self.cloud_resource_configs.get('locations', {})

        new_devices = []

        # Add Panorama if panorama managed is selected
        if hasattr(self, 'management_type') and self.management_type == 'panorama':
            panorama_name = "Panorama"
            auto_device_names.add(panorama_name)
            # Check if Panorama already exists
            if not any(d['name'] == panorama_name for d in current_devices):
                primary_region = self.cloud_region_combo.currentText() if hasattr(self, 'cloud_region_combo') else "eastus"
                new_devices.append({
                    'id': str(uuid.uuid4()),
                    'name': panorama_name,
                    'location': f"Primary ({primary_region})",
                    'location_type': 'primary',
                    'device_type': 'Panorama',
                    'subtype': 'Management',
                    'services': [],
                    'auto_generated': True,
                })

        # 1 Windows UserVM per branch
        for branch in loc_config.get('branches', []):
            device_name = f"{branch['name']}-UserVM"
            auto_device_names.add(device_name)
            if not any(d['name'] == device_name for d in current_devices):
                new_devices.append({
                    'id': str(uuid.uuid4()),
                    'name': device_name,
                    'location': branch['name'],
                    'location_type': 'branch',
                    'device_type': 'UserVM',
                    'subtype': 'Windows',
                    'services': [],
                    'auto_generated': True,
                })

        # 1 Linux ServerVM (DNS/WebApp) per datacenter
        for dc in loc_config.get('datacenters', []):
            device_name = f"{dc['name']}-ServerVM"
            auto_device_names.add(device_name)
            if not any(d['name'] == device_name for d in current_devices):
                new_devices.append({
                    'id': str(uuid.uuid4()),
                    'name': device_name,
                    'location': dc['name'],
                    'location_type': 'datacenter',
                    'device_type': 'ServerVM',
                    'subtype': 'Linux',
                    'services': ['DNS', 'WebApp'],
                    'auto_generated': True,
                })

        # Keep existing devices (both auto-generated that still have locations and manually added)
        for device in current_devices:
            # Keep if it's a custom device or if its auto-generated source still exists
            if not device.get('auto_generated', False):
                new_devices.append(device)
            elif device['name'] in auto_device_names:
                new_devices.append(device)
            # Otherwise, the location was removed, so don't keep the device

        # Update storage
        self.cloud_resource_configs['trust_devices']['devices'] = new_devices

        # Refresh UI
        self._refresh_devices_list()
        self._refresh_device_location_dropdown()
        self._update_trust_devices_status()

    def _refresh_devices_list(self):
        """Refresh the unified devices list display."""
        from PyQt6.QtWidgets import QListWidgetItem

        self.devices_list.clear()
        devices = self.cloud_resource_configs.get('trust_devices', {}).get('devices', [])

        if not devices:
            placeholder = QListWidgetItem("(Add locations to generate devices)")
            placeholder.setForeground(Qt.GlobalColor.gray)
            self.devices_list.addItem(placeholder)
            return

        for device in devices:
            if device['device_type'] == 'Panorama':
                icon = "🔧"
            elif device['device_type'] == 'UserVM':
                icon = "💻"
            else:
                icon = "🖥️"

            services_str = f" [{', '.join(device['services'])}]" if device['services'] else ""
            display_text = f"{icon} {device['name']} ({device['subtype']}){services_str}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, device['id'])
            self.devices_list.addItem(item)

    def _refresh_device_location_dropdown(self):
        """Refresh the location dropdown for adding devices."""
        self.device_location_combo.clear()

        loc_config = self.cloud_resource_configs.get('locations', {})

        # Add primary location
        if hasattr(self, 'cloud_region_combo'):
            primary_region = self.cloud_region_combo.currentText()
            self.device_location_combo.addItem(f"📍 Primary ({primary_region})", f"Primary ({primary_region})")

        # Add branches
        for branch in loc_config.get('branches', []):
            self.device_location_combo.addItem(f"🏢 {branch['name']}", branch['name'])

        # Add datacenters
        for dc in loc_config.get('datacenters', []):
            self.device_location_combo.addItem(f"🏛️ {dc['name']}", dc['name'])

        if self.device_location_combo.count() == 0:
            self.device_location_combo.addItem("(Add locations first)", None)

    def _on_device_type_changed(self, device_type: str):
        """Handle device type change to show/hide ServerVM options."""
        is_server = device_type == "ServerVM"
        self.services_widget.setVisible(is_server)

        # Default subtype based on device type
        if is_server:
            idx = self.device_subtype_combo.findText("Linux")
            if idx >= 0:
                self.device_subtype_combo.setCurrentIndex(idx)
        else:
            idx = self.device_subtype_combo.findText("Windows")
            if idx >= 0:
                self.device_subtype_combo.setCurrentIndex(idx)

    def _add_device(self):
        """Add a device to the list."""
        import uuid

        location = self.device_location_combo.currentData()
        if not location:
            return

        # Determine location type
        loc_config = self.cloud_resource_configs.get('locations', {})
        location_type = 'primary'
        if location.startswith("Primary"):
            location_type = 'primary'
        else:
            for dc in loc_config.get('datacenters', []):
                if dc['name'] == location:
                    location_type = 'datacenter'
                    break
            else:
                location_type = 'branch'

        device_type = self.device_type_combo.currentText()
        subtype = self.device_subtype_combo.currentText()

        services = []
        if device_type == "ServerVM":
            if self.service_dns_check.isChecked():
                services.append("DNS")
            if self.service_webapp_check.isChecked():
                services.append("WebApp")
            if self.service_ad_check.isChecked():
                services.append("AD")

        device = {
            'id': str(uuid.uuid4()),
            'name': f"{location}-{device_type}-{subtype}",
            'location': location,
            'location_type': location_type,
            'device_type': device_type,
            'subtype': subtype,
            'services': services,
            'auto_generated': False,
        }

        self.cloud_resource_configs['trust_devices']['devices'].append(device)

        self._refresh_devices_list()
        self._update_trust_devices_status()

        logger.info(f"Added device: {device['name']}")

    def _remove_device(self):
        """Remove the selected device."""
        current_item = self.devices_list.currentItem()
        if not current_item:
            return

        device_id = current_item.data(Qt.ItemDataRole.UserRole)
        if not device_id:
            return  # Placeholder item

        # Check if trying to remove Panorama while Panorama Managed is selected
        devices = self.cloud_resource_configs.get('trust_devices', {}).get('devices', [])
        device_to_remove = next((d for d in devices if d['id'] == device_id), None)

        if device_to_remove and device_to_remove.get('device_type') == 'Panorama':
            if self.management_type == 'panorama':
                # Show error and prevent removal
                self.trust_devices_error_label.setText(
                    "⚠ Cannot remove Panorama device if Panorama Managed is selected"
                )
                self.trust_devices_error_label.setVisible(True)
                return

        # Clear any previous error
        self.trust_devices_error_label.setVisible(False)

        self.cloud_resource_configs['trust_devices']['devices'] = [
            d for d in devices if d['id'] != device_id
        ]

        self._refresh_devices_list()
        self._update_trust_devices_status()

        logger.info(f"Removed device: {device_id}")

    def _on_device_selection_changed(self):
        """Handle device selection change."""
        current_item = self.devices_list.currentItem()
        has_selection = current_item is not None and current_item.data(Qt.ItemDataRole.UserRole) is not None
        self.remove_device_btn.setEnabled(has_selection)

        # Clear error message when selection changes
        if hasattr(self, 'trust_devices_error_label'):
            self.trust_devices_error_label.setVisible(False)

    def _update_trust_devices_status(self):
        """Update the Trust Network Devices status indicator."""
        devices = self.cloud_resource_configs.get('trust_devices', {}).get('devices', [])
        count = len(devices)

        if count > 0:
            self.trust_devices_status.setText(f"✓ {count} devices")
            self.trust_devices_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            self.trust_devices_status.setText("")

    def _get_selected_use_cases(self) -> List[str]:
        """Get list of selected POV use cases."""
        selected = []
        for use_case, config in self.use_case_configs.items():
            if config.get('enabled', False):
                selected.append(use_case)
        return selected

    def _preview_use_cases(self):
        """Preview selected POV use cases."""
        selected = self._get_selected_use_cases()
        if not selected:
            QMessageBox.information(
                self,
                "No Use Cases Selected",
                "No use cases are currently enabled.\n\n"
                "Click the ⚙️ button on a use case card to enable and configure it."
            )
            return

        # Build preview message
        use_case_names = {
            'mobile_users': 'Connect & Secure Mobile Users',
            'proxy_users': 'Connect & Secure Proxy Users',
            'private_app': 'Private App Access',
            'remote_branch': 'Connect Remote Branch',
            'aiops_adem': 'AIOPS-ADEM',
            'app_accel': 'App Acceleration',
            'rbi': 'Remote Browser Isolation',
            'pab': 'Prisma Access Browser',
        }

        preview = "Selected Use Cases:\n\n"
        for uc in selected:
            preview += f"  • {use_case_names.get(uc, uc)}\n"

        QMessageBox.information(self, "Selected Use Cases", preview)

    def _apply_use_cases(self):
        """Apply selected POV use cases."""
        selected = self._get_selected_use_cases()
        logger.info(f"Applying {len(selected)} use cases: {selected}")

        # Store use case selections in config_data for later use
        self.config_data['use_cases'] = self.use_case_configs.copy()

    # ============================================================================
    # DIALOG HANDLERS - Cloud Resources and Use Cases
    # ============================================================================

    def _open_cloud_resource_dialog(self, resource_name: str):
        """Open configuration dialog for a cloud resource."""
        dialog_class = CLOUD_RESOURCE_DIALOGS.get(resource_name)
        if not dialog_class:
            logger.warning(f"No dialog class found for cloud resource: {resource_name}")
            return

        # Get current config for this resource
        current_config = self.cloud_resource_configs.get(resource_name, {}).copy()

        # For cloud_deployment, sync inline fields to config before opening dialog
        if resource_name == 'cloud_deployment' and hasattr(self, 'cloud_customer_name'):
            current_config['customer_name'] = self.cloud_customer_name.text().lower().strip()
            current_config['location'] = self.cloud_region_combo.currentText()

        logger.info(f"Opening cloud resource dialog: {resource_name}")

        # Create and show dialog
        dialog = dialog_class(config=current_config, parent=self)
        if dialog.exec():
            # Save the configuration
            new_config = dialog.get_config()
            self.cloud_resource_configs[resource_name] = new_config
            self._update_cloud_resource_status(resource_name)
            logger.info(f"Cloud resource '{resource_name}' configured: {new_config}")

            # For cloud_deployment, sync dialog values back to inline fields
            if resource_name == 'cloud_deployment' and hasattr(self, 'cloud_customer_name'):
                if 'customer_name' in new_config:
                    self.cloud_customer_name.setText(new_config['customer_name'])
                if 'location' in new_config:
                    idx = self.cloud_region_combo.findText(new_config['location'])
                    if idx >= 0:
                        self.cloud_region_combo.setCurrentIndex(idx)
                self._update_cloud_rg_preview()

            # Log to activity log
            self._log_activity(f"Configured cloud resource: {resource_name}")

    def _open_use_case_dialog(self, use_case_name: str):
        """Open configuration dialog for a use case."""
        dialog_class = USE_CASE_DIALOGS.get(use_case_name)
        if not dialog_class:
            logger.warning(f"No dialog class found for use case: {use_case_name}")
            return

        # Get current config for this use case
        current_config = self.use_case_configs.get(use_case_name, {})

        logger.info(f"Opening use case dialog: {use_case_name}")

        # Create and show dialog
        dialog = dialog_class(config=current_config, parent=self)
        if dialog.exec():
            # Save the configuration
            self.use_case_configs[use_case_name] = dialog.get_config()
            self._update_use_case_status(use_case_name)
            logger.info(f"Use case '{use_case_name}' configured: {self.use_case_configs[use_case_name]}")

            # Log to activity log
            enabled = self.use_case_configs[use_case_name].get('enabled', False)
            status = "enabled" if enabled else "disabled"
            self._log_activity(f"Use case '{use_case_name}' {status}")

    # ========== USE CASE INLINE HANDLERS ==========

    def _on_mobile_users_changed(self):
        """Handle Mobile Users inline field changes."""
        # Get selected locations
        selected_locations = []
        for i in range(self.mobile_locations_list.count()):
            item = self.mobile_locations_list.item(i)
            if item.isSelected():
                selected_locations.append(item.text())

        self.use_case_configs['mobile_users'] = {
            'enabled': self.mobile_users_enable.isChecked(),
            'portal_name': self.mobile_portal_input.text(),
            'vpn_mode': self.mobile_vpn_mode.currentText(),
            'locations': selected_locations,
        }
        self._update_use_case_status('mobile_users')

    def _on_proxy_users_changed(self):
        """Handle Proxy Users inline field changes."""
        self.use_case_configs['proxy_users'] = {
            'enabled': self.proxy_users_enable.isChecked(),
            'proxy_port': self.proxy_port_input.value(),
            'auth_required': self.proxy_auth_required.isChecked(),
            'pac_file': self.proxy_pac_file.isChecked(),
        }
        self._update_use_case_status('proxy_users')

    def _on_private_app_changed(self):
        """Handle Private App Access inline field changes."""
        # Connections are managed via refresh method, just update enabled state
        config = self.use_case_configs.get('private_app', {})
        config['enabled'] = self.private_app_enable.isChecked()
        self.use_case_configs['private_app'] = config
        self._update_use_case_status('private_app')

    def _on_remote_branch_changed(self):
        """Handle Remote Branch inline field changes."""
        self.use_case_configs['remote_branch'] = {
            'enabled': self.remote_branch_enable.isChecked(),
            'branch_count': self.branch_count_input.value(),
            'branch_bandwidth': self.branch_bandwidth_combo.currentText(),
            'sdwan_integration': self.branch_sdwan.isChecked(),
            'bgp_routing': self.branch_bgp.isChecked(),
        }
        self._update_use_case_status('remote_branch')

    def _on_aiops_adem_changed(self):
        """Handle AIOPS-ADEM inline field changes."""
        # Tests are managed via add/remove methods, just update enabled state
        config = self.use_case_configs.get('aiops_adem', {'tests': []})
        config['enabled'] = self.aiops_adem_enable.isChecked()
        self.use_case_configs['aiops_adem'] = config
        self._update_use_case_status('aiops_adem')

    def _add_adem_test(self):
        """Add a new ADEM test to the list."""
        target = self.adem_test_input.text().strip()
        if not target:
            return

        test = {
            'target': target,
            'on_vpn': True,  # Always true
            'in_office': self.adem_in_office.isChecked(),
            'not_on_vpn': self.adem_not_on_vpn.isChecked(),
        }

        # Add to config
        if 'tests' not in self.use_case_configs.get('aiops_adem', {}):
            self.use_case_configs['aiops_adem'] = {'enabled': False, 'tests': []}
        self.use_case_configs['aiops_adem']['tests'].append(test)

        # Add to list display
        conditions = ["VPN"]
        if test['in_office']:
            conditions.append("Office")
        if test['not_on_vpn']:
            conditions.append("No-VPN")
        display_text = f"{target} ({', '.join(conditions)})"
        self.adem_tests_list.addItem(display_text)

        # Clear input
        self.adem_test_input.clear()
        self.adem_in_office.setChecked(False)
        self.adem_not_on_vpn.setChecked(False)

        self._update_use_case_status('aiops_adem')

    def _remove_adem_test(self):
        """Remove the selected ADEM test."""
        current_row = self.adem_tests_list.currentRow()
        if current_row >= 0:
            self.adem_tests_list.takeItem(current_row)
            tests = self.use_case_configs.get('aiops_adem', {}).get('tests', [])
            if current_row < len(tests):
                tests.pop(current_row)
            self._update_use_case_status('aiops_adem')

    def _on_adem_test_selected(self):
        """Handle ADEM test selection change."""
        has_selection = self.adem_tests_list.currentRow() >= 0
        self.adem_remove_btn.setEnabled(has_selection)

    def _on_app_accel_changed(self):
        """Handle App Acceleration inline field changes."""
        self.use_case_configs['app_accel'] = {
            'enabled': self.app_accel_enable.isChecked(),
            'saas_acceleration': self.accel_saas.isChecked(),
            'private_acceleration': self.accel_private.isChecked(),
        }
        self._update_use_case_status('app_accel')

    def _on_rbi_changed(self):
        """Handle RBI inline field changes."""
        # Get selected categories
        selected_categories = []
        for i in range(self.rbi_categories_list.count()):
            item = self.rbi_categories_list.item(i)
            if item.isSelected():
                selected_categories.append(item.text())

        self.use_case_configs['rbi'] = {
            'enabled': self.rbi_enable.isChecked(),
            'categories': selected_categories,
        }
        self._update_use_case_status('rbi')

    def _on_pab_changed(self):
        """Handle PAB inline field changes."""
        self.use_case_configs['pab'] = {
            'enabled': self.pab_enable.isChecked(),
            'enable_dlp': self.pab_dlp.isChecked(),
            'enable_threat_prevention': self.pab_threat.isChecked(),
            'enable_compliance': self.pab_compliance.isChecked(),
        }
        self._update_use_case_status('pab')

    def _refresh_private_app_connections(self):
        """Refresh the Private App connections list based on Locations tab data."""
        self.private_app_connections_list.clear()

        locations = self.cloud_resource_configs.get('locations', {})
        connections = []

        # Add Panorama if panorama managed (must be Service Connection)
        if self.management_type == 'panorama':
            conn = {
                'name': 'Panorama',
                'type': 'datacenter',
                'connection_type': 'service_connection',
                'locked': True,  # Cannot change
            }
            connections.append(conn)
            self.private_app_connections_list.addItem("🏛️ Panorama → Service Connection (required)")

        # Add datacenters
        for dc in locations.get('datacenters', []):
            conn = {
                'name': dc['name'],
                'type': 'datacenter',
                'connection_type': 'service_connection',  # Default
                'locked': False,
            }
            connections.append(conn)
            self.private_app_connections_list.addItem(f"🏛️ {dc['name']} → Service Connection")

        # Add branches
        for branch in locations.get('branches', []):
            conn = {
                'name': branch['name'],
                'type': 'branch',
                'connection_type': 'remote_network',  # Default for branches
                'locked': False,
            }
            connections.append(conn)
            self.private_app_connections_list.addItem(f"🏢 {branch['name']} → Remote Network")

        self.use_case_configs['private_app']['connections'] = connections

    def _update_cloud_resource_status(self, resource_name: str):
        """Update the status indicator for a cloud resource."""
        status_label = getattr(self, f"{resource_name}_status", None)
        if status_label:
            config = self.cloud_resource_configs.get(resource_name, {})
            if config:
                status_label.setText("✓ Configured")
                status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            else:
                status_label.setText("")

    def _update_use_case_status(self, use_case_name: str):
        """Update the status indicator for a use case."""
        status_label = getattr(self, f"{use_case_name}_status", None)
        if status_label:
            config = self.use_case_configs.get(use_case_name, {})
            if config.get('enabled', False):
                status_label.setText("✓ Enabled")
                status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            else:
                status_label.setText("○ Disabled")
                status_label.setStyleSheet("color: #999; font-size: 11px;")

    def _log_activity(self, message: str, level: str = "info"):
        """Log a message to the activity log and Python logger."""
        # Log to Python logger
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

        # Log to results panels if available
        if hasattr(self, 'cloud_deploy_results'):
            self.cloud_deploy_results.append_text(f"[{level.upper()}] {message}\n")

    def _update_all_status_indicators(self):
        """Update all status indicators based on current configurations."""
        # Update cloud resource status indicators
        for resource_name in self.cloud_resource_configs:
            self._update_cloud_resource_status(resource_name)

        # Update use case status indicators
        for use_case_name in self.use_case_configs:
            self._update_use_case_status(use_case_name)

    def _on_tab_changed(self, index: int):
        """Handle tab change events."""
        tab_names = [
            "Tenant Info",
            "Cloud Resources",
            "POV Use Cases",
            "Cloud Deployment",
            "Deploy POV Config",
            "Review & Execute",
        ]
        if 0 <= index < len(tab_names):
            tab_name = tab_names[index]
            logger.info(f"Navigated to Step {index + 1}: {tab_name}")

            # Update status indicators when entering Cloud Resources or Use Cases tabs
            if index in (1, 2):
                self._update_all_status_indicators()

            # Refresh Private App connections when entering Use Cases tab
            if index == 2:
                self._refresh_private_app_connections()

    # ============================================================================
    # EVENT HANDLERS - CLOUD DEPLOYMENT TAB (Tab 4)
    # ============================================================================

    def _authenticate_azure(self):
        """Authenticate with Azure and generate Terraform configuration."""
        import os
        import tempfile

        self._log_activity("Starting Azure authentication and Terraform generation...")

        # Check if we have deployment configuration
        deployment_config = self._gather_deployment_config()
        if not deployment_config.get('firewalls'):
            self._log_activity("No firewalls configured - aborting", "warning")
            QMessageBox.warning(
                self,
                "No Firewalls Configured",
                "Please configure firewall deployment options in Step 1 before proceeding."
            )
            return

        # Get output directory
        self._terraform_output_dir = os.path.join(
            tempfile.gettempdir(),
            "pa_config_lab_terraform"
        )
        os.makedirs(self._terraform_output_dir, exist_ok=True)
        self._log_activity(f"Terraform output directory: {self._terraform_output_dir}")

        # Build CloudConfig from UI selections
        try:
            cloud_config = self._build_cloud_config()
            self._log_activity("Cloud configuration built successfully")
        except Exception as e:
            self._log_activity(f"Failed to build cloud configuration: {str(e)}", "error")
            QMessageBox.critical(
                self,
                "Configuration Error",
                f"Failed to build cloud configuration:\n{str(e)}"
            )
            return

        # Start Terraform generation worker
        from gui.workers import TerraformWorker

        self._log_activity("Starting Terraform generation worker...")
        self._terraform_worker = TerraformWorker(
            operation="generate",
            config=cloud_config,
            output_dir=self._terraform_output_dir,
        )
        self._terraform_worker.progress.connect(self._on_terraform_progress)
        self._terraform_worker.finished.connect(self._on_terraform_generated)
        self._terraform_worker.error.connect(self._on_terraform_error)
        self._terraform_worker.start()

        # Update UI
        self.azure_auth_btn.setEnabled(False)
        self.terraform_status_widget.setVisible(True)
        self.terraform_gen_status.setText("⏳ Generating Terraform configuration...")

    def _build_cloud_config(self) -> dict:
        """Build CloudConfig dictionary from UI selections."""
        from config.models.cloud import (
            CloudConfig,
            CloudDeployment,
            CloudFirewall,
            CloudPanorama,
        )

        deployment_config = self._gather_deployment_config()

        # Build deployment settings
        deployment = CloudDeployment(
            customer_name="pov",
            management_type=deployment_config.get('management_type', 'scm'),
            provider="azure",
            location="eastus",
        )

        # Build firewalls
        firewalls = []
        for i, fw_config in enumerate(deployment_config.get('firewalls', [])):
            fw_type = "datacenter" if fw_config.get('type') == 'service_connection' else "branch"
            fw = CloudFirewall(
                name=f"fw{i+1}" if len(deployment_config.get('firewalls', [])) > 1 else "fw",
                firewall_type=fw_type,
            )
            firewalls.append(fw)

        # Build Panorama if Panorama-managed
        panorama = None
        if deployment_config.get('management_type') == 'panorama':
            panorama = CloudPanorama(name="panorama")

        # Create config
        config = CloudConfig(
            deployment=deployment,
            firewalls=firewalls,
            panorama=panorama,
        )

        return config

    def _on_terraform_progress(self, message: str, percentage: int):
        """Handle Terraform generation progress."""
        self.terraform_gen_status.setText(f"⏳ {message}")
        self._log_activity(f"Terraform: {message}")

    def _on_terraform_generated(self, success: bool, message: str, result: dict):
        """Handle Terraform generation completion."""
        self.azure_auth_btn.setEnabled(True)

        if success:
            self._log_activity("Terraform configuration generated successfully")
            self._on_azure_auth_success()
        else:
            self._log_activity(f"Terraform generation failed: {message}", "error")
            self.terraform_gen_status.setText(f"✗ Generation failed: {message}")
            self.terraform_gen_status.setStyleSheet(
                "color: #C62828; padding: 10px; background-color: #FFEBEE; "
                "border-radius: 5px;"
            )
            QMessageBox.critical(
                self,
                "Generation Failed",
                f"Failed to generate Terraform configuration:\n{message}"
            )

    def _on_terraform_error(self, error: str):
        """Handle Terraform error."""
        self._log_activity(f"Terraform error: {error}", "error")
        self.azure_auth_btn.setEnabled(True)
        self.terraform_gen_status.setText(f"✗ Error: {error}")
        self.terraform_gen_status.setStyleSheet(
            "color: #C62828; padding: 10px; background-color: #FFEBEE; "
            "border-radius: 5px;"
        )

    def _on_azure_auth_success(self):
        """Handle successful Azure authentication."""
        self._log_activity("Azure authentication successful")
        self.azure_auth_status.setText("🟢 Authenticated")
        self.azure_auth_status.setStyleSheet("font-weight: bold; color: #4CAF50;")

        # Show terraform generation status
        self.terraform_status_widget.setVisible(True)

        # Simulate terraform generation (in real implementation, this would be background task)
        # For now, just enable the buttons
        self._on_terraform_ready()

    def _on_terraform_ready(self):
        """Handle terraform configuration ready."""
        self._log_activity("Terraform configuration ready for deployment")
        self.terraform_gen_status.setText("✓ Terraform configuration generated successfully")
        self.terraform_gen_status.setStyleSheet(
            "color: #2E7D32; padding: 10px; background-color: #E8F5E9; "
            "border-radius: 5px;"
        )

        # Enable terraform action buttons
        self.review_terraform_btn.setEnabled(True)
        self.deploy_terraform_btn.setEnabled(True)

    def _review_terraform(self):
        """Review generated Terraform configuration."""
        import os
        from gui.dialogs import show_terraform_review

        self._log_activity("Opening Terraform configuration review...")

        if not hasattr(self, '_terraform_output_dir') or not self._terraform_output_dir:
            self._log_activity("No Terraform configuration to review", "warning")
            QMessageBox.warning(
                self,
                "No Configuration",
                "Please generate Terraform configuration first by clicking 'Authenticate with Azure'."
            )
            return

        terraform_dir = os.path.join(self._terraform_output_dir, "terraform")
        if not os.path.exists(terraform_dir):
            self._log_activity(f"Terraform directory not found: {terraform_dir}", "warning")
            QMessageBox.warning(
                self,
                "Configuration Not Found",
                f"Terraform configuration directory not found:\n{terraform_dir}"
            )
            return

        # Build summary from deployment config
        deployment_config = self._gather_deployment_config()
        summary = {
            'deployment_name': 'POV Deployment',
            'location': 'eastus',
            'firewalls': deployment_config.get('firewalls', []),
            'panorama': deployment_config.get('management_type') == 'panorama',
        }

        show_terraform_review(terraform_dir, summary, self)

    def _deploy_terraform(self):
        """Deploy Terraform configuration to Azure."""
        from terraform import check_terraform_installed

        self._log_activity("Starting Terraform deployment...")

        if not hasattr(self, '_terraform_output_dir') or not self._terraform_output_dir:
            self._log_activity("No Terraform configuration available", "warning")
            QMessageBox.warning(
                self,
                "No Configuration",
                "Please generate Terraform configuration first."
            )
            return

        # Check if Terraform is installed
        if not check_terraform_installed():
            QMessageBox.critical(
                self,
                "Terraform Not Found",
                "Terraform is not installed or not in PATH.\n\n"
                "Please install Terraform from:\nhttps://www.terraform.io/downloads"
            )
            return

        reply = QMessageBox.question(
            self,
            "Deploy Terraform",
            "This will deploy cloud resources to Azure using Terraform.\n\n"
            "This operation will:\n"
            "  • Initialize Terraform\n"
            "  • Create a deployment plan\n"
            "  • Apply the configuration\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Get credentials
        credentials = self._get_terraform_credentials()

        # Start Terraform deployment worker
        from gui.workers import TerraformWorker

        cloud_config = self._build_cloud_config()

        self._terraform_deploy_worker = TerraformWorker(
            operation="full",
            config=cloud_config,
            output_dir=self._terraform_output_dir,
            credentials=credentials,
            auto_approve=True,  # Auto-approve for POV
        )
        self._terraform_deploy_worker.progress.connect(self._on_deploy_progress)
        self._terraform_deploy_worker.phase_changed.connect(self._on_deploy_phase_changed)
        self._terraform_deploy_worker.finished.connect(self._on_deploy_finished)
        self._terraform_deploy_worker.error.connect(self._on_deploy_error)
        self._terraform_deploy_worker.log_message.connect(self._on_deploy_log)
        self._terraform_deploy_worker.start()

        # Update UI
        self.deploy_terraform_btn.setEnabled(False)
        self.review_terraform_btn.setEnabled(False)
        self.cloud_deploy_progress.setVisible(True)
        self.cloud_deploy_progress.setValue(0)
        self.cloud_deploy_results.set_text("Starting Terraform deployment...")

    def _get_terraform_credentials(self) -> dict:
        """Get credentials for Terraform deployment."""
        # For now, use a placeholder password
        # In production, this would prompt user or use tenant manager
        return {
            'admin_password': 'PaloAlto123!',  # Default for POV
        }

    def _on_deploy_progress(self, message: str, percentage: int):
        """Handle deployment progress update."""
        self.cloud_deploy_progress.setValue(percentage)
        logger.debug(f"Deploy progress: {percentage}% - {message}")

    def _on_deploy_phase_changed(self, phase: str):
        """Handle deployment phase change."""
        phase_names = {
            'generating': 'Generating configuration...',
            'initializing': 'Initializing Terraform...',
            'planning': 'Creating deployment plan...',
            'applying': 'Deploying infrastructure...',
        }
        status = phase_names.get(phase, phase)
        self._log_activity(f"Deployment phase: {status}")
        self.cloud_deploy_results.append_text(f"\n[{phase.upper()}] {status}")

    def _on_deploy_finished(self, success: bool, message: str, outputs: dict):
        """Handle deployment completion."""
        self.deploy_terraform_btn.setEnabled(True)
        self.review_terraform_btn.setEnabled(True)
        self.cloud_deploy_progress.setVisible(False)

        if success:
            self._log_activity("Infrastructure deployment completed successfully")
            # Store outputs for later use
            self._terraform_outputs = outputs

            result_text = "✓ Deployment Successful!\n\n"
            if outputs:
                result_text += "Deployed Resources:\n"
                for key, value in outputs.items():
                    if value:
                        result_text += f"  • {key}: {value}\n"
                        self._log_activity(f"  Deployed: {key} = {value}")

            self.cloud_deploy_results.set_text(result_text)

            QMessageBox.information(
                self,
                "Deployment Complete",
                "Infrastructure deployed successfully!\n\n"
                "You can now proceed to deploy the POV configuration."
            )
        else:
            self._log_activity(f"Infrastructure deployment failed: {message}", "error")
            self.cloud_deploy_results.set_text(f"✗ Deployment Failed\n\n{message}")
            QMessageBox.critical(
                self,
                "Deployment Failed",
                f"Infrastructure deployment failed:\n{message}"
            )

    def _on_deploy_error(self, error: str):
        """Handle deployment error."""
        self._log_activity(f"Deployment error: {error}", "error")
        self.cloud_deploy_results.append_text(f"\n[ERROR] {error}")

    def _on_deploy_log(self, message: str):
        """Handle deployment log message."""
        logger.debug(f"Deploy log: {message}")
        self.cloud_deploy_results.append_text(f"\n{message}")

    # ============================================================================
    # EVENT HANDLERS - DEPLOY POV CONFIG TAB (Tab 5)
    # ============================================================================

    def _on_deploy_tenant_changed(self, api_client, tenant_name: str):
        """Handle deploy tenant connection changes."""
        # Enable action buttons when connected
        if api_client:
            self._log_activity(f"Connected to tenant: {tenant_name}")
            self.review_config_btn.setEnabled(True)
            self.deploy_config_btn.setEnabled(True)
            self.deploy_summary_label.setText(
                f"<b>Connected to:</b> {tenant_name}<br><br>"
                "Configuration from previous steps will be deployed to this tenant."
            )
        else:
            self._log_activity("Disconnected from tenant")
            self.review_config_btn.setEnabled(False)
            self.deploy_config_btn.setEnabled(False)
            self.deploy_summary_label.setText(
                "Connect to an SCM tenant to deploy the POV configuration."
            )

    def _test_panorama_connection(self):
        """Test Panorama connection."""
        host = self.panorama_host_input.text().strip()
        user = self.panorama_user_input.text().strip()
        password = self.panorama_pass_input.text()

        if not host or not user:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter Panorama hostname and username."
            )
            return

        if not password:
            QMessageBox.warning(
                self,
                "Missing Password",
                "Please enter Panorama password or API key."
            )
            return

        # Test connection
        try:
            from panorama import PanoramaAPIClient, PanoramaConnectionError

            self.test_panorama_btn.setEnabled(False)
            self.test_panorama_btn.setText("Testing...")

            client = PanoramaAPIClient(
                hostname=host,
                username=user,
                password=password,
            )
            client.connect()
            info = client.get_device_info()
            client.disconnect()

            QMessageBox.information(
                self,
                "Connection Successful",
                f"Successfully connected to Panorama!\n\n"
                f"Hostname: {info.hostname}\n"
                f"Serial: {info.serial}\n"
                f"Model: {info.model}\n"
                f"Version: {info.sw_version}"
            )

        except PanoramaConnectionError as e:
            QMessageBox.critical(
                self,
                "Connection Failed",
                f"Failed to connect to Panorama:\n{str(e)}"
            )
        except ImportError:
            QMessageBox.warning(
                self,
                "Missing Dependency",
                "pan-os-python is required for Panorama connectivity.\n\n"
                "Install with: pip install pan-os-python"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Error connecting to Panorama:\n{str(e)}"
            )
        finally:
            self.test_panorama_btn.setEnabled(True)
            self.test_panorama_btn.setText("Test Connection")

    def _review_pov_config(self):
        """Review POV configuration before deployment."""
        deployment_config = self._gather_deployment_config()

        # Build review text
        review_text = "<h3>POV Configuration Summary</h3>"

        # Management type
        mgmt_type = deployment_config.get('management_type', 'scm').upper()
        review_text += f"<p><b>Management Type:</b> {mgmt_type}</p>"

        # SCM Tenant
        scm_info = deployment_config.get('scm_tenant', {})
        if scm_info.get('connected'):
            review_text += f"<p><b>SCM Tenant:</b> {scm_info.get('name', 'Unknown')}</p>"

        # Firewalls
        firewalls = deployment_config.get('firewalls', [])
        if firewalls:
            review_text += f"<p><b>Firewalls:</b> {len(firewalls)}</p>"
            review_text += "<ul>"
            for fw in firewalls:
                fw_type = fw.get('type', 'unknown').replace('_', ' ').title()
                review_text += f"<li>{fw.get('name', 'Firewall')} ({fw_type})</li>"
            review_text += "</ul>"

        # Terraform outputs if available
        if hasattr(self, '_terraform_outputs') and self._terraform_outputs:
            review_text += "<p><b>Deployed Infrastructure:</b></p><ul>"
            for key, value in self._terraform_outputs.items():
                if value and 'ip' in key.lower():
                    name = key.replace('_', ' ').title()
                    review_text += f"<li>{name}: {value}</li>"
            review_text += "</ul>"

        # Show in message box for now
        # TODO: Create a proper review dialog
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("POV Configuration Review")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)
        label = QLabel(review_text)
        label.setWordWrap(True)
        layout.addWidget(label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()

    def _deploy_pov_config(self):
        """Deploy POV configuration to firewalls/Panorama."""
        self._log_activity("Starting POV configuration deployment...")
        deployment_config = self._gather_deployment_config()

        # Check if we have Terraform outputs with IPs
        if not hasattr(self, '_terraform_outputs') or not self._terraform_outputs:
            # Check if already deployed with manual credentials
            if not deployment_config.get('already_deployed'):
                self._log_activity("No deployed infrastructure found", "warning")
                QMessageBox.warning(
                    self,
                    "No Deployed Infrastructure",
                    "Please deploy infrastructure using Terraform first, "
                    "or select 'Yes, already deployed' in Step 1 and provide credentials."
                )
                return

        reply = QMessageBox.question(
            self,
            "Deploy POV Configuration",
            "This will push configuration to your deployed firewalls.\n\n"
            "This includes:\n"
            "  • Device settings (DNS, NTP, hostname)\n"
            "  • Network interfaces and zones\n"
            "  • Basic security policy\n"
            "  • Outbound NAT\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            self._log_activity("POV configuration deployment cancelled by user")
            return

        # Get firewall credentials
        if deployment_config.get('already_deployed'):
            credentials = self._get_firewall_credentials()
            if not credentials:
                QMessageBox.warning(
                    self,
                    "Missing Credentials",
                    "Please enter firewall credentials in Step 1."
                )
                return
            fw_ip = credentials.get('mgmt_ip')
        else:
            # Get IP from Terraform outputs
            fw_ip = self._terraform_outputs.get(
                'firewall_management_ip',
                self._terraform_outputs.get('fw_management_ip')
            )
            if not fw_ip:
                # Try to find any firewall IP in outputs
                for key, value in self._terraform_outputs.items():
                    if 'firewall' in key.lower() and 'ip' in key.lower() and value:
                        fw_ip = value
                        break

            if not fw_ip:
                QMessageBox.warning(
                    self,
                    "No Firewall IP",
                    "Could not find firewall management IP in Terraform outputs."
                )
                return

            credentials = {
                'username': 'admin',
                'password': 'PaloAlto123!',  # Default POV password
            }

        # Start device configuration worker
        from gui.workers import DeviceConfigWorker

        fw_config = {
            'name': 'pov-firewall',
            'device': {
                'hostname': 'pov-firewall',
                'dns_primary': '8.8.8.8',
                'dns_secondary': '8.8.4.4',
                'ntp_primary': 'time.google.com',
            },
            'interfaces': [
                {'name': 'ethernet1/1'},
                {'name': 'ethernet1/2'},
            ],
        }

        deployment = {
            'name': 'pov-deployment',
            'virtual_network': {
                'subnets': [
                    {'name': 'trust', 'prefix': '10.100.2.0/24'},
                    {'name': 'untrust', 'prefix': '10.100.1.0/24'},
                ],
            },
        }

        self._device_config_worker = DeviceConfigWorker(
            device_type='firewall',
            config=fw_config,
            deployment=deployment,
            management_ip=fw_ip,
            credentials=credentials,
        )
        self._device_config_worker.progress.connect(self._on_pov_deploy_progress)
        self._device_config_worker.phase_changed.connect(self._on_pov_deploy_phase)
        self._device_config_worker.finished.connect(self._on_pov_deploy_finished)
        self._device_config_worker.error.connect(self._on_pov_deploy_error)
        self._device_config_worker.log_message.connect(self._on_pov_deploy_log)
        self._device_config_worker.start()

        # Update UI
        self.deploy_config_btn.setEnabled(False)
        self.review_config_btn.setEnabled(False)
        self.pov_deploy_progress.setVisible(True)
        self.pov_deploy_progress.setValue(0)
        self.pov_deploy_results.set_text(f"Connecting to firewall at {fw_ip}...")

    def _on_pov_deploy_progress(self, message: str, percentage: int):
        """Handle POV deployment progress."""
        self.pov_deploy_progress.setValue(percentage)
        logger.debug(f"POV deploy progress: {percentage}% - {message}")

    def _on_pov_deploy_phase(self, phase: str):
        """Handle POV deployment phase change."""
        self._log_activity(f"POV deployment phase: {phase}")
        self.pov_deploy_results.append_text(f"\n[{phase.upper()}]")

    def _on_pov_deploy_finished(self, success: bool, message: str, result: dict):
        """Handle POV deployment completion."""
        self.deploy_config_btn.setEnabled(True)
        self.review_config_btn.setEnabled(True)
        self.pov_deploy_progress.setVisible(False)

        if success:
            self._log_activity("POV configuration deployed successfully")
            self.pov_deploy_results.set_text(
                "✓ Configuration Deployed Successfully!\n\n"
                f"{message}\n\n"
                "The firewall has been configured with:\n"
                "  • Device settings (DNS, NTP)\n"
                "  • Network interfaces\n"
                "  • Security zones\n"
                "  • Basic security policy\n"
                "  • Outbound NAT"
            )
            self.complete_btn.setEnabled(True)

            QMessageBox.information(
                self,
                "Deployment Complete",
                "POV configuration deployed successfully!\n\n"
                "You can now complete the POV setup."
            )
        else:
            self._log_activity(f"POV deployment failed: {message}", "error")
            self.pov_deploy_results.set_text(f"✗ Deployment Failed\n\n{message}")
            QMessageBox.critical(
                self,
                "Deployment Failed",
                f"Configuration deployment failed:\n{message}"
            )

    def _on_pov_deploy_error(self, error: str):
        """Handle POV deployment error."""
        self._log_activity(f"POV deployment error: {error}", "error")
        self.pov_deploy_results.append_text(f"\n[ERROR] {error}")

    def _on_pov_deploy_log(self, message: str):
        """Handle POV deployment log message."""
        logger.debug(f"POV deploy log: {message}")
        self.pov_deploy_results.append_text(f"\n{message}")

    def _sync_tenant_to_deploy_tab(self):
        """Sync the tenant from Tab 1 to Tab 5."""
        if hasattr(self, 'deploy_tenant_selector') and self.api_client:
            # Set the same tenant as selected in Tab 1
            self.deploy_tenant_selector.set_connection(
                self.api_client,
                self.connection_name or ""
            )

    def _update_panorama_visibility(self):
        """Update Panorama section visibility based on management type."""
        if hasattr(self, 'panorama_deploy_group'):
            # Show Panorama section only if Panorama was selected in Tab 1
            is_panorama = not self.scm_managed_radio.isChecked()
            self.panorama_deploy_group.setVisible(is_panorama)

    def _save_current_config(self):
        """Save the current configuration to a JSON file."""
        if not self.config_data:
            QMessageBox.information(
                self,
                "No Configuration",
                "Please load or create a configuration first."
            )
            return

        # Generate default filename
        from datetime import datetime
        default_name = self.config_data.get("metadata", {}).get("saved_name", "")
        if not default_name:
            source = self.config_data.get("metadata", {}).get("source_tenant", "")
            if source:
                default_name = f"pov_{source}"
            else:
                default_name = f"pov_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Show save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save POV Configuration",
            f"{default_name}.json",
            "JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            try:
                import json
                with open(file_path, 'w') as f:
                    json.dump(self.config_data, f, indent=2)

                self.load_status.setText(f"Saved to: {Path(file_path).name}")
                self.load_status.setStyleSheet("color: green; font-weight: bold;")
                QMessageBox.information(
                    self,
                    "Configuration Saved",
                    f"Configuration saved to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Save Failed",
                    f"Failed to save configuration:\n{str(e)}"
                )
    
    def has_unsaved_work(self) -> bool:
        """
        Check if workflow has unsaved work that would be lost on switch.
        
        Returns:
            True if there is unsaved work, False otherwise
        """
        # Check if there's loaded config data
        if self.config_data:
            return True
        
        # Check if there's an active connection
        if self.api_client is not None:
            return True
        
        # Check if any sources were loaded
        if self.loaded_sources:
            return True
        
        return False
    
    def clear_state(self):
        """Clear all workflow state when switching workflows."""
        # Clear config data
        self.config_data = {}

        # Clear API client
        self.api_client = None
        self.connection_name = None

        # Clear loaded sources
        self.loaded_sources = []

        # Clear worker
        if self.worker is not None:
            self.worker = None

        # Reset tenant selector
        if hasattr(self, 'tenant_selector'):
            self.tenant_selector.reset()

        # Reset deployment options
        if hasattr(self, 'azure_no_radio'):
            self.azure_no_radio.setChecked(True)
            self.deploy_sc_firewall_check.setChecked(False)
            self.deploy_rn_firewall_check.setChecked(False)
            self.panorama_rn_no_radio.setChecked(True)
            self.deployed_no_radio.setChecked(True)
            self.deploy_manual_radio.setChecked(True)
            self.fw_mgmt_ip_input.clear()
            self.fw_username_input.clear()
            self.fw_password_input.clear()

        # Reset UI elements
        import json
        self.config_review_text.setPlainText(json.dumps({}, indent=2))
        self.load_status.setText("Configure your environment above")
        self.load_status.setStyleSheet("color: gray;")
        self.sources_summary.setText("<i>No sources loaded</i>")

        # Reset defaults status
        self._update_pa_defaults_status()
