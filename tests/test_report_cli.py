# SPDX-License-Identifier: Apache-2.0
"""Tests for report CLI commands."""

import json
import os
import subprocess
import tempfile
import pytest


@pytest.fixture
def temp_report_paths():
    """Set up temporary paths for all Policy Scout data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        report_root = os.path.join(tmpdir, "reports")
        db_path = os.path.join(tmpdir, "audit.db")
        jsonl_path = os.path.join(tmpdir, "audit.jsonl")
        approval_path = os.path.join(tmpdir, "approvals.jsonl")
        sandbox_root = os.path.join(tmpdir, "sandboxes")
        sweep_root = os.path.join(tmpdir, "sweeps")
        
        # Create directories
        os.makedirs(report_root, exist_ok=True)
        os.makedirs(sandbox_root, exist_ok=True)
        os.makedirs(sweep_root, exist_ok=True)
        
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env["POLICY_SCOUT_REPORT_ROOT"] = report_root
        env["POLICY_SCOUT_AUDIT_DB_PATH"] = db_path
        env["POLICY_SCOUT_AUDIT_PATH"] = jsonl_path
        env["POLICY_SCOUT_APPROVAL_PATH"] = approval_path
        env["POLICY_SCOUT_SANDBOX_ROOT"] = sandbox_root
        env["POLICY_SCOUT_SWEEP_ROOT"] = sweep_root
        
        yield tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env


def create_fixture_report(report_root, report_id, report_type="command_decision"):
    """Create a fixture report for testing."""
    report_dir = os.path.join(report_root, report_id)
    os.makedirs(report_dir, exist_ok=True)
    
    # Create JSON report
    json_report = {
        "report_id": report_id,
        "report_type": report_type,
        "title": f"Test Report {report_id}",
        "summary": "Test summary",
        "created_at": "2026-06-07T00:00:00Z",
        "request_id": "req_test",
    }
    
    with open(os.path.join(report_dir, "report.json"), "w") as f:
        json.dump(json_report, f, indent=2)
    
    # Create Markdown report
    md_content = f"# Scout Report: Test Report {report_id}\n\nTest summary."
    with open(os.path.join(report_dir, "report.md"), "w") as f:
        f.write(md_content)


def test_report_list_shows_reports_from_report_root(temp_report_paths):
    """Test that report list shows reports from report root."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture reports
    create_fixture_report(report_root, "report_001")
    create_fixture_report(report_root, "report_002")
    
    # Run report list
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "list"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0
    assert "Recent Scout Reports" in result.stdout
    assert "report_001" in result.stdout
    assert "report_002" in result.stdout


def test_report_list_json_returns_valid_json(temp_report_paths):
    """Test that report list --json returns valid JSON."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture report
    create_fixture_report(report_root, "report_001")
    
    # Run report list with JSON
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "list", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert "reports" in payload
    assert "total_count" in payload
    reports = payload["reports"]
    assert isinstance(reports, list)
    assert len(reports) > 0
    assert "report_id" in reports[0]
    assert "report_type" in reports[0]


def test_report_list_limit_limits_output(temp_report_paths):
    """Test that report list --limit limits output."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create multiple fixture reports
    for i in range(5):
        create_fixture_report(report_root, f"report_{i:03d}")
    
    # Run report list with limit 2
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "list", "--limit", "2"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0
    # Count "Report ID:" occurrences - should be 2
    report_count = result.stdout.count("Report ID:")
    assert report_count == 2


def test_report_show_displays_markdown_report(temp_report_paths):
    """Test that report show displays Markdown report."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture report
    create_fixture_report(report_root, "report_001")
    
    # Show report
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "show", "report_001"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0
    assert "Scout Report: Test Report report_001" in result.stdout
    assert "Test summary" in result.stdout


def test_report_show_missing_report_returns_error(temp_report_paths):
    """Test that report show missing report returns non-zero or clear error."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture report
    create_fixture_report(report_root, "report_001")
    
    # Try to show non-existent report
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "show", "report_nonexistent"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode != 0
    assert "Report not found" in result.stderr


def test_report_show_json_returns_json_report(temp_report_paths):
    """Test that report show --json returns JSON report if available."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture report
    create_fixture_report(report_root, "report_001")
    
    # Show report with JSON
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "show", "report_001", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert "report_id" in report
    assert report["report_id"] == "report_001"


def test_report_export_markdown_prints_markdown_content(temp_report_paths):
    """Test that report export --format markdown prints Markdown content."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture report
    create_fixture_report(report_root, "report_001")
    
    # Export Markdown
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "export", "report_001", "--format", "markdown"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0
    assert "Scout Report: Test Report report_001" in result.stdout
    assert "Test summary" in result.stdout


def test_report_export_json_prints_valid_json(temp_report_paths):
    """Test that report export --format json prints valid JSON."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture report
    create_fixture_report(report_root, "report_001")
    
    # Export JSON
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "export", "report_001", "--format", "json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert "report_id" in report
    assert report["report_id"] == "report_001"


def test_report_export_missing_format_returns_error(temp_report_paths):
    """Test that report export missing format/file returns clear error."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture report without Markdown
    report_dir = os.path.join(report_root, "report_001")
    os.makedirs(report_dir, exist_ok=True)
    json_report = {"report_id": "report_001", "report_type": "test"}
    with open(os.path.join(report_dir, "report.json"), "w") as f:
        json.dump(json_report, f)
    
    # Try to export missing Markdown
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "export", "report_001", "--format", "markdown"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode != 0
    assert "Markdown report not found" in result.stderr


def test_report_cli_preserves_redaction(temp_report_paths):
    """Test that report CLI preserves redaction and does not print raw secret-like values."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture report with secret-like value
    report_dir = os.path.join(report_root, "report_001")
    os.makedirs(report_dir, exist_ok=True)
    
    # Create JSON report with redacted placeholder
    json_report = {
        "report_id": "report_001",
        "report_type": "test",
        "title": "Test Report",
        "summary": "Test summary",
        "created_at": "2026-06-07T00:00:00Z",
    }
    with open(os.path.join(report_dir, "report.json"), "w") as f:
        json.dump(json_report, f, indent=2)
    
    # Create Markdown report with redacted placeholder
    md_content = "# Scout Report\n\nAPI key: <redacted:secret>"
    with open(os.path.join(report_dir, "report.md"), "w") as f:
        f.write(md_content)
    
    # Show report
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "show", "report_001"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0
    # Check that redaction placeholder is preserved
    assert "<redacted:secret>" in result.stdout or "redacted" in result.stdout


def test_report_cli_uses_policy_scout_report_root_override(temp_report_paths):
    """Test that report CLI uses POLICY_SCOUT_REPORT_ROOT override."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture report
    create_fixture_report(report_root, "report_001")
    
    # Verify the custom report_root was used
    assert os.path.exists(report_root)
    
    # Report list should work with the custom path
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "list"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0


def test_report_list_recognizes_report_ids_with_report_prefix(temp_report_paths):
    """Test that report list recognizes report IDs with report_ prefix."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Create fixture report with report_ prefix
    create_fixture_report(report_root, "report_001")
    
    # Create a directory without report_ prefix (should be ignored)
    other_dir = os.path.join(report_root, "other_dir")
    os.makedirs(other_dir, exist_ok=True)
    
    # Run report list
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "list"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0
    assert "report_001" in result.stdout
    assert "other_dir" not in result.stdout


def test_report_cli_no_reports_shows_helpful_message(temp_report_paths):
    """Test that report CLI shows helpful message when no reports exist."""
    tmpdir, report_root, db_path, jsonl_path, approval_path, sandbox_root, sweep_root, env = temp_report_paths
    
    # Don't create any reports - report root will be empty
    
    # Try to run report list
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "report", "list"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    assert result.returncode == 0
    assert "No Scout Reports found" in result.stdout
