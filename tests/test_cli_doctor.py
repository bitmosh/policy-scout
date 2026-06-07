"""Tests for policy-scout doctor command."""

import subprocess
import json
import os


def test_doctor_human_output_success():
    """Test doctor command produces human-readable output on success."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "doctor"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Policy Scout Doctor" in result.stdout
    assert "Version:" in result.stdout
    assert "Python:" in result.stdout
    assert "Platform:" in result.stdout
    assert "Health Checks:" in result.stdout
    assert "Overall Status:" in result.stdout


def test_doctor_json_output_success():
    """Test doctor command produces valid JSON output with --json."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "doctor", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    # Parse JSON
    data = json.loads(result.stdout)

    # Check top-level fields
    assert "policy_scout_version" in data
    assert "python_version" in data
    assert "platform" in data
    assert "checks" in data

    # Check platform structure
    assert "system" in data["platform"]
    assert "release" in data["platform"]

    # Check checks structure
    assert "cli_import" in data["checks"]
    assert "python_version" in data["checks"]
    assert "command_registry" in data["checks"]
    assert "default_policy" in data["checks"]
    assert "eval_cases" in data["checks"]
    assert "audit_store" in data["checks"]
    assert "report_directory" in data["checks"]
    assert "npm" in data["checks"]
    assert "pnpm" in data["checks"]
    assert "yarn" in data["checks"]
    assert "bun" in data["checks"]

    # Check each check has status and message
    for check_name, check_result in data["checks"].items():
        assert "status" in check_result
        assert "message" in check_result
        assert check_result["status"] in ["ok", "warning", "error", "not_found"]


def test_doctor_registry_counts_appear():
    """Test doctor command includes registry entry counts."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "doctor", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)

    # Check command registry has entry count
    if data["checks"]["command_registry"]["status"] == "ok":
        assert "entry_count" in data["checks"]["command_registry"]
        assert isinstance(data["checks"]["command_registry"]["entry_count"], int)

    # Check policy registry has entry count
    if data["checks"]["default_policy"]["status"] == "ok":
        assert "entry_count" in data["checks"]["default_policy"]
        assert isinstance(data["checks"]["default_policy"]["entry_count"], int)

    # Check eval cases has entry count
    if data["checks"]["eval_cases"]["status"] == "ok":
        assert "entry_count" in data["checks"]["eval_cases"]
        assert isinstance(data["checks"]["eval_cases"]["entry_count"], int)


def test_doctor_package_manager_missing_produces_warning():
    """Test that missing optional package managers produce warnings, not errors."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "doctor", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)

    # Check that if a package manager is missing, it's a warning
    for pm in ["npm", "pnpm", "yarn", "bun"]:
        if data["checks"][pm]["status"] != "ok":
            # If not ok, should be warning (not error)
            assert data["checks"][pm]["status"] == "warning"
            assert "not found" in data["checks"][pm]["message"]


def test_doctor_no_secrets_printed():
    """Test that doctor command does not print secret-like environment values."""
    # Set a secret-like environment variable
    os.environ["TEST_SECRET_TOKEN"] = "sk-1234567890abcdef"

    try:
        result = subprocess.run(
            ["python", "-m", "policy_scout.cli.main", "doctor"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

        # Check that the secret value is not in output
        assert "sk-1234567890abcdef" not in result.stdout
        assert "TEST_SECRET_TOKEN" not in result.stdout
    finally:
        # Clean up
        del os.environ["TEST_SECRET_TOKEN"]


def test_doctor_json_no_secrets_printed():
    """Test that doctor JSON output does not contain secret-like values."""
    # Set a secret-like environment variable
    os.environ["TEST_SECRET_TOKEN"] = "sk-1234567890abcdef"

    try:
        result = subprocess.run(
            ["python", "-m", "policy_scout.cli.main", "doctor", "--json"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

        # Check that the secret value is not in output
        assert "sk-1234567890abcdef" not in result.stdout
        assert "TEST_SECRET_TOKEN" not in result.stdout
    finally:
        # Clean up
        del os.environ["TEST_SECRET_TOKEN"]


def test_doctor_includes_audit_report_paths():
    """Test that doctor includes audit store and report directory paths."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "doctor", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)

    # Check audit store has path
    if data["checks"]["audit_store"]["status"] == "ok":
        assert "path" in data["checks"]["audit_store"]
        assert isinstance(data["checks"]["audit_store"]["path"], str)

    # Check report directory has path
    if data["checks"]["report_directory"]["status"] == "ok":
        assert "path" in data["checks"]["report_directory"]
        assert isinstance(data["checks"]["report_directory"]["path"], str)


def test_doctor_help_message():
    """Test that doctor command has help message."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "doctor", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "doctor" in result.stdout.lower()
    assert "--json" in result.stdout
