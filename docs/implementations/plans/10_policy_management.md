# Implementation Plan — Gap 10: Policy Management Tooling

## Problem
Policy registries are static YAML files. You edit them and restart. You can't simulate the effect of a change against historical decisions, detect contradictory rules, or understand what a new rule would actually change. Discovering a misconfigured policy from a failed real-world decision is the worst way to find the bug.

## Goal
Policy simulation against historical audit data, conflict/dead-code detection in the registry, per-project policy overrides, and policy versioning via git.

---

## New Module: `policy_scout/policy/management/`

```
policy_scout/policy/management/
├── __init__.py
├── simulator.py        # re-evaluate commands against a policy variant
├── validator.py        # conflict + dead-code detection
├── history_tester.py   # dry-run policy against audit history
└── project_override.py # load + merge per-project .policy-scout.yaml
```

---

## Implementation Approach

### Step 1 — Policy Simulator (`management/simulator.py`)

The simulator evaluates a command against the current (or a candidate) policy and returns the full evaluation trace — every rule that was checked, in what order, and why it matched or didn't.

```python
@dataclass
class RuleTrace:
    rule_id: str
    checked: bool
    matched: bool
    reasons: list[str]
    decision: str | None   # only if this rule made the final decision

@dataclass
class SimulationResult:
    command: str
    decision: str
    risk_score: float
    risk_band: str
    rule_traces: list[RuleTrace]
    classification: ClassificationResult
    registry_hits: list[str]
    matched_rule: str | None   # the rule that produced the final decision

def simulate(command: str, policy_override: dict | None = None) -> SimulationResult:
    """
    Evaluate command against current policy (or a provided override),
    returning the full rule trace rather than just the final decision.
    """
    policy = load_policy(override=policy_override)
    request = build_request(command, actor_type="agent")
    classification = classifier.classify(request)
    risk = risk_scorer.score(classification)

    traces = []
    final_decision = None
    matched_rule = None

    for rule in policy.rules:
        matched = rule.matches(classification)
        trace = RuleTrace(
            rule_id=rule.id,
            checked=True,
            matched=matched,
            reasons=rule.reasons if matched else [],
            decision=rule.decision if matched else None,
        )
        traces.append(trace)
        if matched and final_decision is None:
            final_decision = rule.decision
            matched_rule = rule.id

    return SimulationResult(
        command=command,
        decision=final_decision or "ALLOW",
        risk_score=risk.score,
        risk_band=risk.band,
        rule_traces=traces,
        classification=classification,
        registry_hits=classification.registry_hits,
        matched_rule=matched_rule,
    )
```

The key difference from `policy-scout check` is that `simulate` returns the full trace, not just the decision. This is the debugging tool.

**CLI output:**

```
$ policy-scout policy simulate -- npm install lodash

Command:    npm install lodash
Decision:   SANDBOX_FIRST
Risk:       7.0 / 10 (high)
Matched:    package_install_sandbox (rule 3 of 11)

Rule trace:
  ✓ safe_read_allow     — did not match (no safe_read capability)
  ✓ credential_deny     — did not match (no credential_adjacent capability)
  ✓ package_install_sandbox — MATCHED → SANDBOX_FIRST
    - Package installs may execute lifecycle scripts
    - Package installs download third-party code
  (8 subsequent rules not evaluated — decision reached)
```

### Step 2 — History Tester (`management/history_tester.py`)

Re-evaluate the last N days of audit events against the current (or candidate) policy, compare against the recorded decisions, and show what would have changed.

```python
def test_against_history(
    days: int = 7,
    policy_override: dict | None = None,
) -> HistoryTestResult:
    events = audit_store.get_events_by_type("DecisionIssued", since_days=days)
    results = []

    for event in events:
        original_decision = event.data["decision"]
        command = event.data["command"]

        sim = simulate(command, policy_override=policy_override)
        changed = sim.decision != original_decision

        results.append(HistoryTestCase(
            event_id=event.event_id,
            timestamp=event.timestamp,
            command=command,
            original_decision=original_decision,
            simulated_decision=sim.decision,
            changed=changed,
            matched_rule=sim.matched_rule,
        ))

    changed = [r for r in results if r.changed]
    return HistoryTestResult(
        total=len(results),
        changed=len(changed),
        unchanged=len(results) - len(changed),
        changed_cases=changed,
    )
```

**CLI output:**

```
$ policy-scout policy test --against-history --days 7

Evaluated 847 historical decisions against current policy.

Changed: 12 / 847
  2 decisions became more restrictive (ALLOW → REQUIRE_APPROVAL)
  10 decisions became less restrictive (REQUIRE_APPROVAL → ALLOW_LOGGED)

Changed decisions:
  [2026-06-08T14:23:11] 'git push --force' : DENY → REQUIRE_APPROVAL
  [2026-06-07T09:11:44] 'npm run build'    : ALLOW_LOGGED → ALLOW
  ...
```

This is critical before deploying a policy change. "My new rule changes 2 decisions over the last week, both in the expected direction" is a confident deployment. "My new rule changes 200 decisions" is a misconfiguration.

### Step 3 — Policy Validator (`management/validator.py`)

Check the loaded policy for correctness issues:

```python
@dataclass
class PolicyIssue:
    issue_type: str   # "unreachable_rule" | "conflict" | "missing_coverage"
    rule_id: str
    description: str
    severity: str     # "warning" | "error"

def validate_policy(policy: Policy) -> list[PolicyIssue]:
    issues = []
    issues.extend(_check_unreachable_rules(policy))
    issues.extend(_check_contradictions(policy))
    issues.extend(_check_missing_coverage(policy))
    return issues

def _check_unreachable_rules(policy: Policy) -> list[PolicyIssue]:
    """
    A rule is unreachable if a preceding rule with a broader or equal matcher
    always fires first, meaning this rule can never be the first match.
    """
    for i, rule in enumerate(policy.rules):
        for prev_rule in policy.rules[:i]:
            if _subsumes(prev_rule.matcher, rule.matcher):
                yield PolicyIssue(
                    issue_type="unreachable_rule",
                    rule_id=rule.id,
                    description=f"Rule '{rule.id}' is unreachable — rule '{prev_rule.id}' always matches first.",
                    severity="warning",
                )

def _check_contradictions(policy: Policy) -> list[PolicyIssue]:
    """
    Two rules with the same or equivalent matchers but different decisions.
    """
    for i, rule_a in enumerate(policy.rules):
        for rule_b in policy.rules[i+1:]:
            if _equivalent_matchers(rule_a.matcher, rule_b.matcher):
                if rule_a.decision != rule_b.decision:
                    yield PolicyIssue(
                        issue_type="contradiction",
                        rule_id=rule_b.id,
                        description=f"Rules '{rule_a.id}' and '{rule_b.id}' have equivalent matchers but different decisions.",
                        severity="error",
                    )

def _check_missing_coverage(policy: Policy) -> list[PolicyIssue]:
    """
    Check if any well-known capability combination has no matching rule.
    Uses the eval suite cases as the reference set.
    """
    eval_cases = load_eval_cases()
    for case in eval_cases:
        sim = simulate(case.command)
        if sim.matched_rule is None:
            yield PolicyIssue(
                issue_type="missing_coverage",
                rule_id="(none)",
                description=f"No rule matched eval case '{case.id}' (command: {case.command!r}). Fell through to default ALLOW.",
                severity="warning",
            )
```

### Step 4 — Per-Project Policy Override (`management/project_override.py`)

A `.policy-scout.yaml` file in the project root can tighten global policy:

```yaml
# .policy-scout.yaml — project-level policy overrides
# These can only TIGHTEN global policy, not loosen it.

mode: paranoid               # override enforcement mode for this project

additional_rules:
  - id: deny_python_scripts
    description: "This project should not run arbitrary Python scripts through the agent"
    match:
      command_pattern: '^python\s'
    decision: REQUIRE_APPROVAL
    reasons:
      - "Python execution is restricted in this project"

override_decisions:
  # Strengthen a global REQUIRE_APPROVAL to DENY for this project
  - rule_id: destructive_deny
    strengthen_to: DENY_AND_ALERT

intel:
  remote: true     # enable remote intel for this project specifically

scan:
  pre_commit: true  # auto-scan staged files in this project
```

**Loading:**

```python
def load_project_override(cwd: Path) -> ProjectOverride | None:
    config_path = cwd / ".policy-scout.yaml"
    if not config_path.exists():
        return None
    raw = yaml.safe_load(config_path.read_text())
    override = ProjectOverride.from_dict(raw)
    _validate_override_only_tightens(override)  # raises if it loosens global policy
    return override
```

The validation step ensures project overrides cannot loosen global policy — they can only add rules, strengthen decisions, or change the mode to something stricter. This prevents a compromised project config from weakening security posture.

In the policy engine:

```python
def decide(self, request: CommandRequest) -> PolicyDecision:
    override = load_project_override(Path.cwd())
    effective_policy = merge_policies(self._global_policy, override)
    ...
```

### Step 5 — Policy Versioning

A `policy-scout policy commit` command snapshots the current registry state into git:

```python
def commit_policy_state(message: str | None = None) -> None:
    registry_dir = Path(__file__).parent.parent / "data"
    policy_files = [
        registry_dir / "command_registry.yaml",
        registry_dir / "default_policy.yaml",
        registry_dir / "suspicious_patterns.yaml",
    ]

    # Run git add on just the policy files
    subprocess.run(["git", "add"] + [str(p) for p in policy_files], check=True)

    commit_msg = message or f"policy: snapshot registry state [{datetime.now().strftime('%Y-%m-%d')}]"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
```

This works only when Policy Scout is installed in a git repo (which it typically is, as part of the project). The command is advisory — it makes policy evolution visible in git history alongside code changes.

---

## CLI Commands

```bash
# Simulate a command against current (or candidate) policy
policy-scout policy simulate -- npm install lodash
policy-scout policy simulate --policy-file /path/to/candidate.yaml -- npm install lodash

# Test policy against recent history
policy-scout policy test --against-history                # last 7 days
policy-scout policy test --against-history --days 30      # last 30 days
policy-scout policy test --against-history --policy-file /path/to/candidate.yaml

# Validate current policy
policy-scout policy validate
policy-scout policy validate --strict    # treat warnings as errors

# Show effective policy (global + project override merged)
policy-scout policy show
policy-scout policy show --effective     # show with project override applied

# Commit policy state to git
policy-scout policy commit
policy-scout policy commit --message "tighten: require approval for all pip installs"
```

---

## New Audit Event Types

```
PolicySimulated         — simulation ran (command, result, matched_rule)
PolicyValidated         — validation ran (issues found)
PolicyHistoryTested     — history test ran (changed count, period)
ProjectOverrideLoaded   — .policy-scout.yaml was loaded
```

---

## Integration Points

- `policy/engine.py` — add `project_override` merging at decision time
- `policy/engine.py` — expose `simulate()` as a public method
- `cli/main.py` — register `policy` command group
- `audit/events.py` — four new event types
- `registry/validator.py` (existing) — extend with the new checks
- `doctor.py` — run `validate_policy()` and report issues

---

## Test Strategy

- Unit test `simulate()` returns correct matched_rule for each decision type
- Unit test `test_against_history()` with mocked audit events and a policy that changes two decisions
- Unit test `_check_unreachable_rules()` with a known-unreachable rule fixture
- Unit test `_check_contradictions()` with two rules that have equivalent matchers
- Unit test `load_project_override()` with a valid and an invalid (loosening) override
- Unit test `merge_policies()` correctly applies override tightening
- Regression: existing eval suite must produce identical results before and after this change

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `simulator.py` | ~200 | Medium |
| `history_tester.py` | ~180 | Medium |
| `validator.py` (new checks) | ~250 | Medium-High |
| `project_override.py` | ~200 | Medium |
| Policy engine integration | ~60 delta | Low |
| CLI commands | ~200 | Medium |
| Tests | ~400 | Medium-High |
| **Total** | **~1490** | |

---

## Open Questions

1. Should `simulate` write an audit event? Recommendation: yes, but as a lightweight `PolicySimulated` event — simulations shouldn't trigger the same audit weight as real decisions. Flag them as `dry_run: true`.
2. Should per-project `.policy-scout.yaml` be checked into the project repo? Recommendation: yes — it's a security configuration file and should be versioned alongside the project. Note that a malicious PR could try to modify it, which is itself a finding for the workflow injection detector.
3. What's the right fallback when no rule matches? Currently it's implicitly `ALLOW`. Should the validator warn when any command could fall through? Recommendation: yes — the validator should require an explicit catch-all rule (e.g., `match: {}` → `ALLOW_LOGGED`) rather than silently allowing unmatched commands.
