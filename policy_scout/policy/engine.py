"""Policy engine for making authorization decisions."""

from typing import Optional
from ..core.decision import PolicyDecision, RiskScore
from ..classify.command_classifier import ClassificationResult
from ..registry.models import PolicyRegistry


class PolicyEngine:
    """Evaluates classification and risk to produce policy decisions."""

    # Fallback policy rules for things not in registry
    FALLBACK_RULES = [
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

    def __init__(self, policy_registry: Optional[PolicyRegistry] = None):
        """Initialize policy engine with optional policy registry."""
        self.policy_registry = policy_registry

    def evaluate(
        self,
        classification: ClassificationResult,
        risk_score: RiskScore,
        request_id: str = "",
    ) -> PolicyDecision:
        """Evaluate classification and risk to produce a decision."""
        decision = PolicyDecision(request_id=request_id)
        decision.category = (
            classification.categories[0] if classification.categories else "unknown"
        )
        decision.risk_score = risk_score.risk_score
        decision.confidence = classification.confidence

        # Find matching policy rules from registry first
        matched_rules = []
        if self.policy_registry:
            matched_rules = self._match_from_registry(classification)

        # If no registry matches, try fallback rules
        if not matched_rules:
            matched_rules = self._match_fallback_rules(classification)

        # Sort by priority (higher priority first)
        matched_rules.sort(key=lambda r: r["priority"], reverse=True)

        if matched_rules:
            # Use highest priority matching rule
            decisive_rule = matched_rules[0]
            decision.decision = decisive_rule["decision"]
            decision.reasons = decisive_rule["reasons"]
            decision.recommended_next_action = (
                decisive_rule["recommended_next_action"] or ""
            )
            decision.policy_hits = [rule["id"] for rule in matched_rules]
        else:
            # No rule matched - deny by default for safety
            decision.decision = "DENY"
            decision.reasons = ["No policy rule matched this command."]
            decision.recommended_next_action = (
                "Review command and add policy rule if needed."
            )

        # Override for specific destructive patterns
        if "destructive" in classification.categories:
            # Check if it's a system-level destructive command
            if "/" in classification.command_family or classification.structure.get(
                "has_pipe"
            ):
                decision.decision = "DENY"
                decision.reasons = ["System-level destructive command detected."]
                decision.recommended_next_action = (
                    "This command is too dangerous to allow."
                )

        return decision

    def _match_from_registry(self, classification: ClassificationResult) -> list:
        """Match policies from registry."""
        matched = []

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

            # Policy matches if categories match AND (no capabilities specified OR capabilities match) AND not excluded
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
