# SPDX-License-Identifier: Apache-2.0
"""watch command handler."""

import json
import sys


def handle_watch_command(args) -> None:
    """Handle watch start/stop/status/logs subcommands."""
    from ...watch.daemon import (
        start_daemon,
        stop_daemon,
        daemon_status,
        tail_logs,
    )
    from ...watch.fs_watcher import platform_watch_supported

    sub = getattr(args, "watch_subcommand", None)

    if sub == "start":
        supported, reason = platform_watch_supported()
        if not supported:
            msg = f"Watch mode not supported on this platform: {reason}"
            if getattr(args, "json", False):
                print(json.dumps({"ok": False, "error": msg}))
            else:
                print(f"Error: {msg}", file=sys.stderr)
            sys.exit(1)

        result = start_daemon(
            mode=args.mode,
            poll_interval=args.poll_interval,
            foreground=args.foreground,
        )
        if getattr(args, "json", False):
            print(json.dumps(result))
        else:
            if result.get("ok"):
                print(f"Watch daemon started (PID {result.get('pid')})")
            else:
                print(f"Error: {result.get('error')}", file=sys.stderr)
                sys.exit(1)

    elif sub == "stop":
        result = stop_daemon()
        if result.get("ok"):
            print(f"Watch daemon stopped (was PID {result.get('stopped_pid')})")
        else:
            print(f"Error: {result.get('error')}", file=sys.stderr)
            sys.exit(1)

    elif sub == "status":
        status = daemon_status()
        if getattr(args, "json", False):
            print(json.dumps(status))
        else:
            if status.get("running"):
                print(f"Watch daemon running (PID {status.get('pid')})")
            elif status.get("stale"):
                print(f"Watch daemon not running (stale PID file: {status.get('pid')})")
            else:
                print("Watch daemon not running")

    elif sub == "logs":
        lines = tail_logs(n=args.lines)
        if lines:
            print("\n".join(lines))
        else:
            print("No watch daemon log found.")

    else:
        print("Error: No watch subcommand provided (start|stop|status|logs)", file=sys.stderr)
        sys.exit(1)
