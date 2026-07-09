# SPDX-License-Identifier: Apache-2.0
"""Sweep models."""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from ..core.ids import utcnow_iso, utcnow_timestamp


@dataclass
class Finding:
    """Represents a sweep finding."""

    finding_id: str = field(default_factory=lambda: f"find_{utcnow_timestamp()}")
    sweep_id: str = ""
    severity: str = "info"  # info, low, medium, high, critical
    confidence: str = "moderate"  # low, moderate, high, confirmed
    category: str = ""  # suspicious_lifecycle_script, secret_harvesting_pattern, etc.
    title: str = ""
    location: str = ""
    evidence_ref: str = ""
    why_it_matters: str = ""
    recommended_action: str = ""
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "finding_id": self.finding_id,
            "sweep_id": self.sweep_id,
            "severity": self.severity,
            "confidence": self.confidence,
            "category": self.category,
            "title": self.title,
            "location": self.location,
            "evidence_ref": self.evidence_ref,
            "why_it_matters": self.why_it_matters,
            "recommended_action": self.recommended_action,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finding":
        """Create from dictionary."""
        return cls(
            finding_id=data.get("finding_id", ""),
            sweep_id=data.get("sweep_id", ""),
            severity=data.get("severity", "info"),
            confidence=data.get("confidence", "moderate"),
            category=data.get("category", ""),
            title=data.get("title", ""),
            location=data.get("location", ""),
            evidence_ref=data.get("evidence_ref", ""),
            why_it_matters=data.get("why_it_matters", ""),
            recommended_action=data.get("recommended_action", ""),
            schema_version=data.get("schema_version", 1),
        )


@dataclass
class SweepResult:
    """Represents a sweep result."""

    sweep_id: str = field(default_factory=lambda: f"sweep_{utcnow_timestamp()}")
    sweep_type: str = "project"  # project, quick_system, sandbox, deep
    started_at: str = field(default_factory=utcnow_iso)
    completed_at: str = ""
    project_root: str = ""
    platform: str = ""  # linux, darwin, windows, unknown
    findings_count: Dict[str, int] = field(
        default_factory=lambda: {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
    )
    findings: List[Finding] = field(default_factory=list)
    could_not_verify: List[str] = field(default_factory=list)
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sweep_id": self.sweep_id,
            "sweep_type": self.sweep_type,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "project_root": self.project_root,
            "platform": self.platform,
            "findings_count": self.findings_count,
            "findings": [f.to_dict() for f in self.findings],
            "could_not_verify": self.could_not_verify,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SweepResult":
        """Create from dictionary."""
        findings = [Finding.from_dict(f) for f in data.get("findings", [])]
        return cls(
            sweep_id=data.get("sweep_id", ""),
            sweep_type=data.get("sweep_type", "project"),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            project_root=data.get("project_root", ""),
            platform=data.get("platform", ""),
            findings_count=data.get(
                "findings_count",
                {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "info": 0,
                },
            ),
            findings=findings,
            could_not_verify=data.get("could_not_verify", []),
            schema_version=data.get("schema_version", 1),
        )

    def add_finding(self, finding: Finding) -> None:
        """Add a finding and update counts."""
        finding.sweep_id = self.sweep_id
        self.findings.append(finding)
        self.findings_count[finding.severity] = (
            self.findings_count.get(finding.severity, 0) + 1
        )
