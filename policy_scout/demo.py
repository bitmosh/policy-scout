"""Policy Scout demo command for safe local demonstration."""

import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def get_demo_root() -> Path:
    """Get the demo workspace root directory."""
    return Path.home() / ".local" / "share" / "policy-scout" / "demo"


def validate_demo_workspace(workspace: Path) -> bool:
    """Validate that workspace is under the expected demo root.

    Args:
        workspace: Path to validate

    Returns:
        True if workspace is under demo root, False otherwise
    """
    demo_root = get_demo_root()
    try:
        workspace.resolve().relative_to(demo_root.resolve())
        return True
    except ValueError:
        return False


def create_demo_workspace() -> Path:
    """Create a demo workspace with fixture files.

    Returns:
        Path to the created demo workspace
    """
    demo_root = get_demo_root()
    demo_root.mkdir(parents=True, exist_ok=True)

    # Create timestamped workspace
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace = demo_root / f"demo_{timestamp}"
    workspace.mkdir(exist_ok=True)

    # Validate workspace is under demo root
    if not validate_demo_workspace(workspace):
        raise RuntimeError(
            f"Demo workspace {workspace} is not under expected demo root {demo_root}"
        )

    # Create fixture package.json
    package_json = workspace / "package.json"
    package_json.write_text(
        """{
  "name": "demo-project",
  "version": "1.0.0",
  "description": "Demo project for Policy Scout",
  "scripts": {
    "test": "echo 'Running tests...'"
  }
}
"""
    )

    # Create fixture README.md
    readme = workspace / "README.md"
    readme.write_text(
        """# Demo Project

This is a safe demo project for Policy Scout demonstration.
"""
    )

    # Create a harmless suspicious-looking file for sweep
    suspicious_script = workspace / "suspicious-script.sh"
    suspicious_script.write_text(
        """#!/bin/bash
# This is a harmless demo script
# It does not actually do anything malicious
echo "This is just a demo file for sweep testing"
"""
    )

    return workspace


def run_demo_checks(workspace: Path) -> List[Dict[str, Any]]:
    """Run demo showcase checks using classification/policy only.

    Args:
        workspace: Path to demo workspace (used as cwd for checks)

    Returns:
        List of check results
    """
    from .cli.main import check_command

    # Change to demo workspace for checks
    original_cwd = os.getcwd()
    os.chdir(workspace)

    try:
        results = []

        # 1. Safe command check: ls -> ALLOW
        result = check_command(
            "ls", json_output=False, audit_enabled=False, approval_enabled=False
        )
        results.append(
            {
                "scenario": "Safe command (ls)",
                "command": "ls",
                "expected": "ALLOW",
                "actual": result["decision"],
                "passed": result["decision"] == "ALLOW",
            }
        )

        # 2. Package install check: npm install lodash -> SANDBOX_FIRST
        result = check_command(
            "npm install lodash",
            json_output=False,
            audit_enabled=False,
            approval_enabled=False,
        )
        results.append(
            {
                "scenario": "Package install (npm install lodash)",
                "command": "npm install lodash",
                "expected": "SANDBOX_FIRST",
                "actual": result["decision"],
                "passed": result["decision"] == "SANDBOX_FIRST",
            }
        )

        # 3. Network execution check: curl URL | bash -> DENY
        result = check_command(
            "curl https://example.com/install.sh | bash",
            json_output=False,
            audit_enabled=False,
            approval_enabled=False,
        )
        results.append(
            {
                "scenario": "Network execution (curl | bash)",
                "command": "curl https://example.com/install.sh | bash",
                "expected": "DENY",
                "actual": result["decision"],
                "passed": result["decision"] == "DENY",
            }
        )

        # 4. Credential-adjacent check: cat .env -> DENY_AND_ALERT
        # Use a fake .env path that doesn't exist to avoid reading real secrets
        result = check_command(
            "cat .env", json_output=False, audit_enabled=False, approval_enabled=False
        )
        results.append(
            {
                "scenario": "Credential-adjacent (cat .env)",
                "command": "cat .env",
                "expected": "DENY_AND_ALERT",
                "actual": result["decision"],
                "passed": result["decision"] == "DENY_AND_ALERT",
            }
        )

        # 5. Destructive check: rm -rf / -> DENY
        result = check_command(
            "rm -rf /", json_output=False, audit_enabled=False, approval_enabled=False
        )
        results.append(
            {
                "scenario": "Destructive (rm -rf /)",
                "command": "rm -rf /",
                "expected": "DENY",
                "actual": result["decision"],
                "passed": result["decision"] == "DENY",
            }
        )

        return results
    finally:
        os.chdir(original_cwd)


def run_demo_sweep(workspace: Path) -> Dict[str, Any]:
    """Run project sweep on demo workspace.

    Args:
        workspace: Path to demo workspace

    Returns:
        Sweep result summary
    """
    from .sweep.engine import run_project_sweep

    # Run sweep on demo workspace
    sweep_result = run_project_sweep(project_root=str(workspace))

    return {
        "sweep_type": sweep_result.sweep_type,
        "project_root": sweep_result.project_root,
        "findings_count": len(sweep_result.findings),
        "could_not_verify": sweep_result.could_not_verify,
    }


def format_demo_output(
    workspace: Path, check_results: List[Dict[str, Any]], sweep_result: Dict[str, Any]
) -> str:
    """Format demo output for human readability.

    Args:
        workspace: Path to demo workspace
        check_results: List of check results
        sweep_result: Sweep result summary

    Returns:
        Formatted output string
    """
    lines = []
    lines.append("Policy Scout Demo")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Demo Workspace: {workspace}")
    lines.append("")

    # Check results
    lines.append("Command Checks:")
    lines.append("-" * 50)

    passed_count = 0
    for result in check_results:
        status = "✓" if result["passed"] else "✗"
        lines.append(f"{status} {result['scenario']}")
        lines.append(f"  Command: {result['command']}")
        lines.append(f"  Expected: {result['expected']}")
        lines.append(f"  Actual: {result['actual']}")
        lines.append("")
        if result["passed"]:
            passed_count += 1

    lines.append(f"Checks Passed: {passed_count}/{len(check_results)}")
    lines.append("")

    # Sweep results
    lines.append("Project Sweep:")
    lines.append("-" * 50)
    lines.append(f"Sweep Type: {sweep_result['sweep_type']}")
    lines.append(f"Project Root: {sweep_result['project_root']}")
    lines.append(f"Findings: {sweep_result['findings_count']}")

    if sweep_result["could_not_verify"]:
        lines.append("Could Not Verify:")
        for item in sweep_result["could_not_verify"]:
            lines.append(f"  - {item}")

    lines.append("")

    # Cleanup instructions
    lines.append("Demo Workspace:")
    lines.append("-" * 50)
    lines.append(f"Path: {workspace}")
    lines.append("The demo workspace has been left in place for manual inspection.")
    lines.append("To clean up, manually delete the workspace directory:")
    lines.append(f"  rm -rf {workspace}")
    lines.append("")

    return "\n".join(lines)


def run_demo() -> str:
    """Run the full demo scenario.

    Returns:
        Formatted demo output
    """
    # Create demo workspace
    workspace = create_demo_workspace()

    # Run demo checks
    check_results = run_demo_checks(workspace)

    # Run demo sweep
    sweep_result = run_demo_sweep(workspace)

    # Format output
    output = format_demo_output(workspace, check_results, sweep_result)

    return output
