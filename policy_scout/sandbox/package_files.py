# SPDX-License-Identifier: Apache-2.0
"""Safe package manifest/lockfile copying for sandbox."""

import shutil
from pathlib import Path
from typing import List, Tuple
from .package_manager import get_package_files


def has_token_like_content(file_path: Path) -> bool:
    """Check if a file contains token-like content.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if token-like content is detected, False otherwise.
    """
    if not file_path.exists():
        return False

    try:
        content = file_path.read_text()
        # Check for common token patterns
        token_patterns = [
            "//registry.npmjs.org/:_authToken",
            "_authToken",
            "NPM_TOKEN",
            "TOKEN",
            "SECRET",
            "PASSWORD",
            "API_KEY",
        ]

        for pattern in token_patterns:
            if pattern in content:
                return True

        return False
    except Exception:
        # If we can't read the file, assume it's unsafe
        return True


def copy_package_files(
    host_cwd: Path, sandbox_workspace: Path, package_manager: str = "npm"
) -> Tuple[List[str], List[str]]:
    """Copy package manifest/lockfile files to sandbox workspace.

    Args:
        host_cwd: Host project directory.
        sandbox_workspace: Sandbox workspace directory.
        package_manager: Package manager name (npm, pnpm, yarn, bun).

    Returns:
        Tuple of (copied_files, skipped_files) lists.
    """
    copied_files = []
    skipped_files = []

    package_files = get_package_files(package_manager)

    for filename in package_files:
        host_file = host_cwd / filename
        sandbox_file = sandbox_workspace / filename

        if not host_file.exists():
            continue

        # Skip config files if they contain token-like content
        if filename in [
            ".npmrc",
            ".pnpmrc",
            ".yarnrc.yml",
            "bunfig.toml",
        ] and has_token_like_content(host_file):
            skipped_files.append(filename)
            continue

        try:
            shutil.copy2(host_file, sandbox_file)
            copied_files.append(filename)
        except Exception:
            skipped_files.append(filename)

    return copied_files, skipped_files


def create_minimal_package_json(
    sandbox_workspace: Path, package_name: str = ""
) -> Path:
    """Create a minimal package.json in the sandbox workspace.

    This is used when the host project has no package.json but we need
    to run npm install for review purposes.

    Args:
        sandbox_workspace: Sandbox workspace directory.
        package_name: Optional package name to include.

    Returns:
        Path to the created package.json.
    """
    package_json_path = sandbox_workspace / "package.json"

    minimal_package = {
        "name": package_name or "sandbox-review",
        "version": "1.0.0",
        "description": "Minimal package for sandbox review",
        "private": True,
    }

    import json

    package_json_path.write_text(json.dumps(minimal_package, indent=2))

    return package_json_path
