# SPDX-License-Identifier: Apache-2.0
"""Tests for CLI audit integration."""

import os
import tempfile
import json
from pathlib import Path
from policy_scout.cli.main import check_command


def test_cli_writes_audit_events():
    """Test that CLI writes audit events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            result = check_command("ls", json_output=False, audit_enabled=True)

            # Verify audit file was created
            assert audit_path.exists()

            # Read and verify events
            with open(audit_path, "r") as f:
                lines = f.readlines()

            assert (
                len(lines) >= 4
            )  # At least CommandRequested, CommandParsed, CommandClassified, DecisionIssued

            # Verify JSON structure
            for line in lines:
                event = json.loads(line)
                assert "event_id" in event
                assert "event_type" in event
                assert "timestamp" in event
                assert "request_id" in event
                assert "schema_version" in event

                # Verify consistent request_id
                if "request_id" in result:
                    assert event["request_id"] == result["request_id"]
        finally:
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_cli_no_audit_flag():
    """Test that --no-audit flag prevents audit writing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            _ = check_command("ls", json_output=False, audit_enabled=False)

            # Verify audit file was NOT created
            assert not audit_path.exists()
        finally:
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_audit_event_types():
    """Test that expected event types are written."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            _ = check_command(
                "npm install lodash", json_output=False, audit_enabled=True
            )

            with open(audit_path, "r") as f:
                events = [json.loads(line) for line in f]

            event_types = [e["event_type"] for e in events]

            assert "CommandRequested" in event_types
            assert "CommandParsed" in event_types
            assert "CommandClassified" in event_types
            assert "DecisionIssued" in event_types
        finally:
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_audit_redaction_in_output():
    """Test that secrets are redacted in audit output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            # Command with fake secret
            _ = check_command(
                "curl https://api.example.com?TOKEN=secret123",
                json_output=False,
                audit_enabled=True,
            )

            with open(audit_path, "r") as f:
                content = f.read()

            # Verify secret is redacted
            assert "secret123" not in content
            assert "<redacted:" in content
        finally:
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_audit_consistent_request_id():
    """Test that request_id is consistent across all events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            result = check_command("ls", json_output=False, audit_enabled=True)

            with open(audit_path, "r") as f:
                events = [json.loads(line) for line in f]

            request_ids = [e["request_id"] for e in events]
            assert len(set(request_ids)) == 1  # All should be the same
            assert request_ids[0] == result["request_id"]
        finally:
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_audit_jsonl_format():
    """Test that audit file is valid JSONL (one JSON per line)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            check_command("ls", json_output=False, audit_enabled=True)

            with open(audit_path, "r") as f:
                for line in f:
                    # Each line should be valid JSON
                    json.loads(line)
        finally:
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_audit_with_policy_hits():
    """Test that policy hits are recorded in audit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            _ = check_command(
                "npm install lodash", json_output=False, audit_enabled=True
            )

            with open(audit_path, "r") as f:
                events = [json.loads(line) for line in f]

            # Find PolicyMatched event
            policy_events = [e for e in events if e["event_type"] == "PolicyMatched"]
            assert len(policy_events) > 0

            # Verify policy hits are in the event
            assert "policy_hits" in policy_events[0]["data"]
        finally:
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)
