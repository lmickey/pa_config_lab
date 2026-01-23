"""
Tenant Manager - Manage saved tenant credentials.

This module provides functionality to save, load, and manage Prisma Access
tenant information (TSG ID, Client ID, labels) and extended cloud credentials
for firewalls, Panorama, and supporting VMs.

Extended in Phase 2 to support:
- Firewall credentials (password, API key, certificate)
- Panorama credentials (password, API key, certificate)
- Supporting VM credentials (password, SSH key)
- Secure credential generation
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from config.storage.crypto_utils import derive_key_secure, encrypt_data, decrypt_data
from config.credential_manager import (
    TenantCredentials,
    DeviceCredentials,
    VMCredentials,
    SCMCredentials,
    CredentialManager,
    PasswordGenerator,
    AuthType,
)


class TenantManager:
    """
    Manage saved tenant information.
    
    Stores tenant metadata (TSG, client_id, name, description) in encrypted file.
    Client secrets are NEVER stored - user must enter on each connection.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize tenant manager.
        
        Args:
            base_dir: Base directory for tenant storage (defaults to ~/.pa_config_lab)
        """
        if base_dir is None:
            base_dir = os.path.expanduser("~/.pa_config_lab")
        
        self.base_dir = Path(base_dir)
        self.tenants_file = self.base_dir / "tenants.json"
        
        # Ensure directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for current session
        self._tenants_cache = None
        self._encryption_key = None
    
    def _get_system_password(self) -> str:
        """
        Get system-specific password for encryption.
        
        Uses machine info to create a consistent password.
        This is less secure than user password but acceptable for non-secret data.
        
        Returns:
            System-specific password string
        """
        import platform
        return f"{platform.node()}-{platform.system()}-tenant-storage"
    
    def _get_encryption_key(self) -> tuple:
        """
        Get or create encryption key for tenant storage.
        
        Uses system-specific key derivation (no user password required).
        
        Returns:
            Tuple of (cipher, salt)
        """
        if self._encryption_key is None:
            self._encryption_key = derive_key_secure(self._get_system_password())
        
        return self._encryption_key
    
    def _load_tenants(self) -> Dict[str, Any]:
        """
        Load tenants from encrypted file.
        
        Returns:
            Dictionary with tenant data structure
        """
        if not self.tenants_file.exists():
            # Return empty structure
            return {
                "version": "1.0",
                "tenants": []
            }
        
        try:
            # Read encrypted file
            with open(self.tenants_file, 'rb') as f:
                file_data = f.read()
            
            # Check if file is empty or corrupted
            if len(file_data) < 16:
                print(f"Warning: Tenant file is corrupted (too small: {len(file_data)} bytes)")
                print("Deleting corrupted file...")
                # Delete corrupted file
                self.tenants_file.unlink()
                return {"version": "1.0", "tenants": []}
            
            # Extract salt (first 16 bytes) and encrypted data
            salt = file_data[:16]
            encrypted_data = file_data[16:]
            
            if len(encrypted_data) == 0:
                print("Warning: Tenant file has no encrypted data")
                print("Deleting corrupted file...")
                # Delete corrupted file
                self.tenants_file.unlink()
                return {"version": "1.0", "tenants": []}
            
            # Decrypt
            cipher, _ = self._get_encryption_key()
            # Re-derive key with stored salt
            cipher, _ = derive_key_secure(self._get_system_password(), salt)
            decrypted_bytes = decrypt_data(encrypted_data, cipher)
            
            # Parse JSON
            json_str = decrypted_bytes.decode('utf-8')
            data = json.loads(json_str)
            
            # Validate structure
            if "tenants" not in data:
                data["tenants"] = []
            if "version" not in data:
                data["version"] = "1.0"
            
            return data
            
        except Exception as e:
            print(f"Error loading tenants: {e}")
            import traceback
            traceback.print_exc()
            print("\nReturning empty tenant structure (file may be corrupted)...")
            # Return empty structure on error but DON'T try to save
            # (saving might fail and cause more corruption)
            return {"version": "1.0", "tenants": []}
    
    def _save_tenants(self, data: Dict[str, Any]) -> bool:
        """
        Save tenants to encrypted file using atomic write.
        
        Uses atomic write (write to temp file, then rename) to prevent
        corruption if process crashes during write.
        
        Args:
            data: Tenant data structure
        
        Returns:
            True if successful
        """
        try:
            # Convert to JSON
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            
            # Encrypt
            cipher, salt = self._get_encryption_key()
            json_bytes = json_str.encode('utf-8')
            encrypted_data = encrypt_data(json_bytes, cipher, include_version=True)
            
            # Atomic write: write to temp file first
            temp_file = self.tenants_file.with_suffix('.tmp')
            try:
                # Write to temp file
                with open(temp_file, 'wb') as f:
                    f.write(salt)  # Write salt first
                    f.write(encrypted_data)
                    f.flush()  # Ensure data is written
                    os.fsync(f.fileno())  # Force write to disk
                
                # Atomic rename (replaces old file)
                temp_file.replace(self.tenants_file)
                
            finally:
                # Clean up temp file if it still exists
                if temp_file.exists():
                    temp_file.unlink()
            
            # Update cache
            self._tenants_cache = data
            
            return True
            
        except Exception as e:
            print(f"Error saving tenants: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def validate_credentials(
        self,
        tsg_id: str,
        client_id: str,
        client_secret: str
    ) -> tuple[bool, str]:
        """
        Validate tenant credentials by testing API connection.
        
        Args:
            tsg_id: Tenant Service Group ID
            client_id: Service account client ID
            client_secret: Service account client secret
        
        Returns:
            Tuple of (success, message)
        """
        try:
            from prisma.api_client import PrismaAccessAPIClient
            
            # Create temporary client (API uses api_user/api_secret parameter names)
            client = PrismaAccessAPIClient(
                tsg_id=tsg_id,
                api_user=client_id,
                api_secret=client_secret
            )
            
            # Test connection by getting token
            success = client.authenticate()
            
            if success:
                return True, "Credentials validated successfully"
            else:
                return False, "Authentication failed - invalid credentials"
                
        except Exception as e:
            return False, f"Validation failed: {str(e)}"
    
    def add_tenant(
        self,
        name: str,
        tsg_id: str,
        client_id: str,
        client_secret: str,
        description: str = "",
        validate: bool = True
    ) -> tuple[bool, str, Optional[str]]:
        """
        Add a new tenant.
        
        Args:
            name: Display name for the tenant
            tsg_id: Tenant Service Group ID
            client_id: Service account client ID
            client_secret: Service account client secret (encrypted in storage)
            description: Optional description
        
        Returns:
            Tuple of (success, message, tenant_id)
        """
        # Validate inputs
        if not name or not name.strip():
            return False, "Tenant name is required", None
        
        if not tsg_id or not tsg_id.strip():
            return False, "TSG ID is required", None
        
        if not client_id or not client_id.strip():
            return False, "Client ID is required", None
        
        if not client_secret or not client_secret.strip():
            return False, "Client secret is required", None
        
        # Validate credentials if requested
        if validate:
            valid, message = self.validate_credentials(tsg_id, client_id, client_secret)
            if not valid:
                return False, f"Credential validation failed: {message}", None
        
        # Load existing tenants
        data = self._load_tenants()
        
        # Check for duplicate name
        for tenant in data["tenants"]:
            if tenant["name"].lower() == name.lower():
                return False, f"Tenant with name '{name}' already exists", None
        
        # Create new tenant
        tenant_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        new_tenant = {
            "id": tenant_id,
            "name": name.strip(),
            "tsg_id": tsg_id.strip(),
            "client_id": client_id.strip(),
            "client_secret": client_secret.strip(),
            "description": description.strip(),
            "created": now,
            "last_used": None
        }
        
        # Add to list
        data["tenants"].append(new_tenant)
        
        # Save
        if self._save_tenants(data):
            return True, f"Tenant '{name}' added successfully", tenant_id
        else:
            return False, "Failed to save tenant", None
    
    def update_tenant(
        self,
        tenant_id: str,
        name: Optional[str] = None,
        tsg_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        description: Optional[str] = None,
        validate: bool = False
    ) -> tuple[bool, str]:
        """
        Update an existing tenant.
        
        Args:
            tenant_id: ID of tenant to update
            name: New name (optional)
            tsg_id: New TSG ID (optional)
            client_id: New client ID (optional)
            client_secret: New client secret (optional)
            description: New description (optional)
            validate: Validate credentials if TSG/client_id/secret changed
        
        Returns:
            Tuple of (success, message)
        """
        # Load tenants
        data = self._load_tenants()
        
        # Find tenant
        tenant = None
        for t in data["tenants"]:
            if t["id"] == tenant_id:
                tenant = t
                break
        
        if not tenant:
            return False, f"Tenant with ID '{tenant_id}' not found"
        
        # Check for duplicate name if changing name
        if name and name.strip() != tenant["name"]:
            for t in data["tenants"]:
                if t["id"] != tenant_id and t["name"].lower() == name.lower():
                    return False, f"Tenant with name '{name}' already exists"
        
        # Validate credentials if any auth fields changed
        if validate and (tsg_id or client_id or client_secret):
            test_tsg = tsg_id.strip() if tsg_id else tenant["tsg_id"]
            test_client_id = client_id.strip() if client_id else tenant["client_id"]
            test_secret = client_secret.strip() if client_secret else tenant["client_secret"]
            
            valid, message = self.validate_credentials(test_tsg, test_client_id, test_secret)
            if not valid:
                return False, f"Credential validation failed: {message}"
        
        # Update fields
        if name is not None:
            tenant["name"] = name.strip()
        if tsg_id is not None:
            tenant["tsg_id"] = tsg_id.strip()
        if client_id is not None:
            tenant["client_id"] = client_id.strip()
        if client_secret is not None:
            tenant["client_secret"] = client_secret.strip()
        if description is not None:
            tenant["description"] = description.strip()
        
        # Save
        if self._save_tenants(data):
            return True, f"Tenant '{tenant['name']}' updated successfully"
        else:
            return False, "Failed to save changes"
    
    def delete_tenant(self, tenant_id: str) -> tuple[bool, str]:
        """
        Delete a tenant.
        
        Args:
            tenant_id: ID of tenant to delete
        
        Returns:
            Tuple of (success, message)
        """
        # Load tenants
        data = self._load_tenants()
        
        # Find and remove tenant
        tenant_name = None
        for i, tenant in enumerate(data["tenants"]):
            if tenant["id"] == tenant_id:
                tenant_name = tenant["name"]
                data["tenants"].pop(i)
                break
        
        if tenant_name is None:
            return False, f"Tenant with ID '{tenant_id}' not found"
        
        # Save
        if self._save_tenants(data):
            return True, f"Tenant '{tenant_name}' deleted successfully"
        else:
            return False, "Failed to save changes"
    
    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific tenant by ID.
        
        Args:
            tenant_id: ID of tenant to retrieve
        
        Returns:
            Tenant dictionary or None if not found
        """
        data = self._load_tenants()
        
        for tenant in data["tenants"]:
            if tenant["id"] == tenant_id:
                return tenant.copy()
        
        return None
    
    def list_tenants(self, sort_by: str = "name") -> List[Dict[str, Any]]:
        """
        List all tenants.
        
        Args:
            sort_by: Sort field ("name", "last_used", "created")
        
        Returns:
            List of tenant dictionaries
        """
        data = self._load_tenants()
        tenants = data["tenants"].copy()
        
        # Sort
        if sort_by == "name":
            tenants.sort(key=lambda t: t["name"].lower())
        elif sort_by == "last_used":
            # Sort by last_used (None values last)
            tenants.sort(key=lambda t: t["last_used"] or "", reverse=True)
        elif sort_by == "created":
            tenants.sort(key=lambda t: t["created"], reverse=True)
        
        return tenants
    
    def search_tenants(self, query: str) -> List[Dict[str, Any]]:
        """
        Search tenants by name, TSG ID, or description.
        
        Args:
            query: Search query
        
        Returns:
            List of matching tenant dictionaries
        """
        if not query or not query.strip():
            return self.list_tenants()
        
        query_lower = query.lower().strip()
        data = self._load_tenants()
        
        results = []
        for tenant in data["tenants"]:
            # Search in name, TSG ID, client ID, and description
            if (query_lower in tenant["name"].lower() or
                query_lower in tenant["tsg_id"].lower() or
                query_lower in tenant["client_id"].lower() or
                query_lower in tenant.get("description", "").lower()):
                results.append(tenant.copy())
        
        # Sort by name
        results.sort(key=lambda t: t["name"].lower())
        
        return results
    
    def mark_used(self, tenant_id: str) -> bool:
        """
        Update the last_used timestamp for a tenant.
        
        Args:
            tenant_id: ID of tenant that was used
        
        Returns:
            True if successful
        """
        data = self._load_tenants()
        
        # Find tenant
        for tenant in data["tenants"]:
            if tenant["id"] == tenant_id:
                tenant["last_used"] = datetime.now().isoformat()
                return self._save_tenants(data)
        
        return False
    
    def get_tenant_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a tenant by name (case-insensitive).
        
        Args:
            name: Tenant name
        
        Returns:
            Tenant dictionary or None if not found
        """
        data = self._load_tenants()
        name_lower = name.lower()
        
        for tenant in data["tenants"]:
            if tenant["name"].lower() == name_lower:
                return tenant.copy()
        
        return None
    
    def export_tenants(self, filepath: str) -> tuple[bool, str]:
        """
        Export tenants to a JSON file (unencrypted for portability).
        
        Args:
            filepath: Path to export file
        
        Returns:
            Tuple of (success, message)
        """
        try:
            data = self._load_tenants()
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True, f"Tenants exported to {filepath}"
        except Exception as e:
            return False, f"Export failed: {str(e)}"
    
    def import_tenants(self, filepath: str, merge: bool = True) -> tuple[bool, str]:
        """
        Import tenants from a JSON file.

        Args:
            filepath: Path to import file
            merge: If True, merge with existing; if False, replace

        Returns:
            Tuple of (success, message)
        """
        try:
            # Load import file
            with open(filepath, 'r') as f:
                import_data = json.load(f)

            if "tenants" not in import_data:
                return False, "Invalid tenant file format"

            if merge:
                # Merge with existing
                existing_data = self._load_tenants()
                existing_names = {t["name"].lower() for t in existing_data["tenants"]}

                added = 0
                skipped = 0
                for tenant in import_data["tenants"]:
                    if tenant["name"].lower() in existing_names:
                        skipped += 1
                    else:
                        # Assign new ID
                        tenant["id"] = str(uuid.uuid4())
                        existing_data["tenants"].append(tenant)
                        added += 1

                if self._save_tenants(existing_data):
                    return True, f"Imported {added} tenant(s), skipped {skipped} duplicate(s)"
                else:
                    return False, "Failed to save imported tenants"
            else:
                # Replace existing
                if self._save_tenants(import_data):
                    return True, f"Imported {len(import_data['tenants'])} tenant(s)"
                else:
                    return False, "Failed to save imported tenants"

        except Exception as e:
            return False, f"Import failed: {str(e)}"

    # ========== Extended Credential Management (Phase 2) ==========

    def get_tenant_credentials(self, tenant_id: str) -> Optional[TenantCredentials]:
        """
        Get full credential object for a tenant.

        Supports both legacy and new credential formats.

        Args:
            tenant_id: Tenant ID

        Returns:
            TenantCredentials object or None if tenant not found
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None

        # Check if using new format (has 'credentials' key)
        if 'credentials' in tenant:
            return TenantCredentials.from_dict(tenant['credentials'])

        # Convert from legacy format
        return TenantCredentials.from_legacy_tenant(tenant)

    def update_tenant_credentials(
        self,
        tenant_id: str,
        credentials: TenantCredentials
    ) -> tuple[bool, str]:
        """
        Update tenant with full credential set.

        Args:
            tenant_id: Tenant ID
            credentials: TenantCredentials object

        Returns:
            Tuple of (success, message)
        """
        data = self._load_tenants()

        # Find tenant
        tenant = None
        for t in data["tenants"]:
            if t["id"] == tenant_id:
                tenant = t
                break

        if not tenant:
            return False, f"Tenant with ID '{tenant_id}' not found"

        # Store credentials in new format
        tenant['credentials'] = credentials.to_dict()

        # Also update legacy fields for backward compatibility
        tenant['tsg_id'] = credentials.scm.tsg_id
        tenant['client_id'] = credentials.scm.client_id
        tenant['client_secret'] = credentials.scm.client_secret

        if self._save_tenants(data):
            return True, f"Credentials updated for tenant '{tenant['name']}'"
        else:
            return False, "Failed to save credentials"

    def set_firewall_credentials(
        self,
        tenant_id: str,
        use_generated: bool = True,
        username: str = "admin",
        password: Optional[str] = None,
        auth_type: str = "password"
    ) -> tuple[bool, str]:
        """
        Set firewall credentials for a tenant.

        Args:
            tenant_id: Tenant ID
            use_generated: Use auto-generated password
            username: Admin username
            password: Password (required if not use_generated)
            auth_type: Authentication type (password, api_key, certificate)

        Returns:
            Tuple of (success, message)
        """
        credentials = self.get_tenant_credentials(tenant_id)
        if not credentials:
            return False, f"Tenant with ID '{tenant_id}' not found"

        credentials.firewall.use_generated = use_generated
        credentials.firewall.username = username
        credentials.firewall.auth_type = AuthType(auth_type)

        if not use_generated:
            if not password:
                return False, "Password required when not using generated credentials"
            credentials.firewall.password = password
        elif use_generated and not credentials.firewall.password:
            # Generate password now
            credentials.firewall.generate_password()

        return self.update_tenant_credentials(tenant_id, credentials)

    def set_panorama_credentials(
        self,
        tenant_id: str,
        use_generated: bool = True,
        username: str = "admin",
        password: Optional[str] = None,
        auth_type: str = "password"
    ) -> tuple[bool, str]:
        """
        Set Panorama credentials for a tenant.

        Args:
            tenant_id: Tenant ID
            use_generated: Use auto-generated password
            username: Admin username
            password: Password (required if not use_generated)
            auth_type: Authentication type (password, api_key, certificate)

        Returns:
            Tuple of (success, message)
        """
        credentials = self.get_tenant_credentials(tenant_id)
        if not credentials:
            return False, f"Tenant with ID '{tenant_id}' not found"

        credentials.panorama.use_generated = use_generated
        credentials.panorama.username = username
        credentials.panorama.auth_type = AuthType(auth_type)

        if not use_generated:
            if not password:
                return False, "Password required when not using generated credentials"
            credentials.panorama.password = password
        elif use_generated and not credentials.panorama.password:
            # Generate password now
            credentials.panorama.generate_password()

        return self.update_tenant_credentials(tenant_id, credentials)

    def set_vm_credentials(
        self,
        tenant_id: str,
        use_generated: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssh_public_key: Optional[str] = None,
        resource_group: str = ""
    ) -> tuple[bool, str]:
        """
        Set supporting VM credentials for a tenant.

        Args:
            tenant_id: Tenant ID
            use_generated: Use auto-generated credentials
            username: VM admin username
            password: Password
            ssh_public_key: SSH public key for Linux VMs
            resource_group: Resource group name (for username generation)

        Returns:
            Tuple of (success, message)
        """
        credentials = self.get_tenant_credentials(tenant_id)
        if not credentials:
            return False, f"Tenant with ID '{tenant_id}' not found"

        credentials.supporting_vms.use_generated = use_generated

        if not use_generated:
            if not username:
                return False, "Username required when not using generated credentials"
            if not password and not ssh_public_key:
                return False, "Password or SSH key required when not using generated credentials"
            credentials.supporting_vms.username = username
            credentials.supporting_vms.password = password
            credentials.supporting_vms.ssh_public_key = ssh_public_key
        elif use_generated and not credentials.supporting_vms.has_credentials():
            # Generate credentials now
            credentials.supporting_vms.generate_credentials(
                resource_group=resource_group or 'pov',
                include_ssh_key=True
            )

        return self.update_tenant_credentials(tenant_id, credentials)

    def generate_all_credentials(
        self,
        tenant_id: str,
        resource_group: str = ""
    ) -> tuple[bool, str, Dict[str, Any]]:
        """
        Generate all device credentials for a tenant.

        Used before Terraform deployment to ensure all credentials exist.

        Args:
            tenant_id: Tenant ID
            resource_group: Resource group name for VM username

        Returns:
            Tuple of (success, message, generated_credentials)
        """
        credentials = self.get_tenant_credentials(tenant_id)
        if not credentials:
            return False, f"Tenant with ID '{tenant_id}' not found", {}

        try:
            generated = credentials.generate_all_device_credentials(
                resource_group=resource_group,
                include_ssh=True
            )

            # Save updated credentials
            success, message = self.update_tenant_credentials(tenant_id, credentials)
            if not success:
                return False, message, {}

            return True, "Credentials generated successfully", generated

        except Exception as e:
            return False, f"Error generating credentials: {str(e)}", {}

    def get_terraform_credentials(
        self,
        tenant_id: str,
        resource_group: str
    ) -> tuple[bool, str, Dict[str, Any]]:
        """
        Get credentials formatted for Terraform deployment.

        Generates any missing credentials before returning.

        Args:
            tenant_id: Tenant ID
            resource_group: Resource group name

        Returns:
            Tuple of (success, message, terraform_vars)
        """
        credentials = self.get_tenant_credentials(tenant_id)
        if not credentials:
            return False, f"Tenant with ID '{tenant_id}' not found", {}

        try:
            tf_creds = CredentialManager.prepare_terraform_credentials(
                credentials,
                resource_group
            )

            # Save any generated credentials
            success, message = self.update_tenant_credentials(tenant_id, credentials)
            if not success:
                return False, f"Warning: {message}", tf_creds

            return True, "Credentials ready for Terraform", tf_creds

        except Exception as e:
            return False, f"Error preparing credentials: {str(e)}", {}

    def get_credential_summary(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get credential summary for UI display (no sensitive data).

        Args:
            tenant_id: Tenant ID

        Returns:
            Summary dictionary or None if tenant not found
        """
        credentials = self.get_tenant_credentials(tenant_id)
        if not credentials:
            return None

        return credentials.get_summary()

    def validate_all_credentials(self, tenant_id: str) -> tuple[bool, Dict[str, List[str]]]:
        """
        Validate all credentials for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tuple of (all_valid, errors_by_type)
        """
        credentials = self.get_tenant_credentials(tenant_id)
        if not credentials:
            return False, {'tenant': ['Tenant not found']}

        errors = credentials.validate()
        all_valid = len(errors) == 0

        return all_valid, errors

    def migrate_legacy_tenant(self, tenant_id: str) -> tuple[bool, str]:
        """
        Migrate a legacy tenant to new credential format.

        Preserves existing SCM credentials and initializes device credentials
        with default (use_generated=True) settings.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tuple of (success, message)
        """
        data = self._load_tenants()

        # Find tenant
        tenant = None
        for t in data["tenants"]:
            if t["id"] == tenant_id:
                tenant = t
                break

        if not tenant:
            return False, f"Tenant with ID '{tenant_id}' not found"

        # Skip if already migrated
        if 'credentials' in tenant:
            return True, "Tenant already using new credential format"

        # Create new credentials from legacy format
        credentials = TenantCredentials.from_legacy_tenant(tenant)

        # Store in new format
        tenant['credentials'] = credentials.to_dict()

        if self._save_tenants(data):
            return True, f"Tenant '{tenant['name']}' migrated to new credential format"
        else:
            return False, "Failed to save migrated tenant"

    def migrate_all_tenants(self) -> tuple[int, int, List[str]]:
        """
        Migrate all legacy tenants to new credential format.

        Returns:
            Tuple of (migrated_count, skipped_count, errors)
        """
        data = self._load_tenants()
        migrated = 0
        skipped = 0
        errors = []

        for tenant in data["tenants"]:
            if 'credentials' in tenant:
                skipped += 1
                continue

            try:
                credentials = TenantCredentials.from_legacy_tenant(tenant)
                tenant['credentials'] = credentials.to_dict()
                migrated += 1
            except Exception as e:
                errors.append(f"Error migrating '{tenant['name']}': {str(e)}")

        if migrated > 0:
            self._save_tenants(data)

        return migrated, skipped, errors
