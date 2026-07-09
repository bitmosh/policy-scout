# SPDX-License-Identifier: Apache-2.0
"""Lockfile integrity checker — validates SRI hashes in package-lock.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from ..adapter import IntelResult


def _find_lockfile(start_dir: str = ".") -> Optional[Path]:
    """Walk up from start_dir looking for package-lock.json."""
    cwd = Path(start_dir).resolve()
    for directory in [cwd, *cwd.parents]:
        candidate = directory / "package-lock.json"
        if candidate.exists():
            return candidate
    return None


def _validate_sri(integrity: str) -> bool:
    """Return True if the SRI string looks structurally valid."""
    # SRI format: sha512-<base64> or sha384-<base64> or sha256-<base64>
    if not integrity:
        return False
    parts = integrity.split("-", 1)
    if len(parts) != 2:
        return False
    algo, b64 = parts
    if algo not in ("sha512", "sha384", "sha256"):
        return False
    if len(b64) < 40:
        return False
    return True


class LockfileIntegrityResult:
    def __init__(self):
        self.packages_checked: int = 0
        self.packages_missing_integrity: list[str] = []
        self.packages_bad_integrity: list[str] = []
        self.lockfile_path: Optional[str] = None

    @property
    def ok(self) -> bool:
        return not self.packages_missing_integrity and not self.packages_bad_integrity


def check_lockfile_integrity(lockfile_path: Optional[str] = None) -> LockfileIntegrityResult:
    """Check integrity fields in a package-lock.json file.

    Looks for the lockfile relative to the current directory if not provided.
    Returns a result object — does not raise on missing lockfile (returns ok=True).
    """
    result = LockfileIntegrityResult()

    if lockfile_path:
        lf_path = Path(lockfile_path)
    else:
        lf_path = _find_lockfile()

    if lf_path is None or not lf_path.exists():
        return result  # No lockfile — not an error condition

    result.lockfile_path = str(lf_path)

    try:
        data = json.loads(lf_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        result.packages_bad_integrity.append("<lockfile parse error>")
        return result

    lockfile_version = data.get("lockfileVersion", 1)

    # lockfileVersion 2 and 3 use "packages" key; v1 uses "dependencies"
    if lockfile_version >= 2:
        packages: dict = data.get("packages", {})
        for pkg_path, pkg_data in packages.items():
            if not isinstance(pkg_data, dict):
                continue
            if not pkg_path:  # root package has empty key
                continue
            # Optional dependency entries may not have resolved/integrity
            if "resolved" not in pkg_data and "version" not in pkg_data:
                continue
            result.packages_checked += 1
            integrity = pkg_data.get("integrity", "")
            if not integrity:
                result.packages_missing_integrity.append(pkg_path)
            elif not _validate_sri(integrity):
                result.packages_bad_integrity.append(pkg_path)
    else:
        # v1 format
        deps: dict = data.get("dependencies", {})
        _check_deps_v1(deps, result)

    return result


def _check_deps_v1(deps: dict, result: LockfileIntegrityResult) -> None:
    for name, pkg_data in deps.items():
        if not isinstance(pkg_data, dict):
            continue
        if pkg_data.get("bundled"):
            continue
        result.packages_checked += 1
        integrity = pkg_data.get("integrity", "")
        if not integrity:
            result.packages_missing_integrity.append(name)
        elif not _validate_sri(integrity):
            result.packages_bad_integrity.append(name)
        # Recurse into nested dependencies (v1 format)
        if "dependencies" in pkg_data:
            _check_deps_v1(pkg_data["dependencies"], result)


class LockfileIntegrityAdapter:
    """Local adapter: validates SRI hashes in package-lock.json."""

    def enrich_package(
        self,
        ecosystem: str,
        name: str,
        version: Optional[str] = None,
    ) -> IntelResult:
        if ecosystem != "npm":
            # Only npm has package-lock.json
            return IntelResult(package_name=name, ecosystem=ecosystem,
                               lockfile_integrity_ok=None, source="local")

        lf_result = check_lockfile_integrity()

        ok: Optional[bool]
        if lf_result.lockfile_path is None:
            ok = None  # no lockfile found
        elif not lf_result.ok:
            ok = False
        else:
            ok = True if lf_result.packages_checked > 0 else None

        evidence = None
        if ok is False:
            parts = []
            if lf_result.packages_missing_integrity:
                parts.append(
                    f"{len(lf_result.packages_missing_integrity)} packages missing integrity"
                )
            if lf_result.packages_bad_integrity:
                parts.append(
                    f"{len(lf_result.packages_bad_integrity)} packages with malformed integrity"
                )
            evidence = "; ".join(parts)

        return IntelResult(
            package_name=name,
            ecosystem=ecosystem,
            lockfile_integrity_ok=ok,
            known_bad_evidence=evidence if ok is False else None,
            confidence="high",
            source="local",
        )
