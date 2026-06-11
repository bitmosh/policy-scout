"""Risk scoring with component-based evaluation."""

from typing import TYPE_CHECKING, Literal, Optional
from ..core.decision import RiskScore
from ..classify.command_classifier import ClassificationResult

if TYPE_CHECKING:
    from ..intel.adapter import IntelResult


class RiskScorer:
    """Computes granular risk scores from classification results."""

    # Risk component weights
    COMPONENT_WEIGHTS = {
        "package_install": 2,
        "package_execute": 3,
        "network_fetch": 1,
        "network_execute": 4,
        "credential_adjacent": 5,
        "destructive": 4,
        "lifecycle_script_possible": 2,
        "actor_trust_penalty": 1,
        "shell_complexity": 1,
        # Intel-derived components (weights can exceed base to force high/critical)
        "known_bad_package": 9,
        "typosquatting_risk": 6,
        "known_advisory_critical": 8,
        "known_advisory_high": 5,
        "known_advisory_medium": 2,
        "lockfile_integrity_fail": 4,
    }

    def score(
        self,
        classification: ClassificationResult,
        request_id: str = "",
        intel_results: Optional[list["IntelResult"]] = None,
    ) -> RiskScore:
        """Compute risk score from classification result and optional intel."""
        risk = RiskScore(request_id=request_id)

        # Initialize components
        components = {}

        # Score based on categories
        for category in classification.categories:
            if category == "package_install":
                components["package_install"] = 2
                components["lifecycle_script_possible"] = 2
                components["network_fetch"] = 1
            elif category == "package_execute":
                components["package_execute"] = 3
                components["network_fetch"] = 1
            elif category == "network_execute":
                components["network_execute"] = 4
                components["shell.execute"] = 2
            elif category == "credential_adjacent":
                components["credential_adjacent"] = 5
            elif category == "destructive":
                components["destructive"] = 4
            elif category == "network_fetch":
                components["network_fetch"] = 1
            elif category == "safe_read":
                components["safe_read"] = 0
            elif category == "local_inspection":
                components["local_inspection"] = 0
            elif category == "unknown":
                components["unknown"] = 2

        # Add shell complexity penalty
        shell_complexity = classification.structure.get("shell_complexity", 1)
        if shell_complexity > 3:
            components["shell_complexity"] = min(shell_complexity - 3, 2)

        # Add actor trust penalty (for now, assume untrusted agent)
        components["actor_trust_penalty"] = 1

        # ── Intel-derived components ──────────────────────────────────────────
        if intel_results:
            for intel in intel_results:
                if intel.known_bad:
                    components["known_bad_package"] = 9
                if intel.typosquatting_candidates:
                    components["typosquatting_risk"] = max(
                        components.get("typosquatting_risk", 0), 6
                    )
                for adv in intel.advisories:
                    if adv.severity == "critical":
                        components["known_advisory_critical"] = max(
                            components.get("known_advisory_critical", 0), 8
                        )
                    elif adv.severity == "high":
                        components["known_advisory_high"] = max(
                            components.get("known_advisory_high", 0), 5
                        )
                    elif adv.severity == "medium":
                        if "known_advisory_critical" not in components and "known_advisory_high" not in components:
                            components["known_advisory_medium"] = max(
                                components.get("known_advisory_medium", 0), 2
                            )
                if intel.lockfile_integrity_ok is False:
                    components["lockfile_integrity_fail"] = max(
                        components.get("lockfile_integrity_fail", 0), 4
                    )

        risk.components = components

        # Calculate final score
        risk.risk_score = sum(components.values())

        # Clamp to 0-10
        risk.risk_score = min(max(risk.risk_score, 0), 10)

        # Determine risk band
        risk.risk_band = self._get_risk_band(risk.risk_score)

        # Set confidence based on classification confidence
        risk.confidence = classification.confidence

        # Evidence strength based on classification method and confidence
        if (
            classification.classification_method == "pattern_match"
            and classification.confidence >= 0.9
        ):
            risk.evidence_strength = 0.9
        elif classification.confidence >= 0.7:
            risk.evidence_strength = 0.7
        else:
            risk.evidence_strength = 0.5

        return risk

    def _get_risk_band(
        self, score: int
    ) -> Literal["low", "medium", "high", "critical"]:
        """Convert numeric score to risk band."""
        if score <= 2:
            return "low"
        elif score <= 4:
            return "medium"
        elif score <= 7:
            return "high"
        else:
            return "critical"
