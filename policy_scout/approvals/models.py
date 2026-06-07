"""Approval request models."""

from dataclasses import dataclass, field
from typing import Optional
from ..core.ids import generate_id, utcnow_iso, utcnow_plus_hours_iso


@dataclass
class ApprovalRequest:
    """Approval request for command execution."""

    approval_id: str = field(default_factory=lambda: generate_id("appr"))
    request_id: str = ""
    decision_id: str = ""
    created_at: str = field(default_factory=utcnow_iso)
    expires_at: str = field(default_factory=lambda: utcnow_plus_hours_iso(24))
    status: str = "pending"
    actor: Optional[dict] = None
    command: str = ""
    cwd: str = ""
    risk_score: int = 0
    decision: str = ""
    reasons: list = field(default_factory=list)
    recommended_action: str = ""
    scope: str = "once"
    schema_version: int = 1

    def to_dict(self) -> dict:
        return {
            "approval_id": self.approval_id,
            "request_id": self.request_id,
            "decision_id": self.decision_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "actor": self.actor,
            "command": self.command,
            "cwd": self.cwd,
            "risk_score": self.risk_score,
            "decision": self.decision,
            "reasons": self.reasons,
            "recommended_action": self.recommended_action,
            "scope": self.scope,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ApprovalRequest":
        return cls(
            approval_id=data.get("approval_id", ""),
            request_id=data.get("request_id", ""),
            decision_id=data.get("decision_id", ""),
            created_at=data.get("created_at", ""),
            expires_at=data.get("expires_at", ""),
            status=data.get("status", "pending"),
            actor=data.get("actor"),
            command=data.get("command", ""),
            cwd=data.get("cwd", ""),
            risk_score=data.get("risk_score", 0),
            decision=data.get("decision", ""),
            reasons=data.get("reasons", []),
            recommended_action=data.get("recommended_action", ""),
            scope=data.get("scope", "once"),
            schema_version=data.get("schema_version", 1),
        )


class ApprovalStatus:
    """Canonical approval statuses."""

    PENDING = "pending"
    APPROVED_ONCE = "approved_once"
    DENIED_ONCE = "denied_once"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    EXECUTED = "executed"
    FAILED = "failed"


class ApprovalScope:
    """Canonical approval scopes."""

    ONCE = "once"


def can_resolve_approval(
    requesting_actor: Optional[dict], resolver_actor: Optional[dict]
) -> bool:
    """
    Determine if a resolver actor can approve a request from a requesting actor.

    Rules:
    - human resolving human request: allowed
    - human resolving agent request: allowed
    - agent resolving same agent request: denied
    - agent resolving any approval: denied for v0.1
    - unknown/non-human resolver: denied (fail safe)

    Args:
        requesting_actor: The actor who made the approval request (dict with 'type' and 'name')
        resolver_actor: The actor attempting to approve (dict with 'type' and 'name')

    Returns:
        True if resolver can approve, False otherwise
    """
    if not requesting_actor or not resolver_actor:
        # If actor identity is unavailable, fail safe: deny
        return False

    requesting_type = requesting_actor.get("type", "unknown")
    resolver_type = resolver_actor.get("type", "unknown")

    # Non-human resolvers are not allowed to approve in v0.1
    if resolver_type not in ["human", "cli"]:
        return False

    # Human/CLI resolvers can approve human requests (including self-approval for local CLI)
    if requesting_type in ["human", "cli"]:
        return True

    # Human/CLI resolvers can approve agent requests
    if requesting_type in ["agent", "ide", "ci", "mcp", "api", "unknown"]:
        return True

    # Default: deny
    return False
