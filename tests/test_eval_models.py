# SPDX-License-Identifier: Apache-2.0
"""Tests for eval models."""

from policy_scout.evals.models import EvalCase, EvalResult, EvalSummary


def test_eval_case_creation():
    """Test EvalCase creation."""
    case = EvalCase(
        case_id="eval_001",
        title="Test case",
        command="ls",
        actor_type="human",
        mode="balanced",
        expected_decision="ALLOW",
        expected_categories=["safe_read"],
        expected_capabilities=["filesystem.read"],
        expected_policy_hits=["safe_reads_allow"],
        expected_registry_hits=["safe_read_command"],
        expected_risk_min=1,
        expected_risk_max=3,
        expected_contains_reasons=["read-only"],
        tags=["safe_read"],
        notes="Test note",
    )

    assert case.case_id == "eval_001"
    assert case.title == "Test case"
    assert case.command == "ls"
    assert case.actor_type == "human"
    assert case.mode == "balanced"
    assert case.expected_decision == "ALLOW"
    assert case.expected_categories == ["safe_read"]
    assert case.expected_capabilities == ["filesystem.read"]
    assert case.expected_policy_hits == ["safe_reads_allow"]
    assert case.expected_registry_hits == ["safe_read_command"]
    assert case.expected_risk_min == 1
    assert case.expected_risk_max == 3
    assert case.expected_contains_reasons == ["read-only"]
    assert case.tags == ["safe_read"]
    assert case.notes == "Test note"


def test_eval_case_defaults():
    """Test EvalCase with default values."""
    case = EvalCase(
        case_id="eval_002",
        title="Test defaults",
        command="pwd",
    )

    assert case.actor_type == "human"
    assert case.mode == "balanced"
    assert case.expected_decision is None
    assert case.expected_categories is None
    assert case.expected_capabilities is None
    assert case.expected_policy_hits is None
    assert case.expected_registry_hits is None
    assert case.expected_risk_min is None
    assert case.expected_risk_max is None
    assert case.expected_contains_reasons is None
    assert case.tags is None
    assert case.notes is None


def test_eval_case_to_dict():
    """Test EvalCase serialization to dict."""
    case = EvalCase(
        case_id="eval_003",
        title="Test serialization",
        command="cat README.md",
        expected_decision="ALLOW",
        expected_categories=["safe_read"],
    )

    data = case.to_dict()

    assert data["case_id"] == "eval_003"
    assert data["title"] == "Test serialization"
    assert data["command"] == "cat README.md"
    assert data["expected_decision"] == "ALLOW"
    assert data["expected_categories"] == ["safe_read"]
    assert data["expected_capabilities"] == []
    assert data["expected_policy_hits"] == []
    assert data["expected_registry_hits"] == []
    assert data["expected_risk_min"] is None
    assert data["expected_risk_max"] is None
    assert data["expected_contains_reasons"] == []
    assert data["tags"] == []
    assert data["notes"] is None


def test_eval_case_from_dict():
    """Test EvalCase deserialization from dict."""
    data = {
        "case_id": "eval_004",
        "title": "Test deserialization",
        "command": "npm test",
        "actor_type": "agent",
        "mode": "paranoid",
        "expected_decision": "ALLOW_LOGGED",
        "expected_categories": ["local_inspection"],
        "expected_capabilities": ["shell.execute"],
        "expected_policy_hits": ["test_commands_allow_logged"],
        "expected_registry_hits": ["npm_test"],
        "expected_risk_min": 2,
        "expected_risk_max": 4,
        "expected_contains_reasons": ["test command"],
        "tags": ["local_action"],
        "notes": "Test note",
    }

    case = EvalCase.from_dict(data)

    assert case.case_id == "eval_004"
    assert case.title == "Test deserialization"
    assert case.command == "npm test"
    assert case.actor_type == "agent"
    assert case.mode == "paranoid"
    assert case.expected_decision == "ALLOW_LOGGED"
    assert case.expected_categories == ["local_inspection"]
    assert case.expected_capabilities == ["shell.execute"]
    assert case.expected_policy_hits == ["test_commands_allow_logged"]
    assert case.expected_registry_hits == ["npm_test"]
    assert case.expected_risk_min == 2
    assert case.expected_risk_max == 4
    assert case.expected_contains_reasons == ["test command"]
    assert case.tags == ["local_action"]
    assert case.notes == "Test note"


def test_eval_result_creation():
    """Test EvalResult creation."""
    result = EvalResult(
        case_id="eval_001",
        passed=True,
        command="ls",
        expected_decision="ALLOW",
        actual_decision="ALLOW",
        expected_categories=["safe_read"],
        actual_categories=["safe_read"],
        expected_capabilities=["filesystem.read"],
        actual_capabilities=["filesystem.read"],
        expected_policy_hits=["safe_reads_allow"],
        actual_policy_hits=["safe_reads_allow"],
        expected_registry_hits=["safe_read_command"],
        actual_registry_hits=["safe_read_command"],
        expected_risk_range=(1, 3),
        actual_risk_score=2,
        failure_reasons=[],
        execution_time_ms=50,
    )

    assert result.case_id == "eval_001"
    assert result.passed is True
    assert result.command == "ls"
    assert result.expected_decision == "ALLOW"
    assert result.actual_decision == "ALLOW"
    assert result.expected_categories == ["safe_read"]
    assert result.actual_categories == ["safe_read"]
    assert result.expected_capabilities == ["filesystem.read"]
    assert result.actual_capabilities == ["filesystem.read"]
    assert result.expected_policy_hits == ["safe_reads_allow"]
    assert result.actual_policy_hits == ["safe_reads_allow"]
    assert result.expected_registry_hits == ["safe_read_command"]
    assert result.actual_registry_hits == ["safe_read_command"]
    assert result.expected_risk_range == (1, 3)
    assert result.actual_risk_score == 2
    assert result.failure_reasons == []
    assert result.execution_time_ms == 50


def test_eval_result_failure():
    """Test EvalResult with failure."""
    result = EvalResult(
        case_id="eval_002",
        passed=False,
        command="rm -rf /",
        expected_decision="DENY",
        actual_decision="ALLOW",
        expected_categories=["destructive"],
        actual_categories=["safe_read"],
        expected_capabilities=["destructive.mutation"],
        actual_capabilities=["filesystem.read"],
        expected_policy_hits=["destructive_system_commands_deny"],
        actual_policy_hits=["safe_reads_allow"],
        expected_registry_hits=["rm_rf_slash"],
        actual_registry_hits=["safe_read"],
        expected_risk_range=(9, 10),
        actual_risk_score=1,
        failure_reasons=[
            "Decision mismatch: expected DENY, got ALLOW",
            "Missing categories: {'destructive'}",
        ],
        execution_time_ms=75,
    )

    assert result.passed is False
    assert len(result.failure_reasons) == 2
    assert "Decision mismatch" in result.failure_reasons[0]


def test_eval_result_to_dict():
    """Test EvalResult serialization to dict."""
    result = EvalResult(
        case_id="eval_003",
        passed=True,
        command="pwd",
        expected_decision="ALLOW",
        actual_decision="ALLOW",
        expected_categories=["safe_read"],
        actual_categories=["safe_read"],
        expected_capabilities=["filesystem.read"],
        actual_capabilities=["filesystem.read"],
        expected_policy_hits=["safe_reads_allow"],
        actual_policy_hits=["safe_reads_allow"],
        expected_registry_hits=["pwd"],
        actual_registry_hits=["pwd"],
        expected_risk_range=(1, 2),
        actual_risk_score=1,
        failure_reasons=[],
        execution_time_ms=25,
    )

    data = result.to_dict()

    assert data["case_id"] == "eval_003"
    assert data["passed"] is True
    assert data["command"] == "pwd"
    assert data["expected_decision"] == "ALLOW"
    assert data["actual_decision"] == "ALLOW"
    assert data["expected_categories"] == ["safe_read"]
    assert data["actual_categories"] == ["safe_read"]
    assert data["expected_capabilities"] == ["filesystem.read"]
    assert data["actual_capabilities"] == ["filesystem.read"]
    assert data["expected_policy_hits"] == ["safe_reads_allow"]
    assert data["actual_policy_hits"] == ["safe_reads_allow"]
    assert data["expected_registry_hits"] == ["pwd"]
    assert data["actual_registry_hits"] == ["pwd"]
    assert data["expected_risk_min"] == 1
    assert data["expected_risk_max"] == 2
    assert data["actual_risk_score"] == 1
    assert data["failure_reasons"] == []
    assert data["execution_time_ms"] == 25


def test_eval_summary_creation():
    """Test EvalSummary creation."""
    summary = EvalSummary(
        total_cases=30,
        passed=25,
        failed=5,
        pass_rate=0.8333,
        failed_case_ids=["eval_010", "eval_015", "eval_020", "eval_025", "eval_030"],
        execution_time_ms=1500,
    )

    assert summary.total_cases == 30
    assert summary.passed == 25
    assert summary.failed == 5
    assert summary.pass_rate == 0.8333
    assert len(summary.failed_case_ids) == 5
    assert summary.execution_time_ms == 1500
    assert summary.timestamp is not None


def test_eval_summary_defaults():
    """Test EvalSummary with default values."""
    summary = EvalSummary(
        total_cases=10,
        passed=10,
        failed=0,
        pass_rate=1.0,
    )

    assert summary.failed_case_ids == []
    assert summary.execution_time_ms is None
    assert summary.timestamp is not None


def test_eval_summary_to_dict():
    """Test EvalSummary serialization to dict."""
    summary = EvalSummary(
        total_cases=20,
        passed=18,
        failed=2,
        pass_rate=0.9,
        failed_case_ids=["eval_005", "eval_010"],
        execution_time_ms=1000,
    )

    data = summary.to_dict()

    assert data["total_cases"] == 20
    assert data["passed"] == 18
    assert data["failed"] == 2
    assert data["pass_rate"] == 0.9
    assert data["failed_case_ids"] == ["eval_005", "eval_010"]
    assert data["execution_time_ms"] == 1000
    assert data["timestamp"] is not None
