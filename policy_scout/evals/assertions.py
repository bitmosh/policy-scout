"""Assertion logic for comparing expected vs actual eval results."""

from typing import List, Optional


def assert_decision(
    expected: Optional[str],
    actual: Optional[str],
    case_id: str,
) -> List[str]:
    """Assert decision matches expected.

    Returns:
        List of failure reasons. Empty if passes.
    """
    if expected is None:
        return []

    if actual is None:
        return [f"Decision was None, expected {expected}"]

    if expected != actual:
        return [f"Decision mismatch: expected {expected}, got {actual}"]

    return []


def assert_categories(
    expected: Optional[List[str]],
    actual: Optional[List[str]],
    case_id: str,
) -> List[str]:
    """Assert categories match expected.

    Returns:
        List of failure reasons. Empty if passes.
    """
    if expected is None:
        return []

    if actual is None:
        return [f"Categories were None, expected {expected}"]

    expected_set = set(expected)
    actual_set = set(actual)

    missing = expected_set - actual_set
    extra = actual_set - expected_set

    reasons = []
    if missing:
        reasons.append(f"Missing categories: {missing}")
    if extra:
        reasons.append(f"Extra categories: {extra}")

    return reasons


def assert_capabilities(
    expected: Optional[List[str]],
    actual: Optional[List[str]],
    case_id: str,
) -> List[str]:
    """Assert capabilities match expected.

    Returns:
        List of failure reasons. Empty if passes.
    """
    if expected is None:
        return []

    if actual is None:
        return [f"Capabilities were None, expected {expected}"]

    expected_set = set(expected)
    actual_set = set(actual)

    missing = expected_set - actual_set
    extra = actual_set - expected_set

    reasons = []
    if missing:
        reasons.append(f"Missing capabilities: {missing}")
    if extra:
        reasons.append(f"Extra capabilities: {extra}")

    return reasons


def assert_policy_hits(
    expected: Optional[List[str]],
    actual: Optional[List[str]],
    case_id: str,
) -> List[str]:
    """Assert policy hits match expected.

    Returns:
        List of failure reasons. Empty if passes.
    """
    if expected is None:
        return []

    if actual is None:
        return [f"Policy hits were None, expected {expected}"]

    expected_set = set(expected)
    actual_set = set(actual)

    missing = expected_set - actual_set
    extra = actual_set - expected_set

    reasons = []
    if missing:
        reasons.append(f"Missing policy hits: {missing}")
    if extra:
        reasons.append(f"Extra policy hits: {extra}")

    return reasons


def assert_registry_hits(
    expected: Optional[List[str]],
    actual: Optional[List[str]],
    case_id: str,
) -> List[str]:
    """Assert registry hits match expected.

    Returns:
        List of failure reasons. Empty if passes.
    """
    if expected is None:
        return []

    if actual is None:
        return [f"Registry hits were None, expected {expected}"]

    expected_set = set(expected)
    actual_set = set(actual)

    missing = expected_set - actual_set
    extra = actual_set - expected_set

    reasons = []
    if missing:
        reasons.append(f"Missing registry hits: {missing}")
    if extra:
        reasons.append(f"Extra registry hits: {extra}")

    return reasons


def assert_risk_range(
    expected_min: Optional[int],
    expected_max: Optional[int],
    actual: Optional[int],
    case_id: str,
) -> List[str]:
    """Assert risk score falls within expected range.

    Returns:
        List of failure reasons. Empty if passes.
    """
    if expected_min is None and expected_max is None:
        return []

    if actual is None:
        return ["Risk score was None"]

    reasons = []
    if expected_min is not None and actual < expected_min:
        reasons.append(f"Risk score {actual} below minimum {expected_min}")
    if expected_max is not None and actual > expected_max:
        reasons.append(f"Risk score {actual} above maximum {expected_max}")

    return reasons


def assert_reasons(
    expected_contains: Optional[List[str]],
    actual_reasons: Optional[List[str]],
    case_id: str,
) -> List[str]:
    """Assert reasons contain expected substrings.

    Returns:
        List of failure reasons. Empty if passes.
    """
    if expected_contains is None:
        return []

    if actual_reasons is None:
        return [f"Reasons were None, expected to contain: {expected_contains}"]

    reasons_text = " ".join(actual_reasons).lower()
    missing = []

    for expected in expected_contains:
        if expected.lower() not in reasons_text:
            missing.append(expected)

    if missing:
        return [f"Reasons missing expected text: {missing}"]

    return []
