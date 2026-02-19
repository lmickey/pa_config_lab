"""
POV Configuration Workflow GUI - Complete Rewrite.

This module provides a comprehensive workflow for configuring new POV environments
with flexible source loading, management type selection, and default injection.
"""

import logging
import hashlib
import base64
import secrets
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
    QComboBox,
    QFrame,
    QGridLayout,
    QScrollArea,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
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
            'services': {
                'domain': '',
                'applications': [],
                'pki': {
                    'server_cert': True,
                    'device_certs': True,
                    'user_certs': True,
                    'decryption_ca': True,
                },
                'employees': [],
            },
        }

        # Use Cases configuration storage
        self.use_case_configs = {
            'mobile_users': {'enabled': True},  # Default enabled
            'prisma_browser': {'enabled': False},
            'private_app': {'enabled': True},  # Default enabled
            'remote_branch': {'enabled': False},
            'aiops_adem': {'enabled': True, 'tests': []},  # Default enabled with empty tests
            'app_accel': {'enabled': False},
            'rbi': {'enabled': False},
            'custom_policies': {'enabled': True, 'policies': []},  # Replaces PAB
        }

        # Deployment configuration state tracking
        self.deployment_config = {
            'management_type': 'scm',
            'infrastructure_configured': False,
            'infrastructure_source': None,  # 'default', 'tenant', or 'existing'
            'panorama_placeholder': None,
            'deploy_cloud_resources': False,  # Default to not deploying cloud resources
        }

        # POV deployment state tracking
        self._pov_deployment_in_progress = False
        self._pov_deployment_cancelled = False
        self._pov_deployment_phases_completed = []  # Track completed phases for resume
        self._deploy_tenant_name = None  # Track deploy tenant for auto-connect on tab switch

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

        title = QLabel("<h3>Step 1: Tenant & Customer Information</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Configure your management type, connect to your SCM tenant, and provide customer details."
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
        # Customer Information Section (Name and Industry side by side)
        # =====================================================================
        customer_group = QGroupBox("Customer Information")
        customer_layout = QHBoxLayout()

        # Customer Name
        name_label = QLabel("Customer Name:")
        name_label.setStyleSheet("font-size: 12px; color: #333;")
        customer_layout.addWidget(name_label)

        self.customer_name_input = QLineEdit()
        self.customer_name_input.setPlaceholderText("e.g., acme")
        self.customer_name_input.setMaximumWidth(150)
        self.customer_name_input.setStyleSheet(
            "QLineEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
        )
        self.customer_name_input.textChanged.connect(self._on_customer_name_changed)
        customer_layout.addWidget(self.customer_name_input)

        customer_layout.addSpacing(20)

        # Industry (shortened label)
        industry_label = QLabel("Industry:")
        industry_label.setStyleSheet("font-size: 12px; color: #333;")
        customer_layout.addWidget(industry_label)

        self.customer_industry_combo = QComboBox()
        self.customer_industry_combo.addItems([
            "-- Select --",
            "Healthcare",
            "Financial Services",
            "Retail & E-Commerce",
            "Manufacturing",
            "Technology & Software",
            "Education",
            "Government",
            "Energy & Utilities",
            "Telecommunications",
            "Media & Entertainment",
            "Transportation & Logistics",
            "Professional Services",
            "Hospitality",
            "Real Estate",
            "Other",
        ])
        self.customer_industry_combo.setStyleSheet(
            "QComboBox { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }"
        )
        self.customer_industry_combo.currentTextChanged.connect(self._on_customer_industry_changed)
        customer_layout.addWidget(self.customer_industry_combo)

        customer_layout.addStretch()
        customer_group.setLayout(customer_layout)
        layout.addWidget(customer_group)

        # =====================================================================
        # Infrastructure Configuration Section
        # =====================================================================
        self.infra_group = QGroupBox("Infrastructure Configuration")
        infra_layout = QVBoxLayout()

        infra_label = QLabel("Configure Prisma Access infrastructure settings (network, BGP, ZTNA subnets, etc.)")
        infra_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        infra_layout.addWidget(infra_label)

        # Three buttons in a row
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)

        # Button 1: Infrastructure Configuration (Default) - Blue
        default_config_btn = QPushButton("⚙️ Infrastructure Configuration (Default)")
        default_config_btn.setMinimumHeight(50)
        default_config_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; padding: 12px 20px; "
            "  font-weight: bold; border-radius: 6px; font-size: 12px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
        )
        default_config_btn.clicked.connect(self._show_infrastructure_config_dialog)
        buttons_layout.addWidget(default_config_btn)

        # Button 2: Load Infrastructure Config from Tenant - Purple
        load_tenant_btn = QPushButton("☁️ Load Infrastructure Config from Tenant")
        load_tenant_btn.setMinimumHeight(50)
        load_tenant_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #9C27B0; color: white; padding: 12px 20px; "
            "  font-weight: bold; border-radius: 6px; font-size: 12px; "
            "  border: 1px solid #7B1FA2; border-bottom: 3px solid #6A1B9A; "
            "}"
            "QPushButton:hover { background-color: #8E24AA; border-bottom: 3px solid #4A148C; }"
            "QPushButton:pressed { background-color: #7B1FA2; border-bottom: 1px solid #6A1B9A; }"
        )
        load_tenant_btn.clicked.connect(self._load_infrastructure_from_tenant)
        buttons_layout.addWidget(load_tenant_btn)

        # Button 3: Import Existing Deployed Systems - Orange
        import_btn = QPushButton("📥 Import Existing Deployed Systems")
        import_btn.setMinimumHeight(50)
        import_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #FF9800; color: white; padding: 12px 20px; "
            "  font-weight: bold; border-radius: 6px; font-size: 12px; "
            "  border: 1px solid #F57C00; border-bottom: 3px solid #E65100; "
            "}"
            "QPushButton:hover { background-color: #FB8C00; border-bottom: 3px solid #BF360C; }"
            "QPushButton:pressed { background-color: #F57C00; border-bottom: 1px solid #E65100; }"
        )
        import_btn.clicked.connect(self._import_existing_systems)
        buttons_layout.addWidget(import_btn)

        infra_layout.addLayout(buttons_layout)

        # Status display for infrastructure config
        self.infra_status_label = QLabel("Status: Using default configuration")
        self.infra_status_label.setStyleSheet("color: #666; font-style: italic; margin-top: 10px;")
        infra_layout.addWidget(self.infra_status_label)

        # Initialize infrastructure config with defaults
        self.cloud_resource_configs['infrastructure'] = {
            'configured': False,
            'source': 'default',
            'network': {
                'infrastructure_subnet': '10.255.0.0/16',
                'infrastructure_bgp_as': '65534',
                'ipv6_enabled': False,
            },
            'dns': {
                'primary': '8.8.8.8',
                'secondary': '8.8.4.4',
            },
            'internal_dns': {
                'server1': '',
                'server2': '',
                'forward_domains': [],
            },
            'ztna': {
                'application_networks': ['192.168.0.0/16'],
                'controller_networks': ['10.0.0.0/8'],
            },
        }

        infra_layout.addStretch()
        self.infra_group.setLayout(infra_layout)
        layout.addWidget(self.infra_group)

        layout.addStretch()

        # =====================================================================
        # Bottom Status and Navigation
        # =====================================================================
        bottom_layout = QHBoxLayout()

        self.load_status = QLabel("Configure your environment above")
        self.load_status.setStyleSheet("color: gray;")
        bottom_layout.addWidget(self.load_status)

        bottom_layout.addStretch()

        # Resume POV Deployment button
        resume_btn = QPushButton("📂 Resume POV Deployment")
        resume_btn.setMinimumWidth(180)
        resume_btn.setMinimumHeight(40)
        resume_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #9C27B0; color: white; padding: 10px; font-weight: bold; "
            "  border-radius: 5px; border: 1px solid #7B1FA2; border-bottom: 3px solid #6A1B9A; "
            "}"
            "QPushButton:hover { background-color: #8E24AA; border-bottom: 3px solid #4A148C; }"
            "QPushButton:pressed { background-color: #7B1FA2; border-bottom: 1px solid #6A1B9A; }"
        )
        resume_btn.clicked.connect(self._show_resume_pov_dialog)
        bottom_layout.addWidget(resume_btn)

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
        next_btn.clicked.connect(lambda: self._next_tab(1))
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

        # Deploy toggle at top
        deploy_container = QWidget()
        deploy_layout = QHBoxLayout(deploy_container)
        deploy_layout.setContentsMargins(10, 5, 10, 10)

        self.deploy_cloud_checkbox = QCheckBox("Deploy Cloud Resources")
        self.deploy_cloud_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        self.deploy_cloud_checkbox.setChecked(False)  # Default OFF
        self.deploy_cloud_checkbox.stateChanged.connect(self._on_deploy_cloud_changed)

        deploy_hint = QLabel("Enable to deploy Azure infrastructure for this POV")
        deploy_hint.setStyleSheet("color: #666; font-style: italic;")

        deploy_layout.addWidget(self.deploy_cloud_checkbox)
        deploy_layout.addWidget(deploy_hint)
        deploy_layout.addStretch()

        layout.addWidget(deploy_container)

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

            # Note: Customer Name moved to Tenant Info tab

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

            # Help note for source IPs
            source_help = QLabel(
                "💡 Default is your current public IP for management access. "
                "Add others in comma-separated format."
            )
            source_help.setStyleSheet("font-size: 9px; color: #888; font-style: italic; margin-left: 2px;")
            source_help.setWordWrap(True)
            card_layout.addWidget(source_help)

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
            self.branches_list.setMinimumHeight(80)
            self.branches_list.setMaximumHeight(120)
            self.branches_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 11px; background-color: white; spacing: 0px; }"
                "QListWidget::item { padding: 1px 2px; margin: 0px; }"
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
            self.datacenters_list.setMinimumHeight(80)
            self.datacenters_list.setMaximumHeight(120)
            self.datacenters_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 11px; background-color: white; spacing: 0px; }"
                "QListWidget::item { padding: 1px 2px; margin: 0px; }"
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

            self.dc_style_combo = QComboBox()
            self.dc_style_combo.addItems(["Traditional (Firewall)", "SD-WAN (ION)", "SD-WAN (ION HA)"])
            self.dc_style_combo.setStyleSheet(
                "QComboBox { padding: 3px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; }"
            )
            dc_add_row.addWidget(self.dc_style_combo)

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

            # Initialize config with default datacenter
            default_region = self.cloud_region_combo.currentText() if hasattr(self, 'cloud_region_combo') else "eastus"
            self.cloud_resource_configs['locations'] = {
                'branches': [],
                'datacenters': [
                    {
                        'name': 'Datacenter',
                        'cloud': 'Azure',
                        'region': default_region,
                        'style': 'traditional',
                        'bgp_enabled': True,
                        'default_gateway': False,
                        'connection_type': 'service_connection',
                    }
                ],
            }

            # Populate the datacenters list with the default
            self._refresh_datacenters_list()
            self._update_locations_status()

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
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 11px; background-color: white; }"
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

            # Initialize config with empty devices list (will be populated by sync)
            self.cloud_resource_configs['trust_devices'] = {
                'devices': [],
            }

            # Initialize location dropdown
            self._refresh_device_location_dropdown()

            # Sync devices from locations (creates default ServerVM for default Datacenter)
            self._sync_devices_from_locations()

            # Prevent vertical stretching
            card_layout.addStretch()

            return card

        # Create Services & Applications card
        def create_services_card():
            from gui.workflows.pov_services import DEFAULT_APPLICATIONS

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
            title_label = QLabel("<b>🌐 Services & Applications</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            status_label = QLabel("")
            status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            self.services_status = status_label
            top_row.addWidget(status_label)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Domain input
            domain_row = QHBoxLayout()
            domain_label = QLabel("Domain:")
            domain_label.setStyleSheet("font-size: 11px; color: #555; font-weight: bold;")
            domain_row.addWidget(domain_label)

            self.services_domain_input = QLineEdit()
            self.services_domain_input.setPlaceholderText("acme.com")
            self.services_domain_input.setStyleSheet(
                "QLineEdit { padding: 3px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; }"
            )
            self.services_domain_input.textChanged.connect(self._update_services_status)
            domain_row.addWidget(self.services_domain_input)
            card_layout.addLayout(domain_row)

            # Applications list (read-only display)
            apps_label = QLabel(f"<b>Applications</b> ({len(DEFAULT_APPLICATIONS)} included)")
            apps_label.setStyleSheet("font-size: 11px; color: #555; margin-top: 2px;")
            card_layout.addWidget(apps_label)

            self.services_apps_list = QListWidget()
            self.services_apps_list.setMaximumHeight(80)
            self.services_apps_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 10px; background-color: white; }"
                "QListWidget::item { padding: 1px; }"
            )
            for app in DEFAULT_APPLICATIONS:
                from PyQt6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(f"  {app['subdomain']:12s} {app['name']} ({app['category']})")
                self.services_apps_list.addItem(item)
            card_layout.addWidget(self.services_apps_list)

            # PKI options
            pki_label = QLabel("<b>PKI Certificates</b>")
            pki_label.setStyleSheet("font-size: 11px; color: #555; margin-top: 2px;")
            card_layout.addWidget(pki_label)

            pki_row = QHBoxLayout()
            self.pki_server_cert_cb = QCheckBox("Server")
            self.pki_server_cert_cb.setChecked(True)
            self.pki_server_cert_cb.setStyleSheet("font-size: 10px;")
            self.pki_server_cert_cb.stateChanged.connect(self._update_services_status)
            pki_row.addWidget(self.pki_server_cert_cb)

            self.pki_device_certs_cb = QCheckBox("Device")
            self.pki_device_certs_cb.setChecked(True)
            self.pki_device_certs_cb.setStyleSheet("font-size: 10px;")
            self.pki_device_certs_cb.stateChanged.connect(self._update_services_status)
            pki_row.addWidget(self.pki_device_certs_cb)

            self.pki_user_certs_cb = QCheckBox("User")
            self.pki_user_certs_cb.setChecked(True)
            self.pki_user_certs_cb.setStyleSheet("font-size: 10px;")
            self.pki_user_certs_cb.stateChanged.connect(self._update_services_status)
            pki_row.addWidget(self.pki_user_certs_cb)

            self.pki_decryption_ca_cb = QCheckBox("Decryption")
            self.pki_decryption_ca_cb.setChecked(True)
            self.pki_decryption_ca_cb.setStyleSheet("font-size: 10px;")
            self.pki_decryption_ca_cb.stateChanged.connect(self._update_services_status)
            pki_row.addWidget(self.pki_decryption_ca_cb)

            card_layout.addLayout(pki_row)

            # Summary
            summary_frame = QFrame()
            summary_frame.setStyleSheet(
                "QFrame { background-color: #E3F2FD; border: 1px solid #90CAF9; "
                "border-radius: 4px; padding: 4px; margin-top: 4px; }"
            )
            summary_layout = QHBoxLayout(summary_frame)
            summary_layout.setContentsMargins(6, 2, 6, 2)

            self.services_summary = QLabel("Enter a domain to enable services")
            self.services_summary.setStyleSheet("color: #1565C0; font-size: 10px;")
            summary_layout.addWidget(self.services_summary)

            card_layout.addWidget(summary_frame)

            card_layout.addStretch()
            return card

        # Scrollable area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Grid layout
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

        # Row 3: Services & Applications (spans both columns)
        grid.addWidget(create_services_card(), 3, 0, 1, 2)

        scroll_layout.addLayout(grid)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)

        # Store reference and initially disable (deploy toggle is OFF by default)
        self.cloud_resources_scroll = scroll
        self.cloud_resources_scroll.setEnabled(False)

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
        next_btn.clicked.connect(lambda: self._next_tab(2))
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
            self.mobile_users_enable.setChecked(True)  # Default enabled
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
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 10px; background-color: white; }"
                "QListWidget::item { padding: 1px; }"
                "QListWidget::item:selected { background-color: #2196F3; color: white; }"
            )
            for loc in PRISMA_ACCESS_LOCATIONS:
                item = QListWidgetItem(loc)
                self.mobile_locations_list.addItem(item)
            self.mobile_locations_list.itemSelectionChanged.connect(self._on_mobile_users_changed)
            card_layout.addWidget(self.mobile_locations_list)

            # Auto-select default locations (US East, US West)
            for i in range(self.mobile_locations_list.count()):
                item = self.mobile_locations_list.item(i)
                if item.text() in ['US East', 'US West']:
                    item.setSelected(True)

            # Explicit Proxy checkbox
            self.mobile_explicit_proxy = QCheckBox("Enable Explicit Proxy")
            self.mobile_explicit_proxy.setStyleSheet(checkbox_style)
            self.mobile_explicit_proxy.stateChanged.connect(self._on_mobile_users_changed)
            card_layout.addWidget(self.mobile_explicit_proxy)

            # Hint about auto-enable
            self.explicit_proxy_hint = QLabel("")
            self.explicit_proxy_hint.setStyleSheet("font-size: 8px; color: #888; font-style: italic;")
            self.explicit_proxy_hint.setWordWrap(True)
            card_layout.addWidget(self.explicit_proxy_hint)

            # Initialize config with defaults
            self.use_case_configs['mobile_users'] = {
                'enabled': True,
                'portal_name': '',
                'vpn_mode': 'On Demand',
                'locations': ['US East', 'US West'],  # Default locations
                'explicit_proxy': False,
            }

            card_layout.addStretch()
            return card

        # ========== PRISMA BROWSER CARD ==========
        def create_prisma_browser_card():
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

            self.prisma_browser_enable = QCheckBox()
            self.prisma_browser_enable.setStyleSheet("margin-right: 4px;")
            self.prisma_browser_enable.stateChanged.connect(self._on_prisma_browser_changed)
            top_row.addWidget(self.prisma_browser_enable)

            title_label = QLabel("<b>🌐 Prisma Access Browser</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            self.prisma_browser_status = QLabel("")
            self.prisma_browser_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            top_row.addWidget(self.prisma_browser_status)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Options
            self.browser_default_policy = QCheckBox("Setup default policy for testing")
            self.browser_default_policy.setStyleSheet(checkbox_style)
            self.browser_default_policy.stateChanged.connect(self._on_prisma_browser_changed)
            card_layout.addWidget(self.browser_default_policy)

            self.browser_device_posture = QCheckBox("Device posture checks")
            self.browser_device_posture.setStyleSheet(checkbox_style)
            self.browser_device_posture.stateChanged.connect(self._on_prisma_browser_changed)
            card_layout.addWidget(self.browser_device_posture)

            # Route traffic dropdown
            route_row = QHBoxLayout()
            route_label = QLabel("Route traffic:")
            route_label.setStyleSheet("font-size: 10px; color: #666;")
            route_row.addWidget(route_label)

            self.browser_route_traffic = QComboBox()
            self.browser_route_traffic.addItems([
                "None",
                "Route private apps only",
                "Route all traffic to PA",
            ])
            self.browser_route_traffic.setStyleSheet(
                "QComboBox { padding: 2px 6px; border: 1px solid #ccc; border-radius: 3px; font-size: 10px; }"
            )
            self.browser_route_traffic.currentTextChanged.connect(self._on_prisma_browser_changed)
            route_row.addWidget(self.browser_route_traffic)
            route_row.addStretch()
            card_layout.addLayout(route_row)

            # Hint about explicit proxy
            browser_hint = QLabel("💡 Route traffic options will auto-enable Explicit Proxy in Mobile Users")
            browser_hint.setStyleSheet("font-size: 8px; color: #888; font-style: italic;")
            browser_hint.setWordWrap(True)
            card_layout.addWidget(browser_hint)

            # Initialize config
            self.use_case_configs['prisma_browser'] = {
                'enabled': False,
                'default_policy': False,
                'device_posture': False,
                'route_traffic': 'None',
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
            self.private_app_enable.setChecked(True)  # Default enabled
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

            # Connections list header
            conn_header = QHBoxLayout()
            conn_label = QLabel("Connections:")
            conn_label.setStyleSheet("font-size: 10px; color: #666;")
            conn_header.addWidget(conn_label)
            conn_header.addStretch()
            card_layout.addLayout(conn_header)

            # Click-to-toggle hint
            toggle_hint = QLabel("💡 Click a datacenter to toggle: Service Connection ↔ ZTNA Connector")
            toggle_hint.setStyleSheet("font-size: 9px; color: #888; font-style: italic;")
            card_layout.addWidget(toggle_hint)

            self.private_app_connections_list = QListWidget()
            self.private_app_connections_list.setMaximumHeight(100)
            self.private_app_connections_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 10px; background-color: white; }"
                "QListWidget::item { padding: 2px; color: #333; }"
                "QListWidget::item:selected { background-color: #e3f2fd; color: #333; }"
            )
            self.private_app_connections_list.itemClicked.connect(self._on_private_app_item_clicked)
            self.private_app_connections_list.currentRowChanged.connect(self._on_private_app_selection_changed)
            card_layout.addWidget(self.private_app_connections_list)

            # Add/Remove ZTNA buttons
            ztna_btn_row = QHBoxLayout()

            self.add_ztna_btn = QPushButton("+ Add ZTNA")
            self.add_ztna_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; padding: 4px 8px; "
                "font-size: 10px; font-weight: bold; border-radius: 3px; }"
                "QPushButton:hover { background-color: #45a049; }"
            )
            self.add_ztna_btn.clicked.connect(self._add_ztna_connector)
            ztna_btn_row.addWidget(self.add_ztna_btn)

            self.remove_ztna_btn = QPushButton("- Remove")
            self.remove_ztna_btn.setStyleSheet(
                "QPushButton { background-color: #f44336; color: white; padding: 4px 8px; "
                "font-size: 10px; font-weight: bold; border-radius: 3px; }"
                "QPushButton:hover { background-color: #d32f2f; }"
                "QPushButton:disabled { background-color: #ccc; }"
            )
            self.remove_ztna_btn.clicked.connect(self._remove_ztna_connector)
            self.remove_ztna_btn.setEnabled(False)
            ztna_btn_row.addWidget(self.remove_ztna_btn)

            ztna_btn_row.addStretch()
            card_layout.addLayout(ztna_btn_row)

            # Limits info
            self.private_app_limits_label = QLabel("Limits: 5 Service Connections, 10 ZTNA Connectors")
            self.private_app_limits_label.setStyleSheet("font-size: 9px; color: #666;")
            card_layout.addWidget(self.private_app_limits_label)

            # ZTNA note
            ztna_note = QLabel("⚠️ Adding ZTNA creates a placeholder in a new Connector Group")
            ztna_note.setStyleSheet("font-size: 9px; color: #888; font-style: italic;")
            ztna_note.setWordWrap(True)
            card_layout.addWidget(ztna_note)

            # Initialize config with default enabled
            self.use_case_configs['private_app'] = {
                'enabled': True,
                'connections': [],  # List of {name, type, connection_type: 'service_connection'|'ztna'|'remote_network'}
                'custom_ztna': [],  # List of custom ZTNA connectors added by user
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
            card_layout.setSpacing(4)
            card_layout.setContentsMargins(12, 8, 12, 8)

            # Top row with enable and title
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

            # ========== BANDWIDTH ALLOCATION ROW (header + controls on same line) ==========
            bw_row = QHBoxLayout()
            bw_row.setSpacing(4)

            self.branch_bw_total_label = QLabel("Bandwidth: 0/1000 Mbps")
            self.branch_bw_total_label.setStyleSheet("font-size: 10px; color: #666; font-weight: bold;")
            bw_row.addWidget(self.branch_bw_total_label)

            bw_row.addStretch()

            # Prisma Access location dropdown
            self.branch_bw_region_combo = QComboBox()
            self.branch_bw_region_combo.addItems(PRISMA_ACCESS_LOCATIONS)
            self.branch_bw_region_combo.setStyleSheet(combo_style)
            self.branch_bw_region_combo.setFixedWidth(140)
            bw_row.addWidget(self.branch_bw_region_combo)

            # Bandwidth dropdown with Mbps included
            self.branch_bw_amount_combo = QComboBox()
            self.branch_bw_amount_combo.addItems(["50 Mbps", "100 Mbps", "200 Mbps", "500 Mbps", "1000 Mbps"])
            self.branch_bw_amount_combo.setStyleSheet(combo_style)
            self.branch_bw_amount_combo.setFixedWidth(80)
            bw_row.addWidget(self.branch_bw_amount_combo)

            add_bw_btn = QPushButton("+")
            add_bw_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; padding: 2px 8px; "
                "font-size: 12px; font-weight: bold; border-radius: 3px; }"
                "QPushButton:hover { background-color: #45a049; }"
            )
            add_bw_btn.setFixedWidth(28)
            add_bw_btn.clicked.connect(self._add_bandwidth_allocation)
            bw_row.addWidget(add_bw_btn)

            card_layout.addLayout(bw_row)

            # Bandwidth list
            self.branch_bw_list = QListWidget()
            self.branch_bw_list.setMaximumHeight(45)
            self.branch_bw_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 9px; background-color: white; }"
                "QListWidget::item { padding: 1px; color: #333; }"
                "QListWidget::item:selected { background-color: #e3f2fd; color: #333; }"
            )
            card_layout.addWidget(self.branch_bw_list)

            # Remove bandwidth button
            remove_bw_btn = QPushButton("- Remove Selected")
            remove_bw_btn.setStyleSheet(
                "QPushButton { background-color: #f44336; color: white; padding: 2px 6px; "
                "font-size: 9px; border-radius: 3px; }"
                "QPushButton:hover { background-color: #d32f2f; }"
            )
            remove_bw_btn.clicked.connect(self._remove_bandwidth_allocation)
            card_layout.addWidget(remove_bw_btn)

            # ========== BRANCHES SECTION (header + add controls on same line) ==========
            branches_row = QHBoxLayout()
            branches_row.setSpacing(4)

            branches_label = QLabel("Branches:")
            branches_label.setStyleSheet("font-size: 10px; color: #666; font-weight: bold;")
            branches_row.addWidget(branches_label)

            branches_row.addStretch()

            self.staged_branch_name = QLineEdit()
            self.staged_branch_name.setPlaceholderText("Name")
            self.staged_branch_name.setStyleSheet(
                "QLineEdit { padding: 2px 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 9px; }"
            )
            self.staged_branch_name.setFixedWidth(70)
            branches_row.addWidget(self.staged_branch_name)

            # Region dropdown - populated from bandwidth allocations
            self.staged_branch_region = QComboBox()
            self.staged_branch_region.setStyleSheet(combo_style)
            self.staged_branch_region.setFixedWidth(140)
            self.staged_branch_region.setPlaceholderText("Allocate BW first")
            branches_row.addWidget(self.staged_branch_region)

            add_branch_btn = QPushButton("+ Add")
            add_branch_btn.setStyleSheet(
                "QPushButton { background-color: #2196F3; color: white; padding: 2px 6px; "
                "font-size: 9px; font-weight: bold; border-radius: 3px; }"
                "QPushButton:hover { background-color: #1976D2; }"
            )
            add_branch_btn.clicked.connect(self._add_staged_branch)
            branches_row.addWidget(add_branch_btn)

            card_layout.addLayout(branches_row)

            # Branches list (auto-populated from Locations + staged)
            self.branch_list = QListWidget()
            self.branch_list.setMaximumHeight(55)
            self.branch_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 9px; background-color: white; }"
                "QListWidget::item { padding: 1px; color: #333; }"
                "QListWidget::item:selected { background-color: #e3f2fd; color: #333; }"
            )
            card_layout.addWidget(self.branch_list)

            # Remove branch button
            remove_branch_btn = QPushButton("- Remove Selected")
            remove_branch_btn.setStyleSheet(
                "QPushButton { background-color: #f44336; color: white; padding: 2px 6px; "
                "font-size: 9px; border-radius: 3px; }"
                "QPushButton:hover { background-color: #d32f2f; }"
            )
            remove_branch_btn.clicked.connect(self._remove_staged_branch)
            card_layout.addWidget(remove_branch_btn)

            # Options row (SD-WAN, BGP)
            opts_row = QHBoxLayout()
            opts_row.setSpacing(8)

            self.branch_sdwan = QCheckBox("SD-WAN")
            self.branch_sdwan.setStyleSheet(checkbox_style)
            self.branch_sdwan.stateChanged.connect(self._on_remote_branch_changed)
            opts_row.addWidget(self.branch_sdwan)

            self.branch_bgp = QCheckBox("BGP")
            self.branch_bgp.setStyleSheet(checkbox_style)
            self.branch_bgp.setChecked(True)  # Default BGP on
            self.branch_bgp.stateChanged.connect(self._on_remote_branch_changed)
            opts_row.addWidget(self.branch_bgp)

            opts_row.addStretch()
            card_layout.addWidget(QLabel("💡 Cloud branches auto-assigned from Locations",
                styleSheet="font-size: 8px; color: #888; font-style: italic;"))

            card_layout.addLayout(opts_row)

            # Initialize config
            self.use_case_configs['remote_branch'] = {
                'enabled': False,
                'bandwidth_allocations': [],  # [{region (PA location), bandwidth}]
                'cloud_branches': [],  # Auto-populated from Locations
                'staged_branches': [],  # User-added staged branches
                'sdwan_integration': False,
                'bgp_routing': True,
            }

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
            self.adem_tests_list.setMinimumHeight(80)
            self.adem_tests_list.setMaximumHeight(120)
            self.adem_tests_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 11px; background-color: white; }"
                "QListWidget::item { padding: 3px 4px; }"
                "QListWidget::item:selected { background-color: #2196F3; color: white; }"
            )
            self.adem_tests_list.itemSelectionChanged.connect(self._on_adem_test_selected)
            card_layout.addWidget(self.adem_tests_list, 1)  # Give stretch factor

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

            # Initialize config - ADEM is enabled by default
            self.use_case_configs['aiops_adem'] = {
                'enabled': True,
                'tests': [],  # List of {target, on_vpn, in_office, not_on_vpn}
            }
            self.aiops_adem_enable.setChecked(True)  # Set checkbox to match

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
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 10px; background-color: white; }"
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

        # ========== CUSTOM SECURITY POLICIES CARD ==========
        def create_custom_policies_card():
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

            self.custom_policies_enable = QCheckBox()
            self.custom_policies_enable.setChecked(True)  # Default enabled
            self.custom_policies_enable.setStyleSheet("margin-right: 4px;")
            self.custom_policies_enable.stateChanged.connect(self._on_custom_policies_changed)
            top_row.addWidget(self.custom_policies_enable)

            title_label = QLabel("<b>🔒 Custom Security Policies</b>")
            title_label.setStyleSheet("font-size: 13px; color: #333;")
            top_row.addWidget(title_label)

            self.custom_policies_status = QLabel("")
            self.custom_policies_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            top_row.addWidget(self.custom_policies_status)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            # Description
            desc = QLabel("Configure basic firewall rules for this POV")
            desc.setStyleSheet("font-size: 10px; color: #666; margin-left: 20px;")
            card_layout.addWidget(desc)

            # Policies list with checkboxes
            self.custom_policies_list = QListWidget()
            self.custom_policies_list.setMaximumHeight(120)
            self.custom_policies_list.setStyleSheet(
                "QListWidget { border: 1px solid #ccc; border-radius: 4px; font-size: 10px; background-color: white; }"
                "QListWidget::item { padding: 2px; }"
            )

            # Default policies
            default_policies = [
                "Allow internet access from Mobile Users",
                "Allow internal DNS queries",
                "Block high-risk URL categories",
                "Allow SaaS applications",
                "Deny and log unknown applications",
            ]

            for policy in default_policies:
                item = QListWidgetItem(policy)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.custom_policies_list.addItem(item)

            self.custom_policies_list.itemChanged.connect(self._on_custom_policies_changed)
            card_layout.addWidget(self.custom_policies_list)

            # Add custom policy row
            add_row = QHBoxLayout()
            add_row.setSpacing(4)

            self.custom_policy_input = QLineEdit()
            self.custom_policy_input.setPlaceholderText("Add custom policy description...")
            self.custom_policy_input.setStyleSheet(input_style)
            add_row.addWidget(self.custom_policy_input)

            add_btn = QPushButton("+")
            add_btn.setFixedSize(24, 24)
            add_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
                "border-radius: 4px; font-size: 14px; }"
                "QPushButton:hover { background-color: #45a049; }"
            )
            add_btn.clicked.connect(self._add_custom_policy)
            add_row.addWidget(add_btn)

            card_layout.addLayout(add_row)

            # Initialize config with default policies
            self.use_case_configs['custom_policies'] = {
                'enabled': True,
                'policies': default_policies.copy(),
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
        grid.addWidget(create_prisma_browser_card(), 0, 1)

        # Row 1
        grid.addWidget(create_private_app_card(), 1, 0)
        grid.addWidget(create_remote_branch_card(), 1, 1)

        # Row 2
        grid.addWidget(create_aiops_adem_card(), 2, 0)
        grid.addWidget(create_app_accel_card(), 2, 1)

        # Row 3
        grid.addWidget(create_rbi_card(), 3, 0)
        grid.addWidget(create_custom_policies_card(), 3, 1)

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
        next_btn.clicked.connect(lambda: self._next_tab(3))
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
        next_btn.clicked.connect(lambda: self._next_tab(2))
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

        # Tenant ID input (optional - needed if subscriptions are in a different tenant)
        tenant_row = QHBoxLayout()
        tenant_label = QLabel("Tenant ID (optional):")
        tenant_label.setStyleSheet("color: #666;")
        tenant_row.addWidget(tenant_label)

        self.azure_tenant_input = QLineEdit()
        self.azure_tenant_input.setPlaceholderText("Leave blank for default, or enter tenant ID/domain")
        self.azure_tenant_input.setToolTip(
            "Optional: Enter your Azure tenant ID (GUID) or domain (e.g., contoso.onmicrosoft.com).\n"
            "Find this in Azure Portal > Microsoft Entra ID > Overview > Tenant ID.\n"
            "Leave blank to use your default/home tenant."
        )
        self.azure_tenant_input.setStyleSheet("padding: 5px; background-color: white;")
        tenant_row.addWidget(self.azure_tenant_input)
        azure_auth_layout.addLayout(tenant_row)

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
        self.azure_auth_btn.setToolTip("Sign in with your Microsoft account to deploy Azure resources")
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

        # Regenerate Terraform button - regenerates files from current POV config
        self.regen_terraform_btn = QPushButton("🔄 Regenerate")
        self.regen_terraform_btn.setMinimumWidth(140)
        self.regen_terraform_btn.setEnabled(False)
        self.regen_terraform_btn.setToolTip("Regenerate Terraform files from current POV configuration")
        self.regen_terraform_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; padding: 10px 20px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #42A5F5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #9E9E9E; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        self.regen_terraform_btn.clicked.connect(self._regenerate_terraform)
        actions_row.addWidget(self.regen_terraform_btn)

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

        # Edit Terraform button - opens directory in file manager
        self.edit_terraform_btn = QPushButton("📝 Edit Terraform")
        self.edit_terraform_btn.setMinimumWidth(160)
        self.edit_terraform_btn.setEnabled(False)
        self.edit_terraform_btn.setToolTip("Open Terraform files directory for manual editing")
        self.edit_terraform_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #9C27B0; color: white; padding: 10px 20px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #7B1FA2; border-bottom: 3px solid #6A1B9A; "
            "}"
            "QPushButton:hover { background-color: #8E24AA; border-bottom: 3px solid #4A148C; }"
            "QPushButton:pressed { background-color: #7B1FA2; border-bottom: 1px solid #6A1B9A; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #9E9E9E; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        self.edit_terraform_btn.clicked.connect(self._edit_terraform)
        actions_row.addWidget(self.edit_terraform_btn)

        # Deploy button - text changes based on deployment state ("Deploy" or "Redeploy")
        self.deploy_terraform_btn = QPushButton("🚀 Deploy")
        self.deploy_terraform_btn.setMinimumWidth(140)
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

        # Add View Credentials button (hidden until deployment completes)
        self.view_credentials_btn = QPushButton("🔑 View Credentials")
        self.view_credentials_btn.setMinimumWidth(160)
        self.view_credentials_btn.setVisible(False)
        self.view_credentials_btn.setToolTip("View credentials for deployed resources")
        self.view_credentials_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #673AB7; color: white; padding: 10px 20px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #5E35B1; border-bottom: 3px solid #4527A0; "
            "}"
            "QPushButton:hover { background-color: #7E57C2; border-bottom: 3px solid #311B92; }"
            "QPushButton:pressed { background-color: #5E35B1; border-bottom: 1px solid #4527A0; }"
        )
        self.view_credentials_btn.clicked.connect(self._show_credentials_dialog)
        actions_row.addWidget(self.view_credentials_btn)

        tf_actions_layout.addLayout(actions_row)
        tf_actions_group.setLayout(tf_actions_layout)
        layout.addWidget(tf_actions_group)

        # Store credentials internally (not displayed until requested)
        self._deployed_credentials = {
            'firewall': {'ip': '', 'username': '', 'password': ''},
            'vms': {'ips': [], 'username': '', 'password': ''},
        }

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

        self.cloud_deploy_next_btn = QPushButton("Next: Deploy POV Config →")
        self.cloud_deploy_next_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; padding: 8px 16px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
            "QPushButton:disabled { background-color: #BDBDBD; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        self.cloud_deploy_next_btn.clicked.connect(lambda: self._next_tab(4))
        # Initially disabled until Terraform is deployed (or cloud deployment is disabled)
        self.cloud_deploy_next_btn.setEnabled(False)
        self.cloud_deploy_next_btn.setToolTip("Deploy Terraform first to enable this button")
        nav_layout.addWidget(self.cloud_deploy_next_btn)

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

        self.deploy_config_btn = QPushButton("Deploy Configuration")
        self.deploy_config_btn.setMinimumWidth(180)
        self.deploy_config_btn.setEnabled(False)
        self.deploy_config_btn.setToolTip("Deploy POV configuration to SCM/Panorama")
        self._update_deploy_config_button_style()
        self.deploy_config_btn.clicked.connect(self._handle_deploy_config_click)
        actions_row.addWidget(self.deploy_config_btn)

        # Restart Deployment button - for starting fresh after partial deployment
        self.restart_deploy_btn = QPushButton("🔄 Restart")
        self.restart_deploy_btn.setMinimumWidth(100)
        self.restart_deploy_btn.setToolTip("Clear completed phases and start deployment from the beginning")
        self.restart_deploy_btn.setVisible(False)  # Hidden until there are completed phases
        self.restart_deploy_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; font-weight: bold; "
            "border: 1px solid #F57C00; border-radius: 4px; padding: 8px 16px; "
            "border-bottom: 3px solid #E65100; }"
            "QPushButton:hover { background-color: #FFB74D; }"
            "QPushButton:pressed { background-color: #F57C00; border-bottom: 1px solid #E65100; }"
        )
        self.restart_deploy_btn.clicked.connect(self._restart_deployment)
        actions_row.addWidget(self.restart_deploy_btn)

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

        # Update deployment_config tracking
        self.deployment_config['management_type'] = self.management_type

        # Handle Panorama placeholder based on management type
        if is_scm:
            # Remove Panorama placeholder if exists
            if self.deployment_config.get('panorama_placeholder'):
                self.deployment_config['panorama_placeholder'] = None
                # Remove placeholder from existing_devices
                existing = self.cloud_resource_configs.get('existing_devices', [])
                self.cloud_resource_configs['existing_devices'] = [
                    d for d in existing if not d.get('placeholder')
                ]
        else:
            # Create Panorama placeholder for Panorama Managed mode
            self.deployment_config['panorama_placeholder'] = {
                'device_type': 'Panorama',
                'placeholder': True,
                'mgmt_ip': '',
                'username': '',
                'password': '',
                'scannable': True,
            }
            # Add to existing_devices for visibility
            if 'existing_devices' not in self.cloud_resource_configs:
                self.cloud_resource_configs['existing_devices'] = []
            # Check if placeholder already exists
            has_placeholder = any(
                d.get('placeholder') and d.get('device_type') == 'Panorama'
                for d in self.cloud_resource_configs['existing_devices']
            )
            if not has_placeholder:
                self.cloud_resource_configs['existing_devices'].append(
                    self.deployment_config['panorama_placeholder']
                )

        # Update tenant selector visibility/title
        if is_scm:
            self.tenant_selector.group_box.setTitle("SCM Tenant (Required)")
            self.tenant_selector.setEnabled(True)
        else:
            self.tenant_selector.group_box.setTitle("SCM Tenant (Optional for Hybrid)")
            self.tenant_selector.setEnabled(True)  # Still allow optional SCM for hybrid

        # Update infrastructure status to reflect Panorama requirement
        if hasattr(self, 'infra_status_label'):
            existing_count = len(self.cloud_resource_configs.get('existing_devices', []))
            if not is_scm and existing_count > 0:
                placeholder_count = sum(1 for d in self.cloud_resource_configs.get('existing_devices', []) if d.get('placeholder'))
                if placeholder_count > 0:
                    self.infra_status_label.setText(f"Status: Panorama configuration required ({existing_count} system(s))")
                    self.infra_status_label.setStyleSheet("color: #FF9800; font-weight: bold;")

        # Update Panorama visibility in Tab 5
        self._update_panorama_visibility()

        # Sync devices to add/remove Panorama based on management type
        if hasattr(self, 'devices_list'):
            self._sync_devices_from_locations()

    def _sanitize_customer_name(self, name: str) -> str:
        """Sanitize customer name for use in system identifiers (lowercase, no spaces/special chars)."""
        import re
        # Lowercase, remove spaces and special characters, keep only alphanumeric
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def _on_customer_name_changed(self, text: str):
        """Handle customer name change in Tenant Info tab."""
        # Store original name (with case/spaces) for display
        customer_display = text.strip()
        # Sanitized version for system use (lowercase, no spaces/special chars)
        customer_sanitized = self._sanitize_customer_name(text)

        # Store in config - both versions
        if 'customer_info' not in self.cloud_resource_configs:
            self.cloud_resource_configs['customer_info'] = {}
        self.cloud_resource_configs['customer_info']['customer_name'] = customer_display
        self.cloud_resource_configs['customer_info']['customer_name_sanitized'] = customer_sanitized
        self.cloud_resource_configs['cloud_deployment']['customer_name'] = customer_sanitized

        # Update resource group preview if it exists
        if hasattr(self, 'cloud_rg_preview'):
            self._update_cloud_rg_preview()

        # Update Cloud Deployment status
        if hasattr(self, 'cloud_deployment_status'):
            self._update_cloud_deployment_status()

        # Auto-update admin username if it's empty or matches old pattern (use sanitized)
        if hasattr(self, 'cloud_admin_username'):
            current_username = self.cloud_admin_username.text()
            last_auto = self.cloud_resource_configs['cloud_deployment'].get('_last_auto_username', '')
            if not current_username or current_username == last_auto:
                if customer_sanitized:
                    new_username = f"{customer_sanitized}admin"
                    self.cloud_admin_username.setText(new_username)
                    self.cloud_resource_configs['cloud_deployment']['_last_auto_username'] = new_username

        # Auto-update mobile portal name if it's empty or matches old pattern (use sanitized)
        if hasattr(self, 'mobile_portal_input'):
            current_portal = self.mobile_portal_input.text()
            last_auto_portal = self.use_case_configs.get('mobile_users', {}).get('_last_auto_portal', '')
            if not current_portal or current_portal == last_auto_portal:
                if customer_sanitized:
                    self.mobile_portal_input.setText(customer_sanitized)
                    self.use_case_configs['mobile_users']['_last_auto_portal'] = customer_sanitized

    def _on_customer_industry_changed(self, industry: str):
        """Handle customer industry change."""
        if industry == "-- Select Industry --":
            industry = ""

        if 'customer_info' not in self.cloud_resource_configs:
            self.cloud_resource_configs['customer_info'] = {}
        self.cloud_resource_configs['customer_info']['industry'] = industry

    def _show_infrastructure_config_dialog(self):
        """Show dialog to configure/validate Prisma Access infrastructure settings."""
        from PyQt6.QtWidgets import (
            QDialog, QFormLayout, QDialogButtonBox, QTabWidget,
            QTextEdit, QGroupBox
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Infrastructure Configuration")
        dialog.setMinimumSize(550, 500)

        layout = QVBoxLayout(dialog)

        info_label = QLabel("Configure Prisma Access infrastructure settings. These will be used during deployment.")
        info_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Tabs for different config sections
        tabs = QTabWidget()

        config = self.cloud_resource_configs.get('infrastructure', {})

        # === Network Tab ===
        network_tab = QWidget()
        network_layout = QVBoxLayout(network_tab)

        # Basic network settings
        basic_group = QGroupBox("Network Settings")
        basic_form = QFormLayout(basic_group)
        basic_form.setSpacing(8)

        self._infra_subnet = QLineEdit(config.get('network', {}).get('infrastructure_subnet', '10.255.0.0/16'))
        basic_form.addRow("Infrastructure Subnet:", self._infra_subnet)

        self._infra_bgp_as = QLineEdit(config.get('network', {}).get('infrastructure_bgp_as', '65534'))
        basic_form.addRow("Infrastructure BGP AS:", self._infra_bgp_as)

        self._infra_ipv6 = QCheckBox("Enable IPv6")
        self._infra_ipv6.setChecked(config.get('network', {}).get('ipv6_enabled', False))
        basic_form.addRow("IPv6:", self._infra_ipv6)

        network_layout.addWidget(basic_group)

        # Public DNS settings
        dns_group = QGroupBox("Public DNS Servers")
        dns_form = QFormLayout(dns_group)
        dns_form.setSpacing(8)

        self._dns_primary = QLineEdit(config.get('dns', {}).get('primary', '8.8.8.8'))
        dns_form.addRow("Primary DNS:", self._dns_primary)

        self._dns_secondary = QLineEdit(config.get('dns', {}).get('secondary', '8.8.4.4'))
        dns_form.addRow("Secondary DNS:", self._dns_secondary)

        network_layout.addWidget(dns_group)

        # Internal DNS settings
        internal_dns_group = QGroupBox("Internal DNS (Domain Forwarding)")
        internal_dns_layout = QVBoxLayout(internal_dns_group)

        int_dns_form = QFormLayout()
        int_dns_form.setSpacing(8)

        self._internal_dns1 = QLineEdit(config.get('internal_dns', {}).get('server1', ''))
        self._internal_dns1.setPlaceholderText("e.g., 10.0.0.53")
        int_dns_form.addRow("Internal DNS 1:", self._internal_dns1)

        self._internal_dns2 = QLineEdit(config.get('internal_dns', {}).get('server2', ''))
        self._internal_dns2.setPlaceholderText("e.g., 10.0.0.54")
        int_dns_form.addRow("Internal DNS 2:", self._internal_dns2)

        internal_dns_layout.addLayout(int_dns_form)

        domains_label = QLabel("Forward Domains (one per line):")
        domains_label.setStyleSheet("margin-top: 5px;")
        internal_dns_layout.addWidget(domains_label)

        domains_hint = QLabel(
            "<small>Formats: <code>domain.com</code>, <code>^.domain.com</code> (single subdomain), "
            "<code>*.domain.com</code> (all subdomains), <code>^sub.domain.com</code>, <code>*sub.domain.com</code></small>"
        )
        domains_hint.setStyleSheet("color: #666; margin-bottom: 5px;")
        domains_hint.setWordWrap(True)
        internal_dns_layout.addWidget(domains_hint)

        self._internal_dns_domains = QTextEdit()
        self._internal_dns_domains.setMaximumHeight(80)
        self._internal_dns_domains.setPlaceholderText("corp.example.com\n^.internal.example.com\n*.servers.example.com")
        # Load existing domains
        existing_domains = config.get('internal_dns', {}).get('forward_domains', [])
        if existing_domains:
            self._internal_dns_domains.setPlainText('\n'.join(existing_domains))
        internal_dns_layout.addWidget(self._internal_dns_domains)

        network_layout.addWidget(internal_dns_group)
        network_layout.addStretch()

        tabs.addTab(network_tab, "Network")

        # === ZTNA Tab ===
        ztna_tab = QWidget()
        ztna_layout = QVBoxLayout(ztna_tab)

        # Application Network (formerly Trusted)
        app_network_group = QGroupBox("Application Network")
        app_network_layout = QVBoxLayout(app_network_group)

        app_hint = QLabel("<small>Networks where ZTNA-protected applications reside (one per line, CIDR format)</small>")
        app_hint.setStyleSheet("color: #666;")
        app_network_layout.addWidget(app_hint)

        self._ztna_app_networks = QTextEdit()
        self._ztna_app_networks.setMaximumHeight(80)
        self._ztna_app_networks.setPlaceholderText("192.168.0.0/16\n10.10.0.0/16")
        # Load existing app networks
        existing_app = config.get('ztna', {}).get('application_networks', [])
        if not existing_app:
            # Fallback to old trusted_network for backward compat
            old_trusted = config.get('ztna', {}).get('trusted_network', '')
            if old_trusted:
                existing_app = [old_trusted]
        if existing_app:
            self._ztna_app_networks.setPlainText('\n'.join(existing_app))
        app_network_layout.addWidget(self._ztna_app_networks)

        ztna_layout.addWidget(app_network_group)

        # Controller Network (formerly Untrusted)
        ctrl_network_group = QGroupBox("Controller Network")
        ctrl_network_layout = QVBoxLayout(ctrl_network_group)

        ctrl_hint = QLabel("<small>Networks where ZTNA connectors/controllers are deployed (one per line, CIDR format)</small>")
        ctrl_hint.setStyleSheet("color: #666;")
        ctrl_network_layout.addWidget(ctrl_hint)

        self._ztna_ctrl_networks = QTextEdit()
        self._ztna_ctrl_networks.setMaximumHeight(80)
        self._ztna_ctrl_networks.setPlaceholderText("10.0.0.0/8\n172.16.0.0/12")
        # Load existing controller networks
        existing_ctrl = config.get('ztna', {}).get('controller_networks', [])
        if not existing_ctrl:
            # Fallback to old untrusted_network for backward compat
            old_untrusted = config.get('ztna', {}).get('untrusted_network', '')
            if old_untrusted:
                existing_ctrl = [old_untrusted]
        if existing_ctrl:
            self._ztna_ctrl_networks.setPlainText('\n'.join(existing_ctrl))
        ctrl_network_layout.addWidget(self._ztna_ctrl_networks)

        ztna_layout.addWidget(ctrl_network_group)
        ztna_layout.addStretch()

        tabs.addTab(ztna_tab, "ZTNA")

        layout.addWidget(tabs)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec():
            # Validate and parse internal DNS domains
            domains_text = self._internal_dns_domains.toPlainText().strip()
            forward_domains = []
            validation_errors = []

            if domains_text:
                for line in domains_text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue

                    is_valid, error = self._validate_dns_forward_domain(line)
                    if is_valid:
                        forward_domains.append(line)
                    else:
                        validation_errors.append(f"'{line}': {error}")

            if validation_errors:
                QMessageBox.warning(
                    dialog, "Invalid Domain Format",
                    "The following domains have invalid formats:\n\n" + '\n'.join(validation_errors)
                )
                return

            # Parse and validate ZTNA networks
            app_networks_text = self._ztna_app_networks.toPlainText().strip()
            app_networks = []
            ctrl_networks_text = self._ztna_ctrl_networks.toPlainText().strip()
            ctrl_networks = []
            network_errors = []

            for line in app_networks_text.split('\n'):
                line = line.strip()
                if line:
                    is_valid, error = self._validate_cidr_network(line)
                    if is_valid:
                        app_networks.append(line)
                    else:
                        network_errors.append(f"Application Network '{line}': {error}")

            for line in ctrl_networks_text.split('\n'):
                line = line.strip()
                if line:
                    is_valid, error = self._validate_cidr_network(line)
                    if is_valid:
                        ctrl_networks.append(line)
                    else:
                        network_errors.append(f"Controller Network '{line}': {error}")

            if network_errors:
                QMessageBox.warning(
                    dialog, "Invalid Network Format",
                    "The following networks have invalid formats:\n\n" + '\n'.join(network_errors)
                )
                return

            # Save configuration
            self.cloud_resource_configs['infrastructure'] = {
                'configured': True,
                'source': 'manual',
                'network': {
                    'infrastructure_subnet': self._infra_subnet.text(),
                    'infrastructure_bgp_as': self._infra_bgp_as.text(),
                    'ipv6_enabled': self._infra_ipv6.isChecked(),
                },
                'dns': {
                    'primary': self._dns_primary.text(),
                    'secondary': self._dns_secondary.text(),
                },
                'internal_dns': {
                    'server1': self._internal_dns1.text().strip(),
                    'server2': self._internal_dns2.text().strip(),
                    'forward_domains': forward_domains,
                },
                'ztna': {
                    'application_networks': app_networks,
                    'controller_networks': ctrl_networks,
                },
            }

            # Update deployment config state
            self.deployment_config['infrastructure_configured'] = True
            self.deployment_config['infrastructure_source'] = 'manual'

            self.infra_status_label.setText("Status: ✓ Configured manually")
            self.infra_status_label.setStyleSheet("color: #4CAF50; font-weight: bold; margin-top: 10px;")
            logger.info("Infrastructure configuration saved")

    def _validate_dns_forward_domain(self, domain: str) -> tuple:
        """
        Validate a DNS forward domain entry.

        Valid formats:
        - domain.suffix (e.g., mydomain.com)
        - ^.domain.suffix (single subdomain wildcard)
        - *.domain.suffix (multi-subdomain wildcard)
        - ^sub.domain.suffix (single level wildcard at subdomain)
        - *sub.domain.suffix (multi-level wildcard at subdomain)

        Rules:
        - Must have at least domain.suffix
        - Only one ^ or * allowed per entry
        - Wildcards must be at the start

        Returns (is_valid: bool, error_message: str or None)
        """
        import re

        if not domain:
            return False, "Empty domain"

        # Check for multiple wildcards
        wildcard_count = domain.count('^') + domain.count('*')
        if wildcard_count > 1:
            return False, "Only one wildcard (^ or *) allowed per domain"

        # Check wildcard is at the start if present
        if ('^' in domain or '*' in domain) and not (domain.startswith('^') or domain.startswith('*')):
            return False, "Wildcard (^ or *) must be at the start of the domain"

        # Remove wildcard prefix for base domain validation
        base_domain = domain
        if domain.startswith('^.') or domain.startswith('*.'):
            base_domain = domain[2:]
        elif domain.startswith('^') or domain.startswith('*'):
            base_domain = domain[1:]

        # Validate base domain format
        # Must have at least one dot (domain.suffix)
        if '.' not in base_domain:
            return False, "Must have at least domain.suffix format (e.g., example.com)"

        # Check that it doesn't start or end with a dot
        if base_domain.startswith('.') or base_domain.endswith('.'):
            return False, "Domain cannot start or end with a dot"

        # Check for valid domain characters
        # Valid: a-z, A-Z, 0-9, hyphen (but not at start/end of label), dots
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$'
        if not re.match(domain_pattern, base_domain):
            return False, "Invalid characters in domain (use a-z, 0-9, hyphens, dots)"

        # Check TLD exists and is valid (at least 2 chars)
        parts = base_domain.split('.')
        if len(parts[-1]) < 2:
            return False, "TLD must be at least 2 characters"

        return True, None

    def _validate_cidr_network(self, network: str) -> tuple:
        """
        Validate a CIDR network address.

        Valid formats:
        - IPv4: 192.168.0.0/16, 10.0.0.0/8
        - IPv6: 2001:db8::/32, fd00::/8

        Returns (is_valid: bool, error_message: str or None)
        """
        import re

        if not network:
            return False, "Empty network"

        # Check for CIDR notation
        if '/' not in network:
            return False, "Must include CIDR prefix (e.g., /24)"

        parts = network.split('/')
        if len(parts) != 2:
            return False, "Invalid CIDR format"

        ip_part, prefix_part = parts

        # Validate prefix is a number
        try:
            prefix = int(prefix_part)
        except ValueError:
            return False, "Prefix must be a number"

        # Check if IPv4 or IPv6
        if ':' in ip_part:
            # IPv6 validation
            if prefix < 0 or prefix > 128:
                return False, "IPv6 prefix must be 0-128"
            # Basic IPv6 format check
            ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$|^::$|^::1$'
            if not re.match(ipv6_pattern, ip_part):
                return False, "Invalid IPv6 address format"
        else:
            # IPv4 validation
            if prefix < 0 or prefix > 32:
                return False, "IPv4 prefix must be 0-32"
            # Check IPv4 format
            ipv4_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
            match = re.match(ipv4_pattern, ip_part)
            if not match:
                return False, "Invalid IPv4 address format"
            # Check each octet is 0-255
            for octet in match.groups():
                if int(octet) > 255:
                    return False, "IPv4 octets must be 0-255"

        return True, None

    def _load_infrastructure_from_tenant(self):
        """Load infrastructure configuration from connected SCM tenant."""
        from PyQt6.QtWidgets import QApplication

        # Check if tenant is connected
        if not self.api_client:
            QMessageBox.warning(
                self, "No Tenant Connected",
                "Please connect to an SCM tenant using the tenant selector above "
                "before loading configuration."
            )
            return

        # Show loading indicator
        self.infra_status_label.setText("Loading from tenant...")
        self.infra_status_label.setStyleSheet("color: #2196F3; font-style: italic;")
        QApplication.processEvents()

        try:
            # TODO: Implement actual API call to fetch infrastructure config
            # For now, use defaults as placeholder until API integration is complete
            # infrastructure = self.api_client.get_infrastructure_config()

            # Populate with defaults (placeholder until API implemented)
            self.cloud_resource_configs['infrastructure'] = {
                'configured': True,
                'source': 'tenant',
                'tenant_name': self.connection_name,
                'network': {
                    'infrastructure_subnet': '10.255.0.0/16',
                    'infrastructure_bgp_as': '65534',
                    'ipv6_enabled': False,
                },
                'dns': {
                    'primary': '8.8.8.8',
                    'secondary': '8.8.4.4',
                },
                'internal_dns': {
                    'server1': '',
                    'server2': '',
                    'forward_domains': [],
                },
                'ztna': {
                    'application_networks': [],
                    'controller_networks': [],
                },
            }

            # Update deployment config state
            self.deployment_config['infrastructure_configured'] = True
            self.deployment_config['infrastructure_source'] = 'tenant'

            self.infra_status_label.setText(f"Status: ✓ Loaded from {self.connection_name}")
            self.infra_status_label.setStyleSheet("color: #9C27B0; font-weight: bold;")

            QMessageBox.information(
                self, "Configuration Loaded",
                f"Infrastructure configuration loaded from {self.connection_name}.\n\n"
                "You can click 'Infrastructure Configuration (Default)' to review and modify."
            )

            logger.info(f"Infrastructure config loaded from tenant: {self.connection_name}")

        except Exception as e:
            logger.error(f"Failed to load infrastructure from tenant: {e}")
            self.infra_status_label.setText("Status: Failed to load from tenant")
            self.infra_status_label.setStyleSheet("color: #F44336;")
            QMessageBox.critical(
                self, "Load Failed",
                f"Failed to load infrastructure configuration:\n{str(e)}"
            )

    def _apply_default_infrastructure(self):
        """Apply default infrastructure configuration without showing dialog.

        Called automatically when user clicks 'Next' without configuring infrastructure.
        """
        if 'infrastructure' not in self.cloud_resource_configs:
            self.cloud_resource_configs['infrastructure'] = {}

        # Only apply if not already configured
        if not self.cloud_resource_configs['infrastructure'].get('configured'):
            self.cloud_resource_configs['infrastructure'] = {
                'configured': True,
                'source': 'default',
                'network': {
                    'infrastructure_subnet': '10.255.0.0/16',
                    'infrastructure_bgp_as': '65534',
                    'ipv6_enabled': False,
                },
                'dns': {
                    'primary': '8.8.8.8',
                    'secondary': '8.8.4.4',
                },
                'internal_dns': {
                    'server1': '',
                    'server2': '',
                    'forward_domains': [],
                },
                'ztna': {
                    'application_networks': ['192.168.0.0/16'],
                    'controller_networks': ['10.0.0.0/8'],
                },
            }

        self.deployment_config['infrastructure_configured'] = True
        self.deployment_config['infrastructure_source'] = 'default'

        if hasattr(self, 'infra_status_label'):
            self.infra_status_label.setText("Status: Using default configuration")
            self.infra_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")

    def _import_existing_systems(self):
        """Show dialog to add existing deployed cloud resources or physical hardware."""
        from PyQt6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Import Existing Deployed Systems")
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(dialog)

        info_label = QLabel("Add existing deployed resources (firewalls, Panorama, servers, VMs) that should be integrated with this deployment.")
        info_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Two-column layout
        main_layout = QHBoxLayout()

        # Left: Add device form
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)

        add_label = QLabel("<b>Add Device:</b>")
        left_layout.addWidget(add_label)

        form = QFormLayout()
        form.setSpacing(8)

        device_type_combo = QComboBox()
        device_type_combo.addItems(["Firewall", "Panorama", "ServerVM", "UserVM"])
        form.addRow("Type:", device_type_combo)

        # Credentials fields (for Firewall/Panorama)
        creds_widget = QWidget()
        creds_layout = QFormLayout(creds_widget)
        creds_layout.setContentsMargins(0, 0, 0, 0)

        mgmt_ip_input = QLineEdit()
        mgmt_ip_input.setPlaceholderText("IP or hostname")
        creds_layout.addRow("Management IP:", mgmt_ip_input)

        username_input = QLineEdit()
        username_input.setPlaceholderText("admin")
        creds_layout.addRow("Username:", username_input)

        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_input.setPlaceholderText("Password or API key")
        creds_layout.addRow("Password:", password_input)

        # Services field (for ServerVM/UserVM)
        services_widget = QWidget()
        services_layout = QFormLayout(services_widget)
        services_layout.setContentsMargins(0, 0, 0, 0)

        services_input = QLineEdit()
        services_input.setPlaceholderText("e.g., DNS, Web, AD")
        services_layout.addRow("Services/Role:", services_input)
        services_widget.setVisible(False)

        def on_type_changed(device_type):
            is_scannable = device_type in ("Firewall", "Panorama")
            creds_widget.setVisible(is_scannable)
            services_widget.setVisible(not is_scannable)

        device_type_combo.currentTextChanged.connect(on_type_changed)

        left_layout.addLayout(form)
        left_layout.addWidget(creds_widget)
        left_layout.addWidget(services_widget)

        add_btn = QPushButton("+ Add Device")
        add_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px; "
            "font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        left_layout.addWidget(add_btn)
        left_layout.addStretch()

        main_layout.addWidget(left_widget)

        # Right: Device list
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)

        list_label = QLabel("<b>Existing Systems:</b>")
        right_layout.addWidget(list_label)

        devices_list = QListWidget()
        devices_list.setMinimumHeight(200)
        devices_list.setStyleSheet(
            "QListWidget { border: 1px solid #ccc; border-radius: 4px; background-color: white; }"
            "QListWidget::item { padding: 4px; color: #333; }"
            "QListWidget::item:selected { background-color: #e3f2fd; color: #333; }"
        )

        # Populate from existing config
        existing = self.cloud_resource_configs.get('existing_devices', [])
        for dev in existing:
            dtype = dev.get('device_type', 'Unknown')
            if dev.get('scannable', True):
                icon = "🔥" if dtype == "Firewall" else "🌐"
                devices_list.addItem(f"{icon} {dtype}: {dev.get('mgmt_ip', '?')}")
            else:
                icon = "🖥️" if dtype == "ServerVM" else "💻"
                devices_list.addItem(f"{icon} {dtype}: {dev.get('services', '?')}")

        right_layout.addWidget(devices_list)

        remove_btn = QPushButton("- Remove Selected")
        remove_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; padding: 8px; "
            "font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #d32f2f; }"
        )
        right_layout.addWidget(remove_btn)

        main_layout.addWidget(right_widget, 1)
        layout.addLayout(main_layout)

        # Local device list for dialog
        dialog_devices = list(existing)

        def add_device():
            dtype = device_type_combo.currentText()
            is_scannable = dtype in ("Firewall", "Panorama")

            if is_scannable:
                ip = mgmt_ip_input.text().strip()
                user = username_input.text().strip()
                pwd = password_input.text()
                if not ip or not user or not pwd:
                    QMessageBox.warning(dialog, "Missing Info", "Please fill in all credential fields.")
                    return
                device = {'device_type': dtype, 'mgmt_ip': ip, 'username': user, 'password': pwd, 'scannable': True}
                icon = "🔥" if dtype == "Firewall" else "🌐"
                devices_list.addItem(f"{icon} {dtype}: {ip}")
                mgmt_ip_input.clear()
                username_input.clear()
                password_input.clear()
            else:
                services = services_input.text().strip()
                if not services:
                    QMessageBox.warning(dialog, "Missing Info", "Please enter services/role.")
                    return
                device = {'device_type': dtype, 'services': services, 'scannable': False}
                icon = "🖥️" if dtype == "ServerVM" else "💻"
                devices_list.addItem(f"{icon} {dtype}: {services}")
                services_input.clear()

            dialog_devices.append(device)

        def remove_device():
            row = devices_list.currentRow()
            if row >= 0:
                devices_list.takeItem(row)
                if row < len(dialog_devices):
                    dialog_devices.pop(row)

        add_btn.clicked.connect(add_device)
        remove_btn.clicked.connect(remove_device)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec():
            # Save to config
            self.cloud_resource_configs['existing_devices'] = dialog_devices
            count = len(dialog_devices)
            if count > 0:
                self.infra_status_label.setText(f"Status: ✓ {count} existing system(s) configured")
                self.infra_status_label.setStyleSheet("color: #FF9800; font-weight: bold; margin-top: 10px;")
            logger.info(f"Configured {count} existing systems")

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
        # Check for existing devices
        existing_devices = self.cloud_resource_configs.get('existing_devices', [])
        has_existing = len(existing_devices) > 0

        config = {
            "management_type": self.management_type,
            "deployment_method": "terraform",  # Default to Terraform deployment
            "has_existing_resources": has_existing,
        }

        # Add customer information
        customer_info = self.cloud_resource_configs.get('customer_info', {})
        if customer_info:
            config["customer_name"] = customer_info.get('customer_name', '')
            config["customer_industry"] = customer_info.get('customer_industry', '')

        # Add SCM tenant info if connected
        if self.api_client and self.connection_name:
            config["scm_tenant"] = {
                "name": self.connection_name,
                "connected": True,
            }

        # Add cloud deployment configuration
        config["cloud_deployment"] = self.cloud_resource_configs.get('cloud_deployment', {})

        # Add locations (branches and datacenters)
        locations = self.cloud_resource_configs.get('locations', {})
        config["locations"] = locations

        # Generate firewalls list from locations
        # Only traditional DCs get firewalls; SD-WAN DCs get ION devices
        firewalls = []
        ion_devices = []
        fw_index = 1

        # Firewalls/ION for datacenters with service connections
        for dc in locations.get('datacenters', []):
            if dc.get('connection_type') == 'service_connection':
                dc_style = dc.get('style', 'traditional')
                if dc_style == 'sdwan_ha':
                    # HA pair: deploy 2 IONs in separate availability zones
                    for i in range(1, 3):
                        ion_devices.append({
                            'name': f"ion-{dc['name'].lower().replace(' ', '-')}-{i}",
                            'type': 'service_connection',
                            'location': dc['name'],
                            'region': dc.get('region', 'eastus'),
                            'style': 'sdwan_ha',
                            'ha_peer': i,
                            'availability_zone': str(i),
                        })
                elif dc_style == 'sdwan':
                    ion_devices.append({
                        'name': f"ion-{dc['name'].lower().replace(' ', '-')}",
                        'type': 'service_connection',
                        'location': dc['name'],
                        'region': dc.get('region', 'eastus'),
                        'style': 'sdwan',
                    })
                else:
                    firewalls.append({
                        'name': f"fw-{dc['name'].lower().replace(' ', '-')}",
                        'type': 'service_connection',
                        'location': dc['name'],
                        'region': dc.get('region', 'eastus'),
                    })
                    fw_index += 1

        # Firewalls for branches (remote networks)
        for branch in locations.get('branches', []):
            firewalls.append({
                'name': f"fw-{branch['name'].lower().replace(' ', '-')}",
                'type': 'remote_network',
                'location': branch['name'],
                'region': branch.get('region', 'eastus'),
            })
            fw_index += 1

        config["firewalls"] = firewalls
        config["ion_devices"] = ion_devices

        # Add services configuration
        config["services"] = self.cloud_resource_configs.get('services', {})

        # Add trust devices configuration
        config["trust_devices"] = self.cloud_resource_configs.get('trust_devices', {})

        # Add existing device credentials if resources already deployed
        if has_existing:
            existing_devices = self.cloud_resource_configs.get('existing_devices', [])
            if existing_devices:
                config["existing_devices"] = existing_devices

        return config

    def _get_firewall_credentials(self) -> Optional[Dict[str, str]]:
        """Get firewall credentials from the existing devices config."""
        existing_devices = self.cloud_resource_configs.get('existing_devices', [])

        # Find first firewall with credentials
        for device in existing_devices:
            if device.get('device_type') == 'Firewall' and device.get('scannable'):
                mgmt_ip = device.get('mgmt_ip', '')
                username = device.get('username', '')
                password = device.get('password', '')

                if mgmt_ip and username and password:
                    return {
                        "mgmt_ip": mgmt_ip,
                        "username": username,
                        "password": password,
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

    def _on_cloud_region_changed(self, region: str):
        """Handle region change in Cloud Deployment card."""
        self._update_cloud_rg_preview()
        # Sync to cloud_resource_configs
        self.cloud_resource_configs['cloud_deployment']['location'] = region
        self._update_cloud_deployment_status()
        logger.info(f"Primary region set to: {region}")

    def _update_cloud_rg_preview(self):
        """Update the resource group name preview."""
        if not hasattr(self, 'customer_name_input') or not hasattr(self, 'cloud_region_combo'):
            return

        # Use sanitized customer name for resource group
        customer = self._sanitize_customer_name(self.customer_name_input.text())
        region = self.cloud_region_combo.currentText()

        if customer and region:
            rg_name = f"{customer}-{region}-pov-rg"
            self.cloud_rg_preview.setText(f"<b>{rg_name}</b>")
            self.cloud_rg_preview.setStyleSheet("font-size: 12px; color: #2E7D32;")
        else:
            self.cloud_rg_preview.setText("<i>(enter customer name on Tenant Info tab)</i>")
            self.cloud_rg_preview.setStyleSheet("font-size: 12px; color: #666;")

    def _update_cloud_deployment_status(self):
        """Update Cloud Deployment card status based on required fields."""
        if not hasattr(self, 'customer_name_input'):
            return

        customer = self.customer_name_input.text().strip()
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

    def _copy_to_clipboard(self, text: str, label: str = ""):
        """Copy text to clipboard and show brief confirmation."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        if not text:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        # Show brief toast if available
        if hasattr(self, 'show_success_toast') and self.show_success_toast:
            self.show_success_toast(f"Copied {label} to clipboard", 1500)
        else:
            self._log_activity(f"Copied {label} to clipboard")

    def _populate_deployment_credentials(self):
        """Populate the credentials storage with deployed resource info."""
        if not hasattr(self, 'view_credentials_btn'):
            return

        # Get terraform outputs
        outputs = getattr(self, '_terraform_outputs', {})
        if not outputs:
            return

        # Get credentials from config
        cloud_deployment = self.cloud_resource_configs.get('cloud_deployment', {})
        admin_username = cloud_deployment.get('admin_username', '')
        admin_password = cloud_deployment.get('admin_password', '')

        # If no stored username, derive from customer name
        if not admin_username:
            customer_info = self.cloud_resource_configs.get('customer_info', {})
            customer_name = customer_info.get('customer_name_sanitized', '')
            if customer_name:
                admin_username = f"{customer_name}admin"

        # Find firewall management IP
        fw_ip = None
        for key, value in outputs.items():
            if not value:
                continue
            key_lower = key.lower()
            # Skip private IPs
            if 'private' in key_lower:
                continue
            # Look for management IP
            if ('firewall' in key_lower or 'fw' in key_lower) and ('mgmt' in key_lower or 'management' in key_lower or 'public' in key_lower):
                fw_ip = value
                break

        # Fallback: look for any firewall IP that's not private
        if not fw_ip:
            for key, value in outputs.items():
                if not value:
                    continue
                key_lower = key.lower()
                if 'private' in key_lower:
                    continue
                if 'firewall' in key_lower or 'fw_' in key_lower:
                    fw_ip = value
                    break

        # Find firewall FQDN (DNS name)
        fw_fqdn = None
        for key, value in outputs.items():
            if not value:
                continue
            key_lower = key.lower()
            if 'fqdn' in key_lower and ('firewall' in key_lower or 'fw' in key_lower or key_lower.endswith('_fqdn')):
                fw_fqdn = value
                break

        # Find server/VM IPs
        vm_ips = []
        for key, value in outputs.items():
            if not value:
                continue
            key_lower = key.lower()
            # Look for server, client, or vm private IPs
            if any(term in key_lower for term in ['server', 'client', 'vm', 'trust_device']):
                if 'private' in key_lower or 'ip' in key_lower:
                    vm_ips.append(value)

        # Store credentials internally (more secure - not displayed until requested)
        self._deployed_credentials = {
            'firewall': {
                'ip': fw_ip or "Not found",
                'fqdn': fw_fqdn or "",
                'username': admin_username or "admin",
                'password': admin_password or "",
            },
            'vms': {
                'ips': vm_ips,
                'username': admin_username or "",
                'password': admin_password or "",
            },
        }

        # Show the View Credentials button
        if hasattr(self, 'view_credentials_btn'):
            self.view_credentials_btn.setVisible(True)
        self._log_activity("Deployment credentials available (click 'View Credentials' to see)")

    def _show_credentials_dialog(self):
        """Show dialog with deployed resource credentials."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QFrame

        if not hasattr(self, '_deployed_credentials') or not self._deployed_credentials:
            QMessageBox.information(
                self, "No Credentials",
                "No deployment credentials available. Deploy infrastructure first."
            )
            return

        creds = self._deployed_credentials

        dialog = QDialog(self)
        dialog.setWindowTitle("Deployed Resource Credentials")
        dialog.setMinimumWidth(450)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)

        # Security notice
        notice = QLabel(
            "🔐 <b>Security Notice:</b> These credentials provide administrative access to your "
            "deployed resources. Keep them secure and do not share."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("background-color: #FFF3E0; padding: 10px; border-radius: 5px; color: #E65100;")
        layout.addWidget(notice)

        # Firewall section
        fw_label = QLabel("<b>🔥 Firewall Credentials</b>")
        fw_label.setStyleSheet("font-size: 13px; margin-top: 5px;")
        layout.addWidget(fw_label)

        fw_grid = QGridLayout()
        fw_grid.setColumnStretch(1, 1)

        # Firewall IP
        fw_grid.addWidget(QLabel("Management IP:"), 0, 0)
        fw_ip_field = QLineEdit(creds['firewall']['ip'])
        fw_ip_field.setReadOnly(True)
        fw_ip_field.setStyleSheet("background-color: #f5f5f5; padding: 5px;")
        fw_grid.addWidget(fw_ip_field, 0, 1)
        fw_ip_copy = QPushButton("Copy")
        fw_ip_copy.setFixedWidth(60)
        fw_ip_copy.clicked.connect(lambda: self._copy_to_clipboard(creds['firewall']['ip'], "Firewall IP"))
        fw_grid.addWidget(fw_ip_copy, 0, 2)

        # Firewall Management URL (HTTPS)
        row_offset = 1
        fw_fqdn = creds['firewall'].get('fqdn', '')
        if fw_fqdn:
            # Create full HTTPS URL for management access
            fw_url = f"https://{fw_fqdn}"
            fw_grid.addWidget(QLabel("Management URL:"), row_offset, 0)
            fw_url_field = QLineEdit(fw_url)
            fw_url_field.setReadOnly(True)
            fw_url_field.setStyleSheet("background-color: #f5f5f5; padding: 5px;")
            fw_url_field.setToolTip("HTTPS management URL - use this for browser access")
            fw_grid.addWidget(fw_url_field, row_offset, 1)
            fw_url_copy = QPushButton("Copy")
            fw_url_copy.setFixedWidth(60)
            fw_url_copy.clicked.connect(lambda: self._copy_to_clipboard(fw_url, "Management URL"))
            fw_grid.addWidget(fw_url_copy, row_offset, 2)
            row_offset += 1

        # Firewall Username
        fw_grid.addWidget(QLabel("Username:"), row_offset, 0)
        fw_user_field = QLineEdit(creds['firewall']['username'])
        fw_user_field.setReadOnly(True)
        fw_user_field.setStyleSheet("background-color: #f5f5f5; padding: 5px;")
        fw_grid.addWidget(fw_user_field, row_offset, 1)
        fw_user_copy = QPushButton("Copy")
        fw_user_copy.setFixedWidth(60)
        fw_user_copy.clicked.connect(lambda: self._copy_to_clipboard(creds['firewall']['username'], "Username"))
        fw_grid.addWidget(fw_user_copy, row_offset, 2)
        row_offset += 1

        # Firewall Password
        fw_grid.addWidget(QLabel("Password:"), row_offset, 0)
        fw_pwd_field = QLineEdit(creds['firewall']['password'])
        fw_pwd_field.setReadOnly(True)
        fw_pwd_field.setEchoMode(QLineEdit.EchoMode.Password)
        fw_pwd_field.setStyleSheet("background-color: #f5f5f5; padding: 5px;")
        fw_grid.addWidget(fw_pwd_field, row_offset, 1)

        fw_pwd_btns = QHBoxLayout()
        fw_show_btn = QPushButton("Show")
        fw_show_btn.setFixedWidth(60)
        fw_show_btn.setCheckable(True)
        fw_show_btn.clicked.connect(lambda checked: fw_pwd_field.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        ))
        fw_pwd_btns.addWidget(fw_show_btn)
        fw_pwd_copy = QPushButton("Copy")
        fw_pwd_copy.setFixedWidth(60)
        fw_pwd_copy.clicked.connect(lambda: self._copy_to_clipboard(creds['firewall']['password'], "Password"))
        fw_pwd_btns.addWidget(fw_pwd_copy)
        fw_grid.addLayout(fw_pwd_btns, row_offset, 2)

        layout.addLayout(fw_grid)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # VM/Server section
        vm_label = QLabel("<b>🖥️ Server/VM Credentials</b>")
        vm_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(vm_label)

        vm_grid = QGridLayout()
        vm_grid.setColumnStretch(1, 1)

        # VM IPs
        vm_ips_str = ", ".join(creds['vms']['ips']) if creds['vms']['ips'] else "No servers deployed"
        vm_grid.addWidget(QLabel("Server IPs:"), 0, 0)
        vm_ip_field = QLineEdit(vm_ips_str)
        vm_ip_field.setReadOnly(True)
        vm_ip_field.setStyleSheet("background-color: #f5f5f5; padding: 5px;")
        vm_grid.addWidget(vm_ip_field, 0, 1)
        vm_ip_copy = QPushButton("Copy")
        vm_ip_copy.setFixedWidth(60)
        vm_ip_copy.clicked.connect(lambda: self._copy_to_clipboard(vm_ips_str, "Server IPs"))
        vm_grid.addWidget(vm_ip_copy, 0, 2)

        # VM Username
        vm_grid.addWidget(QLabel("Username:"), 1, 0)
        vm_user_field = QLineEdit(creds['vms']['username'])
        vm_user_field.setReadOnly(True)
        vm_user_field.setStyleSheet("background-color: #f5f5f5; padding: 5px;")
        vm_grid.addWidget(vm_user_field, 1, 1)
        vm_user_copy = QPushButton("Copy")
        vm_user_copy.setFixedWidth(60)
        vm_user_copy.clicked.connect(lambda: self._copy_to_clipboard(creds['vms']['username'], "Username"))
        vm_grid.addWidget(vm_user_copy, 1, 2)

        # VM Password
        vm_grid.addWidget(QLabel("Password:"), 2, 0)
        vm_pwd_field = QLineEdit(creds['vms']['password'])
        vm_pwd_field.setReadOnly(True)
        vm_pwd_field.setEchoMode(QLineEdit.EchoMode.Password)
        vm_pwd_field.setStyleSheet("background-color: #f5f5f5; padding: 5px;")
        vm_grid.addWidget(vm_pwd_field, 2, 1)

        vm_pwd_btns = QHBoxLayout()
        vm_show_btn = QPushButton("Show")
        vm_show_btn.setFixedWidth(60)
        vm_show_btn.setCheckable(True)
        vm_show_btn.clicked.connect(lambda checked: vm_pwd_field.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        ))
        vm_pwd_btns.addWidget(vm_show_btn)
        vm_pwd_copy = QPushButton("Copy")
        vm_pwd_copy.setFixedWidth(60)
        vm_pwd_copy.clicked.connect(lambda: self._copy_to_clipboard(creds['vms']['password'], "Password"))
        vm_pwd_btns.addWidget(vm_pwd_copy)
        vm_grid.addLayout(vm_pwd_btns, 2, 2)

        layout.addLayout(vm_grid)

        # Access note
        access_note = QLabel(
            "<i>Connect via HTTPS to firewall management IP, or SSH to server IPs. "
            "Ensure your source IP is allowed in the NSG rules.</i>"
        )
        access_note.setWordWrap(True)
        access_note.setStyleSheet("color: #666; margin-top: 10px; font-size: 11px;")
        layout.addWidget(access_note)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            "QPushButton { background-color: #607D8B; color: white; padding: 8px 20px; "
            "font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #546E7A; }"
        )
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

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
        import sys

        self._log_activity("Detecting public IP address...")

        # Method 1: Try curl (available on Linux, macOS, Windows 10+)
        try:
            self._log_activity("Trying curl method...")
            result = subprocess.run(
                ['curl', '-s', '--connect-timeout', '5', 'https://ipinfo.io/ip'],
                capture_output=True, text=True, timeout=10
            )
            self._log_activity(f"curl returncode: {result.returncode}")
            if result.returncode == 0:
                ip = result.stdout.strip()
                if ip and self._is_valid_ip(ip):
                    if hasattr(self, 'cloud_security_source_ips'):
                        self.cloud_security_source_ips.setText(f"{ip}/32")
                        self._log_activity(f"Detected public IP via curl: {ip}")
                        logger.info(f"Detected public IP: {ip}")
                        return
                else:
                    self._log_activity(f"curl returned invalid IP: '{ip}'", "warning")
            else:
                self._log_activity(f"curl failed: {result.stderr}", "warning")
        except FileNotFoundError:
            self._log_activity("curl not found, trying alternative methods...", "warning")
        except Exception as e:
            self._log_activity(f"curl method failed: {type(e).__name__}: {e}", "warning")

        # Method 2: Try PowerShell (Windows)
        if sys.platform == 'win32':
            try:
                self._log_activity("Trying PowerShell method...")
                ps_cmd = "(Invoke-WebRequest -Uri 'https://ipinfo.io/ip' -UseBasicParsing -TimeoutSec 5).Content.Trim()"
                result = subprocess.run(
                    ['powershell', '-Command', ps_cmd],
                    capture_output=True, text=True, timeout=15
                )
                self._log_activity(f"PowerShell returncode: {result.returncode}")
                if result.returncode == 0:
                    ip = result.stdout.strip()
                    if ip and self._is_valid_ip(ip):
                        if hasattr(self, 'cloud_security_source_ips'):
                            self.cloud_security_source_ips.setText(f"{ip}/32")
                            self._log_activity(f"Detected public IP via PowerShell: {ip}")
                            logger.info(f"Detected public IP: {ip}")
                            return
                    else:
                        self._log_activity(f"PowerShell returned invalid IP: '{ip}'", "warning")
                else:
                    self._log_activity(f"PowerShell failed: {result.stderr}", "warning")
            except Exception as e:
                self._log_activity(f"PowerShell method failed: {type(e).__name__}: {e}", "warning")

        # Method 3: Try Python urllib (cross-platform fallback)
        try:
            self._log_activity("Trying Python urllib method...")
            import urllib.request
            with urllib.request.urlopen('https://ipinfo.io/ip', timeout=5) as response:
                ip = response.read().decode('utf-8').strip()
                if ip and self._is_valid_ip(ip):
                    if hasattr(self, 'cloud_security_source_ips'):
                        self.cloud_security_source_ips.setText(f"{ip}/32")
                        self._log_activity(f"Detected public IP via urllib: {ip}")
                        logger.info(f"Detected public IP: {ip}")
                        return
                else:
                    self._log_activity(f"urllib returned invalid IP: '{ip}'", "warning")
        except Exception as e:
            self._log_activity(f"urllib method failed: {type(e).__name__}: {e}", "warning")

        # Fallback - set to 0.0.0.0/0 with warning
        self._log_activity("All IP detection methods failed, using 0.0.0.0/0", "warning")
        if hasattr(self, 'cloud_security_source_ips'):
            if not self.cloud_security_source_ips.text():
                self.cloud_security_source_ips.setText("0.0.0.0/0")

    def _is_valid_ip(self, ip: str) -> bool:
        """Check if string is a valid IPv4 address."""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        parts = ip.split('.')
        return all(0 <= int(p) <= 255 for p in parts)

    def _on_deploy_cloud_changed(self, state):
        """Handle deploy cloud resources toggle change."""
        from PyQt6.QtCore import Qt

        is_enabled = state == Qt.CheckState.Checked.value

        # Enable/disable all cards in the scroll area
        if hasattr(self, 'cloud_resources_scroll'):
            self.cloud_resources_scroll.setEnabled(is_enabled)

        # Update deployment_config
        self.deployment_config['deploy_cloud_resources'] = is_enabled

        # Update Next button state:
        # - If cloud deployment disabled: enable Next button (no Terraform needed)
        # - If cloud deployment enabled: disable Next until Terraform deployed
        if hasattr(self, 'cloud_deploy_next_btn'):
            if is_enabled:
                # Cloud deployment enabled - check if already deployed
                already_deployed = hasattr(self, '_terraform_deployed') and self._terraform_deployed
                self.cloud_deploy_next_btn.setEnabled(already_deployed)
                if already_deployed:
                    self.cloud_deploy_next_btn.setToolTip("Proceed to deploy POV configuration")
                else:
                    self.cloud_deploy_next_btn.setToolTip("Deploy Terraform first to enable this button")
            else:
                # Cloud deployment disabled - enable Next button
                self.cloud_deploy_next_btn.setEnabled(True)
                self.cloud_deploy_next_btn.setToolTip("Proceed to deploy POV configuration (no cloud resources)")

        logger.info(f"Cloud deployment {'enabled' if is_enabled else 'disabled'}")

    def _validate_cloud_resources_tab(self) -> bool:
        """Validate Cloud Resources tab before proceeding to next tab.

        Returns True if validation passes, False if blocked.
        """
        deploy_enabled = self.deployment_config.get('deploy_cloud_resources', False)

        # If deploying cloud resources, no special validation needed
        if deploy_enabled:
            # Cloud resource configs are already populated via inline editing
            logger.info("Cloud deployment enabled - including cloud resources in config")
            return True

        # Not deploying cloud resources - check Panorama requirements
        if self.management_type == 'panorama':
            # Check if Panorama exists in existing_devices (not a placeholder)
            existing_devices = self.cloud_resource_configs.get('existing_devices', [])
            has_panorama = any(
                d.get('device_type') == 'Panorama' and not d.get('placeholder', False)
                for d in existing_devices
            )

            if not has_panorama:
                # No Panorama and not deploying cloud resources - error
                QMessageBox.warning(
                    self, "Panorama Required",
                    "Panorama Managed deployment requires either:\n\n"
                    "• An existing Panorama system (configure in Tab 1: Import Existing Systems)\n"
                    "• Cloud deployment enabled to deploy a new Panorama\n\n"
                    "Please enable 'Deploy Cloud Resources' or add an existing Panorama."
                )
                return False

            # Has existing Panorama - can proceed without cloud deployment
            logger.info("Panorama Managed with existing Panorama - skipping cloud deployment")
        else:
            # SCM Managed - can proceed without cloud deployment
            logger.info("SCM Managed - cloud deployment optional, skipping")

        # Clear cloud resource configs since not deploying
        self._clear_cloud_resource_configs()
        return True

    def _clear_cloud_resource_configs(self):
        """Clear cloud resource configs when not deploying cloud infrastructure."""
        # Keep customer_info, infrastructure, existing_devices
        # Clear deployment-specific configs
        self.cloud_resource_configs['cloud_deployment'] = {}
        self.cloud_resource_configs['cloud_security'] = {}
        self.cloud_resource_configs['device_config'] = {}
        self.cloud_resource_configs['policy_objects'] = {}
        self.cloud_resource_configs['locations'] = {'branches': [], 'datacenters': []}
        self.cloud_resource_configs['trust_devices'] = {'devices': []}

        logger.info("Cleared cloud resource configurations (deployment disabled)")

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
        self._sync_branches_to_remote_branch_card()

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
        self._sync_branches_to_remote_branch_card()

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

        # Determine style from dropdown
        style_text = self.dc_style_combo.currentText() if hasattr(self, 'dc_style_combo') else "Traditional (Firewall)"
        if 'ION HA' in style_text:
            style = 'sdwan_ha'
        elif 'SD-WAN' in style_text:
            style = 'sdwan'
        else:
            style = 'traditional'

        # Create datacenter entry
        datacenter = {
            'name': name,
            'cloud': 'Azure',
            'region': region,
            'style': style,
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
            style = dc.get('style', 'traditional')
            icon = "\U0001f4e1" if style in ('sdwan', 'sdwan_ha') else "\U0001f525"  # 📡 or 🔥
            style_label = "ION-HA" if style == 'sdwan_ha' else "SD-WAN" if style == 'sdwan' else "FW"
            item = QListWidgetItem(f"{icon} {dc['name']} ({dc['region']}) [{style_label}]")
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
    # SERVICES & APPLICATIONS HANDLERS
    # ============================================================================

    def _update_services_status(self):
        """Update the Services card status and persist config."""
        domain = self.services_domain_input.text().strip() if hasattr(self, 'services_domain_input') else ''

        # Persist to config
        services_config = self.cloud_resource_configs.get('services', {})
        services_config['domain'] = domain
        services_config['pki'] = {
            'server_cert': self.pki_server_cert_cb.isChecked() if hasattr(self, 'pki_server_cert_cb') else True,
            'device_certs': self.pki_device_certs_cb.isChecked() if hasattr(self, 'pki_device_certs_cb') else True,
            'user_certs': self.pki_user_certs_cb.isChecked() if hasattr(self, 'pki_user_certs_cb') else True,
            'decryption_ca': self.pki_decryption_ca_cb.isChecked() if hasattr(self, 'pki_decryption_ca_cb') else True,
        }
        self.cloud_resource_configs['services'] = services_config

        if not domain:
            if hasattr(self, 'services_status'):
                self.services_status.setText("")
            if hasattr(self, 'services_summary'):
                self.services_summary.setText("Enter a domain to enable services")
            return

        from gui.workflows.pov_services import DEFAULT_APPLICATIONS
        app_count = len(DEFAULT_APPLICATIONS)

        # Build PKI summary
        pki_parts = []
        if services_config['pki'].get('server_cert'):
            pki_parts.append('Server')
        if services_config['pki'].get('device_certs'):
            pki_parts.append('Device')
        if services_config['pki'].get('user_certs'):
            pki_parts.append('User')
        if services_config['pki'].get('decryption_ca'):
            pki_parts.append('Decrypt')
        pki_label = "Full" if len(pki_parts) == 4 else ", ".join(pki_parts) if pki_parts else "None"

        if hasattr(self, 'services_status'):
            self.services_status.setText(f"✓ {domain}")
            self.services_status.setStyleSheet("color: #4CAF50; font-size: 11px;")

        if hasattr(self, 'services_summary'):
            self.services_summary.setText(f"✓ {app_count} apps @ {domain} | DNS + HTTPS | PKI: {pki_label}")

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

        # 1 Linux ServerVM (DNS/WebApp) per datacenter + ION device entry for SD-WAN DCs
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

            # For single SD-WAN DCs, also create an ION device entry
            # ION HA pairs are managed at infrastructure level, not as trust devices
            dc_style = dc.get('style', 'traditional')
            if dc_style == 'sdwan':
                ion_name = f"{dc['name']}-ION"
                auto_device_names.add(ion_name)
                if not any(d['name'] == ion_name for d in current_devices):
                    new_devices.append({
                        'id': str(uuid.uuid4()),
                        'name': ion_name,
                        'location': dc['name'],
                        'location_type': 'datacenter',
                        'device_type': 'ION',
                        'subtype': 'SD-WAN',
                        'services': [],
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
            elif device['device_type'] == 'ION':
                icon = "\U0001f4e1"  # 📡
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

        # Exclude Panorama from count if Panorama Managed
        if self.management_type == 'panorama':
            count = len([d for d in devices if d.get('device_type') != 'Panorama'])
        else:
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
            'prisma_browser': 'Prisma Access Browser',
            'private_app': 'Private App Access',
            'remote_branch': 'Connect Remote Branch',
            'aiops_adem': 'AIOPS-ADEM',
            'app_accel': 'App Acceleration',
            'rbi': 'Remote Browser Isolation',
            'custom_policies': 'Custom Security Policies',
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
        # Guard against being called during widget initialization
        if not hasattr(self, 'mobile_explicit_proxy'):
            return

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
            'explicit_proxy': self.mobile_explicit_proxy.isChecked(),
        }
        self._update_use_case_status('mobile_users')

    def _on_prisma_browser_changed(self):
        """Handle Prisma Browser inline field changes."""
        self.use_case_configs['prisma_browser'] = {
            'enabled': self.prisma_browser_enable.isChecked(),
            'default_policy': self.browser_default_policy.isChecked(),
            'device_posture': self.browser_device_posture.isChecked(),
            'route_traffic': self.browser_route_traffic.currentText(),
        }
        self._update_use_case_status('prisma_browser')

        # Auto-enable explicit proxy in Mobile Users if routing traffic through PA
        route_traffic = self.browser_route_traffic.currentText()
        browser_enabled = self.prisma_browser_enable.isChecked()

        if browser_enabled and route_traffic in ("Route private apps only", "Route all traffic to PA"):
            # Auto-enable and grey out the checkbox
            self.mobile_explicit_proxy.setChecked(True)
            self.mobile_explicit_proxy.setEnabled(False)
            self.explicit_proxy_hint.setText("⚠️ Auto-enabled by Prisma Browser routing")
        else:
            # Re-enable user control
            self.mobile_explicit_proxy.setEnabled(True)
            self.explicit_proxy_hint.setText("")

        # Update mobile users config to reflect the change
        self._on_mobile_users_changed()

    def _on_private_app_changed(self):
        """Handle Private App Access inline field changes."""
        # Connections are managed via refresh method, just update enabled state
        config = self.use_case_configs.get('private_app', {})
        config['enabled'] = self.private_app_enable.isChecked()
        self.use_case_configs['private_app'] = config
        self._update_use_case_status('private_app')

    def _on_private_app_selection_changed(self, row: int):
        """Handle Private App connection selection change."""
        if row < 0:
            self.remove_ztna_btn.setEnabled(False)
            return

        connections = self.use_case_configs.get('private_app', {}).get('connections', [])
        if row >= len(connections):
            return

        conn = connections[row]

        # Enable remove button only for custom ZTNA connectors
        is_custom = conn.get('custom', False)
        self.remove_ztna_btn.setEnabled(is_custom)

    def _on_private_app_item_clicked(self, item):
        """Handle click on a connection item to toggle type."""
        row = self.private_app_connections_list.currentRow()
        if row < 0:
            return

        connections = self.use_case_configs.get('private_app', {}).get('connections', [])
        if row >= len(connections):
            return

        conn = connections[row]
        loc_type = conn.get('type', 'datacenter')

        # Handle branches: toggle RN <-> RN + ZTNA
        if loc_type == 'branch':
            ztna_count = sum(1 for c in connections if c.get('connection_type') == 'ztna')
            has_ztna = conn.get('has_ztna', False)

            if has_ztna:
                # Remove ZTNA from branch
                conn['has_ztna'] = False
            else:
                # Add ZTNA to branch - check limit
                if ztna_count >= 10:
                    QMessageBox.warning(
                        self, "Limit Reached",
                        "Maximum of 10 ZTNA Connectors allowed."
                    )
                    return
                conn['has_ztna'] = True

            self._refresh_private_app_connections_display()
            self._update_private_app_limits()
            self._on_private_app_changed()
            return

        # Handle datacenters: toggle connection type
        if conn.get('locked', False) or loc_type != 'datacenter':
            return

        # Count current SC and ZTNA
        sc_count = sum(1 for c in connections if c.get('connection_type') == 'service_connection')
        ztna_count = sum(1 for c in connections if c.get('connection_type') == 'ztna')

        current_type = conn.get('connection_type', 'service_connection')
        is_sdwan = conn.get('style', 'traditional') == 'sdwan'

        if is_sdwan:
            # SD-WAN (ION) DCs: toggle none <-> service_connection (no ZTNA option)
            if current_type == 'none':
                if sc_count >= 5:
                    QMessageBox.warning(
                        self, "Limit Reached",
                        "Maximum of 5 Service Connections allowed."
                    )
                    return
                conn['connection_type'] = 'service_connection'
            else:
                conn['connection_type'] = 'none'
        else:
            # Traditional DCs: toggle SC <-> ZTNA
            if current_type == 'service_connection':
                # Switching to ZTNA - check ZTNA limit
                if ztna_count >= 10:
                    QMessageBox.warning(
                        self, "Limit Reached",
                        "Maximum of 10 ZTNA Connectors allowed."
                    )
                    return
                conn['connection_type'] = 'ztna'
            else:
                # Switching to SC - check SC limit
                if sc_count >= 5:
                    QMessageBox.warning(
                        self, "Limit Reached",
                        "Maximum of 5 Service Connections allowed."
                    )
                    return
                conn['connection_type'] = 'service_connection'

        # Refresh display and update limits label
        self._refresh_private_app_connections_display()
        self._update_private_app_limits()
        self._on_private_app_changed()

    def _add_ztna_connector(self):
        """Add a new custom ZTNA connector."""
        from PyQt6.QtWidgets import QInputDialog

        # Check ZTNA limit first
        connections = self.use_case_configs.get('private_app', {}).get('connections', [])
        ztna_count = sum(1 for c in connections if c.get('connection_type') == 'ztna')
        if ztna_count >= 10:
            QMessageBox.warning(
                self, "Limit Reached",
                "Maximum of 10 ZTNA Connectors allowed.\n\n"
                "You can convert an existing Service Connection to ZTNA by clicking on it."
            )
            return

        name, ok = QInputDialog.getText(
            self, "Add ZTNA Connector",
            "Enter a name for the ZTNA connector:\n\n"
            "(This creates a placeholder in a new Connector Group)"
        )
        if not ok or not name.strip():
            return

        name = name.strip()

        # Check for duplicates
        if any(c['name'] == name for c in connections):
            QMessageBox.warning(self, "Duplicate", f"A connection named '{name}' already exists.")
            return

        # Add custom ZTNA connector
        conn = {
            'name': name,
            'type': 'datacenter',
            'connection_type': 'ztna',
            'locked': False,
            'custom': True,
        }
        connections.append(conn)

        # Also track in custom_ztna list
        if 'custom_ztna' not in self.use_case_configs['private_app']:
            self.use_case_configs['private_app']['custom_ztna'] = []
        self.use_case_configs['private_app']['custom_ztna'].append(name)

        # Refresh display and update limits
        self._refresh_private_app_connections_display()
        self._update_private_app_limits()
        self._on_private_app_changed()

    def _remove_ztna_connector(self):
        """Remove the selected custom ZTNA connector."""
        row = self.private_app_connections_list.currentRow()
        if row < 0:
            return

        connections = self.use_case_configs.get('private_app', {}).get('connections', [])
        if row >= len(connections):
            return

        conn = connections[row]
        if not conn.get('custom', False):
            QMessageBox.information(
                self, "Cannot Remove",
                "Only custom ZTNA connectors can be removed. Location-based connections are managed from the Locations tab."
            )
            return

        # Remove from connections and custom_ztna list
        name = conn['name']
        connections.pop(row)
        custom_list = self.use_case_configs['private_app'].get('custom_ztna', [])
        if name in custom_list:
            custom_list.remove(name)

        # Refresh display and update limits
        self._refresh_private_app_connections_display()
        self._update_private_app_limits()
        self._on_private_app_changed()

    def _update_private_app_limits(self):
        """Update the Private App limits label with current counts."""
        connections = self.use_case_configs.get('private_app', {}).get('connections', [])
        sc_count = sum(1 for c in connections if c.get('connection_type') == 'service_connection')
        # Count ZTNA connectors + branches with ZTNA enabled
        ztna_count = sum(1 for c in connections if c.get('connection_type') == 'ztna')
        ztna_count += sum(1 for c in connections if c.get('type') == 'branch' and c.get('has_ztna', False))

        # Color code based on limits
        sc_color = "#f44336" if sc_count >= 5 else "#666"
        ztna_color = "#f44336" if ztna_count >= 10 else "#666"

        self.private_app_limits_label.setText(
            f"<span style='color:{sc_color}'>SC: {sc_count}/5</span> | "
            f"<span style='color:{ztna_color}'>ZTNA: {ztna_count}/10</span>"
        )

    def _refresh_private_app_connections_display(self):
        """Refresh the Private App connections list display only (not data)."""
        self.private_app_connections_list.clear()
        connections = self.use_case_configs.get('private_app', {}).get('connections', [])

        for conn in connections:
            name = conn['name']
            conn_type = conn.get('connection_type', 'service_connection')
            is_locked = conn.get('locked', False)
            is_custom = conn.get('custom', False)
            loc_type = conn.get('type', 'datacenter')

            if loc_type == 'branch':
                icon = "🏢"
                has_ztna = conn.get('has_ztna', False)
                if has_ztna:
                    type_display = "Remote Network + ZTNA"
                    suffix = ""
                else:
                    type_display = "Remote Network"
                    suffix = " (click to add ZTNA)"
            elif conn_type == 'none':
                icon = "\U0001f4e1" if conn.get('style') == 'sdwan' else "🏛️"  # 📡
                type_display = "None"
                suffix = " (click to enable SC)"
            elif conn_type == 'ztna':
                icon = "🔗" if is_custom else "🏛️"
                type_display = "ZTNA Connector"
                suffix = " (custom)" if is_custom else ""
            else:
                icon = "🏛️"
                type_display = "Service Connection"
                suffix = " (required)" if is_locked else ""

            self.private_app_connections_list.addItem(f"{icon} {name} → {type_display}{suffix}")

    def _on_remote_branch_changed(self):
        """Handle Remote Branch inline field changes."""
        config = self.use_case_configs.get('remote_branch', {})
        config['enabled'] = self.remote_branch_enable.isChecked()
        config['sdwan_integration'] = self.branch_sdwan.isChecked()
        config['bgp_routing'] = self.branch_bgp.isChecked()
        self.use_case_configs['remote_branch'] = config
        self._update_use_case_status('remote_branch')

    def _add_bandwidth_allocation(self):
        """Add a bandwidth allocation for a Prisma Access region."""
        region = self.branch_bw_region_combo.currentText()
        # Parse "200 Mbps" to get 200
        bandwidth_text = self.branch_bw_amount_combo.currentText()
        bandwidth = int(bandwidth_text.replace(" Mbps", ""))

        config = self.use_case_configs.get('remote_branch', {})
        allocations = config.get('bandwidth_allocations', [])

        # Check total bandwidth limit
        current_total = sum(a['bandwidth'] for a in allocations)
        if current_total + bandwidth > 1000:
            QMessageBox.warning(
                self, "Bandwidth Limit",
                f"Cannot add {bandwidth} Mbps. Total would exceed 1000 Mbps.\n"
                f"Currently allocated: {current_total} Mbps\n"
                f"Available: {1000 - current_total} Mbps"
            )
            return

        # Check for duplicate region
        if any(a['region'] == region for a in allocations):
            QMessageBox.warning(
                self, "Duplicate Region",
                f"Bandwidth already allocated to {region}. Remove it first to change."
            )
            return

        # Add allocation
        allocations.append({'region': region, 'bandwidth': bandwidth})
        config['bandwidth_allocations'] = allocations
        self.use_case_configs['remote_branch'] = config

        # Refresh UI and reassign branches to closest regions
        self._sync_branches_to_remote_branch_card()
        self._refresh_remote_branch_lists()
        self._on_remote_branch_changed()

    def _remove_bandwidth_allocation(self):
        """Remove selected bandwidth allocation."""
        row = self.branch_bw_list.currentRow()
        if row < 0:
            return

        config = self.use_case_configs.get('remote_branch', {})
        allocations = config.get('bandwidth_allocations', [])

        if row < len(allocations):
            allocations.pop(row)
            config['bandwidth_allocations'] = allocations
            self.use_case_configs['remote_branch'] = config

            # Reassign branches to closest remaining regions
            self._sync_branches_to_remote_branch_card()
            self._refresh_remote_branch_lists()
            self._on_remote_branch_changed()

    def _add_staged_branch(self):
        """Add a staged branch (config only, no Azure deployment)."""
        name = self.staged_branch_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter a branch name.")
            return

        region = self.staged_branch_region.currentText()
        if not region:
            QMessageBox.warning(
                self, "No Region",
                "Please allocate bandwidth to a region first, then select it."
            )
            return

        config = self.use_case_configs.get('remote_branch', {})
        staged = config.get('staged_branches', [])
        cloud = config.get('cloud_branches', [])

        # Check for duplicates
        all_names = [b['name'] for b in staged] + [b['name'] for b in cloud]
        if name in all_names:
            QMessageBox.warning(self, "Duplicate", f"A branch named '{name}' already exists.")
            return

        staged.append({'name': name, 'region': region, 'staged': True})
        config['staged_branches'] = staged
        self.use_case_configs['remote_branch'] = config

        # Clear input and refresh
        self.staged_branch_name.clear()
        self._refresh_remote_branch_lists()
        self._on_remote_branch_changed()

    def _remove_staged_branch(self):
        """Remove selected staged branch (only staged branches can be removed)."""
        row = self.branch_list.currentRow()
        if row < 0:
            return

        config = self.use_case_configs.get('remote_branch', {})
        cloud = config.get('cloud_branches', [])
        staged = config.get('staged_branches', [])

        # Cloud branches come first in the list
        if row < len(cloud):
            QMessageBox.information(
                self, "Cannot Remove",
                "Cloud-deployed branches are managed from the Locations tab (Step 2).\n"
                "Only staged branches can be removed here."
            )
            return

        # Remove from staged list
        staged_index = row - len(cloud)
        if staged_index < len(staged):
            staged.pop(staged_index)
            config['staged_branches'] = staged
            self.use_case_configs['remote_branch'] = config

            self._refresh_remote_branch_lists()
            self._on_remote_branch_changed()

    def _refresh_remote_branch_lists(self):
        """Refresh the bandwidth and branch lists."""
        config = self.use_case_configs.get('remote_branch', {})

        # Refresh bandwidth list
        self.branch_bw_list.clear()
        allocations = config.get('bandwidth_allocations', [])
        total_bw = 0
        for alloc in allocations:
            self.branch_bw_list.addItem(f"📍 {alloc['region']}: {alloc['bandwidth']} Mbps")
            total_bw += alloc['bandwidth']

        # Update total label with color coding
        color = "#f44336" if total_bw >= 1000 else "#666"
        self.branch_bw_total_label.setText(f"Bandwidth: <span style='color:{color}'>{total_bw}/1000 Mbps</span>")

        # Update staged branch region dropdown with only allocated regions
        self.staged_branch_region.clear()
        if allocations:
            for alloc in allocations:
                self.staged_branch_region.addItem(alloc['region'])
        else:
            self.staged_branch_region.setPlaceholderText("Allocate BW first")

        # Refresh branch list
        self.branch_list.clear()

        # Cloud-deployed branches first (from Locations tab)
        cloud_branches = config.get('cloud_branches', [])
        for branch in cloud_branches:
            assigned_region = branch.get('assigned_region', branch.get('region', '?'))
            self.branch_list.addItem(f"☁️ {branch['name']} → {assigned_region} (cloud)")

        # Staged branches
        staged_branches = config.get('staged_branches', [])
        for branch in staged_branches:
            self.branch_list.addItem(f"📋 {branch['name']} → {branch['region']} (staged)")

    def _sync_branches_to_remote_branch_card(self):
        """Sync branches from Locations tab to Remote Branch card with auto-allocation."""
        locations = self.cloud_resource_configs.get('locations', {})
        branches = locations.get('branches', [])

        config = self.use_case_configs.get('remote_branch', {})
        allocations = config.get('bandwidth_allocations', [])

        # Map each branch's Azure region to closest Prisma Access location
        pa_locations_needed = set()
        branch_pa_mapping = {}

        for branch in branches:
            azure_region = branch.get('region', 'eastus')
            pa_location = self._azure_to_prisma_access_location(azure_region)
            pa_locations_needed.add(pa_location)
            branch_pa_mapping[branch['name']] = pa_location

        # Auto-allocate bandwidth for PA locations not already allocated
        already_allocated = {a['region'] for a in allocations}
        new_locations = pa_locations_needed - already_allocated

        if new_locations:
            # Determine bandwidth: 200 Mbps default, 100 Mbps if 4+ unique regions
            total_regions = len(already_allocated) + len(new_locations)
            default_bw = 100 if total_regions >= 4 else 200

            # Check if we have enough bandwidth capacity
            current_total = sum(a['bandwidth'] for a in allocations)
            needed_bw = len(new_locations) * default_bw

            if current_total + needed_bw > 1000:
                # Reduce bandwidth per region to fit
                available = 1000 - current_total
                default_bw = max(50, available // len(new_locations)) if new_locations else 50

            for pa_loc in new_locations:
                if current_total + default_bw <= 1000:
                    allocations.append({'region': pa_loc, 'bandwidth': default_bw})
                    current_total += default_bw

        # Build list of cloud branches with assigned PA locations
        cloud_branches = []
        for branch in branches:
            pa_location = branch_pa_mapping.get(branch['name'], 'US East')
            cloud_branches.append({
                'name': branch['name'],
                'region': branch.get('region', 'eastus'),  # Azure region
                'assigned_region': pa_location,  # Prisma Access location
                'staged': False,
            })

        config['bandwidth_allocations'] = allocations
        config['cloud_branches'] = cloud_branches
        self.use_case_configs['remote_branch'] = config

        # Refresh the display
        if hasattr(self, 'branch_list'):
            self._refresh_remote_branch_lists()

    def _azure_to_prisma_access_location(self, azure_region: str) -> str:
        """Map Azure region to closest Prisma Access location."""
        # Azure region to Prisma Access location mapping
        mapping = {
            # US regions
            'eastus': 'US East',
            'eastus2': 'US East',
            'centralus': 'US Central',
            'westus': 'US West',
            'westus2': 'US West',
            'westus3': 'US West',
            'northcentralus': 'US Central',
            'southcentralus': 'US Central',
            # Europe regions
            'northeurope': 'Europe North',
            'westeurope': 'Europe West',
            'uksouth': 'UK',
            'ukwest': 'UK',
            'francecentral': 'Europe West',
            'germanywestcentral': 'Germany',
            # Asia Pacific regions
            'australiaeast': 'Australia East',
            'australiasoutheast': 'Australia Southeast',
            'southeastasia': 'Singapore',
            'eastasia': 'Hong Kong',
            'japaneast': 'Japan Central',
            'japanwest': 'Japan Central',
            'koreacentral': 'South Korea',
            'indiacentral': 'India West',
            # Default
        }
        return mapping.get(azure_region, 'US East')

    def _find_closest_bandwidth_region(self, branch_region: str, allocations: list) -> str:
        """Find the closest bandwidth allocation region (PA location) to an Azure region."""
        if not allocations:
            return self._azure_to_prisma_access_location(branch_region)

        # Get the PA location for this Azure region
        target_pa = self._azure_to_prisma_access_location(branch_region)

        # Check if we already have this PA location allocated
        for alloc in allocations:
            if alloc['region'] == target_pa:
                return target_pa

        # Group PA locations by continent for fallback
        pa_groups = {
            'americas': ['US East', 'US West', 'US Central', 'US Northwest', 'US Southwest', 'Canada East', 'Canada West', 'Mexico Central', 'Brazil South'],
            'europe': ['Europe North', 'Europe West', 'UK', 'Germany', 'France North', 'France South', 'Switzerland', 'Netherlands North', 'Netherlands South'],
            'asia': ['Singapore', 'Hong Kong', 'Japan Central', 'Japan South', 'South Korea', 'India West', 'India South', 'Taiwan'],
            'oceania': ['Australia East', 'Australia Southeast', 'New Zealand'],
        }

        # Find which group target PA location belongs to
        target_group = None
        for group, locations in pa_groups.items():
            if target_pa in locations:
                target_group = group
                break

        # Try to find an allocation in the same group
        for alloc in allocations:
            for group, locations in pa_groups.items():
                if alloc['region'] in locations and group == target_group:
                    return alloc['region']

        # No same-group allocation, return first allocation's region
        return allocations[0]['region']

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

    def _on_custom_policies_changed(self):
        """Handle Custom Security Policies inline field changes."""
        # Guard against being called during widget initialization
        if not hasattr(self, 'custom_policies_list'):
            return

        # Gather enabled policies from list
        enabled_policies = []
        for i in range(self.custom_policies_list.count()):
            item = self.custom_policies_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                enabled_policies.append(item.text())

        # Preserve staged_objects if they exist
        existing = self.use_case_configs.get('custom_policies', {})
        staged = existing.get('staged_objects', {})

        self.use_case_configs['custom_policies'] = {
            'enabled': self.custom_policies_enable.isChecked(),
            'policies': enabled_policies,
            'staged_objects': staged,
            'customer_prefix': existing.get('customer_prefix', ''),
            'source_tenant': existing.get('source_tenant', ''),
            'generated_at': existing.get('generated_at', ''),
        }
        self._update_use_case_status('custom_policies')

    def _add_custom_policy(self):
        """Add a custom policy to the list."""
        from PyQt6.QtWidgets import QListWidgetItem

        policy_text = self.custom_policy_input.text().strip()
        if not policy_text:
            return

        # Add to list with checkbox
        item = QListWidgetItem(policy_text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        self.custom_policies_list.addItem(item)

        # Clear input
        self.custom_policy_input.clear()

        # Update config
        self._on_custom_policies_changed()

    def _sync_use_cases_from_cloud_resources(self):
        """Sync use case defaults based on cloud resources configuration.

        Called when entering Tab 3 (POV Use Cases) to auto-enable use cases
        based on what was configured in Tab 2 (Cloud Resources).
        """
        # Enable Remote Branch if any branches were configured
        branches = self.cloud_resource_configs.get('locations', {}).get('branches', [])
        if branches and hasattr(self, 'remote_branch_enable'):
            if not self.remote_branch_enable.isChecked():
                self.remote_branch_enable.setChecked(True)
                self._on_remote_branch_changed()
                logger.info(f"Auto-enabled Remote Branch use case - {len(branches)} branches configured")

    def _populate_adem_defaults(self):
        """Populate ADEM with default test entries.

        Adds default entries for common collaboration tools and
        unique base domains from internal DNS forward_domains.
        """
        # Only populate if ADEM list is empty
        current_tests = self.use_case_configs.get('aiops_adem', {}).get('tests', [])
        if current_tests:
            return  # Don't override existing entries

        # Default entries for collaboration tools
        default_entries = ['teams.microsoft.com', 'zoom.us']

        # Add unique base domains from internal DNS forward_domains
        internal_dns = self.cloud_resource_configs.get('infrastructure', {}).get('internal_dns', {})
        forward_domains = internal_dns.get('forward_domains', [])

        for domain in forward_domains:
            # Extract base domain (remove wildcard prefixes)
            base = domain
            if base.startswith('^.') or base.startswith('*.'):
                base = base[2:]
            elif base.startswith('^') or base.startswith('*'):
                base = base[1:]

            # Get base domain (last two parts for typical domains)
            parts = base.split('.')
            if len(parts) >= 2:
                base_domain = '.'.join(parts[-2:])
                if base_domain not in default_entries and base_domain != domain:
                    default_entries.append(base_domain)

        # Add entries to ADEM list
        for entry in default_entries:
            self._add_adem_entry(entry)

        if default_entries:
            logger.info(f"Populated ADEM with {len(default_entries)} default entries")

    def _add_adem_entry(self, target: str):
        """Add an ADEM test entry programmatically.

        Args:
            target: IP address or domain name to test
        """
        from PyQt6.QtWidgets import QListWidgetItem

        # Check if entry already exists
        for i in range(self.adem_tests_list.count()):
            item = self.adem_tests_list.item(i)
            if target in item.text():
                return  # Already exists

        test = {
            'target': target,
            'on_vpn': True,  # Always true
            'in_office': False,
            'not_on_vpn': False,
        }

        # Add to config
        if 'tests' not in self.use_case_configs.get('aiops_adem', {}):
            self.use_case_configs['aiops_adem'] = {'enabled': False, 'tests': []}
        self.use_case_configs['aiops_adem']['tests'].append(test)

        # Add to list display
        display_text = f"{target} (VPN)"
        self.adem_tests_list.addItem(display_text)

    def _auto_generate_security_objects(self):
        """Automatically generate security objects from POV configuration.

        This runs silently in the background when entering Tab 3.
        Generates address objects from infrastructure config and clones
        security profiles from the connected tenant if available.
        """
        from datetime import datetime
        from gui.workflows.pov_security_objects import generate_staged_objects

        # Get customer prefix
        customer_info = self.cloud_resource_configs.get('customer_info', {})
        prefix = customer_info.get('customer_name_sanitized', '')

        if not prefix:
            # No customer name yet, skip generation
            return

        # Check if we need to regenerate
        custom_policies = self.use_case_configs.get('custom_policies', {})
        staged = custom_policies.get('staged_objects', {})
        existing_prefix = custom_policies.get('customer_prefix', '')

        # Skip if already generated with same prefix and has objects
        if (staged.get('address_objects') and existing_prefix == prefix):
            # Already generated, check if profiles need cloning
            if self.api_client and not staged.get('profiles'):
                # Tenant connected but no profiles - try to clone
                self._clone_profiles_to_staged(prefix)
            return

        try:
            # Generate all security objects
            staged_objects = generate_staged_objects(
                customer_prefix=prefix,
                cloud_resource_configs=self.cloud_resource_configs,
                use_case_configs=self.use_case_configs,
                api_client=self.api_client,
            )

            # Update config
            self.use_case_configs['custom_policies']['staged_objects'] = staged_objects
            self.use_case_configs['custom_policies']['customer_prefix'] = prefix
            self.use_case_configs['custom_policies']['generated_at'] = datetime.now().isoformat()

            if self.api_client:
                self.use_case_configs['custom_policies']['source_tenant'] = self.connection_name

            # Log activity
            addr_count = len(staged_objects.get('address_objects', []))
            profile_count = sum(len(v) for v in staged_objects.get('profiles', {}).values())
            logger.info(
                f"Auto-generated security objects: {addr_count} addresses, "
                f"{profile_count} profiles"
            )

        except Exception as e:
            logger.warning(f"Failed to auto-generate security objects: {e}")

    def _clone_profiles_to_staged(self, prefix: str):
        """Clone profiles from tenant to staged objects.

        Called when tenant connects and we already have address objects generated.
        """
        from datetime import datetime
        from gui.workflows.pov_security_objects import ProfileCloner

        if not self.api_client:
            return

        try:
            cloner = ProfileCloner(
                api_client=self.api_client,
                customer_prefix=prefix,
            )
            cloned_profiles = cloner.clone_all_profiles()
            profile_group = cloner.create_profile_group(cloned_profiles)

            # Update staged objects
            staged = self.use_case_configs['custom_policies'].get('staged_objects', {})
            staged['profiles'] = cloned_profiles
            staged['profile_groups'] = [profile_group] if any(cloned_profiles.values()) else []

            self.use_case_configs['custom_policies']['staged_objects'] = staged
            self.use_case_configs['custom_policies']['source_tenant'] = self.connection_name
            self.use_case_configs['custom_policies']['profiles_cloned_at'] = datetime.now().isoformat()

            profile_count = sum(len(v) for v in cloned_profiles.values())
            logger.info(f"Cloned {profile_count} security profiles from tenant")

        except Exception as e:
            logger.warning(f"Failed to clone profiles: {e}")

    def _refresh_private_app_connections(self):
        """Refresh the Private App connections list based on Locations tab data.

        Applies limits: max 5 Service Connections, max 10 ZTNA Connectors.
        When defaults exceed limits, first 5 datacenters get SC, next 10 get ZTNA.
        """
        locations = self.cloud_resource_configs.get('locations', {})

        # Get existing connections to preserve user's connection type changes
        existing_connections = {
            c['name']: c for c in self.use_case_configs.get('private_app', {}).get('connections', [])
        }

        connections = []
        sc_count = 0
        ztna_count = 0

        # Add Panorama if panorama managed (must be Service Connection, counts toward limit)
        if self.management_type == 'panorama':
            conn = {
                'name': 'Panorama',
                'type': 'datacenter',
                'connection_type': 'service_connection',
                'locked': True,  # Cannot change
                'custom': False,
            }
            connections.append(conn)
            sc_count += 1

        # Add datacenters - preserve user's type if set, otherwise assign based on limits
        # ION (SD-WAN) DCs default to 'none' — user must click to enable service connection
        for dc in locations.get('datacenters', []):
            existing = existing_connections.get(dc['name'])
            dc_style = dc.get('style', 'traditional')

            if existing:
                # Preserve user's choice
                conn_type = existing.get('connection_type', 'service_connection')
            elif dc_style == 'sdwan':
                # SD-WAN (ION) DCs default to no connection — click to enable
                conn_type = 'none'
            else:
                # Traditional datacenter - assign type based on limits
                # First 5 get SC, next 10 get ZTNA, rest are skipped
                if sc_count < 5:
                    conn_type = 'service_connection'
                elif ztna_count < 10:
                    conn_type = 'ztna'
                else:
                    # Skip this datacenter - limits reached
                    continue

            # Update counts
            if conn_type == 'service_connection':
                sc_count += 1
            elif conn_type == 'ztna':
                ztna_count += 1

            conn = {
                'name': dc['name'],
                'type': 'datacenter',
                'connection_type': conn_type,
                'locked': False,
                'custom': False,
                'style': dc_style,
            }
            connections.append(conn)

        # Add branches (always Remote Network, not changeable, doesn't count toward limits)
        for branch in locations.get('branches', []):
            conn = {
                'name': branch['name'],
                'type': 'branch',
                'connection_type': 'remote_network',
                'locked': True,  # Branches must be Remote Network
                'custom': False,
            }
            connections.append(conn)

        # Add custom ZTNA connectors (only if under ZTNA limit)
        custom_ztna = self.use_case_configs.get('private_app', {}).get('custom_ztna', [])
        for name in custom_ztna:
            # Skip if already added from locations or ZTNA limit reached
            if any(c['name'] == name for c in connections):
                continue
            if ztna_count >= 10:
                continue

            conn = {
                'name': name,
                'type': 'datacenter',
                'connection_type': 'ztna',
                'locked': False,
                'custom': True,
            }
            connections.append(conn)
            ztna_count += 1

        self.use_case_configs['private_app']['connections'] = connections

        # Refresh the display and update limits label
        self._refresh_private_app_connections_display()
        if hasattr(self, 'private_app_limits_label'):
            self._update_private_app_limits()

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
        elif level == "debug":
            logger.debug(message)
        else:
            logger.info(message)

        # Log to results panels if available
        if hasattr(self, 'cloud_deploy_results'):
            # Show debug messages with a distinct format
            if level == "debug":
                self.cloud_deploy_results.append_text(f"  {message}\n")
            else:
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

            # Sync use cases and refresh connections when entering POV Use Cases tab
            if index == 2:
                self._sync_use_cases_from_cloud_resources()
                self._populate_adem_defaults()
                self._refresh_private_app_connections()
                self._auto_generate_security_objects()

            # Auto-connect to saved deploy tenant when entering Deploy POV Config tab
            if index == 4:
                self._auto_connect_deploy_tenant()

    def _auto_connect_deploy_tenant(self):
        """Auto-connect to the saved deploy tenant if not already connected."""
        # Check if we have a saved deploy tenant name
        saved_tenant = getattr(self, '_deploy_tenant_name', None)
        if not saved_tenant:
            logger.debug("No saved deploy tenant to auto-connect")
            return

        # Check if already connected to this tenant
        if hasattr(self, 'deploy_tenant_selector'):
            current_client, current_name = self.deploy_tenant_selector.get_connection()
            if current_client and current_name == saved_tenant:
                logger.debug(f"Already connected to deploy tenant: {saved_tenant}")
                return

            # Check if tenant exists in the dropdown
            combo = self.deploy_tenant_selector.tenant_combo
            tenant_found = False
            for i in range(combo.count()):
                if combo.itemText(i) == saved_tenant:
                    tenant_found = True
                    # Ensure correct index is selected (without triggering signal)
                    combo.blockSignals(True)
                    combo.setCurrentIndex(i)
                    combo.blockSignals(False)
                    break

            if not tenant_found:
                logger.warning(f"Saved deploy tenant '{saved_tenant}' not found in tenant list")
                return

            # Directly call the connection method on the TenantSelector
            # This bypasses the combo signal issue when index is already set
            logger.info(f"Auto-connecting to saved deploy tenant: {saved_tenant}")
            self.deploy_tenant_selector._connect_to_saved_tenant(saved_tenant)

    # ============================================================================
    # EVENT HANDLERS - CLOUD DEPLOYMENT TAB (Tab 4)
    # ============================================================================

    def _authenticate_azure(self):
        """Authenticate with Azure using Interactive Browser OAuth."""
        import sys
        import os

        # Check for saved credentials first
        saved_sub_name = self.deployment_config.get('azure_subscription_name', '')
        saved_sub_id = self.deployment_config.get('azure_subscription_id', '')
        saved_tenant_id = self.deployment_config.get('azure_tenant_id', '')

        if saved_sub_name and saved_sub_id:
            # Offer to use saved credentials
            reply = QMessageBox.question(
                self,
                "Saved Azure Credentials",
                f"Found saved Azure credentials:\n\n"
                f"Subscription: {saved_sub_name}\n"
                f"ID: {saved_sub_id}\n\n"
                f"Use these credentials, or re-authenticate?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Restore saved credentials
                self._azure_subscription = {
                    'name': saved_sub_name,
                    'id': saved_sub_id,
                    'tenant_id': saved_tenant_id,
                }
                self._log_activity(f"Restored saved Azure credentials: {saved_sub_name}")
                self._on_azure_auth_success()
                return

        self._log_activity("Starting Azure authentication...")
        self.azure_auth_btn.setEnabled(False)
        self.azure_auth_status.setText("🔄 Authenticating...")
        self.azure_auth_status.setStyleSheet("font-weight: bold; color: #FF9800;")

        # Process events to update UI before blocking browser auth
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            from azure.identity import InteractiveBrowserCredential
            from azure.mgmt.subscription import SubscriptionClient
            import requests

            # Log SDK versions for debugging
            try:
                import azure.identity
                import azure.mgmt.subscription
                self._log_activity(f"SDK: azure-identity={azure.identity.__version__}, azure-mgmt-subscription={azure.mgmt.subscription.VERSION}")
            except Exception as ver_err:
                self._log_activity(f"Could not get SDK versions: {ver_err}", "warning")

            # Check if tenant ID was specified in the input field or from saved state
            specified_tenant_id = None
            if hasattr(self, 'azure_tenant_input') and self.azure_tenant_input.text().strip():
                specified_tenant_id = self.azure_tenant_input.text().strip()
                self._log_activity(f"Using specified tenant: {specified_tenant_id}")
            elif saved_tenant_id:
                # Pre-fill tenant from saved state
                specified_tenant_id = saved_tenant_id
                self._log_activity(f"Using saved tenant: {specified_tenant_id}")

            self._log_activity("Opening browser for Azure sign-in...")

            # Suppress browser subprocess stdout/stderr (Chrome warnings)
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            devnull = open(os.devnull, 'w')
            try:
                sys.stdout = devnull
                sys.stderr = devnull

                # Step 1: Initial authentication (multi-tenant if no tenant specified)
                if specified_tenant_id:
                    credential = InteractiveBrowserCredential(
                        redirect_uri="http://localhost:8400",
                        tenant_id=specified_tenant_id,
                    )
                else:
                    credential = InteractiveBrowserCredential(
                        redirect_uri="http://localhost:8400",
                    )

                # Restore stdout before logging (so our logs appear)
                sys.stdout = original_stdout
                self._log_activity("Requesting token for Azure Management API...")
                sys.stdout = devnull

                token = credential.get_token("https://management.azure.com/.default")

            finally:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                devnull.close()

            self._log_activity(f"Token acquired successfully")

            # Bring window back to focus after browser auth
            self.activateWindow()
            self.raise_()
            QApplication.processEvents()

            # Decode token to get user info
            authenticated_user = "unknown"
            home_tenant_id = None
            try:
                import base64
                import json
                payload = token.token.split('.')[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = json.loads(base64.b64decode(payload))
                home_tenant_id = decoded.get('tid', 'unknown')
                authenticated_user = decoded.get('upn', decoded.get('unique_name', 'unknown'))
                self._log_activity(f"Authenticated as: {authenticated_user}")
            except Exception as decode_err:
                self._log_activity(f"Could not decode token details: {decode_err}", "warning")

            # Step 2: If no tenant specified, list available tenants and let user choose
            selected_tenant_id = specified_tenant_id
            if not specified_tenant_id:
                self._log_activity("Fetching available directories/tenants...")
                try:
                    # Call Azure REST API to list tenants
                    headers = {"Authorization": f"Bearer {token.token}"}
                    response = requests.get(
                        "https://management.azure.com/tenants?api-version=2020-01-01",
                        headers=headers
                    )
                    response.raise_for_status()
                    tenants_data = response.json()
                    tenants = tenants_data.get('value', [])

                    self._log_activity(f"Found {len(tenants)} directory/tenant(s)")
                    for t in tenants:
                        self._log_activity(f"  - {t.get('displayName', 'Unknown')} ({t.get('tenantId')})")

                    if len(tenants) > 1:
                        # Show tenant selection dialog
                        selected_tenant = self._show_tenant_selection_dialog(tenants, home_tenant_id)
                        if selected_tenant:
                            selected_tenant_id = selected_tenant['tenantId']
                            self._log_activity(f"Selected directory: {selected_tenant.get('displayName')} ({selected_tenant_id})")
                        else:
                            self._log_activity("Tenant selection cancelled", "warning")
                            self.azure_auth_status.setText("🔴 Not authenticated")
                            self.azure_auth_status.setStyleSheet("font-weight: bold; color: #F44336;")
                            return
                    elif len(tenants) == 1:
                        selected_tenant_id = tenants[0].get('tenantId')
                        self._log_activity(f"Using only available directory: {tenants[0].get('displayName')}")
                    else:
                        raise Exception("No Azure directories found for this account")

                except requests.exceptions.RequestException as e:
                    self._log_activity(f"Failed to list tenants: {e}", "error")
                    raise Exception(f"Failed to list Azure directories: {e}")

            # Step 3: If we selected a different tenant, re-authenticate to that tenant
            if selected_tenant_id and selected_tenant_id != home_tenant_id:
                self._log_activity(f"Re-authenticating to selected directory...")
                original_stdout = sys.stdout
                original_stderr = sys.stderr
                devnull = open(os.devnull, 'w')
                try:
                    sys.stdout = devnull
                    sys.stderr = devnull
                    credential = InteractiveBrowserCredential(
                        redirect_uri="http://localhost:8400",
                        tenant_id=selected_tenant_id,
                    )
                    token = credential.get_token("https://management.azure.com/.default")
                finally:
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
                    devnull.close()
                self._log_activity(f"Token acquired for selected directory")

                # Bring window back to focus after browser auth
                self.activateWindow()
                self.raise_()
                QApplication.processEvents()

            # Step 4: List subscriptions from the selected tenant
            self._log_activity("Fetching Azure subscriptions...")
            try:
                subscription_client = SubscriptionClient(credential)
                sub_iterator = subscription_client.subscriptions.list()

                subscriptions = []
                for sub in sub_iterator:
                    self._log_activity(f"  Found: {sub.display_name} ({sub.subscription_id})")
                    subscriptions.append(sub)

                self._log_activity(f"Found {len(subscriptions)} subscription(s)")

            except Exception as sub_error:
                self._log_activity(f"Subscription list error: {type(sub_error).__name__}: {sub_error}", "error")
                raise Exception(
                    f"Failed to list Azure subscriptions: {sub_error}\n\n"
                    "This may be due to:\n"
                    "- Account doesn't have Reader access to any subscriptions\n"
                    "- Azure AD permissions issue\n"
                    "- Network/firewall blocking Azure management API"
                )

            if not subscriptions:
                raise Exception(
                    "No Azure subscriptions found in the selected directory.\n\n"
                    "Please verify:\n"
                    "- You selected the correct directory/tenant\n"
                    "- Your account has access to at least one subscription\n"
                    "- You have Reader role or higher on the subscription"
                )

            self._log_activity(f"Found {len(subscriptions)} subscription(s)")

            # Store credential for later use
            self._azure_credential = credential

            # Show subscription selection dialog (pass tenant_id for saving)
            selected_sub = self._show_subscription_dialog(subscriptions, selected_tenant_id)

            if selected_sub:
                self._azure_subscription = selected_sub
                self._log_activity(f"Selected subscription: {selected_sub['name']}")
                self._on_azure_auth_success()
            else:
                # User cancelled
                self._log_activity("Azure authentication cancelled", "warning")
                self.azure_auth_status.setText("🔴 Not authenticated")
                self.azure_auth_status.setStyleSheet("font-weight: bold; color: #F44336;")
                self._azure_credential = None

        except ImportError as e:
            self._log_activity(f"Azure SDK not installed: {e}", "error")
            QMessageBox.critical(
                self,
                "Azure SDK Missing",
                "Azure SDK packages are not installed.\n\n"
                "Please run: pip install azure-identity azure-mgmt-subscription azure-mgmt-resource"
            )
            self.azure_auth_status.setText("🔴 SDK missing")
            self.azure_auth_status.setStyleSheet("font-weight: bold; color: #F44336;")

        except Exception as e:
            self._log_activity(f"Azure authentication failed: {e}", "error")
            QMessageBox.critical(
                self,
                "Authentication Failed",
                f"Failed to authenticate with Azure:\n\n{str(e)}"
            )
            self.azure_auth_status.setText("🔴 Auth failed")
            self.azure_auth_status.setStyleSheet("font-weight: bold; color: #F44336;")
            self._azure_credential = None

        finally:
            self.azure_auth_btn.setEnabled(True)

    def _show_terraform_warning_dialog(self) -> bool:
        """Show a custom styled warning dialog for Terraform not deployed.

        Returns:
            True if user wants to continue, False to cancel
        """
        from PyQt6.QtWidgets import QDialog
        from PyQt6.QtGui import QPalette, QColor

        dialog = QDialog(self)
        dialog.setWindowTitle("⚠️ Cloud Resources Not Deployed")
        dialog.setMinimumWidth(500)
        dialog.setModal(True)

        # Use palette for background color (more reliable on Windows)
        palette = dialog.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#fff3f3"))
        dialog.setPalette(palette)
        dialog.setAutoFillBackground(True)

        # Main layout
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Red header bar
        header_widget = QWidget()
        header_widget.setAutoFillBackground(True)
        header_palette = header_widget.palette()
        header_palette.setColor(QPalette.ColorRole.Window, QColor("#f44336"))
        header_widget.setPalette(header_palette)
        header_widget.setMinimumHeight(60)

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 10, 20, 10)

        warning_icon = QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 28px; color: white;")
        header_layout.addWidget(warning_icon)

        title = QLabel("Terraform Not Deployed!")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        main_layout.addWidget(header_widget)

        # Content area
        content_widget = QWidget()
        content_widget.setAutoFillBackground(True)
        content_palette = content_widget.palette()
        content_palette.setColor(QPalette.ColorRole.Window, QColor("#fff3f3"))
        content_widget.setPalette(content_palette)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # Warning message
        message = QLabel(
            "Cloud resource deployment is enabled but you haven't deployed Terraform yet.\n\n"
            "Your Azure infrastructure (VNet, subnets, VMs) will <b>NOT</b> be created."
        )
        message.setWordWrap(True)
        message.setStyleSheet("color: #333; font-size: 13px;")
        content_layout.addWidget(message)

        # Red border warning box
        warning_frame = QFrame()
        warning_frame.setFrameShape(QFrame.Shape.Box)
        warning_frame.setLineWidth(2)
        warning_frame.setAutoFillBackground(True)
        warning_palette = warning_frame.palette()
        warning_palette.setColor(QPalette.ColorRole.Window, QColor("#ffebee"))
        warning_frame.setPalette(warning_palette)
        warning_frame.setStyleSheet("QFrame { border: 2px solid #f44336; border-radius: 4px; }")

        warning_layout = QVBoxLayout(warning_frame)
        warning_layout.setContentsMargins(15, 15, 15, 15)
        warning_label = QLabel(
            "⛔ <b>Warning:</b> Proceeding without Terraform deployment means "
            "no Azure infrastructure will be created for this POV."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #c62828; font-size: 12px;")
        warning_layout.addWidget(warning_label)
        content_layout.addWidget(warning_frame)

        # Question
        question = QLabel("Do you want to continue anyway?")
        question.setStyleSheet("color: #333; font-size: 13px; font-weight: bold;")
        content_layout.addWidget(question)

        content_layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        no_btn = QPushButton("Go Back and Deploy")
        no_btn.setMinimumWidth(150)
        no_btn.setMinimumHeight(36)
        no_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        no_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(no_btn)

        yes_btn = QPushButton("Continue Anyway")
        yes_btn.setMinimumWidth(150)
        yes_btn.setMinimumHeight(36)
        yes_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        yes_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(yes_btn)

        content_layout.addLayout(btn_layout)
        main_layout.addWidget(content_widget)

        return dialog.exec() == QDialog.DialogCode.Accepted

    def _show_deploy_confirmation_dialog(self, is_update: bool) -> bool:
        """Show a custom styled confirmation dialog for Terraform deployment.

        Args:
            is_update: True if this is updating an existing deployment

        Returns:
            True if user confirms, False to cancel
        """
        from PyQt6.QtWidgets import QDialog
        from PyQt6.QtGui import QPalette, QColor

        dialog = QDialog(self)
        dialog.setMinimumWidth(550)
        dialog.setModal(True)

        # Use amber/orange palette for caution (different from red error)
        if is_update:
            dialog.setWindowTitle("⚠️ Redeploy Terraform")
            header_color = "#FF9800"  # Orange for update
            header_text = "Redeploy to Azure"
            icon_text = "🔄"
        else:
            dialog.setWindowTitle("🚀 Deploy Terraform")
            header_color = "#FF9800"  # Orange for deploy
            header_text = "Deploy to Azure"
            icon_text = "🚀"

        # Use palette for background color (Windows compatible)
        palette = dialog.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#fff8e1"))
        dialog.setPalette(palette)
        dialog.setAutoFillBackground(True)

        # Main layout
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Orange header bar
        header_widget = QWidget()
        header_widget.setAutoFillBackground(True)
        header_palette = header_widget.palette()
        header_palette.setColor(QPalette.ColorRole.Window, QColor(header_color))
        header_widget.setPalette(header_palette)
        header_widget.setMinimumHeight(60)

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 10, 20, 10)

        header_icon = QLabel(icon_text)
        header_icon.setStyleSheet("font-size: 28px;")
        header_layout.addWidget(header_icon)

        title = QLabel(header_text)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        main_layout.addWidget(header_widget)

        # Content area
        content_widget = QWidget()
        content_widget.setAutoFillBackground(True)
        content_palette = content_widget.palette()
        content_palette.setColor(QPalette.ColorRole.Window, QColor("#fff8e1"))
        content_widget.setPalette(content_palette)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # Main message
        if is_update:
            message_text = (
                "<b>This will regenerate Terraform files and update Azure resources.</b>"
            )
        else:
            message_text = (
                "<b>This will create cloud resources in your Azure subscription.</b>"
            )
        message = QLabel(message_text)
        message.setWordWrap(True)
        message.setStyleSheet("color: #333; font-size: 13px;")
        content_layout.addWidget(message)

        # What will happen list
        list_frame = QFrame()
        list_frame.setFrameShape(QFrame.Shape.Box)
        list_frame.setAutoFillBackground(True)
        list_palette = list_frame.palette()
        list_palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        list_frame.setPalette(list_palette)
        list_frame.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 4px; }")

        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(15, 15, 15, 15)

        list_title = QLabel("<b>This operation will:</b>")
        list_title.setStyleSheet("color: #333; font-size: 12px;")
        list_layout.addWidget(list_title)

        if is_update:
            items = [
                "• Regenerate .tf files from current POV configuration",
                "• Compare with existing deployed resources",
                "• Apply updates (add/modify/remove resources)",
            ]
        else:
            items = [
                "• Initialize Terraform providers",
                "• Create a deployment plan",
                "• Deploy VNet, subnets, NSGs, and VMs to Azure",
            ]

        for item in items:
            item_label = QLabel(item)
            item_label.setStyleSheet("color: #555; font-size: 12px; margin-left: 10px;")
            list_layout.addWidget(item_label)

        content_layout.addWidget(list_frame)

        # Warning box for updates
        if is_update:
            warning_frame = QFrame()
            warning_frame.setFrameShape(QFrame.Shape.Box)
            warning_frame.setAutoFillBackground(True)
            warning_palette = warning_frame.palette()
            warning_palette.setColor(QPalette.ColorRole.Window, QColor("#fff3e0"))
            warning_frame.setPalette(warning_palette)
            warning_frame.setStyleSheet("QFrame { border: 2px solid #FF9800; border-radius: 4px; }")

            warning_layout = QVBoxLayout(warning_frame)
            warning_layout.setContentsMargins(15, 10, 15, 10)
            warning_label = QLabel(
                "⚠️ <b>Note:</b> Manual edits to .tf files will be overwritten."
            )
            warning_label.setWordWrap(True)
            warning_label.setStyleSheet("color: #e65100; font-size: 12px;")
            warning_layout.addWidget(warning_label)
            content_layout.addWidget(warning_frame)

        # Cost warning
        cost_label = QLabel(
            "💰 <i>Azure resources will incur costs. Review the Terraform plan before proceeding.</i>"
        )
        cost_label.setWordWrap(True)
        cost_label.setStyleSheet("color: #666; font-size: 11px;")
        content_layout.addWidget(cost_label)

        content_layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        if is_update:
            confirm_text = "🔄 Redeploy"
        else:
            confirm_text = "🚀 Deploy"

        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setMinimumWidth(120)
        confirm_btn.setMinimumHeight(36)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        confirm_btn.clicked.connect(dialog.accept)
        confirm_btn.setDefault(True)
        btn_layout.addWidget(confirm_btn)

        content_layout.addLayout(btn_layout)
        main_layout.addWidget(content_widget)

        return dialog.exec() == QDialog.DialogCode.Accepted

    def _show_pov_deploy_confirmation_dialog(self) -> bool:
        """Show a comprehensive styled confirmation dialog for POV deployment.

        Shows all configuration to be deployed in a tabbed view matching the review dialog,
        with deployment phases clearly outlined.

        Returns:
            True if user confirms, False to cancel
        """
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
            QTabWidget, QWidget, QGroupBox, QFrame, QPushButton
        )
        from PyQt6.QtGui import QPalette, QColor
        from PyQt6.QtCore import Qt

        deployment_config = self._gather_deployment_config()

        dialog = QDialog(self)
        dialog.setWindowTitle("Deploy POV Configuration")
        dialog.setMinimumSize(750, 650)
        dialog.setModal(True)

        # Use orange palette for caution
        palette = dialog.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#fff8e1"))
        dialog.setPalette(palette)
        dialog.setAutoFillBackground(True)

        # Main layout
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Orange header bar
        header_widget = QWidget()
        header_widget.setAutoFillBackground(True)
        header_palette = header_widget.palette()
        header_palette.setColor(QPalette.ColorRole.Window, QColor("#FF9800"))
        header_widget.setPalette(header_palette)
        header_widget.setMinimumHeight(60)

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 10, 20, 10)

        header_icon = QLabel("!!")
        header_icon.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        header_layout.addWidget(header_icon)

        title = QLabel("Deploy POV to Prisma Access")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        main_layout.addWidget(header_widget)

        # Content area
        content_widget = QWidget()
        content_widget.setAutoFillBackground(True)
        content_palette = content_widget.palette()
        content_palette.setColor(QPalette.ColorRole.Window, QColor("#fff8e1"))
        content_widget.setPalette(content_palette)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(15, 15, 15, 15)

        # Main message
        message = QLabel(
            "<b>This will deploy the full POV configuration in multiple phases.</b>"
        )
        message.setWordWrap(True)
        message.setStyleSheet("color: #333; font-size: 13px;")
        content_layout.addWidget(message)

        # Tabbed content showing all configuration
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ddd; background: white; }
            QTabBar::tab { padding: 8px 16px; }
            QTabBar::tab:selected { background: white; border-bottom: 2px solid #FF9800; }
        """)

        # === TAB 1: Infrastructure Config (ON deployed firewalls) ===
        infra_config_tab = QWidget()
        infra_config_layout = QVBoxLayout(infra_config_tab)

        infra_config_scroll = QScrollArea()
        infra_config_scroll.setWidgetResizable(True)
        infra_config_content = QWidget()
        infra_config_scroll_layout = QVBoxLayout(infra_config_content)

        # Section header
        infra_header = QLabel("<b>Configuration pushed TO deployed firewalls:</b>")
        infra_header.setStyleSheet("color: #1565C0; font-size: 12px; padding: 5px; background-color: #E3F2FD;")
        infra_config_scroll_layout.addWidget(infra_header)

        # Firewall Base Configuration
        firewalls = deployment_config.get('firewalls', [])
        fw_group = QGroupBox(f"Firewall Base Configuration ({len(firewalls)})")
        fw_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        fw_layout = QVBoxLayout(fw_group)
        if firewalls:
            for fw in firewalls:
                fw_layout.addWidget(QLabel(f"<b>{fw.get('name')}</b> ({fw.get('type', 'unknown').replace('_', ' ')})"))
            fw_layout.addWidget(QLabel("Configuration includes:"))
            fw_layout.addWidget(QLabel("  - Device settings (DNS, NTP, hostname)"))
            fw_layout.addWidget(QLabel("  - Network interfaces and security zones"))
            fw_layout.addWidget(QLabel("  - Basic security policy and outbound NAT"))
        else:
            fw_layout.addWidget(QLabel("<i>No firewalls to configure</i>"))
        infra_config_scroll_layout.addWidget(fw_group)

        # Service Connection IPsec (Firewall Side)
        datacenters = deployment_config.get('locations', {}).get('datacenters', [])
        sc_datacenters = [dc for dc in datacenters if dc.get('connection_type') == 'service_connection']

        sc_fw_group = QGroupBox(f"Service Connection IPsec - Firewall Side ({len(sc_datacenters)})")
        sc_fw_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        sc_fw_layout = QVBoxLayout(sc_fw_group)
        if sc_datacenters:
            for dc in sc_datacenters:
                sc_fw_layout.addWidget(QLabel(f"<b>{dc.get('name')}</b> - {dc.get('region', 'Unknown')}"))
            sc_fw_layout.addWidget(QLabel("Configuration includes:"))
            sc_fw_layout.addWidget(QLabel("  - IKE Gateway (Phase 1)"))
            sc_fw_layout.addWidget(QLabel("  - IPsec Tunnel (Phase 2)"))
            sc_fw_layout.addWidget(QLabel("  - Tunnel interface"))
            sc_fw_layout.addWidget(QLabel("  - Static routes to Prisma Access"))
        else:
            sc_fw_layout.addWidget(QLabel("<i>No service connection tunnels to configure</i>"))
        infra_config_scroll_layout.addWidget(sc_fw_group)

        # Remote Network IPsec (Firewall Side)
        branches = deployment_config.get('locations', {}).get('branches', [])

        rn_fw_group = QGroupBox(f"Remote Network IPsec - Firewall Side ({len(branches)})")
        rn_fw_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        rn_fw_layout = QVBoxLayout(rn_fw_group)
        if branches:
            for branch in branches:
                rn_fw_layout.addWidget(QLabel(f"<b>{branch.get('name')}</b> - {branch.get('region', 'Unknown')}"))
            rn_fw_layout.addWidget(QLabel("Configuration includes:"))
            rn_fw_layout.addWidget(QLabel("  - IKE Gateway (Phase 1)"))
            rn_fw_layout.addWidget(QLabel("  - IPsec Tunnel (Phase 2)"))
            rn_fw_layout.addWidget(QLabel("  - Tunnel interface"))
            rn_fw_layout.addWidget(QLabel("  - BGP or static routing"))
        else:
            rn_fw_layout.addWidget(QLabel("<i>No remote network tunnels to configure</i>"))
        infra_config_scroll_layout.addWidget(rn_fw_group)

        infra_config_scroll_layout.addStretch()
        infra_config_scroll.setWidget(infra_config_content)
        infra_config_layout.addWidget(infra_config_scroll)
        tabs.addTab(infra_config_tab, "Infrastructure Config")

        # === TAB 2: Prisma Access Config (pushed TO SCM/PA) ===
        pa_config_tab = QWidget()
        pa_config_layout = QVBoxLayout(pa_config_tab)

        pa_config_scroll = QScrollArea()
        pa_config_scroll.setWidgetResizable(True)
        pa_config_content = QWidget()
        pa_config_scroll_layout = QVBoxLayout(pa_config_content)

        # Section header
        pa_header = QLabel("<b>Configuration pushed TO Prisma Access / SCM:</b>")
        pa_header.setStyleSheet("color: #E65100; font-size: 12px; padding: 5px; background-color: #FFF3E0;")
        pa_config_scroll_layout.addWidget(pa_header)

        # Service Connections (PA Side)
        sc_pa_group = QGroupBox(f"Service Connections ({len(sc_datacenters)})")
        sc_pa_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        sc_pa_layout = QVBoxLayout(sc_pa_group)
        if sc_datacenters:
            for dc in sc_datacenters:
                sc_pa_layout.addWidget(QLabel(f"<b>SC-{dc.get('name')}</b> - Region: {dc.get('region', 'Unknown')}"))
            sc_pa_layout.addWidget(QLabel("Creates in Prisma Access:"))
            sc_pa_layout.addWidget(QLabel("  - Service Connection object"))
            sc_pa_layout.addWidget(QLabel("  - IPsec tunnel endpoint"))
            sc_pa_layout.addWidget(QLabel("  - Routing to on-prem subnets"))
        else:
            sc_pa_layout.addWidget(QLabel("<i>No service connections to create</i>"))
        pa_config_scroll_layout.addWidget(sc_pa_group)

        # Remote Networks (PA Side)
        rn_pa_group = QGroupBox(f"Remote Networks ({len(branches)})")
        rn_pa_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        rn_pa_layout = QVBoxLayout(rn_pa_group)
        if branches:
            for branch in branches:
                rn_pa_layout.addWidget(QLabel(f"<b>RN-{branch.get('name')}</b> - Region: {branch.get('region', 'Unknown')}"))
            rn_pa_layout.addWidget(QLabel("Creates in Prisma Access:"))
            rn_pa_layout.addWidget(QLabel("  - Remote Network object"))
            rn_pa_layout.addWidget(QLabel("  - IPsec tunnel endpoint"))
            rn_pa_layout.addWidget(QLabel("  - BGP/Static routing"))
        else:
            rn_pa_layout.addWidget(QLabel("<i>No remote networks to create</i>"))
        pa_config_scroll_layout.addWidget(rn_pa_group)

        # Use Cases & Policy
        use_cases = self.use_case_configs
        staged = use_cases.get('custom_policies', {}).get('staged_objects', {})

        uc_group = QGroupBox("Use Cases & Features")
        uc_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        uc_layout = QVBoxLayout(uc_group)

        if use_cases.get('mobile_users', {}).get('enabled'):
            mu = use_cases.get('mobile_users', {})
            uc_layout.addWidget(QLabel(f"<b>Mobile Users</b> - Portal: {mu.get('portal_name', 'GlobalProtect')}"))

        if use_cases.get('aiops_adem', {}).get('enabled'):
            adem = use_cases.get('aiops_adem', {})
            test_count = len(adem.get('tests', []))
            uc_layout.addWidget(QLabel(f"<b>ADEM/AIOps</b> - {test_count} synthetic test(s)"))

        if use_cases.get('private_app', {}).get('enabled'):
            pa_cfg = use_cases.get('private_app', {})
            conn_count = len(pa_cfg.get('connections', []))
            uc_layout.addWidget(QLabel(f"<b>Private App Access</b> - {conn_count} connection(s)"))

        if use_cases.get('rbi', {}).get('enabled'):
            uc_layout.addWidget(QLabel("<b>Remote Browser Isolation</b> - Enabled"))

        if not any([
            use_cases.get('mobile_users', {}).get('enabled'),
            use_cases.get('aiops_adem', {}).get('enabled'),
            use_cases.get('private_app', {}).get('enabled'),
            use_cases.get('rbi', {}).get('enabled'),
        ]):
            uc_layout.addWidget(QLabel("<i>No use cases enabled</i>"))

        pa_config_scroll_layout.addWidget(uc_group)

        # Policy Objects
        addr_count = len(staged.get('address_objects', []))
        grp_count = len(staged.get('address_groups', []))
        policy_count = len(use_cases.get('custom_policies', {}).get('policies', []))

        policy_group = QGroupBox("Security Policy Objects")
        policy_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        policy_layout = QVBoxLayout(policy_group)

        if addr_count > 0 or grp_count > 0 or policy_count > 0:
            if addr_count > 0:
                policy_layout.addWidget(QLabel(f"<b>Address Objects:</b> {addr_count}"))
            if grp_count > 0:
                policy_layout.addWidget(QLabel(f"<b>Address Groups:</b> {grp_count}"))
            if policy_count > 0:
                policy_layout.addWidget(QLabel(f"<b>Security Policies:</b> {policy_count}"))
        else:
            policy_layout.addWidget(QLabel("<i>No policy objects to deploy</i>"))

        pa_config_scroll_layout.addWidget(policy_group)

        pa_config_scroll_layout.addStretch()
        pa_config_scroll.setWidget(pa_config_content)
        pa_config_layout.addWidget(pa_config_scroll)
        tabs.addTab(pa_config_tab, "Prisma Access Config")

        # === TAB 2: Infrastructure ===
        infra_tab = QWidget()
        infra_layout = QVBoxLayout(infra_tab)

        # Customer Info
        customer_info = self.cloud_resource_configs.get('customer_info', {})
        cust_group = QGroupBox("Customer")
        cust_layout = QVBoxLayout(cust_group)
        cust_layout.addWidget(QLabel(f"<b>Name:</b> {customer_info.get('customer_name', 'Not set')}"))
        cust_layout.addWidget(QLabel(f"<b>Industry:</b> {customer_info.get('industry', 'Not set')}"))
        cust_layout.addWidget(QLabel(f"<b>Management:</b> {self.management_type.upper()}"))
        if self.connection_name:
            cust_layout.addWidget(QLabel(f"<b>SCM Tenant:</b> {self.connection_name}"))
        infra_layout.addWidget(cust_group)

        # Datacenters
        dc_group = QGroupBox(f"Datacenters ({len(datacenters)})")
        dc_layout = QVBoxLayout(dc_group)
        if datacenters:
            for dc in datacenters:
                conn_type = dc.get('connection_type', 'service_connection').replace('_', ' ').title()
                dc_layout.addWidget(QLabel(
                    f"- <b>{dc.get('name', 'Datacenter')}</b> - {dc.get('cloud', 'Azure')} "
                    f"{dc.get('region', '')} ({conn_type})"
                ))
        else:
            dc_layout.addWidget(QLabel("<i>No datacenters</i>"))
        infra_layout.addWidget(dc_group)

        # Branches
        branch_group = QGroupBox(f"Branches ({len(branches)})")
        branch_layout = QVBoxLayout(branch_group)
        if branches:
            for branch in branches:
                branch_layout.addWidget(QLabel(
                    f"- <b>{branch.get('name', 'Branch')}</b> - {branch.get('region', 'Unknown region')}"
                ))
        else:
            branch_layout.addWidget(QLabel("<i>No branches</i>"))
        infra_layout.addWidget(branch_group)

        # Firewalls
        fw_group = QGroupBox(f"Firewalls ({len(firewalls)})")
        fw_layout = QVBoxLayout(fw_group)
        if firewalls:
            for fw in firewalls:
                fw_type = fw.get('type', 'unknown').replace('_', ' ').title()
                fw_layout.addWidget(QLabel(f"- <b>{fw.get('name')}</b> ({fw_type}) - {fw.get('location', '')}"))
        else:
            fw_layout.addWidget(QLabel("<i>No firewalls</i>"))
        infra_layout.addWidget(fw_group)

        infra_layout.addStretch()
        tabs.addTab(infra_tab, "Infrastructure")

        # === TAB 3: Use Cases ===
        usecases_tab = QWidget()
        usecases_layout = QVBoxLayout(usecases_tab)

        # Mobile Users
        mu = use_cases.get('mobile_users', {})
        mu_group = QGroupBox("Mobile Users")
        mu_layout = QVBoxLayout(mu_group)
        mu_enabled = "[Enabled]" if mu.get('enabled') else "[Disabled]"
        mu_layout.addWidget(QLabel(f"<b>Status:</b> {mu_enabled}"))
        if mu.get('enabled'):
            mu_layout.addWidget(QLabel(f"<b>Portal Name:</b> {mu.get('portal_name', 'Not set')}"))
            mu_layout.addWidget(QLabel(f"<b>VPN Mode:</b> {mu.get('vpn_mode', 'On Demand')}"))
        usecases_layout.addWidget(mu_group)

        # Private App Access
        pa = use_cases.get('private_app', {})
        pa_group = QGroupBox("Private App Access")
        pa_layout = QVBoxLayout(pa_group)
        pa_enabled = "[Enabled]" if pa.get('enabled') else "[Disabled]"
        pa_layout.addWidget(QLabel(f"<b>Status:</b> {pa_enabled}"))
        if pa.get('enabled'):
            connections = pa.get('connections', [])
            pa_layout.addWidget(QLabel(f"<b>Connections:</b> {len(connections)}"))
        usecases_layout.addWidget(pa_group)

        # Remote Branch
        rb = use_cases.get('remote_branch', {})
        rb_group = QGroupBox("Remote Branch")
        rb_layout = QVBoxLayout(rb_group)
        rb_enabled = "[Enabled]" if rb.get('enabled') else "[Disabled]"
        rb_layout.addWidget(QLabel(f"<b>Status:</b> {rb_enabled}"))
        if rb.get('enabled'):
            rb_layout.addWidget(QLabel(f"<b>BGP Routing:</b> {'Yes' if rb.get('bgp_routing') else 'No'}"))
        usecases_layout.addWidget(rb_group)

        # ADEM
        adem = use_cases.get('aiops_adem', {})
        adem_group = QGroupBox("AIOps / ADEM")
        adem_layout = QVBoxLayout(adem_group)
        adem_enabled = "[Enabled]" if adem.get('enabled') else "[Disabled]"
        adem_layout.addWidget(QLabel(f"<b>Status:</b> {adem_enabled}"))
        usecases_layout.addWidget(adem_group)

        usecases_layout.addStretch()
        tabs.addTab(usecases_tab, "Use Cases")

        # === TAB 4: Policy Objects ===
        policy_tab = QWidget()
        policy_layout = QVBoxLayout(policy_tab)

        custom_policies = use_cases.get('custom_policies', {})
        staged = custom_policies.get('staged_objects', {})

        # Address Objects
        addr_objs = staged.get('address_objects', [])
        addr_group = QGroupBox(f"Address Objects ({len(addr_objs)})")
        addr_layout = QVBoxLayout(addr_group)
        if addr_objs:
            for obj in addr_objs[:8]:
                addr_layout.addWidget(QLabel(f"- <b>{obj.get('name')}</b>: {obj.get('ip_netmask', '')}"))
            if len(addr_objs) > 8:
                addr_layout.addWidget(QLabel(f"<i>... and {len(addr_objs) - 8} more</i>"))
        else:
            addr_layout.addWidget(QLabel("<i>No address objects</i>"))
        policy_layout.addWidget(addr_group)

        # Address Groups
        addr_groups = staged.get('address_groups', [])
        grp_group = QGroupBox(f"Address Groups ({len(addr_groups)})")
        grp_layout = QVBoxLayout(grp_group)
        if addr_groups:
            for grp in addr_groups[:5]:
                members = ', '.join(grp.get('static', [])[:3])
                if len(grp.get('static', [])) > 3:
                    members += '...'
                grp_layout.addWidget(QLabel(f"- <b>{grp.get('name')}</b>: {members}"))
        else:
            grp_layout.addWidget(QLabel("<i>No address groups</i>"))
        policy_layout.addWidget(grp_group)

        # Policies
        policies = custom_policies.get('policies', [])
        pol_group = QGroupBox(f"Security Policies ({len(policies)})")
        pol_layout = QVBoxLayout(pol_group)
        if policies:
            for pol in policies[:5]:
                pol_layout.addWidget(QLabel(f"- {pol}"))
            if len(policies) > 5:
                pol_layout.addWidget(QLabel(f"<i>... and {len(policies) - 5} more</i>"))
        else:
            pol_layout.addWidget(QLabel("<i>No policies</i>"))
        policy_layout.addWidget(pol_group)

        policy_layout.addStretch()
        tabs.addTab(policy_tab, "Policy Objects")

        content_layout.addWidget(tabs, 1)

        # Warning box
        warning_frame = QFrame()
        warning_frame.setFrameShape(QFrame.Shape.Box)
        warning_frame.setAutoFillBackground(True)
        warning_palette = warning_frame.palette()
        warning_palette.setColor(QPalette.ColorRole.Window, QColor("#fff3e0"))
        warning_frame.setPalette(warning_palette)
        warning_frame.setStyleSheet("QFrame { border: 2px solid #FF9800; border-radius: 4px; }")

        warning_layout = QVBoxLayout(warning_frame)
        warning_layout.setContentsMargins(15, 10, 15, 10)
        warning_label = QLabel(
            "!! <b>Important:</b> This will deploy configuration to firewalls and modify your "
            "Prisma Access tenant. Review all phases above before proceeding."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #e65100; font-size: 12px;")
        warning_layout.addWidget(warning_label)
        content_layout.addWidget(warning_frame)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("Start Deployment")
        confirm_btn.setMinimumWidth(150)
        confirm_btn.setMinimumHeight(36)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        confirm_btn.clicked.connect(dialog.accept)
        confirm_btn.setDefault(True)
        btn_layout.addWidget(confirm_btn)

        content_layout.addLayout(btn_layout)
        main_layout.addWidget(content_widget)

        return dialog.exec() == QDialog.DialogCode.Accepted

    def _show_tenant_selection_dialog(self, tenants: list, current_tenant_id: str = None) -> dict:
        """Show dialog to select an Azure directory/tenant.

        Args:
            tenants: List of tenant dicts from Azure API
            current_tenant_id: The currently authenticated tenant ID (to highlight)

        Returns:
            Selected tenant dict, or None if cancelled
        """
        from PyQt6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QHeaderView
        from PyQt6.QtGui import QFont

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Azure Directory")
        dialog.setMinimumSize(650, 350)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(
            "Your Azure account has access to multiple directories (tenants).\n"
            "Select the directory that contains your Azure subscriptions."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # Table of tenants
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Directory Name", "Tenant ID", "Type"])
        table.setRowCount(len(tenants))
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setStyleSheet("QTableWidget { background-color: white; }")

        default_row = 0
        for row, tenant in enumerate(tenants):
            tenant_id = tenant.get('tenantId', 'Unknown')
            display_name = tenant.get('displayName', 'Unknown')
            tenant_type = tenant.get('tenantType', 'Unknown')

            name_item = QTableWidgetItem(display_name)
            id_item = QTableWidgetItem(tenant_id)
            type_item = QTableWidgetItem(tenant_type)

            # Highlight current tenant
            if tenant_id == current_tenant_id:
                name_item.setText(f"{display_name} (current)")
                font = QFont()
                font.setItalic(True)
                name_item.setFont(font)
                id_item.setFont(font)
                type_item.setFont(font)
            else:
                # Select first non-current tenant as default (likely has subscriptions)
                if default_row == 0 or (current_tenant_id and tenant_id != current_tenant_id and default_row == 0):
                    default_row = row

            table.setItem(row, 0, name_item)
            table.setItem(row, 1, id_item)
            table.setItem(row, 2, type_item)

        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(table)

        # Auto-select (prefer a non-current tenant since current has no subscriptions)
        if tenants:
            # Find a tenant that's not the current one
            for i, t in enumerate(tenants):
                if t.get('tenantId') != current_tenant_id:
                    table.selectRow(i)
                    break
            else:
                table.selectRow(0)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #757575; color: white; padding: 8px 16px; "
            "font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #616161; }"
        )
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        select_btn = QPushButton("Select Directory")
        select_btn.setStyleSheet(
            "QPushButton { background-color: #0078D4; color: white; padding: 8px 16px; "
            "font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #106EBE; }"
        )

        def on_select():
            selected = table.selectedItems()
            if selected:
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "No Selection", "Please select a directory.")

        select_btn.clicked.connect(on_select)
        btn_layout.addWidget(select_btn)

        layout.addLayout(btn_layout)

        # Store tenants for retrieval
        dialog.tenants = tenants

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_row = table.currentRow()
            if selected_row >= 0:
                return tenants[selected_row]

        return None

    def _show_subscription_dialog(self, subscriptions: list, tenant_id: str = None) -> dict:
        """Show dialog to select an Azure subscription.

        Args:
            subscriptions: List of Azure subscription objects
            tenant_id: The Azure tenant ID to include in the result

        Returns:
            Selected subscription dict with 'id', 'name', and 'tenant_id', or None if cancelled
        """
        from PyQt6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QHeaderView

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Azure Subscription")
        dialog.setMinimumSize(600, 350)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(
            "Select the Azure subscription to use for POV resource deployment."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # Table of subscriptions
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Subscription Name", "Subscription ID", "State"])
        table.setRowCount(len(subscriptions))
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        for row, sub in enumerate(subscriptions):
            table.setItem(row, 0, QTableWidgetItem(sub.display_name))
            table.setItem(row, 1, QTableWidgetItem(sub.subscription_id))
            # Handle state as string or enum
            state_str = str(sub.state) if sub.state else "Unknown"
            if hasattr(sub.state, 'value'):
                state_str = sub.state.value
            table.setItem(row, 2, QTableWidgetItem(state_str))

        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)

        # Auto-select first row
        if subscriptions:
            table.selectRow(0)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #757575; color: white; padding: 8px 16px; "
            "font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #616161; }"
        )
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        select_btn = QPushButton("Select Subscription")
        select_btn.setStyleSheet(
            "QPushButton { background-color: #0078D4; color: white; padding: 8px 16px; "
            "font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #106EBE; }"
        )

        def on_select():
            selected = table.selectedItems()
            if selected:
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "No Selection", "Please select a subscription.")

        select_btn.clicked.connect(on_select)
        btn_layout.addWidget(select_btn)

        layout.addLayout(btn_layout)

        # Store subscriptions for retrieval
        dialog.subscriptions = subscriptions
        dialog.table = table

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_row = table.currentRow()
            if selected_row >= 0:
                sub = subscriptions[selected_row]
                # Handle state as string or enum
                state_str = str(sub.state) if sub.state else "Unknown"
                if hasattr(sub.state, 'value'):
                    state_str = sub.state.value
                return {
                    'id': sub.subscription_id,
                    'name': sub.display_name,
                    'state': state_str,
                    'tenant_id': tenant_id or '',
                }

        return None

    def _build_cloud_config(self) -> dict:
        """Build CloudConfig dictionary from UI selections."""
        from config.models.cloud import CloudConfig

        deployment_config = self._gather_deployment_config()

        # Get customer info
        customer_info = self.cloud_resource_configs.get('customer_info', {})
        customer_name = customer_info.get('customer_name_sanitized', 'pov')

        # Get location from first datacenter
        locations = self.cloud_resource_configs.get('locations', {})
        datacenters = locations.get('datacenters', [])
        azure_region = 'eastus'
        if datacenters:
            azure_region = datacenters[0].get('region', 'eastus')

        # Get Azure subscription/tenant from auth
        subscription_id = ''
        tenant_id = ''
        if hasattr(self, '_azure_subscription') and self._azure_subscription:
            subscription_id = self._azure_subscription.get('id', '')
            tenant_id = self._azure_subscription.get('tenant_id', '')

        # Build deployment dict
        deployment_dict = {
            'customer_name': customer_name,
            'management_type': deployment_config.get('management_type', 'scm'),
            'provider': 'azure',
            'location': azure_region,
            'subscription_id': subscription_id,
            'tenant_id': tenant_id,
        }

        # Build firewalls list
        firewalls_list = []
        for i, fw_config in enumerate(deployment_config.get('firewalls', [])):
            fw_type = "datacenter" if fw_config.get('type') == 'service_connection' else "branch"
            fw_dict = {
                'name': f"fw{i+1}" if len(deployment_config.get('firewalls', [])) > 1 else "fw",
                'firewall_type': fw_type,
            }
            firewalls_list.append(fw_dict)

        # Build Panorama if Panorama-managed
        panorama_dict = None
        if deployment_config.get('management_type') == 'panorama':
            panorama_dict = {'name': 'panorama'}

        # Create config from raw_config dict
        raw_config = {
            'deployment': deployment_dict,
            'firewalls': firewalls_list,
            'panorama': panorama_dict,
        }

        config = CloudConfig(raw_config)
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

        # Bring window back to focus after browser auth
        self.activateWindow()
        self.raise_()

        # Update status with subscription info
        sub_name = self._azure_subscription.get('name', 'Unknown') if hasattr(self, '_azure_subscription') else 'Unknown'
        self.azure_auth_status.setText(f"🟢 {sub_name}")
        self.azure_auth_status.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self.azure_auth_status.setToolTip(
            f"Subscription: {sub_name}\n"
            f"ID: {self._azure_subscription.get('id', 'N/A')}"
        )

        # Save Azure credentials to deployment_config for state persistence
        if hasattr(self, '_azure_subscription') and self._azure_subscription:
            self.deployment_config['azure_subscription_id'] = self._azure_subscription.get('id', '')
            self.deployment_config['azure_subscription_name'] = self._azure_subscription.get('name', '')
            self.deployment_config['azure_tenant_id'] = self._azure_subscription.get('tenant_id', '')
            # Immediately save state so credentials persist
            self.save_state()
            self._log_activity(f"Saved Azure credentials to state: {self._azure_subscription.get('name')}")

            # Check Azure CLI auth status (non-blocking, just warns if expired)
            self._prime_azure_cli_auth()

        # Change button to allow re-authentication
        self.azure_auth_btn.setText("🔄 Change Subscription")

        # Show terraform generation status
        self.terraform_status_widget.setVisible(True)

        # Generate Terraform configuration
        self._generate_terraform_from_pov()

    def _generate_terraform_from_pov(self, force_regenerate: bool = False):
        """Generate Terraform configuration from POV settings.

        Args:
            force_regenerate: If True, skip the prompt for existing files
        """
        import os
        import tempfile
        from datetime import datetime

        self._log_activity("Generating Terraform configuration...")
        self.terraform_gen_status.setText("⏳ Generating Terraform configuration...")

        try:
            # Get customer info
            customer_info = self.cloud_resource_configs.get('customer_info', {})
            customer_name = customer_info.get('customer_name_sanitized', 'pov')

            # Get first datacenter for location info
            locations = self.cloud_resource_configs.get('locations', {})
            datacenters = locations.get('datacenters', [])

            # Determine Azure region from datacenter or default
            azure_region = 'eastus'
            if datacenters:
                azure_region = datacenters[0].get('region', 'eastus')

            # Get subscription info from Azure auth
            subscription_id = ''
            tenant_id = ''
            if hasattr(self, '_azure_subscription') and self._azure_subscription:
                subscription_id = self._azure_subscription.get('id', '')
                tenant_id = self._azure_subscription.get('tenant_id', '')

            # Get cloud deployment settings
            cloud_deployment = self.cloud_resource_configs.get('cloud_deployment', {})
            admin_username = cloud_deployment.get('admin_username', f'{customer_name}admin')
            admin_password = cloud_deployment.get('admin_password', '')

            # Get security settings
            cloud_security = self.cloud_resource_configs.get('cloud_security', {})
            source_ips = cloud_security.get('source_ips', '')

            # Create output directory
            output_base = os.path.join(
                os.path.expanduser('~'),
                '.pa_config_lab',
                'terraform',
                customer_name
            )
            os.makedirs(output_base, exist_ok=True)

            # Create terraform subdirectory
            terraform_dir = os.path.join(output_base, 'terraform')
            os.makedirs(terraform_dir, exist_ok=True)

            # Check if terraform files already exist
            main_tf_exists = os.path.exists(os.path.join(terraform_dir, 'main.tf'))
            state_exists = os.path.exists(os.path.join(terraform_dir, 'terraform.tfstate'))

            if main_tf_exists and not force_regenerate:
                # Files exist - prompt user for action
                state_note = ""
                if state_exists:
                    state_note = (
                        "\n\nNote: Terraform state file exists, indicating resources may "
                        "have been deployed. Regenerating files and rerunning 'terraform apply' "
                        "will update existing resources to match the new configuration."
                    )

                reply = QMessageBox.question(
                    self,
                    "Terraform Configuration Exists",
                    f"Terraform configuration already exists for this customer.\n\n"
                    f"Directory: {terraform_dir}\n\n"
                    "Choose an action:\n\n"
                    "• YES - Regenerate files (overwrites any manual edits)\n"
                    "• NO - Keep existing files (use current configuration)"
                    f"{state_note}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply != QMessageBox.StandardButton.Yes:
                    # User chose to keep existing files
                    self._log_activity("Using existing Terraform configuration")
                    self._terraform_output_dir = output_base
                    self._on_terraform_ready()
                    return

            # Generate firewalls list from locations
            # Each datacenter with service_connection needs a firewall
            # Each branch (remote_network) needs a firewall
            firewalls = []
            for dc in datacenters:
                if dc.get('connection_type') == 'service_connection':
                    firewalls.append({
                        'name': f"fw-{dc['name'].lower().replace(' ', '-')}",
                        'type': 'service_connection',
                        'location_name': dc['name'],
                        'region': dc.get('region', azure_region),
                    })

            for branch in locations.get('branches', []):
                firewalls.append({
                    'name': f"fw-{branch['name'].lower().replace(' ', '-')}",
                    'type': 'remote_network',
                    'location_name': branch['name'],
                    'region': branch.get('region', azure_region),
                })

            # Generate terraform.tfvars.json directly (simpler approach without full CloudConfig)
            tfvars = {
                '_metadata': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'generator': 'pov_workflow',
                    'customer': customer_name,
                },
                'customer_name': customer_name,
                'location': azure_region,
                'subscription_id': subscription_id,
                'tenant_id': tenant_id,
                'admin_username': admin_username,
                'admin_password': admin_password,
                'source_ips': [ip.strip() for ip in source_ips.split(',') if ip.strip()] if source_ips else [],
                'allow_ssh': cloud_security.get('allow_ssh', True),
                'allow_https': cloud_security.get('allow_https', True),
                'datacenters': datacenters,
                'branches': locations.get('branches', []),
                'firewalls': firewalls,
                'trust_devices': self.cloud_resource_configs.get('trust_devices', {}).get('devices', []),
            }

            # Write tfvars
            import json
            tfvars_path = os.path.join(terraform_dir, 'terraform.tfvars.json')
            with open(tfvars_path, 'w') as f:
                json.dump(tfvars, f, indent=2)

            # Generate main.tf with basic Azure resources
            main_tf_content = self._generate_main_tf(tfvars)
            with open(os.path.join(terraform_dir, 'main.tf'), 'w') as f:
                f.write(main_tf_content)

            # Generate cloud-init scripts for ServerVMs with services
            services_config = self.cloud_resource_configs.get('services', {})
            svc_domain = services_config.get('domain', '')
            if svc_domain:
                from gui.workflows.pov_services import CloudInitBuilder
                trust_devs = tfvars.get('trust_devices', [])
                customer_name_raw = tfvars.get('customer_name', 'POV')
                server_ip_counter = 10
                for dev in trust_devs:
                    if dev.get('device_type') == 'ServerVM' and dev.get('subtype') == 'Linux':
                        dev_file_name = dev.get('name', 'vm').lower().replace(' ', '-').replace('_', '-')
                        server_ip = f"10.100.2.{server_ip_counter}"
                        server_ip_counter += 1
                        builder = CloudInitBuilder(
                            domain=svc_domain,
                            customer_name=customer_name_raw,
                            server_ip=server_ip,
                            pki_options=services_config.get('pki', {}),
                            trust_devices=trust_devs,
                        )
                        cloud_init_script = builder.build_cloud_init()
                        cloud_init_path = os.path.join(terraform_dir, f'cloud-init-{dev_file_name}.sh')
                        with open(cloud_init_path, 'w') as f:
                            f.write(cloud_init_script)
                        self._log_activity(f"Generated cloud-init script: cloud-init-{dev_file_name}.sh")

            # Generate variables.tf
            variables_tf_content = self._generate_variables_tf()
            with open(os.path.join(terraform_dir, 'variables.tf'), 'w') as f:
                f.write(variables_tf_content)

            # Generate provider.tf
            provider_tf_content = self._generate_provider_tf(subscription_id, tenant_id)
            with open(os.path.join(terraform_dir, 'provider.tf'), 'w') as f:
                f.write(provider_tf_content)

            # Generate outputs.tf
            outputs_tf_content = self._generate_outputs_tf(tfvars)
            with open(os.path.join(terraform_dir, 'outputs.tf'), 'w') as f:
                f.write(outputs_tf_content)

            # Set the terraform output directory for review
            self._terraform_output_dir = output_base

            self._log_activity(f"Terraform configuration generated: {terraform_dir}")
            self._on_terraform_ready()

        except Exception as e:
            self._log_activity(f"Terraform generation failed: {e}", "error")
            self.terraform_gen_status.setText(f"✗ Generation failed: {str(e)}")
            self.terraform_gen_status.setStyleSheet(
                "color: #C62828; padding: 10px; background-color: #FFEBEE; "
                "border-radius: 5px;"
            )
            import traceback
            logger.error(f"Terraform generation error: {traceback.format_exc()}")

    def _generate_md5_crypt_hash(self, password: str, salt: str = None) -> str:
        """
        Generate MD5 crypt hash for PAN-OS bootstrap.

        PAN-OS uses the MD5-crypt format: $1$<salt>$<hash>
        This implements the MD5-crypt algorithm compatible with PAN-OS phash.
        """
        if salt is None:
            # Generate 8-character salt from alphanumeric characters
            import string
            salt_chars = string.ascii_letters + string.digits + './'
            salt = ''.join(secrets.choice(salt_chars) for _ in range(8))

        # MD5-crypt algorithm implementation
        def md5_crypt(password: str, salt: str) -> str:
            # Ensure salt is max 8 chars
            salt = salt[:8]

            # Initial hash: password + magic + salt + password
            ctx = hashlib.md5()
            ctx.update(password.encode())
            ctx.update(b'$1$')
            ctx.update(salt.encode())

            # Alternate hash: just password + salt + password
            ctx_alt = hashlib.md5()
            ctx_alt.update(password.encode())
            ctx_alt.update(salt.encode())
            ctx_alt.update(password.encode())
            alt_result = ctx_alt.digest()

            # Add alternating hash to main hash
            pw_len = len(password)
            i = pw_len
            while i > 0:
                ctx.update(alt_result[:min(i, 16)])
                i -= 16

            # Add bits from password length
            i = pw_len
            while i:
                if i & 1:
                    ctx.update(b'\x00')
                else:
                    ctx.update(password[0:1].encode())
                i >>= 1

            result = ctx.digest()

            # 1000 rounds of MD5
            for i in range(1000):
                ctx = hashlib.md5()
                if i & 1:
                    ctx.update(password.encode())
                else:
                    ctx.update(result)
                if i % 3:
                    ctx.update(salt.encode())
                if i % 7:
                    ctx.update(password.encode())
                if i & 1:
                    ctx.update(result)
                else:
                    ctx.update(password.encode())
                result = ctx.digest()

            # Convert to base64-like encoding
            itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

            def to64(v, n):
                ret = ''
                while n > 0:
                    ret += itoa64[v & 0x3f]
                    v >>= 6
                    n -= 1
                return ret

            final = ''
            final += to64((result[0] << 16) | (result[6] << 8) | result[12], 4)
            final += to64((result[1] << 16) | (result[7] << 8) | result[13], 4)
            final += to64((result[2] << 16) | (result[8] << 8) | result[14], 4)
            final += to64((result[3] << 16) | (result[9] << 8) | result[15], 4)
            final += to64((result[4] << 16) | (result[10] << 8) | result[5], 4)
            final += to64(result[11], 2)

            return f'$1${salt}${final}'

        return md5_crypt(password, salt)

    def _generate_main_tf(self, tfvars: dict) -> str:
        """Generate main.tf content for POV deployment."""
        customer = tfvars.get('customer_name', 'pov')
        location = tfvars.get('location', 'eastus')

        content = f'''# POV Deployment - {customer}
# Generated by PA Config Lab POV Builder

# Resource Group
resource "azurerm_resource_group" "pov" {{
  name     = "{customer}-{location}-pov-rg"
  location = var.location

  tags = {{
    environment = "pov"
    customer    = "{customer}"
    managed_by  = "pa_config_lab"
  }}
}}

# Virtual Network
resource "azurerm_virtual_network" "pov" {{
  name                = "{customer}-{location}-vnet"
  address_space       = ["10.100.0.0/16"]
  location            = azurerm_resource_group.pov.location
  resource_group_name = azurerm_resource_group.pov.name

  tags = azurerm_resource_group.pov.tags
}}

# Management Subnet
resource "azurerm_subnet" "management" {{
  name                 = "management"
  resource_group_name  = azurerm_resource_group.pov.name
  virtual_network_name = azurerm_virtual_network.pov.name
  address_prefixes     = ["10.100.0.0/24"]

  # Service endpoint required for storage account network rules
  service_endpoints    = ["Microsoft.Storage"]
}}

# Untrust Subnet
resource "azurerm_subnet" "untrust" {{
  name                 = "untrust"
  resource_group_name  = azurerm_resource_group.pov.name
  virtual_network_name = azurerm_virtual_network.pov.name
  address_prefixes     = ["10.100.1.0/24"]
}}

# Trust Subnet
resource "azurerm_subnet" "trust" {{
  name                 = "trust"
  resource_group_name  = azurerm_resource_group.pov.name
  virtual_network_name = azurerm_virtual_network.pov.name
  address_prefixes     = ["10.100.2.0/24"]
}}

# Network Security Group for Management
resource "azurerm_network_security_group" "management" {{
  name                = "{customer}-{location}-mgmt-nsg"
  location            = azurerm_resource_group.pov.location
  resource_group_name = azurerm_resource_group.pov.name

  tags = azurerm_resource_group.pov.tags
}}
'''

        # Add NSG rules based on security settings
        # Note: source_address_prefix (singular) is used for "*", source_address_prefixes (plural) for specific IPs
        source_ips = tfvars.get('source_ips', [])
        if source_ips:
            quoted_ips = ', '.join(f'"{ip}"' for ip in source_ips)
            source_line = f'source_address_prefixes     = [{quoted_ips}]'
        else:
            source_line = 'source_address_prefix       = "*"'

        if tfvars.get('allow_https', True):
            content += f'''
resource "azurerm_network_security_rule" "allow_https" {{
  name                        = "Allow-HTTPS"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  {source_line}
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.pov.name
  network_security_group_name = azurerm_network_security_group.management.name
}}
'''

        if tfvars.get('allow_ssh', True):
            content += f'''
resource "azurerm_network_security_rule" "allow_ssh" {{
  name                        = "Allow-SSH"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  {source_line}
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.pov.name
  network_security_group_name = azurerm_network_security_group.management.name
}}
'''

        # Add subnet NSG association
        content += '''
resource "azurerm_subnet_network_security_group_association" "management" {
  subnet_id                 = azurerm_subnet.management.id
  network_security_group_id = azurerm_network_security_group.management.id
}
'''

        # Add firewalls (VM-Series)
        firewalls = tfvars.get('firewalls', [])

        # Add bootstrap storage and marketplace agreement for VM-Series
        if firewalls:
            # Storage account for bootstrap (name must be globally unique, lowercase, no special chars, max 24 chars)
            # Format: {customer}{location}boot (truncated to fit)
            storage_base = f"{customer}{location}".lower().replace('-', '').replace('_', '')[:19]
            storage_name = f"{storage_base}boot"

            # Generate password hash in Python (works cross-platform)
            admin_password = tfvars.get('admin_password', 'PaloAlto123!')
            admin_username = tfvars.get('admin_username', f'{customer}admin')
            password_hash = self._generate_md5_crypt_hash(admin_password)

            content += f'''
# =============================================================================
# VM-Series Bootstrap Configuration
# =============================================================================

# Get current public IP for storage account access
# This allows Terraform to access the storage account while keeping network rules restrictive
data "http" "my_ip" {{
  url = "https://api.ipify.org?format=text"
}}

# Storage account for VM-Series bootstrap files
# Network rules: Deny by default, allow current IP and Azure services
resource "azurerm_storage_account" "bootstrap" {{
  name                     = "{storage_name}"
  resource_group_name      = azurerm_resource_group.pov.name
  location                 = azurerm_resource_group.pov.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  public_network_access_enabled   = true
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = true

  # Network rules satisfy Azure policy while allowing Terraform access
  network_rules {{
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
    ip_rules                   = [data.http.my_ip.response_body]
    virtual_network_subnet_ids = [azurerm_subnet.management.id]
  }}

  tags = azurerm_resource_group.pov.tags

  depends_on = [azurerm_subnet.management]
}}

# Bootstrap container
resource "azurerm_storage_container" "bootstrap" {{
  name                  = "bootstrap"
  storage_account_name  = azurerm_storage_account.bootstrap.name
  container_access_type = "private"
}}

# init-cfg.txt - Basic bootstrap configuration
resource "azurerm_storage_blob" "init_cfg" {{
  name                   = "config/init-cfg.txt"
  storage_account_name   = azurerm_storage_account.bootstrap.name
  storage_container_name = azurerm_storage_container.bootstrap.name
  type                   = "Block"
  source_content         = <<-EOF
type=dhcp-client
ip-address=
default-gateway=
netmask=
hostname={customer}-{location}-DC-fw
dns-primary=8.8.8.8
dns-secondary=8.8.4.4
op-command-modes=mgmt-interface-swap
dhcp-send-hostname=yes
dhcp-send-client-id=yes
dhcp-accept-server-hostname=yes
dhcp-accept-server-domain=yes
EOF

  depends_on = [azurerm_storage_container.bootstrap]
}}

# bootstrap.xml - PAN-OS configuration with admin user credentials
# Password hash generated by Python MD5-crypt implementation
resource "azurerm_storage_blob" "bootstrap_xml" {{
  name                   = "config/bootstrap.xml"
  storage_account_name   = azurerm_storage_account.bootstrap.name
  storage_container_name = azurerm_storage_container.bootstrap.name
  type                   = "Block"
  source_content         = <<-EOF
<?xml version="1.0"?>
<config version="10.2.0" urldb="paloaltonetworks">
  <mgt-config>
    <users>
      <entry name="{admin_username}">
        <phash>{password_hash}</phash>
        <permissions><role-based><superuser>yes</superuser></role-based></permissions>
      </entry>
    </users>
  </mgt-config>
  <shared>
    <admin-role>
      <entry name="superuser">
        <role>
          <device><superuser>yes</superuser></device>
        </role>
      </entry>
    </admin-role>
  </shared>
  <devices>
    <entry name="localhost.localdomain">
      <deviceconfig>
        <system>
          <type>
            <dhcp-client>
              <send-hostname>yes</send-hostname>
              <send-client-id>yes</send-client-id>
              <accept-dhcp-hostname>yes</accept-dhcp-hostname>
              <accept-dhcp-domain>yes</accept-dhcp-domain>
            </dhcp-client>
          </type>
          <dns-setting>
            <servers>
              <primary>8.8.8.8</primary>
              <secondary>8.8.4.4</secondary>
            </servers>
          </dns-setting>
        </system>
      </deviceconfig>
    </entry>
  </devices>
</config>
EOF

  depends_on = [azurerm_storage_container.bootstrap]
}}

# Accept Palo Alto Networks VM-Series Marketplace Agreement
# This is required before deploying VM-Series firewalls
resource "azurerm_marketplace_agreement" "paloalto" {{
  publisher = "paloaltonetworks"
  offer     = "vmseries-flex"
  plan      = "byol"
}}
'''
        for fw in firewalls:
            fw_name = fw.get('name', 'fw').lower().replace(' ', '-').replace('_', '-')
            fw_type = fw.get('type', 'service_connection')
            location_name = fw.get('location_name', 'Datacenter')

            # Determine site prefix: DC for datacenter/service_connection, BR for branch
            site_prefix = "DC" if fw_type == 'service_connection' else "BR"

            # Resource naming: {customer}-{location}-{site}-{fw_name}-{part}-{detail}
            resource_prefix = f"{customer}-{location}-{site_prefix}-{fw_name}"

            # DNS label must be lowercase, alphanumeric and hyphens only
            dns_label = f"{resource_prefix}-mgmt".lower()

            content += f'''
# Firewall: {fw_name} ({fw_type}) for {location_name}
# Public IP for management access
resource "azurerm_public_ip" "pip_{fw_name}" {{
  name                = "{resource_prefix}-IP-public"
  location            = azurerm_resource_group.pov.location
  resource_group_name = azurerm_resource_group.pov.name
  allocation_method   = "Static"
  sku                 = "Standard"

  # DNS label creates FQDN: {dns_label}.{{region}}.cloudapp.azure.com
  domain_name_label   = "{dns_label}"

  tags = azurerm_resource_group.pov.tags
}}

# Management NIC
resource "azurerm_network_interface" "nic_{fw_name}_mgmt" {{
  name                = "{resource_prefix}-nic-mgmt"
  location            = azurerm_resource_group.pov.location
  resource_group_name = azurerm_resource_group.pov.name

  ip_configuration {{
    name                          = "mgmt"
    subnet_id                     = azurerm_subnet.management.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pip_{fw_name}.id
  }}

  tags = azurerm_resource_group.pov.tags
}}

# Untrust NIC
resource "azurerm_network_interface" "nic_{fw_name}_untrust" {{
  name                 = "{resource_prefix}-nic-untrust"
  location             = azurerm_resource_group.pov.location
  resource_group_name  = azurerm_resource_group.pov.name
  enable_ip_forwarding = true

  ip_configuration {{
    name                          = "untrust"
    subnet_id                     = azurerm_subnet.untrust.id
    private_ip_address_allocation = "Dynamic"
  }}

  tags = azurerm_resource_group.pov.tags
}}

# Trust NIC
resource "azurerm_network_interface" "nic_{fw_name}_trust" {{
  name                 = "{resource_prefix}-nic-trust"
  location             = azurerm_resource_group.pov.location
  resource_group_name  = azurerm_resource_group.pov.name
  enable_ip_forwarding = true

  ip_configuration {{
    name                          = "trust"
    subnet_id                     = azurerm_subnet.trust.id
    private_ip_address_allocation = "Dynamic"
  }}

  tags = azurerm_resource_group.pov.tags
}}

# VM-Series Firewall
resource "azurerm_linux_virtual_machine" "fw_{fw_name}" {{
  name                            = "{resource_prefix}"
  resource_group_name             = azurerm_resource_group.pov.name
  location                        = azurerm_resource_group.pov.location
  size                            = "Standard_DS3_v2"
  admin_username                  = var.admin_username
  admin_password                  = var.admin_password
  disable_password_authentication = false

  # Bootstrap configuration - points to storage account with PAN-OS config
  custom_data = base64encode(join("", [
    "storage-account=", azurerm_storage_account.bootstrap.name,
    ",access-key=", azurerm_storage_account.bootstrap.primary_access_key,
    ",file-share=bootstrap",
    ",share-directory="
  ]))

  network_interface_ids = [
    azurerm_network_interface.nic_{fw_name}_mgmt.id,
    azurerm_network_interface.nic_{fw_name}_untrust.id,
    azurerm_network_interface.nic_{fw_name}_trust.id,
  ]

  os_disk {{
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
  }}

  plan {{
    name      = "byol"
    publisher = "paloaltonetworks"
    product   = "vmseries-flex"
  }}

  source_image_reference {{
    publisher = "paloaltonetworks"
    offer     = "vmseries-flex"
    sku       = "byol"
    version   = "latest"
  }}

  tags = azurerm_resource_group.pov.tags

  # Wait for marketplace agreement and bootstrap files
  depends_on = [
    azurerm_marketplace_agreement.paloalto,
    azurerm_storage_blob.init_cfg,
    azurerm_storage_blob.bootstrap_xml
  ]
}}
'''

        # Add ION devices for SD-WAN datacenters
        ion_devices = tfvars.get('ion_devices', [])
        if ion_devices:
            content += f'''
# Accept Palo Alto Networks CloudGenix ION Marketplace Agreement
resource "azurerm_marketplace_agreement" "ion" {{
  publisher = "paloaltonetworks"
  offer     = "cloudgenix_ion"
  plan      = "byol"
}}
'''
        for ion in ion_devices:
            ion_name = ion.get('name', 'ion').lower().replace(' ', '-').replace('_', '-')
            location_name = ion.get('location', 'Datacenter')
            resource_prefix = f"{customer}-{location}-DC-{ion_name}"
            dns_label = f"{resource_prefix}-wan".lower()

            content += f'''
# ION Device: {ion_name} (SD-WAN) for {location_name}
# WAN Public IP for SD-WAN tunnels
resource "azurerm_public_ip" "pip_{ion_name}" {{
  name                = "{resource_prefix}-IP-public"
  location            = azurerm_resource_group.pov.location
  resource_group_name = azurerm_resource_group.pov.name
  allocation_method   = "Static"
  sku                 = "Standard"
  domain_name_label   = "{dns_label}"
  tags = azurerm_resource_group.pov.tags
}}

# WAN NIC (untrust subnet, public IP, IP forwarding)
resource "azurerm_network_interface" "nic_{ion_name}_wan" {{
  name                 = "{resource_prefix}-nic-wan"
  location             = azurerm_resource_group.pov.location
  resource_group_name  = azurerm_resource_group.pov.name
  enable_ip_forwarding = true

  ip_configuration {{
    name                          = "wan"
    subnet_id                     = azurerm_subnet.untrust.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pip_{ion_name}.id
  }}

  tags = azurerm_resource_group.pov.tags
}}

# LAN NIC (trust subnet, IP forwarding)
resource "azurerm_network_interface" "nic_{ion_name}_lan" {{
  name                 = "{resource_prefix}-nic-lan"
  location             = azurerm_resource_group.pov.location
  resource_group_name  = azurerm_resource_group.pov.name
  enable_ip_forwarding = true

  ip_configuration {{
    name                          = "lan"
    subnet_id                     = azurerm_subnet.trust.id
    private_ip_address_allocation = "Dynamic"
  }}

  tags = azurerm_resource_group.pov.tags
}}

# SD-WAN ION Virtual Appliance
resource "azurerm_linux_virtual_machine" "ion_{ion_name}" {{
  name                            = "{resource_prefix}"
  resource_group_name             = azurerm_resource_group.pov.name
  location                        = azurerm_resource_group.pov.location
  size                            = "Standard_DS3_v2"
  admin_username                  = var.admin_username
  admin_password                  = var.admin_password
  disable_password_authentication = false

  network_interface_ids = [
    azurerm_network_interface.nic_{ion_name}_wan.id,
    azurerm_network_interface.nic_{ion_name}_lan.id,
  ]

  os_disk {{
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
  }}

  plan {{
    name      = "byol"
    publisher = "paloaltonetworks"
    product   = "cloudgenix_ion"
  }}

  source_image_reference {{
    publisher = "paloaltonetworks"
    offer     = "cloudgenix_ion"
    sku       = "byol"
    version   = "latest"
  }}

  tags = azurerm_resource_group.pov.tags

  depends_on = [azurerm_marketplace_agreement.ion]
}}
'''

        # Add trust devices (VMs)
        trust_devices = tfvars.get('trust_devices', [])
        services_config = tfvars.get('services', {})
        domain = services_config.get('domain', '')
        server_ip_counter = 10  # Static IPs start at 10.100.2.10

        for device in trust_devices:
            device_name = device.get('name', 'vm').lower().replace(' ', '-').replace('_', '-')
            device_type = device.get('device_type', 'ServerVM')
            subtype = device.get('subtype', 'Linux')

            # Skip ION devices here — they are generated above
            if device_type == 'ION':
                continue

            # Determine site prefix based on device location (default to DC for trust devices)
            device_site = device.get('site', 'datacenter')
            site_prefix = "DC" if device_site in ('datacenter', 'service_connection') else "BR"

            # Resource naming: {customer}-{location}-{site}-{device_name}
            vm_resource_prefix = f"{customer}-{location}-{site_prefix}-{device_name}"

            # Determine VM image
            if subtype == 'Windows':
                publisher = 'MicrosoftWindowsServer'
                offer = 'WindowsServer'
                sku = '2022-datacenter-g2'
            else:
                publisher = 'Canonical'
                offer = '0001-com-ubuntu-server-jammy'
                sku = '22_04-lts-gen2'

            # For ServerVMs with domain configured, use static IP and cloud-init
            is_server_with_services = (device_type == 'ServerVM' and subtype == 'Linux' and domain)
            if is_server_with_services:
                server_ip = f"10.100.2.{server_ip_counter}"
                server_ip_counter += 1
                ip_allocation = "Static"
                ip_address_line = f'\n    private_ip_address            = "{server_ip}"'
            else:
                ip_allocation = "Dynamic"
                ip_address_line = ""

            content += f'''
# {device.get('name', 'VM')} - {device_type}
resource "azurerm_network_interface" "nic_{device_name}" {{
  name                = "{vm_resource_prefix}-nic"
  location            = azurerm_resource_group.pov.location
  resource_group_name = azurerm_resource_group.pov.name

  ip_configuration {{
    name                          = "internal"
    subnet_id                     = azurerm_subnet.trust.id
    private_ip_address_allocation = "{ip_allocation}"{ip_address_line}
  }}

  tags = azurerm_resource_group.pov.tags
}}

resource "azurerm_linux_virtual_machine" "vm_{device_name}" {{
  name                            = "{vm_resource_prefix}"
  resource_group_name             = azurerm_resource_group.pov.name
  location                        = azurerm_resource_group.pov.location
  size                            = "Standard_B2s"
  admin_username                  = var.admin_username
  admin_password                  = var.admin_password
  disable_password_authentication = false
'''
            # Add cloud-init custom_data for ServerVMs with services
            if is_server_with_services:
                content += f'''
  custom_data = base64encode(file("${{path.module}}/cloud-init-{device_name}.sh"))
'''

            content += f'''
  network_interface_ids = [
    azurerm_network_interface.nic_{device_name}.id,
  ]

  os_disk {{
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }}

  source_image_reference {{
    publisher = "{publisher}"
    offer     = "{offer}"
    sku       = "{sku}"
    version   = "latest"
  }}

  tags = azurerm_resource_group.pov.tags
}}
'''

        return content

    def _generate_variables_tf(self) -> str:
        """Generate variables.tf content."""
        return '''# Variables for POV Deployment

variable "location" {
  description = "Azure region for deployment"
  type        = string
  default     = "eastus"
}

variable "admin_username" {
  description = "Admin username for VMs"
  type        = string
  default     = "povadmin"
}

variable "admin_password" {
  description = "Admin password for VMs"
  type        = string
  sensitive   = true
  default     = ""
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = ""
}

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
  default     = ""
}
'''

    def _generate_provider_tf(self, subscription_id: str, tenant_id: str) -> str:
        """Generate provider.tf content."""
        return f'''# Azure Provider Configuration

terraform {{
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }}
    http = {{
      source  = "hashicorp/http"
      version = "~> 3.0"
    }}
  }}
}}

provider "azurerm" {{
  features {{}}

  subscription_id = "{subscription_id}"
  tenant_id       = "{tenant_id}"
}}
'''

    def _generate_outputs_tf(self, tfvars: dict) -> str:
        """Generate outputs.tf content."""
        content = '''# Outputs for POV Deployment

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.pov.name
}

output "virtual_network_name" {
  description = "Name of the virtual network"
  value       = azurerm_virtual_network.pov.name
}

output "management_subnet_id" {
  description = "ID of the management subnet"
  value       = azurerm_subnet.management.id
}

output "trust_subnet_id" {
  description = "ID of the trust subnet"
  value       = azurerm_subnet.trust.id
}

output "untrust_subnet_id" {
  description = "ID of the untrust subnet"
  value       = azurerm_subnet.untrust.id
}
'''

        # Add outputs for firewalls
        firewalls = tfvars.get('firewalls', [])
        for fw in firewalls:
            fw_name = fw.get('name', 'fw').lower().replace(' ', '-').replace('_', '-')
            content += f'''
output "{fw_name}_public_ip" {{
  description = "Public IP of firewall {fw_name}"
  value       = azurerm_public_ip.pip_{fw_name}.ip_address
}}

output "{fw_name}_fqdn" {{
  description = "DNS name for firewall {fw_name} management"
  value       = azurerm_public_ip.pip_{fw_name}.fqdn
}}

output "{fw_name}_mgmt_private_ip" {{
  description = "Management private IP of firewall {fw_name}"
  value       = azurerm_network_interface.nic_{fw_name}_mgmt.private_ip_address
}}
'''

        # Add outputs for trust devices
        trust_devices = tfvars.get('trust_devices', [])
        for device in trust_devices:
            device_name = device.get('name', 'vm').lower().replace(' ', '-').replace('_', '-')
            content += f'''
output "{device_name}_private_ip" {{
  description = "Private IP of {device.get('name', 'VM')}"
  value       = azurerm_network_interface.nic_{device_name}.private_ip_address
}}
'''

        return content

    def _on_terraform_ready(self):
        """Handle terraform configuration ready."""
        self._log_activity("Terraform configuration ready for deployment")
        self.terraform_gen_status.setText("✓ Terraform configuration generated successfully")
        self.terraform_gen_status.setStyleSheet(
            "color: #2E7D32; padding: 10px; background-color: #E8F5E9; "
            "border-radius: 5px;"
        )

        # Enable terraform action buttons
        self.regen_terraform_btn.setEnabled(True)
        self.review_terraform_btn.setEnabled(True)
        self.edit_terraform_btn.setEnabled(True)
        self.deploy_terraform_btn.setEnabled(True)

        # Update deploy button text based on whether terraform has been deployed before
        self._update_deploy_button_state()

    def _update_deploy_button_state(self):
        """Update deploy button text based on terraform deployment state."""
        import os

        # Check if terraform state file exists (indicates previous deployment)
        is_deployed = False
        if hasattr(self, '_terraform_output_dir') and self._terraform_output_dir:
            terraform_dir = os.path.join(self._terraform_output_dir, "terraform")
            state_file = os.path.join(terraform_dir, "terraform.tfstate")
            is_deployed = os.path.exists(state_file)

        # Also check the runtime flag
        if hasattr(self, '_terraform_deployed') and self._terraform_deployed:
            is_deployed = True

        if is_deployed:
            self.deploy_terraform_btn.setText("🔄 Redeploy")
            self.deploy_terraform_btn.setToolTip(
                "Regenerate Terraform files from POV config and update Azure resources"
            )
        else:
            self.deploy_terraform_btn.setText("🚀 Deploy")
            self.deploy_terraform_btn.setToolTip(
                "Deploy resources to Azure using Terraform"
            )

    def _regenerate_terraform(self):
        """Regenerate Terraform files from current POV configuration."""
        # Check if we have Azure credentials
        if not hasattr(self, '_azure_subscription') or not self._azure_subscription:
            QMessageBox.warning(
                self,
                "Azure Not Authenticated",
                "Please authenticate with Azure first before regenerating Terraform files."
            )
            return

        # Confirm regeneration
        reply = QMessageBox.question(
            self,
            "Regenerate Terraform?",
            "This will regenerate all Terraform files from the current POV configuration.\n\n"
            "Any manual changes to the Terraform files will be overwritten.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self._log_activity("Regenerating Terraform configuration...")
        self.terraform_gen_status.setText("⏳ Regenerating Terraform configuration...")
        self.terraform_gen_status.setStyleSheet(
            "color: #1565C0; padding: 10px; background-color: #E3F2FD; "
            "border-radius: 5px;"
        )

        # Force regenerate
        self._generate_terraform_from_pov(force_regenerate=True)

    def _edit_terraform(self):
        """Open Terraform directory in system file manager for manual editing."""
        import os
        import subprocess
        import sys

        if not hasattr(self, '_terraform_output_dir') or not self._terraform_output_dir:
            QMessageBox.warning(
                self,
                "No Configuration",
                "Please generate Terraform configuration first."
            )
            return

        terraform_dir = os.path.join(self._terraform_output_dir, "terraform")
        if not os.path.exists(terraform_dir):
            QMessageBox.warning(
                self,
                "Configuration Not Found",
                f"Terraform directory not found:\n{terraform_dir}"
            )
            return

        self._log_activity(f"Opening Terraform directory: {terraform_dir}")

        try:
            # Open directory in system file manager
            if sys.platform == 'win32':
                os.startfile(terraform_dir)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', terraform_dir])
            else:
                # Linux - try xdg-open, then fall back to common file managers
                try:
                    subprocess.Popen(['xdg-open', terraform_dir])
                except FileNotFoundError:
                    # Try common file managers
                    for fm in ['nautilus', 'dolphin', 'nemo', 'thunar', 'pcmanfm']:
                        try:
                            subprocess.Popen([fm, terraform_dir])
                            break
                        except FileNotFoundError:
                            continue
                    else:
                        QMessageBox.information(
                            self,
                            "Directory Path",
                            f"Please open this directory manually:\n\n{terraform_dir}"
                        )

            self._log_activity("Terraform directory opened for editing")

        except Exception as e:
            logger.error(f"Failed to open terraform directory: {e}")
            QMessageBox.information(
                self,
                "Directory Path",
                f"Please open this directory manually:\n\n{terraform_dir}"
            )

    def _regenerate_terraform_files(self):
        """Regenerate Terraform configuration files (internal helper).

        Called by _deploy_terraform when redeploying to update files from POV config.
        """
        self._log_activity("Regenerating Terraform configuration...")
        self.terraform_gen_status.setText("⏳ Regenerating Terraform configuration...")
        self.terraform_gen_status.setStyleSheet(
            "color: #1565C0; padding: 10px; background-color: #E3F2FD; "
            "border-radius: 5px;"
        )

        # Regenerate (force=True to skip the existing file check)
        self._generate_terraform_from_pov(force_regenerate=True)

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
        self._deploy_error_shown = False  # Reset error flag for new deployment

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

        # Check if terraform state exists (previous deployment)
        import os
        terraform_dir = os.path.join(self._terraform_output_dir, "terraform")
        state_file = os.path.join(terraform_dir, "terraform.tfstate")
        is_update = os.path.exists(state_file)

        # Show custom styled confirmation dialog
        if not self._show_deploy_confirmation_dialog(is_update):
            return  # User cancelled

        # If redeploying, regenerate terraform files first
        if is_update:
            self._log_activity("Regenerating Terraform files for redeploy...")
            self._generate_terraform_from_pov(force_regenerate=True)

        # Validate Azure CLI authentication before proceeding
        if not self._ensure_azure_cli_auth():
            return  # Auth failed or user cancelled

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

        # Update UI - disable all terraform action buttons during deployment
        self.regen_terraform_btn.setEnabled(False)
        self.deploy_terraform_btn.setEnabled(False)
        self.review_terraform_btn.setEnabled(False)
        self.edit_terraform_btn.setEnabled(False)
        self.cloud_deploy_progress.setVisible(True)
        self.cloud_deploy_progress.setValue(0)

        # Show appropriate starting message
        if is_update:
            self.cloud_deploy_results.set_text("Starting Terraform update deployment...")
        else:
            self.cloud_deploy_results.set_text("Starting Terraform deployment...")

    def _get_terraform_credentials(self) -> dict:
        """Get credentials for Terraform deployment."""
        cloud_deployment = self.cloud_resource_configs.get('cloud_deployment', {})
        return {
            'admin_username': cloud_deployment.get('admin_username', ''),
            'admin_password': cloud_deployment.get('admin_password', ''),
        }

    def _ensure_azure_cli_auth(self) -> bool:
        """
        Validate Azure CLI token and re-authenticate if needed.

        Must be called from the main thread (before starting TerraformWorker)
        because az login requires browser interaction.

        Returns:
            True if CLI auth is valid and ready for Terraform.
            False if auth failed or user cancelled.
        """
        from terraform.azure_cli_auth import (
            check_azure_cli_installed,
            validate_cli_token,
            login_cli,
        )
        from PyQt6.QtWidgets import QApplication

        # Get tenant and subscription from saved state
        tenant_id = ''
        subscription_id = ''
        if hasattr(self, '_azure_subscription') and self._azure_subscription:
            subscription_id = self._azure_subscription.get('id', '')
            tenant_id = self._azure_subscription.get('tenant_id', '')
        else:
            subscription_id = self.deployment_config.get('azure_subscription_id', '')
            tenant_id = self.deployment_config.get('azure_tenant_id', '')

        # Check if Azure CLI is installed
        if not check_azure_cli_installed():
            QMessageBox.critical(
                self,
                "Azure CLI Not Found",
                "Azure CLI (az) is not installed or not in PATH.\n\n"
                "Terraform requires Azure CLI for authentication.\n\n"
                "Install from: https://aka.ms/installazurecli"
            )
            return False

        self._log_activity("Validating Azure CLI authentication...")

        # Quick check: is the current CLI token valid?
        is_valid, message = validate_cli_token(
            subscription_id=subscription_id,
            tenant_id=tenant_id,
        )

        if is_valid:
            self._log_activity("Azure CLI token is valid")
            return True

        # Token is expired or invalid -- prompt user to re-authenticate
        self._log_activity(f"Azure CLI token expired or invalid: {message}", "warning")

        reply = QMessageBox.question(
            self,
            "Azure CLI Authentication Required",
            "Your Azure CLI session has expired or is not logged in.\n\n"
            "Terraform needs a valid Azure CLI token to deploy resources.\n\n"
            "Sign in now? (A browser window will open)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply != QMessageBox.StandardButton.Yes:
            self._log_activity("User cancelled Azure CLI re-authentication")
            return False

        # Show progress indicator during login
        self._log_activity("Opening browser for Azure CLI sign-in...")
        self.cloud_deploy_results.set_text(
            "Waiting for Azure CLI sign-in...\n"
            "Please complete authentication in your browser."
        )
        QApplication.processEvents()

        # Perform az login (blocking -- opens browser)
        success, login_message = login_cli(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
        )

        # Bring window back to focus after browser auth
        self.activateWindow()
        self.raise_()

        if not success:
            self._log_activity(f"Azure CLI login failed: {login_message}", "error")
            tenant_hint = f"\n  az login --tenant {tenant_id}" if tenant_id else "\n  az login"
            QMessageBox.critical(
                self,
                "Azure CLI Login Failed",
                f"Failed to authenticate with Azure CLI:\n\n{login_message}\n\n"
                f"You can try manually running:{tenant_hint}"
            )
            self.cloud_deploy_results.set_text("")
            return False

        # Verify the new token works
        is_valid, message = validate_cli_token(
            subscription_id=subscription_id,
            tenant_id=tenant_id,
        )

        if is_valid:
            self._log_activity("Azure CLI re-authentication successful")
            self.cloud_deploy_results.set_text("")
            return True
        else:
            self._log_activity(f"Token still invalid after login: {message}", "error")
            QMessageBox.critical(
                self,
                "Authentication Error",
                f"Azure CLI login completed but token is still invalid:\n\n{message}\n\n"
                "Please verify the correct subscription and tenant are set."
            )
            self.cloud_deploy_results.set_text("")
            return False

    def _prime_azure_cli_auth(self):
        """
        Check Azure CLI auth status after SDK auth completes.

        Non-intrusive: only logs a warning if CLI token isn't valid.
        The mandatory gate is _ensure_azure_cli_auth() at deploy time.
        """
        from terraform.azure_cli_auth import check_azure_cli_installed, validate_cli_token

        if not check_azure_cli_installed():
            self._log_activity(
                "Azure CLI not installed - will need CLI auth at deploy time",
                "warning"
            )
            return

        tenant_id = self._azure_subscription.get('tenant_id', '')
        subscription_id = self._azure_subscription.get('id', '')

        is_valid, _ = validate_cli_token(
            subscription_id=subscription_id,
            tenant_id=tenant_id,
        )

        if not is_valid:
            self._log_activity(
                "Azure CLI token not valid - will prompt for CLI login at deploy time",
                "warning"
            )
        else:
            self._log_activity("Azure CLI token is valid for Terraform")

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
        # Re-enable all terraform action buttons
        self.regen_terraform_btn.setEnabled(True)
        self.deploy_terraform_btn.setEnabled(True)
        self.review_terraform_btn.setEnabled(True)
        self.edit_terraform_btn.setEnabled(True)
        self.cloud_deploy_progress.setVisible(False)

        # Update deploy button text (will show "Redeploy" after successful deployment)
        self._update_deploy_button_state()

        if success:
            self._log_activity("Infrastructure deployment completed successfully")
            # Store outputs for later use
            self._terraform_outputs = outputs
            # Mark Terraform as deployed for navigation validation
            self._terraform_deployed = True

            # Append summary to results (don't clear existing output)
            result_text = "\n" + "=" * 60 + "\n"
            result_text += "[OK] DEPLOYMENT SUCCESSFUL\n"
            result_text += "=" * 60 + "\n\n"
            if outputs:
                result_text += "Deployed Resources:\n"
                for key, value in outputs.items():
                    if value:
                        result_text += f"  - {key}: {value}\n"
                        self._log_activity(f"  Deployed: {key} = {value}")

            self.cloud_deploy_results.append_text(result_text)

            # Enable the Next button now that Terraform is deployed
            if hasattr(self, 'cloud_deploy_next_btn'):
                self.cloud_deploy_next_btn.setEnabled(True)
                self.cloud_deploy_next_btn.setToolTip("Proceed to deploy POV configuration")

            # Populate and show the credentials panel
            self._populate_deployment_credentials()
        else:
            self._log_activity(f"Infrastructure deployment failed: {message}", "error")
            # Append failure summary to results (don't clear existing output)
            result_text = "\n" + "=" * 60 + "\n"
            result_text += "[FAILED] DEPLOYMENT FAILED\n"
            result_text += "=" * 60 + "\n\n"
            result_text += f"Error: {message}\n"
            result_text += "\nReview the output above for details."
            self.cloud_deploy_results.append_text(result_text)

    def _on_deploy_error(self, error: str):
        """Handle deployment error - shows in results window."""
        self._log_activity(f"Deployment error: {error}", "error")
        # Only show the simple error, not duplicates
        if not hasattr(self, '_deploy_error_shown'):
            self._deploy_error_shown = False
        if not self._deploy_error_shown:
            self.cloud_deploy_results.append_text(f"\n[ERROR] {error}")
            self._deploy_error_shown = True

    def _on_deploy_log(self, message: str):
        """Handle deployment log message.

        All terraform output goes to activity log only (for debugging).
        The results window only shows the final success/failure from _on_deploy_complete.
        """
        # Log to activity log for debugging - raw terraform output stays hidden from user
        logger.debug(f"Deploy log: {message}")

    # ============================================================================
    # EVENT HANDLERS - DEPLOY POV CONFIG TAB (Tab 5)
    # ============================================================================

    def _update_deploy_config_button_style(self, state: str = "deploy"):
        """Update the deploy config button style based on state.

        Args:
            state: One of 'deploy', 'cancel', 'resume'
        """
        # Show/hide restart button based on whether there are completed phases
        has_completed_phases = bool(self._pov_deployment_phases_completed)
        if hasattr(self, 'restart_deploy_btn'):
            # Show restart button when resuming or when there are completed phases and not actively deploying
            self.restart_deploy_btn.setVisible(has_completed_phases and state != "cancel")

        if state == "cancel":
            self.deploy_config_btn.setText("Cancel Push")
            self.deploy_config_btn.setStyleSheet(
                "QPushButton { "
                "  background-color: #f44336; color: white; padding: 10px 20px; "
                "  font-weight: bold; border-radius: 5px; "
                "  border: 1px solid #d32f2f; border-bottom: 3px solid #c62828; "
                "}"
                "QPushButton:hover { background-color: #e53935; border-bottom: 3px solid #b71c1c; }"
                "QPushButton:pressed { background-color: #d32f2f; border-bottom: 1px solid #c62828; }"
            )
            self.deploy_config_btn.setToolTip("Cancel the current deployment")
        elif state == "resume":
            self.deploy_config_btn.setText("Resume Deployment")
            self.deploy_config_btn.setStyleSheet(
                "QPushButton { "
                "  background-color: #FF9800; color: white; padding: 10px 20px; "
                "  font-weight: bold; border-radius: 5px; "
                "  border: 1px solid #F57C00; border-bottom: 3px solid #E65100; "
                "}"
                "QPushButton:hover { background-color: #FB8C00; border-bottom: 3px solid #BF360C; }"
                "QPushButton:pressed { background-color: #F57C00; border-bottom: 1px solid #E65100; }"
            )
            self.deploy_config_btn.setToolTip("Resume deployment from where it left off")
        else:  # deploy
            self.deploy_config_btn.setText("Deploy Configuration")
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
            self.deploy_config_btn.setToolTip("Deploy POV configuration to SCM/Panorama")

    def _handle_deploy_config_click(self):
        """Handle the deploy config button click based on current state."""
        if self._pov_deployment_in_progress:
            # Cancel the current deployment
            self._cancel_pov_deployment()
        else:
            # Check if we need to resume
            if self._pov_deployment_phases_completed:
                # Has previously completed phases - ask to resume or restart
                reply = QMessageBox.question(
                    self,
                    "Resume Deployment?",
                    f"Previous deployment completed {len(self._pov_deployment_phases_completed)} phase(s).\n\n"
                    "Do you want to resume from where it left off?\n\n"
                    "Click 'Yes' to resume, 'No' to restart from the beginning.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                elif reply == QMessageBox.StandardButton.No:
                    # Reset completed phases
                    self._pov_deployment_phases_completed = []

            # Start deployment
            self._deploy_pov_config()

    def _restart_deployment(self):
        """Restart deployment from the beginning, clearing all completed phases."""
        if self._pov_deployment_in_progress:
            QMessageBox.warning(
                self,
                "Deployment In Progress",
                "Cannot restart while a deployment is in progress.\n\n"
                "Please cancel the current deployment first."
            )
            return

        # Confirm restart
        completed_count = len(self._pov_deployment_phases_completed)
        reply = QMessageBox.question(
            self,
            "Restart Deployment?",
            f"This will clear {completed_count} completed phase(s) and start fresh.\n\n"
            "Are you sure you want to restart from the beginning?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Clear completed phases
        self._pov_deployment_phases_completed = []
        self._log_activity("Cleared deployment progress - ready for fresh start")

        # Update button states
        self._update_deploy_config_button_style("deploy")
        self.restart_deploy_btn.setVisible(False)

        # Clear results panel
        self.pov_deploy_results.set_text("Deployment progress cleared. Click 'Deploy Configuration' to start fresh.")

        # Save state
        self.save_state()

    def _cancel_pov_deployment(self):
        """Cancel the current POV deployment."""
        self._log_activity("Cancelling POV deployment...")
        self._pov_deployment_cancelled = True

        # Update UI
        self._update_deploy_config_button_style("resume")
        self.deploy_config_btn.setEnabled(True)
        self.pov_deploy_results.append_text("\n\n[CANCELLED] Deployment cancelled by user.")
        self.pov_deploy_results.append_text(f"\nCompleted phases: {len(self._pov_deployment_phases_completed)}")

        # Save state so user can resume later
        self.save_state()

    def _on_deploy_tenant_changed(self, api_client, tenant_name: str):
        """Handle deploy tenant connection changes."""
        # Track the deploy tenant name for state persistence
        self._deploy_tenant_name = tenant_name if api_client else None

        # Enable action buttons when connected
        if api_client:
            self._log_activity(f"Connected to tenant: {tenant_name}")
            self.review_config_btn.setEnabled(True)
            self.deploy_config_btn.setEnabled(True)
            self.deploy_summary_label.setText(
                f"<b>Connected to:</b> {tenant_name}<br><br>"
                "Configuration from previous steps will be deployed to this tenant."
            )
            # Save state with deploy tenant
            self.save_state()
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
        """Review comprehensive POV configuration before deployment."""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
            QTabWidget, QWidget, QGroupBox, QDialogButtonBox
        )
        from PyQt6.QtGui import QPalette, QColor
        from PyQt6.QtCore import Qt

        deployment_config = self._gather_deployment_config()

        dialog = QDialog(self)
        dialog.setWindowTitle("📋 POV Configuration Review")
        dialog.setMinimumSize(700, 600)

        main_layout = QVBoxLayout(dialog)

        # Header
        header = QLabel("<h2>POV Configuration Summary</h2>")
        header.setStyleSheet("color: #1565C0; margin-bottom: 10px;")
        main_layout.addWidget(header)

        info = QLabel("Review all configuration that will be deployed to Prisma Access.")
        info.setStyleSheet("color: #666; margin-bottom: 15px;")
        main_layout.addWidget(info)

        # Tabbed content for different sections
        tabs = QTabWidget()

        # === TAB 1: Overview ===
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)

        # Customer Info
        customer_info = self.cloud_resource_configs.get('customer_info', {})
        customer_group = QGroupBox("Customer Information")
        customer_layout = QVBoxLayout(customer_group)
        customer_layout.addWidget(QLabel(f"<b>Customer:</b> {customer_info.get('customer_name', 'Not set')}"))
        customer_layout.addWidget(QLabel(f"<b>Industry:</b> {customer_info.get('industry', 'Not set')}"))
        customer_layout.addWidget(QLabel(f"<b>Management:</b> {self.management_type.upper()}"))
        if self.connection_name:
            customer_layout.addWidget(QLabel(f"<b>SCM Tenant:</b> {self.connection_name}"))
        overview_layout.addWidget(customer_group)

        # Infrastructure
        infra = self.cloud_resource_configs.get('infrastructure', {})
        infra_group = QGroupBox("Infrastructure Settings")
        infra_layout = QVBoxLayout(infra_group)
        network = infra.get('network', {})
        infra_layout.addWidget(QLabel(f"<b>Infrastructure Subnet:</b> {network.get('infrastructure_subnet', 'Default')}"))
        infra_layout.addWidget(QLabel(f"<b>BGP AS:</b> {network.get('infrastructure_bgp_as', 'Default')}"))
        dns = infra.get('dns', {})
        infra_layout.addWidget(QLabel(f"<b>DNS:</b> {dns.get('primary', '8.8.8.8')}, {dns.get('secondary', '8.8.4.4')}"))
        overview_layout.addWidget(infra_group)

        overview_layout.addStretch()
        tabs.addTab(overview_tab, "Overview")

        # === TAB 2: Locations & Devices ===
        locations_tab = QWidget()
        locations_layout = QVBoxLayout(locations_tab)

        locations = self.cloud_resource_configs.get('locations', {})

        # Datacenters
        datacenters = locations.get('datacenters', [])
        dc_group = QGroupBox(f"Datacenters ({len(datacenters)})")
        dc_layout = QVBoxLayout(dc_group)
        if datacenters:
            for dc in datacenters:
                conn_type = dc.get('connection_type', 'service_connection').replace('_', ' ').title()
                dc_layout.addWidget(QLabel(
                    f"• <b>{dc.get('name', 'Datacenter')}</b> - {dc.get('cloud', 'Azure')} "
                    f"{dc.get('region', '')} ({conn_type})"
                ))
        else:
            dc_layout.addWidget(QLabel("<i>No datacenters configured</i>"))
        locations_layout.addWidget(dc_group)

        # Branches
        branches = locations.get('branches', [])
        branch_group = QGroupBox(f"Branches ({len(branches)})")
        branch_layout = QVBoxLayout(branch_group)
        if branches:
            for branch in branches:
                branch_layout.addWidget(QLabel(
                    f"• <b>{branch.get('name', 'Branch')}</b> - {branch.get('region', 'Unknown region')}"
                ))
        else:
            branch_layout.addWidget(QLabel("<i>No branches configured</i>"))
        locations_layout.addWidget(branch_group)

        # Trust Devices
        trust_devices = self.cloud_resource_configs.get('trust_devices', {}).get('devices', [])
        devices_group = QGroupBox(f"Trust Zone Devices ({len(trust_devices)})")
        devices_layout = QVBoxLayout(devices_group)
        if trust_devices:
            for device in trust_devices:
                services = ', '.join(device.get('services', [])) or 'None'
                devices_layout.addWidget(QLabel(
                    f"• <b>{device.get('name', 'Device')}</b> - {device.get('device_type', 'VM')} "
                    f"({device.get('subtype', '')}) - Services: {services}"
                ))
        else:
            devices_layout.addWidget(QLabel("<i>No trust devices configured</i>"))
        locations_layout.addWidget(devices_group)

        locations_layout.addStretch()
        tabs.addTab(locations_tab, "Locations & Devices")

        # === TAB 3: Use Cases ===
        usecases_tab = QWidget()
        usecases_scroll = QScrollArea()
        usecases_scroll.setWidgetResizable(True)
        usecases_content = QWidget()
        usecases_layout = QVBoxLayout(usecases_content)

        use_cases = self.use_case_configs

        # Mobile Users
        mu = use_cases.get('mobile_users', {})
        mu_group = QGroupBox("Mobile Users")
        mu_layout = QVBoxLayout(mu_group)
        mu_enabled = "✅ Enabled" if mu.get('enabled') else "❌ Disabled"
        mu_layout.addWidget(QLabel(f"<b>Status:</b> {mu_enabled}"))
        if mu.get('enabled'):
            mu_layout.addWidget(QLabel(f"<b>Portal Name:</b> {mu.get('portal_name', 'Not set')}"))
            mu_layout.addWidget(QLabel(f"<b>VPN Mode:</b> {mu.get('vpn_mode', 'On Demand')}"))
            locs = ', '.join(mu.get('locations', [])) or 'Default'
            mu_layout.addWidget(QLabel(f"<b>Locations:</b> {locs}"))
        usecases_layout.addWidget(mu_group)

        # Private App Access
        pa = use_cases.get('private_app', {})
        pa_group = QGroupBox("Private App Access")
        pa_layout = QVBoxLayout(pa_group)
        pa_enabled = "✅ Enabled" if pa.get('enabled') else "❌ Disabled"
        pa_layout.addWidget(QLabel(f"<b>Status:</b> {pa_enabled}"))
        if pa.get('enabled'):
            connections = pa.get('connections', [])
            pa_layout.addWidget(QLabel(f"<b>Connections:</b> {len(connections)}"))
            for conn in connections[:5]:  # Show first 5
                pa_layout.addWidget(QLabel(f"  • {conn.get('name', 'Connection')} ({conn.get('connection_type', '')})"))
        usecases_layout.addWidget(pa_group)

        # Remote Branch
        rb = use_cases.get('remote_branch', {})
        rb_group = QGroupBox("Remote Branch")
        rb_layout = QVBoxLayout(rb_group)
        rb_enabled = "✅ Enabled" if rb.get('enabled') else "❌ Disabled"
        rb_layout.addWidget(QLabel(f"<b>Status:</b> {rb_enabled}"))
        if rb.get('enabled'):
            rb_layout.addWidget(QLabel(f"<b>BGP Routing:</b> {'Yes' if rb.get('bgp_routing') else 'No'}"))
            rb_layout.addWidget(QLabel(f"<b>SD-WAN Integration:</b> {'Yes' if rb.get('sdwan_integration') else 'No'}"))
        usecases_layout.addWidget(rb_group)

        # ADEM
        adem = use_cases.get('aiops_adem', {})
        adem_group = QGroupBox("AIOps / ADEM")
        adem_layout = QVBoxLayout(adem_group)
        adem_enabled = "✅ Enabled" if adem.get('enabled') else "❌ Disabled"
        adem_layout.addWidget(QLabel(f"<b>Status:</b> {adem_enabled}"))
        if adem.get('enabled'):
            tests = adem.get('tests', [])
            adem_layout.addWidget(QLabel(f"<b>Synthetic Tests:</b> {len(tests)}"))
        usecases_layout.addWidget(adem_group)

        # RBI
        rbi = use_cases.get('rbi', {})
        rbi_group = QGroupBox("Remote Browser Isolation")
        rbi_layout = QVBoxLayout(rbi_group)
        rbi_enabled = "✅ Enabled" if rbi.get('enabled') else "❌ Disabled"
        rbi_layout.addWidget(QLabel(f"<b>Status:</b> {rbi_enabled}"))
        usecases_layout.addWidget(rbi_group)

        usecases_layout.addStretch()
        usecases_scroll.setWidget(usecases_content)
        usecases_tab_layout = QVBoxLayout(usecases_tab)
        usecases_tab_layout.addWidget(usecases_scroll)
        tabs.addTab(usecases_tab, "Use Cases")

        # === TAB 4: Policy Objects ===
        policy_tab = QWidget()
        policy_layout = QVBoxLayout(policy_tab)

        custom_policies = use_cases.get('custom_policies', {})
        staged = custom_policies.get('staged_objects', {})

        # Address Objects
        addr_objs = staged.get('address_objects', [])
        addr_group = QGroupBox(f"Address Objects ({len(addr_objs)})")
        addr_layout = QVBoxLayout(addr_group)
        if addr_objs:
            for obj in addr_objs[:10]:  # Show first 10
                addr_layout.addWidget(QLabel(f"• <b>{obj.get('name')}</b>: {obj.get('ip_netmask', '')}"))
            if len(addr_objs) > 10:
                addr_layout.addWidget(QLabel(f"<i>... and {len(addr_objs) - 10} more</i>"))
        else:
            addr_layout.addWidget(QLabel("<i>No address objects staged</i>"))
        policy_layout.addWidget(addr_group)

        # Address Groups
        addr_groups = staged.get('address_groups', [])
        grp_group = QGroupBox(f"Address Groups ({len(addr_groups)})")
        grp_layout = QVBoxLayout(grp_group)
        if addr_groups:
            for grp in addr_groups:
                members = ', '.join(grp.get('static', [])[:3])
                if len(grp.get('static', [])) > 3:
                    members += '...'
                grp_layout.addWidget(QLabel(f"• <b>{grp.get('name')}</b>: {members}"))
        else:
            grp_layout.addWidget(QLabel("<i>No address groups staged</i>"))
        policy_layout.addWidget(grp_group)

        # Policies
        policies = custom_policies.get('policies', [])
        pol_group = QGroupBox(f"Security Policies ({len(policies)})")
        pol_layout = QVBoxLayout(pol_group)
        if policies:
            for pol in policies:
                pol_layout.addWidget(QLabel(f"• {pol}"))
        else:
            pol_layout.addWidget(QLabel("<i>No policies staged</i>"))
        policy_layout.addWidget(pol_group)

        policy_layout.addStretch()
        tabs.addTab(policy_tab, "Policy Objects")

        # === TAB 5: Cloud Deployment ===
        cloud_tab = QWidget()
        cloud_layout = QVBoxLayout(cloud_tab)

        # Terraform Status
        tf_group = QGroupBox("Terraform Deployment")
        tf_layout = QVBoxLayout(tf_group)
        if hasattr(self, '_terraform_deployed') and self._terraform_deployed:
            tf_layout.addWidget(QLabel("✅ <b>Status:</b> Deployed"))
            if hasattr(self, '_terraform_outputs') and self._terraform_outputs:
                tf_layout.addWidget(QLabel("<b>Outputs:</b>"))
                for key, value in self._terraform_outputs.items():
                    if value:
                        name = key.replace('_', ' ').title()
                        tf_layout.addWidget(QLabel(f"  • {name}: {value}"))
        else:
            tf_layout.addWidget(QLabel("⏳ <b>Status:</b> Not deployed"))
        cloud_layout.addWidget(tf_group)

        # Firewalls
        firewalls = deployment_config.get('firewalls', [])
        fw_group = QGroupBox(f"Firewalls ({len(firewalls)})")
        fw_layout = QVBoxLayout(fw_group)
        if firewalls:
            for fw in firewalls:
                fw_type = fw.get('type', 'unknown').replace('_', ' ').title()
                fw_layout.addWidget(QLabel(f"• <b>{fw.get('name')}</b> ({fw_type}) - {fw.get('location_name', '')}"))
        else:
            fw_layout.addWidget(QLabel("<i>No firewalls in deployment</i>"))
        cloud_layout.addWidget(fw_group)

        cloud_layout.addStretch()
        tabs.addTab(cloud_tab, "Cloud Deployment")

        main_layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        main_layout.addWidget(buttons)

        dialog.exec()

    def _deploy_pov_config(self):
        """Deploy POV configuration using multi-phase deployment.

        Deployment phases:
        1. Firewall base configuration (device settings, interfaces, zones, policy)
        2. Service Connection setup (IKE gateway, IPsec tunnel on FW; Service Connection in PA)
        3. Remote Network setup (IKE gateway, IPsec tunnel on FW; Remote Network in PA)
        4. Prisma Access configuration (Mobile Users, policies, objects)
        """
        self._log_activity("Starting multi-phase POV deployment...")
        deployment_config = self._gather_deployment_config()

        # Check if we have Terraform outputs with IPs or existing device credentials
        has_terraform = hasattr(self, '_terraform_outputs') and self._terraform_outputs
        existing_devices = self.cloud_resource_configs.get('existing_devices', [])
        has_existing = len(existing_devices) > 0

        # If no terraform outputs in memory, try to read from terraform.tfstate file
        if not has_terraform and hasattr(self, '_terraform_output_dir') and self._terraform_output_dir:
            self._log_activity("No terraform outputs in memory, checking state file...")
            self._terraform_outputs = self._read_terraform_outputs_from_state()
            has_terraform = bool(self._terraform_outputs)
            if has_terraform:
                self._log_activity(f"Loaded {len(self._terraform_outputs)} outputs from terraform.tfstate")

        if not has_terraform and not has_existing:
            self._log_activity("No deployed infrastructure found", "warning")
            QMessageBox.warning(
                self,
                "No Deployed Infrastructure",
                "Please deploy infrastructure using Terraform first, "
                "or select 'Yes, already deployed' in Step 1 and provide credentials."
            )
            return

        # Show comprehensive confirmation dialog
        if not self._show_pov_deploy_confirmation_dialog():
            self._log_activity("POV configuration deployment cancelled by user")
            return

        # Gather firewall credentials and IPs
        firewalls_to_configure = []
        locations = deployment_config.get('locations', {})
        datacenters = locations.get('datacenters', [])
        branches = locations.get('branches', [])

        if has_existing:
            # Use existing device credentials
            for device in existing_devices:
                if device.get('device_type') == 'Firewall' and device.get('scannable'):
                    firewalls_to_configure.append({
                        'name': device.get('name', 'firewall'),
                        'ip': device.get('mgmt_ip'),
                        'credentials': {
                            'username': device.get('username', 'admin'),
                            'password': device.get('password', ''),
                        },
                        'type': device.get('connection_type', 'service_connection'),
                        'location': device.get('location', ''),
                    })

        if has_terraform and not firewalls_to_configure:
            # Get IPs from Terraform outputs
            tf_outputs = self._terraform_outputs
            self._log_activity(f"Looking for firewall IPs in Terraform outputs: {list(tf_outputs.keys())}")

            # Helper function to find firewall IP in outputs
            def find_firewall_ip(outputs: dict) -> Optional[str]:
                """Search terraform outputs for a firewall PUBLIC management IP.

                Prioritizes public IPs over private IPs since we need to connect
                from outside Azure.
                """
                # First pass: Look for PUBLIC IP keys (preferred)
                for key, value in outputs.items():
                    if not value:
                        continue
                    key_lower = key.lower()
                    # Skip private IPs - we need public for external access
                    if 'private' in key_lower:
                        continue
                    # Look for firewall public IP
                    if ('firewall' in key_lower or 'fw' in key_lower) and 'public' in key_lower:
                        self._log_activity(f"Found public IP key: {key} = {value}")
                        return value

                # Second pass: Look for any public IP
                for key, value in outputs.items():
                    if not value:
                        continue
                    key_lower = key.lower()
                    if 'private' in key_lower:
                        continue
                    if 'public_ip' in key_lower or 'public_address' in key_lower:
                        self._log_activity(f"Found public IP key: {key} = {value}")
                        return value

                # Third pass: Generic management IP patterns (but not private)
                ip_patterns = [
                    'firewall_management_ip',
                    'fw_management_ip',
                    'management_ip',
                    'firewall_ip',
                    'fw_ip',
                ]
                for pattern in ip_patterns:
                    if pattern in outputs and outputs[pattern]:
                        # Check it's not a private IP pattern
                        if 'private' not in pattern.lower():
                            return outputs[pattern]

                # Last resort: Any firewall IP that's not explicitly private
                for key, value in outputs.items():
                    if not value:
                        continue
                    key_lower = key.lower()
                    if 'private' in key_lower:
                        continue
                    if ('firewall' in key_lower or 'fw' in key_lower) and \
                       ('ip' in key_lower or 'address' in key_lower):
                        return value

                return None

            # Get customer name for admin username (format: {customer}admin)
            customer_info = self.cloud_resource_configs.get('customer_info', {})
            customer_name_sanitized = customer_info.get(
                'customer_name_sanitized',
                self._sanitize_customer_name(customer_info.get('customer_name', 'pov'))
            )
            # Build admin username: {customer}admin (e.g., "acmeadmin")
            cloud_deployment = self.cloud_resource_configs.get('cloud_deployment', {})
            admin_username = cloud_deployment.get('admin_username', f"{customer_name_sanitized}admin")
            admin_password = cloud_deployment.get('admin_password', '')

            if not admin_password:
                self._log_activity("Warning: No admin password found in config - firewall login may fail", "warning")

            self._log_activity(f"Using firewall credentials: {admin_username}")

            # Map firewalls from deployment config to Terraform outputs
            deployment_firewalls = deployment_config.get('firewalls', [])

            if deployment_firewalls:
                for fw in deployment_firewalls:
                    fw_name = fw.get('name', '')
                    fw_ip = find_firewall_ip(tf_outputs)

                    if fw_ip:
                        firewalls_to_configure.append({
                            'name': fw_name,
                            'ip': fw_ip,
                            'credentials': {
                                'username': admin_username,
                                'password': admin_password,
                            },
                            'type': fw.get('type', 'service_connection'),
                            'location': fw.get('location', ''),
                        })
                        self._log_activity(f"Found firewall IP for {fw_name}: {fw_ip}")
            else:
                # No explicit firewalls in config, but terraform deployed
                # Try to use any firewall IP found in terraform outputs
                fw_ip = find_firewall_ip(tf_outputs)
                if fw_ip:
                    firewalls_to_configure.append({
                        'name': f"fw-{customer_name_sanitized}",
                        'ip': fw_ip,
                        'credentials': {
                            'username': admin_username,
                            'password': admin_password,
                        },
                        'type': 'service_connection',
                        'location': 'datacenter',
                    })
                    self._log_activity(f"Using terraform firewall IP: {fw_ip}")

        # Check if we found any firewalls to configure
        if not firewalls_to_configure:
            # Show more helpful error with terraform output keys
            tf_keys = list(getattr(self, '_terraform_outputs', {}).keys()) if has_terraform else []
            self._log_activity(f"No firewall IPs found. Terraform outputs: {tf_keys}", "warning")

            error_msg = "Could not find firewall management IP(s).\n\n"
            if has_terraform and tf_keys:
                error_msg += f"Terraform outputs available:\n  {', '.join(tf_keys)}\n\n"
                error_msg += "Expected output names like: firewall_management_ip, fw_ip, management_ip"
            else:
                error_msg += "No Terraform outputs available and no existing devices configured."

            QMessageBox.warning(
                self,
                "No Firewall IPs Found",
                error_msg
            )
            return

        # Store deployment context for the worker
        self._deployment_context = {
            'firewalls': firewalls_to_configure,
            'datacenters': datacenters,
            'branches': branches,
            'use_cases': self.use_case_configs,
            'custom_policies': self.use_case_configs.get('custom_policies', {}),
            'api_client': self.api_client,
            'connection_name': self.connection_name,
            'infrastructure': self.cloud_resource_configs.get('infrastructure', {}),
            'services': self.cloud_resource_configs.get('services', {}),
        }

        # Update UI for deployment
        self._pov_deployment_in_progress = True
        self._pov_deployment_cancelled = False
        self._update_deploy_config_button_style("cancel")
        self.deploy_config_btn.setEnabled(True)  # Enable for cancel
        self.review_config_btn.setEnabled(False)
        self.pov_deploy_progress.setVisible(True)
        self.pov_deploy_progress.setValue(0)

        # Start multi-phase deployment
        self._deploy_phases = self._build_deployment_phases()
        self._deploy_phase_results = {}

        # Determine starting phase (for resume support)
        if self._pov_deployment_phases_completed:
            # Find first phase not yet completed
            self._current_deploy_phase = len(self._pov_deployment_phases_completed)
            self._log_activity(f"Resuming deployment from phase {self._current_deploy_phase + 1}")
        else:
            self._current_deploy_phase = 0

        # Show initial status
        phases_text = "POV Deployment Phases:\n"
        for i, phase in enumerate(self._deploy_phases, 1):
            completed = i <= len(self._pov_deployment_phases_completed)
            status = "[DONE]" if completed else "[    ]"
            phases_text += f"  {status} {i}. {phase['name']}\n"

        if self._pov_deployment_phases_completed:
            phases_text += f"\nResuming from phase {self._current_deploy_phase + 1}..."
        else:
            phases_text += "\nStarting deployment..."
        self.pov_deploy_results.set_text(phases_text)

        # Begin deployment
        self._execute_next_deploy_phase()

    def _build_deployment_phases(self) -> list:
        """Build the list of deployment phases based on configuration.

        Phase order:
        1. Firewall base config
        2. All PA/SCM configuration (service connections PA, remote networks PA,
           mobile users, address objects, security policies, ADEM)
        3. ONE SCM commit to activate all config at once
        4. FW-side IPsec config (needs endpoint IPs from committed PA config)
        """
        phases = []
        ctx = self._deployment_context

        # Phase 1: Firewall base configuration (for each firewall)
        for fw in ctx.get('firewalls', []):
            phases.append({
                'name': f"Firewall Config: {fw['name']}",
                'type': 'firewall_base',
                'firewall': fw,
            })

        # Collect all SCM phases and FW-side phases separately
        scm_phases = []
        fw_side_phases = []
        folders_to_commit = set()

        # Service Connections (PA side goes to SCM, FW side goes after commit)
        # SD-WAN (ION) DCs get PA side config but skip FW side (ION auto-establishes tunnels)
        sc_datacenters = [dc for dc in ctx.get('datacenters', [])
                        if dc.get('connection_type') == 'service_connection']
        for dc in sc_datacenters:
            dc_style = dc.get('style', 'traditional')
            scm_phases.append({
                'name': f"Service Connection: {dc['name']} (PA side)",
                'type': 'service_connection_pa',
                'datacenter': dc,
            })
            folders_to_commit.add('Service Connections')
            # Only traditional (firewall) DCs need FW-side IPsec config
            if dc_style != 'sdwan':
                fw = self._find_firewall_for_location(dc.get('name'))
                if fw:
                    fw_side_phases.append({
                        'name': f"Service Connection: {dc['name']} (FW side)",
                        'type': 'service_connection_fw',
                        'datacenter': dc,
                        'firewall': fw,
                    })

        # Remote Networks (PA side goes to SCM, FW side goes after commit)
        for branch in ctx.get('branches', []):
            fw = self._find_firewall_for_location(branch.get('name'))
            scm_phases.append({
                'name': f"Remote Network: {branch['name']} (PA side)",
                'type': 'remote_network_pa',
                'branch': branch,
            })
            folders_to_commit.add('Remote Networks')
            if fw:
                fw_side_phases.append({
                    'name': f"Remote Network: {branch['name']} (FW side)",
                    'type': 'remote_network_fw',
                    'branch': branch,
                    'firewall': fw,
                })

        # Mobile Users Configuration (SCM config)
        use_cases = ctx.get('use_cases', {})
        if use_cases.get('mobile_users', {}).get('enabled'):
            scm_phases.append({
                'name': 'Mobile Users Configuration',
                'type': 'mobile_users',
            })
            folders_to_commit.add('Mobile Users')

        # Address Objects & Groups (SCM config)
        custom_policies = ctx.get('custom_policies', {})
        staged = custom_policies.get('staged_objects', {})
        if staged.get('address_objects') or staged.get('address_groups'):
            scm_phases.append({
                'name': 'Address Objects & Groups',
                'type': 'policy_objects',
            })
            folders_to_commit.add('Mobile Users')  # Objects typically go to Mobile Users folder

        # Security Policies (SCM config)
        if custom_policies.get('policies'):
            scm_phases.append({
                'name': 'Security Policies',
                'type': 'security_policies',
            })
            folders_to_commit.add('Mobile Users')

        # ADEM Configuration (SCM config)
        if use_cases.get('aiops_adem', {}).get('enabled'):
            scm_phases.append({
                'name': 'ADEM Configuration',
                'type': 'adem',
            })

        # Add all SCM config phases
        phases.extend(scm_phases)

        # Add ONE SCM commit phase to activate all config at once
        if scm_phases and folders_to_commit:
            phases.append({
                'name': 'SCM Commit (Activate All Configuration)',
                'type': 'scm_commit',
                'folders': list(folders_to_commit),
            })

        # Add FW-side phases AFTER commit (they need endpoint IPs)
        phases.extend(fw_side_phases)

        # Add Firewall Objects & Rules phase for each firewall
        # This pushes address objects and security rules to the firewall
        for fw in ctx.get('firewalls', []):
            phases.append({
                'name': f"Firewall Objects & Rules: {fw['name']}",
                'type': 'firewall_objects_rules',
                'firewall': fw,
            })

        # SSL Decryption CA phase — upload decryption CA to SCM
        services = ctx.get('services', {})
        if services.get('domain') and services.get('pki', {}).get('decryption_ca', False):
            phases.append({
                'name': 'SSL Decryption CA Upload',
                'type': 'ssl_decryption_ca',
                'domain': services['domain'],
            })

        return phases

    def _find_firewall_for_location(self, location_name: str) -> Optional[dict]:
        """Find the firewall associated with a location."""
        for fw in self._deployment_context.get('firewalls', []):
            # Match by location name or firewall name containing location
            if fw.get('location', '').lower() == location_name.lower():
                return fw
            if location_name.lower().replace(' ', '-') in fw.get('name', '').lower():
                return fw
        # Return first firewall as fallback
        firewalls = self._deployment_context.get('firewalls', [])
        return firewalls[0] if firewalls else None

    def _execute_next_deploy_phase(self):
        """Execute the next deployment phase."""
        # Check if cancelled
        if self._pov_deployment_cancelled:
            self._log_activity("Deployment cancelled, stopping execution")
            self._pov_deployment_in_progress = False
            return

        if self._current_deploy_phase >= len(self._deploy_phases):
            # All phases complete
            self._on_all_deploy_phases_complete()
            return

        phase = self._deploy_phases[self._current_deploy_phase]
        phase_num = self._current_deploy_phase + 1
        total_phases = len(self._deploy_phases)

        # Check if this phase was already marked as skipped due to dependency failure
        if phase['name'] in self._deploy_phase_results and self._deploy_phase_results[phase['name']].get('skipped'):
            skip_msg = self._deploy_phase_results[phase['name']].get('message', 'Dependency failed')
            self.pov_deploy_results.append_text(f"\n\n[PHASE {phase_num}/{total_phases}] {phase['name']}")
            self.pov_deploy_results.append_text(f"\n  [SKIPPED] {skip_msg}")
            self._current_deploy_phase += 1
            self._execute_next_deploy_phase()
            return

        self._log_activity(f"Starting phase {phase_num}/{total_phases}: {phase['name']}")
        self.pov_deploy_results.append_text(f"\n\n[PHASE {phase_num}/{total_phases}] {phase['name']}")

        # Calculate progress
        base_progress = int((self._current_deploy_phase / total_phases) * 100)
        self.pov_deploy_progress.setValue(base_progress)

        phase_type = phase['type']

        if phase_type == 'firewall_base':
            self._execute_firewall_base_phase(phase)
        elif phase_type == 'service_connection_fw':
            self._execute_service_connection_fw_phase(phase)
        elif phase_type == 'service_connection_pa':
            self._execute_service_connection_pa_phase(phase)
        elif phase_type == 'scm_commit':
            self._execute_scm_commit_phase(phase)
        elif phase_type == 'remote_network_fw':
            self._execute_remote_network_fw_phase(phase)
        elif phase_type == 'remote_network_pa':
            self._execute_remote_network_pa_phase(phase)
        elif phase_type == 'mobile_users':
            self._execute_mobile_users_phase(phase)
        elif phase_type == 'policy_objects':
            self._execute_policy_objects_phase(phase)
        elif phase_type == 'security_policies':
            self._execute_security_policies_phase(phase)
        elif phase_type == 'adem':
            self._execute_adem_phase(phase)
        elif phase_type == 'firewall_objects_rules':
            self._execute_firewall_objects_rules_phase(phase)
        elif phase_type == 'ssl_decryption_ca':
            self._execute_ssl_decryption_ca_phase(phase)
        else:
            self._log_activity(f"Unknown phase type: {phase_type}", "warning")
            self._advance_to_next_phase(True, "Skipped unknown phase type")

    def _execute_firewall_base_phase(self, phase: dict):
        """Execute firewall base configuration phase."""
        from gui.workers import DeviceConfigWorker

        fw = phase['firewall']
        infra = self._deployment_context.get('infrastructure', {})
        network = infra.get('network', {})

        fw_config = {
            'name': fw['name'],
            'device': {
                'hostname': fw['name'],
                'dns_primary': infra.get('dns', {}).get('primary', '8.8.8.8'),
                'dns_secondary': infra.get('dns', {}).get('secondary', '8.8.4.4'),
                'ntp_primary': 'time.google.com',
            },
            'interfaces': [
                {'name': 'ethernet1/1'},
                {'name': 'ethernet1/2'},
            ],
        }

        deployment = {
            'name': f"{fw['name']}-deployment",
            'virtual_network': {
                'subnets': [
                    {'name': 'trust', 'prefix': network.get('trust_subnet', '10.100.2.0/24')},
                    {'name': 'untrust', 'prefix': network.get('untrust_subnet', '10.100.1.0/24')},
                ],
            },
        }

        self._device_config_worker = DeviceConfigWorker(
            device_type='firewall',
            config=fw_config,
            deployment=deployment,
            management_ip=fw['ip'],
            credentials=fw['credentials'],
        )
        self._device_config_worker.progress.connect(self._on_phase_progress)
        self._device_config_worker.phase_changed.connect(lambda p: self._log_activity(f"  Sub-phase: {p}"))
        self._device_config_worker.finished.connect(self._on_phase_finished)
        self._device_config_worker.error.connect(self._on_phase_error)
        self._device_config_worker.log_message.connect(lambda m: self.pov_deploy_results.append_text(f"\n  {m}"))
        self._device_config_worker.start()

    def _execute_service_connection_fw_phase(self, phase: dict):
        """Configure IPsec tunnel on firewall for service connection."""
        fw = phase['firewall']
        dc = phase['datacenter']
        dc_name = dc['name']
        fw_name = fw['name']

        self.pov_deploy_results.append_text(f"\n  Configuring IPsec on {fw_name} for {dc_name}...")

        # Get PA endpoint details from PA side phase
        pa_endpoints = getattr(self, '_pa_endpoints', {})
        pa_info = pa_endpoints.get(dc_name, {})
        pa_endpoint_ip = pa_info.get('service_ip')

        if not pa_endpoint_ip:
            self.pov_deploy_results.append_text("\n  [SKIP] No PA endpoint IP available yet")
            self.pov_deploy_results.append_text("\n  Note: PA side must complete first to provide endpoint IPs")
            self._advance_to_next_phase(True, f"Skipped - waiting for PA endpoint")
            return

        self.pov_deploy_results.append_text(f"\n  - PA Endpoint: {pa_endpoint_ip}")

        # Get firewall connection info - note: firewall dict uses 'ip' not 'management_ip'
        fw_ip = fw.get('ip') or fw.get('management_ip')
        if not fw_ip:
            self.pov_deploy_results.append_text("\n  [ERROR] No firewall management IP")
            self._advance_to_next_phase(False, "No firewall management IP")
            return

        # Get credentials from firewall dict (set during deployment context build)
        fw_credentials = fw.get('credentials', {})
        admin_username = fw_credentials.get('username', '')
        admin_password = fw_credentials.get('password', '')

        # Fallback to cloud deployment config if not in firewall dict
        if not admin_username or not admin_password:
            cloud_deployment = self.cloud_resource_configs.get('cloud_deployment', {})
            customer_info = self.cloud_resource_configs.get('customer_info', {})
            customer_name = customer_info.get('customer_name_sanitized', 'pov')
            admin_username = admin_username or cloud_deployment.get('admin_username', f'{customer_name}admin')
            admin_password = admin_password or cloud_deployment.get('admin_password', '')

        try:
            from firewall.api_client import FirewallAPIClient

            self.pov_deploy_results.append_text(f"\n  Connecting to firewall at {fw_ip}...")
            client = FirewallAPIClient(
                hostname=fw_ip,
                username=admin_username,
                password=admin_password,
            )
            client.connect()

            # Configure IPsec tunnel to Prisma Access
            tunnel_name = f"SC-{dc_name.replace(' ', '-')}"
            self.pov_deploy_results.append_text(f"\n  Creating IPsec tunnel: {tunnel_name}")

            result = client.configure_ipsec_to_prisma_access(
                name=tunnel_name,
                pa_endpoint_ip=pa_endpoint_ip,
                pre_shared_key='PaloAltoPOV123!',  # Same PSK as PA side
                local_interface='ethernet1/1',  # Untrust interface
                tunnel_number=1,
                trust_zone='trust',
            )

            self.pov_deploy_results.append_text(f"\n  - IKE Crypto: {result['ike_crypto_profile']}")
            self.pov_deploy_results.append_text(f"\n  - IPsec Crypto: {result['ipsec_crypto_profile']}")
            self.pov_deploy_results.append_text(f"\n  - Tunnel: {result['tunnel_interface']}")
            self.pov_deploy_results.append_text(f"\n  - IKE GW: {result['ike_gateway']}")
            self.pov_deploy_results.append_text(f"\n  - IPsec: {result['ipsec_tunnel']}")

            # Commit the configuration
            self.pov_deploy_results.append_text("\n  Committing configuration...")
            commit_result = client.commit(
                description=f"IPsec tunnel for Service Connection {dc_name}",
                sync=True,
                timeout=300,
            )

            client.disconnect()

            if commit_result.success:
                self.pov_deploy_results.append_text("\n  [OK] IPsec tunnel configured")
                self._advance_to_next_phase(True, f"Firewall IPsec configured for {dc_name}")
            else:
                self.pov_deploy_results.append_text(f"\n  [ERROR] Commit: {commit_result.message}")
                self._advance_to_next_phase(False, f"Commit failed: {commit_result.message}")

        except Exception as e:
            self._log_activity(f"Failed to configure firewall IPsec: {e}", "error")
            self.pov_deploy_results.append_text(f"\n  [ERROR] {str(e)}")
            self._advance_to_next_phase(False, str(e))

    def _execute_firewall_objects_rules_phase(self, phase: dict):
        """Push address objects and security rules to the firewall.

        Creates:
        - Address objects for trust/untrust networks
        - Address objects for servers in datacenters/branches
        - Security rules allowing outbound access (DNS, web, etc.)
        """
        fw = phase['firewall']
        fw_name = fw['name']

        self.pov_deploy_results.append_text(f"\n  Configuring objects and rules on {fw_name}...")

        # Get firewall connection info - note: firewall dict uses 'ip' not 'management_ip'
        fw_ip = fw.get('ip') or fw.get('management_ip')
        if not fw_ip:
            # Try to get from terraform outputs as fallback
            tf_outputs = getattr(self, '_terraform_outputs', {})
            for key, value in tf_outputs.items():
                key_lower = key.lower()
                if ('firewall' in key_lower or 'fw' in key_lower) and 'public' in key_lower:
                    fw_ip = value
                    break
                if 'management_ip' in key_lower or 'mgmt_ip' in key_lower:
                    if 'private' not in key_lower:
                        fw_ip = value
                        break

        if not fw_ip:
            self.pov_deploy_results.append_text("\n  [SKIP] No firewall management IP available")
            self._advance_to_next_phase(True, "No firewall IP - skipping objects/rules")
            return

        self.pov_deploy_results.append_text(f"\n  - Management IP: {fw_ip}")

        # Get credentials from firewall dict (set during deployment context build)
        fw_credentials = fw.get('credentials', {})
        admin_username = fw_credentials.get('username', '')
        admin_password = fw_credentials.get('password', '')

        # Fallback to cloud deployment config if not in firewall dict
        if not admin_username or not admin_password:
            cloud_deployment = self.cloud_resource_configs.get('cloud_deployment', {})
            customer_info = self.cloud_resource_configs.get('customer_info', {})
            customer_name = customer_info.get('customer_name_sanitized', 'pov')
            admin_username = admin_username or cloud_deployment.get('admin_username', f'{customer_name}admin')
            admin_password = admin_password or cloud_deployment.get('admin_password', '')

        try:
            from firewall.api_client import FirewallAPIClient

            self.pov_deploy_results.append_text(f"\n  Connecting to firewall at {fw_ip}...")
            client = FirewallAPIClient(
                hostname=fw_ip,
                username=admin_username,
                password=admin_password,
            )
            client.connect()

            # Get network info from context
            infra = self._deployment_context.get('infrastructure', {})
            network = infra.get('network', {})
            trust_subnet = network.get('trust_subnet', '10.100.2.0/24')
            untrust_subnet = network.get('untrust_subnet', '10.100.1.0/24')

            # Create address objects
            self.pov_deploy_results.append_text("\n  Creating address objects...")

            # Trust and untrust network objects
            try:
                client.create_address_object(
                    name="trust-network",
                    value=trust_subnet,
                    description="Trust network CIDR"
                )
                self.pov_deploy_results.append_text(f"\n    - trust-network: {trust_subnet}")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    self.pov_deploy_results.append_text("\n    - trust-network [EXISTS]")
                else:
                    logger.warning(f"Failed to create trust network object: {e}")

            try:
                client.create_address_object(
                    name="untrust-network",
                    value=untrust_subnet,
                    description="Untrust network CIDR"
                )
                self.pov_deploy_results.append_text(f"\n    - untrust-network: {untrust_subnet}")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    self.pov_deploy_results.append_text("\n    - untrust-network [EXISTS]")
                else:
                    logger.warning(f"Failed to create untrust network object: {e}")

            # Create objects for datacenters/branches with servers
            for dc in self._deployment_context.get('datacenters', []):
                dc_name = dc['name'].replace(' ', '-').lower()
                dc_subnet = dc.get('subnet', dc.get('subnets', ['10.100.10.0/24'])[0] if dc.get('subnets') else '10.100.10.0/24')
                try:
                    client.create_address_object(
                        name=f"{dc_name}-servers",
                        value=dc_subnet,
                        description=f"Server network for {dc['name']}"
                    )
                    self.pov_deploy_results.append_text(f"\n    - {dc_name}-servers: {dc_subnet}")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        self.pov_deploy_results.append_text(f"\n    - {dc_name}-servers [EXISTS]")
                    else:
                        logger.warning(f"Failed to create DC server object: {e}")

            for branch in self._deployment_context.get('branches', []):
                branch_name = branch['name'].replace(' ', '-').lower()
                branch_subnet = branch.get('subnet', branch.get('subnets', ['10.100.20.0/24'])[0] if branch.get('subnets') else '10.100.20.0/24')
                try:
                    client.create_address_object(
                        name=f"{branch_name}-servers",
                        value=branch_subnet,
                        description=f"Server network for {branch['name']}"
                    )
                    self.pov_deploy_results.append_text(f"\n    - {branch_name}-servers: {branch_subnet}")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        self.pov_deploy_results.append_text(f"\n    - {branch_name}-servers [EXISTS]")
                    else:
                        logger.warning(f"Failed to create branch server object: {e}")

            # Create security rules
            self.pov_deploy_results.append_text("\n  Creating security rules...")

            # Rule 1: Allow DNS to servers
            try:
                client.create_security_rule(
                    name="allow-dns-outbound",
                    source_zone=['trust'],
                    destination_zone=['untrust', 'trust'],
                    source=['any'],
                    destination=['any'],
                    application=['dns'],
                    service=['application-default'],
                    action='allow',
                    description="Allow DNS queries outbound"
                )
                self.pov_deploy_results.append_text(f"\n    - allow-dns-outbound [OK]")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    self.pov_deploy_results.append_text(f"\n    - allow-dns-outbound [EXISTS]")
                else:
                    logger.warning(f"Failed to create DNS rule: {e}")

            # Rule 2: Allow web (HTTP/HTTPS) outbound
            try:
                client.create_security_rule(
                    name="allow-web-outbound",
                    source_zone=['trust'],
                    destination_zone=['untrust'],
                    source=['any'],
                    destination=['any'],
                    application=['web-browsing', 'ssl'],
                    service=['application-default'],
                    action='allow',
                    description="Allow web browsing outbound"
                )
                self.pov_deploy_results.append_text(f"\n    - allow-web-outbound [OK]")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    self.pov_deploy_results.append_text(f"\n    - allow-web-outbound [EXISTS]")
                else:
                    logger.warning(f"Failed to create web rule: {e}")

            # Rule 3: Allow inbound to servers (from Prisma Access/tunnel)
            try:
                client.create_security_rule(
                    name="allow-inbound-servers",
                    source_zone=['untrust'],
                    destination_zone=['trust'],
                    source=['any'],
                    destination=["trust-network"],
                    application=['any'],
                    service=['any'],
                    action='allow',
                    description="Allow inbound to servers from tunnel"
                )
                self.pov_deploy_results.append_text(f"\n    - allow-inbound-servers [OK]")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    self.pov_deploy_results.append_text(f"\n    - allow-inbound-servers [EXISTS]")
                else:
                    logger.warning(f"Failed to create inbound rule: {e}")

            # Commit the configuration
            self.pov_deploy_results.append_text("\n  Committing configuration...")
            commit_result = client.commit(
                description=f"POV objects and rules for {customer_name}",
                sync=True,
                timeout=300,
            )

            client.disconnect()

            if commit_result.success:
                self.pov_deploy_results.append_text("\n  [OK] Firewall objects and rules configured")
                self._advance_to_next_phase(True, f"Firewall objects/rules configured on {fw_name}")
            else:
                self.pov_deploy_results.append_text(f"\n  [ERROR] Commit: {commit_result.message}")
                self._advance_to_next_phase(False, f"Commit failed: {commit_result.message}")

        except Exception as e:
            self._log_activity(f"Failed to configure firewall objects/rules: {e}", "error")
            self.pov_deploy_results.append_text(f"\n  [ERROR] {str(e)}")
            self._advance_to_next_phase(False, str(e))

    def _execute_ssl_decryption_ca_phase(self, phase: dict):
        """Upload decryption CA certificate to SCM for SSL decryption."""
        domain = phase.get('domain', '')
        self.pov_deploy_results.append_text(f"\n  Generating decryption CA for {domain}...")

        try:
            import subprocess
            import tempfile
            import os

            customer_info = self.cloud_resource_configs.get('customer_info', {})
            customer_name = customer_info.get('customer_name', 'POV')

            # Generate decryption CA cert locally using OpenSSL
            with tempfile.TemporaryDirectory() as tmpdir:
                root_key = os.path.join(tmpdir, 'root-ca.key')
                root_crt = os.path.join(tmpdir, 'root-ca.crt')
                dec_key = os.path.join(tmpdir, 'decryption-ca.key')
                dec_csr = os.path.join(tmpdir, 'decryption-ca.csr')
                dec_crt = os.path.join(tmpdir, 'decryption-ca.crt')

                # Generate Root CA
                subprocess.run([
                    'openssl', 'genrsa', '-out', root_key, '4096'
                ], capture_output=True, check=True)

                subprocess.run([
                    'openssl', 'req', '-new', '-x509', '-days', '3650', '-sha256',
                    '-key', root_key, '-out', root_crt,
                    '-subj', f'/C=US/ST=California/L=Santa Clara/O={customer_name}/OU=Security/CN={customer_name} Root CA'
                ], capture_output=True, check=True)

                # Generate Decryption CA
                subprocess.run([
                    'openssl', 'genrsa', '-out', dec_key, '4096'
                ], capture_output=True, check=True)

                subprocess.run([
                    'openssl', 'req', '-new', '-sha256',
                    '-key', dec_key, '-out', dec_csr,
                    '-subj', f'/C=US/ST=California/L=Santa Clara/O={customer_name}/OU=Security/CN={customer_name} Decryption CA'
                ], capture_output=True, check=True)

                # Sign with Root CA
                ext_file = os.path.join(tmpdir, 'ext.cnf')
                with open(ext_file, 'w') as f:
                    f.write(
                        "basicConstraints = critical, CA:TRUE, pathlen:0\n"
                        "keyUsage = critical, keyCertSign, cRLSign\n"
                        "subjectKeyIdentifier = hash\n"
                        "authorityKeyIdentifier = keyid:always, issuer\n"
                    )

                subprocess.run([
                    'openssl', 'x509', '-req', '-days', '1825', '-sha256',
                    '-in', dec_csr, '-CA', root_crt, '-CAkey', root_key,
                    '-CAcreateserial', '-out', dec_crt, '-extfile', ext_file
                ], capture_output=True, check=True)

                # Read the generated certificate
                with open(dec_crt, 'r') as f:
                    cert_pem = f.read()

                self.pov_deploy_results.append_text("\n  - Decryption CA cert generated locally")

            # Upload to SCM
            api_client = self._get_deploy_api_client()
            if not api_client:
                self.pov_deploy_results.append_text("\n  [SKIP] No SCM API client available")
                self._advance_to_next_phase(True, "No API client - skipping SSL decryption CA upload")
                return

            cert_name = f"{customer_name}-Decryption-CA".replace(' ', '-')

            try:
                cert_payload = {
                    'name': cert_name,
                    'certificate': cert_pem,
                    'format': 'pem',
                    'folder': 'Shared',
                }
                api_client.post('/config/objects/v1/certificates', json=cert_payload)
                self.pov_deploy_results.append_text(f"\n  - Uploaded '{cert_name}' to SCM")
            except Exception as upload_err:
                if 'already exists' in str(upload_err).lower():
                    self.pov_deploy_results.append_text(f"\n  - '{cert_name}' already exists in SCM")
                else:
                    raise upload_err

            self.pov_deploy_results.append_text("\n  [OK] SSL Decryption CA configured")
            self._advance_to_next_phase(True, "SSL Decryption CA uploaded to SCM")

        except FileNotFoundError:
            self.pov_deploy_results.append_text("\n  [SKIP] OpenSSL not available on this system")
            self._advance_to_next_phase(True, "OpenSSL not found - skipping decryption CA")
        except Exception as e:
            self._log_activity(f"SSL Decryption CA phase failed: {e}", "error")
            self.pov_deploy_results.append_text(f"\n  [ERROR] {str(e)}")
            self._advance_to_next_phase(False, str(e))

    def _get_deploy_api_client(self):
        """Get the API client from the deploy tenant selector (Tab 5)."""
        if hasattr(self, 'deploy_tenant_selector'):
            api_client, tenant_name = self.deploy_tenant_selector.get_connection()
            return api_client
        return None

    def _execute_service_connection_pa_phase(self, phase: dict):
        """Create Service Connection in Prisma Access."""
        dc = phase['datacenter']
        sc_name = f"SC-{dc['name'].replace(' ', '-')}"
        tunnel_name = f"{sc_name}-tunnel"
        ike_gw_name = f"{sc_name}-ike-gw"
        region = dc.get('region', 'us-east-1')

        self.pov_deploy_results.append_text(f"\n  Creating Service Connection in Prisma Access...")
        self.pov_deploy_results.append_text(f"\n  - Name: {sc_name}")
        self.pov_deploy_results.append_text(f"\n  - Region: {region}")

        # Get deploy tenant API client (not source tenant)
        deploy_api_client = self._get_deploy_api_client()

        if deploy_api_client:
            try:
                # Get subnets from datacenter config or use default trust subnet CIDR
                subnets = dc.get('subnets', [])
                if not subnets:
                    # Try to get trust subnet prefix from terraform outputs
                    # Note: trust_subnet_id is the Azure resource ID, not the CIDR
                    # We need a CIDR like 10.100.2.0/24, not /subscriptions/.../subnets/trust
                    tf_outputs = getattr(self, '_terraform_outputs', {})
                    for key, value in tf_outputs.items():
                        # Look specifically for prefix/cidr outputs, not IDs
                        if ('trust' in key.lower() and 'prefix' in key.lower()) or \
                           ('trust' in key.lower() and 'cidr' in key.lower()):
                            if value and '/' in str(value) and not value.startswith('/subscriptions'):
                                subnets = [value]
                                break
                    # Default fallback - use standard POV trust subnet CIDR
                    if not subnets:
                        subnets = ['10.100.2.0/24']

                # Validate subnets are CIDR format, not Azure resource IDs
                valid_subnets = []
                for subnet in subnets:
                    if subnet and '/' in subnet and not subnet.startswith('/subscriptions'):
                        valid_subnets.append(subnet)
                    else:
                        logger.warning(f"Invalid subnet format (Azure resource ID?): {subnet}")

                if not valid_subnets:
                    valid_subnets = ['10.100.2.0/24']  # Fallback to default
                subnets = valid_subnets

                self.pov_deploy_results.append_text(f"\n  - Subnets: {', '.join(subnets)}")

                # Step 1: Create IKE Gateway
                self.pov_deploy_results.append_text(f"\n  Creating IKE Gateway: {ike_gw_name}...")
                ike_gateway_config = {
                    'name': ike_gw_name,
                    'authentication': {
                        'pre_shared_key': {
                            'key': 'PaloAltoPOV123!'  # Default POV PSK
                        }
                    },
                    'peer_address': {
                        'dynamic': {}  # Dynamic peer for service connections
                    },
                    'protocol': {
                        'ikev2': {
                            'dpd': {'enable': True}
                        }
                    },
                    'protocol_common': {
                        'nat_traversal': {'enable': True},
                        'fragmentation': {'enable': False}
                    }
                }
                try:
                    deploy_api_client.create_ike_gateway(ike_gateway_config, folder='Service Connections')
                    self.pov_deploy_results.append_text(" [OK]")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        self.pov_deploy_results.append_text(" [EXISTS]")
                    else:
                        raise

                # Step 2: Create IPsec Tunnel
                self.pov_deploy_results.append_text(f"\n  Creating IPsec Tunnel: {tunnel_name}...")
                ipsec_tunnel_config = {
                    'name': tunnel_name,
                    'auto_key': {
                        'ike_gateway': [{'name': ike_gw_name}],
                        'ipsec_crypto_profile': 'PaloAlto-Networks-IPSec-Crypto'  # Default profile
                    },
                    'tunnel_monitor': {'enable': False},
                    'anti_replay': True
                }
                try:
                    deploy_api_client.create_ipsec_tunnel(ipsec_tunnel_config, folder='Service Connections')
                    self.pov_deploy_results.append_text(" [OK]")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        self.pov_deploy_results.append_text(" [EXISTS]")
                    else:
                        raise

                # Step 3: Create Service Connection
                self.pov_deploy_results.append_text(f"\n  Creating Service Connection: {sc_name}...")
                sc_config = {
                    'name': sc_name,
                    'region': region,
                    'onboarding_type': 'classic',
                    'ipsec_tunnel': tunnel_name,
                    'subnets': subnets,
                }

                try:
                    result = deploy_api_client.create_service_connection(sc_config, folder='Service Connections')
                    self.pov_deploy_results.append_text(" [OK]")

                    # Store service endpoint details for FW side
                    # The API should return details including service_ip_address
                    if result and 'details' in result:
                        endpoint_ip = result['details'].get('service_ip_address')
                        endpoint_fqdn = result['details'].get('fqdn')
                        if endpoint_ip:
                            self.pov_deploy_results.append_text(f"\n  - PA Endpoint IP: {endpoint_ip}")
                        if endpoint_fqdn:
                            self.pov_deploy_results.append_text(f"\n  - PA Endpoint FQDN: {endpoint_fqdn}")

                        # Store for FW side phase
                        if not hasattr(self, '_pa_endpoints'):
                            self._pa_endpoints = {}
                        self._pa_endpoints[dc['name']] = {
                            'service_ip': endpoint_ip,
                            'fqdn': endpoint_fqdn,
                            'tunnel_name': tunnel_name,
                            'ike_gateway': ike_gw_name,
                        }
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        self.pov_deploy_results.append_text(" [EXISTS]")
                        # Try to get existing service connection details
                        try:
                            existing = deploy_api_client.get_all_service_connections()
                            for sc in existing:
                                if sc.get('name') == sc_name:
                                    details = sc.get('details', {})
                                    endpoint_ip = details.get('service_ip_address')
                                    if endpoint_ip:
                                        self.pov_deploy_results.append_text(f"\n  - PA Endpoint IP: {endpoint_ip}")
                                        if not hasattr(self, '_pa_endpoints'):
                                            self._pa_endpoints = {}
                                        self._pa_endpoints[dc['name']] = {
                                            'service_ip': endpoint_ip,
                                            'fqdn': details.get('fqdn'),
                                            'tunnel_name': tunnel_name,
                                            'ike_gateway': ike_gw_name,
                                        }
                                    break
                        except Exception:
                            pass
                    else:
                        raise

                self.pov_deploy_results.append_text("\n  [OK] Service Connection configured successfully")
                self._advance_to_next_phase(True, f"Service Connection created for {dc['name']}")

            except Exception as e:
                self._log_activity(f"Failed to create service connection: {e}", "error")
                self.pov_deploy_results.append_text(f"\n  [ERROR] {str(e)}")
                self._advance_to_next_phase(False, str(e))
        else:
            self.pov_deploy_results.append_text("\n  [SKIP] No deploy tenant connected - connect on Tab 5 first")
            self._advance_to_next_phase(False, "No deploy tenant connected")

    def _execute_scm_commit_phase(self, phase: dict):
        """Commit SCM candidate configuration to activate changes.

        This is required after PA-side configs to:
        1. Activate the service connections/remote networks
        2. Get the endpoint IPs assigned by Prisma Access
        """
        folders = phase.get('folders', ['Service Connections'])
        self.pov_deploy_results.append_text(f"\n  Committing configuration to SCM...")
        self.pov_deploy_results.append_text(f"\n  - Folders: {', '.join(folders)}")

        deploy_api_client = self._get_deploy_api_client()

        if deploy_api_client:
            try:
                # Push the candidate configuration
                self.pov_deploy_results.append_text("\n  Pushing candidate config...")
                push_result = deploy_api_client.push_candidate_config(
                    folders=folders,
                    description="POV Builder deployment"
                )

                # Get job ID from result
                job_id = push_result.get('id') or push_result.get('job_id')
                if not job_id:
                    # Check if it's nested in result
                    if isinstance(push_result.get('result'), dict):
                        job_id = push_result['result'].get('id')
                    elif isinstance(push_result.get('data'), list) and push_result['data']:
                        job_id = push_result['data'][0].get('id')

                if job_id:
                    self.pov_deploy_results.append_text(f"\n  - Job ID: {job_id}")
                    self.pov_deploy_results.append_text("\n  Waiting for commit to complete...")

                    # Wait for job completion
                    def progress_cb(percent, msg):
                        self.pov_deploy_results.append_text(f"\n    {percent}% - {msg}")

                    try:
                        job_result = deploy_api_client.wait_for_job_completion(
                            job_id,
                            timeout_seconds=300,
                            poll_interval=10,
                            progress_callback=progress_cb
                        )
                        # Check job result for actual success
                        job_data = job_result.get('data', [{}])[0] if job_result.get('data') else job_result
                        result_str = job_data.get('result_str', '')
                        if result_str and 'fail' in result_str.lower():
                            self.pov_deploy_results.append_text(f"\n  [ERROR] Job completed with failure: {result_str}")
                            self._advance_to_next_phase(False, f"SCM push failed: {result_str}")
                            return
                        self.pov_deploy_results.append_text("\n  [OK] Configuration committed successfully")
                    except RuntimeError as e:
                        # Job explicitly failed
                        self._log_activity(f"SCM push job failed: {e}", "error")
                        self.pov_deploy_results.append_text(f"\n  [ERROR] Push job failed: {e}")
                        self._advance_to_next_phase(False, f"SCM push failed: {e}")
                        return

                    # After commit, refresh service connection details to get endpoint IPs
                    endpoints_found = self._refresh_service_connection_endpoints(deploy_api_client)

                    # CRITICAL: If no endpoints found, fail the phase - FW side can't proceed without them
                    if not endpoints_found:
                        self.pov_deploy_results.append_text("\n  [ERROR] No service endpoint IPs retrieved")
                        self.pov_deploy_results.append_text("\n  FW-side configuration cannot proceed without endpoint IPs")
                        self.pov_deploy_results.append_text("\n  Check SCM > Service Connections for provisioning status")
                        self._advance_to_next_phase(False, "No endpoint IPs - FW config cannot proceed")
                        return

                else:
                    # No job ID - might mean changes were already committed or nothing to commit
                    self.pov_deploy_results.append_text("\n  [OK] No pending changes to commit (already active)")
                    # Still try to get endpoint IPs
                    endpoints_found = self._refresh_service_connection_endpoints(deploy_api_client)

                    # Even if already committed, we need endpoints for FW side
                    if not endpoints_found:
                        self.pov_deploy_results.append_text("\n  [ERROR] No service endpoint IPs found")
                        self.pov_deploy_results.append_text("\n  Service connections may not be provisioned yet")
                        self._advance_to_next_phase(False, "No endpoint IPs available")
                        return

                self._advance_to_next_phase(True, "SCM commit completed")

            except TimeoutError as e:
                self._log_activity(f"SCM commit timed out: {e}", "error")
                self.pov_deploy_results.append_text(f"\n  [ERROR] Commit timed out: {e}")
                self._advance_to_next_phase(False, str(e))
            except Exception as e:
                self._log_activity(f"SCM commit failed: {e}", "error")
                self.pov_deploy_results.append_text(f"\n  [ERROR] {str(e)}")
                self._advance_to_next_phase(False, str(e))
        else:
            self.pov_deploy_results.append_text("\n  [SKIP] No deploy tenant connected")
            self._advance_to_next_phase(False, "No deploy tenant connected")

    def _refresh_service_connection_endpoints(self, api_client) -> bool:
        """Refresh service connection details to get endpoint IPs after commit.

        Returns:
            True if at least one endpoint IP was found, False otherwise.
        """
        try:
            self.pov_deploy_results.append_text("\n  Retrieving endpoint IPs...")
            service_connections = api_client.get_all_service_connections()

            if not hasattr(self, '_pa_endpoints'):
                self._pa_endpoints = {}

            for sc in service_connections:
                sc_name = sc.get('name', '')
                # Try to match to a datacenter by name
                for dc in self._deployment_context.get('datacenters', []):
                    expected_sc_name = f"SC-{dc['name'].replace(' ', '-')}"
                    if sc_name == expected_sc_name:
                        # Get endpoint details
                        # Service connections have 'protocol' -> 'bgp' -> 'peer_ip_address'
                        # or 'details' -> 'service_ip_address' after commit
                        endpoint_ip = None

                        # Check various locations for the endpoint IP
                        if 'protocol' in sc and 'bgp' in sc['protocol']:
                            endpoint_ip = sc['protocol']['bgp'].get('peer_ip_address')

                        # Also check for service_ip in details
                        details = sc.get('details', {})
                        if not endpoint_ip and details:
                            endpoint_ip = details.get('service_ip_address')

                        # Check for fqdn_list which has the endpoint FQDNs
                        fqdn_list = sc.get('fqdn_list', [])
                        fqdn = fqdn_list[0] if fqdn_list else None

                        if endpoint_ip or fqdn:
                            self._pa_endpoints[dc['name']] = {
                                'service_ip': endpoint_ip,
                                'fqdn': fqdn,
                                'tunnel_name': f"{sc_name}-tunnel",
                                'ike_gateway': f"{sc_name}-ike-gw",
                            }
                            self.pov_deploy_results.append_text(
                                f"\n  - {dc['name']}: {endpoint_ip or fqdn}"
                            )
                        break

            if self._pa_endpoints:
                self.pov_deploy_results.append_text(f"\n  [OK] Retrieved {len(self._pa_endpoints)} endpoint(s)")
                return True
            else:
                self.pov_deploy_results.append_text("\n  [WARN] No endpoint IPs retrieved yet")
                self.pov_deploy_results.append_text("\n    Note: Endpoints may take time to provision")
                return False

        except Exception as e:
            self._log_activity(f"Failed to refresh endpoints: {e}", "warning")
            self.pov_deploy_results.append_text(f"\n  [WARN] Could not retrieve endpoints: {e}")
            return False

    def _execute_remote_network_fw_phase(self, phase: dict):
        """Configure IPsec tunnel on firewall for remote network."""
        fw = phase['firewall']
        branch = phase['branch']
        branch_name = branch['name']
        fw_name = fw['name']

        self.pov_deploy_results.append_text(f"\n  Configuring IPsec on {fw_name} for {branch_name}...")

        # Get PA endpoint details from PA side phase
        pa_endpoints = getattr(self, '_pa_endpoints', {})
        pa_info = pa_endpoints.get(branch_name, {})
        pa_endpoint_ip = pa_info.get('service_ip')

        if not pa_endpoint_ip:
            self.pov_deploy_results.append_text("\n  [SKIP] No PA endpoint IP available yet")
            self.pov_deploy_results.append_text("\n  Note: PA side must complete first to provide endpoint IPs")
            self._advance_to_next_phase(True, f"Skipped - waiting for PA endpoint")
            return

        self.pov_deploy_results.append_text(f"\n  - PA Endpoint: {pa_endpoint_ip}")

        # Get firewall connection info
        fw_ip = fw.get('management_ip')
        if not fw_ip:
            self.pov_deploy_results.append_text("\n  [ERROR] No firewall management IP")
            self._advance_to_next_phase(False, "No firewall management IP")
            return

        # Get credentials
        cloud_deployment = self.cloud_resource_configs.get('cloud_deployment', {})
        customer_info = self.cloud_resource_configs.get('customer_info', {})
        customer_name = customer_info.get('customer_name_sanitized', 'pov')
        admin_username = cloud_deployment.get('admin_username', f'{customer_name}admin')
        admin_password = cloud_deployment.get('admin_password', '')

        try:
            from firewall.api_client import FirewallAPIClient

            self.pov_deploy_results.append_text(f"\n  Connecting to firewall at {fw_ip}...")
            client = FirewallAPIClient(
                hostname=fw_ip,
                username=admin_username,
                password=admin_password,
            )
            client.connect()

            # Configure IPsec tunnel to Prisma Access for Remote Network
            tunnel_name = f"RN-{branch_name.replace(' ', '-')}"
            # Use different tunnel number than Service Connection
            tunnel_number = 2 + len([k for k in pa_endpoints.keys() if pa_endpoints[k].get('type') == 'remote_network'])

            self.pov_deploy_results.append_text(f"\n  Creating IPsec tunnel: {tunnel_name}")

            result = client.configure_ipsec_to_prisma_access(
                name=tunnel_name,
                pa_endpoint_ip=pa_endpoint_ip,
                pre_shared_key='PaloAltoPOV123!',  # Same PSK as PA side
                local_interface='ethernet1/1',  # Untrust interface
                tunnel_number=tunnel_number,
                trust_zone='trust',
            )

            self.pov_deploy_results.append_text(f"\n  - IKE Crypto: {result['ike_crypto_profile']}")
            self.pov_deploy_results.append_text(f"\n  - IPsec Crypto: {result['ipsec_crypto_profile']}")
            self.pov_deploy_results.append_text(f"\n  - Tunnel: {result['tunnel_interface']}")
            self.pov_deploy_results.append_text(f"\n  - IKE GW: {result['ike_gateway']}")
            self.pov_deploy_results.append_text(f"\n  - IPsec: {result['ipsec_tunnel']}")

            # Commit the configuration
            self.pov_deploy_results.append_text("\n  Committing configuration...")
            commit_result = client.commit(
                description=f"IPsec tunnel for Remote Network {branch_name}",
                sync=True,
                timeout=300,
            )

            client.disconnect()

            if commit_result.success:
                self.pov_deploy_results.append_text("\n  [OK] IPsec tunnel configured")
                self._advance_to_next_phase(True, f"Firewall IPsec configured for {branch_name}")
            else:
                self.pov_deploy_results.append_text(f"\n  [ERROR] Commit: {commit_result.message}")
                self._advance_to_next_phase(False, f"Commit failed: {commit_result.message}")

        except Exception as e:
            self._log_activity(f"Failed to configure firewall IPsec: {e}", "error")
            self.pov_deploy_results.append_text(f"\n  [ERROR] {str(e)}")
            self._advance_to_next_phase(False, str(e))

    def _execute_remote_network_pa_phase(self, phase: dict):
        """Create Remote Network in Prisma Access."""
        branch = phase['branch']
        rn_name = f"RN-{branch['name'].replace(' ', '-')}"
        tunnel_name = f"{rn_name}-tunnel"
        ike_gw_name = f"{rn_name}-ike-gw"
        region = branch.get('region', 'us-east-1')

        self.pov_deploy_results.append_text(f"\n  Creating Remote Network in Prisma Access...")
        self.pov_deploy_results.append_text(f"\n  - Name: {rn_name}")
        self.pov_deploy_results.append_text(f"\n  - Region: {region}")

        # Get deploy tenant API client (not source tenant)
        deploy_api_client = self._get_deploy_api_client()

        if deploy_api_client:
            try:
                # Get subnets from branch config
                subnets = branch.get('subnets', [])
                if not subnets:
                    # Default fallback for branch subnet
                    subnets = ['10.200.0.0/24']

                self.pov_deploy_results.append_text(f"\n  - Subnets: {', '.join(subnets)}")

                # Step 1: Create IKE Gateway for Remote Network
                self.pov_deploy_results.append_text(f"\n  Creating IKE Gateway: {ike_gw_name}...")
                ike_gateway_config = {
                    'name': ike_gw_name,
                    'authentication': {
                        'pre_shared_key': {
                            'key': 'PaloAltoPOV123!'  # Default POV PSK
                        }
                    },
                    'peer_address': {
                        'dynamic': {}  # Dynamic peer for remote networks
                    },
                    'protocol': {
                        'ikev2': {
                            'dpd': {'enable': True}
                        }
                    },
                    'protocol_common': {
                        'nat_traversal': {'enable': True},
                        'fragmentation': {'enable': False}
                    }
                }
                try:
                    deploy_api_client.create_ike_gateway(ike_gateway_config, folder='Remote Networks')
                    self.pov_deploy_results.append_text(" [OK]")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        self.pov_deploy_results.append_text(" [EXISTS]")
                    else:
                        raise

                # Step 2: Create IPsec Tunnel for Remote Network
                self.pov_deploy_results.append_text(f"\n  Creating IPsec Tunnel: {tunnel_name}...")
                ipsec_tunnel_config = {
                    'name': tunnel_name,
                    'auto_key': {
                        'ike_gateway': [{'name': ike_gw_name}],
                        'ipsec_crypto_profile': 'PaloAlto-Networks-IPSec-Crypto'  # Default profile
                    },
                    'tunnel_monitor': {'enable': False},
                    'anti_replay': True
                }
                try:
                    deploy_api_client.create_ipsec_tunnel(ipsec_tunnel_config, folder='Remote Networks')
                    self.pov_deploy_results.append_text(" [OK]")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        self.pov_deploy_results.append_text(" [EXISTS]")
                    else:
                        raise

                # Step 3: Create Remote Network
                self.pov_deploy_results.append_text(f"\n  Creating Remote Network: {rn_name}...")
                rn_config = {
                    'name': rn_name,
                    'region': region,
                    'license_type': 'FWAAS-AGGREGATE',
                    'ecmp_load_balancing': 'disable',
                    'ipsec_tunnel': tunnel_name,
                    'subnets': subnets,
                }

                # Add BGP configuration if enabled
                if branch.get('bgp_enabled', False):
                    peer_as = branch.get('bgp_peer_as', '65000')
                    rn_config['protocol'] = {
                        'bgp': {
                            'enable': True,
                            'peer_as': str(peer_as),
                        }
                    }

                try:
                    result = deploy_api_client.create_remote_network(rn_config, folder='Remote Networks')
                    self.pov_deploy_results.append_text(" [OK]")

                    # Store service endpoint details for FW side
                    if result and 'details' in result:
                        endpoint_ip = result['details'].get('service_ip_address')
                        endpoint_fqdn = result['details'].get('fqdn')
                        if endpoint_ip:
                            self.pov_deploy_results.append_text(f"\n  - PA Endpoint IP: {endpoint_ip}")
                        if endpoint_fqdn:
                            self.pov_deploy_results.append_text(f"\n  - PA Endpoint FQDN: {endpoint_fqdn}")

                        # Store for FW side phase
                        if not hasattr(self, '_pa_endpoints'):
                            self._pa_endpoints = {}
                        self._pa_endpoints[branch['name']] = {
                            'service_ip': endpoint_ip,
                            'fqdn': endpoint_fqdn,
                            'tunnel_name': tunnel_name,
                            'ike_gateway': ike_gw_name,
                            'type': 'remote_network',
                        }
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        self.pov_deploy_results.append_text(" [EXISTS]")
                        # Try to get existing remote network details
                        try:
                            existing = deploy_api_client.get_all_remote_networks()
                            for rn in existing:
                                if rn.get('name') == rn_name:
                                    details = rn.get('details', {})
                                    endpoint_ip = details.get('service_ip_address')
                                    if endpoint_ip:
                                        self.pov_deploy_results.append_text(f"\n  - PA Endpoint IP: {endpoint_ip}")
                                        if not hasattr(self, '_pa_endpoints'):
                                            self._pa_endpoints = {}
                                        self._pa_endpoints[branch['name']] = {
                                            'service_ip': endpoint_ip,
                                            'fqdn': details.get('fqdn'),
                                            'tunnel_name': tunnel_name,
                                            'ike_gateway': ike_gw_name,
                                            'type': 'remote_network',
                                        }
                                    break
                        except Exception:
                            pass
                    else:
                        raise

                self.pov_deploy_results.append_text("\n  [OK] Remote Network configured successfully")
                self._advance_to_next_phase(True, f"Remote Network created for {branch['name']}")

            except Exception as e:
                self._log_activity(f"Failed to create remote network: {e}", "error")
                self.pov_deploy_results.append_text(f"\n  [ERROR] {str(e)}")
                self._advance_to_next_phase(False, str(e))
        else:
            self.pov_deploy_results.append_text("\n  [SKIP] No deploy tenant connected - connect on Tab 5 first")
            self._advance_to_next_phase(False, "No deploy tenant connected")

    def _execute_mobile_users_phase(self, phase: dict):
        """Configure Mobile Users settings."""
        mu_config = self._deployment_context.get('use_cases', {}).get('mobile_users', {})

        if not mu_config.get('enabled', False):
            self.pov_deploy_results.append_text("\n  [SKIP] Mobile Users not enabled in POV configuration")
            self._advance_to_next_phase(True, "Mobile Users not enabled")
            return

        self.pov_deploy_results.append_text("\n  Verifying Mobile Users configuration...")
        self.pov_deploy_results.append_text(f"\n  - Portal Name: {mu_config.get('portal_name', 'GlobalProtect-Portal')}")
        self.pov_deploy_results.append_text(f"\n  - VPN Mode: {mu_config.get('vpn_mode', 'On Demand')}")

        # Get split tunnel settings
        split_tunnel = mu_config.get('split_tunnel', {})
        if split_tunnel.get('enabled', False):
            self.pov_deploy_results.append_text(f"\n  - Split Tunnel: Enabled")
            include_domains = split_tunnel.get('include_domains', [])
            exclude_domains = split_tunnel.get('exclude_domains', [])
            if include_domains:
                self.pov_deploy_results.append_text(f"\n    Include: {', '.join(include_domains[:3])}{'...' if len(include_domains) > 3 else ''}")
            if exclude_domains:
                self.pov_deploy_results.append_text(f"\n    Exclude: {', '.join(exclude_domains[:3])}{'...' if len(exclude_domains) > 3 else ''}")
        else:
            self.pov_deploy_results.append_text(f"\n  - Split Tunnel: Disabled (full tunnel)")

        # Get deploy tenant API client to verify
        deploy_api_client = self._get_deploy_api_client()

        if deploy_api_client:
            try:
                # Verify Mobile Users is enabled in tenant
                self.pov_deploy_results.append_text("\n  Checking tenant Mobile Users status...")
                mu_infra = deploy_api_client.get_mobile_user_infrastructure()

                if mu_infra:
                    self.pov_deploy_results.append_text("\n  [OK] Mobile Users is active in tenant")

                    # Note: Mobile Users GlobalProtect settings are typically pre-configured
                    # in Prisma Access and managed via SCM UI. The POV focuses on:
                    # 1. Security policies for mobile users (handled in security policies phase)
                    # 2. Address objects for mobile user segments (handled in policy objects phase)

                    self._advance_to_next_phase(True, "Mobile Users verified and active")
                else:
                    self.pov_deploy_results.append_text("\n  [WARN] Mobile Users may not be enabled in tenant")
                    self._advance_to_next_phase(True, "Mobile Users status unknown")

            except Exception as e:
                self._log_activity(f"Could not verify Mobile Users: {e}", "warning")
                self.pov_deploy_results.append_text(f"\n  [WARN] Could not verify: {str(e)[:50]}")
                self._advance_to_next_phase(True, "Mobile Users verification skipped")
        else:
            self.pov_deploy_results.append_text("\n  [SKIP] No deploy tenant - cannot verify Mobile Users")
            self._advance_to_next_phase(True, "Skipped - no deploy tenant")

    def _execute_policy_objects_phase(self, phase: dict):
        """Deploy address objects and groups to SCM."""
        custom_policies = self._deployment_context.get('custom_policies', {})
        staged = custom_policies.get('staged_objects', {})
        addr_objects = staged.get('address_objects', [])
        addr_groups = staged.get('address_groups', [])

        self.pov_deploy_results.append_text(f"\n  Deploying {len(addr_objects)} address objects...")
        self.pov_deploy_results.append_text(f"\n  Deploying {len(addr_groups)} address groups...")

        # Get deploy tenant API client
        deploy_api_client = self._get_deploy_api_client()

        if deploy_api_client:
            try:
                created_tags = 0
                skipped_tags = 0
                created_objects = 0
                skipped_objects = 0
                created_groups = 0
                skipped_groups = 0

                # Step 1: Extract and create all unique tags first
                # Tags must exist before objects that reference them
                unique_tags = set()
                for obj in addr_objects:
                    tags = obj.get('tag', [])
                    if tags:
                        unique_tags.update(tags)
                for grp in addr_groups:
                    tags = grp.get('tag', [])
                    if tags:
                        unique_tags.update(tags)

                if unique_tags:
                    self.pov_deploy_results.append_text(f"\n  Creating {len(unique_tags)} tags first...")
                    for tag_name in unique_tags:
                        try:
                            tag_data = {'name': tag_name}
                            deploy_api_client.create_tag(tag_data, folder='Mobile Users')
                            created_tags += 1
                            self._log_activity(f"Created tag: {tag_name}")
                        except Exception as e:
                            if 'already exists' in str(e).lower():
                                skipped_tags += 1
                            else:
                                self._log_activity(f"Failed to create tag {tag_name}: {e}", "warning")

                    if created_tags > 0 or skipped_tags > 0:
                        tag_text = f"\n  Tags: {created_tags} created"
                        if skipped_tags:
                            tag_text += f", {skipped_tags} existed"
                        self.pov_deploy_results.append_text(tag_text)

                # Step 2: Deploy address objects
                for obj in addr_objects:
                    try:
                        obj_name = obj.get('name', 'unnamed')
                        # Remove 'id' if present (from pulled config)
                        obj_data = {k: v for k, v in obj.items() if k != 'id'}
                        deploy_api_client.create_address(obj_data, folder='Mobile Users')
                        created_objects += 1
                        self._log_activity(f"Created address object: {obj_name}")
                    except Exception as e:
                        if 'already exists' in str(e).lower():
                            skipped_objects += 1
                        else:
                            self._log_activity(f"Failed to create address {obj.get('name')}: {e}", "warning")

                # Step 3: Deploy address groups (after objects since groups may reference objects)
                for grp in addr_groups:
                    try:
                        grp_name = grp.get('name', 'unnamed')
                        # Remove 'id' if present
                        grp_data = {k: v for k, v in grp.items() if k != 'id'}
                        deploy_api_client.create_address_group(grp_data, folder='Mobile Users')
                        created_groups += 1
                        self._log_activity(f"Created address group: {grp_name}")
                    except Exception as e:
                        if 'already exists' in str(e).lower():
                            skipped_groups += 1
                        else:
                            self._log_activity(f"Failed to create group {grp.get('name')}: {e}", "warning")

                result_text = f"\n  [OK] Objects: {created_objects} created"
                if skipped_objects:
                    result_text += f", {skipped_objects} existed"
                result_text += f" | Groups: {created_groups} created"
                if skipped_groups:
                    result_text += f", {skipped_groups} existed"
                self.pov_deploy_results.append_text(result_text)
                self._advance_to_next_phase(True, f"Deployed {created_objects} objects, {created_groups} groups")

            except Exception as e:
                self._log_activity(f"Failed to deploy policy objects: {e}", "error")
                self.pov_deploy_results.append_text(f"\n  [ERROR] {str(e)}")
                self._advance_to_next_phase(False, str(e))
        else:
            self.pov_deploy_results.append_text("\n  [SKIP] No deploy tenant connected")
            self._advance_to_next_phase(True, "Skipped - no deploy tenant")

    def _execute_security_policies_phase(self, phase: dict):
        """Deploy security policies to SCM."""
        policies = self._deployment_context.get('custom_policies', {}).get('policies', [])

        # Filter to only dict policies (actual rule configs, not UI description strings)
        rule_policies = [p for p in policies if isinstance(p, dict)]
        string_policies = [p for p in policies if isinstance(p, str)]

        # If we only have description strings, build actual rule configs from them
        if string_policies and not rule_policies:
            self.pov_deploy_results.append_text(f"\n  Building {len(string_policies)} security rules from policy descriptions...")
            rule_policies = self._build_default_security_rules(string_policies)

        if not rule_policies:
            self.pov_deploy_results.append_text("\n  [OK] No security policies to deploy")
            self._advance_to_next_phase(True, "No policies to deploy")
            return

        self.pov_deploy_results.append_text(f"\n  Deploying {len(rule_policies)} security policies...")

        # Get deploy tenant API client
        deploy_api_client = self._get_deploy_api_client()

        if deploy_api_client and rule_policies:
            try:
                created_rules = 0
                skipped_rules = 0

                for policy in rule_policies:
                    try:
                        policy_name = policy.get('name', 'unnamed')
                        # Remove 'id' and 'folder' if present (will use target folder)
                        policy_data = {k: v for k, v in policy.items() if k not in ['id', 'folder']}
                        deploy_api_client.create_security_rule(policy_data, folder='Mobile Users')
                        created_rules += 1
                        self._log_activity(f"Created security rule: {policy_name}")
                    except Exception as e:
                        if 'already exists' in str(e).lower():
                            skipped_rules += 1
                        else:
                            self._log_activity(f"Failed to create rule {policy.get('name')}: {e}", "warning")

                result_text = f"\n  [OK] Rules: {created_rules} created"
                if skipped_rules:
                    result_text += f", {skipped_rules} existed"
                self.pov_deploy_results.append_text(result_text)
                self._advance_to_next_phase(True, f"Deployed {created_rules} security rules")

            except Exception as e:
                self._log_activity(f"Failed to deploy security policies: {e}", "error")
                self.pov_deploy_results.append_text(f"\n  [ERROR] {str(e)}")
                self._advance_to_next_phase(False, str(e))
        elif not rule_policies:
            self.pov_deploy_results.append_text("\n  [OK] No security rule configs to deploy")
            self._advance_to_next_phase(True, "No rule configs to deploy")
        else:
            self.pov_deploy_results.append_text("\n  [SKIP] No deploy tenant connected")
            self._advance_to_next_phase(True, "Skipped - no deploy tenant")

    def _build_default_security_rules(self, policy_descriptions: list) -> list:
        """Build actual security rule configurations from policy descriptions.

        Interprets common policy descriptions and creates proper SCM security rule
        configs. These are the default POV security policies.

        Args:
            policy_descriptions: List of policy description strings

        Returns:
            List of security rule config dicts ready for SCM API
        """
        rules = []

        # Map common descriptions to actual rule configs
        for desc in policy_descriptions:
            desc_lower = desc.lower()

            # Rule: Trust to Untrust (internet access)
            if 'trust' in desc_lower and 'untrust' in desc_lower and ('internet' in desc_lower or 'outbound' in desc_lower):
                rules.append({
                    'name': 'allow-trust-to-untrust',
                    'source': ['any'],
                    'destination': ['any'],
                    'source_user': ['any'],
                    'application': ['any'],
                    'service': ['application-default'],
                    'action': 'allow',
                    'from': ['trust'],
                    'to': ['untrust'],
                    'log_end': True,
                    'description': desc,
                })

            # Rule: Trust to Trust (inter-datacenter/inter-zone)
            elif 'trust' in desc_lower and ('inter' in desc_lower or 'between' in desc_lower or 'datacenter' in desc_lower):
                rules.append({
                    'name': 'allow-trust-to-trust',
                    'source': ['any'],
                    'destination': ['any'],
                    'source_user': ['any'],
                    'application': ['any'],
                    'service': ['application-default'],
                    'action': 'allow',
                    'from': ['trust'],
                    'to': ['trust'],
                    'log_end': True,
                    'description': desc,
                })

            # Rule: Untrust to Trust (inbound from Prisma Access / GlobalProtect users)
            elif 'untrust' in desc_lower and 'trust' in desc_lower and ('inbound' in desc_lower or 'prisma' in desc_lower or 'globalprotect' in desc_lower or 'user' in desc_lower):
                rules.append({
                    'name': 'allow-prisma-access-inbound',
                    'source': ['any'],
                    'destination': ['any'],
                    'source_user': ['any'],
                    'application': ['any'],
                    'service': ['application-default'],
                    'action': 'allow',
                    'from': ['untrust'],
                    'to': ['trust'],
                    'log_end': True,
                    'description': desc,
                })

            # Rule: DNS access
            elif 'dns' in desc_lower:
                rules.append({
                    'name': 'allow-dns',
                    'source': ['any'],
                    'destination': ['any'],
                    'source_user': ['any'],
                    'application': ['dns'],
                    'service': ['application-default'],
                    'action': 'allow',
                    'from': ['any'],
                    'to': ['any'],
                    'log_end': True,
                    'description': desc,
                })

            # Rule: Web/HTTP/HTTPS access
            elif 'web' in desc_lower or 'http' in desc_lower or 'ssl' in desc_lower or 'internet' in desc_lower:
                rules.append({
                    'name': 'allow-web-browsing',
                    'source': ['any'],
                    'destination': ['any'],
                    'source_user': ['any'],
                    'application': ['web-browsing', 'ssl'],
                    'service': ['application-default'],
                    'action': 'allow',
                    'from': ['trust'],
                    'to': ['untrust'],
                    'log_end': True,
                    'description': desc,
                })

            # Generic allow rule for unrecognized descriptions
            else:
                # Create a sanitized name from the description
                rule_name = desc.lower().replace(' ', '-')[:30]
                # Remove non-alphanumeric characters except hyphens
                import re
                rule_name = re.sub(r'[^a-z0-9-]', '', rule_name)
                rule_name = re.sub(r'-+', '-', rule_name).strip('-')
                if not rule_name:
                    rule_name = f'custom-rule-{len(rules)+1}'

                rules.append({
                    'name': rule_name,
                    'source': ['any'],
                    'destination': ['any'],
                    'source_user': ['any'],
                    'application': ['any'],
                    'service': ['application-default'],
                    'action': 'allow',
                    'from': ['any'],
                    'to': ['any'],
                    'log_end': True,
                    'description': desc,
                })

        return rules

    def _execute_adem_phase(self, phase: dict):
        """Configure ADEM synthetic tests.

        Note: ADEM (Autonomous Digital Experience Management) synthetic test
        configuration via API is not publicly documented by Palo Alto Networks.
        This phase logs the configured tests and provides guidance for manual
        setup via Strata Cloud Manager UI.
        """
        adem_config = self._deployment_context.get('use_cases', {}).get('aiops_adem', {})
        tests = adem_config.get('tests', [])

        if not adem_config.get('enabled', False):
            self.pov_deploy_results.append_text("\n  ADEM is disabled - skipping")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(300, lambda: self._advance_to_next_phase(True, "ADEM disabled"))
            return

        if not tests:
            self.pov_deploy_results.append_text("\n  No ADEM synthetic tests configured")
            self.pov_deploy_results.append_text("\n  [INFO] Configure tests in SCM: Insights > Application Experience > Application Tests")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(300, lambda: self._advance_to_next_phase(True, "No ADEM tests to configure"))
            return

        self.pov_deploy_results.append_text(f"\n  ADEM synthetic tests to configure ({len(tests)}):")

        # Log each test configuration for manual setup reference
        for i, test in enumerate(tests, 1):
            target = test.get('target', 'unknown')
            conditions = []
            if test.get('on_vpn', True):
                conditions.append('On VPN')
            if test.get('in_office', False):
                conditions.append('In Office')
            if test.get('not_on_vpn', False):
                conditions.append('Not on VPN')

            cond_str = ', '.join(conditions) if conditions else 'On VPN'
            self.pov_deploy_results.append_text(f"\n    {i}. {target} ({cond_str})")

        # ADEM API for synthetic test creation is not publicly documented
        # Provide guidance for manual configuration
        self.pov_deploy_results.append_text("\n")
        self.pov_deploy_results.append_text("\n  [INFO] ADEM synthetic test API is not publicly documented.")
        self.pov_deploy_results.append_text("\n  [INFO] Please configure tests manually in Strata Cloud Manager:")
        self.pov_deploy_results.append_text("\n         Insights > Application Experience > Application Tests")
        self.pov_deploy_results.append_text("\n  [OK] ADEM test requirements documented")

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self._advance_to_next_phase(True, f"ADEM: {len(tests)} tests documented for manual setup"))

    def _on_phase_progress(self, message: str, percentage: int):
        """Handle progress from current phase."""
        # Scale phase progress to overall progress
        total_phases = len(self._deploy_phases)
        base_progress = int((self._current_deploy_phase / total_phases) * 100)
        phase_contribution = int((percentage / 100) * (100 / total_phases))
        overall_progress = min(base_progress + phase_contribution, 99)
        self.pov_deploy_progress.setValue(overall_progress)

    def _on_phase_error(self, error: str):
        """Handle phase error."""
        self._log_activity(f"Phase error: {error}", "error")
        self.pov_deploy_results.append_text(f"\n  [ERROR] {error}")

    def _on_phase_finished(self, success: bool, message: str, result: dict):
        """Handle phase completion."""
        phase = self._deploy_phases[self._current_deploy_phase]
        self._deploy_phase_results[phase['name']] = {
            'success': success,
            'message': message,
            'result': result,
        }

        if success:
            self.pov_deploy_results.append_text(f"\n  [OK] {message}")
        else:
            self.pov_deploy_results.append_text(f"\n  [FAILED] {message}")

        self._advance_to_next_phase(success, message)

    def _advance_to_next_phase(self, success: bool, message: str):
        """Advance to the next deployment phase."""
        phase = self._deploy_phases[self._current_deploy_phase]
        phase_type = phase.get('type', '')

        if phase['name'] not in self._deploy_phase_results:
            self._deploy_phase_results[phase['name']] = {
                'success': success,
                'message': message,
            }

        # Track completed phases for resume support
        if success:
            self._pov_deployment_phases_completed.append(phase['name'])

        # If a critical phase failed, mark dependent phases as skipped
        if not success:
            self._mark_dependent_phases_failed(phase)

        # Save state after each phase for resume support
        self.save_state()

        self._current_deploy_phase += 1
        self._execute_next_deploy_phase()

    def _mark_dependent_phases_failed(self, failed_phase: dict):
        """Mark phases that depend on a failed phase as skipped.

        Dependencies:
        - firewall_base failure -> skip service_connection_fw, remote_network_fw for that firewall
        - service_connection_pa failure -> skip service_connection_fw for that datacenter (no endpoint IPs)
        - remote_network_pa failure -> skip remote_network_fw for that branch (no endpoint IPs)
        """
        failed_type = failed_phase.get('type', '')
        failed_fw = failed_phase.get('firewall', {})
        failed_dc = failed_phase.get('datacenter', {})
        failed_branch = failed_phase.get('branch', {})

        for i, phase in enumerate(self._deploy_phases):
            if i <= self._current_deploy_phase:
                continue  # Already processed

            phase_type = phase.get('type', '')
            should_skip = False
            skip_reason = ""

            # Firewall base failure -> skip FW-side phases for that firewall
            if failed_type == 'firewall_base':
                phase_fw = phase.get('firewall', {})
                if phase_fw.get('name') == failed_fw.get('name'):
                    if phase_type in ['service_connection_fw', 'remote_network_fw']:
                        should_skip = True
                        skip_reason = f"Firewall {failed_fw.get('name')} base config failed"

            # Service connection PA failure -> skip FW side for that datacenter (no endpoint IPs)
            if failed_type == 'service_connection_pa':
                phase_dc = phase.get('datacenter', {})
                if phase_dc.get('name') == failed_dc.get('name') and phase_type == 'service_connection_fw':
                    should_skip = True
                    skip_reason = f"PA side failed for {failed_dc.get('name')} - no endpoint IPs available"

            # Remote network PA failure -> skip FW side for that branch (no endpoint IPs)
            if failed_type == 'remote_network_pa':
                phase_branch = phase.get('branch', {})
                if phase_branch.get('name') == failed_branch.get('name') and phase_type == 'remote_network_fw':
                    should_skip = True
                    skip_reason = f"PA side failed for {failed_branch.get('name')} - no endpoint IPs available"

            if should_skip:
                self._deploy_phase_results[phase['name']] = {
                    'success': False,
                    'message': f"Skipped: {skip_reason}",
                    'skipped': True,
                }
                self._log_activity(f"Skipping {phase['name']}: {skip_reason}", "warning")

    def _on_all_deploy_phases_complete(self):
        """Handle completion of all deployment phases."""
        # Reset deployment state
        self._pov_deployment_in_progress = False
        self._pov_deployment_cancelled = False

        self.review_config_btn.setEnabled(True)
        self.pov_deploy_progress.setValue(100)
        self.pov_deploy_progress.setVisible(False)

        # Count successes, failures, and skipped
        successes = sum(1 for r in self._deploy_phase_results.values() if r.get('success'))
        skipped = sum(1 for r in self._deploy_phase_results.values() if r.get('skipped'))
        failures = len(self._deploy_phase_results) - successes - skipped

        # Save final state
        self.save_state()

        if failures == 0 and skipped == 0:
            self._log_activity("All deployment phases completed successfully")
            self._update_deploy_config_button_style("deploy")
            self.deploy_config_btn.setEnabled(True)
            self._pov_deployment_phases_completed = []  # Reset for fresh deployment
            self.pov_deploy_results.append_text(
                f"\n\n=== DEPLOYMENT COMPLETE ===\n"
                f"All {successes} phases completed successfully!\n\n"
                "Summary:\n"
                "  - Firewall configuration: Complete\n"
                "  - Service Connections: Configured\n"
                "  - Remote Networks: Configured\n"
                "  - Prisma Access Config: Deployed"
            )
            self.complete_btn.setEnabled(True)
        else:
            self._log_activity(f"Deployment completed with {failures} failures, {skipped} skipped", "warning")
            # Keep button as "Resume Deployment" if there were failures
            self._update_deploy_config_button_style("resume")
            self.deploy_config_btn.setEnabled(True)

            summary_text = f"\n\n=== DEPLOYMENT COMPLETED WITH ERRORS ===\n"
            summary_text += f"Completed: {successes} phases\n"
            if failures > 0:
                summary_text += f"Failed: {failures} phases\n"
            if skipped > 0:
                summary_text += f"Skipped: {skipped} phases (due to dependencies)\n"
            summary_text += "\nReview the logs above for details."
            summary_text += "\nClick 'Resume Deployment' to retry failed phases."

            self.pov_deploy_results.append_text(summary_text)

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

    # ========================================================================
    # STATE PERSISTENCE (Auto-save/Resume)
    # ========================================================================

    def _get_state_dir(self) -> Path:
        """Get the directory for POV state files."""
        state_dir = Path.home() / ".pa_config_lab" / "pov_states"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    def _next_tab(self, tab_index: int):
        """Navigate to the next tab after saving state."""
        current_tab = tab_index - 1

        # Special handling for Tab 1 -> Tab 2 transition
        if current_tab == 0:
            # Ensure infrastructure is configured before proceeding
            if not self.deployment_config.get('infrastructure_configured', False):
                # Auto-apply defaults
                self._apply_default_infrastructure()
                logger.info("Applied default infrastructure configuration on tab navigation")

        # Special handling for Tab 2 -> Tab 3 transition
        if current_tab == 1:
            # Validate cloud resources requirements
            if not self._validate_cloud_resources_tab():
                return  # Validation failed, don't proceed

        # Special handling for Tab 3 -> Tab 4 transition (Cloud Deployment -> Deploy POV Config)
        if current_tab == 3:
            # Check if cloud deployment is enabled but not completed
            if self.deployment_config.get('deploy_cloud_resources', False):
                if not hasattr(self, '_terraform_deployed') or not self._terraform_deployed:
                    # Use custom styled warning dialog (QMessageBox styling doesn't work on Windows)
                    if not self._show_terraform_warning_dialog():
                        return  # User chose not to continue

        # Save current state before moving to next tab
        self.save_state(current_tab)  # Save the tab we're leaving
        # Switch to the requested tab
        self.tabs.setCurrentIndex(tab_index)

    def save_state(self, current_tab: int = None):
        """Save current workflow state to a file for later resume (overwrites existing)."""
        import json
        from datetime import datetime

        if current_tab is None:
            current_tab = self.tabs.currentIndex()

        # Generate state filename based on sanitized customer name (one file per customer)
        customer_info = self.cloud_resource_configs.get('customer_info', {})
        customer_display = customer_info.get('customer_name', '')
        # Use sanitized name for filename, fall back to sanitizing display name
        customer = customer_info.get('customer_name_sanitized', '')
        if not customer and customer_display:
            customer = self._sanitize_customer_name(customer_display)
        if not customer:
            customer = 'unnamed'

        # Use fixed filename per customer (overwrites existing)
        state_filename = f"pov_state_{customer}.json"

        # Build state data
        state = {
            'version': '1.0',
            'customer': customer,
            'saved_at': datetime.now().isoformat(),
            'last_tab': current_tab,
            'management_type': self.management_type,
            'connection_name': self.connection_name,
            'customer_info': self.cloud_resource_configs.get('customer_info', {}),
            'cloud_resource_configs': self.cloud_resource_configs,
            'use_case_configs': getattr(self, 'use_case_configs', {}),
            'config_data': self.config_data,
            'deployment_config': self.deployment_config,
            # Terraform state tracking
            'terraform_output_dir': getattr(self, '_terraform_output_dir', None),
            'terraform_deployed': getattr(self, '_terraform_deployed', False),
            'terraform_outputs': getattr(self, '_terraform_outputs', {}),
            # POV deployment state tracking
            'pov_deployment_phases_completed': getattr(self, '_pov_deployment_phases_completed', []),
            # Deploy tenant name (Tab 5 destination tenant)
            'deploy_tenant_name': getattr(self, '_deploy_tenant_name', None),
        }

        # Save to file (overwrites existing)
        state_path = self._get_state_dir() / state_filename
        try:
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            logger.info(f"Saved POV state to {state_path}")
        except Exception as e:
            logger.error(f"Failed to save POV state: {e}")

    def load_state(self, state_path: Path) -> bool:
        """Load a saved workflow state from file."""
        import json

        try:
            with open(state_path, 'r') as f:
                state = json.load(f)

            # Restore state
            self.management_type = state.get('management_type', 'scm')
            self.connection_name = state.get('connection_name')
            self.cloud_resource_configs = state.get('cloud_resource_configs', {})
            self.config_data = state.get('config_data', {})

            # Restore deployment_config with defaults if not present
            self.deployment_config = state.get('deployment_config', {
                'management_type': self.management_type,
                'infrastructure_configured': False,
                'infrastructure_source': None,
                'panorama_placeholder': None,
            })

            if hasattr(self, 'use_case_configs'):
                self.use_case_configs = state.get('use_case_configs', {})

            # Restore terraform state
            self._terraform_output_dir = state.get('terraform_output_dir')
            self._terraform_deployed = state.get('terraform_deployed', False)
            self._terraform_outputs = state.get('terraform_outputs', {})

            # If terraform was deployed but outputs are missing, try to read from terraform state
            if self._terraform_deployed and not self._terraform_outputs and self._terraform_output_dir:
                self._terraform_outputs = self._read_terraform_outputs_from_state()

            # Restore POV deployment state
            self._pov_deployment_phases_completed = state.get('pov_deployment_phases_completed', [])
            self._pov_deployment_in_progress = False
            self._pov_deployment_cancelled = False

            # Restore deploy tenant name (Tab 5 destination tenant)
            self._deploy_tenant_name = state.get('deploy_tenant_name')

            # Restore UI state
            self._restore_ui_from_state(state)

            # Navigate to the tab after the last configured one
            last_tab = state.get('last_tab', 0)
            next_tab = min(last_tab + 1, self.tabs.count() - 1)
            self.tabs.setCurrentIndex(next_tab)

            logger.info(f"Loaded POV state from {state_path}, resuming at tab {next_tab}")
            return True

        except Exception as e:
            logger.error(f"Failed to load POV state: {e}")
            QMessageBox.critical(
                self,
                "Load Failed",
                f"Failed to load saved state:\n{str(e)}"
            )
            return False

    def _restore_ui_from_state(self, state: Dict[str, Any]):
        """Restore UI widgets from loaded state."""
        # Restore management type radio
        if self.management_type == 'panorama':
            self.panorama_managed_radio.setChecked(True)
        else:
            self.scm_managed_radio.setChecked(True)

        # Restore customer info
        customer_info = state.get('customer_info', {})
        if hasattr(self, 'customer_name_input') and customer_info.get('customer_name'):
            self.customer_name_input.setText(customer_info['customer_name'])

        if hasattr(self, 'customer_industry_combo') and customer_info.get('industry'):
            index = self.customer_industry_combo.findText(customer_info['industry'])
            if index >= 0:
                self.customer_industry_combo.setCurrentIndex(index)

        # Restore infrastructure configuration status
        infra_config = self.cloud_resource_configs.get('infrastructure', {})
        existing_devices = self.cloud_resource_configs.get('existing_devices', [])
        if hasattr(self, 'infra_status_label'):
            if infra_config.get('configured'):
                source = infra_config.get('source', 'manual')
                if existing_devices:
                    self.infra_status_label.setText(f"Status: ✓ Configured ({source}) + {len(existing_devices)} system(s)")
                else:
                    self.infra_status_label.setText(f"Status: ✓ Configured ({source})")
                self.infra_status_label.setStyleSheet("color: #4CAF50; font-weight: bold; margin-top: 10px;")
            elif existing_devices:
                self.infra_status_label.setText(f"Status: {len(existing_devices)} existing system(s)")
                self.infra_status_label.setStyleSheet("color: #FF9800; font-weight: bold; margin-top: 10px;")

        # Restore deploy cloud resources checkbox
        if hasattr(self, 'deploy_cloud_checkbox'):
            deploy_enabled = self.deployment_config.get('deploy_cloud_resources', False)
            self.deploy_cloud_checkbox.setChecked(deploy_enabled)
            # Also update the scroll widget state
            if hasattr(self, 'cloud_resources_scroll'):
                self.cloud_resources_scroll.setEnabled(deploy_enabled)
            # Update Next button state based on deploy setting
            if hasattr(self, 'cloud_deploy_next_btn'):
                if deploy_enabled:
                    # Cloud deployment enabled - disable Next until Terraform deployed
                    self.cloud_deploy_next_btn.setEnabled(False)
                    self.cloud_deploy_next_btn.setToolTip("Deploy Terraform first to enable this button")
                else:
                    # Cloud deployment disabled - enable Next
                    self.cloud_deploy_next_btn.setEnabled(True)
                    self.cloud_deploy_next_btn.setToolTip("Proceed to deploy POV configuration")

        # Restore tenant connection status display - show saved tenant but note reconnection needed
        if hasattr(self, 'load_status') and self.connection_name:
            self.load_status.setText(f"Previously: {self.connection_name} (reconnect to continue)")
            self.load_status.setStyleSheet("color: #FF9800;")  # Orange - needs attention
        elif hasattr(self, 'load_status'):
            self.load_status.setText("No tenant connected")
            self.load_status.setStyleSheet("color: gray;")

        # If tenant selector exists, select the saved tenant in dropdown so user can easily reconnect
        if hasattr(self, 'tenant_selector') and self.connection_name:
            # Find and select the tenant in dropdown without triggering connection
            combo = self.tenant_selector.tenant_combo
            combo.blockSignals(True)
            for i in range(combo.count()):
                if combo.itemText(i) == self.connection_name:
                    combo.setCurrentIndex(i)
                    break
            combo.blockSignals(False)
            # Update status label to show needs reconnection
            self.tenant_selector.status_label.setText(f"⚠️ Select '{self.connection_name}' to reconnect")
            self.tenant_selector.status_label.setStyleSheet("color: #FF9800; padding: 8px; margin-top: 5px;")

        # Restore deploy tenant selector status (Tab 5)
        deploy_tenant_name = state.get('deploy_tenant_name')
        if hasattr(self, 'deploy_tenant_selector') and deploy_tenant_name:
            # Pre-select the deploy tenant in dropdown (without triggering connection)
            combo = self.deploy_tenant_selector.tenant_combo
            combo.blockSignals(True)
            for i in range(combo.count()):
                if combo.itemText(i) == deploy_tenant_name:
                    combo.setCurrentIndex(i)
                    break
            combo.blockSignals(False)
            # Update status to show auto-connect pending
            self.deploy_tenant_selector.status_label.setText(
                f"⏳ Will auto-connect to '{deploy_tenant_name}' when tab opens"
            )
            self.deploy_tenant_selector.status_label.setStyleSheet(
                "color: #1565C0; padding: 8px; margin-top: 5px; font-style: italic;"
            )

        # Restore admin credentials in UI
        cloud_deployment = self.cloud_resource_configs.get('cloud_deployment', {})
        if hasattr(self, 'cloud_admin_username') and cloud_deployment.get('admin_username'):
            self.cloud_admin_username.setText(cloud_deployment['admin_username'])
        if hasattr(self, 'cloud_admin_password') and cloud_deployment.get('admin_password'):
            # Block signals to avoid triggering password change handler
            self.cloud_admin_password.blockSignals(True)
            self.cloud_admin_password.setText(cloud_deployment['admin_password'])
            self.cloud_admin_password.blockSignals(False)
            # Update password strength indicator
            if hasattr(self, '_update_password_strength'):
                self._update_password_strength()

        # Restore services & applications card
        services_config = self.cloud_resource_configs.get('services', {})
        if hasattr(self, 'services_domain_input') and services_config.get('domain'):
            self.services_domain_input.setText(services_config['domain'])
        pki_config = services_config.get('pki', {})
        if hasattr(self, 'pki_server_cert_cb'):
            self.pki_server_cert_cb.setChecked(pki_config.get('server_cert', True))
        if hasattr(self, 'pki_device_certs_cb'):
            self.pki_device_certs_cb.setChecked(pki_config.get('device_certs', True))
        if hasattr(self, 'pki_user_certs_cb'):
            self.pki_user_certs_cb.setChecked(pki_config.get('user_certs', True))
        if hasattr(self, 'pki_decryption_ca_cb'):
            self.pki_decryption_ca_cb.setChecked(pki_config.get('decryption_ca', True))
        if hasattr(self, '_update_services_status'):
            self._update_services_status()

        # Refresh other UI elements
        if hasattr(self, '_update_cloud_rg_preview'):
            self._update_cloud_rg_preview()
        if hasattr(self, '_update_cloud_deployment_status'):
            self._update_cloud_deployment_status()
        if hasattr(self, '_refresh_locations_list'):
            self._refresh_locations_list()
        if hasattr(self, '_refresh_trust_devices_list'):
            self._refresh_trust_devices_list()

        # Refresh Use Cases tab elements
        if hasattr(self, '_refresh_private_app_connections'):
            self._refresh_private_app_connections()
        if hasattr(self, '_update_private_app_limits'):
            self._update_private_app_limits()
        if hasattr(self, '_refresh_remote_branch_lists'):
            self._refresh_remote_branch_lists()

        # Restore ADEM configuration
        self._restore_adem_ui_state()

        # Restore Azure credentials from saved state
        self._restore_azure_credentials_ui_state()

        # Restore terraform UI state
        self._restore_terraform_ui_state(state)

        # Restore deploy button state based on completed phases
        if hasattr(self, '_pov_deployment_phases_completed') and self._pov_deployment_phases_completed:
            self._update_deploy_config_button_style("resume")

    def _restore_adem_ui_state(self):
        """Restore ADEM configuration UI from use_case_configs."""
        adem_config = self.use_case_configs.get('aiops_adem', {})

        # Restore enabled checkbox
        if hasattr(self, 'aiops_adem_enable'):
            self.aiops_adem_enable.setChecked(adem_config.get('enabled', True))

        # Restore tests list
        if hasattr(self, 'adem_tests_list'):
            self.adem_tests_list.clear()
            tests = adem_config.get('tests', [])
            for test in tests:
                target = test.get('target', '')
                conditions = []
                if test.get('on_vpn'):
                    conditions.append("VPN")
                if test.get('in_office'):
                    conditions.append("Office")
                if test.get('not_on_vpn'):
                    conditions.append("No-VPN")
                if not conditions:
                    conditions.append("VPN")  # Default
                display_text = f"{target} ({', '.join(conditions)})"
                self.adem_tests_list.addItem(display_text)

        # Update status label
        self._update_use_case_status('aiops_adem')

    def _restore_azure_credentials_ui_state(self):
        """Restore Azure credentials UI from saved deployment_config."""
        # Check if we have saved Azure credentials
        saved_sub_id = self.deployment_config.get('azure_subscription_id', '')
        saved_sub_name = self.deployment_config.get('azure_subscription_name', '')
        saved_tenant_id = self.deployment_config.get('azure_tenant_id', '')

        if saved_sub_id and saved_tenant_id:
            # Restore the _azure_subscription object for use by terraform generation
            self._azure_subscription = {
                'id': saved_sub_id,
                'name': saved_sub_name,
                'tenant_id': saved_tenant_id,
            }

            # Populate the tenant ID field with cached indicator
            if hasattr(self, 'azure_tenant_input'):
                self.azure_tenant_input.setText(f"{saved_tenant_id} (cached credential)")
                self.azure_tenant_input.setStyleSheet(
                    "padding: 5px; background-color: #E8F5E9; color: #2E7D32;"
                )

            # Update auth status to show cached credentials
            if hasattr(self, 'azure_auth_status'):
                self.azure_auth_status.setText(f"🟢 {saved_sub_name} (cached)")
                self.azure_auth_status.setStyleSheet("font-weight: bold; color: #4CAF50;")
                self.azure_auth_status.setToolTip(
                    f"Subscription: {saved_sub_name}\n"
                    f"ID: {saved_sub_id}\n"
                    f"Tenant: {saved_tenant_id}\n\n"
                    "Using cached credentials from previous session.\n"
                    "Click 'Change Subscription' to re-authenticate."
                )

            # Update auth button to show change option
            if hasattr(self, 'azure_auth_btn'):
                self.azure_auth_btn.setText("🔄 Change Subscription")
                self.azure_auth_btn.setStyleSheet(
                    "padding: 10px 20px; font-size: 14px; "
                    "background-color: #E3F2FD; color: #1565C0; "
                    "border: 1px solid #1565C0; border-radius: 5px;"
                )
                self.azure_auth_btn.setToolTip(
                    "Click to re-authenticate or select a different subscription"
                )

            self._log_activity(
                f"Restored Azure credentials from cache: {saved_sub_name} (tenant: {saved_tenant_id})"
            )

            # Show terraform status widget and trigger generation if needed
            if hasattr(self, 'terraform_status_widget'):
                self.terraform_status_widget.setVisible(True)

            # Check if terraform files exist and enable buttons accordingly
            terraform_output_dir = self.deployment_config.get('terraform_output_dir') or \
                                   getattr(self, '_terraform_output_dir', None)
            if terraform_output_dir:
                import os
                terraform_dir = os.path.join(terraform_output_dir, 'terraform') if 'terraform' not in terraform_output_dir else terraform_output_dir
                main_tf_exists = os.path.exists(os.path.join(terraform_dir, 'main.tf'))

                if main_tf_exists:
                    # Terraform files exist - enable action buttons
                    if hasattr(self, 'regen_terraform_btn'):
                        self.regen_terraform_btn.setEnabled(True)
                    if hasattr(self, 'review_terraform_btn'):
                        self.review_terraform_btn.setEnabled(True)
                    if hasattr(self, 'edit_terraform_btn'):
                        self.edit_terraform_btn.setEnabled(True)
                    if hasattr(self, 'deploy_terraform_btn'):
                        self.deploy_terraform_btn.setEnabled(True)

                    if hasattr(self, 'terraform_gen_status'):
                        self.terraform_gen_status.setText("✓ Terraform configuration ready (from cache)")
                        self.terraform_gen_status.setStyleSheet(
                            "color: #2E7D32; padding: 10px; background-color: #E8F5E9; "
                            "border-radius: 5px;"
                        )
                else:
                    # Need to regenerate terraform files
                    if hasattr(self, 'terraform_gen_status'):
                        self.terraform_gen_status.setText("⚠️ Click to regenerate Terraform configuration")
                        self.terraform_gen_status.setStyleSheet(
                            "color: #FF9800; padding: 10px; background-color: #FFF3E0; "
                            "border-radius: 5px; cursor: pointer;"
                        )
            else:
                # No terraform output dir - prompt to generate
                if hasattr(self, 'terraform_gen_status'):
                    self.terraform_gen_status.setText("⚠️ Terraform not generated - authenticate to generate")
                    self.terraform_gen_status.setStyleSheet(
                        "color: #FF9800; padding: 10px; background-color: #FFF3E0; "
                        "border-radius: 5px;"
                    )

    def _restore_terraform_ui_state(self, state: Dict[str, Any]):
        """Restore terraform-related UI state."""
        import os

        # Check if terraform files exist for this customer
        terraform_output_dir = state.get('terraform_output_dir')
        terraform_deployed = state.get('terraform_deployed', False)

        if terraform_output_dir:
            terraform_dir = os.path.join(terraform_output_dir, 'terraform')
            main_tf_exists = os.path.exists(os.path.join(terraform_dir, 'main.tf'))
            state_exists = os.path.exists(os.path.join(terraform_dir, 'terraform.tfstate'))

            if main_tf_exists:
                # Terraform files exist - enable buttons
                if hasattr(self, 'regen_terraform_btn'):
                    self.regen_terraform_btn.setEnabled(True)
                if hasattr(self, 'review_terraform_btn'):
                    self.review_terraform_btn.setEnabled(True)
                if hasattr(self, 'edit_terraform_btn'):
                    self.edit_terraform_btn.setEnabled(True)
                if hasattr(self, 'deploy_terraform_btn'):
                    self.deploy_terraform_btn.setEnabled(True)

                # Update generation status
                if hasattr(self, 'terraform_gen_status'):
                    if state_exists or terraform_deployed:
                        self.terraform_gen_status.setText("✓ Terraform deployed - ready for updates")
                    else:
                        self.terraform_gen_status.setText("✓ Terraform configuration ready")
                    self.terraform_gen_status.setStyleSheet(
                        "color: #2E7D32; padding: 10px; background-color: #E8F5E9; "
                        "border-radius: 5px;"
                    )
                    if hasattr(self, 'terraform_status_widget'):
                        self.terraform_status_widget.setVisible(True)

                # Update deploy button text
                if hasattr(self, '_update_deploy_button_state'):
                    self._update_deploy_button_state()

                # Update Next button state
                if hasattr(self, 'cloud_deploy_next_btn'):
                    if terraform_deployed or state_exists:
                        self.cloud_deploy_next_btn.setEnabled(True)
                        self.cloud_deploy_next_btn.setToolTip("Proceed to deploy POV configuration")

                # Populate credentials panel if terraform was deployed
                if terraform_deployed or state_exists:
                    # Ensure terraform outputs are loaded
                    if not getattr(self, '_terraform_outputs', None):
                        self._terraform_outputs = self._read_terraform_outputs_from_state()
                    # Populate and show credentials
                    self._populate_deployment_credentials()

    def _read_terraform_outputs_from_state(self) -> Dict[str, Any]:
        """Read terraform outputs from the terraform.tfstate file.

        This is a fallback when resuming a POV where outputs weren't saved.

        Returns:
            Dict of terraform outputs, or empty dict if not available
        """
        import os
        import json

        if not self._terraform_output_dir:
            return {}

        state_file = os.path.join(self._terraform_output_dir, 'terraform', 'terraform.tfstate')
        if not os.path.exists(state_file):
            logger.debug(f"Terraform state file not found: {state_file}")
            return {}

        try:
            with open(state_file, 'r') as f:
                tf_state = json.load(f)

            # Parse outputs from terraform state
            outputs = {}
            tf_outputs = tf_state.get('outputs', {})
            for key, value_obj in tf_outputs.items():
                # Terraform state format: {"output_name": {"value": "...", "type": "..."}}
                if isinstance(value_obj, dict):
                    outputs[key] = value_obj.get('value')
                else:
                    outputs[key] = value_obj

            if outputs:
                logger.info(f"Restored {len(outputs)} terraform outputs from state file")
                self._log_activity(f"Restored terraform outputs: {list(outputs.keys())}")

            return outputs

        except Exception as e:
            logger.warning(f"Failed to read terraform outputs from state: {e}")
            return {}

    def _get_saved_states(self) -> List[Dict[str, Any]]:
        """Get list of saved POV states with metadata."""
        import json

        state_dir = self._get_state_dir()
        states = []

        for state_file in sorted(state_dir.glob("pov_state_*.json"),
                                  key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                # Get display customer name from customer_info (original case/spaces)
                # Fall back to sanitized 'customer' field if customer_info not available
                customer_info = data.get('customer_info', {})
                customer = customer_info.get('customer_name') or data.get('customer', 'Unknown')
                states.append({
                    'path': state_file,
                    'filename': state_file.name,
                    'customer': customer,
                    'saved_at': data.get('saved_at', 'Unknown'),
                    'last_tab': data.get('last_tab', 0),
                    'management_type': data.get('management_type', 'scm'),
                })
            except Exception as e:
                logger.warning(f"Failed to read state file {state_file}: {e}")

        return states

    def _show_resume_pov_dialog(self):
        """Show dialog to select and load a saved POV state."""
        from PyQt6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QHeaderView

        states = self._get_saved_states()

        if not states:
            QMessageBox.information(
                self,
                "No Saved States",
                "No saved POV deployment states found.\n\n"
                "States are automatically saved when you click 'Next' on each tab."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Resume POV Deployment")
        dialog.setMinimumSize(700, 400)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(
            "Select a saved POV deployment state to resume. "
            "States are automatically saved as you progress through the tabs."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # Table of saved states
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Customer", "Saved At", "Last Tab", "Type", "Filename"])
        table.setRowCount(len(states))
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        tab_names = ["Tenant Info", "Cloud Resources", "Use Cases", "Cloud Deployment", "Deploy Config", "Review"]

        for row, state in enumerate(states):
            table.setItem(row, 0, QTableWidgetItem(state['customer']))

            # Format saved_at timestamp
            saved_at = state['saved_at']
            if 'T' in saved_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(saved_at.replace('Z', '+00:00'))
                    saved_at = dt.strftime("%b %d, %Y %I:%M %p")
                except:
                    pass
            table.setItem(row, 1, QTableWidgetItem(saved_at))

            last_tab = state['last_tab']
            tab_name = tab_names[last_tab] if last_tab < len(tab_names) else f"Tab {last_tab}"
            table.setItem(row, 2, QTableWidgetItem(tab_name))
            table.setItem(row, 3, QTableWidgetItem(state['management_type'].upper()))
            table.setItem(row, 4, QTableWidgetItem(state['filename']))

        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)

        # Auto-select the first row
        if states:
            table.selectRow(0)

        # Store states for later access
        dialog.states = states

        # Button row
        btn_layout = QHBoxLayout()

        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; padding: 8px 16px; "
            "font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #d32f2f; }"
        )
        def delete_selected():
            selected = table.selectedItems()
            if not selected:
                return
            row = selected[0].row()
            state_path = dialog.states[row]['path']
            reply = QMessageBox.question(
                dialog, "Confirm Delete",
                f"Delete saved state for '{dialog.states[row]['customer']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    state_path.unlink()
                    table.removeRow(row)
                    dialog.states.pop(row)
                except Exception as e:
                    QMessageBox.warning(dialog, "Delete Failed", str(e))
        delete_btn.clicked.connect(delete_selected)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #757575; color: white; padding: 8px 16px; "
            "font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #616161; }"
        )
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        load_btn = QPushButton("📂 Load & Resume")
        load_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; "
            "font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        def load_selected():
            selected = table.selectedItems()
            if not selected:
                QMessageBox.information(dialog, "No Selection", "Please select a state to load.")
                return
            row = selected[0].row()
            state_path = dialog.states[row]['path']
            dialog.accept()
            self.load_state(state_path)
        load_btn.clicked.connect(load_selected)
        btn_layout.addWidget(load_btn)

        layout.addLayout(btn_layout)
        dialog.exec()

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

        # Reset Tenant Info tab options
        if hasattr(self, 'customer_name_input'):
            self.customer_name_input.clear()
        if hasattr(self, 'customer_industry_combo'):
            self.customer_industry_combo.setCurrentIndex(0)
        if hasattr(self, 'infra_status_label'):
            self.infra_status_label.setText("Using default infrastructure settings")
            self.infra_status_label.setStyleSheet("color: #555; font-style: italic;")

        # Reset Cloud Resources configs
        self.cloud_resource_configs = {
            'cloud_deployment': {},
            'cloud_security': {},
            'device_config': {},
            'policy_objects': {},
            'locations': {'branches': [], 'datacenters': []},
            'trust_devices': {'devices': []},
            'customer_info': {},
            'infrastructure_config': {},
            'existing_devices': [],
        }

        # Reset UI elements
        import json
        self.config_review_text.setPlainText(json.dumps({}, indent=2))
        self.load_status.setText("Configure your environment above")
        self.load_status.setStyleSheet("color: gray;")
        self.sources_summary.setText("<i>No sources loaded</i>")

        # Reset defaults status
        self._update_pa_defaults_status()
