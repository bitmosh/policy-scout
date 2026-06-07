"""Credential-adjacent reference checks for sweep."""

import os
from typing import List
from .models import Finding


# Credential-related patterns to detect
CREDENTIAL_PATTERNS = [
    ".env",
    ".npmrc",
    ".ssh",
    "id_rsa",
    "id_ed25519",
    "AWS_ACCESS_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "GITHUB_TOKEN",
    "NPM_TOKEN",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "API_KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "dotenv",
    "require('dotenv')",
    "process.env",
]


def check_credential_references(
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check files for credential-adjacent references.

    Args:
        project_root: Path to project root
        sweep_id: Sweep ID for findings

    Returns:
        List of findings
    """
    findings = []

    # File extensions to check
    CHECK_EXTENSIONS = [
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".py",
        ".sh",
        ".bash",
        ".zsh",
        ".yml",
        ".yaml",
        ".json",
        ".md",
    ]

    for root, dirs, files in os.walk(project_root):
        # Skip node_modules and .git
        if "node_modules" in dirs:
            dirs.remove("node_modules")
        if ".git" in dirs:
            dirs.remove(".git")

        for filename in files:
            if any(filename.endswith(ext) for ext in CHECK_EXTENSIONS):
                filepath = os.path.join(root, filename)
                findings.extend(
                    _check_file_for_credentials(filepath, project_root, sweep_id)
                )

    return findings


def _check_file_for_credentials(
    filepath: str,
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check a single file for credential references."""
    findings = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        # Unreadable file - skip
        return findings

    # Check for credential patterns
    credential_found = []
    for pattern in CREDENTIAL_PATTERNS:
        if pattern.lower() in content.lower():
            credential_found.append(pattern)

    if credential_found:
        findings.append(
            Finding(
                sweep_id=sweep_id,
                severity="medium",
                confidence="low",
                category="credential_file_access",
                title="Credential-adjacent reference detected",
                location=_get_relative_path(filepath, project_root),
                evidence_ref="credential_reference",
                why_it_matters=f"File references credential-related terms: {', '.join(credential_found)}.",
                recommended_action="Review file to ensure credentials are not exposed.",
            )
        )

    return findings


def _get_relative_path(file_path: str, project_root: str) -> str:
    """Get relative path from project root."""
    try:
        return os.path.relpath(file_path, project_root)
    except ValueError:
        return file_path
