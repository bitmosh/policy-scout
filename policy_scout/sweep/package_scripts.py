# SPDX-License-Identifier: Apache-2.0
"""Package script checks for sweep."""

import json
import os
from typing import List
from .models import Finding


# Lifecycle script names to inspect
LIFECYCLE_SCRIPTS = [
    "preinstall",
    "install",
    "postinstall",
    "prepack",
    "prepare",
    "prepublish",
    "prepublishOnly",
]

# Suspicious indicators in scripts
SUSPICIOUS_INDICATORS = [
    "child_process",
    "curl",
    "wget",
    "bash",
    "sh",
    "powershell",
    "env",
    "printenv",
    "process.env",
    ".env",
    ".npmrc",
    "~/.ssh",
    "chmod",
    "chown",
    "crontab",
    "systemctl",
    "base64",
    "eval",
]


def check_package_scripts(
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check package.json and node_modules for suspicious lifecycle scripts.

    Args:
        project_root: Path to project root
        sweep_id: Sweep ID for findings

    Returns:
        List of findings
    """
    findings = []

    # Check root package.json
    root_package_json = os.path.join(project_root, "package.json")
    if os.path.exists(root_package_json):
        findings.extend(_check_package_file(root_package_json, project_root, sweep_id))

    # Check node_modules package.json files if present
    node_modules = os.path.join(project_root, "node_modules")
    if os.path.exists(node_modules) and os.path.isdir(node_modules):
        findings.extend(_scan_node_modules(node_modules, sweep_id))

    return findings


def _check_package_file(
    package_path: str,
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check a single package.json file for suspicious scripts."""
    findings = []

    try:
        with open(package_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError, UnicodeDecodeError):
        # Malformed or unreadable JSON - report as low-severity finding
        findings.append(
            Finding(
                sweep_id=sweep_id,
                severity="low",
                confidence="moderate",
                category="suspicious_package_manifest",
                title="Unreadable or malformed package.json",
                location=_get_relative_path(package_path, project_root),
                evidence_ref="file_read_error",
                why_it_matters="Malformed package.json may indicate corruption or tampering.",
                recommended_action="Review the file manually.",
            )
        )
        return findings

    scripts = data.get("scripts", {})

    for script_name, script_content in scripts.items():
        # Only check lifecycle scripts
        if script_name not in LIFECYCLE_SCRIPTS:
            continue

        # Check for suspicious indicators
        suspicious_found = []
        for indicator in SUSPICIOUS_INDICATORS:
            if indicator.lower() in script_content.lower():
                suspicious_found.append(indicator)

        if suspicious_found:
            severity = _determine_script_severity(suspicious_found, script_content)
            findings.append(
                Finding(
                    sweep_id=sweep_id,
                    severity=severity,
                    confidence="moderate",
                    category="suspicious_lifecycle_script",
                    title=f"Suspicious lifecycle script: {script_name}",
                    location=_get_relative_path(package_path, project_root),
                    evidence_ref=f"script:{script_name}",
                    why_it_matters=f"Lifecycle script {script_name} contains suspicious indicators: {', '.join(suspicious_found)}.",
                    recommended_action="Review the script content before approving package operations.",
                )
            )

    return findings


def _scan_node_modules(
    node_modules_path: str,
    sweep_id: str,
) -> List[Finding]:
    """Scan node_modules for suspicious package.json files.

    This is a limited scan to avoid performance issues.
    """
    findings = []

    # Limit scan depth to avoid performance issues
    max_depth = 3
    scanned_count = 0
    max_packages = 100  # Limit number of packages to scan

    for root, dirs, files in os.walk(node_modules_path):
        # Check depth
        depth = root[len(node_modules_path) :].count(os.sep)
        if depth > max_depth:
            continue

        # Skip .bin directories
        if ".bin" in dirs:
            dirs.remove(".bin")

        if "package.json" in files:
            scanned_count += 1
            if scanned_count > max_packages:
                findings.append(
                    Finding(
                        sweep_id=sweep_id,
                        severity="info",
                        confidence="high",
                        category="suspicious_package_manifest",
                        title="Node modules scan limit reached",
                        location="node_modules/",
                        evidence_ref="scan_limit",
                        why_it_matters="Scan was limited to avoid performance issues.",
                        recommended_action="Consider deeper manual review if needed.",
                    )
                )
                break

            package_path = os.path.join(root, "package.json")
            findings.extend(
                _check_package_file(package_path, node_modules_path, sweep_id)
            )

    return findings


def _determine_script_severity(
    suspicious_indicators: List[str],
    script_content: str,
) -> str:
    """Determine severity based on suspicious indicators."""
    # High severity indicators
    high_severity = ["child_process", "eval", "base64", "chmod", "chown"]

    # Medium severity indicators
    medium_severity = ["curl", "wget", "bash", "sh", "powershell"]

    for indicator in suspicious_indicators:
        if indicator in high_severity:
            return "high"
        if indicator in medium_severity:
            return "medium"

    return "low"


def _get_relative_path(file_path: str, project_root: str) -> str:
    """Get relative path from project root."""
    try:
        return os.path.relpath(file_path, project_root)
    except ValueError:
        return file_path
