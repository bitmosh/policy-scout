"""SQLite audit store for queryable local audit records."""

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from ..core.ids import utcnow_iso
from .events import AuditEvent
from .redaction import redact_dict

Append = None  # type: ignore[assignment]
FossicStore = None  # type: ignore[assignment]
FossicEventId = None  # type: ignore[assignment]
_FOSSIC_AVAILABLE = False
try:
    from fossic import Append, EventId as FossicEventId, Store as FossicStore  # type: ignore[assignment]
    _FOSSIC_AVAILABLE = True
except ImportError:
    pass


class SQLiteAuditStore:
    """SQLite-based audit event store with query helpers."""

    def __init__(self, path: Optional[str] = None, fossic_path: Optional[str] = None):
        """Initialize SQLite audit store."""
        if path is None:
            # Default to ~/.local/share/policy-scout/audit.db
            path = str(Path.home() / ".local" / "share" / "policy-scout" / "audit.db")

        # Support environment variable override
        env_path = os.environ.get("POLICY_SCOUT_AUDIT_DB_PATH")
        if env_path:
            path = env_path

        self.path = path
        self._ensure_directory()
        self._init_db()
        self._fossic: Optional[Any] = None
        self._init_fossic(fossic_path)

    def _ensure_directory(self):
        """Ensure the audit directory exists."""
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.path) as conn:
            # WAL mode: better read concurrency and crash safety.
            # Best-effort: silently skipped on read-only databases.
            try:
                conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError:
                pass

            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    request_id TEXT,
                    actor_type TEXT,
                    actor_name TEXT,
                    summary TEXT,
                    data_json TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    decision_id TEXT,
                    approval_id TEXT,
                    sandbox_id TEXT,
                    sweep_id TEXT,
                    report_id TEXT,
                    execution_id TEXT
                )
            """)

            # Tamper prevention: block UPDATE and DELETE on committed rows.
            # The only legitimate way to clear is drop+recreate (see clear()).
            # Silently skipped on read-only databases; warns on any other failure.
            try:
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS prevent_audit_update
                    BEFORE UPDATE ON audit_events
                    BEGIN
                        SELECT RAISE(ABORT, 'Audit records are immutable');
                    END
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
                    BEFORE DELETE ON audit_events
                    BEGIN
                        SELECT RAISE(ABORT, 'Audit records are immutable');
                    END
                """)
            except sqlite3.OperationalError as exc:
                if "read" not in str(exc).lower():
                    print(
                        f"Warning: audit tamper-prevention triggers could not be created: {exc}",
                        file=sys.stderr,
                    )

            # Create indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_request_id ON audit_events(request_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)")
            conn.commit()

    def _init_fossic(self, fossic_path: Optional[str] = None) -> None:
        """Open the fossic store if fossic-py is available."""
        if not _FOSSIC_AVAILABLE:
            return
        if fossic_path is None:
            fossic_path = str(Path.home() / ".local" / "share" / "policy-scout" / "fossic.db")
        env_path = os.environ.get("POLICY_SCOUT_FOSSIC_DB_PATH")
        if env_path:
            fossic_path = env_path
        try:
            Path(fossic_path).parent.mkdir(parents=True, exist_ok=True)
            self._fossic = FossicStore.open(fossic_path)
        except Exception as e:
            print(f"Warning: Failed to open fossic store, audit events will not be emitted to fossic: {e}", file=sys.stderr)

    def _emit_to_fossic(self, redacted_data: Dict[str, Any]) -> None:
        """Emit a redacted audit event to the fossic store (best-effort, non-fatal)."""
        if self._fossic is None:
            return
        event_type = redacted_data.get("event_type", "")
        data = redacted_data.get("data") or {}

        # Route to correct stream
        request_id = redacted_data.get("request_id")
        if event_type in ("LockdownActivated", "LockdownDeactivated",
                          "WatchDaemonStarted", "WatchDaemonStopped"):
            stream_id = "policy-scout/posture"
        elif request_id:
            stream_id = f"policy-scout/audit/{request_id}"
        else:
            return  # non-posture event without request_id: no valid stream

        # Build indexed_tags
        indexed_tags: Dict[str, Any] = {"source_store": "policy-scout"}
        if request_id:
            indexed_tags["request_id"] = request_id
        if event_type in ("LockdownActivated", "LockdownDeactivated"):
            reason = data.get("reason")
            if reason:
                indexed_tags["reason"] = reason
        if event_type in ("ApprovalRequested", "ApprovalApprovedOnce",
                          "ApprovalDeniedOnce", "ApprovalExpired"):
            approval_id = data.get("approval_id")
            if approval_id:
                indexed_tags["approval_id"] = approval_id
        if event_type == "ApprovalRequested":
            risk_band = data.get("risk_band")
            if risk_band:
                indexed_tags["risk_band"] = risk_band
        if event_type in ("DecisionIssued", "CommandRequested"):
            for field in ("risk_band", "decision"):
                val = data.get(field)
                if val:
                    indexed_tags[field] = val

        # causation_id: cross-project link to Cerebra's ActionProposed (case-2 chain)
        causation_id = None
        upstream = data.get("upstream_causation_id")
        if upstream and FossicEventId is not None:
            try:
                causation_id = FossicEventId.from_hex(upstream)
            except Exception:
                pass

        try:
            self._fossic.declare_stream(stream_id, declared_by="policy-scout")
            self._fossic.append(Append(
                stream_id=stream_id,
                event_type=event_type,
                payload=data,
                external_id=redacted_data["event_id"],
                causation_id=causation_id,
                indexed_tags=indexed_tags,
            ))
        except Exception as e:
            print(f"Warning: Failed to emit audit event to fossic: {e}",
                  file=sys.stderr)

    def write_event(self, event: AuditEvent) -> bool:
        """Write a single audit event to SQLite."""
        try:
            # Redact sensitive data before writing
            event_data = event.to_dict()
            redacted_data = redact_dict(event_data)
            
            # Extract optional IDs from data if present
            decision_id = redacted_data.get("data", {}).get("decision_id")
            approval_id = redacted_data.get("data", {}).get("approval_id")
            sandbox_id = redacted_data.get("data", {}).get("sandbox_id")
            sweep_id = redacted_data.get("data", {}).get("sweep_id")
            report_id = redacted_data.get("data", {}).get("report_id")
            execution_id = redacted_data.get("data", {}).get("execution_id")
            
            # Extract actor info
            actor = redacted_data.get("actor", {})
            actor_type = actor.get("type") if actor else None
            actor_name = actor.get("name") if actor else None
            
            with sqlite3.connect(self.path) as conn:
                conn.execute(
                    """
                    INSERT INTO audit_events (
                        event_id, event_type, timestamp, request_id,
                        actor_type, actor_name, summary, data_json,
                        schema_version, created_at,
                        decision_id, approval_id, sandbox_id, sweep_id,
                        report_id, execution_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        redacted_data["event_id"],
                        redacted_data["event_type"],
                        redacted_data["timestamp"],
                        redacted_data["request_id"],
                        actor_type,
                        actor_name,
                        redacted_data["summary"],
                        json.dumps(redacted_data["data"]),
                        redacted_data["schema_version"],
                        utcnow_iso(),
                        decision_id,
                        approval_id,
                        sandbox_id,
                        sweep_id,
                        report_id,
                        execution_id,
                    ),
                )
                conn.commit()

            self._emit_to_fossic(redacted_data)
            return True
        except Exception as e:
            print(f"Warning: Failed to write audit event to SQLite: {e}", file=sys.stderr)
            return False

    def write_events(self, events: List[AuditEvent]) -> int:
        """Write multiple audit events to SQLite."""
        success_count = 0
        for event in events:
            if self.write_event(event):
                success_count += 1
        return success_count

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get a single event by event_id."""
        try:
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM audit_events WHERE event_id = ?",
                    (event_id,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            print(f"Warning: Failed to get event: {e}", file=sys.stderr)
            return None

    def list_recent(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List recent events ordered by timestamp descending."""
        try:
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Warning: Failed to list recent events: {e}", file=sys.stderr)
            return []

    def list_by_request_id(self, request_id: str) -> List[Dict[str, Any]]:
        """List all events for a specific request_id."""
        try:
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM audit_events WHERE request_id = ? ORDER BY timestamp ASC",
                    (request_id,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Warning: Failed to list events by request_id: {e}", file=sys.stderr)
            return []

    def list_by_event_type(self, event_type: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List events of a specific type with pagination."""
        try:
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM audit_events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (event_type, limit, offset)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Warning: Failed to list events by type: {e}", file=sys.stderr)
            return []

    def count_by_event_type(self, event_type: str) -> int:
        """Count events of a specific type."""
        try:
            with sqlite3.connect(self.path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM audit_events WHERE event_type = ?",
                    (event_type,)
                )
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Warning: Failed to count events by type: {e}", file=sys.stderr)
            return 0

    def count_events(self) -> int:
        """Count total events in the store."""
        try:
            with sqlite3.connect(self.path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Warning: Failed to count events: {e}", file=sys.stderr)
            return 0

    def clear(self):
        """Clear all audit events by dropping and recreating the table.

        Uses drop+recreate rather than DELETE to work around the immutability
        triggers that block row-level deletion. Intended for testing only.
        """
        try:
            with sqlite3.connect(self.path) as conn:
                conn.execute("DROP TABLE IF EXISTS audit_events")
                conn.commit()
            self._init_db()
        except Exception as e:
            print(f"Warning: Failed to clear audit events: {e}", file=sys.stderr)
