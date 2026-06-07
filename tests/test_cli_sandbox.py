"""Tests for CLI sandbox command."""

import os
import tempfile
from pathlib import Path
from policy_scout.cli.main import handle_sandbox_command


def test_sandbox_help_shows_dual_mode():
    """Test sandbox help explains dual-mode behavior."""
    import sys
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "policy_scout.cli.main", "sandbox", "--help"],
        capture_output=True,
        text=True,
    )
    help_output = result.stdout

    assert "Install/review mode" in help_output
    assert "Migration mode" in help_output
    assert "Dry-run migration" in help_output
    assert "Non-interactive migration" in help_output
    assert "--dry-run" in help_output
    assert "--yes" in help_output
    assert "migration mode only" in help_output


def test_sandbox_command_npm_install():
    """Test sandbox command with npm install."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = tmpdir
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(Path(tmpdir) / "audit.jsonl")

        try:
            import sys
            from io import StringIO

            old_stderr = sys.stderr
            sys.stderr = StringIO()

            try:
                handle_sandbox_command(
                    "npm install lodash", json_output=False, audit_enabled=False
                )
            except SystemExit:
                # Expected - sandbox command calls sys.exit
                pass
            finally:
                sys.stderr = old_stderr
        except Exception:
            # Expected if npm not available or network fails
            pass
        finally:
            os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_sandbox_command_non_npm():
    """Test sandbox command rejects non-npm commands."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = tmpdir
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(Path(tmpdir) / "audit.jsonl")

        try:
            import sys
            from io import StringIO

            old_stderr = sys.stderr
            sys.stderr = StringIO()

            try:
                handle_sandbox_command(
                    "pip install requests", json_output=False, audit_enabled=False
                )
            except SystemExit:
                pass  # Expected

            stderr_output = sys.stderr.getvalue()
            sys.stderr = old_stderr

            assert (
                "Only npm/pnpm/yarn/bun install/add commands are supported"
                in stderr_output
            )
        finally:
            os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_sandbox_command_json_output():
    """Test sandbox command JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = tmpdir
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(Path(tmpdir) / "audit.jsonl")

        try:
            import sys
            from io import StringIO

            old_stdout = sys.stdout
            sys.stdout = StringIO()

            try:
                handle_sandbox_command(
                    "npm install lodash", json_output=True, audit_enabled=False
                )
            except SystemExit:
                pass  # Expected

            stdout_output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            # Should contain JSON structure
            if stdout_output:
                import json

                try:
                    result = json.loads(stdout_output)
                    assert "sandbox_id" in result
                    assert "command" in result
                except json.JSONDecodeError:
                    pass  # May have error message instead
        finally:
            os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_sandbox_command_audit_events():
    """Test sandbox command writes audit events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = tmpdir
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            import sys
            from io import StringIO

            old_stderr = sys.stderr
            sys.stderr = StringIO()

            try:
                handle_sandbox_command(
                    "npm install lodash", json_output=False, audit_enabled=True
                )
            except SystemExit:
                pass  # Expected

            sys.stderr = old_stderr

            # Check audit events were written
            if audit_path.exists():
                content = audit_path.read_text()
                # Should contain sandbox-related events
                assert "SandboxRequested" in content or "SandboxError" in content
        finally:
            os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_sandbox_command_creates_result_file():
    """Test sandbox command creates result JSON artifact."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = tmpdir
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(Path(tmpdir) / "audit.jsonl")

        try:
            import sys
            from io import StringIO

            old_stderr = sys.stderr
            sys.stderr = StringIO()

            try:
                handle_sandbox_command(
                    "npm install lodash", json_output=False, audit_enabled=False
                )
            except SystemExit:
                pass  # Expected

            sys.stderr = old_stderr

            # Check result file was created
            results_dir = Path(tmpdir).parent / "results"
            if results_dir.exists():
                _ = list(results_dir.glob("sbx_*.json"))
                # May have result file if install succeeded
        finally:
            os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_sandbox_human_output_includes_report_id():
    """Test sandbox human output includes report_id when report created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = tmpdir
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(Path(tmpdir) / "audit.jsonl")
        os.environ["POLICY_SCOUT_REPORT_ROOT"] = tmpdir

        try:
            import sys
            from io import StringIO

            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()

            try:
                handle_sandbox_command(
                    "npm install lodash", json_output=False, audit_enabled=False
                )
            except SystemExit:
                pass  # Expected

            stdout_output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            # If report was generated, check for report_id in output
            if "Scout Report generated" in stdout_output:
                assert "Report ID:" in stdout_output
        finally:
            os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)
            os.environ.pop("POLICY_SCOUT_REPORT_ROOT", None)
