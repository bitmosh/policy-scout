"""Lockfile and package manifest tamper detection."""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


_LOCKFILE_NAMES = [
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Pipfile.lock",
    "poetry.lock",
    "requirements.txt",
    "Cargo.lock",
    "go.sum",
]


@dataclass
class LockfileDiff:
    """Changes detected in a lockfile between HEAD and the working tree / index."""

    lockfile: str
    added: list = field(default_factory=list)      # new packages/entries
    removed: list = field(default_factory=list)    # removed packages/entries
    modified: int = 0                              # changed lines (rough count)
    error: Optional[str] = None

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.modified)

    def to_dict(self) -> dict:
        return {
            "lockfile": self.lockfile,
            "has_changes": self.has_changes,
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "error": self.error,
        }


@dataclass
class LockfileCheckResult:
    """Result of checking all lockfiles in a repo."""

    diffs: list = field(default_factory=list)
    lockfiles_found: int = 0
    lockfiles_changed: int = 0

    @property
    def any_changes(self) -> bool:
        return self.lockfiles_changed > 0

    def to_dict(self) -> dict:
        return {
            "lockfiles_found": self.lockfiles_found,
            "lockfiles_changed": self.lockfiles_changed,
            "any_changes": self.any_changes,
            "diffs": [d.to_dict() for d in self.diffs],
        }


def _run_git(args: list, cwd: Optional[Path] = None) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            timeout=15,
        )
        return r.returncode, r.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 1, str(e)


def _parse_added_removed(diff_text: str) -> tuple[list, list, int]:
    """Extract added/removed line summaries from a unified diff."""
    added = []
    removed = []
    modified = 0

    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            content = line[1:].strip()
            if content:
                added.append(content[:120])
        elif line.startswith("-") and not line.startswith("---"):
            content = line[1:].strip()
            if content:
                removed.append(content[:120])

    # Approximate modify count: lines that appear in both added and removed
    added_set = set(added)
    removed_set = set(removed)
    likely_modified = added_set & removed_set
    modified = len(likely_modified)
    added = [l for l in added if l not in likely_modified]
    removed = [l for l in removed if l not in likely_modified]

    return added[:50], removed[:50], modified


def check_lockfile_changes(
    repo_root: Optional[Path] = None,
    compare_ref: str = "HEAD",
) -> LockfileCheckResult:
    """Compare lockfiles between compare_ref and working tree."""
    root = Path(repo_root or ".").resolve()
    result = LockfileCheckResult()

    # Find all lockfiles tracked in the repo
    rc, tracked = _run_git(["ls-files"] + _LOCKFILE_NAMES, cwd=root)
    if rc != 0:
        return result

    lockfiles = [f.strip() for f in tracked.splitlines() if f.strip()]
    result.lockfiles_found = len(lockfiles)

    for rel_path in lockfiles:
        rc2, diff_out = _run_git(
            ["diff", compare_ref, "--", rel_path],
            cwd=root,
        )
        if rc2 != 0:
            result.diffs.append(
                LockfileDiff(lockfile=rel_path, error="git diff failed")
            )
            continue

        if not diff_out.strip():
            # No changes
            result.diffs.append(LockfileDiff(lockfile=rel_path))
            continue

        added, removed, modified = _parse_added_removed(diff_out)
        diff = LockfileDiff(
            lockfile=rel_path,
            added=added,
            removed=removed,
            modified=modified,
        )
        result.diffs.append(diff)
        if diff.has_changes:
            result.lockfiles_changed += 1

    return result
