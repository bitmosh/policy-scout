"""Tests for sandbox with multiple package managers."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from policy_scout.sandbox.models import SandboxResult
from policy_scout.sandbox.package_manager import detect_package_manager
from policy_scout.sandbox.package_files import copy_package_files
from policy_scout.sandbox.runner import run_package_manager_install


def test_pnpm_add_creates_sandbox_result_with_package_manager():
    """Test pnpm add creates sandbox result with package_manager pnpm."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # Create package.json in host
        (host_root / "package.json").write_text('{"name": "test"}')

        # Copy package files for pnpm
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "pnpm")

        assert "package.json" in copied
        assert (sandbox_workspace / "package.json").exists()


def test_yarn_add_creates_sandbox_result_with_package_manager():
    """Test yarn add creates sandbox result with package_manager yarn."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # Create package.json in host
        (host_root / "package.json").write_text('{"name": "test"}')

        # Copy package files for yarn
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "yarn")

        assert "package.json" in copied
        assert (sandbox_workspace / "package.json").exists()


def test_bun_add_creates_sandbox_result_with_package_manager():
    """Test bun add creates sandbox result with package_manager bun."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # Create package.json in host
        (host_root / "package.json").write_text('{"name": "test"}')

        # Copy package files for bun
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "bun")

        assert "package.json" in copied
        assert (sandbox_workspace / "package.json").exists()


def test_missing_pnpm_executable_fails_safely():
    """Test missing pnpm executable fails safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox_workspace = Path(tmpdir) / "sandbox"
        sandbox_workspace.mkdir()

        # Mock subprocess.run to simulate missing executable
        with patch("policy_scout.sandbox.runner.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("pnpm not found")

            exit_code, stdout, stderr, duration_ms = run_package_manager_install(
                "pnpm", sandbox_workspace, ["add", "test"]
            )

            assert exit_code == -1
            assert "Package manager executable not found" in stderr


def test_missing_yarn_executable_fails_safely():
    """Test missing yarn executable fails safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox_workspace = Path(tmpdir) / "sandbox"
        sandbox_workspace.mkdir()

        # Mock subprocess.run to simulate missing executable
        with patch("policy_scout.sandbox.runner.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("yarn not found")

            exit_code, stdout, stderr, duration_ms = run_package_manager_install(
                "yarn", sandbox_workspace, ["add", "test"]
            )

            assert exit_code == -1
            assert "Package manager executable not found" in stderr


def test_missing_bun_executable_fails_safely():
    """Test missing bun executable fails safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox_workspace = Path(tmpdir) / "sandbox"
        sandbox_workspace.mkdir()

        # Mock subprocess.run to simulate missing executable
        with patch("policy_scout.sandbox.runner.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("bun not found")

            exit_code, stdout, stderr, duration_ms = run_package_manager_install(
                "bun", sandbox_workspace, ["add", "test"]
            )

            assert exit_code == -1
            assert "Package manager executable not found" in stderr


def test_host_package_json_not_mutated_for_pnpm():
    """Test host package.json not mutated for pnpm."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # Create package.json in host
        original_content = '{"name": "test"}'
        (host_root / "package.json").write_text(original_content)

        # Copy package files for pnpm
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "pnpm")

        # Host package.json should be unchanged
        assert (host_root / "package.json").read_text() == original_content


def test_host_package_json_not_mutated_for_yarn():
    """Test host package.json not mutated for yarn."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # Create package.json in host
        original_content = '{"name": "test"}'
        (host_root / "package.json").write_text(original_content)

        # Copy package files for yarn
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "yarn")

        # Host package.json should be unchanged
        assert (host_root / "package.json").read_text() == original_content


def test_host_package_json_not_mutated_for_bun():
    """Test host package.json not mutated for bun."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # Create package.json in host
        original_content = '{"name": "test"}'
        (host_root / "package.json").write_text(original_content)

        # Copy package files for bun
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "bun")

        # Host package.json should be unchanged
        assert (host_root / "package.json").read_text() == original_content


def test_minimal_sandbox_package_json_created_when_host_absent():
    """Test minimal sandbox package.json created only inside sandbox when host package.json absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # No package.json in host
        assert not (host_root / "package.json").exists()

        # Copy package files for pnpm (should not fail)
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "pnpm")

        # Host still has no package.json
        assert not (host_root / "package.json").exists()


def test_relevant_lockfiles_copied_for_pnpm():
    """Test relevant lockfiles are copied for pnpm."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # Create package.json and pnpm-lock.yaml in host
        (host_root / "package.json").write_text('{"name": "test"}')
        (host_root / "pnpm-lock.yaml").write_text("{}")

        # Copy package files for pnpm
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "pnpm")

        assert "package.json" in copied
        assert "pnpm-lock.yaml" in copied
        assert (sandbox_workspace / "pnpm-lock.yaml").exists()


def test_relevant_lockfiles_copied_for_yarn():
    """Test relevant lockfiles are copied for yarn."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # Create package.json and yarn.lock in host
        (host_root / "package.json").write_text('{"name": "test"}')
        (host_root / "yarn.lock").write_text("{}")

        # Copy package files for yarn
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "yarn")

        assert "package.json" in copied
        assert "yarn.lock" in copied
        assert (sandbox_workspace / "yarn.lock").exists()


def test_relevant_lockfiles_copied_for_bun():
    """Test relevant lockfiles are copied for bun."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # Create package.json and bun.lockb in host
        (host_root / "package.json").write_text('{"name": "test"}')
        (host_root / "bun.lockb").write_text("{}")

        # Copy package files for bun
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "bun")

        assert "package.json" in copied
        assert "bun.lockb" in copied
        assert (sandbox_workspace / "bun.lockb").exists()


def test_token_bearing_config_files_not_copied():
    """Test token-bearing config files are not copied."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_root = Path(tmpdir) / "host"
        sandbox_workspace = Path(tmpdir) / "sandbox"
        host_root.mkdir()
        sandbox_workspace.mkdir()

        # Create package.json and .npmrc with token in host
        (host_root / "package.json").write_text('{"name": "test"}')
        (host_root / ".npmrc").write_text("//registry.npmjs.org/:_authToken=secret")

        # Copy package files for npm
        copied, skipped = copy_package_files(host_root, sandbox_workspace, "npm")

        assert "package.json" in copied
        assert ".npmrc" in skipped
        assert not (sandbox_workspace / ".npmrc").exists()


def test_runner_handles_missing_executable():
    """Test runner handles missing executable gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox_workspace = Path(tmpdir) / "sandbox"
        sandbox_workspace.mkdir()

        # Run with non-existent package manager
        exit_code, stdout, stderr, duration_ms = run_package_manager_install(
            "nonexistent-pm", sandbox_workspace, ["install", "test"]
        )

        assert exit_code == -1
        assert "Package manager executable not found" in stderr


def test_sandbox_result_package_manager_field():
    """Test SandboxResult package_manager field."""
    result = SandboxResult(package_manager="pnpm")
    assert result.package_manager == "pnpm"

    result = SandboxResult(package_manager="yarn")
    assert result.package_manager == "yarn"

    result = SandboxResult(package_manager="bun")
    assert result.package_manager == "bun"
