"""Test sandbox report generation."""

import os
import json
import tempfile
from pathlib import Path
from policy_scout.reports.sandbox_report import generate_sandbox_report
from policy_scout.sandbox.models import SandboxResult, LifecycleScript


def test_generate_sandbox_report_basic():
    """Test basic sandbox report generation."""
    os.environ["POLICY_SCOUT_REPORT_ROOT"] = tempfile.mkdtemp()

    try:
        sandbox_result = SandboxResult(
            sandbox_id="sbx_test123",
            request_id="req_test123",
            command="npm install lodash",
            package_manager="npm",
            temp_workspace="/tmp/sandbox",
            exit_code=0,
            duration_ms=500,
            stdout="",
            stderr="",
            manifest_changed=True,
            lockfile_changed=True,
            lifecycle_scripts_found=[],
            findings=[],
            migration_available=True,
            migration_requires_approval=True,
        )

        report = generate_sandbox_report(sandbox_result)

        assert report.report_id.startswith("report_")
        assert report.report_type == "sandbox_result"
        assert report.request_id == "req_test123"
        assert report.sandbox_id == "sbx_test123"
        assert Path(report.markdown_path).exists()
        assert Path(report.json_path).exists()

        # Check markdown content
        markdown_content = Path(report.markdown_path).read_text()
        assert "Sandbox Result: npm install lodash" in markdown_content
        assert "sbx_test123" in markdown_content
        assert "Exit Code: `0`" in markdown_content
        assert "500ms" in markdown_content
        assert "NOT MUTATED" in markdown_content

        # Check JSON content
        import json

        json_content = json.loads(Path(report.json_path).read_text())
        assert json_content["report_id"] == report.report_id
        assert json_content["sandbox_id"] == "sbx_test123"
        assert json_content["exit_code"] == 0
        assert json_content["host_mutation_status"] == "NOT MUTATED"
    finally:
        del os.environ["POLICY_SCOUT_REPORT_ROOT"]


def test_generate_sandbox_report_with_lifecycle_scripts():
    """Test sandbox report with lifecycle scripts."""
    os.environ["POLICY_SCOUT_REPORT_ROOT"] = tempfile.mkdtemp()

    try:
        lifecycle_scripts = [
            LifecycleScript(
                package_name="root",
                script_name="postinstall",
                script_content="echo 'hello'",
                location="package.json",
            )
        ]

        sandbox_result = SandboxResult(
            sandbox_id="sbx_test123",
            request_id="req_test123",
            command="npm install lodash",
            package_manager="npm",
            temp_workspace="/tmp/sandbox",
            exit_code=0,
            duration_ms=500,
            stdout="",
            stderr="",
            manifest_changed=True,
            lockfile_changed=True,
            lifecycle_scripts_found=lifecycle_scripts,
            findings=[],
            migration_available=True,
            migration_requires_approval=True,
        )

        report = generate_sandbox_report(sandbox_result)

        markdown_content = Path(report.markdown_path).read_text()
        assert "## 8. Lifecycle Scripts" in markdown_content
        assert "Total lifecycle scripts found: 1" in markdown_content
        assert "root" in markdown_content
        assert "postinstall" in markdown_content

        json_content = json.loads(Path(report.json_path).read_text())
        assert len(json_content["lifecycle_scripts"]) == 1
        assert json_content["lifecycle_scripts"][0]["package_name"] == "root"
    finally:
        del os.environ["POLICY_SCOUT_REPORT_ROOT"]


def test_generate_sandbox_report_with_findings():
    """Test sandbox report with findings."""
    os.environ["POLICY_SCOUT_REPORT_ROOT"] = tempfile.mkdtemp()

    try:
        findings = [
            {
                "type": "warning",
                "message": "Skipped files with token-like content: .npmrc",
            }
        ]

        sandbox_result = SandboxResult(
            sandbox_id="sbx_test123",
            request_id="req_test123",
            command="npm install lodash",
            package_manager="npm",
            temp_workspace="/tmp/sandbox",
            exit_code=0,
            duration_ms=500,
            stdout="",
            stderr="",
            manifest_changed=True,
            lockfile_changed=True,
            lifecycle_scripts_found=[],
            findings=findings,
            migration_available=True,
            migration_requires_approval=True,
        )

        report = generate_sandbox_report(sandbox_result)

        markdown_content = Path(report.markdown_path).read_text()
        assert "## 6. Findings" in markdown_content
        assert "Skipped files with token-like content" in markdown_content

        json_content = json.loads(Path(report.json_path).read_text())
        assert len(json_content["findings"]) == 1
    finally:
        del os.environ["POLICY_SCOUT_REPORT_ROOT"]


def test_generate_sandbox_report_failed_install():
    """Test sandbox report for failed install."""
    os.environ["POLICY_SCOUT_REPORT_ROOT"] = tempfile.mkdtemp()

    try:
        sandbox_result = SandboxResult(
            sandbox_id="sbx_test123",
            request_id="req_test123",
            command="npm install nonexistent-package",
            package_manager="npm",
            temp_workspace="/tmp/sandbox",
            exit_code=1,
            duration_ms=200,
            stdout="",
            stderr="Error: package not found",
            manifest_changed=False,
            lockfile_changed=False,
            lifecycle_scripts_found=[],
            findings=[],
            migration_available=False,
            migration_requires_approval=True,
        )

        report = generate_sandbox_report(sandbox_result)

        markdown_content = Path(report.markdown_path).read_text()
        assert "Exit Code: `1`" in markdown_content
        assert "The sandbox install failed" in markdown_content

        json_content = json.loads(Path(report.json_path).read_text())
        assert json_content["exit_code"] == 1
    finally:
        del os.environ["POLICY_SCOUT_REPORT_ROOT"]


def test_generate_sandbox_report_with_audit_ids():
    """Test sandbox report with audit event IDs."""
    os.environ["POLICY_SCOUT_REPORT_ROOT"] = tempfile.mkdtemp()

    try:
        audit_event_ids = ["evt_123", "evt_456"]
        sandbox_result = SandboxResult(
            sandbox_id="sbx_test123",
            request_id="req_test123",
            command="npm install lodash",
            package_manager="npm",
            temp_workspace="/tmp/sandbox",
            exit_code=0,
            duration_ms=500,
            stdout="",
            stderr="",
            manifest_changed=True,
            lockfile_changed=True,
            lifecycle_scripts_found=[],
            findings=[],
            migration_available=True,
            migration_requires_approval=True,
        )

        report = generate_sandbox_report(
            sandbox_result, audit_event_ids=audit_event_ids
        )

        assert report.audit_event_ids == audit_event_ids

        markdown_content = Path(report.markdown_path).read_text()
        assert "evt_123" in markdown_content
        assert "evt_456" in markdown_content
    finally:
        del os.environ["POLICY_SCOUT_REPORT_ROOT"]


def test_generate_sandbox_report_files_changed():
    """Test sandbox report includes files changed section."""
    os.environ["POLICY_SCOUT_REPORT_ROOT"] = tempfile.mkdtemp()

    try:
        sandbox_result = SandboxResult(
            sandbox_id="sbx_test123",
            request_id="req_test123",
            command="npm install lodash",
            package_manager="npm",
            temp_workspace="/tmp/sandbox",
            exit_code=0,
            duration_ms=500,
            stdout="",
            stderr="",
            manifest_changed=True,
            lockfile_changed=False,
            lifecycle_scripts_found=[],
            findings=[],
            migration_available=True,
            migration_requires_approval=True,
        )

        report = generate_sandbox_report(sandbox_result)

        markdown_content = Path(report.markdown_path).read_text()
        assert "## 11. Files Changed" in markdown_content
        assert "package.json: CHANGED" in markdown_content
        assert "package-lock.json or npm-shrinkwrap.json: NO CHANGE" in markdown_content
    finally:
        del os.environ["POLICY_SCOUT_REPORT_ROOT"]
