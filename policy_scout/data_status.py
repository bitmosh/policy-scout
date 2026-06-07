"""Local data status visibility for Policy Scout."""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional


def get_data_root() -> Path:
    """Get the default data root directory."""
    return Path.home() / ".local" / "share" / "policy-scout"


def normalize_path_for_human(path: Path) -> str:
    """Normalize path for human output, replacing home with ~."""
    try:
        home = Path.home()
        if path.is_relative_to(home):
            return "~" / path.relative_to(home)
        return str(path)
    except ValueError:
        return str(path)


def get_path_info(
    default_path: Path,
    env_var: Optional[str],
    is_file: bool = False,
) -> Dict[str, Any]:
    """Get path information including existence and override status.

    Args:
        default_path: Default path for this data location
        env_var: Environment variable name that can override the path
        is_file: True if this is a file path, False if directory

    Returns:
        Dict with path, exists, override_env, and normalized_path for human output
    """
    # Check for env override
    override_path = None
    if env_var and env_var in os.environ:
        override_path = Path(os.environ[env_var])
        actual_path = override_path
    else:
        actual_path = default_path

    # Check existence (read-only, no creation)
    exists = actual_path.exists()

    return {
        "path": str(actual_path),
        "normalized_path": normalize_path_for_human(actual_path),
        "exists": exists,
        "override_env": env_var,
        "is_file": is_file,
    }


def count_directory_items(path: Path) -> int:
    """Count items in a directory safely.

    Args:
        path: Directory path to count

    Returns:
        Number of items, or 0 if path doesn't exist or isn't a directory
    """
    if not path.exists() or not path.is_dir():
        return 0
    try:
        return len([item for item in path.iterdir() if item.name != ".gitkeep"])
    except (PermissionError, OSError):
        return 0


def count_jsonl_lines(path: Path) -> int:
    """Count lines in a JSONL file safely.

    Args:
        path: Path to JSONL file

    Returns:
        Number of lines, or 0 if file doesn't exist
    """
    if not path.exists() or not path.is_file():
        return 0
    try:
        with open(path, "r") as f:
            return sum(1 for line in f if line.strip())
    except (PermissionError, OSError):
        return 0


def count_audit_events(db_path: Path) -> int:
    """Count audit events in SQLite database directly.

    Args:
        db_path: Path to SQLite database

    Returns:
        Number of events, or 0 if database doesn't exist or can't be read
    """
    if not db_path.exists() or not db_path.is_file():
        return 0
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
            return cursor.fetchone()[0]
    except (sqlite3.Error, PermissionError, OSError):
        return 0


def get_data_status() -> Dict[str, Any]:
    """Get comprehensive data status for Policy Scout.

    Returns:
        Dict with data_root, paths, and counts
    """
    data_root = get_data_root()

    # Define all paths with their env overrides
    paths = {}

    # Audit DB
    paths["audit_db"] = get_path_info(
        default_path=data_root / "audit.db",
        env_var="POLICY_SCOUT_AUDIT_DB_PATH",
        is_file=True,
    )

    # Audit JSONL
    paths["audit_jsonl"] = get_path_info(
        default_path=data_root / "audit.jsonl",
        env_var="POLICY_SCOUT_AUDIT_PATH",
        is_file=True,
    )

    # Approvals
    paths["approvals"] = get_path_info(
        default_path=data_root / "approvals.jsonl",
        env_var="POLICY_SCOUT_APPROVAL_PATH",
        is_file=True,
    )

    # Reports
    paths["reports"] = get_path_info(
        default_path=data_root / "reports",
        env_var="POLICY_SCOUT_REPORT_ROOT",
        is_file=False,
    )

    # Sandbox
    paths["sandbox"] = get_path_info(
        default_path=data_root / "sandboxes",
        env_var="POLICY_SCOUT_SANDBOX_ROOT",
        is_file=False,
    )

    # Demo (no env override)
    paths["demo"] = get_path_info(
        default_path=data_root / "demo",
        env_var=None,
        is_file=False,
    )

    # Migration
    paths["migration"] = get_path_info(
        default_path=data_root / "migrations",
        env_var="POLICY_SCOUT_MIGRATION_ROOT",
        is_file=False,
    )

    # Backup
    paths["backup"] = get_path_info(
        default_path=data_root / "backups",
        env_var="POLICY_SCOUT_BACKUP_ROOT",
        is_file=False,
    )

    # Count items where paths exist
    counts = {}

    # Reports
    if paths["reports"]["exists"]:
        report_path = Path(paths["reports"]["path"])
        counts["reports"] = count_directory_items(report_path)
    else:
        counts["reports"] = 0

    # Sandbox results
    if paths["sandbox"]["exists"]:
        sandbox_path = Path(paths["sandbox"]["path"])
        counts["sandbox_results"] = count_directory_items(sandbox_path)
    else:
        counts["sandbox_results"] = 0

    # Demo workspaces
    if paths["demo"]["exists"]:
        demo_path = Path(paths["demo"]["path"])
        counts["demo_workspaces"] = count_directory_items(demo_path)
    else:
        counts["demo_workspaces"] = 0

    # Approvals
    if paths["approvals"]["exists"]:
        approval_path = Path(paths["approvals"]["path"])
        counts["approvals"] = count_jsonl_lines(approval_path)
    else:
        counts["approvals"] = 0

    # Audit events
    if paths["audit_db"]["exists"]:
        db_path = Path(paths["audit_db"]["path"])
        counts["audit_events"] = count_audit_events(db_path)
    else:
        counts["audit_events"] = 0

    # Migrations
    if paths["migration"]["exists"]:
        migration_path = Path(paths["migration"]["path"])
        counts["migrations"] = count_directory_items(migration_path)
    else:
        counts["migrations"] = 0

    # Backups
    if paths["backup"]["exists"]:
        backup_path = Path(paths["backup"]["path"])
        counts["backups"] = count_directory_items(backup_path)
    else:
        counts["backups"] = 0

    return {
        "data_root": str(data_root),
        "data_root_normalized": normalize_path_for_human(data_root),
        "paths": paths,
        "counts": counts,
    }


def format_data_status_human(status: Dict[str, Any]) -> str:
    """Format data status for human-readable output.

    Args:
        status: Data status dict from get_data_status()

    Returns:
        Formatted human-readable string
    """
    lines = []
    lines.append("Policy Scout Data Status")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Data Root: {status['data_root_normalized']}")
    lines.append("")

    lines.append("Paths:")
    lines.append("-" * 50)

    for key, info in status["paths"].items():
        status_marker = "✓" if info["exists"] else "○"
        lines.append(f"{status_marker} {key}: {info['normalized_path']}")
        if info["override_env"]:
            lines.append(f"  Override env: {info['override_env']}")

    lines.append("")

    lines.append("Counts:")
    lines.append("-" * 50)

    for key, count in status["counts"].items():
        lines.append(f"{key}: {count}")

    lines.append("")

    return "\n".join(lines)


def format_data_status_json(status: Dict[str, Any]) -> str:
    """Format data status for JSON output.

    Args:
        status: Data status dict from get_data_status()

    Returns:
        JSON string
    """
    import json

    # Build JSON output with absolute paths
    output = {
        "data_root": status["data_root"],
        "paths": {},
        "counts": status["counts"],
    }

    for key, info in status["paths"].items():
        output["paths"][key] = {
            "path": info["path"],
            "exists": info["exists"],
            "override_env": info["override_env"],
        }

    return json.dumps(output, indent=2)
