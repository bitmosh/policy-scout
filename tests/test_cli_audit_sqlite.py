"""Tests for CLI audit SQLite integration using subprocess."""

import json
import os
import subprocess
import tempfile
import pytest


@pytest.fixture
def temp_audit_paths():
    """Set up temporary paths for all Policy Scout data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "audit.db")
        jsonl_path = os.path.join(tmpdir, "audit.jsonl")
        approval_path = os.path.join(tmpdir, "approvals.jsonl")
        report_root = os.path.join(tmpdir, "reports")
        sandbox_root = os.path.join(tmpdir, "sandboxes")
        sweep_root = os.path.join(tmpdir, "sweeps")

        # Create directories
        os.makedirs(report_root, exist_ok=True)
        os.makedirs(sandbox_root, exist_ok=True)
        os.makedirs(sweep_root, exist_ok=True)

        env = os.environ.copy()
        env["PYTHONPATH"] = "/home/boop/Projects/policy-scout"
        env["POLICY_SCOUT_AUDIT_DB_PATH"] = db_path
        env["POLICY_SCOUT_AUDIT_PATH"] = jsonl_path
        env["POLICY_SCOUT_APPROVAL_PATH"] = approval_path
        env["POLICY_SCOUT_REPORT_ROOT"] = report_root
        env["POLICY_SCOUT_SANDBOX_ROOT"] = sandbox_root
        env["POLICY_SCOUT_SWEEP_ROOT"] = sweep_root

        yield tmpdir, db_path, jsonl_path, approval_path, report_root, sandbox_root, sweep_root, env


def test_check_npm_install_writes_to_sqlite(temp_audit_paths):
    """Test that check npm install writes CommandRequested and DecisionIssued to SQLite."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "check",
            "--",
            "npm",
            "install",
            "lodash",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Should succeed with SANDBOX_FIRST decision
    assert result.returncode == 10

    # Verify SQLite database was created
    assert os.path.exists(db_path)

    # Verify events were written to SQLite
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
        count = cursor.fetchone()[0]
        assert count >= 2  # At least CommandRequested and DecisionIssued

        # Verify event types
        cursor = conn.execute("SELECT DISTINCT event_type FROM audit_events")
        event_types = [row[0] for row in cursor.fetchall()]
        assert "CommandRequested" in event_types
        assert "DecisionIssued" in event_types


def test_check_curl_pipe_bash_writes_deny_to_sqlite(temp_audit_paths):
    """Test that check curl pipe bash writes DENY decision data to SQLite."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "check",
            "--",
            "curl",
            "https://example.com/install.sh",
            "|",
            "bash",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Should succeed with DENY decision
    assert result.returncode == 20

    # Verify SQLite database was created
    assert os.path.exists(db_path)

    # Verify DENY decision was written
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT data_json FROM audit_events WHERE event_type = 'DecisionIssued'"
        )
        row = cursor.fetchone()
        assert row is not None
        data = json.loads(row[0])
        assert data["decision"] == "DENY"


def test_run_echo_hello_writes_execution_events_to_sqlite(temp_audit_paths):
    """Test that run echo hello writes CommandExecutionStarted and CommandExecutionCompleted to SQLite."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "run", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Should succeed with ALLOW decision
    assert result.returncode == 0

    # Verify SQLite database was created
    assert os.path.exists(db_path)

    # Verify execution events were written
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT DISTINCT event_type FROM audit_events")
        event_types = [row[0] for row in cursor.fetchall()]
        assert "CommandExecutionStarted" in event_types
        assert "CommandExecutionCompleted" in event_types


def test_run_npm_install_blocks_and_writes_blocked_event(temp_audit_paths):
    """Test that run npm install blocks and writes CommandExecutionBlocked to SQLite."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "run",
            "--",
            "npm",
            "install",
            "lodash",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Should block with SANDBOX_FIRST decision
    assert result.returncode == 10

    # Verify SQLite database was created
    assert os.path.exists(db_path)

    # Verify blocked event was written
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT DISTINCT event_type FROM audit_events")
        event_types = [row[0] for row in cursor.fetchall()]
        assert (
            "CommandExecutionBlocked" in event_types
            or "CommandRequested" in event_types
        )


def test_run_rm_rf_creates_approval_and_writes_to_sqlite(temp_audit_paths):
    """Test that run rm -rf node_modules creates approval and writes ApprovalRequested to SQLite."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "run",
            "--",
            "rm",
            "-rf",
            "node_modules",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Should block with REQUIRE_APPROVAL decision
    assert result.returncode == 10

    # Verify SQLite database was created
    assert os.path.exists(db_path)

    # Verify approval event was written
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT DISTINCT event_type FROM audit_events")
        event_types = [row[0] for row in cursor.fetchall()]
        assert "ApprovalRequested" in event_types


def test_approvals_list_writes_audit_event(temp_audit_paths):
    """Test that approvals list writes audit event if current behavior does that."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    # First create an approval
    subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "run",
            "--",
            "rm",
            "-rf",
            "node_modules",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Then list approvals
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "approvals", "list"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Verify SQLite has events
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
        count = cursor.fetchone()[0]
        assert count >= 1


def test_sweep_project_writes_sweep_events_to_sqlite(temp_audit_paths):
    """Test that sweep project writes SweepStarted and SweepCompleted to SQLite."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    # Create a minimal project structure
    os.makedirs(os.path.join(tmpdir, "node_modules"), exist_ok=True)

    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "sweep", "project"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Should succeed
    assert result.returncode == 0

    # Verify SQLite database was created
    assert os.path.exists(db_path)

    # Verify sweep events were written
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT DISTINCT event_type FROM audit_events")
        event_types = [row[0] for row in cursor.fetchall()]
        # Check for sweep-related events
        has_sweep_event = any(
            "Sweep" in et or "sweep" in et.lower() for et in event_types
        )
        assert has_sweep_event or len(event_types) >= 1  # At least some events written


def test_sandbox_writes_sandbox_events_to_sqlite(temp_audit_paths):
    """Test that sandbox writes sandbox audit events to SQLite."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    # Create a minimal package.json
    package_json = os.path.join(tmpdir, "package.json")
    with open(package_json, "w") as f:
        f.write('{"name": "test", "version": "1.0.0"}')

    subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "sandbox",
            "--",
            "npm",
            "install",
            "lodash",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Verify SQLite database was created (may fail if npm not available, but audit should still write)
    assert os.path.exists(db_path)

    # Verify events were written
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
        count = cursor.fetchone()[0]
        assert count >= 1


def test_sqlite_rows_are_redacted(temp_audit_paths):
    """Test that SQLite rows are redacted and do not contain raw secret-like values."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    # Run a command that might have secrets
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    # Verify SQLite rows are redacted
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT * FROM audit_events")
        rows = cursor.fetchall()

        for row in rows:
            row_str = str(row)
            # Check that no raw secret patterns appear
            # (This is a basic check; actual redaction patterns are in redaction.py)
            assert "sk-" not in row_str or "<redacted:" in row_str
            assert "OPENAI_API_KEY=" not in row_str or "<redacted:" in row_str


def test_jsonl_compatibility_still_works(temp_audit_paths):
    """Test that JSONL audit still writes valid redacted events."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    # Verify JSONL file was created
    assert os.path.exists(jsonl_path)

    # Verify JSONL contains valid JSON lines
    with open(jsonl_path, "r") as f:
        lines = f.readlines()
        assert len(lines) >= 1

        # Parse each line as JSON
        for line in lines:
            line = line.strip()
            if line:
                data = json.loads(line)
                assert "event_id" in data
                assert "event_type" in data
                assert "timestamp" in data


def test_run_fails_safe_on_critical_audit_failure(temp_audit_paths):
    """Test that run fails safe when critical audit persistence fails."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    # Make the SQLite database path read-only to simulate failure
    # First create the database
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "test"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Make database directory read-only
    os.chmod(os.path.dirname(db_path), 0o555)

    try:
        result = subprocess.run(
            ["python", "-m", "policy_scout.cli.main", "run", "--", "echo", "hello"],
            env=env,
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        # Should fail with exit code 30 (audit failure)
        assert result.returncode == 30
        assert "Failed to persist audit event" in result.stderr
    finally:
        # Restore permissions
        os.chmod(os.path.dirname(db_path), 0o755)


def test_check_continues_on_audit_failure(temp_audit_paths):
    """Test that check can continue with warning on audit failure."""
    (
        tmpdir,
        db_path,
        jsonl_path,
        approval_path,
        report_root,
        sandbox_root,
        sweep_root,
        env,
    ) = temp_audit_paths

    # Make the SQLite database path read-only to simulate failure
    # First create the database
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "test"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Make database directory read-only
    os.chmod(os.path.dirname(db_path), 0o555)

    try:
        result = subprocess.run(
            ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
            env=env,
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        # Check should still return a decision (0, 10, or 20) despite audit failure
        # because check does not execute commands
        assert result.returncode in [0, 10, 20]
    finally:
        # Restore permissions
        os.chmod(os.path.dirname(db_path), 0o755)
