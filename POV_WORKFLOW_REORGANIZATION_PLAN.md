# POV Workflow Reorganization - Implementation Guide

## Overview

Due to the complexity of the 1220-line `pov_workflow.py` file, this document provides the implementation plan for reorganizing the POV workflow.

## Required Changes

### 1. Tab Sequence (Update `_init_ui`)

**Current Order:**
1. Sources
2. Review  
3. Inject Defaults
4. Firewall
5. Prisma Access

**New Order:**
1. Load Sources
2. Firewall Defaults (NEW)
3. Prisma Access Defaults (NEW - replaces old "Inject Defaults")
4. Configure Firewall
5. Configure Prisma Access
6. Review & Execute (MOVED from #2)

### 2. Remove Old Defaults Tab

Delete the `_create_defaults_tab()` method entirely (lines ~417-538). This tab had:
- ADEM Monitoring
- Local DNS
- ZTNA

These Prisma Access-related defaults will be moved to the new "Prisma Access Defaults" tab.

### 3. Create Firewall Defaults Tab (NEW - Step 2)

**Method:** `_create_firewall_defaults_tab()`

**Location:** Insert after `_create_sources_tab()` (after line ~357)

**Content:**
- Title: "Step 2: Firewall Default Configurations"
- Two checkboxes:
  1. **🛡️ Basic Firewall Policy**
     - Internet access rule (Trust → Untrust)
     - Inbound RDP rule to .10 address  
     - Address objects for .10 host
  2. **🔄 Basic NAT Policy**
     - Outbound PAT for internet
     - Inbound static NAT for RDP to .10

- **Status Label:** `self.fw_defaults_status` - Shows warning if FW data not available
- **Preview/Apply buttons**
- Navigation: Back to Sources | Skip | Next to Prisma Defaults

**Key Logic:**
```python
def _update_fw_defaults_status(self):
    """Check if firewall data exists and show status."""
    has_fw_data = self.config_data.get('fwData') is not None
    if not has_fw_data and (self.fw_policy_check.isChecked() or self.fw_nat_check.isChecked()):
        self.fw_defaults_status.setText(
            "⚠️ Firewall configuration required. Please load firewall data in Step 1 (via Manual Entry or other source)."
        )
        self.fw_defaults_status.setVisible(True)
    else:
        self.fw_defaults_status.setVisible(False)
```

### 4. Create Prisma Access Defaults Tab (NEW - Step 3)

**Method:** `_create_prisma_defaults_tab()`

**Location:** Insert after `_create_firewall_defaults_tab()`

**Content:**
- Title: "Step 3: Prisma Access Default Configurations"
- Three checkboxes:
  1. **🔌 Service Connection** (requires FW data)
     - IPSec tunnel to firewall
     - BGP peering
     - Route advertisements
  2. **🌐 Remote Network** (requires FW data)
     - Remote network configuration
     - Subnets and routing
     - Firewall integration
  3. **📱 Mobile User Configuration** (always available)
     - GlobalProtect gateway
     - Authentication
     - Split tunnel settings

- **Status Label:** `self.pa_defaults_status` - Shows warning if Service Conn or Remote Network checked without FW data
- **Preview/Apply buttons**
- Navigation: Back to FW Defaults | Skip | Next to Configure Firewall

**Key Logic:**
```python
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
        # Optionally disable these checkboxes
        # self.service_conn_check.setEnabled(False)
        # self.remote_network_check.setEnabled(False)
    else:
        self.pa_defaults_status.setVisible(False)
```

### 5. Move Review Tab to End (Step 6)

**Method:** `_create_review_tab()` - Already exists, just needs:

1. **Update Title:** "Step 6: Review Configuration & Execute"
2. **Update Description:** "Review the complete configuration before executing..."
3. **Update Navigation:**
   - Back button → Index 4 (Prisma Access Setup)
   - Replace "Next" with "🚀 Execute POV Setup" button
4. **Update Tab Label:** "6️⃣ Review & Execute"

### 6. Update Step Indicator

Update the steps label in `_init_ui` (around line 98):

```python
steps_label = QLabel(
    "<b>POV Configuration Steps:</b> "
    "1️⃣ Load Sources → 2️⃣ Firewall Defaults → 3️⃣ Prisma Access Defaults → "
    "4️⃣ Configure Firewall → 5️⃣ Configure Prisma Access → 6️⃣ Review & Execute"
)
```

### 7. Update Tab Creation Order in `_init_ui`

```python
self._create_sources_tab()  # Step 1
self._create_firewall_defaults_tab()  # Step 2 (NEW)
self._create_prisma_defaults_tab()  # Step 3 (NEW)
self._create_firewall_tab()  # Step 4
self._create_prisma_tab()  # Step 5
self._create_review_tab()  # Step 6 (MOVED)
```

### 8. Update All Tab Indices in Navigation

After reordering, update these navigation button indices:
- Sources (tab 0) → Next goes to 1 (Firewall Defaults)
- Firewall Defaults (tab 1) → Back to 0, Next to 2
- Prisma Defaults (tab 2) → Back to 1, Next to 3
- Firewall Setup (tab 3) → Back to 2, Next to 4
- Prisma Setup (tab 4) → Back to 3, Next to 5
- Review (tab 5) → Back to 4, Execute POV Setup

### 9. Implement Preview/Apply Methods

**For Firewall Defaults:**
```python
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
    # Check if FW data exists
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
    # Apply defaults to self.config_data
    
    QMessageBox.information(
        self,
        "Defaults Applied",
        f"Applied {len(selected)} firewall default configuration(s)."
    )
```

**For Prisma Access Defaults:**
```python
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
    # Check FW data for service conn / remote network
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
    # Apply defaults to self.config_data
    
    QMessageBox.information(
        self,
        "Defaults Applied",
        f"Applied {len(selected)} Prisma Access default configuration(s)."
    )
```

### 10. Update Config Load Method

In `_load_and_merge_config()`, after merging configs, call the status update methods:

```python
# Store merged config
self.config_data = merged_config

# Update defaults status
self._update_fw_defaults_status()
self._update_pa_defaults_status()

# Update UI...
```

## Implementation Checklist

- [ ] Update `_init_ui` tab creation order
- [ ] Update steps label text
- [ ] Delete old `_create_defaults_tab()` method
- [ ] Create `_create_firewall_defaults_tab()` method
- [ ] Create `_create_prisma_defaults_tab()` method
- [ ] Move `_create_review_tab()` to end and update it
- [ ] Update all navigation button indices (0→1, 1→2, etc.)
- [ ] Implement `_update_fw_defaults_status()` method
- [ ] Implement `_update_pa_defaults_status()` method
- [ ] Implement `_preview_firewall_defaults()` method
- [ ] Implement `_apply_firewall_defaults()` method
- [ ] Implement `_preview_prisma_defaults()` method
- [ ] Implement `_apply_prisma_defaults()` method
- [ ] Call status update methods in `_load_and_merge_config()`
- [ ] Test GUI navigation flow
- [ ] Test FW data detection
- [ ] Test checkbox enablement logic

## Testing Scenarios

1. **No FW Data:**
   - Load only SPOV or JSON (no manual entry)
   - Go to Firewall Defaults → Check firewall policy → See warning
   - Go to Prisma Defaults → Check service connection → See warning

2. **With FW Data:**
   - Load manual entry with firewall details
   - Go to Firewall Defaults → No warnings
   - Go to Prisma Defaults → Service Conn/Remote Network enabled

3. **Navigation:**
   - Verify all "Next" and "Back" buttons go to correct tabs
   - Verify "Skip" buttons work
   - Verify final "Execute" button

4. **Preview/Apply:**
   - Preview each default → See correct descriptions
   - Apply defaults → Verify config updated
   - Apply without selection → See "no selection" message

## Files to Reference

- `config/defaults/default_configs.py` - Default configuration templates
- `config/defaults/default_detector.py` - Logic for detecting which defaults are applicable
- `configure_firewall.py` - Firewall configuration logic
- `configure_service_connection.py` - Service connection logic

---

**Status:** Ready for manual implementation
**Est. Time:** 2-3 hours
**Complexity:** Medium-High (large file, many navigation updates)
