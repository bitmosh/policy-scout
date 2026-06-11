# ADR-002: Policy Config Precedence and Project Override Contract

**Status:** Accepted  
**Date:** 2026-06-10  
**Deciders:** Developer (bitmosh)  
**Related Plans:** [10_policy_management.md](../implementations/plans/10_policy_management.md), [12_git_integration.md](../implementations/plans/12_git_integration.md)  
**Related ADRs:** [ADR-001](ADR-001-mcp-transport-and-trust-model.md) (MCP session trust reads from the same config chain), [ADR-003](ADR-003-graph-export-contract.md) (policy version is a graph node property)

---

## Context

Policy Scout currently has exactly one source of policy truth: the built-in `data/default_policy.yaml`, loaded unconditionally at startup. Every command evaluated anywhere against any project uses the same global rules. This was the right call for v1 — you can't debug a complex config chain before the core pipeline is stable.

Two features in Tier 2 break this assumption:

1. **[10] Policy Management** introduces per-project `.policy-scout.yaml` overrides, policy simulation against candidate policies, and history testing. The simulator needs to know what the *effective* policy is for a given context — which is the merge of global rules plus any project override. If there's no defined merge semantics, the simulator can't work reliably.

2. **[06] MCP Server** (ADR-001) uses `~/.config/policy-scout/config.yaml` for server trust settings. Once that file exists as a concept, it becomes natural to also put global policy overrides there (e.g., a developer who always wants `paranoid` mode on their machine). Without locking the config chain now, the MCP server and policy management features will build incompatible assumptions about where config comes from.

Additionally, `[12] Git Integration` (already built) has a pre-commit hook that calls `policy-scout scan staged`. If a project defines `scan.pre_commit: true` in `.policy-scout.yaml`, that preference needs a defined place to live.

This ADR locks the three-layer config chain, the merge semantics (especially the tighten-only invariant), the discovery algorithm for project configs, and the validation contract. Every future feature that reads config must use this chain.

---

## Forces

- **Security invariant:** A per-project config must not be able to loosen global policy. A malicious PR that modifies `.policy-scout.yaml` to downgrade `DENY` to `ALLOW` would silently weaken the harness for that project. The tighten-only constraint must be enforced at load time, not trusted to convention.
- **Predictability:** The effective policy for a given command must be deterministic and inspectable. `policy-scout policy show --effective` must show exactly what will fire, with no ambiguity about which layer contributed which rule.
- **Test isolation:** Tests run in directories. Once the policy engine loads project configs by walking up from `cwd`, every test that creates files in a temp directory could inadvertently inherit a real project config if there's one up the directory tree. Test isolation needs an explicit escape hatch.
- **Discoverability:** Project configs should be findable without knowing where the project root is. The engine must walk up the directory tree to find `.policy-scout.yaml`, stopping at a git root or filesystem root.
- **Simplicity:** The config chain should be exactly three layers. Adding more layers (workspace, org, team) is explicitly deferred — premature generalization here would make the merge logic and the test matrix unmanageable.
- **Versioning:** Policy changes should be auditable. The validator and history tester both need to know the policy version they're evaluating against.

---

## Decision

### D1 — Three-layer config chain, evaluated in priority order

```
Layer 1 (lowest priority): built-in defaults
  source:  policy_scout/data/default_policy.yaml
  loaded:  always, unconditionally

Layer 2 (medium priority): user global config
  source:  ~/.config/policy-scout/config.yaml
  loaded:  if the file exists; silently skipped if not
  content: may contain server config (ADR-001), global mode override,
           global additional_rules, global intelligence settings

Layer 3 (highest priority): project override
  source:  .policy-scout.yaml in the project root
  loaded:  if found by discovery algorithm (see D3)
  content: may only tighten Layer 1+2 (see D2)
```

Layers are merged left-to-right. Higher layers win on conflict. The result is the **effective policy** for that command evaluation.

### D2 — Tighten-only semantics for Layer 3

A project override (Layer 3) may:
- Add new rules with a decision of `REQUIRE_APPROVAL`, `SANDBOX_FIRST`, `DENY`, or `DENY_AND_ALERT`
- Set `mode` to any value that is *at least as strict* as the current effective mode (strict ordering: `lenient < balanced < strict < paranoid`)
- Set `strengthen_to` on an existing rule ID to escalate its decision to something stricter
- Set `scan.pre_commit: true` (enabling scan; cannot set to false if global is true)
- Set `intel.remote: true` (enabling intel; cannot disable if global is true)

A project override may NOT:
- Add rules with decision `ALLOW` or `ALLOW_LOGGED`
- Set `mode` to anything less strict than the effective Layer 1+2 mode
- Set `strengthen_to` on an existing rule to something less strict (e.g., `DENY → SANDBOX_FIRST`)
- Remove or disable any rule from Layer 1 or Layer 2
- Set `scan.pre_commit: false` if Layer 1+2 has it as true

Validation happens at load time in `load_project_override()`. A config that violates any tighten-only constraint raises `PolicyOverrideViolation` and the engine falls back to the Layer 1+2 effective policy with a warning to stderr. **It does not fail closed by refusing to evaluate commands** — failing closed here would let a malicious config denial-of-service the harness. The warning goes to stderr and is written as an audit event.

### D3 — Discovery algorithm for project configs

```python
def find_project_config(cwd: Path) -> Path | None:
    """Walk up from cwd, stop at git root or filesystem root."""
    current = cwd.resolve()
    while True:
        candidate = current / ".policy-scout.yaml"
        if candidate.exists():
            return candidate
        # Stop at git root (has a .git directory or .git file)
        if (current / ".git").exists():
            return None
        parent = current.parent
        if parent == current:
            return None   # filesystem root
        current = parent
```

The walk stops at the git root. This prevents projects from accidentally inheriting a config from a parent directory that happens to contain one. If no `.policy-scout.yaml` is found within the git repo, Layer 3 is simply absent and the effective policy is Layer 1+2 only.

### D4 — Test isolation escape hatch

The policy engine exposes a `config_override` parameter in its constructor that bypasses discovery entirely:

```python
PolicyEngine(config_override=None)           # normal: uses discovery
PolicyEngine(config_override="none")         # explicit: skip Layer 2 and Layer 3
PolicyEngine(config_override=Path("/path"))  # explicit: use this file as Layer 3
```

All tests that instantiate a `PolicyEngine` and need isolation must pass `config_override="none"`. The test suite enforces this via a `conftest.py` fixture that patches the discovery function to return `None` during test runs unless explicitly overridden. This prevents any real `.policy-scout.yaml` in the repo root from leaking into tests.

### D5 — Effective policy is inspectable and versioned

Every policy layer must have a `version` field:

```yaml
# default_policy.yaml
version: "1.3.0"
schema_version: 1
```

The effective policy carry a computed `effective_version` field:
```python
effective_version = f"{layer1.version}+{layer2_version or ''}+{layer3_version or ''}"
# e.g., "1.3.0++project-custom-v2"
```

`policy-scout policy show --effective` prints the effective policy with the source layer annotated for each rule, and the effective_version string. This is the ground truth for what will fire.

### D6 — Merge semantics for `additional_rules`

Rules from higher layers are **prepended** to the rule list, not appended. Policy Scout evaluates rules in order and returns on first match. Prepending means project rules fire before global rules — which is the correct behavior for "this project needs stricter handling of X."

The built-in default catch-all rule (explicit `ALLOW_LOGGED` for any unmatched command) is always last. This is validated by the policy validator (see [10]).

---

## Interface Definition

### `~/.config/policy-scout/config.yaml` (Layer 2 schema)

```yaml
# Layer 2 — user global config
# All fields optional. Presence of this file does not require any specific field.

version: "user-v1"         # optional version label

mode: balanced             # global mode override (lenient|balanced|strict|paranoid)

server:                    # MCP server settings (ADR-001)
  default_agent_trust: medium
  require_check_before_run: true

additional_rules:          # global rule additions (same schema as default_policy.yaml)
  - id: deny_curl_bash
    match:
      command_pattern: 'curl\s+.*\|\s*(bash|sh|zsh)'
    decision: DENY_AND_ALERT
    reasons:
      - "curl-pipe-shell is disallowed globally by user policy"

intel:
  remote: false            # enable remote threat intel for all projects

scan:
  pre_commit: false        # enable pre-commit secret scanning for all projects
```

### `.policy-scout.yaml` (Layer 3 schema)

```yaml
# Layer 3 — project override
# Schema version is validated on load.
schema_version: 1
version: "project-v1"     # optional version label for history tester

mode: paranoid             # must be >= effective Layer 1+2 mode

additional_rules:          # prepended to effective rule list
  - id: deny_python_direct
    match:
      command_pattern: '^python\s'
    decision: REQUIRE_APPROVAL
    reasons:
      - "Direct Python execution requires approval in this project"

override_decisions:        # strengthen existing rules
  - rule_id: destructive_deny
    strengthen_to: DENY_AND_ALERT

intel:
  remote: true             # enable remote intel for this project

scan:
  pre_commit: true         # enable pre-commit scan for this project
```

### Policy engine constructor signature change

```python
class PolicyEngine:
    def __init__(
        self,
        registry: RegistryLoader | None = None,
        config_override: Path | Literal["none"] | None = None,
    ):
        ...
```

### `EffectivePolicy` data class

```python
@dataclass
class EffectivePolicy:
    rules: list[PolicyRule]
    mode: str
    effective_version: str
    layers: list[str]        # ["builtin:1.3.0", "global:user-v1", "project:project-v1"]
    project_config_path: Path | None
```

### New audit event types

```python
class EventType:
    PROJECT_OVERRIDE_LOADED    = "ProjectOverrideLoaded"
    PROJECT_OVERRIDE_VIOLATED  = "ProjectOverrideViolated"   # tighten-only violation
    POLICY_SIMULATED           = "PolicySimulated"
    POLICY_VALIDATED           = "PolicyValidated"
    POLICY_HISTORY_TESTED      = "PolicyHistoryTested"
```

`ProjectOverrideLoaded` data:
```json
{
  "config_path": "/home/user/myproject/.policy-scout.yaml",
  "version": "project-v1",
  "additional_rules_count": 2,
  "override_decisions_count": 1
}
```

`ProjectOverrideViolated` data:
```json
{
  "config_path": "/home/user/myproject/.policy-scout.yaml",
  "violation": "Rule 'allow_npm' has decision ALLOW — project overrides may not loosen policy",
  "fallback": "layer1+layer2 effective policy"
}
```

---

## Blast Radius

### Files changed

| File | Change type | Risk |
|---|---|---|
| `policy_scout/policy/engine.py` | Add `config_override` param; call `load_effective_policy()` at start of `decide()` | **Medium-High** — this is the hot path, runs on every evaluation |
| `policy_scout/policy/management/__init__.py` (new) | Package init | Low |
| `policy_scout/policy/management/project_override.py` (new) | Discovery, loading, validation, tighten-only check | Medium (new file) |
| `policy_scout/policy/management/simulator.py` (new) | `simulate()` with full rule trace | Medium (new file) |
| `policy_scout/policy/management/validator.py` (new) | Conflict/unreachable/coverage checks | Medium-High (new file, complex logic) |
| `policy_scout/policy/management/history_tester.py` (new) | Re-run history against candidate policy | Medium (new file) |
| `policy_scout/audit/events.py` | 5 new event types | Low (additive) |
| `policy_scout/cli/main.py` | Add `policy` command group (simulate, test, validate, show, commit) | Medium |
| `policy_scout/doctor.py` | Add policy validation check row | Low (additive) |
| `tests/conftest.py` | Add `config_override="none"` fixture to isolate policy engine tests | **Critical** — must land with Phase 1 |

### Tests requiring changes

All tests that instantiate `PolicyEngine()` directly must be updated to pass `config_override="none"`. This is a one-liner change per test but affects potentially every test file that touches the policy engine. Estimate: 15–25 test cases across `test_policy_engine.py`, `test_risk_scorer.py`, `test_audit.py`, `test_approvals.py`.

The safe approach: add a `conftest.py` autouse fixture that monkeypatches `find_project_config` to return `None` during all test runs, then explicitly opt back in only for tests that test the override mechanism itself. This means individual test files don't need to change.

### Performance implication

`load_effective_policy()` is now called on every `decide()` invocation. The project config discovery (directory walk) must be cached per-process by memoizing on `(cwd, file_mtime)`. On the first call per cwd it does a filesystem walk; subsequent calls return the cached result unless the file has changed. This keeps the hot path fast (<1ms overhead).

```python
@functools.lru_cache(maxsize=16)
def _cached_load_project_override(cwd: Path, mtime: float) -> ProjectOverride | None:
    return load_project_override(cwd)
```

---

## Implementation Phases

### Phase 1 — Config chain infrastructure (~200 lines, no behavior change)

**Scope:** `project_override.py` (discovery + loading + tighten-only validation), `EffectivePolicy` dataclass, `conftest.py` isolation fixture.  
**Acceptance:** `find_project_config()` correctly walks up to git root. `load_project_override()` raises `PolicyOverrideViolation` on a loosening config. All 758 existing tests still pass (conftest fixture ensures no test accidentally uses a real `.policy-scout.yaml`).  
**Commit:** `feat(policy): project override loading + tighten-only validation`  
**Unlocks:** Phase 2. Nothing changes in the policy engine yet — this is pure loading logic.

### Phase 2 — Policy engine integration (~60 lines delta)

**Scope:** Wire `load_effective_policy()` into `PolicyEngine.decide()`. Add `config_override` constructor param. Add `ProjectOverrideLoaded`/`ProjectOverrideViolated` audit events.  
**Acceptance:** `policy-scout check -- some-command` in a project with a `.policy-scout.yaml` that adds a DENY rule correctly denies it. Same command outside the project uses global policy only. `policy-scout policy show --effective` shows the merged rule list with layer annotations.  
**Regression test:** Full eval suite (`policy-scout eval run`) must produce identical results to baseline — project configs in the repo root should not change any eval case outcomes.  
**Commit:** `feat(policy): wire project override into policy engine hot path`  
**Unlocks:** Phase 3, Phase 4. ADR-001 Phase 1 (MCP server) can now reference the config chain for agent trust settings.

### Phase 3 — Policy simulator (~200 lines)

**Scope:** `simulator.py` → `simulate()` function returning full `SimulationResult` with `RuleTrace` list; `policy-scout policy simulate` CLI command.  
**Acceptance:** `policy-scout policy simulate -- npm install lodash` prints full rule trace showing which rule fired and why. `simulate()` returns identical final decisions to `decide()` for all eval suite cases (validated by a new test).  
**Commit:** `feat(policy): policy simulator with full rule trace`  
**Unlocks:** Phase 4 (history tester calls `simulate()` for each historical event).

### Phase 4 — History tester (~180 lines)

**Scope:** `history_tester.py` → `test_against_history()` pulling `DecisionIssued` events from the audit store, re-simulating with current or candidate policy, reporting diffs.  
**Acceptance:** `policy-scout policy test --against-history --days 7` runs without error on a populated audit store. If no policy changes have been made, reports `0 changed decisions`. With a known policy change (add a test fixture rule), reports the correct change count.  
**Commit:** `feat(policy): history tester — replay audit decisions against current policy`  
**Unlocks:** Phase 5 (validator uses history data for coverage checking).

### Phase 5 — Policy validator (~250 lines)

**Scope:** `validator.py` → unreachable rule detection, contradiction detection, missing coverage (using eval suite); `policy-scout policy validate` CLI; doctor integration.  
**Acceptance:** Validator correctly identifies: (a) a known-unreachable rule in a fixture policy, (b) a known contradiction in a fixture policy, (c) an eval case that falls through to no rule. `policy-scout doctor` shows the policy validation row.  
**Commit:** `feat(policy): policy validator — unreachable rules, contradictions, coverage gaps`

### Phase 6 — Policy versioning and commit (~80 lines)

**Scope:** `policy-scout policy commit` command (git add the data files + git commit).  
**Note:** This is the lowest-priority step in [10]. The simulator and validator deliver most of the value. Versioning is useful but not blocking.  
**Acceptance:** `policy-scout policy commit -m "tighten: deny pip installs"` creates a git commit containing only the policy data files.  
**Commit:** `feat(policy): policy commit — snapshot registry state to git`

---

## Consequences

**Enabled:**
- Every project can declare its own security posture without weakening the global harness.
- The simulator gives developers confidence before deploying a policy change: "my new rule changes 3 decisions over the last 30 days, all in the expected direction."
- The validator catches dead code and contradictions in the policy registry before they cause silent evaluation errors.
- The MCP server (ADR-001) can read `default_agent_trust` from `~/.config/policy-scout/config.yaml` via the Layer 2 chain without needing separate config loading logic.
- Git-tracked `.policy-scout.yaml` files are themselves a signal for the [07] injection scanner — a PR modifying the project policy config is a notable security event.

**Given up / deferred:**
- Multi-layer configs beyond three (workspace, org, team). Three layers covers all realistic local-developer use cases. More layers increase merge complexity quadratically.
- Loosening overrides. A project that genuinely needs to loosen global policy (e.g., a security research project that needs `ALLOW` for commands that would normally be denied) must change the global Layer 1 config and document the exception there. This is intentional friction.
- Hot-reload of project configs. Config is cached per-process. A `policy-scout check` invoked after editing `.policy-scout.yaml` picks up the change because it's a new process. A long-running MCP server (ADR-001) would need a `SIGHUP` or restart to pick up config changes. This is acceptable for v1.

**Risks to watch:**
- The tighten-only validation must be comprehensive. The first version should err on the side of rejecting ambiguous cases (e.g., a rule with `decision: ALLOW_LOGGED` added in Layer 3 — reject it, because `ALLOW_LOGGED` is not clearly stricter than `ALLOW`). A permissive validator here is a security hole.
- The `conftest.py` autouse fixture is critical for test suite integrity. If it's missing or has a bug, real project configs on the developer's machine could silently alter test results. Add an explicit test that verifies the isolation fixture is working.
