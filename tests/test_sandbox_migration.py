# SPDX-License-Identifier: Apache-2.0
"""Tests for sandbox migration."""

import json
import os
import tempfile
from pathlib import Path
import pytest
from policy_scout.sandbox.models import SandboxResult, MigrationResult
from policy_scout.sandbox.migration import (
    plan_migration,
    execute_migration,
    save_migration_result,
    load_migration_result,
    get_migration_root,
    get_backup_root,
    validate_sandbox_id,
    validate_sandbox_result,
    validate_sandbox_workspace,
    validate_host_project_root,
    validate_migration_available,
    validate_findings,
    plan_migration_files,
    validate_migration_files,
    create_backups,
    migrate_files,
    MigrationBlockedError,
    MigrationValidationError,
    MIGRATION_FORBIDDEN,
)


@pytest.fixture
def temp_paths():
    """Set up temporary paths for migration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox_root = Path(tmpdir) / "sandboxes"
        migration_root = Path(tmpdir) / "migrations"
        backup_root = Path(tmpdir) / "backups"
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"

        sandbox_root.mkdir()
        migration_root.mkdir()
        backup_root.mkdir()
        host_root.mkdir()
        sandbox_workspace.mkdir()

        os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = str(sandbox_root)
        os.environ["POLICY_SCOUT_MIGRATION_ROOT"] = str(migration_root)
        os.environ["POLICY_SCOUT_BACKUP_ROOT"] = str(backup_root)

        yield {
            "sandbox_root": sandbox_root,
            "migration_root": migration_root,
            "backup_root": backup_root,
            "host_root": host_root,
            "sandbox_workspace": sandbox_workspace,
        }

        # Cleanup
        os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)
        os.environ.pop("POLICY_SCOUT_MIGRATION_ROOT", None)
        os.environ.pop("POLICY_SCOUT_BACKUP_ROOT", None)


def test_migration_id_starts_with_mig():
    """Test migration ID starts with mig_."""
    result = MigrationResult()
    assert result.migration_id.startswith("mig_")


def test_validate_sandbox_id():
    """Test sandbox ID validation."""
    # Valid ID
    validate_sandbox_id("sbx_123")

    # Invalid ID
    with pytest.raises(MigrationValidationError):
        validate_sandbox_id("invalid_id")


def test_validate_sandbox_result():
    """Test sandbox result validation."""
    # Valid result
    result = SandboxResult(sandbox_id="sbx_123")
    validate_sandbox_result(result)

    # None result
    with pytest.raises(MigrationValidationError):
        validate_sandbox_result(None)

    # Empty sandbox_id
    with pytest.raises(MigrationValidationError):
        validate_sandbox_result(SandboxResult(sandbox_id=""))


def test_validate_sandbox_workspace():
    """Test sandbox workspace validation."""
    # Valid workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        validate_sandbox_workspace(tmpdir)

    # Non-existent workspace
    with pytest.raises(MigrationValidationError):
        validate_sandbox_workspace("/nonexistent/path")

    # Empty workspace
    with pytest.raises(MigrationValidationError):
        validate_sandbox_workspace("")


def test_validate_host_project_root():
    """Test host project root validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host = Path(tmpdir) / "host"
        sandbox = Path(tmpdir) / "sandbox"
        host.mkdir()
        sandbox.mkdir()

        # Valid host root
        validate_host_project_root(str(host), str(sandbox))

        # Non-existent host root
        with pytest.raises(MigrationValidationError):
            validate_host_project_root("/nonexistent", str(sandbox))

        # Empty host root
        with pytest.raises(MigrationValidationError):
            validate_host_project_root("", str(sandbox))

        # Same as sandbox workspace
        with pytest.raises(MigrationValidationError):
            validate_host_project_root(str(sandbox), str(sandbox))


def test_validate_migration_available():
    """Test migration availability validation."""
    # Migration available
    result = SandboxResult(
        sandbox_id="sbx_123",
        migration_available=True,
        migration_requires_approval=True,
    )
    validate_migration_available(result)

    # Migration not available
    result.migration_available = False
    with pytest.raises(MigrationBlockedError):
        validate_migration_available(result)

    # Migration does not require approval
    result.migration_available = True
    result.migration_requires_approval = False
    with pytest.raises(MigrationBlockedError):
        validate_migration_available(result)


def test_validate_findings():
    """Test findings validation."""
    # No findings
    result = SandboxResult(sandbox_id="sbx_123", findings=[])
    validate_findings(result)

    # Low severity findings
    result.findings = [{"severity": "low", "description": "test"}]
    validate_findings(result)

    # High severity findings
    result.findings = [{"severity": "high", "description": "test"}]
    with pytest.raises(MigrationBlockedError):
        validate_findings(result)

    # Critical severity findings
    result.findings = [{"severity": "critical", "description": "test"}]
    with pytest.raises(MigrationBlockedError):
        validate_findings(result)


def test_plan_migration_files(temp_paths):
    """Test planning migration files."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create package.json in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "test"}')

    # Create package-lock.json in sandbox
    (sandbox_workspace / "package-lock.json").write_text("{}")

    # Create node_modules in sandbox (should be skipped)
    (sandbox_workspace / "node_modules").mkdir()

    files_planned, files_skipped = plan_migration_files(
        str(sandbox_workspace), str(host_root)
    )

    assert "package.json" in files_planned
    assert "package-lock.json" in files_planned
    assert "node_modules" not in files_planned


def test_validate_migration_files():
    """Test migration file validation."""
    # Valid files
    validate_migration_files(["package.json", "package-lock.json"])

    # File not in allowlist
    with pytest.raises(MigrationValidationError):
        validate_migration_files(["arbitrary_file.txt"])

    # Forbidden file
    with pytest.raises(MigrationValidationError):
        validate_migration_files(["node_modules"])


def test_create_backups(temp_paths):
    """Test backup creation."""
    host_root = temp_paths["host_root"]
    backup_root = temp_paths["backup_root"]

    # Create package.json in host
    (host_root / "package.json").write_text('{"name": "old"}')

    backups = create_backups(str(host_root), ["package.json"], "mig_test")

    assert len(backups) == 1
    assert (backup_root / "mig_test" / "package.json").exists()
    assert (backup_root / "mig_test" / "package.json").read_text() == '{"name": "old"}'


def test_migrate_files(temp_paths):
    """Test file migration."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create package.json in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "new"}')

    migrated = migrate_files(str(sandbox_workspace), str(host_root), ["package.json"])

    assert "package.json" in migrated
    assert (host_root / "package.json").read_text() == '{"name": "new"}'


def test_plan_migration(temp_paths):
    """Test migration planning."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create package.json in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "test"}')

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = plan_migration(result)

    assert migration_result.sandbox_id == "sbx_123"
    assert "package.json" in migration_result.files_planned
    assert not migration_result.blocked
    assert migration_result.success


def test_plan_migration_blocked_by_findings(temp_paths):
    """Test migration blocked by high severity findings."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        migration_available=True,
        migration_requires_approval=True,
        findings=[{"severity": "high", "description": "test"}],
    )

    migration_result = plan_migration(result)

    assert migration_result.blocked
    assert len(migration_result.block_reasons) > 0


def test_execute_migration(temp_paths):
    """Test migration execution."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]
    backup_root = temp_paths["backup_root"]

    # Create package.json in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "new"}')

    # Create package.json in host
    (host_root / "package.json").write_text('{"name": "old"}')

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = execute_migration(result, dry_run=False)

    assert migration_result.success
    assert "package.json" in migration_result.files_migrated
    assert len(migration_result.backups_created) > 0
    assert (host_root / "package.json").read_text() == '{"name": "new"}'
    assert (backup_root / migration_result.migration_id / "package.json").exists()


def test_execute_migration_dry_run(temp_paths):
    """Test migration dry run."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create package.json in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "new"}')

    # Create package.json in host
    (host_root / "package.json").write_text('{"name": "old"}')

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = execute_migration(result, dry_run=True)

    assert migration_result.success
    assert "package.json" in migration_result.files_planned
    assert len(migration_result.files_migrated) == 0  # No files migrated in dry run
    assert (host_root / "package.json").read_text() == '{"name": "old"}'  # Unchanged


def test_save_and_load_migration_result(temp_paths):
    """Test saving and loading migration result."""
    result = MigrationResult(
        sandbox_id="sbx_123",
        files_planned=["package.json"],
        files_migrated=["package.json"],
        success=True,
    )

    save_migration_result(result)

    loaded = load_migration_result(result.migration_id)

    assert loaded is not None
    assert loaded.migration_id == result.migration_id
    assert loaded.sandbox_id == "sbx_123"
    assert loaded.success


def test_migration_never_copies_node_modules(temp_paths):
    """Test migration never copies node_modules."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create node_modules in sandbox
    (sandbox_workspace / "node_modules").mkdir()
    (sandbox_workspace / "node_modules" / "test").write_text("test")

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = plan_migration(result)

    assert "node_modules" not in migration_result.files_planned


def test_migration_never_copies_npmrc(temp_paths):
    """Test migration never copies .npmrc."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create .npmrc in sandbox
    (sandbox_workspace / ".npmrc").write_text("test")

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = plan_migration(result)

    assert ".npmrc" not in migration_result.files_planned


def test_migration_never_copies_arbitrary_files(temp_paths):
    """Test migration never copies arbitrary generated files."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create arbitrary file in sandbox
    (sandbox_workspace / "arbitrary.txt").write_text("test")

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = plan_migration(result)

    assert "arbitrary.txt" not in migration_result.files_planned


def test_migration_creates_backups_before_overwriting(temp_paths):
    """Test migration creates backups before overwriting."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]
    backup_root = temp_paths["backup_root"]

    # Create package.json in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "new"}')

    # Create package.json in host
    (host_root / "package.json").write_text('{"name": "old"}')

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = execute_migration(result, dry_run=False)

    assert migration_result.success
    assert len(migration_result.backups_created) > 0
    assert (backup_root / migration_result.migration_id / "package.json").exists()
    assert (
        backup_root / migration_result.migration_id / "package.json"
    ).read_text() == '{"name": "old"}'


def test_migration_allows_low_info_findings(temp_paths):
    """Test migration allows when only low/info findings exist."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    (sandbox_workspace / "package.json").write_text('{"name": "test"}')

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        migration_available=True,
        migration_requires_approval=True,
        findings=[
            {"severity": "info", "description": "test"},
            {"severity": "low", "description": "test"},
        ],
    )

    migration_result = plan_migration(result)

    assert not migration_result.blocked
    assert migration_result.success


def test_migration_result_json_is_written(temp_paths):
    """Test migration result JSON is written."""
    result = MigrationResult(
        sandbox_id="sbx_123",
        success=True,
    )

    save_migration_result(result)

    migration_file = temp_paths["migration_root"] / f"{result.migration_id}.json"
    assert migration_file.exists()

    with open(migration_file, "r") as f:
        data = json.load(f)

    assert data["migration_id"] == result.migration_id
    assert data["sandbox_id"] == "sbx_123"


def test_migration_uses_temp_override_paths(temp_paths):
    """Test migration uses temp override paths."""
    # This is tested by the temp_paths fixture which sets env vars
    migration_root = get_migration_root()
    backup_root = get_backup_root()

    assert migration_root == temp_paths["migration_root"]
    assert backup_root == temp_paths["backup_root"]


def test_migration_allowlist():
    """Test migration allowlist contains expected files."""
    from policy_scout.sandbox.package_manager import get_migration_allowlist
    from policy_scout.sandbox.migration import COMMON_MIGRATION_ALLOWLIST

    assert "package.json" in COMMON_MIGRATION_ALLOWLIST
    assert "package.json" in get_migration_allowlist("npm")
    assert "package-lock.json" in get_migration_allowlist("npm")
    assert "npm-shrinkwrap.json" in get_migration_allowlist("npm")
    assert "pnpm-lock.yaml" in get_migration_allowlist("pnpm")
    assert "yarn.lock" in get_migration_allowlist("yarn")
    assert "bun.lockb" in get_migration_allowlist("bun")


def test_migration_forbidden():
    """Test migration forbidden list contains expected files."""
    assert "node_modules" in MIGRATION_FORBIDDEN
    assert ".npmrc" in MIGRATION_FORBIDDEN
    assert ".pnpmrc" in MIGRATION_FORBIDDEN
    assert ".yarnrc.yml" in MIGRATION_FORBIDDEN
    assert "bunfig.toml" in MIGRATION_FORBIDDEN
    assert ".env" in MIGRATION_FORBIDDEN


def test_migration_allowlist_permits_correct_lockfile_for_npm(temp_paths):
    """Test migration allowlist permits correct lockfile for npm."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create package.json and package-lock.json in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "test"}')
    (sandbox_workspace / "package-lock.json").write_text("{}")

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        package_manager="npm",
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = plan_migration(result)

    assert "package.json" in migration_result.files_planned
    assert "package-lock.json" in migration_result.files_planned


def test_migration_allowlist_permits_correct_lockfile_for_pnpm(temp_paths):
    """Test migration allowlist permits correct lockfile for pnpm."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create package.json and pnpm-lock.yaml in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "test"}')
    (sandbox_workspace / "pnpm-lock.yaml").write_text("{}")

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        package_manager="pnpm",
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = plan_migration(result)

    assert "package.json" in migration_result.files_planned
    assert "pnpm-lock.yaml" in migration_result.files_planned


def test_migration_allowlist_permits_correct_lockfile_for_yarn(temp_paths):
    """Test migration allowlist permits correct lockfile for yarn."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create package.json and yarn.lock in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "test"}')
    (sandbox_workspace / "yarn.lock").write_text("{}")

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        package_manager="yarn",
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = plan_migration(result)

    assert "package.json" in migration_result.files_planned
    assert "yarn.lock" in migration_result.files_planned


def test_migration_allowlist_permits_correct_lockfile_for_bun(temp_paths):
    """Test migration allowlist permits correct lockfile for bun."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create package.json and bun.lockb in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "test"}')
    (sandbox_workspace / "bun.lockb").write_text("{}")

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        package_manager="bun",
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = plan_migration(result)

    assert "package.json" in migration_result.files_planned
    assert "bun.lockb" in migration_result.files_planned


def test_migration_blocks_wrong_lockfile_for_package_manager(temp_paths):
    """Test migration blocks wrong lockfile for package manager."""
    sandbox_workspace = temp_paths["sandbox_workspace"]
    host_root = temp_paths["host_root"]

    # Create package.json and pnpm-lock.yaml in sandbox
    (sandbox_workspace / "package.json").write_text('{"name": "test"}')
    (sandbox_workspace / "pnpm-lock.yaml").write_text("{}")

    result = SandboxResult(
        sandbox_id="sbx_123",
        temp_workspace=str(sandbox_workspace),
        host_project_root=str(host_root),
        package_manager="npm",  # Wrong package manager for lockfile
        migration_available=True,
        migration_requires_approval=True,
        findings=[],
    )

    migration_result = plan_migration(result)

    # pnpm-lock.yaml should not be planned for npm
    assert "pnpm-lock.yaml" not in migration_result.files_planned
    assert "package.json" in migration_result.files_planned
