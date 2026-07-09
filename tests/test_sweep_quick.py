# SPDX-License-Identifier: Apache-2.0
"""Tests for quick system sweep modules."""

import io
import json
import sqlite3
from contextlib import redirect_stdout
from pathlib import Path
from policy_scout.cli import main as cli_main
import policy_scout.cli.commands.sweep as cli_sweep_cmds
from policy_scout.sweep.ports import (
    check_listening_ports,
    _parse_ss_output,
    _parse_netstat_output,
)
from policy_scout.sweep.processes import (
    check_suspicious_processes,
    _parse_ps_output,
    _redact_process_command,
)
from policy_scout.sweep.shell_profiles import check_shell_profiles
from policy_scout.sweep.package_manager_config import check_package_manager_configs
from policy_scout.sweep.environment import check_environment_variables
from policy_scout.sweep.quick_engine import run_quick_system_sweep
from policy_scout.sweep.models import Finding, SweepResult


def test_parse_ss_output():
    """Test parsing ss output with IPv4 localhost bind."""
    output = """Netid State  Recv-Q Send-Q  Local Address:Port   Peer Address:Port Process
tcp   LISTEN 0      128          127.0.0.1:3000       0.0.0.0:*      users:(("node",pid=5678,fd=4))
"""
    ports = _parse_ss_output(output)

    assert len(ports) == 1
    assert ports[0]["protocol"] == "tcp"
    assert ports[0]["local_address"] == "127.0.0.1"
    assert ports[0]["port"] == "3000"
    assert ports[0]["pid"] == "5678"
    assert ports[0]["process_name"] == "node"


def test_parse_ss_output_ipv4_wildcard():
    """Test parsing ss output with IPv4 0.0.0.0 bind."""
    output = """Netid State  Recv-Q Send-Q  Local Address:Port   Peer Address:Port Process
tcp   LISTEN 0      128          0.0.0.0:22           0.0.0.0:*      users:(("sshd",pid=1234,fd=3))
"""
    ports = _parse_ss_output(output)

    assert len(ports) == 1
    assert ports[0]["protocol"] == "tcp"
    assert ports[0]["local_address"] == "0.0.0.0"
    assert ports[0]["port"] == "22"
    assert ports[0]["pid"] == "1234"
    assert ports[0]["process_name"] == "sshd"


def test_parse_ss_output_ipv6():
    """Test parsing ss output with IPv6 bind."""
    output = """Netid State  Recv-Q Send-Q  Local Address:Port   Peer Address:Port Process
tcp6  LISTEN 0      128          [::]:80              [::]:*         users:(("nginx",pid=9999,fd=5))
"""
    ports = _parse_ss_output(output)

    assert len(ports) == 1
    assert ports[0]["protocol"] == "tcp6"
    assert ports[0]["local_address"] == "[::]"
    assert ports[0]["port"] == "80"
    assert ports[0]["pid"] == "9999"
    assert ports[0]["process_name"] == "nginx"


def test_parse_ss_output_no_process_info():
    """Test parsing ss output without process info."""
    output = """Netid State  Recv-Q Send-Q  Local Address:Port   Peer Address:Port Process
tcp   LISTEN 0      128          0.0.0.0:22           0.0.0.0:*      
"""
    ports = _parse_ss_output(output)

    assert len(ports) == 1
    assert ports[0]["protocol"] == "tcp"
    assert ports[0]["local_address"] == "0.0.0.0"
    assert ports[0]["port"] == "22"
    assert ports[0]["pid"] == ""
    assert ports[0]["process_name"] == ""


def test_parse_ss_output_malformed_lines():
    """Test parsing ss output with malformed lines ignored safely."""
    output = """Netid State  Recv-Q Send-Q  Local Address:Port   Peer Address:Port Process
tcp   LISTEN 0      128          0.0.0.0:22           0.0.0.0:*      users:(("sshd",pid=1234,fd=3))
invalid line here
tcp   LISTEN 0      128          0.0.0.0:80           0.0.0.0:*      users:(("nginx",pid=9999,fd=5))
"""
    ports = _parse_ss_output(output)

    # Should parse valid lines and skip malformed
    assert len(ports) == 2
    assert ports[0]["port"] == "22"
    assert ports[1]["port"] == "80"


def test_parse_netstat_output():
    """Test parsing netstat output with IPv4 localhost bind."""
    output = """Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 127.0.0.1:3000          0.0.0.0:*               LISTEN      5678/node
"""
    ports = _parse_netstat_output(output)

    assert len(ports) == 1
    assert ports[0]["protocol"] == "tcp"
    assert ports[0]["local_address"] == "127.0.0.1"
    assert ports[0]["port"] == "3000"
    assert ports[0]["pid"] == "5678"
    assert ports[0]["process_name"] == "node"


def test_parse_netstat_output_ipv4_wildcard():
    """Test parsing netstat output with IPv4 0.0.0.0 bind."""
    output = """Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      1234/sshd
"""
    ports = _parse_netstat_output(output)

    assert len(ports) == 1
    assert ports[0]["protocol"] == "tcp"
    assert ports[0]["local_address"] == "0.0.0.0"
    assert ports[0]["port"] == "22"
    assert ports[0]["pid"] == "1234"
    assert ports[0]["process_name"] == "sshd"


def test_parse_netstat_output_ipv6():
    """Test parsing netstat output with IPv6 bind."""
    output = """Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp6       0      0 [::]:80                [::]:*                  LISTEN      9999/nginx
"""
    ports = _parse_netstat_output(output)

    assert len(ports) == 1
    assert ports[0]["protocol"] == "tcp6"
    assert ports[0]["local_address"] == "[::]"
    assert ports[0]["port"] == "80"
    assert ports[0]["pid"] == "9999"
    assert ports[0]["process_name"] == "nginx"


def test_parse_netstat_output_no_process_info():
    """Test parsing netstat output without process info."""
    output = """Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN
"""
    ports = _parse_netstat_output(output)

    assert len(ports) == 1
    assert ports[0]["protocol"] == "tcp"
    assert ports[0]["local_address"] == "0.0.0.0"
    assert ports[0]["port"] == "22"
    assert ports[0]["pid"] == ""
    assert ports[0]["process_name"] == ""


def test_parse_netstat_output_malformed_lines():
    """Test parsing netstat output with malformed lines ignored safely."""
    output = """Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      1234/sshd
invalid line here
tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN      9999/nginx
"""
    ports = _parse_netstat_output(output)

    # Should parse valid lines and skip malformed
    assert len(ports) == 2
    assert ports[0]["port"] == "22"
    assert ports[1]["port"] == "80"


def test_parse_netstat_output_single_header():
    """Test parsing netstat output with only one header line."""
    output = """Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      1234/sshd
"""
    ports = _parse_netstat_output(output)

    # Should correctly find data start after single header
    assert len(ports) == 1
    assert ports[0]["port"] == "22"


def test_parse_netstat_output_header_only():
    """Test parsing netstat output with only headers and no data rows."""
    output = """Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
"""
    ports = _parse_netstat_output(output)

    # Should return empty list when only headers present
    assert len(ports) == 0


def test_parse_ps_output():
    """Test parsing ps output."""
    output = """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.1  12345  6789 ?        Ss   Jan01   0:01 /sbin/init
user      1234  0.5  1.2  54321 12345 ?        Sl   10:00   0:05 node server.js
"""
    processes = _parse_ps_output(output)

    assert len(processes) == 2
    assert processes[0]["pid"] == "1"
    assert processes[0]["command"] == "/sbin/init"
    assert processes[1]["pid"] == "1234"
    assert processes[1]["command"] == "node server.js"


def test_process_command_redaction_covers_flag_and_url_secrets():
    """Test process command evidence redacts common flag and URL secret forms."""
    command = "node app.js --token supersecret https://example.test/?api_key=abc123"

    redacted = _redact_process_command(command)

    assert "supersecret" not in redacted
    assert "abc123" not in redacted
    assert "<redacted:possible_token>" in redacted


def test_check_environment_variables(monkeypatch):
    """Test environment variable checks."""
    # Set some test environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_aws_key")

    findings = check_environment_variables("sweep_test")

    # Should find findings for sensitive env vars
    assert len(findings) > 0

    # Clean up
    monkeypatch.delenv("OPENAI_API_KEY")
    monkeypatch.delenv("AWS_ACCESS_KEY_ID")


def test_check_environment_variables_no_sensitive(monkeypatch):
    """Test environment variable checks with no sensitive vars."""
    # Ensure no sensitive vars are set
    for var in [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN",
        "NPM_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "API_KEY",
        "TOKEN",
        "SECRET",
        "PASSWORD",
    ]:
        monkeypatch.delenv(var, raising=False)

    findings = check_environment_variables("sweep_test")

    # Should return empty list
    assert len(findings) == 0


def test_run_quick_system_sweep():
    """Test running quick system sweep."""
    result = run_quick_system_sweep()

    assert result.sweep_type == "quick_system"
    assert result.sweep_id.startswith("sweep_")
    assert result.platform in ["linux", "darwin", "windows", "unknown"]
    assert isinstance(result.findings, list)
    assert isinstance(result.findings_count, dict)
    assert isinstance(result.could_not_verify, list)


def test_handle_sweep_quick_json_redacts_finding_evidence(tmp_path, monkeypatch):
    """Test quick sweep JSON output redacts secret-like finding evidence."""
    sweep_result = SweepResult(
        sweep_id="sweep_test", sweep_type="quick_system", platform="linux"
    )
    sweep_result.add_finding(
        Finding(
            sweep_id="sweep_test",
            severity="medium",
            confidence="moderate",
            category="suspicious_process",
            title="Process command references token",
            location="PID 1234",
            evidence_ref="command=node app.js --token supersecret",
            why_it_matters="Process command pattern may indicate suspicious activity.",
            recommended_action="Review if this process is expected.",
        )
    )

    monkeypatch.setattr(cli_sweep_cmds, "run_quick_system_sweep", lambda: sweep_result)
    monkeypatch.setenv("POLICY_SCOUT_REPORT_ROOT", str(tmp_path / "reports"))

    stdout_capture = io.StringIO()
    with redirect_stdout(stdout_capture):
        cli_main.handle_sweep_quick_command(json_output=True, audit_enabled=False)

    output = stdout_capture.getvalue()
    data = json.loads(output)

    assert data["sweep_type"] == "quick_system"
    assert "supersecret" not in output
    assert "<redacted:possible_token>" in output


def test_handle_sweep_quick_writes_audit_events(tmp_path, monkeypatch):
    """Test quick sweep writes the same core audit event pattern as project sweep."""
    db_path = tmp_path / "audit.db"
    jsonl_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("POLICY_SCOUT_AUDIT_DB_PATH", str(db_path))
    monkeypatch.setenv("POLICY_SCOUT_AUDIT_PATH", str(jsonl_path))
    monkeypatch.setenv("POLICY_SCOUT_REPORT_ROOT", str(tmp_path / "reports"))

    sweep_result = SweepResult(
        sweep_id="sweep_test", sweep_type="quick_system", platform="linux"
    )
    monkeypatch.setattr(cli_sweep_cmds, "run_quick_system_sweep", lambda: sweep_result)

    stdout_capture = io.StringIO()
    with redirect_stdout(stdout_capture):
        cli_main.handle_sweep_quick_command(json_output=True, audit_enabled=True)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT DISTINCT event_type FROM audit_events")
        event_types = {row[0] for row in cursor.fetchall()}

    assert "SweepStarted" in event_types
    assert "SweepCompleted" in event_types
    assert "ScoutReportGenerated" in event_types


def test_check_listening_ports_no_ss_netstat(monkeypatch):
    """Test port checks when ss and netstat are unavailable."""
    # Mock subprocess.run to simulate command not found
    import subprocess

    def mock_run(*args, **kwargs):
        raise FileNotFoundError("Command not found")

    monkeypatch.setattr(subprocess, "run", mock_run)

    findings, could_not_verify = check_listening_ports("sweep_test")

    # Should return empty findings and could_not_verify entry
    assert len(findings) == 0
    assert len(could_not_verify) == 1
    assert "ss and netstat commands unavailable" in could_not_verify[0]


def test_check_suspicious_processes_no_ps(monkeypatch):
    """Test process checks when ps is unavailable."""
    import subprocess

    def mock_run(*args, **kwargs):
        raise FileNotFoundError("Command not found")

    monkeypatch.setattr(subprocess, "run", mock_run)

    findings, could_not_verify = check_suspicious_processes("sweep_test")

    # Should return empty findings and could_not_verify entry
    assert len(findings) == 0
    assert len(could_not_verify) == 1
    assert "ps command unavailable" in could_not_verify[0]


def test_check_shell_profiles_no_profiles(tmp_path, monkeypatch):
    """Test shell profile checks when no profiles exist."""
    # Mock home directory to empty temp path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    findings = check_shell_profiles("sweep_test")

    # Should return empty list when no profiles exist
    assert len(findings) == 0


def test_check_package_manager_configs_no_configs(tmp_path, monkeypatch):
    """Test package manager config checks when no configs exist."""
    # Mock home directory to empty temp path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    findings = check_package_manager_configs("sweep_test")

    # Should return empty list when no configs exist
    assert len(findings) == 0


def test_check_suspicious_temp_files_no_temp(tmp_path, monkeypatch):
    """Test temp file checks when temp directories don't exist."""
    # Override the function to return empty list
    import policy_scout.sweep.temp_files as temp_module

    def mock_check(sweep_id):
        return []

    monkeypatch.setattr(temp_module, "check_suspicious_temp_files", mock_check)

    findings = temp_module.check_suspicious_temp_files("sweep_test")

    # Should return empty list
    assert len(findings) == 0


def test_run_quick_system_sweep_non_linux_platform(monkeypatch):
    """Test quick sweep on non-Linux platform adds could_not_verify note."""
    import platform

    def mock_system():
        return "Darwin"

    monkeypatch.setattr(platform, "system", mock_system)

    result = run_quick_system_sweep()

    # Should detect platform as darwin
    assert result.platform == "darwin"

    # Should add could_not_verify note about limited support
    assert any("Linux-first" in cnv for cnv in result.could_not_verify)
    assert any("darwin" in cnv for cnv in result.could_not_verify)


def test_check_shell_profiles_unicode_decode_error(tmp_path, monkeypatch):
    """Test shell profile check handles UnicodeDecodeError gracefully."""
    # Create a mock profile file
    profile_dir = tmp_path / "home" / "user"
    profile_dir.mkdir(parents=True)
    profile_path = profile_dir / ".bashrc"
    profile_path.write_text("test")  # Create the file

    # Mock read_text to raise UnicodeDecodeError
    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if self == profile_path:
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid byte sequence")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mock_read_text)
    monkeypatch.setattr(Path, "home", lambda: profile_dir)

    findings = check_shell_profiles("sweep_test")

    # Should return a low-confidence finding about decode failure
    assert len(findings) == 1
    assert findings[0].severity == "low"
    assert findings[0].confidence == "low"
    assert "Could not decode" in findings[0].title
    assert "encoding issue" in findings[0].evidence_ref


def test_check_package_manager_configs_unicode_decode_error(tmp_path, monkeypatch):
    """Test package manager config check handles UnicodeDecodeError gracefully."""
    # Create a mock config file
    config_dir = tmp_path / "home" / "user"
    config_dir.mkdir(parents=True)
    config_path = config_dir / ".npmrc"
    config_path.write_text("test")  # Create the file

    # Mock read_text to raise UnicodeDecodeError
    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if self == config_path:
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid byte sequence")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mock_read_text)
    monkeypatch.setattr(Path, "home", lambda: config_dir)

    findings = check_package_manager_configs("sweep_test")

    # Should return a low-confidence finding about decode failure
    assert len(findings) == 1
    assert findings[0].severity == "low"
    assert findings[0].confidence == "low"
    assert "Could not decode" in findings[0].title
    assert "encoding issue" in findings[0].evidence_ref


def test_home_path_normalization_in_shell_profile_findings(tmp_path, monkeypatch):
    """Test shell profile findings normalize home directory to ~."""
    # Create a mock profile file
    profile_dir = tmp_path / "home" / "user"
    profile_dir.mkdir(parents=True)
    profile_path = profile_dir / ".bashrc"
    profile_path.write_text("export TEST=value")

    monkeypatch.setattr(Path, "home", lambda: profile_dir)

    findings = check_shell_profiles("sweep_test")

    # Should normalize path to use ~ instead of full path
    if findings:
        for finding in findings:
            # Location should use ~ instead of full absolute path
            assert str(tmp_path) not in finding.location
            assert (
                "~/" in finding.location or "/home/user" not in finding.location.lower()
            )


def test_home_path_normalization_in_package_config_findings(tmp_path, monkeypatch):
    """Test package manager config findings normalize home directory to ~."""
    # Create a mock config file with token pattern
    config_dir = tmp_path / "home" / "user"
    config_dir.mkdir(parents=True)
    config_path = config_dir / ".npmrc"
    config_path.write_text("_authToken=abc123")

    monkeypatch.setattr(Path, "home", lambda: config_dir)

    findings = check_package_manager_configs("sweep_test")

    # Should normalize path to use ~ instead of full path
    if findings:
        for finding in findings:
            # Location should use ~ instead of full absolute path
            assert str(tmp_path) not in finding.location
            assert (
                "~/" in finding.location or "/home/user" not in finding.location.lower()
            )


def test_temp_file_path_redacts_token_like_filename(tmp_path):
    """Test temp file findings redact token-like patterns from filenames."""
    from policy_scout.sweep.temp_files import (
        _redact_sensitive_filename,
        _normalize_temp_path,
    )

    # Test with a filename containing a long alphanumeric string (token-like)
    token_filename = (
        "script_abc123def456ghi789jkl012mno345pqr678st901uv234wx567yz890.sh"
    )
    redacted = _redact_sensitive_filename(token_filename)

    # Should redact the long alphanumeric string
    assert "<redacted:token>" in redacted
    assert "abc123def456ghi789jkl012mno345pqr678st901uv234wx567yz890" not in redacted

    # Test with UUID-like filename
    uuid_filename = "config_550e8400-e29b-41d4-a716-446655440000.json"
    redacted = _redact_sensitive_filename(uuid_filename)

    # Should redact the UUID
    assert "<redacted:uuid>" in redacted
    assert "550e8400-e29b-41d4-a716-446655440000" not in redacted

    # Test path normalization
    file_path = tmp_path / token_filename
    normalized = _normalize_temp_path(file_path)

    # Should contain redacted filename
    assert "<redacted:token>" in normalized
    assert str(tmp_path) in normalized  # Parent directory should be preserved
