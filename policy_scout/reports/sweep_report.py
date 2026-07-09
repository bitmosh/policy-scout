# SPDX-License-Identifier: Apache-2.0
"""Sweep report generation."""

import os
from dataclasses import dataclass
from typing import Optional, List
from ..sweep.models import SweepResult
from ..core.ids import generate_id
from .markdown_report import generate_markdown_report
from .json_report import generate_json_report


def generate_sweep_report(
    sweep_result: SweepResult,
    audit_event_ids: Optional[List[str]] = None,
    request_id: Optional[str] = None,
) -> "ScoutReport":
    """Generate Markdown and JSON Scout Reports for a sweep.

    Args:
        sweep_result: SweepResult from sweep engine
        audit_event_ids: List of audit event IDs to reference
        request_id: Request ID for the report

    Returns:
        ScoutReport with markdown_path and json_path
    """
    if audit_event_ids is None:
        audit_event_ids = []
    if request_id is None:
        request_id = generate_id("req")

    report_id = generate_id("report")

    # Build summary
    total_findings = sum(sweep_result.findings_count.values())

    # Generate created_at timestamp
    from ..core.ids import utcnow_iso

    created_at = utcnow_iso()

    # Determine report type and title based on sweep type
    if sweep_result.sweep_type == "quick_system":
        report_type = "system_quick_sweep"
        title = "Quick System Sweep"
        summary = f"Quick system sweep completed with {total_findings} findings. Critical: {sweep_result.findings_count.get('critical', 0)}, High: {sweep_result.findings_count.get('high', 0)}, Medium: {sweep_result.findings_count.get('medium', 0)}, Low: {sweep_result.findings_count.get('low', 0)}, Info: {sweep_result.findings_count.get('info', 0)}."
    else:
        report_type = "project_sweep"
        title = f"Project Sweep: {sweep_result.project_root}"
        summary = f"Project sweep completed with {total_findings} findings. Critical: {sweep_result.findings_count.get('critical', 0)}, High: {sweep_result.findings_count.get('high', 0)}, Medium: {sweep_result.findings_count.get('medium', 0)}, Low: {sweep_result.findings_count.get('low', 0)}, Info: {sweep_result.findings_count.get('info', 0)}."

    # Convert findings to report format
    findings = []
    for finding in sweep_result.findings:
        findings.append(
            {
                "title": finding.title,
                "severity": finding.severity,
                "category": finding.category,
                "location": finding.location,
                "evidence_ref": finding.evidence_ref,
                "why_it_matters": finding.why_it_matters,
                "recommended_action": finding.recommended_action,
            }
        )

    # Build recommended actions
    recommended_actions = []
    if sweep_result.findings_count.get("critical", 0) > 0:
        recommended_actions.append("Review critical findings immediately.")
    if sweep_result.findings_count.get("high", 0) > 0:
        recommended_actions.append("Review high-severity findings before proceeding.")
    if sweep_result.findings_count.get("medium", 0) > 0:
        recommended_actions.append(
            "Review medium-severity findings at your earliest convenience."
        )
    if not recommended_actions:
        recommended_actions.append(
            "No suspicious findings detected. Continue monitoring."
        )

    # Generate Markdown report
    markdown = generate_markdown_report(
        report_type=report_type,
        title=title,
        summary=summary,
        command=None,
        findings=findings,
        lifecycle_scripts=None,
        recommended_actions=recommended_actions,
        could_not_verify=sweep_result.could_not_verify,
    )

    # Generate JSON report
    json_report = generate_json_report(
        report_id=report_id,
        report_type=report_type,
        title=title,
        summary=summary,
        request_id=request_id,
        command=None,
        decision=None,
        risk_score=None,
        risk_band=None,
        findings=findings,
        lifecycle_scripts=None,
        recommended_actions=recommended_actions,
        could_not_verify=sweep_result.could_not_verify,
        audit_event_ids=audit_event_ids,
        redaction_applied=True,
        sweep_id=sweep_result.sweep_id,
        project_root=sweep_result.project_root,
        findings_count=sweep_result.findings_count,
        created_at=created_at,
    )

    # Write report files
    report_root = os.environ.get(
        "POLICY_SCOUT_REPORT_ROOT",
        os.path.expanduser("~/.local/share/policy-scout/reports"),
    )
    report_dir = os.path.join(report_root, report_id)
    os.makedirs(report_dir, exist_ok=True)

    markdown_path = os.path.join(report_dir, "report.md")
    json_path = os.path.join(report_dir, "report.json")

    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    with open(json_path, "w", encoding="utf-8") as f:
        import json

        json.dump(json_report, f, indent=2)

    return ScoutReport(
        report_id=report_id,
        report_type=report_type,
        markdown_path=markdown_path,
        json_path=json_path,
    )


@dataclass
class ScoutReport:
    """Scout Report paths."""

    report_id: str
    report_type: str
    markdown_path: str
    json_path: str
