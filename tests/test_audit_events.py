"""Tests for audit events."""

from policy_scout.audit.events import (
    AuditEvent,
    EventType,
    create_command_requested_event,
    create_command_parsed_event,
    create_command_classified_event,
    create_policy_matched_event,
    create_decision_issued_event,
    create_policy_error_event,
    create_audit_error_event,
    create_sweep_completed_event,
)


def test_audit_event_structure():
    """Test audit event has required fields."""
    event = AuditEvent(
        event_type="TestEvent", request_id="req_test", summary="Test summary"
    )

    assert event.event_id.startswith("evt_")
    assert event.event_type == "TestEvent"
    assert event.request_id == "req_test"
    assert event.summary == "Test summary"
    assert event.timestamp is not None
    assert event.schema_version == 1
    assert isinstance(event.data, dict)


def test_audit_event_to_dict():
    """Test audit event serialization."""
    event = AuditEvent(
        event_type="TestEvent",
        request_id="req_test",
        summary="Test summary",
        data={"key": "value"},
    )

    event_dict = event.to_dict()

    assert event_dict["event_id"] == event.event_id
    assert event_dict["event_type"] == event.event_type
    assert event_dict["request_id"] == event.request_id
    assert event_dict["summary"] == event.summary
    assert event_dict["data"] == {"key": "value"}
    assert event_dict["schema_version"] == event.schema_version


def test_command_requested_event():
    """Test CommandRequested event creation."""
    event = create_command_requested_event(
        request_id="req_test",
        command="npm install lodash",
        actor={"type": "human", "name": "test_user"},
    )

    assert event.event_type == EventType.COMMAND_REQUESTED
    assert event.request_id == "req_test"
    assert "npm install lodash" in event.summary
    assert event.data["command"] == "npm install lodash"
    assert event.actor == {"type": "human", "name": "test_user"}


def test_command_parsed_event():
    """Test CommandParsed event creation."""
    event = create_command_parsed_event(
        request_id="req_test",
        parse_result={
            "primary_command": "npm",
            "args": ["install", "lodash"],
            "structure": {"has_pipe": False},
        },
    )

    assert event.event_type == EventType.COMMAND_PARSED
    assert event.request_id == "req_test"
    assert event.data["primary_command"] == "npm"
    assert event.data["args"] == ["install", "lodash"]
    assert event.data["structure"]["has_pipe"] is False


def test_command_classified_event():
    """Test CommandClassified event creation."""
    event = create_command_classified_event(
        request_id="req_test",
        classification={
            "category": "package_install",
            "categories": ["package_install"],
            "capabilities": ["network.fetch", "package.install"],
            "confidence": 0.95,
            "registry_hits": [{"entry_id": "npm.install"}],
        },
    )

    assert event.event_type == EventType.COMMAND_CLASSIFIED
    assert event.request_id == "req_test"
    assert "package_install" in event.summary
    assert event.data["category"] == "package_install"
    assert event.data["confidence"] == 0.95
    assert len(event.data["registry_hits"]) == 1


def test_policy_matched_event():
    """Test PolicyMatched event creation."""
    event = create_policy_matched_event(
        request_id="req_test",
        policy_hits=["package_install_sandbox_first", "network_fetch_deny"],
    )

    assert event.event_type == EventType.POLICY_MATCHED
    assert event.request_id == "req_test"
    assert "2 rules" in event.summary
    assert event.data["policy_hits"] == [
        "package_install_sandbox_first",
        "network_fetch_deny",
    ]


def test_decision_issued_event():
    """Test DecisionIssued event creation."""
    event = create_decision_issued_event(
        request_id="req_test",
        decision="SANDBOX_FIRST",
        risk_score=6,
        risk_band="high",
        reasons=["Package installs may execute lifecycle scripts."],
    )

    assert event.event_type == EventType.DECISION_ISSUED
    assert event.request_id == "req_test"
    assert "SANDBOX_FIRST" in event.summary
    assert event.data["decision"] == "SANDBOX_FIRST"
    assert event.data["risk_score"] == 6
    assert event.data["risk_band"] == "high"
    assert len(event.data["reasons"]) == 1


def test_policy_error_event():
    """Test PolicyError event creation."""
    event = create_policy_error_event(
        request_id="req_test", error_message="Policy evaluation failed"
    )

    assert event.event_type == EventType.POLICY_ERROR
    assert event.request_id == "req_test"
    assert event.data["error"] == "Policy evaluation failed"


def test_audit_error_event():
    """Test AuditError event creation."""
    event = create_audit_error_event(
        request_id="req_test", error_message="Audit write failed"
    )

    assert event.event_type == EventType.AUDIT_ERROR
    assert event.request_id == "req_test"
    assert event.data["error"] == "Audit write failed"


def test_sweep_completed_event_total_from_severity_buckets():
    """Test SweepCompleted event computes total from severity buckets when 'total' key is absent."""
    # Findings count without 'total' key
    findings_count = {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4,
        "info": 5,
    }

    event = create_sweep_completed_event(
        request_id="req_test",
        sweep_id="sweep_test",
        findings_count=findings_count,
        duration_ms=1000,
    )

    assert event.event_type == EventType.SWEEP_COMPLETED
    assert event.request_id == "req_test"
    # Summary should show total computed from severity buckets (1+2+3+4+5=15)
    assert "15 findings" in event.summary
    assert event.data["findings_count"] == findings_count
    assert event.data["duration_ms"] == 1000


def test_sweep_completed_event_with_explicit_total():
    """Test SweepCompleted event uses explicit total when provided."""
    # Findings count with 'total' key
    findings_count = {
        "total": 10,
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4,
    }

    event = create_sweep_completed_event(
        request_id="req_test",
        sweep_id="sweep_test",
        findings_count=findings_count,
        duration_ms=1000,
    )

    assert event.event_type == EventType.SWEEP_COMPLETED
    # Summary should use explicit total (10)
    assert "10 findings" in event.summary
    assert event.data["findings_count"] == findings_count
