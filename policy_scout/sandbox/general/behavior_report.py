# SPDX-License-Identifier: Apache-2.0
"""Combine fs diff + syscall analysis into a behavior report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .overlay_fs import FSChanges
from .syscall_analyzer import SyscallReport


@dataclass
class BehaviorFinding:
    severity: str
    category: str
    title: str
    evidence: str
    confidence: str = "high"

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


@dataclass
class BehaviorReport:
    command: str
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str
    fs_changes: FSChanges
    syscall_report: SyscallReport
    findings: List[BehaviorFinding] = field(default_factory=list)
    detection_confidence: str = "high"

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "stdout": self.stdout[:4096],
            "stderr": self.stderr[:2048],
            "fs_changes": self.fs_changes.to_dict(),
            "syscall_report": self.syscall_report.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "finding_count": len(self.findings),
            "detection_confidence": self.detection_confidence,
        }

    @property
    def worst_severity(self) -> str:
        order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        if not self.findings:
            return "info"
        return max(self.findings, key=lambda f: order.get(f.severity, 0)).severity


def build_behavior_report(
    command: str,
    exit_code: int,
    timed_out: bool,
    stdout: str,
    stderr: str,
    fs_changes: FSChanges,
    syscall_report: SyscallReport,
    overlayfs_used: bool = True,
) -> BehaviorReport:
    findings: List[BehaviorFinding] = []

    # Network attempts inside isolated namespace — should never happen with --net
    if syscall_report.network_attempts:
        findings.append(BehaviorFinding(
            severity="high",
            category="network_in_sandbox",
            title=f"Command attempted {len(syscall_report.network_attempts)} network connection(s)",
            evidence=str([n.syscall for n in syscall_report.network_attempts[:5]]),
        ))

    # Sensitive file access
    for access in syscall_report.sensitive_accesses:
        sev = "critical" if ".ssh" in access.path or "id_rsa" in access.path else "high"
        findings.append(BehaviorFinding(
            severity=sev,
            category="sensitive_file_access",
            title=f"Accessed sensitive path: {access.path}",
            evidence=f"syscall={access.syscall} flags={access.flags}",
        ))

    # Unexpected subprocess execution
    if syscall_report.exec_calls:
        findings.append(BehaviorFinding(
            severity="medium",
            category="subprocess_execution",
            title=f"Command spawned {len(syscall_report.exec_calls)} subprocess(es)",
            evidence=str([e.command for e in syscall_report.exec_calls[:10]]),
        ))

    # Filesystem changes
    if fs_changes.created:
        findings.append(BehaviorFinding(
            severity="low",
            category="fs_created",
            title=f"Created {len(fs_changes.created)} file(s)",
            evidence=str(fs_changes.created[:10]),
        ))
    if fs_changes.modified:
        findings.append(BehaviorFinding(
            severity="medium",
            category="fs_modified",
            title=f"Modified {len(fs_changes.modified)} file(s)",
            evidence=str(fs_changes.modified[:10]),
        ))
    if fs_changes.deleted:
        findings.append(BehaviorFinding(
            severity="high",
            category="fs_deleted",
            title=f"Deleted {len(fs_changes.deleted)} file(s)",
            evidence=str(fs_changes.deleted[:10]),
        ))

    # Timed out
    if timed_out:
        findings.append(BehaviorFinding(
            severity="medium",
            category="timeout",
            title="Command timed out",
            evidence="Process did not complete within the timeout limit",
        ))

    confidence = "high" if overlayfs_used else "medium"
    return BehaviorReport(
        command=command,
        exit_code=exit_code,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        fs_changes=fs_changes,
        syscall_report=syscall_report,
        findings=findings,
        detection_confidence=confidence,
    )
