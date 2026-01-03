"""
Load Configuration Dialog.

Provides a dialog for loading saved configurations with file list,
advanced options, and password decryption.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QFileDialog,
    QAbstractItemView,
)
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QColor, QIcon

from config.utils.encryption import (
    is_encrypted_file,
    get_config_metadata,
    load_config_from_file,
)
from .password_dialog import PasswordDialog

logger = logging.getLogger(__name__)


class LoadConfigDialog(QDialog):
    """Dialog for loading saved configurations."""
    
    SAVED_FOLDER = "saved"
    MAX_PASSWORD_ATTEMPTS = 3
    
    def __init__(self, parent=None):
        """
        Initialize load configuration dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.settings = QSettings("PrismaAccess", "ConfigManager")
        self.loaded_config = None
        self.loaded_metadata = None
        self.ignore_defaults = True
        
        self._init_ui()
        self._load_file_list()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Load Configuration")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Load Configuration</h2>")
        layout.addWidget(title)
        
        # File list
        list_group = QGroupBox("Saved Configurations")
        list_layout = QVBoxLayout()
        
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["Name", "Date", "Size", "Encrypted"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.file_table.doubleClicked.connect(self._load_selected)
        self.file_table.itemSelectionChanged.connect(self._on_selection_changed)
        
        list_layout.addWidget(self.file_table)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_file_list)
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        list_layout.addLayout(refresh_layout)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Advanced options (collapsible)
        self.advanced_group = QGroupBox("Advanced Options")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        advanced_layout = QVBoxLayout()
        
        self.ignore_defaults_check = QCheckBox("Ignore default configurations when loading")
        self.ignore_defaults_check.setChecked(True)
        self.ignore_defaults_check.setToolTip(
            "When enabled, default/system configurations will be filtered out after loading"
        )
        advanced_layout.addWidget(self.ignore_defaults_check)
        
        self.validate_check = QCheckBox("Validate configuration after loading")
        self.validate_check.setChecked(False)
        self.validate_check.setToolTip(
            "Run validation checks on the loaded configuration"
        )
        advanced_layout.addWidget(self.validate_check)
        
        self.advanced_group.setLayout(advanced_layout)
        layout.addWidget(self.advanced_group)
        
        # Selected file info
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #666; font-size: 11px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)
        button_layout.addWidget(browse_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.load_btn = QPushButton("Load")
        self.load_btn.setDefault(True)
        self.load_btn.setEnabled(False)
        self.load_btn.clicked.connect(self._load_selected)
        button_layout.addWidget(self.load_btn)
        
        layout.addLayout(button_layout)
    
    def _load_file_list(self):
        """Load list of saved configuration files."""
        self.file_table.setRowCount(0)
        self.file_data = []  # Store file info for each row
        
        # Get saved folder path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        saved_path = os.path.join(base_path, self.SAVED_FOLDER)
        
        if not os.path.exists(saved_path):
            logger.info(f"Saved folder does not exist: {saved_path}")
            return
        
        # List files
        files = []
        for filename in os.listdir(saved_path):
            if filename.endswith(('.pac', '.json')):
                file_path = os.path.join(saved_path, filename)
                files.append(file_path)
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Populate table
        for file_path in files:
            try:
                metadata = get_config_metadata(file_path)
                if metadata is None:
                    metadata = {}
                
                # Get file info
                stat = os.stat(file_path)
                file_size = self._format_size(stat.st_size)
                mod_time = datetime.fromtimestamp(stat.st_mtime)
                
                # Get display name
                name = metadata.get("name", os.path.basename(file_path))
                date_str = mod_time.strftime("%Y-%m-%d %H:%M")
                encrypted = metadata.get("encrypted", is_encrypted_file(file_path))
                
                # Add row
                row = self.file_table.rowCount()
                self.file_table.insertRow(row)
                
                # Name
                name_item = QTableWidgetItem(name)
                name_item.setToolTip(file_path)
                self.file_table.setItem(row, 0, name_item)
                
                # Date
                date_item = QTableWidgetItem(date_str)
                self.file_table.setItem(row, 1, date_item)
                
                # Size
                size_item = QTableWidgetItem(file_size)
                self.file_table.setItem(row, 2, size_item)
                
                # Encrypted
                enc_item = QTableWidgetItem("🔒" if encrypted else "")
                enc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.file_table.setItem(row, 3, enc_item)
                
                # Store file data
                self.file_data.append({
                    "path": file_path,
                    "name": name,
                    "encrypted": encrypted,
                    "metadata": metadata,
                })
                
            except Exception as e:
                logger.warning(f"Error reading file {file_path}: {e}")
        
        logger.info(f"Loaded {len(files)} configuration files")
    
    def _format_size(self, size: int) -> str:
        """Format file size for display."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    
    def _on_selection_changed(self):
        """Handle selection change in file table."""
        selected = self.file_table.selectedItems()
        if selected:
            row = selected[0].row()
            if row < len(self.file_data):
                file_info = self.file_data[row]
                metadata = file_info.get("metadata", {})
                
                # Show file info
                info_parts = []
                if metadata.get("description"):
                    info_parts.append(f"<b>Description:</b> {metadata['description']}")
                if metadata.get("item_count"):
                    info_parts.append(f"<b>Items:</b> {metadata['item_count']}")
                if metadata.get("source_tenant"):
                    info_parts.append(f"<b>Source:</b> {metadata['source_tenant']}")
                
                self.info_label.setText("<br>".join(info_parts) if info_parts else "")
                self.load_btn.setEnabled(True)
        else:
            self.info_label.setText("")
            self.load_btn.setEnabled(False)
    
    def _load_selected(self):
        """Load the selected configuration."""
        selected = self.file_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        if row >= len(self.file_data):
            return
        
        file_info = self.file_data[row]
        self._load_file(file_info["path"], file_info["encrypted"], file_info["name"])
    
    def _browse_file(self):
        """Browse for a configuration file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Configuration",
            "",
            "Configuration Files (*.pac *.json);;All Files (*)"
        )
        
        if file_path:
            encrypted = is_encrypted_file(file_path)
            metadata = get_config_metadata(file_path)
            name = metadata.get("name", os.path.basename(file_path)) if metadata else os.path.basename(file_path)
            self._load_file(file_path, encrypted, name)
    
    def _load_file(self, file_path: str, encrypted: bool, name: str):
        """
        Load a configuration file.
        
        Args:
            file_path: Path to configuration file
            encrypted: Whether file is encrypted
            name: Display name of configuration
        """
        password = None
        
        if encrypted:
            # Prompt for password
            attempts = 0
            while attempts < self.MAX_PASSWORD_ATTEMPTS:
                dialog = PasswordDialog(
                    name,
                    self,
                    attempts_remaining=self.MAX_PASSWORD_ATTEMPTS - attempts
                )
                
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return  # User cancelled
                
                password = dialog.get_password()
                
                # Try to decrypt
                try:
                    config = load_config_from_file(file_path, password)
                    self.loaded_config = config
                    self.loaded_metadata = get_config_metadata(file_path)
                    self.ignore_defaults = self.ignore_defaults_check.isChecked()
                    
                    logger.info(f"Loaded configuration: {name}")
                    self.accept()
                    return
                    
                except ValueError as e:
                    if "Incorrect password" in str(e):
                        attempts += 1
                        if attempts < self.MAX_PASSWORD_ATTEMPTS:
                            QMessageBox.warning(
                                self,
                                "Incorrect Password",
                                f"The password is incorrect.\n\n"
                                f"{self.MAX_PASSWORD_ATTEMPTS - attempts} attempt(s) remaining."
                            )
                        else:
                            QMessageBox.critical(
                                self,
                                "Access Denied",
                                "Maximum password attempts exceeded.\n\n"
                                "Please try again later."
                            )
                            return
                    else:
                        QMessageBox.critical(
                            self,
                            "Load Failed",
                            f"Failed to decrypt configuration:\n\n{str(e)}"
                        )
                        return
                        
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Load Failed",
                        f"Failed to load configuration:\n\n{str(e)}"
                    )
                    return
        else:
            # Load unencrypted file
            try:
                config = load_config_from_file(file_path)
                self.loaded_config = config
                self.loaded_metadata = get_config_metadata(file_path)
                self.ignore_defaults = self.ignore_defaults_check.isChecked()
                
                logger.info(f"Loaded configuration: {name}")
                self.accept()
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Load Failed",
                    f"Failed to load configuration:\n\n{str(e)}"
                )
    
    def get_config(self) -> Optional[Dict[str, Any]]:
        """Get the loaded configuration."""
        return self.loaded_config
    
    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Get metadata from loaded configuration."""
        return self.loaded_metadata
    
    def should_ignore_defaults(self) -> bool:
        """Check if defaults should be ignored."""
        return self.ignore_defaults
