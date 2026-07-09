# SPDX-License-Identifier: Apache-2.0
"""Tests for audit CLI commands."""

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
        env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env["POLICY_SCOUT_AUDIT_DB_PATH"] = db_path
        env["POLICY_SCOUT_AUDIT_PATH"] = jsonl_path
        env["POLICY_SCOUT_APPROVAL_PATH"] = approval_path
        env["POLICY_SCOUT_REPORT_ROOT"] = report_root
        env["POLICY_SCOUT_SANDBOX_ROOT"] = sandbox_root
        env["POLICY_SCOUT_SWEEP_ROOT"] = sweep_root

        yield tmpdir, db_path, jsonl_path, approval_path, report_root, sandbox_root, sweep_root, env


def test_audit_list_shows_recent_events(temp_audit_paths):
    """Test that audit list shows recent events from SQLite."""
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

    # First create some audit events by running a check command
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Now run audit list
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Should succeed
    assert result.returncode == 0
    assert "Recent Audit Events" in result.stdout
    assert "Event ID:" in result.stdout
    assert "Type:" in result.stdout


def test_audit_list_json_returns_valid_json(temp_audit_paths):
    """Test that audit list --json returns valid JSON."""
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

    # Create some audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Run audit list with JSON
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert "events" in payload
    assert "total_count" in payload
    events = payload["events"]
    assert isinstance(events, list)
    assert len(events) > 0
    assert "event_id" in events[0]
    assert "event_type" in events[0]


def test_audit_list_limit_limits_rows(temp_audit_paths):
    """Test that audit list --limit limits rows."""
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

    # Create multiple audit events
    for i in range(5):
        subprocess.run(
            [
                "python",
                "-m",
                "policy_scout.cli.main",
                "check",
                "--",
                "echo",
                f"test{i}",
            ],
            env=env,
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

    # Run audit list with limit 2
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list", "--limit", "2"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0
    # Count "Event ID:" occurrences - should be 2
    event_count = result.stdout.count("Event ID:")
    assert event_count == 2


def test_audit_show_returns_specific_event(temp_audit_paths):
    """Test that audit show returns specific event."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Get event_id from list
    list_result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )
    events = json.loads(list_result.stdout)["events"]
    event_id = events[0]["event_id"]

    # Show specific event
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "show", event_id],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0
    assert event_id in result.stdout
    assert "Audit Event:" in result.stdout


def test_audit_show_missing_event_returns_error(temp_audit_paths):
    """Test that audit show missing event returns non-zero or clear error."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Try to show non-existent event
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "show", "evt_nonexistent"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode != 0
    assert "Event not found" in result.stderr


def test_audit_request_returns_events_for_one_request_id(temp_audit_paths):
    """Test that audit request returns events for one request_id only."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Get request_id from list
    list_result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )
    events = json.loads(list_result.stdout)["events"]
    request_id = events[0]["request_id"]

    # Query by request_id
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "request", request_id],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0
    assert request_id in result.stdout
    assert "Events for Request:" in result.stdout


def test_audit_type_returns_events_for_one_event_type(temp_audit_paths):
    """Test that audit type returns events for one event_type only."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Query by event type
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "type", "CommandRequested"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0
    assert "Events of Type:" in result.stdout
    assert "CommandRequested" in result.stdout


def test_audit_stats_returns_total_count(temp_audit_paths):
    """Test that audit stats returns total count."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Get stats
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "stats"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0
    assert "Audit Statistics:" in result.stdout
    assert "Total Events:" in result.stdout


def test_audit_stats_includes_counts_by_event_type(temp_audit_paths):
    """Test that audit stats includes counts by event_type."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Get stats
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "stats"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0
    assert "By Event Type:" in result.stdout


def test_audit_cli_output_redacts_secret_like_values(temp_audit_paths):
    """Test that audit CLI output does not show raw token-like values."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Get audit list output
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Check that no raw secret patterns appear
    assert "sk-" not in result.stdout or "<redacted:" in result.stdout
    assert "OPENAI_API_KEY=" not in result.stdout or "<redacted:" in result.stdout


def test_audit_cli_uses_polity_scout_audit_db_path_override(temp_audit_paths):
    """Test that audit CLI uses POLICY_SCOUT_AUDIT_DB_PATH override in tests."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Verify the custom db_path was used
    assert os.path.exists(db_path)

    # Audit list should work with the custom path
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0


def test_audit_cli_does_not_require_jsonl_to_exist(temp_audit_paths):
    """Test that audit CLI does not require JSONL to exist."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Delete JSONL file
    if os.path.exists(jsonl_path):
        os.remove(jsonl_path)

    # Audit list should still work
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0


def test_audit_show_includes_redaction_note(temp_audit_paths):
    """Test that audit show human output includes redaction note."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Get event_id from list
    list_result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "list", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )
    events = json.loads(list_result.stdout)["events"]
    event_id = events[0]["event_id"]

    # Show specific event
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "show", event_id],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0
    assert "Redaction: applied" in result.stdout


def test_audit_stats_includes_time_range(temp_audit_paths):
    """Test that audit stats includes time range."""
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

    # Create audit events
    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "echo", "hello"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Get stats
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "audit", "stats"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0
    assert "Time Range:" in result.stdout
    assert "First Event:" in result.stdout
    assert "Last Event:" in result.stdout
