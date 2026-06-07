# Policy Scout — Documentation Index

## 1. Purpose

This index explains the Policy Scout documentation set and how agents or developers should use it.

Policy Scout is a local-first safety harness for agent commands, package installs, and suspicious project activity.

Short tagline:

```text
Policy Scout: light armor for fast agents.
```

The documentation is organized to keep the project policy-centered, registry-first, local-first, and audit-friendly.

---

## 2. Recommended Reading Order

Agents and developers should read these docs in order:

```text
1. PROJECT_SCOPE.md
2. ARCHITECTURE.md
3. THREAT_MODEL.md
4. TAXONOMIES.md
5. EVALUATION_GRANULARITY.md
6. REGISTRY_DESIGN.md
7. POLICY_DESIGN.md
8. RISK_SCORING_AND_CLUTCH.md
9. CLI_SPEC.md
10. MVP_SPEC.md
11. IMPLEMENTATION_PLAN.md
12. TESTING_STRATEGY.md
13. LOCAL_FIRST_AND_PRIVACY.md
14. AUDIT_AND_REPORTING.md
15. COMMAND_CLASSIFIER_DESIGN.md
16. SANDBOX_DESIGN.md
17. SWEEP_ENGINE_DESIGN.md
18. APPROVAL_QUEUE_DESIGN.md
19. INTEGRATION_BOUNDARIES.md
20. DATA_MODELS.md
21. AGENT_HANDOFF.md
```

When in doubt, follow `PROJECT_SCOPE.md`, `ARCHITECTURE.md`, and `POLICY_DESIGN.md` first.

---

## 3. Core Docs

### 3.1 `PROJECT_SCOPE.md`

Defines:

- what Policy Scout is
- what it is not
- the core doctrine
- non-goals
- MVP definition
- project split between Policy Scout, Bons.ai, Cerebra, and LumaWeave

This is the anchor doc.

---

### 3.2 `ARCHITECTURE.md`

Defines the major system components:

- request normalizer
- parser
- classifier
- capability detector
- context inspector
- registry matcher
- risk scorer
- policy engine
- approval queue
- sandbox
- sweep engine
- audit store
- Scout Reports

Use this when designing modules.

---

### 3.3 `THREAT_MODEL.md`

Defines what Policy Scout is protecting against.

Covers:

- unsafe agent commands
- risky package installs
- lifecycle scripts
- network-executed scripts
- credential-adjacent access
- workflow injection
- persistence mechanisms
- suspicious processes and ports

Use this when deciding whether a feature belongs in scope.

---

### 3.4 `TAXONOMIES.md`

Defines shared vocabulary:

- actor types
- actor trust levels
- command categories
- capabilities
- decisions
- risk levels
- finding severities
- confidence levels
- enforcement modes
- report types
- evidence types

Use this when adding new classifiers, rules, reports, or tests.

---

## 4. Policy and Evaluation Docs

### 4.1 `EVALUATION_GRANULARITY.md`

Defines the requirement that Policy Scout must score granular steps, not only lump-sum processes.

This is critical for:

- risk scoring
- clutch functionality
- audit clarity
- Scout Reports
- tests

This doc should guide evaluation packet design.

---

### 4.2 `REGISTRY_DESIGN.md`

Defines registry-first design.

Covers:

- command registry
- policy registry
- suspicious pattern registry
- indicator registry
- registry validation
- registry priority
- local rule packs

Use this before hardcoding any command behavior.

---

### 4.3 `POLICY_DESIGN.md`

Defines how Policy Scout makes decisions.

Covers:

- decisions
- policy inputs
- priority
- default rules
- enforcement modes
- human overrides
- LLM boundary
- adaptive policy boundary

The policy engine should implement this doc.

---

### 4.4 `RISK_SCORING_AND_CLUTCH.md`

Defines granular risk components and clutch behavior.

Covers:

- risk components
- confidence
- evidence strength
- mode routing
- clutch inputs/outputs
- adaptive learning boundaries

Use this when implementing the risk scorer and mode router.

---

## 5. Implementation Docs

### 5.1 `CLI_SPEC.md`

Defines the user-facing command line interface.

Covers:

- `check`
- `run`
- `sandbox`
- `sweep`
- `approvals`
- `report`
- global options
- JSON mode
- exit codes

Use this for CLI implementation.

---

### 5.2 `MVP_SPEC.md`

Defines the v0.1 product target.

Covers:

- MVP commands
- in-scope behavior
- out-of-scope behavior
- definition of done
- test matrix
- repo layout
- build order

Use this to prevent scope creep.

---

### 5.3 `IMPLEMENTATION_PLAN.md`

Defines the practical build milestones.

Covers:

- scaffold
- models
- parser
- classifier
- registries
- risk scorer
- policy engine
- audit store
- CLI
- approvals
- sandbox
- sweep
- reports

Use this as the development sequence.

---

### 5.4 `TESTING_STRATEGY.md`

Defines how the project should be tested.

Covers:

- parser tests
- classifier tests
- registry tests
- policy tests
- risk scoring tests
- clutch tests
- audit tests
- approval tests
- sandbox tests
- sweep tests
- report tests
- redaction tests
- fail-safe tests

Use this before merging feature work.

---

## 6. Subsystem Design Docs

### 6.1 `COMMAND_CLASSIFIER_DESIGN.md`

Defines command parsing and classification.

Use this for:

- shell parsing
- command family detection
- category detection
- capability detection
- confidence scoring

---

### 6.2 `SANDBOX_DESIGN.md`

Defines package install sandboxing.

Use this for:

- temp workspace creation
- manifest and lockfile copying
- lifecycle script inspection
- diff capture
- sandbox result objects
- migration behavior

---

### 6.3 `SWEEP_ENGINE_DESIGN.md`

Defines project and system sweeps.

Use this for:

- project sweep
- quick system sweep
- sandbox sweep
- findings
- severity/confidence
- redaction
- reports

---

### 6.4 `APPROVAL_QUEUE_DESIGN.md`

Defines approval handling.

Use this for:

- approval request objects
- approval status
- approval scope
- CLI approval flow
- audit events
- safety rules

---

### 6.5 `AUDIT_AND_REPORTING.md`

Defines durable audit events and Scout Reports.

Use this for:

- event model
- audit storage
- report generation
- finding shape
- redaction
- evidence references

---

### 6.6 `LOCAL_FIRST_AND_PRIVACY.md`

Defines privacy and local-first requirements.

Use this for:

- data locations
- redaction
- `.npmrc` handling
- environment variable handling
- process information
- optional network behavior

---

### 6.7 `INTEGRATION_BOUNDARIES.md`

Defines how Policy Scout should integrate with other systems.

Use this for:

- CLI wrapper
- shell shims
- local API
- MCP-style server
- editor extensions
- CI
- Cerebra
- LumaWeave
- LLMs

---

### 6.8 `DATA_MODELS.md`

Defines canonical data structures.

Use this when implementing shared models.

---

### 6.9 `AGENT_HANDOFF.md`

Defines instructions for agents working on the project.

Agents should read this before editing code.

---

## 7. Project Laws

These rules override feature enthusiasm.

```text
1. Policy Scout is policy-centered, not agent-centered.
2. Agents request; Policy Scout decides.
3. Registries before cleverness.
4. Granular scoring before final score.
5. LLMs may explain; policy decides.
6. Risky execution requires auditability.
7. Package installs are untrusted until reviewed.
8. Secret values must be redacted.
9. Local-first by default.
10. No silent safety regression.
```

---

## 8. How Agents Should Use These Docs

Agents should:

1. Read relevant docs before planning.
2. State which docs they used.
3. Keep changes aligned with the project laws.
4. Avoid inventing new taxonomies unless necessary.
5. Add tests for every behavior change.
6. Preserve granular evaluation fields.
7. Avoid expanding scope beyond MVP without documenting it.
8. Ask for human review when security boundaries are unclear.

Agents should not:

1. Port Bons.ai code directly.
2. Add autonomous agent loops to Policy Scout.
3. Let LLMs make final policy decisions.
4. Hide policy logic in scattered code.
5. Auto-approve risky commands.
6. Remove auditability.
7. Print secrets into logs or reports.
