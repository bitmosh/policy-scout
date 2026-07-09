# SPDX-License-Identifier: Apache-2.0
"""policy command handler and helpers."""

import json
import sys


def handle_policy_command(args) -> None:
    """Handle all policy subcommands."""
    from ...policy.management.simulator import simulate, SimulationResult
    from ...registry.loader import RegistryLoader
    from pathlib import Path as _Path

    sub = getattr(args, "policy_subcommand", None)
    if not sub:
        print("Error: No policy subcommand provided. Use: simulate, show", file=sys.stderr)
        sys.exit(1)

    if sub == "simulate":
        raw_parts = args.command
        # Strip leading "--" separator if present
        if raw_parts and raw_parts[0] == "--":
            raw_parts = raw_parts[1:]
        command_str = " ".join(raw_parts)
        if not command_str:
            print("Error: No command provided to simulate", file=sys.stderr)
            sys.exit(1)

        cwd = _Path(args.cwd) if getattr(args, "cwd", None) else None
        result = simulate(command_str, cwd=cwd)

        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_simulation_result(result)

    elif sub == "show":
        cwd = _Path(args.cwd) if getattr(args, "cwd", None) else None
        effective = getattr(args, "effective", False)
        loader = RegistryLoader()

        from ...policy.management.project_override import load_project_override
        override = load_project_override(cwd=cwd) if effective else None

        if getattr(args, "json", False):
            out: dict = {
                "registry_version": loader.policy_registry.version if loader.policy_registry else None,
                "rules": [],
                "project_override": override.to_dict() if override else None,
            }
            if loader.policy_registry:
                for entry in loader.policy_registry.policies:
                    out["rules"].append({
                        "id": entry.id,
                        "priority": entry.priority,
                        "decision": entry.decision,
                        "status": entry.status,
                        "source": "registry",
                    })
            if override:
                for rule in override.additional_rules:
                    out["rules"].append({
                        "id": rule.id,
                        "priority": rule.priority,
                        "decision": rule.decision,
                        "source": "override",
                    })
            print(json.dumps(out, indent=2))
        else:
            _print_policy_show(loader, override)

    elif sub == "test":
        if not getattr(args, "against_history", False):
            print(
                "Error: Specify a test mode. Currently supported: --against-history",
                file=sys.stderr,
            )
            sys.exit(1)
        from ...policy.management.history_tester import test_against_history
        cwd = _Path(args.cwd) if getattr(args, "cwd", None) else None
        days = getattr(args, "days", 7)
        result = test_against_history(days=days, cwd=cwd)

        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_history_test_result(result)

    elif sub == "validate":
        from ...policy.management.validator import validate_policy
        strict = getattr(args, "strict", False)
        result = validate_policy(strict=strict)

        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_validation_result(result)

        if not result.is_valid:
            sys.exit(1)

    elif sub == "commit":
        from ...policy.management.policy_commit import commit_policy_state
        message = getattr(args, "message", None)
        try:
            sha = commit_policy_state(message=message)
            print(f"Policy snapshot committed: {sha}")
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Error: Unknown policy subcommand: {sub}", file=sys.stderr)
        sys.exit(1)


def _print_simulation_result(result) -> None:
    """Print human-readable simulation output."""
    DECISION_COLORS = {
        "ALLOW": "ALLOW",
        "ALLOW_LOGGED": "ALLOW_LOGGED",
        "REQUIRE_APPROVAL": "REQUIRE_APPROVAL",
        "SANDBOX_FIRST": "SANDBOX_FIRST",
        "DENY": "DENY",
        "DENY_AND_ALERT": "DENY_AND_ALERT",
    }
    decision = DECISION_COLORS.get(result.decision, result.decision)

    print(f"\nCommand:    {result.command}")
    print(f"Decision:   {decision}")
    print(f"Risk:       {result.risk_score} / 10 ({result.risk_band})")

    if result.matched_rule:
        matched_index = next(
            (i + 1 for i, t in enumerate(result.rule_traces) if t.decisive),
            None,
        )
        print(
            f"Matched:    {result.matched_rule}"
            + (f" (rule {matched_index} of {result.total_rules_checked})" if matched_index else "")
        )
    else:
        print("Matched:    (no rule matched — default DENY)")

    if result.categories:
        print(f"Categories: {', '.join(result.categories)}")
    if result.capabilities:
        print(f"Caps:       {', '.join(result.capabilities)}")

    if result.project_override_loaded:
        print(f"Override:   {result.project_override_path}")

    print("\nRule trace:")
    for trace in result.rule_traces:
        source_tag = f"[{trace.source}]"
        if trace.decisive:
            marker = "→"
            detail = f"MATCHED → {trace.decision}"
            print(f"  {marker} {trace.rule_id:<40} {source_tag:<12} {detail}")
            for reason in trace.reasons:
                print(f"      - {reason}")
        elif trace.matched:
            print(f"    {trace.rule_id:<40} {source_tag:<12} matched (lower priority — not decisive)")
        else:
            print(f"    {trace.rule_id:<40} {source_tag:<12} no match")
    print()


def _print_history_test_result(result) -> None:
    """Print human-readable history test output."""
    print(f"\nTested {result.total} historical decisions from the last {result.days} days.\n")
    if result.skipped:
        print(f"  Skipped: {result.skipped} events (missing command data)\n")
    if result.changed == 0:
        print("  No decisions would change under the current policy.")
    else:
        print(f"  Changed: {result.changed} / {result.total}")
        if result.tightened:
            print(f"    {result.tightened} decisions became more restrictive")
        if result.loosened:
            print(f"    {result.loosened} decisions became less restrictive")
        print("\nChanged decisions:")
        for case in result.changed_cases[:20]:
            direction = f"[{case.direction}]" if case.direction else ""
            print(
                f"  [{case.timestamp[:19]}] {repr(case.command)[:60]:<62} "
                f"{case.original_decision} → {case.simulated_decision} {direction}"
            )
        if len(result.changed_cases) > 20:
            print(f"  ... and {len(result.changed_cases) - 20} more")
    print()


def _print_validation_result(result) -> None:
    """Print human-readable validation output."""
    print(
        f"\nPolicy validation: checked {result.rules_checked} rules, "
        f"{result.eval_cases_checked} eval cases.\n"
    )
    if not result.issues:
        print("  No issues found — policy is valid.")
    else:
        errors = [i for i in result.issues if i.severity == "error"]
        warnings = [i for i in result.issues if i.severity == "warning"]
        if errors:
            print(f"  Errors ({len(errors)}):")
            for issue in errors:
                print(f"    [{issue.issue_type}] {issue.rule_id}: {issue.description}")
        if warnings:
            print(f"  Warnings ({len(warnings)}):")
            for issue in warnings:
                print(f"    [{issue.issue_type}] {issue.rule_id}: {issue.description}")
    print()


def _print_policy_show(loader, override) -> None:
    """Print human-readable effective policy."""
    registry = loader.policy_registry
    print("\nEffective policy rules (sorted by priority, highest first):\n")

    rules = []
    if registry:
        for entry in registry.policies:
            rules.append({
                "id": entry.id,
                "priority": entry.priority,
                "decision": entry.decision,
                "status": entry.status,
                "source": "registry",
            })

    if override:
        for rule in override.additional_rules:
            rules.append({
                "id": rule.id,
                "priority": rule.priority,
                "decision": rule.decision,
                "status": "active",
                "source": "override",
            })

    rules.sort(key=lambda r: r["priority"], reverse=True)

    for rule in rules:
        status = "" if rule["status"] == "active" else f" [{rule['status']}]"
        src = f"({rule['source']})"
        print(f"  {rule['priority']:>4}  {rule['id']:<45} {rule['decision']:<20} {src}{status}")

    if override:
        print(f"\nProject override: {override.config_path} (version: {override.version or 'unversioned'})")
        if override.override_decisions:
            print("  Strengthened decisions:")
            for od in override.override_decisions:
                print(f"    {od.rule_id} → {od.strengthen_to}")
    print()
