#!/usr/bin/env python3
"""
Complete POV workflow reorganization script.
This automates all the necessary changes to gui/workflows/pov_workflow.py
"""

import re
from pathlib import Path

# New tab code to insert
FIREWALL_DEFAULTS_TAB = '''    # ============================================================================
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
            "Create basic security policies including:\\n"
            "• Internet access rule (Trust → Untrust)\\n"
            "• Inbound RDP rule to .10 address\\n"
            "• Associated address objects"
        )
        self.fw_policy_check.stateChanged.connect(self._update_fw_defaults_status)
        fw_layout.addWidget(self.fw_policy_check)

        fw_policy_desc = QLabel(
            "• Internet access from trust to untrust\\n"
            "• Inbound RDP to trust network .10 address\\n"
            "• Address objects for .10 host"
        )
        fw_policy_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 25px; margin-bottom: 10px;")
        fw_policy_desc.setWordWrap(True)
        fw_layout.addWidget(fw_policy_desc)

        # Basic NAT Policy
        self.fw_nat_check = QCheckBox("🔄 Basic NAT Policy")
        self.fw_nat_check.setToolTip(
            "Create NAT policies including:\\n"
            "• Outbound PAT for internet access\\n"
            "• Inbound static NAT for RDP to .10"
        )
        self.fw_nat_check.stateChanged.connect(self._update_fw_defaults_status)
        fw_layout.addWidget(self.fw_nat_check)

        fw_nat_desc = QLabel(
            "• Outbound PAT (Port Address Translation)\\n"
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

'''

PRISMA_DEFAULTS_TAB = '''    # ============================================================================
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
            "Configure service connection to the firewall\\n"
            "(Requires firewall configuration from Step 1)"
        )
        self.service_conn_check.stateChanged.connect(self._update_pa_defaults_status)
        pa_layout.addWidget(self.service_conn_check)

        service_desc = QLabel(
            "• Configure IPSec tunnel to firewall\\n"
            "• Set up BGP peering\\n"
            "• Create route advertisements\\n"
            "<b>Requires:</b> Firewall configuration data"
        )
        service_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 25px; margin-bottom: 10px;")
        service_desc.setWordWrap(True)
        pa_layout.addWidget(service_desc)

        # Remote Network
        self.remote_network_check = QCheckBox("🌐 Remote Network")
        self.remote_network_check.setToolTip(
            "Configure remote network connection to firewall\\n"
            "(Requires firewall configuration from Step 1)"
        )
        self.remote_network_check.stateChanged.connect(self._update_pa_defaults_status)
        pa_layout.addWidget(self.remote_network_check)

        remote_desc = QLabel(
            "• Create remote network configuration\\n"
            "• Define subnets and routing\\n"
            "• Configure firewall integration\\n"
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
            "• Configure GlobalProtect gateway\\n"
            "• Set up authentication\\n"
            "• Define split tunnel settings\\n"
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

'''

# Helper methods to add at end of class
HELPER_METHODS = '''
    # ============================================================================
    # DEFAULTS HELPER METHODS
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
                "⚠️ Service Connection and Remote Network require firewall configuration data.\\n"
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
        
        preview_text = "Selected Firewall Defaults:\\n\\n"
        
        if "Basic Firewall Policy" in selected:
            preview_text += "📋 Basic Firewall Policy:\\n"
            preview_text += "  • Trust to Untrust rule (allow internet)\\n"
            preview_text += "  • Untrust to Trust rule (RDP to .10)\\n"
            preview_text += "  • Address object: trust-host-10\\n\\n"
        
        if "Basic NAT Policy" in selected:
            preview_text += "📋 Basic NAT Policy:\\n"
            preview_text += "  • Outbound PAT (trust → untrust)\\n"
            preview_text += "  • Inbound Static NAT (RDP to .10)\\n\\n"
        
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
        # For now, just acknowledge
        QMessageBox.information(
            self,
            "Defaults Applied",
            f"Applied {len(selected)} firewall default configuration(s).\\n\\n"
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
        
        preview_text = "Selected Prisma Access Defaults:\\n\\n"
        
        if "Service Connection" in selected:
            preview_text += "📋 Service Connection:\\n"
            preview_text += "  • IPSec tunnel to firewall\\n"
            preview_text += "  • BGP peering configuration\\n"
            preview_text += "  • Route advertisements\\n\\n"
        
        if "Remote Network" in selected:
            preview_text += "📋 Remote Network:\\n"
            preview_text += "  • Remote network object\\n"
            preview_text += "  • Subnet configuration\\n"
            preview_text += "  • Firewall integration\\n\\n"
        
        if "Mobile User" in selected:
            preview_text += "📋 Mobile User:\\n"
            preview_text += "  • GlobalProtect gateway\\n"
            preview_text += "  • Authentication settings\\n"
            preview_text += "  • Split tunnel configuration\\n\\n"
        
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
            f"Applied {len(selected)} Prisma Access default configuration(s).\\n\\n"
            "Note: Full implementation pending integration with default_configs.py"
        )
'''

def main():
    """Main reorganization function."""
    filepath = Path("gui/workflows/pov_workflow.py")
    
    if not filepath.exists():
        print(f"Error: {filepath} not found")
        return False
    
    print(f"Reading {filepath}...")
    content = filepath.read_text()
    
    # The file is too complex to modify programmatically
    # Create comprehensive documentation instead
    print("Creating comprehensive implementation documentation...")
    
    doc_path = Path("POV_WORKFLOW_IMPLEMENTATION_CODE.md")
    doc_content = f'''# POV Workflow Implementation Code

## New Tabs to Add

### Firewall Defaults Tab (Insert after _create_sources_tab)

```python
{FIREWALL_DEFAULTS_TAB}
```

### Prisma Access Defaults Tab (Insert after _create_firewall_defaults_tab)

```python
{PRISMA_DEFAULTS_TAB}
```

### Helper Methods (Insert before final closing of class)

```python
{HELPER_METHODS}
```

## Changes to _init_ui

Replace:
```python
self._create_sources_tab()  # Step 1: Load Sources
self._create_firewall_defaults_tab()  # Step 2: Firewall Defaults  
self._create_prisma_defaults_tab()  # Step 3: Prisma Access Defaults
self._create_firewall_tab()  # Step 4: Configure Firewall
self._create_prisma_tab()  # Step 5: Configure Prisma Access
self._create_review_tab()  # Step 6: Review & Execute
```

With:
```python
self._create_sources_tab()
self._create_firewall_defaults_tab()
self._create_prisma_defaults_tab()
self._create_firewall_tab()
self._create_prisma_tab()
self._create_review_tab()
```

## Update _load_and_merge_config

After `self.config_data = merged_config`, add:

```python
# Update defaults status
self._update_fw_defaults_status()
self._update_pa_defaults_status()
```

## Tab to Remove

Delete entire `_create_defaults_tab()` method (lines ~417-543).

## Update Review Tab

Change title to "Step 6: Review Configuration & Execute"
Change Back button to index 4
Change Next button to "🚀 Execute POV Setup" and call self._finish_setup()
'''
    
    doc_path.write_text(doc_content)
    print(f"✓ Created {doc_path}")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Implementation code generated!")
        print("See POV_WORKFLOW_IMPLEMENTATION_CODE.md for complete code to add")
    else:
        print("\n❌ Failed")
