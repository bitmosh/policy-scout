"""Test Markdown report generation."""

from policy_scout.reports.markdown_report import generate_markdown_report


def test_generate_markdown_report_basic():
    """Test basic Markdown report generation."""
    markdown = generate_markdown_report(
        report_type="command_decision",
        title="Test Report",
        summary="This is a test summary.",
        decision="DENY",
        risk_score=8,
        risk_band="high",
        command="rm -rf /",
    )

    assert "# Scout Report: Test Report" in markdown
    assert "## 1. Summary" in markdown
    assert "This is a test summary." in markdown
    assert "## 2. Redaction Applied" in markdown
    assert "## 3. Decision / Risk Level" in markdown
    assert "DENY" in markdown
    assert "8/10" in markdown
    assert "high" in markdown
    assert "## 4. Triggering Command" in markdown
    assert "rm -rf /" in markdown


def test_generate_markdown_report_sandbox():
    """Test Markdown report for sandbox result."""
    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed successfully.",
        command="npm install lodash",
        sandbox_id="sbx_test123",
        exit_code=0,
        duration_ms=500,
        lifecycle_scripts=[],
        manifest_changed=True,
        lockfile_changed=True,
    )

    assert "# Scout Report: Sandbox Result" in markdown
    assert "sbx_test123" in markdown
    assert "500ms" in markdown
    assert "Exit Code: `0`" in markdown
    assert "## 5. Timeline" in markdown
    assert "## 7. Evidence" in markdown
    assert "package.json changed" in markdown
    assert "package-lock.json or npm-shrinkwrap.json changed" in markdown


def test_generate_markdown_report_with_findings():
    """Test Markdown report with findings."""
    findings = [
        {
            "title": "Suspicious Script",
            "severity": "high",
            "category": "lifecycle_scripts",
            "message": "This script looks suspicious.",
        }
    ]

    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed with findings.",
        command="npm install lodash",
        findings=findings,
    )

    assert "## 6. Findings" in markdown
    assert "### Finding 1: Suspicious Script" in markdown
    assert "high" in markdown
    assert "lifecycle_scripts" in markdown
    assert "This script looks suspicious." in markdown


def test_generate_markdown_report_with_lifecycle_scripts():
    """Test Markdown report with lifecycle scripts."""
    lifecycle_scripts = [
        {
            "package_name": "root",
            "script_name": "postinstall",
            "script_content": "echo 'hello'",
            "location": "package.json",
        }
    ]

    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        command="npm install lodash",
        lifecycle_scripts=lifecycle_scripts,
    )

    assert "## 8. Lifecycle Scripts" in markdown
    assert "Total lifecycle scripts found: 1" in markdown
    assert "root" in markdown
    assert "postinstall" in markdown


def test_generate_markdown_report_with_recommended_actions():
    """Test Markdown report with recommended actions."""
    recommended_actions = [
        "Review the sandbox result.",
        "Do not migrate yet.",
    ]

    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        command="npm install lodash",
        recommended_actions=recommended_actions,
    )

    assert "## 10. Recommended Actions" in markdown
    assert "1. Review the sandbox result." in markdown
    assert "2. Do not migrate yet." in markdown


def test_generate_markdown_report_with_audit_ids():
    """Test Markdown report with audit event IDs."""
    audit_event_ids = ["evt_123", "evt_456"]

    markdown = generate_markdown_report(
        report_type="command_decision",
        title="Test Report",
        summary="Test summary.",
        command="ls",
        audit_event_ids=audit_event_ids,
    )

    assert "## 14. Audit Event IDs" in markdown
    assert "evt_123" in markdown
    assert "evt_456" in markdown


def test_generate_markdown_report_host_status():
    """Test Markdown report includes host project status for sandbox."""
    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        command="npm install lodash",
        host_mutation_status="NOT MUTATED",
        migration_status="Not performed, requires approval",
    )

    assert "## 13. Host Project Status" in markdown
    assert "NOT MUTATED" in markdown
    assert "Not performed, requires approval" in markdown


def test_generate_markdown_report_could_not_verify():
    """Test Markdown report includes what could not be verified."""
    could_not_verify = [
        "Network packet inspection",
        "Full malware analysis",
    ]

    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        command="npm install lodash",
        could_not_verify=could_not_verify,
    )

    assert "## 12. What Policy Scout Could Not Verify" in markdown
    assert "Network packet inspection" in markdown
    assert "Full malware analysis" in markdown


def test_markdown_report_redacts_token_in_finding_title():
    """Test Markdown report redacts token-like values in finding title."""
    findings = [
        {
            "title": "Token found: sk-1234567890abcdef",
            "severity": "high",
            "category": "credential_adjacent",
            "message": "This finding contains a token.",
        }
    ]

    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        command="npm install lodash",
        findings=findings,
    )

    assert "sk-1234567890abcdef" not in markdown
    assert "<redacted:possible_token>" in markdown
    assert "Token found:" in markdown


def test_markdown_report_redacts_token_in_finding_message():
    """Test Markdown report redacts token-like values in finding message."""
    findings = [
        {
            "title": "Suspicious finding",
            "severity": "high",
            "category": "credential_adjacent",
            "message": "API key detected: OPENAI_API_KEY=sk-abc123",
        }
    ]

    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        command="npm install lodash",
        findings=findings,
    )

    assert "sk-abc123" not in markdown
    assert "<redacted:possible_token>" in markdown
    assert "API key detected:" in markdown


def test_markdown_report_redacts_token_in_recommended_actions():
    """Test Markdown report redacts token-like values in recommended actions."""
    recommended_actions = [
        "Review the token: sk-1234567890abcdef",
        "Check API_KEY=secret123 in config",
    ]

    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        command="npm install lodash",
        recommended_actions=recommended_actions,
    )

    assert "sk-1234567890abcdef" not in markdown
    assert "secret123" not in markdown
    assert "<redacted:possible_token>" in markdown
    assert "<redacted:env_value>" in markdown
    assert "Review the token:" in markdown


def test_markdown_report_redacts_token_in_summary():
    """Test Markdown report redacts token-like values in summary."""
    markdown = generate_markdown_report(
        report_type="command_decision",
        title="Command Decision",
        summary="Command contains token: sk-1234567890abcdef",
        command="curl https://example.com/install.sh | bash",
    )

    assert "sk-1234567890abcdef" not in markdown
    assert "<redacted:possible_token>" in markdown
    assert "Command contains token:" in markdown


def test_markdown_report_redacts_token_in_command():
    """Test Markdown report redacts token-like values in command."""
    markdown = generate_markdown_report(
        report_type="command_decision",
        title="Command Decision",
        summary="Command evaluation.",
        command="curl https://example.com/install.sh?token=sk-1234567890abcdef",
    )

    assert "sk-1234567890abcdef" not in markdown
    assert "<redacted:possible_token>" in markdown
    assert "curl https://example.com/install.sh?token=" in markdown


def test_markdown_report_redacts_ssh_key():
    """Test Markdown report redacts SSH private keys."""
    markdown = generate_markdown_report(
        report_type="command_decision",
        title="Command Decision",
        summary="Command contains SSH key.",
        command="cat ~/.ssh/id_rsa",
    )

    # The command itself doesn't contain the key, but if it did
    # it would be redacted. This test verifies the redaction pattern exists.
    # We'll test with a finding that contains a key
    findings = [
        {
            "title": "SSH key found",
            "severity": "high",
            "category": "credential_adjacent",
            "message": "-----BEGIN RSA PRIVATE KEY-----\nsecret content\n-----END RSA PRIVATE KEY-----",
        }
    ]

    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        command="cat ~/.ssh/id_rsa",
        findings=findings,
    )

    assert "-----BEGIN RSA PRIVATE KEY-----" not in markdown
    assert "<redacted:ssh_private_key>" in markdown


def test_markdown_report_redacts_env_values():
    """Test Markdown report redacts environment variable values."""
    could_not_verify = [
        "Environment variable TOKEN=sk-1234567890abcdef",
        "Environment variable API_KEY=secret123",
    ]

    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        command="npm install lodash",
        could_not_verify=could_not_verify,
    )

    assert "sk-1234567890abcdef" not in markdown
    assert "secret123" not in markdown
    assert "<redacted:possible_token>" in markdown
    assert "<redacted:env_value>" in markdown
    assert "Environment variable TOKEN=" in markdown
    # The API_KEY pattern redacts the entire assignment, so we check for the placeholder
    assert "<redacted:env_value>" in markdown


def test_markdown_report_redacts_lifecycle_script_content():
    """Test Markdown report redacts lifecycle script content."""
    lifecycle_scripts = [
        {
            "package_name": "root",
            "script_name": "postinstall",
            "script_content": "curl https://api.example.com?token=sk-1234567890abcdef",
            "location": "package.json",
        }
    ]

    markdown = generate_markdown_report(
        report_type="sandbox_result",
        title="Sandbox Result",
        summary="Sandbox completed.",
        command="npm install lodash",
        lifecycle_scripts=lifecycle_scripts,
    )

    assert "sk-1234567890abcdef" not in markdown
    assert "<redacted:possible_token>" in markdown
    assert "postinstall" in markdown
    assert "root" in markdown


def test_markdown_report_includes_redaction_section():
    """Test Markdown report includes redaction visibility section."""
    markdown = generate_markdown_report(
        report_type="command_decision",
        title="Test Report",
        summary="Test summary.",
        command="ls",
    )

    assert "## 2. Redaction Applied" in markdown
    assert "This report has been redacted to protect sensitive information" in markdown
    assert "<redacted:possible_token>" in markdown
    assert "<redacted:ssh_private_key>" in markdown
    assert "<redacted:env_value>" in markdown
