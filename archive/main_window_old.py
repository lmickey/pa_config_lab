"""
Prisma Access Configuration Manager - Main GUI Application.

This module provides the main window and application entry point for the
PyQt6-based GUI for managing Prisma Access configurations.
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
    QMenuBar,
    QMenu,
    QMessageBox,
    QTabWidget,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction, QIcon

from gui.connection_dialog import ConnectionDialog
from gui.pull_widget import PullConfigWidget
from gui.config_viewer import ConfigViewerWidget
from gui.push_widget import PushConfigWidget
from gui.logs_widget import LogsWidget
from gui.settings_dialog import SettingsDialog
from gui.workers import DefaultDetectionWorker, DependencyAnalysisWorker


class PrismaConfigMainWindow(QMainWindow):
    """Main window for Prisma Access Configuration Manager."""

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
        self.setMinimumSize(1200, 800)

        # Create menu bar
        self._create_menu_bar()

        # Create central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create tabs
        self._create_dashboard_tab()
        self._create_pull_tab()
        self._create_config_tab()
        self._create_push_tab()
        self._create_logs_tab()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Connection status label
        self.connection_status = QLabel("Not Connected")
        self.connection_status.setStyleSheet("color: gray;")
        self.status_bar.addPermanentWidget(self.connection_status)

    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        connect_action = QAction("&Connect...", self)
        connect_action.setShortcut("Ctrl+N")
        connect_action.setStatusTip("Connect to Prisma Access")
        connect_action.triggered.connect(self._show_connection_dialog)
        file_menu.addAction(connect_action)

        file_menu.addSeparator()

        load_action = QAction("&Load Configuration...", self)
        load_action.setShortcut("Ctrl+O")
        load_action.setStatusTip("Load configuration from file")
        load_action.triggered.connect(self._load_configuration)
        file_menu.addAction(load_action)

        save_action = QAction("&Save Configuration...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip("Save configuration to file")
        save_action.triggered.connect(self._save_configuration)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Config menu
        config_menu = menubar.addMenu("&Configuration")

        pull_action = QAction("&Pull Configuration", self)
        pull_action.setShortcut("Ctrl+P")
        pull_action.setStatusTip("Pull configuration from source")
        pull_action.triggered.connect(self._pull_configuration)
        config_menu.addAction(pull_action)

        push_action = QAction("P&ush Configuration", self)
        push_action.setShortcut("Ctrl+U")
        push_action.setStatusTip("Push configuration to target")
        push_action.triggered.connect(self._push_configuration)
        config_menu.addAction(push_action)

        config_menu.addSeparator()

        defaults_action = QAction("Detect &Defaults", self)
        defaults_action.setStatusTip("Detect and filter default configurations")
        defaults_action.triggered.connect(self._detect_defaults)
        config_menu.addAction(defaults_action)

        dependencies_action = QAction("Analyze &Dependencies", self)
        dependencies_action.setStatusTip("Analyze configuration dependencies")
        dependencies_action.triggered.connect(self._analyze_dependencies)
        config_menu.addAction(dependencies_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        settings_action = QAction("&Settings...", self)
        settings_action.setStatusTip("Application settings")
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)

        clear_logs_action = QAction("Clear &Logs", self)
        clear_logs_action.setStatusTip("Clear log display")
        clear_logs_action.triggered.connect(self._clear_logs)
        tools_menu.addAction(clear_logs_action)

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

    def _create_dashboard_tab(self):
        """Create the dashboard tab."""
        dashboard = QWidget()
        layout = QVBoxLayout(dashboard)

        # Welcome message
        welcome = QLabel("<h1>Prisma Access Configuration Manager</h1>")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome)

        description = QLabel(
            "<p>Manage Prisma Access configurations with pull/push workflows,<br>"
            "dependency resolution, and conflict detection.</p>"
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        layout.addStretch()

        # Quick actions
        actions_label = QLabel("<h2>Quick Actions</h2>")
        actions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(actions_label)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        connect_btn = QPushButton("Connect to Prisma Access")
        connect_btn.setMinimumSize(200, 60)
        connect_btn.clicked.connect(self._show_connection_dialog)
        actions_layout.addWidget(connect_btn)

        load_btn = QPushButton("Load Configuration File")
        load_btn.setMinimumSize(200, 60)
        load_btn.clicked.connect(self._load_configuration)
        actions_layout.addWidget(load_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        layout.addStretch()

        # Status info
        status_label = QLabel("<h3>Status</h3>")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)

        self.dashboard_status = QLabel("Not connected to any tenant")
        self.dashboard_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dashboard_status.setStyleSheet("color: gray; font-size: 14px;")
        layout.addWidget(self.dashboard_status)

        layout.addStretch()

        self.tabs.addTab(dashboard, "Dashboard")

    def _create_pull_tab(self):
        """Create the pull configuration tab."""
        self.pull_widget = PullConfigWidget()
        self.pull_widget.pull_completed.connect(self._on_pull_completed)
        self.tabs.addTab(self.pull_widget, "Pull")

    def _create_config_tab(self):
        """Create the configuration viewer/editor tab."""
        self.config_viewer = ConfigViewerWidget()
        self.tabs.addTab(self.config_viewer, "Configuration")

    def _create_push_tab(self):
        """Create the push configuration tab."""
        self.push_widget = PushConfigWidget()
        self.push_widget.push_completed.connect(self._on_push_completed)
        self.tabs.addTab(self.push_widget, "Push")

    def _create_logs_tab(self):
        """Create the logs tab."""
        self.logs_widget = LogsWidget()
        self.tabs.addTab(self.logs_widget, "Logs")

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
                self.connection_status.setText(f"Connected: {tsg_id}")
                self.connection_status.setStyleSheet("color: green;")
                self.dashboard_status.setText(
                    f"Connected to tenant: {tsg_id}\nReady to pull configuration"
                )
                self.dashboard_status.setStyleSheet("color: green; font-size: 14px;")

                self.status_bar.showMessage(f"Connected to {tsg_id}", 5000)

                # Update pull widget
                self.pull_widget.set_api_client(self.api_client)

                # Update push widget
                self.push_widget.set_api_client(self.api_client)

                # Log connection
                self.logs_widget.log(f"Connected to tenant {tsg_id}", "success")

    def _load_configuration(self):
        """Load configuration from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                from config.storage.json_storage import load_config_json

                # Load configuration
                config = load_config_json(file_path, encrypted=None, validate=True)

                if config:
                    self.current_config = config
                    self.status_bar.showMessage(
                        f"Loaded configuration from {file_path}", 5000
                    )

                    # Update config viewer
                    self.config_viewer.set_config(config)

                    # Update push widget
                    self.push_widget.set_config(config)

                    # Log success
                    self.logs_widget.log(
                        f"Loaded configuration from {file_path}", "success"
                    )

                    QMessageBox.information(
                        self,
                        "Success",
                        f"Configuration loaded successfully.\n\n"
                        f"Version: {config.get('metadata', {}).get('version', 'Unknown')}\n"
                        f"Source: {config.get('metadata', {}).get('source_tenant', 'Unknown')}",
                    )
                else:
                    QMessageBox.warning(
                        self, "Load Failed", "Failed to load configuration file."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Error loading configuration:\n{str(e)}"
                )

    def _save_configuration(self):
        """Save configuration to file."""
        if not self.current_config:
            QMessageBox.warning(
                self, "No Configuration", "Please load or pull a configuration first."
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                from config.storage.json_storage import save_config_json

                # Save configuration
                success = save_config_json(
                    self.current_config, file_path, encrypt=False, validate=True
                )

                if success:
                    self.status_bar.showMessage(
                        f"Saved configuration to {file_path}", 5000
                    )
                    QMessageBox.information(
                        self, "Success", "Configuration saved successfully."
                    )

                    # Log success
                    self.logs_widget.log(
                        f"Saved configuration to {file_path}", "success"
                    )
                else:
                    QMessageBox.warning(
                        self, "Save Failed", "Failed to save configuration file."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Error saving configuration:\n{str(e)}"
                )

    def _pull_configuration(self):
        """Pull configuration from source."""
        if not self.api_client:
            QMessageBox.warning(
                self, "Not Connected", "Please connect to a Prisma Access tenant first."
            )
            return

        # Switch to pull tab
        self.tabs.setCurrentWidget(self.pull_widget)

    def _on_pull_completed(self, config):
        """Handle pull completion."""
        self.current_config = config
        self.status_bar.showMessage("Configuration pulled successfully", 5000)

        # Update config viewer
        self.config_viewer.set_config(config)

        # Update push widget
        self.push_widget.set_config(config)

        # Log success
        self.logs_widget.log("Configuration pulled successfully", "success")

    def _on_push_completed(self, result):
        """Handle push completion."""
        self.status_bar.showMessage("Configuration pushed successfully", 5000)

        # Log success
        self.logs_widget.log("Configuration pushed successfully", "success")

    def _push_configuration(self):
        """Push configuration to target."""
        if not self.api_client:
            QMessageBox.warning(
                self, "Not Connected", "Please connect to a Prisma Access tenant first."
            )
            return

        if not self.current_config:
            QMessageBox.warning(
                self, "No Configuration", "Please load or pull a configuration first."
            )
            return

        # Switch to push tab
        self.tabs.setCurrentWidget(self.push_widget)

    def _detect_defaults(self):
        """Detect default configurations."""
        if not self.current_config:
            QMessageBox.warning(
                self, "No Configuration", "Please load or pull a configuration first."
            )
            return

        # Create progress dialog
        from PyQt6.QtWidgets import QProgressDialog

        progress = QProgressDialog("Detecting defaults...", None, 0, 100, self)
        progress.setWindowTitle("Default Detection")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        # Create worker
        worker = DefaultDetectionWorker(self.current_config)

        def on_progress(msg, pct):
            progress.setLabelText(msg)
            progress.setValue(pct)

        def on_finished(success, message, report):
            progress.close()
            if success:
                QMessageBox.information(self, "Default Detection Complete", message)
                self.logs_widget.log("Default detection completed", "success")
            else:
                QMessageBox.critical(self, "Detection Failed", message)
                self.logs_widget.log(f"Default detection failed: {message}", "error")

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.start()

    def _analyze_dependencies(self):
        """Analyze configuration dependencies."""
        if not self.current_config:
            QMessageBox.warning(
                self, "No Configuration", "Please load or pull a configuration first."
            )
            return

        # Create progress dialog
        from PyQt6.QtWidgets import QProgressDialog

        progress = QProgressDialog("Analyzing dependencies...", None, 0, 100, self)
        progress.setWindowTitle("Dependency Analysis")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        # Create worker
        worker = DependencyAnalysisWorker(self.current_config)

        def on_progress(msg, pct):
            progress.setLabelText(msg)
            progress.setValue(pct)

        def on_finished(success, message, analysis):
            progress.close()
            if success:
                QMessageBox.information(self, "Dependency Analysis Complete", message)
                self.logs_widget.log("Dependency analysis completed", "success")
            else:
                QMessageBox.critical(self, "Analysis Failed", message)
                self.logs_widget.log(f"Dependency analysis failed: {message}", "error")

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.start()

    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()

    def _clear_logs(self):
        """Clear log display."""
        self.logs_widget.clear_logs()

    def _show_documentation(self):
        """Show documentation."""
        QMessageBox.information(
            self,
            "Documentation",
            "Documentation viewer will be implemented.\n\n"
            "For now, see the docs/ directory for comprehensive documentation.",
        )

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Prisma Access Configuration Manager",
            "<h2>Prisma Access Configuration Manager</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A comprehensive tool for managing Prisma Access configurations "
            "with pull/push workflows, dependency resolution, and conflict detection.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Pull/Push configurations between tenants</li>"
            "<li>Default configuration detection</li>"
            "<li>Dependency resolution</li>"
            "<li>Conflict detection and resolution</li>"
            "<li>Secure encrypted storage (NIST compliant)</li>"
            "</ul>"
            "<p>Built with PyQt6</p>",
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
