"""
Resume Workflow Dialog.

Shown when loading a configuration that has an incomplete deployment workflow.
Allows user to resume from where they left off or start fresh.
"""

from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QWidget,
    QTextEdit,
    QGroupBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ResumeWorkflowDialog(QDialog):
    """Dialog for resuming an incomplete deployment workflow."""

    # Return values
    RESUME = "resume"
    START_FRESH = "start_fresh"
    VIEW_ONLY = "view_only"
    CANCEL = "cancel"

    def __init__(
        self,
        workflow_state: Dict[str, Any],
        parent=None,
    ):
        """
        Initialize resume workflow dialog.

        Args:
            workflow_state: Workflow state dictionary from saved config
            parent: Parent widget
        """
        super().__init__(parent)
        self.workflow_state = workflow_state
        self.result_action = self.CANCEL

        self.setWindowTitle("Resume Previous Deployment?")
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("Resume Previous Deployment?")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # Info text
        info = QLabel(
            "This configuration has an incomplete deployment workflow. "
            "You can resume from where you left off, start fresh, or view the configuration only."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info)

        # Phase status display
        phases_group = QGroupBox("Deployment Progress")
        phases_layout = QVBoxLayout()

        phases = self._get_phase_status()
        for phase_name, status, is_current in phases:
            phase_widget = self._create_phase_row(phase_name, status, is_current)
            phases_layout.addWidget(phase_widget)

        phases_group.setLayout(phases_layout)
        layout.addWidget(phases_group)

        # Last updated
        last_updated = self.workflow_state.get("last_updated", "Unknown")
        current_phase = self.workflow_state.get("current_phase", "Unknown")

        status_text = f"<b>Current Phase:</b> {self._format_phase_name(current_phase)}<br>"
        status_text += f"<b>Last Updated:</b> {self._format_timestamp(last_updated)}"

        status_label = QLabel(status_text)
        status_label.setStyleSheet(
            "background-color: #f5f5f5; padding: 10px; border-radius: 5px; "
            "border: 1px solid #ddd;"
        )
        layout.addWidget(status_label)

        # Notes (if any)
        notes = self.workflow_state.get("notes", "")
        if notes:
            notes_group = QGroupBox("Notes")
            notes_layout = QVBoxLayout()
            notes_text = QLabel(notes)
            notes_text.setWordWrap(True)
            notes_text.setStyleSheet("color: #666;")
            notes_layout.addWidget(notes_text)
            notes_group.setLayout(notes_layout)
            layout.addWidget(notes_group)

        # Terraform outputs summary (if any)
        outputs = self._get_terraform_outputs()
        if outputs:
            outputs_group = QGroupBox("Deployed Resources")
            outputs_layout = QVBoxLayout()

            for name, value in outputs.items():
                if value:
                    output_label = QLabel(f"<b>{self._format_output_name(name)}:</b> {value}")
                    output_label.setWordWrap(True)
                    outputs_layout.addWidget(output_label)

            outputs_group.setLayout(outputs_layout)
            layout.addWidget(outputs_group)

        layout.addStretch()

        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Resume button (primary action)
        resume_btn = QPushButton("Resume Deployment")
        resume_btn.setMinimumWidth(150)
        resume_btn.setMinimumHeight(40)
        resume_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; font-weight: bold; "
            "  padding: 10px; border-radius: 5px; "
            "  border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
        )
        resume_btn.clicked.connect(self._on_resume)
        buttons_layout.addWidget(resume_btn)

        # Start Fresh button
        fresh_btn = QPushButton("Start Fresh")
        fresh_btn.setMinimumWidth(120)
        fresh_btn.setMinimumHeight(40)
        fresh_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #FF9800; color: white; font-weight: bold; "
            "  padding: 10px; border-radius: 5px; "
            "  border: 1px solid #F57C00; border-bottom: 3px solid #E65100; "
            "}"
            "QPushButton:hover { background-color: #FB8C00; }"
            "QPushButton:pressed { background-color: #F57C00; border-bottom: 1px solid #E65100; }"
        )
        fresh_btn.clicked.connect(self._on_start_fresh)
        buttons_layout.addWidget(fresh_btn)

        # View Only button
        view_btn = QPushButton("View Config Only")
        view_btn.setMinimumWidth(120)
        view_btn.setMinimumHeight(40)
        view_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; font-weight: bold; "
            "  padding: 10px; border-radius: 5px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
        )
        view_btn.clicked.connect(self._on_view_only)
        buttons_layout.addWidget(view_btn)

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def _get_phase_status(self) -> List[tuple]:
        """
        Get list of phases with their status.

        Returns:
            List of (phase_name, status, is_current) tuples
        """
        phases_data = self.workflow_state.get("phases", {})
        current_phase = self.workflow_state.get("current_phase", "")

        # Define phase order
        phase_order = [
            "config_complete",
            "terraform_running",
            "terraform_complete",
            "licensing_pending",
            "firewall_config",
            "panorama_config",
            "scm_config",
            "complete",
        ]

        result = []
        for phase in phase_order:
            phase_info = phases_data.get(phase, {})
            status = phase_info.get("status", "pending")
            is_current = (phase == current_phase)
            result.append((phase, status, is_current))

        return result

    def _create_phase_row(self, phase_name: str, status: str, is_current: bool) -> QWidget:
        """Create a row widget for a phase."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(5, 2, 5, 2)

        # Status icon
        if status == "complete":
            icon = "✓"
            icon_style = "color: #4CAF50; font-weight: bold;"
        elif status == "in_progress":
            icon = "⏸" if is_current else "⋯"
            icon_style = "color: #FF9800; font-weight: bold;"
        else:
            icon = "○"
            icon_style = "color: #9E9E9E;"

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(icon_style)
        icon_label.setFixedWidth(20)
        layout.addWidget(icon_label)

        # Phase name
        name_label = QLabel(self._format_phase_name(phase_name))
        if is_current:
            name_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        elif status == "complete":
            name_label.setStyleSheet("color: #4CAF50;")
        else:
            name_label.setStyleSheet("color: #9E9E9E;")
        layout.addWidget(name_label)

        layout.addStretch()

        return row

    def _format_phase_name(self, phase: str) -> str:
        """Format phase name for display."""
        names = {
            "config_complete": "Configuration Saved",
            "terraform_running": "Terraform Running",
            "terraform_complete": "Infrastructure Deployed",
            "licensing_pending": "Licensing Pending",
            "firewall_config": "Firewall Configuration",
            "panorama_config": "Panorama Configuration",
            "scm_config": "SCM Configuration",
            "complete": "Deployment Complete",
        }
        return names.get(phase, phase.replace("_", " ").title())

    def _format_timestamp(self, timestamp: str) -> str:
        """Format timestamp for display."""
        if not timestamp or timestamp == "Unknown":
            return "Unknown"

        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%b %d, %Y %I:%M %p")
        except Exception:
            return timestamp

    def _format_output_name(self, name: str) -> str:
        """Format output name for display."""
        return name.replace("_", " ").replace("-", " ").title()

    def _get_terraform_outputs(self) -> Dict[str, Any]:
        """Get Terraform outputs from workflow state."""
        phases = self.workflow_state.get("phases", {})
        tf_complete = phases.get("terraform_complete", {})
        return tf_complete.get("outputs", {})

    def _on_resume(self):
        """Handle resume button click."""
        self.result_action = self.RESUME
        self.accept()

    def _on_start_fresh(self):
        """Handle start fresh button click."""
        self.result_action = self.START_FRESH
        self.accept()

    def _on_view_only(self):
        """Handle view only button click."""
        self.result_action = self.VIEW_ONLY
        self.accept()

    def get_action(self) -> str:
        """Get the selected action."""
        return self.result_action


def show_resume_dialog(
    workflow_state: Dict[str, Any],
    parent=None,
) -> str:
    """
    Show resume workflow dialog and return the selected action.

    Args:
        workflow_state: Workflow state dictionary
        parent: Parent widget

    Returns:
        Action string: 'resume', 'start_fresh', 'view_only', or 'cancel'
    """
    dialog = ResumeWorkflowDialog(workflow_state, parent)
    dialog.exec()
    return dialog.get_action()
