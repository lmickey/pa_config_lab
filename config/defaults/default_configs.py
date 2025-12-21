"""
Default Configuration Database for Prisma Access.

This module contains a comprehensive database of default configurations
that are commonly found in Prisma Access deployments. These defaults
are used to identify and filter default configurations during capture.
"""

from typing import Dict, Any, List, Set, Optional
import re


class DefaultConfigs:
    """Database of default Prisma Access configurations."""

    # Default folder names (case-insensitive patterns)
    DEFAULT_FOLDER_PATTERNS: List[str] = [
        r"^shared$",
        r"^default$",
        r".*default.*",
        r"^all$",
        r"^service connections$",
        r"^remote networks$",
        r"^mobile user container$",
        r"^mobile users container$",
        r"^mobile users$",  # Mobile Users folder (without Container)
        r"^prisma access$",
        r"^ngfw-shared$",
    ]

    # Folders that are parents of default folders (all children are defaults)
    DEFAULT_PARENT_FOLDERS: List[str] = [
        "prisma access"  # Everything under Prisma Access is default
    ]

    # Default snippet names (case-insensitive patterns)
    DEFAULT_SNIPPET_PATTERNS: List[str] = [
        r"^default$",
        r"^predefined-snippet$",
        r".*default.*",
        r".*predefined.*",
        r"^optional-default$",
        r".*best-practice.*",
        r".*best practice.*",
        r"^hip-default$",
        r"^web-security-default$",
        r"^dlp-predefined-snippet$",
    ]

    # Default profile name patterns
    DEFAULT_PROFILE_NAME_PATTERNS: List[str] = [
        r"^default$",
        r".*default.*",
        r".*best-practice.*",
        r".*best practice.*",
        r".*predefined.*",
        r"^best.*practice.*",
        r"^standard.*",
        r"^recommended.*",
    ]

    # Default authentication profile patterns
    DEFAULT_AUTH_PROFILE_PATTERNS: List[str] = [
        r"^default$",
        r".*default.*",
        r".*ldap.*default.*",
        r".*saml.*default.*",
        r".*okta.*default.*",
    ]

    # Default security profile types and their known default names
    DEFAULT_SECURITY_PROFILE_NAMES: Dict[str, List[str]] = {
        "anti_spyware": [
            "default",
            "default-protection",
            "best-practice",
            "strict",
            "moderate",
        ],
        "antivirus": [
            "default",
            "default-protection",
            "best-practice",
            "strict",
            "moderate",
        ],
        "vulnerability_protection": [
            "default",
            "default-protection",
            "best-practice",
            "strict",
            "moderate",
        ],
        "url_access": [
            "default",
            "default-policy",
            "best-practice",
            "strict",
            "moderate",
        ],
        "file_blocking": ["default", "default-policy", "best-practice"],
        "wildfire_anti_virus": ["default", "default-protection", "best-practice"],
        "dns_security": ["default", "default-policy", "best-practice"],
        "http_header": ["default", "default-policy"],
    }

    # Default decryption profile patterns
    DEFAULT_DECRYPTION_PROFILE_PATTERNS: List[str] = [
        r"^default$",
        r".*default.*",
        r".*forward.*proxy.*default.*",
        r".*inbound.*inspection.*default.*",
        r".*ssl.*default.*",
    ]

    # Default object name patterns
    DEFAULT_OBJECT_NAME_PATTERNS: List[str] = [
        r"^any$",
        r"^any-ipv4$",
        r"^any-ipv6$",
        r"^any-ipv4-ipv6$",
        r"^any-tcp$",
        r"^any-udp$",
        r"^any-tcp-udp$",
        r".*palo alto.*sinkhole.*",
        r".*sinkhole.*",
        r"^default.*",
        r".*predefined.*",
    ]

    # Default address object names
    DEFAULT_ADDRESS_OBJECTS: Set[str] = {
        "any",
        "any-ipv4",
        "any-ipv6",
        "any-ipv4-ipv6",
        "Palo Alto Networks Sinkhole",
    }

    # Default service object names
    DEFAULT_SERVICE_OBJECTS: Set[str] = {
        "any-tcp",
        "any-udp",
        "any-tcp-udp",
        "service-http",
        "service-https",
        "service-dns",
        "service-ntp",
    }

    # Default application names (common Palo Alto predefined apps)
    DEFAULT_APPLICATION_PATTERNS: List[str] = [
        r"^.*palo alto.*",
        r"^.*pan-.*",
        r"^.*predefined.*",
        r"^.*default.*",
    ]

    # Default rule patterns
    DEFAULT_RULE_PATTERNS: Dict[str, Any] = {
        "name_patterns": [
            r"^default.*",
            r".*default.*rule.*",
            r".*best.*practice.*",
            r"^.*deny.*all.*",
            r"^.*allow.*all.*",
            r"^.*block.*all.*",
        ],
        "common_default_rules": [
            {
                "name": "default-deny",
                "action": "deny",
                "source": ["any"],
                "destination": ["any"],
                "application": ["any"],
                "service": ["any"],
            },
            {
                "name": "default-allow",
                "action": "allow",
                "source": ["any"],
                "destination": ["any"],
                "application": ["any"],
                "service": ["any"],
            },
        ],
    }

    @staticmethod
    def is_default_folder(
        folder_name: str, parent_folder: Optional[str] = None
    ) -> bool:
        """
        Check if folder name matches default patterns.

        Args:
            folder_name: Folder name to check
            parent_folder: Optional parent folder name (if folder is a child)

        Returns:
            True if folder matches default patterns
        """
        if not folder_name:
            return False

        # Check if parent is a default parent folder (all children are defaults)
        if parent_folder:
            parent_lower = parent_folder.lower()
            for default_parent in DefaultConfigs.DEFAULT_PARENT_FOLDERS:
                if parent_lower == default_parent.lower():
                    return True

        # Check folder name patterns
        folder_lower = folder_name.lower()
        for pattern in DefaultConfigs.DEFAULT_FOLDER_PATTERNS:
            if re.match(pattern, folder_lower, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def is_default_snippet(snippet_name: str) -> bool:
        """
        Check if snippet name matches default patterns.

        Args:
            snippet_name: Snippet name to check

        Returns:
            True if snippet matches default patterns
        """
        if not snippet_name:
            return False

        snippet_lower = snippet_name.lower()
        for pattern in DefaultConfigs.DEFAULT_SNIPPET_PATTERNS:
            if re.match(pattern, snippet_lower, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def is_default_profile_name(
        profile_name: str, profile_type: Optional[str] = None
    ) -> bool:
        """
        Check if profile name matches default patterns.

        Args:
            profile_name: Profile name to check
            profile_type: Optional profile type (e.g., 'anti_spyware', 'antivirus')

        Returns:
            True if profile matches default patterns
        """
        if not profile_name:
            return False

        profile_lower = profile_name.lower()

        # Check type-specific defaults
        if (
            profile_type
            and profile_type in DefaultConfigs.DEFAULT_SECURITY_PROFILE_NAMES
        ):
            for default_name in DefaultConfigs.DEFAULT_SECURITY_PROFILE_NAMES[
                profile_type
            ]:
                if profile_lower == default_name.lower():
                    return True

        # Check general patterns
        for pattern in DefaultConfigs.DEFAULT_PROFILE_NAME_PATTERNS:
            if re.match(pattern, profile_lower, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def is_default_auth_profile(auth_profile_name: str) -> bool:
        """
        Check if authentication profile name matches default patterns.

        Args:
            auth_profile_name: Authentication profile name to check

        Returns:
            True if profile matches default patterns
        """
        if not auth_profile_name:
            return False

        profile_lower = auth_profile_name.lower()
        for pattern in DefaultConfigs.DEFAULT_AUTH_PROFILE_PATTERNS:
            if re.match(pattern, profile_lower, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def is_default_decryption_profile(decryption_profile_name: str) -> bool:
        """
        Check if decryption profile name matches default patterns.

        Args:
            decryption_profile_name: Decryption profile name to check

        Returns:
            True if profile matches default patterns
        """
        if not decryption_profile_name:
            return False

        profile_lower = decryption_profile_name.lower()
        for pattern in DefaultConfigs.DEFAULT_DECRYPTION_PROFILE_PATTERNS:
            if re.match(pattern, profile_lower, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def is_default_object(
        object_name: str,
        object_type: Optional[str] = None,
        object_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if object name matches default patterns.

        Args:
            object_name: Object name to check
            object_type: Optional object type ('address', 'service', 'application')
            object_data: Optional full object dictionary (for checking snippet associations)

        Returns:
            True if object matches default patterns
        """
        if not object_name:
            return False

        # Check if object is associated with a predefined snippet
        # Applications (and potentially other objects) can be part of predefined snippets
        if object_data:
            snippet = object_data.get("snippet", "")
            if snippet:
                snippet_lower = snippet.lower()
                # Check if snippet matches predefined snippet patterns
                for pattern in DefaultConfigs.DEFAULT_SNIPPET_PATTERNS:
                    if re.match(pattern, snippet_lower, re.IGNORECASE):
                        return True

        object_lower = object_name.lower()

        # Check type-specific defaults
        if (
            object_type == "address"
            and object_name in DefaultConfigs.DEFAULT_ADDRESS_OBJECTS
        ):
            return True

        if (
            object_type == "service"
            and object_name in DefaultConfigs.DEFAULT_SERVICE_OBJECTS
        ):
            return True

        if object_type == "application":
            for pattern in DefaultConfigs.DEFAULT_APPLICATION_PATTERNS:
                if re.match(pattern, object_lower, re.IGNORECASE):
                    return True

        # Check general patterns
        for pattern in DefaultConfigs.DEFAULT_OBJECT_NAME_PATTERNS:
            if re.match(pattern, object_lower, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def is_default_rule(rule: Dict[str, Any]) -> bool:
        """
        Check if rule matches default patterns.

        Args:
            rule: Rule dictionary with name, action, source, destination, etc.

        Returns:
            True if rule matches default patterns
        """
        if not rule:
            return False

        rule_name = rule.get("name", "")
        if rule_name:
            rule_name_lower = rule_name.lower()
            for pattern in DefaultConfigs.DEFAULT_RULE_PATTERNS["name_patterns"]:
                if re.match(pattern, rule_name_lower, re.IGNORECASE):
                    return True

        # Check if rule matches common default rule patterns
        action = rule.get("action", "").lower()
        source = rule.get("source", [])
        destination = rule.get("destination", [])
        application = rule.get("application", [])
        service = rule.get("service", [])

        # Check for "any" patterns (common in default rules)
        has_any_source = not source or "any" in [s.lower() for s in source]
        has_any_dest = not destination or "any" in [d.lower() for d in destination]
        has_any_app = not application or "any" in [a.lower() for a in application]
        has_any_service = not service or "any" in [s.lower() for s in service]

        # Very permissive rules with "any" everywhere are often defaults
        if has_any_source and has_any_dest and has_any_app and has_any_service:
            # But only if action is deny or allow (not custom)
            if action in ["deny", "allow"]:
                return True

        return False

    @staticmethod
    def get_default_patterns_summary() -> Dict[str, List[str]]:
        """
        Get summary of all default patterns for documentation.

        Returns:
            Dictionary mapping category to list of patterns
        """
        return {
            "folders": DefaultConfigs.DEFAULT_FOLDER_PATTERNS,
            "snippets": DefaultConfigs.DEFAULT_SNIPPET_PATTERNS,
            "profiles": DefaultConfigs.DEFAULT_PROFILE_NAME_PATTERNS,
            "auth_profiles": DefaultConfigs.DEFAULT_AUTH_PROFILE_PATTERNS,
            "decryption_profiles": DefaultConfigs.DEFAULT_DECRYPTION_PROFILE_PATTERNS,
            "objects": DefaultConfigs.DEFAULT_OBJECT_NAME_PATTERNS,
            "rules": DefaultConfigs.DEFAULT_RULE_PATTERNS["name_patterns"],
        }
