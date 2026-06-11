"""Audit store interface."""

from typing import Optional
from .jsonl_writer import JSONLWriter
from .sqlite_store import SQLiteAuditStore
from .events import AuditEvent


class AuditStore:
    """Audit event store with dual-write (SQLite primary, JSONL secondary)."""

    def __init__(self, path: Optional[str] = None, enabled: bool = True):
        """Initialize audit store."""
        import sys as _sys

        self.enabled = enabled
        self._sqlite_init_failed = False
        if enabled:
            try:
                self.sqlite_store = SQLiteAuditStore()
            except Exception as e:
                print(
                    f"Warning: Audit store unavailable: {e}",
                    file=_sys.stderr,
                )
                self.sqlite_store = None
                self._sqlite_init_failed = True
            try:
                self.jsonl_writer = JSONLWriter(path)
            except Exception as e:
                print(
                    f"Warning: JSONL writer unavailable: {e}",
                    file=_sys.stderr,
                )
                self.jsonl_writer = None
        else:
            self.sqlite_store = None
            self.jsonl_writer = None

    def write(self, event: AuditEvent, critical: bool = False) -> bool:
        """Write an audit event to both SQLite and JSONL if enabled.

        Args:
            event: The audit event to write
            critical: If True, SQLite write must succeed for operation to proceed

        Returns:
            True if SQLite write succeeded (or critical=False and enabled=False),
            False if SQLite write failed
        """
        if not self.enabled:
            return (
                not critical
            )  # If critical and disabled, fail; if non-critical, succeed

        # If SQLite init failed, treat it as a write failure
        if self._sqlite_init_failed:
            return False if critical else True

        # Write to SQLite (primary)
        sqlite_success = True
        if self.sqlite_store:
            sqlite_success = self.sqlite_store.write_event(event)

        # Write to JSONL (secondary debug/export)
        if self.jsonl_writer:
            self.jsonl_writer.write_event(event)

        # Return success only if SQLite write succeeded
        return sqlite_success

    def write_batch(self, events: list) -> int:
        """Write multiple audit events to both stores if enabled."""
        if not self.enabled:
            return 0

        # Write to SQLite (primary)
        sqlite_count = 0
        if self.sqlite_store:
            sqlite_count = self.sqlite_store.write_events(events)

        # Write to JSONL (secondary debug/export)
        if self.jsonl_writer:
            self.jsonl_writer.write_events(events)

        # Return SQLite count as primary
        return sqlite_count

    def read_all(self) -> list:
        """Read all audit events from JSONL if enabled (for backward compatibility)."""
        if not self.enabled or self.jsonl_writer is None:
            return []
        return self.jsonl_writer.read_events()

    def clear(self):
        """Clear audit events from both stores if enabled."""
        if self.sqlite_store:
            self.sqlite_store.clear()
        if self.jsonl_writer:
            self.jsonl_writer.clear()

    # SQLite query helpers
    def get_event(self, event_id: str):
        """Get a single event by event_id from SQLite."""
        if not self.enabled or self.sqlite_store is None:
            return None
        return self.sqlite_store.get_event(event_id)

    def list_recent(self, limit: int = 50):
        """List recent events from SQLite."""
        if not self.enabled or self.sqlite_store is None:
            return []
        return self.sqlite_store.list_recent(limit)

    def list_by_request_id(self, request_id: str):
        """List events by request_id from SQLite."""
        if not self.enabled or self.sqlite_store is None:
            return []
        return self.sqlite_store.list_by_request_id(request_id)

    def list_by_event_type(self, event_type: str):
        """List events by type from SQLite."""
        if not self.enabled or self.sqlite_store is None:
            return []
        return self.sqlite_store.list_by_event_type(event_type)

    def count_events(self) -> int:
        """Count total events in SQLite."""
        if not self.enabled or self.sqlite_store is None:
            return 0
        return self.sqlite_store.count_events()
