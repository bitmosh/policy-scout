# SPDX-License-Identifier: Apache-2.0
"""Routes FSEvents through trigger patterns to audit + sweep sub-checkers."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, List, Optional

from .fs_watcher import FSEvent
from .watch_config import TriggerPattern, WatchConfig

if TYPE_CHECKING:
    from ..audit.sqlite_store import SQLiteAuditStore


def _utcnow_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RouterFinding:
    """A finding produced by the event router."""

    def __init__(
        self,
        path: str,
        severity: str,
        trigger: str,
        event_type: str,
        detection_confidence: str,
        description: str,
    ):
        self.path = path
        self.severity = severity
        self.trigger = trigger
        self.event_type = event_type
        self.detection_confidence = detection_confidence
        self.description = description
        self.timestamp = _utcnow_iso()

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "severity": self.severity,
            "trigger": self.trigger,
            "event_type": self.event_type,
            "detection_confidence": self.detection_confidence,
            "description": self.description,
            "timestamp": self.timestamp,
        }


class EventRouter:
    """Evaluates FSEvents against watch config and emits audit events + findings."""

    def __init__(
        self,
        config: WatchConfig,
        audit_store: Optional["SQLiteAuditStore"] = None,
    ):
        self._config = config
        self._audit_store = audit_store

    def route(self, event: FSEvent) -> List[RouterFinding]:
        """Match event against trigger patterns; emit audit event; return findings."""
        matched = self._config.matching_patterns(event.path, event.event_type)
        if not matched:
            return []

        findings = []
        for pattern in matched:
            finding = RouterFinding(
                path=event.path,
                severity=pattern.severity,
                trigger=pattern.path_glob,
                event_type=event.event_type,
                detection_confidence=event.detection_confidence,
                description=_describe(event, pattern),
            )
            findings.append(finding)

        if self._audit_store and findings:
            self._emit_audit_event(event, findings)

        # For classifiable files, run the relevant sub-sweep
        if event.event_type in ("create", "modify", "close_write"):
            findings.extend(self._run_sub_sweep(event, matched))

        return findings

    def _emit_audit_event(self, event: FSEvent, findings: List[RouterFinding]) -> None:
        from ..audit.events import AuditEvent, EventType
        from ..core.ids import generate_id

        severities = [f.severity for f in findings]
        top_severity = _top_severity(severities)

        ae = AuditEvent(
            event_type=EventType.WATCH_TRIGGER_DETECTED,
            request_id=generate_id("req"),
            actor={"type": "watch_daemon", "name": "policy-scout-watch"},
            summary=f"Watch trigger: {event.event_type} {event.path} [{top_severity}]",
            data={
                "path": event.path,
                "event_type": event.event_type,
                "detection_confidence": event.detection_confidence,
                "top_severity": top_severity,
                "findings_count": len(findings),
                "triggers": [f.trigger for f in findings],
            },
        )
        try:
            self._audit_store.store(ae)  # type: ignore[union-attr]
        except Exception:
            pass

    def _run_sub_sweep(self, event: FSEvent, _matched: List[TriggerPattern]) -> List[RouterFinding]:
        """Run targeted sub-checkers on the affected file."""
        from ..core.ids import generate_id

        path = event.path
        ext = os.path.splitext(path)[1].lower()
        basename = os.path.basename(path)
        findings: List[RouterFinding] = []

        sweep_id = generate_id("sweep")

        try:
            if basename == "package.json" or path.endswith("/package.json"):
                parent = os.path.dirname(path)
                from ..sweep.package_scripts import check_package_scripts
                for f in check_package_scripts(parent, sweep_id):
                    findings.append(RouterFinding(
                        path=path,
                        severity=f.severity,
                        trigger="sweep:package_scripts",
                        event_type=event.event_type,
                        detection_confidence=event.detection_confidence,
                        description=f.title or str(f),
                    ))

            elif ext == ".sh" or (os.access(path, os.X_OK) and ext in ("", ".bash", ".zsh")):
                parent = os.path.dirname(path) or "."
                from ..sweep.shell_scripts import check_shell_scripts
                for f in check_shell_scripts(parent, sweep_id):
                    if f.location and path in f.location:
                        findings.append(RouterFinding(
                            path=path,
                            severity=f.severity,
                            trigger="sweep:shell_scripts",
                            event_type=event.event_type,
                            detection_confidence=event.detection_confidence,
                            description=f.title or str(f),
                        ))

            elif ext in (".js", ".mjs", ".cjs", ".ts"):
                parent = os.path.dirname(path) or "."
                from ..sweep.javascript_patterns import check_javascript_patterns
                for f in check_javascript_patterns(parent, sweep_id):
                    if f.location and path in f.location:
                        findings.append(RouterFinding(
                            path=path,
                            severity=f.severity,
                            trigger="sweep:javascript_patterns",
                            event_type=event.event_type,
                            detection_confidence=event.detection_confidence,
                            description=f.title or str(f),
                        ))

            elif ext in (".yml", ".yaml") and ".github/workflows" in path:
                parent = os.path.dirname(os.path.dirname(path))
                from ..sweep.workflows import check_workflows
                for f in check_workflows(parent, sweep_id):
                    if f.location and path in f.location:
                        findings.append(RouterFinding(
                            path=path,
                            severity=f.severity,
                            trigger="sweep:workflows",
                            event_type=event.event_type,
                            detection_confidence=event.detection_confidence,
                            description=f.title or str(f),
                        ))

        except Exception:
            # Sub-sweep failures are non-fatal — router keeps running
            pass

        return findings


def _describe(event: FSEvent, pattern: TriggerPattern) -> str:
    verb = {"create": "created", "modify": "modified", "delete": "deleted",
             "attrib": "chmod'd", "moved_to": "moved in"}.get(event.event_type, event.event_type)
    return (
        f"{os.path.basename(event.path)} {verb} — matches pattern "
        f"'{pattern.path_glob}' (severity: {pattern.severity})"
    )


def _top_severity(severities: List[str]) -> str:
    order = ["critical", "high", "medium", "low", "info"]
    for level in order:
        if level in severities:
            return level
    return "medium"
