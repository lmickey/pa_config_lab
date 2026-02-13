"""
DoR (Definition of Requirements) Workflow GUI.

Provides a 4-tab workflow for generating DoR data:
1. Tenant Connection + Pull - Connect and pull config for analysis
2. Environment Questions - Business context, delivery model
3. Technical Questions - Tenant info, MU/RN/ZTNA details, detection/response
4. Summary + Export - Review all answers, preview/save JSON
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QScrollArea,
    QProgressBar,
    QFrame,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.widgets import TenantSelectorWidget
from gui.workflows.dor_schema import (
    create_empty_dor_schema,
    generate_dor_from_config,
    merge_manual_answers,
    validate_dor_completeness,
    DOR_FEATURE_MAP,
)

logger = logging.getLogger(__name__)

# Human-readable mappings for license app_id and license_type values
LICENSE_APP_NAMES = {
    'prisma_access_edition': 'Prisma Access',
    'logging_service': 'Logging Service',
    'customer_success': 'Customer Success',
    'add_adem_aiops': 'ADEM AIOps',
    'add_traffic_mirroring': 'Traffic Mirroring',
    'add_app_accl': 'App Acceleration',
    'dlp': 'Data Loss Prevention (DLP)',
    'aperture': 'SaaS Security (Aperture)',
    'zingbox': 'IoT Security',
    'strata_cloud_manager': 'Strata Cloud Manager',
    'cortex_data_lake': 'Cortex Data Lake',
    'globalprotect': 'GlobalProtect',
    'wildfire': 'WildFire',
    'dns_security': 'DNS Security',
    'sd_wan': 'SD-WAN',
    'ztna_connector': 'ZTNA Connector',
    'autonomous_dem': 'Autonomous DEM',
}

LICENSE_TYPE_NAMES = {
    # Mobile Users
    'SE-LCL-MU': 'Mobile Users',
    'SEMUADEMAIOPSPAE': 'MU ADEM AIOps',
    'SEMUSAASINLINEPAE': 'MU SaaS Inline',
    # Remote Networks
    'SE-LCL-RN': 'Remote Networks',
    'SERNADEMAIOPSPAE': 'RN ADEM AIOps',
    'SERNSAASINLINEPAE': 'RN SaaS Inline',
    # Add-ons
    'SETRAFFICREPLICA': 'Traffic Replication',
    'EVALACCESSAPPACCLPAE': 'App Acceleration (Eval)',
    'SE-PA-DLP': 'DLP',
    'SESAASAPI': 'SaaS API',
    'SESAASAPIDLP': 'SaaS API DLP',
    'SESAASSSPM': 'SaaS SSPM',
    'SEIOTPAE': 'IoT Security',
    'SESITESAASINLPAE': 'Sites SaaS Inline',
    # Customer Success
    'PA-SUCCESS-STD': 'Standard Support',
    'PA-SUCCESS-PREM': 'Premium Support',
    # Other
    'SE License': 'SE License',
}


class DorWorkflowWidget(QWidget):
    """Widget for the DoR (Definition of Requirements) workflow."""

    connection_changed = pyqtSignal(object, str, str)  # api_client, tenant_name, source_type

    def __init__(self, parent=None):
        """Initialize DoR workflow widget."""
        super().__init__(parent)

        self.api_client = None
        self.connection_name = None
        self.pulled_config = None  # Configuration object from pull
        self.dor_data = create_empty_dor_schema()
        self.manual_answers = {}
        self._pull_worker = None
        self._config_file_path = None  # Path to saved config file (for state persistence)
        self._license_info = None  # License data from pull
        self._auth_info = None  # Auth/CIE data from pull
        self._mu_info = None  # Mobile Users config data from pull

        self._init_ui()

        # Check for saved states on startup
        self._check_saved_states()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tabs
        self.tabs = QTabWidget()

        self.tabs.addTab(self._create_pull_tab(), "1. Tenant + Pull")
        self.tabs.addTab(self._create_environment_tab(), "2. Environment")
        self.tabs.addTab(self._create_technical_tab(), "3. Technical")
        self.tabs.addTab(self._create_summary_tab(), "4. Summary + Export")

        layout.addWidget(self.tabs)

    # ========================================================================
    # Tab 1: Tenant Connection + Pull
    # ========================================================================

    def _create_pull_tab(self) -> QWidget:
        """Create the tenant connection and pull tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Top row: Tenant selector on left, Resume/Load buttons on right
        top_row = QHBoxLayout()

        # Tenant selector (left side, takes available space)
        self.tenant_selector = TenantSelectorWidget(
            title="Source Tenant",
            label="Select tenant:",
        )
        self.tenant_selector.connection_changed.connect(self._on_connection_changed)
        top_row.addWidget(self.tenant_selector, stretch=1)

        # Resume + Load buttons (right side, stacked vertically)
        side_btn_layout = QVBoxLayout()
        side_btn_layout.addStretch()

        self.resume_btn = QPushButton("Resume Saved DoR...")
        self.resume_btn.setMinimumHeight(36)
        self.resume_btn.setMinimumWidth(180)
        self.resume_btn.setStyleSheet(
            "QPushButton { background-color: #5C6BC0; color: white; font-weight: bold; "
            "border-radius: 5px; padding: 8px 16px; border: 1px solid #3949AB; "
            "border-bottom: 3px solid #283593; }"
            "QPushButton:hover { background-color: #7986CB; }"
            "QPushButton:disabled { background-color: #ccc; color: #666; border: 1px solid #999; }"
        )
        self.resume_btn.clicked.connect(self._show_resume_dialog)
        side_btn_layout.addWidget(self.resume_btn)

        self.load_file_btn = QPushButton("Load Saved Config...")
        self.load_file_btn.setMinimumHeight(36)
        self.load_file_btn.setMinimumWidth(180)
        self.load_file_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; font-weight: bold; "
            "border-radius: 5px; padding: 8px 16px; border: 1px solid #F57C00; "
            "border-bottom: 3px solid #E65100; }"
            "QPushButton:hover { background-color: #FB8C00; }"
            "QPushButton:disabled { background-color: #ccc; color: #666; border: 1px solid #999; }"
        )
        self.load_file_btn.clicked.connect(self._load_config_from_file)
        side_btn_layout.addWidget(self.load_file_btn)

        side_btn_layout.addStretch()
        top_row.addLayout(side_btn_layout)
        layout.addLayout(top_row)

        # Enable buttons only if their directories have files
        self._update_side_button_states()

        # Populate tenants
        try:
            from config.tenant_manager import TenantManager
            tenants = TenantManager().list_tenants()
            for tenant in tenants:
                name = tenant.get('name', 'Unknown')
                self.tenant_selector.tenant_combo.addItem(name, tenant)
        except Exception:
            pass

        # Pull controls
        pull_group = QGroupBox("Pull Configuration for Analysis")
        pull_layout = QVBoxLayout()

        pull_desc = QLabel(
            "Pull the tenant's configuration to automatically answer DoR questions about "
            "security profiles, rules, infrastructure, and feature usage."
        )
        pull_desc.setWordWrap(True)
        pull_desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        pull_layout.addWidget(pull_desc)

        btn_row = QHBoxLayout()
        self.pull_btn = QPushButton("Pull Configuration")
        self.pull_btn.setEnabled(False)
        self.pull_btn.setMinimumHeight(40)
        self.pull_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
            "border-radius: 5px; padding: 8px 20px; border: 1px solid #388E3C; "
            "border-bottom: 3px solid #2E7D32; }"
            "QPushButton:hover { background-color: #43A047; }"
            "QPushButton:disabled { background-color: #ccc; color: #666; border: 1px solid #999; }"
        )
        self.pull_btn.clicked.connect(self._start_pull)
        btn_row.addWidget(self.pull_btn)

        self.cancel_pull_btn = QPushButton("Cancel")
        self.cancel_pull_btn.setMinimumHeight(40)
        self.cancel_pull_btn.setVisible(False)
        self.cancel_pull_btn.clicked.connect(self._cancel_pull)
        btn_row.addWidget(self.cancel_pull_btn)

        btn_row.addStretch()
        pull_layout.addLayout(btn_row)

        # Progress
        self.pull_progress = QProgressBar()
        self.pull_progress.setVisible(False)
        pull_layout.addWidget(self.pull_progress)

        self.pull_status = QLabel("")
        self.pull_status.setWordWrap(True)
        pull_layout.addWidget(self.pull_status)

        pull_group.setLayout(pull_layout)
        layout.addWidget(pull_group)

        # Config analysis results
        self.analysis_group = QGroupBox("Configuration Analysis")
        self.analysis_group.setVisible(False)
        analysis_layout = QVBoxLayout()

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMaximumHeight(300)
        analysis_layout.addWidget(self.analysis_text)

        self.analysis_group.setLayout(analysis_layout)
        layout.addWidget(self.analysis_group)

        # Next button
        next_row = QHBoxLayout()
        next_row.addStretch()
        next_btn = QPushButton("Next: Environment Questions >>")
        next_btn.setMinimumHeight(36)
        next_btn.clicked.connect(lambda: self._next_tab(1))
        next_row.addWidget(next_btn)
        layout.addLayout(next_row)

        layout.addStretch()
        return tab

    def _update_side_button_states(self):
        """Enable Resume/Load buttons only if their directories have files."""
        import os

        # Resume: check for saved DoR state files
        state_dir = self._get_state_dir()
        has_states = any(state_dir.glob("dor_state_*.json")) if state_dir.exists() else False
        self.resume_btn.setEnabled(has_states)
        if not has_states:
            self.resume_btn.setToolTip("No saved DoR questionnaires found")
        else:
            self.resume_btn.setToolTip("Resume a previously saved DoR questionnaire")

        # Load from file: check for saved config files
        has_configs = False
        try:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            saved_path = os.path.join(base_path, "saved")
            if os.path.isdir(saved_path):
                has_configs = any(
                    f.endswith(('.pac', '.json'))
                    for f in os.listdir(saved_path)
                )
        except Exception:
            pass
        self.load_file_btn.setEnabled(has_configs)
        if not has_configs:
            self.load_file_btn.setToolTip("No saved configuration files found in saved/ directory")
        else:
            self.load_file_btn.setToolTip("Load a saved configuration file for DoR analysis")

    def _on_connection_changed(self, api_client, tenant_name: str):
        """Handle tenant connection change."""
        self.api_client = api_client
        self.connection_name = tenant_name
        self.pull_btn.setEnabled(api_client is not None)
        self.connection_changed.emit(api_client, tenant_name, "dor")

    def _start_pull(self):
        """Start the DoR pull operation."""
        if not self.api_client:
            QMessageBox.warning(self, "Not Connected", "Please connect to a tenant first.")
            return

        from gui.workers.dor_pull_worker import DorPullWorker

        self.pull_btn.setEnabled(False)
        self.cancel_pull_btn.setVisible(True)
        self.pull_progress.setVisible(True)
        self.pull_progress.setValue(0)
        self.pull_status.setText("Starting pull...")

        self._pull_worker = DorPullWorker(self.api_client, self.connection_name)
        self._pull_worker.progress.connect(self._on_pull_progress)
        self._pull_worker.finished.connect(self._on_pull_finished)
        self._pull_worker.license_data.connect(self._on_license_data)
        self._pull_worker.auth_data.connect(self._on_auth_data)
        self._pull_worker.mu_data.connect(self._on_mu_data)
        self._pull_worker.error.connect(self._on_pull_error)
        self._pull_worker.start()

    def _cancel_pull(self):
        """Cancel the current pull operation."""
        if self._pull_worker:
            self._pull_worker.cancel()
            self.pull_status.setText("Cancelling...")

    def _on_pull_progress(self, message: str, percentage: int):
        """Handle pull progress updates."""
        self.pull_progress.setValue(percentage)
        self.pull_status.setText(message)

    def _on_pull_error(self, error_msg: str):
        """Handle pull error."""
        self.pull_status.setText(f"Error: {error_msg}")
        self.pull_status.setStyleSheet("color: red;")

    def _on_pull_finished(self, success: bool, message: str, config):
        """Handle pull completion."""
        self.cancel_pull_btn.setVisible(False)
        self.pull_btn.setEnabled(True)

        if success and config:
            self.pulled_config = config
            self.pull_status.setText(f"Pull complete: {message}")
            self.pull_status.setStyleSheet("color: green;")
            self.pull_progress.setValue(100)
            self.answer_from_config_btn.setEnabled(True)

            # Run config analysis
            self._analyze_config()
        else:
            self.pull_status.setText(f"Pull failed: {message}")
            self.pull_status.setStyleSheet("color: red;")

        self._pull_worker = None

    def _load_config_from_file(self):
        """Load a saved configuration file for DoR analysis."""
        try:
            from gui.dialogs import LoadConfigDialog
        except ImportError:
            QMessageBox.warning(
                self, "Not Available",
                "LoadConfigDialog is not available."
            )
            return

        dialog = LoadConfigDialog(self)
        if dialog.exec() != LoadConfigDialog.DialogCode.Accepted:
            return

        config_data = dialog.get_config()
        metadata = dialog.get_metadata()
        if not config_data:
            return

        try:
            config_name = (metadata.get('name', 'Configuration')
                           if metadata else 'Configuration')

            # Convert dict to Configuration object
            config = self._convert_dict_to_configuration(config_data)

            # Store and analyze
            self.pulled_config = config
            if not self.connection_name:
                self.connection_name = (
                    config.source_tenant or config_name
                )

            self.pull_status.setText(
                f"Loaded from file: {config_name} "
                f"({len(config.get_all_items())} items)"
            )
            self.pull_status.setStyleSheet("color: green;")
            self.answer_from_config_btn.setEnabled(True)

            # Run config analysis
            self._analyze_config()

            logger.info(
                f"Loaded config from file for DoR: {config_name}, "
                f"{len(config.get_all_items())} items"
            )
        except Exception as e:
            logger.exception(f"Failed to load config from file: {e}")
            QMessageBox.critical(
                self, "Load Error",
                f"Failed to process configuration:\n\n{e}"
            )

    def load_configuration_from_main(self, config):
        """
        Accept a Configuration object from the main window
        (e.g. loaded via File > Load Configuration).
        """
        self.pulled_config = config
        if not self.connection_name:
            self.connection_name = config.source_tenant

        total = len(config.get_all_items())
        self.pull_status.setText(
            f"Configuration loaded: {total} items"
        )
        self.pull_status.setStyleSheet("color: green;")
        self.answer_from_config_btn.setEnabled(True)
        self._analyze_config()
        logger.info(f"DoR received config from main window: {total} items")

    @staticmethod
    def _convert_dict_to_configuration(config_data: dict):
        """Convert a configuration dictionary to a Configuration object."""
        from config.models.containers import Configuration, FolderConfig, SnippetConfig
        from config.models.factory import ConfigItemFactory

        config = Configuration()

        # Copy metadata
        metadata = config_data.get('metadata', {})
        config.source_tsg = metadata.get('source_tsg')
        config.source_tenant = metadata.get('source_tenant')
        config.source_config = (
            metadata.get('source_config') or metadata.get('source_file')
        )
        config.load_type = metadata.get('load_type', 'From File')
        config.saved_credentials_ref = metadata.get('saved_credentials_ref')
        config.created_at = metadata.get('created_at')
        config.modified_at = metadata.get('modified_at')
        config.program_version = config_data.get(
            'program_version', Configuration.PROGRAM_VERSION
        )
        config.config_version = config_data.get('config_version', 1)

        # Process folders
        for folder_name, folder_data in config_data.get('folders', {}).items():
            folder_config = FolderConfig(folder_name)
            if isinstance(folder_data, dict):
                if 'items' in folder_data and isinstance(folder_data['items'], list):
                    folder_config.parent = folder_data.get('parent')
                    for item_dict in folder_data['items']:
                        try:
                            item_type = item_dict.get('item_type', 'unknown')
                            item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                            folder_config.add_item(item)
                        except Exception:
                            pass
                else:
                    for item_type, items in folder_data.items():
                        if item_type == 'parent':
                            folder_config.parent = items
                            continue
                        if isinstance(items, list):
                            for item_dict in items:
                                try:
                                    item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                                    folder_config.add_item(item)
                                except Exception:
                                    pass
            config.add_folder(folder_config)

        # Process snippets
        for snippet_name, snippet_data in config_data.get('snippets', {}).items():
            snippet_config = SnippetConfig(snippet_name)
            if isinstance(snippet_data, dict):
                if 'items' in snippet_data and isinstance(snippet_data['items'], list):
                    for item_dict in snippet_data['items']:
                        try:
                            item_type = item_dict.get('item_type', 'unknown')
                            item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                            snippet_config.add_item(item)
                        except Exception:
                            pass
                else:
                    for item_type, items in snippet_data.items():
                        if isinstance(items, list):
                            for item_dict in items:
                                try:
                                    item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                                    snippet_config.add_item(item)
                                except Exception:
                                    pass
            config.add_snippet(snippet_config)

        # Process infrastructure
        infra_data = config_data.get('infrastructure', {})
        if isinstance(infra_data, dict):
            if 'items' in infra_data and isinstance(infra_data['items'], list):
                for item_dict in infra_data['items']:
                    try:
                        item_type = item_dict.get('item_type', 'unknown')
                        item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                        config.infrastructure.add_item(item)
                    except Exception:
                        pass
            else:
                for item_type, items in infra_data.items():
                    if isinstance(items, list):
                        for item_dict in items:
                            try:
                                item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                                config.infrastructure.add_item(item)
                            except Exception:
                                pass

        return config

    def _on_license_data(self, license_info):
        """Handle license data from pull worker."""
        if not license_info:
            return

        self._license_info = license_info
        self.dor_data['license_info'] = license_info

        # Populate serial number if found
        serial = license_info.get('serial_number')
        if serial and not self.serial_edit.text():
            self.serial_edit.setText(str(serial))

        # Show panorama management status
        panorama = license_info.get('panorama_managed', False)
        if panorama:
            self.panorama_managed_label.setText("Yes")
            self.panorama_managed_label.setStyleSheet("font-weight: bold; color: #e65100;")
        else:
            self.panorama_managed_label.setText("No (Cloud Managed)")
            self.panorama_managed_label.setStyleSheet("font-weight: bold; color: green;")

        # Build structured license display
        licenses = license_info.get('licenses', [])
        self._populate_license_display(licenses, license_info.get('infra_settings_raw'))

        # Refresh analysis display if visible (adds license summary)
        if self.analysis_group.isVisible():
            self._update_analysis_display()

        # Extract MU licensed quantity from license entries
        if licenses and self.mu_licensed_spin.value() < 0:
            mu_keywords = {'mobile', 'remote', 'globalprotect', 'prisma access', 'mu'}
            mu_qty = None
            fallback_qty = None
            for lic in licenses:
                if not isinstance(lic, dict):
                    continue
                # Check if this license relates to Mobile Users
                lic_text = ' '.join(
                    str(v).lower() for v in lic.values() if isinstance(v, str)
                )
                is_mu = any(kw in lic_text for kw in mu_keywords)
                # Extract quantity from common fields
                qty = None
                for key in ('quantity', 'units', 'count', 'seats'):
                    val = lic.get(key)
                    if val is not None:
                        try:
                            qty = int(val)
                        except (ValueError, TypeError):
                            pass
                        break
                if qty and is_mu:
                    mu_qty = qty
                    break
                if qty and fallback_qty is None:
                    fallback_qty = qty

            final_qty = mu_qty or fallback_qty
            if final_qty and final_qty > 0:
                self.mu_licensed_spin.setValue(final_qty)
                logger.info(f"Set MU licensed users from license data: {final_qty}")

        logger.info(f"License data populated: {len(licenses)} license(s), "
                    f"serial={serial}, panorama_managed={panorama}")

    def _populate_license_display(self, licenses, infra_settings_raw=None):
        """Populate the structured license display with formatted entries."""
        # Clear existing widgets (except placeholder)
        while self.license_display_layout.count() > 0:
            item = self.license_display_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not licenses:
            # Show placeholder
            placeholder = QLabel("No license data available")
            placeholder.setStyleSheet("color: #666; font-style: italic; padding: 8px;")
            self.license_display_layout.addWidget(placeholder)
            self.license_display_layout.addStretch()
            return

        # Build display for each top-level license entry
        for lic_entry in licenses:
            if not isinstance(lic_entry, dict):
                continue

            app_id = lic_entry.get('app_id', 'unknown')
            app_name = LICENSE_APP_NAMES.get(app_id, app_id.replace('_', ' ').title())
            sub_licenses = lic_entry.get('licenses', [])

            # Create a frame for this app
            app_frame = QFrame()
            app_frame.setFrameShape(QFrame.Shape.StyledPanel)
            app_frame.setStyleSheet("""
                QFrame {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    margin: 2px;
                }
            """)
            app_layout = QVBoxLayout(app_frame)
            app_layout.setContentsMargins(10, 8, 10, 8)
            app_layout.setSpacing(4)

            # App name header
            app_label = QLabel(f"<b>{app_name}</b>")
            app_label.setStyleSheet("font-size: 13px; color: #1976d2;")
            app_layout.addWidget(app_label)

            # Sub-licenses
            if sub_licenses:
                for sub_lic in sub_licenses:
                    if not isinstance(sub_lic, dict):
                        continue
                    lic_type = sub_lic.get('license_type', 'Unknown')
                    lic_type_name = LICENSE_TYPE_NAMES.get(lic_type, lic_type)
                    purchased = sub_lic.get('purchased_size', 0)

                    # Format quantity with commas
                    if isinstance(purchased, (int, float)):
                        qty_str = f"{int(purchased):,}"
                    else:
                        qty_str = str(purchased)

                    sub_label = QLabel(f"  • {lic_type_name}: <b>{qty_str}</b>")
                    sub_label.setStyleSheet("font-size: 12px; color: #333; margin-left: 8px;")
                    app_layout.addWidget(sub_label)
            else:
                # No sub-licenses, check for quantity at top level
                qty = lic_entry.get('quantity') or lic_entry.get('units') or lic_entry.get('purchased_size')
                if qty:
                    if isinstance(qty, (int, float)):
                        qty_str = f"{int(qty):,}"
                    else:
                        qty_str = str(qty)
                    qty_label = QLabel(f"  Quantity: <b>{qty_str}</b>")
                    qty_label.setStyleSheet("font-size: 12px; color: #333;")
                    app_layout.addWidget(qty_label)

            self.license_display_layout.addWidget(app_frame)

        self.license_display_layout.addStretch()

        # Also store raw text for save/restore (hidden field)
        raw_lines = []
        for lic in licenses:
            app_id = lic.get('app_id', 'unknown')
            app_name = LICENSE_APP_NAMES.get(app_id, app_id)
            sub_lics = lic.get('licenses', [])
            raw_lines.append(f"{app_name}:")
            for sl in sub_lics:
                lt = sl.get('license_type', 'Unknown')
                lt_name = LICENSE_TYPE_NAMES.get(lt, lt)
                ps = sl.get('purchased_size', 0)
                raw_lines.append(f"  - {lt_name}: {ps}")
        self.license_text.setPlainText("\n".join(raw_lines) if raw_lines else "")

    def _on_auth_data(self, auth_info):
        """Handle authentication/CIE data from pull worker."""
        if not auth_info:
            return

        self._auth_info = auth_info
        self.dor_data['auth_info'] = auth_info

        # Build auth methods display
        profiles = auth_info.get('auth_profiles', [])
        methods = auth_info.get('auth_methods', [])

        lines = []
        if methods:
            lines.append(f"Methods: {', '.join(methods)}")
        if profiles:
            lines.append("")
            for p in profiles:
                detail = f"  {p['name']} ({p['method_label']})"
                if p.get('folder'):
                    detail += f" - {p['folder']}"
                lines.append(detail)

        self.auth_methods_text.setPlainText("\n".join(lines) if lines else "No auth profiles found")

        # CIE domains
        has_cie = auth_info.get('has_cie', False)
        cie_domains = auth_info.get('cie_domains', [])

        self.cie_domains_label.setVisible(has_cie)
        self.cie_domains_text.setVisible(has_cie)

        if has_cie and cie_domains:
            domain_lines = []
            for d in cie_domains:
                line = f"{d.get('domain', '?')} ({d.get('type', '?')})"
                status = d.get('status', '')
                if status:
                    line += f" - {status}"
                users = d.get('user_count', 0)
                groups = d.get('group_count', 0)
                if users or groups:
                    line += f" [{users} users, {groups} groups]"
                domain_lines.append(line)
            self.cie_domains_text.setPlainText("\n".join(domain_lines))
        elif has_cie:
            self.cie_domains_text.setPlainText("CIE detected but no domains returned from API")

        logger.info(f"Auth data populated: {len(profiles)} profiles, "
                    f"has_cie={has_cie}, {len(cie_domains)} CIE domain(s)")

        if self.analysis_group.isVisible():
            self._update_analysis_display()

    def _on_mu_data(self, mu_info):
        """Handle Mobile Users configuration data from pull worker."""
        if not mu_info:
            return

        self._mu_info = mu_info

        # Region-to-parent mapping for auto-checking base regions
        region_parent_map = {
            'us': 'Americas', 'united states': 'Americas', 'canada': 'Americas',
            'brazil': 'Americas', 'mexico': 'Americas', 'colombia': 'Americas',
            'argentina': 'Americas', 'chile': 'Americas', 'peru': 'Americas',
            'us-east': 'Americas', 'us-west': 'Americas', 'us-central': 'Americas',
            'us-south': 'Americas', 'us-northwest': 'Americas', 'us-southeast': 'Americas',
            'us-east-1': 'Americas', 'us-west-1': 'Americas',
            'uk': 'EMEA', 'united kingdom': 'EMEA', 'germany': 'EMEA',
            'france': 'EMEA', 'netherlands': 'EMEA', 'ireland': 'EMEA',
            'italy': 'EMEA', 'spain': 'EMEA', 'sweden': 'EMEA',
            'switzerland': 'EMEA', 'norway': 'EMEA', 'denmark': 'EMEA',
            'belgium': 'EMEA', 'austria': 'EMEA', 'poland': 'EMEA',
            'israel': 'EMEA', 'south africa': 'EMEA', 'uae': 'EMEA',
            'saudi arabia': 'EMEA', 'nigeria': 'EMEA', 'egypt': 'EMEA',
            'eu-west': 'EMEA', 'eu-central': 'EMEA', 'europe': 'EMEA',
            'japan': 'APAC', 'australia': 'APAC', 'india': 'APAC',
            'singapore': 'APAC', 'hong kong': 'APAC', 'south korea': 'APAC',
            'taiwan': 'APAC', 'new zealand': 'APAC', 'indonesia': 'APAC',
            'malaysia': 'APAC', 'thailand': 'APAC', 'philippines': 'APAC',
            'vietnam': 'APAC', 'china': 'APAC',
            'ap-southeast': 'APAC', 'ap-northeast': 'APAC', 'asia': 'APAC',
        }

        # --- Geographic Distribution ---
        location_regions = mu_info.get('location_regions', [])
        if location_regions:
            # Add dynamic sub-region checkboxes
            # Clear existing dynamic widgets
            while self.mu_geo_dynamic_layout.count():
                item = self.mu_geo_dynamic_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

            cols = 4
            for i, region in enumerate(location_regions):
                if region not in self.mu_geo_checks:
                    cb = QCheckBox(region)
                    cb.setStyleSheet("font-size: 11px;")
                    self.mu_geo_dynamic_layout.addWidget(cb, i // cols, i % cols)
                    self.mu_geo_checks[region] = cb

            # Auto-check detected regions and their parents
            parents_to_check = set()
            for region in location_regions:
                # Check the sub-region itself
                if region in self.mu_geo_checks:
                    self.mu_geo_checks[region].setChecked(True)
                # Map to parent region
                region_lower = region.lower().strip()
                parent = region_parent_map.get(region_lower)
                if parent:
                    parents_to_check.add(parent)

            # Auto-check parent regions
            for parent in parents_to_check:
                if parent in self.mu_geo_checks:
                    self.mu_geo_checks[parent].setChecked(True)

        # --- Device Assignment ---
        profile_analysis = mu_info.get('profile_analysis', {})
        device_assignment = profile_analysis.get('device_assignment')
        if device_assignment and self.mu_device_combo.currentIndex() == 0:
            self._set_combo(self.mu_device_combo, device_assignment)

        # --- Connect Method ---
        connect_method = profile_analysis.get('connect_method')
        if connect_method and self.mu_connect_combo.currentIndex() == 0:
            self._set_combo(self.mu_connect_combo, connect_method)

        # --- OS Platforms: default Windows + macOS if profiles exist ---
        if mu_info.get('profiles'):
            any_checked = any(cb.isChecked() for cb in self.mu_os_checks.values())
            if not any_checked:
                for platform in ['Windows', 'macOS']:
                    if platform in self.mu_os_checks:
                        self.mu_os_checks[platform].setChecked(True)

        # --- Bypass Traffic ---
        bypass_analysis = mu_info.get('bypass_analysis', {})
        summary = bypass_analysis.get('summary')
        if summary and not self.mu_bypass_text.toPlainText().strip():
            self.mu_bypass_text.setPlainText(summary)

        logger.info(
            f"MU data populated: {len(location_regions)} regions, "
            f"device={device_assignment}, connect={connect_method}"
        )

        if self.analysis_group.isVisible():
            self._update_analysis_display()

    def _analyze_config(self):
        """Analyze pulled config and update DoR data."""
        if not self.pulled_config:
            return

        config_answers = generate_dor_from_config(self.pulled_config)
        self.dor_data['config_analysis'] = config_answers

        # Update metadata
        self.dor_data['metadata']['tenant_name'] = self.connection_name

        # Show analysis results
        self.analysis_group.setVisible(True)
        self._update_analysis_display()

    def _update_analysis_display(self):
        """Rebuild the configuration analysis text from current data."""
        config_answers = self.dor_data.get('config_analysis', {})

        lines = []
        lines.append(f"Total items pulled: {config_answers.get('total_items', 0)}")
        lines.append(f"Folders: {', '.join(config_answers.get('folders', []))}")
        lines.append(f"Snippets: {', '.join(config_answers.get('snippets', []))}")
        lines.append("")

        # Quantities
        q = config_answers.get('quantities', {})
        lines.append("=== Quantities ===")
        lines.append(f"Service Connections: {q.get('service_connection_count', 0)}")
        lines.append(f"Remote Networks: {q.get('remote_network_count', 0)}")
        lines.append(f"Security Rules: {q.get('security_rule_count', 0)}")
        lines.append(f"Decryption Rules: {q.get('decryption_rule_count', 0)}")
        lines.append(f"Address Objects: {q.get('address_object_count', 0)}")
        lines.append(f"Address Groups: {q.get('address_group_count', 0)}")
        lines.append(f"Service Objects: {q.get('service_object_count', 0)}")
        lines.append(f"External Dynamic Lists: {q.get('edl_count', 0)}")
        lines.append(f"Tags: {q.get('tag_count', 0)}")
        lines.append("")

        # Features
        lines.append("=== Feature Detection ===")
        for key, result in config_answers.get('features', {}).items():
            label = DOR_FEATURE_MAP.get(key, {}).get('label', key)
            status = "CUSTOM" if result.get('has_custom') else ("DEFAULT" if result.get('detected') else "NOT CONFIGURED")
            lines.append(f"  {label}: {status} ({result.get('evidence', '')})")
        lines.append("")

        # Infrastructure
        infra = config_answers.get('infrastructure', {})
        lines.append("=== Infrastructure ===")
        lines.append(f"IKE Gateways: {infra.get('ike_gateway_count', 0)}")
        lines.append(f"IPsec Tunnels: {infra.get('ipsec_tunnel_count', 0)}")
        lines.append(f"IKE Crypto Profiles: {infra.get('ike_crypto_profile_count', 0)}")
        lines.append(f"IPsec Crypto Profiles: {infra.get('ipsec_crypto_profile_count', 0)}")
        lines.append(f"Agent Profiles: {infra.get('agent_profile_count', 0)}")
        lines.append(f"Certificate Profiles: {infra.get('certificate_profile_count', 0)}")

        # License / Tenant Info
        lines.append("")
        lines.append("=== License & Tenant Info ===")
        if self._license_info:
            licenses = self._license_info.get('licenses', [])
            if licenses:
                lines.append(f"License entries: {len(licenses)}")
                for lic in licenses:
                    if isinstance(lic, dict):
                        # Show key fields from each license entry
                        parts = []
                        for key in ('type', 'name', 'description', 'license_type',
                                    'quantity', 'units', 'count', 'seats',
                                    'status', 'expiry', 'expires'):
                            val = lic.get(key)
                            if val is not None:
                                parts.append(f"{key}={val}")
                        lines.append(f"  {' | '.join(parts) if parts else str(lic)}")
                    else:
                        lines.append(f"  {lic}")
            else:
                lines.append("License types: Access denied (403) or not available")

            serial = self._license_info.get('serial_number')
            if serial:
                lines.append(f"Serial Number: {serial}")

            panorama = self._license_info.get('panorama_managed')
            if panorama:
                lines.append("Panorama Managed: Yes")

            # Infrastructure settings summary
            infra_raw = self._license_info.get('infra_settings_raw', {})
            if infra_raw:
                bgp_as = infra_raw.get('infra_bgp_as')
                subnet = infra_raw.get('infrastructure_subnet')
                if bgp_as:
                    lines.append(f"BGP AS: {bgp_as}")
                if subnet:
                    lines.append(f"Infrastructure Subnet: {subnet}")
        else:
            lines.append("No license/tenant data captured (API may lack permissions)")

        # MU Info
        if self._mu_info:
            lines.append("")
            lines.append("=== Mobile Users ===")
            loc_regions = self._mu_info.get('location_regions', [])
            if loc_regions:
                lines.append(f"Location Regions: {', '.join(loc_regions)}")
            else:
                lines.append("Location Regions: None detected")
            pa = self._mu_info.get('profile_analysis', {})
            if pa.get('device_assignment'):
                lines.append(f"Device Assignment: {pa['device_assignment']}")
            if pa.get('connect_method'):
                lines.append(f"Connect Method: {pa['connect_method']}")
            bypass = self._mu_info.get('bypass_analysis', {})
            if bypass.get('summary'):
                lines.append(f"Bypass: {bypass['summary']}")

        # Auth Info
        if self._auth_info:
            lines.append("")
            lines.append("=== Authentication ===")
            methods = self._auth_info.get('auth_methods', [])
            if methods:
                lines.append(f"Methods: {', '.join(methods)}")
            has_cie = self._auth_info.get('has_cie', False)
            lines.append(f"Cloud Identity Engine: {'Yes' if has_cie else 'No'}")
            cie_domains = self._auth_info.get('cie_domains', [])
            if cie_domains:
                lines.append(f"CIE Domains: {len(cie_domains)}")
                for d in cie_domains:
                    lines.append(f"  {d.get('domain', '?')} ({d.get('type', '?')})")

        self.analysis_text.setPlainText("\n".join(lines))

    def _answer_from_config(self):
        """
        Populate empty technical fields from pulled configuration data.

        Only fills fields that are currently empty/unchecked/unset.
        Never overwrites existing user-entered answers.
        Auto-enables gated sections (MU/RN) if relevant config is detected.
        """
        if not self.pulled_config:
            QMessageBox.information(
                self, "No Configuration",
                "No configuration has been pulled yet. Pull from a tenant first."
            )
            return

        config_answers = self.dor_data.get('config_analysis')
        if not config_answers:
            config_answers = generate_dor_from_config(self.pulled_config)
            self.dor_data['config_analysis'] = config_answers

        filled = []
        q = config_answers.get('quantities', {})
        infra = config_answers.get('infrastructure', {})

        # --- Serial Number (from license info) ---
        if not self.serial_edit.text() and self._license_info:
            serial = self._license_info.get('serial_number')
            if serial:
                self.serial_edit.setText(str(serial))
                filled.append("Serial Number")

        # --- Panorama Managed (from license info) ---
        if self.panorama_managed_label.text() == '--' and self._license_info:
            panorama = self._license_info.get('panorama_managed', False)
            if panorama:
                self.panorama_managed_label.setText("Yes")
                self.panorama_managed_label.setStyleSheet("font-weight: bold; color: #e65100;")
            else:
                self.panorama_managed_label.setText("No (Cloud Managed)")
                self.panorama_managed_label.setStyleSheet("font-weight: bold; color: green;")
            filled.append("Panorama Managed")

        # --- License Info (from license info) ---
        if self._license_info:
            license_content = self.license_text.toPlainText().strip()
            if (not license_content
                    or license_content.startswith("No license data")
                    or license_content.startswith("License types: Not available")):
                self._on_license_data(self._license_info)
                filled.append("License Info")
            # Also try to populate MU licensed spin independently
            if self.mu_licensed_spin.value() < 0:
                licenses = self._license_info.get('licenses', [])
                if licenses:
                    mu_keywords = {'mobile', 'remote', 'globalprotect', 'prisma access', 'mu'}
                    mu_qty = None
                    fallback_qty = None
                    for lic in licenses:
                        if not isinstance(lic, dict):
                            continue
                        lic_text = ' '.join(
                            str(v).lower() for v in lic.values() if isinstance(v, str)
                        )
                        is_mu = any(kw in lic_text for kw in mu_keywords)
                        qty = None
                        for key in ('quantity', 'units', 'count', 'seats'):
                            val = lic.get(key)
                            if val is not None:
                                try:
                                    qty = int(val)
                                except (ValueError, TypeError):
                                    pass
                                break
                        if qty is not None and is_mu:
                            mu_qty = qty
                            break
                        if qty is not None and fallback_qty is None:
                            fallback_qty = qty
                    final_qty = mu_qty if mu_qty is not None else fallback_qty
                    if final_qty is not None and final_qty >= 0:
                        self.mu_licensed_spin.setValue(final_qty)
                        filled.append(f"Licensed Remote Workers ({final_qty})")

        # --- Auth Methods (from auth info) ---
        if not self.auth_methods_text.toPlainText().strip() and self._auth_info:
            self._on_auth_data(self._auth_info)
            filled.append("Auth Methods")

        # --- Mobile Users: auto-enable if MU config detected ---
        mu_detected = False
        # Check for Mobile Users folder with items
        if 'Mobile Users' in config_answers.get('folders', []):
            mu_detected = True
        # Check for agent profiles (GlobalProtect)
        if infra.get('agent_profile_count', 0) > 0:
            mu_detected = True
        # Check for HIP objects/profiles
        hip_result = config_answers.get('features', {}).get('hip', {})
        if hip_result.get('detected'):
            mu_detected = True

        if mu_detected and not self.mu_check.isChecked():
            self.mu_check.setChecked(True)
            filled.append("Mobile Users (enabled - config detected)")

        # Fill MU sub-fields only if empty
        if self.mu_check.isChecked():
            if hip_result.get('has_custom') and not self.mu_hip_edit.toPlainText().strip():
                custom_names = hip_result.get('custom_names', [])
                if custom_names:
                    self.mu_hip_edit.setPlainText(
                        f"HIP profiles/objects detected: {', '.join(custom_names)}"
                    )
                    filled.append("HIP Check Details")

            # Use stored MU info for additional fields
            if self._mu_info:
                # Geo: check/populate from location_regions if no checkboxes checked
                any_geo_checked = any(cb.isChecked() for cb in self.mu_geo_checks.values())
                if not any_geo_checked:
                    location_regions = self._mu_info.get('location_regions', [])
                    if location_regions:
                        # Trigger the full handler logic for geo population
                        self._on_mu_data(self._mu_info)
                        filled.append("Geographic Distribution")

                # Device assignment from profile analysis
                profile_analysis = self._mu_info.get('profile_analysis', {})
                device_assignment = profile_analysis.get('device_assignment')
                if device_assignment and self.mu_device_combo.currentIndex() == 0:
                    self._set_combo(self.mu_device_combo, device_assignment)
                    filled.append("Device Assignment")

                # Connect method from profile analysis
                connect_method = profile_analysis.get('connect_method')
                if connect_method and self.mu_connect_combo.currentIndex() == 0:
                    self._set_combo(self.mu_connect_combo, connect_method)
                    filled.append("Agent Connect Method")

                # OS platforms: default Win + Mac if profiles exist and nothing checked
                any_os_checked = any(cb.isChecked() for cb in self.mu_os_checks.values())
                if not any_os_checked and self._mu_info.get('profiles'):
                    for platform in ['Windows', 'macOS']:
                        if platform in self.mu_os_checks:
                            self.mu_os_checks[platform].setChecked(True)
                    filled.append("OS Platforms (default: Windows, macOS)")

                # Bypass from tunnel analysis
                bypass_summary = self._mu_info.get('bypass_analysis', {}).get('summary')
                if bypass_summary and not self.mu_bypass_text.toPlainText().strip():
                    self.mu_bypass_text.setPlainText(bypass_summary)
                    filled.append("Bypass/Tunnel Traffic")

        # --- Remote Networks: auto-enable if RN config detected ---
        rn_count = q.get('remote_network_count', 0)
        if rn_count > 0 and not self.rn_check.isChecked():
            self.rn_check.setChecked(True)
            filled.append("Remote Networks (enabled - config detected)")

        # Fill RN sub-fields only if empty
        if self.rn_check.isChecked() and rn_count > 0:
            if self.rn_offices_spin.value() < 0:
                self.rn_offices_spin.setValue(rn_count)
                filled.append(f"Remote Network count ({rn_count})")

            rn_locations = q.get('remote_network_locations', [])
            if rn_locations and not self.rn_locations_edit.text():
                loc_str = ', '.join(
                    loc.get('region', loc.get('name', ''))
                    for loc in rn_locations if loc.get('region') or loc.get('name')
                )
                if loc_str:
                    self.rn_locations_edit.setText(loc_str)
                    filled.append("Remote Network locations")

        # --- Service Connections: fill BGP info if empty ---
        sc_count = q.get('service_connection_count', 0)
        if sc_count > 0 and not self.sc_bgp_edit.text():
            # Check IKE gateways for BGP-related info
            ike_gws = infra.get('ike_gateways', [])
            if ike_gws:
                gw_summary = ', '.join(
                    f"{gw.get('name', '?')} ({gw.get('peer_address', '?')})"
                    for gw in ike_gws[:5]
                )
                self.sc_bgp_edit.setText(f"{len(ike_gws)} IKE gateway(s): {gw_summary}")
                filled.append("Service Connection IKE details")

        # --- Show results ---
        if filled:
            self.answer_from_config_status.setText(
                f"Populated {len(filled)} field(s): {', '.join(filled)}"
            )
            self.answer_from_config_status.setStyleSheet("color: green; font-size: 11px;")
            logger.info(f"Answer from config populated: {filled}")
        else:
            self.answer_from_config_status.setText(
                "No empty fields could be answered from configuration."
            )
            self.answer_from_config_status.setStyleSheet("color: gray; font-size: 11px;")

    # ========================================================================
    # Tab 2: Environment Questions
    # ========================================================================

    def _create_environment_tab(self) -> QWidget:
        """Create the environment/business context tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Domain
        domain_group = QGroupBox("Domain & Delivery")
        domain_form = QFormLayout()

        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["SASE", "Cloud Security", "SOC/XDR", "Other"])
        domain_form.addRow("Domain:", self.domain_combo)

        self.delivery_combo = QComboBox()
        self.delivery_combo.addItems([
            "-- Select --",
            "Internal",
            "Co-Delivery",
            "MSSP",
            "Delivery Assurance",
        ])
        domain_form.addRow("Delivery Model:", self.delivery_combo)

        self.eval_combo = QComboBox()
        self.eval_combo.addItems(["-- Select --", "Eval to Prod", "Net New"])
        domain_form.addRow("Eval to Prod / Net New:", self.eval_combo)

        self.sales_team_edit = QLineEdit()
        self.sales_team_edit.setPlaceholderText("Name of Service Sales Team member")
        domain_form.addRow("Service Sales Team Member:", self.sales_team_edit)

        domain_group.setLayout(domain_form)
        layout.addWidget(domain_group)

        # Business Context
        biz_group = QGroupBox("Business Context")
        biz_form = QFormLayout()

        self.problems_edit = QTextEdit()
        self.problems_edit.setPlaceholderText("What problems is the customer trying to solve?")
        self.problems_edit.setMaximumHeight(80)
        biz_form.addRow("Customer Problems:", self.problems_edit)

        self.why_insufficient_edit = QTextEdit()
        self.why_insufficient_edit.setPlaceholderText("Why is the current technology insufficient?")
        self.why_insufficient_edit.setMaximumHeight(80)
        biz_form.addRow("Why Current Tech Insufficient:", self.why_insufficient_edit)

        self.outcomes_edit = QTextEdit()
        self.outcomes_edit.setPlaceholderText("What are the desired business outcomes?")
        self.outcomes_edit.setMaximumHeight(80)
        biz_form.addRow("Desired Business Outcomes:", self.outcomes_edit)

        self.use_cases_edit = QTextEdit()
        self.use_cases_edit.setPlaceholderText("List identified use cases (one per line)")
        self.use_cases_edit.setMaximumHeight(80)
        biz_form.addRow("Identified Use Cases:", self.use_cases_edit)

        self.critical_caps_edit = QTextEdit()
        self.critical_caps_edit.setPlaceholderText("List critical capabilities (one per line)")
        self.critical_caps_edit.setMaximumHeight(80)
        biz_form.addRow("Critical Capabilities:", self.critical_caps_edit)

        biz_group.setLayout(biz_form)
        layout.addWidget(biz_group)

        # Network Design
        network_group = QGroupBox("Network & Architecture")
        network_form = QFormLayout()

        self.network_design_edit = QTextEdit()
        self.network_design_edit.setPlaceholderText("Describe current state network design")
        self.network_design_edit.setMaximumHeight(80)
        network_form.addRow("Current State Network Design:", self.network_design_edit)

        self.additional_info_edit = QTextEdit()
        self.additional_info_edit.setPlaceholderText("Additional current/future state information")
        self.additional_info_edit.setMaximumHeight(80)
        network_form.addRow("Additional Info:", self.additional_info_edit)

        self.innovation_edit = QTextEdit()
        self.innovation_edit.setPlaceholderText("Any innovation/preview features needed?")
        self.innovation_edit.setMaximumHeight(60)
        network_form.addRow("Innovation/Preview Features:", self.innovation_edit)

        network_group.setLayout(network_form)
        layout.addWidget(network_group)

        # Navigation
        nav_row = QHBoxLayout()
        prev_btn = QPushButton("<< Previous")
        prev_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        nav_row.addWidget(prev_btn)
        nav_row.addStretch()
        next_btn = QPushButton("Next: Technical Questions >>")
        next_btn.clicked.connect(lambda: self._next_tab(2))
        nav_row.addWidget(next_btn)
        layout.addLayout(nav_row)

        layout.addStretch()

        scroll.setWidget(tab)
        return scroll

    # ========================================================================
    # Tab 3: Technical Questions
    # ========================================================================

    def _create_technical_tab(self) -> QWidget:
        """Create the technical questions tab with collapsible gated sections."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Answer from Configuration button
        config_btn_row = QHBoxLayout()
        self.answer_from_config_btn = QPushButton("Answer from Configuration")
        self.answer_from_config_btn.setToolTip(
            "Fill in empty fields from pulled configuration data.\n"
            "Only populates fields that haven't been filled yet — never overwrites existing answers."
        )
        self.answer_from_config_btn.setMinimumHeight(36)
        self.answer_from_config_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; font-weight: bold; "
            "border-radius: 5px; padding: 8px 16px; border: 1px solid #1565C0; "
            "border-bottom: 3px solid #0D47A1; }"
            "QPushButton:hover { background-color: #1E88E5; }"
            "QPushButton:disabled { background-color: #ccc; color: #666; border: 1px solid #999; }"
        )
        self.answer_from_config_btn.setEnabled(False)
        self.answer_from_config_btn.clicked.connect(self._answer_from_config)
        config_btn_row.addWidget(self.answer_from_config_btn)
        self.answer_from_config_status = QLabel("")
        self.answer_from_config_status.setStyleSheet("color: green; font-size: 11px;")
        config_btn_row.addWidget(self.answer_from_config_status)
        config_btn_row.addStretch()
        layout.addLayout(config_btn_row)

        # Tenant Info
        tenant_group = QGroupBox("Tenant Information")
        tenant_form = QFormLayout()

        self.tenant_url_edit = QLineEdit()
        self.tenant_url_edit.setPlaceholderText("https://...")
        tenant_form.addRow("Tenant URL:", self.tenant_url_edit)

        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText("Auto-populated from pull, or enter manually")
        tenant_form.addRow("Serial Number:", self.serial_edit)

        self.panorama_managed_label = QLabel("--")
        self.panorama_managed_label.setStyleSheet("font-weight: bold;")
        tenant_form.addRow("Panorama Managed:", self.panorama_managed_label)

        tenant_group.setLayout(tenant_form)
        layout.addWidget(tenant_group)

        # License Info (auto-populated from pull)
        license_group = QGroupBox("License Information")
        license_layout = QVBoxLayout()

        license_hint = QLabel(
            "License details are auto-populated from the tenant pull."
        )
        license_hint.setWordWrap(True)
        license_hint.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        license_layout.addWidget(license_hint)

        # Scrollable license display area
        license_scroll = QScrollArea()
        license_scroll.setWidgetResizable(True)
        license_scroll.setMaximumHeight(200)
        license_scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #ccc; border-radius: 4px; background: #fafafa; }"
        )

        self.license_display_widget = QWidget()
        self.license_display_layout = QVBoxLayout(self.license_display_widget)
        self.license_display_layout.setContentsMargins(8, 8, 8, 8)
        self.license_display_layout.setSpacing(6)

        # Placeholder label when no licenses loaded
        self.license_placeholder = QLabel(
            "License data will appear here after pulling from a tenant."
        )
        self.license_placeholder.setStyleSheet("color: #888; font-style: italic;")
        self.license_display_layout.addWidget(self.license_placeholder)
        self.license_display_layout.addStretch()

        license_scroll.setWidget(self.license_display_widget)
        license_layout.addWidget(license_scroll)

        # Hidden text field for storing raw license data (for save/restore)
        self.license_text = QTextEdit()
        self.license_text.setVisible(False)

        # Editable overrides below the read-only display
        license_form = QFormLayout()

        self.license_notes_edit = QLineEdit()
        self.license_notes_edit.setPlaceholderText("Additional license notes or overrides")
        license_form.addRow("Notes:", self.license_notes_edit)

        self.multi_tenant_check = QCheckBox("Multi-tenant requested")
        license_form.addRow("", self.multi_tenant_check)

        self.num_tenants_spin = QSpinBox()
        self.num_tenants_spin.setRange(1, 100)
        self.num_tenants_spin.setEnabled(False)
        self.multi_tenant_check.toggled.connect(self.num_tenants_spin.setEnabled)
        license_form.addRow("Number of Tenants:", self.num_tenants_spin)

        license_layout.addLayout(license_form)
        license_group.setLayout(license_layout)
        layout.addWidget(license_group)

        # ---- Mobile Users (gated) ----
        self.mu_check = QCheckBox("Mobile Users in scope")
        self.mu_check.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        layout.addWidget(self.mu_check)

        self.mu_group = QGroupBox("Mobile Users Details")
        self.mu_group.setVisible(False)
        self.mu_check.toggled.connect(self.mu_group.setVisible)
        mu_form = QFormLayout()

        self.mu_licensed_spin = QSpinBox()
        self.mu_licensed_spin.setRange(-1, 999999)
        self.mu_licensed_spin.setValue(-1)
        self.mu_licensed_spin.setSpecialValueText("Not specified")
        mu_form.addRow("Licensed Remote Workers:", self.mu_licensed_spin)

        self.mu_total_spin = QSpinBox()
        self.mu_total_spin.setRange(-1, 999999)
        self.mu_total_spin.setValue(-1)
        self.mu_total_spin.setSpecialValueText("Not specified")
        mu_form.addRow("Total Mobile Users:", self.mu_total_spin)

        self.mu_3p_spin = QSpinBox()
        self.mu_3p_spin.setRange(-1, 999999)
        self.mu_3p_spin.setValue(-1)
        self.mu_3p_spin.setSpecialValueText("Not specified")
        mu_form.addRow("3rd Party Users:", self.mu_3p_spin)

        # Geographic Distribution - multi-select checkboxes
        geo_widget = QWidget()
        geo_layout = QVBoxLayout(geo_widget)
        geo_layout.setContentsMargins(0, 0, 0, 0)
        geo_layout.setSpacing(2)

        self.mu_geo_checks = {}
        geo_base_row = QGridLayout()
        geo_base_row.setSpacing(8)
        for i, region in enumerate(["Americas", "EMEA", "APAC"]):
            cb = QCheckBox(region)
            geo_base_row.addWidget(cb, 0, i)
            self.mu_geo_checks[region] = cb
        geo_layout.addLayout(geo_base_row)

        # Dynamic sub-region layout (populated from API)
        self.mu_geo_dynamic_layout = QGridLayout()
        self.mu_geo_dynamic_layout.setSpacing(6)
        geo_layout.addLayout(self.mu_geo_dynamic_layout)

        mu_form.addRow("Geographic Distribution:", geo_widget)

        self.mu_device_combo = QComboBox()
        self.mu_device_combo.addItems(["-- Select --", "Managed", "BYOD", "Both"])
        mu_form.addRow("Device Assignment:", self.mu_device_combo)

        # OS Platforms - multi-select checkboxes
        os_widget = QWidget()
        os_layout = QHBoxLayout(os_widget)
        os_layout.setContentsMargins(0, 0, 0, 0)
        os_layout.setSpacing(8)

        self.mu_os_checks = {}
        for platform in ["Windows", "macOS", "Android", "iOS", "ChromeOS", "Linux"]:
            cb = QCheckBox(platform)
            os_layout.addWidget(cb)
            self.mu_os_checks[platform] = cb
        os_layout.addStretch()

        mu_form.addRow("OS Platforms:", os_widget)

        self.mu_connect_combo = QComboBox()
        self.mu_connect_combo.addItems([
            "-- Select --", "Pre-logon + Always-On", "Always-On", "On-demand"
        ])
        mu_form.addRow("Agent Connect Method:", self.mu_connect_combo)

        self.mu_bypass_text = QTextEdit()
        self.mu_bypass_text.setPlaceholderText("Apps/traffic to bypass tunnel (auto-populated from split tunnel config)")
        self.mu_bypass_text.setMaximumHeight(100)
        mu_form.addRow("Bypass/Tunnel Traffic:", self.mu_bypass_text)

        self.mu_hip_edit = QTextEdit()
        self.mu_hip_edit.setPlaceholderText("HIP check details (vendor-specific entries)")
        self.mu_hip_edit.setMaximumHeight(60)
        mu_form.addRow("HIP Check Details:", self.mu_hip_edit)

        self.mu_group.setLayout(mu_form)
        layout.addWidget(self.mu_group)

        # ---- Remote Networks (gated) ----
        self.rn_check = QCheckBox("Remote Networks in scope")
        self.rn_check.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        layout.addWidget(self.rn_check)

        self.rn_group = QGroupBox("Remote Networks Details")
        self.rn_group.setVisible(False)
        self.rn_check.toggled.connect(self.rn_group.setVisible)
        rn_form = QFormLayout()

        self.rn_offices_spin = QSpinBox()
        self.rn_offices_spin.setRange(-1, 99999)
        self.rn_offices_spin.setValue(-1)
        self.rn_offices_spin.setSpecialValueText("Not specified")
        rn_form.addRow("Total Offices:", self.rn_offices_spin)

        self.rn_locations_edit = QLineEdit()
        self.rn_locations_edit.setPlaceholderText("Key office locations")
        rn_form.addRow("Locations:", self.rn_locations_edit)

        self.rn_cpe_edit = QLineEdit()
        self.rn_cpe_edit.setPlaceholderText("e.g., PA-440, PA-450, ISR, etc.")
        rn_form.addRow("CPE Device:", self.rn_cpe_edit)

        self.rn_largest_branch_spin = QSpinBox()
        self.rn_largest_branch_spin.setRange(-1, 99999)
        self.rn_largest_branch_spin.setValue(-1)
        self.rn_largest_branch_spin.setSpecialValueText("Not specified")
        rn_form.addRow("Largest Branch User Count:", self.rn_largest_branch_spin)

        self.rn_circuit_edit = QLineEdit()
        self.rn_circuit_edit.setPlaceholderText("e.g., 100Mbps, 1Gbps")
        rn_form.addRow("Circuit Size:", self.rn_circuit_edit)

        self.rn_bandwidth_edit = QLineEdit()
        self.rn_bandwidth_edit.setPlaceholderText("Bandwidth requirements per site")
        rn_form.addRow("Bandwidth per Site:", self.rn_bandwidth_edit)

        self.rn_group.setLayout(rn_form)
        layout.addWidget(self.rn_group)

        # ---- ZTNA Connectors (gated) ----
        self.ztna_check = QCheckBox("ZTNA Connectors in scope")
        self.ztna_check.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        layout.addWidget(self.ztna_check)

        self.ztna_group = QGroupBox("ZTNA Connector Details")
        self.ztna_group.setVisible(False)
        self.ztna_check.toggled.connect(self.ztna_group.setVisible)
        ztna_form = QFormLayout()

        self.ztna_details_edit = QTextEdit()
        self.ztna_details_edit.setPlaceholderText("ZTNA connector requirements and details")
        self.ztna_details_edit.setMaximumHeight(80)
        ztna_form.addRow("Details:", self.ztna_details_edit)

        self.ztna_group.setLayout(ztna_form)
        layout.addWidget(self.ztna_group)

        # ---- Service Connections ----
        sc_group = QGroupBox("Service Connection Details")
        sc_layout = QVBoxLayout()

        sc_form = QFormLayout()
        self.sc_bgp_edit = QLineEdit()
        self.sc_bgp_edit.setPlaceholderText("BGP attributes for symmetric routing")
        sc_form.addRow("BGP for Symmetric:", self.sc_bgp_edit)
        sc_layout.addLayout(sc_form)

        sc_checks_row = QHBoxLayout()
        self.sc_nat_check = QCheckBox("SC-NAT Feature")
        self.sc_china_check = QCheckBox("China CBL")
        self.sc_premium_check = QCheckBox("Premium Internet")
        sc_checks_row.addWidget(self.sc_nat_check)
        sc_checks_row.addWidget(self.sc_china_check)
        sc_checks_row.addWidget(self.sc_premium_check)
        sc_checks_row.addStretch()
        sc_layout.addLayout(sc_checks_row)

        sc_group.setLayout(sc_layout)
        layout.addWidget(sc_group)

        # ---- Detection & Response ----
        dr_group = QGroupBox("Detection & Response (External Tools)")
        dr_form = QFormLayout()

        # Tool definitions: (key, label, description, common vendors)
        dr_tools = [
            ('siem', 'SIEM', 'Security Information & Event Management', [
                '', 'N/A', 'Splunk', 'Microsoft Sentinel', 'IBM QRadar',
                'Elastic SIEM', 'Exabeam', 'LogRhythm', 'Sumo Logic',
                'Google Chronicle', 'Cortex XSIAM',
            ]),
            ('edr', 'EDR', 'Endpoint Detection & Response', [
                '', 'N/A', 'CrowdStrike Falcon', 'Microsoft Defender for Endpoint',
                'SentinelOne', 'Carbon Black', 'Cortex XDR', 'Cybereason',
                'Trend Micro Vision One',
            ]),
            ('ndr', 'NDR', 'Network Detection & Response', [
                '', 'N/A', 'Darktrace', 'ExtraHop Reveal(x)', 'Vectra AI',
                'Cisco Secure Network Analytics', 'Cortex XDR',
            ]),
            ('cdr', 'CDR', 'Cloud Detection & Response', [
                '', 'N/A', 'Abnormal Security', 'Proofpoint',
                'Microsoft Defender for Cloud', 'Cortex XDR',
            ]),
            ('soar', 'SOAR', 'Security Orchestration, Automation & Response', [
                '', 'N/A', 'Cortex XSOAR', 'Splunk SOAR', 'IBM Resilient',
                'Swimlane', 'Tines', 'Google Chronicle SOAR',
            ]),
            ('tim', 'TIM', 'Threat Intelligence Management', [
                '', 'N/A', 'Cortex XSOAR TIM', 'Recorded Future',
                'Anomali', 'ThreatConnect', 'Mandiant Threat Intelligence',
            ]),
            ('ueba', 'UEBA', 'User & Entity Behavior Analytics', [
                '', 'N/A', 'Exabeam', 'Securonix', 'Microsoft Sentinel UEBA',
                'Splunk UBA', 'Cortex XSIAM',
            ]),
            ('epp_edr', 'EPP/EDR', 'Endpoint Protection Platform', [
                '', 'N/A', 'CrowdStrike Falcon', 'Microsoft Defender',
                'SentinelOne', 'Symantec', 'Trend Micro', 'Cortex XDR',
            ]),
            ('tip', 'TIP', 'Threat Intelligence Platform', [
                '', 'N/A', 'MISP', 'Anomali', 'ThreatConnect',
                'Recorded Future', 'Cortex XSOAR',
            ]),
            ('itdr', 'ITDR', 'Identity Threat Detection & Response', [
                '', 'N/A', 'CrowdStrike Falcon Identity',
                'Microsoft Defender for Identity', 'Silverfort',
                'Semperis', 'Cortex XSIAM',
            ]),
            ('asm', 'ASM', 'Attack Surface Management', [
                '', 'N/A', 'Cortex Xpanse', 'Censys', 'CyCognito',
                'Tenable ASM', 'Mandiant ASM',
            ]),
        ]

        self.dr_fields = {}
        for key, acronym, description, vendors in dr_tools:
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItems(vendors)
            combo.setCurrentIndex(0)
            combo.lineEdit().setPlaceholderText(f"Select or type vendor")
            dr_form.addRow(f"{acronym} ({description}):", combo)
            self.dr_fields[key] = combo

        dr_group.setLayout(dr_form)
        layout.addWidget(dr_group)

        # ---- Cloud Security ----
        cloud_group = QGroupBox("Cloud Security")
        cloud_form = QFormLayout()

        cloud_tools = [
            ('cspm', 'CSPM', 'Cloud Security Posture Management', [
                '', 'N/A', 'Prisma Cloud', 'Wiz', 'Orca Security',
                'Microsoft Defender for Cloud', 'AWS Security Hub',
                'Lacework', 'Aqua Security',
            ]),
            ('ciem', 'CIEM', 'Cloud Infrastructure Entitlement Management', [
                '', 'N/A', 'Prisma Cloud', 'CrowdStrike Falcon Cloud Security',
                'Wiz', 'Ermetic', 'Sonrai Security',
                'Microsoft Entra Permissions Management',
            ]),
            ('dspm', 'DSPM', 'Data Security Posture Management', [
                '', 'N/A', 'Prisma Cloud', 'Dig Security', 'Laminar',
                'Varonis', 'BigID', 'Wiz',
            ]),
            ('asm', 'ASM', 'Attack Surface Management', [
                '', 'N/A', 'Cortex Xpanse', 'Censys', 'CyCognito',
                'Tenable ASM', 'Mandiant ASM', 'Microsoft Defender EASM',
            ]),
            ('cwp', 'CWP', 'Cloud Workload Protection', [
                '', 'N/A', 'Prisma Cloud', 'CrowdStrike Falcon Cloud Security',
                'Aqua Security', 'Sysdig Secure', 'Wiz',
                'Microsoft Defender for Cloud',
            ]),
            ('api_security', 'API Security', 'API Discovery & Protection', [
                '', 'N/A', 'Prisma Cloud', 'Salt Security', 'Noname Security',
                'Traceable AI', 'Wallarm', 'Akamai API Security',
            ]),
            ('ai_spm', 'AI-SPM', 'AI Security Posture Management', [
                '', 'N/A', 'Prisma Cloud', 'Wiz', 'Protect AI',
                'Robust Intelligence', 'CalypsoAI',
            ]),
        ]

        self.cloud_fields = {}
        for key, acronym, description, vendors in cloud_tools:
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItems(vendors)
            combo.setCurrentIndex(0)
            combo.lineEdit().setPlaceholderText("Select or type vendor")
            cloud_form.addRow(f"{acronym} ({description}):", combo)
            self.cloud_fields[key] = combo

        cloud_group.setLayout(cloud_form)
        layout.addWidget(cloud_group)

        # ---- Third-Party Access ----
        tpa_group = QGroupBox("Third-Party Access")
        tpa_form = QFormLayout()

        self.tpa_who_combo = QComboBox()
        self.tpa_who_combo.setEditable(True)
        self.tpa_who_combo.addItems(['', 'Contractors', 'Partners', 'Contractors & Partners'])
        self.tpa_who_combo.lineEdit().setPlaceholderText("Select or type who needs access")
        tpa_form.addRow("Who:", self.tpa_who_combo)

        self.tpa_count_spin = QSpinBox()
        self.tpa_count_spin.setRange(-1, 99999)
        self.tpa_count_spin.setValue(-1)
        self.tpa_count_spin.setSpecialValueText("Not specified")
        tpa_form.addRow("How Many:", self.tpa_count_spin)

        self.tpa_managed_combo = QComboBox()
        self.tpa_managed_combo.addItems(["-- Select --", "Managed", "Unmanaged", "Both"])
        tpa_form.addRow("Managed/Unmanaged:", self.tpa_managed_combo)

        self.tpa_method_combo = QComboBox()
        self.tpa_method_combo.setEditable(True)
        self.tpa_method_combo.addItems(['', 'Web Browser Only', 'Full Tunnel', 'Proxy Only', 'Clientless'])
        self.tpa_method_combo.lineEdit().setPlaceholderText("Select or type connection method")
        tpa_form.addRow("Connection Method:", self.tpa_method_combo)

        tpa_group.setLayout(tpa_form)
        layout.addWidget(tpa_group)

        # ---- Applications ----
        apps_group = QGroupBox("Applications")
        apps_form = QFormLayout()

        genai_widget, self.apps_genai_input, self.apps_genai_list = \
            self._create_list_entry_widget("Type app name and press Add")
        apps_form.addRow("GenAI Apps:", genai_widget)

        saas_widget, self.apps_saas_input, self.apps_saas_list = \
            self._create_list_entry_widget("Type app name and press Add")
        apps_form.addRow("SaaS Apps:", saas_widget)

        self.apps_private_edit = QLineEdit()
        self.apps_private_edit.setPlaceholderText("Private app protocols (e.g., RDP, SSH, HTTP)")
        apps_form.addRow("Private App Protocols:", self.apps_private_edit)

        self.apps_hosting_edit = QLineEdit()
        self.apps_hosting_edit.setPlaceholderText("Hosting environment (on-prem, AWS, Azure, GCP)")
        apps_form.addRow("Hosting:", self.apps_hosting_edit)

        apps_group.setLayout(apps_form)
        layout.addWidget(apps_group)

        # ---- Data Security ----
        ds_group = QGroupBox("Data Security")
        ds_form = QFormLayout()

        # Compliance - multi-select checkboxes + custom entry
        compliance_widget = QWidget()
        compliance_layout = QVBoxLayout(compliance_widget)
        compliance_layout.setContentsMargins(0, 0, 0, 0)

        compliance_frameworks = [
            ('PCI-DSS', 'Payment Card Industry'),
            ('HIPAA', 'Health Insurance Portability'),
            ('SOC 2', 'Service Org Controls'),
            ('SOX', 'Sarbanes-Oxley'),
            ('GDPR', 'EU Data Protection'),
            ('CCPA', 'California Consumer Privacy'),
            ('ISO 27001', 'Info Security Mgmt'),
            ('NIST CSF', 'Cybersecurity Framework'),
            ('NIST 800-53', 'Security & Privacy Controls'),
            ('FedRAMP', 'Federal Cloud Security'),
            ('CMMC', 'Cybersecurity Maturity Model'),
            ('HITRUST', 'Health Info Trust Alliance'),
            ('GLBA', 'Gramm-Leach-Bliley'),
            ('FERPA', 'Education Records Privacy'),
            ('NERC CIP', 'Energy Sector Cybersecurity'),
            ('ITAR', 'Int\'l Traffic in Arms'),
            ('CIS Controls', 'Center for Internet Security'),
            ('StateRAMP', 'State Risk Authorization'),
        ]

        self.compliance_checks = {}
        grid = QGridLayout()
        grid.setSpacing(4)
        cols = 3
        for i, (name, desc) in enumerate(compliance_frameworks):
            cb = QCheckBox(f"{name} ({desc})")
            grid.addWidget(cb, i // cols, i % cols)
            self.compliance_checks[name] = cb
        compliance_layout.addLayout(grid)

        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("Other:"))
        self.ds_compliance_custom = QLineEdit()
        self.ds_compliance_custom.setPlaceholderText("Additional frameworks (comma-separated)")
        custom_row.addWidget(self.ds_compliance_custom)
        compliance_layout.addLayout(custom_row)

        ds_form.addRow("Compliance Requirements:", compliance_widget)

        self.ds_exfil_edit = QTextEdit()
        self.ds_exfil_edit.setPlaceholderText("Data exfiltration channels of concern")
        self.ds_exfil_edit.setMaximumHeight(60)
        ds_form.addRow("Exfiltration Channels:", self.ds_exfil_edit)

        # Classification strategy - checkboxes with descriptions + combination
        classification_widget = QWidget()
        classification_layout = QVBoxLayout(classification_widget)
        classification_layout.setContentsMargins(0, 0, 0, 0)
        classification_layout.setSpacing(2)

        self.classification_checks = {}
        classification_options = [
            ('Manual', 'Human Intent', 'Small teams, high-context docs', 'Inconsistency'),
            ('Automated', 'Data Patterns', 'PII, PCI, and structured data', 'False positives'),
            ('Contextual', 'Environment', 'Departmental silos, workflow-heavy apps', 'Lack of granular detail'),
            ('Combination', 'Multiple methods above', 'Broad coverage across data types', 'Complexity'),
        ]

        cls_grid = QGridLayout()
        cls_grid.setSpacing(2)
        # Header row
        for col, header in enumerate(['', 'Based On', 'Best For', 'Risk']):
            lbl = QLabel(f"<b>{header}</b>")
            lbl.setStyleSheet("font-size: 11px; color: gray;")
            cls_grid.addWidget(lbl, 0, col)

        for i, (name, based_on, best_for, risk) in enumerate(classification_options):
            row = i + 1
            cb = QCheckBox(name)
            cls_grid.addWidget(cb, row, 0)
            cls_grid.addWidget(QLabel(based_on), row, 1)
            cls_grid.addWidget(QLabel(best_for), row, 2)
            risk_lbl = QLabel(risk)
            risk_lbl.setStyleSheet("color: #e65100; font-size: 11px;")
            cls_grid.addWidget(risk_lbl, row, 3)
            self.classification_checks[name] = cb

        classification_layout.addLayout(cls_grid)

        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("Notes:"))
        self.ds_classification_notes = QLineEdit()
        self.ds_classification_notes.setPlaceholderText("Additional classification details")
        custom_row.addWidget(self.ds_classification_notes)
        classification_layout.addLayout(custom_row)

        ds_form.addRow("Classification Strategy:", classification_widget)

        # DLP Policy maturity - radio-style checkboxes with descriptions
        dlp_widget = QWidget()
        dlp_layout = QVBoxLayout(dlp_widget)
        dlp_layout.setContentsMargins(0, 0, 0, 0)
        dlp_layout.setSpacing(4)

        dlp_options = [
            ('Ad-Hoc', 'Reactive',
             'No formal policy. Reacting when things break. '
             'Relying on basic email filters or native SaaS defaults without central oversight.'),
            ('Compliance-Led', 'Foundational',
             'Static, pattern-based rules driven by audit requirements (SOC2, HIPAA). '
             'Scanning for SSNs and credit card numbers. Often high false-positive rates.'),
            ('Risk-Driven', 'Proactive',
             'Crown Jewels identified (IP, source code, trade secrets). '
             'Monitoring high-risk users and key departments. '
             'Granular policies based on metadata and contextual labels.'),
            ('Adaptive', 'Optimized',
             'DLP integrated with IAM and endpoint security. '
             'Policies adjust automatically based on user behavior and device health. '
             'Zero Trust architecture with real-time automated response.'),
        ]

        self.dlp_checks = {}
        for name, stage, description in dlp_options:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)

            cb = QCheckBox()
            cb.setFixedWidth(20)
            row_layout.addWidget(cb)

            label = QLabel(f"<b>{name}</b> <i>({stage})</i>")
            label.setFixedWidth(180)
            row_layout.addWidget(label)

            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #555; font-size: 11px;")
            row_layout.addWidget(desc_label, 1)

            dlp_layout.addWidget(row_widget)
            self.dlp_checks[name] = cb

        dlp_notes_row = QHBoxLayout()
        dlp_notes_row.addWidget(QLabel("Notes:"))
        self.ds_dlp_notes = QLineEdit()
        self.ds_dlp_notes.setPlaceholderText("Additional DLP policy details or requirements")
        dlp_notes_row.addWidget(self.ds_dlp_notes)
        dlp_layout.addLayout(dlp_notes_row)

        ds_form.addRow("DLP Policy Maturity:", dlp_widget)

        ds_group.setLayout(ds_form)
        layout.addWidget(ds_group)

        # ---- Authentication / CIE ----
        auth_group = QGroupBox("Authentication / CIE")
        auth_layout = QVBoxLayout()

        auth_hint = QLabel(
            "Authentication methods and CIE domains are auto-populated from "
            "the tenant pull. Metadata URL and username attribute must be "
            "entered manually."
        )
        auth_hint.setWordWrap(True)
        auth_hint.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        auth_layout.addWidget(auth_hint)

        # Auto-populated: auth methods detected
        auth_auto_form = QFormLayout()

        self.auth_methods_text = QTextEdit()
        self.auth_methods_text.setMaximumHeight(80)
        self.auth_methods_text.setPlaceholderText(
            "Auto-populated from pulled authentication profiles"
        )
        auth_auto_form.addRow("Auth Methods Detected:", self.auth_methods_text)

        # Auto-populated: CIE domains (only visible when CIE detected)
        self.cie_domains_label = QLabel("CIE Domains:")
        self.cie_domains_text = QTextEdit()
        self.cie_domains_text.setMaximumHeight(100)
        self.cie_domains_text.setPlaceholderText(
            "CIE domains auto-populated if Cloud Identity Engine is detected"
        )
        self.cie_domains_label.setVisible(False)
        self.cie_domains_text.setVisible(False)
        auth_auto_form.addRow(self.cie_domains_label, self.cie_domains_text)

        auth_layout.addLayout(auth_auto_form)

        # Manual fields
        auth_manual_form = QFormLayout()

        self.auth_idp_edit = QLineEdit()
        self.auth_idp_edit.setPlaceholderText("e.g., Okta, Azure AD, Ping")
        auth_manual_form.addRow("SAML IdP Vendor:", self.auth_idp_edit)

        self.auth_metadata_edit = QLineEdit()
        self.auth_metadata_edit.setPlaceholderText("IdP metadata URL or details")
        auth_manual_form.addRow("Metadata URL:", self.auth_metadata_edit)

        self.auth_username_edit = QLineEdit()
        self.auth_username_edit.setPlaceholderText("e.g., email, samAccountName, UPN")
        auth_manual_form.addRow("Username Attribute:", self.auth_username_edit)

        auth_layout.addLayout(auth_manual_form)

        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)

        # Navigation
        nav_row = QHBoxLayout()
        prev_btn = QPushButton("<< Previous")
        prev_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        nav_row.addWidget(prev_btn)
        nav_row.addStretch()
        next_btn = QPushButton("Next: Summary + Export >>")
        next_btn.clicked.connect(lambda: self._next_tab(3))
        nav_row.addWidget(next_btn)
        layout.addLayout(nav_row)

        layout.addStretch()

        scroll.setWidget(tab)
        return scroll

    # ========================================================================
    # Tab 4: Summary + Export
    # ========================================================================

    def _create_summary_tab(self) -> QWidget:
        """Create the summary and export tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Completeness check
        self.completeness_group = QGroupBox("Completeness Check")
        completeness_layout = QVBoxLayout()

        self.completeness_label = QLabel("Click 'Refresh' to check completeness.")
        self.completeness_label.setWordWrap(True)
        completeness_layout.addWidget(self.completeness_label)

        refresh_btn = QPushButton("Refresh Completeness Check")
        refresh_btn.clicked.connect(self._refresh_completeness)
        completeness_layout.addWidget(refresh_btn)

        self.completeness_group.setLayout(completeness_layout)
        layout.addWidget(self.completeness_group)

        # Preview
        preview_group = QGroupBox("DoR Data Preview")
        preview_layout = QVBoxLayout()

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(300)
        preview_layout.addWidget(self.preview_text)

        preview_btn_row = QHBoxLayout()
        preview_btn = QPushButton("Generate Preview")
        preview_btn.clicked.connect(self._preview_json)
        preview_btn_row.addWidget(preview_btn)

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        preview_btn_row.addWidget(copy_btn)

        preview_btn_row.addStretch()
        preview_layout.addLayout(preview_btn_row)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Export buttons
        export_group = QGroupBox("Export")
        export_layout = QHBoxLayout()

        save_btn = QPushButton("Save DoR JSON...")
        save_btn.setMinimumHeight(40)
        save_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
            "border-radius: 5px; padding: 8px 20px; }"
            "QPushButton:hover { background-color: #43A047; }"
        )
        save_btn.clicked.connect(self._save_json)
        export_layout.addWidget(save_btn)

        load_btn = QPushButton("Load Existing DoR JSON...")
        load_btn.setMinimumHeight(40)
        load_btn.clicked.connect(self._load_existing)
        export_layout.addWidget(load_btn)

        export_layout.addStretch()

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        # Navigation
        nav_row = QHBoxLayout()
        prev_btn = QPushButton("<< Previous")
        prev_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        nav_row.addWidget(prev_btn)
        nav_row.addStretch()
        layout.addLayout(nav_row)

        layout.addStretch()
        return tab

    # ========================================================================
    # Data Collection from Forms
    # ========================================================================

    def _collect_manual_answers(self) -> Dict[str, Any]:
        """Collect all manual form answers from tabs 2 and 3."""
        manual = {}

        # Tab 2: Environment
        manual['environment'] = {
            'domain': self.domain_combo.currentText(),
            'delivery_model': self.delivery_combo.currentText() if self.delivery_combo.currentIndex() > 0 else None,
            'eval_to_prod_or_net_new': self.eval_combo.currentText() if self.eval_combo.currentIndex() > 0 else None,
            'service_sales_team_member': self.sales_team_edit.text() or None,
            'customer_problems': self.problems_edit.toPlainText() or None,
            'why_current_tech_insufficient': self.why_insufficient_edit.toPlainText() or None,
            'desired_business_outcomes': self.outcomes_edit.toPlainText() or None,
            'identified_use_cases': [x.strip() for x in self.use_cases_edit.toPlainText().split('\n') if x.strip()],
            'critical_capabilities': [x.strip() for x in self.critical_caps_edit.toPlainText().split('\n') if x.strip()],
            'current_state_network_design': self.network_design_edit.toPlainText() or None,
            'additional_current_future_state': self.additional_info_edit.toPlainText() or None,
            'innovation_preview_features': self.innovation_edit.toPlainText() or None,
        }

        # Tab 3: Technical - Tenant Info
        manual['metadata'] = {
            'tenant_name': self.connection_name,
            'tenant_url': self.tenant_url_edit.text() or None,
            'serial_number': self.serial_edit.text() or None,
        }

        manual['license'] = {
            'license_data': self.license_text.toPlainText() or None,
            'license_notes': self.license_notes_edit.text() or None,
            'panorama_managed': self.panorama_managed_label.text() if self.panorama_managed_label.text() != '--' else None,
            'multi_tenant_requested': self.multi_tenant_check.isChecked(),
            'number_of_tenants': self.num_tenants_spin.value() if self.multi_tenant_check.isChecked() else None,
        }
        # Include raw license info from pull if available
        if self._license_info:
            manual['license']['license_info_raw'] = self._license_info

        # Mobile Users
        manual['mobile_users'] = {
            'in_scope': self.mu_check.isChecked(),
        }
        if self.mu_check.isChecked():
            manual['mobile_users'].update({
                'licensed_remote_workers': self.mu_licensed_spin.value() if self.mu_licensed_spin.value() >= 0 else None,
                'total_mobile_users': self.mu_total_spin.value() if self.mu_total_spin.value() >= 0 else None,
                'third_party_users': self.mu_3p_spin.value() if self.mu_3p_spin.value() >= 0 else None,
                'geographic_distribution': [name for name, cb in self.mu_geo_checks.items() if cb.isChecked()] or None,
                'device_assignment': self.mu_device_combo.currentText() if self.mu_device_combo.currentIndex() > 0 else None,
                'os_platforms': [name for name, cb in self.mu_os_checks.items() if cb.isChecked()],
                'agent_connect_method': self.mu_connect_combo.currentText() if self.mu_connect_combo.currentIndex() > 0 else None,
                'bypass_tunnel_traffic': self.mu_bypass_text.toPlainText() or None,
                'hip_check_details': self.mu_hip_edit.toPlainText() or None,
            })
        if self._mu_info:
            manual['mobile_users']['mu_info_raw'] = self._mu_info

        # Remote Networks
        manual['remote_networks'] = {
            'in_scope': self.rn_check.isChecked(),
        }
        if self.rn_check.isChecked():
            manual['remote_networks'].update({
                'total_offices': self.rn_offices_spin.value() if self.rn_offices_spin.value() >= 0 else None,
                'locations': self.rn_locations_edit.text() or None,
                'cpe_device': self.rn_cpe_edit.text() or None,
                'largest_branch_users': self.rn_largest_branch_spin.value() if self.rn_largest_branch_spin.value() >= 0 else None,
                'circuit_size': self.rn_circuit_edit.text() or None,
                'bandwidth_per_site': self.rn_bandwidth_edit.text() or None,
            })

        # ZTNA
        manual['ztna_connectors'] = {
            'in_scope': self.ztna_check.isChecked(),
            'details': self.ztna_details_edit.toPlainText() or None if self.ztna_check.isChecked() else None,
        }

        # Service Connections
        manual['service_connections'] = {
            'sc_nat_feature': self.sc_nat_check.isChecked(),
            'bgp_attributes_symmetric': self.sc_bgp_edit.text() or None,
            'china_cbl': self.sc_china_check.isChecked(),
            'premium_internet': self.sc_premium_check.isChecked(),
        }

        # Detection & Response
        manual['detection_response'] = {}
        for key, combo in self.dr_fields.items():
            val = combo.currentText().strip()
            manual['detection_response'][key] = val if val else None

        # Cloud Security
        manual['cloud_security'] = {}
        for key, combo in self.cloud_fields.items():
            val = combo.currentText().strip()
            manual['cloud_security'][key] = val if val else None

        # Third-Party Access
        manual['third_party_access'] = {
            'who': self.tpa_who_combo.currentText().strip() or None,
            'how_many': self.tpa_count_spin.value() if self.tpa_count_spin.value() >= 0 else None,
            'managed_unmanaged': self.tpa_managed_combo.currentText() if self.tpa_managed_combo.currentIndex() > 0 else None,
            'connection_method': self.tpa_method_combo.currentText().strip() or None,
        }

        # Applications
        manual['applications'] = {
            'genai_apps': self._get_list_items(self.apps_genai_list) or None,
            'saas_apps': self._get_list_items(self.apps_saas_list) or None,
            'private_app_protocols': self.apps_private_edit.text() or None,
            'hosting': self.apps_hosting_edit.text() or None,
        }

        # Data Security
        manual['data_security'] = {
            'compliance_requirements': self._get_selected_compliance(),
            'exfiltration_channels': self.ds_exfil_edit.toPlainText() or None,
            'classification_strategy': self._get_selected_classification(),
            'dlp_policy': self._get_selected_dlp(),
        }

        # Authentication
        manual['authentication'] = {
            'auth_methods_detected': self.auth_methods_text.toPlainText() or None,
            'saml_idp_vendor': self.auth_idp_edit.text() or None,
            'metadata_url': self.auth_metadata_edit.text() or None,
            'username_attribute': self.auth_username_edit.text() or None,
        }
        if self._auth_info:
            manual['authentication']['auth_info_raw'] = self._auth_info

        return manual

    def _generate_dor_json(self) -> Dict[str, Any]:
        """Generate the complete DoR JSON by merging config + manual answers."""
        # Start with base schema
        dor = create_empty_dor_schema()

        # Merge config-derived data
        if self.dor_data.get('config_analysis'):
            dor['config_analysis'] = self.dor_data['config_analysis']

        # Merge manual answers
        manual = self._collect_manual_answers()
        dor = merge_manual_answers(dor, manual)

        # Set generation metadata
        dor['metadata']['generated_at'] = datetime.now().isoformat()
        dor['metadata']['tenant_name'] = self.connection_name

        return dor

    # ========================================================================
    # Summary / Export Actions
    # ========================================================================

    def _refresh_completeness(self):
        """Check and display DoR completeness."""
        dor = self._generate_dor_json()
        missing = validate_dor_completeness(dor)

        if not missing:
            self.completeness_label.setText(
                "<span style='color: green; font-weight: bold;'>"
                "All required fields are complete.</span>"
            )
        else:
            items_html = "".join(f"<li>{m}</li>" for m in missing)
            self.completeness_label.setText(
                f"<span style='color: #e65100; font-weight: bold;'>"
                f"Missing {len(missing)} field(s):</span>"
                f"<ul>{items_html}</ul>"
            )

    def _preview_json(self):
        """Generate and display JSON preview."""
        dor = self._generate_dor_json()
        self.preview_text.setPlainText(json.dumps(dor, indent=2, default=str))

    def _copy_to_clipboard(self):
        """Copy preview JSON to clipboard."""
        from PyQt6.QtWidgets import QApplication
        text = self.preview_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _save_json(self):
        """Save DoR JSON to file."""
        dor = self._generate_dor_json()

        default_name = f"dor_{self.connection_name or 'tenant'}_{datetime.now().strftime('%Y%m%d')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save DoR JSON",
            default_name,
            "JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(dor, f, indent=2, default=str)
                QMessageBox.information(self, "Saved", f"DoR data saved to:\n{file_path}")
                logger.info(f"DoR data saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save:\n{e}")

    def _load_existing(self):
        """Load an existing DoR JSON file and populate forms."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load DoR JSON",
            "",
            "JSON Files (*.json);;All Files (*)",
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Restore data
            self.dor_data = data

            # Restore config analysis
            if data.get('config_analysis'):
                self.analysis_group.setVisible(True)
                self.analysis_text.setPlainText("(Loaded from file)")

            # Restore form fields from loaded data
            self._restore_forms_from_data(data)

            QMessageBox.information(self, "Loaded", f"DoR data loaded from:\n{file_path}")
            logger.info(f"DoR data loaded from {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load:\n{e}")

    def _restore_forms_from_data(self, data: Dict[str, Any]):
        """Restore form fields from loaded DoR data."""
        # Environment
        env = data.get('environment', {})
        self._set_combo(self.domain_combo, env.get('domain', 'SASE'))
        self._set_combo(self.delivery_combo, env.get('delivery_model'))
        self._set_combo(self.eval_combo, env.get('eval_to_prod_or_net_new'))
        self.sales_team_edit.setText(env.get('service_sales_team_member') or '')
        self.problems_edit.setPlainText(env.get('customer_problems') or '')
        self.why_insufficient_edit.setPlainText(env.get('why_current_tech_insufficient') or '')
        self.outcomes_edit.setPlainText(env.get('desired_business_outcomes') or '')
        self.use_cases_edit.setPlainText('\n'.join(env.get('identified_use_cases', [])))
        self.critical_caps_edit.setPlainText('\n'.join(env.get('critical_capabilities', [])))
        self.network_design_edit.setPlainText(env.get('current_state_network_design') or '')
        self.additional_info_edit.setPlainText(env.get('additional_current_future_state') or '')
        self.innovation_edit.setPlainText(env.get('innovation_preview_features') or '')

        # Metadata / Tenant
        meta = data.get('metadata', {})
        self.tenant_url_edit.setText(meta.get('tenant_url') or '')
        self.serial_edit.setText(meta.get('serial_number') or '')

        # License
        lic = data.get('license', {})
        self.license_text.setPlainText(lic.get('license_data') or '')
        self.license_notes_edit.setText(lic.get('license_notes') or '')
        panorama = lic.get('panorama_managed')
        if panorama:
            self.panorama_managed_label.setText(panorama)
            if 'Yes' in panorama:
                self.panorama_managed_label.setStyleSheet("font-weight: bold; color: #e65100;")
            else:
                self.panorama_managed_label.setStyleSheet("font-weight: bold; color: green;")
        self.multi_tenant_check.setChecked(lic.get('multi_tenant_requested', False))
        self.num_tenants_spin.setValue(lic.get('number_of_tenants') or 1)
        # Restore raw license info if available
        if lic.get('license_info_raw'):
            self._license_info = lic['license_info_raw']
            # Rebuild license display from raw data
            licenses = self._license_info.get('licenses', [])
            self._populate_license_display(licenses, self._license_info.get('infra_settings_raw'))

        # Mobile Users
        mu = data.get('mobile_users', {})
        self.mu_check.setChecked(mu.get('in_scope', False))
        self.mu_licensed_spin.setValue(mu.get('licensed_remote_workers') if mu.get('licensed_remote_workers') is not None else -1)
        self.mu_total_spin.setValue(mu.get('total_mobile_users') if mu.get('total_mobile_users') is not None else -1)
        self.mu_3p_spin.setValue(mu.get('third_party_users') if mu.get('third_party_users') is not None else -1)

        # Geographic distribution - handle list (new) and string (legacy)
        for cb in self.mu_geo_checks.values():
            cb.setChecked(False)
        geo = mu.get('geographic_distribution')
        if geo:
            if isinstance(geo, str):
                # Legacy comma-separated string
                geo = [g.strip() for g in geo.split(',') if g.strip()]
            if isinstance(geo, list):
                for region in geo:
                    if region in self.mu_geo_checks:
                        self.mu_geo_checks[region].setChecked(True)
                    else:
                        # Dynamically add unknown regions
                        cb = QCheckBox(region)
                        cb.setStyleSheet("font-size: 11px;")
                        cb.setChecked(True)
                        count = self.mu_geo_dynamic_layout.count()
                        cols = 4
                        self.mu_geo_dynamic_layout.addWidget(cb, count // cols, count % cols)
                        self.mu_geo_checks[region] = cb

        self._set_combo(self.mu_device_combo, mu.get('device_assignment'))

        # OS platforms - handle list (new) and string (legacy comma-separated)
        for cb in self.mu_os_checks.values():
            cb.setChecked(False)
        os_plats = mu.get('os_platforms')
        if os_plats:
            if isinstance(os_plats, str):
                os_plats = [p.strip() for p in os_plats.split(',') if p.strip()]
            if isinstance(os_plats, list):
                for platform in os_plats:
                    if platform in self.mu_os_checks:
                        self.mu_os_checks[platform].setChecked(True)

        # Connect method - map legacy values
        connect_method = mu.get('agent_connect_method')
        if connect_method:
            legacy_map = {
                'Pre-logon': 'Pre-logon + Always-On',
                'User-logon': 'Always-On',
            }
            connect_method = legacy_map.get(connect_method, connect_method)
            # Handle legacy always_on boolean
            always_on = mu.get('always_on', False)
            if always_on and connect_method == 'On-demand':
                connect_method = 'Always-On'
        elif mu.get('always_on', False):
            connect_method = 'Always-On'
        self._set_combo(self.mu_connect_combo, connect_method)

        self.mu_bypass_text.setPlainText(mu.get('bypass_tunnel_traffic') or '')
        self.mu_hip_edit.setPlainText(mu.get('hip_check_details') or '')

        # Restore raw MU info if available
        if mu.get('mu_info_raw'):
            self._mu_info = mu['mu_info_raw']

        # Remote Networks
        rn = data.get('remote_networks', {})
        self.rn_check.setChecked(rn.get('in_scope', False))
        self.rn_offices_spin.setValue(rn.get('total_offices') if rn.get('total_offices') is not None else -1)
        self.rn_locations_edit.setText(rn.get('locations') or '')
        self.rn_cpe_edit.setText(rn.get('cpe_device') or '')
        self.rn_largest_branch_spin.setValue(rn.get('largest_branch_users') if rn.get('largest_branch_users') is not None else -1)
        self.rn_circuit_edit.setText(rn.get('circuit_size') or '')
        self.rn_bandwidth_edit.setText(rn.get('bandwidth_per_site') or '')

        # ZTNA
        ztna = data.get('ztna_connectors', {})
        self.ztna_check.setChecked(ztna.get('in_scope', False))
        self.ztna_details_edit.setPlainText(ztna.get('details') or '')

        # Service Connections
        sc = data.get('service_connections', {})
        self.sc_nat_check.setChecked(sc.get('sc_nat_feature', False))
        self.sc_bgp_edit.setText(sc.get('bgp_attributes_symmetric') or '')
        self.sc_china_check.setChecked(sc.get('china_cbl', False))
        self.sc_premium_check.setChecked(sc.get('premium_internet', False))

        # Detection & Response
        dr = data.get('detection_response', {})
        for key, combo in self.dr_fields.items():
            val = dr.get(key) or ''
            idx = combo.findText(val)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentText(val)

        # Cloud Security
        cs = data.get('cloud_security', {})
        for key, combo in self.cloud_fields.items():
            val = cs.get(key) or ''
            idx = combo.findText(val)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentText(val)

        # Third-Party Access
        tpa = data.get('third_party_access', {})
        who_val = tpa.get('who') or ''
        idx = self.tpa_who_combo.findText(who_val)
        if idx >= 0:
            self.tpa_who_combo.setCurrentIndex(idx)
        else:
            self.tpa_who_combo.setCurrentText(who_val)
        self.tpa_count_spin.setValue(tpa.get('how_many') if tpa.get('how_many') is not None else -1)
        self._set_combo(self.tpa_managed_combo, tpa.get('managed_unmanaged'))
        method_val = tpa.get('connection_method') or ''
        idx = self.tpa_method_combo.findText(method_val)
        if idx >= 0:
            self.tpa_method_combo.setCurrentIndex(idx)
        else:
            self.tpa_method_combo.setCurrentText(method_val)

        # Applications
        apps = data.get('applications', {})
        self._set_list_items(self.apps_genai_list, apps.get('genai_apps') or [])
        self._set_list_items(self.apps_saas_list, apps.get('saas_apps') or [])
        self.apps_private_edit.setText(apps.get('private_app_protocols') or '')
        self.apps_hosting_edit.setText(apps.get('hosting') or '')

        # Data Security
        ds = data.get('data_security', {})
        compliance = ds.get('compliance_requirements')
        # Reset all checkboxes
        for cb in self.compliance_checks.values():
            cb.setChecked(False)
        self.ds_compliance_custom.clear()
        if compliance:
            # Handle both list and legacy comma-separated string
            if isinstance(compliance, str):
                compliance = [c.strip() for c in compliance.split(',') if c.strip()]
            custom_items = []
            for item in compliance:
                if item in self.compliance_checks:
                    self.compliance_checks[item].setChecked(True)
                else:
                    custom_items.append(item)
            if custom_items:
                self.ds_compliance_custom.setText(', '.join(custom_items))
        self.ds_exfil_edit.setPlainText(ds.get('exfiltration_channels') or '')
        classification = ds.get('classification_strategy')
        for cb in self.classification_checks.values():
            cb.setChecked(False)
        self.ds_classification_notes.clear()
        if classification:
            if isinstance(classification, str):
                # Legacy string format
                self.ds_classification_notes.setText(classification)
            elif isinstance(classification, dict):
                for strategy in classification.get('strategies', []):
                    if strategy in self.classification_checks:
                        self.classification_checks[strategy].setChecked(True)
                self.ds_classification_notes.setText(classification.get('notes') or '')
        dlp = ds.get('dlp_policy')
        for cb in self.dlp_checks.values():
            cb.setChecked(False)
        self.ds_dlp_notes.clear()
        if dlp:
            if isinstance(dlp, str):
                # Legacy string format
                self.ds_dlp_notes.setText(dlp)
            elif isinstance(dlp, dict):
                for level in dlp.get('maturity', []):
                    if level in self.dlp_checks:
                        self.dlp_checks[level].setChecked(True)
                self.ds_dlp_notes.setText(dlp.get('notes') or '')

        # Authentication
        auth = data.get('authentication', {})
        self.auth_methods_text.setPlainText(auth.get('auth_methods_detected') or '')
        self.auth_idp_edit.setText(auth.get('saml_idp_vendor') or '')
        self.auth_metadata_edit.setText(auth.get('metadata_url') or auth.get('metadata') or '')
        self.auth_username_edit.setText(auth.get('username_attribute') or '')
        # Restore raw auth info and CIE domain visibility
        if auth.get('auth_info_raw'):
            self._auth_info = auth['auth_info_raw']
            has_cie = self._auth_info.get('has_cie', False)
            self.cie_domains_label.setVisible(has_cie)
            self.cie_domains_text.setVisible(has_cie)
            cie_domains = self._auth_info.get('cie_domains', [])
            if has_cie and cie_domains:
                domain_lines = []
                for d in cie_domains:
                    line = f"{d.get('domain', '?')} ({d.get('type', '?')})"
                    status = d.get('status', '')
                    if status:
                        line += f" - {status}"
                    users = d.get('user_count', 0)
                    groups = d.get('group_count', 0)
                    if users or groups:
                        line += f" [{users} users, {groups} groups]"
                    domain_lines.append(line)
                self.cie_domains_text.setPlainText("\n".join(domain_lines))

    def _create_list_entry_widget(self, placeholder: str = "Type and press Add"):
        """Create a reusable add-to-list widget with input, add/remove buttons, and list."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Input row
        input_row = QHBoxLayout()
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        input_row.addWidget(line_edit)

        add_btn = QPushButton("Add")
        add_btn.setFixedWidth(60)
        input_row.addWidget(add_btn)

        layout.addLayout(input_row)

        # List + remove button
        list_row = QHBoxLayout()
        list_widget = QListWidget()
        list_widget.setMaximumHeight(100)
        list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        list_row.addWidget(list_widget)

        remove_btn = QPushButton("Remove")
        remove_btn.setFixedWidth(60)
        list_row.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addLayout(list_row)

        # Wire up add
        def add_item():
            text = line_edit.text().strip()
            if text:
                list_widget.addItem(text)
                line_edit.clear()

        add_btn.clicked.connect(add_item)
        line_edit.returnPressed.connect(add_item)

        # Wire up remove
        def remove_selected():
            for item in list_widget.selectedItems():
                list_widget.takeItem(list_widget.row(item))

        remove_btn.clicked.connect(remove_selected)

        return widget, line_edit, list_widget

    def _get_list_items(self, list_widget: QListWidget) -> list:
        """Get all items from a QListWidget as a list of strings."""
        return [list_widget.item(i).text() for i in range(list_widget.count())]

    def _set_list_items(self, list_widget: QListWidget, items):
        """Populate a QListWidget from a list of strings or newline-separated text."""
        list_widget.clear()
        if isinstance(items, str):
            # Legacy: newline-separated text
            for line in items.split('\n'):
                line = line.strip()
                if line:
                    list_widget.addItem(line)
        elif isinstance(items, list):
            for item in items:
                if item:
                    list_widget.addItem(str(item))

    def _get_selected_compliance(self):
        """Get selected compliance frameworks as a list."""
        selected = [name for name, cb in self.compliance_checks.items() if cb.isChecked()]
        custom = self.ds_compliance_custom.text().strip()
        if custom:
            selected.extend([c.strip() for c in custom.split(',') if c.strip()])
        return selected or None

    def _get_selected_classification(self):
        """Get selected classification strategies as a dict."""
        selected = [name for name, cb in self.classification_checks.items() if cb.isChecked()]
        notes = self.ds_classification_notes.text().strip()
        if not selected and not notes:
            return None
        result = {'strategies': selected}
        if notes:
            result['notes'] = notes
        return result

    def _get_selected_dlp(self):
        """Get selected DLP policy maturity as a dict."""
        selected = [name for name, cb in self.dlp_checks.items() if cb.isChecked()]
        notes = self.ds_dlp_notes.text().strip()
        if not selected and not notes:
            return None
        result = {'maturity': selected}
        if notes:
            result['notes'] = notes
        return result

    def _set_combo(self, combo: QComboBox, value):
        """Set a combo box to a value, falling back to index 0 if not found."""
        if value:
            idx = combo.findText(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    # ========================================================================
    # Tab Navigation with Auto-Save
    # ========================================================================

    def _next_tab(self, target_index: int):
        """Navigate to next tab, saving state."""
        self.save_state(self.tabs.currentIndex())
        self.tabs.setCurrentIndex(target_index)

    # ========================================================================
    # State Persistence
    # ========================================================================

    def _get_state_dir(self) -> Path:
        """Get the directory for DoR state files."""
        state_dir = Path.home() / ".pa_config_lab" / "dor_states"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    def save_state(self, current_tab: int = None):
        """Save current workflow state to file for later resume."""
        if current_tab is None:
            current_tab = self.tabs.currentIndex()

        # Determine filename from tenant name
        tenant = self.connection_name or 'unnamed'
        # Sanitize for filename
        safe_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in tenant)
        state_filename = f"dor_state_{safe_name}.json"

        # Collect manual answers
        manual = self._collect_manual_answers()

        # Save pulled config to a separate file if we have one
        config_path = None
        if self.pulled_config and not self._config_file_path:
            config_dir = self._get_state_dir() / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = str(config_dir / f"dor_config_{safe_name}.json")
            try:
                self.pulled_config.save_to_file(config_path)
                self._config_file_path = config_path
            except Exception as e:
                logger.warning(f"Failed to save config for state persistence: {e}")
                config_path = None
        elif self._config_file_path:
            config_path = self._config_file_path

        state = {
            'version': '1.0',
            'tenant_name': self.connection_name,
            'saved_at': datetime.now().isoformat(),
            'last_tab': current_tab,
            'connection_name': self.connection_name,
            'pulled_config_path': config_path,
            'manual_answers': manual,
            'dor_data': self.dor_data,
            'license_info': self._license_info,
            'auth_info': self._auth_info,
            'mu_info': self._mu_info,
        }

        state_path = self._get_state_dir() / state_filename
        try:
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
            logger.info(f"Saved DoR state to {state_path}")
            # Refresh side button states (resume button may now be enabled)
            self._update_side_button_states()
        except Exception as e:
            logger.error(f"Failed to save DoR state: {e}")

    def load_state(self, state_path: Path) -> bool:
        """Load a saved DoR workflow state."""
        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.connection_name = state.get('connection_name')
            self.dor_data = state.get('dor_data', create_empty_dor_schema())
            self._license_info = state.get('license_info')
            self._auth_info = state.get('auth_info')
            self._mu_info = state.get('mu_info')

            # Restore manual answers to forms
            manual = state.get('manual_answers', {})
            if manual:
                # Build a merged data dict for form restoration
                restore_data = dict(self.dor_data)
                restore_data.update(manual)
                self._restore_forms_from_data(restore_data)

            # Restore pulled config if path exists
            config_path = state.get('pulled_config_path')
            if config_path and Path(config_path).exists():
                try:
                    from config.models.containers import Configuration
                    self.pulled_config = Configuration.load_from_file(
                        config_path, strict=False, on_error='warn'
                    )
                    self._config_file_path = config_path

                    # Re-run analysis
                    self._analyze_config()
                    self.answer_from_config_btn.setEnabled(True)
                    self.pull_status.setText(
                        f"Restored config: {len(self.pulled_config.get_all_items())} items"
                    )
                    self.pull_status.setStyleSheet("color: green;")
                    logger.info(f"Restored config from {config_path}")
                except Exception as e:
                    logger.warning(f"Failed to restore config from {config_path}: {e}")

            # Auto-connect to the saved tenant
            if self.connection_name:
                self._auto_connect_tenant(self.connection_name)

            # Navigate to last tab
            last_tab = state.get('last_tab', 0)
            self.tabs.setCurrentIndex(last_tab)

            logger.info(f"Loaded DoR state: tenant={self.connection_name}, tab={last_tab}")
            return True

        except Exception as e:
            logger.error(f"Failed to load DoR state: {e}")
            return False

    def _auto_connect_tenant(self, tenant_name: str):
        """
        Auto-select and connect to a tenant by name in the tenant selector.

        Finds the tenant in the dropdown and triggers the connection.
        If the tenant is not found in saved tenants, shows a status message.
        """
        if not tenant_name:
            return

        # Find the tenant in the dropdown and select it (triggers connection)
        combo = self.tenant_selector.tenant_combo
        for i in range(combo.count()):
            if combo.itemText(i) == tenant_name:
                logger.info(f"Auto-connecting to saved tenant: {tenant_name}")
                combo.setCurrentIndex(i)
                return

        # Tenant not found in dropdown — show info, don't block workflow
        logger.warning(f"Saved tenant '{tenant_name}' not found in tenant list")
        self.pull_status.setText(
            f"Tenant '{tenant_name}' not in saved list — "
            f"select manually to re-connect"
        )
        self.pull_status.setStyleSheet("color: #e65100;")

    def _get_saved_states(self) -> list:
        """Get list of saved DoR states with metadata."""
        state_dir = self._get_state_dir()
        states = []

        for state_file in sorted(state_dir.glob("dor_state_*.json"), reverse=True):
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                states.append({
                    'path': state_file,
                    'tenant_name': data.get('tenant_name', 'Unknown'),
                    'saved_at': data.get('saved_at', ''),
                    'last_tab': data.get('last_tab', 0),
                })
            except Exception:
                continue

        return states

    def _check_saved_states(self):
        """Check for saved states on startup and offer to resume."""
        states = self._get_saved_states()
        if states:
            # Don't auto-show dialog; let File menu or explicit call handle it
            pass

    def _show_resume_dialog(self):
        """Show dialog to resume a saved DoR questionnaire."""
        states = self._get_saved_states()
        if not states:
            QMessageBox.information(
                self, "No Saved States",
                "No saved DoR questionnaires found."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Resume DoR Questionnaire")
        dialog.setMinimumSize(500, 350)
        dlg_layout = QVBoxLayout(dialog)

        dlg_layout.addWidget(QLabel("Select a saved DoR questionnaire to resume:"))

        list_widget = QListWidget()
        tab_names = ["Tenant + Pull", "Environment", "Technical", "Summary + Export"]
        for state in states:
            tab_idx = state.get('last_tab', 0)
            tab_label = tab_names[tab_idx] if tab_idx < len(tab_names) else f"Tab {tab_idx}"
            saved_at = state.get('saved_at', '')
            # Format date for display
            try:
                dt = datetime.fromisoformat(saved_at)
                date_str = dt.strftime("%m/%d/%Y %I:%M %p")
            except Exception:
                date_str = saved_at

            item_text = f"{state['tenant_name']} - Last: {tab_label} - {date_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, state['path'])
            list_widget.addItem(item)

        dlg_layout.addWidget(list_widget)

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)

        # Delete button
        delete_btn = btn_box.addButton("Delete", QDialogButtonBox.ButtonRole.DestructiveRole)
        delete_btn.clicked.connect(lambda: self._delete_saved_state(list_widget, states))

        dlg_layout.addWidget(btn_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = list_widget.currentItem()
            if selected:
                state_path = selected.data(Qt.ItemDataRole.UserRole)
                self.load_state(Path(state_path))

    def _delete_saved_state(self, list_widget: QListWidget, states: list):
        """Delete a saved DoR state."""
        selected = list_widget.currentItem()
        if not selected:
            return

        reply = QMessageBox.question(
            self, "Delete State",
            "Delete this saved DoR questionnaire?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            state_path = selected.data(Qt.ItemDataRole.UserRole)
            try:
                Path(state_path).unlink()
                row = list_widget.row(selected)
                list_widget.takeItem(row)
                logger.info(f"Deleted DoR state: {state_path}")
            except Exception as e:
                logger.error(f"Failed to delete state: {e}")

    # ========================================================================
    # API Client Management
    # ========================================================================

    def set_api_client(self, api_client, connection_name: str):
        """Set API client from main window connection."""
        self.api_client = api_client
        self.connection_name = connection_name
        self.pull_btn.setEnabled(api_client is not None)

    def has_unsaved_work(self) -> bool:
        """Check if there is unsaved work."""
        # Check if any manual fields have been filled
        manual = self._collect_manual_answers()
        for section_key, section_data in manual.items():
            if isinstance(section_data, dict):
                for key, val in section_data.items():
                    if val and val not in (False, [], 'SASE'):
                        return True
        return self.pulled_config is not None

    def clear_state(self):
        """Clear all state."""
        self.pulled_config = None
        self.dor_data = create_empty_dor_schema()
        self.manual_answers = {}
        self._config_file_path = None
        self._pull_worker = None
        self._license_info = None
        self._auth_info = None
        self._mu_info = None
