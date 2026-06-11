"""Policy versioning — snapshot current registry state into git."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


_REGISTRY_FILES = [
    "command_registry.yaml",
    "default_policy.yaml",
    "eval_cases.yaml",
    "playbooks.yaml",
    "secret_patterns.yaml",
]


def commit_policy_state(
    message: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> str:
    """
    Stage all policy data files and create a git commit.

    Returns the commit SHA on success.
    Raises RuntimeError if not in a git repo or if git commands fail.
    """
    data_dir = Path(__file__).parent.parent.parent / "data"
    policy_files = [data_dir / f for f in _REGISTRY_FILES if (data_dir / f).exists()]

    if not policy_files:
        raise RuntimeError("No policy data files found to commit.")

    cwd = repo_root or Path.cwd()

    # Verify we're in a git repo
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True, text=True, cwd=str(cwd),
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Not in a git repository. policy commit requires a git repo."
        )

    # Stage only the policy files
    add_result = subprocess.run(
        ["git", "add"] + [str(p) for p in policy_files],
        capture_output=True, text=True, cwd=str(cwd),
    )
    if add_result.returncode != 0:
        raise RuntimeError(f"git add failed: {add_result.stderr.strip()}")

    # Check if there's anything staged
    status = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True, cwd=str(cwd),
    )
    if not status.stdout.strip():
        raise RuntimeError(
            "No policy file changes to commit. "
            "Files are already up to date with the last commit."
        )

    commit_msg = message or _default_message(policy_files)
    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        capture_output=True, text=True, cwd=str(cwd),
    )
    if commit_result.returncode != 0:
        raise RuntimeError(f"git commit failed: {commit_result.stderr.strip()}")

    # Return the new commit SHA
    sha_result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, cwd=str(cwd),
    )
    return sha_result.stdout.strip() if sha_result.returncode == 0 else "(unknown)"


def _default_message(policy_files: list[Path]) -> str:
    names = ", ".join(sorted(f.name for f in policy_files))
    return f"policy: snapshot registry state ({names})"
