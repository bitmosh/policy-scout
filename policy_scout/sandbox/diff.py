"""Manifest/lockfile diff capture for sandbox."""

from pathlib import Path
from typing import Dict, Tuple

from .package_manager import get_package_files

# Filenames that are lockfiles (not manifests) per package manager
_LOCKFILE_NAMES = frozenset({
    "package-lock.json",
    "npm-shrinkwrap.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "bun.lock",
})


def capture_manifest_diffs(
    before_snapshot: Dict[str, str],
    after_snapshot: Dict[str, str],
    package_manager: str = "npm",
) -> Tuple[bool, bool, Dict[str, str]]:
    """Capture diffs for package.json and lockfiles.

    Returns:
        Tuple of (manifest_changed, lockfile_changed, diffs_dict).
    """
    manifest_changed = False
    lockfile_changed = False
    diffs = {}

    all_files = get_package_files(package_manager)

    for filename in all_files:
        before_content = before_snapshot.get(filename, "")
        after_content = after_snapshot.get(filename, "")

        if before_content == after_content:
            continue

        diff_str = _simple_diff(before_content, after_content)
        diffs[filename] = diff_str

        if filename == "package.json":
            manifest_changed = True
        elif filename in _LOCKFILE_NAMES:
            lockfile_changed = True

    return manifest_changed, lockfile_changed, diffs


def take_file_snapshot(
    sandbox_workspace: Path,
    package_manager: str = "npm",
) -> Dict[str, str]:
    """Take a snapshot of package manifest/lockfile files.

    Returns:
        Dict mapping filename to file content.
    """
    snapshot = {}

    for filename in get_package_files(package_manager):
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
