"""run command handler."""

import json
import sys
import os
from typing import Optional

from ...core.request import CommandRequest, Actor
from ...classify.shell_parser import ShellParser
from ...classify.command_classifier import CommandClassifier
from ...policy.risk_scorer import RiskScorer
from ...policy.engine import PolicyEngine
from ...registry.loader import RegistryLoader
from ...audit.store import AuditStore
from ...audit.events import (
    create_command_requested_event,
    create_command_parsed_event,
    create_command_classified_event,
    create_policy_matched_event,
    create_decision_issued_event,
    create_approval_requested_event,
)
from ...approvals.store import ApprovalStore
from ...approvals.models import ApprovalRequest
from ...core.ids import generate_id
from ...core.decision import derive_risk_band
from ...executor.direct_executor import DirectExecutor


def handle_run_command(
    command: str,
    json_output: bool = False,
    audit_enabled: bool = True,
    approval_id: Optional[str] = None,
):
    """Handle run command - execute allowed commands through policy gate."""

    # Initialize audit store
    audit_store = AuditStore(enabled=audit_enabled)

    # Initialize approval store
    approval_store = ApprovalStore()

    # Load registries
    loader = RegistryLoader()
    command_registry = loader.command_registry
    policy_registry = loader.policy_registry

    # Create request
    request = CommandRequest(
        actor=Actor(type="human", name="cli_user"), command=command, cwd=os.getcwd()
    )

    # Write CommandRequested event
    if audit_store.enabled:
        audit_store.write(
            create_command_requested_event(
                request.request_id,
                command,
                actor={"type": request.actor.type, "name": request.actor.name},
            )
        )

    # Parse command
    parser = ShellParser()
    parse_result = parser.parse(command, request.request_id)

    # Write CommandParsed event
    if audit_store.enabled:
        audit_store.write(
            create_command_parsed_event(request.request_id, parse_result.to_dict())
        )

    # Classify command with registry
    classifier = CommandClassifier(command_registry=command_registry)
    classification = classifier.classify(parse_result, command, request.request_id)

    # Write CommandClassified event
    if audit_store.enabled:
        audit_store.write(
            create_command_classified_event(
                request.request_id, classification.to_dict()
            )
        )

    # Score risk
    risk_scorer = RiskScorer()
    risk_score = risk_scorer.score(classification, request.request_id)

    # Evaluate policy with registry
    policy_engine = PolicyEngine(policy_registry=policy_registry)
    decision = policy_engine.evaluate(
        classification, risk_score, request.request_id, command=request.command
    )

    # Write PolicyMatched event
    if audit_store.enabled and decision.policy_hits:
        audit_store.write(
            create_policy_matched_event(request.request_id, decision.policy_hits)
        )

    # Write DecisionIssued event
    if audit_store.enabled:
        # Derive risk band from risk score
        risk_band = derive_risk_band(decision.risk_score)

        audit_store.write(
            create_decision_issued_event(
                request_id=request.request_id,
                decision=decision.decision,
                risk_score=decision.risk_score,
                risk_band=risk_band,
                reasons=decision.reasons,
            )
        )

    # Route based on decision
    executor = DirectExecutor()

    if decision.decision in ["ALLOW", "ALLOW_LOGGED"]:
        # Write CommandExecutionStarted event as CRITICAL before execution
        if audit_store.enabled:
            execution_id = generate_id("exec")
            started_event = executor.create_execution_started_event(
                request_id=request.request_id,
                execution_id=execution_id,
                command=command,
            )
            if not audit_store.write(started_event, critical=True):
                print(
                    "Error: Failed to persist audit event. Command not executed for safety.",
                    file=sys.stderr,
                )
                sys.exit(30)
        else:
            execution_id = generate_id("exec")

        # Execute the command
        execution_result = executor.execute(
            command=command,
            cwd=os.getcwd(),
            request_id=request.request_id,
            decision_id=decision.decision_id,
            decision=decision.decision,
            execution_id=execution_id,
        )

        # Write CommandExecutionCompleted event
        if audit_store.enabled:
            audit_store.write(
                executor.create_execution_completed_event(
                    request_id=request.request_id,
                    execution_id=execution_result.execution_id,
                    command=command,
                    exit_code=execution_result.exit_code or -1,
                    duration_ms=execution_result.duration_ms or 0,
                )
            )

        # Output results
        if json_output:
            print(json.dumps(execution_result.to_dict(), indent=2))
        else:
            print("Policy Scout Run")
            print()
            print(f"Decision: {decision.decision}")
            print(f"Command: {command}")
            print()
            print("Running command...")
            print(f"Exit code: {execution_result.exit_code}")
            if execution_result.stdout:
                print(f"Stdout: {execution_result.stdout}")
            if execution_result.stderr:
                print(f"Stderr: {execution_result.stderr}")
            print()

        # Set exit code based on command exit code
        if execution_result.exit_code != 0:
            sys.exit(execution_result.exit_code or 1)
        else:
            sys.exit(0)

    elif decision.decision == "REQUIRE_APPROVAL":
        # Check if approval_id is provided for one-time execution
        if approval_id:
            from ...audit.events import (
                create_approval_execution_started_event,
                create_approval_execution_completed_event,
                create_approval_execution_failed_event,
            )

            # Load approval by ID
            approval = approval_store.get_by_id(approval_id)
            if not approval:
                print(f"Error: Approval not found: {approval_id}", file=sys.stderr)
                sys.exit(1)

            # Validate approval status
            if approval.status != "approved_once":
                print(
                    f"Error: Approval status is '{approval.status}', not 'approved_once'. Cannot execute.",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Validate approval scope
            if approval.scope != "once":
                print(
                    f"Error: Approval scope is '{approval.scope}', not 'once'. Cannot execute.",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Validate command exact match
            if approval.command != command:
                print(
                    f"Error: Command mismatch. Approval command: '{approval.command}', Requested command: '{command}'",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Validate cwd exact match
            current_cwd = os.getcwd()
            if approval.cwd != current_cwd:
                print(
                    f"Error: CWD mismatch. Approval CWD: '{approval.cwd}', Current CWD: '{current_cwd}'",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Validate approval not expired
            from ...core.ids import utcnow_timestamp

            current_time = utcnow_timestamp()
            # Parse expires_at (ISO format) to timestamp
            from datetime import datetime

            expires_at = datetime.fromisoformat(
                approval.expires_at.replace("Z", "+00:00")
            ).timestamp()
            if current_time > expires_at:
                print(
                    f"Error: Approval expired at {approval.expires_at}",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Re-evaluate policy for the command
            # This ensures approval cannot bypass hard-deny or sandbox-first decisions
            registry_loader = RegistryLoader()
            command_registry = registry_loader.load_command_registry()
            policy_registry = registry_loader.load_policy_registry()
            parser = ShellParser()
            parse_result = parser.parse(command)
            classifier = CommandClassifier(command_registry=command_registry)
            classification = classifier.classify(
                parse_result, command, request.request_id
            )
            risk_scorer = RiskScorer()
            risk_score = risk_scorer.score(classification, command_registry)
            policy_engine = PolicyEngine(policy_registry)
            re_decision = policy_engine.evaluate(
                classification=classification,
                risk_score=risk_score,
                request_id=request.request_id,
                command=command,
            )

            # Only proceed if current decision is REQUIRE_APPROVAL
            if re_decision.decision != "REQUIRE_APPROVAL":
                print(
                    f"Error: Current policy decision is '{re_decision.decision}', not 'REQUIRE_APPROVAL'. Approval cannot bypass this decision.",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Pre-generate execution_id for critical audit
            execution_id = generate_id("exec")

            # Write ApprovalExecutionStarted event
            if audit_store.enabled:
                audit_store.write(
                    create_approval_execution_started_event(
                        request_id=request.request_id,
                        approval_id=approval.approval_id,
                        command=command,
                        original_policy_decision=decision.decision,
                        execution_id=execution_id,
                    )
                )

            # Write CommandExecutionStarted event with critical flag
            if audit_store.enabled:
                started_event = executor.create_execution_started_event(
                    request_id=request.request_id,
                    execution_id=execution_id,
                    command=command,
                    approval_id=approval.approval_id,
                )
                if not audit_store.write(started_event, critical=True):
                    print(
                        "Error: Failed to persist audit event. Command not executed for safety.",
                        file=sys.stderr,
                    )
                    # Mark approval as failed
                    approval_store.update_status(approval.approval_id, "failed")
                    sys.exit(30)

            # Execute the command
            # Use ALLOW decision since approval has been validated
            execution_result = executor.execute(
                command=command,
                cwd=os.getcwd(),
                request_id=request.request_id,
                decision_id=decision.decision_id,
                decision="ALLOW",
                execution_id=execution_id,
            )

            # Write CommandExecutionCompleted event
            if audit_store.enabled:
                audit_store.write(
                    executor.create_execution_completed_event(
                        request_id=request.request_id,
                        execution_id=execution_result.execution_id,
                        command=command,
                        exit_code=execution_result.exit_code or -1,
                        duration_ms=execution_result.duration_ms or 0,
                    )
                )

            # Mark approval based on execution result
            if execution_result.exit_code == 0:
                approval_store.update_status(approval.approval_id, "executed")
                # Write ApprovalExecutionCompleted event
                if audit_store.enabled:
                    audit_store.write(
                        create_approval_execution_completed_event(
                            request_id=request.request_id,
                            approval_id=approval.approval_id,
                            command=command,
                            exit_code=execution_result.exit_code,
                            original_policy_decision=decision.decision,
                            execution_id=execution_id,
                        )
                    )
            else:
                approval_store.update_status(approval.approval_id, "failed")
                # Write ApprovalExecutionFailed event
                if audit_store.enabled:
                    audit_store.write(
                        create_approval_execution_failed_event(
                            request_id=request.request_id,
                            approval_id=approval.approval_id,
                            command=command,
                            reason=f"Command exited with code {execution_result.exit_code}",
                            original_policy_decision=decision.decision,
                            execution_id=execution_id,
                        )
                    )

            # Output results
            if json_output:
                print(json.dumps(execution_result.to_dict(), indent=2))
            else:
                print("Policy Scout Run (with approval)")
                print()
                print(f"Decision: {decision.decision}")
                print(f"Approval ID: {approval.approval_id}")
                print(f"Command: {command}")
                print()
                print("Running command...")
                print(f"Exit code: {execution_result.exit_code}")
                if execution_result.stdout:
                    print(f"Stdout: {execution_result.stdout}")
                if execution_result.stderr:
                    print(f"Stderr: {execution_result.stderr}")
                print()

            # Set exit code based on command exit code
            if execution_result.exit_code != 0:
                sys.exit(execution_result.exit_code or 1)
            else:
                sys.exit(0)

        # Normal REQUIRE_APPROVAL flow without --approval flag
        # Create approval request
        from ...core.config import get_approval_timeout_hours
        from ...core.ids import utcnow_plus_hours_iso
        approval = ApprovalRequest(
            request_id=request.request_id,
            decision_id=decision.decision_id,
            command=command,
            cwd=os.getcwd(),
            risk_score=decision.risk_score,
            reasons=decision.reasons,
            expires_at=utcnow_plus_hours_iso(get_approval_timeout_hours()),
        )
        approval_store.save(approval)

        # Write ApprovalRequested event
        if audit_store.enabled:
            audit_store.write(
                create_approval_requested_event(
                    request_id=request.request_id,
                    approval_id=approval.approval_id,
                    command=command,
                    actor={"type": request.actor.type, "name": request.actor.name},
                )
            )

        # Write CommandExecutionBlocked event
        if audit_store.enabled:
            audit_store.write(
                executor.create_execution_blocked_event(
                    request_id=request.request_id,
                    execution_id=generate_id("exec"),
                    command=command,
                    decision=decision.decision,
                    reason="Command requires approval",
                )
            )

        # Output results
        if json_output:
            # Derive risk band from risk score
            risk_band = derive_risk_band(decision.risk_score)
            print(
                json.dumps(
                    {
                        "decision": decision.decision,
                        "decision_id": decision.decision_id,
                        "approval_id": approval.approval_id,
                        "risk_score": decision.risk_score,
                        "risk_band": risk_band,
                        "category": decision.category,
                        "confidence": decision.confidence,
                        "policy_hits": decision.policy_hits,
                        "reasons": decision.reasons,
                        "recommended_next_action": decision.recommended_next_action,
                        "requires_audit": decision.requires_audit,
                        "override_allowed": decision.override_allowed,
                        "command": command,
                    },
                    indent=2,
                )
            )
        else:
            print("Policy Scout Run")
            print()
            print(f"Decision: {decision.decision}")
            print(f"Command: {command}")
            print()
            print("Why:")
            for reason in decision.reasons:
                print(f"  - {reason}")
            print()
            print(f"Approval ID: {approval.approval_id}")
            print("To approve: policy-scout approvals approve " + approval.approval_id)
            print()

        sys.exit(10)

    elif decision.decision == "SANDBOX_FIRST":
        # Write CommandExecutionBlocked event
        if audit_store.enabled:
            audit_store.write(
                executor.create_execution_blocked_event(
                    request_id=request.request_id,
                    execution_id=generate_id("exec"),
                    command=command,
                    decision=decision.decision,
                    reason="Command requires sandbox analysis",
                )
            )

        # Output results
        if json_output:
            # Derive risk band from risk score
            risk_band = derive_risk_band(decision.risk_score)
            print(
                json.dumps(
                    {
                        "decision": decision.decision,
                        "decision_id": decision.decision_id,
                        "risk_score": decision.risk_score,
                        "risk_band": risk_band,
                        "category": decision.category,
                        "confidence": decision.confidence,
                        "policy_hits": decision.policy_hits,
                        "reasons": decision.reasons,
                        "recommended_next_action": decision.recommended_next_action,
                        "requires_audit": decision.requires_audit,
                        "override_allowed": decision.override_allowed,
                        "command": command,
                        "recommended": f"policy-scout sandbox -- {command}",
                    },
                    indent=2,
                )
            )
        else:
            print("Policy Scout Run")
            print()
            print(f"Decision: {decision.decision}")
            print(f"Command: {command}")
            print()
            print("Why:")
            for reason in decision.reasons:
                print(f"  - {reason}")
            print()
            print("Recommended:")
            print(f"  policy-scout sandbox -- {command}")
            print()
            print("Command not executed on host.")
            print()

        sys.exit(10)

    elif decision.decision in ["DENY", "DENY_AND_ALERT"]:
        # Write CommandExecutionBlocked event
        if audit_store.enabled:
            audit_store.write(
                executor.create_execution_blocked_event(
                    request_id=request.request_id,
                    execution_id=generate_id("exec"),
                    command=command,
                    decision=decision.decision,
                    reason="Command denied by policy",
                )
            )

        # Output results
        if json_output:
            # Derive risk band from risk score
            risk_band = derive_risk_band(decision.risk_score)
            print(
                json.dumps(
                    {
                        "decision": decision.decision,
                        "decision_id": decision.decision_id,
                        "risk_score": decision.risk_score,
                        "risk_band": risk_band,
                        "category": decision.category,
                        "confidence": decision.confidence,
                        "policy_hits": decision.policy_hits,
                        "reasons": decision.reasons,
                        "recommended_next_action": decision.recommended_next_action,
                        "requires_audit": decision.requires_audit,
                        "override_allowed": decision.override_allowed,
                        "command": command,
                    },
                    indent=2,
                )
            )
        else:
            print("Policy Scout Run")
            print()
            print(f"Decision: {decision.decision}")
            print(f"Command: {command}")
            print()
            print("Why:")
            for reason in decision.reasons:
                print(f"  - {reason}")
            print()
            print("Command not executed.")
            print()

        sys.exit(20)

    else:
        # Unknown decision - fail safe
        if audit_store.enabled:
            audit_store.write(
                executor.create_execution_blocked_event(
                    request_id=request.request_id,
                    execution_id=generate_id("exec"),
                    command=command,
                    decision=decision.decision,
                    reason="Unknown decision - fail safe",
                )
            )

        print(f"Error: Unknown decision: {decision.decision}", file=sys.stderr)
        sys.exit(30)
