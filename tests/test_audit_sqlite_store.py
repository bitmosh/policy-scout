"""Tests for SQLite audit store."""

import json
import os
import tempfile
import pytest

from policy_scout.audit.sqlite_store import SQLiteAuditStore
from policy_scout.audit.events import AuditEvent, create_command_requested_event


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "audit.db")
        yield db_path


@pytest.fixture
def sqlite_store(temp_db_path):
    """Create a SQLite store with temporary database."""
    return SQLiteAuditStore(path=temp_db_path)


def test_database_file_created(sqlite_store, temp_db_path):
    """Test that SQLite database file is created."""
    assert os.path.exists(temp_db_path)


def test_audit_events_table_created(sqlite_store):
    """Test that audit_events table is created."""
    import sqlite3

    with sqlite3.connect(sqlite_store.path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_events'"
        )
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "audit_events"


def test_write_event_inserts_event(sqlite_store):
    """Test that write_event inserts an event."""
    event = create_command_requested_event(
        request_id="req_test",
        command="echo hello",
        actor={"type": "human", "name": "test_user"},
    )

    success = sqlite_store.write_event(event)
    assert success is True

    # Verify event was inserted
    retrieved = sqlite_store.get_event(event.event_id)
    assert retrieved is not None
    assert retrieved["event_id"] == event.event_id
    assert retrieved["event_type"] == "CommandRequested"


def test_get_event_returns_inserted_event(sqlite_store):
    """Test that get_event returns the inserted event."""
    event = create_command_requested_event(
        request_id="req_test",
        command="ls",
        actor={"type": "human", "name": "test_user"},
    )

    sqlite_store.write_event(event)
    retrieved = sqlite_store.get_event(event.event_id)

    assert retrieved is not None
    assert retrieved["event_id"] == event.event_id
    assert retrieved["request_id"] == "req_test"
    assert json.loads(retrieved["data_json"])["command"] == "ls"


def test_list_recent_returns_events_in_order(sqlite_store):
    """Test that list_recent returns events in expected order."""
    # Write multiple events
    for i in range(5):
        event = create_command_requested_event(
            request_id=f"req_{i}",
            command=f"echo {i}",
            actor={"type": "human", "name": "test_user"},
        )
        sqlite_store.write_event(event)

    # List recent events
    recent = sqlite_store.list_recent(limit=3)
    assert len(recent) == 3

    # Should be in descending timestamp order
    assert recent[0]["request_id"] == "req_4"
    assert recent[1]["request_id"] == "req_3"
    assert recent[2]["request_id"] == "req_2"


def test_list_by_request_id_returns_matching_events(sqlite_store):
    """Test that list_by_request_id returns only matching events."""
    # Write events for different requests
    for i in range(3):
        event = create_command_requested_event(
            request_id="req_shared",
            command=f"echo {i}",
            actor={"type": "human", "name": "test_user"},
        )
        sqlite_store.write_event(event)

    # Write event for different request
    other_event = create_command_requested_event(
        request_id="req_other",
        command="ls",
        actor={"type": "human", "name": "test_user"},
    )
    sqlite_store.write_event(other_event)

    # Query by request_id
    events = sqlite_store.list_by_request_id("req_shared")
    assert len(events) == 3
    for event in events:
        assert event["request_id"] == "req_shared"


def test_list_by_event_type_returns_matching_events(sqlite_store):
    """Test that list_by_event_type returns only matching events."""
    # Write CommandRequested events
    for i in range(3):
        event = create_command_requested_event(
            request_id=f"req_{i}",
            command=f"echo {i}",
            actor={"type": "human", "name": "test_user"},
        )
        sqlite_store.write_event(event)

    # Write a different event type
    from policy_scout.audit.events import create_decision_issued_event

    decision_event = create_decision_issued_event(
        request_id="req_0",
        decision="ALLOW",
        risk_score=1,
        risk_band="low",
        reasons=["Safe command"],
    )
    sqlite_store.write_event(decision_event)

    # Query by event type
    events = sqlite_store.list_by_event_type("CommandRequested")
    assert len(events) == 3
    for event in events:
        assert event["event_type"] == "CommandRequested"


def test_count_events_works(sqlite_store):
    """Test that count_events returns correct count."""
    assert sqlite_store.count_events() == 0

    # Write events
    for i in range(5):
        event = create_command_requested_event(
            request_id=f"req_{i}",
            command=f"echo {i}",
            actor={"type": "human", "name": "test_user"},
        )
        sqlite_store.write_event(event)

    assert sqlite_store.count_events() == 5


def test_duplicate_event_id_behavior(sqlite_store):
    """Test that duplicate event_id behavior is safe."""
    event = create_command_requested_event(
        request_id="req_test",
        command="echo hello",
        actor={"type": "human", "name": "test_user"},
    )

    # Write same event twice
    sqlite_store.write_event(event)
    success = sqlite_store.write_event(event)

    # Should fail due to primary key constraint
    assert success is False

    # Count should still be 1
    assert sqlite_store.count_events() == 1


def test_event_data_json_is_valid_json(sqlite_store):
    """Test that event data_json is valid JSON."""
    event = create_command_requested_event(
        request_id="req_test",
        command="echo hello",
        actor={"type": "human", "name": "test_user"},
    )

    sqlite_store.write_event(event)
    retrieved = sqlite_store.get_event(event.event_id)

    # Should be able to parse data_json
    data = json.loads(retrieved["data_json"])
    assert data["command"] == "echo hello"


def test_redaction_applied_before_sqlite_insert(sqlite_store):
    """Test that redaction is applied before SQLite insert."""
    # Create event with secret-like value
    event = AuditEvent(
        event_type="CommandRequested",
        request_id="req_test",
        summary="Command with secret",
        data={
            "command": "npm install",
            "env_token": "sk-1234567890abcdef",  # Should be redacted
        },
    )

    sqlite_store.write_event(event)
    retrieved = sqlite_store.get_event(event.event_id)

    # Check that secret was redacted in data_json
    data = json.loads(retrieved["data_json"])
    assert "sk-1234567890abcdef" not in str(data)
    assert "<redacted:" in str(data)


def test_no_raw_secret_values_in_sqlite_row(sqlite_store):
    """Test that raw secret-like values do not appear in SQLite row."""
    event = AuditEvent(
        event_type="CommandRequested",
        request_id="req_test",
        summary="Command with API key",
        data={
            "command": "curl",
            "api_key": "OPENAI_API_KEY=sk-test123",  # Should be redacted
        },
    )

    sqlite_store.write_event(event)
    retrieved = sqlite_store.get_event(event.event_id)

    # Check all text fields for raw secret
    row_str = str(retrieved)
    assert "sk-test123" not in row_str
    assert "OPENAI_API_KEY=" not in row_str or "<redacted:" in row_str


def test_env_override_works():
    """Test that POLICY_SCOUT_AUDIT_DB_PATH environment override works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_path = os.path.join(tmpdir, "custom.db")
        os.environ["POLICY_SCOUT_AUDIT_DB_PATH"] = custom_path

        try:
            store = SQLiteAuditStore()
            assert store.path == custom_path

            # Write an event
            event = create_command_requested_event(
                request_id="req_test",
                command="echo test",
                actor={"type": "human", "name": "test"},
            )
            store.write_event(event)

            # Verify it was written to custom path
            assert os.path.exists(custom_path)
        finally:
            os.environ.pop("POLICY_SCOUT_AUDIT_DB_PATH", None)


def test_clear_deletes_all_events(sqlite_store):
    """Test that clear deletes all events."""
    # Write events
    for i in range(3):
        event = create_command_requested_event(
            request_id=f"req_{i}",
            command=f"echo {i}",
            actor={"type": "human", "name": "test_user"},
        )
        sqlite_store.write_event(event)

    assert sqlite_store.count_events() == 3

    # Clear
    sqlite_store.clear()

    assert sqlite_store.count_events() == 0


def test_optional_id_columns_extracted(sqlite_store):
    """Test that optional ID columns are extracted from event data when present."""
    # Create an event with decision_id in data
    event = AuditEvent(
        event_type="DecisionIssued",
        request_id="req_test",
        summary="Decision issued",
        data={
            "decision": "ALLOW",
            "decision_id": "dec_test123",
            "risk_score": 1,
            "risk_band": "low",
            "reasons": ["Safe command"],
        },
    )

    sqlite_store.write_event(event)
    retrieved = sqlite_store.get_event(event.event_id)

    # decision_id should be extracted when present in data
    assert retrieved["decision_id"] == "dec_test123"


def test_indexes_created(sqlite_store):
    """Test that required indexes are created."""
    import sqlite3

    with sqlite3.connect(sqlite_store.path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        assert "idx_request_id" in indexes
        assert "idx_event_type" in indexes
        assert "idx_timestamp" in indexes


def test_write_events_batch(sqlite_store):
    """Test that write_events writes multiple events."""
    events = []
    for i in range(5):
        event = create_command_requested_event(
            request_id=f"req_{i}",
            command=f"echo {i}",
            actor={"type": "human", "name": "test_user"},
        )
        events.append(event)

    count = sqlite_store.write_events(events)
    assert count == 5
    assert sqlite_store.count_events() == 5
