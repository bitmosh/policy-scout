# SPDX-License-Identifier: Apache-2.0
"""Lightweight self-check run on every Policy Scout invocation."""

import sys
from dataclasses import dataclass, field
from typing import Optional

from .registry_manifest import verify_registry_integrity, IntegrityCheckResult

_startup_check_done = False


@dataclass
class StartupCheckResult:
    """Result of the startup self-check."""

    passed: bool
    from_cache: bool = False
    lockdown_active: bool = False
    integrity_errors: list = field(default_factory=list)


def _check_lockdown() -> bool:
    """Check if lockdown mode is active. Returns False if module unavailable."""
    try:
        from ..response.lockdown import is_lockdown_active
        return is_lockdown_active()
    except Exception:
        return False


def run_startup_check(
    force: bool = False,
    audit_store=None,
) -> StartupCheckResult:
    """Run registry integrity + lockdown check.

    Results are cached per-process (flag _startup_check_done) to avoid
    re-hashing on every call in a single invocation.

    Does NOT exit on failure — operating with a warning is safer than
    becoming a denial-of-service vector.
    """
    global _startup_check_done
    if _startup_check_done and not force:
        return StartupCheckResult(passed=True, from_cache=True)

    integrity = verify_registry_integrity()
    lockdown_active = _check_lockdown()

    if not integrity.passed:
        print(
            f"\nPOLICY SCOUT INTEGRITY WARNING: {integrity.reason}",
            file=sys.stderr,
        )
        if integrity.errors:
            for err in integrity.errors:
                print(f"  - {err}", file=sys.stderr)
        print(
            "Registry files may have been tampered with.\n"
            "Run 'policy-scout doctor' for details.\n",
            file=sys.stderr,
        )
        if audit_store is not None:
            try:
                from ..audit.events import create_integrity_check_failed_event
                audit_store.write(create_integrity_check_failed_event(integrity.errors))
            except Exception:
                pass

    _startup_check_done = True
    return StartupCheckResult(
        passed=integrity.passed,
        lockdown_active=lockdown_active,
        integrity_errors=integrity.errors,
    )


def reset_startup_check_cache() -> None:
    """Reset the per-process startup check cache. Intended for testing only."""
    global _startup_check_done
    _startup_check_done = False
