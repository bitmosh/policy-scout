"""audit command handler."""

import json
import sys
import os

from ...audit.store import AuditStore
from ...audit.sqlite_store import SQLiteAuditStore


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
        offset = getattr(args, "offset", 0)
        total_count = sqlite_store.count_events()
        events = sqlite_store.list_recent(limit=args.limit, offset=offset)
        if args.json:
            print(json.dumps({"events": events, "total_count": total_count}, indent=2))
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
        offset = getattr(args, "offset", 0)
        total_count = sqlite_store.count_by_event_type(args.event_type)
        events = sqlite_store.list_by_event_type(args.event_type, limit=args.limit, offset=offset)
        if args.json:
            print(json.dumps({"events": events, "total_count": total_count}, indent=2))
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
        from ...audit.chain_verifier import verify_chain
        from ...audit.events import create_chain_verification_event

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
