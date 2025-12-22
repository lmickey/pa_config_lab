#!/usr/bin/env python3
"""
Script to reorganize POV workflow tabs.
This modifies gui/workflows/pov_workflow.py to match the new structure.
"""

import re
from pathlib import Path

def reorganize_pov_workflow():
    """Reorganize the POV workflow file."""
    
    filepath = Path("gui/workflows/pov_workflow.py")
    
    if not filepath.exists():
        print(f"Error: {filepath} not found")
        return False
    
    print(f"Reading {filepath}...")
    content = filepath.read_text()
    
    # 1. Update the steps label
    old_steps = (
        '"<b>POV Configuration Steps:</b> "\n'
        '            "1️⃣ Configure Sources → 2️⃣ Review → 3️⃣ Inject Defaults → "\n'
        '            "4️⃣ Configure Firewall → 5️⃣ Configure Prisma Access"'
    )
    new_steps = (
        '"<b>POV Configuration Steps:</b> "\n'
        '            "1️⃣ Load Sources → 2️⃣ Firewall Defaults → 3️⃣ Prisma Access Defaults → "\n'
        '            "4️⃣ Configure Firewall → 5️⃣ Configure Prisma Access → 6️⃣ Review & Execute"'
    )
    
    if old_steps in content:
        content = content.replace(old_steps, new_steps)
        print("✓ Updated steps label")
    
    # 2. Update tab creation order in _init_ui
    old_tab_order = (
        "        self._create_sources_tab()  # Step 1: Load Sources\n"
        "        self._create_firewall_defaults_tab()  # Step 2: Firewall Defaults  \n"
        "        self._create_prisma_defaults_tab()  # Step 3: Prisma Access Defaults\n"
        "        self._create_firewall_tab()  # Step 4: Configure Firewall\n"
        "        self._create_prisma_tab()  # Step 5: Configure Prisma Access\n"
        "        self._create_review_tab()  # Step 6: Review & Execute"
    )
    
    # Find where the old tabs are created
    pattern = r"        self\._create_sources_tab\(\).*?\n.*?self\._create_review_tab\(\).*?\n.*?self\._create_defaults_tab\(\).*?\n.*?self\._create_firewall_tab\(\).*?\n.*?self\._create_prisma_tab\(\)"
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, old_tab_order.rstrip(), content, flags=re.DOTALL)
        print("✓ Updated tab creation order")
    
    # 3. Update tab labels
    content = content.replace('self.tabs.addTab(tab, "1. Sources")', 'self.tabs.addTab(tab, "1️⃣ Load Sources")')
    content = content.replace('self.tabs.addTab(tab, "2. Review")', '# MOVED TO END')
    content = content.replace('self.tabs.addTab(tab, "3. Defaults")', '# DELETED - REPLACED')
    content = content.replace('self.tabs.addTab(tab, "4. Firewall")', 'self.tabs.addTab(tab, "4️⃣ Firewall Setup")')
    content = content.replace('self.tabs.addTab(tab, "5. Prisma Access")', 'self.tabs.addTab(tab, "5️⃣ Prisma Access Setup")')
    
    print("✓ Updated tab labels")
    
    # Save
    filepath.write_text(content)
    print(f"✓ Saved changes to {filepath}")
    
    return True

if __name__ == "__main__":
    success = reorganize_pov_workflow()
    if success:
        print("\n✅ POV workflow reorganization complete!")
        print("Next steps:")
        print("1. Remove old _create_defaults_tab() method")
        print("2. Add new _create_firewall_defaults_tab() method")
        print("3. Add new _create_prisma_defaults_tab() method")
        print("4. Update _create_review_tab() and move to end")
        print("5. Update all navigation indices")
    else:
        print("\n❌ Reorganization failed")
