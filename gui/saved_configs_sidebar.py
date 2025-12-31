"""
Saved Configurations Sidebar Widget.

This widget provides a sidebar for viewing, loading, and managing saved configurations.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QMessageBox,
    QInputDialog,
    QLineEdit,
    QFileDialog,
    QMenu,
    QToolButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from gui.saved_configs_manager import SavedConfigsManager


class SavedConfigsSidebar(QWidget):
    """Sidebar widget for managing saved configurations."""

    # Signals
    config_loaded = pyqtSignal(dict)  # Emitted when config is loaded
    config_list_updated = pyqtSignal()  # Emitted when list needs refresh

    def __init__(self, parent=None):
        """Initialize the saved configs sidebar."""
        super().__init__(parent)
        
        self.manager = SavedConfigsManager()
        self._init_ui()
        self._refresh_list()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header with hamburger menu button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header = QLabel("<b>Saved Configurations</b>")
        header.setStyleSheet("font-size: 13px; padding: 5px;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Hamburger menu button
        self.menu_button = QToolButton()
        self.menu_button.setText("☰")
        self.menu_button.setStyleSheet(
            "QToolButton { font-size: 18px; padding: 2px 8px; border: none; background: transparent; }"
            "QToolButton:hover { background-color: #E3F2FD; border-radius: 3px; }"
            "QToolButton:pressed { background-color: #BBDEFB; }"
        )
        self.menu_button.setToolTip("Right-click on a config or click here for options")
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu_button.clicked.connect(self._show_hamburger_menu)
        header_layout.addWidget(self.menu_button)
        
        layout.addLayout(header_layout)
        
        # Error banner (initially hidden)
        self.error_banner = QLabel()
        self.error_banner.setWordWrap(True)
        self.error_banner.setStyleSheet(
            "QLabel {"
            "    background-color: #f8d7da;"
            "    color: #721c24;"
            "    border: 1px solid #f5c6cb;"
            "    border-radius: 4px;"
            "    padding: 10px;"
            "    margin: 5px 0;"
            "}"
        )
        self.error_banner.setVisible(False)
        layout.addWidget(self.error_banner)

        # Config list
        self.config_list = QListWidget()
        self.config_list.setStyleSheet(
            "QListWidget { border: 1px solid #ccc; border-radius: 3px; }"
            "QListWidget::item { padding: 8px; }"
            "QListWidget::item:selected { background-color: #2196F3; color: white; }"
            "QListWidget::item:hover:!selected { background-color: #E3F2FD; }"  # Only hover when NOT selected
            "QListWidget::item:selected:hover { background-color: #2196F3; color: white; }"  # Keep blue when selected+hover
        )
        self.config_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.config_list.customContextMenuRequested.connect(self._show_context_menu)
        self.config_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.config_list)

        # Info label
        self.info_label = QLabel("No configurations saved")
        self.info_label.setStyleSheet("color: gray; font-size: 11px; padding: 5px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Action buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(5)

        load_btn = QPushButton("📂 Load Selected")
        load_btn.setToolTip("Load the selected configuration")
        load_btn.clicked.connect(self._load_selected)
        btn_layout.addWidget(load_btn)

        import_btn = QPushButton("📥 Import Config")
        import_btn.setToolTip("Import a configuration from file")
        import_btn.clicked.connect(self._import_config)
        btn_layout.addWidget(import_btn)

        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.setToolTip("Refresh the list of saved configurations")
        refresh_btn.clicked.connect(self._refresh_list)
        btn_layout.addWidget(refresh_btn)

        layout.addLayout(btn_layout)

    def _refresh_list(self):
        """Refresh the list of saved configurations."""
        self.config_list.clear()
        
        configs = self.manager.list_configs()
        
        if not configs:
            self.info_label.setText("No configurations saved")
            return
        
        for config in configs:
            # Format item text
            name = config["name"]
            modified = config["modified"].strftime("%Y-%m-%d %H:%M")
            size_kb = config["size"] / 1024
            encrypted = "🔒" if config["encrypted"] else "📄"
            
            item_text = f"{encrypted} {name}\n   {modified} • {size_kb:.1f} KB"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, config)
            self.config_list.addItem(item)
        
        self.info_label.setText(f"{len(configs)} configuration(s) saved")
        self.config_list_updated.emit()

    def _get_selected_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected configuration metadata."""
        current_item = self.config_list.currentItem()
        if not current_item:
            return None
        return current_item.data(Qt.ItemDataRole.UserRole)

    def _load_selected(self):
        """Load the selected configuration."""
        # Clear any previous errors
        self.error_banner.setVisible(False)
        
        config_meta = self._get_selected_config()
        if not config_meta:
            QMessageBox.information(self, "No Selection", "Please select a configuration to load.")
            return
        
        name = config_meta["name"]
        is_encrypted = config_meta["encrypted"]
        
        # Get password if encrypted
        password = None
        if is_encrypted:
            password, ok = QInputDialog.getText(
                self,
                "Password Required",
                f"Enter password for '{name}':",
                QLineEdit.EchoMode.Password
            )
            if not ok or not password:
                return
        
        # Load config
        success, config, message = self.manager.load_config(name, password)
        
        if success:
            # Clear error banner on success
            self.error_banner.setVisible(False)
            # No success dialog - just emit the config
            self.config_loaded.emit(config)
        else:
            # Show error in banner instead of dialog
            self.error_banner.setText(f"❌ {message}")
            self.error_banner.setVisible(True)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on item."""
        self._load_selected()

    def _import_config(self):
        """Import a configuration from file."""
        # Clear any previous errors
        self.error_banner.setVisible(False)
        
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import Configuration",
            str(self.manager.base_dir),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not filepath:
            return
        
        # Get name for imported config
        name, ok = QInputDialog.getText(
            self,
            "Import Name",
            "Enter a name for the imported configuration:",
            text=Path(filepath).stem
        )
        
        if not ok or not name:
            return
        
        # Check if encrypted
        with open(filepath, 'rb') as f:
            first_bytes = f.read(16)
            is_encrypted = not (first_bytes.startswith(b'{') or first_bytes.startswith(b'{\n'))
        
        # Get password if encrypted
        password = None
        if is_encrypted:
            password, ok = QInputDialog.getText(
                self,
                "Password Required",
                f"Enter password for encrypted file:",
                QLineEdit.EchoMode.Password
            )
            if not ok:
                return
        
        # Import
        success, config, message = self.manager.import_config(filepath, name, password)
        
        if success:
            # Clear error banner on success
            self.error_banner.setVisible(False)
            # No success dialog - just refresh and emit
            self._refresh_list()
            if config:
                self.config_loaded.emit(config)
        else:
            # Show error in banner instead of dialog
            self.error_banner.setText(f"❌ {message}")
            self.error_banner.setVisible(True)

    def _show_context_menu(self, position):
        """Show context menu for config item."""
        item = self.config_list.itemAt(position)
        if not item:
            return
        
        config_meta = item.data(Qt.ItemDataRole.UserRole)
        name = config_meta["name"]
        
        menu = self._create_config_menu(name)
        menu.exec(self.config_list.mapToGlobal(position))
    
    def _show_hamburger_menu(self):
        """Show hamburger menu for selected config."""
        config_meta = self._get_selected_config()
        if not config_meta:
            QMessageBox.information(self, "No Selection", "Please select a configuration first.")
            return
        
        name = config_meta["name"]
        menu = self._create_config_menu(name)
        
        # Show menu below the hamburger button
        button_pos = self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft())
        menu.exec(button_pos)
    
    def _create_config_menu(self, name: str) -> QMenu:
        """Create the context menu for a configuration."""
        menu = QMenu(self)
        
        load_action = QAction("📂 Load", self)
        load_action.triggered.connect(self._load_selected)
        menu.addAction(load_action)
        
        menu.addSeparator()
        
        rename_action = QAction("✏️ Rename", self)
        rename_action.triggered.connect(lambda: self._rename_config(name))
        menu.addAction(rename_action)
        
        export_action = QAction("📤 Export", self)
        export_action.triggered.connect(lambda: self._export_config(name))
        menu.addAction(export_action)
        
        menu.addSeparator()
        
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(lambda: self._delete_config(name))
        menu.addAction(delete_action)
        
        return menu

    def _rename_config(self, old_name: str):
        """Rename a configuration."""
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Configuration",
            f"Enter new name for '{old_name}':",
            text=old_name
        )
        
        if not ok or not new_name or new_name == old_name:
            return
        
        success, message = self.manager.rename_config(old_name, new_name)
        
        if success:
            # No success dialog - just refresh the list
            self._refresh_list()
        else:
            QMessageBox.warning(self, "Rename Failed", message)

    def _export_config(self, name: str):
        """Export a configuration to file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Configuration",
            f"{name}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not filepath:
            return
        
        success, message = self.manager.export_config(name, filepath)
        
        if success:
            # No success dialog - file is saved
            pass
        else:
            QMessageBox.warning(self, "Export Failed", message)

    def _delete_config(self, name: str):
        """Delete a configuration."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        success, message = self.manager.delete_config(name)
        
        if success:
            # No success dialog - just refresh the list
            self._refresh_list()
        else:
            QMessageBox.warning(self, "Delete Failed", message)

    def _get_password_with_confirmation(self, config_name: str) -> Optional[str]:
        """
        Show a dialog to get password and confirmation in one dialog.
        
        Args:
            config_name: Name of the config being encrypted
        
        Returns:
            Password if successful, None if cancelled or mismatch
        """
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Encryption Password")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        label = QLabel(f"Enter a password to encrypt '{config_name}':")
        layout.addWidget(label)
        
        # Password field
        password_label = QLabel("Password:")
        layout.addWidget(password_label)
        
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(password_input)
        
        # Confirm password field
        confirm_label = QLabel("Confirm Password:")
        layout.addWidget(confirm_label)
        
        confirm_input = QLineEdit()
        confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(confirm_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            password = password_input.text()
            confirm = confirm_input.text()
            
            if password != confirm:
                QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
                return None
            
            return password
        
        return None  # User cancelled
    
    def save_current_config(
        self,
        config: Dict[str, Any],
        default_name: Optional[str] = None,
        encrypt: bool = True
    ) -> bool:
        """
        Save the current configuration.

        Args:
            config: Configuration to save
            default_name: Default name for the config
            encrypt: Whether to encrypt the config

        Returns:
            True if saved successfully
        """
        # Get name from config metadata if not provided
        if default_name is None:
            default_name = config.get("metadata", {}).get("saved_name", "")
            if not default_name:
                default_name = f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Show combined save dialog
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QDialogButtonBox
        from PyQt6.QtCore import QTimer
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Save Configuration")
        dialog.setMinimumWidth(450)
        
        layout = QVBoxLayout(dialog)
        
        # Status label (hidden by default, shown for success/error)
        status_label = QLabel()
        status_label.setWordWrap(True)
        status_label.setStyleSheet("padding: 10px; border-radius: 4px; font-weight: bold;")
        status_label.hide()
        layout.addWidget(status_label)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Name field
        name_input = QLineEdit()
        name_input.setText(default_name)
        name_input.selectAll()
        form_layout.addRow("Configuration Name*:", name_input)
        
        # Password fields (if encrypting)
        password_input = None
        confirm_input = None
        if encrypt:
            password_input = QLineEdit()
            password_input.setEchoMode(QLineEdit.EchoMode.Password)
            password_input.setPlaceholderText("Enter encryption password")
            form_layout.addRow("Password*:", password_input)
            
            confirm_input = QLineEdit()
            confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
            confirm_input.setPlaceholderText("Confirm password")
            form_layout.addRow("Confirm Password*:", confirm_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)
        
        # Handle save
        def on_save():
            name = name_input.text().strip()
            if not name:
                status_label.setText("⚠ Please enter a configuration name")
                status_label.setStyleSheet("background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 4px; font-weight: bold;")
                status_label.show()
                return
            
            # Validate password if encrypting
            password = None
            if encrypt:
                password = password_input.text()
                confirm = confirm_input.text()
                
                if not password:
                    status_label.setText("⚠ Please enter a password")
                    status_label.setStyleSheet("background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 4px; font-weight: bold;")
                    status_label.show()
                    return
                
                if password != confirm:
                    status_label.setText("⚠ Passwords do not match")
                    status_label.setStyleSheet("background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 4px; font-weight: bold;")
                    status_label.show()
                    return
            
            # Try to save
            success, message = self.manager.save_config(config, name, password, overwrite=False)
            
            if success:
                # Show success message
                status_label.setText(f"✓ Configuration saved as '{name}'")
                status_label.setStyleSheet("background-color: #e8f5e9; color: #2e7d32; padding: 10px; border-radius: 4px; font-weight: bold;")
                status_label.show()
                
                # Refresh list
                self._refresh_list()
                
                # Close dialog after 1 second
                QTimer.singleShot(1000, dialog.accept)
            else:
                # Check if it's an overwrite situation
                if "already exists" in message:
                    reply = QMessageBox.question(
                        dialog,
                        "Overwrite?",
                        f"Configuration '{name}' already exists. Overwrite it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        success, message = self.manager.save_config(config, name, password, overwrite=True)
                        if success:
                            # Show success message
                            status_label.setText(f"✓ Configuration saved as '{name}'")
                            status_label.setStyleSheet("background-color: #e8f5e9; color: #2e7d32; padding: 10px; border-radius: 4px; font-weight: bold;")
                            status_label.show()
                            
                            # Refresh list
                            self._refresh_list()
                            
                            # Close dialog after 1 second
                            QTimer.singleShot(1000, dialog.accept)
                        else:
                            # Show error
                            status_label.setText(f"✗ {message}")
                            status_label.setStyleSheet("background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 4px; font-weight: bold;")
                            status_label.show()
                else:
                    # Show error
                    status_label.setText(f"✗ {message}")
                    status_label.setStyleSheet("background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 4px; font-weight: bold;")
                    status_label.show()
        
        buttons.button(QDialogButtonBox.StandardButton.Save).clicked.connect(on_save)
        buttons.rejected.connect(dialog.reject)
        
        # Show dialog
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
