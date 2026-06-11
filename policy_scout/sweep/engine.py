"""Sweep engine for project scanning."""

import os
from typing import Optional
from ..core.ids import utcnow_iso
from .models import SweepResult
from .package_scripts import check_package_scripts
from .workflows import check_workflows
from .executables import check_executables
from .javascript_patterns import check_javascript_patterns
from .shell_scripts import check_shell_scripts
from .credentials import check_credential_references
from .repo_changes import check_repo_changes


def run_project_sweep(
    project_root: Optional[str] = None,
) -> SweepResult:
    """Run a project sweep.

    Args:
        project_root: Path to project root. If None, uses current directory.

    Returns:
        SweepResult with findings
    """
    if project_root is None:
        project_root = os.getcwd()

    # Create sweep result
    sweep_result = SweepResult(
        sweep_type="project",
        project_root=project_root,
    )

    # Run all checks
    findings = []

    # Package script checks
    findings.extend(check_package_scripts(project_root, sweep_result.sweep_id))

    # Workflow checks
    findings.extend(check_workflows(project_root, sweep_result.sweep_id))

    # Executable file checks
    findings.extend(check_executables(project_root, sweep_result.sweep_id))

    # JavaScript pattern checks
    findings.extend(check_javascript_patterns(project_root, sweep_result.sweep_id))

    # Shell script checks
    findings.extend(check_shell_scripts(project_root, sweep_result.sweep_id))

    # Credential reference checks
    findings.extend(check_credential_references(project_root, sweep_result.sweep_id))

    # Repository mutation checks
    findings.extend(check_repo_changes(project_root, sweep_result.sweep_id))

    # Prompt injection detection (agent-readable files)
    try:
        from .prompt_injection import scan_agent_readable_files
        findings.extend(scan_agent_readable_files(project_root, sweep_result.sweep_id))
    except Exception:
        pass

    # Add findings to result
    for finding in findings:
        sweep_result.add_finding(finding)

    # Set completion time
    sweep_result.completed_at = utcnow_iso()

    # Add could_not_verify items
    could_not_verify = []

    # Check if git is available
    git_dir = os.path.join(project_root, ".git")
    if not os.path.exists(git_dir):
        could_not_verify.append("Repository mutation status (not a git repository)")

    # Check if node_modules exists but wasn't fully scanned
    node_modules = os.path.join(project_root, "node_modules")
    if os.path.exists(node_modules):
        could_not_verify.append("Full node_modules scan (limited for performance)")

    sweep_result.could_not_verify = could_not_verify

    return sweep_result
