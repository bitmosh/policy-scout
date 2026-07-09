# SPDX-License-Identifier: Apache-2.0
"""Workflow checks for sweep."""

import os
from typing import List
from .models import Finding


# Workflow paths to check
WORKFLOW_PATHS = [
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
]

# Suspicious workflow indicators
SUSPICIOUS_WORKFLOW_INDICATORS = [
    "secrets:",
    "printenv",
    "curl | sh",
    "curl | bash",
    "wget | sh",
    "wget | bash",
    "npm publish",
    "npm token",
    "GITHUB_TOKEN",
    "chmod",
    "chown",
    "base64",
    "eval",
]


def check_workflows(
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check CI workflow files for suspicious patterns.

    Args:
        project_root: Path to project root
        sweep_id: Sweep ID for findings

    Returns:
        List of findings
    """
    findings = []

    # Check GitHub Actions workflows
    github_workflows = os.path.join(project_root, ".github", "workflows")
    if os.path.exists(github_workflows) and os.path.isdir(github_workflows):
        for filename in os.listdir(github_workflows):
            if filename.endswith((".yml", ".yaml")):
                workflow_path = os.path.join(github_workflows, filename)
                findings.extend(
                    _check_workflow_file(workflow_path, project_root, sweep_id)
                )

    # Check GitLab CI
    gitlab_ci = os.path.join(project_root, ".gitlab-ci.yml")
    if os.path.exists(gitlab_ci):
        findings.extend(_check_workflow_file(gitlab_ci, project_root, sweep_id))

    return findings


def _check_workflow_file(
    workflow_path: str,
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check a single workflow file for suspicious patterns."""
    findings = []

    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        # Unreadable file - skip
        return findings

    # Check for suspicious indicators
    suspicious_found = []
    for indicator in SUSPICIOUS_WORKFLOW_INDICATORS:
        if indicator.lower() in content.lower():
            suspicious_found.append(indicator)

    if suspicious_found:
        severity = _determine_workflow_severity(suspicious_found, content)
        findings.append(
            Finding(
                sweep_id=sweep_id,
                severity=severity,
                confidence="moderate",
                category="workflow_injection",
                title="Suspicious workflow pattern detected",
                location=_get_relative_path(workflow_path, project_root),
                evidence_ref="workflow_content",
                why_it_matters=f"Workflow contains suspicious indicators: {', '.join(suspicious_found)}.",
                recommended_action="Review workflow steps and secret handling.",
            )
        )

    return findings


def _determine_workflow_severity(
    suspicious_indicators: List[str],
    content: str,
) -> str:
    """Determine severity based on suspicious indicators."""
    # High severity indicators
    high_severity = [
        "secrets:",
        "curl | sh",
        "curl | bash",
        "wget | sh",
        "wget | bash",
        "eval",
    ]

    # Medium severity indicators
    medium_severity = ["npm publish", "GITHUB_TOKEN", "base64"]

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
