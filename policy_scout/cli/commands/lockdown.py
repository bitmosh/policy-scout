"""lockdown command handler."""

import json
import sys


def handle_lockdown_command(args):
    """Handle lockdown subcommands."""
    from ...response.lockdown import (
        activate_lockdown,
        deactivate_lockdown,
        is_lockdown_active,
        get_lockdown_reason,
    )
    from ...audit.store import AuditStore

    audit_store = AuditStore()

    if args.lockdown_subcommand == "on":
        reason = getattr(args, "reason", "")
        json_out = getattr(args, "json", False)
        if is_lockdown_active():
            if json_out:
                print(json.dumps({"ok": False, "already_active": True}))
            else:
                print("Lockdown is already active.")
            return
        success = activate_lockdown(reason=reason, audit_store=audit_store)
        if success:
            if json_out:
                print(json.dumps({"ok": True, "active": True, "reason": reason}))
            else:
                print("Lockdown activated. All non-read operations will be DENIED.")
                if reason:
                    print(f"Reason: {reason}")
        else:
            if json_out:
                print(json.dumps({"ok": False, "error": "Failed to activate lockdown"}))
            else:
                print("Error: Failed to activate lockdown.", file=sys.stderr)
            sys.exit(1)

    elif args.lockdown_subcommand == "off":
        json_out = getattr(args, "json", False)
        if not is_lockdown_active():
            if json_out:
                print(json.dumps({"ok": False, "already_inactive": True}))
            else:
                print("Lockdown is not active.")
            return
        success = deactivate_lockdown(cleared_by="cli", audit_store=audit_store)
        if success:
            if json_out:
                print(json.dumps({"ok": True, "active": False}))
            else:
                print("Lockdown deactivated. Normal policy evaluation restored.")
        else:
            if json_out:
                print(json.dumps({"ok": False, "error": "Failed to deactivate lockdown"}))
            else:
                print("Error: Failed to deactivate lockdown.", file=sys.stderr)
            sys.exit(1)

    elif args.lockdown_subcommand == "status":
        active = is_lockdown_active()
        reason = get_lockdown_reason() if active else None
        if getattr(args, "json", False):
            print(json.dumps({"active": active, "reason": reason}))
        elif active:
            print("Status: LOCKDOWN ACTIVE")
            if reason:
                print(f"Reason: {reason}")
        else:
            print("Status: Lockdown inactive (normal operation)")

    else:
        print("Error: No lockdown subcommand provided", file=sys.stderr)
        sys.exit(1)
