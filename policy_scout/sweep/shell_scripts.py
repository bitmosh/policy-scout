# SPDX-License-Identifier: Apache-2.0
"""Shell script pattern checks for sweep."""

import os
from typing import List
from .models import Finding


# Suspicious shell script patterns
SUSPICIOUS_SHELL_PATTERNS = [
    "curl | sh",
    "curl | bash",
    "wget | sh",
    "wget | bash",
    "chmod +x",
    "crontab",
    "chown",
    "systemctl",
    ".env",
    ".npmrc",
    ".ssh",
    "printenv",
    "env |",
    "base64 -d",
    "eval",
    "source .env",
]

# Shell script extensions
SHELL_EXTENSIONS = [".sh", ".bash", ".zsh"]


def check_shell_scripts(
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check shell scripts for suspicious patterns.

    Args:
        project_root: Path to project root
        sweep_id: Sweep ID for findings

    Returns:
        List of findings
    """
    findings = []

    for root, dirs, files in os.walk(project_root):
        # Skip node_modules
        if "node_modules" in dirs:
            dirs.remove("node_modules")

        for filename in files:
            if any(filename.endswith(ext) for ext in SHELL_EXTENSIONS):
                filepath = os.path.join(root, filename)
                findings.extend(_check_shell_file(filepath, project_root, sweep_id))

    return findings


def _check_shell_file(
    filepath: str,
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check a single shell script for suspicious patterns."""
    findings = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        # Unreadable file - skip
        return findings

    # Check for suspicious patterns
    suspicious_found = []
    for pattern in SUSPICIOUS_SHELL_PATTERNS:
        if pattern.lower() in content.lower():
            suspicious_found.append(pattern)

    if suspicious_found:
        severity = _determine_shell_severity(suspicious_found, content)
        findings.append(
            Finding(
                sweep_id=sweep_id,
                severity=severity,
                confidence="moderate",
                category="destructive_payload",
                title="Suspicious shell script pattern detected",
                location=_get_relative_path(filepath, project_root),
                evidence_ref="shell_pattern",
                why_it_matters=f"Script contains suspicious patterns: {', '.join(suspicious_found)}.",
                recommended_action="Review script for potentially dangerous operations.",
            )
        )

    return findings


def _determine_shell_severity(
    suspicious_patterns: List[str],
    content: str,
) -> str:
    """Determine severity based on suspicious patterns."""
    # High severity patterns
    high_severity = ["curl | sh", "curl | bash", "wget | sh", "wget | bash", "eval"]

    # Medium severity patterns
    medium_severity = ["chmod +x", "crontab", "systemctl", "base64 -d"]

    for pattern in suspicious_patterns:
        if pattern in high_severity:
            return "high"
        if pattern in medium_severity:
            return "medium"

    return "low"


def _get_relative_path(file_path: str, project_root: str) -> str:
    """Get relative path from project root."""
    try:
        return os.path.relpath(file_path, project_root)
    except ValueError:
        return file_path
