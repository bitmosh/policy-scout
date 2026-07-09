# SPDX-License-Identifier: Apache-2.0
"""Command decision report generation."""

from typing import Dict, Any, List, Optional
from .models import ScoutReport
from .writer import write_report
from .markdown_report import generate_markdown_report
from .json_report import generate_json_report


def generate_command_decision_report(
    request_id: str,
    command: str,
    decision: str,
    risk_score: int,
    risk_band: str,
    category: Optional[str] = None,
    reasons: Optional[List[str]] = None,
    audit_event_ids: Optional[List[str]] = None,
) -> ScoutReport:
    """Generate a command decision Scout Report.

    Args:
        request_id: Request ID
        command: The command that was checked
        decision: Policy decision (DENY, DENY_AND_ALERT, REQUIRE_APPROVAL, etc.)
        risk_score: Risk score
        risk_band: Risk band (low, medium, high, critical)
        category: Command category
        reasons: List of reasons for the decision
        audit_event_ids: List of audit event IDs

    Returns:
        ScoutReport with paths populated
    """
    from ..core.ids import generate_id, utcnow_iso

    report_id = generate_id("report")
    created_at = utcnow_iso()

    # Build title
    title = f"Command Decision: {decision}"

    # Build summary
    summary = f"Policy Scout evaluated the command and issued a {decision} decision with risk score {risk_score}/10 ({risk_band})."

    # Build findings
    findings = []
    if reasons:
        for reason in reasons:
            findings.append(
                {
                    "title": "Policy Decision Reason",
                    "severity": risk_band,
                    "category": category or "command_evaluation",
                    "message": reason,
                }
            )

    # Build recommended actions
    recommended_actions = []
    if decision == "DENY":
        recommended_actions.append("Do not execute this command.")
        recommended_actions.append("Review the reasons for the denial.")
        recommended_actions.append(
            "Consider an alternative approach if the operation is necessary."
        )
    elif decision == "DENY_AND_ALERT":
        recommended_actions.append("Do not execute this command.")
        recommended_actions.append("This command may expose credentials or secrets.")
        recommended_actions.append("Review credential access manually.")
    elif decision == "REQUIRE_APPROVAL":
        recommended_actions.append("Review the command before approval.")
        recommended_actions.append(
            "Use `policy-scout approvals show <id>` to review the approval request."
        )
    elif decision == "SANDBOX_FIRST":
        recommended_actions.append("Run the command in sandbox review first.")
        recommended_actions.append(
            "Use `policy-scout sandbox -- <command>` to test in sandbox."
        )

    # Build what could not verify
    could_not_verify = [
        "Full impact of command execution",
        "Side effects not visible in static analysis",
    ]

    # Generate Markdown
    markdown_content = generate_markdown_report(
        report_type="command_decision",
        title=title,
        summary=summary,
        decision=decision,
        risk_score=risk_score,
        risk_band=risk_band,
        command=command,
        findings=findings,
        could_not_verify=could_not_verify,
        audit_event_ids=audit_event_ids,
        recommended_actions=recommended_actions,
    )

    # Generate JSON
    json_content = generate_json_report(
        report_id=report_id,
        report_type="command_decision",
        title=title,
        summary=summary,
        request_id=request_id,
        decision=decision,
        risk_score=risk_score,
        risk_band=risk_band,
        command=command,
        findings=findings,
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
        report_type="command_decision",
        title=title,
        request_id=request_id,
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
