"""
Saved Configurations Manager.

This module manages encrypted configuration files, providing storage, retrieval,
and listing of saved configurations.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from config.storage.json_storage import save_config_json, load_config_json
from config.storage.crypto_utils import derive_key_secure


class SavedConfigsManager:
    """Manager for saved configuration files."""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the saved configs manager.

        Args:
            base_dir: Base directory for saved configs (defaults to ~/.pa_config_lab/saved_configs)
        """
        if base_dir is None:
            base_dir = Path.home() / ".pa_config_lab" / "saved_configs"
        
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def list_configs(self) -> List[Dict[str, Any]]:
        """
        List all saved configurations.

        Returns:
            List of dicts with config metadata (name, path, modified_time, size, encrypted)
        """
        configs = []
        
        for config_file in self.base_dir.glob("*.json"):
            try:
                stat = config_file.stat()
                
                # Try to determine if encrypted by reading first few bytes
                with open(config_file, 'rb') as f:
                    first_bytes = f.read(16)
                    # Check if it looks like encrypted data (not valid JSON start)
                    is_encrypted = not (first_bytes.startswith(b'{') or first_bytes.startswith(b'{\n'))
                
                configs.append({
                    "name": config_file.stem,
                    "path": str(config_file),
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "size": stat.st_size,
                    "encrypted": is_encrypted,
                })
            except Exception as e:
                print(f"Error reading {config_file}: {e}")
                continue
        
        # Sort by modified time (newest first)
        configs.sort(key=lambda x: x["modified"], reverse=True)
        
        return configs

    def save_config(
        self,
        config: Dict[str, Any],
        name: str,
        password: Optional[str] = None,
        overwrite: bool = False
    ) -> tuple[bool, str]:
        """
        Save a configuration to file.

        Args:
            config: Configuration dictionary
            name: Name for the saved config (without extension)
            password: Optional password for encryption
            overwrite: Whether to overwrite existing file

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            return False, "Invalid configuration name"
        
        filepath = self.base_dir / f"{safe_name}.json"
        
        # Check if exists
        if filepath.exists() and not overwrite:
            return False, f"Configuration '{safe_name}' already exists"
        
        try:
            # Add metadata
            if "metadata" not in config:
                config["metadata"] = {}
            
            config["metadata"]["saved_at"] = datetime.now().isoformat()
            config["metadata"]["saved_name"] = safe_name
            
            # Save with encryption if password provided
            if password:
                cipher, salt = derive_key_secure(password)
                success = save_config_json(
                    config,
                    str(filepath),
                    cipher=cipher,
                    encrypt=True,
                    validate=False  # Skip validation for flexibility
                )
            else:
                success = save_config_json(
                    config,
                    str(filepath),
                    encrypt=False,
                    validate=False
                )
            
            if success:
                return True, f"Configuration saved to {safe_name}.json"
            else:
                return False, "Failed to save configuration"
        
        except Exception as e:
            return False, f"Error saving configuration: {str(e)}"

    def load_config(
        self,
        name: str,
        password: Optional[str] = None
    ) -> tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Load a configuration from file.

        Args:
            name: Name of the saved config (without extension)
            password: Optional password for decryption

        Returns:
            Tuple of (success: bool, config: Optional[Dict], message: str)
        """
        filepath = self.base_dir / f"{name}.json"
        
        if not filepath.exists():
            return False, None, f"Configuration '{name}' not found"
        
        try:
            # Determine if encrypted
            with open(filepath, 'rb') as f:
                first_bytes = f.read(16)
                is_encrypted = not (first_bytes.startswith(b'{') or first_bytes.startswith(b'{\n'))
            
            if is_encrypted:
                if not password:
                    return False, None, "Password required for encrypted configuration"
                
                cipher, salt = derive_key_secure(password)
                config = load_config_json(
                    str(filepath),
                    cipher=cipher,
                    encrypted=True,
                    validate=False
                )
            else:
                config = load_config_json(
                    str(filepath),
                    encrypted=False,
                    validate=False
                )
            
            if config:
                return True, config, f"Configuration '{name}' loaded successfully"
            else:
                return False, None, "Failed to load configuration"
        
        except Exception as e:
            return False, None, f"Error loading configuration: {str(e)}"

    def delete_config(self, name: str) -> tuple[bool, str]:
        """
        Delete a saved configuration.

        Args:
            name: Name of the config to delete

        Returns:
            Tuple of (success: bool, message: str)
        """
        filepath = self.base_dir / f"{name}.json"
        
        if not filepath.exists():
            return False, f"Configuration '{name}' not found"
        
        try:
            filepath.unlink()
            return True, f"Configuration '{name}' deleted"
        except Exception as e:
            return False, f"Error deleting configuration: {str(e)}"

    def rename_config(self, old_name: str, new_name: str) -> tuple[bool, str]:
        """
        Rename a saved configuration.

        Args:
            old_name: Current name
            new_name: New name

        Returns:
            Tuple of (success: bool, message: str)
        """
        old_path = self.base_dir / f"{old_name}.json"
        
        # Sanitize new name
        safe_new_name = "".join(c for c in new_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_new_name:
            return False, "Invalid new configuration name"
        
        new_path = self.base_dir / f"{safe_new_name}.json"
        
        if not old_path.exists():
            return False, f"Configuration '{old_name}' not found"
        
        if new_path.exists():
            return False, f"Configuration '{safe_new_name}' already exists"
        
        try:
            old_path.rename(new_path)
            return True, f"Configuration renamed to '{safe_new_name}'"
        except Exception as e:
            return False, f"Error renaming configuration: {str(e)}"

    def export_config(self, name: str, export_path: str) -> tuple[bool, str]:
        """
        Export a configuration to a different location.

        Args:
            name: Name of config to export
            export_path: Destination path

        Returns:
            Tuple of (success: bool, message: str)
        """
        source_path = self.base_dir / f"{name}.json"
        
        if not source_path.exists():
            return False, f"Configuration '{name}' not found"
        
        try:
            import shutil
            shutil.copy2(source_path, export_path)
            return True, f"Configuration exported to {export_path}"
        except Exception as e:
            return False, f"Error exporting configuration: {str(e)}"

    def import_config(
        self,
        import_path: str,
        name: Optional[str] = None,
        password: Optional[str] = None
    ) -> tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Import a configuration from external file.

        Args:
            import_path: Path to config file to import
            name: Optional name to save as (if None, uses original filename)
            password: Optional password if encrypted

        Returns:
            Tuple of (success: bool, config: Optional[Dict], message: str)
        """
        import_file = Path(import_path)
        
        if not import_file.exists():
            return False, None, f"File not found: {import_path}"
        
        # Determine name
        if name is None:
            name = import_file.stem
        
        # Load the config
        try:
            # Check if encrypted
            with open(import_file, 'rb') as f:
                first_bytes = f.read(16)
                is_encrypted = not (first_bytes.startswith(b'{') or first_bytes.startswith(b'{\n'))
            
            if is_encrypted:
                if not password:
                    return False, None, "Password required for encrypted configuration"
                
                cipher, salt = derive_key_secure(password)
                config = load_config_json(
                    str(import_file),
                    cipher=cipher,
                    encrypted=True,
                    validate=False
                )
            else:
                config = load_config_json(
                    str(import_file),
                    encrypted=False,
                    validate=False
                )
            
            if not config:
                return False, None, "Failed to load configuration"
            
            # Save to saved configs
            success, message = self.save_config(config, name, password, overwrite=False)
            
            if success:
                return True, config, f"Configuration imported as '{name}'"
            else:
                return False, config, f"Loaded but not saved: {message}"
        
        except Exception as e:
            return False, None, f"Error importing configuration: {str(e)}"
