"""Manifest/lockfile diff capture for sandbox."""

from pathlib import Path
from typing import Dict, Tuple


def capture_manifest_diffs(
    sandbox_workspace: Path,
    before_snapshot: Dict[str, str],
    after_snapshot: Dict[str, str],
) -> Tuple[bool, bool, Dict[str, str]]:
    """Capture diffs for package.json and lockfiles.

    Args:
        sandbox_workspace: Path to the sandbox workspace.
        before_snapshot: Dict of file content before install.
        after_snapshot: Dict of file content after install.

    Returns:
        Tuple of (manifest_changed, lockfile_changed, diffs_dict).
    """
    manifest_changed = False
    lockfile_changed = False
    diffs = {}

    # Check package.json
    before_content = before_snapshot.get("package.json", "")
    after_content = after_snapshot.get("package.json", "")

    if before_content != after_content:
        manifest_changed = True
        diffs["package.json"] = _simple_diff(before_content, after_content)

    # Check lockfiles
    lockfiles = ["package-lock.json", "npm-shrinkwrap.json"]
    for lockfile in lockfiles:
        before_content = before_snapshot.get(lockfile, "")
        after_content = after_snapshot.get(lockfile, "")

        if before_content != after_content:
            lockfile_changed = True
            diffs[lockfile] = _simple_diff(before_content, after_content)

    return manifest_changed, lockfile_changed, diffs


def take_file_snapshot(sandbox_workspace: Path) -> Dict[str, str]:
    """Take a snapshot of package manifest/lockfile files.

    Args:
        sandbox_workspace: Path to the sandbox workspace.

    Returns:
        Dict mapping filename to file content.
    """
    snapshot = {}

    files_to_snapshot = ["package.json", "package-lock.json", "npm-shrinkwrap.json"]

    for filename in files_to_snapshot:
        file_path = sandbox_workspace / filename
        if file_path.exists():
            try:
                snapshot[filename] = file_path.read_text()
            except Exception:
                snapshot[filename] = ""
        else:
            snapshot[filename] = ""

    return snapshot


def _simple_diff(before: str, after: str) -> str:
    """Generate a simple text diff.

    For v0.1, this is a simple indicator that content changed.
    A more sophisticated diff can come later.

    Args:
        before: Content before.
        after: Content after.

    Returns:
        Simple diff description.
    """
    if before == after:
        return "No changes"

    if not before and after:
        return "File created"

    if before and not after:
        return "File deleted"

    # Content changed
    before_lines = before.splitlines() if before else []
    after_lines = after.splitlines() if after else []

    return f"Content changed ({len(before_lines)} lines -> {len(after_lines)} lines)"
