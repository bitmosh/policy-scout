# SPDX-License-Identifier: Apache-2.0
"""Suspicious process checks for quick system sweep."""

import subprocess
import re
from typing import List, Optional
from .models import Finding
from ..audit.redaction import redact_string


def check_suspicious_processes(sweep_id: str) -> tuple[List[Finding], List[str]]:
    """Check for suspicious development processes.

    Args:
        sweep_id: Sweep result ID.

    Returns:
        Tuple of (findings, could_not_verify list).
    """
    findings = []
    could_not_verify = []

    # Try ps command
    processes = _parse_ps()
    if not processes:
        # Could not verify
        could_not_verify.append("process checks: ps command unavailable or failed")
        return findings, could_not_verify

    for proc_info in processes:
        finding = _assess_process(proc_info, sweep_id)
        if finding:
            findings.append(finding)

    return findings, could_not_verify


def _parse_ps() -> List[dict]:
    """Parse ps output.

    Returns:
        List of process info dicts.
    """
    try:
        # Use ps aux to get process list
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []

        return _parse_ps_output(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _parse_ps_output(output: str) -> List[dict]:
    """Parse ps aux output.

    Args:
        output: ps command output.

    Returns:
        List of process info dicts.
    """
    processes = []
    lines = output.strip().split("\n")

    for line in lines[1:]:  # Skip header
        if not line.strip():
            continue

        # ps aux format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
        parts = line.split(None, 10)  # Split on whitespace, max 10 parts
        if len(parts) < 11:
            continue

        user = parts[0]
        pid = parts[1]
        cpu = parts[2]
        mem = parts[3]
        command = parts[10]

        processes.append(
            {
                "user": user,
                "pid": pid,
                "cpu": cpu,
                "mem": mem,
                "command": command,
            }
        )

    return processes


def _assess_process(proc_info: dict, sweep_id: str) -> Optional[Finding]:
    """Assess a process for suspiciousness.

    Args:
        proc_info: Process information dict.
        sweep_id: Sweep result ID.

    Returns:
        Finding or None.
    """
    command = proc_info["command"]
    pid = proc_info["pid"]

    # Redact command before analysis
    redacted_command = _redact_process_command(command)

    # Suspicious indicators
    suspicious_patterns = [
        # curl/wget piped to shell
        (r"curl.*\|.*sh", "high", "Network fetch piped to shell"),
        (r"wget.*\|.*sh", "high", "Network fetch piped to shell"),
        (r"curl.*\|.*bash", "high", "Network fetch piped to bash"),
        (r"wget.*\|.*bash", "high", "Network fetch piped to bash"),
        # Reading sensitive files
        (r"cat\s+\.env", "medium", "Reading .env file"),
        (r"cat\s+\.npmrc", "medium", "Reading .npmrc file"),
        (r"cat\s+\.ssh", "high", "Reading SSH directory"),
        (r"cat\s+.*id_rsa", "high", "Reading SSH private key"),
        # Environment dumping
        (r"env\s*\|", "medium", "Environment variable dump"),
        (r"printenv", "low", "Environment variable listing"),
        # Temp directory execution
        (r"/tmp/.*\.sh", "medium", "Shell script in temp directory"),
        (r"/tmp/.*\.js", "medium", "JavaScript in temp directory"),
        (r"/tmp/.*\.py", "medium", "Python script in temp directory"),
        # Base64 decode and execute
        (r"base64.*\|.*sh", "high", "Base64 decode piped to shell"),
        (r"base64.*\|.*bash", "high", "Base64 decode piped to bash"),
        # Chmod on downloaded files
        (r"chmod.*\+x.*\/tmp", "medium", "Making temp file executable"),
        # Long-running unknown process from temp
        (r"/tmp\/node", "medium", "Node process from temp directory"),
        (r"/tmp\/python", "medium", "Python process from temp directory"),
    ]

    for pattern, severity, title in suspicious_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return Finding(
                finding_id=f"find_proc_{pid}_{sweep_id}",
                sweep_id=sweep_id,
                severity=severity,
                confidence="moderate",
                category="suspicious_process",
                title=title,
                location=f"PID {pid}",
                evidence_ref=f"command={redacted_command}",
                why_it_matters="Process command pattern may indicate suspicious activity.",
                recommended_action="Review if this process is expected.",
            )

    # Check for common dev processes that are generally OK
    dev_processes = [
        "node",
        "npm",
        "pnpm",
        "yarn",
        "bun",
        "python",
        "pip",
        "python3",
        "pip3",
    ]
    if any(proc in command.lower() for proc in dev_processes):
        # Check if running from temp directory
        if "/tmp/" in command:
            return Finding(
                finding_id=f"find_proc_{pid}_{sweep_id}",
                sweep_id=sweep_id,
                severity="medium",
                confidence="moderate",
                category="suspicious_process",
                title="Development process running from temp directory",
                location=f"PID {pid}",
                evidence_ref=f"command={redacted_command}",
                why_it_matters="Development process running from temp directory is unusual.",
                recommended_action="Review if this process is expected.",
            )

    return None


def _redact_process_command(command: str) -> str:
    """Redact sensitive content from process command.

    Args:
        command: Process command string.

    Returns:
        Redacted command string.
    """
    return redact_string(command)
