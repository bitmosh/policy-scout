"""JSON contract tests for Policy Scout CLI commands.

These tests lock down the current JSON output contracts for future UI/API/Tauri work.
Tests validate required stable fields and redaction behavior without asserting every incidental field.
"""

import json
import os
import subprocess
import tempfile
import pytest


@pytest.fixture
def temp_state_paths():
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

        yield tmpdir, report_root, env


def test_doctor_json_parses_and_has_required_fields(temp_state_paths):
    """Test that doctor --json parses and has required fields."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "doctor", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert "checks" in data
    assert isinstance(data["checks"], dict)

    # Each check should have status and message
    for check_name, check_data in data["checks"].items():
        assert "status" in check_data
        assert "message" in check_data


def test_check_json_ls_has_required_fields_and_correct_decision(temp_state_paths):
    """Test that check --json -- ls has required fields and correct decision."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "check",
            "--json",
            "--no-audit",
            "--",
            "ls",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert "decision" in data
    assert "risk_score" in data
    assert "category" in data
    assert "capabilities" in data
    assert "reasons" in data

    # ls should be ALLOW
    assert data["decision"] == "ALLOW"
    assert isinstance(data["capabilities"], list)
    assert isinstance(data["reasons"], list)


def test_check_json_npm_install_has_required_fields_and_correct_decision(
    temp_state_paths,
):
    """Test that check --json -- npm install lodash has required fields and correct decision."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "check",
            "--json",
            "--no-audit",
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

    # JSON output should be present even with non-zero exit code (decision signaling)
    data = json.loads(result.stdout)
    assert "decision" in data
    assert "risk_score" in data
    assert "category" in data
    assert "capabilities" in data
    assert "reasons" in data

    # npm install should be SANDBOX_FIRST
    assert data["decision"] == "SANDBOX_FIRST"
    assert isinstance(data["capabilities"], list)
    assert isinstance(data["reasons"], list)


def test_check_json_curl_pipe_bash_has_required_fields_and_correct_decision(
    temp_state_paths,
):
    """Test that check --json -- curl | bash has required fields and correct decision."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "check",
            "--json",
            "--no-audit",
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

    # JSON output should be present even with non-zero exit code (decision signaling)
    data = json.loads(result.stdout)
    assert "decision" in data
    assert "risk_score" in data
    assert "category" in data
    assert "capabilities" in data
    assert "reasons" in data

    # curl | bash should be DENY
    assert data["decision"] == "DENY"
    assert isinstance(data["capabilities"], list)
    assert isinstance(data["reasons"], list)


def test_audit_list_json_parses_and_has_required_fields(temp_state_paths):
    """Test that audit list --json parses and has required fields."""
    tmpdir, report_root, env = temp_state_paths

    # First create an audit event
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Now run audit list with JSON
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    events = json.loads(result.stdout)
    assert isinstance(events, list)

    if len(events) > 0:
        event = events[0]
        assert "event_id" in event
        assert "event_type" in event
        assert "timestamp" in event
        assert "request_id" in event


def test_audit_stats_json_has_total_events_and_by_type(temp_state_paths):
    """Test that audit stats --json has total_events and by_type."""
    tmpdir, report_root, env = temp_state_paths

    # First create an audit event
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Get stats
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "stats", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert "total_events" in data
    assert "by_type" in data
    assert isinstance(data["by_type"], dict)


def test_audit_stats_json_has_time_range_when_events_exist(temp_state_paths):
    """Test that audit stats --json has time_range when events exist."""
    tmpdir, report_root, env = temp_state_paths

    # First create an audit event
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Get stats
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "stats", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    # time_range should be present when events exist
    assert "time_range" in data
    if data["time_range"]:
        assert "first_event" in data["time_range"]
        assert "last_event" in data["time_range"]


def test_report_list_json_has_required_fields(temp_state_paths):
    """Test that report list --json has required fields."""
    tmpdir, report_root, env = temp_state_paths

    # First create a report by running a check with --report
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--report", "--", "ls"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Now run report list with JSON
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "list", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    reports = json.loads(result.stdout)
    assert isinstance(reports, list)

    if len(reports) > 0:
        report = reports[0]
        assert "report_id" in report
        assert "report_type" in report
        assert "title" in report
        assert "has_markdown" in report
        assert "has_json" in report
        # created_at only if generated by current code path
        if "created_at" in report:
            assert isinstance(report["created_at"], str)


def test_sweep_project_json_has_required_fields(temp_state_paths):
    """Test that sweep project --json has required fields on temp fixture."""
    tmpdir, report_root, env = temp_state_paths

    # Create a minimal fixture project
    fixture_dir = os.path.join(tmpdir, "fixture_project")
    os.makedirs(fixture_dir, exist_ok=True)

    # Create package.json
    with open(os.path.join(fixture_dir, "package.json"), "w") as f:
        f.write('{"name": "test-project", "version": "1.0.0"}')

    # Run sweep project with JSON
    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "sweep",
            "project",
            "--json",
            "--no-audit",
            "--project",
            fixture_dir,
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert "sweep_id" in data
    assert "sweep_type" in data
    assert "findings_count" in data
    assert "findings" in data
    assert "could_not_verify" in data
    assert "schema_version" in data

    assert isinstance(data["findings_count"], dict)
    assert isinstance(data["findings"], list)
    assert isinstance(data["could_not_verify"], list)


def test_sweep_quick_json_has_required_fields(temp_state_paths):
    """Test that sweep quick --json has required fields without brittle assertions."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "sweep", "quick", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert "sweep_id" in data
    assert "sweep_type" in data
    assert "findings_count" in data
    assert "findings" in data
    assert "could_not_verify" in data
    assert "schema_version" in data

    assert isinstance(data["findings_count"], dict)
    assert isinstance(data["findings"], list)
    assert isinstance(data["could_not_verify"], list)


def test_check_json_redacts_secret_like_values_in_command(temp_state_paths):
    """Test that check --json redacts secret-like values in command."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "check",
            "--json",
            "--no-audit",
            "--",
            "curl",
            "https://example.com/?token=sk-test-json-contract-secret",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # JSON output should be present even with non-zero exit code (decision signaling)
    output = result.stdout
    # Raw secret should not appear
    assert "sk-test-json-contract-secret" not in output
    # Redaction placeholder should appear
    assert "<redacted:" in output


def test_sweep_json_redacts_secret_like_values_in_findings(temp_state_paths):
    """Test that sweep JSON redacts secret-like values in findings."""
    tmpdir, report_root, env = temp_state_paths

    # Create a fixture with a suspicious file containing a fake token
    fixture_dir = os.path.join(tmpdir, "fixture_project")
    os.makedirs(fixture_dir, exist_ok=True)

    with open(os.path.join(fixture_dir, "suspicious.sh"), "w") as f:
        f.write("#!/bin/bash\ncurl https://api.example.com?token=sk-abc123def456\n")

    # Run sweep project with JSON
    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "sweep",
            "project",
            "--json",
            "--no-audit",
            "--project",
            fixture_dir,
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    output = result.stdout
    # Raw secret should not appear
    assert "sk-abc123def456" not in output
    # Redaction placeholder should appear if finding contains the secret
    # (may not appear if sweep doesn't detect the file, but should not leak if it does)
    if "sk-" in output:
        assert "<redacted:" in output


def test_run_json_echo_hello_has_required_fields(temp_state_paths):
    """Test that run --json for safe command has required fields."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "run",
            "--json",
            "--",
            "echo",
            "hello",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Should execute and exit with 0
    assert result.returncode == 0

    # Should parse as valid JSON
    data = json.loads(result.stdout)

    # Assert required fields (based on actual CLI output)
    assert "execution_id" in data
    assert "command" in data
    assert "exit_code" in data
    assert "stdout" in data
    assert "stderr" in data
    assert "decision_id" in data


def test_run_json_npm_install_blocked_has_decision_fields(temp_state_paths):
    """Test that run --json for blocked command has decision fields."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "run",
            "--json",
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

    # Should not execute, exit with 10 (risky decision)
    assert result.returncode == 10

    # Should parse as valid JSON if emitted
    data = json.loads(result.stdout)

    # Assert decision field exists (based on actual CLI output)
    assert "decision" in data

    # Assert decision is SANDBOX_FIRST
    assert data["decision"] == "SANDBOX_FIRST"


def test_audit_show_json_has_required_fields(temp_state_paths):
    """Test that audit show --json has required fields."""
    tmpdir, report_root, env = temp_state_paths

    # First create an audit event
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Get the event_id from audit list
    list_result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    events = json.loads(list_result.stdout)
    assert len(events) > 0
    event_id = events[0]["event_id"]

    # Now run audit show with JSON
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "show", event_id, "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)

    # Assert required fields
    assert "event_id" in data
    assert "event_type" in data
    assert "timestamp" in data
    assert "request_id" in data
    assert "summary" in data
    assert "data_json" in data


def test_audit_request_json_has_required_fields(temp_state_paths):
    """Test that audit request --json has required fields."""
    tmpdir, report_root, env = temp_state_paths

    # First create an audit event with JSON output
    check_result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "check",
            "--json",
            "--",
            "echo",
            "hello",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Extract request_id from check output
    check_data = json.loads(check_result.stdout)
    request_id = check_data["request_id"]

    # Now run audit request with JSON
    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "audit",
            "request",
            request_id,
            "--json",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    events = json.loads(result.stdout)

    # Assert array shape
    assert isinstance(events, list)

    if len(events) > 0:
        # Assert all events include required fields
        for event in events:
            assert "event_id" in event
            assert "event_type" in event
            assert "timestamp" in event
            assert "request_id" in event


def test_audit_type_json_has_required_fields(temp_state_paths):
    """Test that audit type --json has required fields."""
    tmpdir, report_root, env = temp_state_paths

    # First create an audit event
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Query for CommandRequested event type
    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "audit",
            "type",
            "CommandRequested",
            "--json",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    events = json.loads(result.stdout)

    # Assert array shape
    assert isinstance(events, list)

    if len(events) > 0:
        # Assert all events include required fields
        for event in events:
            assert "event_id" in event
            assert "event_type" in event
            assert "timestamp" in event
            assert "request_id" in event


def test_eval_run_json_has_required_fields(temp_state_paths):
    """Test that eval run --json has required fields."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "eval", "run", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Should run (may exit 1 if any tests fail, but JSON should still be emitted)
    assert result.returncode in [0, 1]

    data = json.loads(result.stdout)

    # Assert summary object with required fields
    assert "summary" in data
    assert "total_cases" in data["summary"]
    assert "passed" in data["summary"]
    assert "failed" in data["summary"]
    assert "execution_time_ms" in data["summary"]

    # Assert results array exists
    assert "results" in data
    assert isinstance(data["results"], list)

    # If current suite passes, assert passed == total_cases
    if data["summary"]["failed"] == 0:
        assert data["summary"]["passed"] == data["summary"]["total_cases"]
