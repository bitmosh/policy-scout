# SPDX-License-Identifier: Apache-2.0
"""Git-aware secret scanning: staged files and commit history."""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .patterns import SecretPatternMatcher


@dataclass
class GitScanResult:
    """Result of a git-aware scan."""

    findings: list = field(default_factory=list)
    files_scanned: int = 0
    commits_scanned: int = 0
    duration_ms: int = 0
    errors: list = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        return any(f.severity == "critical" for f in self.findings)


def _run_git(args: list, cwd: Optional[Path] = None) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 1, "", str(e)


def scan_staged(
    matcher: SecretPatternMatcher,
    repo_root: Optional[Path] = None,
) -> GitScanResult:
    """Scan all staged (index) files for secrets.

    Uses `git diff --cached --name-only` to enumerate staged files, then
    reads each via `git show :path` (index version, not working tree).
    """
    import time

    start = time.monotonic()
    result = GitScanResult()

    rc, stdout, stderr = _run_git(
        ["diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=repo_root,
    )
    if rc != 0:
        result.errors.append(f"git diff --cached failed: {stderr.strip()}")
        return result

    staged_files = [f.strip() for f in stdout.splitlines() if f.strip()]

    for rel_path in staged_files:
        rc2, content, err2 = _run_git(["show", f":{rel_path}"], cwd=repo_root)
        if rc2 != 0:
            result.errors.append(f"git show :{rel_path} failed: {err2.strip()}")
            continue

        findings = matcher.scan_text(content, source=rel_path)
        result.files_scanned += 1
        result.findings.extend(findings)

    result.duration_ms = int((time.monotonic() - start) * 1000)
    return result


def scan_history(
    matcher: SecretPatternMatcher,
    repo_root: Optional[Path] = None,
    max_commits: int = 200,
    since_ref: Optional[str] = None,
) -> GitScanResult:
    """Scan commit history for secrets introduced in diffs.

    Iterates commits (up to max_commits), reads each file change via
    `git show <commit>:<path>` for added/modified files.
    """
    import time

    start = time.monotonic()
    result = GitScanResult()

    log_args = [
        "log",
        "--format=%H",
        f"--max-count={max_commits}",
    ]
    if since_ref:
        log_args.append(f"{since_ref}..HEAD")

    rc, stdout, _ = _run_git(log_args, cwd=repo_root)
    if rc != 0:
        result.errors.append("git log failed — is this a git repository?")
        return result

    commits = [c.strip() for c in stdout.splitlines() if c.strip()]

    for commit in commits:
        rc2, diff_out, _ = _run_git(
            ["diff-tree", "--no-commit-id", "-r", "--name-status", commit],
            cwd=repo_root,
        )
        if rc2 != 0:
            continue

        result.commits_scanned += 1

        for line in diff_out.splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) != 2:
                continue
            status, rel_path = parts
            if status not in ("A", "M"):
                continue

            rc3, content, _ = _run_git(
                ["show", f"{commit}:{rel_path}"], cwd=repo_root
            )
            if rc3 != 0:
                continue

            findings = matcher.scan_text(content, source=rel_path)
            for f in findings:
                f.commit = commit
            result.files_scanned += 1
            result.findings.extend(findings)

    result.duration_ms = int((time.monotonic() - start) * 1000)
    return result
