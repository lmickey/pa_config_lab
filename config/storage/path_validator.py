"""
File path validation to prevent path traversal attacks.

This module provides secure file path validation with configurable
base directory restrictions to prevent path traversal vulnerabilities.
"""

import pathlib
import os
from typing import Union


class PathValidator:
    """Validate file paths to prevent path traversal attacks."""

    DEFAULT_BASE_DIR = os.path.expanduser("~/.pa_config_lab")

    @staticmethod
    def validate_config_path(
        file_path: Union[str, pathlib.Path],
        base_dir: Union[str, pathlib.Path] = None,
        must_exist: bool = False,
        must_be_file: bool = True,
        create_parents: bool = False,
    ) -> pathlib.Path:
        """
        Validate and normalize a configuration file path.

        Args:
            file_path: Path to validate
            base_dir: Base directory to restrict to (default: ~/.pa_config_lab)
            must_exist: If True, path must exist
            must_be_file: If True, path must be a file (not directory)
            create_parents: If True, create parent directories if they don't exist

        Returns:
            Validated and resolved pathlib.Path

        Raises:
            ValueError: If path is invalid or unsafe

        Example:
            >>> path = PathValidator.validate_config_path("configs/backup.json")
            >>> # Returns: ~/.pa_config_lab/configs/backup.json

            >>> PathValidator.validate_config_path("../../etc/passwd")
            ValueError: Path traversal detected
        """
        if base_dir is None:
            base_dir = PathValidator.DEFAULT_BASE_DIR

        # Ensure base directory exists
        base = pathlib.Path(base_dir).resolve()
        if not base.exists():
            base.mkdir(parents=True, exist_ok=True)

        # Convert to Path object
        if isinstance(file_path, str):
            file_path = pathlib.Path(file_path)

        # Handle relative vs absolute paths
        if file_path.is_absolute():
            target = file_path.resolve()
        else:
            target = (base / file_path).resolve()

        # Check for path traversal
        try:
            target.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Invalid file path: '{file_path}' resolves outside base directory '{base}'. "
                "Path traversal detected."
            )

        # Create parent directories if requested
        if create_parents and not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)

        # Check existence
        if must_exist and not target.exists():
            raise ValueError(f"Path does not exist: {target}")

        # Check if file
        if must_be_file and target.exists() and not target.is_file():
            raise ValueError(f"Path is not a file: {target}")

        return target

    @staticmethod
    def validate_directory_path(
        dir_path: Union[str, pathlib.Path],
        base_dir: Union[str, pathlib.Path] = None,
        create: bool = False,
        must_exist: bool = False,
    ) -> pathlib.Path:
        """
        Validate a directory path.

        Args:
            dir_path: Directory path to validate
            base_dir: Base directory to restrict to
            create: If True, create directory if it doesn't exist
            must_exist: If True, directory must exist

        Returns:
            Validated pathlib.Path

        Raises:
            ValueError: If path is invalid or unsafe
        """
        target = PathValidator.validate_config_path(
            dir_path,
            base_dir,
            must_exist=False,
            must_be_file=False,
            create_parents=False,
        )

        if create and not target.exists():
            target.mkdir(parents=True, exist_ok=True)

        if must_exist and not target.exists():
            raise ValueError(f"Directory does not exist: {target}")

        if target.exists() and not target.is_dir():
            raise ValueError(f"Path is not a directory: {target}")

        return target

    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """
        Check if filename is safe (no path separators or dangerous characters).

        Args:
            filename: Filename to check

        Returns:
            True if filename is safe
        """
        if not filename:
            return False

        # Check for path separators
        if "/" in filename or "\\" in filename:
            return False

        # Check for dangerous patterns
        dangerous_patterns = ["..", "~", "$", "`", "|", "&", ";", "<", ">"]
        for pattern in dangerous_patterns:
            if pattern in filename:
                return False

        return True

    @staticmethod
    def sanitize_filename(filename: str, replacement: str = "_") -> str:
        """
        Sanitize filename by removing/replacing unsafe characters.

        Args:
            filename: Filename to sanitize
            replacement: Character to replace unsafe characters with

        Returns:
            Sanitized filename
        """
        # Replace path separators
        safe_name = filename.replace("/", replacement).replace("\\", replacement)

        # Replace dangerous characters
        dangerous_chars = [
            "..",
            "~",
            "$",
            "`",
            "|",
            "&",
            ";",
            "<",
            ">",
            "*",
            "?",
            '"',
            "'",
        ]
        for char in dangerous_chars:
            safe_name = safe_name.replace(char, replacement)

        # Remove leading/trailing dots and spaces
        safe_name = safe_name.strip(". ")

        # Ensure not empty
        if not safe_name:
            safe_name = "unnamed"

        return safe_name
