"""Policy Scout evaluation harness."""

from .models import EvalCase, EvalResult, EvalSummary
from .loader import load_eval_cases, validate_eval_cases
from .runner import run_eval_case, run_eval_suite
from .assertions import assert_decision, assert_categories, assert_capabilities, assert_policy_hits, assert_registry_hits, assert_risk_range, assert_reasons
from .report import generate_eval_report, generate_eval_json

__all__ = [
    "EvalCase",
    "EvalResult",
    "EvalSummary",
    "load_eval_cases",
    "validate_eval_cases",
    "run_eval_case",
    "run_eval_suite",
    "assert_decision",
    "assert_categories",
    "assert_capabilities",
    "assert_policy_hits",
    "assert_registry_hits",
    "assert_risk_range",
    "assert_reasons",
    "generate_eval_report",
    "generate_eval_json",
]
