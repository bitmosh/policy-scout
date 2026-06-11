"""Known-bad package registry adapter."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from ..adapter import IntelResult


@lru_cache(maxsize=1)
def _load_registry() -> dict:
    import yaml

    path = Path(__file__).parent.parent.parent / "data" / "known_bad_registry.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _lookup(ecosystem: str, name: str, version: Optional[str]) -> tuple[bool, Optional[str]]:
    """Return (is_bad, evidence) for a package. Checks exact versioned and unversioned entries."""
    registry = _load_registry()
    eco_entries: dict = registry.get(ecosystem, {})
    if not eco_entries:
        return False, None

    lower_name = name.lower()

    # Versioned lookup first: "name@version"
    if version:
        key = f"{lower_name}@{version}"
        if key in eco_entries:
            entry = eco_entries[key]
            evidence = entry.get("reason", "") if isinstance(entry, dict) else str(entry)
            src = entry.get("source", "") if isinstance(entry, dict) else ""
            return True, f"{evidence} [{src}]" if src else evidence

    # Unversioned lookup: matches any version
    if lower_name in eco_entries:
        entry = eco_entries[lower_name]
        evidence = entry.get("reason", "") if isinstance(entry, dict) else str(entry)
        src = entry.get("source", "") if isinstance(entry, dict) else ""
        return True, f"{evidence} [{src}]" if src else evidence

    return False, None


class KnownBadAdapter:
    """Local adapter: checks against the bundled known-bad registry."""

    def enrich_package(
        self,
        ecosystem: str,
        name: str,
        version: Optional[str] = None,
    ) -> IntelResult:
        is_bad, evidence = _lookup(ecosystem, name, version)
        return IntelResult(
            package_name=name,
            ecosystem=ecosystem,
            known_bad=is_bad,
            known_bad_evidence=evidence,
            confidence="high",
            source="local",
        )
