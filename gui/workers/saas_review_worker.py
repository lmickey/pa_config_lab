"""
Background worker for SaaS Inline Review analysis.

Pulls security policy config (existing API) + application activity data
(Insights API), cross-references them, and generates actionable
recommendations for ungoverned apps, missing profiles, overly broad
rules, unused rules, rule consolidation, and app group candidates.
"""

import logging
from collections import defaultdict
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

# Folders that contain security rules in Prisma Access
SECURITY_RULE_FOLDERS = ["Mobile Users", "Remote Networks", "Service Connections"]


class SaaSReviewWorker(QThread):
    """Background worker that pulls config + Insights data and runs analysis."""

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
        """Request cancellation."""
        self._cancelled = True

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    def run(self):
        try:
            results = {
                "config": {},
                "insights": {},
                "recommendations": [],
                "summary": {},
                "insights_available": False,
            }

            # Phase 1: Pull config data (0-40%)
            self.progress.emit("Pulling security rules...", 5)
            rules = self._pull_security_rules()
            if self._cancelled:
                self.finished.emit(False, "Cancelled", None)
                return

            self.progress.emit("Pulling application objects...", 15)
            apps = self._pull_applications()
            app_groups = self._pull_application_groups()
            app_filters = self._pull_application_filters()
            if self._cancelled:
                self.finished.emit(False, "Cancelled", None)
                return

            self.progress.emit("Pulling security profile groups...", 25)
            profile_groups = self._pull_profile_groups()
            if self._cancelled:
                self.finished.emit(False, "Cancelled", None)
                return

            results["config"] = {
                "rules": rules,
                "applications": apps,
                "application_groups": app_groups,
                "application_filters": app_filters,
                "profile_groups": profile_groups,
            }
            self.progress.emit(
                f"Config pull complete: {len(rules)} rules, "
                f"{len(apps)} apps, {len(profile_groups)} profile groups",
                40,
            )

            # Phase 2: Pull Insights activity data (40-70%)
            insights_data = {}
            try:
                self.progress.emit("Pulling top application activity...", 45)
                insights_data["top_apps"] = self.api_client.get_top_applications(
                    time_range=self.time_range
                )
                if self._cancelled:
                    self.finished.emit(False, "Cancelled", None)
                    return

                self.progress.emit("Pulling app-to-rule correlations...", 52)
                insights_data["app_usage"] = (
                    self.api_client.get_application_usage_details(
                        time_range=self.time_range
                    )
                )
                if self._cancelled:
                    self.finished.emit(False, "Cancelled", None)
                    return

                self.progress.emit("Pulling rule hit counts...", 60)
                insights_data["rule_hits"] = self.api_client.get_rule_hit_counts(
                    time_range=self.time_range
                )

                results["insights"] = insights_data
                results["insights_available"] = True
                self.progress.emit(
                    f"Insights pull complete: {len(insights_data.get('top_apps', []))} active apps",
                    70,
                )
            except Exception as e:
                logger.warning(f"Insights API unavailable, config-only analysis: {e}")
                self.progress.emit(
                    "Insights API unavailable — running config-only analysis...", 70
                )

            if self._cancelled:
                self.finished.emit(False, "Cancelled", None)
                return

            # Phase 3: Cross-reference analysis (70-100%)
            self.progress.emit("Analyzing security policy...", 75)
            recommendations = self._analyze(
                rules, apps, app_groups, app_filters, profile_groups, insights_data
            )
            results["recommendations"] = recommendations

            # Build summary
            severity_counts = defaultdict(int)
            category_counts = defaultdict(int)
            for rec in recommendations:
                severity_counts[rec["severity"]] += 1
                category_counts[rec["category"]] += 1

            results["summary"] = {
                "total_rules": len(rules),
                "total_apps_configured": len(apps),
                "active_apps": len(insights_data.get("top_apps", [])),
                "total_recommendations": len(recommendations),
                "by_severity": dict(severity_counts),
                "by_category": dict(category_counts),
                "time_range_days": self.time_range,
                "insights_available": results["insights_available"],
            }

            self.progress.emit("Analysis complete!", 100)
            self.finished.emit(
                True,
                f"Analysis complete: {len(recommendations)} recommendations",
                results,
            )

        except Exception as e:
            logger.error(f"SaaS review worker error: {e}", exc_info=True)
            self.error.emit(str(e))
            self.finished.emit(False, f"Error: {e}", None)

    # ------------------------------------------------------------------
    # Config pull helpers
    # ------------------------------------------------------------------

    def _pull_security_rules(self) -> List[Dict[str, Any]]:
        all_rules = []
        for folder in SECURITY_RULE_FOLDERS:
            try:
                rules = self.api_client.get_security_rules(folder=folder, limit=500)
                for r in rules:
                    r["_folder"] = folder
                all_rules.extend(rules)
            except Exception as e:
                logger.warning(f"Failed to pull rules from {folder}: {e}")
        return all_rules

    def _pull_applications(self) -> List[Dict[str, Any]]:
        try:
            return self.api_client.get_applications(folder="Shared", limit=500)
        except Exception:
            try:
                return self.api_client.get_applications(
                    folder="Mobile Users", limit=500
                )
            except Exception as e:
                logger.warning(f"Failed to pull applications: {e}")
                return []

    def _pull_application_groups(self) -> List[Dict[str, Any]]:
        try:
            return self.api_client.get_application_groups(
                folder="Shared", limit=500
            )
        except Exception:
            try:
                return self.api_client.get_application_groups(
                    folder="Mobile Users", limit=500
                )
            except Exception as e:
                logger.warning(f"Failed to pull application groups: {e}")
                return []

    def _pull_application_filters(self) -> List[Dict[str, Any]]:
        try:
            return self.api_client.get_application_filters(
                folder="Shared", limit=500
            )
        except Exception:
            try:
                return self.api_client.get_application_filters(
                    folder="Mobile Users", limit=500
                )
            except Exception as e:
                logger.warning(f"Failed to pull application filters: {e}")
                return []

    def _pull_profile_groups(self) -> List[Dict[str, Any]]:
        try:
            return self.api_client.get_profile_groups(folder="Shared", limit=500)
        except Exception:
            try:
                return self.api_client.get_profile_groups(
                    folder="Mobile Users", limit=500
                )
            except Exception as e:
                logger.warning(f"Failed to pull profile groups: {e}")
                return []

    # ------------------------------------------------------------------
    # Analysis engine
    # ------------------------------------------------------------------

    def _analyze(
        self,
        rules: List[Dict],
        apps: List[Dict],
        app_groups: List[Dict],
        app_filters: List[Dict],
        profile_groups: List[Dict],
        insights: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        recommendations = []

        # Build lookup sets
        profile_group_names = {pg.get("name") for pg in profile_groups}
        app_group_names = {ag.get("name") for ag in app_groups}

        # Expand app groups into individual app sets for reference
        app_group_members = {}
        for ag in app_groups:
            app_group_members[ag.get("name")] = set(ag.get("members", []))

        # Set of all apps explicitly referenced in rules
        rule_referenced_apps = set()
        rules_with_any_app = []
        for rule in rules:
            rule_apps = rule.get("application", [])
            if isinstance(rule_apps, list):
                if "any" in rule_apps:
                    rules_with_any_app.append(rule)
                else:
                    for app_ref in rule_apps:
                        rule_referenced_apps.add(app_ref)
                        # Also expand app group members
                        if app_ref in app_group_members:
                            rule_referenced_apps.update(app_group_members[app_ref])

        # 1. Missing Security Profiles (config-only)
        self.progress.emit("Checking for missing security profiles...", 80)
        recommendations.extend(
            self._check_missing_profiles(rules, profile_group_names)
        )

        # 2. Overly Broad Rules (config + optional insights)
        self.progress.emit("Checking for overly broad rules...", 83)
        recommendations.extend(
            self._check_overly_broad_rules(rules_with_any_app, insights)
        )

        # Insights-dependent checks
        if insights.get("top_apps"):
            # 3. Ungoverned SaaS Apps
            self.progress.emit("Identifying ungoverned SaaS apps...", 86)
            recommendations.extend(
                self._check_ungoverned_apps(
                    insights["top_apps"], rule_referenced_apps, app_group_names
                )
            )

        if insights.get("rule_hits"):
            # 4. Unused Rules
            self.progress.emit("Identifying unused rules...", 90)
            recommendations.extend(
                self._check_unused_rules(rules, insights["rule_hits"])
            )

        # 5. Rule Consolidation (config + optional insights)
        self.progress.emit("Checking for rule consolidation opportunities...", 93)
        recommendations.extend(
            self._check_rule_consolidation(rules, app_group_names)
        )

        # 6. App Group Candidates (insights-dependent)
        if insights.get("app_usage"):
            self.progress.emit("Identifying app group candidates...", 96)
            recommendations.extend(
                self._check_app_group_candidates(
                    insights["app_usage"], app_group_names
                )
            )

        return recommendations

    # ------------------------------------------------------------------
    # Individual recommendation checks
    # ------------------------------------------------------------------

    def _check_missing_profiles(
        self, rules: List[Dict], profile_group_names: set
    ) -> List[Dict]:
        recs = []
        for rule in rules:
            action = rule.get("action", "")
            if action != "allow":
                continue
            # Check if rule has a profile group assigned
            pg = rule.get("profile_setting", {})
            group_list = pg.get("group", []) if isinstance(pg, dict) else []
            if not group_list:
                rule_name = rule.get("name", "unknown")
                folder = rule.get("_folder", "")
                recs.append(
                    {
                        "category": "missing_profiles",
                        "severity": "high",
                        "rule_name": rule_name,
                        "folder": folder,
                        "suggestion": (
                            f"Rule '{rule_name}' in {folder} allows traffic "
                            f"without a security profile group. Attach a "
                            f"profile group to inspect for threats."
                        ),
                        "config_snippet": {
                            "profile_setting": {
                                "group": ["best-practice"]
                            }
                        },
                    }
                )
        return recs

    def _check_overly_broad_rules(
        self, rules_with_any: List[Dict], insights: Dict
    ) -> List[Dict]:
        recs = []
        rule_hit_map = {}
        if insights.get("rule_hits"):
            for rh in insights["rule_hits"]:
                rule_hit_map[rh.get("rule", "")] = rh

        for rule in rules_with_any:
            rule_name = rule.get("name", "unknown")
            folder = rule.get("_folder", "")
            hit_info = rule_hit_map.get(rule_name, {})
            unique_apps = hit_info.get("unique_apps", None)

            severity = "medium"
            detail = ""
            if unique_apps is not None and unique_apps < 50:
                severity = "high"
                detail = (
                    f" Only {unique_apps} unique apps seen in "
                    f"last {self.time_range} days — replace 'any' "
                    f"with an explicit app list."
                )
            else:
                detail = (
                    " Consider narrowing 'application: any' to "
                    "specific apps or app groups."
                )

            recs.append(
                {
                    "category": "overly_broad",
                    "severity": severity,
                    "rule_name": rule_name,
                    "folder": folder,
                    "unique_apps": unique_apps,
                    "suggestion": (
                        f"Rule '{rule_name}' in {folder} uses "
                        f"'application: any'.{detail}"
                    ),
                    "config_snippet": None,
                }
            )
        return recs

    def _check_ungoverned_apps(
        self,
        top_apps: List[Dict],
        rule_referenced_apps: set,
        app_group_names: set,
    ) -> List[Dict]:
        recs = []
        for app_data in top_apps:
            app_name = app_data.get("app", "")
            if not app_name or app_name in ("unknown", "incomplete", "non-syn-tcp"):
                continue
            # Check if app is referenced by any rule (directly or via group)
            if app_name not in rule_referenced_apps:
                risk = app_data.get("risk", "unknown")
                total_bytes = app_data.get("total_bytes", 0)
                category = app_data.get("app_category", "")
                severity = "high" if str(risk) in ("4", "5") else "medium"

                # Format bytes
                if total_bytes > 1_073_741_824:
                    bytes_str = f"{total_bytes / 1_073_741_824:.1f} GB"
                elif total_bytes > 1_048_576:
                    bytes_str = f"{total_bytes / 1_048_576:.1f} MB"
                else:
                    bytes_str = f"{total_bytes / 1024:.1f} KB"

                recs.append(
                    {
                        "category": "ungoverned_apps",
                        "severity": severity,
                        "app_name": app_name,
                        "risk": risk,
                        "category_name": category,
                        "total_bytes": total_bytes,
                        "suggestion": (
                            f"'{app_name}' ({category}, risk {risk}) transferred "
                            f"{bytes_str} but is not referenced in any "
                            f"security rule. Create a rule or add to an app group."
                        ),
                        "config_snippet": {
                            "application": [app_name],
                            "action": "allow",
                            "profile_setting": {"group": ["best-practice"]},
                        },
                    }
                )
        return recs

    def _check_unused_rules(
        self, rules: List[Dict], rule_hits: List[Dict]
    ) -> List[Dict]:
        recs = []
        hit_rule_names = {rh.get("rule", "") for rh in rule_hits if rh.get("hit_count", 0) > 0}
        for rule in rules:
            rule_name = rule.get("name", "unknown")
            if rule.get("disabled"):
                continue
            if rule_name not in hit_rule_names:
                folder = rule.get("_folder", "")
                recs.append(
                    {
                        "category": "unused_rules",
                        "severity": "low",
                        "rule_name": rule_name,
                        "folder": folder,
                        "suggestion": (
                            f"Rule '{rule_name}' in {folder} had zero hits "
                            f"in the last {self.time_range} days. Consider "
                            f"disabling or removing it."
                        ),
                        "config_snippet": None,
                    }
                )
        return recs

    def _check_rule_consolidation(
        self, rules: List[Dict], app_group_names: set
    ) -> List[Dict]:
        recs = []
        # Group rules by their source+destination+action to find overlap
        rule_groups = defaultdict(list)
        for rule in rules:
            apps = rule.get("application", [])
            if not isinstance(apps, list) or "any" in apps:
                continue
            action = rule.get("action", "")
            src = tuple(sorted(rule.get("source", ["any"])))
            dst = tuple(sorted(rule.get("destination", ["any"])))
            key = (src, dst, action, rule.get("_folder", ""))
            rule_groups[key].append(rule)

        for key, group in rule_groups.items():
            if len(group) < 2:
                continue
            # Collect all apps across rules in this group
            all_apps = set()
            rule_names = []
            for r in group:
                rule_names.append(r.get("name", "unknown"))
                for a in r.get("application", []):
                    all_apps.add(a)

            if len(all_apps) >= 3:
                folder = key[3]
                group_name = f"app-group-{'_'.join(sorted(all_apps)[:3])}"
                if len(all_apps) > 3:
                    group_name += f"-plus{len(all_apps) - 3}"
                recs.append(
                    {
                        "category": "rule_consolidation",
                        "severity": "medium",
                        "rule_names": rule_names,
                        "folder": folder,
                        "apps": sorted(all_apps),
                        "suggestion": (
                            f"Rules {', '.join(rule_names)} in {folder} share "
                            f"source/destination/action. Consolidate into one "
                            f"rule with an application group containing "
                            f"{len(all_apps)} apps."
                        ),
                        "config_snippet": {
                            "application_group": {
                                "name": group_name,
                                "members": sorted(all_apps),
                            }
                        },
                    }
                )
        return recs

    def _check_app_group_candidates(
        self, app_usage: List[Dict], app_group_names: set
    ) -> List[Dict]:
        recs = []
        # Find apps that co-occur on the same rules
        rule_to_apps = defaultdict(set)
        for entry in app_usage:
            rule = entry.get("rule", "")
            app = entry.get("app", "")
            if rule and app and app not in ("unknown", "incomplete"):
                rule_to_apps[rule].add(app)

        # Find rules with multiple apps that aren't already in a group
        for rule, apps in rule_to_apps.items():
            if len(apps) < 5:
                continue
            # Check if these apps are already covered by an existing group
            already_grouped = any(a in app_group_names for a in apps)
            if already_grouped:
                continue

            app_list = sorted(apps)
            group_name = f"auto-group-{rule.lower().replace(' ', '-')[:30]}"
            recs.append(
                {
                    "category": "app_group_candidates",
                    "severity": "low",
                    "rule_name": rule,
                    "apps": app_list,
                    "suggestion": (
                        f"{len(apps)} apps co-occur on rule '{rule}'. "
                        f"Create an application group to simplify management."
                    ),
                    "config_snippet": {
                        "application_group": {
                            "name": group_name,
                            "members": app_list[:20],  # Cap at 20 for readability
                        }
                    },
                }
            )
        return recs
