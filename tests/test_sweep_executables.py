"""Tests for executable file checks."""

import os
import tempfile
from policy_scout.sweep.executables import check_executables


def test_check_executables_detects_executable():
    """Test detection of executable files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an executable file
        script_path = os.path.join(tmpdir, "script.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'hello'")

        # Make it executable
        os.chmod(script_path, 0o755)

        findings = check_executables(tmpdir, "sweep_123")

        assert len(findings) > 0
        assert any(f.category == "unknown_suspicious_artifact" for f in findings)
        assert any(f.severity == "info" for f in findings)


def test_check_executables_skips_non_executable():
    """Test that non-executable files are not flagged."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a non-executable file
        script_path = os.path.join(tmpdir, "script.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'hello'")

        # Keep it non-executable
        os.chmod(script_path, 0o644)

        findings = check_executables(tmpdir, "sweep_123")

        # Should not flag non-executable files
        assert len(findings) == 0


def test_check_executables_skips_node_modules():
    """Test that node_modules directory is skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create node_modules directory with executable
        node_modules = os.path.join(tmpdir, "node_modules")
        os.makedirs(node_modules)

        script_path = os.path.join(node_modules, "script.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'hello'")
        os.chmod(script_path, 0o755)

        findings = check_executables(tmpdir, "sweep_123")

        # Should skip node_modules
        assert len(findings) == 0


def test_check_executables_skips_git():
    """Test that .git directory is skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create .git directory with executable
        git_dir = os.path.join(tmpdir, ".git")
        os.makedirs(git_dir)

        script_path = os.path.join(git_dir, "hook")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'hello'")
        os.chmod(script_path, 0o755)

        findings = check_executables(tmpdir, "sweep_123")

        # Should skip .git
        assert len(findings) == 0
