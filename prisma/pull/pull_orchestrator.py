"""
Pull orchestration for Prisma Access configuration capture.

This module orchestrates the complete pull process, coordinating all
capture modules and providing progress tracking and error handling.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time

from ..api_client import PrismaAccessAPIClient
from .folder_capture import FolderCapture
from .rule_capture import RuleCapture
from .object_capture import ObjectCapture
from .profile_capture import ProfileCapture
from .snippet_capture import SnippetCapture


class PullOrchestrator:
    """Orchestrate the complete configuration pull process."""
    
    def __init__(self, api_client: PrismaAccessAPIClient):
        """
        Initialize pull orchestrator.
        
        Args:
            api_client: PrismaAccessAPIClient instance
        """
        self.api_client = api_client
        self.folder_capture = FolderCapture(api_client)
        self.rule_capture = RuleCapture(api_client)
        self.object_capture = ObjectCapture(api_client)
        self.profile_capture = ProfileCapture(api_client)
        self.snippet_capture = SnippetCapture(api_client)
        
        self.progress_callback: Optional[Callable[[str, int, int], None]] = None
        self.error_handler: Optional[Callable[[str, Exception], None]] = None
        
        self.stats = {
            'folders_captured': 0,
            'rules_captured': 0,
            'objects_captured': 0,
            'profiles_captured': 0,
            'snippets_captured': 0,
            'errors': []
        }
    
    def set_progress_callback(self, callback: Callable[[str, int, int], None]):
        """
        Set progress callback function.
        
        Args:
            callback: Function(message, current, total)
        """
        self.progress_callback = callback
    
    def set_error_handler(self, handler: Callable[[str, Exception], None]):
        """
        Set error handler function.
        
        Args:
            handler: Function(message, exception)
        """
        self.error_handler = handler
    
    def _report_progress(self, message: str, current: int = 0, total: int = 0):
        """Report progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(message, current, total)
        else:
            print(f"[{current}/{total}] {message}")
    
    def _handle_error(self, message: str, error: Exception):
        """Handle error if handler is set."""
        self.stats['errors'].append({'message': message, 'error': str(error)})
        
        if self.error_handler:
            self.error_handler(message, error)
        else:
            print(f"Error: {message} - {error}")
    
    def pull_folder_configuration(
        self,
        folder_name: str,
        include_objects: bool = True,
        include_profiles: bool = True
    ) -> Dict[str, Any]:
        """
        Pull complete configuration for a single folder.
        
        Args:
            folder_name: Name of the folder
            include_objects: Whether to capture objects
            include_profiles: Whether to capture profiles
            
        Returns:
            Complete folder configuration dictionary
        """
        folder_config = {
            'name': folder_name,
            'path': f"/config/security-policy/folders/{folder_name}",
            'is_default': self.folder_capture._is_default_folder(folder_name),
            'security_rules': [],
            'objects': {},
            'profiles': {}
        }
        
        try:
            # Capture security rules (reduced verbosity - progress callback handles output)
            self._report_progress(f"Capturing rules from {folder_name}", 1, 3)
            rules = self.rule_capture.capture_rules_from_folder(folder_name)
            folder_config['security_rules'] = rules
            self.stats['rules_captured'] += len(rules)
            
            # Capture objects (reduced verbosity)
            if include_objects:
                self._report_progress(f"Capturing objects from {folder_name}", 2, 3)
                objects = self.object_capture.capture_all_objects(folder=folder_name)
                folder_config['objects'] = objects
                self.stats['objects_captured'] += sum(len(objs) for objs in objects.values())
            
            # Capture profiles (reduced verbosity)
            if include_profiles:
                self._report_progress(f"Capturing profiles from {folder_name}", 3, 3)
                profiles = self.profile_capture.capture_all_profiles(folder=folder_name)
                folder_config['profiles'] = profiles
                
                # Count profiles
                auth_count = len(profiles.get('authentication_profiles', []))
                sec_count = sum(len(profs) for profs in profiles.get('security_profiles', {}).values())
                # Decryption profiles is now a list, not a dict
                dec_profiles = profiles.get('decryption_profiles', [])
                dec_count = len(dec_profiles) if isinstance(dec_profiles, list) else sum(len(profs) for profs in dec_profiles.values())
                self.stats['profiles_captured'] += auth_count + sec_count + dec_count
            
            self.stats['folders_captured'] += 1
            
        except Exception as e:
            self._handle_error(f"Error pulling folder {folder_name}", e)
        
        return folder_config
    
    def pull_all_folders(
        self,
        folder_names: Optional[List[str]] = None,
        include_defaults: bool = False,
        include_objects: bool = True,
        include_profiles: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Pull configuration for all folders.
        
        Args:
            folder_names: List of folder names (None = all folders)
            include_defaults: Whether to include default folders
            include_objects: Whether to capture objects
            include_profiles: Whether to capture profiles
            
        Returns:
            List of complete folder configurations
        """
        if folder_names is None:
            folder_names = self.folder_capture.list_folders_for_capture(include_defaults=include_defaults)
        
        total_folders = len(folder_names)
        folder_configs = []
        
        for idx, folder_name in enumerate(folder_names, 1):
            self._report_progress(f"Pulling folder {folder_name}", idx, total_folders)
            folder_config = self.pull_folder_configuration(
                folder_name,
                include_objects=include_objects,
                include_profiles=include_profiles
            )
            folder_configs.append(folder_config)
        
        return folder_configs
    
    def pull_snippets(self) -> List[Dict[str, Any]]:
        """
        Pull all snippet configurations.
        
        Returns:
            List of complete snippet configurations
        """
        try:
            snippets = self.snippet_capture.capture_all_snippets()
            self.stats['snippets_captured'] = len(snippets)
            return snippets
        except Exception as e:
            self._handle_error("Error pulling snippets", e)
            return []
    
    def pull_complete_configuration(
        self,
        folder_names: Optional[List[str]] = None,
        include_defaults: bool = False,
        include_snippets: bool = True,
        include_objects: bool = True,
        include_profiles: bool = True
    ) -> Dict[str, Any]:
        """
        Pull complete Prisma Access configuration.
        
        Args:
            folder_names: List of folder names (None = all folders)
            include_defaults: Whether to include default folders
            include_snippets: Whether to capture snippets
            include_objects: Whether to capture objects
            include_profiles: Whether to capture profiles
            
        Returns:
            Complete configuration dictionary in v2 format
        """
        from config.schema.config_schema_v2 import create_empty_config_v2
        
        # Initialize configuration
        config = create_empty_config_v2(
            source_tenant=self.api_client.tsg_id,
            source_type="scm",
            description="Complete configuration pull"
        )
        
        # Reset stats
        self.stats = {
            'folders_captured': 0,
            'rules_captured': 0,
            'objects_captured': 0,
            'profiles_captured': 0,
            'snippets_captured': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            # Pull folders
            self._report_progress("Pulling folder configurations", 0, 3)
            folder_configs = self.pull_all_folders(
                folder_names=folder_names,
                include_defaults=include_defaults,
                include_objects=include_objects,
                include_profiles=include_profiles
            )
            config['security_policies']['folders'] = folder_configs
            
            # Pull snippets
            if include_snippets:
                self._report_progress("Pulling snippet configurations", 1, 3)
                snippet_configs = self.pull_snippets()
                config['security_policies']['snippets'] = snippet_configs
            
            # Pull infrastructure (if needed)
            self._report_progress("Pulling infrastructure settings", 2, 3)
            try:
                infra_settings = self.api_client.get_shared_infrastructure_settings()
                config['infrastructure']['shared_infrastructure_settings'] = infra_settings
            except Exception as e:
                self._handle_error("Error pulling infrastructure settings", e)
            
            elapsed_time = time.time() - start_time
            
            # Add pull metadata
            config['metadata']['pull_stats'] = {
                'folders': self.stats['folders_captured'],
                'rules': self.stats['rules_captured'],
                'objects': self.stats['objects_captured'],
                'profiles': self.stats['profiles_captured'],
                'snippets': self.stats['snippets_captured'],
                'errors': len(self.stats['errors']),
                'elapsed_seconds': elapsed_time
            }
            
            self._report_progress("Pull complete", 3, 3)
            
        except Exception as e:
            self._handle_error("Error during complete pull", e)
        
        return config
    
    def get_pull_report(self) -> Dict[str, Any]:
        """
        Get pull statistics and report.
        
        Returns:
            Pull report dictionary
        """
        return {
            'stats': self.stats.copy(),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
