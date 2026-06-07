"""Executor data models."""

from dataclasses import dataclass, field
from typing import Optional
from ..core.ids import utcnow_iso


@dataclass
class ExecutionResult:
    """Represents command execution result."""

    execution_id: str
    request_id: str
    decision_id: str
    command: str
    cwd: str
    route: str = "direct"
    started_at: str = field(default_factory=utcnow_iso)
    completed_at: Optional[str] = None
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    schema_version: int = 1

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "request_id": self.request_id,
            "decision_id": self.decision_id,
            "command": self.command,
            "cwd": self.cwd,
            "route": self.route,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "schema_version": self.schema_version,
        }
