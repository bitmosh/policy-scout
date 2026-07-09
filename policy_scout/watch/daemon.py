# SPDX-License-Identifier: Apache-2.0
"""Watch daemon — PID file lifecycle, main event loop, heartbeat."""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

_PID_DIR = Path.home() / ".policy-scout"
_PID_FILE = _PID_DIR / "watch.pid"
_LOG_FILE = _PID_DIR / "watch.log"
_HEARTBEAT_INTERVAL = 60  # seconds


# ── PID file helpers ──────────────────────────────────────────────────────────


def _ensure_pid_dir() -> None:
    _PID_DIR.mkdir(parents=True, exist_ok=True)


def _write_pid(pid: int) -> None:
    _ensure_pid_dir()
    _PID_FILE.write_text(str(pid))


def _read_pid() -> Optional[int]:
    try:
        return int(_PID_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def _clear_pid() -> None:
    try:
        _PID_FILE.unlink()
    except FileNotFoundError:
        pass


def _pid_is_alive(pid: int) -> bool:
    """Return True if a process with this PID exists and is alive."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


# ── Log helpers ───────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"[{ts}] {msg}\n"
    _ensure_pid_dir()
    with open(_LOG_FILE, "a") as f:
        f.write(line)
    print(line, end="", file=sys.stderr)


def tail_logs(n: int = 50) -> list[str]:
    """Return the last n lines from the daemon log."""
    try:
        lines = _LOG_FILE.read_text().splitlines()
        return lines[-n:]
    except FileNotFoundError:
        return []


# ── Daemon status ─────────────────────────────────────────────────────────────


def daemon_status() -> dict:
    """Return a status dict for `watch status`."""
    pid = _read_pid()
    if pid is None:
        return {"running": False, "pid": None, "pid_file": str(_PID_FILE)}
    if _pid_is_alive(pid):
        return {"running": True, "pid": pid, "pid_file": str(_PID_FILE)}
    # Stale PID file
    return {"running": False, "pid": pid, "stale": True, "pid_file": str(_PID_FILE)}


# ── Daemon start/stop ─────────────────────────────────────────────────────────


def start_daemon(mode: str = "both", poll_interval: float = 2.0, foreground: bool = False) -> dict:
    """Fork and start the watch daemon. Returns immediately in the parent."""
    existing = _read_pid()
    if existing and _pid_is_alive(existing):
        return {"ok": False, "error": f"Watch daemon already running (PID {existing})"}

    if foreground:
        _run_daemon_loop(mode=mode, poll_interval=poll_interval)
        return {"ok": True, "pid": os.getpid()}

    pid = os.fork()
    if pid > 0:
        # Parent: wait briefly and confirm child started
        time.sleep(0.2)
        return {"ok": True, "pid": pid}

    # Child process: become a daemon
    os.setsid()
    _write_pid(os.getpid())
    _run_daemon_loop(mode=mode, poll_interval=poll_interval)
    sys.exit(0)


def stop_daemon() -> dict:
    """Send SIGTERM to the daemon, wait for it to exit."""
    pid = _read_pid()
    if pid is None:
        return {"ok": False, "error": "No PID file found — is the daemon running?"}
    if not _pid_is_alive(pid):
        _clear_pid()
        return {"ok": False, "error": f"PID {pid} not alive (stale PID file cleared)"}
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(30):
            time.sleep(0.2)
            if not _pid_is_alive(pid):
                _clear_pid()
                return {"ok": True, "stopped_pid": pid}
        return {"ok": False, "error": f"PID {pid} did not exit within 6 seconds"}
    except PermissionError:
        return {"ok": False, "error": f"No permission to signal PID {pid}"}


# ── Main loop ─────────────────────────────────────────────────────────────────


def _run_daemon_loop(mode: str = "both", poll_interval: float = 2.0) -> None:
    """Main event loop. Runs until SIGTERM."""
    from .watch_config import load_watch_config
    from .fs_watcher import make_watcher
    from .event_router import EventRouter

    _log("Watch daemon starting")

    config = load_watch_config()
    paths = config.all_paths(mode=mode)
    if not paths:
        _log("No watch paths configured — exiting")
        return

    audit_store = _try_open_audit_store()
    router = EventRouter(config=config, audit_store=audit_store)

    _emit_lifecycle_event("started", audit_store)

    _log(f"Watching {len(paths)} path(s) [mode={mode}]")
    for p in paths:
        _log(f"  + {p}")

    _stopped = False

    def _handle_sigterm(_signum: int, _frame: object) -> None:
        nonlocal _stopped
        _stopped = True

    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    watcher = make_watcher(paths, poll_interval=poll_interval)
    last_heartbeat = time.monotonic()

    try:
        for event in watcher.watch():
            if _stopped:
                break

            findings = router.route(event)
            if findings:
                top = findings[0]
                _log(f"TRIGGER [{top.severity}] {event.event_type} {event.path}")

            now = time.monotonic()
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL:
                _emit_lifecycle_event("heartbeat", audit_store)
                last_heartbeat = now

    finally:
        watcher.stop()
        _emit_lifecycle_event("stopped", audit_store)
        _clear_pid()
        _log("Watch daemon stopped")


def _try_open_audit_store():  # type: ignore[return]
    """Open the audit store if available; return None if it fails."""
    try:
        from ..audit.sqlite_store import SQLiteAuditStore
        return SQLiteAuditStore()
    except Exception:
        return None


def _emit_lifecycle_event(phase: str, audit_store: object) -> None:
    """Emit WatchDaemonStarted / WatchDaemonStopped / WatchDaemonHeartbeat."""
    if audit_store is None:
        return
    try:
        from ..audit.events import AuditEvent, EventType
        from ..core.ids import generate_id

        type_map = {
            "started": EventType.WATCH_DAEMON_STARTED,
            "stopped": EventType.WATCH_DAEMON_STOPPED,
            "heartbeat": EventType.WATCH_DAEMON_HEARTBEAT,
        }
        event_type = type_map.get(phase, EventType.WATCH_DAEMON_HEARTBEAT)
        ae = AuditEvent(
            event_type=event_type,
            request_id=generate_id("req"),
            actor={"type": "watch_daemon", "name": "policy-scout-watch"},
            summary=f"Watch daemon {phase}",
            data={"pid": os.getpid(), "phase": phase},
        )
        audit_store.store(ae)  # type: ignore[union-attr]
    except Exception:
        pass
