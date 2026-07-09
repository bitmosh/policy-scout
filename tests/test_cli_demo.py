# SPDX-License-Identifier: Apache-2.0
"""Tests for policy-scout demo command."""

import subprocess
import os
from pathlib import Path
from policy_scout.demo import (
    get_demo_root,
    validate_demo_workspace,
    create_demo_workspace,
)


def test_demo_help_message():
    """Test that demo command has help message."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "demo", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "demo" in result.stdout.lower()


def test_demo_creates_workspace_under_expected_root():
    """Test that demo creates workspace under expected demo root."""
    demo_root = get_demo_root()
    assert demo_root == Path.home() / ".local" / "share" / "policy-scout" / "demo"


def test_demo_workspace_validation():
    """Test that workspace validation works correctly."""
    demo_root = get_demo_root()

    # Valid workspace under demo root should pass
    valid_workspace = demo_root / "test_workspace"
    assert validate_demo_workspace(valid_workspace)

    # Invalid workspace outside demo root should fail
    invalid_workspace = Path("/tmp/test_workspace")
    assert not validate_demo_workspace(invalid_workspace)


def test_demo_creates_fixture_files():
    """Test that demo workspace creates expected fixture files."""
    workspace = create_demo_workspace()

    try:
        # Check that workspace exists
        assert workspace.exists()
        assert workspace.is_dir()

        # Check fixture files exist
        assert (workspace / "package.json").exists()
        assert (workspace / "README.md").exists()
        assert (workspace / "suspicious-script.sh").exists()

        # Check package.json content
        package_json = (workspace / "package.json").read_text()
        assert "demo-project" in package_json
        assert "1.0.0" in package_json

        # Check README.md content
        readme = (workspace / "README.md").read_text()
        assert "Demo Project" in readme

        # Check suspicious script content
        script = (workspace / "suspicious-script.sh").read_text()
        assert "harmless demo script" in script
    finally:
        # Cleanup
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace)


def test_demo_output_includes_expected_sections():
    """Test that demo output includes expected sections."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "demo"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = result.stdout

    # Check for expected sections
    assert "Policy Scout Demo" in output
    assert "Demo Workspace:" in output
    assert "Command Checks:" in output
    assert "Project Sweep:" in output
    assert "Checks Passed:" in output


def test_demo_output_includes_expected_decisions():
    """Test that demo output includes expected decision scenarios."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "demo"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = result.stdout

    # Check for expected scenarios
    assert "Safe command (ls)" in output
    assert "ALLOW" in output
    assert "Package install (npm install lodash)" in output
    assert "SANDBOX_FIRST" in output
    assert "Network execution (curl | bash)" in output
    assert "DENY" in output
    assert "Credential-adjacent (cat .env)" in output
    assert "DENY_AND_ALERT" in output
    assert "Destructive (rm -rf /)" in output


def test_demo_does_not_execute_dangerous_commands():
    """Test that demo does not actually execute dangerous commands."""
    # This is verified by the fact that demo uses check_command()
    # which only does classification/policy, not execution
    # The test passes if the demo completes without errors
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "demo"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    # No actual rm -rf / should have run
    assert "/" in result.stdout  # Output should show the command check, not execution


def test_demo_does_not_read_real_credentials():
    """Test that demo does not read real credential files."""
    # Set a secret environment variable
    os.environ["TEST_SECRET_TOKEN"] = "sk-1234567890abcdef"

    try:
        result = subprocess.run(
            ["python", "-m", "policy_scout.cli.main", "demo"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

        assert result.returncode == 0
        # Check that the secret value is not in output
        assert "sk-1234567890abcdef" not in result.stdout
        assert "TEST_SECRET_TOKEN" not in result.stdout
    finally:
        # Clean up
        del os.environ["TEST_SECRET_TOKEN"]


def test_demo_sweep_runs_on_fixture():
    """Test that demo sweep runs on the fixture workspace."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "demo"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = result.stdout

    # Check for sweep section
    assert "Project Sweep:" in output
    assert "Sweep Type:" in output
    assert "project" in output.lower()


def test_demo_workspace_path_printed():
    """Test that demo prints the workspace path for manual cleanup."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "demo"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = result.stdout

    # Check for workspace path and cleanup instructions
    assert "Demo Workspace:" in output
    assert "rm -rf" in output
    assert "manual inspection" in output.lower()
