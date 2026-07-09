# SPDX-License-Identifier: Apache-2.0
"""Tests for EventRouter: pattern matching, audit emission, finding creation."""

import pytest

from policy_scout.watch.event_router import EventRouter, RouterFinding, _top_severity
from policy_scout.watch.fs_watcher import FSEvent
from policy_scout.watch.watch_config import TriggerPattern, WatchConfig


def _config_with_patterns(*patterns: TriggerPattern) -> WatchConfig:
    return WatchConfig(
        project_paths=["."],
        system_paths=[],
        trigger_patterns=list(patterns),
    )


def _event(path: str, event_type: str = "create") -> FSEvent:
    return FSEvent(path=path, event_type=event_type, timestamp="2026-06-10T00:00:00Z")


def test_no_match_returns_empty():
    config = _config_with_patterns(
        TriggerPattern(path_glob="**/.env", event_types=["create"], severity="high")
    )
    router = EventRouter(config=config)
    findings = router.route(_event("/tmp/harmless.txt"))
    assert findings == []


def test_matching_pattern_returns_finding():
    config = _config_with_patterns(
        TriggerPattern(path_glob="**/.env", event_types=["create"], severity="high")
    )
    router = EventRouter(config=config)
    findings = router.route(_event("/project/.env", "create"))
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].trigger == "**/.env"
    assert findings[0].path == "/project/.env"


def test_multiple_patterns_can_match():
    config = _config_with_patterns(
        TriggerPattern(path_glob="**/.env", event_types=["create", "modify"], severity="high"),
        TriggerPattern(path_glob="**/.env*", event_types=["create", "modify"], severity="medium"),
    )
    router = EventRouter(config=config)
    findings = router.route(_event("/project/.env", "create"))
    assert len(findings) == 2


def test_wrong_event_type_not_matched():
    config = _config_with_patterns(
        TriggerPattern(path_glob="**/.env", event_types=["create"], severity="high")
    )
    router = EventRouter(config=config)
    findings = router.route(_event("/project/.env", "delete"))
    assert findings == []


def test_finding_to_dict():
    config = _config_with_patterns(
        TriggerPattern(path_glob="**/*.sh", event_types=["create"], severity="medium")
    )
    router = EventRouter(config=config)
    findings = router.route(_event("/project/deploy.sh", "create"))
    assert len(findings) == 1
    d = findings[0].to_dict()
    assert d["path"] == "/project/deploy.sh"
    assert d["severity"] == "medium"
    assert "timestamp" in d


def test_audit_store_called_on_match():
    from unittest.mock import MagicMock

    config = _config_with_patterns(
        TriggerPattern(path_glob="**/.env", event_types=["create"], severity="high")
    )
    mock_store = MagicMock()
    router = EventRouter(config=config, audit_store=mock_store)
    router.route(_event("/project/.env", "create"))
    assert mock_store.store.called


def test_audit_store_not_called_on_no_match():
    from unittest.mock import MagicMock

    config = _config_with_patterns(
        TriggerPattern(path_glob="**/.env", event_types=["create"], severity="high")
    )
    mock_store = MagicMock()
    router = EventRouter(config=config, audit_store=mock_store)
    router.route(_event("/project/README.md", "create"))
    assert not mock_store.store.called


def test_top_severity_ordering():
    assert _top_severity(["low", "high", "medium"]) == "high"
    assert _top_severity(["critical", "low"]) == "critical"
    assert _top_severity(["info", "low"]) == "low"
    assert _top_severity([]) == "medium"


def test_audit_store_exception_does_not_crash():
    from unittest.mock import MagicMock

    config = _config_with_patterns(
        TriggerPattern(path_glob="**/.env", event_types=["create"], severity="high")
    )
    mock_store = MagicMock()
    mock_store.store.side_effect = RuntimeError("db gone")
    router = EventRouter(config=config, audit_store=mock_store)
    findings = router.route(_event("/project/.env", "create"))
    # Should still return findings even if audit store blew up
    assert len(findings) >= 1
