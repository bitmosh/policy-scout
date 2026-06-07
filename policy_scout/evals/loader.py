"""Eval case loader from YAML."""

import os
from typing import List, Optional
import yaml
from .models import EvalCase


# Valid decision values from TAXONOMIES.md
VALID_DECISIONS = {
    "ALLOW",
    "ALLOW_LOGGED",
    "REQUIRE_APPROVAL",
    "SANDBOX_FIRST",
    "DENY",
    "DENY_AND_ALERT",
}

# Valid category values from TAXONOMIES.md
VALID_CATEGORIES = {
    "safe_read",
    "local_inspection",
    "project_write",
    "package_install",
    "package_execute",
    "lifecycle_execute",
    "network_fetch",
    "network_execute",
    "shell_script",
    "credential_adjacent",
    "system_mutation",
    "destructive",
    "persistence_mechanism",
    "unknown",
}

# Valid capability values from TAXONOMIES.md
VALID_CAPABILITIES = {
    "filesystem.read",
    "filesystem.project_write",
    "filesystem.project_write_possible",
    "filesystem.system_write",
    "filesystem.system_write_possible",
    "filesystem.write_possible",
    "network.fetch",
    "network.execute",
    "package.install",
    "package.execute",
    "lifecycle.execute_possible",
    "shell.execute",
    "credential.access_possible",
    "process.spawn",
    "process.inspect",
    "system.mutation",
    "system.mutation_possible",
    "destructive.mutation",
    "persistence.modify",
}


class EvalCaseValidationError(Exception):
    """Raised when eval case validation fails."""

    pass


def load_eval_cases(path: Optional[str] = None) -> List[EvalCase]:
    """Load eval cases from YAML file.

    Args:
        path: Path to eval cases YAML file. If None, uses default path.

    Returns:
        List of EvalCase objects.

    Raises:
        EvalCaseValidationError: If validation fails.
        FileNotFoundError: If file not found.
    """
    if path is None:
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            "eval_cases.yaml",
        )

    # Allow environment variable override for tests
    path = os.environ.get("POLICY_SCOUT_EVAL_CASES_PATH", path)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Eval cases file not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "cases" not in data:
        raise EvalCaseValidationError(
            "Invalid eval cases file: must be a dict with 'cases' key"
        )

    cases_data = data["cases"]
    if not isinstance(cases_data, list):
        raise EvalCaseValidationError("Invalid eval cases: 'cases' must be a list")

    cases = []
    for case_data in cases_data:
        case = EvalCase.from_dict(case_data)
        cases.append(case)

    return cases


def validate_eval_cases(cases: List[EvalCase]) -> List[str]:
    """Validate eval cases.

    Args:
        cases: List of EvalCase objects to validate.

    Returns:
        List of validation error messages. Empty if all valid.

    Raises:
        EvalCaseValidationError: If critical validation fails (e.g., duplicate IDs).
    """
    errors = []

    # Check for duplicate case IDs
    case_ids = [case.case_id for case in cases]
    duplicates = [cid for cid in case_ids if case_ids.count(cid) > 1]
    if duplicates:
        raise EvalCaseValidationError(f"Duplicate case IDs found: {set(duplicates)}")

    for case in cases:
        # Validate decision if specified
        if case.expected_decision is not None:
            if case.expected_decision not in VALID_DECISIONS:
                errors.append(
                    f"Case {case.case_id}: invalid decision '{case.expected_decision}'. "
                    f"Valid decisions: {VALID_DECISIONS}"
                )

        # Validate categories if specified
        if case.expected_categories:
            for cat in case.expected_categories:
                if cat not in VALID_CATEGORIES:
                    errors.append(
                        f"Case {case.case_id}: invalid category '{cat}'. "
                        f"Valid categories: {VALID_CATEGORIES}"
                    )

        # Validate capabilities if specified
        if case.expected_capabilities:
            for cap in case.expected_capabilities:
                if cap not in VALID_CAPABILITIES:
                    errors.append(
                        f"Case {case.case_id}: invalid capability '{cap}'. "
                        f"Valid capabilities: {VALID_CAPABILITIES}"
                    )

        # Validate risk range if specified
        if case.expected_risk_min is not None or case.expected_risk_max is not None:
            if (
                case.expected_risk_min is not None
                and case.expected_risk_max is not None
            ):
                if case.expected_risk_min > case.expected_risk_max:
                    errors.append(
                        f"Case {case.case_id}: risk_min ({case.expected_risk_min}) "
                        f"greater than risk_max ({case.expected_risk_max})"
                    )
            if case.expected_risk_min is not None and (
                case.expected_risk_min < 0 or case.expected_risk_min > 10
            ):
                errors.append(
                    f"Case {case.case_id}: risk_min must be 0-10, got {case.expected_risk_min}"
                )
            if case.expected_risk_max is not None and (
                case.expected_risk_max < 0 or case.expected_risk_max > 10
            ):
                errors.append(
                    f"Case {case.case_id}: risk_max must be 0-10, got {case.expected_risk_max}"
                )

    return errors
