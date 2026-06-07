"""Main CLI entry point."""

import argparse
import sys
import json
import os
from typing import Optional
from ..core.request import CommandRequest, Actor
from ..classify.shell_parser import ShellParser
from ..classify.command_classifier import CommandClassifier
from ..policy.risk_scorer import RiskScorer
from ..policy.engine import PolicyEngine
from ..registry.loader import RegistryLoader
from ..audit.store import AuditStore
from ..audit.sqlite_store import SQLiteAuditStore
from ..audit.redaction import redact_dict
from ..audit.events import (
    create_command_requested_event,
    create_command_parsed_event,
    create_command_classified_event,
    create_policy_matched_event,
    create_decision_issued_event,
    create_approval_requested_event,
    create_approval_shown_event,
    create_approval_approved_once_event,
    create_approval_denied_once_event,
    create_sandbox_requested_event,
    create_sandbox_workspace_created_event,
    create_sandbox_install_started_event,
    create_sandbox_install_completed_event,
    create_lifecycle_scripts_inspected_event,
    create_sandbox_result_written_event,
    create_sandbox_error_event,
    create_scout_report_generated_event,
    create_sweep_started_event,
    create_sweep_completed_event,
    create_sweep_error_event,
    create_sandbox_migration_requested_event,
    create_sandbox_migration_planned_event,
    create_sandbox_migration_started_event,
    create_sandbox_migration_completed_event,
    create_sandbox_migration_blocked_event,
)
from ..approvals.store import ApprovalStore
from ..approvals.models import ApprovalRequest, ApprovalStatus, can_resolve_approval
from ..sandbox.models import SandboxResult
from ..sandbox.temp_workspace import create_sandbox_workspace
from ..sandbox.package_files import copy_package_files, create_minimal_package_json
from ..sandbox.lifecycle_inspector import inspect_lifecycle_scripts
from ..sandbox.diff import take_file_snapshot, capture_manifest_diffs
from ..sandbox.result_writer import write_sandbox_result
from ..sandbox.migration import (
    execute_migration,
    save_migration_result,
)
from ..sandbox.package_manager import (
    detect_package_manager,
    is_package_manager_available,
)
from ..sandbox.runner import run_package_manager_install
from ..core.ids import generate_id
from ..core.decision import derive_risk_band
from ..reports.command_decision_report import generate_command_decision_report
from ..reports.sandbox_report import generate_sandbox_report
from ..reports.sweep_report import generate_sweep_report
from ..sweep.engine import run_project_sweep
from ..sweep.quick_engine import run_quick_system_sweep
from ..executor.direct_executor import DirectExecutor
from ..evals.loader import load_eval_cases, validate_eval_cases
from ..evals.runner import run_eval_suite
from ..evals.report import generate_eval_report, generate_eval_json
from ..doctor import run_doctor_checks, format_doctor_output
from ..demo import run_demo
from ..data_status import (
    get_data_status,
    format_data_status_human,
    format_data_status_json,
)


def cli():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Policy Scout - Local-first safety harness for agent commands"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    # check command
    check_parser = subparsers.add_parser(
        "check", help="Analyze a command without executing it"
    )
    check_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )
    check_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )
    check_parser.add_argument(
        "--no-approval", action="store_true", help="Disable approval creation"
    )
    check_parser.add_argument(
        "--report", action="store_true", help="Generate a Scout Report for the decision"
    )
    check_parser.add_argument("command", nargs="...", help="Command to check")

    # approvals command
    approvals_parser = subparsers.add_parser(
        "approvals", help="Manage approval requests"
    )
    approvals_subparsers = approvals_parser.add_subparsers(
        dest="approvals_subcommand", help="Approval commands"
    )

    # approvals list
    approvals_subparsers.add_parser("list", help="List pending approval requests")

    # approvals show
    show_parser = approvals_subparsers.add_parser(
        "show", help="Show approval request details"
    )
    show_parser.add_argument("approval_id", help="Approval ID to show")

    # approvals approve
    approve_parser = approvals_subparsers.add_parser(
        "approve", help="Approve a request"
    )
    approve_parser.add_argument("approval_id", help="Approval ID to approve")

    # approvals deny
    deny_parser = approvals_subparsers.add_parser("deny", help="Deny a request")
    deny_parser.add_argument("approval_id", help="Approval ID to deny")

    # sandbox command
    sandbox_parser = subparsers.add_parser(
        "sandbox",
        help="Run package install in sandbox review workspace or migrate sandbox result to host",
        epilog="Install/review mode: policy-scout sandbox -- npm install lodash\nMigration mode: policy-scout sandbox <sbx_id>\nDry-run migration: policy-scout sandbox --dry-run <sbx_id>\nNon-interactive migration: policy-scout sandbox --yes <sbx_id>\n\nNote: --dry-run and --yes apply to migration mode only, not install/review mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sandbox_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )
    sandbox_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )
    sandbox_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run migration (no changes, migration mode only)",
    )
    sandbox_parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-confirm migration (migration mode only)",
    )
    sandbox_parser.add_argument(
        "command",
        nargs="...",
        help="Command to sandbox (install/review mode) or sandbox_id for migrate",
    )

    # sweep command
    sweep_parser = subparsers.add_parser(
        "sweep", help="Scan project for suspicious traces"
    )
    sweep_subparsers = sweep_parser.add_subparsers(
        dest="sweep_subcommand", help="Sweep commands"
    )

    # sweep project
    sweep_project_parser = sweep_subparsers.add_parser(
        "project", help="Scan current project for suspicious traces"
    )
    sweep_project_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )
    sweep_project_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )
    sweep_project_parser.add_argument(
        "--project", help="Path to project root (default: current directory)"
    )

    # sweep quick
    sweep_quick_parser = sweep_subparsers.add_parser(
        "quick", help="Quick system signal scan (Linux-first)"
    )
    sweep_quick_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )
    sweep_quick_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )

    # eval command
    eval_parser = subparsers.add_parser("eval", help="Run evaluation suite")
    eval_subparsers = eval_parser.add_subparsers(
        dest="eval_subcommand", help="Eval commands"
    )

    # eval run
    eval_run_parser = eval_subparsers.add_parser("run", help="Run evaluation suite")
    eval_run_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )
    eval_run_parser.add_argument("--filter", help="Filter cases by tag")
    eval_run_parser.add_argument("--file", help="Path to eval cases YAML file")

    # doctor command
    doctor_parser = subparsers.add_parser("doctor", help="Run health diagnostics")
    doctor_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # demo command
    subparsers.add_parser("demo", help="Run safe local demonstration")

    # data command
    data_parser = subparsers.add_parser("data", help="Show local data status")
    data_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # run command
    run_parser = subparsers.add_parser(
        "run", help="Run a command through the policy gate"
    )
    run_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )
    run_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )
    run_parser.add_argument(
        "--approval", help="Approval ID to use for one-time execution"
    )
    run_parser.add_argument("command", nargs="...", help="Command to run")

    # audit command
    audit_parser = subparsers.add_parser("audit", help="Query audit history")
    audit_subparsers = audit_parser.add_subparsers(
        dest="audit_subcommand", help="Audit commands"
    )

    # audit list
    audit_list_parser = audit_subparsers.add_parser(
        "list", help="List recent audit events"
    )
    audit_list_parser.add_argument(
        "--limit", type=int, default=20, help="Number of events to show (default: 20)"
    )
    audit_list_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # audit show
    audit_show_parser = audit_subparsers.add_parser(
        "show", help="Show a specific audit event"
    )
    audit_show_parser.add_argument("event_id", help="Event ID to show")
    audit_show_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # audit request
    audit_request_parser = audit_subparsers.add_parser(
        "request", help="Show all events for a request"
    )
    audit_request_parser.add_argument("request_id", help="Request ID to query")
    audit_request_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # audit type
    audit_type_parser = audit_subparsers.add_parser(
        "type", help="Show events of a specific type"
    )
    audit_type_parser.add_argument("event_type", help="Event type to query")
    audit_type_parser.add_argument(
        "--limit", type=int, default=50, help="Number of events to show (default: 50)"
    )
    audit_type_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # audit stats
    audit_stats_parser = audit_subparsers.add_parser(
        "stats", help="Show audit statistics"
    )
    audit_stats_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # report command
    report_parser = subparsers.add_parser("report", help="Query Scout Reports")
    report_subparsers = report_parser.add_subparsers(
        dest="report_subcommand", help="Report commands"
    )

    # report list
    report_list_parser = report_subparsers.add_parser(
        "list", help="List recent Scout Reports"
    )
    report_list_parser.add_argument(
        "--limit", type=int, default=20, help="Number of reports to show (default: 20)"
    )
    report_list_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # report show
    report_show_parser = report_subparsers.add_parser(
        "show", help="Show a Scout Report"
    )
    report_show_parser.add_argument("report_id", help="Report ID to show")
    report_show_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # report export
    report_export_parser = report_subparsers.add_parser(
        "export", help="Export a Scout Report"
    )
    report_export_parser.add_argument("report_id", help="Report ID to export")
    report_export_parser.add_argument(
        "--format", choices=["markdown", "json"], required=True, help="Export format"
    )

    args = parser.parse_args()

    if args.subcommand == "check":
        if not args.command:
            print("Error: No command provided to check", file=sys.stderr)
            sys.exit(1)

        command_str = " ".join(args.command)
        # Remove leading -- if present (argparse separator)
        if command_str.startswith("-- "):
            command_str = command_str[3:]
        elif command_str == "--":
            print("Error: No command provided after --", file=sys.stderr)
            sys.exit(1)

        result = check_command(
            command_str,
            json_output=args.json,
            audit_enabled=not args.no_audit,
            approval_enabled=not args.no_approval,
            report_enabled=args.report,
        )

        # Set exit code based on decision
        if result["decision"] in ["DENY", "DENY_AND_ALERT"]:
            sys.exit(20)
        elif result["decision"] in ["REQUIRE_APPROVAL", "SANDBOX_FIRST"]:
            sys.exit(10)
        else:
            sys.exit(0)
    elif args.subcommand == "approvals":
        handle_approvals_command(args)
    elif args.subcommand == "sandbox":
        # Check if migrate subcommand
        if args.command and len(args.command) == 1 and args.command[0] == "migrate":
            print(
                "Error: Use 'policy-scout sandbox migrate <sandbox_id>'",
                file=sys.stderr,
            )
            sys.exit(1)

        # If no command but migrate is implied by flags, treat as migrate
        if not args.command and (args.dry_run or args.yes):
            print("Error: sandbox_id required for migrate", file=sys.stderr)
            sys.exit(1)

        # If command is a single argument that looks like a sandbox_id, treat as migrate
        if (
            args.command
            and len(args.command) == 1
            and args.command[0].startswith("sbx_")
        ):
            handle_sandbox_migrate_command(
                args.command[0],
                dry_run=args.dry_run,
                yes=args.yes,
                json_output=args.json,
                audit_enabled=not args.no_audit,
            )
        elif args.command:
            command_str = " ".join(args.command)
            # Remove leading -- if present (argparse separator)
            if command_str.startswith("-- "):
                command_str = command_str[3:]
            elif command_str == "--":
                print("Error: No command provided after --", file=sys.stderr)
                sys.exit(1)

            handle_sandbox_command(
                command_str,
                json_output=args.json,
                audit_enabled=not args.no_audit,
            )
        else:
            print("Error: No command provided to sandbox", file=sys.stderr)
            sys.exit(1)
    elif args.subcommand == "sweep":
        if args.sweep_subcommand == "project":
            handle_sweep_project_command(
                json_output=args.json,
                audit_enabled=not args.no_audit,
                project_root=args.project,
            )
        elif args.sweep_subcommand == "quick":
            handle_sweep_quick_command(
                json_output=args.json,
                audit_enabled=not args.no_audit,
            )
        else:
            print("Error: No sweep subcommand provided", file=sys.stderr)
            sys.exit(1)
    elif args.subcommand == "eval":
        if args.eval_subcommand == "run":
            handle_eval_run_command(
                json_output=args.json,
                filter_tag=args.filter,
                file_path=args.file,
            )
        else:
            print("Error: No eval subcommand provided", file=sys.stderr)
            sys.exit(1)
    elif args.subcommand == "doctor":
        results = run_doctor_checks()
        output = format_doctor_output(results, json_mode=args.json)
        print(output)

        # Exit with error if any checks failed
        has_errors = any(c.get("status") == "error" for c in results["checks"].values())
        if has_errors:
            sys.exit(1)
    elif args.subcommand == "demo":
        output = run_demo()
        print(output)
    elif args.subcommand == "data":
        status = get_data_status()
        if args.json:
            output = format_data_status_json(status)
        else:
            output = format_data_status_human(status)
        print(output)
    elif args.subcommand == "run":
        if not args.command:
            print("Error: No command provided to run", file=sys.stderr)
            sys.exit(1)

        command_str = " ".join(args.command)
        # Remove leading -- if present (argparse separator)
        if command_str.startswith("-- "):
            command_str = command_str[3:]
        elif command_str == "--":
            print("Error: No command provided after --", file=sys.stderr)
            sys.exit(1)

        handle_run_command(
            command_str,
            json_output=args.json,
            audit_enabled=not args.no_audit,
            approval_id=args.approval,
        )
    elif args.subcommand == "audit":
        handle_audit_command(args)
    elif args.subcommand == "report":
        handle_report_command(args)
    else:
        parser.print_help()
        sys.exit(1)


def check_command(
    command: str,
    json_output: bool = False,
    audit_enabled: bool = True,
    approval_enabled: bool = True,
    report_enabled: bool = False,
) -> dict:
    """Check a command and return the decision."""
    # Initialize audit store
    audit_store = AuditStore(enabled=audit_enabled)

    # Initialize approval store
    approval_store = ApprovalStore() if approval_enabled else None

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
    decision = policy_engine.evaluate(classification, risk_score, request.request_id)

    # Write PolicyMatched event
    if audit_store.enabled and decision.policy_hits:
        audit_store.write(
            create_policy_matched_event(request.request_id, decision.policy_hits)
        )

    # Build result
    result = {
        "request_id": request.request_id,
        "command": command,
        "decision": decision.decision,
        "risk_score": decision.risk_score,
        "risk_band": risk_score.risk_band,
        "category": decision.category,
        "capabilities": classification.capabilities,
        "reasons": decision.reasons,
        "recommended_next_action": decision.recommended_next_action,
        "confidence": decision.confidence,
        "registry_hits": classification.registry_hits,
        "policy_hits": decision.policy_hits,
    }

    # Redact sensitive values from result for JSON output
    result = redact_dict(result)

    # Write DecisionIssued event
    if audit_store.enabled:
        audit_store.write(
            create_decision_issued_event(
                request.request_id,
                decision.decision,
                decision.risk_score,
                risk_score.risk_band,
                decision.reasons,
            )
        )

    # Create approval request for REQUIRE_APPROVAL decisions
    # Only for non-hard-denied commands
    if (
        approval_enabled
        and approval_store
        and decision.decision == "REQUIRE_APPROVAL"
        and decision.decision not in ["DENY", "DENY_AND_ALERT"]
    ):

        approval = ApprovalRequest(
            request_id=request.request_id,
            decision_id=decision.decision,
            actor={"type": request.actor.type, "name": request.actor.name},
            command=command,
            cwd=os.getcwd(),
            risk_score=decision.risk_score,
            decision=decision.decision,
            reasons=decision.reasons,
            recommended_action=decision.recommended_next_action,
            status=ApprovalStatus.PENDING,
        )

        approval_store.save(approval)

        # Write ApprovalRequested event
        if audit_store.enabled:
            audit_store.write(
                create_approval_requested_event(
                    request.request_id,
                    approval.approval_id,
                    command,
                    actor={"type": request.actor.type, "name": request.actor.name},
                )
            )

    # Generate report if requested and decision is high-friction
    if report_enabled and decision.decision in [
        "DENY",
        "DENY_AND_ALERT",
        "REQUIRE_APPROVAL",
    ]:
        try:
            report = generate_command_decision_report(
                request_id=request.request_id,
                command=command,
                decision=decision.decision,
                risk_score=decision.risk_score,
                risk_band=risk_score.risk_band,
                category=decision.category,
                reasons=decision.reasons,
            )

            # Write ScoutReportGenerated event
            if audit_store.enabled:
                audit_store.write(
                    create_scout_report_generated_event(
                        request_id=request.request_id,
                        report_id=report.report_id,
                        report_type=report.report_type,
                        report_path=report.markdown_path,
                    )
                )

            # Print report paths
            print()
            print("Scout Report generated:")
            print(f"  Markdown: {report.markdown_path}")
            print(f"  JSON: {report.json_path}")
        except Exception as e:
            print(f"Warning: Failed to generate report: {e}", file=sys.stderr)

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print_human_output(result)

    return result


def print_human_output(result: dict):
    """Print human-readable output."""
    print("Policy Scout Check")
    print()
    print("Command:")
    print(f"  {result['command']}")
    print()
    print("Decision:")
    print(f"  {result['decision']}")
    print()
    print("Risk:")
    print(f"  {result['risk_score']}/10 ({result['risk_band']})")
    print()
    print("Category:")
    print(f"  {result['category']}")
    print()
    if result["capabilities"]:
        print("Capabilities:")
        for cap in result["capabilities"]:
            print(f"  - {cap}")
        print()
    print("Why:")
    for reason in result["reasons"]:
        print(f"  - {reason}")
    print()
    if result["recommended_next_action"]:
        print("Recommended:")
        print(f"  {result['recommended_next_action']}")
        print()


def handle_approvals_command(args):
    """Handle approvals subcommands."""
    approval_store = ApprovalStore()
    audit_store = AuditStore(enabled=True)

    if args.approvals_subcommand == "list":
        approvals = approval_store.list_pending()
        if not approvals:
            print("No pending approval requests.")
            return

        print("Pending Approval Requests:")
        print()
        for approval in approvals:
            print(f"  ID: {approval.approval_id}")
            print(f"  Command: {approval.command}")
            print(f"  Risk: {approval.risk_score}/10")
            print(f"  Created: {approval.created_at}")
            print(f"  Expires: {approval.expires_at}")
            print()

    elif args.approvals_subcommand == "show":
        approval = approval_store.get_by_id(args.approval_id)
        if not approval:
            print(f"Error: Approval {args.approval_id} not found", file=sys.stderr)
            sys.exit(1)

        print("Approval Request:")
        print()
        print(f"  ID: {approval.approval_id}")
        print(f"  Request ID: {approval.request_id}")
        print(f"  Status: {approval.status}")
        print(f"  Command: {approval.command}")
        print(f"  CWD: {approval.cwd}")
        print(f"  Risk Score: {approval.risk_score}/10")
        print(f"  Decision: {approval.decision}")
        print(f"  Scope: {approval.scope}")
        print(f"  Created: {approval.created_at}")
        print(f"  Expires: {approval.expires_at}")
        print()
        print("Reasons:")
        for reason in approval.reasons:
            print(f"  - {reason}")
        print()
        if approval.recommended_action:
            print(f"Recommended: {approval.recommended_action}")
            print()

        # Write ApprovalShown event
        audit_store.write(
            create_approval_shown_event(
                approval.request_id,
                approval.approval_id,
                actor={"type": "human", "name": "cli_user"},
            )
        )

    elif args.approvals_subcommand == "approve":
        approval = approval_store.get_by_id(args.approval_id)
        if not approval:
            print(f"Error: Approval {args.approval_id} not found", file=sys.stderr)
            sys.exit(1)

        if approval.status != ApprovalStatus.PENDING:
            print(
                f"Error: Approval is not pending (current status: {approval.status})",
                file=sys.stderr,
            )
            sys.exit(1)

        # Self-approval protection: use helper to check if resolver can approve
        # Current approver is always human/cli_user in CLI
        current_approver = {"type": "human", "name": "cli_user"}
        if not can_resolve_approval(approval.actor, current_approver):
            print(
                "Error: Approval not allowed. The requesting actor cannot approve this request.",
                file=sys.stderr,
            )
            sys.exit(1)

        success = approval_store.update_status(
            args.approval_id, ApprovalStatus.APPROVED_ONCE
        )
        if success:
            print(f"Approved: {args.approval_id}")

            # Write ApprovalApprovedOnce event
            audit_store.write(
                create_approval_approved_once_event(
                    approval.request_id,
                    approval.approval_id,
                    actor=current_approver,
                )
            )
        else:
            print("Error: Failed to update approval status", file=sys.stderr)
            sys.exit(1)

    elif args.approvals_subcommand == "deny":
        approval = approval_store.get_by_id(args.approval_id)
        if not approval:
            print(f"Error: Approval {args.approval_id} not found", file=sys.stderr)
            sys.exit(1)

        if approval.status != ApprovalStatus.PENDING:
            print(
                f"Error: Approval is not pending (current status: {approval.status})",
                file=sys.stderr,
            )
            sys.exit(1)

        success = approval_store.update_status(
            args.approval_id, ApprovalStatus.DENIED_ONCE
        )
        if success:
            print(f"Denied: {args.approval_id}")

            # Write ApprovalDeniedOnce event
            audit_store.write(
                create_approval_denied_once_event(
                    approval.request_id,
                    approval.approval_id,
                    actor={"type": "human", "name": "cli_user"},
                )
            )
        else:
            print("Error: Failed to update approval status", file=sys.stderr)
            sys.exit(1)

    else:
        print("Error: Unknown approvals subcommand", file=sys.stderr)
        sys.exit(1)


def handle_sandbox_command(
    command: str,
    json_output: bool = False,
    audit_enabled: bool = True,
):
    """Handle sandbox command."""
    from pathlib import Path
    from ..core.ids import utcnow_iso

    # Initialize audit store if enabled
    audit_store = None
    request_id = ""
    if audit_enabled:
        audit_store = AuditStore()
        request_id = generate_id("req")

        # Write SandboxRequested event
        audit_store.write(
            create_sandbox_requested_event(
                request_id,
                command,
                actor={"type": "human", "name": "cli_user"},
            )
        )

    # Parse command to detect package manager
    package_manager = detect_package_manager(command)
    if not package_manager:
        print(
            "Error: Only npm/pnpm/yarn/bun install/add commands are supported in sandbox v1",
            file=sys.stderr,
        )
        if audit_enabled:
            audit_store.write(
                create_sandbox_error_event(
                    request_id,
                    "",
                    "Only npm/pnpm/yarn/bun install/add commands are supported",
                )
            )
        sys.exit(1)

    # Check if package manager is available
    if not is_package_manager_available(package_manager):
        print(
            f"Error: Package manager executable not found: {package_manager}",
            file=sys.stderr,
        )
        if audit_enabled:
            audit_store.write(
                create_sandbox_error_event(
                    request_id,
                    "",
                    f"Package manager executable not found: {package_manager}",
                )
            )
        sys.exit(1)

    # Parse command to extract package manager args
    parts = command.split()

    # Extract package name for minimal package.json creation
    package_name = ""
    if len(parts) >= 2:
        if parts[1] in ["install", "i", "add"]:
            package_name = parts[2] if len(parts) > 2 else ""

    # Create sandbox workspace
    sandbox_id = generate_id("sbx")
    workspace = create_sandbox_workspace(sandbox_id)

    if audit_enabled:
        audit_store.write(
            create_sandbox_workspace_created_event(
                request_id, sandbox_id, str(workspace)
            )
        )

    # Copy package files from host
    host_cwd = Path.cwd()
    copied_files, skipped_files = copy_package_files(
        host_cwd, workspace, package_manager
    )

    # If no package.json in host, create minimal one in sandbox
    if not (workspace / "package.json").exists():
        create_minimal_package_json(workspace, package_name)

    # Take before snapshot
    before_snapshot = take_file_snapshot(workspace)

    # Run package manager install
    if audit_enabled:
        audit_store.write(
            create_sandbox_install_started_event(request_id, sandbox_id, command)
        )

    # Extract package manager args (remove package manager name)
    pm_args = parts[1:]
    exit_code, stdout, stderr, duration_ms = run_package_manager_install(
        package_manager, workspace, pm_args
    )

    if audit_enabled:
        audit_store.write(
            create_sandbox_install_completed_event(
                request_id, sandbox_id, exit_code, duration_ms
            )
        )

    # Take after snapshot
    after_snapshot = take_file_snapshot(workspace)

    # Capture diffs
    manifest_changed, lockfile_changed, diffs = capture_manifest_diffs(
        workspace, before_snapshot, after_snapshot
    )

    # Inspect lifecycle scripts
    lifecycle_scripts = inspect_lifecycle_scripts(workspace)

    if audit_enabled:
        audit_store.write(
            create_lifecycle_scripts_inspected_event(
                request_id, sandbox_id, len(lifecycle_scripts)
            )
        )

    # Build findings
    findings = []
    if skipped_files:
        findings.append(
            {
                "type": "warning",
                "message": f"Skipped files with token-like content: {', '.join(skipped_files)}",
            }
        )

    # Create sandbox result
    result = SandboxResult(
        sandbox_id=sandbox_id,
        request_id=request_id,
        command=command,
        package_manager=package_manager,
        temp_workspace=str(workspace),
        host_project_root=os.getcwd(),
        exit_code=exit_code,
        duration_ms=duration_ms,
        stdout=stdout,
        stderr=stderr,
        manifest_changed=manifest_changed,
        lockfile_changed=lockfile_changed,
        lifecycle_scripts_found=lifecycle_scripts,
        findings=findings,
        migration_available=exit_code == 0,
        migration_requires_approval=True,
        completed_at=utcnow_iso(),
    )

    # Write result
    result_path = write_sandbox_result(result)

    if audit_enabled:
        audit_store.write(
            create_sandbox_result_written_event(
                request_id, sandbox_id, str(result_path)
            )
        )

    # Generate Scout Report for sandbox result
    try:
        report = generate_sandbox_report(
            sandbox_result=result,
            audit_event_ids=[],
        )

        # Write ScoutReportGenerated event
        if audit_enabled:
            audit_store.write(
                create_scout_report_generated_event(
                    request_id=request_id,
                    report_id=report.report_id,
                    report_type=report.report_type,
                    report_path=report.markdown_path,
                )
            )
    except Exception as e:
        # Report generation failure should not fail the sandbox
        print(f"Warning: Failed to generate Scout Report: {e}", file=sys.stderr)

    # Output results
    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print("Policy Scout Sandbox Review")
        print()
        print(f"Sandbox ID: {result.sandbox_id}")
        print(f"Command: {result.command}")
        print(f"Exit Code: {result.exit_code}")
        print(f"Duration: {result.duration_ms}ms")
        print(f"Lifecycle Scripts Found: {len(result.lifecycle_scripts_found)}")
        print(f"Manifest Changed: {result.manifest_changed}")
        print(f"Lockfile Changed: {result.lockfile_changed}")
        print(f"Result Path: {result_path}")
        print()
        print("Host Project Status: NOT MUTATED")
        print("Next Action: Review result before migration")
        print()
        if result.findings:
            print("Findings:")
            for finding in result.findings:
                msg = finding.get("message", str(finding))
                print(f"  - {msg}")
        print()
        # Print report info if report was generated
        if "report" in locals() and report is not None:
            print(f"Report ID: {report.report_id}")
            print("Scout Report generated:")
            print(f"  Markdown: {report.markdown_path}")
            print(f"  JSON: {report.json_path}")

    # Set exit code based on install success
    if exit_code != 0:
        sys.exit(20)
    else:
        sys.exit(0)


def handle_sandbox_migrate_command(
    sandbox_id: str,
    dry_run: bool = False,
    yes: bool = False,
    json_output: bool = False,
    audit_enabled: bool = True,
):
    """Handle sandbox migrate command."""
    from ..sandbox.result_writer import get_sandbox_root
    from ..core.ids import generate_id

    request_id = generate_id("req")

    # Initialize audit store
    audit_store = AuditStore()

    # Load sandbox result
    sandbox_root = get_sandbox_root()
    sandbox_result_path = sandbox_root / f"{sandbox_id}.json"

    if not sandbox_result_path.exists():
        print(f"Error: Sandbox result not found: {sandbox_id}", file=sys.stderr)
        sys.exit(1)

    with open(sandbox_result_path, "r") as f:
        import json

        sandbox_data = json.load(f)

    sandbox_result = SandboxResult.from_dict(sandbox_data)

    # Write SandboxMigrationRequested event
    if audit_enabled:
        audit_store.write(
            create_sandbox_migration_requested_event(
                request_id=request_id,
                migration_id="",  # Will be set after migration result is created
                sandbox_id=sandbox_id,
                host_project_root=sandbox_result.host_project_root,
            )
        )

    # Plan migration
    from ..sandbox.migration import plan_migration

    migration_result = plan_migration(sandbox_result, dry_run=dry_run)

    # Write SandboxMigrationPlanned event
    if audit_enabled:
        audit_store.write(
            create_sandbox_migration_planned_event(
                request_id=request_id,
                migration_id=migration_result.migration_id,
                sandbox_id=sandbox_id,
                host_project_root=sandbox_result.host_project_root,
                files_planned=migration_result.files_planned,
            )
        )

    # Check if blocked
    if migration_result.blocked:
        if audit_enabled:
            audit_store.write(
                create_sandbox_migration_blocked_event(
                    request_id=request_id,
                    migration_id=migration_result.migration_id,
                    sandbox_id=sandbox_id,
                    host_project_root=sandbox_result.host_project_root,
                    block_reasons=migration_result.block_reasons,
                )
            )

        if json_output:
            print(json.dumps(migration_result.to_dict(), indent=2))
        else:
            print("Migration Blocked")
            print()
            print(f"Sandbox ID: {sandbox_id}")
            print(f"Host Project Root: {sandbox_result.host_project_root}")
            print()
            print("Block Reasons:")
            for reason in migration_result.block_reasons:
                print(f"  - {reason}")
        sys.exit(1)

    # Show migration plan
    if json_output:
        print(json.dumps(migration_result.to_dict(), indent=2))
    else:
        print("Migration Plan")
        print()
        print(f"Migration ID: {migration_result.migration_id}")
        print(f"Sandbox ID: {sandbox_id}")
        print(f"Host Project Root: {sandbox_result.host_project_root}")
        print()
        print("Files Planned:")
        for filename in migration_result.files_planned:
            print(f"  - {filename}")
        if migration_result.files_skipped:
            print()
            print("Files Skipped:")
            for filename in migration_result.files_skipped:
                print(f"  - {filename}")
        print()
        print("Note: node_modules and arbitrary files are never migrated.")
        print()

    # Require confirmation unless --yes or --dry-run
    if not dry_run and not yes:
        response = input("Proceed with migration? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            sys.exit(0)

    # Execute migration
    if not dry_run:
        migration_result = execute_migration(sandbox_result, dry_run=False)

        # Write SandboxMigrationStarted event
        if audit_enabled:
            audit_store.write(
                create_sandbox_migration_started_event(
                    request_id=request_id,
                    migration_id=migration_result.migration_id,
                    sandbox_id=sandbox_id,
                    host_project_root=sandbox_result.host_project_root,
                    files_planned=migration_result.files_planned,
                )
            )

        if migration_result.blocked:
            if audit_enabled:
                audit_store.write(
                    create_sandbox_migration_blocked_event(
                        request_id=request_id,
                        migration_id=migration_result.migration_id,
                        sandbox_id=sandbox_id,
                        host_project_root=sandbox_result.host_project_root,
                        block_reasons=migration_result.block_reasons,
                    )
                )

            if json_output:
                print(json.dumps(migration_result.to_dict(), indent=2))
            else:
                print("Migration Failed")
                print()
                print("Block Reasons:")
                for reason in migration_result.block_reasons:
                    print(f"  - {reason}")
            sys.exit(1)

        # Save migration result
        save_migration_result(migration_result)

        # Write SandboxMigrationCompleted event
        if audit_enabled:
            audit_store.write(
                create_sandbox_migration_completed_event(
                    request_id=request_id,
                    migration_id=migration_result.migration_id,
                    sandbox_id=sandbox_id,
                    host_project_root=sandbox_result.host_project_root,
                    files_migrated=migration_result.files_migrated,
                    files_skipped=migration_result.files_skipped,
                    backups_created=migration_result.backups_created,
                )
            )

    # Output results
    if json_output:
        print(json.dumps(migration_result.to_dict(), indent=2))
    else:
        if dry_run:
            print("Dry Run - No files were migrated.")
        else:
            print("Migration Completed")
            print()
            print(f"Migration ID: {migration_result.migration_id}")
            print(f"Sandbox ID: {sandbox_id}")
            print(f"Host Project Root: {sandbox_result.host_project_root}")
            print()
            print("Files Migrated:")
            for filename in migration_result.files_migrated:
                print(f"  - {filename}")
            if migration_result.files_skipped:
                print()
                print("Files Skipped:")
                for filename in migration_result.files_skipped:
                    print(f"  - {filename}")
            if migration_result.backups_created:
                print()
                print("Backups Created:")
                for backup_path in migration_result.backups_created:
                    print(f"  - {backup_path}")
            print()
            print("Note: node_modules and arbitrary files were not migrated.")


def handle_sweep_project_command(
    json_output: bool = False,
    audit_enabled: bool = True,
    project_root: str = None,
):
    """Handle sweep project command."""
    import time
    from ..core.ids import generate_id

    request_id = generate_id("req")

    # Determine project root
    if project_root is None:
        project_root = os.getcwd()

    # Initialize audit store
    audit_store = AuditStore()

    # Write SweepStarted event
    if audit_enabled:
        sweep_id = generate_id("sweep")
        audit_store.write(
            create_sweep_started_event(
                request_id=request_id,
                sweep_id=sweep_id,
                sweep_type="project",
                project_root=project_root,
            )
        )
    else:
        sweep_id = generate_id("sweep")

    # Run sweep
    start_time = time.time()
    try:
        sweep_result = run_project_sweep(project_root=project_root)
        sweep_result.sweep_id = sweep_id

        # Calculate duration
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        # Write SweepCompleted event
        if audit_enabled:
            audit_store.write(
                create_sweep_completed_event(
                    request_id=request_id,
                    sweep_id=sweep_id,
                    findings_count=sweep_result.findings_count,
                    duration_ms=duration_ms,
                )
            )

        # Generate Scout Report for sweep
        try:
            report = generate_sweep_report(
                sweep_result=sweep_result,
                audit_event_ids=[],
            )

            # Write ScoutReportGenerated event
            if audit_enabled:
                audit_store.write(
                    create_scout_report_generated_event(
                        request_id=request_id,
                        report_id=report.report_id,
                        report_type=report.report_type,
                        report_path=report.markdown_path,
                    )
                )
        except Exception as e:
            # Report generation failure should not fail the sweep
            print(f"Warning: Failed to generate Scout Report: {e}", file=sys.stderr)
            report = None

        # Output results
        if json_output:
            print(json.dumps(redact_dict(sweep_result.to_dict()), indent=2))
        else:
            print("Policy Scout Project Sweep")
            print()
            print(f"Sweep ID: {sweep_result.sweep_id}")
            print(f"Project Root: {sweep_result.project_root}")
            print(f"Duration: {duration_ms}ms")
            print()
            print("Findings:")
            print(f"  Critical: {sweep_result.findings_count.get('critical', 0)}")
            print(f"  High: {sweep_result.findings_count.get('high', 0)}")
            print(f"  Medium: {sweep_result.findings_count.get('medium', 0)}")
            print(f"  Low: {sweep_result.findings_count.get('low', 0)}")
            print(f"  Info: {sweep_result.findings_count.get('info', 0)}")
            print()
            if sweep_result.findings:
                for finding in sweep_result.findings:
                    print(f"  - [{finding.severity.upper()}] {finding.title}")
                    print(f"    Location: {finding.location}")
                    print(f"    Category: {finding.category}")
                    print()
            if sweep_result.could_not_verify:
                print("Could Not Verify:")
                for item in sweep_result.could_not_verify:
                    print(f"  - {item}")
                print()
    except Exception as e:
        # Write SweepError event
        if audit_enabled:
            audit_store.write(
                create_sweep_error_event(
                    request_id=request_id,
                    sweep_id=sweep_id,
                    error_message=str(e),
                )
            )
        print(f"Error: Sweep failed: {e}", file=sys.stderr)


def handle_sweep_quick_command(
    json_output: bool = False,
    audit_enabled: bool = True,
):
    """Handle sweep quick command."""
    import time
    from ..core.ids import generate_id

    request_id = generate_id("req")

    # Initialize audit store
    audit_store = AuditStore()

    # Write SweepStarted event
    if audit_enabled:
        sweep_id = generate_id("sweep")
        audit_store.write(
            create_sweep_started_event(
                request_id=request_id,
                sweep_id=sweep_id,
                sweep_type="quick_system",
                project_root="",
            )
        )
    else:
        sweep_id = generate_id("sweep")

    # Run sweep
    start_time = time.time()
    try:
        sweep_result = run_quick_system_sweep()
        sweep_result.sweep_id = sweep_id

        # Calculate duration
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        # Write SweepCompleted event
        if audit_enabled:
            audit_store.write(
                create_sweep_completed_event(
                    request_id=request_id,
                    sweep_id=sweep_id,
                    findings_count=sweep_result.findings_count,
                    duration_ms=duration_ms,
                )
            )

        # Generate Scout Report for sweep
        try:
            report = generate_sweep_report(
                sweep_result=sweep_result,
                audit_event_ids=[],
            )

            # Write ScoutReportGenerated event
            if audit_enabled:
                audit_store.write(
                    create_scout_report_generated_event(
                        request_id=request_id,
                        report_id=report.report_id,
                        report_type=report.report_type,
                        report_path=report.markdown_path,
                    )
                )
        except Exception as e:
            # Report generation failure should not fail the sweep
            print(f"Warning: Failed to generate Scout Report: {e}", file=sys.stderr)
            report = None

        # Output results
        if json_output:
            print(json.dumps(redact_dict(sweep_result.to_dict()), indent=2))
        else:
            print("Policy Scout Quick System Sweep")
            print()
            print(f"Sweep ID: {sweep_result.sweep_id}")
            print(f"Platform: {sweep_result.platform}")
            print(f"Duration: {duration_ms}ms")
            print()
            print("Findings:")
            print(f"  Critical: {sweep_result.findings_count.get('critical', 0)}")
            print(f"  High: {sweep_result.findings_count.get('high', 0)}")
            print(f"  Medium: {sweep_result.findings_count.get('medium', 0)}")
            print(f"  Low: {sweep_result.findings_count.get('low', 0)}")
            print(f"  Info: {sweep_result.findings_count.get('info', 0)}")
            print()
            if sweep_result.findings:
                for finding in sweep_result.findings:
                    print(f"  - [{finding.severity.upper()}] {finding.title}")
                    print(f"    Location: {finding.location}")
                    print(f"    Category: {finding.category}")
                    print()
            if sweep_result.could_not_verify:
                print("Could Not Verify:")
                for item in sweep_result.could_not_verify:
                    print(f"  - {item}")
                print()
    except Exception as e:
        # Write SweepError event
        if audit_enabled:
            audit_store.write(
                create_sweep_error_event(
                    request_id=request_id,
                    sweep_id=sweep_id,
                    error_message=str(e),
                )
            )
        print(f"Error: Sweep failed: {e}", file=sys.stderr)


def handle_eval_run_command(
    json_output: bool = False,
    filter_tag: str = None,
    file_path: str = None,
):
    """Handle eval run command."""
    try:
        # Load eval cases
        cases = load_eval_cases(path=file_path)

        # Validate eval cases
        validation_errors = validate_eval_cases(cases)
        if validation_errors:
            print("Eval case validation errors:", file=sys.stderr)
            for error in validation_errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)

        # Run eval suite
        results, summary = run_eval_suite(cases, filter_tag=filter_tag)

        # Output results
        if json_output:
            print(json.dumps(generate_eval_json(results, summary), indent=2))
        else:
            print(generate_eval_report(results, summary))

        # Set exit code based on pass/fail
        if summary.failed > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Eval run failed: {e}", file=sys.stderr)
        sys.exit(1)


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
    decision = policy_engine.evaluate(classification, risk_score, request.request_id)

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
            from ..audit.events import (
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
            from ..core.ids import utcnow_timestamp

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
            parser = ShellParser()
            parse_result = parser.parse(command)
            classifier = CommandClassifier()
            classification = classifier.classify(
                parse_result, command, request.request_id
            )
            registry_loader = RegistryLoader()
            command_registry = registry_loader.load_command_registry()
            policy_registry = registry_loader.load_policy_registry()
            risk_scorer = RiskScorer()
            risk_score = risk_scorer.score(classification, command_registry)
            policy_engine = PolicyEngine(policy_registry)
            re_decision = policy_engine.evaluate(
                classification=classification,
                risk_score=risk_score,
                request_id=request.request_id,
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
        approval = ApprovalRequest(
            request_id=request.request_id,
            decision_id=decision.decision_id,
            command=command,
            cwd=os.getcwd(),
            risk_score=decision.risk_score,
            reasons=decision.reasons,
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
            print(
                json.dumps(
                    {
                        "decision": decision.decision,
                        "approval_id": approval.approval_id,
                        "reasons": decision.reasons,
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
            print(
                json.dumps(
                    {
                        "decision": decision.decision,
                        "reasons": decision.reasons,
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
            print(
                json.dumps(
                    {
                        "decision": decision.decision,
                        "reasons": decision.reasons,
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


def handle_audit_command(args):
    """Handle audit subcommands."""
    from pathlib import Path

    # Initialize SQLite store
    try:
        sqlite_store = SQLiteAuditStore()
    except Exception as e:
        print(f"Error: Failed to initialize audit store: {e}", file=sys.stderr)
        sys.exit(1)

    # Check if database exists and has events
    if not Path(sqlite_store.path).exists():
        print(
            "No SQLite audit database found. Run a Policy Scout command first.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.audit_subcommand == "list":
        events = sqlite_store.list_recent(limit=args.limit)
        if args.json:
            print(json.dumps(events, indent=2))
        else:
            if not events:
                print("No audit events found.")
                return
            print("Recent Audit Events:")
            print()
            for event in events:
                print(f"Event ID: {event['event_id']}")
                print(f"Type: {event['event_type']}")
                print(f"Timestamp: {event['timestamp']}")
                print(f"Request ID: {event['request_id']}")
                print(f"Summary: {event['summary']}")
                print()

    elif args.audit_subcommand == "show":
        event = sqlite_store.get_event(args.event_id)
        if event is None:
            print(f"Error: Event not found: {args.event_id}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(event, indent=2))
        else:
            print("Audit Event:")
            print()
            print(f"Event ID: {event['event_id']}")
            print(f"Type: {event['event_type']}")
            print(f"Timestamp: {event['timestamp']}")
            print(f"Request ID: {event['request_id']}")
            print(f"Actor: {event['actor_type']} / {event['actor_name']}")
            print(f"Summary: {event['summary']}")
            print()
            print("Redaction: applied (secret-like values replaced with placeholders)")
            print()
            print("Data:")
            data = json.loads(event["data_json"])
            print(json.dumps(data, indent=2))

    elif args.audit_subcommand == "request":
        events = sqlite_store.list_by_request_id(args.request_id)
        if args.json:
            print(json.dumps(events, indent=2))
        else:
            if not events:
                print(f"No events found for request: {args.request_id}")
                return
            print(f"Events for Request: {args.request_id}")
            print()
            for event in events:
                print(f"Event ID: {event['event_id']}")
                print(f"Type: {event['event_type']}")
                print(f"Timestamp: {event['timestamp']}")
                print(f"Summary: {event['summary']}")
                print()

    elif args.audit_subcommand == "type":
        events = sqlite_store.list_by_event_type(args.event_type)
        if args.limit:
            events = events[: args.limit]
        if args.json:
            print(json.dumps(events, indent=2))
        else:
            if not events:
                print(f"No events found for type: {args.event_type}")
                return
            print(f"Events of Type: {args.event_type}")
            print()
            for event in events:
                print(f"Event ID: {event['event_id']}")
                print(f"Timestamp: {event['timestamp']}")
                print(f"Request ID: {event['request_id']}")
                print(f"Summary: {event['summary']}")
                print()

    elif args.audit_subcommand == "stats":
        total_count = sqlite_store.count_events()

        # Get counts by event type
        try:
            import sqlite3

            with sqlite3.connect(sqlite_store.path) as conn:
                cursor = conn.execute(
                    "SELECT event_type, COUNT(*) as count FROM audit_events GROUP BY event_type ORDER BY count DESC"
                )
                type_counts = {row[0]: row[1] for row in cursor.fetchall()}
        except Exception:
            type_counts = {}

        # Get time range
        first_event = None
        last_event = None
        try:
            import sqlite3

            with sqlite3.connect(sqlite_store.path) as conn:
                cursor = conn.execute(
                    "SELECT MIN(timestamp) as first, MAX(timestamp) as last FROM audit_events"
                )
                row = cursor.fetchone()
                if row:
                    first_event = row[0]
                    last_event = row[1]
        except Exception:
            pass

        if args.json:
            stats_data = {"total_events": total_count, "by_type": type_counts}
            if first_event or last_event:
                stats_data["time_range"] = {
                    "first_event": first_event,
                    "last_event": last_event,
                }
            print(json.dumps(stats_data, indent=2))
        else:
            print("Audit Statistics:")
            print()
            print(f"Total Events: {total_count}")
            if first_event or last_event:
                print()
                print("Time Range:")
                if first_event:
                    print(f"  First Event: {first_event}")
                if last_event:
                    print(f"  Last Event: {last_event}")
            print()
            if type_counts:
                print("By Event Type:")
                for event_type, count in type_counts.items():
                    print(f"  {event_type}: {count}")

    else:
        print("Error: No audit subcommand provided", file=sys.stderr)
        sys.exit(1)


def handle_report_command(args):
    """Handle report subcommands."""
    from ..reports.writer import get_report_root
    from ..audit.redaction import redact_string

    report_root = get_report_root()

    # Check if report root exists
    if not report_root.exists():
        print(
            "No Scout Reports found. Run a Policy Scout command with --report, sandbox, or sweep first.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.report_subcommand == "list":
        # Scan report root for report directories
        reports = []
        for report_dir in sorted(report_root.iterdir(), reverse=True):
            if not report_dir.is_dir():
                continue
            report_id = report_dir.name
            if not report_id.startswith("report_"):
                continue

            # Check for report files
            md_path = report_dir / "report.md"
            json_path = report_dir / "report.json"

            if not (md_path.exists() or json_path.exists()):
                continue

            # Try to read JSON for metadata
            metadata = {
                "report_id": report_id,
                "has_markdown": md_path.exists(),
                "has_json": json_path.exists(),
            }
            if json_path.exists():
                try:
                    with open(json_path, "r") as f:
                        data = json.load(f)
                        metadata["report_type"] = data.get("report_type", "unknown")
                        metadata["title"] = data.get("title", "")
                        metadata["created_at"] = data.get("created_at", "")
                except Exception:
                    pass

            reports.append(metadata)

        # Apply limit
        total_reports = len(reports)
        if args.limit:
            reports = reports[: args.limit]

        if args.json:
            print(json.dumps(reports, indent=2))
        else:
            if not reports:
                print("No Scout Reports found.")
                return
            print("Recent Scout Reports:")
            if total_reports > len(reports):
                print(
                    f"Showing {len(reports)} most recent reports (total: {total_reports})"
                )
            print()
            for report in reports:
                print(f"Report ID: {report['report_id']}")
                print(f"Type: {report.get('report_type', 'unknown')}")
                print(f"Title: {report.get('title', 'N/A')}")
                print(f"Created: {report.get('created_at', 'N/A')}")
                print(
                    f"Formats: Markdown={report['has_markdown']}, JSON={report['has_json']}"
                )
                print()

    elif args.report_subcommand == "show":
        report_dir = report_root / args.report_id
        if not report_dir.exists():
            print(f"Error: Report not found: {args.report_id}", file=sys.stderr)
            sys.exit(1)

        md_path = report_dir / "report.md"
        json_path = report_dir / "report.json"

        if args.json:
            # Show JSON report
            if not json_path.exists():
                print(
                    f"Error: JSON report not found for {args.report_id}",
                    file=sys.stderr,
                )
                sys.exit(1)
            with open(json_path, "r") as f:
                content = f.read()
                # Apply redaction on read
                content = redact_string(content)
                print(content)
        else:
            # Show Markdown report
            if not md_path.exists():
                if json_path.exists():
                    # Fallback to JSON summary
                    print("Markdown report not found. Showing JSON summary:")
                    with open(json_path, "r") as f:
                        data = json.load(f)
                        print(f"Report ID: {data.get('report_id')}")
                        print(f"Type: {data.get('report_type')}")
                        print(f"Title: {data.get('title')}")
                        print(f"Summary: {data.get('summary')}")
                        print(f"Created: {data.get('created_at')}")
                else:
                    print(
                        f"Error: No report files found for {args.report_id}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
            else:
                with open(md_path, "r") as f:
                    content = f.read()
                    # Apply redaction on read
                    content = redact_string(content)
                    print(content)

    elif args.report_subcommand == "export":
        report_dir = report_root / args.report_id
        if not report_dir.exists():
            print(f"Error: Report not found: {args.report_id}", file=sys.stderr)
            sys.exit(1)

        if args.format == "markdown":
            md_path = report_dir / "report.md"
            if not md_path.exists():
                print(
                    f"Error: Markdown report not found for {args.report_id}",
                    file=sys.stderr,
                )
                sys.exit(1)
            with open(md_path, "r") as f:
                content = f.read()
                # Apply redaction on read
                content = redact_string(content)
                print(content)
        elif args.format == "json":
            json_path = report_dir / "report.json"
            if not json_path.exists():
                print(
                    f"Error: JSON report not found for {args.report_id}",
                    file=sys.stderr,
                )
                sys.exit(1)
            with open(json_path, "r") as f:
                content = f.read()
                # Apply redaction on read
                content = redact_string(content)
                print(content)

    else:
        print("Error: No report subcommand provided", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
