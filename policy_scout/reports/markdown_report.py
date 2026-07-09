# SPDX-License-Identifier: Apache-2.0
"""Markdown report generation."""

from typing import Dict, Any, List, Optional
from ..audit.redaction import redact_string, redact_list


def generate_markdown_report(
    report_type: str,
    title: str,
    summary: str,
    decision: Optional[str] = None,
    risk_score: Optional[int] = None,
    risk_band: Optional[str] = None,
    command: Optional[str] = None,
    sandbox_id: Optional[str] = None,
    exit_code: Optional[int] = None,
    duration_ms: Optional[int] = None,
    lifecycle_scripts: Optional[List[Dict[str, Any]]] = None,
    manifest_changed: Optional[bool] = None,
    lockfile_changed: Optional[bool] = None,
    findings: Optional[List[Dict[str, Any]]] = None,
    host_mutation_status: str = "NOT MUTATED",
    migration_status: str = "Not performed, requires approval",
    could_not_verify: Optional[List[str]] = None,
    audit_event_ids: Optional[List[str]] = None,
    recommended_actions: Optional[List[str]] = None,
) -> str:
    """Generate a Markdown Scout Report.

    Args:
        report_type: Type of report (command_decision, sandbox_result, etc.)
        title: Report title
        summary: Summary of what happened
        decision: Policy decision if applicable
        risk_score: Risk score if applicable
        risk_band: Risk band if applicable
        command: Triggering command
        sandbox_id: Sandbox ID if applicable
        exit_code: Sandbox exit code if applicable
        duration_ms: Sandbox duration if applicable
        lifecycle_scripts: List of lifecycle scripts found
        manifest_changed: Whether manifest changed
        lockfile_changed: Whether lockfile changed
        findings: List of findings
        host_mutation_status: Host project mutation status
        migration_status: Migration status
        could_not_verify: List of things that could not be verified
        audit_event_ids: List of audit event IDs
        recommended_actions: List of recommended actions

    Returns:
        Markdown report content
    """
    # Redact sensitive values in all inputs
    title = redact_string(title)
    summary = redact_string(summary)
    if command:
        command = redact_string(command)
    if findings:
        findings = redact_list(findings)
    if lifecycle_scripts:
        lifecycle_scripts = redact_list(lifecycle_scripts)
    if recommended_actions:
        recommended_actions = redact_list(recommended_actions)
    if could_not_verify:
        could_not_verify = redact_list(could_not_verify)

    lines = []

    # Header
    lines.append(f"# Scout Report: {title}")
    lines.append("")

    # Summary
    lines.append("## 1. Summary")
    lines.append("")
    lines.append(summary)
    lines.append("")

    # Redaction Applied
    lines.append("## 2. Redaction Applied")
    lines.append("")
    lines.append(
        "This report has been redacted to protect sensitive information. Secret-like values (tokens, API keys, SSH keys, environment variable values) are replaced with placeholders such as `<redacted:possible_token>`, `<redacted:ssh_private_key>`, or `<redacted:env_value>`."
    )
    lines.append("")

    # Decision / Risk
    if decision or risk_score is not None:
        lines.append("## 3. Decision / Risk Level")
        lines.append("")
        if decision:
            lines.append(f"- Decision: `{decision}`")
        if risk_score is not None:
            lines.append(f"- Risk: `{risk_score}/10`")
        if risk_band:
            lines.append(f"- Risk Band: `{risk_band}`")
        lines.append("")

    # Trigger
    if command:
        lines.append("## 4. Triggering Command")
        lines.append("")
        lines.append("```text")
        lines.append(command)
        lines.append("```")
        lines.append("")

    # Timeline (for sandbox)
    if sandbox_id or duration_ms is not None:
        lines.append("## 5. Timeline")
        lines.append("")
        if sandbox_id:
            lines.append(f"- Sandbox ID: `{sandbox_id}`")
        if duration_ms is not None:
            lines.append(f"- Duration: `{duration_ms}ms`")
        if exit_code is not None:
            lines.append(f"- Exit Code: `{exit_code}`")
        lines.append("")

    # Findings
    if findings:
        lines.append("## 6. Findings")
        lines.append("")
        for i, finding in enumerate(findings, 1):
            lines.append(f"### Finding {i}: {finding.get('title', 'Untitled')}")
            lines.append("")
            if "severity" in finding:
                lines.append(f"- Severity: `{finding['severity']}`")
            if "category" in finding:
                lines.append(f"- Category: `{finding['category']}`")
            if "location" in finding:
                lines.append(f"- Location: `{finding['location']}`")
            if "message" in finding:
                lines.append("")
                lines.append(finding["message"])
            lines.append("")

    # Evidence (for sandbox)
    if manifest_changed is not None or lockfile_changed is not None:
        lines.append("## 7. Evidence")
        lines.append("")
        if manifest_changed:
            lines.append("- package.json changed")
        if lockfile_changed:
            lines.append("- package-lock.json or npm-shrinkwrap.json changed")
        if lifecycle_scripts:
            lines.append(f"- {len(lifecycle_scripts)} lifecycle script(s) found")
        lines.append("")

    # Lifecycle Scripts (for sandbox)
    if lifecycle_scripts:
        lines.append("## 8. Lifecycle Scripts")
        lines.append("")
        lines.append(f"Total lifecycle scripts found: {len(lifecycle_scripts)}")
        lines.append("")
        for script in lifecycle_scripts:
            lines.append(
                f"- **{script.get('package_name', 'root')}** - `{script.get('script_name', 'unknown')}`"
            )
            if script.get("script_content"):
                content = script["script_content"]
                # Truncate long content
                if len(content) > 100:
                    content = content[:100] + "..."
                lines.append(f"  - Content: `{content}`")
        lines.append("")

    # Credential Exposure Assessment
    credential_exposure_level = "none_detected"
    credential_exposure_notes = (
        "Policy Scout did not detect direct credential exposure in this operation."
    )
    if findings:
        credential_signal_categories = {
            "credential_exposure_signal",
            "package_manager_config",
            "suspicious_process",
        }
        if any(
            finding.get("category") in credential_signal_categories
            for finding in findings
        ):
            credential_exposure_level = "possible"
            credential_exposure_notes = (
                "Findings include possible credential exposure signals. Review findings for details. "
                "This is not confirmed exposure."
            )

    lines.append("## 9. Credential Exposure Assessment")
    lines.append("")
    lines.append(f"- Assessment: `{credential_exposure_level}`")
    lines.append(f"- Notes: {credential_exposure_notes}")
    lines.append("")

    # Recommended Actions
    if recommended_actions:
        lines.append("## 10. Recommended Actions")
        lines.append("")
        for i, action in enumerate(recommended_actions, 1):
            lines.append(f"{i}. {action}")
        lines.append("")

    # Files Changed (for sandbox)
    if manifest_changed is not None or lockfile_changed is not None:
        lines.append("## 11. Files Changed")
        lines.append("")
        if manifest_changed:
            lines.append("- package.json: CHANGED")
        else:
            lines.append("- package.json: NO CHANGE")
        if lockfile_changed:
            lines.append("- package-lock.json or npm-shrinkwrap.json: CHANGED")
        else:
            lines.append("- package-lock.json or npm-shrinkwrap.json: NO CHANGE")
        lines.append("")

    # What Policy Scout Could Not Verify
    if could_not_verify:
        lines.append("## 12. What Policy Scout Could Not Verify")
        lines.append("")
        for item in could_not_verify:
            lines.append(f"- {item}")
        lines.append("")
    else:
        lines.append("## 12. What Policy Scout Could Not Verify")
        lines.append("")
        lines.append("- Network packet inspection")
        lines.append("- Full malware analysis of installed packages")
        lines.append("- Remote URL integrity after initial fetch")
        lines.append("")

    # Host Project Status (for sandbox)
    if report_type == "sandbox_result":
        lines.append("## 13. Host Project Status")
        lines.append("")
        lines.append(f"- Status: `{host_mutation_status}`")
        lines.append(f"- Migration: `{migration_status}`")
        lines.append("")

    # Audit Event IDs
    if audit_event_ids:
        lines.append("## 14. Audit Event IDs")
        lines.append("")
        for event_id in audit_event_ids:
            lines.append(f"- `{event_id}`")
        lines.append("")

    return "\n".join(lines)
