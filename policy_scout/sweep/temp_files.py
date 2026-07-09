# SPDX-License-Identifier: Apache-2.0
"""Suspicious temp file checks for quick system sweep."""

import os
import re
from pathlib import Path
from typing import List
from datetime import datetime, timedelta
from .models import Finding


def _redact_sensitive_filename(filename: str) -> str:
    """Redact token-like patterns from filenames for privacy.

    Args:
        filename: Original filename.

    Returns:
        Filename with sensitive patterns redacted.
    """
    # Pattern for long alphanumeric strings (possible tokens/keys)
    # Matches 20+ character alphanumeric strings
    token_pattern = r"[a-zA-Z0-9]{20,}"

    # Pattern for UUID-like strings
    uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"

    # Pattern for base64-like strings (common in JWT tokens)
    base64_pattern = r"[a-zA-Z0-9+/]{32,}={0,2}"

    # Apply redaction
    redacted = filename
    redacted = re.sub(token_pattern, "<redacted:token>", redacted)
    redacted = re.sub(uuid_pattern, "<redacted:uuid>", redacted)
    redacted = re.sub(base64_pattern, "<redacted:base64>", redacted)

    return redacted


def _normalize_temp_path(file_path: Path) -> str:
    """Normalize temp file path for privacy.

    Args:
        file_path: Original file path.

    Returns:
        Normalized path with sensitive filename redacted.
    """
    # Get parent directory
    parent = file_path.parent
    # Redact filename
    redacted_name = _redact_sensitive_filename(file_path.name)
    # Reconstruct path
    return str(parent / redacted_name)


def check_suspicious_temp_files(sweep_id: str) -> List[Finding]:
    """Check for suspicious temp files.

    Args:
        sweep_id: Sweep result ID.

    Returns:
        List of findings.
    """
    findings = []

    # Temp directories to check
    temp_dirs = [
        Path("/tmp"),
        Path("/var/tmp"),
    ]

    # Limit scope
    max_files = 500
    recent_window = timedelta(hours=24)
    now = datetime.now()

    for temp_dir in temp_dirs:
        if not temp_dir.exists():
            continue

        try:
            files_checked = 0
            for entry in temp_dir.iterdir():
                if files_checked >= max_files:
                    break

                if not entry.is_file():
                    continue

                # Check modification time
                try:
                    mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                    if now - mtime > recent_window:
                        continue
                except OSError:
                    continue

                # Skip huge files
                try:
                    if entry.stat().st_size > 10 * 1024 * 1024:  # 10MB
                        continue
                except OSError:
                    continue

                finding = _assess_temp_file(entry, sweep_id)
                if finding:
                    findings.append(finding)

                files_checked += 1
        except (PermissionError, OSError):
            # Could not access directory
            findings.append(
                Finding(
                    finding_id=f"find_temp_access_{temp_dir.name}_{sweep_id}",
                    sweep_id=sweep_id,
                    severity="low",
                    confidence="low",
                    category="suspicious_temp_file",
                    title="Could not access temp directory",
                    location=str(temp_dir),
                    evidence_ref="directory exists but could not be accessed",
                    why_it_matters="Policy Scout could not verify temp directory contents.",
                    recommended_action="Manually review temp directory if concerned.",
                )
            )

    return findings


def _assess_temp_file(file_path: Path, sweep_id: str) -> Finding:
    """Assess a temp file for suspiciousness.

    Args:
        file_path: Path to temp file.
        sweep_id: Sweep result ID.

    Returns:
        Finding or None.
    """
    filename = file_path.name.lower()

    # Suspicious filenames
    suspicious_filenames = [
        "install.sh",
        "payload.sh",
        "update.sh",
        "postinstall.js",
        "setup.sh",
        "deploy.sh",
        "run.sh",
        "execute.sh",
    ]

    if any(sus in filename for sus in suspicious_filenames):
        return Finding(
            finding_id=f"find_temp_{file_path.name}_{sweep_id}",
            sweep_id=sweep_id,
            severity="medium",
            confidence="moderate",
            category="suspicious_temp_file",
            title="Suspicious filename in temp directory",
            location=_normalize_temp_path(file_path),
            evidence_ref=f"filename matches suspicious pattern: {_redact_sensitive_filename(file_path.name)}",
            why_it_matters="Temp file with suspicious name may indicate downloaded script or payload.",
            recommended_action="Review file content before execution.",
        )

    # Check for executable scripts
    try:
        if os.access(file_path, os.X_OK):
            if filename.endswith((".sh", ".js", ".py", ".rb", ".pl")):
                return Finding(
                    finding_id=f"find_temp_{file_path.name}_{sweep_id}",
                    sweep_id=sweep_id,
                    severity="medium",
                    confidence="moderate",
                    category="suspicious_temp_file",
                    title="Executable script in temp directory",
                    location=_normalize_temp_path(file_path),
                    evidence_ref=f"executable script: {_redact_sensitive_filename(file_path.name)}",
                    why_it_matters="Executable script in temp directory may be suspicious.",
                    recommended_action="Review script content before execution.",
                )
    except OSError:
        pass

    # Check for node/python scripts with suspicious patterns
    if filename.endswith((".js", ".py")):
        try:
            content = file_path.read_text()

            suspicious_patterns = [
                (r"curl", "medium", "curl command found"),
                (r"wget", "medium", "wget command found"),
                (r"eval", "medium", "eval command found"),
                (r"base64", "medium", "base64 command found"),
                (r"child_process", "high", "child process execution"),
                (r"subprocess", "high", "subprocess execution"),
                (r"exec", "medium", "exec command found"),
            ]

            for pattern, severity, title in suspicious_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return Finding(
                        finding_id=f"find_temp_{file_path.name}_{sweep_id}",
                        sweep_id=sweep_id,
                        severity=severity,
                        confidence="moderate",
                        category="suspicious_temp_file",
                        title="Suspicious content in temp script",
                        location=_normalize_temp_path(file_path),
                        evidence_ref=title,
                        why_it_matters="Temp script contains suspicious execution patterns.",
                        recommended_action="Review script content before execution.",
                    )
        except (PermissionError, OSError, UnicodeDecodeError):
            # Could not read or binary file
            pass

    return None
