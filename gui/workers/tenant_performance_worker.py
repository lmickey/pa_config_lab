"""
Background worker for Tenant Performance data collection.

Pulls application performance, user counts, rule usage, and app usage
details from the Insights API and computes summary metrics.
"""

import logging
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class TenantPerformanceWorker(QThread):
    """Background worker that pulls Insights API performance data."""

    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(bool, str, object)  # success, message, results dict
    error = pyqtSignal(str)

    def __init__(
        self,
        api_client,
        time_range: int = 30,
        connection_name: Optional[str] = None,
    ):
        super().__init__()
        self.api_client = api_client
        self.time_range = time_range
        self.connection_name = connection_name
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            results = {
                "top_apps": [],
                "app_usage": [],
                "rule_usage": [],
                "connected_users": 0,
                "summary": {},
            }

            # Phase 1: Connected user count (0-15%)
            self.progress.emit("Getting connected user count...", 5)
            try:
                user_data = self.api_client.get_connected_user_count()
                results["connected_users"] = user_data.get("connected_users", 0)
                self.progress.emit(
                    f"Connected users: {results['connected_users']}", 15
                )
            except Exception as e:
                logger.warning(f"Connected user count failed: {e}")
                self.progress.emit("Connected user count unavailable", 15)

            if self._cancelled:
                self.finished.emit(False, "Cancelled", None)
                return

            # Phase 2: Top applications (15-45%)
            self.progress.emit("Pulling top applications...", 20)
            try:
                results["top_apps"] = self.api_client.get_top_applications(
                    time_range=self.time_range, limit=500
                )
                self.progress.emit(
                    f"Retrieved {len(results['top_apps'])} applications", 45
                )
            except Exception as e:
                logger.warning(f"Top applications pull failed: {e}")
                self.progress.emit(f"Top applications unavailable: {e}", 45)

            if self._cancelled:
                self.finished.emit(False, "Cancelled", None)
                return

            # Phase 3: Application usage details (45-70%)
            self.progress.emit("Pulling application usage details...", 50)
            try:
                results["app_usage"] = self.api_client.get_application_usage_details(
                    time_range=self.time_range, limit=500
                )
                self.progress.emit(
                    f"Retrieved {len(results['app_usage'])} app-rule mappings", 70
                )
            except Exception as e:
                logger.warning(f"App usage pull failed: {e}")
                self.progress.emit(f"App usage unavailable: {e}", 70)

            if self._cancelled:
                self.finished.emit(False, "Cancelled", None)
                return

            # Phase 4: Rule hit counts (70-90%)
            self.progress.emit("Pulling rule hit counts...", 75)
            try:
                results["rule_usage"] = self.api_client.get_rule_hit_counts(
                    time_range=self.time_range
                )
                self.progress.emit(
                    f"Retrieved {len(results['rule_usage'])} rule stats", 90
                )
            except Exception as e:
                logger.warning(f"Rule hit counts failed: {e}")
                self.progress.emit(f"Rule hit counts unavailable: {e}", 90)

            if self._cancelled:
                self.finished.emit(False, "Cancelled", None)
                return

            # Phase 5: Compute summary (90-100%)
            self.progress.emit("Computing summary metrics...", 95)
            results["summary"] = self._compute_summary(results)

            self.progress.emit("Analysis complete", 100)
            self.finished.emit(True, "Performance data collected successfully", results)

        except Exception as e:
            logger.error(f"Performance worker error: {e}", exc_info=True)
            self.error.emit(str(e))

    def _compute_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compute summary metrics from raw data."""
        top_apps = results.get("top_apps", [])
        app_usage = results.get("app_usage", [])
        rule_usage = results.get("rule_usage", [])

        # Total bandwidth
        total_bytes = sum(a.get("total_bytes", 0) for a in top_apps)
        total_sessions = sum(a.get("sessions", 0) for a in top_apps)

        # Unique apps and categories
        unique_apps = len(top_apps)
        categories = set()
        for app in top_apps:
            cat = app.get("app_category", "")
            if cat:
                categories.add(cat)

        # Risk breakdown
        risk_counts = {}
        for app in top_apps:
            risk = str(app.get("risk", "unknown"))
            risk_counts[risk] = risk_counts.get(risk, 0) + 1

        # High-risk apps (risk >= 4)
        high_risk_apps = [
            a for a in top_apps
            if _safe_int(a.get("risk", 0)) >= 4
        ]

        # Rule stats
        total_rules = len(rule_usage)
        total_rule_hits = sum(r.get("hit_count", 0) for r in rule_usage)
        zero_hit_rules = [r for r in rule_usage if r.get("hit_count", 0) == 0]

        # Top consumers (by bytes)
        top_consumers = sorted(top_apps, key=lambda a: a.get("total_bytes", 0), reverse=True)[:10]

        # Unique users from app usage
        unique_users = set()
        for au in app_usage:
            uc = au.get("user_count", 0)
            if isinstance(uc, (int, float)) and uc > 0:
                unique_users.add(au.get("app", ""))

        return {
            "total_bytes": total_bytes,
            "total_sessions": total_sessions,
            "unique_apps": unique_apps,
            "unique_categories": len(categories),
            "categories": sorted(categories),
            "risk_counts": risk_counts,
            "high_risk_count": len(high_risk_apps),
            "high_risk_apps": high_risk_apps,
            "total_rules_with_hits": total_rules,
            "total_rule_hits": total_rule_hits,
            "zero_hit_rules": len(zero_hit_rules),
            "top_consumers": top_consumers,
            "connected_users": results.get("connected_users", 0),
            "apps_with_users": len(unique_users),
        }


def _safe_int(val) -> int:
    """Safely convert to int."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0
