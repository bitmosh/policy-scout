# Policy Scout — Implementation Plan

## 1. Purpose

This document turns the Policy Scout architecture into a practical implementation sequence.

Policy Scout should be built as a clean-room security tool, not as a direct port of Bons.ai.

Bons.ai provides useful control patterns:

- pure state-in / decision-out controllers
- mode persistence
- granular metrics
- event logging
- tool usage accounting
- conservative adaptive behavior

Policy Scout should reimplement these ideas with security-specific models, registries, policies, and audit requirements.

---

## 2. Implementation Doctrine

Build in this order:

```text
models -> parser -> classifier -> registry -> policy -> audit -> CLI -> approvals -> sandbox -> sweep -> reports -> integrations
```

Do not build:

- autonomous agent loops
- MCP server
- editor extensions
- cloud dashboard
- community marketplace
- automatic remediation

until the local CLI spine works.

---

## 3. Language and Stack Recommendation

The first implementation can be Python for speed of development.

Recommended v0.1 stack:

```text
Python 3.12+
Typer or argparse for CLI
Pydantic or dataclasses for models
PyYAML or ruamel.yaml for registries
SQLite for audit storage
pytest for tests
rich optional for CLI formatting
```

Avoid heavy dependencies where possible.

Keep core logic dependency-light.

Python owns orchestration, CLI, policy flow, registries, reports, and tests.

Rust is allowed only for isolated components where it clearly improves correctness, parsing, sandbox/process safety, or future Tauri reuse.

---

## 4. Repository Layout

Suggested initial structure:

```text
policy-scout/
  pyproject.toml
  README.md

  policy_scout/
    __init__.py

    cli/
      __init__.py
      main.py
      check.py
      run.py
      sandbox.py
      sweep.py
      approvals.py
      report.py

    core/
      __init__.py
      request.py
      actor.py
      decision.py
      finding.py
      risk.py
      ids.py
      errors.py

    classify/
      __init__.py
      shell_parser.py
      command_classifier.py
      package_manager.py
      destructive_patterns.py
      network_patterns.py

    registry/
      __init__.py
      loader.py
      validator.py
      command_registry.py
      policy_registry.py
      indicator_registry.py
      schemas.py

    policy/
      __init__.py
      engine.py
      matcher.py
      risk_scorer.py
      risk_clutch.py
      mode_router.py
      enforcement_modes.py

    approval/
      __init__.py
      queue.py
      store.py
      resolver.py

    sandbox/
      __init__.py
      temp_workspace.py
      package_install.py
      lifecycle_inspector.py
      diff.py
      migration.py

    sweep/
      __init__.py
      engine.py
      package_scripts.py
      repo_changes.py
      workflows.py
      processes.py
      ports.py
      credentials.py
      suspicious_patterns.py

    audit/
      __init__.py
      events.py
      sqlite_store.py
      jsonl_writer.py
      retention.py

    reports/
      __init__.py
      scout_report.py
      markdown_report.py
      json_report.py
      incident_guidance.py

    data/
      command_registry.yaml
      default_policy.yaml
      suspicious_patterns.yaml
      indicator_registry.yaml

  tests/
    test_models.py
    test_shell_parser.py
    test_classifier.py
    test_registry.py
    test_policy_engine.py
    test_risk_scorer.py
    test_audit.py
    test_approvals.py
    test_sandbox.py
    test_sweep.py
    test_reports.py

  docs/
    PROJECT_SCOPE.md
    ARCHITECTURE.md
    THREAT_MODEL.md
    TAXONOMIES.md
    REGISTRY_DESIGN.md
    POLICY_DESIGN.md
    EVALUATION_GRANULARITY.md
    MVP_SPEC.md
    ROADMAP.md
```

---

## 5. Milestone 1 — Project Scaffold

### Goal

Create installable project skeleton.

### Tasks

1. Create repository.
2. Add `pyproject.toml`.
3. Add package folder.
4. Add CLI entrypoint.
5. Add empty test suite.
6. Add docs folder.
7. Add initial data folder.

### Acceptance Criteria

```text
policy-scout --help works
pytest runs
package imports cleanly
docs are present
```

---

## 6. Milestone 2 — Core Models

### Goal

Define stable data models.

### Models

```text
Actor
CommandRequest
ParseResult
ClassificationResult
CapabilitySet
RegistryHit
RiskScore
PolicyDecision
ApprovalRequest
AuditEvent
Finding
ScoutReport
```

### Acceptance Criteria

- Models serialize to JSON.
- IDs are generated consistently.
- Required fields are validated.
- Tests cover basic construction and serialization.

---

## 7. Milestone 3 — Shell Parser

### Goal

Parse common shell command structure.

### Tasks

1. Tokenize basic commands.
2. Detect pipes.
3. Detect redirects.
4. Detect chained operators.
5. Detect subshells where simple.
6. Detect command substitution where simple.
7. Compute shell complexity.
8. Return parse confidence.

### Acceptance Criteria

Commands such as these produce useful parse results:

```bash
ls
npm install lodash
npm install lodash && npm test
curl https://example.com/install.sh | bash
bash -c "echo hello"
rm -rf /
cat ~/.ssh/id_rsa
```

---

## 8. Milestone 4 — Command Classifier

### Goal

Classify common risky and safe commands.

### Tasks

1. Implement package manager detection.
2. Implement safe-read detection.
3. Implement package-install detection.
4. Implement package-execute detection.
5. Implement network-fetch detection.
6. Implement network-execute detection.
7. Implement destructive-pattern detection.
8. Implement credential-adjacent detection.
9. Return categories, capabilities, confidence, and notes.

### Acceptance Criteria

Classification tests pass for:

```text
safe_read
package_install
package_execute
network_fetch
network_execute
credential_adjacent
destructive
unknown
```

---

## 9. Milestone 5 — Registry Loader and Validator

### Goal

Load and validate YAML registries.

### Tasks

1. Define registry schemas.
2. Load local YAML files.
3. Validate required fields.
4. Validate enum values.
5. Validate regex patterns.
6. Produce useful error messages.
7. Add tests with good and bad registries.

### Acceptance Criteria

- Valid registries load.
- Invalid registries fail with clear errors.
- Registry entries can be matched.
- Registry hits are structured.

---

## 10. Milestone 6 — Risk Scorer

### Goal

Compute granular risk components.

### Tasks

1. Define risk component constants.
2. Implement component scoring.
3. Clamp final risk score to 0-10.
4. Preserve component breakdown.
5. Compute confidence.
6. Compute evidence strength.
7. Add tests.

### Acceptance Criteria

Examples:

```text
npm install lodash -> risk around high / sandbox-first range
curl URL | bash -> severe/high risk
cat ~/.ssh/id_rsa -> critical credential-adjacent risk
ls -> minimal risk
unknown complex shell -> medium/high uncertainty risk
```

Exact numbers can change, but components must remain visible.

---

## 11. Milestone 7 — Policy Engine

### Goal

Produce decisions from structured inputs.

### Tasks

1. Implement policy matching.
2. Implement priority resolution.
3. Implement deny-over-allow behavior.
4. Implement mode-aware adjustments.
5. Include decision reasons.
6. Include policy hits.
7. Add tests.

### Acceptance Criteria

These decisions work:

```text
ls -> ALLOW
npm test -> ALLOW_LOGGED
npm install lodash -> SANDBOX_FIRST
npx unknown-tool -> SANDBOX_FIRST
curl URL | bash -> DENY
cat ~/.ssh/id_rsa -> DENY_AND_ALERT
rm -rf / -> DENY
unknown complex command -> REQUIRE_APPROVAL or DENY
```

---

## 12. Milestone 8 — Audit Store

### Goal

Persist important events.

### Tasks

1. Define audit event model.
2. Implement SQLite store.
3. Optional JSONL writer.
4. Add event creation helpers.
5. Add redaction hooks.
6. Add audit tests.

### Acceptance Criteria

- Events persist locally.
- Events are queryable by request ID.
- Risky execution does not proceed if audit write fails.
- Secret-like values are redacted.

---

## 13. Milestone 9 — `check` CLI

### Goal

Deliver first user-facing useful command.

### Tasks

1. Implement `policy-scout check -- <command>`.
2. Print human-readable decision.
3. Add `--json`.
4. Add `--mode`.
5. Write optional audit event.
6. Add CLI tests.

### Acceptance Criteria

`check` works for common commands and never executes.

---

## 14. Milestone 10 — `run` CLI

### Goal

Run allowed commands through policy.

### Tasks

1. Implement direct executor.
2. Wire policy decisions to execution behavior.
3. Handle `ALLOW`.
4. Handle `ALLOW_LOGGED`.
5. Handle `REQUIRE_APPROVAL`.
6. Handle `SANDBOX_FIRST`.
7. Handle `DENY`.
8. Handle `DENY_AND_ALERT`.

### Acceptance Criteria

- Allowed commands run.
- Risky commands pause or route away.
- Denied commands do not run.
- Execution events are logged.

---

## 15. Milestone 11 — Approval Queue

### Goal

Support human approval for risky commands.

### Tasks

1. Create approval model.
2. Store pending approvals.
3. Implement list/show/approve/deny.
4. Enforce approval expiration.
5. Verify exact command/cwd match.
6. Log approval events.

### Acceptance Criteria

- User can approve once.
- User can deny once.
- Agents cannot self-approve.
- Approval does not create permanent allow rules.

---

## 16. Milestone 12 — Sandbox Install v1

### Goal

Analyze package installs in a temp workspace.

### Tasks

1. Create temp workspace.
2. Copy manifest/lockfiles.
3. Run package manager install.
4. Capture output.
5. Inspect lifecycle scripts.
6. Capture diffs.
7. Produce sandbox result.
8. Block host mutation by default.

### Acceptance Criteria

- Host project is not mutated.
- Lifecycle scripts are reported.
- Manifest/lockfile diff is captured.
- Sandbox report is generated.
- Migration requires explicit approval.

---

## 17. Milestone 13 — Sweep Engine v1

### Goal

Detect suspicious traces.

### Tasks

1. Implement package script scanner.
2. Implement suspicious pattern scanner.
3. Implement workflow scanner.
4. Implement executable file scanner.
5. Implement credential reference scanner.
6. Implement process/port quick checks where available.
7. Produce findings.

### Acceptance Criteria

- Findings include severity and confidence.
- Secret values are redacted.
- Reports include evidence locations.
- Unsupported platform checks are reported clearly.

---

## 18. Milestone 14 — Scout Reports

### Goal

Generate Markdown and JSON reports.

### Tasks

1. Define report model.
2. Implement Markdown renderer.
3. Implement JSON renderer.
4. Include audit IDs.
5. Include findings.
6. Include uncertainty.
7. Include recommended actions.

### Acceptance Criteria

- Reports are readable.
- Reports avoid overclaiming.
- Reports reference evaluation/audit IDs.
- Reports redact secrets.

---

## 19. Milestone 15 — Polish and Hardening

### Goal

Prepare for practical local use.

### Tasks

1. Improve CLI output.
2. Add config file.
3. Add data location command.
4. Add more tests.
5. Add docs examples.
6. Add packaging instructions.
7. Add sample registries.
8. Add fail-safe tests.

### Acceptance Criteria

- Local install is documented.
- Basic user workflow is smooth.
- Core safety boundary is reliable.
- Docs match behavior.

---

## 20. Implementation Doctrine

Do not optimize before the boundary works.

Do not integrate before the CLI works.

Do not make adaptive behavior safety-critical.

Policy Scout should become powerful by being disciplined, inspectable, and boring where it matters.
