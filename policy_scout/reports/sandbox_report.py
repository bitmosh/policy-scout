"""Sandbox result report generation."""

from typing import Dict, Any, List, Optional
from .models import ScoutReport
from .writer import write_report
from .markdown_report import generate_markdown_report
from .json_report import generate_json_report
from ..sandbox.models import SandboxResult


def generate_sandbox_report(
    sandbox_result: SandboxResult,
    audit_event_ids: Optional[List[str]] = None,
) -> ScoutReport:
    """Generate a sandbox result Scout Report.

    Args:
        sandbox_result: SandboxResult from sandbox execution
        audit_event_ids: List of audit event IDs

    Returns:
        ScoutReport with paths populated
    """
    from ..core.ids import generate_id

    report_id = generate_id("report")

    # Generate created_at timestamp
    from ..core.ids import utcnow_iso

    created_at = utcnow_iso()

    # Build title
    title = f"Sandbox Result: {sandbox_result.command}"

    # Build summary
    summary = f"Policy Scout executed the command in a sandbox workspace. The operation completed with exit code {sandbox_result.exit_code} in {sandbox_result.duration_ms}ms."

    # Build findings from sandbox result
    findings = sandbox_result.findings or []

    # Add lifecycle script findings
    if sandbox_result.lifecycle_scripts_found:
        findings.append(
            {
                "title": "Lifecycle Scripts Detected",
                "severity": "medium",
                "category": "lifecycle_scripts",
                "message": f"{len(sandbox_result.lifecycle_scripts_found)} lifecycle script(s) found in installed packages. Review these scripts before migration.",
            }
        )

    # Build recommended actions
    recommended_actions = []
    if sandbox_result.exit_code == 0:
        recommended_actions.append("Review the sandbox result before migration.")
        if sandbox_result.lifecycle_scripts_found:
            recommended_actions.append("Inspect lifecycle scripts in the report.")
        if sandbox_result.manifest_changed or sandbox_result.lockfile_changed:
            recommended_actions.append("Review manifest and lockfile changes.")
        recommended_actions.append(
            "If the sandbox result is acceptable, manually migrate changes to host project."
        )
    else:
        recommended_actions.append(
            "The sandbox install failed. Review the error output."
        )
        recommended_actions.append(
            "Do not migrate to host project until the issue is resolved."
        )

    # Build what could not verify
    could_not_verify = [
        "Network packet inspection during install",
        "Full malware analysis of installed packages",
        "Remote URL integrity after initial fetch",
        "Dynamic behavior of lifecycle scripts during execution",
    ]

    # Convert lifecycle scripts to dict format
    lifecycle_scripts_dict = []
    for script in sandbox_result.lifecycle_scripts_found:
        lifecycle_scripts_dict.append(
            {
                "package_name": script.package_name,
                "script_name": script.script_name,
                "script_content": script.script_content,
                "location": script.location,
            }
        )

    # Generate Markdown
    markdown_content = generate_markdown_report(
        report_type="sandbox_result",
        title=title,
        summary=summary,
        command=sandbox_result.command,
        sandbox_id=sandbox_result.sandbox_id,
        exit_code=sandbox_result.exit_code,
        duration_ms=sandbox_result.duration_ms,
        lifecycle_scripts=lifecycle_scripts_dict,
        manifest_changed=sandbox_result.manifest_changed,
        lockfile_changed=sandbox_result.lockfile_changed,
        findings=findings,
        host_mutation_status="NOT MUTATED",
        migration_status="Not performed, requires approval",
        could_not_verify=could_not_verify,
        audit_event_ids=audit_event_ids,
        recommended_actions=recommended_actions,
    )

    # Generate JSON
    json_content = generate_json_report(
        report_id=report_id,
        report_type="sandbox_result",
        title=title,
        summary=summary,
        request_id=sandbox_result.request_id,
        command=sandbox_result.command,
        sandbox_id=sandbox_result.sandbox_id,
        exit_code=sandbox_result.exit_code,
        duration_ms=sandbox_result.duration_ms,
        lifecycle_scripts=lifecycle_scripts_dict,
        manifest_changed=sandbox_result.manifest_changed,
        lockfile_changed=sandbox_result.lockfile_changed,
        findings=findings,
        host_mutation_status="NOT MUTATED",
        migration_status="Not performed, requires approval",
        could_not_verify=could_not_verify,
        audit_event_ids=audit_event_ids,
        recommended_actions=recommended_actions,
        created_at=created_at,
    )

    # Write files
    report_dir = write_report(ScoutReport(report_id=report_id))

    markdown_path = report_dir / "report.md"
    json_path = report_dir / "report.json"

    markdown_path.write_text(markdown_content)
    json_path.write_text(_json_dumps(json_content))

    # Create and return ScoutReport
    report = ScoutReport(
        report_id=report_id,
        report_type="sandbox_result",
        title=title,
        request_id=sandbox_result.request_id,
        sandbox_id=sandbox_result.sandbox_id,
        findings=findings,
        audit_event_ids=audit_event_ids or [],
        markdown_path=str(markdown_path),
        json_path=str(json_path),
    )

    return report


def _json_dumps(obj: Dict[str, Any]) -> str:
    """JSON dump with pretty formatting."""
    import json

    return json.dumps(obj, indent=2)
