"""
Version management for Prisma Access Configuration Lab.

Version format: <major>.<merge_count>.<commit_count>
- Major: Manually set (currently 3 for architecture rewrite)
- Merge count: Number of merges to main branch
- Commit count: Total number of commits
"""

import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Major version - manually set for significant architecture changes
MAJOR_VERSION = 3


def get_version() -> str:
    """
    Get version string in format: <major>.<merge_count>.<commit_count>
    
    Retrieves version from git history. Falls back to stored version if
    git is not available or if there's an error.
    
    Returns:
        Version string (e.g., "3.5.127")
    """
    try:
        repo_path = Path(__file__).parent.parent
        
        # Get total commit count
        commit_count = subprocess.check_output(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=repo_path,
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        
        # Get merge count (commits with 2+ parents to main branch)
        # This counts merges that reached main
        try:
            merge_count = subprocess.check_output(
                ['git', 'rev-list', '--count', '--merges', 'main'],
                cwd=repo_path,
                stderr=subprocess.DEVNULL
            ).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            # If 'main' doesn't exist, try 'master'
            try:
                merge_count = subprocess.check_output(
                    ['git', 'rev-list', '--count', '--merges', 'master'],
                    cwd=repo_path,
                    stderr=subprocess.DEVNULL
                ).decode('utf-8').strip()
            except subprocess.CalledProcessError:
                # If neither exists, use current branch
                merge_count = subprocess.check_output(
                    ['git', 'rev-list', '--count', '--merges', 'HEAD'],
                    cwd=repo_path,
                    stderr=subprocess.DEVNULL
                ).decode('utf-8').strip()
        
        version = f"{MAJOR_VERSION}.{merge_count}.{commit_count}"
        return version
        
    except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
        # Fallback if git is not available or command fails
        logger.debug(f"Could not get version from git: {e}")
        return f"{MAJOR_VERSION}.0.0"


# Module-level version string
__version__ = get_version()


if __name__ == '__main__':
    # For testing
    print(f"Prisma Access Configuration Lab v{__version__}")
    print(f"Major version: {MAJOR_VERSION}")
    
    try:
        # Show git info
        repo_path = Path(__file__).parent.parent
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=repo_path
        ).decode('utf-8').strip()
        
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=repo_path
        ).decode('utf-8').strip()
        
        print(f"Current branch: {branch}")
        print(f"Current commit: {commit_hash}")
    except Exception as e:
        print(f"Could not get git info: {e}")
