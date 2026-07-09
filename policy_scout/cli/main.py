# SPDX-License-Identifier: Apache-2.0
"""Main CLI entry point."""

import argparse
import sys
import json
import os
from typing import Optional

from ..doctor import run_doctor_checks, format_doctor_output
from ..demo import run_demo
from ..data_status import (
    get_data_status,
    format_data_status_human,
    format_data_status_json,
)
from .commands.check import check_command, print_human_output
from .commands.approvals import handle_approvals_command
from .commands.sandbox import handle_sandbox_command, handle_sandbox_migrate_command
from .commands.sweep import handle_sweep_project_command, handle_sweep_quick_command
from .commands.eval import handle_eval_run_command
from .commands.run import handle_run_command
from .commands.lockdown import handle_lockdown_command
from .commands.clearance import handle_preserve_command, handle_clearance_command
from .commands.integrity import handle_integrity_command
from .commands.audit import handle_audit_command
from .commands.report import handle_report_command
from .commands.scan import handle_scan_command, handle_git_command
from .commands.policy import handle_policy_command
from .commands.intel import handle_intel_command
from .commands.watch import handle_watch_command
from .commands.serve import handle_serve_command
from .commands.canary import handle_canary_command
from .commands.sandbox_run import handle_sandbox_run_command, handle_sandbox_prereqs_command


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
    check_parser.add_argument(
        "--with-intel", action="store_true",
        help="Enrich with remote threat intel (OSV + npm advisories; requires network)"
    )
    check_parser.add_argument(
        "--hook-mode", action="store_true",
        help="Emit only machine-readable JSON to stdout (for use as a Claude Code hook)"
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
    list_parser = approvals_subparsers.add_parser("list", help="List pending approval requests")
    list_parser.add_argument("--json", action="store_true", help="Output JSON")

    # approvals show
    show_parser = approvals_subparsers.add_parser(
        "show", help="Show approval request details"
    )
    show_parser.add_argument("approval_id", help="Approval ID to show")
    show_parser.add_argument("--json", action="store_true", help="Output JSON")

    # approvals approve
    approve_parser = approvals_subparsers.add_parser(
        "approve", help="Approve a request"
    )
    approve_parser.add_argument("approval_id", help="Approval ID to approve")
    approve_parser.add_argument("--json", action="store_true", help="Output JSON")

    # approvals deny
    deny_parser = approvals_subparsers.add_parser("deny", help="Deny a request")
    deny_parser.add_argument("approval_id", help="Approval ID to deny")
    deny_parser.add_argument("--json", action="store_true", help="Output JSON")

    # approvals set-timeout
    set_timeout_parser = approvals_subparsers.add_parser(
        "set-timeout", help="Set default approval expiry window in hours"
    )
    set_timeout_parser.add_argument(
        "hours", type=int, help="Approval timeout in hours (e.g. 24, 48, 168)"
    )
    set_timeout_parser.add_argument("--json", action="store_true", help="Output JSON")

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

    # sandbox run — general-purpose namespace sandbox
    sandbox_run_parser = sandbox_parser  # alias so the next block is readable

    # sandbox run (subparser added to the top-level subparsers, not sandbox_parser)
    sandbox_run_top = subparsers.add_parser(
        "sandbox-run", help="Run any command in a Linux namespace sandbox"
    )
    sandbox_run_top.add_argument(
        "--timeout", type=int, default=30, help="Timeout in seconds (default: 30)"
    )
    sandbox_run_top.add_argument(
        "--allow-network", action="store_true",
        help="Allow outbound network in the sandbox (default: isolated)"
    )
    sandbox_run_top.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    sandbox_run_top.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )
    sandbox_run_top.add_argument(
        "command", nargs="...", help="Command to run in the sandbox (after --)"
    )

    sandbox_prereqs_parser = subparsers.add_parser(
        "sandbox-check-prereqs", help="Check general sandbox prerequisites"
    )
    sandbox_prereqs_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
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
        "cleanup", help="Plan or execute cleanup of temporary local data"
    )
    data_cleanup_parser.add_argument(
        "--target",
        required=True,
        choices=["demo", "sandbox", "sandbox-results"],
        help="Target to clean up (demo, sandbox, sandbox-results)",
    )
    data_cleanup_parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Execute deletion (default is dry-run preview only)",
    )
    data_cleanup_parser.add_argument(
        "--yes",
        action="store_true",
        default=False,
        help="Skip confirmation prompt (only applies with --apply)",
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
        "--offset", type=int, default=0, help="Skip N events (for pagination, default: 0)"
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
        "--offset", type=int, default=0, help="Skip N events (for pagination, default: 0)"
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
    lockdown_on_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    lockdown_off_parser = lockdown_subparsers.add_parser("off", help="Deactivate lockdown")
    lockdown_off_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    lockdown_status_parser = lockdown_subparsers.add_parser(
        "status", help="Show current lockdown status"
    )
    lockdown_status_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
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
        "--offset", type=int, default=0, help="Skip N reports (for pagination, default: 0)"
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

    # scan injection
    scan_injection_parser = scan_subparsers.add_parser(
        "injection", help="Scan files for prompt injection patterns"
    )
    scan_injection_parser.add_argument(
        "path", nargs="?", default=".", help="Directory or file to scan (default: current)"
    )
    scan_injection_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    scan_injection_parser.add_argument(
        "--no-audit", action="store_true", help="Disable audit logging"
    )

    # canary command
    canary_parser = subparsers.add_parser(
        "canary", help="Manage prompt-injection canary files"
    )
    canary_subparsers = canary_parser.add_subparsers(dest="canary_subcommand")

    canary_install_parser = canary_subparsers.add_parser(
        "install", help="Place a canary file in the project root"
    )
    canary_install_parser.add_argument(
        "--path", default=".", help="Project root (default: current directory)"
    )
    canary_install_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )

    canary_check_parser = canary_subparsers.add_parser(
        "check", help="Verify canary state and show audit log hits"
    )
    canary_check_parser.add_argument(
        "--path", default=".", help="Project root (default: current directory)"
    )
    canary_check_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )

    canary_remove_parser = canary_subparsers.add_parser(
        "remove", help="Remove the canary file"
    )
    canary_remove_parser.add_argument(
        "--path", default=".", help="Project root (default: current directory)"
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

    # intel command
    intel_parser = subparsers.add_parser(
        "intel", help="Threat intelligence management"
    )
    intel_subparsers = intel_parser.add_subparsers(dest="intel_subcommand")

    intel_status_parser = intel_subparsers.add_parser(
        "status", help="Show intel adapter status and cache stats"
    )
    intel_status_parser.add_argument("--json", action="store_true", help="Output JSON")

    intel_subparsers.add_parser(
        "clear-cache", help="Flush the remote intel TTL cache"
    )

    intel_subparsers.add_parser(
        "evict-expired", help="Remove expired cache entries"
    )

    # watch command
    watch_parser = subparsers.add_parser(
        "watch", help="Continuous filesystem watch daemon"
    )
    watch_subparsers = watch_parser.add_subparsers(dest="watch_subcommand")

    watch_start_parser = watch_subparsers.add_parser(
        "start", help="Start the watch daemon in the background"
    )
    watch_start_parser.add_argument(
        "--mode", choices=["project", "system", "both"], default="both",
        help="Watch scope (default: both)"
    )
    watch_start_parser.add_argument(
        "--poll-interval", type=float, default=2.0,
        help="Polling fallback interval in seconds (default: 2.0)"
    )
    watch_start_parser.add_argument(
        "--foreground", action="store_true",
        help="Run in foreground instead of forking (for debugging)"
    )
    watch_start_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )

    watch_subparsers.add_parser("stop", help="Stop the running watch daemon")

    watch_status_parser = watch_subparsers.add_parser(
        "status", help="Show watch daemon status"
    )
    watch_status_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )

    watch_logs_parser = watch_subparsers.add_parser(
        "logs", help="Tail the watch daemon log"
    )
    watch_logs_parser.add_argument(
        "--lines", "-n", type=int, default=50,
        help="Number of lines to show (default: 50)"
    )

    # serve command — MCP stdio server
    serve_parser = subparsers.add_parser(
        "serve", help="Start the Policy Scout MCP server"
    )
    serve_subparsers = serve_parser.add_subparsers(dest="serve_subcommand")

    serve_mcp_parser = serve_subparsers.add_parser(
        "mcp", help="Run the JSON-RPC 2.0 MCP server over stdio"
    )
    serve_mcp_parser.add_argument(
        "--log-audit", action="store_true",
        help="Emit audit events for every tool call (default: on)"
    )

    serve_install_parser = serve_subparsers.add_parser(
        "install", help="Install Policy Scout as a Claude Code PreToolUse hook"
    )
    serve_install_parser.add_argument(
        "--scope", choices=["project", "user"], default="project",
        help="Install hook in project .claude/settings.json or user-level settings"
    )
    serve_install_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )

    serve_status_parser = serve_subparsers.add_parser(
        "status", help="Show MCP server registration status"
    )
    serve_status_parser.add_argument(
        "--json", action="store_true", help="Output JSON"
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

        hook_mode = getattr(args, "hook_mode", False)
        result = check_command(
            command_str,
            json_output=args.json or hook_mode,
            audit_enabled=not args.no_audit,
            approval_enabled=not args.no_approval,
            report_enabled=args.report,
            with_intel=getattr(args, "with_intel", False),
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
                execute_cleanup,
                format_cleanup_result_human,
                format_cleanup_result_json,
            )

            plan = plan_cleanup(args.target)

            if not getattr(args, "apply", False):
                # Dry-run: show plan only
                if args.json:
                    output = format_cleanup_plan_json(plan)
                else:
                    output = format_cleanup_plan_human(plan)
                print(output)
            else:
                # Execution path
                if "error" in plan:
                    print(f"Error: {plan['error']}", file=__import__("sys").stderr)
                    raise SystemExit(1)

                if plan["total_items"] == 0:
                    print("Nothing to delete.")
                    raise SystemExit(0)

                # Show plan before confirming
                if not args.json:
                    print(format_cleanup_plan_human(plan))

                confirmed = getattr(args, "yes", False)
                if not confirmed:
                    try:
                        answer = input(
                            f"Delete {plan['total_items']} item(s) "
                            f"({plan['total_bytes']:,} bytes)? [y/N] "
                        ).strip().lower()
                        confirmed = answer in ("y", "yes")
                    except (EOFError, KeyboardInterrupt):
                        confirmed = False

                if not confirmed:
                    print("Aborted.")
                    raise SystemExit(0)

                # Execute
                plan["dry_run"] = False
                result = execute_cleanup(plan)

                # Audit event
                try:
                    from policy_scout.audit.store import AuditStore
                    from policy_scout.audit.events import AuditEvent, EventType
                    _store = AuditStore()
                    _store.write(AuditEvent(
                        event_type=EventType.DATA_CLEANUP_EXECUTED,
                        summary=(
                            f"Data cleanup executed: target={args.target}, "
                            f"deleted={result['deleted_count']}, "
                            f"failed={result['failed_count']}, "
                            f"freed={result['freed_bytes']} bytes"
                        ),
                        data={
                            "target": args.target,
                            "deleted_count": result["deleted_count"],
                            "failed_count": result["failed_count"],
                            "freed_bytes": result["freed_bytes"],
                        },
                    ))
                except Exception:
                    pass

                if args.json:
                    output = format_cleanup_result_json(result)
                else:
                    output = format_cleanup_result_human(result)
                print(output)
                if result["failed_count"]:
                    raise SystemExit(1)
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
    elif args.subcommand == "watch":
        handle_watch_command(args)
    elif args.subcommand == "intel":
        handle_intel_command(args)
    elif args.subcommand == "serve":
        handle_serve_command(args)
    elif args.subcommand == "canary":
        handle_canary_command(args)
    elif args.subcommand == "sandbox-run":
        handle_sandbox_run_command(args)
    elif args.subcommand == "sandbox-check-prereqs":
        handle_sandbox_prereqs_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli()
