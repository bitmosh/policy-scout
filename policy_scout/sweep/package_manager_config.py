# SPDX-License-Identifier: Apache-2.0
"""Package manager config checks for quick system sweep."""

import re
from pathlib import Path
from typing import List, Optional
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


def check_package_manager_configs(sweep_id: str) -> List[Finding]:
    """Check for token-bearing package manager config files.

    Args:
        sweep_id: Sweep result ID.

    Returns:
        List of findings.
    """
    findings = []

    # Common package manager config paths
    home = Path.home()
    configs = [
        home / ".npmrc",
        home / ".pnpmrc",
        home / ".yarnrc",
        home / ".yarnrc.yml",
        home / ".config" / "yarn" / "config",
        home / ".bunfig.toml",
    ]

    for config_path in configs:
        finding = _check_config(config_path, sweep_id)
        if finding:
            findings.append(finding)

    return findings


def _check_config(config_path: Path, sweep_id: str) -> Optional[Finding]:
    """Check a single package manager config.

    Args:
        config_path: Path to config file.
        sweep_id: Sweep result ID.

    Returns:
        Finding or None.
    """
    if not config_path.exists():
        return None

    try:
        try:
            content = config_path.read_text()
        except UnicodeDecodeError:
            # Could not decode file
            return Finding(
                finding_id=f"find_config_{config_path.name}_{sweep_id}",
                sweep_id=sweep_id,
                severity="low",
                confidence="low",
                category="package_manager_config",
                title="Could not decode package manager config",
                location=_normalize_path(config_path),
                evidence_ref="file exists but could not be decoded (encoding issue)",
                why_it_matters="Policy Scout could not verify config content due to encoding issues.",
                recommended_action="Manually review config if concerned.",
            )

        # Check for token-bearing indicators
        token_patterns = [
            (r"_authToken", "high", "auth token present"),
            (r"NPM_TOKEN", "high", "npm token present"),
            (r"TOKEN", "medium", "token reference present"),
            (r"SECRET", "medium", "secret reference present"),
            (r"PASSWORD", "medium", "password reference present"),
            (r"API_KEY", "medium", "API key reference present"),
        ]

        for pattern, severity, title in token_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return Finding(
                    finding_id=f"find_config_{config_path.name}_{sweep_id}",
                    sweep_id=sweep_id,
                    severity=severity,
                    confidence="moderate",
                    category="package_manager_config",
                    title="Token-bearing package manager config",
                    location=_normalize_path(config_path),
                    evidence_ref=title,
                    why_it_matters="Package manager config may contain registry tokens or credentials.",
                    recommended_action="Review config file and ensure tokens are not exposed.",
                )

        # Check for other suspicious settings
        suspicious_settings = [
            (r"registry.*http://", "medium", "insecure registry URL"),
            (r"strict-ssl\s*=\s*false", "medium", "SSL verification disabled"),
            (r"proxy\s*=", "low", "proxy configuration present"),
            (r"script-shell\s*=", "low", "custom script shell configured"),
        ]

        for pattern, severity, title in suspicious_settings:
            if re.search(pattern, content, re.IGNORECASE):
                return Finding(
                    finding_id=f"find_config_{config_path.name}_{sweep_id}",
                    sweep_id=sweep_id,
                    severity=severity,
                    confidence="low",
                    category="package_manager_config",
                    title="Suspicious package manager config setting",
                    location=_normalize_path(config_path),
                    evidence_ref=title,
                    why_it_matters="Config may have security implications.",
                    recommended_action="Review config settings.",
                )

        return None

    except (PermissionError, OSError):
        # Could not read file
        return Finding(
            finding_id=f"find_config_{config_path.name}_{sweep_id}",
            sweep_id=sweep_id,
            severity="low",
            confidence="low",
            category="package_manager_config",
            title="Could not read package manager config",
            location=_normalize_path(config_path),
            evidence_ref="file exists but could not be read",
            why_it_matters="Policy Scout could not verify config content.",
            recommended_action="Manually review config if concerned.",
        )
