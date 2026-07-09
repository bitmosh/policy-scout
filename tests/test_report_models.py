# SPDX-License-Identifier: Apache-2.0
"""Test report models."""

from policy_scout.reports.models import ScoutReport


def test_scout_report_structure():
    """Test ScoutReport has required fields."""
    report = ScoutReport(
        report_id="report_test123",
        report_type="command_decision",
        title="Test Report",
        request_id="req_test123",
    )

    assert report.report_id == "report_test123"
    assert report.report_type == "command_decision"
    assert report.title == "Test Report"
    assert report.request_id == "req_test123"
    assert report.schema_version == 1


def test_scout_report_to_dict():
    """Test ScoutReport serialization."""
    report = ScoutReport(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Test",
        request_id="req_test123",
        sandbox_id="sbx_test123",
    )

    data = report.to_dict()

    assert data["report_id"] == "report_test123"
    assert data["report_type"] == "sandbox_result"
    assert data["sandbox_id"] == "sbx_test123"
    assert data["schema_version"] == 1


def test_scout_report_from_dict():
    """Test ScoutReport deserialization."""
    data = {
        "report_id": "report_test123",
        "report_type": "command_decision",
        "title": "Test",
        "created_at": "2024-01-01T00:00:00Z",
        "request_id": "req_test123",
        "evaluation_id": "eval_test123",
        "decision_id": "dec_test123",
        "sandbox_id": "sbx_test123",
        "findings": [],
        "audit_event_ids": [],
        "markdown_path": "/path/to/report.md",
        "json_path": "/path/to/report.json",
        "schema_version": 1,
    }

    report = ScoutReport.from_dict(data)

    assert report.report_id == "report_test123"
    assert report.report_type == "command_decision"
    assert report.evaluation_id == "eval_test123"
    assert report.decision_id == "dec_test123"
    assert report.sandbox_id == "sbx_test123"


def test_scout_report_id_starts_with_report():
    """Test that default report IDs start with 'report_'."""
    report = ScoutReport()

    assert report.report_id.startswith("report_")


def test_scout_report_defaults():
    """Test ScoutReport default values."""
    report = ScoutReport()

    assert report.report_type == ""
    assert report.title == ""
    assert report.request_id == ""
    assert report.evaluation_id is None
    assert report.decision_id is None
    assert report.sandbox_id is None
    assert report.findings == []
    assert report.audit_event_ids == []
    assert report.markdown_path == ""
    assert report.json_path == ""
    assert report.schema_version == 1
