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
    data_subparsers = data_parser.add_subparsers(
        dest="data_subcommand", help="Data commands"
    )

    # data status (default)
    data_status_parser = data_subparsers.add_parser(
        "status", help="Show local data status"
    )
    data_status_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # data cleanup
    data_cleanup_parser = data_subparsers.add_parser(
        "cleanup", help="Plan cleanup of temporary local data (dry-run only)"
    )
    data_cleanup_parser.add_argument(
        "--target",
        required=True,
        choices=["demo", "sandbox", "sandbox-results"],
        help="Target to clean up (demo, sandbox, sandbox-results)",
    )
    data_cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry-run mode (no deletion, always true in v1)",
    )
    data_cleanup_parser.add_argument(
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

    # audit verify-chain
    audit_verify_chain_parser = audit_subparsers.add_parser(
        "verify-chain", help="Verify HMAC chain integrity of the JSONL audit log"
    )
    audit_verify_chain_parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text"
    )

    # integrity command
    integrity_parser = subparsers.add_parser(
        "integrity", help="Verify Policy Scout self-integrity"
    )
    integrity_subparsers = integrity_parser.add_subparsers(
        dest="integrity_subcommand", help="Integrity commands"
    )
    integrity_check_parser = integrity_subparsers.add_parser(
        "check", help="Verify registry file checksums against manifest"
    )
    integrity_check_parser.add_argument(
        "--verbose", action="store_true", help="Show per-file results"
    )
    integrity_check_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    integrity_update_manifest_parser = integrity_subparsers.add_parser(
        "update-manifest",
        help="Regenerate manifest from current data files (dev/post-update only)",
    )
    integrity_update_manifest_parser.add_argument(
        "--version", default="dev", help="Version string to embed in manifest"
    )

    # lockdown command
    lockdown_parser = subparsers.add_parser(
        "lockdown", help="Manage Policy Scout lockdown mode"
    )
    lockdown_subparsers = lockdown_parser.add_subparsers(
        dest="lockdown_subcommand", help="Lockdown commands"
    )
    lockdown_on_parser = lockdown_subparsers.add_parser(
        "on", help="Activate lockdown (denies all non-read operations)"
    )
    lockdown_on_parser.add_argument(
        "--reason", default="", help="Reason for activating lockdown"
    )
    lockdown_subparsers.add_parser("off", help="Deactivate lockdown")
    lockdown_subparsers.add_parser(
        "status", help="Show current lockdown status"
    )

    # preserve command
    preserve_parser = subparsers.add_parser(
        "preserve", help="Capture system state evidence archive"
    )
    preserve_parser.add_argument(
        "--output-dir", help="Directory to write archive to"
    )
    preserve_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )

    # clearance command
    clearance_parser = subparsers.add_parser(
        "clearance", help="Run post-incident clearance checks before deactivating lockdown"
    )
    clearance_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
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
        "--type",
        type=str,
        help="Filter by report type (command_decision, sandbox_result, project_sweep, system_quick_sweep)",
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

    # scan command
    scan_parser = subparsers.add_parser(
        "scan", help="Scan for exposed secrets and credentials"
    )
    scan_subparsers = scan_parser.add_subparsers(
        dest="scan_subcommand", help="Scan commands"
    )

    # scan dir
    scan_dir_parser = scan_subparsers.add_parser(
        "dir", help="Scan a directory for secrets"
    )
    scan_dir_parser.add_argument(
        "path", nargs="?", default=".", help="Directory to scan (default: current)"
    )
    scan_dir_parser.add_argument(
        "--entropy", action="store_true", help="Enable entropy-based detection on .env files"
    )
    scan_dir_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    scan_dir_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )

    # scan file
    scan_file_parser = scan_subparsers.add_parser(
        "file", help="Scan a single file for secrets"
    )
    scan_file_parser.add_argument("path", help="File to scan")
    scan_file_parser.add_argument(
        "--entropy", action="store_true", help="Enable entropy-based detection"
    )
    scan_file_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    scan_file_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )

    # scan staged
    scan_staged_parser = scan_subparsers.add_parser(
        "staged", help="Scan git staged files for secrets (pre-commit)"
    )
    scan_staged_parser.add_argument(
        "--repo", help="Path to git repo root (default: current directory)"
    )
    scan_staged_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    scan_staged_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )

    # scan history
    scan_history_parser = scan_subparsers.add_parser(
        "history", help="Scan git commit history for secrets"
    )
    scan_history_parser.add_argument(
        "--repo", help="Path to git repo root (default: current directory)"
    )
    scan_history_parser.add_argument(
        "--max-commits", type=int, default=200, help="Max commits to scan (default: 200)"
    )
    scan_history_parser.add_argument(
        "--since", help="Only scan commits since this ref (e.g. origin/main)"
    )
    scan_history_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    scan_history_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )

    # git command
    git_parser = subparsers.add_parser(
        "git", help="Git integration: hooks, lockfile checks, context"
    )
    git_subparsers = git_parser.add_subparsers(
        dest="git_subcommand", help="Git commands"
    )

    # git context
    git_context_parser = git_subparsers.add_parser(
        "context", help="Show git context for the current directory"
    )
    git_context_parser.add_argument(
        "--repo", help="Path to git repo root (default: current directory)"
    )
    git_context_parser.add_argument("--json", action="store_true", help="Output JSON")

    # git hooks
    git_hooks_parser = git_subparsers.add_parser(
        "hooks", help="Manage git hooks installed by policy-scout"
    )
    git_hooks_subparsers = git_hooks_parser.add_subparsers(
        dest="git_hooks_subcommand", help="Hook commands"
    )

    # git hooks install
    hooks_install_parser = git_hooks_subparsers.add_parser(
        "install", help="Install policy-scout pre-commit hook"
    )
    hooks_install_parser.add_argument(
        "--repo", help="Path to git repo root (default: current directory)"
    )
    hooks_install_parser.add_argument("--json", action="store_true", help="Output JSON")

    # git hooks uninstall
    hooks_uninstall_parser = git_hooks_subparsers.add_parser(
        "uninstall", help="Remove policy-scout pre-commit hook"
    )
    hooks_uninstall_parser.add_argument(
        "--repo", help="Path to git repo root (default: current directory)"
    )
    hooks_uninstall_parser.add_argument("--json", action="store_true", help="Output JSON")

    # git hooks status
    hooks_status_parser = git_hooks_subparsers.add_parser(
        "status", help="Show hook installation status"
    )
    hooks_status_parser.add_argument(
        "--repo", help="Path to git repo root (default: current directory)"
    )
    hooks_status_parser.add_argument("--json", action="store_true", help="Output JSON")

    # git lockfile-check
    git_lockfile_parser = git_subparsers.add_parser(
        "lockfile-check", help="Check lockfiles for unexpected changes vs HEAD"
    )
    git_lockfile_parser.add_argument(
        "--repo", help="Path to git repo root (default: current directory)"
    )
    git_lockfile_parser.add_argument(
        "--ref", default="HEAD", help="Git ref to compare against (default: HEAD)"
    )
    git_lockfile_parser.add_argument("--json", action="store_true", help="Output JSON")

    # git staged-check
    git_staged_check_parser = git_subparsers.add_parser(
        "staged-check",
        help="Full pre-commit check: secrets + sensitive files + CI workflow changes",
    )
    git_staged_check_parser.add_argument(
        "--repo", help="Path to git repo root (default: current directory)"
    )
    git_staged_check_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    git_staged_check_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )

    # policy — simulation, validation, history testing, project overrides
    policy_parser = subparsers.add_parser(
        "policy", help="Policy simulation, validation, and management"
    )
    policy_subparsers = policy_parser.add_subparsers(dest="policy_subcommand")

    policy_simulate_parser = policy_subparsers.add_parser(
        "simulate", help="Simulate a command and show the full rule trace"
    )
    policy_simulate_parser.add_argument(
        "command", nargs="+", help="Command to simulate (use -- to separate from flags)"
    )
    policy_simulate_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    policy_simulate_parser.add_argument(
        "--cwd", help="Working directory for project override discovery (default: current dir)"
    )

    policy_show_parser = policy_subparsers.add_parser(
        "show", help="Show effective policy rules"
    )
    policy_show_parser.add_argument(
        "--effective", action="store_true",
        help="Include project override layers in output"
    )
    policy_show_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    policy_show_parser.add_argument(
        "--cwd", help="Working directory for project override discovery (default: current dir)"
    )

    policy_test_parser = policy_subparsers.add_parser(
        "test", help="Test current policy against recent audit history"
    )
    policy_test_parser.add_argument(
        "--against-history", action="store_true",
        help="Re-simulate historical decisions against current policy"
    )
    policy_test_parser.add_argument(
        "--days", type=int, default=7,
        help="Number of days of history to test (default: 7)"
    )
    policy_test_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    policy_test_parser.add_argument(
        "--cwd", help="Working directory for project override discovery"
    )

    policy_validate_parser = policy_subparsers.add_parser(
        "validate", help="Validate policy registry for unreachable rules, contradictions, coverage gaps"
    )
    policy_validate_parser.add_argument(
        "--strict", action="store_true",
        help="Treat warnings as errors (non-zero exit if any warnings)"
    )
    policy_validate_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )

    policy_commit_parser = policy_subparsers.add_parser(
        "commit", help="Snapshot current policy registry state into git"
    )
    policy_commit_parser.add_argument(
        "--message", "-m", help="Commit message (default: auto-generated)"
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
        # Handle data subcommands
        if args.data_subcommand == "cleanup":
            from policy_scout.data_cleanup import (
                plan_cleanup,
                format_cleanup_plan_human,
                format_cleanup_plan_json,
            )

            plan = plan_cleanup(args.target)
            if args.json:
                output = format_cleanup_plan_json(plan)
            else:
                output = format_cleanup_plan_human(plan)
            print(output)
        else:
            # Default to status for backward compatibility
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
    elif args.subcommand == "integrity":
        handle_integrity_command(args)
    elif args.subcommand == "lockdown":
        handle_lockdown_command(args)
    elif args.subcommand == "preserve":
        handle_preserve_command(args)
    elif args.subcommand == "clearance":
        handle_clearance_command(args)
    elif args.subcommand == "scan":
        handle_scan_command(args)
    elif args.subcommand == "git":
        handle_git_command(args)
    elif args.subcommand == "report":
        handle_report_command(args)
    elif args.subcommand == "policy":
        handle_policy_command(args)
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
    decision = policy_engine.evaluate(
        classification, risk_score, request.request_id, command=request.command
    )

    # Write audit events for project override
    if audit_store.enabled:
        if policy_engine.project_override:
            from ..audit.events import EventType
            from ..audit.store import AuditEvent
            audit_store.write(AuditEvent(
                event_type=EventType.PROJECT_OVERRIDE_LOADED,
                request_id=request.request_id,
                summary=f"Project override loaded from {policy_engine.project_override.config_path}",
                data=policy_engine.project_override.to_dict(),
            ))
        elif policy_engine.override_violation:
            from ..audit.events import EventType
            from ..audit.store import AuditEvent
            audit_store.write(AuditEvent(
                event_type=EventType.PROJECT_OVERRIDE_VIOLATED,
                request_id=request.request_id,
                summary="Project override rejected (tighten-only violation)",
                data={"violation": policy_engine.override_violation, "fallback": "global policy"},
            ))

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


def handle_lockdown_command(args):
    """Handle lockdown subcommands."""
    from ..response.lockdown import (
        activate_lockdown,
        deactivate_lockdown,
        is_lockdown_active,
        get_lockdown_reason,
    )
    from ..audit.store import AuditStore

    audit_store = AuditStore()

    if args.lockdown_subcommand == "on":
        reason = getattr(args, "reason", "")
        if is_lockdown_active():
            print("Lockdown is already active.")
            return
        success = activate_lockdown(reason=reason, audit_store=audit_store)
        if success:
            print("Lockdown activated. All non-read operations will be DENIED.")
            if reason:
                print(f"Reason: {reason}")
        else:
            print("Error: Failed to activate lockdown.", file=sys.stderr)
            sys.exit(1)

    elif args.lockdown_subcommand == "off":
        if not is_lockdown_active():
            print("Lockdown is not active.")
            return
        success = deactivate_lockdown(cleared_by="cli", audit_store=audit_store)
        if success:
            print("Lockdown deactivated. Normal policy evaluation restored.")
        else:
            print("Error: Failed to deactivate lockdown.", file=sys.stderr)
            sys.exit(1)

    elif args.lockdown_subcommand == "status":
        if is_lockdown_active():
            reason = get_lockdown_reason()
            print("Status: LOCKDOWN ACTIVE")
            if reason:
                print(f"Reason: {reason}")
        else:
            print("Status: Lockdown inactive (normal operation)")

    else:
        print("Error: No lockdown subcommand provided", file=sys.stderr)
        sys.exit(1)


def handle_preserve_command(args):
    """Handle preserve command."""
    from pathlib import Path as _Path
    from ..response.preserve import preserve_evidence
    from ..audit.store import AuditStore

    audit_store = AuditStore()
    output_dir = None
    if getattr(args, "output_dir", None):
        output_dir = _Path(args.output_dir)

    result = preserve_evidence(output_dir=output_dir, audit_store=audit_store)

    if getattr(args, "json", False):
        print(json.dumps({
            "path": result.path,
            "artifact_count": result.artifact_count,
            "artifacts": result.artifacts,
            "errors": result.errors,
        }, indent=2))
    else:
        print(f"Evidence archive created: {result.path}")
        print(f"  Artifacts: {result.artifact_count}")
        for artifact in result.artifacts:
            print(f"    + {artifact}")
        if result.errors:
            print(f"  Errors ({len(result.errors)}):")
            for err in result.errors:
                print(f"    ! {err}")


def handle_clearance_command(args):
    """Handle clearance command."""
    from ..response.clearance import run_clearance_check
    from ..audit.store import AuditStore

    audit_store = AuditStore()
    result = run_clearance_check(audit_store=audit_store)

    if getattr(args, "json", False):
        print(json.dumps({
            "cleared": result.cleared,
            "summary": result.summary,
            "checks": [
                {"name": c.name, "passed": c.passed, "message": c.message}
                for c in result.checks
            ],
        }, indent=2))
    else:
        print("Post-Incident Clearance Check")
        print("=" * 40)
        for check in result.checks:
            sym = "✓" if check.passed else "✗"
            print(f"  {sym} {check.name}: {check.message}")
        print()
        print(f"Result: {result.summary}")
        if not result.cleared:
            sys.exit(1)


def handle_integrity_command(args):
    """Handle integrity subcommands."""
    from ..integrity.registry_manifest import (
        verify_registry_integrity,
        generate_manifest,
        write_manifest,
    )

    if args.integrity_subcommand == "check":
        result = verify_registry_integrity()

        if args.json:
            out = {
                "passed": result.passed,
                "files_checked": result.files_checked,
                "reason": result.reason,
                "errors": result.errors,
            }
            print(json.dumps(out, indent=2))
        else:
            status_sym = "✓" if result.passed else "✗"
            print(f"Registry integrity: {status_sym}")
            print(f"  {result.reason}")
            if result.errors and (getattr(args, "verbose", False) or not result.passed):
                for err in result.errors:
                    print(f"  - {err}")

        if not result.passed:
            sys.exit(1)

    elif args.integrity_subcommand == "update-manifest":
        version = getattr(args, "version", "dev")
        manifest = generate_manifest(version=version)
        write_manifest(manifest)
        files = manifest["files"]
        print(f"Manifest updated: {len(files)} file(s) hashed.")
        for name in files:
            print(f"  {name}")

    else:
        print("Error: No integrity subcommand provided", file=sys.stderr)
        sys.exit(1)


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

    elif args.audit_subcommand == "verify-chain":
        from pathlib import Path as _Path
        from ..audit.chain_verifier import verify_chain
        from ..audit.events import create_chain_verification_event

        # Resolve the JSONL path the same way JSONLWriter does
        jsonl_path = _Path.home() / ".local" / "share" / "policy-scout" / "audit.jsonl"
        env_path = os.environ.get("POLICY_SCOUT_AUDIT_PATH")
        if env_path:
            jsonl_path = _Path(env_path)

        result = verify_chain(jsonl_path)

        # Write the outcome to the audit log (best-effort)
        try:
            store = AuditStore()
            store.write(
                create_chain_verification_event(
                    verified=result.verified,
                    total_entries=result.total_entries,
                    error_count=len(result.errors),
                )
            )
        except Exception:
            pass

        if args.json:
            out = {
                "verified": result.verified,
                "total_entries": result.total_entries,
                "message": result.message,
                "errors": [
                    {"lineno": e.lineno, "kind": e.kind, "detail": e.detail}
                    for e in result.errors
                ],
            }
            print(json.dumps(out, indent=2))
        else:
            status_sym = "✓" if result.verified else "✗"
            print(f"Audit chain verification: {status_sym}")
            print(f"  File: {jsonl_path}")
            print(f"  {result.message}")
            if result.errors:
                print()
                print("  Errors:")
                for err in result.errors[:20]:
                    print(f"    line {err.lineno}: [{err.kind}] {err.detail}")
                if len(result.errors) > 20:
                    print(f"    ... and {len(result.errors) - 20} more")

        if not result.verified:
            sys.exit(1)

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

        # Apply type filter
        if args.type:
            reports = [r for r in reports if r.get("report_type") == args.type]

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
            if args.type:
                print(f"Filtered by type: {args.type}")
            if total_reports > len(reports):
                print(
                    f"Showing {len(reports)} most recent reports (total: {total_reports})"
                )
            print()
            for report in reports:
                print(f"Report ID: {report['report_id']}")
                print(f"Type: {report.get('report_type', 'unknown')}")
                print(f"Title: {report.get('title', 'N/A')}")
                created_at = report.get("created_at", "")
                print(f"Created: {created_at if created_at else 'unknown'}")
                print(
                    f"Formats: Markdown={report['has_markdown']}, JSON={report['has_json']}"
                )
                print()
            print("Use: policy-scout report show <report_id>")

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


def handle_scan_command(args) -> None:
    """Handle all scan subcommands."""
    from ..scan.engine import SecretScanner
    from ..audit.events import create_secret_scan_completed_event, create_secret_finding_event
    from pathlib import Path

    audit_store = AuditStore() if not getattr(args, "no_audit", False) else None
    scanner = SecretScanner()

    sub = getattr(args, "scan_subcommand", None)
    if not sub:
        print("Error: No scan subcommand provided. Use: dir, file, staged, history", file=sys.stderr)
        sys.exit(1)

    if sub == "dir":
        root = Path(getattr(args, "path", "."))
        if not root.is_dir():
            print(f"Error: Not a directory: {root}", file=sys.stderr)
            sys.exit(1)
        summary = scanner.scan_directory(root, run_entropy=getattr(args, "entropy", False))

    elif sub == "file":
        path = Path(args.path)
        if not path.is_file():
            print(f"Error: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        summary = scanner.scan_file(path, run_entropy=getattr(args, "entropy", False))

    elif sub == "staged":
        repo = Path(getattr(args, "repo", None) or ".")
        summary = scanner.scan_staged(repo_root=repo)

    elif sub == "history":
        repo = Path(getattr(args, "repo", None) or ".")
        summary = scanner.scan_history(
            repo_root=repo,
            max_commits=getattr(args, "max_commits", 200),
            since_ref=getattr(args, "since", None),
        )
    else:
        print(f"Error: Unknown scan subcommand: {sub}", file=sys.stderr)
        sys.exit(1)

    # Audit
    if audit_store:
        for finding in summary.findings:
            audit_store.write(
                create_secret_finding_event(
                    scan_id=summary.scan_id,
                    secret_type=finding.secret_type,
                    service=finding.service,
                    severity=finding.severity,
                    source=finding.source,
                    line=finding.line,
                )
            )
        audit_store.write(
            create_secret_scan_completed_event(
                scan_id=summary.scan_id,
                scan_type=summary.scan_type,
                target=summary.target,
                finding_count=summary.finding_count,
                severity_counts=summary.severity_counts(),
                files_scanned=summary.files_scanned,
                duration_ms=summary.duration_ms,
            )
        )

    if getattr(args, "json", False):
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        _print_scan_summary(summary)

    sys.exit(summary.severity_exit_code)


def _print_scan_summary(summary) -> None:
    """Print human-readable scan output."""
    counts = summary.severity_counts()
    print(f"\nSecret Scan — {summary.scan_type}: {summary.target}")
    print(f"  Files scanned : {summary.files_scanned}")
    if summary.commits_scanned:
        print(f"  Commits scanned: {summary.commits_scanned}")
    print(f"  Duration      : {summary.duration_ms}ms")
    print(f"  Findings      : {summary.finding_count}")

    if not summary.findings:
        print("\n  No secrets detected.")
        return

    # Group by severity for display
    for severity in ("critical", "high", "medium", "low"):
        group = [f for f in summary.findings if f.severity == severity]
        if not group:
            continue
        label = severity.upper()
        print(f"\n  [{label}] {len(group)} finding(s)")
        for f in group:
            commit_suffix = f" (commit {f.commit[:8]})" if f.commit else ""
            print(f"    {f.source}:{f.line}  {f.service}/{f.secret_type}{commit_suffix}")
            print(f"      Redacted: {f.redacted_value}")
            print(f"      Action  : {f.guidance[:120]}")

    if summary.errors:
        print(f"\n  Errors ({len(summary.errors)}):")
        for e in summary.errors[:5]:
            print(f"    {e}")


def handle_git_command(args) -> None:
    """Handle all git subcommands."""
    from ..git.context import get_git_context
    from ..git.hooks import get_hooks_status, install_hooks, uninstall_hooks
    from ..git.lockfile_diff import check_lockfile_changes
    from ..git.staged_scanner import scan_staged_full
    from pathlib import Path

    sub = getattr(args, "git_subcommand", None)
    if not sub:
        print(
            "Error: No git subcommand provided. Use: context, hooks, lockfile-check, staged-check",
            file=sys.stderr,
        )
        sys.exit(1)

    if sub == "context":
        repo = Path(getattr(args, "repo", None) or ".")
        ctx = get_git_context(cwd=repo)
        if ctx is None:
            print("Not a git repository.", file=sys.stderr)
            sys.exit(1)
        if getattr(args, "json", False):
            print(json.dumps(ctx.to_dict(), indent=2))
        else:
            print(f"Branch  : {ctx.branch or '(detached)'}")
            print(f"Commit  : {ctx.commit or '(none)'}")
            print(f"Dirty   : {'yes' if ctx.dirty else 'no'}")
            print(f"Remote  : {ctx.remote or '(none)'}")
            print(f"Root    : {ctx.repo_root}")

    elif sub == "hooks":
        hooks_sub = getattr(args, "git_hooks_subcommand", None)
        repo = Path(getattr(args, "repo", None) or ".")

        if hooks_sub == "install":
            try:
                report = install_hooks(repo_root=repo)
                if getattr(args, "json", False):
                    print(json.dumps(report.to_dict(), indent=2))
                else:
                    print(f"Hooks installed in: {report.hooks_dir}")
                    for h in report.hooks:
                        status = "installed" if h.installed else "failed"
                        print(f"  {h.name}: {status}")
            except RuntimeError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

        elif hooks_sub == "uninstall":
            try:
                report = uninstall_hooks(repo_root=repo)
                if getattr(args, "json", False):
                    print(json.dumps(report.to_dict(), indent=2))
                else:
                    print("Hooks uninstalled.")
                    for h in report.hooks:
                        status = "removed" if not h.installed else "kept (not managed)"
                        print(f"  {h.name}: {status}")
            except RuntimeError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

        elif hooks_sub == "status":
            report = get_hooks_status(repo_root=repo)
            if getattr(args, "json", False):
                print(json.dumps(report.to_dict(), indent=2))
            else:
                print(f"Hooks directory: {report.hooks_dir or '(not found)'}")
                for h in report.hooks:
                    managed_note = " (managed)" if h.managed else " (third-party)" if h.installed else ""
                    print(f"  {h.name}: {'installed' if h.installed else 'not installed'}{managed_note}")
        else:
            print("Error: No hooks subcommand. Use: install, uninstall, status", file=sys.stderr)
            sys.exit(1)

    elif sub == "lockfile-check":
        repo = Path(getattr(args, "repo", None) or ".")
        ref = getattr(args, "ref", "HEAD")
        result = check_lockfile_changes(repo_root=repo, compare_ref=ref)
        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Lockfiles found: {result.lockfiles_found}")
            print(f"Lockfiles changed: {result.lockfiles_changed}")
            for diff in result.diffs:
                if diff.error:
                    print(f"  {diff.lockfile}: ERROR — {diff.error}")
                elif diff.has_changes:
                    print(f"  {diff.lockfile}: CHANGED (+{len(diff.added)} -{len(diff.removed)} ~{diff.modified})")
                    for line in diff.added[:5]:
                        print(f"    + {line}")
                    for line in diff.removed[:5]:
                        print(f"    - {line}")
                else:
                    print(f"  {diff.lockfile}: OK")
        sys.exit(2 if result.any_changes else 0)

    elif sub == "staged-check":
        repo = Path(getattr(args, "repo", None) or ".")
        result = scan_staged_full(repo_root=repo)
        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_staged_check(result)
        sys.exit(result.severity_exit_code)

    else:
        print(f"Error: Unknown git subcommand: {sub}", file=sys.stderr)
        sys.exit(1)


def _print_staged_check(result) -> None:
    """Print human-readable staged-check output."""
    if result.is_clean and not result.has_ci_changes:
        print("Pre-commit check: CLEAN — no secrets or sensitive files detected.")
        return

    if result.has_sensitive_files:
        print(f"\n[BLOCK] {len(result.sensitive_files)} sensitive file(s) staged:")
        for w in result.sensitive_files:
            print(f"  {w.path}")
            print(f"    Reason: {w.reason}")

    if result.has_secrets and result.secret_scan:
        sc = result.secret_scan
        print(f"\n[BLOCK] {sc.finding_count} secret(s) detected in staged files:")
        for f in sc.findings:
            severity_label = f.severity.upper()
            print(f"  [{severity_label}] {f.source}:{f.line}  {f.service}/{f.secret_type}")
            print(f"    Redacted: {f.redacted_value}")
            print(f"    Action  : {f.guidance[:120]}")

    if result.has_ci_changes:
        print(f"\n[WARN] {len(result.ci_workflow_changes)} CI workflow file(s) changed:")
        for path in result.ci_workflow_changes:
            print(f"  {path}")
        print("  Review CI workflow changes carefully before committing.")

    if result.errors:
        print(f"\n[ERROR] Scan errors:")
        for e in result.errors:
            print(f"  {e}")


def handle_policy_command(args) -> None:
    """Handle all policy subcommands."""
    from ..policy.management.simulator import simulate, SimulationResult
    from ..registry.loader import RegistryLoader
    from pathlib import Path as _Path

    sub = getattr(args, "policy_subcommand", None)
    if not sub:
        print("Error: No policy subcommand provided. Use: simulate, show", file=sys.stderr)
        sys.exit(1)

    if sub == "simulate":
        raw_parts = args.command
        # Strip leading "--" separator if present
        if raw_parts and raw_parts[0] == "--":
            raw_parts = raw_parts[1:]
        command_str = " ".join(raw_parts)
        if not command_str:
            print("Error: No command provided to simulate", file=sys.stderr)
            sys.exit(1)

        cwd = _Path(args.cwd) if getattr(args, "cwd", None) else None
        result = simulate(command_str, cwd=cwd)

        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_simulation_result(result)

    elif sub == "show":
        cwd = _Path(args.cwd) if getattr(args, "cwd", None) else None
        effective = getattr(args, "effective", False)
        loader = RegistryLoader()

        from ..policy.management.project_override import load_project_override
        override = load_project_override(cwd=cwd) if effective else None

        if getattr(args, "json", False):
            out: dict = {
                "registry_version": loader.policy_registry.version if loader.policy_registry else None,
                "rules": [],
                "project_override": override.to_dict() if override else None,
            }
            if loader.policy_registry:
                for entry in loader.policy_registry.policies:
                    out["rules"].append({
                        "id": entry.id,
                        "priority": entry.priority,
                        "decision": entry.decision,
                        "status": entry.status,
                        "source": "registry",
                    })
            if override:
                for rule in override.additional_rules:
                    out["rules"].append({
                        "id": rule.id,
                        "priority": rule.priority,
                        "decision": rule.decision,
                        "source": "override",
                    })
            print(json.dumps(out, indent=2))
        else:
            _print_policy_show(loader, override)

    elif sub == "test":
        if not getattr(args, "against_history", False):
            print(
                "Error: Specify a test mode. Currently supported: --against-history",
                file=sys.stderr,
            )
            sys.exit(1)
        from ..policy.management.history_tester import test_against_history
        cwd = _Path(args.cwd) if getattr(args, "cwd", None) else None
        days = getattr(args, "days", 7)
        result = test_against_history(days=days, cwd=cwd)

        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_history_test_result(result)

    elif sub == "validate":
        from ..policy.management.validator import validate_policy
        strict = getattr(args, "strict", False)
        result = validate_policy(strict=strict)

        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_validation_result(result)

        if not result.is_valid:
            sys.exit(1)

    elif sub == "commit":
        from ..policy.management.policy_commit import commit_policy_state
        message = getattr(args, "message", None)
        try:
            sha = commit_policy_state(message=message)
            print(f"Policy snapshot committed: {sha}")
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Error: Unknown policy subcommand: {sub}", file=sys.stderr)
        sys.exit(1)


def _print_simulation_result(result) -> None:
    """Print human-readable simulation output."""
    DECISION_COLORS = {
        "ALLOW": "ALLOW",
        "ALLOW_LOGGED": "ALLOW_LOGGED",
        "REQUIRE_APPROVAL": "REQUIRE_APPROVAL",
        "SANDBOX_FIRST": "SANDBOX_FIRST",
        "DENY": "DENY",
        "DENY_AND_ALERT": "DENY_AND_ALERT",
    }
    decision = DECISION_COLORS.get(result.decision, result.decision)

    print(f"\nCommand:    {result.command}")
    print(f"Decision:   {decision}")
    print(f"Risk:       {result.risk_score} / 10 ({result.risk_band})")

    if result.matched_rule:
        matched_index = next(
            (i + 1 for i, t in enumerate(result.rule_traces) if t.decisive),
            None,
        )
        print(
            f"Matched:    {result.matched_rule}"
            + (f" (rule {matched_index} of {result.total_rules_checked})" if matched_index else "")
        )
    else:
        print("Matched:    (no rule matched — default DENY)")

    if result.categories:
        print(f"Categories: {', '.join(result.categories)}")
    if result.capabilities:
        print(f"Caps:       {', '.join(result.capabilities)}")

    if result.project_override_loaded:
        print(f"Override:   {result.project_override_path}")

    print("\nRule trace:")
    for trace in result.rule_traces:
        source_tag = f"[{trace.source}]"
        if trace.decisive:
            marker = "→"
            detail = f"MATCHED → {trace.decision}"
            print(f"  {marker} {trace.rule_id:<40} {source_tag:<12} {detail}")
            for reason in trace.reasons:
                print(f"      - {reason}")
        elif trace.matched:
            print(f"    {trace.rule_id:<40} {source_tag:<12} matched (lower priority — not decisive)")
        else:
            print(f"    {trace.rule_id:<40} {source_tag:<12} no match")
    print()


def _print_history_test_result(result) -> None:
    """Print human-readable history test output."""
    print(f"\nTested {result.total} historical decisions from the last {result.days} days.\n")
    if result.skipped:
        print(f"  Skipped: {result.skipped} events (missing command data)\n")
    if result.changed == 0:
        print("  No decisions would change under the current policy.")
    else:
        print(f"  Changed: {result.changed} / {result.total}")
        if result.tightened:
            print(f"    {result.tightened} decisions became more restrictive")
        if result.loosened:
            print(f"    {result.loosened} decisions became less restrictive")
        print("\nChanged decisions:")
        for case in result.changed_cases[:20]:
            direction = f"[{case.direction}]" if case.direction else ""
            print(
                f"  [{case.timestamp[:19]}] {repr(case.command)[:60]:<62} "
                f"{case.original_decision} → {case.simulated_decision} {direction}"
            )
        if len(result.changed_cases) > 20:
            print(f"  ... and {len(result.changed_cases) - 20} more")
    print()


def _print_validation_result(result) -> None:
    """Print human-readable validation output."""
    print(
        f"\nPolicy validation: checked {result.rules_checked} rules, "
        f"{result.eval_cases_checked} eval cases.\n"
    )
    if not result.issues:
        print("  No issues found — policy is valid.")
    else:
        errors = [i for i in result.issues if i.severity == "error"]
        warnings = [i for i in result.issues if i.severity == "warning"]
        if errors:
            print(f"  Errors ({len(errors)}):")
            for issue in errors:
                print(f"    [{issue.issue_type}] {issue.rule_id}: {issue.description}")
        if warnings:
            print(f"  Warnings ({len(warnings)}):")
            for issue in warnings:
                print(f"    [{issue.issue_type}] {issue.rule_id}: {issue.description}")
    print()


def _print_policy_show(loader, override) -> None:
    """Print human-readable effective policy."""
    registry = loader.policy_registry
    print("\nEffective policy rules (sorted by priority, highest first):\n")

    rules = []
    if registry:
        for entry in registry.policies:
            rules.append({
                "id": entry.id,
                "priority": entry.priority,
                "decision": entry.decision,
                "status": entry.status,
                "source": "registry",
            })

    if override:
        for rule in override.additional_rules:
            rules.append({
                "id": rule.id,
                "priority": rule.priority,
                "decision": rule.decision,
                "status": "active",
                "source": "override",
            })

    rules.sort(key=lambda r: r["priority"], reverse=True)

    for rule in rules:
        status = "" if rule["status"] == "active" else f" [{rule['status']}]"
        src = f"({rule['source']})"
        print(f"  {rule['priority']:>4}  {rule['id']:<45} {rule['decision']:<20} {src}{status}")

    if override:
        print(f"\nProject override: {override.config_path} (version: {override.version or 'unversioned'})")
        if override.override_decisions:
            print("  Strengthened decisions:")
            for od in override.override_decisions:
                print(f"    {od.rule_id} → {od.strengthen_to}")
    print()


if __name__ == "__main__":
    cli()
