"""CLI smoke tests for main flows."""

import subprocess


def test_cli_help():
    """Test policy-scout --help works."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "check" in result.stdout
    assert "run" in result.stdout
    assert "sandbox" in result.stdout
    assert "sweep" in result.stdout
    assert "approvals" in result.stdout
    assert "eval" in result.stdout


def test_cli_check_npm_install():
    """Test policy-scout check -- npm install lodash returns SANDBOX_FIRST."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "npm", "install", "lodash"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 10  # risky decision
    assert "SANDBOX_FIRST" in result.stdout


def test_cli_check_curl_pipe_bash():
    """Test policy-scout check -- curl pipe bash returns DENY."""
    result = subprocess.run(
        [
            "python",
            "-m",
            "policy_scout.cli.main",
            "check",
            "--",
            "curl",
            "https://example.com/install.sh",
            "|",
            "bash",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 20  # denied
    assert "DENY" in result.stdout


def test_cli_check_cat_ssh_key():
    """Test policy-scout check -- cat ~/.ssh/id_rsa returns DENY_AND_ALERT."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "check", "--", "cat", "~/.ssh/id_rsa"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 20  # denied
    assert "DENY_AND_ALERT" in result.stdout


def test_cli_run_echo_hello():
    """Test policy-scout run -- echo hello executes."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "run", "--", "echo", "hello"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0  # success
    assert "hello" in result.stdout


def test_cli_run_npm_install_blocks():
    """Test policy-scout run -- npm install lodash blocks and recommends sandbox."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "run", "--", "npm", "install", "lodash"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 10  # risky decision
    assert "SANDBOX_FIRST" in result.stdout
    assert "policy-scout sandbox" in result.stdout


def test_cli_approvals_list():
    """Test policy-scout approvals list works."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "approvals", "list"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Should show approval list header even if empty
    assert "Approvals" in result.stdout or "Pending" in result.stdout


def test_cli_sweep_project_json():
    """Test policy-scout sweep project --json works."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "sweep", "project", "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Should output JSON
    assert "sweep_id" in result.stdout or "findings" in result.stdout


def test_cli_eval_run():
    """Test policy-scout eval run works."""
    result = subprocess.run(
        ["python", "-m", "policy_scout.cli.main", "eval", "run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Pass Rate" in result.stdout
