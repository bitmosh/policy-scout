"""preserve and clearance command handlers."""

import json
import sys


def handle_preserve_command(args):
    """Handle preserve command."""
    from pathlib import Path as _Path
    from ...response.preserve import preserve_evidence
    from ...audit.store import AuditStore

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
    from ...response.clearance import run_clearance_check
    from ...audit.store import AuditStore

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
