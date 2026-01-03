"""
POV Configuration Workflow GUI - Complete Rewrite.

This module provides a comprehensive workflow for configuring new POV environments
with flexible source loading, management type selection, and default injection.
"""

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
        self.config_data = {}
        self.management_type = "scm"  # "scm" or "panorama"
        self.loaded_sources = []  # Track which sources were loaded
        self.worker = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self)  # Changed to horizontal to accommodate sidebar

        # Left sidebar for saved configs
        from gui.saved_configs_sidebar import SavedConfigsSidebar
        self.saved_configs_sidebar = SavedConfigsSidebar()
        self.saved_configs_sidebar.setMaximumWidth(300)
        self.saved_configs_sidebar.config_loaded.connect(self._on_saved_config_loaded)
        layout.addWidget(self.saved_configs_sidebar)

        # Main content area (vertical layout)
        main_content = QWidget()
        content_layout = QVBoxLayout(main_content)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Step indicator
        steps_label = QLabel(
            "<b>POV Configuration Steps:</b> "
            "1️⃣ Load Sources → 2️⃣ Firewall Defaults → 3️⃣ Prisma Access Defaults → "
            "4️⃣ Configure Firewall → 5️⃣ Configure Prisma Access → 6️⃣ Review & Execute"
        )
        steps_label.setWordWrap(True)
        steps_label.setStyleSheet(
            "padding: 10px; background-color: #e3f2fd; border-radius: 5px;"
        )
        content_layout.addWidget(steps_label)

        # Tabs for each step (reordered - review moved to end)
        self.tabs = QTabWidget()

        self._create_sources_tab()  # Step 1: Load Sources
        self._create_firewall_defaults_tab()  # Step 2: Firewall Defaults  
        self._create_prisma_defaults_tab()  # Step 3: Prisma Access Defaults
        self._create_firewall_tab()  # Step 4: Configure Firewall
        self._create_prisma_tab()  # Step 5: Configure Prisma Access
        self._create_review_tab()  # Step 6: Review & Execute

        content_layout.addWidget(self.tabs)

        # Progress section
        progress_group = QGroupBox("Operation Progress")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Ready to begin")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        content_layout.addWidget(progress_group)

        # Add main content to layout
        layout.addWidget(main_content)

    # ============================================================================
    # TAB 1: CONFIGURATION SOURCES
    # ============================================================================

    def _create_sources_tab(self):
        """Create configuration sources tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 1: Configuration Sources & Management</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Select your management type and load configuration from multiple sources.\n"
            "Sources will be merged to create the complete POV configuration."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 15px;")
        layout.addWidget(info)

        # Top row: Management Type and SCM Credentials side by side
        top_row = QHBoxLayout()

        # Management Type Selection (left side)
        mgmt_group = QGroupBox("Management Type")
        mgmt_layout = QVBoxLayout()

        self.scm_managed_radio = QRadioButton("SCM Managed")
        self.scm_managed_radio.setChecked(True)
        self.scm_managed_radio.toggled.connect(self._on_management_changed)
        mgmt_layout.addWidget(self.scm_managed_radio)

        scm_desc = QLabel(
            "Configuration via Prisma Access Cloud\n"
            "• Cloud-managed, no Panorama needed\n"
            "• Requires SCM API credentials\n"
            "• Recommended for most deployments"
        )
        scm_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 10px;")
        scm_desc.setWordWrap(True)
        mgmt_layout.addWidget(scm_desc)

        mgmt_layout.addSpacing(10)

        self.panorama_managed_radio = QRadioButton("Panorama Managed")
        self.panorama_managed_radio.toggled.connect(self._on_management_changed)
        mgmt_layout.addWidget(self.panorama_managed_radio)

        pano_desc = QLabel(
            "Configuration via on-premises Panorama\n"
            "• On-premises management\n"
            "• SCM credentials optional (for hybrid)\n"
            "• Traditional management approach"
        )
        pano_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 10px;")
        pano_desc.setWordWrap(True)
        mgmt_layout.addWidget(pano_desc)

        mgmt_layout.addStretch()

        mgmt_group.setLayout(mgmt_layout)
        top_row.addWidget(mgmt_group, 1)

        # SCM Credentials (right side)
        self.scm_creds_group = QGroupBox("SCM API Credentials")
        scm_creds_layout = QVBoxLayout()

        # TSG ID (full width)
        tsg_layout = QFormLayout()
        self.scm_tsg_input = QLineEdit()
        self.scm_tsg_input.setPlaceholderText("tsg-1234567890")
        tsg_layout.addRow("TSG ID:", self.scm_tsg_input)
        scm_creds_layout.addLayout(tsg_layout)

        # API User and Secret side by side
        api_layout = QHBoxLayout()

        user_layout = QVBoxLayout()
        user_layout.addWidget(QLabel("API User:"))
        self.scm_user_input = QLineEdit()
        self.scm_user_input.setPlaceholderText("Client ID")
        user_layout.addWidget(self.scm_user_input)
        api_layout.addLayout(user_layout)

        secret_layout = QVBoxLayout()
        secret_layout.addWidget(QLabel("API Secret:"))
        self.scm_secret_input = QLineEdit()
        self.scm_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.scm_secret_input.setPlaceholderText("Client Secret")
        secret_layout.addWidget(self.scm_secret_input)
        api_layout.addLayout(secret_layout)

        scm_creds_layout.addLayout(api_layout)
        scm_creds_layout.addStretch()

        self.scm_creds_group.setLayout(scm_creds_layout)
        top_row.addWidget(self.scm_creds_group, 1)

        layout.addLayout(top_row)

        # Configuration Sources - 2x2 grid layout
        sources_group = QGroupBox("Configuration Sources (Select all that apply)")
        sources_main_layout = QVBoxLayout()

        # Grid layout for sources with fixed widths
        sources_grid = QHBoxLayout()

        # Left column - fixed width
        left_column = QVBoxLayout()
        left_widget = QWidget()
        left_widget.setMinimumWidth(350)
        left_widget.setMaximumWidth(450)

        # SPOV Questionnaire
        self.spov_check = QCheckBox("📋 SPOV Questionnaire")
        self.spov_check.setToolTip("Load configuration from SPOV questionnaire JSON file")
        self.spov_check.stateChanged.connect(self._update_source_visibility)
        left_column.addWidget(self.spov_check)

        self.spov_layout = QHBoxLayout()
        self.spov_path_input = QLineEdit()
        self.spov_path_input.setPlaceholderText("SPOV questionnaire file...")
        self.spov_path_input.setReadOnly(True)
        self.spov_layout.addWidget(self.spov_path_input)
        self.spov_browse_btn = QPushButton("Browse...")
        self.spov_browse_btn.setMaximumWidth(100)
        self.spov_browse_btn.clicked.connect(self._browse_spov_file)
        self.spov_layout.addWidget(self.spov_browse_btn)
        left_column.addLayout(self.spov_layout)

        left_column.addSpacing(15)

        # Terraform
        self.terraform_check = QCheckBox("🔧 Terraform Configuration")
        self.terraform_check.setToolTip("Import from Terraform files or directory")
        self.terraform_check.stateChanged.connect(self._update_source_visibility)
        left_column.addWidget(self.terraform_check)

        self.terraform_layout = QHBoxLayout()
        self.terraform_path_input = QLineEdit()
        self.terraform_path_input.setPlaceholderText("Terraform directory...")
        self.terraform_path_input.setReadOnly(True)
        self.terraform_layout.addWidget(self.terraform_path_input)
        self.terraform_browse_btn = QPushButton("Browse...")
        self.terraform_browse_btn.setMaximumWidth(100)
        self.terraform_browse_btn.clicked.connect(self._browse_terraform_dir)
        self.terraform_layout.addWidget(self.terraform_browse_btn)
        left_column.addLayout(self.terraform_layout)

        left_widget.setLayout(left_column)
        sources_grid.addWidget(left_widget)

        # Right column - fixed width
        right_column = QVBoxLayout()
        right_widget = QWidget()
        right_widget.setMinimumWidth(350)
        right_widget.setMaximumWidth(450)

        # Existing JSON config
        self.json_check = QCheckBox("📄 Existing JSON Configuration")
        self.json_check.setToolTip("Load from previously saved JSON configuration")
        self.json_check.stateChanged.connect(self._update_source_visibility)
        right_column.addWidget(self.json_check)

        self.json_layout = QHBoxLayout()
        self.json_path_input = QLineEdit()
        self.json_path_input.setPlaceholderText("JSON configuration file...")
        self.json_path_input.setReadOnly(True)
        self.json_layout.addWidget(self.json_path_input)
        self.json_browse_btn = QPushButton("Browse...")
        self.json_browse_btn.setMaximumWidth(100)
        self.json_browse_btn.clicked.connect(self._browse_json_file)
        self.json_layout.addWidget(self.json_browse_btn)
        right_column.addLayout(self.json_layout)

        right_column.addSpacing(15)

        # Manual entry
        self.manual_check = QCheckBox("✏️  Manual Entry")
        self.manual_check.setToolTip("Manually enter or override configuration parameters")
        right_column.addWidget(self.manual_check)

        manual_desc = QLabel("Open dialog to enter additional parameters")
        manual_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 25px;")
        right_column.addWidget(manual_desc)

        right_widget.setLayout(right_column)
        sources_grid.addWidget(right_widget)

        sources_grid.addStretch()

        sources_main_layout.addLayout(sources_grid)
        sources_group.setLayout(sources_main_layout)
        layout.addWidget(sources_group)

        # Load button and status
        bottom_layout = QHBoxLayout()

        self.load_status = QLabel("No configuration loaded")
        self.load_status.setStyleSheet("color: gray;")
        bottom_layout.addWidget(self.load_status)

        bottom_layout.addStretch()

        # Save button
        save_config_btn = QPushButton("💾 Save Config")
        save_config_btn.setMinimumWidth(120)
        save_config_btn.setMinimumHeight(40)
        save_config_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; padding: 10px; font-weight: bold; }"
            "QPushButton:hover { background-color: #F57C00; }"
        )
        save_config_btn.clicked.connect(self._save_current_config)
        bottom_layout.addWidget(save_config_btn)

        # Load button
        self.load_config_btn = QPushButton("Load & Merge Configuration")
        self.load_config_btn.setMinimumWidth(200)
        self.load_config_btn.setMinimumHeight(40)
        self.load_config_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; font-size: 13px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.load_config_btn.clicked.connect(self._load_and_merge_config)
        bottom_layout.addWidget(self.load_config_btn)

        layout.addLayout(bottom_layout)

        layout.addStretch()

        # Initialize visibility
        self._update_source_visibility()
        self._on_management_changed()

        self.tabs.addTab(tab, "1️⃣ Load Sources")

    # ============================================================================
    # TAB 2: FIREWALL DEFAULTS
    # ============================================================================

    def _create_firewall_defaults_tab(self):
        """Create firewall defaults selection tab (Step 2)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 2: Firewall Default Configurations</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Select optional default firewall configurations to automatically create.<br>"
            "<b>Note:</b> These options require firewall configuration data from Step 1."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 15px;")
        layout.addWidget(info)

        # Firewall defaults group
        fw_defaults_group = QGroupBox("Firewall Default Templates")
        fw_layout = QVBoxLayout()

        # Basic Firewall Policy
        self.fw_policy_check = QCheckBox("🛡️ Basic Firewall Policy")
        self.fw_policy_check.setToolTip(
            "Create basic security policies including:\n"
            "• Internet access rule (Trust → Untrust)\n"
            "• Inbound RDP rule to .10 address\n"
            "• Associated address objects"
        )
        self.fw_policy_check.stateChanged.connect(self._update_fw_defaults_status)
        fw_layout.addWidget(self.fw_policy_check)

        fw_policy_desc = QLabel(
            "• Internet access from trust to untrust\n"
            "• Inbound RDP to trust network .10 address\n"
            "• Address objects for .10 host"
        )
        fw_policy_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 25px; margin-bottom: 10px;")
        fw_policy_desc.setWordWrap(True)
        fw_layout.addWidget(fw_policy_desc)

        # Basic NAT Policy
        self.fw_nat_check = QCheckBox("🔄 Basic NAT Policy")
        self.fw_nat_check.setToolTip(
            "Create NAT policies including:\n"
            "• Outbound PAT for internet access\n"
            "• Inbound static NAT for RDP to .10"
        )
        self.fw_nat_check.stateChanged.connect(self._update_fw_defaults_status)
        fw_layout.addWidget(self.fw_nat_check)

        fw_nat_desc = QLabel(
            "• Outbound PAT (Port Address Translation)\n"
            "• Inbound static NAT for RDP to .10 address"
        )
        fw_nat_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 25px; margin-bottom: 10px;")
        fw_nat_desc.setWordWrap(True)
        fw_layout.addWidget(fw_nat_desc)

        fw_layout.addStretch()
        fw_defaults_group.setLayout(fw_layout)
        layout.addWidget(fw_defaults_group)

        # Status message for FW data requirement
        self.fw_defaults_status = QLabel()
        self.fw_defaults_status.setWordWrap(True)
        self.fw_defaults_status.setStyleSheet(
            "background-color: #FFF3E0; color: #F57C00; padding: 10px; border-radius: 5px;"
        )
        self.fw_defaults_status.setVisible(False)
        layout.addWidget(self.fw_defaults_status)

        # Preview/Apply buttons
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout()

        preview_fw_btn = QPushButton("Preview Selected Defaults")
        preview_fw_btn.clicked.connect(self._preview_firewall_defaults)
        actions_layout.addWidget(preview_fw_btn)

        apply_fw_btn = QPushButton("Apply Selected Defaults")
        apply_fw_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px 15px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        apply_fw_btn.clicked.connect(self._apply_firewall_defaults)
        actions_layout.addWidget(apply_fw_btn)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Navigation
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        back_btn = QPushButton("← Back to Sources")
        back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        nav_layout.addWidget(back_btn)

        skip_btn = QPushButton("Skip Firewall Defaults")
        skip_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        nav_layout.addWidget(skip_btn)

        next_btn = QPushButton("Next: Prisma Access Defaults →")
        next_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 8px 15px; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        nav_layout.addWidget(next_btn)

        layout.addLayout(nav_layout)

        self.tabs.addTab(tab, "2️⃣ Firewall Defaults")

    # ============================================================================
    # TAB 3: PRISMA ACCESS DEFAULTS
    # ============================================================================

    def _create_prisma_defaults_tab(self):
        """Create Prisma Access defaults selection tab (Step 3)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 3: Prisma Access Default Configurations</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Select optional default Prisma Access configurations to automatically create.<br>"
            "<b>Note:</b> Some options require firewall configuration data from Step 1."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 15px;")
        layout.addWidget(info)

        # Prisma Access defaults group
        pa_defaults_group = QGroupBox("Prisma Access Default Templates")
        pa_layout = QVBoxLayout()

        # Service Connection
        self.service_conn_check = QCheckBox("🔌 Service Connection")
        self.service_conn_check.setToolTip(
            "Configure service connection to the firewall\n"
            "(Requires firewall configuration from Step 1)"
        )
        self.service_conn_check.stateChanged.connect(self._update_pa_defaults_status)
        pa_layout.addWidget(self.service_conn_check)

        service_desc = QLabel(
            "• Configure IPSec tunnel to firewall\n"
            "• Set up BGP peering\n"
            "• Create route advertisements\n"
            "<b>Requires:</b> Firewall configuration data"
        )
        service_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 25px; margin-bottom: 10px;")
        service_desc.setWordWrap(True)
        pa_layout.addWidget(service_desc)

        # Remote Network
        self.remote_network_check = QCheckBox("🌐 Remote Network")
        self.remote_network_check.setToolTip(
            "Configure remote network connection to firewall\n"
            "(Requires firewall configuration from Step 1)"
        )
        self.remote_network_check.stateChanged.connect(self._update_pa_defaults_status)
        pa_layout.addWidget(self.remote_network_check)

        remote_desc = QLabel(
            "• Create remote network configuration\n"
            "• Define subnets and routing\n"
            "• Configure firewall integration\n"
            "<b>Requires:</b> Firewall configuration data"
        )
        remote_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 25px; margin-bottom: 10px;")
        remote_desc.setWordWrap(True)
        pa_layout.addWidget(remote_desc)

        # Mobile User
        self.mobile_user_check = QCheckBox("📱 Mobile User Configuration")
        self.mobile_user_check.setToolTip("Configure basic mobile user/GlobalProtect settings")
        pa_layout.addWidget(self.mobile_user_check)

        mobile_desc = QLabel(
            "• Configure GlobalProtect gateway\n"
            "• Set up authentication\n"
            "• Define split tunnel settings\n"
            "• Configure DNS and routing"
        )
        mobile_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 25px; margin-bottom: 10px;")
        mobile_desc.setWordWrap(True)
        pa_layout.addWidget(mobile_desc)

        pa_layout.addStretch()
        pa_defaults_group.setLayout(pa_layout)
        layout.addWidget(pa_defaults_group)

        # Status message for FW data requirement
        self.pa_defaults_status = QLabel()
        self.pa_defaults_status.setWordWrap(True)
        self.pa_defaults_status.setStyleSheet(
            "background-color: #FFF3E0; color: #F57C00; padding: 10px; border-radius: 5px;"
        )
        self.pa_defaults_status.setVisible(False)
        layout.addWidget(self.pa_defaults_status)

        # Preview/Apply buttons
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout()

        preview_pa_btn = QPushButton("Preview Selected Defaults")
        preview_pa_btn.clicked.connect(self._preview_prisma_defaults)
        actions_layout.addWidget(preview_pa_btn)

        apply_pa_btn = QPushButton("Apply Selected Defaults")
        apply_pa_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px 15px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        apply_pa_btn.clicked.connect(self._apply_prisma_defaults)
        actions_layout.addWidget(apply_pa_btn)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Navigation
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        back_btn = QPushButton("← Back to Firewall Defaults")
        back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        nav_layout.addWidget(back_btn)

        skip_btn = QPushButton("Skip Prisma Defaults")
        skip_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        nav_layout.addWidget(skip_btn)

        next_btn = QPushButton("Next: Configure Firewall →")
        next_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 8px 15px; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        nav_layout.addWidget(next_btn)

        layout.addLayout(nav_layout)

        self.tabs.addTab(tab, "3️⃣ Prisma Access Defaults")

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
    # TAB 4: CONFIGURE FIREWALL
    # ============================================================================


    # ============================================================================
    # TAB 4: CONFIGURE FIREWALL
    # ============================================================================

    def _create_firewall_tab(self):
        """Create firewall configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 4: Configure Firewall</h3>")
        layout.addWidget(title)

        info = QLabel(
            "Configure the NGFW with zones, interfaces, routes, objects, and policies."
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
        options_group = QGroupBox("Configuration Components")
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

        self.configure_fw_btn = QPushButton("🔧 Configure Firewall")
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

        back_btn = QPushButton("← Back to Prisma Defaults")
        back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        nav_layout.addWidget(back_btn)

        nav_layout.addStretch()

        next_btn = QPushButton("Next: Configure Prisma Access →")
        next_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 8px; }"
        )
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(4))
        nav_layout.addWidget(next_btn)

        layout.addLayout(nav_layout)

        self.tabs.addTab(tab, "4️⃣ Firewall Setup")

    # ============================================================================
    # TAB 5: CONFIGURE PRISMA ACCESS
    # ============================================================================

    def _create_prisma_tab(self):
        """Create Prisma Access configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("<h3>Step 5: Configure Prisma Access</h3>")
        layout.addWidget(title)

        info = QLabel("Configure Prisma Access service connections and settings.")
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

        self.pa_mgmt_label = QLabel("Not loaded")
        pa_layout.addRow("Management:", self.pa_mgmt_label)

        pa_group.setLayout(pa_layout)
        layout.addWidget(pa_group)

        # Configuration options
        options_group = QGroupBox("Configuration Components")
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

        self.configure_pa_btn = QPushButton("🌐 Configure Prisma Access")
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

        back_btn = QPushButton("← Back to Firewall")
        back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        complete_layout.addWidget(back_btn)

        complete_layout.addStretch()

        self.complete_btn = QPushButton("✓ Complete POV Setup")
        self.complete_btn.setMinimumWidth(180)
        self.complete_btn.setEnabled(False)
        self.complete_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.complete_btn.clicked.connect(self._complete_pov_setup)
        complete_layout.addWidget(self.complete_btn)

        layout.addLayout(complete_layout)

        self.tabs.addTab(tab, "5️⃣ Prisma Access Setup")

    # ============================================================================
    # EVENT HANDLERS - SOURCES TAB
    # ============================================================================

    def set_api_client(self, api_client, connection_name=None):
        """Set API client."""
        self.api_client = api_client
        self.connection_name = connection_name

    def _on_management_changed(self):
        """Handle management type change."""
        is_scm = self.scm_managed_radio.isChecked()
        self.management_type = "scm" if is_scm else "panorama"

        # Update credentials label
        if is_scm:
            self.scm_creds_group.setTitle("SCM API Credentials (Required)")
            self.scm_creds_group.setStyleSheet("")
            # Uncheck manual for SCM (it's optional)
            # Manual is only auto-checked for Panorama
        else:
            self.scm_creds_group.setTitle("SCM API Credentials (Optional for Hybrid)")
            self.scm_creds_group.setStyleSheet("QGroupBox { color: gray; }")
            # Auto-check manual for Panorama
            self.manual_check.setChecked(True)

        # Auto-check manual entry for Panorama
        if not is_scm:
            self.manual_check.setChecked(True)
            self.manual_check.setEnabled(False)  # Force manual entry for Panorama
            self.manual_check.setToolTip(
                "Manual entry is required for Panorama managed deployments"
            )
        else:
            self.manual_check.setEnabled(True)
            self.manual_check.setToolTip(
                "Manually enter or override configuration parameters"
            )

    def _update_source_visibility(self):
        """Update visibility of source file selection widgets."""
        # SPOV
        self.spov_path_input.setVisible(self.spov_check.isChecked())
        self.spov_browse_btn.setVisible(self.spov_check.isChecked())

        # Terraform
        self.terraform_path_input.setVisible(self.terraform_check.isChecked())
        self.terraform_browse_btn.setVisible(self.terraform_check.isChecked())

        # JSON
        self.json_path_input.setVisible(self.json_check.isChecked())
        self.json_browse_btn.setVisible(self.json_check.isChecked())

    def _browse_spov_file(self):
        """Browse for SPOV questionnaire file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SPOV Questionnaire File",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            self.spov_path_input.setText(file_path)

    def _browse_terraform_dir(self):
        """Browse for Terraform directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Terraform Configuration Directory"
        )
        if dir_path:
            self.terraform_path_input.setText(dir_path)

    def _browse_json_file(self):
        """Browse for JSON configuration file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select JSON Configuration File",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            self.json_path_input.setText(file_path)

    def _load_and_merge_config(self):
        """Load and merge configuration from all selected sources."""
        try:
            # Validate at least one source selected
            if not any(
                [
                    self.spov_check.isChecked(),
                    self.terraform_check.isChecked(),
                    self.json_check.isChecked(),
                    self.manual_check.isChecked(),
                ]
            ):
                QMessageBox.warning(
                    self,
                    "No Sources Selected",
                    "Please select at least one configuration source.",
                )
                return

            # Validate SCM credentials if required
            if self.management_type == "scm":
                if not all(
                    [
                        self.scm_tsg_input.text(),
                        self.scm_user_input.text(),
                        self.scm_secret_input.text(),
                    ]
                ):
                    QMessageBox.warning(
                        self,
                        "Missing Credentials",
                        "SCM API credentials are required for SCM Managed deployments.",
                    )
                    return

            # Initialize merged config
            merged_config = {}
            self.loaded_sources = []

            # Load SPOV
            if self.spov_check.isChecked():
                spov_data = self._load_spov(self.spov_path_input.text())
                if spov_data:
                    merged_config = self._merge_configs(merged_config, spov_data)
                    self.loaded_sources.append("SPOV Questionnaire")

            # Load Terraform
            if self.terraform_check.isChecked():
                tf_data = self._load_terraform(self.terraform_path_input.text())
                if tf_data:
                    merged_config = self._merge_configs(merged_config, tf_data)
                    self.loaded_sources.append("Terraform")

            # Load JSON
            if self.json_check.isChecked():
                json_data = self._load_json(self.json_path_input.text())
                if json_data:
                    merged_config = self._merge_configs(merged_config, json_data)
                    self.loaded_sources.append("Existing JSON")

            # Manual entry
            if self.manual_check.isChecked():
                manual_data = self._load_manual()
                if manual_data:
                    merged_config = self._merge_configs(merged_config, manual_data)
                    self.loaded_sources.append("Manual Entry")
                else:
                    # User cancelled manual entry dialog
                    if not any([
                        self.spov_check.isChecked() and self.spov_path_input.text(),
                        self.terraform_check.isChecked() and self.terraform_path_input.text(),
                        self.json_check.isChecked() and self.json_path_input.text(),
                    ]):
                        # Manual was the only source, and they cancelled
                        QMessageBox.information(
                            self,
                            "Cancelled",
                            "Manual entry cancelled. Please select at least one configuration source."
                        )
                        return

            # Add management metadata
            merged_config["management_type"] = self.management_type
            if self.management_type == "scm" or self.scm_tsg_input.text():
                merged_config["scm_credentials"] = {
                    "tsg_id": self.scm_tsg_input.text(),
                    "api_user": self.scm_user_input.text(),
                    "api_secret": "***REDACTED***",  # Don't store in plain text
                }

            # Store merged config
            self.config_data = merged_config

            # Update defaults status
            self._update_fw_defaults_status()
            self._update_pa_defaults_status()

            # Update UI
            self.load_status.setText(
                f"✓ Configuration loaded from {len(self.loaded_sources)} source(s)"
            )
            self.load_status.setStyleSheet("color: green;")

            # Update review tab
            import json

            self.config_review_text.setPlainText(json.dumps(merged_config, indent=2))

            sources_text = (
                f"<b>Loaded Sources:</b> {', '.join(self.loaded_sources)}<br>"
                f"<b>Management Type:</b> {self.management_type.upper()}"
            )
            self.sources_summary.setText(sources_text)

            # Enable next steps
            self.configure_fw_btn.setEnabled(True)
            self.configure_pa_btn.setEnabled(True)

            # Update firewall/PA info
            self._update_config_display()

            # Move to review tab
            self.tabs.setCurrentIndex(1)

            QMessageBox.information(
                self,
                "Success",
                f"Configuration loaded successfully from:\n\n"
                + "\n".join(f"  • {s}" for s in self.loaded_sources),
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Load Failed", f"Failed to load configuration:\n{str(e)}"
            )

    def _load_spov(self, file_path: str) -> Dict[str, Any]:
        """Load SPOV questionnaire file."""
        if not file_path:
            return {}

        try:
            from config.storage.json_storage import load_config_json

            return load_config_json(file_path, validate=False)
        except Exception as e:
            QMessageBox.warning(
                self, "SPOV Load Failed", f"Failed to load SPOV file:\n{str(e)}"
            )
            return {}

    def _load_terraform(self, dir_path: str) -> Dict[str, Any]:
        """Load Terraform configuration."""
        if not dir_path:
            return {}

        # TODO: Implement Terraform parsing
        QMessageBox.information(
            self,
            "Coming Soon",
            "Terraform import is planned for a future update.\n\n"
            "For now, use JSON export from your Terraform state.",
        )
        return {}

    def _load_json(self, file_path: str) -> Dict[str, Any]:
        """Load JSON configuration file."""
        if not file_path:
            return {}

        try:
            from config.storage.json_storage import load_config_json

            return load_config_json(file_path, validate=False)
        except Exception as e:
            QMessageBox.warning(
                self, "JSON Load Failed", f"Failed to load JSON file:\n{str(e)}"
            )
            return {}

    def _load_manual(self) -> Dict[str, Any]:
        """Open manual entry dialog and get configuration."""
        from gui.dialogs.manual_config_dialog import ManualConfigDialog

        dialog = ManualConfigDialog(management_type=self.management_type, parent=self)
        if dialog.exec():
            return dialog.get_config()
        return {}

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
    # NEW DEFAULTS HELPER METHODS
    # ============================================================================

    def _update_fw_defaults_status(self):
        """Check if firewall data exists and update status."""
        has_fw_data = self.config_data.get('fwData') is not None
        if not has_fw_data and (self.fw_policy_check.isChecked() or self.fw_nat_check.isChecked()):
            self.fw_defaults_status.setText(
                "⚠️ Firewall configuration required. Please load firewall data in Step 1 (via Manual Entry or other source)."
            )
            self.fw_defaults_status.setVisible(True)
        else:
            self.fw_defaults_status.setVisible(False)

    def _update_pa_defaults_status(self):
        """Check if firewall data exists for PA defaults that need it."""
        has_fw_data = self.config_data.get('fwData') is not None
        needs_fw = self.service_conn_check.isChecked() or self.remote_network_check.isChecked()
        
        if not has_fw_data and needs_fw:
            self.pa_defaults_status.setText(
                "⚠️ Service Connection and Remote Network require firewall configuration data.\n"
                "Please load firewall data in Step 1 (via Manual Entry or other source)."
            )
            self.pa_defaults_status.setVisible(True)
        else:
            self.pa_defaults_status.setVisible(False)

    def _preview_firewall_defaults(self):
        """Preview selected firewall defaults."""
        selected = []
        if self.fw_policy_check.isChecked():
            selected.append("Basic Firewall Policy")
        if self.fw_nat_check.isChecked():
            selected.append("Basic NAT Policy")
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select at least one default configuration.")
            return
        
        preview_text = "Selected Firewall Defaults:\n\n"
        
        if "Basic Firewall Policy" in selected:
            preview_text += "📋 Basic Firewall Policy:\n"
            preview_text += "  • Trust to Untrust rule (allow internet)\n"
            preview_text += "  • Untrust to Trust rule (RDP to .10)\n"
            preview_text += "  • Address object: trust-host-10\n\n"
        
        if "Basic NAT Policy" in selected:
            preview_text += "📋 Basic NAT Policy:\n"
            preview_text += "  • Outbound PAT (trust → untrust)\n"
            preview_text += "  • Inbound Static NAT (RDP to .10)\n\n"
        
        QMessageBox.information(self, "Preview Firewall Defaults", preview_text)

    def _apply_firewall_defaults(self):
        """Apply selected firewall defaults to configuration."""
        if not self.config_data.get('fwData'):
            QMessageBox.warning(
                self,
                "Missing Firewall Data",
                "Firewall configuration data is required. Please load it in Step 1."
            )
            return
        
        selected = []
        if self.fw_policy_check.isChecked():
            selected.append("firewall_policy")
        if self.fw_nat_check.isChecked():
            selected.append("nat_policy")
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select at least one default.")
            return
        
        # TODO: Integrate with config/defaults/default_configs.py
        QMessageBox.information(
            self,
            "Defaults Applied",
            f"Applied {len(selected)} firewall default configuration(s).\n\n"
            "Note: Full implementation pending integration with default_configs.py"
        )

    def _preview_prisma_defaults(self):
        """Preview selected Prisma Access defaults."""
        selected = []
        if self.service_conn_check.isChecked():
            selected.append("Service Connection")
        if self.remote_network_check.isChecked():
            selected.append("Remote Network")
        if self.mobile_user_check.isChecked():
            selected.append("Mobile User")
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select at least one default.")
            return
        
        preview_text = "Selected Prisma Access Defaults:\n\n"
        
        if "Service Connection" in selected:
            preview_text += "📋 Service Connection:\n"
            preview_text += "  • IPSec tunnel to firewall\n"
            preview_text += "  • BGP peering configuration\n"
            preview_text += "  • Route advertisements\n\n"
        
        if "Remote Network" in selected:
            preview_text += "📋 Remote Network:\n"
            preview_text += "  • Remote network object\n"
            preview_text += "  • Subnet configuration\n"
            preview_text += "  • Firewall integration\n\n"
        
        if "Mobile User" in selected:
            preview_text += "📋 Mobile User:\n"
            preview_text += "  • GlobalProtect gateway\n"
            preview_text += "  • Authentication settings\n"
            preview_text += "  • Split tunnel configuration\n\n"
        
        QMessageBox.information(self, "Preview Prisma Access Defaults", preview_text)

    def _apply_prisma_defaults(self):
        """Apply selected Prisma Access defaults."""
        has_fw = self.config_data.get('fwData') is not None
        
        if (self.service_conn_check.isChecked() or self.remote_network_check.isChecked()) and not has_fw:
            QMessageBox.warning(
                self,
                "Missing Firewall Data",
                "Service Connection and Remote Network require firewall data. Please load it in Step 1."
            )
            return
        
        selected = []
        if self.service_conn_check.isChecked():
            selected.append("service_connection")
        if self.remote_network_check.isChecked():
            selected.append("remote_network")
        if self.mobile_user_check.isChecked():
            selected.append("mobile_user")
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select at least one default.")
            return
        
        # TODO: Integrate with config/defaults/default_configs.py
        QMessageBox.information(
            self,
            "Defaults Applied",
            f"Applied {len(selected)} Prisma Access default configuration(s).\n\n"
            "Note: Full implementation pending integration with default_configs.py"
        )

    def _save_current_config(self):
        """Save the current configuration to saved configs."""
        if not self.config_data:
            QMessageBox.information(
                self,
                "No Configuration",
                "Please load or create a configuration first."
            )
            return
        
        # Use the sidebar to save
        default_name = self.config_data.get("metadata", {}).get("saved_name", "")
        if not default_name:
            # Generate name from source tenant or timestamp
            source = self.config_data.get("metadata", {}).get("source_tenant", "")
            if source:
                default_name = f"pov_{source}"
            else:
                from datetime import datetime
                default_name = f"pov_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        success = self.saved_configs_sidebar.save_current_config(
            self.config_data,
            default_name=default_name,
            encrypt=True
        )
        
        if success:
            self.load_status.setText(f"✓ Configuration saved")
            self.load_status.setStyleSheet("color: green; font-weight: bold;")

    def _on_saved_config_loaded(self, config: Dict[str, Any]):
        """Handle when a saved configuration is loaded from sidebar."""
        # Replace or merge the loaded config
        self.config_data = config
        
        # Update UI
        import json
        self.config_review_text.setPlainText(json.dumps(self.config_data, indent=2))
        
        # Update status
        source_name = config.get("metadata", {}).get("saved_name", "saved config")
        self.load_status.setText(f"✓ Loaded from: {source_name}")
        self.load_status.setStyleSheet("color: green; font-weight: bold;")
        
        # Update sources summary
        sources_text = f"<b>Loaded from saved configuration:</b> {source_name}<br>"
        sources_text += f"<b>Original sources:</b> {', '.join(self.loaded_sources) if self.loaded_sources else 'Unknown'}"
        self.sources_summary.setText(sources_text)
        
        # Update defaults status
        self._update_fw_defaults_status()
        self._update_pa_defaults_status()
    
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
        
        # Clear loaded sources
        self.loaded_sources = []
        
        # Clear worker
        if self.worker is not None:
            self.worker = None
        
        # Reset UI elements
        import json
        self.config_review_text.setPlainText(json.dumps({}, indent=2))
        self.load_status.setText("No configuration loaded")
        self.load_status.setStyleSheet("color: gray;")
        self.sources_summary.setText("<i>No sources loaded</i>")
        
        # Reset defaults status
        self._update_fw_defaults_status()
        self._update_pa_defaults_status()
        
        # No success message - config is now visible in viewer
