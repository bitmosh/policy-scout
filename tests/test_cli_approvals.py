# SPDX-License-Identifier: Apache-2.0
"""Tests for CLI approval commands."""

import os
import tempfile
from pathlib import Path
from policy_scout.cli.main import check_command, handle_approvals_command
from policy_scout.approvals.store import ApprovalStore
from policy_scout.approvals.models import ApprovalStatus
import argparse


def test_check_creates_approval_for_require_approval():
    """Test that check creates approval for REQUIRE_APPROVAL decisions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            # Run check on a command that should require approval
            result = check_command(
                "rm -rf node_modules",
                json_output=False,
                audit_enabled=True,
                approval_enabled=True,
            )

            # Verify REQUIRE_APPROVAL decision
            assert result["decision"] == "REQUIRE_APPROVAL"

            # Verify approval was created
            approval_store = ApprovalStore()
            pending = approval_store.list_pending()
            assert len(pending) == 1
            assert pending[0].command == "rm -rf node_modules"
            assert pending[0].status == ApprovalStatus.PENDING
            assert pending[0].risk_score > 0
            assert pending[0].approval_id.startswith("appr_")
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_check_no_approval_for_deny():
    """Test that hard-denied commands do not create approvals."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            # Run check on a hard-denied command
            result = check_command(
                "rm -rf /", json_output=False, audit_enabled=True, approval_enabled=True
            )

            # Verify DENY decision
            assert result["decision"] in ["DENY", "DENY_AND_ALERT"]

            # Verify no approval was created
            approval_store = ApprovalStore()
            pending = approval_store.list_pending()
            assert len(pending) == 0
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_check_no_approval_flag():
    """Test that --no-approval flag prevents approval creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            # Run check with approval disabled
            result = check_command(
                "rm -rf node_modules",
                json_output=False,
                audit_enabled=True,
                approval_enabled=False,
            )

            # Verify REQUIRE_APPROVAL decision still happens
            assert result["decision"] == "REQUIRE_APPROVAL"

            # Verify no approval was created
            approval_store = ApprovalStore()
            pending = approval_store.list_pending()
            assert len(pending) == 0
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_approvals_list():
    """Test approvals list command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            # Create an approval
            approval_store = ApprovalStore()
            from policy_scout.approvals.models import ApprovalRequest

            approval = ApprovalRequest(
                request_id="req_test",
                decision_id="REQUIRE_APPROVAL",
                command="rm -rf node_modules",
                cwd="/home/user/project",
                risk_score=7,
                decision="REQUIRE_APPROVAL",
                reasons=["Destructive command"],
                recommended_action="Review manually",
            )
            approval_store.save(approval)

            # Call list command
            args = argparse.Namespace(approvals_subcommand="list")
            handle_approvals_command(args)

            # Approval should still be pending
            pending = approval_store.list_pending()
            assert len(pending) == 1
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_approvals_show():
    """Test approvals show command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            # Create an approval
            approval_store = ApprovalStore()
            from policy_scout.approvals.models import ApprovalRequest

            approval = ApprovalRequest(
                request_id="req_test",
                decision_id="REQUIRE_APPROVAL",
                command="rm -rf node_modules",
                cwd="/home/user/project",
                risk_score=7,
                decision="REQUIRE_APPROVAL",
                reasons=["Destructive command"],
                recommended_action="Review manually",
            )
            approval_store.save(approval)

            # Call show command
            args = argparse.Namespace(
                approvals_subcommand="show", approval_id=approval.approval_id
            )
            handle_approvals_command(args)

            # Approval should still be pending
            retrieved = approval_store.get_by_id(approval.approval_id)
            assert retrieved.status == ApprovalStatus.PENDING
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_approvals_approve():
    """Test approvals approve command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            # Create an approval
            approval_store = ApprovalStore()
            from policy_scout.approvals.models import ApprovalRequest

            approval = ApprovalRequest(
                request_id="req_test",
                decision_id="REQUIRE_APPROVAL",
                command="rm -rf node_modules",
                cwd="/home/user/project",
                risk_score=7,
                decision="REQUIRE_APPROVAL",
                reasons=["Destructive command"],
                recommended_action="Review manually",
                actor={"type": "human", "name": "cli_user"},
            )
            approval_store.save(approval)

            # Call approve command
            args = argparse.Namespace(
                approvals_subcommand="approve", approval_id=approval.approval_id
            )
            handle_approvals_command(args)

            # Verify status changed
            retrieved = approval_store.get_by_id(approval.approval_id)
            assert retrieved.status == ApprovalStatus.APPROVED_ONCE
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)


def test_approvals_deny():
    """Test approvals deny command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        audit_path = Path(tmpdir) / "audit.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        os.environ["POLICY_SCOUT_AUDIT_PATH"] = str(audit_path)

        try:
            # Create an approval
            approval_store = ApprovalStore()
            from policy_scout.approvals.models import ApprovalRequest

            approval = ApprovalRequest(
                request_id="req_test",
                decision_id="REQUIRE_APPROVAL",
                command="rm -rf node_modules",
                cwd="/home/user/project",
                risk_score=7,
                decision="REQUIRE_APPROVAL",
                reasons=["Destructive command"],
                recommended_action="Review manually",
            )
            approval_store.save(approval)

            # Call deny command
            args = argparse.Namespace(
                approvals_subcommand="deny", approval_id=approval.approval_id
            )
            handle_approvals_command(args)

            # Verify status changed
            retrieved = approval_store.get_by_id(approval.approval_id)
            assert retrieved.status == ApprovalStatus.DENIED_ONCE
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)
            os.environ.pop("POLICY_SCOUT_AUDIT_PATH", None)
