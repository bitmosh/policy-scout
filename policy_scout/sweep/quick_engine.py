# SPDX-License-Identifier: Apache-2.0
"""Quick system sweep engine."""

import platform
from ..core.ids import utcnow_iso
from .models import SweepResult
from .ports import check_listening_ports
from .processes import check_suspicious_processes
from .shell_profiles import check_shell_profiles
from .package_manager_config import check_package_manager_configs
from .temp_files import check_suspicious_temp_files
from .environment import check_environment_variables


def run_quick_system_sweep() -> SweepResult:
    """Run a quick system sweep.

    Returns:
        SweepResult with findings.
    """
    # Create sweep result
    sweep_result = SweepResult(
        sweep_type="quick_system",
        platform=_detect_platform(),
    )

    # Run all checks
    findings = []
    could_not_verify = []

    # Listening port checks
    port_findings, port_cnv = check_listening_ports(sweep_result.sweep_id)
    findings.extend(port_findings)
    could_not_verify.extend(port_cnv)

    # Suspicious process checks
    proc_findings, proc_cnv = check_suspicious_processes(sweep_result.sweep_id)
    findings.extend(proc_findings)
    could_not_verify.extend(proc_cnv)

    # Shell profile checks
    findings.extend(check_shell_profiles(sweep_result.sweep_id))

    # Package manager config checks
    findings.extend(check_package_manager_configs(sweep_result.sweep_id))

    # Temp file checks
    findings.extend(check_suspicious_temp_files(sweep_result.sweep_id))

    # Environment variable checks
    findings.extend(check_environment_variables(sweep_result.sweep_id))

    # Add findings to result
    for finding in findings:
        sweep_result.add_finding(finding)

    # Set completion time
    sweep_result.completed_at = utcnow_iso()

    # Platform-specific limitations
    if sweep_result.platform != "linux":
        could_not_verify.append(
            f"Quick system sweep is Linux-first. Platform {sweep_result.platform} has limited support."
        )

    sweep_result.could_not_verify = could_not_verify

    return sweep_result


def _detect_platform() -> str:
    """Detect the current platform.

    Returns:
        Platform string: linux, darwin, windows, or unknown.
    """
    system = platform.system().lower()

    if system == "linux":
        return "linux"
    elif system == "darwin":
        return "darwin"
    elif system == "windows":
        return "windows"
    else:
        return "unknown"
