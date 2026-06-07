"""Tests for CLI check command."""

import sys
from io import StringIO
from policy_scout.cli.main import check_command, print_human_output


def test_check_command_structure():
    """Test that check_command returns proper structure."""
    result = check_command("ls", json_output=False)

    assert "request_id" in result
    assert "command" in result
    assert "decision" in result
    assert "risk_score" in result
    assert "risk_band" in result
    assert "category" in result
    assert "capabilities" in result
    assert "reasons" in result
    assert "recommended_next_action" in result
    assert "confidence" in result


def test_check_command_ls():
    """Test checking ls command."""
    result = check_command("ls", json_output=False)

    assert result["decision"] == "ALLOW"
    assert result["category"] == "safe_read"
    assert result["risk_score"] <= 2


def test_check_command_npm_install():
    """Test checking npm install command."""
    result = check_command("npm install lodash", json_output=False)

    assert result["decision"] == "SANDBOX_FIRST"
    assert result["category"] == "package_install"
    assert result["risk_score"] >= 5
    assert "network.fetch" in result["capabilities"]
    assert "lifecycle.execute_possible" in result["capabilities"]


def test_check_command_curl_pipe_bash():
    """Test checking curl pipe bash command."""
    result = check_command(
        "curl https://example.com/install.sh | bash", json_output=False
    )

    assert result["decision"] == "DENY"
    # Registry may match curl.fetch first, but network_execute is also detected
    assert (
        "network_fetch" in result["category"] or "network_execute" in result["category"]
    )
    assert result["risk_score"] >= 7


def test_check_command_credential():
    """Test checking credential-adjacent command."""
    result = check_command("cat ~/.ssh/id_rsa", json_output=False)

    assert result["decision"] == "DENY_AND_ALERT"
    assert result["category"] == "credential_adjacent"
    assert result["risk_score"] >= 5


def test_check_command_destructive():
    """Test checking destructive command."""
    result = check_command("rm -rf /", json_output=False)

    assert result["decision"] == "DENY"
    assert "destructive" in result["category"]


def test_check_command_json_output():
    """Test JSON output format."""
    result = check_command("npm install lodash", json_output=True)

    # Should be valid JSON when captured
    assert isinstance(result, dict)
    assert result["decision"] == "SANDBOX_FIRST"


def test_check_command_pnpm_add():
    """Test checking pnpm add command."""
    result = check_command("pnpm add zod", json_output=False)

    assert result["decision"] == "SANDBOX_FIRST"
    assert result["category"] == "package_install"


def test_check_command_yarn_add():
    """Test checking yarn add command."""
    result = check_command("yarn add react", json_output=False)

    assert result["decision"] == "SANDBOX_FIRST"
    assert result["category"] == "package_install"


def test_check_command_bun_add():
    """Test checking bun add command."""
    result = check_command("bun add package", json_output=False)

    assert result["decision"] == "SANDBOX_FIRST"
    assert result["category"] == "package_install"


def test_check_command_npx():
    """Test checking npx command."""
    result = check_command("npx create-vite", json_output=False)

    assert result["decision"] == "SANDBOX_FIRST"
    assert result["category"] == "package_execute"


def test_check_command_npm_test():
    """Test checking npm test command."""
    result = check_command("npm test", json_output=False)

    assert result["decision"] == "ALLOW_LOGGED"
    assert "local_inspection" in result["category"]


def test_human_output_format():
    """Test human output format."""
    result = {
        "command": "npm install lodash",
        "decision": "SANDBOX_FIRST",
        "risk_score": 7,
        "risk_band": "high",
        "category": "package_install",
        "capabilities": ["network.fetch", "package.install"],
        "reasons": ["Package installs may execute lifecycle scripts."],
        "recommended_next_action": "Run sandbox analysis first.",
    }

    # Capture output
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    print_human_output(result)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    assert "Policy Scout Check" in output
    assert "SANDBOX_FIRST" in output
    assert "7/10" in output
    assert "package_install" in output
