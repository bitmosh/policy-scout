# SPDX-License-Identifier: Apache-2.0
"""Post-incident clearance workflow.

Runs a set of checks to determine whether it is safe to exit lockdown.
This is guidance — the human always makes the final call.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .lockdown import is_lockdown_active


@dataclass
class ClearanceCheck:
    """Result of a single clearance check."""

    name: str
    passed: bool
    message: str


@dataclass
class ClearanceResult:
    """Result of the full clearance check suite."""

    cleared: bool
    checks: list = field(default_factory=list)
    summary: str = ""

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)


def _check_audit_chain() -> ClearanceCheck:
    """Verify audit chain integrity."""
    try:
        import os
        from ..audit.chain_verifier import verify_chain

        audit_path_str = os.environ.get(
            "POLICY_SCOUT_AUDIT_PATH",
            str(Path.home() / ".local" / "share" / "policy-scout" / "audit.jsonl"),
        )
        result = verify_chain(Path(audit_path_str))
        if result.verified:
            return ClearanceCheck(
                name="audit_chain",
                passed=True,
                message=f"Audit chain verified ({result.total_entries} entries)",
            )
        return ClearanceCheck(
            name="audit_chain",
            passed=False,
            message=f"Audit chain has integrity errors: {result.message}",
        )
    except Exception as e:
        return ClearanceCheck(
            name="audit_chain",
            passed=False,
            message=f"Audit chain check failed: {e}",
        )


def _check_registry_integrity() -> ClearanceCheck:
    """Verify registry file checksums."""
    try:
        from ..integrity.registry_manifest import verify_registry_integrity

        result = verify_registry_integrity()
        if result.passed:
            return ClearanceCheck(
                name="registry_integrity",
                passed=True,
                message=f"All {result.files_checked} registry files verified",
            )
        return ClearanceCheck(
            name="registry_integrity",
            passed=False,
            message=f"Registry integrity failed: {result.reason}",
        )
    except Exception as e:
        return ClearanceCheck(
            name="registry_integrity",
            passed=False,
            message=f"Registry check failed: {e}",
        )


def _check_no_suspicious_processes() -> ClearanceCheck:
    """Basic check for obviously suspicious process patterns."""
    try:
        import subprocess

        ps = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        ).stdout
        suspicious = [
            line
            for line in ps.splitlines()
            if any(
                pat in line
                for pat in ["nc -l", "ncat", "reverse_shell", "mkfifo /tmp"]
            )
        ]
        if suspicious:
            return ClearanceCheck(
                name="process_check",
                passed=False,
                message=f"Suspicious process(es) found: {len(suspicious)} match(es)",
            )
        return ClearanceCheck(
            name="process_check",
            passed=True,
            message="No obviously suspicious processes detected",
        )
    except Exception as e:
        return ClearanceCheck(
            name="process_check",
            passed=False,
            message=f"Process check failed: {e}",
        )


def _check_lockdown_file_present() -> ClearanceCheck:
    """Confirm lockdown is still active before clearance."""
    if is_lockdown_active():
        return ClearanceCheck(
            name="lockdown_active",
            passed=True,
            message="Lockdown is active — clearance check is meaningful",
        )
    return ClearanceCheck(
        name="lockdown_active",
        passed=False,
        message="Lockdown is not active — clearance check may not be necessary",
    )


def run_clearance_check(audit_store=None) -> ClearanceResult:
    """Run all clearance checks and return a ClearanceResult.

    This is advisory guidance — the operator must decide whether to
    deactivate lockdown based on the results.
    """
    checks = [
        _check_lockdown_file_present(),
        _check_registry_integrity(),
        _check_audit_chain(),
        _check_no_suspicious_processes(),
    ]

    all_passed = all(c.passed for c in checks)

    summary = (
        f"{sum(1 for c in checks if c.passed)}/{len(checks)} checks passed. "
        + (
            "System appears clear. You may consider deactivating lockdown."
            if all_passed
            else "Some checks failed. Review findings before deactivating lockdown."
        )
    )

    result = ClearanceResult(
        cleared=all_passed,
        checks=checks,
        summary=summary,
    )

    if audit_store is not None:
        try:
            from ..audit.events import create_clearance_check_event
            check_summary = {c.name: {"passed": c.passed, "message": c.message} for c in checks}
            audit_store.write(create_clearance_check_event(all_passed, check_summary))
        except Exception:
            pass

    return result
