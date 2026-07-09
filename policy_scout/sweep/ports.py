# SPDX-License-Identifier: Apache-2.0
"""Listening port checks for quick system sweep."""

import subprocess
import re
from typing import List, Optional
from .models import Finding
from ..audit.redaction import redact_string


def check_listening_ports(sweep_id: str) -> tuple[List[Finding], List[str]]:
    """Check for listening ports.

    Args:
        sweep_id: Sweep result ID.

    Returns:
        Tuple of (findings, could_not_verify list).
    """
    findings = []
    could_not_verify = []

    # Try ss first, fallback to netstat
    ports = _parse_ss()
    if not ports:
        ports = _parse_netstat()

    if not ports:
        # Could not verify - both tools unavailable or failed
        could_not_verify.append(
            "listening port checks: ss and netstat commands unavailable or failed"
        )
        return findings, could_not_verify

    for port_info in ports:
        finding = _assess_port(port_info, sweep_id)
        if finding:
            findings.append(finding)

    return findings, could_not_verify


def _parse_ss() -> List[dict]:
    """Parse ss -ltnup output.

    Returns:
        List of port info dicts.
    """
    try:
        result = subprocess.run(
            ["ss", "-ltnup"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []

        return _parse_ss_output(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _parse_ss_output(output: str) -> List[dict]:
    """Parse ss output.

    Args:
        output: ss command output.

    Returns:
        List of port info dicts.
    """
    ports = []
    lines = output.strip().split("\n")

    for line in lines[1:]:  # Skip header
        if not line.strip():
            continue

        # ss output format: Netid State Recv-Q Send-Q Local Address:Port Peer Address:Port Process
        # Example: tcp   LISTEN 0      128          0.0.0.0:22           0.0.0.0:*      users:("sshd",pid=1234,fd=3))
        parts = line.split()
        if len(parts) < 5:
            continue

        # Extract protocol (Netid)
        protocol = parts[0] if parts[0] in ["tcp", "tcp6", "udp", "udp6"] else "tcp"

        # Local Address:Port is at index 4 (after Netid, State, Recv-Q, Send-Q)
        if len(parts) < 5:
            continue
        local_addr_port = parts[4]

        # Process info is at the end
        process_info = parts[-1] if len(parts) > 5 else ""

        # Parse address and port
        if ":" in local_addr_port:
            addr, port = local_addr_port.rsplit(":", 1)
        else:
            addr = local_addr_port
            port = ""

        # Parse process info (pid/name)
        pid = ""
        process_name = ""
        if process_info and "(" in process_info:
            match = re.search(r"pid=(\d+)", process_info)
            if match:
                pid = match.group(1)
            match = re.search(r'"([^"]+)"', process_info)
            if match:
                process_name = match.group(1)

        ports.append(
            {
                "protocol": protocol,
                "local_address": addr,
                "port": port,
                "pid": pid,
                "process_name": process_name,
                "raw_process": process_info,
            }
        )

    return ports


def _parse_netstat() -> List[dict]:
    """Parse netstat -ltnup output.

    Returns:
        List of port info dicts.
    """
    try:
        result = subprocess.run(
            ["netstat", "-ltnup"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []

        return _parse_netstat_output(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _parse_netstat_output(output: str) -> List[dict]:
    """Parse netstat output.

    Args:
        output: netstat command output.

    Returns:
        List of port info dicts.
    """
    ports = []
    lines = output.strip().split("\n")

    # Find the first data line (skip header lines)
    data_start = 0
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith(("Proto", "Active")):
            data_start = i
            break

    # If no data lines found (only headers), return empty list
    if data_start == 0 and len(lines) > 0:
        # Check if we have any non-header lines
        has_data = any(
            line.strip() and not line.startswith(("Proto", "Active")) for line in lines
        )
        if not has_data:
            return []

    for line in lines[data_start:]:
        if not line.strip():
            continue

        # netstat output: Proto Recv-Q Send-Q Local Address Foreign Address State PID/Program name
        # Example: tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      1234/sshd
        parts = line.split()
        if len(parts) < 6:
            continue

        protocol = parts[0]

        # Local Address is at index 3 (after Proto, Recv-Q, Send-Q)
        if len(parts) < 4:
            continue
        local_addr = parts[3]

        # PID/Program name is at the end
        process_info = parts[-1] if len(parts) > 6 else ""

        # Parse address and port
        if ":" in local_addr:
            addr, port = local_addr.rsplit(":", 1)
        else:
            addr = local_addr
            port = ""

        # Parse process info
        pid = ""
        process_name = ""
        if "/" in process_info:
            pid_part, name_part = process_info.split("/", 1)
            pid = pid_part
            process_name = name_part

        ports.append(
            {
                "protocol": protocol,
                "local_address": addr,
                "port": port,
                "pid": pid,
                "process_name": process_name,
                "raw_process": process_info,
            }
        )

    return ports


def _assess_port(port_info: dict, sweep_id: str) -> Optional[Finding]:
    """Assess a listening port for suspiciousness.

    Args:
        port_info: Port information dict.
        sweep_id: Sweep result ID.

    Returns:
        Finding or None.
    """
    port = port_info["port"]
    addr = port_info["local_address"]
    process_name = port_info["process_name"]

    # Common dev ports - generally info/low severity
    common_dev_ports = [
        "3000",
        "3001",
        "4000",
        "5000",
        "5001",
        "8000",
        "8080",
        "8081",
        "9000",
        "9090",
    ]

    # Binding to 0.0.0.0 is more notable than 127.0.0.1
    if addr == "0.0.0.0" or addr == "::":
        if port in common_dev_ports:
            severity = "low"
            confidence = "moderate"
            title = f"Listening port {port} bound to all interfaces"
            why_it_matters = (
                "Port bound to 0.0.0.0 accepts connections from any network interface."
            )
        else:
            severity = "medium"
            confidence = "moderate"
            title = f"Listening port {port} bound to all interfaces"
            why_it_matters = (
                "Non-standard port bound to 0.0.0.0 may expose service to network."
            )
    elif addr == "127.0.0.1" or addr == "::1":
        if port in common_dev_ports:
            # Local dev port - info only
            return None
        else:
            severity = "low"
            confidence = "moderate"
            title = f"Listening port {port} on localhost"
            why_it_matters = (
                "Port listening on localhost is less exposed but worth noting."
            )
    else:
        # Other addresses
        severity = "medium"
        confidence = "moderate"
        title = f"Listening port {port} on {addr}"
        why_it_matters = "Port listening on specific address."

    # Check for suspicious process names
    suspicious_processes = ["nc", "netcat", "socat", "python3 -m http.server"]
    if process_name and any(s in process_name.lower() for s in suspicious_processes):
        severity = "high"
        confidence = "moderate"
        title = f"Suspicious process {process_name} listening on port {port}"
        why_it_matters = "Process name suggests possible unexpected listener or ad-hoc development server."

    # Redact process command line if it contains secrets
    raw_process = port_info.get("raw_process", "")
    if raw_process:
        redacted_process = _redact_process_command(raw_process)
    else:
        redacted_process = ""

    return Finding(
        finding_id=f"find_{port}_{sweep_id}",
        sweep_id=sweep_id,
        severity=severity,
        confidence=confidence,
        category="open_port",
        title=title,
        location=f"{addr}:{port}",
        evidence_ref=f"protocol={port_info['protocol']}, process={redacted_process}",
        why_it_matters=why_it_matters,
        recommended_action="Review if this port and process are expected.",
    )


def _redact_process_command(command: str) -> str:
    """Redact sensitive content from process command.

    Args:
        command: Process command string.

    Returns:
        Redacted command string.
    """
    return redact_string(command)
