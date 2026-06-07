"""Shell profile checks for quick system sweep."""

import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
from .models import Finding


def _normalize_path(path: Path) -> str:
    """Normalize a path to use ~ for home directory.

    Args:
        path: Path to normalize.

    Returns:
        Normalized path string with ~ for home directory.
    """
    home = Path.home()
    try:
        if path.is_relative_to(home):
            return "~/" + str(path.relative_to(home))
    except (ValueError, AttributeError):
        pass
    return str(path)


def check_shell_profiles(sweep_id: str) -> List[Finding]:
    """Check for recent shell profile changes.

    Args:
        sweep_id: Sweep result ID.

    Returns:
        List of findings.
    """
    findings = []

    # Common shell profiles
    home = Path.home()
    profiles = [
        home / ".bashrc",
        home / ".zshrc",
        home / ".profile",
        home / ".bash_profile",
    ]

    for profile_path in profiles:
        finding = _check_profile(profile_path, sweep_id)
        if finding:
            findings.append(finding)

    return findings


def _check_profile(profile_path: Path, sweep_id: str) -> Optional[Finding]:
    """Check a single shell profile.

    Args:
        profile_path: Path to shell profile.
        sweep_id: Sweep result ID.

    Returns:
        Finding or None.
    """
    if not profile_path.exists():
        return None

    try:
        # Check modification time
        mtime = datetime.fromtimestamp(profile_path.stat().st_mtime)
        now = datetime.now()

        # Check if modified in last 24 hours
        if now - mtime > timedelta(hours=24):
            return None

        # Read content
        try:
            content = profile_path.read_text()
        except UnicodeDecodeError:
            # Could not decode file
            return Finding(
                finding_id=f"find_profile_{profile_path.name}_{sweep_id}",
                sweep_id=sweep_id,
                severity="low",
                confidence="low",
                category="shell_profile_change",
                title="Could not decode shell profile",
                location=_normalize_path(profile_path),
                evidence_ref="file exists but could not be decoded (encoding issue)",
                why_it_matters="Policy Scout could not verify shell profile content due to encoding issues.",
                recommended_action="Manually review shell profile if concerned.",
            )

        # Check for suspicious content
        suspicious_patterns = [
            (r"curl", "medium", "curl command found"),
            (r"wget", "medium", "wget command found"),
            (r"\beval\b", "medium", "eval command found"),
            (r"base64", "medium", "base64 command found"),
            (r"source\s+/tmp", "high", "sourcing from /tmp"),
            (r"/tmp/", "medium", "reference to /tmp"),
            (r"crontab", "high", "crontab reference"),
            (r"systemctl\s+--user", "high", "systemctl user service reference"),
            (r"export\s+PATH.*\/tmp", "high", "PATH includes temp directory"),
            (r"\.env", "medium", "reference to .env"),
            (r"\.npmrc", "medium", "reference to .npmrc"),
            (r"\.ssh", "high", "reference to .ssh"),
        ]

        for pattern, severity, title in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return Finding(
                    finding_id=f"find_profile_{profile_path.name}_{sweep_id}",
                    sweep_id=sweep_id,
                    severity=severity,
                    confidence="moderate",
                    category="shell_profile_change",
                    title="Recent shell profile change: " + title,
                    location=_normalize_path(profile_path),
                    evidence_ref=f"modified {now - mtime} ago",
                    why_it_matters="Recent shell profile modification with suspicious content may indicate persistence mechanism.",
                    recommended_action="Review shell profile changes and ensure they are expected.",
                )

        # If modified recently but no suspicious content, still note it
        return Finding(
            finding_id=f"find_profile_{profile_path.name}_{sweep_id}",
            sweep_id=sweep_id,
            severity="low",
            confidence="moderate",
            category="shell_profile_change",
            title="Recent shell profile modification",
            location=_normalize_path(profile_path),
            evidence_ref=f"modified {now - mtime} ago",
            why_it_matters="Shell profile was modified recently. Review if this is expected.",
            recommended_action="Review shell profile changes.",
        )

    except (PermissionError, OSError):
        # Could not read file
        return Finding(
            finding_id=f"find_profile_{profile_path.name}_{sweep_id}",
            sweep_id=sweep_id,
            severity="low",
            confidence="low",
            category="shell_profile_change",
            title="Could not read shell profile",
            location=_normalize_path(profile_path),
            evidence_ref="file exists but could not be read",
            why_it_matters="Policy Scout could not verify shell profile content.",
            recommended_action="Manually review shell profile if concerned.",
        )
