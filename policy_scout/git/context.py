# SPDX-License-Identifier: Apache-2.0
"""Git repository context extraction."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GitContext:
    """Metadata about the current git state."""

    branch: Optional[str]
    commit: Optional[str]    # short hash
    dirty: bool              # uncommitted changes present
    remote: Optional[str]    # first remote name (usually "origin")
    repo_root: Optional[str]

    def to_dict(self) -> dict:
        return {
            "branch": self.branch,
            "commit": self.commit,
            "dirty": self.dirty,
            "remote": self.remote,
            "repo_root": self.repo_root,
        }


def _run(args: list, cwd: Optional[Path] = None) -> tuple[int, str]:
    try:
        r = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            timeout=10,
        )
        return r.returncode, r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, ""


def get_git_context(cwd: Optional[Path] = None) -> Optional[GitContext]:
    """Return git context for the given directory, or None if not in a repo."""
    rc, root = _run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if rc != 0:
        return None

    _, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    _, commit = _run(["git", "rev-parse", "--short", "HEAD"], cwd=cwd)

    rc_status, status_out = _run(["git", "status", "--porcelain"], cwd=cwd)
    dirty = rc_status == 0 and bool(status_out.strip())

    _, remote_out = _run(["git", "remote"], cwd=cwd)
    remote = remote_out.splitlines()[0] if remote_out.strip() else None

    return GitContext(
        branch=branch or None,
        commit=commit or None,
        dirty=dirty,
        remote=remote,
        repo_root=root or None,
    )
