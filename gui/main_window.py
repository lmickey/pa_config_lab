"""
Main GUI Application - Multi-Function Configuration Manager.

This module provides the main window with support for multiple workflows:
1. POV Configuration - Configure new POV environments
2. Configuration Migration - Pull/push between tenants
3. Future workflows - Extensible architecture
"""

import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QStackedWidget,
    QListWidget,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction, QIcon

from gui.connection_dialog import ConnectionDialog
from gui.logs_widget import LogsWidget
from gui.settings_dialog import SettingsDialog


class PrismaConfigMainWindow(QMainWindow):
    """Main window for Prisma Access Configuration Manager - Multi-function."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        self.settings = QSettings("PrismaAccess", "ConfigManager")
        self.api_client = None
        self.current_config = None

        self._init_ui()
        self._restore_window_state()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Prisma Access Configuration Manager")
        self.setMinimumSize(1400, 900)

        # Create menu bar
        self._create_menu_bar()

        # Create central widget with workflow selector
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Left sidebar - Workflow selector
        sidebar = QWidget()
        sidebar.setMaximumWidth(250)
        sidebar.setStyleSheet("QWidget { background-color: #f5f5f5; }")
        sidebar_layout = QVBoxLayout(sidebar)

        sidebar_title = QLabel("<h3>Workflows</h3>")
        sidebar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(sidebar_title)

        self.workflow_list = QListWidget()
        self.workflow_list.addItem("🏠 Home")
        self.workflow_list.addItem("🔧 POV Configuration")
        self.workflow_list.addItem("🔄 Configuration Migration")
        self.workflow_list.addItem("📊 Activity Logs")
        sidebar_layout.addWidget(self.workflow_list)

        sidebar_layout.addStretch()

        # Connection status in sidebar
        sidebar_layout.addWidget(QLabel("<b>Connection Status:</b>"))
        self.connection_status = QLabel("Not Connected")
        self.connection_status.setStyleSheet("color: gray; padding: 5px;")
        self.connection_status.setWordWrap(True)
        sidebar_layout.addWidget(self.connection_status)

        main_layout.addWidget(sidebar)

        # Right side - Stacked widget for different workflows
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create workflow pages
        self._create_home_page()
        self._create_pov_workflow_page()
        self._create_migration_workflow_page()
        self._create_logs_page()

        # Now connect the signal after everything is initialized
        self.workflow_list.currentRowChanged.connect(self._on_workflow_changed)
        self.workflow_list.setCurrentRow(0)

        # Set up GUI logging after logs widget is created
        from gui.gui_logger import setup_gui_logging
        self._original_stdout, self._original_stderr = setup_gui_logging(self.logs_widget)

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Select a workflow to begin")

    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        connect_action = QAction("&Connect to API...", self)
        connect_action.setShortcut("Ctrl+N")
        connect_action.setStatusTip("Connect to Prisma Access API")
        connect_action.triggered.connect(self._show_connection_dialog)
        file_menu.addAction(connect_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        settings_action = QAction("&Settings...", self)
        settings_action.setStatusTip("Application settings")
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        docs_action = QAction("&Documentation", self)
        docs_action.setShortcut("F1")
        docs_action.setStatusTip("Open documentation")
        docs_action.triggered.connect(self._show_documentation)
        help_menu.addAction(docs_action)

        about_action = QAction("&About", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_home_page(self):
        """Create the home/dashboard page."""
        home = QWidget()
        layout = QVBoxLayout(home)

        # Welcome
        welcome = QLabel("<h1>Prisma Access Configuration Manager</h1>")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome)

        tagline = QLabel(
            "<p style='font-size: 14px; color: gray;'>"
            "Comprehensive tool for Prisma Access configuration management</p>"
        )
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)

        layout.addStretch()

        # Workflow cards
        workflows_label = QLabel("<h2>Select a Workflow</h2>")
        workflows_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(workflows_label)

        cards_layout = QHBoxLayout()
        cards_layout.addStretch()

        # POV Configuration card
        pov_card = self._create_workflow_card(
            "🔧 POV Configuration",
            "Configure new POV environments\n"
            "• Load from SCM/Terraform/JSON\n"
            "• Configure firewall settings\n"
            "• Set up service connections\n"
            "• Deploy to NGFW and Prisma Access",
            lambda: self.workflow_list.setCurrentRow(1),
        )
        cards_layout.addWidget(pov_card)

        # Migration card
        migration_card = self._create_workflow_card(
            "🔄 Configuration Migration",
            "Migrate configurations between tenants\n"
            "• Pull from source tenant\n"
            "• View and analyze\n"
            "• Detect conflicts\n"
            "• Push to target tenant",
            lambda: self.workflow_list.setCurrentRow(2),
        )
        cards_layout.addWidget(migration_card)

        cards_layout.addStretch()
        layout.addLayout(cards_layout)

        layout.addStretch()

        # Quick actions
        actions_label = QLabel("<h3>Quick Actions</h3>")
        actions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(actions_label)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        connect_btn = QPushButton("Connect to Prisma Access API")
        connect_btn.setMinimumSize(220, 50)
        connect_btn.clicked.connect(self._show_connection_dialog)
        actions_layout.addWidget(connect_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        layout.addStretch()

        self.stacked_widget.addWidget(home)

    def _create_workflow_card(self, title: str, description: str, on_click) -> QWidget:
        """Create a workflow card."""
        card = QPushButton()
        card.setMinimumSize(300, 200)
        card.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 10px;
                text-align: left;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #f0f8ff;
                border: 2px solid #4CAF50;
            }
        """
        )

        card.setText(f"{title}\n\n{description}")
        card.clicked.connect(on_click)

        return card

    def _create_pov_workflow_page(self):
        """Create the POV configuration workflow page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("<h2>🔧 POV Configuration Workflow</h2>")
        layout.addWidget(title)

        subtitle = QLabel(
            "Configure a new POV (Proof of Value) environment for Prisma Access.\n"
            "This workflow guides you through setting up a complete POV deployment."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: gray; margin-bottom: 20px;")
        layout.addWidget(subtitle)

        # Import POV workflow module
        from gui.workflows.pov_workflow import POVWorkflowWidget

        self.pov_workflow = POVWorkflowWidget()
        layout.addWidget(self.pov_workflow)

        self.stacked_widget.addWidget(page)

    def _create_migration_workflow_page(self):
        """Create the configuration migration workflow page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("<h2>🔄 Configuration Migration Workflow</h2>")
        layout.addWidget(title)

        subtitle = QLabel(
            "Migrate configurations between Prisma Access tenants.\n"
            "Pull from source, analyze, and push to target with conflict resolution."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: gray; margin-bottom: 20px;")
        layout.addWidget(subtitle)

        # Import migration workflow module
        from gui.workflows.migration_workflow import MigrationWorkflowWidget

        self.migration_workflow = MigrationWorkflowWidget()
        layout.addWidget(self.migration_workflow)

        self.stacked_widget.addWidget(page)

    def _create_logs_page(self):
        """Create the logs and monitoring page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("<h2>📊 Logs & Monitoring</h2>")
        layout.addWidget(title)

        self.logs_widget = LogsWidget()
        layout.addWidget(self.logs_widget)

        self.stacked_widget.addWidget(page)

    def _on_workflow_changed(self, index: int):
        """Handle workflow selection change."""
        self.stacked_widget.setCurrentIndex(index)

        workflow_names = [
            "Home",
            "POV Configuration",
            "Configuration Migration",
            "Logs & Monitoring",
        ]

        if index < len(workflow_names):
            # Use statusBar() method instead of status_bar attribute
            self.statusBar().showMessage(f"Switched to: {workflow_names[index]}")

    # Action handlers

    def _show_connection_dialog(self):
        """Show the connection dialog."""
        dialog = ConnectionDialog(self)
        if dialog.exec():
            # Connection successful
            self.api_client = dialog.get_api_client()

            if self.api_client:
                # Update UI
                tsg_id = self.api_client.tsg_id
                self.connection_status.setText(f"✓ Connected\n{tsg_id}")
                self.connection_status.setStyleSheet("color: green; padding: 5px;")

                self.statusBar().showMessage(f"Connected to {tsg_id}", 5000)

                # Update workflows
                self.migration_workflow.set_api_client(self.api_client)
                self.pov_workflow.set_api_client(self.api_client)

                # Log connection
                self.logs_widget.log(f"Connected to tenant {tsg_id}", "success")

    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()

    def _show_documentation(self):
        """Show documentation."""
        QMessageBox.information(
            self,
            "Documentation",
            "Documentation is available in the docs/ directory:\n\n"
            "• GUI_USER_GUIDE.md - GUI usage guide\n"
            "• PULL_PUSH_GUIDE.md - Migration workflow\n"
            "• API_REFERENCE.md - Technical reference\n"
            "• TROUBLESHOOTING.md - Common issues",
        )

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Prisma Access Configuration Manager",
            "<h2>Prisma Access Configuration Manager</h2>"
            "<p>Version 2.0.0</p>"
            "<p>A comprehensive multi-function tool for Prisma Access:</p>"
            "<p><b>Workflows:</b></p>"
            "<ul>"
            "<li><b>POV Configuration:</b> Set up new POV environments</li>"
            "<li><b>Configuration Migration:</b> Clone/migrate between tenants</li>"
            "<li><b>Logs & Monitoring:</b> Track all operations</li>"
            "</ul>"
            "<p><b>Security:</b> NIST SP 800-132 compliant encryption</p>"
            "<p>Built with PyQt6 | Secure by Design</p>",
        )

    def _restore_window_state(self):
        """Restore window state from settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        """Handle window close event."""
        # Save window state
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

        # Accept the close event
        event.accept()

    def log(self, message: str, level: str = "info"):
        """Add log entry."""
        self.logs_widget.log(message, level)


def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Prisma Access Configuration Manager")
    app.setOrganizationName("PrismaAccess")
    app.setOrganizationDomain("prismaaccess.config")

    # Create and show main window
    window = PrismaConfigMainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
