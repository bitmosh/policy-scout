"""Tests for CLI run command."""

import subprocess


# Integration tests using subprocess to test actual CLI behavior


def test_cli_run_echo_hello():
    """Test CLI run with echo hello (should execute)."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "run", "--", "echo", "hello"],
        capture_output=True,
        text=True,
    )

    # Should execute and exit with 0
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_cli_run_echo_hello_json():
    """Test CLI run with echo hello in JSON mode."""
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
        capture_output=True,
        text=True,
    )

    # Should execute and exit with 0
    assert result.returncode == 0
    # Should output JSON
    assert "execution_id" in result.stdout
    assert "exit_code" in result.stdout


def test_cli_run_npm_install_sandbox_first():
    """Test CLI run with npm install (should be SANDBOX_FIRST)."""
    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "run",
            "--",
            "npm",
            "install",
            "lodash",
        ],
        capture_output=True,
        text=True,
    )

    # Should not execute, exit with 10 (risky decision)
    assert result.returncode == 10
    assert "SANDBOX_FIRST" in result.stdout
    assert "policy-scout sandbox" in result.stdout


def test_cli_run_rm_rf_node_modules_require_approval():
    """Test CLI run with rm -rf node_modules (should be REQUIRE_APPROVAL)."""
    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "run",
            "--",
            "rm",
            "-rf",
            "node_modules",
        ],
        capture_output=True,
        text=True,
    )

    # Should not execute, exit with 10 (risky decision)
    assert result.returncode == 10
    assert "REQUIRE_APPROVAL" in result.stdout
    assert "appr_" in result.stdout


def test_cli_run_curl_pipe_bash_deny():
    """Test CLI run with curl pipe bash (should be DENY)."""
    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "run",
            "--",
            "curl",
            "https://example.com/install.sh",
            "|",
            "bash",
        ],
        capture_output=True,
        text=True,
    )

    # Should not execute, exit with 20 (denied)
    assert result.returncode == 20
    assert "DENY" in result.stdout


def test_cli_run_non_zero_exit_code():
    """Test CLI run with command that exits non-zero."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "run", "--", "exit", "1"],
        capture_output=True,
        text=True,
    )

    # Should execute but exit with the command's exit code
    assert result.returncode == 1


def test_cli_run_with_audit_enabled():
    """Test CLI run with audit logging enabled."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "run", "--", "echo", "test"],
        capture_output=True,
        text=True,
    )

    # Should execute and exit with 0
    assert result.returncode == 0
    # Audit events should be written (we can't easily verify this without checking the audit file)


def test_cli_run_no_audit():
    """Test CLI run with audit disabled."""
    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "run",
            "--no-audit",
            "--",
            "echo",
            "test",
        ],
        capture_output=True,
        text=True,
    )

    # Should execute and exit with 0
    assert result.returncode == 0
