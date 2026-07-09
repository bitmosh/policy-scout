# SPDX-License-Identifier: Apache-2.0
"""Tests for HMAC chain integrity in JSONL audit writer and verifier."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from policy_scout.audit.chain_verifier import verify_chain, ZERO_MAC
from policy_scout.audit.jsonl_writer import JSONLWriter, _get_or_create_hmac_key
from policy_scout.audit.events import AuditEvent


@pytest.fixture
def audit_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def writer(audit_dir):
    """JSONLWriter backed by a temp directory."""
    return JSONLWriter(path=audit_dir / "audit.jsonl")


def _make_event(summary: str = "test event") -> AuditEvent:
    return AuditEvent(
        event_type="TestEvent",
        summary=summary,
        data={"value": summary},
    )


class TestJSONLWriterChain:
    def test_write_adds_chain_fields(self, writer, audit_dir):
        writer.write_event(_make_event("first"))
        events = writer.read_events()
        assert len(events) == 1
        assert events[0]["chain_seq"] == 1
        assert len(events[0]["chain_mac"]) == 64  # hex-encoded SHA-256

    def test_sequential_seq_numbers(self, writer):
        for i in range(5):
            writer.write_event(_make_event(f"event {i}"))
        events = writer.read_events()
        seqs = [e["chain_seq"] for e in events]
        assert seqs == [1, 2, 3, 4, 5]

    def test_different_macs_for_different_entries(self, writer):
        writer.write_event(_make_event("alpha"))
        writer.write_event(_make_event("beta"))
        events = writer.read_events()
        assert events[0]["chain_mac"] != events[1]["chain_mac"]

    def test_hmac_key_persisted(self, audit_dir):
        key_path = audit_dir / "audit_hmac.key"
        assert not key_path.exists()
        writer = JSONLWriter(path=audit_dir / "audit.jsonl")
        assert key_path.exists()
        key1 = key_path.read_bytes()

        # Second writer with same path loads the same key
        writer2 = JSONLWriter(path=audit_dir / "audit.jsonl")
        assert writer2._key == key1

    def test_chain_head_persisted(self, audit_dir):
        writer = JSONLWriter(path=audit_dir / "audit.jsonl")
        writer.write_event(_make_event("first"))
        head_path = Path(str(audit_dir / "audit.jsonl") + ".chain_head")
        assert head_path.exists()
        head = json.loads(head_path.read_text())
        assert head["seq"] == 1
        assert len(head["mac"]) == 64

    def test_chain_head_continues_across_instances(self, audit_dir):
        writer1 = JSONLWriter(path=audit_dir / "audit.jsonl")
        writer1.write_event(_make_event("from writer1"))

        writer2 = JSONLWriter(path=audit_dir / "audit.jsonl")
        writer2.write_event(_make_event("from writer2"))

        events = writer2.read_events()
        assert events[0]["chain_seq"] == 1
        assert events[1]["chain_seq"] == 2

    def test_clear_resets_chain(self, writer, audit_dir):
        writer.write_event(_make_event("before clear"))
        writer.clear()

        assert not (audit_dir / "audit.jsonl").exists()
        assert writer._seq == 0
        assert writer._prev_mac == ZERO_MAC

    def test_write_after_clear_starts_at_seq_1(self, writer):
        writer.write_event(_make_event("before clear"))
        writer.clear()
        writer.write_event(_make_event("after clear"))
        events = writer.read_events()
        assert len(events) == 1
        assert events[0]["chain_seq"] == 1


class TestChainVerifier:
    def test_verify_clean_chain(self, audit_dir):
        writer = JSONLWriter(path=audit_dir / "audit.jsonl")
        for i in range(10):
            writer.write_event(_make_event(f"event {i}"))

        result = verify_chain(audit_dir / "audit.jsonl")
        assert result.verified is True
        assert result.total_entries == 10
        assert len(result.errors) == 0

    def test_verify_empty_file(self, audit_dir):
        jsonl_path = audit_dir / "audit.jsonl"
        jsonl_path.write_text("")
        # Need a key too
        _get_or_create_hmac_key(audit_dir / "audit_hmac.key")

        result = verify_chain(jsonl_path)
        assert result.verified is True
        assert result.total_entries == 0
        assert "No chain data" in result.message

    def test_verify_missing_file(self, audit_dir):
        _get_or_create_hmac_key(audit_dir / "audit_hmac.key")
        result = verify_chain(audit_dir / "nonexistent.jsonl")
        assert result.verified is True
        assert result.total_entries == 0
        assert "not found" in result.message

    def test_verify_missing_key(self, audit_dir):
        jsonl_path = audit_dir / "audit.jsonl"
        jsonl_path.write_text('{"event_id": "x", "chain_seq": 1, "chain_mac": "abc"}\n')
        # No key file

        result = verify_chain(jsonl_path)
        assert result.verified is False
        assert "HMAC key not found" in result.message

    def test_verify_tampered_entry(self, audit_dir):
        writer = JSONLWriter(path=audit_dir / "audit.jsonl")
        writer.write_event(_make_event("legit"))
        writer.write_event(_make_event("also legit"))

        # Tamper: modify the summary of the first entry
        jsonl_path = audit_dir / "audit.jsonl"
        lines = jsonl_path.read_text().splitlines()
        entry = json.loads(lines[0])
        entry["summary"] = "TAMPERED"
        lines[0] = json.dumps(entry)
        jsonl_path.write_text("\n".join(lines) + "\n")

        result = verify_chain(jsonl_path)
        assert result.verified is False
        assert len(result.errors) == 1
        assert result.errors[0].kind == "tamper"
        assert result.errors[0].lineno == 1

    def test_verify_deleted_entry(self, audit_dir):
        writer = JSONLWriter(path=audit_dir / "audit.jsonl")
        for i in range(3):
            writer.write_event(_make_event(f"event {i}"))

        # Remove the second line (seq 2)
        jsonl_path = audit_dir / "audit.jsonl"
        lines = jsonl_path.read_text().splitlines()
        del lines[1]
        jsonl_path.write_text("\n".join(lines) + "\n")

        result = verify_chain(jsonl_path)
        assert result.verified is False
        gap_errors = [e for e in result.errors if e.kind == "gap"]
        assert len(gap_errors) >= 1

    def test_verify_with_explicit_key(self, audit_dir):
        writer = JSONLWriter(path=audit_dir / "audit.jsonl")
        writer.write_event(_make_event("explicit key test"))
        key = writer._key

        result = verify_chain(audit_dir / "audit.jsonl", key=key)
        assert result.verified is True

    def test_verify_wrong_key_fails(self, audit_dir):
        writer = JSONLWriter(path=audit_dir / "audit.jsonl")
        writer.write_event(_make_event("key mismatch"))

        import os
        wrong_key = os.urandom(32)
        result = verify_chain(audit_dir / "audit.jsonl", key=wrong_key)
        assert result.verified is False
        assert result.errors[0].kind == "tamper"

    def test_pre_chain_entries_skipped(self, audit_dir):
        """Entries without chain fields are silently skipped (backward compat)."""
        jsonl_path = audit_dir / "audit.jsonl"
        _get_or_create_hmac_key(audit_dir / "audit_hmac.key")

        # Write a pre-chain entry
        jsonl_path.write_text('{"event_id": "old", "event_type": "OldEvent"}\n')

        result = verify_chain(jsonl_path)
        assert result.verified is True
        assert result.total_entries == 0
        assert "No chain data" in result.message

    def test_mixed_pre_chain_and_chain_entries(self, audit_dir):
        """Old entries before chain, new entries after — verifies only chained ones."""
        jsonl_path = audit_dir / "audit.jsonl"

        # First write a "legacy" entry
        with open(jsonl_path, "w") as f:
            f.write('{"event_id": "old", "event_type": "Legacy"}\n')

        # Then use writer to append chained entries
        writer = JSONLWriter(path=jsonl_path)
        writer.write_event(_make_event("chained entry"))

        result = verify_chain(jsonl_path)
        assert result.verified is True
        assert result.total_entries == 1


class TestGetOrCreateHmacKey:
    def test_creates_key_if_absent(self, audit_dir):
        key_path = audit_dir / "audit_hmac.key"
        assert not key_path.exists()
        key = _get_or_create_hmac_key(key_path)
        assert key_path.exists()
        assert len(key) == 32

    def test_loads_existing_key(self, audit_dir):
        key_path = audit_dir / "audit_hmac.key"
        original = b"x" * 32
        key_path.write_bytes(original)
        loaded = _get_or_create_hmac_key(key_path)
        assert loaded == original

    def test_creates_different_keys(self, audit_dir):
        key1 = _get_or_create_hmac_key(audit_dir / "key1.key")
        key2 = _get_or_create_hmac_key(audit_dir / "key2.key")
        assert key1 != key2  # extremely unlikely to collide
