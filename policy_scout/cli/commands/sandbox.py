# SPDX-License-Identifier: Apache-2.0
"""sandbox and sandbox_migrate command handlers."""

import json
import sys
import os

from ...audit.store import AuditStore
from ...audit.events import (
    create_sandbox_requested_event,
    create_sandbox_workspace_created_event,
    create_sandbox_install_started_event,
    create_sandbox_install_completed_event,
    create_lifecycle_scripts_inspected_event,
    create_sandbox_result_written_event,
    create_sandbox_error_event,
    create_scout_report_generated_event,
    create_sandbox_migration_requested_event,
    create_sandbox_migration_planned_event,
    create_sandbox_migration_started_event,
    create_sandbox_migration_completed_event,
    create_sandbox_migration_blocked_event,
)
from ...sandbox.models import SandboxResult
from ...sandbox.temp_workspace import create_sandbox_workspace
from ...sandbox.package_files import copy_package_files, create_minimal_package_json
from ...sandbox.lifecycle_inspector import inspect_lifecycle_scripts
from ...sandbox.diff import take_file_snapshot, capture_manifest_diffs
from ...sandbox.result_writer import write_sandbox_result
from ...sandbox.migration import execute_migration, save_migration_result
from ...sandbox.package_manager import detect_package_manager, is_package_manager_available
from ...sandbox.runner import run_package_manager_install
from ...core.ids import generate_id
from ...reports.sandbox_report import generate_sandbox_report


def handle_sandbox_command(
    command: str,
    json_output: bool = False,
    audit_enabled: bool = True,
):
    """Handle sandbox command."""
    from pathlib import Path
    from ...core.ids import utcnow_iso

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
    before_snapshot = take_file_snapshot(workspace, package_manager)

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
    after_snapshot = take_file_snapshot(workspace, package_manager)

    # Capture diffs
    manifest_changed, lockfile_changed, diffs = capture_manifest_diffs(
        before_snapshot, after_snapshot, package_manager
    )

    # Inspect lifecycle scripts
    lifecycle_scripts = inspect_lifecycle_scripts(workspace)

    if audit_enabled:
        audit_store.write(
            create_lifecycle_scripts_inspected_event(
                request_id, sandbox_id, len(lifecycle_scripts)
            )
        )

    # Supply chain analysis on lifecycle scripts
    supply_chain_findings = []
    try:
        from ...supply_chain import analyze_lifecycle_scripts
        from ...audit.events import EventType
        from ...audit.store import AuditEvent
        supply_chain_findings = analyze_lifecycle_scripts(lifecycle_scripts, project_root=Path.cwd())
        if audit_enabled:
            audit_store.write(AuditEvent(
                event_type=EventType.SUPPLY_CHAIN_ANALYSIS_COMPLETED,
                summary=(
                    f"Supply chain analysis: {len(lifecycle_scripts)} scripts, "
                    f"{len(supply_chain_findings)} finding(s)"
                ),
                data={
                    "sandbox_id": sandbox_id,
                    "scripts_analyzed": len(lifecycle_scripts),
                    "finding_count": len(supply_chain_findings),
                },
            ))
    except Exception:
        pass

    # Transitive dependency analysis (after successful install)
    transitive_findings = []
    if exit_code == 0:
        try:
            from ...supply_chain.transitive import run_list_for_pm, analyze_tree
            from ...intel.adapter import build_default_chain
            pm_tree = run_list_for_pm(package_manager, workspace)
            if pm_tree is not None:
                intel_chain = build_default_chain(remote=False)
                tree_result = analyze_tree(pm_tree, ecosystem="npm", intel_adapter=intel_chain)
                transitive_findings = tree_result.findings
        except Exception:
            pass

    # Build findings
    findings = []
    if skipped_files:
        findings.append(
            {
                "type": "warning",
                "message": f"Skipped files with token-like content: {', '.join(skipped_files)}",
            }
        )
    findings.extend(supply_chain_findings)
    findings.extend(transitive_findings)

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
    from ...sandbox.temp_workspace import get_sandbox_root
    from ...core.ids import generate_id

    request_id = generate_id("req")

    # Initialize audit store
    audit_store = AuditStore()

    # Load sandbox result
    sandbox_root = get_sandbox_root()
    sandbox_result_path = sandbox_root.parent / "results" / f"{sandbox_id}.json"

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
    from ...sandbox.migration import plan_migration

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
