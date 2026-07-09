# SPDX-License-Identifier: Apache-2.0
"""sandbox-run and sandbox-check-prereqs command handlers."""

import json
import sys

from ...audit.store import AuditStore


def handle_sandbox_run_command(args) -> None:
    """Run an arbitrary command inside the Linux namespace sandbox."""
    from ...sandbox.general.namespace_sandbox import run_general_sandbox
    from ...sandbox.general.prereqs import check_sandbox_prerequisites
    from ...audit.events import EventType
    from ...audit.store import AuditEvent

    command = args.command
    if not command:
        print("Error: no command specified for sandbox-run", file=sys.stderr)
        sys.exit(1)

    timeout = getattr(args, "timeout", 30)
    allow_network = getattr(args, "allow_network", False)
    emit_audit = not getattr(args, "no_audit", False)
    as_json = getattr(args, "json", False)

    store = AuditStore()

    if emit_audit:
        store.write(AuditEvent(
            event_type=EventType.GENERAL_SANDBOX_STARTED,
            summary=f"Sandbox run started: {command}",
            data={"command": command, "timeout": timeout, "allow_network": allow_network},
        ))

    try:
        report = run_general_sandbox(
            command=command,
            timeout=timeout,
            allow_network=allow_network,
        )
    except Exception as exc:
        print(f"Error: sandbox run failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if emit_audit:
        store.write(AuditEvent(
            event_type=EventType.GENERAL_SANDBOX_COMPLETED,
            summary=f"Sandbox run completed: exit={report.exit_code} findings={len(report.findings)}",
            data=report.to_dict(),
        ))
        for finding in report.findings:
            store.write(AuditEvent(
                event_type=EventType.SANDBOX_BEHAVIOR_FINDING,
                summary=f"[{finding.severity}] {finding.title}",
                data=finding.to_dict(),
            ))

    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Sandbox run: {report.command}")
        print(f"  Exit code: {report.exit_code}")
        if report.timed_out:
            print("  Timed out: yes")
        print(f"  Detection confidence: {report.detection_confidence}")
        print(f"  Findings: {len(report.findings)}")
        for f in report.findings:
            print(f"    [{f.severity.upper()}] {f.title}")
        fs = report.fs_changes
        if any([fs.created, fs.modified, fs.deleted]):
            print(f"  FS changes: +{len(fs.created)} ~{len(fs.modified)} -{len(fs.deleted)}")
        if report.stdout:
            print("\n--- stdout ---")
            print(report.stdout[:2048])
        if report.stderr:
            print("\n--- stderr ---")
            print(report.stderr[:1024])


def handle_sandbox_prereqs_command(args) -> None:
    """Check whether the general sandbox prerequisites are met."""
    from ...sandbox.general.prereqs import check_sandbox_prerequisites

    prereqs = check_sandbox_prerequisites()
    as_json = getattr(args, "json", False)

    if as_json:
        print(json.dumps(prereqs.to_dict(), indent=2))
    else:
        status = "OK" if prereqs.available else "UNAVAILABLE"
        print(f"General sandbox: {status}")
        details = prereqs.details
        print(f"  unshare: {'yes' if details.get('unshare_available') else 'no'}")
        print(f"  user namespaces: {'enabled' if details.get('user_namespaces_enabled') else 'disabled'}")
        print(f"  overlayfs: {'available' if prereqs.overlayfs_available else 'unavailable'}")
        print(f"  strace: {'available' if prereqs.strace_available else 'unavailable'}")
        missing = prereqs.missing()
        if missing:
            print(f"  Missing: {', '.join(missing)}")
            print("  Tip: On Ubuntu/Debian — sudo sysctl kernel.unprivileged_userns_clone=1")
