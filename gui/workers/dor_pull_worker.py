"""
Background worker for DoR-specific configuration pull.

Thin wrapper around PullOrchestrator that pulls folders and
infrastructure needed for DoR analysis. Excludes defaults to
focus on custom configuration and speed up the pull.

Also fetches license-types and infrastructure settings to
pre-populate tenant metadata in the DoR questionnaire.
"""

import logging
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class DorPullWorker(QThread):
    """Background worker for pulling config data needed for DoR analysis."""

    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(bool, str, object)  # success, message, Configuration
    license_data = pyqtSignal(object)  # license info dict (emitted before finished)
    auth_data = pyqtSignal(object)  # auth/CIE info dict (emitted before finished)
    mu_data = pyqtSignal(object)  # MU info dict (locations, profiles, tunnel data)
    error = pyqtSignal(str)

    def __init__(self, api_client, connection_name: Optional[str] = None):
        """
        Initialize DoR pull worker.

        Args:
            api_client: Authenticated PrismaAccessAPIClient
            connection_name: Friendly tenant name for metadata
        """
        super().__init__()
        self.api_client = api_client
        self.connection_name = connection_name
        self._cancelled = False
        self._orchestrator = None

    def cancel(self):
        """Request cancellation."""
        self._cancelled = True
        if self._orchestrator:
            self._orchestrator.cancel()

    def run(self):
        """Pull configuration for DoR analysis."""
        try:
            from prisma.pull.pull_orchestrator import PullOrchestrator
            from config.workflows import WorkflowConfig

            self.progress.emit("Initializing DoR pull...", 5)

            # Exclude defaults - we only care about custom configuration
            # for DoR analysis. Default/predefined snippets and items
            # are filtered out, which also makes the pull much faster.
            workflow_config = WorkflowConfig(
                include_defaults=False,
                validate_before_pull=False,
            )
            orchestrator = PullOrchestrator(self.api_client, config=workflow_config)
            self._orchestrator = orchestrator

            # Forward progress from orchestrator
            orchestrator.set_progress_callback(
                lambda msg, pct: self.progress.emit(msg, pct)
            )

            self.progress.emit("Pulling custom configurations...", 10)

            # Pull folders and infrastructure, skip snippets with defaults filtered
            # Folders: custom items from bottom folders (inherited config included)
            # Snippets: only custom snippets (predefined/readonly skipped)
            # Infrastructure: service connections, remote networks, mobile users
            result = orchestrator.pull_all(
                include_folders=True,
                include_snippets=True,
                include_infrastructure=True,
                use_bottom_folders=True,
                infrastructure_filter={
                    'remote_networks': True,
                    'service_connections': True,
                    'mobile_users': True,
                },
            )

            if self._cancelled or (result and result.cancelled):
                self.progress.emit("Pull cancelled", 0)
                self.finished.emit(False, "Pull cancelled by user", None)
                return

            configuration = result.configuration if result else None

            if not configuration:
                from config.models.containers import Configuration
                from datetime import datetime

                configuration = Configuration(
                    source_tsg=self.api_client.tsg_id,
                    load_type='From Pull (DoR)',
                    saved_credentials_ref=self.connection_name,
                )
                configuration.source_tenant = self.connection_name
                configuration.created_at = datetime.now().isoformat()
                configuration.modified_at = datetime.now().isoformat()

            # Set metadata
            configuration.source_tenant = self.connection_name
            configuration.saved_credentials_ref = self.connection_name

            # Fetch license and tenant metadata (separate from config pull)
            self.progress.emit("Fetching license information...", 90)
            license_info = self._fetch_license_info()
            if license_info:
                self.license_data.emit(license_info)

            # Analyze authentication profiles and fetch CIE domains if applicable
            self.progress.emit("Analyzing authentication profiles...", 95)
            auth_info = self._fetch_auth_info(configuration)
            if auth_info:
                self.auth_data.emit(auth_info)

            # Fetch Mobile Users agent config (locations, profiles, tunnel)
            self.progress.emit("Analyzing Mobile Users configuration...", 97)
            mu_info = self._fetch_mu_info()
            if mu_info:
                self.mu_data.emit(mu_info)

            total_items = len(configuration.get_all_items())
            self.progress.emit(f"Pull complete: {total_items} items", 100)

            self.finished.emit(
                True,
                f"Successfully pulled {total_items} configuration items",
                configuration,
            )

        except Exception as e:
            logger.exception(f"DoR pull failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(False, f"Pull failed: {e}", None)

    def _fetch_license_info(self) -> Optional[Dict[str, Any]]:
        """
        Fetch license types and infrastructure settings from the tenant.

        Returns:
            Dict with license info, or None if fetch fails
        """
        info: Dict[str, Any] = {
            'licenses': [],
            'panorama_managed': False,
            'serial_number': None,
        }

        # Fetch license-types
        try:
            raw = self.api_client.get_license_types()
            logger.info(f"License-types response: {raw}")

            if isinstance(raw, list):
                info['licenses'] = raw
            elif isinstance(raw, dict):
                # Could be a single object or wrapped
                if 'data' in raw:
                    info['licenses'] = raw['data']
                else:
                    info['licenses'] = [raw]
        except Exception as e:
            logger.warning(f"Failed to fetch license-types: {e}")

        # Fetch shared infrastructure settings for panorama/serial info
        try:
            infra_settings = self.api_client.get_shared_infrastructure_settings()
            logger.info(f"Infrastructure settings keys: {list(infra_settings.keys()) if isinstance(infra_settings, dict) else type(infra_settings)}")

            if isinstance(infra_settings, dict):
                # Check for panorama management
                mgmt = infra_settings.get('management', {})
                if isinstance(mgmt, dict):
                    info['panorama_managed'] = mgmt.get('panorama_managed', False)

                # Look for serial number in various possible locations
                for key in ('serial_number', 'serial', 'device_serial'):
                    val = infra_settings.get(key)
                    if val:
                        info['serial_number'] = val
                        break

                # Store full response for debugging
                info['infra_settings_raw'] = infra_settings
        except Exception as e:
            logger.warning(f"Failed to fetch infrastructure settings: {e}")

        has_data = bool(
            info['licenses']
            or info['serial_number'] is not None
            or info.get('infra_settings_raw')
        )
        return info if has_data else None

    def _fetch_auth_info(self, configuration) -> Optional[Dict[str, Any]]:
        """
        Analyze authentication profiles from pulled config and fetch CIE
        domain info if Cloud Identity Engine is in use.

        Args:
            configuration: Pulled Configuration object

        Returns:
            Dict with auth method summary and CIE domain info, or None
        """
        info: Dict[str, Any] = {
            'auth_profiles': [],
            'auth_methods': [],  # deduplicated method types found
            'has_cie': False,
            'cie_domains': [],
        }

        # Map internal method keys to human-readable names
        method_labels = {
            'saml_idp': 'SAML IdP',
            'ldap': 'LDAP',
            'radius': 'RADIUS',
            'kerberos': 'Kerberos',
            'local_database': 'Local Database',
            'cloud': 'Cloud Identity Engine (CIE)',
            'cloud_authentication_service': 'Cloud Identity Engine (CIE)',
        }

        try:
            auth_profiles = configuration.get_items_by_type('authentication_profile')
            methods_seen = set()

            for profile in auth_profiles:
                method_type = getattr(profile, 'method_type', None)
                is_cie = getattr(profile, 'is_cie_profile', False)

                profile_info = {
                    'name': profile.name,
                    'folder': profile.folder,
                    'method_type': method_type,
                    'method_label': method_labels.get(method_type, method_type or 'Unknown'),
                    'is_cie': is_cie,
                }

                # Extract SAML IdP server URL if present
                raw = getattr(profile, 'raw_config', {})
                method_data = raw.get('method', {})
                if method_type == 'saml_idp' and isinstance(method_data.get('saml_idp'), dict):
                    saml = method_data['saml_idp']
                    profile_info['saml_certificate'] = saml.get('certificate_profile', '')
                    profile_info['saml_sso_url'] = saml.get('sso_url', '')

                info['auth_profiles'].append(profile_info)

                if method_type:
                    methods_seen.add(method_type)
                if is_cie:
                    info['has_cie'] = True

            info['auth_methods'] = [
                method_labels.get(m, m) for m in sorted(methods_seen)
            ]

            logger.info(
                f"Auth analysis: {len(auth_profiles)} profiles, "
                f"methods={info['auth_methods']}, has_cie={info['has_cie']}"
            )
        except Exception as e:
            logger.warning(f"Failed to analyze auth profiles: {e}")

        # If CIE detected, fetch domains from the CIE directory-sync API
        if info['has_cie']:
            try:
                self.progress.emit("Fetching CIE directory domains...", 97)
                domains = self.api_client.get_cie_domains()
                logger.info(f"CIE domains response: {len(domains)} domain(s)")

                for domain in domains:
                    if isinstance(domain, dict):
                        info['cie_domains'].append({
                            'domain': domain.get('domain', ''),
                            'type': domain.get('type', ''),
                            'netbios': domain.get('netbios', ''),
                            'status': domain.get('status', {}).get('description', ''),
                            'user_count': domain.get('count', {}).get('user', 0),
                            'group_count': domain.get('count', {}).get('group', 0),
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch CIE domains: {e}")

        return info if info['auth_profiles'] or info['cie_domains'] else None

    def _fetch_mu_info(self) -> Optional[Dict[str, Any]]:
        """
        Fetch Mobile Users agent configuration: locations, profiles,
        and tunnel profiles for DoR analysis.

        Returns:
            Dict with location/profile/tunnel analysis, or None if all fail
        """
        # Default split tunnel exclusions for comparison
        DEFAULT_SPLIT_TUNNEL_APPS = {
            'dailymotion', 'hulu-base', 'netflix-streaming', 'sling',
            'vimeo-base', 'vimeo-create', 'vimeo-delete', 'vimeo-download',
            'xfinity-tv', 'youku-base', 'youtube-streaming',
            'ms-update', 'zoom',
        }

        info: Dict[str, Any] = {
            'locations': None,
            'location_regions': [],
            'profiles': None,
            'profile_analysis': {
                'has_managed': False,
                'has_byod': False,
                'device_assignment': None,
                'has_pre_logon': False,
                'has_always_on': False,
                'connect_method': None,
                'connect_methods': [],
            },
            'tunnel_profiles': None,
            'bypass_analysis': {
                'excluded_apps': [],
                'is_default_only': True,
                'summary': None,
            },
        }
        has_data = False

        # --- Locations ---
        try:
            locations = self.api_client.get_mobile_agent_locations(
                folder="Mobile Users"
            )
            info['locations'] = locations
            logger.info(f"MU locations response type: {type(locations)}")

            # Extract region names from location data
            # PA API can return various formats:
            #   {"region": "americas"}
            #   {"region": {"americas": ["us-east-1", ...]}}
            #   {"region": ["americas", "europe"]}
            #   {"data": [{"region": "americas"}, ...]}
            regions = set()

            def _extract_regions_recursive(obj, depth=0):
                """Recursively extract region name strings from nested structures."""
                if depth > 4:
                    return
                if isinstance(obj, str):
                    regions.add(obj)
                elif isinstance(obj, list):
                    for item in obj:
                        _extract_regions_recursive(item, depth + 1)
                elif isinstance(obj, dict):
                    # Dict keys at the right level are region names
                    # e.g. {"americas": ["us-east-1"]} -> "americas"
                    for key, val in obj.items():
                        if key in ('data', 'region', 'regions', 'locations',
                                   'location', 'name', 'folder', 'id'):
                            # Structural keys — recurse into value
                            _extract_regions_recursive(val, depth + 1)
                        elif key.startswith('_') or key in ('snippet',):
                            continue
                        else:
                            # Key itself is likely a region name
                            regions.add(key)
                            # Also recurse into sub-locations
                            if isinstance(val, list):
                                for sub in val:
                                    if isinstance(sub, str):
                                        regions.add(sub)

            _extract_regions_recursive(locations)
            logger.info(f"MU locations raw: {locations}")

            info['location_regions'] = sorted(regions)
            if regions:
                has_data = True
            logger.info(f"MU location regions: {info['location_regions']}")
        except Exception as e:
            logger.warning(f"Failed to fetch MU locations: {e}")

        # --- Agent Profiles ---
        try:
            profiles = self.api_client.get_mobile_agent_profiles(
                folder="Mobile Users"
            )
            info['profiles'] = profiles
            logger.info(f"MU profiles response type: {type(profiles)}")

            # Analyze profiles for device assignment and connect method
            profile_list = []
            if isinstance(profiles, dict):
                profile_list = profiles.get('data', [])
                if not profile_list:
                    # Single profile dict
                    profile_list = [profiles]
            elif isinstance(profiles, list):
                profile_list = profiles

            connect_methods = set()
            has_managed = False
            has_byod = False
            has_pre_logon = False
            has_always_on = False

            for profile in profile_list:
                if not isinstance(profile, dict):
                    continue

                # Check for managed (device cert) vs BYOD
                cert = profile.get('certificate', {})
                if isinstance(cert, dict):
                    criteria = cert.get('criteria', {})
                    if isinstance(criteria, dict) and criteria.get('certificate_profile'):
                        has_managed = True
                    else:
                        has_byod = True
                else:
                    has_byod = True

                # Check connect method
                connect_method = profile.get('connect-method')
                if connect_method:
                    connect_methods.add(connect_method)
                    if connect_method == 'pre-logon':
                        has_pre_logon = True

                # Check always-on indicators
                if profile.get('enforce-globalprotect') == 'yes':
                    has_always_on = True
                if profile.get('traffic-enforcement') == 'yes':
                    has_always_on = True

            # Determine device assignment
            if has_managed and has_byod:
                device_assignment = "Both"
            elif has_managed:
                device_assignment = "Managed"
            elif has_byod and profile_list:
                device_assignment = "BYOD"
            else:
                device_assignment = None

            # Determine connect method summary
            if has_pre_logon and has_always_on:
                connect_method_summary = "Pre-logon + Always-On"
            elif has_always_on:
                connect_method_summary = "Always-On"
            elif has_pre_logon:
                connect_method_summary = "Pre-logon + Always-On"
            elif profile_list:
                connect_method_summary = "On-demand"
            else:
                connect_method_summary = None

            info['profile_analysis'] = {
                'has_managed': has_managed,
                'has_byod': has_byod,
                'device_assignment': device_assignment,
                'has_pre_logon': has_pre_logon,
                'has_always_on': has_always_on,
                'connect_method': connect_method_summary,
                'connect_methods': sorted(connect_methods),
            }
            if profile_list:
                has_data = True

            logger.info(
                f"MU profile analysis: device={device_assignment}, "
                f"connect={connect_method_summary}, methods={sorted(connect_methods)}"
            )
        except Exception as e:
            logger.warning(f"Failed to fetch MU agent profiles: {e}")

        # --- Tunnel Profiles ---
        try:
            tunnel_profiles = self.api_client.get_mobile_agent_tunnel_profiles(
                folder="Mobile Users"
            )
            info['tunnel_profiles'] = tunnel_profiles
            logger.info(f"MU tunnel profiles response type: {type(tunnel_profiles)}")

            # Analyze split tunnel exclusions
            tunnel_list = []
            if isinstance(tunnel_profiles, dict):
                tunnel_list = tunnel_profiles.get('data', [])
                if not tunnel_list:
                    tunnel_list = [tunnel_profiles]
            elif isinstance(tunnel_profiles, list):
                tunnel_list = tunnel_profiles

            excluded_apps = set()
            for tunnel in tunnel_list:
                if not isinstance(tunnel, dict):
                    continue
                # Look for split tunnel excluded applications
                split = tunnel.get('split-tunneling', {})
                if isinstance(split, dict):
                    exclude_apps = split.get('exclude-applications', [])
                    if isinstance(exclude_apps, list):
                        excluded_apps.update(exclude_apps)
                    elif isinstance(exclude_apps, str):
                        excluded_apps.add(exclude_apps)

            sorted_apps = sorted(excluded_apps)
            is_default_only = (
                excluded_apps == DEFAULT_SPLIT_TUNNEL_APPS
                or excluded_apps.issubset(DEFAULT_SPLIT_TUNNEL_APPS)
            )

            # Build summary
            if not excluded_apps:
                summary = "No split tunnel exclusions configured"
            elif is_default_only:
                summary = f"Default exclusions only ({len(excluded_apps)} apps: video streaming + MS Update + Zoom)"
            else:
                custom_apps = excluded_apps - DEFAULT_SPLIT_TUNNEL_APPS
                default_present = excluded_apps & DEFAULT_SPLIT_TUNNEL_APPS
                parts = []
                if default_present:
                    parts.append(f"{len(default_present)} default apps")
                if custom_apps:
                    parts.append(f"{len(custom_apps)} custom: {', '.join(sorted(custom_apps))}")
                summary = f"Split tunnel exclusions: {' + '.join(parts)}"

            info['bypass_analysis'] = {
                'excluded_apps': sorted_apps,
                'is_default_only': is_default_only,
                'summary': summary,
            }
            if tunnel_list:
                has_data = True

            logger.info(f"MU bypass analysis: {len(excluded_apps)} apps, default_only={is_default_only}")
        except Exception as e:
            logger.warning(f"Failed to fetch MU tunnel profiles: {e}")

        return info if has_data else None
