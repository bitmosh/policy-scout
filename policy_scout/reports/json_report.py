"""JSON report generation."""

from typing import Dict, Any, List, Optional
from ..audit.redaction import redact_dict


def generate_json_report(
    report_id: str,
    report_type: str,
    title: str,
    summary: str,
    request_id: str,
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
    redaction_applied: bool = False,
    files_changed: Optional[List[str]] = None,
    sweep_id: Optional[str] = None,
    project_root: Optional[str] = None,
    findings_count: Optional[Dict[str, int]] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a JSON Scout Report.

    Args:
        report_id: Report ID
        report_type: Type of report
        title: Report title
        summary: Summary of what happened
        request_id: Request ID
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
        redaction_applied: Whether redaction was applied
        files_changed: List of files changed in sandbox

    Returns:
        JSON-serializable dict
    """
    # Assess credential exposure based on findings
    credential_exposure_level = "none_detected"
    credential_exposure_notes = (
        "Policy Scout did not detect direct credential exposure in this operation."
    )

    if findings:
        credential_signal_categories = [
            "credential_exposure_signal",
            "package_manager_config",
            "suspicious_process",
        ]
        has_credential_signals = any(
            f.get("category") in credential_signal_categories for f in findings
        )

        if has_credential_signals:
            credential_exposure_level = "possible"
            credential_exposure_notes = "Findings include possible credential exposure signals. Review findings for details. This is not confirmed exposure, but warrants investigation."

    report = {
        "report_id": report_id,
        "report_type": report_type,
        "title": title,
        "summary": summary,
        "request_id": request_id,
        "decision": decision,
        "risk_score": risk_score,
        "risk_band": risk_band,
        "command": command,
        "sandbox_id": sandbox_id,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "lifecycle_scripts": lifecycle_scripts or [],
        "manifest_changed": manifest_changed,
        "lockfile_changed": lockfile_changed,
        "findings": findings or [],
        "host_mutation_status": host_mutation_status,
        "migration_status": migration_status,
        "could_not_verify": could_not_verify
        or [
            "Network packet inspection",
            "Full malware analysis of installed packages",
            "Remote URL integrity after initial fetch",
        ],
        "audit_event_ids": audit_event_ids or [],
        "recommended_actions": recommended_actions or [],
        "redaction_applied": redaction_applied,
        "files_changed": files_changed or [],
        "credential_exposure_assessment": {
            "level": credential_exposure_level,
            "notes": credential_exposure_notes,
        },
        "sweep_id": sweep_id,
        "project_root": project_root,
        "findings_count": findings_count,
        "created_at": created_at,
    }

    # Remove None values
    report = {k: v for k, v in report.items() if v is not None}

    # Redact sensitive values recursively
    report = redact_dict(report)

    return report
