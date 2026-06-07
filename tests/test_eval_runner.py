"""Tests for eval runner."""

from policy_scout.evals.models import EvalCase
from policy_scout.evals.runner import run_eval_case, run_eval_suite


def test_run_eval_case_simple():
    """Test running a simple eval case."""
    case = EvalCase(
        case_id="eval_001",
        title="Safe read",
        command="ls",
        expected_decision="ALLOW",
        expected_categories=["safe_read"],
    )

    result = run_eval_case(case)

    assert result.case_id == "eval_001"
    assert result.command == "ls"
    assert result.execution_time_ms is not None
    # The actual result depends on the classifier/policy implementation
    # We're mainly testing that the runner executes without error


def test_run_eval_case_with_all_expectations():
    """Test running an eval case with all expectations set."""
    case = EvalCase(
        case_id="eval_002",
        title="Package install",
        command="npm install lodash",
        expected_decision="SANDBOX_FIRST",
        expected_categories=["package_install"],
        expected_capabilities=["network.fetch", "filesystem.project_write"],
        expected_policy_hits=["package_install_sandbox_first"],
        expected_registry_hits=None,  # registry_hits are complex objects, skip for this test
        expected_risk_min=5,
        expected_risk_max=8,
        expected_contains_reasons=["lifecycle"],
    )

    result = run_eval_case(case)

    assert result.case_id == "eval_002"
    assert result.command == "npm install lodash"
    assert result.execution_time_ms is not None
    assert result.actual_decision is not None
    assert result.actual_categories is not None
    assert result.actual_capabilities is not None
    assert result.actual_policy_hits is not None
    assert result.actual_registry_hits is not None


def test_run_eval_case_no_expectations():
    """Test running an eval case with no expectations."""
    case = EvalCase(
        case_id="eval_003",
        title="Unknown command",
        command="unknown-command",
    )

    result = run_eval_case(case)

    assert result.case_id == "eval_003"
    assert result.command == "unknown-command"
    # With no expectations, the case should pass if it runs without error
    assert result.passed is True
    assert len(result.failure_reasons) == 0


def test_run_eval_suite():
    """Test running a suite of eval cases."""
    cases = [
        EvalCase(
            case_id="eval_001",
            title="Safe read",
            command="ls",
            expected_decision="ALLOW",
        ),
        EvalCase(
            case_id="eval_002",
            title="Package install",
            command="npm install lodash",
            expected_decision="SANDBOX_FIRST",
        ),
        EvalCase(
            case_id="eval_003",
            title="Unknown",
            command="unknown-command",
        ),
    ]

    results, summary = run_eval_suite(cases)

    assert len(results) == 3
    assert summary.total_cases == 3
    assert summary.passed + summary.failed == 3
    assert summary.pass_rate >= 0.0
    assert summary.pass_rate <= 1.0
    assert summary.execution_time_ms is not None
    assert summary.timestamp is not None


def test_run_eval_suite_with_filter():
    """Test running a suite with tag filter."""
    cases = [
        EvalCase(
            case_id="eval_001",
            title="Safe read",
            command="ls",
            tags=["safe_read"],
        ),
        EvalCase(
            case_id="eval_002",
            title="Package install",
            command="npm install lodash",
            tags=["package_install"],
        ),
        EvalCase(
            case_id="eval_003",
            title="Another package install",
            command="npm install react",
            tags=["package_install"],
        ),
    ]

    results, summary = run_eval_suite(cases, filter_tag="package_install")

    assert len(results) == 2
    assert summary.total_cases == 2
    assert all(r.case_id in ["eval_002", "eval_003"] for r in results)


def test_run_eval_suite_empty():
    """Test running an empty suite."""
    cases = []

    results, summary = run_eval_suite(cases)

    assert len(results) == 0
    assert summary.total_cases == 0
    assert summary.passed == 0
    assert summary.failed == 0
    assert summary.pass_rate == 0.0
    assert summary.failed_case_ids == []


def test_run_eval_suite_filter_no_matches():
    """Test running a suite with filter that matches no cases."""
    cases = [
        EvalCase(
            case_id="eval_001",
            title="Safe read",
            command="ls",
            tags=["safe_read"],
        ),
    ]

    results, summary = run_eval_suite(cases, filter_tag="network_execute")

    assert len(results) == 0
    assert summary.total_cases == 0


def test_eval_result_structure():
    """Test that EvalResult has all required fields."""
    case = EvalCase(
        case_id="eval_001",
        title="Test",
        command="ls",
    )

    result = run_eval_case(case)

    # Check all required fields are present
    assert hasattr(result, "case_id")
    assert hasattr(result, "passed")
    assert hasattr(result, "command")
    assert hasattr(result, "expected_decision")
    assert hasattr(result, "actual_decision")
    assert hasattr(result, "expected_categories")
    assert hasattr(result, "actual_categories")
    assert hasattr(result, "expected_capabilities")
    assert hasattr(result, "actual_capabilities")
    assert hasattr(result, "expected_policy_hits")
    assert hasattr(result, "actual_policy_hits")
    assert hasattr(result, "expected_registry_hits")
    assert hasattr(result, "actual_registry_hits")
    assert hasattr(result, "expected_risk_range")
    assert hasattr(result, "actual_risk_score")
    assert hasattr(result, "failure_reasons")
    assert hasattr(result, "execution_time_ms")


def test_eval_summary_structure():
    """Test that EvalSummary has all required fields."""
    cases = [
        EvalCase(case_id="eval_001", title="Test", command="ls"),
    ]

    results, summary = run_eval_suite(cases)

    # Check all required fields are present
    assert hasattr(summary, "total_cases")
    assert hasattr(summary, "passed")
    assert hasattr(summary, "failed")
    assert hasattr(summary, "pass_rate")
    assert hasattr(summary, "failed_case_ids")
    assert hasattr(summary, "execution_time_ms")
    assert hasattr(summary, "timestamp")


def test_eval_result_serialization():
    """Test that EvalResult can be serialized to dict."""
    case = EvalCase(
        case_id="eval_001",
        title="Test",
        command="ls",
    )

    result = run_eval_case(case)
    data = result.to_dict()

    # Check that all fields are in the dict
    assert "case_id" in data
    assert "passed" in data
    assert "command" in data
    assert "expected_decision" in data
    assert "actual_decision" in data
    assert "expected_categories" in data
    assert "actual_categories" in data
    assert "expected_capabilities" in data
    assert "actual_capabilities" in data
    assert "expected_policy_hits" in data
    assert "actual_policy_hits" in data
    assert "expected_registry_hits" in data
    assert "actual_registry_hits" in data
    assert "expected_risk_min" in data
    assert "expected_risk_max" in data
    assert "actual_risk_score" in data
    assert "failure_reasons" in data
    assert "execution_time_ms" in data


def test_eval_summary_serialization():
    """Test that EvalSummary can be serialized to dict."""
    cases = [
        EvalCase(case_id="eval_001", title="Test", command="ls"),
    ]

    results, summary = run_eval_suite(cases)
    data = summary.to_dict()

    # Check that all fields are in the dict
    assert "total_cases" in data
    assert "passed" in data
    assert "failed" in data
    assert "pass_rate" in data
    assert "failed_case_ids" in data
    assert "execution_time_ms" in data
    assert "timestamp" in data
