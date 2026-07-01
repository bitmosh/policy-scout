"""Command request and actor models."""

from dataclasses import dataclass, field
from typing import Any, Literal
import time
from .ids import generate_id


@dataclass
class Actor:
    """Represents who or what requested an action."""
    type: Literal["human", "agent", "ide", "cli", "ci", "unknown"]
    name: str = "unknown"
    trust_level: Literal["trusted_local", "known_tool", "untrusted_agent", "unknown_actor", "ci_actor"] = "unknown_actor"
    source: str = "cli"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "name": self.name,
            "trust_level": self.trust_level,
            "source": self.source,
            "metadata": self.metadata
        }


@dataclass
class CommandRequest:
    """Represents a requested command or action."""
    request_id: str = field(default_factory=lambda: generate_id("req"))
    schema_version: int = 1
    timestamp: int = field(default_factory=lambda: int(time.time()))
    actor: Actor = field(default_factory=lambda: Actor(type="unknown"))
    source: str = "cli"
    command: str = ""
    cwd: str = ""
    declared_intent: str = ""
    mode: Literal["beginner", "balanced", "paranoid", "ci", "incident"] = "balanced"

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "actor": self.actor.to_dict(),
            "source": self.source,
            "command": self.command,
            "cwd": self.cwd,
            "declared_intent": self.declared_intent,
            "mode": self.mode
        }
