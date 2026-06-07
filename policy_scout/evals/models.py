"""Eval case and result models."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from ..core.ids import utcnow_iso


@dataclass
class EvalCase:
    """A single evaluation case."""

    case_id: str
    title: str
    command: str
    actor_type: str = "human"
    mode: str = "balanced"
    expected_decision: Optional[str] = None
    expected_categories: Optional[List[str]] = None
    expected_capabilities: Optional[List[str]] = None
    expected_policy_hits: Optional[List[str]] = None
    expected_registry_hits: Optional[List[str]] = None
    expected_risk_min: Optional[int] = None
    expected_risk_max: Optional[int] = None
    expected_contains_reasons: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "case_id": self.case_id,
            "title": self.title,
            "command": self.command,
            "actor_type": self.actor_type,
            "mode": self.mode,
            "expected_decision": self.expected_decision,
            "expected_categories": self.expected_categories or [],
            "expected_capabilities": self.expected_capabilities or [],
            "expected_policy_hits": self.expected_policy_hits or [],
            "expected_registry_hits": self.expected_registry_hits or [],
            "expected_risk_min": self.expected_risk_min,
            "expected_risk_max": self.expected_risk_max,
            "expected_contains_reasons": self.expected_contains_reasons or [],
            "tags": self.tags or [],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvalCase":
        """Create from dict."""
        return cls(
            case_id=data["case_id"],
            title=data["title"],
            command=data["command"],
            actor_type=data.get("actor_type", "human"),
            mode=data.get("mode", "balanced"),
            expected_decision=data.get("expected_decision"),
            expected_categories=data.get("expected_categories"),
            expected_capabilities=data.get("expected_capabilities"),
            expected_policy_hits=data.get("expected_policy_hits"),
            expected_registry_hits=data.get("expected_registry_hits"),
            expected_risk_min=data.get("expected_risk_min"),
            expected_risk_max=data.get("expected_risk_max"),
            expected_contains_reasons=data.get("expected_contains_reasons"),
            tags=data.get("tags"),
            notes=data.get("notes"),
        )


@dataclass
class EvalResult:
    """Result of evaluating a single case."""

    case_id: str
    passed: bool
    command: str
    expected_decision: Optional[str]
    actual_decision: Optional[str]
    expected_categories: Optional[List[str]]
    actual_categories: Optional[List[str]]
    expected_capabilities: Optional[List[str]]
    actual_capabilities: Optional[List[str]]
    expected_policy_hits: Optional[List[str]]
    actual_policy_hits: Optional[List[str]]
    expected_registry_hits: Optional[List[str]]
    actual_registry_hits: Optional[List[str]]
    expected_risk_range: Optional[tuple]
    actual_risk_score: Optional[int]
    failure_reasons: List[str] = field(default_factory=list)
    execution_time_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "command": self.command,
            "expected_decision": self.expected_decision,
            "actual_decision": self.actual_decision,
            "expected_categories": self.expected_categories or [],
            "actual_categories": self.actual_categories or [],
            "expected_capabilities": self.expected_capabilities or [],
            "actual_capabilities": self.actual_capabilities or [],
            "expected_policy_hits": self.expected_policy_hits or [],
            "actual_policy_hits": self.actual_policy_hits or [],
            "expected_registry_hits": self.expected_registry_hits or [],
            "actual_registry_hits": self.actual_registry_hits or [],
            "expected_risk_min": (
                self.expected_risk_range[0] if self.expected_risk_range else None
            ),
            "expected_risk_max": (
                self.expected_risk_range[1] if self.expected_risk_range else None
            ),
            "actual_risk_score": self.actual_risk_score,
            "failure_reasons": self.failure_reasons,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class EvalSummary:
    """Summary of an eval suite run."""

    total_cases: int
    passed: int
    failed: int
    pass_rate: float
    failed_case_ids: List[str] = field(default_factory=list)
    execution_time_ms: Optional[int] = None
    timestamp: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "failed_case_ids": self.failed_case_ids,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp,
        }
