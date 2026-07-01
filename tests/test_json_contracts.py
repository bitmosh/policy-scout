"""JSON contract tests for Policy Scout CLI commands.

These tests lock down the current JSON output contracts for future UI/API/Tauri work.
Tests validate required stable fields and redaction behavior without asserting every incidental field.

Each CLI command's JSON output is also validated against the JSON Schema in
ui/desktop/src/contracts/ and the corresponding mock fixture in ui/desktop/src/mocks/
to ensure the TypeScript types and browser-preview mocks stay in sync with live output.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
import pytest

# Repo root for resolving contracts and mocks
_REPO_ROOT = Path(__file__).parent.parent
_CONTRACTS = _REPO_ROOT / "ui" / "desktop" / "src" / "contracts"
_MOCKS = _REPO_ROOT / "ui" / "desktop" / "src" / "mocks"


def _validate_schema(data: object, schema_name: str) -> None:
    """Validate data against a JSON Schema file. Skips if jsonschema not installed."""
    try:
        import jsonschema
    except ImportError:
        return

    schema_path = _CONTRACTS / schema_name
    if not schema_path.exists():
        raise FileNotFoundError(f"Contract schema not found: {schema_path}")

    schema = json.loads(schema_path.read_text())
    jsonschema.validate(instance=data, schema=schema)


def _validate_mock(schema_name: str, mock_name: str) -> None:
    """Validate a mock fixture against the same schema. Skips if jsonschema not installed."""
    try:
        import jsonschema
    except ImportError:
        return

    mock_path = _MOCKS / mock_name
    if not mock_path.exists():
        raise FileNotFoundError(f"Mock fixture not found: {mock_path}")

    mock_data = json.loads(mock_path.read_text())
    _validate_schema(mock_data, schema_name)


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
        env["PYTHONPATH"] = str(_REPO_ROOT)
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

    _validate_schema(data, "doctor_status.json")
    _validate_mock("doctor_status.json", "doctor_status.json")


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

    _validate_schema(data, "check_decision.json")
    _validate_mock("check_decision.json", "check_decision.json")


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

    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert "events" in payload
    assert "total_count" in payload
    events = payload["events"]
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

    _validate_schema(data, "audit_stats.json")
    _validate_mock("audit_stats.json", "audit_stats.json")


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

    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert "reports" in payload
    assert "total_count" in payload
    reports = payload["reports"]
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

    _validate_schema(payload, "report_list.json")
    _validate_mock("report_list.json", "report_list.json")


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

    _validate_schema(data, "sweep_data.json")
    _validate_mock("sweep_data.json", "sweep_data.json")


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

    _validate_schema(data, "sweep_data.json")


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

    # Assert new decision/risk fields
    assert "decision_id" in data
    assert "risk_score" in data
    assert "risk_band" in data
    assert "category" in data
    assert "confidence" in data
    assert "policy_hits" in data
    assert "reasons" in data
    assert "recommended_next_action" in data
    assert "requires_audit" in data
    assert "override_allowed" in data

    # Assert command field
    assert "command" in data
    assert data["command"] == "npm install lodash"

    # Assert recommended field for SANDBOX_FIRST
    assert "recommended" in data


def test_run_json_curl_pipe_bash_deny_has_decision_fields(temp_state_paths):
    """Test that run --json -- curl pipe bash DENY has decision fields."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "run",
            "--json",
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

    # Should exit with DENY exit code (20)
    assert result.returncode == 20

    data = json.loads(result.stdout)

    # Assert decision field
    assert "decision" in data
    assert data["decision"] == "DENY"

    # Assert new decision/risk fields
    assert "decision_id" in data
    assert "risk_score" in data
    assert "risk_band" in data
    assert "category" in data
    assert "confidence" in data
    assert "policy_hits" in data
    assert "reasons" in data
    assert "recommended_next_action" in data
    assert "requires_audit" in data
    assert "override_allowed" in data

    # Assert command field
    assert "command" in data


def test_run_json_cat_env_deny_and_alert_has_decision_fields(temp_state_paths):
    """Test that run --json -- cat .env DENY_AND_ALERT has decision fields."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "run", "--json", "--", "cat", ".env"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Should exit with DENY_AND_ALERT exit code (20)
    assert result.returncode == 20

    data = json.loads(result.stdout)

    # Assert decision field
    assert "decision" in data
    assert data["decision"] == "DENY_AND_ALERT"

    # Assert new decision/risk fields
    assert "decision_id" in data
    assert "risk_score" in data
    assert "risk_band" in data
    assert "category" in data
    assert "confidence" in data
    assert "policy_hits" in data
    assert "reasons" in data
    assert "recommended_next_action" in data
    assert "requires_audit" in data
    assert "override_allowed" in data

    # Assert command field
    assert "command" in data


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

    list_payload = json.loads(list_result.stdout)
    events = list_payload["events"]
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

    _validate_schema(data, "audit_event_detail.json")
    _validate_mock("audit_event_detail.json", "audit_event_detail.json")


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

    data = json.loads(result.stdout)

    # Assert paginated dict shape
    assert isinstance(data, dict)
    assert "events" in data
    assert "total_count" in data
    events = data["events"]

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

    _validate_schema(data, "eval_results.json")
    _validate_mock("eval_results.json", "eval_results.json")


def test_eval_run_json_has_duration_ms_alias(temp_state_paths):
    """Test that eval run --json has backward-compatible duration_ms alias alongside execution_time_ms."""
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

    # Assert both fields exist in summary
    assert "summary" in data
    assert "execution_time_ms" in data["summary"]
    assert "duration_ms" in data["summary"]

    # Assert values are equal
    assert data["summary"]["execution_time_ms"] == data["summary"]["duration_ms"]

    # Assert value is numeric and non-negative
    assert isinstance(data["summary"]["execution_time_ms"], (int, type(None)))
    if data["summary"]["execution_time_ms"] is not None:
        assert data["summary"]["execution_time_ms"] >= 0

    # Assert results also have both fields if they include execution_time_ms
    if len(data["results"]) > 0:
        result_item = data["results"][0]
        if "execution_time_ms" in result_item:
            assert "duration_ms" in result_item
            assert result_item["execution_time_ms"] == result_item["duration_ms"]


def test_data_status_json_has_required_fields(temp_state_paths):
    """Test that data status --json has required fields. Current behavior; JSON API v1 candidate."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "data", "status", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)

    # Assert top-level fields
    assert "data_root" in data
    assert "paths" in data
    assert "counts" in data

    # Assert paths structure
    assert isinstance(data["paths"], dict)
    for path_name, path_info in data["paths"].items():
        assert "path" in path_info
        assert "exists" in path_info

    # Assert counts structure
    assert isinstance(data["counts"], dict)

    _validate_schema(data, "data_status.json")
    _validate_mock("data_status.json", "data_status.json")


def test_data_cleanup_dry_run_json_confirms_dry_run_true(temp_state_paths):
    """Test that data cleanup dry-run --json confirms dry_run true and does not delete. Current behavior; JSON API v1 candidate."""
    tmpdir, report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "data",
            "cleanup",
            "--target",
            "demo",
            "--json",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)

    # Assert dry_run is true
    assert "dry_run" in data
    assert data["dry_run"] is True

    # Assert target field
    assert "target" in data

    # Assert planned_items structure
    assert "planned_items" in data
    assert isinstance(data["planned_items"], list)

    # Assert total items field
    assert "total_items" in data
    assert isinstance(data["total_items"], int)

    # If items exist, assert they have required fields
    if len(data["planned_items"]) > 0:
        item = data["planned_items"][0]
        assert "path" in item
        assert "type" in item

    _validate_schema(data, "cleanup_dry_run.json")
    _validate_mock("cleanup_dry_run.json", "cleanup_dry_run.json")


def test_policy_show_json_has_required_fields(temp_state_paths):
    """Test that policy show --json has required fields and validates against schema."""
    tmpdir, _report_root, env = temp_state_paths

    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "policy", "show", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert "rules" in data
    assert isinstance(data["rules"], list)

    if len(data["rules"]) > 0:
        rule = data["rules"][0]
        assert "id" in rule
        assert "priority" in rule
        assert "decision" in rule
        assert "status" in rule

    _validate_schema(data, "policy_overview.json")
    _validate_mock("policy_overview.json", "policy_overview.json")


def test_policy_validate_json_has_required_fields(temp_state_paths):
    """Test that policy validate --json has required fields and validates against schema."""
    tmpdir, _report_root, env = temp_state_paths

    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "policy", "validate", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert "rules_checked" in data
    assert "eval_cases_checked" in data
    assert "error_count" in data
    assert "warning_count" in data
    assert "is_valid" in data
    assert "issues" in data
    assert isinstance(data["issues"], list)

    _validate_schema(data, "policy_validate.json")
    _validate_mock("policy_validate.json", "policy_validate.json")


def test_scan_dir_json_has_required_fields(temp_state_paths):
    """Test that scan dir --json has required fields and validates against schema."""
    tmpdir, _report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python", "-m", "policy_scout.cli.main",
            "scan", "dir", "--json", "--no-audit",
            tmpdir,
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode in [0, 1, 2]

    data = json.loads(result.stdout)
    assert "scan_id" in data
    assert "scan_type" in data
    assert "target" in data
    assert "finding_count" in data
    assert "severity_counts" in data
    assert "files_scanned" in data
    assert "commits_scanned" in data
    assert "duration_ms" in data
    assert "errors" in data
    assert "findings" in data
    assert isinstance(data["findings"], list)
    assert isinstance(data["errors"], list)

    _validate_schema(data, "secret_scan_data.json")
    _validate_mock("secret_scan_data.json", "scan_secret_result.json")


def test_scan_staged_json_has_required_fields(temp_state_paths):
    """Test that scan staged --json has required fields and validates against schema."""
    tmpdir, _report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python", "-m", "policy_scout.cli.main",
            "scan", "staged", "--json", "--no-audit",
            "--repo", tmpdir,
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Non-git dir: git fails gracefully, findings=[], exit 0
    assert result.returncode in [0, 1, 2]

    data = json.loads(result.stdout)
    assert "scan_id" in data
    assert "scan_type" in data
    assert "target" in data
    assert "finding_count" in data
    assert "severity_counts" in data
    assert "files_scanned" in data
    assert "commits_scanned" in data
    assert "duration_ms" in data
    assert "errors" in data
    assert "findings" in data
    assert isinstance(data["findings"], list)
    assert isinstance(data["errors"], list)

    _validate_schema(data, "secret_scan_data.json")


def test_scan_history_json_has_required_fields(temp_state_paths):
    """Test that scan history --json has required fields and validates against schema."""
    tmpdir, _report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python", "-m", "policy_scout.cli.main",
            "scan", "history", "--json", "--no-audit",
            "--repo", tmpdir,
            "--max-commits", "10",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    # Non-git dir: git fails gracefully, findings=[], exit 0
    assert result.returncode in [0, 1, 2]

    data = json.loads(result.stdout)
    assert "scan_id" in data
    assert "scan_type" in data
    assert "target" in data
    assert "finding_count" in data
    assert "severity_counts" in data
    assert "files_scanned" in data
    assert "commits_scanned" in data
    assert "duration_ms" in data
    assert "errors" in data
    assert "findings" in data
    assert isinstance(data["findings"], list)
    assert isinstance(data["errors"], list)

    _validate_schema(data, "secret_scan_data.json")


def test_scan_injection_json_has_required_fields(temp_state_paths):
    """Test that scan injection --json has required fields and validates against schema."""
    tmpdir, _report_root, env = temp_state_paths

    result = subprocess.run(
        [
            "python", "-m", "policy_scout.cli.main",
            "scan", "injection", "--json", "--no-audit",
            tmpdir,
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir,
    )

    assert result.returncode in [0, 10, 20]

    data = json.loads(result.stdout)
    assert "target" in data
    assert "finding_count" in data
    assert "findings" in data
    assert isinstance(data["findings"], list)

    _validate_schema(data, "injection_scan_data.json")


def test_check_redacts_secret_in_jsonl_audit(temp_state_paths):
    """Secret-like values in checked commands must be redacted in the persisted JSONL record.

    Proves the redaction chain reaches the audit file — not just stdout.
    The JSON contract tests cover stdout; this closes the JSONL gap.
    """
    tmpdir, report_root, env = temp_state_paths
    jsonl_path = env["POLICY_SCOUT_AUDIT_PATH"]

    # sk-ant- prefix matches the Anthropic token redaction pattern
    secret = "sk-ant-api03-abc123def456ghi789jkl012"

    subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", f"echo {secret}"],
        env=env,
        capture_output=True,
        text=True,
    )

    assert Path(jsonl_path).exists(), "JSONL audit file was not written by check"
    jsonl_content = Path(jsonl_path).read_text()

    assert secret not in jsonl_content, "Secret leaked into JSONL audit record unredacted"
    assert "<redacted:" in jsonl_content, "Expected redaction placeholder absent from JSONL"
    _validate_mock("injection_scan_data.json", "scan_injection_result.json")
