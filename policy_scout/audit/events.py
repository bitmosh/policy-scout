"""Audit event models."""

from dataclasses import dataclass, field
from typing import Optional
from ..core.ids import generate_id, utcnow_iso


AUDIT_SCHEMA_VERSION = 1


@dataclass
class AuditEvent:
    """Base audit event."""

    event_id: str = field(default_factory=lambda: generate_id("evt"))
    event_type: str = ""
    timestamp: str = field(default_factory=utcnow_iso)
    request_id: str = ""
    summary: str = ""
    data: dict = field(default_factory=dict)
    actor: Optional[dict] = None
    schema_version: int = AUDIT_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "summary": self.summary,
            "data": self.data,
            "actor": self.actor,
            "schema_version": self.schema_version,
        }


# Canonical event types
class EventType:
    """Canonical audit event types."""

    COMMAND_REQUESTED = "CommandRequested"
    COMMAND_PARSED = "CommandParsed"
    COMMAND_CLASSIFIED = "CommandClassified"
    POLICY_MATCHED = "PolicyMatched"
    DECISION_ISSUED = "DecisionIssued"
    POLICY_ERROR = "PolicyError"
    AUDIT_ERROR = "AuditError"
    APPROVAL_REQUESTED = "ApprovalRequested"
    APPROVAL_SHOWN = "ApprovalShown"
    APPROVAL_APPROVED_ONCE = "ApprovalApprovedOnce"
    APPROVAL_DENIED_ONCE = "ApprovalDeniedOnce"
    APPROVAL_EXPIRED = "ApprovalExpired"
    APPROVAL_ERROR = "ApprovalError"
    APPROVAL_EXECUTION_STARTED = "ApprovalExecutionStarted"
    APPROVAL_EXECUTION_COMPLETED = "ApprovalExecutionCompleted"
    APPROVAL_EXECUTION_FAILED = "ApprovalExecutionFailed"
    SANDBOX_REQUESTED = "SandboxRequested"
    SANDBOX_WORKSPACE_CREATED = "SandboxWorkspaceCreated"
    SANDBOX_INSTALL_STARTED = "SandboxInstallStarted"
    SANDBOX_INSTALL_COMPLETED = "SandboxInstallCompleted"
    LIFECYCLE_SCRIPTS_INSPECTED = "LifecycleScriptsInspected"
    SANDBOX_RESULT_WRITTEN = "SandboxResultWritten"
    SANDBOX_ERROR = "SandboxError"
    SANDBOX_MIGRATION_REQUESTED = "SandboxMigrationRequested"
    SANDBOX_MIGRATION_PLANNED = "SandboxMigrationPlanned"
    SANDBOX_MIGRATION_STARTED = "SandboxMigrationStarted"
    SANDBOX_MIGRATION_COMPLETED = "SandboxMigrationCompleted"
    SANDBOX_MIGRATION_BLOCKED = "SandboxMigrationBlocked"
    SANDBOX_MIGRATION_FAILED = "SandboxMigrationFailed"
    SCOUT_REPORT_GENERATED = "ScoutReportGenerated"
    SWEEP_STARTED = "SweepStarted"
    SWEEP_FINDING_CREATED = "SweepFindingCreated"
    SWEEP_COMPLETED = "SweepCompleted"
    SWEEP_ERROR = "SweepError"
    COMMAND_EXECUTION_STARTED = "CommandExecutionStarted"
    COMMAND_EXECUTION_COMPLETED = "CommandExecutionCompleted"
    COMMAND_EXECUTION_BLOCKED = "CommandExecutionBlocked"
    COMMAND_EXECUTION_FAILED = "CommandExecutionFailed"
    # [05] Tamper-Evident Audit
    CHAIN_VERIFICATION_COMPLETED = "ChainVerificationCompleted"
    # [13] Self-Integrity
    INTEGRITY_CHECK_FAILED = "IntegrityCheckFailed"
    INTEGRITY_CHECK_PASSED = "IntegrityCheckPassed"
    # [09] Incident Response
    LOCKDOWN_ACTIVATED = "LockdownActivated"
    LOCKDOWN_DEACTIVATED = "LockdownDeactivated"
    EVIDENCE_PRESERVED = "EvidencePreserved"
    CLEARANCE_CHECK_RUN = "ClearanceCheckRun"
    # [04] Secret Scanning
    SECRET_SCAN_COMPLETED = "SecretScanCompleted"
    SECRET_FINDING_CREATED = "SecretFindingCreated"
    # [10] Policy Management
    PROJECT_OVERRIDE_LOADED = "ProjectOverrideLoaded"
    PROJECT_OVERRIDE_VIOLATED = "ProjectOverrideViolated"
    POLICY_SIMULATED = "PolicySimulated"
    POLICY_VALIDATED = "PolicyValidated"
    POLICY_HISTORY_TESTED = "PolicyHistoryTested"
    # [01] Watch Mode Daemon
    WATCH_TRIGGER_DETECTED = "WatchTriggerDetected"
    WATCH_DAEMON_STARTED = "WatchDaemonStarted"
    WATCH_DAEMON_STOPPED = "WatchDaemonStopped"
    WATCH_DAEMON_HEARTBEAT = "WatchDaemonHeartbeat"
    # [02] Threat Intelligence
    INTEL_LOOKUP_COMPLETED = "IntelLookupCompleted"
    INTEL_CACHE_HIT = "IntelCacheHit"
    INTEL_LOOKUP_FAILED = "IntelLookupFailed"
    # [06] MCP Server
    MCP_SERVER_STARTED = "McpServerStarted"
    MCP_TOOL_CALL_RECEIVED = "McpToolCallReceived"
    MCP_TOOL_CALL_COMPLETED = "McpToolCallCompleted"
    MCP_SESSION_ENDED = "McpSessionEnded"
    # [08] General Sandbox
    GENERAL_SANDBOX_STARTED = "GeneralSandboxStarted"
    GENERAL_SANDBOX_COMPLETED = "GeneralSandboxCompleted"
    SANDBOX_BEHAVIOR_FINDING = "SandboxBehaviorFinding"
    # [07] Prompt Injection Detection
    INJECTION_PATTERN_FOUND = "InjectionPatternFound"
    INJECTION_FOUND_IN_TOOL_RESPONSE = "InjectionFoundInToolResponse"
    CANARY_FILE_INSTALLED = "CanaryFileInstalled"
    CANARY_AUDIT_HIT_DETECTED = "CanaryAuditHitDetected"
    # [03] Supply Chain Detection Depth
    SUPPLY_CHAIN_ANALYSIS_COMPLETED = "SupplyChainAnalysisCompleted"
    DEPENDENCY_CONFUSION_SUSPECTED = "DependencyConfusionSuspected"
    PUBLISH_ANOMALY_DETECTED = "PublishAnomalyDetected"


def create_command_requested_event(
    request_id: str, command: str, actor: Optional[dict] = None
) -> AuditEvent:
    """Create a CommandRequested event."""
    return AuditEvent(
        event_type=EventType.COMMAND_REQUESTED,
        request_id=request_id,
        summary=f"Command requested: {command}",
        data={"command": command},
        actor=actor,
    )


def create_command_parsed_event(request_id: str, parse_result: dict) -> AuditEvent:
    """Create a CommandParsed event."""
    return AuditEvent(
        event_type=EventType.COMMAND_PARSED,
        request_id=request_id,
        summary="Command parsed successfully",
        data={
            "primary_command": parse_result.get("primary_command"),
            "args": parse_result.get("args"),
            "structure": parse_result.get("structure"),
        },
    )


def create_command_classified_event(
    request_id: str, classification: dict
) -> AuditEvent:
    """Create a CommandClassified event."""
    return AuditEvent(
        event_type=EventType.COMMAND_CLASSIFIED,
        request_id=request_id,
        summary=f"Command classified as: {classification.get('category')}",
        data={
            "category": classification.get("category"),
            "categories": classification.get("categories"),
            "capabilities": classification.get("capabilities"),
            "confidence": classification.get("confidence"),
            "registry_hits": classification.get("registry_hits", []),
        },
    )


def create_policy_matched_event(request_id: str, policy_hits: list) -> AuditEvent:
    """Create a PolicyMatched event."""
    return AuditEvent(
        event_type=EventType.POLICY_MATCHED,
        request_id=request_id,
        summary=f"Policy matched: {len(policy_hits)} rules",
        data={"policy_hits": policy_hits},
    )


def create_decision_issued_event(
    request_id: str, decision: str, risk_score: int, risk_band: str, reasons: list
) -> AuditEvent:
    """Create a DecisionIssued event."""
    return AuditEvent(
        event_type=EventType.DECISION_ISSUED,
        request_id=request_id,
        summary=f"Decision issued: {decision}",
        data={
            "decision": decision,
            "risk_score": risk_score,
            "risk_band": risk_band,
            "reasons": reasons,
        },
    )


def create_policy_error_event(request_id: str, error_message: str) -> AuditEvent:
    """Create a PolicyError event."""
    return AuditEvent(
        event_type=EventType.POLICY_ERROR,
        request_id=request_id,
        summary="Policy evaluation error",
        data={"error": error_message},
    )


def create_audit_error_event(request_id: str, error_message: str) -> AuditEvent:
    """Create an AuditError event."""
    return AuditEvent(
        event_type=EventType.AUDIT_ERROR,
        request_id=request_id,
        summary="Audit system error",
        data={"error": error_message},
    )


def create_approval_requested_event(
    request_id: str, approval_id: str, command: str, actor: Optional[dict] = None
) -> AuditEvent:
    """Create an ApprovalRequested event."""
    return AuditEvent(
        event_type=EventType.APPROVAL_REQUESTED,
        request_id=request_id,
        summary=f"Approval requested for: {command}",
        data={"approval_id": approval_id, "command": command},
        actor=actor,
    )


def create_approval_shown_event(
    request_id: str, approval_id: str, actor: Optional[dict] = None
) -> AuditEvent:
    """Create an ApprovalShown event."""
    return AuditEvent(
        event_type=EventType.APPROVAL_SHOWN,
        request_id=request_id,
        summary=f"Approval shown: {approval_id}",
        data={"approval_id": approval_id},
        actor=actor,
    )


def create_approval_approved_once_event(
    request_id: str, approval_id: str, actor: Optional[dict] = None
) -> AuditEvent:
    """Create an ApprovalApprovedOnce event."""
    return AuditEvent(
        event_type=EventType.APPROVAL_APPROVED_ONCE,
        request_id=request_id,
        summary=f"Approval approved once: {approval_id}",
        data={"approval_id": approval_id},
        actor=actor,
    )


def create_approval_denied_once_event(
    request_id: str, approval_id: str, actor: Optional[dict] = None
) -> AuditEvent:
    """Create an ApprovalDeniedOnce event."""
    return AuditEvent(
        event_type=EventType.APPROVAL_DENIED_ONCE,
        request_id=request_id,
        summary=f"Approval denied once: {approval_id}",
        data={"approval_id": approval_id},
        actor=actor,
    )


def create_approval_expired_event(request_id: str, approval_id: str) -> AuditEvent:
    """Create an ApprovalExpired event."""
    return AuditEvent(
        event_type=EventType.APPROVAL_EXPIRED,
        request_id=request_id,
        summary=f"Approval expired: {approval_id}",
        data={"approval_id": approval_id},
    )


def create_approval_error_event(request_id: str, error_message: str) -> AuditEvent:
    """Create an ApprovalError event."""
    return AuditEvent(
        event_type=EventType.APPROVAL_ERROR,
        request_id=request_id,
        summary="Approval system error",
        data={"error": error_message},
    )


def create_sandbox_requested_event(
    request_id: str, command: str, actor: Optional[dict] = None
) -> AuditEvent:
    """Create a SandboxRequested event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_REQUESTED,
        request_id=request_id,
        summary=f"Sandbox requested for command: {command}",
        data={"command": command},
        actor=actor,
    )


def create_sandbox_workspace_created_event(
    request_id: str, sandbox_id: str, workspace_path: str
) -> AuditEvent:
    """Create a SandboxWorkspaceCreated event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_WORKSPACE_CREATED,
        request_id=request_id,
        summary=f"Sandbox workspace created: {workspace_path}",
        data={"sandbox_id": sandbox_id, "workspace_path": workspace_path},
    )


def create_sandbox_install_started_event(
    request_id: str, sandbox_id: str, command: str
) -> AuditEvent:
    """Create a SandboxInstallStarted event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_INSTALL_STARTED,
        request_id=request_id,
        summary=f"Sandbox install started: {command}",
        data={"sandbox_id": sandbox_id, "command": command},
    )


def create_sandbox_install_completed_event(
    request_id: str, sandbox_id: str, exit_code: int, duration_ms: int
) -> AuditEvent:
    """Create a SandboxInstallCompleted event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_INSTALL_COMPLETED,
        request_id=request_id,
        summary=f"Sandbox install completed with exit code: {exit_code}",
        data={
            "sandbox_id": sandbox_id,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
        },
    )


def create_lifecycle_scripts_inspected_event(
    request_id: str, sandbox_id: str, script_count: int
) -> AuditEvent:
    """Create a LifecycleScriptsInspected event."""
    return AuditEvent(
        event_type=EventType.LIFECYCLE_SCRIPTS_INSPECTED,
        request_id=request_id,
        summary=f"Lifecycle scripts inspected: {script_count} found",
        data={"sandbox_id": sandbox_id, "script_count": script_count},
    )


def create_sandbox_result_written_event(
    request_id: str, sandbox_id: str, result_path: str
) -> AuditEvent:
    """Create a SandboxResultWritten event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_RESULT_WRITTEN,
        request_id=request_id,
        summary=f"Sandbox result written: {result_path}",
        data={"sandbox_id": sandbox_id, "result_path": result_path},
    )


def create_sandbox_error_event(
    request_id: str, sandbox_id: str, error_message: str
) -> AuditEvent:
    """Create a SandboxError event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_ERROR,
        request_id=request_id,
        summary="Sandbox error",
        data={"sandbox_id": sandbox_id, "error": error_message},
    )


def create_scout_report_generated_event(
    request_id: str, report_id: str, report_type: str, report_path: str
) -> AuditEvent:
    """Create a ScoutReportGenerated event."""
    return AuditEvent(
        event_type=EventType.SCOUT_REPORT_GENERATED,
        request_id=request_id,
        summary=f"Scout Report generated: {report_type}",
        data={
            "report_id": report_id,
            "report_type": report_type,
            "report_path": report_path,
        },
    )


def create_sweep_started_event(
    request_id: str, sweep_id: str, sweep_type: str, project_root: str
) -> AuditEvent:
    """Create a SweepStarted event."""
    return AuditEvent(
        event_type=EventType.SWEEP_STARTED,
        request_id=request_id,
        summary=f"Sweep started: {sweep_type}",
        data={
            "sweep_id": sweep_id,
            "sweep_type": sweep_type,
            "project_root": project_root,
        },
    )


def create_sweep_finding_created_event(
    request_id: str, sweep_id: str, finding_id: str, category: str, severity: str
) -> AuditEvent:
    """Create a SweepFindingCreated event."""
    return AuditEvent(
        event_type=EventType.SWEEP_FINDING_CREATED,
        request_id=request_id,
        summary=f"Sweep finding created: {category}",
        data={
            "sweep_id": sweep_id,
            "finding_id": finding_id,
            "category": category,
            "severity": severity,
        },
    )


def create_sweep_completed_event(
    request_id: str, sweep_id: str, findings_count: dict, duration_ms: int
) -> AuditEvent:
    """Create a SweepCompleted event."""
    # Compute total from severity buckets if 'total' key is absent
    total_findings = findings_count.get("total")
    if total_findings is None:
        total_findings = sum(
            findings_count.get(k, 0)
            for k in ["critical", "high", "medium", "low", "info"]
        )

    return AuditEvent(
        event_type=EventType.SWEEP_COMPLETED,
        request_id=request_id,
        summary=f"Sweep completed: {total_findings} findings",
        data={
            "sweep_id": sweep_id,
            "findings_count": findings_count,
            "duration_ms": duration_ms,
        },
    )


def create_sweep_error_event(
    request_id: str, sweep_id: str, error_message: str
) -> AuditEvent:
    """Create a SweepError event."""
    return AuditEvent(
        event_type=EventType.SWEEP_ERROR,
        request_id=request_id,
        summary="Sweep error",
        data={"sweep_id": sweep_id, "error": error_message},
    )


def create_approval_execution_started_event(
    request_id: str,
    approval_id: str,
    command: str,
    original_policy_decision: str = "",
    execution_id: str = "",
) -> AuditEvent:
    """Create an ApprovalExecutionStarted event."""
    return AuditEvent(
        event_type=EventType.APPROVAL_EXECUTION_STARTED,
        request_id=request_id,
        summary=f"Approval execution started: {approval_id}",
        data={
            "approval_id": approval_id,
            "command": command,
            "original_policy_decision": original_policy_decision,
            "execution_route": "approved_once",
            "execution_id": execution_id,
        },
    )


def create_approval_execution_completed_event(
    request_id: str,
    approval_id: str,
    command: str,
    exit_code: int,
    original_policy_decision: str = "",
    execution_id: str = "",
) -> AuditEvent:
    """Create an ApprovalExecutionCompleted event."""
    return AuditEvent(
        event_type=EventType.APPROVAL_EXECUTION_COMPLETED,
        request_id=request_id,
        summary=f"Approval execution completed: {approval_id}",
        data={
            "approval_id": approval_id,
            "command": command,
            "exit_code": exit_code,
            "original_policy_decision": original_policy_decision,
            "execution_route": "approved_once",
            "execution_id": execution_id,
        },
    )


def create_approval_execution_failed_event(
    request_id: str,
    approval_id: str,
    command: str,
    reason: str,
    original_policy_decision: str = "",
    execution_id: str = "",
) -> AuditEvent:
    """Create an ApprovalExecutionFailed event."""
    return AuditEvent(
        event_type=EventType.APPROVAL_EXECUTION_FAILED,
        request_id=request_id,
        summary=f"Approval execution failed: {approval_id}",
        data={
            "approval_id": approval_id,
            "command": command,
            "reason": reason,
            "original_policy_decision": original_policy_decision,
            "execution_route": "approved_once",
            "execution_id": execution_id,
        },
    )


def create_sandbox_migration_requested_event(
    request_id: str,
    migration_id: str,
    sandbox_id: str,
    host_project_root: str,
) -> AuditEvent:
    """Create a SandboxMigrationRequested event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_MIGRATION_REQUESTED,
        request_id=request_id,
        summary=f"Sandbox migration requested: {migration_id} for sandbox {sandbox_id}",
        data={
            "migration_id": migration_id,
            "sandbox_id": sandbox_id,
            "host_project_root": host_project_root,
        },
    )


def create_sandbox_migration_planned_event(
    request_id: str,
    migration_id: str,
    sandbox_id: str,
    host_project_root: str,
    files_planned: list,
) -> AuditEvent:
    """Create a SandboxMigrationPlanned event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_MIGRATION_PLANNED,
        request_id=request_id,
        summary=f"Sandbox migration planned: {migration_id}",
        data={
            "migration_id": migration_id,
            "sandbox_id": sandbox_id,
            "host_project_root": host_project_root,
            "files_planned": files_planned,
        },
    )


def create_sandbox_migration_started_event(
    request_id: str,
    migration_id: str,
    sandbox_id: str,
    host_project_root: str,
    files_planned: list,
) -> AuditEvent:
    """Create a SandboxMigrationStarted event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_MIGRATION_STARTED,
        request_id=request_id,
        summary=f"Sandbox migration started: {migration_id}",
        data={
            "migration_id": migration_id,
            "sandbox_id": sandbox_id,
            "host_project_root": host_project_root,
            "files_planned": files_planned,
        },
    )


def create_sandbox_migration_completed_event(
    request_id: str,
    migration_id: str,
    sandbox_id: str,
    host_project_root: str,
    files_migrated: list,
    files_skipped: list,
    backups_created: list,
) -> AuditEvent:
    """Create a SandboxMigrationCompleted event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_MIGRATION_COMPLETED,
        request_id=request_id,
        summary=f"Sandbox migration completed: {migration_id}",
        data={
            "migration_id": migration_id,
            "sandbox_id": sandbox_id,
            "host_project_root": host_project_root,
            "files_migrated": files_migrated,
            "files_skipped": files_skipped,
            "backups_created": backups_created,
        },
    )


def create_sandbox_migration_blocked_event(
    request_id: str,
    migration_id: str,
    sandbox_id: str,
    host_project_root: str,
    block_reasons: list,
) -> AuditEvent:
    """Create a SandboxMigrationBlocked event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_MIGRATION_BLOCKED,
        request_id=request_id,
        summary=f"Sandbox migration blocked: {migration_id}",
        data={
            "migration_id": migration_id,
            "sandbox_id": sandbox_id,
            "host_project_root": host_project_root,
            "block_reasons": block_reasons,
        },
    )


def create_sandbox_migration_failed_event(
    request_id: str,
    migration_id: str,
    sandbox_id: str,
    host_project_root: str,
    reason: str,
) -> AuditEvent:
    """Create a SandboxMigrationFailed event."""
    return AuditEvent(
        event_type=EventType.SANDBOX_MIGRATION_FAILED,
        request_id=request_id,
        summary=f"Sandbox migration failed: {migration_id}",
        data={
            "migration_id": migration_id,
            "sandbox_id": sandbox_id,
            "host_project_root": host_project_root,
            "reason": reason,
        },
    )


# ── [05] Tamper-Evident Audit ──────────────────────────────────────────────


def create_chain_verification_event(
    verified: bool, total_entries: int, error_count: int
) -> AuditEvent:
    """Create a ChainVerificationCompleted event."""
    return AuditEvent(
        event_type=EventType.CHAIN_VERIFICATION_COMPLETED,
        summary=(
            f"Chain verification {'PASSED' if verified else 'FAILED'} "
            f"({total_entries} entries)"
        ),
        data={
            "verified": verified,
            "total_entries": total_entries,
            "error_count": error_count,
        },
    )


# ── [13] Self-Integrity ────────────────────────────────────────────────────


def create_integrity_check_failed_event(errors: list) -> AuditEvent:
    """Create an IntegrityCheckFailed event."""
    return AuditEvent(
        event_type=EventType.INTEGRITY_CHECK_FAILED,
        summary=f"Registry integrity check failed: {len(errors)} file(s)",
        data={"errors": errors, "error_count": len(errors)},
    )


def create_integrity_check_passed_event(files_checked: int) -> AuditEvent:
    """Create an IntegrityCheckPassed event."""
    return AuditEvent(
        event_type=EventType.INTEGRITY_CHECK_PASSED,
        summary=f"Registry integrity verified: {files_checked} files",
        data={"files_checked": files_checked},
    )


# ── [09] Incident Response ─────────────────────────────────────────────────


def create_lockdown_activated_event(reason: str) -> AuditEvent:
    """Create a LockdownActivated event."""
    return AuditEvent(
        event_type=EventType.LOCKDOWN_ACTIVATED,
        summary="Lockdown mode activated",
        data={"reason": reason},
    )


def create_lockdown_deactivated_event(cleared_by: str = "") -> AuditEvent:
    """Create a LockdownDeactivated event."""
    return AuditEvent(
        event_type=EventType.LOCKDOWN_DEACTIVATED,
        summary="Lockdown mode deactivated",
        data={"cleared_by": cleared_by},
    )


def create_evidence_preserved_event(
    archive_path: str, artifact_count: int
) -> AuditEvent:
    """Create an EvidencePreserved event."""
    return AuditEvent(
        event_type=EventType.EVIDENCE_PRESERVED,
        summary=f"Evidence archive created: {artifact_count} artifact(s)",
        data={"archive_path": archive_path, "artifact_count": artifact_count},
    )


def create_clearance_check_event(passed: bool, check_summary: dict) -> AuditEvent:
    """Create a ClearanceCheckRun event."""
    return AuditEvent(
        event_type=EventType.CLEARANCE_CHECK_RUN,
        summary=f"Clearance check {'passed' if passed else 'failed'}",
        data={"passed": passed, "checks": check_summary},
    )


# ── [04] Secret Scanning ───────────────────────────────────────────────────


def create_secret_scan_completed_event(
    scan_id: str,
    scan_type: str,
    target: str,
    finding_count: int,
    severity_counts: dict,
    files_scanned: int,
    duration_ms: int,
) -> AuditEvent:
    """Create a SecretScanCompleted event."""
    return AuditEvent(
        event_type=EventType.SECRET_SCAN_COMPLETED,
        summary=f"Secret scan completed: {finding_count} finding(s) in {target}",
        data={
            "scan_id": scan_id,
            "scan_type": scan_type,
            "target": target,
            "finding_count": finding_count,
            "severity_counts": severity_counts,
            "files_scanned": files_scanned,
            "duration_ms": duration_ms,
        },
    )


def create_secret_finding_event(
    scan_id: str,
    secret_type: str,
    service: str,
    severity: str,
    source: str,
    line: int,
) -> AuditEvent:
    """Create a SecretFindingCreated event (one per finding)."""
    return AuditEvent(
        event_type=EventType.SECRET_FINDING_CREATED,
        summary=f"Secret found: {service} {secret_type} in {source}:{line}",
        data={
            "scan_id": scan_id,
            "secret_type": secret_type,
            "service": service,
            "severity": severity,
            "source": source,
            "line": line,
        },
    )
