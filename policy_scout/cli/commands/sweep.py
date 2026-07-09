# SPDX-License-Identifier: Apache-2.0
"""sweep command handlers."""

import json
import sys
import os

from ...audit.store import AuditStore
from ...audit.redaction import redact_dict
from ...audit.events import (
    create_sweep_started_event,
    create_sweep_completed_event,
    create_sweep_error_event,
    create_scout_report_generated_event,
)
from ...sweep.engine import run_project_sweep
from ...sweep.quick_engine import run_quick_system_sweep
from ...core.ids import generate_id
from ...reports.sweep_report import generate_sweep_report


def handle_sweep_project_command(
    json_output: bool = False,
    audit_enabled: bool = True,
    project_root: str = None,
):
    """Handle sweep project command."""
    import time
    from ...core.ids import generate_id

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
    from ...core.ids import generate_id

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
