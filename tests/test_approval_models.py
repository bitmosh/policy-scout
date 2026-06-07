"""Tests for approval models."""

from policy_scout.approvals.models import ApprovalRequest, ApprovalStatus, ApprovalScope


def test_approval_request_structure():
    """Test approval request has required fields."""
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

    assert approval.approval_id.startswith("appr_")
    assert approval.request_id == "req_test"
    assert approval.decision_id == "REQUIRE_APPROVAL"
    assert approval.command == "rm -rf node_modules"
    assert approval.cwd == "/home/user/project"
    assert approval.risk_score == 7
    assert approval.decision == "REQUIRE_APPROVAL"
    assert approval.reasons == ["Destructive command"]
    assert approval.recommended_action == "Review manually"
    assert approval.status == "pending"
    assert approval.scope == "once"
    assert approval.schema_version == 1
    assert approval.created_at is not None
    assert approval.expires_at is not None


def test_approval_request_to_dict():
    """Test approval request serialization."""
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

    approval_dict = approval.to_dict()

    assert approval_dict["approval_id"] == approval.approval_id
    assert approval_dict["request_id"] == approval.request_id
    assert approval_dict["decision_id"] == approval.decision_id
    assert approval_dict["command"] == approval.command
    assert approval_dict["cwd"] == approval.cwd
    assert approval_dict["risk_score"] == approval.risk_score
    assert approval_dict["decision"] == approval.decision
    assert approval_dict["reasons"] == approval.reasons
    assert approval_dict["recommended_action"] == approval.recommended_action
    assert approval_dict["status"] == approval.status
    assert approval_dict["scope"] == approval.scope
    assert approval_dict["schema_version"] == approval.schema_version


def test_approval_request_from_dict():
    """Test approval request deserialization."""
    data = {
        "approval_id": "appr_test123",
        "request_id": "req_test",
        "decision_id": "REQUIRE_APPROVAL",
        "created_at": "2024-01-01T00:00:00Z",
        "expires_at": "2024-01-02T00:00:00Z",
        "status": "pending",
        "actor": {"type": "human", "name": "test_user"},
        "command": "rm -rf node_modules",
        "cwd": "/home/user/project",
        "risk_score": 7,
        "decision": "REQUIRE_APPROVAL",
        "reasons": ["Destructive command"],
        "recommended_action": "Review manually",
        "scope": "once",
        "schema_version": 1,
    }

    approval = ApprovalRequest.from_dict(data)

    assert approval.approval_id == "appr_test123"
    assert approval.request_id == "req_test"
    assert approval.decision_id == "REQUIRE_APPROVAL"
    assert approval.command == "rm -rf node_modules"
    assert approval.status == "pending"
    assert approval.scope == "once"


def test_approval_status_constants():
    """Test approval status constants."""
    assert ApprovalStatus.PENDING == "pending"
    assert ApprovalStatus.APPROVED_ONCE == "approved_once"
    assert ApprovalStatus.DENIED_ONCE == "denied_once"
    assert ApprovalStatus.EXPIRED == "expired"
    assert ApprovalStatus.CANCELLED == "cancelled"
    assert ApprovalStatus.EXECUTED == "executed"
    assert ApprovalStatus.FAILED == "failed"


def test_approval_scope_constants():
    """Test approval scope constants."""
    assert ApprovalScope.ONCE == "once"
