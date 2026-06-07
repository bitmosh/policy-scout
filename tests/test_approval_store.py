"""Tests for approval store."""

import os
import tempfile
from pathlib import Path
from policy_scout.approvals.store import ApprovalStore
from policy_scout.approvals.models import ApprovalRequest, ApprovalStatus


def test_approval_store_save_and_retrieve():
    """Test saving and retrieving approval requests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        
        try:
            store = ApprovalStore()
            
            approval = ApprovalRequest(
                request_id="req_test",
                decision_id="REQUIRE_APPROVAL",
                command="rm -rf node_modules",
                cwd="/home/user/project",
                risk_score=7,
                decision="REQUIRE_APPROVAL",
                reasons=["Destructive command"],
                recommended_action="Review manually"
            )
            
            # Save
            success = store.save(approval)
            assert success
            
            # Retrieve
            retrieved = store.get_by_id(approval.approval_id)
            assert retrieved is not None
            assert retrieved.approval_id == approval.approval_id
            assert retrieved.command == approval.command
            assert retrieved.status == ApprovalStatus.PENDING
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)


def test_approval_store_list_pending():
    """Test listing pending approvals."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        
        try:
            store = ApprovalStore()
            
            # Create multiple approvals
            approval1 = ApprovalRequest(
                request_id="req_1",
                decision_id="REQUIRE_APPROVAL",
                command="rm -rf node_modules",
                cwd="/home/user/project",
                risk_score=7,
                decision="REQUIRE_APPROVAL",
                reasons=["Destructive command"],
                recommended_action="Review manually"
            )
            
            approval2 = ApprovalRequest(
                request_id="req_2",
                decision_id="REQUIRE_APPROVAL",
                command="rm -rf dist",
                cwd="/home/user/project",
                risk_score=6,
                decision="REQUIRE_APPROVAL",
                reasons=["Destructive command"],
                recommended_action="Review manually"
            )
            
            store.save(approval1)
            store.save(approval2)
            
            # List pending
            pending = store.list_pending()
            assert len(pending) == 2
            assert all(a.status == ApprovalStatus.PENDING for a in pending)
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)


def test_approval_store_update_status():
    """Test updating approval status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        
        try:
            store = ApprovalStore()
            
            approval = ApprovalRequest(
                request_id="req_test",
                decision_id="REQUIRE_APPROVAL",
                command="rm -rf node_modules",
                cwd="/home/user/project",
                risk_score=7,
                decision="REQUIRE_APPROVAL",
                reasons=["Destructive command"],
                recommended_action="Review manually"
            )
            
            store.save(approval)
            
            # Update to approved
            success = store.update_status(approval.approval_id, ApprovalStatus.APPROVED_ONCE)
            assert success
            
            # Verify update
            retrieved = store.get_by_id(approval.approval_id)
            assert retrieved.status == ApprovalStatus.APPROVED_ONCE
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)


def test_approval_store_clear():
    """Test clearing all approvals."""
    with tempfile.TemporaryDirectory() as tmpdir:
        approval_path = Path(tmpdir) / "approvals.jsonl"
        os.environ["POLICY_SCOUT_APPROVAL_PATH"] = str(approval_path)
        
        try:
            store = ApprovalStore()
            
            approval = ApprovalRequest(
                request_id="req_test",
                decision_id="REQUIRE_APPROVAL",
                command="rm -rf node_modules",
                cwd="/home/user/project",
                risk_score=7,
                decision="REQUIRE_APPROVAL",
                reasons=["Destructive command"],
                recommended_action="Review manually"
            )
            
            store.save(approval)
            assert approval_path.exists()
            
            # Clear
            store.clear()
            assert not approval_path.exists()
        finally:
            os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)


def test_approval_store_default_path():
    """Test approval store uses default path when no env var."""
    # Remove env var if set
    os.environ.pop("POLICY_SCOUT_APPROVAL_PATH", None)
    
    store = ApprovalStore()
    expected_path = Path.home() / ".local" / "share" / "policy-scout" / "approvals.jsonl"
    assert store.path == expected_path
