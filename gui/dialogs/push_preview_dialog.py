"""
Push preview dialog for reviewing changes before push.

This dialog fetches destination configurations and shows real conflicts
and new items that will be pushed.
"""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QLabel,
    QDialogButtonBox,
    QTabWidget,
    QWidget,
    QTextEdit,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class ConfigFetchWorker(QThread):
    """Worker thread to fetch destination configurations."""
    
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(object)  # destination_config
    error = pyqtSignal(str)  # error message
    
    def __init__(self, api_client, selected_items):
        super().__init__()
        self.api_client = api_client
        self.selected_items = selected_items
    
    def run(self):
        """Fetch configurations from destination tenant."""
        try:
            print(f"\n=== ConfigFetchWorker.run() starting ===")
            print(f"API Client: {self.api_client}")
            print(f"Selected items keys: {list(self.selected_items.keys())}")
            for key, value in self.selected_items.items():
                if isinstance(value, dict):
                    print(f"  {key}: {list(value.keys())} ({sum(len(v) for v in value.values() if isinstance(v, list))} items)")
                elif isinstance(value, list):
                    print(f"  {key}: {len(value)} items")
                else:
                    print(f"  {key}: {value}")
            
            dest_config = {
                'folders': {},
                'snippets': {},
                'objects': {},
                'infrastructure': {}
            }
            
            total_items = 0
            for category in ['folders', 'snippets', 'objects', 'infrastructure']:
                items = self.selected_items.get(category, [])
                if isinstance(items, dict):
                    total_items += sum(len(v) for v in items.values() if isinstance(v, list))
                else:
                    total_items += len(items)
            
            print(f"Total items to check: {total_items}")
            current = 0
            
            # Fetch folders
            folders = self.selected_items.get('folders', [])
            if folders:
                self.progress.emit(f"Checking folders...", int((current / max(total_items, 1)) * 100))
                try:
                    print(f"  Fetching folders using get_security_policy_folders()")
                    existing_folders = self.api_client.get_security_policy_folders()
                    print(f"    Found {len(existing_folders)} existing folders")
                    for folder in existing_folders:
                        folder_name = folder.get('name')
                        if folder_name:
                            dest_config['folders'][folder_name] = folder
                            print(f"      - {folder_name}")
                except Exception as e:
                    print(f"    ERROR fetching folders: {e}")
                    import traceback
                    traceback.print_exc()
                current += len(folders)
            
            # Fetch snippets
            snippets = self.selected_items.get('snippets', [])
            if snippets:
                self.progress.emit(f"Checking snippets...", int((current / max(total_items, 1)) * 100))
                try:
                    print(f"  Fetching snippets using get_security_policy_snippets()")
                    existing_snippets = self.api_client.get_security_policy_snippets()
                    print(f"    Found {len(existing_snippets)} existing snippets")
                    for snippet in existing_snippets:
                        snippet_name = snippet.get('name')
                        if snippet_name:
                            dest_config['snippets'][snippet_name] = snippet
                            print(f"      - {snippet_name}")
                except Exception as e:
                    print(f"    ERROR fetching snippets: {e}")
                    import traceback
                    traceback.print_exc()
                current += len(snippets)
            
            # Fetch objects
            objects = self.selected_items.get('objects', {})
            if objects:
                self.progress.emit(f"Checking objects...", int((current / max(total_items, 1)) * 100))
                
                # Map object types to API client methods
                object_method_map = {
                    'address_objects': 'get_all_addresses',
                    'address_groups': 'get_all_address_groups',
                    'service_objects': 'get_all_services',
                    'service_groups': 'get_all_service_groups',
                    'applications': 'get_all_applications',
                    'application_groups': None,  # Not implemented yet
                }
                
                for obj_type, obj_list in objects.items():
                    if not isinstance(obj_list, list):
                        continue
                    
                    print(f"  Checking {obj_type}: {len(obj_list)} items")
                    method_name = object_method_map.get(obj_type)
                    if method_name and hasattr(self.api_client, method_name):
                        try:
                            print(f"    Calling API method: {method_name}")
                            method = getattr(self.api_client, method_name)
                            existing_objects = method()
                            print(f"    Found {len(existing_objects)} existing items")
                            
                            if obj_type not in dest_config['objects']:
                                dest_config['objects'][obj_type] = {}
                            
                            for obj in existing_objects:
                                obj_name = obj.get('name')
                                if obj_name:
                                    dest_config['objects'][obj_type][obj_name] = obj
                                    print(f"      - {obj_name}")
                        except Exception as e:
                            print(f"    ERROR fetching {obj_type}: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"    No API method for {obj_type}")
                    
                    current += len(obj_list)
            
            # Fetch infrastructure components
            infrastructure = self.selected_items.get('infrastructure', {})
            print(f"\nInfrastructure to check: {list(infrastructure.keys()) if infrastructure else 'None'}")
            if infrastructure:
                self.progress.emit(f"Checking infrastructure...", int((current / max(total_items, 1)) * 100))
                
                # Map infrastructure types to API client methods
                infra_method_map = {
                    'remote_networks': 'get_all_remote_networks',
                    'service_connections': 'get_all_service_connections',
                    'ipsec_tunnels': 'get_all_ipsec_tunnels',
                    'ike_gateways': 'get_all_ike_gateways',
                    'ike_crypto_profiles': 'get_all_ike_crypto_profiles',
                    'ipsec_crypto_profiles': 'get_all_ipsec_crypto_profiles',
                }
                
                for infra_type, infra_list in infrastructure.items():
                    if not isinstance(infra_list, list):
                        print(f"  Skipping {infra_type} - not a list")
                        continue
                    
                    print(f"  Checking {infra_type}: {len(infra_list)} items")
                    method_name = infra_method_map.get(infra_type)
                    if method_name and hasattr(self.api_client, method_name):
                        try:
                            print(f"    Calling API method: {method_name}")
                            method = getattr(self.api_client, method_name)
                            existing_items = method()
                            print(f"    Found {len(existing_items)} existing items")
                            
                            if infra_type not in dest_config['infrastructure']:
                                dest_config['infrastructure'][infra_type] = {}
                            
                            for item in existing_items:
                                item_name = item.get('name', item.get('id'))
                                if item_name:
                                    dest_config['infrastructure'][infra_type][item_name] = item
                                    print(f"      - {item_name}")
                        except Exception as e:
                            # Continue even if fetch fails (endpoint might not be available)
                            print(f"    ERROR fetching {infra_type}: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"    No API method for {infra_type} (method: {method_name})")
                    
                    current += len(infra_list)
            
            self.progress.emit("Analysis complete", 100)
            print(f"\n=== ConfigFetchWorker.run() complete ===")
            print(f"Destination config keys: {list(dest_config.keys())}")
            for key, value in dest_config.items():
                if isinstance(value, dict):
                    print(f"  {key}: {len(value)} items")
                    for subkey in list(value.keys())[:5]:  # Show first 5
                        print(f"    - {subkey}")
            print("=" * 50)
            self.finished.emit(dest_config)
            
        except Exception as e:
            print(f"\n=== ConfigFetchWorker ERROR ===")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            print("=" * 50)
            self.error.emit(f"Error fetching destination config: {str(e)}")


class PushPreviewDialog(QDialog):
    """Dialog for previewing push operation before execution."""
    
    def __init__(self, api_client, selected_items: Dict[str, Any], destination_name: str, conflict_resolution: str, parent=None):
        """Initialize the push preview dialog.
        
        Args:
            api_client: API client for destination tenant
            selected_items: Dictionary of selected components to push
            destination_name: Name of destination tenant
            conflict_resolution: Conflict resolution strategy (SKIP, OVERWRITE, RENAME)
            parent: Parent widget
        """
        super().__init__(parent)
        self.api_client = api_client
        self.selected_items = selected_items
        self.destination_name = destination_name
        self.conflict_resolution = conflict_resolution
        self.destination_config = None
        self.worker = None
        
        self.setWindowTitle("Push Preview - Analyzing...")
        self.resize(900, 650)
        
        self._init_ui()
        self._start_fetch()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"<h2>Push Preview: {self.destination_name}</h2>")
        layout.addWidget(header)
        
        info = QLabel(
            f"Analyzing destination tenant for conflicts...<br>"
            f"<b>Conflict Resolution:</b> {self.conflict_resolution}"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Progress section (shown during fetch)
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        
        self.progress_label = QLabel("Fetching destination configurations...")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_widget)
        
        # Tabs for conflict analysis (hidden until fetch complete)
        self.tabs = QTabWidget()
        self.tabs.setVisible(False)
        
        # Conflicts tab
        conflicts_widget = QWidget()
        conflicts_layout = QVBoxLayout(conflicts_widget)
        
        self.conflicts_tree = QTreeWidget()
        self.conflicts_tree.setHeaderLabels(["Component", "Type", "Action"])
        self.conflicts_tree.setColumnWidth(0, 400)
        self.conflicts_tree.setColumnWidth(1, 150)
        conflicts_layout.addWidget(self.conflicts_tree)
        
        self.tabs.addTab(conflicts_widget, "⚠️ Conflicts")
        
        # New items tab
        new_items_widget = QWidget()
        new_items_layout = QVBoxLayout(new_items_widget)
        
        self.new_items_tree = QTreeWidget()
        self.new_items_tree.setHeaderLabels(["Component", "Type", "Action"])
        self.new_items_tree.setColumnWidth(0, 400)
        self.new_items_tree.setColumnWidth(1, 150)
        new_items_layout.addWidget(self.new_items_tree)
        
        self.tabs.addTab(new_items_widget, "✨ New Items")
        
        layout.addWidget(self.tabs)
        
        # Action summary at bottom
        self.action_label = QLabel()
        self.action_label.setStyleSheet(
            "padding: 10px; background-color: #FFF3E0; border-radius: 5px; font-weight: bold;"
        )
        self.action_label.setWordWrap(True)
        self.action_label.setVisible(False)
        layout.addWidget(self.action_label)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # Style the OK button to be more prominent
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("✓ Proceed with Push")
        self.ok_button.setEnabled(False)  # Disabled until analysis complete
        self.ok_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("✗ Cancel")
        
        layout.addWidget(self.button_box)
    
    def _start_fetch(self):
        """Start fetching destination configurations."""
        self.worker = ConfigFetchWorker(self.api_client, self.selected_items)
        self.worker.progress.connect(self._on_fetch_progress)
        self.worker.finished.connect(self._on_fetch_finished)
        self.worker.error.connect(self._on_fetch_error)
        self.worker.start()
    
    def _on_fetch_progress(self, message: str, percentage: int):
        """Handle fetch progress updates."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(percentage)
    
    def _on_fetch_error(self, error: str):
        """Handle fetch errors."""
        self.progress_label.setText(f"Error: {error}")
        self.progress_label.setStyleSheet("color: red;")
        # Still allow proceeding even if fetch fails
        self.ok_button.setEnabled(True)
    
    def _on_fetch_finished(self, destination_config: Dict):
        """Handle fetch completion and analyze conflicts."""
        self.destination_config = destination_config
        
        # Update progress to show completion
        self.progress_label.setText("✓ Destination configuration loaded - Analyzing conflicts...")
        self.progress_label.setStyleSheet("color: green; font-weight: bold;")
        self.progress_bar.setValue(100)
        
        # Brief delay to show completion message
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self._show_analysis)
    
    def _show_analysis(self):
        """Show the analysis results after brief delay."""
        # Hide progress, show tabs
        self.progress_widget.setVisible(False)
        self.tabs.setVisible(True)
        self.action_label.setVisible(True)
        
        # Update window title
        self.setWindowTitle("Push Preview - Analysis Complete")
        
        # Analyze conflicts
        self._analyze_and_populate()
        
        # Enable proceed button
        self.ok_button.setEnabled(True)
    
    def _analyze_and_populate(self):
        """Analyze conflicts and populate trees."""
        conflicts = []
        new_items = []
        
        # Built-in folders that should not be created
        BUILTIN_FOLDERS = {
            'Prisma Access',
            'Mobile Users', 
            'Remote Networks',
            'Service Connections',
            'Mobile Users Container',
            'Mobile Users Explicit Proxy'
        }
        
        # Analyze folders - skip built-in folders
        for folder in self.selected_items.get('folders', []):
            name = folder.get('name', 'Unknown')
            
            # Skip built-in folders entirely
            if name in BUILTIN_FOLDERS:
                continue
                
            if name in self.destination_config.get('folders', {}):
                conflicts.append(('folder', name, folder))
            else:
                new_items.append(('folder', name, folder))
        
        # Analyze snippets
        for snippet in self.selected_items.get('snippets', []):
            name = snippet.get('name', 'Unknown')
            if name in self.destination_config.get('snippets', {}):
                conflicts.append(('snippet', name, snippet))
            else:
                new_items.append(('snippet', name, snippet))
        
        # Analyze objects
        for obj_type, obj_list in self.selected_items.get('objects', {}).items():
            if not isinstance(obj_list, list):
                continue
            dest_objects = self.destination_config.get('objects', {}).get(obj_type, {})
            for obj in obj_list:
                name = obj.get('name', 'Unknown')
                if name in dest_objects:
                    conflicts.append((obj_type, name, obj))
                else:
                    new_items.append((obj_type, name, obj))
        
        # Analyze infrastructure
        for infra_type, infra_list in self.selected_items.get('infrastructure', {}).items():
            if not isinstance(infra_list, list):
                continue
            dest_infra = self.destination_config.get('infrastructure', {}).get(infra_type, {})
            for item in infra_list:
                name = item.get('name', item.get('id', 'Unknown'))
                if name in dest_infra:
                    conflicts.append((infra_type, name, item))
                else:
                    new_items.append((infra_type, name, item))
        
        # Populate conflicts tree
        self.conflicts_tree.clear()
        if not conflicts:
            no_conflicts = QTreeWidgetItem(self.conflicts_tree, ["✓ No Conflicts Detected", "", ""])
            no_conflicts.setForeground(0, Qt.GlobalColor.darkGreen)
            font = no_conflicts.font(0)
            font.setBold(True)
            no_conflicts.setFont(0, font)
        else:
            # Group by type
            conflict_groups = {}
            for item_type, name, item in conflicts:
                if item_type not in conflict_groups:
                    conflict_groups[item_type] = []
                conflict_groups[item_type].append((name, item))
            
            for item_type, items in conflict_groups.items():
                action = self.conflict_resolution
                type_item = QTreeWidgetItem(
                    self.conflicts_tree,
                    [item_type.replace('_', ' ').title(), "Conflict", f"{len(items)} items - {action}"]
                )
                type_item.setExpanded(True)
                
                for name, item in items:
                    action_text = {
                        'SKIP': 'Will be skipped',
                        'OVERWRITE': 'Will be overwritten',
                        'RENAME': 'Will be renamed'
                    }.get(self.conflict_resolution, 'Unknown')
                    
                    item_widget = QTreeWidgetItem(type_item, [name, item_type, action_text])
                    
                    # Color code by action
                    if self.conflict_resolution == 'OVERWRITE':
                        item_widget.setForeground(2, Qt.GlobalColor.red)
                    elif self.conflict_resolution == 'RENAME':
                        item_widget.setForeground(2, Qt.GlobalColor.blue)
                    else:
                        item_widget.setForeground(2, Qt.GlobalColor.gray)
        
        # Populate new items tree
        self.new_items_tree.clear()
        if not new_items:
            no_new = QTreeWidgetItem(self.new_items_tree, ["No new items to create", "", ""])
            no_new.setForeground(0, Qt.GlobalColor.gray)
        else:
            # Group by type
            new_groups = {}
            for item_type, name, item in new_items:
                if item_type not in new_groups:
                    new_groups[item_type] = []
                new_groups[item_type].append((name, item))
            
            for item_type, items in new_groups.items():
                type_item = QTreeWidgetItem(
                    self.new_items_tree,
                    [item_type.replace('_', ' ').title(), "New", f"{len(items)} items"]
                )
                type_item.setExpanded(True)
                
                for name, item in items:
                    item_widget = QTreeWidgetItem(type_item, [name, item_type, "Will be created"])
                    item_widget.setForeground(2, Qt.GlobalColor.darkGreen)
        
        # Update action label
        total = len(conflicts) + len(new_items)
        conflict_text = f"{len(conflicts)} conflict{'s' if len(conflicts) != 1 else ''}" if conflicts else "no conflicts"
        new_text = f"{len(new_items)} new item{'s' if len(new_items) != 1 else ''}" if new_items else "no new items"
        
        self.action_label.setText(
            f"📊 Ready to push: {conflict_text}, {new_text} ({total} total items)"
        )
