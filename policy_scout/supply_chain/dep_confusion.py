"""Dependency confusion detection."""

from __future__ import annotations

import configparser
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


_INTERNAL_PATTERN = re.compile(
    r'\b(internal|private|corp|company|local|intranet)\b', re.IGNORECASE
)
_SCOPED_PUBLIC_RE = re.compile(r'^@[a-z0-9-]+/[a-z0-9-]+$')

# Public scopes that are clearly legitimate (not confused internal packages)
_KNOWN_PUBLIC_SCOPES = frozenset({
    "@types", "@babel", "@jest", "@angular", "@vue", "@react", "@nestjs",
    "@aws-sdk", "@google-cloud", "@microsoft", "@azure", "@firebase",
    "@sentry", "@testing-library", "@storybook", "@emotion", "@mui",
})


@dataclass
class DependencyConfusionResult:
    package_name: str
    ecosystem: str
    suspicious: bool
    reasons: List[str] = field(default_factory=list)
    severity: str = "info"

    def to_dict(self) -> dict:
        return {
            "type": "supply_chain",
            "pattern_id": "dependency_confusion",
            "description": f"Potential dependency confusion: {self.package_name}",
            "severity": self.severity,
            "confidence": "medium",
            "matched_text": self.package_name,
            "line_number": 0,
            "source": "dep_confusion",
            "reasons": self.reasons,
        }


def _read_npm_private_registries(project_root: Path) -> List[str]:
    """Parse .npmrc files for private registry entries."""
    registries = []
    for candidate in (project_root / ".npmrc", Path.home() / ".npmrc"):
        if not candidate.exists():
            continue
        for line in candidate.read_text(errors="replace").splitlines():
            line = line.strip()
            if "registry" in line and "=" in line:
                _, _, value = line.partition("=")
                value = value.strip()
                if value and "registry.npmjs.org" not in value:
                    registries.append(value)
    return registries


def _read_pip_private_registries(project_root: Path) -> List[str]:
    """Parse pip.conf or pyproject.toml for private index URLs."""
    registries = []
    candidates = [
        project_root / "pip.conf",
        Path.home() / ".pip" / "pip.conf",
        Path.home() / ".config" / "pip" / "pip.conf",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        cfg = configparser.ConfigParser()
        try:
            cfg.read(str(candidate))
            url = cfg.get("global", "index-url", fallback="")
            if url and "pypi.org" not in url:
                registries.append(url)
            extra = cfg.get("global", "extra-index-url", fallback="")
            if extra:
                registries.extend(u.strip() for u in extra.splitlines() if u.strip())
        except Exception:
            pass
    return registries


def read_private_registries(project_root: Optional[Path], ecosystem: str) -> List[str]:
    root = project_root or Path.cwd()
    if ecosystem in ("npm", "yarn", "pnpm"):
        return _read_npm_private_registries(root)
    if ecosystem in ("pypi", "pip"):
        return _read_pip_private_registries(root)
    return []


def check_dependency_confusion(
    package_name: str,
    ecosystem: str,
    project_root: Optional[Path] = None,
) -> DependencyConfusionResult:
    """Check a package name for dependency confusion signals."""
    reasons: List[str] = []

    # Signal 1: name contains internal-sounding keywords
    if _INTERNAL_PATTERN.search(package_name):
        reasons.append(f"name contains internal-sounding keyword")

    # Signal 2: scoped package on public registry where scope looks private
    if package_name.startswith("@"):
        scope = package_name.split("/")[0]
        if scope not in _KNOWN_PUBLIC_SCOPES and _SCOPED_PUBLIC_RE.match(package_name):
            reasons.append(f"scoped package with unknown/private-looking scope: {scope}")

    # Signal 3: name follows common internal naming conventions
    if re.search(r'-(?:api|service|lib|sdk|client|core|utils?|helpers?|common)$', package_name, re.I):
        # Only flag if combined with a private registry or internal keyword
        private_registries = read_private_registries(project_root, ecosystem)
        if private_registries:
            reasons.append(
                f"generic internal-style name with private registry configured: {private_registries[0]!r}"
            )

    suspicious = len(reasons) > 0
    severity = "high" if len(reasons) >= 2 else ("medium" if suspicious else "info")
    return DependencyConfusionResult(
        package_name=package_name,
        ecosystem=ecosystem,
        suspicious=suspicious,
        reasons=reasons,
        severity=severity,
    )
