"""
SaaS Inline Review workflow.

Connects to a SASE tenant, pulls application activity + security policy,
cross-references them, and generates actionable recommendations:
ungoverned apps, missing profiles, overly broad rules, unused rules,
rule consolidation, and app group candidates.

Two-tab layout:
  Tab 1 — Connect & Analyze (tenant selector, time range, progress)
  Tab 2 — Review & Recommendations (tree + detail panel)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QComboBox,
    QGroupBox,
    QProgressBar,
    QTreeWidget,
    QTreeWidgetItem,
    QTextEdit,
    QSplitter,
    QFileDialog,
    QApplication,
    QScrollArea,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from gui.widgets import TenantSelectorWidget
from gui.widgets.results_panel import ResultsPanel
from gui.workers.saas_review_worker import SaaSReviewWorker

logger = logging.getLogger(__name__)

# Display labels and colors for recommendation categories
CATEGORY_META = {
    "ungoverned_apps": {
        "label": "Ungoverned SaaS Apps",
        "icon": "🌐",
        "description": "Applications seen in traffic but not referenced by any security rule",
    },
    "missing_profiles": {
        "label": "Missing Security Profiles",
        "icon": "🛡️",
        "description": "Allow rules without a security profile group attached",
    },
    "overly_broad": {
        "label": "Overly Broad Rules",
        "icon": "📏",
        "description": "Rules using 'application: any' that could be narrowed",
    },
    "unused_rules": {
        "label": "Unused Rules",
        "icon": "💤",
        "description": "Rules with zero hits in the analysis period",
    },
    "rule_consolidation": {
        "label": "Rule Consolidation",
        "icon": "🔗",
        "description": "Multiple rules that could be merged into one with an app group",
    },
    "app_group_candidates": {
        "label": "App Group Candidates",
        "icon": "📦",
        "description": "Apps co-occurring in traffic that could form a new application group",
    },
}

SEVERITY_COLORS = {
    "high": QColor("#e74c3c"),
    "medium": QColor("#f39c12"),
    "low": QColor("#3498db"),
}


class SaaSReviewWorkflowWidget(QWidget):
    """Main widget for the SaaS Inline Review workflow."""

    connection_changed = pyqtSignal(object, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = None
        self.connection_name = None
        self._worker = None
        self._results = None
        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_connect_tab()
        self._build_review_tab()

        # Disable review tab until analysis completes
        self.tabs.setTabEnabled(1, False)

    # ---- Tab 1: Connect & Analyze ----

    def _build_connect_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)

        outer = QVBoxLayout()
        outer.addWidget(scroll)
        container = QWidget()
        container.setLayout(outer)
        self.tabs.addTab(container, "Connect & Analyze")

        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # Tenant selector
        self.tenant_selector = TenantSelectorWidget(
            title="Tenant Connection",
            show_load_file=False,
        )
        self.tenant_selector.connection_changed.connect(self._on_tenant_connected)
        layout.addWidget(self.tenant_selector)

        # Options group
        options_group = QGroupBox("Analysis Options")
        options_layout = QHBoxLayout(options_group)

        options_layout.addWidget(QLabel("Time Range:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["Last 7 Days", "Last 30 Days"])
        self.time_range_combo.setCurrentIndex(1)
        options_layout.addWidget(self.time_range_combo)
        options_layout.addStretch()

        self.analyze_btn = QPushButton("Pull Data && Analyze")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setMinimumWidth(180)
        self.analyze_btn.clicked.connect(self._start_analysis)
        options_layout.addWidget(self.analyze_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_analysis)
        options_layout.addWidget(self.cancel_btn)

        layout.addWidget(options_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results panel
        self.results_panel = ResultsPanel(
            title="Analysis Log",
            placeholder="Connect to a tenant and click 'Pull Data & Analyze' to begin...",
        )
        layout.addWidget(self.results_panel)

        layout.addStretch()

    # ---- Tab 2: Review & Recommendations ----

    def _build_review_tab(self):
        tab = QWidget()
        self.tabs.addTab(tab, "Review & Recommendations")
        layout = QVBoxLayout(tab)

        # Summary header
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 13px; padding: 6px;")
        layout.addWidget(self.summary_label)

        # Splitter: tree (left) + detail (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        # Left: recommendation tree
        self.rec_tree = QTreeWidget()
        self.rec_tree.setHeaderLabels(["Recommendation", "Severity"])
        self.rec_tree.setColumnWidth(0, 400)
        self.rec_tree.setColumnWidth(1, 80)
        self.rec_tree.currentItemChanged.connect(self._on_tree_item_changed)
        splitter.addWidget(self.rec_tree)

        # Right: detail panel
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(4, 4, 4, 4)

        self.detail_title = QLabel("Select a recommendation")
        self.detail_title.setWordWrap(True)
        self.detail_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        detail_layout.addWidget(self.detail_title)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text, 1)

        # Config snippet area
        snippet_label = QLabel("Config Snippet:")
        snippet_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        detail_layout.addWidget(snippet_label)

        self.snippet_text = QTextEdit()
        self.snippet_text.setReadOnly(True)
        self.snippet_text.setMaximumHeight(200)
        self.snippet_text.setStyleSheet("font-family: monospace; font-size: 12px;")
        detail_layout.addWidget(self.snippet_text)

        # Buttons
        btn_layout = QHBoxLayout()
        self.copy_snippet_btn = QPushButton("Copy Config Snippet")
        self.copy_snippet_btn.clicked.connect(self._copy_snippet)
        btn_layout.addWidget(self.copy_snippet_btn)

        self.export_btn = QPushButton("Export All Recommendations")
        self.export_btn.clicked.connect(self._export_recommendations)
        btn_layout.addWidget(self.export_btn)

        btn_layout.addStretch()
        detail_layout.addLayout(btn_layout)

        splitter.addWidget(detail_widget)
        splitter.setSizes([400, 500])

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_tenant_connected(self, api_client, tenant_name: str):
        """Handle tenant connection from selector."""
        self.api_client = api_client
        self.connection_name = tenant_name
        self.analyze_btn.setEnabled(api_client is not None)
        if api_client:
            self.results_panel.results_text.clear()
            self.results_panel.results_text.setPlaceholderText(
                f"Connected to {tenant_name}. Click 'Pull Data & Analyze' to begin."
            )
        # Forward to main window
        self.connection_changed.emit(
            api_client, tenant_name, "saas_review"
        )

    def _start_analysis(self):
        if not self.api_client:
            return

        time_range = 7 if self.time_range_combo.currentIndex() == 0 else 30
        self.results_panel.results_text.clear()
        self.results_panel.append_text(
            f"Starting SaaS Inline Review ({time_range}-day window)..."
        )

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.analyze_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.tabs.setTabEnabled(1, False)

        self._worker = SaaSReviewWorker(
            api_client=self.api_client,
            time_range=time_range,
            connection_name=self.connection_name,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel_analysis(self):
        if self._worker:
            self._worker.cancel()
            self.results_panel.append_text("Cancelling...")

    def _on_progress(self, message: str, pct: int):
        self.progress_bar.setValue(pct)
        self.results_panel.append_text(message)

    def _on_error(self, message: str):
        self.results_panel.append_text(f"ERROR: {message}")
        self.analyze_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def _on_finished(self, success: bool, message: str, results):
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if success and results:
            self._results = results
            self.results_panel.append_text(f"\n{message}")

            summary = results.get("summary", {})
            if not summary.get("insights_available"):
                self.results_panel.append_text(
                    "Note: Insights API was unavailable. "
                    "Results are config-only (missing profiles, overly broad rules)."
                )

            self._populate_review_tab(results)
            self.tabs.setTabEnabled(1, True)
            self.tabs.setCurrentIndex(1)
        else:
            self.results_panel.append_text(f"\nAnalysis failed: {message}")

    # ------------------------------------------------------------------
    # Review tab population
    # ------------------------------------------------------------------

    def _populate_review_tab(self, results: Dict[str, Any]):
        summary = results.get("summary", {})
        recs = results.get("recommendations", [])

        # Summary header
        insights_note = ""
        if not summary.get("insights_available"):
            insights_note = " (config-only — Insights API unavailable)"

        self.summary_label.setText(
            f"<b>{summary.get('total_rules', 0)}</b> security rules | "
            f"<b>{summary.get('active_apps', 0)}</b> active applications | "
            f"<b>{summary.get('total_recommendations', 0)}</b> recommendations"
            f"{insights_note}<br>"
            f"<span style='color:#e74c3c'>High: {summary.get('by_severity', {}).get('high', 0)}</span> &nbsp; "
            f"<span style='color:#f39c12'>Medium: {summary.get('by_severity', {}).get('medium', 0)}</span> &nbsp; "
            f"<span style='color:#3498db'>Low: {summary.get('by_severity', {}).get('low', 0)}</span>"
        )

        # Build tree
        self.rec_tree.clear()

        # Group by category
        by_category = {}
        for rec in recs:
            cat = rec.get("category", "other")
            by_category.setdefault(cat, []).append(rec)

        # Add categories in display order
        category_order = [
            "ungoverned_apps",
            "missing_profiles",
            "overly_broad",
            "unused_rules",
            "rule_consolidation",
            "app_group_candidates",
        ]
        for cat_key in category_order:
            cat_recs = by_category.get(cat_key, [])
            if not cat_recs:
                continue

            meta = CATEGORY_META.get(cat_key, {"label": cat_key, "icon": "", "description": ""})
            cat_item = QTreeWidgetItem(self.rec_tree)
            cat_item.setText(
                0, f"{meta['icon']} {meta['label']} ({len(cat_recs)})"
            )
            cat_item.setToolTip(0, meta["description"])
            cat_item.setData(0, Qt.ItemDataRole.UserRole, None)  # No rec data on category
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)

            for rec in cat_recs:
                child = QTreeWidgetItem(cat_item)
                # Build display name from rec fields
                name = rec.get("rule_name") or rec.get("app_name") or ""
                if rec.get("rule_names"):
                    name = ", ".join(rec["rule_names"][:3])
                child.setText(0, name)

                severity = rec.get("severity", "low")
                child.setText(1, severity.upper())
                color = SEVERITY_COLORS.get(severity, QColor("#999999"))
                child.setForeground(1, color)

                # Store full rec as item data
                child.setData(0, Qt.ItemDataRole.UserRole, rec)

            cat_item.setExpanded(True)

        self.rec_tree.resizeColumnToContents(1)

    def _on_tree_item_changed(self, current, previous):
        if not current:
            return
        rec = current.data(0, Qt.ItemDataRole.UserRole)
        if rec is None:
            # Category header — show description
            cat_text = current.text(0)
            self.detail_title.setText(cat_text)
            self.detail_text.setPlainText("")
            self.snippet_text.setPlainText("")
            return

        # Show recommendation detail
        self.detail_title.setText(
            f"{rec.get('severity', '').upper()} — "
            f"{CATEGORY_META.get(rec.get('category', ''), {}).get('label', rec.get('category', ''))}"
        )

        # Build detail text
        lines = [rec.get("suggestion", "")]
        if rec.get("folder"):
            lines.append(f"\nFolder: {rec['folder']}")
        if rec.get("rule_name"):
            lines.append(f"Rule: {rec['rule_name']}")
        if rec.get("app_name"):
            lines.append(f"Application: {rec['app_name']}")
        if rec.get("risk"):
            lines.append(f"Risk Level: {rec['risk']}")
        if rec.get("unique_apps") is not None:
            lines.append(f"Unique Apps Observed: {rec['unique_apps']}")
        if rec.get("apps"):
            lines.append(f"\nApplications ({len(rec['apps'])}):")
            for app in rec["apps"][:30]:
                lines.append(f"  - {app}")
            if len(rec["apps"]) > 30:
                lines.append(f"  ... and {len(rec['apps']) - 30} more")
        if rec.get("rule_names"):
            lines.append(f"\nRules to consolidate:")
            for rn in rec["rule_names"]:
                lines.append(f"  - {rn}")

        self.detail_text.setPlainText("\n".join(lines))

        # Config snippet
        snippet = rec.get("config_snippet")
        if snippet:
            self.snippet_text.setPlainText(json.dumps(snippet, indent=2))
        else:
            self.snippet_text.setPlainText("(no config snippet for this recommendation)")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _copy_snippet(self):
        text = self.snippet_text.toPlainText()
        if text and text != "(no config snippet for this recommendation)":
            QApplication.clipboard().setText(text)
            self.results_panel.append_text("Config snippet copied to clipboard.")

    def _export_recommendations(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Recommendations",
            f"saas_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)",
        )
        if path:
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "tenant": self.connection_name,
                "summary": self._results.get("summary", {}),
                "recommendations": self._results.get("recommendations", []),
            }
            Path(path).write_text(json.dumps(export_data, indent=2))
            self.results_panel.append_text(f"Recommendations exported to {path}")

    # ------------------------------------------------------------------
    # Interface methods (called by main_window)
    # ------------------------------------------------------------------

    def set_api_client(self, api_client, connection_name: str):
        """Receive API client from main window connection."""
        self.api_client = api_client
        self.connection_name = connection_name
        self.analyze_btn.setEnabled(api_client is not None)

    def has_unsaved_work(self) -> bool:
        return self._results is not None

    def clear_state(self):
        self._results = None
        self._worker = None
        self.rec_tree.clear()
        self.summary_label.setText("")
        self.detail_title.setText("Select a recommendation")
        self.detail_text.clear()
        self.snippet_text.clear()
        self.results_panel.results_text.clear()
        self.progress_bar.setVisible(False)
        self.tabs.setTabEnabled(1, False)
        self.tabs.setCurrentIndex(0)
