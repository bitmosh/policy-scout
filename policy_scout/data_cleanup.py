# SPDX-License-Identifier: Apache-2.0
"""Data cleanup for Policy Scout — plan (dry-run) and execute (--apply)."""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional


def get_data_root() -> Path:
    """Get the default data root directory."""
    env_override = os.environ.get("POLICY_SCOUT_DATA_ROOT")
    if env_override:
        return Path(env_override)
    return Path.home() / ".local" / "share" / "policy-scout"


def normalize_path_for_human(path: Path) -> str:
    """Normalize path for human output, replacing home with ~."""
    try:
        home = Path.home()
        if path.is_relative_to(home):
            return str(Path("~") / path.relative_to(home))
        return str(path)
    except ValueError:
        return str(path)


def get_target_root(target: str) -> Optional[Path]:
    """Get the root directory for a given cleanup target.

    Args:
        target: Target name (demo, sandbox, sandbox-results)

    Returns:
        Path to target root, or None if target is unsupported
    """
    data_root = get_data_root()

    if target == "demo":
        return data_root / "demo"
    elif target == "sandbox":
        return data_root / "sandboxes"
    elif target == "sandbox-results":
        # Results are stored at data_root/results (sibling to sandboxes)
        return data_root / "results"
    else:
        return None


def validate_path_under_root(path: Path, root: Path) -> bool:
    """Validate that a resolved path is under the expected root.

    Args:
        path: Path to validate
        root: Expected root directory

    Returns:
        True if path is under root, False otherwise
    """
    try:
        resolved = path.resolve()
        root_resolved = root.resolve()
        resolved.relative_to(root_resolved)
        return True
    except ValueError:
        return False


def get_item_size(path: Path) -> int:
    """Get size of a file or directory without following symlinks.

    Args:
        path: Path to item

    Returns:
        Size in bytes, or 0 if cannot determine
    """
    try:
        # Use lstat to get symlink itself, not target
        stat = path.lstat()
        if path.is_symlink():
            # Symlink size is the size of the link itself
            return stat.st_size
        elif path.is_file():
            return stat.st_size
        elif path.is_dir():
            # Sum directory contents without following symlinks
            total = 0
            for item in path.iterdir():
                total += get_item_size(item)
            return total
        else:
            return 0
    except (PermissionError, OSError):
        return 0


def plan_cleanup(target: str) -> Dict[str, Any]:
    """Plan cleanup for a target (dry-run only, no deletion).

    Args:
        target: Target name (demo, sandbox, sandbox-results)

    Returns:
        Dict with cleanup plan including planned_items, warnings, etc.
    """
    target_root = get_target_root(target)

    if target_root is None:
        return {
            "target": target,
            "dry_run": True,
            "error": f"Unsupported target: {target}",
            "supported_targets": ["demo", "sandbox", "sandbox-results"],
        }

    # If target root doesn't exist, return zero items
    if not target_root.exists():
        return {
            "target": target,
            "dry_run": True,
            "target_root": str(target_root),
            "planned_items": [],
            "total_items": 0,
            "total_bytes": 0,
            "warnings": [],
            "could_not_verify": [],
        }

    # Validate target root is under data root
    data_root = get_data_root()
    if not validate_path_under_root(target_root, data_root):
        return {
            "target": target,
            "dry_run": True,
            "error": f"Target root {target_root} is not under data root {data_root}",
        }

    # Plan items
    planned_items = []
    warnings = []
    could_not_verify = []

    try:
        for item in target_root.iterdir():
            # Skip .gitkeep
            if item.name == ".gitkeep":
                continue

            # Check if item is a symlink that escapes root
            if item.is_symlink():
                if not validate_path_under_root(item, data_root):
                    # Symlink escapes root, exclude and warn
                    warnings.append(
                        f"Symlink {item} resolves outside data root, excluded"
                    )
                    could_not_verify.append(str(item))
                    continue

            # Add to planned items
            size = get_item_size(item)
            item_type = (
                "symlink"
                if item.is_symlink()
                else ("directory" if item.is_dir() else "file")
            )

            planned_items.append(
                {
                    "path": str(item),
                    "type": item_type,
                    "size_bytes": size,
                }
            )
    except (PermissionError, OSError) as e:
        warnings.append(f"Cannot read target root: {e}")

    total_bytes = sum(item["size_bytes"] for item in planned_items)

    return {
        "target": target,
        "dry_run": True,
        "target_root": str(target_root),
        "planned_items": planned_items,
        "total_items": len(planned_items),
        "total_bytes": total_bytes,
        "warnings": warnings,
        "could_not_verify": could_not_verify,
    }


def format_cleanup_plan_human(plan: Dict[str, Any]) -> str:
    """Format cleanup plan for human-readable output.

    Args:
        plan: Cleanup plan dict from plan_cleanup()

    Returns:
        Formatted human-readable string
    """
    lines = []

    if "error" in plan:
        lines.append(f"Error: {plan['error']}")
        if "supported_targets" in plan:
            lines.append(f"Supported targets: {', '.join(plan['supported_targets'])}")
        return "\n".join(lines)

    lines.append("Policy Scout Data Cleanup Plan")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Target: {plan['target']}")
    lines.append("Mode: dry-run (no deletion)")
    lines.append(f"Target Root: {normalize_path_for_human(Path(plan['target_root']))}")
    lines.append("")

    if plan["total_items"] == 0:
        lines.append("No items to clean up.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"Planned Items: {plan['total_items']}")
    lines.append(f"Total Size: {plan['total_bytes']:,} bytes")
    lines.append("")

    lines.append("Items to remove:")
    lines.append("-" * 50)

    for item in plan["planned_items"]:
        path_display = normalize_path_for_human(Path(item["path"]))
        lines.append(f"{item['type']}: {path_display} ({item['size_bytes']:,} bytes)")

    if plan["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        lines.append("-" * 50)
        for warning in plan["warnings"]:
            lines.append(f"  {warning}")

    if plan["could_not_verify"]:
        lines.append("")
        lines.append("Could Not Verify:")
        lines.append("-" * 50)
        for path in plan["could_not_verify"]:
            lines.append(f"  {path}")

    lines.append("")
    lines.append("This is a dry-run. No files will be deleted.")
    lines.append("")

    return "\n".join(lines)


def format_cleanup_plan_json(plan: Dict[str, Any]) -> str:
    """Format cleanup plan for JSON output.

    Args:
        plan: Cleanup plan dict from plan_cleanup()

    Returns:
        JSON string
    """
    import json

    # Build JSON output with absolute paths
    output = {
        "target": plan["target"],
        "dry_run": plan["dry_run"],
    }

    if "error" in plan:
        output["error"] = plan["error"]
        if "supported_targets" in plan:
            output["supported_targets"] = plan["supported_targets"]
    else:
        output["target_root"] = plan["target_root"]
        output["planned_items"] = plan["planned_items"]
        output["total_items"] = plan["total_items"]
        output["total_bytes"] = plan["total_bytes"]
        output["warnings"] = plan["warnings"]
        output["could_not_verify"] = plan["could_not_verify"]

    return json.dumps(output, indent=2)


def execute_cleanup(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a cleanup plan, deleting all planned items.

    Safety invariants:
    - Every path is re-validated under data root at execution time.
    - Symlinks that escape the data root are skipped.
    - Only items listed in plan["planned_items"] are touched.
    - Returns a result dict regardless of individual item errors.
    """
    if plan.get("dry_run", True):
        return {
            "target": plan.get("target", ""),
            "executed": False,
            "error": "Cannot execute: plan is marked dry_run=True",
            "deleted_items": [],
            "failed_items": [],
            "deleted_count": 0,
            "failed_count": 0,
            "freed_bytes": 0,
        }

    if "error" in plan:
        return {
            "target": plan.get("target", ""),
            "executed": False,
            "error": plan["error"],
            "deleted_items": [],
            "failed_items": [],
            "deleted_count": 0,
            "failed_count": 0,
            "freed_bytes": 0,
        }

    data_root = get_data_root()
    target_root_str = plan.get("target_root", "")
    if not target_root_str:
        return {
            "target": plan.get("target", ""),
            "executed": False,
            "error": "Plan has no target_root",
            "deleted_items": [],
            "failed_items": [],
            "deleted_count": 0,
            "failed_count": 0,
            "freed_bytes": 0,
        }

    deleted_items: List[Dict[str, Any]] = []
    failed_items: List[Dict[str, Any]] = []
    freed_bytes = 0

    for item in plan.get("planned_items", []):
        item_path = Path(item["path"])

        # Re-validate under data root at execution time (TOCTOU defence)
        if not validate_path_under_root(item_path, data_root):
            failed_items.append({
                "path": str(item_path),
                "reason": "Path escaped data root — skipped",
            })
            continue

        # Skip symlinks that resolve outside data root
        if item_path.is_symlink() and not validate_path_under_root(item_path, data_root):
            failed_items.append({
                "path": str(item_path),
                "reason": "Symlink resolves outside data root — skipped",
            })
            continue

        try:
            size = item.get("size_bytes", 0)
            if item_path.is_symlink() or item_path.is_file():
                item_path.unlink()
            elif item_path.is_dir():
                shutil.rmtree(item_path)
            else:
                # Already gone — count as success
                pass
            deleted_items.append({"path": str(item_path), "size_bytes": size})
            freed_bytes += size
        except (PermissionError, OSError) as exc:
            failed_items.append({"path": str(item_path), "reason": str(exc)})

    return {
        "target": plan.get("target", ""),
        "executed": True,
        "target_root": target_root_str,
        "deleted_items": deleted_items,
        "failed_items": failed_items,
        "deleted_count": len(deleted_items),
        "failed_count": len(failed_items),
        "freed_bytes": freed_bytes,
    }


def format_cleanup_result_human(result: Dict[str, Any]) -> str:
    lines = ["Policy Scout Data Cleanup Result", "=" * 50, ""]
    lines.append(f"Target: {result['target']}")

    if not result.get("executed"):
        lines.append(f"Error: {result.get('error', 'unknown')}")
        return "\n".join(lines)

    lines.append(
        f"Target Root: {normalize_path_for_human(Path(result['target_root']))}"
    )
    lines.append("")

    if result["deleted_count"] == 0 and result["failed_count"] == 0:
        lines.append("Nothing to delete.")
    else:
        lines.append(f"Deleted: {result['deleted_count']} item(s), "
                     f"{result['freed_bytes']:,} bytes freed")
        if result["failed_count"]:
            lines.append(f"Failed:  {result['failed_count']} item(s)")

    if result["deleted_items"]:
        lines += ["", "Deleted:"]
        for item in result["deleted_items"]:
            lines.append(
                f"  {normalize_path_for_human(Path(item['path']))} "
                f"({item['size_bytes']:,} bytes)"
            )

    if result["failed_items"]:
        lines += ["", "Errors:"]
        for item in result["failed_items"]:
            lines.append(
                f"  {normalize_path_for_human(Path(item['path']))}: {item['reason']}"
            )

    lines.append("")
    return "\n".join(lines)


def format_cleanup_result_json(result: Dict[str, Any]) -> str:
    import json
    return json.dumps(result, indent=2)
