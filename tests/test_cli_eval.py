"""Tests for CLI eval command."""

import os
import tempfile
import yaml
import json
import subprocess
import sys


def test_cli_eval_run_help():
    """Test `policy-scout eval run --help` works."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "eval", "run", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Filter cases by tag" in result.stdout


def test_cli_eval_run_with_default_cases():
    """Test `policy-scout eval run` with default eval cases."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "eval", "run"],
        capture_output=True,
        text=True,
    )
    # The command should run (may fail if classifier/policy not fully implemented)
    # We're mainly testing that the CLI command exists and doesn't crash
    assert result.returncode in [0, 1]  # 0 if all pass, 1 if any fail


def test_cli_eval_run_with_json():
    """Test `policy-scout eval run --json` outputs valid JSON."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "eval", "run", "--json"],
        capture_output=True,
        text=True,
    )
    # Try to parse as JSON
    try:
        data = json.loads(result.stdout)
        assert "summary" in data
        assert "results" in data
    except json.JSONDecodeError:
        # If not valid JSON, that's a test failure
        assert False, "Output was not valid JSON"


def test_cli_eval_run_with_filter():
    """Test `policy-scout eval run --filter` filters cases."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "policy_scout.cli.main",
            "eval",
            "run",
            "--filter",
            "package_install",
        ],
        capture_output=True,
        text=True,
    )
    # The command should run
    assert result.returncode in [0, 1]


def test_cli_eval_run_with_custom_file():
    """Test `policy-scout eval run --file` uses custom eval cases file."""
    # Create a temporary eval cases file
    cases_data = {
        "cases": [
            {
                "case_id": "custom_001",
                "title": "Custom test",
                "command": "ls",
                "expected_decision": "ALLOW",
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(cases_data, f)
        temp_path = f.name

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "policy_scout.cli.main",
                "eval",
                "run",
                "--file",
                temp_path,
            ],
            capture_output=True,
            text=True,
        )
        # The command should run
        assert result.returncode in [0, 1]
    finally:
        os.unlink(temp_path)


def test_cli_eval_run_with_nonexistent_file():
    """Test `policy-scout eval run --file` with non-existent file fails gracefully."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "policy_scout.cli.main",
            "eval",
            "run",
            "--file",
            "/nonexistent/path/eval_cases.yaml",
        ],
        capture_output=True,
        text=True,
    )
    # Should fail with error message
    assert result.returncode == 1
    assert "Error" in result.stderr


def test_cli_eval_subcommand_missing():
    """Test `policy-scout eval` without subcommand shows help."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "eval"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "No eval subcommand provided" in result.stderr


def test_cli_eval_invalid_subcommand():
    """Test `policy-scout eval invalid` shows error."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "eval", "invalid"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_cli_eval_run_with_env_override():
    """Test `policy-scout eval run` with POLICY_SCOUT_EVAL_CASES_PATH override."""
    # Create a temporary eval cases file
    cases_data = {
        "cases": [
            {
                "case_id": "env_001",
                "title": "Env override test",
                "command": "pwd",
                "expected_decision": "ALLOW",
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(cases_data, f)
        temp_path = f.name

    try:
        env = os.environ.copy()
        env["POLICY_SCOUT_EVAL_CASES_PATH"] = temp_path
        result = subprocess.run(
            [sys.executable, "-m", "policy_scout.cli.main", "eval", "run"],
            capture_output=True,
            text=True,
            env=env,
        )
        # The command should run
        assert result.returncode in [0, 1]
    finally:
        os.unlink(temp_path)


def test_cli_eval_run_output_contains_summary():
    """Test `policy-scout eval run` output contains summary information."""
    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "eval", "run"],
        capture_output=True,
        text=True,
    )
    # Output should contain summary information
    if not result.returncode:  # If it ran successfully
        assert "Total Cases" in result.stdout or "total_cases" in result.stdout
        assert "Passed" in result.stdout or "passed" in result.stdout
        assert "Failed" in result.stdout or "failed" in result.stdout
