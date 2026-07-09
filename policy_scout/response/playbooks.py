# SPDX-License-Identifier: Apache-2.0
"""Incident response playbook loader and finding enrichment."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

_PLAYBOOKS_PATH = Path(__file__).parent.parent / "data" / "playbooks.yaml"

_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


@dataclass
class Playbook:
    """A single incident response playbook."""

    id: str
    categories: list
    severity_threshold: str
    title: str
    summary: str
    immediate_actions: list = field(default_factory=list)
    investigation_steps: list = field(default_factory=list)
    containment: list = field(default_factory=list)
    escalation_criteria: list = field(default_factory=list)

    def matches(self, category: str, severity: str) -> bool:
        """Return True if this playbook applies to the given category/severity."""
        if category not in self.categories:
            return False
        finding_level = _SEVERITY_ORDER.get(severity, 0)
        threshold_level = _SEVERITY_ORDER.get(self.severity_threshold, 0)
        return finding_level >= threshold_level

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "immediate_actions": self.immediate_actions,
            "investigation_steps": self.investigation_steps,
            "containment": self.containment,
            "escalation_criteria": self.escalation_criteria,
        }


class PlaybookRegistry:
    """Registry of loaded playbooks."""

    def __init__(self, playbooks: list[Playbook]):
        self._playbooks = playbooks

    def find(self, category: str, severity: str) -> list[Playbook]:
        """Return playbooks that match the given category and severity."""
        return [p for p in self._playbooks if p.matches(category, severity)]

    def __len__(self) -> int:
        return len(self._playbooks)


def load_playbooks(path: Path = _PLAYBOOKS_PATH) -> PlaybookRegistry:
    """Load playbooks from YAML file. Returns empty registry on failure."""
    if yaml is None:
        return PlaybookRegistry([])

    if not path.exists():
        return PlaybookRegistry([])

    try:
        data = yaml.safe_load(path.read_text())
        raw_playbooks = data.get("playbooks", [])
        playbooks = []
        for raw in raw_playbooks:
            try:
                playbooks.append(
                    Playbook(
                        id=raw["id"],
                        categories=raw.get("categories", []),
                        severity_threshold=raw.get("severity_threshold", "high"),
                        title=raw["title"],
                        summary=raw["summary"],
                        immediate_actions=raw.get("immediate_actions", []),
                        investigation_steps=raw.get("investigation_steps", []),
                        containment=raw.get("containment", []),
                        escalation_criteria=raw.get("escalation_criteria", []),
                    )
                )
            except (KeyError, TypeError):
                pass
        return PlaybookRegistry(playbooks)
    except Exception as e:
        print(f"Warning: Failed to load playbooks: {e}", file=sys.stderr)
        return PlaybookRegistry([])


def enrich_report_findings(
    findings: list[dict], registry: PlaybookRegistry | None = None
) -> list[dict]:
    """Attach matching response playbooks to critical/high severity findings.

    Modifies finding dicts in-place by adding a 'response_playbook' key.
    Returns the (modified) findings list.
    """
    if registry is None:
        registry = load_playbooks()

    for finding in findings:
        severity = finding.get("severity", "info")
        if _SEVERITY_ORDER.get(severity, 0) < _SEVERITY_ORDER["high"]:
            continue

        category = finding.get("category", "")
        matches = registry.find(category, severity)
        if matches:
            finding["response_playbook"] = matches[0].to_dict()

    return findings
