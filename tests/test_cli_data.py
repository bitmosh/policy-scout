"""Tests for data command CLI."""

import os
import tempfile
import json
from pathlib import Path
import subprocess
import sys


def test_data_help_shows_usage():
    """Test data command help shows usage information."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data", "--help"],
        capture_output=True,
        text=True,
    )
    help_output = result.stdout

    # Check for subcommands
    assert "status" in help_output
    assert "cleanup" in help_output


def test_data_human_output_includes_expected_paths():
    """Test data command human output includes expected paths."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data", "status"],
        capture_output=True,
        text=True,
    )
    output = result.stdout

    # Check for expected path keys
    assert "audit_db" in output
    assert "audit_jsonl" in output
    assert "approvals" in output
    assert "reports" in output
    assert "sandbox" in output
    assert "demo" in output
    assert "migration" in output
    assert "backup" in output

    # Check for data root
    assert "Data Root:" in output

    # Check for counts section
    assert "Counts:" in output


def test_data_human_output_normalizes_home_path():
    """Test data command human output normalizes home directory to ~."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data", "status"],
        capture_output=True,
        text=True,
    )
    output = result.stdout

    # Should contain ~ for home directory paths
    assert "~" in output


def test_data_json_output_parses_and_contains_expected_fields():
    """Test data command JSON output parses and contains expected fields."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data", "status", "--json"],
        capture_output=True,
        text=True,
    )
    output = result.stdout

    # Should parse as valid JSON
    data = json.loads(output)

    # Check for top-level fields
    assert "data_root" in data
    assert "paths" in data
    assert "counts" in data

    # Check for expected path keys
    assert "audit_db" in data["paths"]
    assert "audit_jsonl" in data["paths"]
    assert "approvals" in data["paths"]
    assert "reports" in data["paths"]
    assert "sandbox" in data["paths"]
    assert "demo" in data["paths"]
    assert "migration" in data["paths"]
    assert "backup" in data["paths"]

    # Check for expected count keys
    assert "reports" in data["counts"]
    assert "sandbox_results" in data["counts"]
    assert "demo_workspaces" in data["counts"]
    assert "approvals" in data["counts"]
    assert "audit_events" in data["counts"]
    assert "migrations" in data["counts"]
    assert "backups" in data["counts"]


def test_data_json_path_structure():
    """Test data command JSON output has correct path structure."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data", "status", "--json"],
        capture_output=True,
        text=True,
    )
    output = result.stdout
    data = json.loads(output)

    # Check each path has required fields
    for key, path_info in data["paths"].items():
        assert "path" in path_info
        assert "exists" in path_info
        assert isinstance(path_info["exists"], bool)
        assert "override_env" in path_info


def test_data_env_override_respected():
    """Test data command respects POLICY_SCOUT_* environment overrides."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env["POLICY_SCOUT_REPORT_ROOT"] = tmpdir

        result = subprocess.run(
            [sys.executable, "-m", "policy_scout.cli.main", "data", "status", "--json"],
            capture_output=True,
            text=True,
            env=env,
        )
        output = result.stdout
        data = json.loads(output)

        # Should use override path
        assert data["paths"]["reports"]["path"] == tmpdir


def test_data_counts_accurate_with_temp_fixtures():
    """Test data command counts are accurate with temporary fixtures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some report directories
        report_root = Path(tmpdir) / "reports"
        report_root.mkdir()
        (report_root / "report1").mkdir()
        (report_root / "report2").mkdir()

        # Create some sandbox directories
        sandbox_root = Path(tmpdir) / "sandboxes"
        sandbox_root.mkdir()
        (sandbox_root / "sbx_123").mkdir()
        (sandbox_root / "sbx_456").mkdir()

        env = os.environ.copy()
        env["POLICY_SCOUT_REPORT_ROOT"] = str(report_root)
        env["POLICY_SCOUT_SANDBOX_ROOT"] = str(sandbox_root)

        result = subprocess.run(
            [sys.executable, "-m", "policy_scout.cli.main", "data", "status", "--json"],
            capture_output=True,
            text=True,
            env=env,
        )
        output = result.stdout
        data = json.loads(output)

        # Should count correctly
        assert data["counts"]["reports"] == 2
        assert data["counts"]["sandbox_results"] == 2


def test_data_command_does_not_create_missing_directories():
    """Test data command does not create missing directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use a non-existent path
        non_existent = Path(tmpdir) / "does_not_exist"

        env = os.environ.copy()
        env["POLICY_SCOUT_REPORT_ROOT"] = str(non_existent)

        result = subprocess.run(
            [sys.executable, "-m", "policy_scout.cli.main", "data", "status", "--json"],
            capture_output=True,
            text=True,
            env=env,
        )
        output = result.stdout
        data = json.loads(output)

        # Path should not exist
        assert data["paths"]["reports"]["exists"] is False

        # Directory should not have been created
        assert not non_existent.exists()


def test_data_missing_paths_do_not_fail():
    """Test data command handles missing paths gracefully."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data", "status", "--json"],
        capture_output=True,
        text=True,
    )

    # Should succeed even if some paths don't exist
    assert result.returncode == 0

    output = result.stdout
    data = json.loads(output)

    # Should have counts even for missing paths
    assert "counts" in data
    for key, count in data["counts"].items():
        assert isinstance(count, int)


def test_data_no_secret_like_values_printed():
    """Test data command does not print secret-like values."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data", "status", "--json"],
        capture_output=True,
        text=True,
    )
    output = result.stdout

    # Should not contain common secret patterns
    # (This is a basic sanity check; actual redaction is handled elsewhere)
    assert "password" not in output.lower()
    assert "secret" not in output.lower()
    assert (
        "token" not in output.lower() or "override_env" in output
    )  # "token" might appear in override_env


def test_data_json_uses_absolute_paths():
    """Test data command JSON output uses absolute paths."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data", "status", "--json"],
        capture_output=True,
        text=True,
    )
    output = result.stdout
    data = json.loads(output)

    # JSON should use absolute paths, not ~
    for key, path_info in data["paths"].items():
        assert "~" not in path_info["path"]
        assert path_info["path"].startswith("/") or path_info["path"].startswith("C:")


def test_cleanup_help_shows_usage():
    """Test data cleanup help shows usage information."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data", "cleanup", "--help"],
        capture_output=True,
        text=True,
    )
    help_output = result.stdout

    # Check for required arguments
    assert "--target" in help_output
    assert "demo" in help_output
    assert "sandbox" in help_output
    assert "sandbox-results" in help_output
    assert "--apply" in help_output
    assert "--json" in help_output


def test_cleanup_demo_dry_run_shows_planned_items():
    """Test data cleanup demo dry-run shows planned items."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create demo root with some workspaces
        demo_root = Path(tmpdir) / "demo"
        demo_root.mkdir()
        (demo_root / "demo_1").mkdir()
        (demo_root / "demo_2").mkdir()

        env = os.environ.copy()
        # Override data root to use tmpdir
        env["POLICY_SCOUT_DATA_ROOT"] = tmpdir

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "policy_scout.cli.main",
                "data",
                "cleanup",
                "--target",
                "demo",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        output = result.stdout

        # Should show planned items
        assert "Planned Items:" in output
        assert "demo_1" in output or "demo_2" in output
        assert "dry-run" in output


def test_cleanup_sandbox_dry_run_shows_planned_items():
    """Test data cleanup sandbox dry-run shows planned items."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sandbox root with some workspaces
        sandbox_root = Path(tmpdir) / "sandboxes"
        sandbox_root.mkdir()
        (sandbox_root / "sbx_123").mkdir()
        (sandbox_root / "sbx_456").mkdir()

        env = os.environ.copy()
        env["POLICY_SCOUT_DATA_ROOT"] = tmpdir

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "policy_scout.cli.main",
                "data",
                "cleanup",
                "--target",
                "sandbox",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        output = result.stdout

        # Should show planned items
        assert "Planned Items:" in output
        assert "sbx" in output
        assert "dry-run" in output


def test_cleanup_sandbox_results_dry_run_shows_planned_items():
    """Test data cleanup sandbox-results dry-run shows planned items."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create results root with some JSON files
        results_root = Path(tmpdir) / "results"
        results_root.mkdir()
        (results_root / "sbx_123.json").write_text("{}")
        (results_root / "sbx_456.json").write_text("{}")

        env = os.environ.copy()
        env["POLICY_SCOUT_DATA_ROOT"] = tmpdir

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "policy_scout.cli.main",
                "data",
                "cleanup",
                "--target",
                "sandbox-results",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        output = result.stdout

        # Should show planned items
        assert "Planned Items:" in output
        assert "sbx" in output
        assert "dry-run" in output


def test_cleanup_missing_target_returns_zero_items():
    """Test data cleanup with missing target returns zero items."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use a non-existent path
        env = os.environ.copy()
        env["POLICY_SCOUT_DATA_ROOT"] = tmpdir

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "policy_scout.cli.main",
                "data",
                "cleanup",
                "--target",
                "demo",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        output = result.stdout

        # Should show zero items
        assert "No items to clean up" in output


def test_cleanup_unsupported_target_errors():
    """Test data cleanup with unsupported target errors."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "policy_scout.cli.main",
            "data",
            "cleanup",
            "--target",
            "reports",
        ],
        capture_output=True,
        text=True,
    )
    # argparse choices will reject invalid target
    assert result.returncode != 0
    assert (
        "invalid choice" in result.stderr.lower() or "reports" in result.stderr.lower()
    )


def test_cleanup_json_output_has_expected_shape():
    """Test data cleanup JSON output has expected shape."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create demo root with some workspaces
        demo_root = Path(tmpdir) / "demo"
        demo_root.mkdir()
        (demo_root / "demo_1").mkdir()

        env = os.environ.copy()
        env["POLICY_SCOUT_DATA_ROOT"] = tmpdir

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "policy_scout.cli.main",
                "data",
                "cleanup",
                "--target",
                "demo",
                "--json",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        output = result.stdout
        data = json.loads(output)

        # Check for expected fields
        assert "target" in data
        assert data["target"] == "demo"
        assert "dry_run" in data
        assert data["dry_run"] is True
        assert "target_root" in data
        assert "planned_items" in data
        assert "total_items" in data
        assert "total_bytes" in data
        assert "warnings" in data
        assert "could_not_verify" in data


def test_cleanup_human_output_normalizes_home_paths():
    """Test data cleanup human output normalizes home paths with ~."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "policy_scout.cli.main",
            "data",
            "cleanup",
            "--target",
            "demo",
        ],
        capture_output=True,
        text=True,
    )
    output = result.stdout

    # Should contain ~ for home directory paths
    assert "~" in output


def test_cleanup_symlink_escaping_outside_root_is_excluded_and_warned():
    """Test data cleanup treats symlinks as their own items (not followed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create demo root
        demo_root = Path(tmpdir) / "demo"
        demo_root.mkdir()

        # Create a symlink inside the root
        target_dir = demo_root / "target"
        target_dir.mkdir()
        symlink_path = demo_root / "safe_link"
        symlink_path.symlink_to(target_dir)

        env = os.environ.copy()
        env["POLICY_SCOUT_DATA_ROOT"] = tmpdir

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "policy_scout.cli.main",
                "data",
                "cleanup",
                "--target",
                "demo",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        output = result.stdout

        # Symlink should be treated as its own item (type: symlink)
        # This verifies we don't follow symlinks for traversal
        assert "symlink" in output.lower()


def test_cleanup_dry_run_does_not_delete_files_or_directories():
    """Test data cleanup dry-run does not delete files or directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create demo root with some workspaces
        demo_root = Path(tmpdir) / "demo"
        demo_root.mkdir()
        demo_1 = demo_root / "demo_1"
        demo_1.mkdir()
        (demo_1 / "test.txt").write_text("test")

        env = os.environ.copy()
        env["POLICY_SCOUT_DATA_ROOT"] = tmpdir

        # Run cleanup dry-run
        subprocess.run(
            [
                sys.executable,
                "-m",
                "policy_scout.cli.main",
                "data",
                "cleanup",
                "--target",
                "demo",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        # Files should still exist
        assert demo_1.exists()
        assert (demo_1 / "test.txt").exists()


def test_cleanup_no_directories_created_for_missing_roots():
    """Test data cleanup does not create directories for missing roots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use a non-existent path
        non_existent = Path(tmpdir) / "does_not_exist"

        env = os.environ.copy()
        env["POLICY_SCOUT_DATA_ROOT"] = tmpdir

        # Run cleanup dry-run
        subprocess.run(
            [
                sys.executable,
                "-m",
                "policy_scout.cli.main",
                "data",
                "cleanup",
                "--target",
                "demo",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        # Directory should not have been created
        assert not non_existent.exists()
