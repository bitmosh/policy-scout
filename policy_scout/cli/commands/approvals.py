# SPDX-License-Identifier: Apache-2.0
"""approvals command handler."""

import json
import sys

from ...audit.store import AuditStore
from ...approvals.store import ApprovalStore
from ...approvals.models import ApprovalStatus, can_resolve_approval
from ...audit.events import (
    create_approval_shown_event,
    create_approval_approved_once_event,
    create_approval_denied_once_event,
)


def handle_approvals_command(args):
    """Handle approvals subcommands."""
    approval_store = ApprovalStore()
    audit_store = AuditStore(enabled=True)
    json_output = getattr(args, "json", False)

    if args.approvals_subcommand == "list":
        approvals = approval_store.list_pending()
        if json_output:
            print(json.dumps({"approvals": [a.to_dict() for a in approvals]}))
            return
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
            # Write ApprovalApprovedOnce event
            audit_store.write(
                create_approval_approved_once_event(
                    approval.request_id,
                    approval.approval_id,
                    actor=current_approver,
                )
            )
            if json_output:
                print(json.dumps({"approval_id": args.approval_id, "status": "approved_once"}))
            else:
                print(f"Approved: {args.approval_id}")
        else:
            if json_output:
                print(json.dumps({"error": "Failed to update approval status"}), file=sys.stderr)
            else:
                print("Error: Failed to update approval status", file=sys.stderr)
            sys.exit(1)

    elif args.approvals_subcommand == "deny":
        approval = approval_store.get_by_id(args.approval_id)
        if not approval:
            if json_output:
                print(json.dumps({"error": f"Approval {args.approval_id} not found"}), file=sys.stderr)
            else:
                print(f"Error: Approval {args.approval_id} not found", file=sys.stderr)
            sys.exit(1)

        if approval.status != ApprovalStatus.PENDING:
            if json_output:
                print(json.dumps({"error": f"Approval is not pending (current status: {approval.status})"}), file=sys.stderr)
            else:
                print(
                    f"Error: Approval is not pending (current status: {approval.status})",
                    file=sys.stderr,
                )
            sys.exit(1)

        success = approval_store.update_status(
            args.approval_id, ApprovalStatus.DENIED_ONCE
        )
        if success:
            # Write ApprovalDeniedOnce event
            audit_store.write(
                create_approval_denied_once_event(
                    approval.request_id,
                    approval.approval_id,
                    actor={"type": "human", "name": "cli_user"},
                )
            )
            if json_output:
                print(json.dumps({"approval_id": args.approval_id, "status": "denied_once"}))
            else:
                print(f"Denied: {args.approval_id}")
        else:
            if json_output:
                print(json.dumps({"error": "Failed to update approval status"}), file=sys.stderr)
            else:
                print("Error: Failed to update approval status", file=sys.stderr)
            sys.exit(1)

    elif args.approvals_subcommand == "set-timeout":
        from ...core.config import write_setting
        hours = args.hours
        if hours < 1 or hours > 8760:
            msg = "Timeout must be between 1 and 8760 hours (1 year)"
            if json_output:
                print(json.dumps({"error": msg}), file=sys.stderr)
            else:
                print(f"Error: {msg}", file=sys.stderr)
            sys.exit(1)
        write_setting("approval_timeout_hours", hours)
        if json_output:
            print(json.dumps({"ok": True, "approval_timeout_hours": hours}))
        else:
            print(f"Approval timeout set to {hours} hour(s).")

    else:
        print("Error: Unknown approvals subcommand", file=sys.stderr)
        sys.exit(1)
