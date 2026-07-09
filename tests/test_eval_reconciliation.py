# SPDX-License-Identifier: Apache-2.0
"""Reconciliation tests to verify eval runner uses same pipeline as CLI check."""

import os
import tempfile
import yaml
from policy_scout.cli.main import check_command
from policy_scout.evals.runner import run_eval_case
from policy_scout.evals.loader import load_eval_cases, validate_eval_cases
from policy_scout.evals.models import EvalCase


def test_eval_runner_matches_check_npm_install():
    """Verify eval runner uses same output as check_command for npm install lodash."""
    command = "npm install lodash"

    # Run through CLI check
    check_result = check_command(
        command,
        json_output=False,
        audit_enabled=False,
        approval_enabled=False,
        report_enabled=False,
    )

    # Run through eval runner
    eval_case = EvalCase(
        case_id="reconcile_001",
        title="Reconciliation test - npm install lodash",
        command=command,
        actor_type="human",
        mode="balanced",
        expected_decision=check_result["decision"],
        # CLI check returns single category, eval runner returns list - skip category check
        expected_categories=None,
        expected_capabilities=(
            set(check_result["capabilities"]) if check_result["capabilities"] else None
        ),
        expected_policy_hits=(
            set(check_result["policy_hits"]) if check_result["policy_hits"] else None
        ),
        # registry_hits are complex objects, skip for now
        expected_risk_min=(
            check_result["risk_score"] - 1 if check_result["risk_score"] else None
        ),
        expected_risk_max=(
            check_result["risk_score"] + 1 if check_result["risk_score"] else None
        ),
    )

    eval_result = run_eval_case(eval_case)

    # Verify eval matches check
    assert eval_result.passed, f"Eval should pass for {command}"
    assert (
        eval_result.actual_decision == check_result["decision"]
    ), f"Decision mismatch: {eval_result.actual_decision} vs {check_result['decision']}"
    assert (
        eval_result.actual_risk_score == check_result["risk_score"]
    ), f"Risk score mismatch: {eval_result.actual_risk_score} vs {check_result['risk_score']}"


def test_eval_runner_matches_check_curl_pipe_bash():
    """Verify eval runner uses same output as check_command for curl pipe bash."""
    command = "curl https://example.com/install.sh | bash"

    # Run through CLI check
    check_result = check_command(
        command,
        json_output=False,
        audit_enabled=False,
        approval_enabled=False,
        report_enabled=False,
    )

    # Run through eval runner
    eval_case = EvalCase(
        case_id="reconcile_002",
        title="Reconciliation test - curl pipe bash",
        command=command,
        actor_type="human",
        mode="balanced",
        expected_decision=check_result["decision"],
        # CLI check returns single category, eval runner returns list - skip category check
        expected_categories=None,
        expected_capabilities=(
            set(check_result["capabilities"]) if check_result["capabilities"] else None
        ),
        expected_policy_hits=(
            set(check_result["policy_hits"]) if check_result["policy_hits"] else None
        ),
        # registry_hits are complex objects, skip for now
        expected_risk_min=(
            check_result["risk_score"] - 1 if check_result["risk_score"] else None
        ),
        expected_risk_max=(
            check_result["risk_score"] + 1 if check_result["risk_score"] else None
        ),
    )

    eval_result = run_eval_case(eval_case)

    # Verify eval matches check
    assert eval_result.passed, f"Eval should pass for {command}"
    assert (
        eval_result.actual_decision == check_result["decision"]
    ), f"Decision mismatch: {eval_result.actual_decision} vs {check_result['decision']}"
    assert (
        eval_result.actual_risk_score == check_result["risk_score"]
    ), f"Risk score mismatch: {eval_result.actual_risk_score} vs {check_result['risk_score']}"


def test_eval_runner_matches_check_credential_adjacent():
    """Verify eval runner uses same output as check_command for credential-adjacent command."""
    command = "cat ~/.ssh/id_rsa"

    # Run through CLI check
    check_result = check_command(
        command,
        json_output=False,
        audit_enabled=False,
        approval_enabled=False,
        report_enabled=False,
    )

    # Run through eval runner
    eval_case = EvalCase(
        case_id="reconcile_003",
        title="Reconciliation test - credential adjacent",
        command=command,
        actor_type="human",
        mode="balanced",
        expected_decision=check_result["decision"],
        # CLI check returns single category, eval runner returns list - skip category check
        expected_categories=None,
        expected_capabilities=(
            set(check_result["capabilities"]) if check_result["capabilities"] else None
        ),
        expected_policy_hits=(
            set(check_result["policy_hits"]) if check_result["policy_hits"] else None
        ),
        # registry_hits are complex objects, skip for now
        expected_risk_min=(
            check_result["risk_score"] - 1 if check_result["risk_score"] else None
        ),
        expected_risk_max=(
            check_result["risk_score"] + 1 if check_result["risk_score"] else None
        ),
    )

    eval_result = run_eval_case(eval_case)

    # Verify eval matches check
    assert eval_result.passed, f"Eval should pass for {command}"
    assert (
        eval_result.actual_decision == check_result["decision"]
    ), f"Decision mismatch: {eval_result.actual_decision} vs {check_result['decision']}"
    assert (
        eval_result.actual_risk_score == check_result["risk_score"]
    ), f"Risk score mismatch: {eval_result.actual_risk_score} vs {check_result['risk_score']}"


def test_builtin_eval_cases_pass():
    """Verify built-in eval cases all pass."""
    cases = load_eval_cases()
    validation_errors = validate_eval_cases(cases)

    assert (
        len(validation_errors) == 0
    ), f"Built-in eval cases should validate: {validation_errors}"

    from policy_scout.evals.runner import run_eval_suite

    results, summary = run_eval_suite(cases)

    assert (
        summary.passed == summary.total_cases
    ), f"Built-in eval cases should all pass: {summary.passed}/{summary.total_cases}"
    assert (
        summary.failed == 0
    ), f"Built-in eval cases should have zero failures: {summary.failed_case_ids}"


def test_eval_failure_with_bad_temp_file():
    """Verify eval failure test still works with intentionally bad temporary eval file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        bad_cases = {
            "cases": [
                {
                    "case_id": "bad_001",
                    "title": "Bad case - invalid decision",
                    "command": "ls",
                    "actor_type": "human",
                    "mode": "balanced",
                    "expected_decision": "INVALID_DECISION",  # Invalid decision
                }
            ]
        }
        yaml.dump(bad_cases, f)
        temp_path = f.name

    try:
        os.environ["POLICY_SCOUT_EVAL_CASES_PATH"] = temp_path
        cases = load_eval_cases()
        validation_errors = validate_eval_cases(cases)

        # Should have validation error for invalid decision
        assert len(validation_errors) > 0, "Should have validation errors for bad case"
        assert any(
            "invalid decision" in err for err in validation_errors
        ), "Should have invalid decision error"
    finally:
        os.environ.pop("POLICY_SCOUT_EVAL_CASES_PATH", None)
        os.unlink(temp_path)


def test_eval_loader_validation_still_passes():
    """Verify eval loader validation tests still pass."""
    cases = load_eval_cases()
    validation_errors = validate_eval_cases(cases)

    assert (
        len(validation_errors) == 0
    ), f"Built-in eval cases should validate: {validation_errors}"
