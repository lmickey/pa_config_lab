"""
Tenant Performance workflow.

Connects to a SASE tenant, pulls application performance data, user counts,
rule usage statistics, and displays an interactive performance dashboard.

Two-tab layout:
  Tab 1 — Connect & Pull (tenant selector, time range, progress)
  Tab 2 — Performance Dashboard (metric cards, top apps table, rule stats)
"""

import logging
from datetime import datetime
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
    QScrollArea,
    QFrame,
    QHeaderView,
    QSizePolicy,
    QFileDialog,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from gui.widgets import TenantSelectorWidget
from gui.widgets.results_panel import ResultsPanel
from gui.workers.tenant_performance_worker import TenantPerformanceWorker

logger = logging.getLogger(__name__)


def _format_bytes(num_bytes) -> str:
    """Format bytes into human-readable string."""
    try:
        b = float(num_bytes)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _format_number(num) -> str:
    """Format large numbers with comma separators."""
    try:
        return f"{int(num):,}"
    except (TypeError, ValueError):
        return "0"


class TenantPerformanceWidget(QWidget):
    """Main widget for the Tenant Performance workflow."""

    connection_changed = pyqtSignal(object, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = None
        self.connection_name = None
        self._worker = None
        self._results = None
        self._init_ui()
        self._populate_tenant_dropdown()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_connect_tab()
        self._build_dashboard_tab()

        # Disable dashboard tab until data is pulled
        self.tabs.setTabEnabled(1, False)

    # ------------------------------------------------------------------
    # Tab 1: Connect & Pull
    # ------------------------------------------------------------------

    def _build_connect_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(16)

        # Tenant selector
        self.tenant_selector = TenantSelectorWidget(title="Tenant Connection")
        self.tenant_selector.connection_changed.connect(self._on_tenant_connected)
        layout.addWidget(self.tenant_selector)

        # Options
        options_group = QGroupBox("Data Collection Options")
        options_layout = QVBoxLayout(options_group)

        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Time Range:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["Last 7 Days", "Last 30 Days"])
        self.time_range_combo.setCurrentIndex(1)
        time_row.addWidget(self.time_range_combo)
        time_row.addStretch()
        options_layout.addLayout(time_row)

        btn_row = QHBoxLayout()
        self.pull_btn = QPushButton("Pull Performance Data")
        self.pull_btn.setEnabled(False)
        self.pull_btn.setStyleSheet(
            "QPushButton { background-color: #1565C0; color: white; padding: 8px 20px; "
            "font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #0D47A1; }"
            "QPushButton:disabled { background-color: #ccc; color: #888; }"
        )
        self.pull_btn.clicked.connect(self._start_pull)
        btn_row.addWidget(self.pull_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet(
            "QPushButton { background-color: #757575; color: white; padding: 8px 16px; "
            "border-radius: 5px; }"
            "QPushButton:hover { background-color: #616161; }"
            "QPushButton:disabled { background-color: #ccc; color: #888; }"
        )
        self.cancel_btn.clicked.connect(self._cancel_pull)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        options_layout.addLayout(btn_row)

        layout.addWidget(options_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results log
        self.results_panel = ResultsPanel(
            title="Collection Log",
            placeholder="Connect to a tenant and click 'Pull Performance Data' to begin...",
        )
        layout.addWidget(self.results_panel)

        layout.addStretch()
        scroll.setWidget(scroll_widget)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        self.tabs.addTab(tab, "Connect && Pull Data")

    # ------------------------------------------------------------------
    # Tab 2: Performance Dashboard
    # ------------------------------------------------------------------

    def _build_dashboard_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(12)

        # Summary header
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet(
            "font-size: 13px; color: #333; padding: 8px; "
            "background-color: #E3F2FD; border-radius: 6px;"
        )
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # Metric cards row
        self.metrics_frame = QFrame()
        self.metrics_layout = QHBoxLayout(self.metrics_frame)
        self.metrics_layout.setSpacing(12)
        layout.addWidget(self.metrics_frame)

        # Top Applications table
        apps_group = QGroupBox("Top Applications (by bandwidth)")
        apps_layout = QVBoxLayout(apps_group)

        self.apps_tree = QTreeWidget()
        self.apps_tree.setHeaderLabels([
            "Application", "Category", "Risk", "Bandwidth", "Sessions"
        ])
        self.apps_tree.setRootIsDecorated(False)
        self.apps_tree.setAlternatingRowColors(True)
        self.apps_tree.setMinimumHeight(250)
        header = self.apps_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        apps_layout.addWidget(self.apps_tree)
        layout.addWidget(apps_group)

        # Rule Usage table
        rules_group = QGroupBox("Security Rule Usage")
        rules_layout = QVBoxLayout(rules_group)

        self.rules_tree = QTreeWidget()
        self.rules_tree.setHeaderLabels([
            "Rule", "Hit Count", "Unique Apps"
        ])
        self.rules_tree.setRootIsDecorated(False)
        self.rules_tree.setAlternatingRowColors(True)
        self.rules_tree.setMinimumHeight(200)
        rh = self.rules_tree.header()
        rh.setStretchLastSection(False)
        rh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        rh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        rh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        rules_layout.addWidget(self.rules_tree)
        layout.addWidget(rules_group)

        # High-risk applications
        risk_group = QGroupBox("High-Risk Applications (risk >= 4)")
        risk_layout = QVBoxLayout(risk_group)

        self.risk_tree = QTreeWidget()
        self.risk_tree.setHeaderLabels([
            "Application", "Category", "Risk", "Bandwidth", "Sessions"
        ])
        self.risk_tree.setRootIsDecorated(False)
        self.risk_tree.setAlternatingRowColors(True)
        self.risk_tree.setMinimumHeight(150)
        rkh = self.risk_tree.header()
        rkh.setStretchLastSection(False)
        rkh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        rkh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        rkh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        rkh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        rkh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        risk_layout.addWidget(self.risk_tree)
        layout.addWidget(risk_group)

        # Export button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.export_btn = QPushButton("Export Performance Report")
        self.export_btn.setStyleSheet(
            "QPushButton { background-color: #2E7D32; color: white; padding: 8px 20px; "
            "font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #1B5E20; }"
        )
        self.export_btn.clicked.connect(self._export_report)
        btn_row.addWidget(self.export_btn)

        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.setStyleSheet(
            "QPushButton { background-color: #1565C0; color: white; padding: 8px 16px; "
            "border-radius: 5px; }"
            "QPushButton:hover { background-color: #0D47A1; }"
        )
        self.refresh_btn.clicked.connect(self._start_pull)
        btn_row.addWidget(self.refresh_btn)
        layout.addLayout(btn_row)

        layout.addStretch()
        scroll.setWidget(scroll_widget)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        self.tabs.addTab(tab, "Performance Dashboard")

    # ------------------------------------------------------------------
    # Tenant connection
    # ------------------------------------------------------------------

    def _on_tenant_connected(self, api_client, tenant_name: str):
        self.api_client = api_client
        self.connection_name = tenant_name
        self.pull_btn.setEnabled(api_client is not None)
        if api_client:
            self.results_panel.results_text.setPlaceholderText(
                f"Connected to {tenant_name}. Click 'Pull Performance Data' to begin."
            )
        self.connection_changed.emit(api_client, tenant_name, "tenant_performance")

    def _populate_tenant_dropdown(self):
        try:
            from config.tenant_manager import TenantManager
            tenants = TenantManager.list_tenants()
            self.tenant_selector.populate_tenants(tenants)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Pull data
    # ------------------------------------------------------------------

    def _start_pull(self):
        if not self.api_client:
            return

        time_range = 7 if self.time_range_combo.currentIndex() == 0 else 30

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.pull_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.tabs.setTabEnabled(1, False)
        self.results_panel.results_text.clear()

        self._worker = TenantPerformanceWorker(
            api_client=self.api_client,
            time_range=time_range,
            connection_name=self.connection_name,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel_pull(self):
        if self._worker:
            self._worker.cancel()
        self.cancel_btn.setEnabled(False)

    def _on_progress(self, message: str, pct: int):
        self.progress_bar.setValue(pct)
        self.results_panel.append_text(f"  {message}")

    def _on_finished(self, success: bool, message: str, results):
        self.pull_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        if success and results:
            self._results = results
            self.results_panel.append_text(f"\n  {message}")
            self._populate_dashboard(results)
            self.tabs.setTabEnabled(1, True)
            self.tabs.setCurrentIndex(1)
        else:
            self.results_panel.append_text(f"\n  {message or 'Data collection failed'}")

    def _on_error(self, message: str):
        self.pull_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.results_panel.append_text(f"\n  ERROR: {message}")

    # ------------------------------------------------------------------
    # Populate dashboard
    # ------------------------------------------------------------------

    def _populate_dashboard(self, results: Dict[str, Any]):
        summary = results.get("summary", {})

        # Summary header
        time_label = "7 days" if self.time_range_combo.currentIndex() == 0 else "30 days"
        self.summary_label.setText(
            f"<b>{self.connection_name}</b> &mdash; {time_label} &nbsp;|&nbsp; "
            f"<b>{_format_number(summary.get('unique_apps', 0))}</b> apps &nbsp;|&nbsp; "
            f"<b>{_format_bytes(summary.get('total_bytes', 0))}</b> total bandwidth &nbsp;|&nbsp; "
            f"<b>{_format_number(summary.get('total_sessions', 0))}</b> sessions &nbsp;|&nbsp; "
            f"<b>{_format_number(summary.get('connected_users', 0))}</b> connected users &nbsp;|&nbsp; "
            f"<b>{summary.get('high_risk_count', 0)}</b> high-risk apps"
        )

        # Metric cards
        self._build_metric_cards(summary)

        # Top applications table
        self._populate_apps_tree(results.get("top_apps", []))

        # Rule usage table
        self._populate_rules_tree(results.get("rule_usage", []))

        # High-risk apps table
        self._populate_risk_tree(summary.get("high_risk_apps", []))

    def _build_metric_cards(self, summary: Dict[str, Any]):
        # Clear existing cards
        while self.metrics_layout.count():
            child = self.metrics_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        cards = [
            ("Connected Users", _format_number(summary.get("connected_users", 0)), "#1565C0"),
            ("Active Apps", _format_number(summary.get("unique_apps", 0)), "#2E7D32"),
            ("Categories", _format_number(summary.get("unique_categories", 0)), "#6A1B9A"),
            ("Total Bandwidth", _format_bytes(summary.get("total_bytes", 0)), "#E65100"),
            ("Total Sessions", _format_number(summary.get("total_sessions", 0)), "#00838F"),
            ("High-Risk Apps", str(summary.get("high_risk_count", 0)), "#C62828"),
            ("Active Rules", _format_number(summary.get("total_rules_with_hits", 0)), "#37474F"),
            ("Zero-Hit Rules", str(summary.get("zero_hit_rules", 0)), "#FF6F00"),
        ]

        for label, value, color in cards:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background-color: white; border: 1px solid #ddd; "
                f"border-radius: 8px; border-top: 3px solid {color}; }}"
            )
            card.setMinimumWidth(110)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(2)

            val_label = QLabel(value)
            val_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")
            val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(val_label)

            name_label = QLabel(label)
            name_label.setStyleSheet("font-size: 10px; color: #666;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(name_label)

            self.metrics_layout.addWidget(card)

    def _populate_apps_tree(self, top_apps: list):
        self.apps_tree.clear()
        for app in top_apps[:100]:  # Show top 100
            risk = str(app.get("risk", ""))
            item = QTreeWidgetItem([
                app.get("app", "Unknown"),
                app.get("app_category", ""),
                risk,
                _format_bytes(app.get("total_bytes", 0)),
                _format_number(app.get("sessions", 0)),
            ])
            # Color-code risk
            try:
                risk_val = int(risk)
                if risk_val >= 4:
                    item.setForeground(2, Qt.GlobalColor.red)
                elif risk_val >= 3:
                    from PyQt6.QtGui import QColor
                    item.setForeground(2, QColor("#FF6F00"))
            except (TypeError, ValueError):
                pass
            self.apps_tree.addTopLevelItem(item)

    def _populate_rules_tree(self, rule_usage: list):
        self.rules_tree.clear()
        for rule in rule_usage:
            hit_count = rule.get("hit_count", 0)
            item = QTreeWidgetItem([
                rule.get("rule", "Unknown"),
                _format_number(hit_count),
                str(rule.get("unique_apps", 0)),
            ])
            # Highlight zero-hit rules
            if hit_count == 0:
                item.setForeground(0, Qt.GlobalColor.gray)
                item.setForeground(1, Qt.GlobalColor.red)
            self.rules_tree.addTopLevelItem(item)

    def _populate_risk_tree(self, high_risk_apps: list):
        self.risk_tree.clear()
        if not high_risk_apps:
            item = QTreeWidgetItem(["No high-risk applications found", "", "", "", ""])
            item.setForeground(0, Qt.GlobalColor.gray)
            self.risk_tree.addTopLevelItem(item)
            return
        for app in high_risk_apps:
            item = QTreeWidgetItem([
                app.get("app", "Unknown"),
                app.get("app_category", ""),
                str(app.get("risk", "")),
                _format_bytes(app.get("total_bytes", 0)),
                _format_number(app.get("sessions", 0)),
            ])
            item.setForeground(2, Qt.GlobalColor.red)
            self.risk_tree.addTopLevelItem(item)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_report(self):
        if not self._results:
            return

        import json
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Performance Report", "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return

        report = {
            "tenant": self.connection_name,
            "exported_at": datetime.now().isoformat(),
            "time_range_days": 7 if self.time_range_combo.currentIndex() == 0 else 30,
            "summary": self._results.get("summary", {}),
            "top_applications": self._results.get("top_apps", []),
            "application_usage": self._results.get("app_usage", []),
            "rule_usage": self._results.get("rule_usage", []),
        }

        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        self.results_panel.append_text(f"\n  Report exported to: {path}")
