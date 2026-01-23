"""
Terraform Review Dialog.

Displays generated Terraform configuration files for review before deployment.
"""

import os
from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
    QGroupBox,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QTextDocument
import re


class TerraformSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Terraform/HCL files."""

    def __init__(self, parent: QTextDocument):
        super().__init__(parent)
        self._init_rules()

    def _init_rules(self):
        """Initialize highlighting rules."""
        self.rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "resource", "data", "variable", "output", "module",
            "provider", "terraform", "locals", "for_each", "count",
            "depends_on", "lifecycle", "provisioner", "connection",
        ]
        for word in keywords:
            pattern = rf'\b{word}\b'
            self.rules.append((re.compile(pattern), keyword_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#008000"))
        self.rules.append((re.compile(r'"[^"]*"'), string_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#FF8C00"))
        self.rules.append((re.compile(r'\b\d+\b'), number_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        comment_format.setFontItalic(True)
        self.rules.append((re.compile(r'#.*$'), comment_format))
        self.rules.append((re.compile(r'//.*$'), comment_format))

        # Resource types
        resource_format = QTextCharFormat()
        resource_format.setForeground(QColor("#800080"))
        self.rules.append((re.compile(r'"azurerm_\w+"'), resource_format))

        # Variables
        var_format = QTextCharFormat()
        var_format.setForeground(QColor("#008B8B"))
        self.rules.append((re.compile(r'\$\{[^}]+\}'), var_format))
        self.rules.append((re.compile(r'var\.\w+'), var_format))
        self.rules.append((re.compile(r'local\.\w+'), var_format))

        # Booleans
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#FF0000"))
        self.rules.append((re.compile(r'\b(true|false|null)\b'), bool_format))

    def highlightBlock(self, text: str):
        """Apply highlighting to a block of text."""
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class TerraformReviewDialog(QDialog):
    """Dialog for reviewing Terraform configuration."""

    def __init__(
        self,
        terraform_dir: str,
        config_summary: Optional[Dict[str, Any]] = None,
        parent=None,
    ):
        """
        Initialize Terraform review dialog.

        Args:
            terraform_dir: Directory containing Terraform files
            config_summary: Optional summary of the deployment configuration
            parent: Parent widget
        """
        super().__init__(parent)
        self.terraform_dir = terraform_dir
        self.config_summary = config_summary or {}
        self.files: Dict[str, str] = {}

        self.setWindowTitle("Review Terraform Configuration")
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)

        self._load_files()
        self._init_ui()

    def _load_files(self):
        """Load Terraform files from directory."""
        if not os.path.exists(self.terraform_dir):
            return

        for filename in os.listdir(self.terraform_dir):
            if filename.endswith('.tf') or filename.endswith('.tfvars'):
                filepath = os.path.join(self.terraform_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        self.files[filename] = f.read()
                except Exception:
                    self.files[filename] = f"Error reading file: {filepath}"

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Terraform Configuration Review")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # Info text
        info = QLabel(
            "Review the generated Terraform configuration before deploying. "
            "These files will be used to create your Azure infrastructure."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info)

        # Summary section (if provided)
        if self.config_summary:
            summary_group = QGroupBox("Deployment Summary")
            summary_layout = QVBoxLayout()

            summary_text = self._format_summary()
            summary_label = QLabel(summary_text)
            summary_label.setWordWrap(True)
            summary_label.setStyleSheet("padding: 5px;")
            summary_layout.addWidget(summary_label)

            summary_group.setLayout(summary_layout)
            layout.addWidget(summary_group)

        # File browser
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # File list (left side)
        file_list_widget = QWidget()
        file_list_layout = QVBoxLayout(file_list_widget)
        file_list_layout.setContentsMargins(0, 0, 0, 0)

        file_list_label = QLabel("<b>Files</b>")
        file_list_layout.addWidget(file_list_label)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.itemClicked.connect(self._on_file_selected)

        # Populate file tree
        for filename in sorted(self.files.keys()):
            item = QTreeWidgetItem([filename])
            if filename.endswith('.tf'):
                item.setIcon(0, self.style().standardIcon(
                    self.style().StandardPixmap.SP_FileIcon
                ))
            self.file_tree.addTopLevelItem(item)

        file_list_layout.addWidget(self.file_tree)
        splitter.addWidget(file_list_widget)

        # File content (right side)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.content_label = QLabel("<b>Select a file to view</b>")
        content_layout.addWidget(self.content_label)

        self.content_editor = QTextEdit()
        self.content_editor.setReadOnly(True)
        self.content_editor.setFont(QFont("Courier New", 10))
        self.content_editor.setStyleSheet(
            "QTextEdit { background-color: #f8f8f8; border: 1px solid #ddd; }"
        )

        # Add syntax highlighter
        self.highlighter = TerraformSyntaxHighlighter(self.content_editor.document())

        content_layout.addWidget(self.content_editor)
        splitter.addWidget(content_widget)

        # Set initial sizes
        splitter.setSizes([200, 700])

        layout.addWidget(splitter, 1)

        # Bottom buttons
        buttons_layout = QHBoxLayout()

        # Export button
        export_btn = QPushButton("Export Files...")
        export_btn.clicked.connect(self._export_files)
        buttons_layout.addWidget(export_btn)

        buttons_layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        # Select first file if any
        if self.file_tree.topLevelItemCount() > 0:
            self.file_tree.setCurrentItem(self.file_tree.topLevelItem(0))
            self._on_file_selected(self.file_tree.topLevelItem(0), 0)

    def _format_summary(self) -> str:
        """Format configuration summary for display."""
        lines = []

        if 'deployment_name' in self.config_summary:
            lines.append(f"<b>Deployment:</b> {self.config_summary['deployment_name']}")

        if 'location' in self.config_summary:
            lines.append(f"<b>Location:</b> {self.config_summary['location']}")

        if 'resource_group' in self.config_summary:
            lines.append(f"<b>Resource Group:</b> {self.config_summary['resource_group']}")

        if 'firewalls' in self.config_summary:
            fw_count = len(self.config_summary['firewalls'])
            lines.append(f"<b>Firewalls:</b> {fw_count}")

        if 'panorama' in self.config_summary and self.config_summary['panorama']:
            lines.append("<b>Panorama:</b> Yes")

        if 'supporting_vms' in self.config_summary:
            vm_count = len(self.config_summary['supporting_vms'])
            lines.append(f"<b>Supporting VMs:</b> {vm_count}")

        return "<br>".join(lines) if lines else "No summary available"

    def _on_file_selected(self, item: QTreeWidgetItem, column: int):
        """Handle file selection."""
        filename = item.text(0)
        self.content_label.setText(f"<b>{filename}</b>")

        content = self.files.get(filename, "File not found")
        self.content_editor.setPlainText(content)

    def _export_files(self):
        """Export Terraform files to a directory."""
        export_dir = QFileDialog.getExistingDirectory(
            self,
            "Export Terraform Files",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )

        if not export_dir:
            return

        try:
            exported = 0
            for filename, content in self.files.items():
                filepath = os.path.join(export_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
                exported += 1

            QMessageBox.information(
                self,
                "Export Complete",
                f"Exported {exported} files to:\n{export_dir}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export files:\n{str(e)}"
            )


def show_terraform_review(
    terraform_dir: str,
    config_summary: Optional[Dict[str, Any]] = None,
    parent=None,
) -> bool:
    """
    Show Terraform review dialog.

    Args:
        terraform_dir: Directory containing Terraform files
        config_summary: Optional deployment summary
        parent: Parent widget

    Returns:
        True if dialog was accepted
    """
    dialog = TerraformReviewDialog(terraform_dir, config_summary, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
