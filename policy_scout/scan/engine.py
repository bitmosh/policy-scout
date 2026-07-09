# SPDX-License-Identifier: Apache-2.0
"""SecretScanner orchestrator — ties together file and git scanning."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .patterns import SecretPatternMatcher, load_patterns
from .file_scanner import scan_file as _scan_file, scan_directory as _scan_directory
from .git_scanner import scan_staged as _scan_staged, scan_history as _scan_history


@dataclass
class ScanSummary:
    """Aggregated scan summary for audit and reporting."""

    scan_id: str
    scan_type: str                      # "directory", "staged", "history", "file"
    target: str
    findings: list = field(default_factory=list)
    files_scanned: int = 0
    commits_scanned: int = 0
    duration_ms: int = 0
    errors: list = field(default_factory=list)

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def severity_exit_code(self) -> int:
        """0=clean, 1=medium/low, 2=high/critical."""
        if self.critical_count > 0 or self.high_count > 0:
            return 2
        if self.findings:
            return 1
        return 0

    def severity_counts(self) -> dict:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts

    def to_dict(self) -> dict:
        return {
            "scan_id": self.scan_id,
            "scan_type": self.scan_type,
            "target": self.target,
            "finding_count": self.finding_count,
            "severity_counts": self.severity_counts(),
            "files_scanned": self.files_scanned,
            "commits_scanned": self.commits_scanned,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "findings": [f.to_dict() for f in self.findings],
        }


class SecretScanner:
    """High-level secret scanning orchestrator."""

    def __init__(self, patterns_path: Optional[Path] = None):
        specs = load_patterns(patterns_path) if patterns_path else load_patterns()
        self._matcher = SecretPatternMatcher(specs)

    @property
    def pattern_count(self) -> int:
        return len(self._matcher)

    def scan_directory(
        self,
        root: Path,
        scan_id: Optional[str] = None,
        run_entropy: bool = False,
    ) -> ScanSummary:
        """Scan a directory tree for secrets."""
        from ..core.ids import generate_id

        sid = scan_id or generate_id("scan")
        result = _scan_directory(root, self._matcher, run_entropy=run_entropy)
        return ScanSummary(
            scan_id=sid,
            scan_type="directory",
            target=str(root),
            findings=result.findings,
            files_scanned=result.files_scanned,
            duration_ms=result.duration_ms,
            errors=result.errors,
        )

    def scan_file(
        self,
        path: Path,
        scan_id: Optional[str] = None,
        run_entropy: bool = False,
    ) -> ScanSummary:
        """Scan a single file for secrets."""
        from ..core.ids import generate_id

        sid = scan_id or generate_id("scan")
        findings = _scan_file(path, self._matcher, run_entropy=run_entropy)
        return ScanSummary(
            scan_id=sid,
            scan_type="file",
            target=str(path),
            findings=findings,
            files_scanned=1 if findings is not None else 0,
            duration_ms=0,
        )

    def scan_staged(
        self,
        repo_root: Optional[Path] = None,
        scan_id: Optional[str] = None,
    ) -> ScanSummary:
        """Scan git staged files for secrets."""
        from ..core.ids import generate_id

        sid = scan_id or generate_id("scan")
        result = _scan_staged(self._matcher, repo_root=repo_root)
        return ScanSummary(
            scan_id=sid,
            scan_type="staged",
            target=str(repo_root or "."),
            findings=result.findings,
            files_scanned=result.files_scanned,
            duration_ms=result.duration_ms,
            errors=result.errors,
        )

    def scan_history(
        self,
        repo_root: Optional[Path] = None,
        max_commits: int = 200,
        since_ref: Optional[str] = None,
        scan_id: Optional[str] = None,
    ) -> ScanSummary:
        """Scan git commit history for secrets."""
        from ..core.ids import generate_id

        sid = scan_id or generate_id("scan")
        result = _scan_history(
            self._matcher,
            repo_root=repo_root,
            max_commits=max_commits,
            since_ref=since_ref,
        )
        return ScanSummary(
            scan_id=sid,
            scan_type="history",
            target=str(repo_root or "."),
            findings=result.findings,
            files_scanned=result.files_scanned,
            commits_scanned=result.commits_scanned,
            duration_ms=result.duration_ms,
            errors=result.errors,
        )
