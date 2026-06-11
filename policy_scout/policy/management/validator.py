"""Policy validator — detect unreachable rules, contradictions, and coverage gaps."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ...registry.loader import RegistryLoader
from ...registry.models import PolicyRegistry


@dataclass
class PolicyIssue:
    """A single detected problem in the policy registry."""

    issue_type: str       # "unreachable_rule" | "contradiction" | "missing_coverage"
    rule_id: str
    description: str
    severity: str         # "warning" | "error"
    related_rule_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type,
            "rule_id": self.rule_id,
            "description": self.description,
            "severity": self.severity,
            "related_rule_id": self.related_rule_id,
        }


@dataclass
class ValidationResult:
    """Aggregated result of a policy validation run."""

    issues: list = field(default_factory=list)   # list[PolicyIssue]
    rules_checked: int = 0
    eval_cases_checked: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict:
        return {
            "rules_checked": self.rules_checked,
            "eval_cases_checked": self.eval_cases_checked,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
        }


def validate_policy(
    registry: Optional[PolicyRegistry] = None,
    strict: bool = False,
) -> ValidationResult:
    """
    Validate the current policy registry for correctness issues.

    Checks:
      1. Unreachable rules — a preceding broader rule always fires first
      2. Contradictions — equivalent matchers with different decisions
      3. Missing coverage — eval suite cases that fall through to no rule
      4. No catch-all — registry has no rule covering the "unknown" category

    With `strict=True`, warnings are treated as errors for exit-code purposes
    (ValidationResult.is_valid will be False if any warning exists).
    """
    if registry is None:
        loader = RegistryLoader()
        registry = loader.policy_registry

    issues: list[PolicyIssue] = []
    active_rules = [r for r in registry.policies if r.status == "active"]
    active_rules_sorted = sorted(active_rules, key=lambda r: r.priority, reverse=True)

    issues.extend(_check_unreachable_rules(active_rules_sorted))
    issues.extend(_check_contradictions(active_rules_sorted))
    eval_cases_checked = 0
    coverage_issues, eval_cases_checked = _check_missing_coverage(registry)
    issues.extend(coverage_issues)
    issues.extend(_check_no_catchall(active_rules_sorted))

    if strict:
        # Promote all warnings to errors
        for issue in issues:
            if issue.severity == "warning":
                issue.severity = "error"

    return ValidationResult(
        issues=issues,
        rules_checked=len(active_rules),
        eval_cases_checked=eval_cases_checked,
    )


def _check_unreachable_rules(rules: list) -> list[PolicyIssue]:
    """
    A rule is unreachable if any preceding higher-priority rule has a superset
    of its matchers — meaning it will always fire instead.
    """
    issues = []
    for i, rule in enumerate(rules):
        for prev_rule in rules[:i]:
            if _is_subsumes(prev_rule, rule):
                issues.append(PolicyIssue(
                    issue_type="unreachable_rule",
                    rule_id=rule.id,
                    description=(
                        f"Rule '{rule.id}' (priority {rule.priority}) is unreachable — "
                        f"rule '{prev_rule.id}' (priority {prev_rule.priority}) always matches first "
                        f"because it covers a superset of '{rule.id}'s categories and capabilities."
                    ),
                    severity="warning",
                    related_rule_id=prev_rule.id,
                ))
                break  # one report per unreachable rule is enough
    return issues


def _check_contradictions(rules: list) -> list[PolicyIssue]:
    """
    Two active rules with identical matchers but different decisions is a
    contradiction — one will always shadow the other.
    """
    issues = []
    seen_pairs: set[tuple[str, str]] = set()
    for i, rule_a in enumerate(rules):
        for rule_b in rules[i + 1:]:
            pair = (min(rule_a.id, rule_b.id), max(rule_a.id, rule_b.id))
            if pair in seen_pairs:
                continue
            if _matchers_equivalent(rule_a, rule_b) and rule_a.decision != rule_b.decision:
                seen_pairs.add(pair)
                issues.append(PolicyIssue(
                    issue_type="contradiction",
                    rule_id=rule_b.id,
                    description=(
                        f"Rules '{rule_a.id}' and '{rule_b.id}' have equivalent matchers "
                        f"but different decisions ('{rule_a.decision}' vs '{rule_b.decision}'). "
                        f"The higher-priority rule ('{rule_a.id}') will always win."
                    ),
                    severity="error",
                    related_rule_id=rule_a.id,
                ))
    return issues


def _check_missing_coverage(_registry: PolicyRegistry) -> tuple[list[PolicyIssue], int]:
    """
    Run all eval suite cases through the current policy and flag any that
    fall through without matching any rule.
    """
    from .simulator import simulate
    from ...evals.loader import load_eval_cases

    issues = []
    try:
        cases = load_eval_cases()
    except Exception:
        return [], 0

    for case in cases:
        try:
            result = simulate(case.command)
        except Exception:
            continue
        if result.matched_rule is None:
            issues.append(PolicyIssue(
                issue_type="missing_coverage",
                rule_id="(none)",
                description=(
                    f"Eval case '{case.case_id}' "
                    f"(command: {repr(case.command)}) "
                    f"matched no rule — falls through to default DENY."
                ),
                severity="warning",
            ))

    return issues, len(cases)


def _check_no_catchall(rules: list) -> list[PolicyIssue]:
    """
    Warn if no rule covers the 'unknown' category. Commands the classifier
    can't categorize silently hit the hardcoded fallback instead of a
    deliberate policy decision.
    """
    has_unknown_catch = any(
        "unknown" in r.match.get("categories", [])
        for r in rules
    )
    if not has_unknown_catch:
        return [PolicyIssue(
            issue_type="missing_coverage",
            rule_id="(none)",
            description=(
                "No active rule covers the 'unknown' category. "
                "Unclassified commands fall through to the hardcoded fallback "
                "('unknown_require_approval') instead of an explicit policy decision. "
                "Consider adding an explicit catch-all rule."
            ),
            severity="warning",
        )]
    return []


# ── Matcher comparison helpers ────────────────────────────────────────────────

def _is_subsumes(broader: object, narrower: object) -> bool:
    """
    Return True if `broader` would always match whenever `narrower` matches,
    making `narrower` unreachable (given broader has higher priority).

    Conservative: only flags obvious subsumption (superset categories, no
    additional capability constraints). False negatives are acceptable here —
    better to miss an unreachable rule than to false-alarm a legitimate one.
    """
    b_match = getattr(broader, "match", {}) or {}
    n_match = getattr(narrower, "match", {}) or {}

    b_cats = set(b_match.get("categories", []))
    n_cats = set(n_match.get("categories", []))

    # Broader must cover at least all of narrower's categories
    if not b_cats.issuperset(n_cats):
        return False

    # If broader has capability constraints, it's not strictly broader
    if b_match.get("capabilities"):
        return False

    # Narrower must have no additional fields that broaden wouldn't match
    # (e.g., if narrower has capability requirements, broader might not cover them)
    if n_match.get("capabilities"):
        return False

    # Narrower must have no exclude logic that broader doesn't have
    b_exclude = getattr(broader, "exclude", {}) or {}
    n_exclude = getattr(narrower, "exclude", {}) or {}
    if n_exclude and not b_exclude:
        return False

    return True


def _matchers_equivalent(rule_a: object, rule_b: object) -> bool:
    """Return True if two rules have logically identical matchers."""
    a_match = getattr(rule_a, "match", {}) or {}
    b_match = getattr(rule_b, "match", {}) or {}
    a_exclude = getattr(rule_a, "exclude", {}) or {}
    b_exclude = getattr(rule_b, "exclude", {}) or {}

    return (
        set(a_match.get("categories", [])) == set(b_match.get("categories", []))
        and set(a_match.get("capabilities", [])) == set(b_match.get("capabilities", []))
        and set(a_exclude.get("capabilities", [])) == set(b_exclude.get("capabilities", []))
    )
