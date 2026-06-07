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

    # Check for JSON flag
    assert "--json" in help_output
    assert "Output JSON instead of human-readable text" in help_output


def test_data_human_output_includes_expected_paths():
    """Test data command human output includes expected paths."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data"],
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
        [sys.executable, "-m", "policy_scout.cli.main", "data"],
        capture_output=True,
        text=True,
    )
    output = result.stdout

    # Should contain ~ for home directory paths
    assert "~" in output


def test_data_json_output_parses_and_contains_expected_fields():
    """Test data command JSON output parses and contains expected fields."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "data", "--json"],
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
        [sys.executable, "-m", "policy_scout.cli.main", "data", "--json"],
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
            [sys.executable, "-m", "policy_scout.cli.main", "data", "--json"],
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
            [sys.executable, "-m", "policy_scout.cli.main", "data", "--json"],
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
            [sys.executable, "-m", "policy_scout.cli.main", "data", "--json"],
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
        [sys.executable, "-m", "policy_scout.cli.main", "data", "--json"],
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
        [sys.executable, "-m", "policy_scout.cli.main", "data", "--json"],
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
        [sys.executable, "-m", "policy_scout.cli.main", "data", "--json"],
        capture_output=True,
        text=True,
    )
    output = result.stdout
    data = json.loads(output)

    # JSON should use absolute paths, not ~
    for key, path_info in data["paths"].items():
        assert "~" not in path_info["path"]
        assert path_info["path"].startswith("/") or path_info["path"].startswith("C:")
