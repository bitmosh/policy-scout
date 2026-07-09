# SPDX-License-Identifier: Apache-2.0
"""Report models for Policy Scout."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from ..core.ids import utcnow_iso, utcnow_timestamp


@dataclass
class ScoutReport:
    """A Scout Report explaining a Policy Scout decision, sandbox result, or finding."""

    report_id: str = field(default_factory=lambda: f"report_{utcnow_timestamp()}")
    report_type: str = ""
    title: str = ""
    created_at: str = field(default_factory=utcnow_iso)
    request_id: str = ""
    evaluation_id: Optional[str] = None
    decision_id: Optional[str] = None
    sandbox_id: Optional[str] = None
    findings: List[Dict[str, Any]] = field(default_factory=list)
    audit_event_ids: List[str] = field(default_factory=list)
    markdown_path: str = ""
    json_path: str = ""
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "title": self.title,
            "created_at": self.created_at,
            "request_id": self.request_id,
            "evaluation_id": self.evaluation_id,
            "decision_id": self.decision_id,
            "sandbox_id": self.sandbox_id,
            "findings": self.findings,
            "audit_event_ids": self.audit_event_ids,
            "markdown_path": self.markdown_path,
            "json_path": self.json_path,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScoutReport":
        """Create from dict."""
        return cls(
            report_id=data.get("report_id", ""),
            report_type=data.get("report_type", ""),
            title=data.get("title", ""),
            created_at=data.get("created_at", ""),
            request_id=data.get("request_id", ""),
            evaluation_id=data.get("evaluation_id"),
            decision_id=data.get("decision_id"),
            sandbox_id=data.get("sandbox_id"),
            findings=data.get("findings", []),
            audit_event_ids=data.get("audit_event_ids", []),
            markdown_path=data.get("markdown_path", ""),
            json_path=data.get("json_path", ""),
            schema_version=data.get("schema_version", 1),
        )
