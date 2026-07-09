# SPDX-License-Identifier: Apache-2.0
"""Temporary workspace creation for sandbox."""

import os
from pathlib import Path
from typing import Optional
from ..core.ids import generate_id


def get_sandbox_root() -> Path:
    """Get the sandbox root directory from env or default."""
    env_override = os.environ.get("POLICY_SCOUT_SANDBOX_ROOT")
    if env_override:
        return Path(env_override)

    # Default: ~/.local/share/policy-scout/sandboxes
    default_root = Path.home() / ".local" / "share" / "policy-scout" / "sandboxes"
    return default_root


def create_sandbox_workspace(sandbox_id: Optional[str] = None) -> Path:
    """Create a temporary sandbox workspace.

    Args:
        sandbox_id: Optional sandbox ID. If not provided, generates one.

    Returns:
        Path to the created workspace directory.
    """
    if sandbox_id is None:
        sandbox_id = generate_id("sbx")

    sandbox_root = get_sandbox_root()
    workspace_path = sandbox_root / sandbox_id

    # Create the workspace directory
    workspace_path.mkdir(parents=True, exist_ok=True)

    return workspace_path


def cleanup_sandbox_workspace(workspace_path: Path) -> bool:
    """Remove a sandbox workspace directory.

    Args:
        workspace_path: Path to the workspace to clean up.

    Returns:
        True if cleanup succeeded, False otherwise.
    """
    try:
        if workspace_path.exists():
            import shutil

            shutil.rmtree(workspace_path)
        return True
    except Exception:
        return False
