# Policy Scout — Roadmap

## 1. Roadmap Purpose

This roadmap defines the phased build path for Policy Scout.

Policy Scout should be built in a strict order:

```text
docs -> models -> classifier -> registry -> policy -> audit -> run wrapper -> approval -> sandbox -> sweep -> reports -> integrations
```

The goal is to avoid building impressive but unstable features before the policy spine is solid.

Policy Scout should remain:

- local-first
- policy-centered
- registry-first
- audit-first
- conservative under uncertainty
- modular and recomposable

---

## 2. Core Build Doctrine

Policy Scout should not begin as an autonomous agent.

It should begin as a deterministic command safety harness.

The first working spine is:

```text
CommandRequest
  -> CommandClassifier
  -> RiskScorer
  -> PolicyEngine
  -> Decision
  -> AuditEvent
```

Only after that spine is reliable should Policy Scout add execution, sandboxing, sweeps, reports, and agent integrations.

---

## 3. Phase 0 — Planning Docs and Conventions

### Goal

Lock the project boundary, vocabulary, threat model, and MVP.

### Deliverables

```text
README.md
PROJECT_SCOPE.md
THREAT_MODEL.md
TAXONOMIES.md
ARCHITECTURE.md
REGISTRY_DESIGN.md
POLICY_DESIGN.md
EVALUATION_GRANULARITY.md
MVP_SPEC.md
ROADMAP.md
CLI_SPEC.md
AUDIT_AND_REPORTING.md
```

### Done When

- Project scope is clear.
- Non-goals are documented.
- Initial taxonomies are stable.
- Command decisions are defined.
- MVP is testable.
- Agents have clear docs to work from.

### Confidence

```text
98%
```

This phase is straightforward and extremely important.

---

## 4. Phase 1 — CLI Skeleton and Core Models

### Goal

Create the minimal CLI and core data models.

### Deliverables

```text
policy-scout --help
policy-scout check -- echo hello
CommandRequest model
Actor model
Decision model
Finding model
Risk model
basic config loader
```

### Core Models

- `CommandRequest`
- `Actor`
- `ParseResult`
- `ClassificationResult`
- `CapabilitySet`
- `RiskScore`
- `PolicyDecision`
- `AuditEvent`

### Done When

- CLI runs locally.
- A command can be turned into a `CommandRequest`.
- A placeholder decision can be returned.
- Unit tests cover model serialization.

### Confidence

```text
96%
```

---

## 5. Phase 2 — Command Parser and Classifier

### Goal

Classify common commands into stable categories.

### Initial Command Coverage

```text
ls
pwd
cat README.md
npm test
npm install
npm i
pnpm add
yarn add
bun add
npx
pnpm dlx
bunx
curl URL | bash
wget URL | sh
rm -rf
cat .env
cat ~/.ssh/id_rsa
```

### Deliverables

```text
classify/shell_parser.py
classify/command_classifier.py
classify/package_manager.py
classify/destructive_patterns.py
classify/network_patterns.py
```

### Done When

- Common safe-read commands classify as `safe_read`.
- Package installs classify as `package_install`.
- Package execution classifies as `package_execute`.
- Curl-pipe-shell classifies as `network_execute`.
- Credential-adjacent reads classify as `credential_adjacent`.
- Destructive commands classify as `destructive`.
- Unknown commands preserve uncertainty.

### Confidence

```text
90%
```

Shell parsing is tricky. v0.1 should handle the most important patterns and fail safely on complex syntax.

---

## 6. Phase 3 — Registry Loader and Validator

### Goal

Move command and policy knowledge into YAML registries.

### Deliverables

```text
data/command_registry.yaml
data/default_policy.yaml
data/suspicious_patterns.yaml
data/indicator_registry.yaml

registry/command_registry.py
registry/policy_registry.py
registry/indicator_registry.py
registry/schemas.py
registry/validator.py
```

### Done When

- Registries load from local files.
- Registry schemas validate.
- Invalid registries produce clear errors.
- Registry hits are included in evaluation packets.
- Tests cover expected command and policy matches.

### Confidence

```text
93%
```

---

## 7. Phase 4 — Policy Engine and Risk Scorer

### Goal

Make deterministic policy decisions from granular evaluation data.

### Deliverables

```text
policy/engine.py
policy/matcher.py
policy/risk_scorer.py
policy/risk_clutch.py
policy/mode_router.py
policy/enforcement_modes.py
```

### Required Decisions

```text
ALLOW
ALLOW_LOGGED
REQUIRE_APPROVAL
SANDBOX_FIRST
DENY
DENY_AND_ALERT
```

### Done When

- `npm install lodash` returns `SANDBOX_FIRST`.
- `curl URL | bash` returns `DENY`.
- `cat ~/.ssh/id_rsa` returns `DENY_AND_ALERT`.
- `ls` returns `ALLOW`.
- Decisions include policy hits and reasons.
- Risk is granular, not lump-sum only.

### Confidence

```text
94%
```

---

## 8. Phase 5 — Audit Store

### Goal

Record every important request, decision, approval, execution, sandbox run, finding, and report.

### Deliverables

```text
audit/events.py
audit/sqlite_store.py
audit/jsonl_writer.py
audit/retention.py
```

### Initial Events

```text
CommandRequested
CommandParsed
CommandClassified
PolicyMatched
DecisionIssued
ApprovalRequested
ApprovalResolved
CommandExecuted
SandboxStarted
SandboxCompleted
SweepStarted
SweepFindingCreated
ScoutReportGenerated
```

### Done When

- Every `check` writes an optional evaluation/audit record.
- Every `run` writes durable request/decision/execution records.
- Audit records include request IDs and decision IDs.
- Audit records avoid secret values.
- Audit store failure blocks risky execution.

### Confidence

```text
92%
```

---

## 9. Phase 6 — `check` Command MVP

### Goal

Deliver the first useful CLI command.

### Example

```bash
policy-scout check -- npm install lodash
```

### Output

```text
Decision: SANDBOX_FIRST
Risk: 7/10
Category: package_install

Why:
- Package installs may execute lifecycle scripts.
- Package installs download third-party code.
- Package installs can modify manifests and lockfiles.

Recommended:
Run sandbox analysis first.
```

### Done When

- `check` produces deterministic decisions.
- Output is human-readable.
- JSON output is available for agents/scripts.
- Tests verify output.

### Confidence

```text
95%
```

---

## 10. Phase 7 — `run` Wrapper

### Goal

Execute allowed commands through Policy Scout.

### Deliverables

```text
cli/run.py
core/executor.py
```

### Behavior

- `ALLOW` runs directly.
- `ALLOW_LOGGED` runs and logs.
- `REQUIRE_APPROVAL` pauses.
- `SANDBOX_FIRST` does not run directly.
- `DENY` does not run.
- `DENY_AND_ALERT` does not run and creates warning/report path.

### Done When

- Safe commands can execute.
- Risky commands are paused or blocked.
- Execution result is logged.
- Failures are recorded.
- Risky commands do not run if audit logging fails.

### Confidence

```text
92%
```

---

## 11. Phase 8 — Approval Queue

### Goal

Let users approve or deny pending requests.

### Deliverables

```text
approval/queue.py
approval/store.py
approval/resolver.py
cli/approvals.py
```

### Commands

```bash
policy-scout approvals list
policy-scout approvals show req_123
policy-scout approvals approve req_123
policy-scout approvals deny req_123
```

### Done When

- Risky requests can be saved as pending approvals.
- User can approve once.
- User can deny once.
- Approval decisions are logged.
- Approval does not silently create permanent allow rules.

### Confidence

```text
89%
```

---

## 12. Phase 9 — Sandbox Install v1

### Goal

Analyze package installs before host mutation.

### Deliverables

```text
sandbox/temp_workspace.py
sandbox/package_install.py
sandbox/lifecycle_inspector.py
sandbox/diff.py
sandbox/migration.py
cli/sandbox.py
```

### Supported Package Managers

```text
npm
pnpm
yarn
bun
```

### Flow

```text
create temp workspace
copy package manifest and lockfile
run install in sandbox
capture output
inspect lifecycle scripts
capture manifest/lockfile diff
run sandbox sweep
produce Scout Report
ask before migration
```

### Done When

- Sandbox install does not mutate the host project.
- Lifecycle scripts are inspected.
- Manifest/lockfile diffs are captured.
- Report is generated.
- Migration requires explicit approval.

### Confidence

```text
86-88%
```

This is valuable but edge-case heavy: monorepos, workspaces, native builds, private registries, and package-manager quirks matter.

---

## 13. Phase 10 — Project Sweep v1

### Goal

Detect suspicious traces in a project.

### Deliverables

```text
sweep/engine.py
sweep/package_scripts.py
sweep/repo_changes.py
sweep/workflows.py
sweep/credentials.py
sweep/suspicious_patterns.py
```

### Initial Checks

- package lifecycle scripts
- suspicious use of `child_process`
- suspicious `curl`/`wget` usage
- obfuscated JS patterns
- GitHub Actions workflow changes
- new executable files
- credential-adjacent references
- suspicious package manifests

### Done When

- Sweep returns findings with severity and confidence.
- Findings include evidence locations.
- Secret values are redacted.
- Markdown and JSON outputs are available.

### Confidence

```text
84-87%
```

False positives are the main challenge.

---

## 14. Phase 11 — System Quick Sweep

### Goal

Check local environment signals that may indicate suspicious activity.

### Deliverables

```text
sweep/processes.py
sweep/ports.py
sweep/system_config.py
```

### Initial Checks

- open ports
- suspicious Node/Bun/Python processes
- package-manager config changes
- recent shell profile changes
- suspicious temp files

### Done When

- Works on Linux first.
- Findings are cautious and evidence-based.
- Platform unsupported areas are clearly reported.

### Confidence

```text
82-85%
```

Platform differences matter.

---

## 15. Phase 12 — Scout Reports

### Goal

Produce clear reports for users and agents.

### Deliverables

```text
reports/scout_report.py
reports/markdown_report.py
reports/json_report.py
reports/incident_guidance.py
```

### Report Types

```text
command_decision
package_install_review
sandbox_result
project_sweep
system_quick_sweep
possible_credential_exposure
blocked_command
incident_summary
```

### Done When

- Reports reference audit event IDs.
- Reports include evidence locations.
- Reports include uncertainty.
- Reports avoid overclaiming.
- Reports redact secrets.

### Confidence

```text
94%
```

---

## 16. Phase 13 — Local API / Agent Gateway

### Goal

Expose Policy Scout to agents through a structured local API.

### Possible Tools

```text
policy_scout.check_command
policy_scout.run_command
policy_scout.sandbox_install
policy_scout.sweep_project
policy_scout.get_report
policy_scout.list_approvals
policy_scout.resolve_approval
```

### Done When

- Agents can request checks.
- Agents receive structured decisions.
- Agents cannot bypass policy.
- Agent API is disabled unless explicitly enabled.

### Confidence

```text
82-86%
```

This should come after the CLI core is proven.

---

## 17. Phase 14 — Community Rule Packs

### Goal

Allow optional extension through rule packs.

### Example Packs

```text
npm-baseline
python-pip-baseline
dangerous-shell-patterns
github-actions-sweep
beginner-mode
ci-strict-mode
known-campaign-indicators
```

### Done When

- Local rule packs can be added.
- Rule packs are validated.
- Rule pack sources are visible.
- Remote update is optional.
- Signing/checksums are planned before broad community use.

### Confidence

```text
80%
```

Governance and trust are the challenge.

---

## 18. Build Order Summary

```text
1. Planning docs
2. CLI skeleton
3. Core models
4. Parser/classifier
5. Taxonomy constants
6. Registry loader
7. Registry validator
8. Policy engine
9. Risk scorer
10. check command
11. Audit store
12. run wrapper
13. Approval queue
14. Sandbox temp workspace
15. Package install sandbox
16. Lifecycle inspector
17. Diff capture
18. Project sweep
19. System quick sweep
20. Scout Reports
21. Local API / agent gateway
22. Rule packs
```

---

## 19. Roadmap Doctrine

Build the harness first.

Do not build a security agent before the policy boundary exists.

Do not build integrations before the CLI is useful.

Do not build adaptive behavior before deterministic policy is trustworthy.

Policy Scout should become powerful by remaining disciplined.
