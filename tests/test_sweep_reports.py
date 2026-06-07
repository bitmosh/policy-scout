"""Tests for sweep report generation."""

import os
import tempfile
import json
from policy_scout.sweep.models import SweepResult, Finding
from policy_scout.reports.sweep_report import generate_sweep_report


def test_generate_sweep_report_creates_files():
    """Test that sweep report creates Markdown and JSON files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override report root
        os.environ["POLICY_SCOUT_REPORT_ROOT"] = tmpdir

        # Create sweep result
        sweep_result = SweepResult(
            sweep_id="sweep_123",
            sweep_type="project",
            project_root="/test/project",
            findings_count={"critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
            findings=[
                Finding(
                    sweep_id="sweep_123",
                    severity="high",
                    confidence="moderate",
                    category="suspicious_lifecycle_script",
                    title="Test finding",
                    location="package.json",
                    evidence_ref="test",
                    why_it_matters="Test",
                    recommended_action="Review",
                )
            ],
            could_not_verify=["test"],
        )

        # Generate report
        report = generate_sweep_report(sweep_result, audit_event_ids=[])

        # Check files exist
        assert os.path.exists(report.markdown_path)
        assert os.path.exists(report.json_path)

        # Check report ID
        assert report.report_id.startswith("report_")
        assert report.report_type == "project_sweep"


def test_generate_sweep_report_markdown_content():
    """Test that sweep report Markdown contains expected content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_REPORT_ROOT"] = tmpdir

        sweep_result = SweepResult(
            sweep_id="sweep_123",
            sweep_type="project",
            project_root="/test/project",
            findings_count={"critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
            findings=[
                Finding(
                    sweep_id="sweep_123",
                    severity="high",
                    confidence="moderate",
                    category="suspicious_lifecycle_script",
                    title="Test finding",
                    location="package.json",
                    evidence_ref="test",
                    why_it_matters="Test",
                    recommended_action="Review",
                )
            ],
        )

        report = generate_sweep_report(sweep_result, audit_event_ids=[])

        # Read Markdown content
        with open(report.markdown_path, "r") as f:
            markdown = f.read()

        # Check for expected sections
        assert "Scout Report" in markdown
        assert "Project Sweep" in markdown
        assert "Findings" in markdown
        assert "Test finding" in markdown
        assert "package.json" in markdown


def test_generate_sweep_report_json_content():
    """Test that sweep report JSON contains expected content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_REPORT_ROOT"] = tmpdir

        sweep_result = SweepResult(
            sweep_id="sweep_123",
            sweep_type="project",
            project_root="/test/project",
            findings_count={"critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
            findings=[
                Finding(
                    sweep_id="sweep_123",
                    severity="high",
                    confidence="moderate",
                    category="suspicious_lifecycle_script",
                    title="Test finding",
                    location="package.json",
                )
            ],
        )

        report = generate_sweep_report(sweep_result, audit_event_ids=[])

        # Read JSON content
        with open(report.json_path, "r") as f:
            json_data = json.load(f)

        # Check for expected fields
        assert json_data["report_id"] == report.report_id
        assert json_data["report_type"] == "project_sweep"
        assert json_data["sweep_id"] == "sweep_123"
        assert json_data["project_root"] == "/test/project"
        assert json_data["findings_count"]["high"] == 1
        assert len(json_data["findings"]) == 1
        assert json_data["findings"][0]["title"] == "Test finding"
        assert json_data["redaction_applied"]


def test_generate_sweep_report_with_no_findings():
    """Test sweep report with no findings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_REPORT_ROOT"] = tmpdir

        sweep_result = SweepResult(
            sweep_id="sweep_123",
            sweep_type="project",
            project_root="/test/project",
            findings_count={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            findings=[],
        )

        report = generate_sweep_report(sweep_result, audit_event_ids=[])

        # Should still create files
        assert os.path.exists(report.markdown_path)
        assert os.path.exists(report.json_path)

        # Check JSON
        with open(report.json_path, "r") as f:
            json_data = json.load(f)

        assert json_data["findings_count"]["high"] == 0
        assert len(json_data["findings"]) == 0


def test_generate_sweep_report_with_could_not_verify():
    """Test sweep report includes could_not_verify."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_REPORT_ROOT"] = tmpdir

        sweep_result = SweepResult(
            sweep_id="sweep_123",
            sweep_type="project",
            project_root="/test/project",
            findings_count={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            findings=[],
            could_not_verify=["Full node_modules scan (limited for performance)"],
        )

        report = generate_sweep_report(sweep_result, audit_event_ids=[])

        # Check Markdown
        with open(report.markdown_path, "r") as f:
            markdown = f.read()

        assert "Could Not Verify" in markdown
        assert "node_modules" in markdown

        # Check JSON
        with open(report.json_path, "r") as f:
            json_data = json.load(f)

    assert any("node_modules" in item for item in json_data["could_not_verify"])


def test_generate_quick_sweep_report_metadata_and_credential_signal():
    """Test quick system sweep reports are labeled correctly and cautious on credentials."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_REPORT_ROOT"] = tmpdir

        sweep_result = SweepResult(
            sweep_id="sweep_123",
            sweep_type="quick_system",
            platform="linux",
            findings_count={"critical": 0, "high": 0, "medium": 1, "low": 0, "info": 0},
            findings=[
                Finding(
                    sweep_id="sweep_123",
                    severity="medium",
                    confidence="high",
                    category="credential_exposure_signal",
                    title="Sensitive API key environment variable names present",
                    location="process environment",
                    evidence_ref="variables: OPENAI_API_KEY",
                    why_it_matters="Sensitive environment variable names are present.",
                    recommended_action="Review if these environment variables are expected.",
                )
            ],
        )

        report = generate_sweep_report(sweep_result, audit_event_ids=[])

        with open(report.markdown_path, "r") as f:
            markdown = f.read()
        with open(report.json_path, "r") as f:
            json_data = json.load(f)

        assert report.report_type == "system_quick_sweep"
        assert json_data["report_type"] == "system_quick_sweep"
        assert "Quick System Sweep" in markdown
        assert "Assessment: `possible`" in markdown
        assert "not confirmed exposure" in markdown
        assert json_data["credential_exposure_assessment"]["level"] == "possible"
