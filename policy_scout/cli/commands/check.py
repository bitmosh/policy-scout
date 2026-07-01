"""check and print_human_output command handlers."""

import json
import sys
import os

from ...core.request import CommandRequest, Actor
from ...classify.shell_parser import ShellParser
from ...classify.command_classifier import CommandClassifier
from ...policy.risk_scorer import RiskScorer
from ...policy.engine import PolicyEngine
from ...registry.loader import RegistryLoader
from ...audit.store import AuditStore
from ...audit.redaction import redact_dict
from ...audit.events import (
    create_command_requested_event,
    create_command_parsed_event,
    create_command_classified_event,
    create_policy_matched_event,
    create_decision_issued_event,
    create_approval_requested_event,
    create_scout_report_generated_event,
)
from ...approvals.store import ApprovalStore
from ...approvals.models import ApprovalRequest, ApprovalStatus
from ...core.ids import generate_id
from ...reports.command_decision_report import generate_command_decision_report


def check_command(
    command: str,
    json_output: bool = False,
    audit_enabled: bool = True,
    approval_enabled: bool = True,
    report_enabled: bool = False,
    with_intel: bool = False,
) -> dict:
    """Check a command and return the decision."""
    # Initialize audit store
    audit_store = AuditStore(enabled=audit_enabled)

    # Initialize approval store
    approval_store = ApprovalStore() if approval_enabled else None

    # Load registries
    loader = RegistryLoader()
    command_registry = loader.command_registry
    policy_registry = loader.policy_registry

    # Create request
    request = CommandRequest(
        actor=Actor(type="human", name="cli_user"), command=command, cwd=os.getcwd()
    )

    # Write CommandRequested event
    if audit_store.enabled:
        audit_store.write(
            create_command_requested_event(
                request.request_id,
                command,
                actor={"type": request.actor.type, "name": request.actor.name},
            )
        )

    # Parse command
    parser = ShellParser()
    parse_result = parser.parse(command, request.request_id)

    # Write CommandParsed event
    if audit_store.enabled:
        audit_store.write(
            create_command_parsed_event(request.request_id, parse_result.to_dict())
        )

    # Classify command with registry
    classifier = CommandClassifier(command_registry=command_registry)
    classification = classifier.classify(parse_result, command, request.request_id)

    # Write CommandClassified event
    if audit_store.enabled:
        audit_store.write(
            create_command_classified_event(
                request.request_id, classification.to_dict()
            )
        )

    # ── Threat intelligence enrichment ───────────────────────────────────────
    intel_results = []
    if any(c in classification.categories for c in ("package_install", "package_execute")):
        try:
            from ...intel.adapter import build_default_chain
            from ...audit.events import EventType
            from ...audit.store import AuditEvent as _AuditEvent

            chain = build_default_chain(remote=with_intel)
            ecosystem_map = {"npm": "npm", "yarn": "npm", "pnpm": "npm", "bun": "npm",
                             "pip": "pypi", "pip3": "pypi", "uv": "pypi"}
            eco = ecosystem_map.get(classification.command_family)
            packages = []
            if eco and len(parse_result.args) >= 2 and parse_result.args[0] in ("install", "add", "i"):
                for arg in parse_result.args[1:]:
                    if not arg.startswith("-"):
                        name = arg.split("@")[0].split("==")[0].split(">=")[0].strip()
                        if name:
                            packages.append((eco, name))

            for ecosystem, pkg_name in packages:
                intel_result = chain.enrich_package(ecosystem, pkg_name)
                intel_results.append(intel_result)
                if audit_store.enabled:
                    if "cache" in intel_result.source:
                        evt_type = EventType.INTEL_CACHE_HIT
                    elif intel_result.error and not intel_result.has_findings:
                        evt_type = EventType.INTEL_LOOKUP_FAILED
                    else:
                        evt_type = EventType.INTEL_LOOKUP_COMPLETED
                    audit_store.write(_AuditEvent(
                        event_type=evt_type,
                        request_id=request.request_id,
                        summary=(
                            f"Intel lookup: {ecosystem}/{pkg_name} — "
                            f"{{'findings' if intel_result.has_findings else 'clean'}}"
                        ),
                        data={
                            "package": pkg_name,
                            "ecosystem": ecosystem,
                            "source": intel_result.source,
                            "has_findings": intel_result.has_findings,
                            "known_bad": intel_result.known_bad,
                            "typosquatting_count": len(intel_result.typosquatting_candidates),
                            "advisory_count": len(intel_result.advisories),
                            "error": intel_result.error,
                        },
                    ))
        except Exception:
            pass  # intel failures are non-fatal

    # Score risk (with intel findings if available)
    risk_scorer = RiskScorer()
    risk_score = risk_scorer.score(classification, request.request_id,
                                   intel_results=intel_results if intel_results else None)
    # Evaluate policy with registry
    policy_engine = PolicyEngine(policy_registry=policy_registry)
    decision = policy_engine.evaluate(
        classification, risk_score, request.request_id, command=request.command
    )

    # Write audit events for project override
    if audit_store.enabled:
        if policy_engine.project_override:
            from ...audit.events import EventType
            from ...audit.store import AuditEvent
            audit_store.write(AuditEvent(
                event_type=EventType.PROJECT_OVERRIDE_LOADED,
                request_id=request.request_id,
                summary=f"Project override loaded from {policy_engine.project_override.config_path}",
                data=policy_engine.project_override.to_dict(),
            ))
        elif policy_engine.override_violation:
            from ...audit.events import EventType
            from ...audit.store import AuditEvent
            audit_store.write(AuditEvent(
                event_type=EventType.PROJECT_OVERRIDE_VIOLATED,
                request_id=request.request_id,
                summary="Project override rejected (tighten-only violation)",
                data={"violation": policy_engine.override_violation, "fallback": "global policy"},
            ))

    # Write PolicyMatched event
    if audit_store.enabled and decision.policy_hits:
        audit_store.write(
            create_policy_matched_event(request.request_id, decision.policy_hits)
        )

    # Build result
    result = {
        "request_id": request.request_id,
        "command": command,
        "decision": decision.decision,
        "risk_score": decision.risk_score,
        "risk_band": risk_score.risk_band,
        "category": decision.category,
        "capabilities": classification.capabilities,
        "reasons": decision.reasons,
        "recommended_next_action": decision.recommended_next_action,
        "confidence": decision.confidence,
        "registry_hits": classification.registry_hits,
        "policy_hits": decision.policy_hits,
    }

    # Redact sensitive values from result for JSON output
    result = redact_dict(result)

    # Write DecisionIssued event
    if audit_store.enabled:
        audit_store.write(
            create_decision_issued_event(
                request.request_id,
                decision.decision,
                decision.risk_score,
                risk_score.risk_band,
                decision.reasons,
            )
        )

    # Create approval request for REQUIRE_APPROVAL decisions
    # Only for non-hard-denied commands
    if (
        approval_enabled
        and approval_store
        and decision.decision == "REQUIRE_APPROVAL"
    ):

        from ...core.config import get_approval_timeout_hours
        from ...core.ids import utcnow_plus_hours_iso
        approval = ApprovalRequest(
            request_id=request.request_id,
            decision_id=decision.decision,
            actor={"type": request.actor.type, "name": request.actor.name},
            command=command,
            cwd=os.getcwd(),
            risk_score=decision.risk_score,
            decision=decision.decision,
            reasons=decision.reasons,
            recommended_action=decision.recommended_next_action,
            status=ApprovalStatus.PENDING,
            expires_at=utcnow_plus_hours_iso(get_approval_timeout_hours()),
        )

        approval_store.save(approval)

        # Write ApprovalRequested event
        if audit_store.enabled:
            audit_store.write(
                create_approval_requested_event(
                    request.request_id,
                    approval.approval_id,
                    command,
                    actor={"type": request.actor.type, "name": request.actor.name},
                )
            )

    # Generate report if requested and decision is high-friction
    if report_enabled and decision.decision in [
        "DENY",
        "DENY_AND_ALERT",
        "REQUIRE_APPROVAL",
    ]:
        try:
            report = generate_command_decision_report(
                request_id=request.request_id,
                command=command,
                decision=decision.decision,
                risk_score=decision.risk_score,
                risk_band=risk_score.risk_band,
                category=decision.category,
                reasons=decision.reasons,
            )

            # Write ScoutReportGenerated event
            if audit_store.enabled:
                audit_store.write(
                    create_scout_report_generated_event(
                        request_id=request.request_id,
                        report_id=report.report_id,
                        report_type=report.report_type,
                        report_path=report.markdown_path,
                    )
                )

            # Print report paths
            print()
            print("Scout Report generated:")
            print(f"  Markdown: {report.markdown_path}")
            print(f"  JSON: {report.json_path}")
        except Exception as e:
            print(f"Warning: Failed to generate report: {e}", file=sys.stderr)

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print_human_output(result)

    return result


def print_human_output(result: dict):
    """Print human-readable output."""
    print("Policy Scout Check")
    print()
    print("Command:")
    print(f"  {result['command']}")
    print()
    print("Decision:")
    print(f"  {result['decision']}")
    print()
    print("Risk:")
    print(f"  {result['risk_score']}/10 ({result['risk_band']})")
    print()
    print("Category:")
    print(f"  {result['category']}")
    print()
    if result["capabilities"]:
        print("Capabilities:")
        for cap in result["capabilities"]:
            print(f"  - {cap}")
        print()
    print("Why:")
    for reason in result["reasons"]:
        print(f"  - {reason}")
    print()
    if result["recommended_next_action"]:
        print("Recommended:")
        print(f"  {result['recommended_next_action']}")
        print()
