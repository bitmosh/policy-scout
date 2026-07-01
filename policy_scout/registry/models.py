"""Registry data models."""

from dataclasses import dataclass, field
from typing import Any, Literal, Optional


@dataclass
class RegistryHit:
    """Represents a matched registry entry."""

    registry_name: str
    entry_id: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "registry_name": self.registry_name,
            "entry_id": self.entry_id,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class CommandRegistryEntry:
    """Represents a command registry entry."""

    id: str
    title: str
    description: str = ""
    match: dict[str, Any] = field(default_factory=dict)
    categories: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    default_risk: str = "R3"
    recommended_controls: list[str] = field(default_factory=list)
    version: int = 1
    status: Literal["active", "deprecated", "experimental"] = "active"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "match": self.match,
            "categories": self.categories,
            "capabilities": self.capabilities,
            "default_risk": self.default_risk,
            "recommended_controls": self.recommended_controls,
            "version": self.version,
            "status": self.status,
        }


@dataclass
class PolicyRegistryEntry:
    """Represents a policy registry entry."""

    id: str
    title: str
    priority: int
    match: dict[str, Any] = field(default_factory=dict)
    exclude: dict[str, Any] = field(default_factory=dict)
    decision: Literal[
        "ALLOW",
        "ALLOW_LOGGED",
        "REQUIRE_APPROVAL",
        "SANDBOX_FIRST",
        "DENY",
        "DENY_AND_ALERT",
    ] = "DENY"
    reasons: list[str] = field(default_factory=list)
    recommended_next_action: Optional[str] = None
    version: int = 1
    status: Literal["active", "deprecated", "experimental"] = "active"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "match": self.match,
            "exclude": self.exclude,
            "decision": self.decision,
            "reasons": self.reasons,
            "recommended_next_action": self.recommended_next_action,
            "version": self.version,
            "status": self.status,
        }


@dataclass
class CommandRegistry:
    """Container for command registry entries."""

    version: int = 1
    commands: list[CommandRegistryEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "commands": [cmd.to_dict() for cmd in self.commands],
        }


@dataclass
class PolicyRegistry:
    """Container for policy registry entries."""

    version: int = 1
    policies: list[PolicyRegistryEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "policies": [policy.to_dict() for policy in self.policies],
        }
