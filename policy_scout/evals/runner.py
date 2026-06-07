"""Eval runner that executes cases and compares results."""

import time
import os
from typing import List, Optional
from ..core.request import CommandRequest, Actor
from ..classify.shell_parser import ShellParser
from ..classify.command_classifier import CommandClassifier
from ..policy.engine import PolicyEngine
from ..policy.risk_scorer import RiskScorer
from ..registry.loader import RegistryLoader
from ..core.ids import generate_id
from .models import EvalCase, EvalResult, EvalSummary
from .assertions import (
    assert_decision,
    assert_categories,
    assert_capabilities,
    assert_policy_hits,
    assert_registry_hits,
    assert_risk_range,
    assert_reasons,
)


def run_eval_case(case: EvalCase) -> EvalResult:
    """Run a single eval case.

    Args:
        case: EvalCase to run.

    Returns:
        EvalResult with pass/fail status and details.
    """
    start_time = time.time()

    # Load registries (same as CLI check)
    loader = RegistryLoader()
    command_registry = loader.command_registry
    policy_registry = loader.policy_registry

    # Build CommandRequest (use current cwd like CLI check)
    actor = Actor(type=case.actor_type, name="eval_test")
    request = CommandRequest(
        request_id=generate_id("req"),
        command=case.command,
        cwd=os.getcwd(),  # Use current working directory like CLI check
        actor=actor,
        mode=case.mode,
    )

    # Parse
    parser = ShellParser()
    parse_result = parser.parse(case.command, request.request_id)

    # Classify with registry (same as CLI check)
    classifier = CommandClassifier(command_registry=command_registry)
    classification = classifier.classify(parse_result, case.command, request.request_id)

    # Score risk
    risk_scorer = RiskScorer()
    risk_score = risk_scorer.score(classification, request.request_id)

    # Evaluate policy with registry (same as CLI check)
    policy_engine = PolicyEngine(policy_registry=policy_registry)
    decision = policy_engine.evaluate(classification, risk_score, request.request_id)

    # Collect actual values
    actual_decision = decision.decision if decision else None
    actual_categories = classification.categories if classification else []
    actual_capabilities = classification.capabilities if classification else []
    actual_policy_hits = decision.policy_hits if decision else []
    actual_registry_hits = classification.registry_hits if classification else []
    actual_risk_score = decision.risk_score if decision else None
    actual_reasons = decision.reasons if decision else []

    # Build expected risk range
    expected_risk_range = None
    if case.expected_risk_min is not None or case.expected_risk_max is not None:
        expected_risk_range = (
            case.expected_risk_min or 0,
            case.expected_risk_max or 10,
        )

    # Run assertions
    failure_reasons = []

    failure_reasons.extend(
        assert_decision(case.expected_decision, actual_decision, case.case_id)
    )
    failure_reasons.extend(
        assert_categories(case.expected_categories, actual_categories, case.case_id)
    )
    failure_reasons.extend(
        assert_capabilities(
            case.expected_capabilities, actual_capabilities, case.case_id
        )
    )
    failure_reasons.extend(
        assert_policy_hits(case.expected_policy_hits, actual_policy_hits, case.case_id)
    )
    failure_reasons.extend(
        assert_registry_hits(
            case.expected_registry_hits, actual_registry_hits, case.case_id
        )
    )
    if expected_risk_range:
        failure_reasons.extend(
            assert_risk_range(
                expected_risk_range[0],
                expected_risk_range[1],
                actual_risk_score,
                case.case_id,
            )
        )
    failure_reasons.extend(
        assert_reasons(case.expected_contains_reasons, actual_reasons, case.case_id)
    )

    execution_time_ms = int((time.time() - start_time) * 1000)

    return EvalResult(
        case_id=case.case_id,
        passed=len(failure_reasons) == 0,
        command=case.command,
        expected_decision=case.expected_decision,
        actual_decision=actual_decision,
        expected_categories=case.expected_categories,
        actual_categories=actual_categories,
        expected_capabilities=case.expected_capabilities,
        actual_capabilities=actual_capabilities,
        expected_policy_hits=case.expected_policy_hits,
        actual_policy_hits=actual_policy_hits,
        expected_registry_hits=case.expected_registry_hits,
        actual_registry_hits=actual_registry_hits,
        expected_risk_range=expected_risk_range,
        actual_risk_score=actual_risk_score,
        failure_reasons=failure_reasons,
        execution_time_ms=execution_time_ms,
    )


def run_eval_suite(
    cases: List[EvalCase],
    filter_tag: Optional[str] = None,
) -> tuple[List[EvalResult], EvalSummary]:
    """Run a suite of eval cases.

    Args:
        cases: List of EvalCase objects to run.
        filter_tag: Optional tag to filter cases by.

    Returns:
        Tuple of (results, summary).
    """
    # Filter by tag if specified
    if filter_tag:
        cases = [c for c in cases if filter_tag in (c.tags or [])]

    start_time = time.time()
    results = []

    for case in cases:
        result = run_eval_case(case)
        results.append(result)

    execution_time_ms = int((time.time() - start_time) * 1000)

    # Build summary
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    pass_rate = passed / len(results) if results else 0.0
    failed_case_ids = [r.case_id for r in results if not r.passed]

    summary = EvalSummary(
        total_cases=len(results),
        passed=passed,
        failed=failed,
        pass_rate=pass_rate,
        failed_case_ids=failed_case_ids,
        execution_time_ms=execution_time_ms,
    )

    return results, summary
