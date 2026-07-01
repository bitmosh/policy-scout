"""Policy engine for making authorization decisions."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional

from ..core.decision import PolicyDecision, RiskScore
from ..classify.command_classifier import ClassificationResult
from ..registry.models import PolicyRegistry

# project_override is imported lazily inside _load_override() to avoid a
# circular import: engine → management.project_override → management.__init__
# → simulator → engine.
if TYPE_CHECKING:
    from ..policy.management.project_override import ProjectOverride


class PolicyEngine:
    """Evaluates classification and risk to produce policy decisions."""

    # Fallback policy rules for things not in registry
    FALLBACK_RULES: list[dict[str, Any]] = [
        {
            "id": "destructive_system_deny",
            "priority": 975,
            "categories": ["destructive"],
            "decision": "DENY",
            "reasons": ["The command can cause destructive filesystem mutation."],
            "recommended_next_action": "Review destructive command carefully.",
        },
        {
            "id": "unknown_require_approval",
            "priority": 650,
            "categories": ["unknown"],
            "decision": "REQUIRE_APPROVAL",
            "reasons": [
                "Policy Scout could not confidently classify this command.",
                "Unknown commands should be reviewed before execution.",
            ],
            "recommended_next_action": "Review command before approval.",
        },
    ]

    def __init__(
        self,
        policy_registry: Optional[PolicyRegistry] = None,
        config_override: Optional[Path | Literal["none"]] = None,
    ):
        self.policy_registry = policy_registry
        self._override_violation: Optional[str] = None  # set if override was rejected
        self._project_override: Optional[ProjectOverride] = self._load_override(config_override)

    def _load_override(
        self,
        config_override: Optional[Path | Literal["none"]],
    ):
        if config_override == "none":
            return None
        from ..policy.management.project_override import (
            load_project_override,
            PolicyOverrideViolation,
        )
        try:
            if isinstance(config_override, Path):
                return load_project_override(
                    cwd=config_override.parent if config_override.is_file() else config_override
                )
            return load_project_override()
        except PolicyOverrideViolation as exc:
            self._override_violation = str(exc)
            return None
        except Exception:
            return None

    @property
    def project_override(self) -> Optional[ProjectOverride]:
        return self._project_override

    @property
    def override_violation(self) -> Optional[str]:
        """Non-None if a project override was found but rejected (tighten-only violation)."""
        return self._override_violation

    def evaluate(
        self,
        classification: ClassificationResult,
        risk_score: RiskScore,
        request_id: str = "",
        command: str = "",
    ) -> PolicyDecision:
        """Evaluate classification and risk to produce a decision."""
        # Lockdown check: when active, force DENY for everything except safe reads
        try:
            from ..response.lockdown import is_lockdown_active
            if is_lockdown_active():
                decision = PolicyDecision(request_id=request_id)
                decision.category = (
                    classification.categories[0] if classification.categories else "unknown"
                )
                decision.risk_score = risk_score.risk_score
                decision.confidence = classification.confidence
                if "safe_read" in classification.categories:
                    decision.decision = "ALLOW_LOGGED"
                    decision.reasons = ["Lockdown active — safe reads logged."]
                    decision.recommended_next_action = "Deactivate lockdown when investigation is complete."
                else:
                    decision.decision = "DENY"
                    decision.reasons = [
                        "Policy Scout is in lockdown mode.",
                        "All non-read operations are blocked until lockdown is deactivated.",
                    ]
                    decision.recommended_next_action = (
                        "Run 'policy-scout clearance' to check system state, "
                        "then 'policy-scout lockdown off' to deactivate."
                    )
                return decision
        except ImportError:
            pass  # lockdown module unavailable — continue normal evaluation
        except Exception as exc:
            import sys
            print(f"Warning: lockdown check failed, proceeding as unlocked: {exc}", file=sys.stderr)

        decision = PolicyDecision(request_id=request_id)
        decision.category = (
            classification.categories[0] if classification.categories else "unknown"
        )
        decision.risk_score = risk_score.risk_score
        decision.confidence = classification.confidence

        # Build combined rule list:
        #   1. project override additional_rules (prepended — fire first)
        #   2. global registry rules
        # Falls back to hardcoded fallback rules if neither matched.
        matched_rules = []

        if self._project_override:
            matched_rules.extend(
                self._match_override_rules(classification, command)
            )

        if self.policy_registry:
            matched_rules.extend(self._match_from_registry(classification))

        if not matched_rules:
            matched_rules = self._match_fallback_rules(classification)

        # Structural destructive override: full-path binary or piped destructive
        # command gets a higher-priority DENY injected into the rule chain so
        # policy simulate sees the same outcome as the final decision.
        if "destructive" in classification.categories:
            if "/" in classification.command_family or classification.structure.get("has_pipe"):
                matched_rules.append({
                    "id": "system_destructive_structural_deny",
                    "priority": 990,
                    "decision": "DENY",
                    "reasons": ["System-level destructive command detected."],
                    "recommended_next_action": "This command is too dangerous to allow.",
                })

        # Sort by priority (higher priority first)
        matched_rules.sort(key=lambda r: r["priority"], reverse=True)

        # Apply override_decisions strengthening before selecting the winner
        if self._project_override and matched_rules:
            matched_rules = self._apply_decision_strengthening(matched_rules)

        if matched_rules:
            decisive_rule = matched_rules[0]
            decision.decision = decisive_rule["decision"]
            decision.reasons = decisive_rule["reasons"]
            decision.recommended_next_action = (
                decisive_rule["recommended_next_action"] or ""
            )
            decision.policy_hits = [rule["id"] for rule in matched_rules]
        else:
            decision.decision = "DENY"
            decision.reasons = ["No policy rule matched this command."]
            decision.recommended_next_action = (
                "Review command and add policy rule if needed."
            )

        return decision

    def _match_override_rules(
        self,
        classification: ClassificationResult,
        command: str,
    ) -> list:
        """Match project override additional_rules against classification + raw command."""
        if not self._project_override:
            return []

        matched = []
        for rule in self._project_override.additional_rules:
            match_spec = rule.match

            # Empty match dict → matches everything
            if not match_spec:
                matched.append({
                    "id": rule.id,
                    "priority": rule.priority,
                    "decision": rule.decision,
                    "reasons": rule.reasons or [rule.description or rule.id],
                    "recommended_next_action": "",
                })
                continue

            # command_pattern matching (requires raw command string)
            if "command_pattern" in match_spec:
                if not command:
                    continue  # can't match without command; skip this rule
                try:
                    if not re.search(match_spec["command_pattern"], command):
                        continue
                except re.error:
                    continue

            # categories matching (same semantics as global registry)
            if "categories" in match_spec:
                if not any(
                    cat in match_spec["categories"]
                    for cat in classification.categories
                ):
                    continue

            matched.append({
                "id": rule.id,
                "priority": rule.priority,
                "decision": rule.decision,
                "reasons": rule.reasons or [rule.description or rule.id],
                "recommended_next_action": "",
            })

        return matched

    def _apply_decision_strengthening(self, matched_rules: list) -> list:
        """Apply override_decisions strengthening to matched rules."""
        if not self._project_override or not self._project_override.override_decisions:
            return matched_rules

        strengthening_map = {
            od.rule_id: od.strengthen_to
            for od in self._project_override.override_decisions
        }

        result = []
        for rule in matched_rules:
            if rule["id"] in strengthening_map:
                rule = dict(rule)  # copy before mutating
                rule["decision"] = strengthening_map[rule["id"]]
                rule["reasons"] = rule["reasons"] + [
                    f"Project override strengthened decision to {rule['decision']}"
                ]
            result.append(rule)
        return result

    def _match_from_registry(self, classification: ClassificationResult) -> list:
        """Match policies from registry."""
        matched: list[dict[str, Any]] = []

        if not self.policy_registry:
            return matched

        for entry in self.policy_registry.policies:
            if entry.status != "active":
                continue

            # Check category match
            category_match = False
            if "categories" in entry.match:
                if any(
                    cat in entry.match["categories"]
                    for cat in classification.categories
                ):
                    category_match = True

            # Check capability match (if specified)
            capability_match = True
            if "capabilities" in entry.match:
                if any(
                    cap in entry.match["capabilities"]
                    for cap in classification.capabilities
                ):
                    capability_match = True
                else:
                    capability_match = False

            # Check exclude (if specified)
            exclude_match = True
            if entry.exclude and "capabilities" in entry.exclude:
                if any(
                    cap in entry.exclude["capabilities"]
                    for cap in classification.capabilities
                ):
                    exclude_match = False

            if category_match and capability_match and exclude_match:
                matched.append(
                    {
                        "id": entry.id,
                        "priority": entry.priority,
                        "decision": entry.decision,
                        "reasons": entry.reasons,
                        "recommended_next_action": entry.recommended_next_action or "",
                    }
                )

        return matched

    def _match_fallback_rules(self, classification: ClassificationResult) -> list:
        """Match fallback hardcoded rules."""
        matched = []

        for rule in self.FALLBACK_RULES:
            if any(cat in rule["categories"] for cat in classification.categories):
                matched.append(rule)

        return matched
