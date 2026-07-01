"""canary command handler."""

import json
import sys

from ...audit.store import AuditStore


def handle_canary_command(args) -> None:
    """Handle canary subcommands (install, check, remove)."""
    sub = getattr(args, "canary_subcommand", None)

    if sub == "install":
        from ...canary.installer import install_canary
        from ...audit.events import EventType
        from ...audit.store import AuditEvent

        result = install_canary(getattr(args, "path", "."))
        audit = AuditStore()
        if not result["already_existed"]:
            audit.write(AuditEvent(
                event_type=EventType.CANARY_FILE_INSTALLED,
                summary=f"Canary file installed at {result['path']}",
                data=result,
            ))

        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            if result["already_existed"]:
                print(f"Canary already installed: {result['path']}")
                print(f"  Token: {result['token']}")
            else:
                print(f"Canary installed: {result['path']}")
                print(f"  Token: {result['token']}")
                print("  Tip: commit this file to git so it persists across clones.")

    elif sub == "check":
        from ...canary.checker import check_canary_status
        from ...audit.events import EventType
        from ...audit.store import AuditEvent

        status = check_canary_status(getattr(args, "path", "."))
        if status.installed and status.audit_hits:
            AuditStore().write(AuditEvent(
                event_type=EventType.CANARY_AUDIT_HIT_DETECTED,
                summary=f"Canary token {status.token} found in {len(status.audit_hits)} audit events",
                data=status.to_dict(),
            ))

        if getattr(args, "json", False):
            print(json.dumps(status.to_dict(), indent=2))
        else:
            if not status.installed:
                print("Canary not installed. Run: policy-scout canary install")
            else:
                print(f"Canary: {status.path}")
                print(f"  Token: {status.token}")
                hits = status.audit_hits
                if hits:
                    print(f"  Audit hits: {len(hits)}")
                    for h in hits[:5]:
                        print(f"    - [{h.get('event_type', '')}] {h.get('summary', '')}")
                else:
                    print("  Audit hits: none (token has not appeared in audit log)")

    elif sub == "remove":
        from ...canary.installer import remove_canary
        removed = remove_canary(getattr(args, "path", "."))
        if removed:
            print("Canary file removed.")
        else:
            print("No canary file found.")

    else:
        print("Error: No canary subcommand provided (install|check|remove)", file=sys.stderr)
        sys.exit(1)
