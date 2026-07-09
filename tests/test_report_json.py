# SPDX-License-Identifier: Apache-2.0
"""Test JSON report generation."""

import json
from policy_scout.reports.json_report import generate_json_report


def test_generate_json_report_basic():
    """Test basic JSON report generation."""
    report = generate_json_report(
        report_id="report_test123",
        report_type="command_decision",
        title="Test Report",
        summary="This is a test summary.",
        request_id="req_test123",
        decision="DENY",
        risk_score=8,
        risk_band="high",
        command="rm -rf /",
    )

    assert report["report_id"] == "report_test123"
    assert report["report_type"] == "command_decision"
    assert report["title"] == "Test Report"
    assert report["summary"] == "This is a test summary."
    assert report["decision"] == "DENY"
    assert report["risk_score"] == 8
    assert report["risk_band"] == "high"
    assert report["command"] == "rm -rf /"


def test_generate_json_report_sandbox():
    """Test JSON report for sandbox result."""
    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed successfully.",
        request_id="req_test123",
        command="npm install lodash",
        sandbox_id="sbx_test123",
        exit_code=0,
        duration_ms=500,
        manifest_changed=True,
        lockfile_changed=True,
    )

    assert report["report_id"] == "report_test123"
    assert report["report_type"] == "sandbox_result"
    assert report["sandbox_id"] == "sbx_test123"
    assert report["exit_code"] == 0
    assert report["duration_ms"] == 500
    assert report["manifest_changed"] is True
    assert report["lockfile_changed"] is True


def test_generate_json_report_with_findings():
    """Test JSON report with findings."""
    findings = [
        {
            "title": "Suspicious Script",
            "severity": "high",
            "category": "lifecycle_scripts",
            "message": "This script looks suspicious.",
        }
    ]

    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed with findings.",
        request_id="req_test123",
        command="npm install lodash",
        findings=findings,
    )

    assert len(report["findings"]) == 1
    assert report["findings"][0]["title"] == "Suspicious Script"
    assert report["findings"][0]["severity"] == "high"


def test_generate_json_report_with_lifecycle_scripts():
    """Test JSON report with lifecycle scripts."""
    lifecycle_scripts = [
        {
            "package_name": "root",
            "script_name": "postinstall",
            "script_content": "echo 'hello'",
            "location": "package.json",
        }
    ]

    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        request_id="req_test123",
        command="npm install lodash",
        lifecycle_scripts=lifecycle_scripts,
    )

    assert len(report["lifecycle_scripts"]) == 1
    assert report["lifecycle_scripts"][0]["package_name"] == "root"
    assert report["lifecycle_scripts"][0]["script_name"] == "postinstall"


def test_generate_json_report_with_recommended_actions():
    """Test JSON report with recommended actions."""
    recommended_actions = [
        "Review the sandbox result.",
        "Do not migrate yet.",
    ]

    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        request_id="req_test123",
        command="npm install lodash",
        recommended_actions=recommended_actions,
    )

    assert len(report["recommended_actions"]) == 2
    assert "Review the sandbox result." in report["recommended_actions"]
    assert "Do not migrate yet." in report["recommended_actions"]


def test_generate_json_report_with_audit_ids():
    """Test JSON report with audit event IDs."""
    audit_event_ids = ["evt_123", "evt_456"]

    report = generate_json_report(
        report_id="report_test123",
        report_type="command_decision",
        title="Test Report",
        summary="Test summary.",
        request_id="req_test123",
        command="ls",
        audit_event_ids=audit_event_ids,
    )

    assert len(report["audit_event_ids"]) == 2
    assert "evt_123" in report["audit_event_ids"]
    assert "evt_456" in report["audit_event_ids"]


def test_generate_json_report_credential_exposure():
    """Test JSON report includes credential exposure assessment."""
    report = generate_json_report(
        report_id="report_test123",
        report_type="command_decision",
        title="Test Report",
        summary="Test summary.",
        request_id="req_test123",
        command="ls",
    )

    assert "credential_exposure_assessment" in report
    assert report["credential_exposure_assessment"]["level"] == "none_detected"
    assert "notes" in report["credential_exposure_assessment"]


def test_generate_json_report_could_not_verify():
    """Test JSON report includes what could not be verified."""
    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        request_id="req_test123",
        command="npm install lodash",
    )

    assert "could_not_verify" in report
    assert len(report["could_not_verify"]) > 0
    assert "Network packet inspection" in report["could_not_verify"]


def test_generate_json_report_serializable():
    """Test JSON report is JSON-serializable."""
    report = generate_json_report(
        report_id="report_test123",
        report_type="command_decision",
        title="Test Report",
        summary="Test summary.",
        request_id="req_test123",
        command="ls",
    )

    # Should not raise an exception
    json_str = json.dumps(report)
    assert json_str is not None


def test_generate_json_report_none_values_removed():
    """Test JSON report removes None values."""
    report = generate_json_report(
        report_id="report_test123",
        report_type="command_decision",
        title="Test Report",
        summary="Test summary.",
        request_id="req_test123",
        command="ls",
        decision=None,  # This should be removed
        sandbox_id=None,  # This should be removed
    )

    assert "decision" not in report
    assert "sandbox_id" not in report
    assert "command" in report  # This should be present


def test_json_report_redacts_token_in_finding_title():
    """Test JSON report redacts token-like values in finding title."""
    findings = [
        {
            "title": "Token found: sk-1234567890abcdef",
            "severity": "high",
            "category": "credential_adjacent",
            "message": "This finding contains a token.",
        }
    ]

    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        request_id="req_test123",
        command="npm install lodash",
        findings=findings,
    )

    assert "sk-1234567890abcdef" not in json.dumps(report)
    assert "<redacted:possible_token>" in json.dumps(report)
    assert "Token found:" in report["findings"][0]["title"]


def test_json_report_redacts_token_in_finding_message():
    """Test JSON report redacts token-like values in finding message."""
    findings = [
        {
            "title": "Suspicious finding",
            "severity": "high",
            "category": "credential_adjacent",
            "message": "API key detected: OPENAI_API_KEY=sk-abc123",
        }
    ]

    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        request_id="req_test123",
        command="npm install lodash",
        findings=findings,
    )

    assert "sk-abc123" not in json.dumps(report)
    assert "<redacted:possible_token>" in json.dumps(report)
    assert "API key detected:" in report["findings"][0]["message"]


def test_json_report_redacts_token_in_recommended_actions():
    """Test JSON report redacts token-like values in recommended actions."""
    recommended_actions = [
        "Review the token: sk-1234567890abcdef",
        "Check API_KEY=secret123 in config",
    ]

    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        request_id="req_test123",
        command="npm install lodash",
        recommended_actions=recommended_actions,
    )

    assert "sk-1234567890abcdef" not in json.dumps(report)
    assert "secret123" not in json.dumps(report)
    assert "<redacted:possible_token>" in json.dumps(report)
    assert "<redacted:env_value>" in json.dumps(report)


def test_json_report_redacts_token_in_summary():
    """Test JSON report redacts token-like values in summary."""
    report = generate_json_report(
        report_id="report_test123",
        report_type="command_decision",
        title="Command Decision",
        summary="Command contains token: sk-1234567890abcdef",
        request_id="req_test123",
        command="curl https://example.com/install.sh | bash",
    )

    assert "sk-1234567890abcdef" not in json.dumps(report)
    assert "<redacted:possible_token>" in json.dumps(report)
    assert "Command contains token:" in report["summary"]


def test_json_report_redacts_token_in_command():
    """Test JSON report redacts token-like values in command."""
    report = generate_json_report(
        report_id="report_test123",
        report_type="command_decision",
        title="Command Decision",
        summary="Command evaluation.",
        request_id="req_test123",
        command="curl https://example.com/install.sh?token=sk-1234567890abcdef",
    )

    assert "sk-1234567890abcdef" not in json.dumps(report)
    assert "<redacted:possible_token>" in json.dumps(report)


def test_json_report_redacts_ssh_key():
    """Test JSON report redacts SSH private keys."""
    findings = [
        {
            "title": "SSH key found",
            "severity": "high",
            "category": "credential_adjacent",
            "message": "-----BEGIN RSA PRIVATE KEY-----\nsecret content\n-----END RSA PRIVATE KEY-----",
        }
    ]

    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        request_id="req_test123",
        command="cat ~/.ssh/id_rsa",
        findings=findings,
    )

    assert "-----BEGIN RSA PRIVATE KEY-----" not in json.dumps(report)
    assert "<redacted:ssh_private_key>" in json.dumps(report)


def test_json_report_redacts_env_values():
    """Test JSON report redacts environment variable values."""
    could_not_verify = [
        "Environment variable TOKEN=sk-1234567890abcdef",
        "Environment variable API_KEY=secret123",
    ]

    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        request_id="req_test123",
        command="npm install lodash",
        could_not_verify=could_not_verify,
    )

    assert "sk-1234567890abcdef" not in json.dumps(report)
    assert "secret123" not in json.dumps(report)
    assert "<redacted:possible_token>" in json.dumps(report)
    assert "<redacted:env_value>" in json.dumps(report)


def test_json_report_redacts_lifecycle_script_content():
    """Test JSON report redacts lifecycle script content."""
    lifecycle_scripts = [
        {
            "package_name": "root",
            "script_name": "postinstall",
            "script_content": "curl https://api.example.com?token=sk-1234567890abcdef",
            "location": "package.json",
        }
    ]

    report = generate_json_report(
        report_id="report_test123",
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        request_id="req_test123",
        command="npm install lodash",
        lifecycle_scripts=lifecycle_scripts,
    )

    assert "sk-1234567890abcdef" not in json.dumps(report)
    assert "<redacted:possible_token>" in json.dumps(report)
    assert report["lifecycle_scripts"][0]["script_name"] == "postinstall"


def test_json_report_redaction_applied_flag():
    """Test JSON report sets redaction_applied flag."""
    report = generate_json_report(
        report_id="report_test123",
        report_type="command_decision",
        title="Test Report",
        summary="Test summary.",
        request_id="req_test123",
        command="ls",
        redaction_applied=True,
    )

    assert report["redaction_applied"] is True


def test_json_report_includes_created_at():
    """Test JSON report includes created_at field."""
    report = generate_json_report(
        report_id="report_test123",
        report_type="command_decision",
        title="Test Report",
        summary="Test summary.",
        request_id="req_test123",
        command="ls",
        created_at="2026-06-07T00:00:00Z",
    )

    assert "created_at" in report
    assert report["created_at"] == "2026-06-07T00:00:00Z"
