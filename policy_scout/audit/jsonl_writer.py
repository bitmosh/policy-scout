"""JSONL audit writer."""

import json
import os
from pathlib import Path
from typing import Optional
from .events import AuditEvent
from .redaction import redact_dict


class JSONLWriter:
    """Writes audit events to a JSONL file."""

    def __init__(self, path: Optional[Path] = None):
        """Initialize writer with audit file path."""
        if path is None:
            # Default to ~/.local/share/policy-scout/audit.jsonl
            path = Path.home() / ".local" / "share" / "policy-scout" / "audit.jsonl"
        
        # Support environment variable override
        env_path = os.environ.get("POLICY_SCOUT_AUDIT_PATH")
        if env_path:
            path = Path(env_path)
        
        self.path = path
        self._ensure_directory()

    def _ensure_directory(self):
        """Ensure the audit directory exists."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_event(self, event: AuditEvent) -> bool:
        """Write a single audit event to the JSONL file."""
        try:
            # Redact sensitive data before writing
            event_data = event.to_dict()
            redacted_data = redact_dict(event_data)
            
            # Append to file
            with open(self.path, "a") as f:
                f.write(json.dumps(redacted_data) + "\n")
            
            return True
        except Exception as e:
            # Log error but don't crash
            print(f"Warning: Failed to write audit event: {e}", file=__import__("sys").stderr)
            return False

    def write_events(self, events: list) -> int:
        """Write multiple audit events to the JSONL file."""
        success_count = 0
        for event in events:
            if self.write_event(event):
                success_count += 1
        return success_count

    def read_events(self) -> list:
        """Read all events from the JSONL file."""
        events = []
        if not self.path.exists():
            return events
        
        try:
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except Exception as e:
            print(f"Warning: Failed to read audit events: {e}", file=__import__("sys").stderr)
        
        return events

    def clear(self):
        """Clear the audit file."""
        if self.path.exists():
            self.path.unlink()
