# ADR-005: Registry Coverage Expansion and Eval Coverage Contract

**Status:** Accepted  
**Date:** 2026-06-10  
**Deciders:** Developer (bitmosh)  
**Related ADRs:** [ADR-002](ADR-002-policy-config-precedence.md) (project overrides may only tighten registry decisions), [ADR-004](ADR-004-sandbox-backend-abstraction.md) (new package managers require sandbox execution support)

---

## Context

The command registry has 15 entries, all from the JS/Node ecosystem. The eval suite has 44 cases. Policy Scout classifies commands into roughly 8 categories (`package_install`, `package_execute`, `network_execute`, `safe_read`, `destructive`, `credential_adjacent`, `env_mutation`, `unknown`), but the only commands covered end-to-end in the registry are npm, pnpm, yarn, bun, npx, curl-pipe-shell, rm -rf, cat .env, and ls/pwd/cat README.

A developer using Policy Scout in a Python, Rust, Go, or mixed-stack project today gets one of two outcomes for most commands:
1. A broad category match with no specific registry reasoning (the classifier infers `package_install` from the command structure)
2. `unknown` category with a fallback REQUIRE_APPROVAL

Neither is reliable enough for an agent that needs deterministic, explainable decisions. An agent calling `pip install numpy` should get a registry-backed decision with specific reasons, not a pattern-match heuristic.

There's also a structural problem: there is no metric that tells us whether the registry is well-covered. The eval suite passes at 100%, but that's a regression signal, not a coverage signal. A registry with 100 entries and 10 eval cases has blind spots the 100% pass rate doesn't reveal.

This ADR defines the expansion order, the eval coverage contract, and the governance rules that keep the registry from drifting out of sync with the eval suite.

---

## Forces

- **Ecosystem breadth vs. depth.** It's better to have 3 solid entries per ecosystem (covering the most common install, execute, and search patterns) than 30 shallow entries. Each entry costs maintenance — reasons must stay accurate, priorities must be calibrated, and eval cases must verify decisions.
- **False negatives are worse than false positives.** A registry that misses `pip install` and emits `unknown → REQUIRE_APPROVAL` is annoying but safe. A registry that has `pip install` but assigns `ALLOW` is dangerous. Coverage expansion must not lower the bar on unknown commands to make pass rates look better.
- **Eval coverage as a merge gate.** If a new registry entry can be added without a corresponding eval case, the entry drifts from its stated purpose over time. The eval coverage contract prevents this.
- **Decision rationale must be specific.** A reason like "Package installs may execute lifecycle scripts" is true for npm but also true for pip (setup.py hooks), cargo (build scripts), and gem (native extensions). Reasons must be specific to the ecosystem where they differ from the default.
- **Container/IaC commands need distinct treatment.** `docker run`, `terraform apply`, and `kubectl apply` are not package installs. They need their own categories or a clean extension of the existing taxonomy before registry entries are added.

---

## Decision

### D1 — Expansion order and priority tiers

**Tier A — Python ecosystem (highest priority)**

Rationale: Python is the second most common ecosystem for AI agent workflows (after JS). `pip install` is common in agent-generated commands. The absence of Python registry entries is the single largest coverage gap.

Entries required:
```
python.pip_install          pip install, pip3 install
python.pip_install_req      pip install -r requirements.txt
python.uv_add               uv add, uv install
python.poetry_add           poetry add, poetry install
python.pipx_install         pipx install, pipx run
python.pip_download         pip download (network, no execution)
```

**Tier B — Rust and Go**

Rationale: Common in developer toolchains and CI. `cargo install` and `go install` are the primary vectors; both execute arbitrary build scripts at install time.

Entries required:
```
rust.cargo_add              cargo add (manifest only, no execution)
rust.cargo_install          cargo install (downloads and compiles; build.rs runs)
rust.cargo_run              cargo run (in context; may be safe or not)
go.go_get                   go get
go.go_install               go install
```

**Tier C — System package managers**

Rationale: Agents are sometimes asked to install system dependencies. `apt install` and `brew install` require elevated privileges (or sudo) and have broad system impact.

Entries required:
```
system.apt_install          apt install, apt-get install
system.brew_install         brew install, brew upgrade
system.gem_install          gem install
system.conda_install        conda install, mamba install
```

**Tier D — Container and IaC (deferred to v2, taxonomy prerequisite)**

`docker run`, `kubectl apply`, `terraform apply`, `helm install` cannot be added to the existing command registry without first extending the category taxonomy (these are not `package_install` or `network_execute`). Adding them with an incorrect category produces misleading policy reasoning.

A new `infrastructure_mutation` category (or equivalent) is a prerequisite for Tier D. Tier D entries are **explicitly deferred** until that taxonomy change lands.

### D2 — Eval coverage contract

Every active registry entry must have at minimum:
- One **affirming eval case** — a command that should match this entry and receive the expected decision
- One **boundary eval case** — a command that should NOT match this entry (tests that the rule doesn't over-match)

For entries with `SANDBOX_FIRST` or `DENY` decisions:
- One **affirming eval case** must use a realistic attacker-pattern command (not only the canonical form)

The eval coverage metric is defined as:

```
coverage = entries_with_affirming_case / total_active_entries
```

Target: **≥ 90% coverage** before any Tier B expansion begins; **≥ 85% coverage maintained** at all times.

The metric is computed by `policy-scout eval coverage` (new subcommand, Phase 3 of implementation). It runs as part of `policy-scout doctor` output (warning if below 85%).

### D3 — Entry authoring requirements

Every new registry entry requires all of the following fields to be populated before it merges:

```yaml
- id: python.pip_install
  title: "pip package install"
  version: 1
  status: active
  priority: 700
  match:
    categories: [package_install]
    command_pattern: "^pip[3]? install"
  decision: SANDBOX_FIRST
  reasons:
    - "pip install runs setup.py and pyproject.toml build hooks at install time"
    - "setup.py hooks execute arbitrary Python with host filesystem access"
    - "pip downloads from PyPI; packages may contain malicious __init__.py payloads"
  recommended_controls:
    - "Run in a virtual environment scoped to the project"
    - "Review pyproject.toml and setup.py before installation"
  recommended_next_action: "sandbox_install"
  eval_cases:
    - id: "pip_install_basic"        # must exist in eval_cases.yaml
    - id: "pip_install_boundary"     # must exist in eval_cases.yaml
```

The `reasons` field must be ecosystem-specific where the risk differs from the category default. "Package installs may execute lifecycle scripts" is not acceptable as the only reason for `pip install` — it must name the specific mechanisms (setup.py, pyproject hooks).

### D4 — Classifier extension

New registry entries that rely on `command_pattern` matching require no classifier changes. However, Tier B and C entries surface a gap: the classifier's category inference (`package_install`, `destructive`, etc.) must recognize these command prefixes to assign the right category before the registry fires.

`classify/command_classifier.py` must be updated alongside each tier's registry entries to recognize:
- Tier A: `pip`, `pip3`, `uv`, `poetry`, `pipx` → `package_install`; `python -m pip` → `package_install`
- Tier B: `cargo install`, `go install`, `go get` → `package_install`; `cargo add`, `cargo build` → distinct treatment
- Tier C: `apt install`, `apt-get install`, `brew install`, `gem install` → `package_install`

Classifier updates are in-scope for each tier's registry expansion. They are the same change list, not a separate pass.

### D5 — Deprecated patterns

Three existing entries have broad `command_pattern` values that will overlap with Tier A/B/C entries at the wrong priority:

- `generic_package_install` (if it exists) — must have priority lower than any specific ecosystem entry
- Any catch-all `package_install` category rule — must be reviewed for over-matching before Tier A lands

Priority ordering rule: specific-ecosystem entries (`python.pip_install`, priority 700) must always have higher priority than any broad catch-all entry (priority ≤ 500). This is validated by the `validate_policy` check for unreachable rules — if a broad entry shadows a specific one, it will be flagged.

---

## Consequences

### Positive
- Policy Scout becomes useful for Python, Rust, and Go developers immediately after Tier A/B land
- The eval coverage metric prevents registry drift — new entries can't be added without tests
- The 90% coverage gate gives a quantitative readiness signal for each expansion tier
- `policy-scout eval coverage` surfaces the gap to the developer without manual counting

### Negative / Risks
- Tier D (container/IaC) is explicitly blocked on a taxonomy extension. If someone adds `docker run` to the registry without the taxonomy change, it gets an incorrect category and misleading reasons. The entry authoring requirements (D3) must be enforced in review, not only documented.
- Python's `setup.py` decision is nuanced: `pip install numpy` from a known-safe wheel has no lifecycle script risk; `pip install <unknown-package>` from source does. The registry cannot distinguish these cases per-entry. The decision must default to the risky case (`SANDBOX_FIRST`) with the reason explicitly noting the wheel/source distinction. Accepting some false positives on known-safe packages is correct.
- `cargo add` (manifest-only) is categorically different from `cargo install` (downloads and compiles). The registry must not assign them the same decision. `cargo add` is `ALLOW_LOGGED`; `cargo install` is `SANDBOX_FIRST`. This distinction must be preserved in both the registry entry and the classifier.

---

## Blast Radius

| File | Change |
|---|---|
| `data/command_registry.yaml` | modified — Tier A (6 entries), Tier B (5 entries), Tier C (4 entries) |
| `data/eval_cases.yaml` | modified — affirming + boundary eval cases for every new entry |
| `classify/command_classifier.py` | modified — Tier A/B/C prefix recognition |
| `policy_scout/evals/runner.py` | modified — `eval coverage` subcommand |
| `policy_scout/doctor.py` | modified — coverage metric check |
| `cli/main.py` | modified — `eval coverage` subcommand wiring |

---

## Implementation Phases

### Phase 1 — Eval coverage metric and baseline
- Add `policy-scout eval coverage` subcommand
- Compute current baseline coverage against existing 15 entries + 44 eval cases
- Add coverage check to `policy-scout doctor` (warning if < 85%)
- Document the baseline; this is the starting point all future tiers are measured from

**STOP gate:** `policy-scout eval coverage` runs cleanly. Current coverage percentage documented.

### Phase 2 — Tier A: Python ecosystem
- Add 6 Python registry entries to `data/command_registry.yaml`
- Add affirming + boundary eval cases for each (minimum 12 new eval cases)
- Update `command_classifier.py` to recognize Python package manager prefixes
- Ensure coverage stays ≥ 90% after additions

**STOP gate:** `policy-scout eval run` passes 100%. `pip install numpy` returns `SANDBOX_FIRST` with Python-specific reasons. `python --version` does NOT match `python.pip_install`.

### Phase 3 — Tier B: Rust and Go
- Add 5 entries; update classifier; add eval cases
- Verify `cargo add` vs. `cargo install` decision distinction

**STOP gate:** `cargo install ripgrep` returns `SANDBOX_FIRST`. `cargo add serde` returns `ALLOW_LOGGED`. Coverage ≥ 90%.

### Phase 4 — Tier C: System package managers
- Add 4 entries; update classifier; add eval cases
- Note in entry reasons that `apt install` may require sudo (different risk surface)

**STOP gate:** `apt install curl` returns `DENY_AND_ALERT` or `REQUIRE_APPROVAL` with sudo-escalation reason. Coverage ≥ 90%.

### Phase 5 — Tier D taxonomy prerequisite (deferred)
- Define `infrastructure_mutation` category (or equivalent)
- Update classifier, schemas, and eval models to recognize it
- Tier D entries follow in a subsequent pass once taxonomy lands
