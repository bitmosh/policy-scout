"""Policy decision and risk score models."""

from dataclasses import dataclass, field
from typing import Any, Literal
from .ids import generate_id


def derive_risk_band(risk_score: int) -> Literal["low", "medium", "high", "critical"]:
    """Derive risk band from numeric risk score.

    Mapping:
    - 0-2: low
    - 2-4: medium
    - 5-7: high
    - 8-10: critical
    """
    if risk_score <= 2:
        return "low"
    elif risk_score <= 4:
        return "medium"
    elif risk_score <= 7:
        return "high"
    else:
        return "critical"


@dataclass
class RiskScore:
    """Represents granular risk scoring."""

    risk_id: str = field(default_factory=lambda: generate_id("risk"))
    request_id: str = ""
    risk_score: int = 0  # 0-10
    risk_band: Literal["low", "medium", "high", "critical"] = "low"
    components: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    evidence_strength: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "risk_id": self.risk_id,
            "request_id": self.request_id,
            "risk_score": self.risk_score,
            "risk_band": self.risk_band,
            "components": self.components,
            "confidence": self.confidence,
            "evidence_strength": self.evidence_strength,
            "notes": self.notes,
        }


@dataclass
class PolicyDecision:
    """Represents the final policy decision."""

    decision_id: str = field(default_factory=lambda: generate_id("dec"))
    request_id: str = ""
    decision: Literal[
        "ALLOW",
        "ALLOW_LOGGED",
        "REQUIRE_APPROVAL",
        "SANDBOX_FIRST",
        "DENY",
        "DENY_AND_ALERT",
    ] = "DENY"
    risk_score: int = 0
    confidence: float = 0.0
    category: str = ""
    policy_hits: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    recommended_next_action: str = ""
    override_allowed: bool = True
    requires_audit: bool = True

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "decision": self.decision,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "category": self.category,
            "policy_hits": self.policy_hits,
            "reasons": self.reasons,
            "recommended_next_action": self.recommended_next_action,
            "override_allowed": self.override_allowed,
            "requires_audit": self.requires_audit,
        }
