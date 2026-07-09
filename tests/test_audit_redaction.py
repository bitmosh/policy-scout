# SPDX-License-Identifier: Apache-2.0
"""Tests for audit redaction."""

from policy_scout.audit.redaction import redact_string, redact_dict, redact_list


def test_redact_openai_api_key():
    """Test redaction of OPENAI_API_KEY."""
    text = "OPENAI_API_KEY=sk-abc123def456"
    redacted = redact_string(text)
    assert "sk-abc123def456" not in redacted
    assert "<redacted:possible_token>" in redacted


def test_redact_anthropic_api_key():
    """Test redaction of ANTHROPIC_API_KEY."""
    text = "ANTHROPIC_API_KEY=sk-ant-xyz789"
    redacted = redact_string(text)
    assert "sk-ant-xyz789" not in redacted
    assert "<redacted:possible_token>" in redacted


def test_redact_npm_token():
    """Test redaction of NPM_TOKEN."""
    text = "NPM_TOKEN=npm_123456"
    redacted = redact_string(text)
    assert "npm_123456" not in redacted
    assert "<redacted:possible_token>" in redacted


def test_redact_github_token():
    """Test redaction of GITHUB_TOKEN."""
    text = "GITHUB_TOKEN=ghp_abc123"
    redacted = redact_string(text)
    assert "ghp_abc123" not in redacted
    assert "<redacted:possible_token>" in redacted


def test_redact_aws_secret():
    """Test redaction of AWS_SECRET_ACCESS_KEY."""
    text = "AWS_SECRET_ACCESS_KEY=awsXYZ123/+=abc"
    redacted = redact_string(text)
    assert "awsXYZ123/+=abc" not in redacted
    assert "<redacted:possible_token>" in redacted


def test_redact_sk_token():
    """Test redaction of sk- tokens."""
    text = "sk-abc123def456"
    redacted = redact_string(text)
    assert "sk-abc123def456" not in redacted
    assert "<redacted:possible_token>" in redacted


def test_redact_ssh_private_key():
    """Test redaction of SSH private key header."""
    text = "-----BEGIN RSA PRIVATE KEY-----"
    redacted = redact_string(text)
    assert "-----BEGIN RSA PRIVATE KEY-----" not in redacted
    assert "<redacted:ssh_private_key>" in redacted


def test_redact_token_equals():
    """Test redaction of TOKEN= pattern."""
    text = "TOKEN=secret123"
    redacted = redact_string(text)
    assert "secret123" not in redacted
    assert "<redacted:env_value>" in redacted


def test_redact_api_key_equals():
    """Test redaction of API_KEY= pattern."""
    text = "API_KEY=abc123xyz"
    redacted = redact_string(text)
    assert "abc123xyz" not in redacted
    assert "<redacted:env_value>" in redacted


def test_redact_secret_equals():
    """Test redaction of SECRET= pattern."""
    text = "SECRET=mysecret"
    redacted = redact_string(text)
    assert "mysecret" not in redacted
    assert "<redacted:env_value>" in redacted


def test_redact_password_equals():
    """Test redaction of PASSWORD= pattern."""
    text = "PASSWORD=mypassword123"
    redacted = redact_string(text)
    assert "mypassword123" not in redacted
    assert "<redacted:env_value>" in redacted


def test_redact_url_param_secret():
    """Test redaction of URL parameter secrets."""
    text = "api_key=abc123&token=xyz789"
    redacted = redact_string(text)
    assert "abc123" not in redacted
    assert "xyz789" not in redacted
    # URL params match env-style patterns first
    assert "<redacted:env_value>" in redacted


def test_redact_dict():
    """Test redaction in dictionary."""
    data = {
        "command": "curl https://api.example.com?TOKEN=secret123",
        "env": {"OPENAI_API_KEY": "sk-abc123"},
    }
    redacted = redact_dict(data)

    assert "secret123" not in str(redacted)
    assert "sk-abc123" not in str(redacted)
    assert "<redacted:" in str(redacted)


def test_redact_list():
    """Test redaction in list."""
    data = ["OPENAI_API_KEY=sk-abc123", "npm install lodash", "TOKEN=secret456"]
    redacted = redact_list(data)

    assert "sk-abc123" not in str(redacted)
    assert "secret456" not in str(redacted)
    assert "npm install lodash" in str(redacted)
    assert "<redacted:" in str(redacted)


def test_redact_nested_structures():
    """Test redaction in nested structures."""
    data = {
        "commands": [
            {"cmd": "curl -H 'Authorization: TOKEN=secret123'"},
            {"env": "SECRET=mysecret"},
        ]
    }
    redacted = redact_dict(data)

    assert "secret123" not in str(redacted)
    assert "mysecret" not in str(redacted)
    assert "<redacted:" in str(redacted)


def test_no_redaction_on_safe_text():
    """Test that safe text is not redacted."""
    text = "npm install lodash"
    redacted = redact_string(text)
    assert redacted == text


def test_redact_empty_string():
    """Test redaction of empty string."""
    text = ""
    redacted = redact_string(text)
    assert redacted == ""


def test_redact_none():
    """Test redaction of None."""
    redacted = redact_dict(None)
    assert redacted is None
