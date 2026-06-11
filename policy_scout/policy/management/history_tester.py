"""Policy history tester — replay audit decisions against current or candidate policy."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .simulator import simulate


@dataclass
class HistoryTestCase:
    """A single historical decision compared against the simulated decision."""

    event_id: str
    request_id: str
    timestamp: str
    command: str
    original_decision: str
    simulated_decision: str
    changed: bool
    matched_rule: Optional[str] = None
    direction: Optional[str] = None  # "tightened" | "loosened" | "unchanged"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "command": self.command,
            "original_decision": self.original_decision,
            "simulated_decision": self.simulated_decision,
            "changed": self.changed,
            "matched_rule": self.matched_rule,
            "direction": self.direction,
        }


@dataclass
class HistoryTestResult:
    """Aggregated result of a history test run."""

    days: int
    total: int
    changed: int
    unchanged: int
    tightened: int          # decisions became MORE restrictive
    loosened: int           # decisions became LESS restrictive
    skipped: int            # events without recoverable command string
    changed_cases: list = field(default_factory=list)   # list[HistoryTestCase]

    @property
    def change_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.changed / self.total

    def to_dict(self) -> dict:
        return {
            "days": self.days,
            "total": self.total,
            "changed": self.changed,
            "unchanged": self.unchanged,
            "tightened": self.tightened,
            "loosened": self.loosened,
            "skipped": self.skipped,
            "change_rate": round(self.change_rate, 4),
            "changed_cases": [c.to_dict() for c in self.changed_cases],
        }


# Strictness ordering for computing direction.
_DECISION_STRICTNESS = {
    "ALLOW": 0,
    "ALLOW_LOGGED": 1,
    "REQUIRE_APPROVAL": 2,
    "SANDBOX_FIRST": 3,
    "DENY": 4,
    "DENY_AND_ALERT": 5,
}


def _decision_direction(original: str, simulated: str) -> str:
    orig_level = _DECISION_STRICTNESS.get(original, -1)
    sim_level = _DECISION_STRICTNESS.get(simulated, -1)
    if sim_level > orig_level:
        return "tightened"
    if sim_level < orig_level:
        return "loosened"
    return "unchanged"


def test_against_history(
    days: int = 7,
    cwd: Optional[Path] = None,
    audit_store=None,
) -> HistoryTestResult:
    """
    Re-simulate the last N days of DecisionIssued events against the current
    effective policy and report what would have changed.

    `audit_store` can be injected for testing; defaults to the standard store.
    `cwd` is used for project override discovery (same semantics as simulate()).
    """
    if audit_store is None:
        from ...audit.sqlite_store import SQLiteAuditStore
        audit_store = SQLiteAuditStore()

    # Compute cutoff timestamp (ISO format, UTC)
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%S")

    # Fetch relevant event types
    decision_events = audit_store.list_by_event_type("DecisionIssued")
    command_events = audit_store.list_by_event_type("CommandRequested")

    # Build request_id → command lookup from CommandRequested events
    command_by_request_id: dict[str, str] = {}
    for evt in command_events:
        rid = evt.get("request_id", "")
        if not rid:
            continue
        raw_data = evt.get("data_json") or evt.get("data") or {}
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except (json.JSONDecodeError, TypeError):
                raw_data = {}
        cmd = raw_data.get("command", "")
        if cmd and rid:
            command_by_request_id[rid] = cmd

    # Process each DecisionIssued event
    cases: list[HistoryTestCase] = []
    skipped = 0

    for evt in decision_events:
        ts = evt.get("timestamp", "")
        # Filter by time window
        if ts and ts < cutoff_str:
            continue

        request_id = evt.get("request_id", "")
        command = command_by_request_id.get(request_id, "")

        if not command:
            skipped += 1
            continue

        # Parse the stored decision
        raw_data = evt.get("data_json") or evt.get("data") or {}
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except (json.JSONDecodeError, TypeError):
                raw_data = {}

        original_decision = raw_data.get("decision", "")
        if not original_decision:
            skipped += 1
            continue

        # Re-simulate
        try:
            sim = simulate(command, cwd=cwd)
        except Exception:
            skipped += 1
            continue

        changed = sim.decision != original_decision
        direction = _decision_direction(original_decision, sim.decision)

        cases.append(HistoryTestCase(
            event_id=evt.get("event_id", ""),
            request_id=request_id,
            timestamp=ts,
            command=command,
            original_decision=original_decision,
            simulated_decision=sim.decision,
            changed=changed,
            matched_rule=sim.matched_rule,
            direction=direction if changed else "unchanged",
        ))

    changed_cases = [c for c in cases if c.changed]
    tightened = sum(1 for c in changed_cases if c.direction == "tightened")
    loosened = sum(1 for c in changed_cases if c.direction == "loosened")

    return HistoryTestResult(
        days=days,
        total=len(cases),
        changed=len(changed_cases),
        unchanged=len(cases) - len(changed_cases),
        tightened=tightened,
        loosened=loosened,
        skipped=skipped,
        changed_cases=changed_cases,
    )


# Prevent pytest from collecting this as a test function
test_against_history.__test__ = False  # type: ignore[attr-defined]
