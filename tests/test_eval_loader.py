"""Tests for eval case loader."""

import os
import tempfile
import yaml
from policy_scout.evals.loader import (
    load_eval_cases,
    validate_eval_cases,
    EvalCaseValidationError,
    VALID_DECISIONS,
    VALID_CATEGORIES,
    VALID_CAPABILITIES,
)
from policy_scout.evals.models import EvalCase


def test_load_eval_cases():
    """Test loading eval cases from YAML."""
    # Create a temporary eval cases file
    cases_data = {
        "cases": [
            {
                "case_id": "eval_001",
                "title": "Test case",
                "command": "ls",
                "expected_decision": "ALLOW",
                "expected_categories": ["safe_read"],
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(cases_data, f)
        temp_path = f.name

    try:
        cases = load_eval_cases(temp_path)
        assert len(cases) == 1
        assert cases[0].case_id == "eval_001"
        assert cases[0].command == "ls"
        assert cases[0].expected_decision == "ALLOW"
    finally:
        os.unlink(temp_path)


def test_load_eval_cases_env_override():
    """Test loading eval cases with environment variable override."""
    # Create a temporary eval cases file
    cases_data = {
        "cases": [
            {
                "case_id": "eval_002",
                "title": "Env override test",
                "command": "pwd",
                "expected_decision": "ALLOW",
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(cases_data, f)
        temp_path = f.name

    try:
        # Set environment variable
        os.environ["POLICY_SCOUT_EVAL_CASES_PATH"] = temp_path
        cases = load_eval_cases()
        assert len(cases) == 1
        assert cases[0].case_id == "eval_002"
    finally:
        os.unlink(temp_path)
        if "POLICY_SCOUT_EVAL_CASES_PATH" in os.environ:
            del os.environ["POLICY_SCOUT_EVAL_CASES_PATH"]


def test_load_eval_cases_file_not_found():
    """Test loading eval cases from non-existent file."""
    try:
        load_eval_cases("/nonexistent/path/eval_cases.yaml")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "Eval cases file not found" in str(e)


def test_load_eval_cases_invalid_format():
    """Test loading eval cases with invalid format."""
    # Create a file with invalid format
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid yaml content")
        temp_path = f.name

    try:
        load_eval_cases(temp_path)
        assert False, "Should have raised EvalCaseValidationError"
    except EvalCaseValidationError as e:
        assert "must be a dict with 'cases' key" in str(e)
    finally:
        os.unlink(temp_path)


def test_load_eval_cases_cases_not_list():
    """Test loading eval cases where 'cases' is not a list."""
    cases_data = {"cases": "not a list"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(cases_data, f)
        temp_path = f.name

    try:
        load_eval_cases(temp_path)
        assert False, "Should have raised EvalCaseValidationError"
    except EvalCaseValidationError as e:
        assert "'cases' must be a list" in str(e)
    finally:
        os.unlink(temp_path)


def test_validate_eval_cases_duplicate_ids():
    """Test validation fails with duplicate case IDs."""
    cases = [
        EvalCase(case_id="eval_001", title="Test 1", command="ls"),
        EvalCase(case_id="eval_001", title="Test 2", command="pwd"),
    ]

    try:
        validate_eval_cases(cases)
        assert False, "Should have raised EvalCaseValidationError"
    except EvalCaseValidationError as e:
        assert "Duplicate case IDs" in str(e)
        assert "eval_001" in str(e)


def test_validate_eval_cases_invalid_decision():
    """Test validation fails with invalid decision."""
    cases = [
        EvalCase(
            case_id="eval_001",
            title="Test",
            command="ls",
            expected_decision="INVALID_DECISION",
        )
    ]

    errors = validate_eval_cases(cases)
    assert len(errors) == 1
    assert "invalid decision" in errors[0]
    assert "INVALID_DECISION" in errors[0]


def test_validate_eval_cases_invalid_category():
    """Test validation fails with invalid category."""
    cases = [
        EvalCase(
            case_id="eval_001",
            title="Test",
            command="ls",
            expected_categories=["invalid_category"],
        )
    ]

    errors = validate_eval_cases(cases)
    assert len(errors) == 1
    assert "invalid category" in errors[0]
    assert "invalid_category" in errors[0]


def test_validate_eval_cases_invalid_capability():
    """Test validation fails with invalid capability."""
    cases = [
        EvalCase(
            case_id="eval_001",
            title="Test",
            command="ls",
            expected_capabilities=["invalid_capability"],
        )
    ]

    errors = validate_eval_cases(cases)
    assert len(errors) == 1
    assert "invalid capability" in errors[0]
    assert "invalid_capability" in errors[0]


def test_validate_eval_cases_risk_min_greater_than_max():
    """Test validation fails when risk_min > risk_max."""
    cases = [
        EvalCase(
            case_id="eval_001",
            title="Test",
            command="ls",
            expected_risk_min=8,
            expected_risk_max=3,
        )
    ]

    errors = validate_eval_cases(cases)
    assert len(errors) == 1
    assert "risk_min" in errors[0]
    assert "greater than risk_max" in errors[0]


def test_validate_eval_cases_risk_out_of_range():
    """Test validation fails when risk is out of 0-10 range."""
    cases = [
        EvalCase(
            case_id="eval_001",
            title="Test",
            command="ls",
            expected_risk_min=15,
        ),
        EvalCase(
            case_id="eval_002",
            title="Test 2",
            command="pwd",
            expected_risk_max=-5,
        ),
    ]

    errors = validate_eval_cases(cases)
    assert len(errors) == 2
    assert any("risk_min must be 0-10" in e for e in errors)
    assert any("risk_max must be 0-10" in e for e in errors)


def test_validate_eval_cases_valid():
    """Test validation passes with valid cases."""
    cases = [
        EvalCase(
            case_id="eval_001",
            title="Test",
            command="ls",
            expected_decision="ALLOW",
            expected_categories=["safe_read"],
            expected_capabilities=["filesystem.read"],
            expected_risk_min=1,
            expected_risk_max=3,
        )
    ]

    errors = validate_eval_cases(cases)
    assert len(errors) == 0


def test_validate_eval_cases_no_validation_required():
    """Test validation passes when no expectations are set."""
    cases = [
        EvalCase(
            case_id="eval_001",
            title="Test",
            command="ls",
        )
    ]

    errors = validate_eval_cases(cases)
    assert len(errors) == 0


def test_valid_decisions_constant():
    """Test VALID_DECISIONS contains expected values."""
    assert "ALLOW" in VALID_DECISIONS
    assert "ALLOW_LOGGED" in VALID_DECISIONS
    assert "REQUIRE_APPROVAL" in VALID_DECISIONS
    assert "SANDBOX_FIRST" in VALID_DECISIONS
    assert "DENY" in VALID_DECISIONS
    assert "DENY_AND_ALERT" in VALID_DECISIONS


def test_valid_categories_constant():
    """Test VALID_CATEGORIES contains expected values."""
    assert "safe_read" in VALID_CATEGORIES
    assert "package_install" in VALID_CATEGORIES
    assert "network_execute" in VALID_CATEGORIES
    assert "credential_adjacent" in VALID_CATEGORIES
    assert "destructive" in VALID_CATEGORIES
    assert "unknown" in VALID_CATEGORIES


def test_valid_capabilities_constant():
    """Test VALID_CAPABILITIES contains expected values."""
    assert "filesystem.read" in VALID_CAPABILITIES
    assert "network.fetch" in VALID_CAPABILITIES
    assert "package.install" in VALID_CAPABILITIES
    assert "shell.execute" in VALID_CAPABILITIES
    assert "credential.access_possible" in VALID_CAPABILITIES
    assert "destructive.mutation" in VALID_CAPABILITIES
