"""Policy simulator — full rule trace for a command evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ...classify.command_classifier import ClassificationResult, CommandClassifier
from ...classify.shell_parser import ShellParser
from ...policy.engine import PolicyEngine
from ...policy.risk_scorer import RiskScorer
from ...registry.loader import RegistryLoader


@dataclass
class RuleTrace:
    """Trace record for a single rule during simulation."""

    rule_id: str
    source: str           # "override" | "registry" | "fallback"
    priority: int
    checked: bool
    matched: bool
    reasons: list = field(default_factory=list)
    decision: Optional[str] = None   # None when rule did not match
    decisive: bool = False           # True = this rule produced the final answer

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "source": self.source,
            "priority": self.priority,
            "checked": self.checked,
            "matched": self.matched,
            "reasons": self.reasons,
            "decision": self.decision,
            "decisive": self.decisive,
        }


@dataclass
class SimulationResult:
    """Full simulation result with per-rule trace."""

    command: str
    decision: str
    risk_score: int
    risk_band: str
    rule_traces: list = field(default_factory=list)   # list[RuleTrace]
    matched_rule: Optional[str] = None
    categories: list = field(default_factory=list)
    capabilities: list = field(default_factory=list)
    confidence: float = 0.0
    project_override_loaded: bool = False
    project_override_path: Optional[str] = None
    total_rules_checked: int = 0

    @property
    def matched_traces(self) -> list:
        return [t for t in self.rule_traces if t.matched]

    @property
    def unmatched_traces(self) -> list:
        return [t for t in self.rule_traces if not t.matched]

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "decision": self.decision,
            "risk_score": self.risk_score,
            "risk_band": self.risk_band,
            "matched_rule": self.matched_rule,
            "categories": self.categories,
            "capabilities": self.capabilities,
            "confidence": self.confidence,
            "project_override_loaded": self.project_override_loaded,
            "project_override_path": self.project_override_path,
            "total_rules_checked": self.total_rules_checked,
            "rule_traces": [t.to_dict() for t in self.rule_traces],
        }


def simulate(
    command: str,
    cwd: Optional[Path] = None,
) -> SimulationResult:
    """
    Evaluate a command against the effective policy and return the full rule trace.

    Unlike `policy-scout check`, this traces every rule — matched and unmatched —
    so you can see exactly why a particular decision was reached.
    """
    # Parse and classify
    parser = ShellParser()
    parse_result = parser.parse(command)

    loader = RegistryLoader()
    classifier = CommandClassifier(command_registry=loader.command_registry)
    classification = classifier.classify(parse_result, command)

    risk_scorer = RiskScorer()
    risk_result = risk_scorer.score(classification)

    # Load engine with project override (if any)
    engine = PolicyEngine(
        policy_registry=loader.policy_registry,
        config_override=cwd,
    )

    # Collect all rules with source tags
    all_rules = _collect_all_rules(engine, loader)

    # Sort by priority (highest first) — same order as engine.evaluate()
    all_rules.sort(key=lambda r: r["priority"], reverse=True)

    # Evaluate every rule and build trace
    traces: list[RuleTrace] = []
    first_match_id: Optional[str] = None
    final_decision: Optional[str] = None

    for rule in all_rules:
        matched = _rule_matches(rule, classification, command)
        trace = RuleTrace(
            rule_id=rule["id"],
            source=rule["source"],
            priority=rule["priority"],
            checked=True,
            matched=matched,
            reasons=list(rule.get("reasons", [])) if matched else [],
            decision=rule["decision"] if matched else None,
            decisive=False,
        )
        traces.append(trace)
        if matched and first_match_id is None:
            first_match_id = rule["id"]
            final_decision = rule["decision"]

    # Apply override_decisions strengthening to the decisive rule
    if engine.project_override and engine.project_override.override_decisions and first_match_id:
        strengthening_map = {
            od.rule_id: od.strengthen_to
            for od in engine.project_override.override_decisions
        }
        if first_match_id in strengthening_map:
            final_decision = strengthening_map[first_match_id]
            for trace in traces:
                if trace.rule_id == first_match_id:
                    trace.decision = final_decision
                    trace.reasons = trace.reasons + [
                        f"Project override strengthened decision to {final_decision}"
                    ]
                    break

    # Apply the same destructive hard-override logic as engine.evaluate()
    override_reason = None
    if "destructive" in classification.categories:
        if "/" in classification.command_family or classification.structure.get("has_pipe"):
            final_decision = "DENY"
            override_reason = "System-level destructive command detected."

    if final_decision is None:
        final_decision = "DENY"  # no rule matched — default deny

    # Mark the decisive trace
    decisive_id = first_match_id
    for trace in traces:
        if trace.rule_id == decisive_id:
            trace.decisive = True
            if override_reason:
                trace.reasons = [override_reason]
                trace.decision = "DENY"
            break

    return SimulationResult(
        command=command,
        decision=final_decision,
        risk_score=risk_result.risk_score,
        risk_band=risk_result.risk_band,
        rule_traces=traces,
        matched_rule=first_match_id,
        categories=classification.categories,
        capabilities=classification.capabilities,
        confidence=classification.confidence,
        project_override_loaded=engine.project_override is not None,
        project_override_path=(
            str(engine.project_override.config_path) if engine.project_override else None
        ),
        total_rules_checked=len(traces),
    )


def _collect_all_rules(engine: PolicyEngine, loader: RegistryLoader) -> list:
    """Collect all rules from all sources into a single flat list with source tags."""
    rules = []

    # 1. Project override additional_rules
    if engine.project_override:
        for rule in engine.project_override.additional_rules:
            rules.append({
                "id": rule.id,
                "source": "override",
                "priority": rule.priority,
                "decision": rule.decision,
                "reasons": list(rule.reasons),
                "match": dict(rule.match),
                "exclude": {},
            })

    # 2. Registry rules
    if loader.policy_registry:
        for entry in loader.policy_registry.policies:
            if entry.status != "active":
                continue
            rules.append({
                "id": entry.id,
                "source": "registry",
                "priority": entry.priority,
                "decision": entry.decision,
                "reasons": list(entry.reasons),
                "match": dict(entry.match),
                "exclude": dict(entry.exclude) if entry.exclude else {},
            })

    # 3. Hardcoded fallback rules (only added if no registry/override matched categories)
    # Always include them in the trace so users can see them
    for rule in PolicyEngine.FALLBACK_RULES:
        rules.append({
            "id": rule["id"],
            "source": "fallback",
            "priority": rule["priority"],
            "decision": rule["decision"],
            "reasons": list(rule["reasons"]),
            "match": {"categories": rule["categories"]},
            "exclude": {},
        })

    return rules


def _rule_matches(
    rule: dict,
    classification: ClassificationResult,
    command: str,
) -> bool:
    """Return True if the rule matches the classification and command."""
    match_spec = rule.get("match", {})

    # Empty match → matches everything
    if not match_spec:
        return True

    # command_pattern (override rules only, but support it for any rule)
    if "command_pattern" in match_spec:
        if not command:
            return False
        try:
            if not re.search(match_spec["command_pattern"], command):
                return False
        except re.error:
            return False
        # If only command_pattern, a match here is sufficient (fall through to other checks)

    # categories matching
    if "categories" in match_spec:
        if not any(cat in match_spec["categories"] for cat in classification.categories):
            return False

    # capabilities matching
    if "capabilities" in match_spec:
        if not any(cap in match_spec["capabilities"] for cap in classification.capabilities):
            return False

    # exclude capabilities
    exclude = rule.get("exclude", {})
    if exclude and "capabilities" in exclude:
        if any(cap in exclude["capabilities"] for cap in classification.capabilities):
            return False

    return True
