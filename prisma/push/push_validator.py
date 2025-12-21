"""
Push Validation for Prisma Access Configurations.

This module provides pre-push validation to ensure configurations are valid
before attempting to push them to a target tenant.
"""

from typing import Dict, Any, List, Optional
from ..dependencies.dependency_resolver import DependencyResolver


class PushValidator:
    """Validate configurations before pushing to target tenant."""

    def __init__(self):
        """Initialize push validator."""
        self.dependency_resolver = DependencyResolver()
        self.validation_errors: List[Dict[str, Any]] = []
        self.validation_warnings: List[Dict[str, Any]] = []

    def validate_configuration(
        self,
        config: Dict[str, Any],
        target_api_client: Any,  # PrismaAccessAPIClient
        check_dependencies: bool = True,
        check_permissions: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate configuration before push.

        Args:
            config: Configuration to validate
            target_api_client: API client for target tenant
            check_dependencies: Whether to check dependencies
            check_permissions: Whether to check API permissions

        Returns:
            Dictionary with validation results
        """
        self.validation_errors = []
        self.validation_warnings = []

        # Validate schema structure
        schema_valid = self._validate_schema(config)

        # Validate dependencies
        dependency_valid = True
        if check_dependencies:
            dependency_valid = self._validate_dependencies(config)

        # Validate permissions (basic check)
        permissions_valid = True
        if check_permissions:
            permissions_valid = self._validate_permissions(config, target_api_client)

        # Validate folder existence
        folder_valid = self._validate_folders(config, target_api_client)

        return {
            "valid": (
                schema_valid
                and dependency_valid
                and permissions_valid
                and folder_valid
                and len(self.validation_errors) == 0
            ),
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "error_count": len(self.validation_errors),
            "warning_count": len(self.validation_warnings),
        }

    def _validate_schema(self, config: Dict[str, Any]) -> bool:
        """Validate configuration schema."""
        # Check required top-level keys
        required_keys = ["metadata", "security_policies"]
        for key in required_keys:
            if key not in config:
                self.validation_errors.append(
                    {
                        "type": "schema",
                        "message": f"Missing required key: {key}",
                        "severity": "error",
                    }
                )
                return False

        # Validate metadata
        metadata = config.get("metadata", {})
        if "version" not in metadata:
            self.validation_warnings.append(
                {
                    "type": "schema",
                    "message": "Missing version in metadata",
                    "severity": "warning",
                }
            )

        # Validate security_policies structure
        security_policies = config.get("security_policies", {})
        if "folders" not in security_policies and "snippets" not in security_policies:
            self.validation_warnings.append(
                {
                    "type": "schema",
                    "message": "No folders or snippets in security_policies",
                    "severity": "warning",
                }
            )

        return True

    def _validate_dependencies(self, config: Dict[str, Any]) -> bool:
        """Validate dependencies are present."""
        validation = self.dependency_resolver.validate_dependencies(config)

        if not validation.get("valid", True):
            missing = validation.get("missing_dependencies", {})
            for obj_name, missing_deps in missing.items():
                self.validation_errors.append(
                    {
                        "type": "dependency",
                        "object": obj_name,
                        "message": f'Missing dependencies: {", ".join(missing_deps[:5])}',
                        "missing_dependencies": missing_deps,
                        "severity": "error",
                    }
                )
            return False

        return True

    def _validate_permissions(self, config: Dict[str, Any], api_client: Any) -> bool:
        """Validate API permissions (basic check)."""
        # Try to access folders endpoint as a permission check
        try:
            api_client.get_security_policy_folders()
            return True
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                self.validation_errors.append(
                    {
                        "type": "permission",
                        "message": "Insufficient permissions: Cannot access folders endpoint",
                        "severity": "error",
                    }
                )
                return False
            else:
                # Other errors might be temporary
                self.validation_warnings.append(
                    {
                        "type": "permission",
                        "message": f"Could not verify permissions: {e}",
                        "severity": "warning",
                    }
                )
                return True

    def _validate_folders(self, config: Dict[str, Any], api_client: Any) -> bool:
        """Validate that folders exist in target tenant."""
        security_policies = config.get("security_policies", {})
        folders = security_policies.get("folders", [])

        if not folders:
            return True

        # Get available folders from target
        try:
            from ..pull.folder_capture import FolderCapture

            folder_capture = FolderCapture(api_client)
            available_folders = folder_capture.list_folders_for_capture(
                include_defaults=True
            )
            available_folder_names = set(available_folders)

            # Check if folders in config exist in target
            for folder in folders:
                folder_name = folder.get("name", "")
                if folder_name and folder_name not in available_folder_names:
                    self.validation_warnings.append(
                        {
                            "type": "folder",
                            "folder": folder_name,
                            "message": f'Folder "{folder_name}" may not exist in target tenant',
                            "severity": "warning",
                        }
                    )
        except Exception as e:
            self.validation_warnings.append(
                {
                    "type": "folder",
                    "message": f"Could not verify folder existence: {e}",
                    "severity": "warning",
                }
            )

        return True

    def get_validation_report(self) -> Dict[str, Any]:
        """
        Get validation report.

        Returns:
            Dictionary with validation report
        """
        return {
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "error_count": len(self.validation_errors),
            "warning_count": len(self.validation_warnings),
            "valid": len(self.validation_errors) == 0,
        }
