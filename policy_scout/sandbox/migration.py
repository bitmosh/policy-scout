"""Sandbox migration logic."""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from .models import SandboxResult, MigrationResult
from .package_manager import get_migration_allowlist
from ..core.ids import utcnow_iso


# Common allowed migration files
COMMON_MIGRATION_ALLOWLIST = [
    "package.json",
]

# Forbidden files
MIGRATION_FORBIDDEN = [
    "node_modules",
    ".npmrc",
    ".pnpmrc",
    ".yarnrc.yml",
    "bunfig.toml",
    ".env",
]


class MigrationBlockedError(Exception):
    """Raised when migration is blocked by safety validation."""

    pass


class MigrationValidationError(Exception):
    """Raised when migration validation fails."""

    pass


def get_migration_root() -> Path:
    """Get the migration root directory."""
    from os import environ

    if "POLICY_SCOUT_MIGRATION_ROOT" in environ:
        return Path(environ["POLICY_SCOUT_MIGRATION_ROOT"])
    default = Path.home() / ".local" / "share" / "policy-scout" / "migrations"
    default.mkdir(parents=True, exist_ok=True)
    return default


def get_backup_root() -> Path:
    """Get the backup root directory."""
    from os import environ

    if "POLICY_SCOUT_BACKUP_ROOT" in environ:
        return Path(environ["POLICY_SCOUT_BACKUP_ROOT"])
    default = Path.home() / ".local" / "share" / "policy-scout" / "backups"
    default.mkdir(parents=True, exist_ok=True)
    return default


def validate_sandbox_id(sandbox_id: str) -> None:
    """Validate sandbox ID format."""
    if not sandbox_id.startswith("sbx_"):
        raise MigrationValidationError(
            f"Invalid sandbox ID: {sandbox_id}. Must start with 'sbx_'."
        )


def validate_sandbox_result(sandbox_result: Optional[SandboxResult]) -> None:
    """Validate sandbox result exists and is valid."""
    if sandbox_result is None:
        raise MigrationValidationError("Sandbox result not found.")
    if not sandbox_result.sandbox_id:
        raise MigrationValidationError("Sandbox result has no sandbox_id.")


def validate_sandbox_workspace(sandbox_workspace: str) -> None:
    """Validate sandbox workspace exists."""
    if not sandbox_workspace:
        raise MigrationValidationError("Sandbox workspace path is empty.")
    if not os.path.exists(sandbox_workspace):
        raise MigrationValidationError(
            f"Sandbox workspace does not exist: {sandbox_workspace}"
        )


def validate_host_project_root(host_project_root: str, sandbox_workspace: str) -> None:
    """Validate host project root exists and is not the sandbox workspace."""
    if not host_project_root:
        raise MigrationValidationError(
            "Host project root was not recorded in sandbox result."
        )
    if not os.path.exists(host_project_root):
        raise MigrationValidationError(
            f"Host project root does not exist: {host_project_root}"
        )
    if os.path.abspath(host_project_root) == os.path.abspath(sandbox_workspace):
        raise MigrationValidationError(
            "Host project root cannot be the same as sandbox workspace."
        )


def validate_migration_available(sandbox_result: SandboxResult) -> None:
    """Validate migration is available and requires approval."""
    if not sandbox_result.migration_available:
        raise MigrationBlockedError(
            "Migration is not available for this sandbox result."
        )
    if not sandbox_result.migration_requires_approval:
        raise MigrationBlockedError(
            "Migration does not require approval (unexpected state)."
        )


def validate_findings(sandbox_result: SandboxResult) -> None:
    """Validate findings - block on high/critical severity."""
    for finding in sandbox_result.findings:
        severity = finding.get("severity", "info").lower()
        if severity in ["high", "critical"]:
            raise MigrationBlockedError(
                f"Migration blocked: finding with {severity} severity detected: {finding.get('description', 'unknown')}"
            )


def plan_migration_files(
    sandbox_workspace: str,
    host_project_root: str,
    package_manager: str = "npm",
) -> Tuple[List[str], List[str]]:
    """Plan which files to migrate."""
    files_planned = []
    files_skipped = []

    sandbox_path = Path(sandbox_workspace)
    host_path = Path(host_project_root)

    migration_allowlist = COMMON_MIGRATION_ALLOWLIST + get_migration_allowlist(
        package_manager
    )
    migration_allowlist = list(set(migration_allowlist))  # Remove duplicates

    for filename in migration_allowlist:
        source_file = sandbox_path / filename
        if source_file.exists():
            # Verify source is inside sandbox workspace
            if not str(source_file.resolve()).startswith(str(sandbox_path.resolve())):
                files_skipped.append(filename)
                continue

            # Verify destination would be inside host project root
            dest_file = host_path / filename
            if not str(dest_file.resolve()).startswith(str(host_path.resolve())):
                files_skipped.append(filename)
                continue

            files_planned.append(filename)

    return files_planned, files_skipped


def validate_migration_files(
    files_planned: List[str], package_manager: str = "npm"
) -> None:
    """Validate planned files are in allowlist and not forbidden."""
    migration_allowlist = COMMON_MIGRATION_ALLOWLIST + get_migration_allowlist(
        package_manager
    )
    migration_allowlist = list(set(migration_allowlist))  # Remove duplicates

    for filename in files_planned:
        if filename not in migration_allowlist:
            raise MigrationValidationError(f"File not in allowlist: {filename}")
        if filename in MIGRATION_FORBIDDEN:
            raise MigrationValidationError(f"File is forbidden: {filename}")


def create_backups(
    host_project_root: str,
    files_planned: List[str],
    migration_id: str,
) -> List[str]:
    """Create backups of host files before migration."""
    backup_root = get_backup_root()
    backup_dir = backup_root / migration_id
    backup_dir.mkdir(parents=True, exist_ok=True)

    backups_created = []
    host_path = Path(host_project_root)

    for filename in files_planned:
        source_file = host_path / filename
        if source_file.exists():
            backup_file = backup_dir / filename
            shutil.copy2(source_file, backup_file)
            backups_created.append(str(backup_file))

    return backups_created


def migrate_files(
    sandbox_workspace: str,
    host_project_root: str,
    files_planned: List[str],
) -> List[str]:
    """Copy files from sandbox to host."""
    files_migrated = []
    sandbox_path = Path(sandbox_workspace)
    host_path = Path(host_project_root)

    for filename in files_planned:
        source_file = sandbox_path / filename
        dest_file = host_path / filename

        if source_file.exists():
            shutil.copy2(source_file, dest_file)
            files_migrated.append(filename)

    return files_migrated


def plan_migration(
    sandbox_result: SandboxResult,
    dry_run: bool = False,
) -> MigrationResult:
    """Plan a sandbox migration without executing it."""
    migration_result = MigrationResult(
        sandbox_id=sandbox_result.sandbox_id,
        request_id=sandbox_result.request_id,
        host_project_root=sandbox_result.host_project_root,
        sandbox_workspace=sandbox_result.temp_workspace,
    )

    try:
        validate_sandbox_id(sandbox_result.sandbox_id)
        validate_sandbox_result(sandbox_result)
        validate_sandbox_workspace(sandbox_result.temp_workspace)
        validate_host_project_root(
            sandbox_result.host_project_root, sandbox_result.temp_workspace
        )
        validate_migration_available(sandbox_result)
        validate_findings(sandbox_result)

        files_planned, files_skipped = plan_migration_files(
            sandbox_result.temp_workspace,
            sandbox_result.host_project_root,
            sandbox_result.package_manager,
        )
        validate_migration_files(files_planned, sandbox_result.package_manager)

        migration_result.files_planned = files_planned
        migration_result.files_skipped = files_skipped
        migration_result.success = True

    except MigrationBlockedError as e:
        migration_result.blocked = True
        migration_result.block_reasons = [str(e)]
    except MigrationValidationError as e:
        migration_result.blocked = True
        migration_result.block_reasons = [str(e)]

    return migration_result


def execute_migration(
    sandbox_result: SandboxResult,
    dry_run: bool = False,
) -> MigrationResult:
    """Execute a sandbox migration."""
    migration_result = MigrationResult(
        sandbox_id=sandbox_result.sandbox_id,
        request_id=sandbox_result.request_id,
        host_project_root=sandbox_result.host_project_root,
        sandbox_workspace=sandbox_result.temp_workspace,
    )

    try:
        validate_sandbox_id(sandbox_result.sandbox_id)
        validate_sandbox_result(sandbox_result)
        validate_sandbox_workspace(sandbox_result.temp_workspace)
        validate_host_project_root(
            sandbox_result.host_project_root, sandbox_result.temp_workspace
        )
        validate_migration_available(sandbox_result)
        validate_findings(sandbox_result)

        files_planned, files_skipped = plan_migration_files(
            sandbox_result.temp_workspace,
            sandbox_result.host_project_root,
            sandbox_result.package_manager,
        )
        validate_migration_files(files_planned, sandbox_result.package_manager)

        migration_result.files_planned = files_planned
        migration_result.files_skipped = files_skipped

        if dry_run:
            migration_result.success = True
            return migration_result

        # Create backups
        backups_created = create_backups(
            sandbox_result.host_project_root,
            files_planned,
            migration_result.migration_id,
        )
        migration_result.backups_created = backups_created

        # Migrate files
        files_migrated = migrate_files(
            sandbox_result.temp_workspace,
            sandbox_result.host_project_root,
            files_planned,
        )
        migration_result.files_migrated = files_migrated

        migration_result.success = True

    except MigrationBlockedError as e:
        migration_result.blocked = True
        migration_result.block_reasons = [str(e)]
    except MigrationValidationError as e:
        migration_result.blocked = True
        migration_result.block_reasons = [str(e)]
    except Exception as e:
        migration_result.blocked = True
        migration_result.block_reasons = [f"Migration failed: {str(e)}"]

    migration_result.completed_at = utcnow_iso()
    return migration_result


def save_migration_result(migration_result: MigrationResult) -> None:
    """Save migration result to file."""
    migration_root = get_migration_root()
    migration_file = migration_root / f"{migration_result.migration_id}.json"
    import json

    with open(migration_file, "w") as f:
        json.dump(migration_result.to_dict(), f, indent=2)


def load_migration_result(migration_id: str) -> Optional[MigrationResult]:
    """Load migration result from file."""
    migration_root = get_migration_root()
    migration_file = migration_root / f"{migration_id}.json"
    if not migration_file.exists():
        return None
    import json

    with open(migration_file, "r") as f:
        data = json.load(f)
    return MigrationResult.from_dict(data)
