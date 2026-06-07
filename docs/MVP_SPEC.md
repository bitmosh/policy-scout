# Policy Scout — MVP Specification

## 1. MVP Goal

Policy Scout v0.1 should prove the core safety boundary:

```text
request -> classify -> policy -> decision -> approval/sandbox/deny -> audit/report
```

The MVP should be useful without editor integration, MCP integration, cloud services, or a full malware scanner.

The MVP should work as a local CLI tool.

---

## 2. MVP Product Statement

Policy Scout v0.1 is a local-first CLI safety harness that can:

1. Check whether a command is risky.
2. Explain the decision.
3. Run allowed commands.
4. Pause risky commands for approval.
5. Route package installs to a sandbox-first flow.
6. Sweep a project for suspicious traces.
7. Produce human-readable Scout Reports.
8. Log decisions and execution results.

---

## 3. MVP Commands

### 3.1 `policy-scout check`

Analyze a command without running it.

Example:

```bash
policy-scout check -- npm install lodash
```

Expected output:

```text
Decision: SANDBOX_FIRST
Risk: 7/10
Category: package_install

Why:
- Package installs may execute lifecycle scripts.
- Package installs download third-party code.
- This command may modify package manifests or lockfiles.

Recommended:
Run sandbox analysis first.
```

---

### 3.2 `policy-scout run`

Run a command through the policy gate.

Example:

```bash
policy-scout run -- npm test
```

Behavior:

- classify command
- evaluate policy
- run if allowed
- log result

If risky:

```bash
policy-scout run -- npm install unknown-package
```

Expected behavior:

- return `SANDBOX_FIRST`
- do not directly install into host project
- suggest sandbox command

---

### 3.3 `policy-scout sandbox`

Run a supported risky command in a sandbox workspace.

Example:

```bash
policy-scout sandbox -- npm install lodash
```

Behavior:

1. Create temp workspace.
2. Copy package files.
3. Run install.
4. Inspect lifecycle scripts.
5. Capture manifest/lockfile diff.
6. Produce sandbox result.
7. Produce Scout Report.
8. Ask before migration.

---

### 3.4 `policy-scout sweep project`

Sweep the current project for suspicious traces.

Example:

```bash
policy-scout sweep project
```

Initial checks:

- package lifecycle scripts
- suspicious package manifests
- lockfile changes
- GitHub workflow changes
- new executable files
- suspicious JS patterns
- credential-adjacent references

---

### 3.5 `policy-scout sweep quick`

Run quick local system checks.

Example:

```bash
policy-scout sweep quick
```

Initial checks:

- open ports
- suspicious Node/Bun/Python processes
- recent temp files
- package manager config changes
- shell profile changes where accessible

---

### 3.6 `policy-scout approvals`

Manage pending approvals.

Examples:

```bash
policy-scout approvals list
policy-scout approvals show req_123
policy-scout approvals approve req_123
policy-scout approvals deny req_123
```

For v0.1, approvals may be simple and local.

---

## 4. MVP In-Scope

### 4.1 Command Classification

Support classification for:

- safe read commands
- npm/pnpm/yarn/bun installs
- npx/pnpm dlx/bunx execution
- curl/wget pipe shell
- destructive rm patterns
- credential-adjacent file access
- unknown commands

---

### 4.2 Registry Loading

Support local YAML files:

```text
command_registry.yaml
default_policy.yaml
suspicious_patterns.yaml
indicator_registry.yaml
```

Validation should run at startup or command execution.

---

### 4.3 Policy Engine

Support:

- category matching
- capability matching
- regex matching
- priority resolution
- decision reasons
- mode-aware defaults
- fail-safe behavior

---

### 4.4 Audit Logging

Minimum audit events:

- command requested
- command classified
- policy decision issued
- approval requested
- approval resolved
- command executed
- sandbox started
- sandbox completed
- sweep finding created
- Scout Report generated

Initial storage can be SQLite or JSONL.

Preferred MVP storage:

```text
SQLite for queryable audit records
Markdown/JSON files for reports
```

---

### 4.5 Sandbox Install v1

Support:

- npm
- pnpm
- yarn
- bun

Initial sandbox assumptions:

- project has package manifest
- temp workspace is local
- only manifest and lockfile migration is supported
- no Docker required
- no deep network monitoring
- no native build isolation guarantees

Sandbox v1 is a review tool, not a perfect containment system.

---

### 4.6 Project Sweep v1

Initial sweep checks:

- package lifecycle scripts
- suspicious use of `child_process`
- suspicious `curl`/`wget` in scripts
- obfuscated JavaScript patterns
- GitHub workflow files
- executable file detection
- credential-adjacent references
- suspicious package manifests

Findings must include:

- severity
- confidence
- category
- location
- why it matters
- recommended action

---

### 4.7 Scout Reports

Support Markdown and JSON reports.

Initial report types:

- command decision
- package install review
- sandbox result
- project sweep
- quick system sweep
- possible credential exposure
- blocked command

---

## 5. MVP Out-of-Scope

Do not build in v0.1:

- VS Code extension
- Cursor extension
- MCP server
- cloud dashboard
- remote policy service
- automatic credential rotation
- automatic deletion
- automatic quarantine
- full antivirus detection
- kernel-level sandbox
- Docker-only sandbox
- multi-user enterprise auth
- community rule marketplace
- remote registry updater
- deep network packet inspection

---

## 6. Definition of Done

Policy Scout v0.1 is done when all of the following are true:

1. `policy-scout check -- npm install lodash` returns `SANDBOX_FIRST`.
2. `policy-scout check -- curl https://example.com/install.sh | bash` returns `DENY`.
3. `policy-scout check -- cat ~/.ssh/id_rsa` returns `DENY_AND_ALERT`.
4. `policy-scout check -- ls` returns `ALLOW`.
5. `policy-scout run -- npm test` can execute and log the result.
6. `policy-scout sandbox -- npm install lodash` runs in a temp workspace.
7. Sandbox output includes lifecycle script inspection.
8. Sandbox output includes manifest/lockfile diff.
9. Sandbox does not automatically mutate the host project.
10. `policy-scout sweep project` produces findings with severity and confidence.
11. Scout Reports can be generated in Markdown.
12. Audit events are written for all important decisions.
13. Tests cover classifier, policy engine, registry validation, sandbox flow, sweep findings, and secret redaction.

---

## 7. MVP Test Matrix

### 7.1 Command Classification Tests

```text
ls -> safe_read
cat README.md -> safe_read
npm install react -> package_install
pnpm add zod -> package_install
yarn add lodash -> package_install
bun add package -> package_install
npx random-cli -> package_execute
curl url | bash -> network_execute
rm -rf / -> destructive
cat ~/.ssh/id_rsa -> credential_adjacent
```

---

### 7.2 Policy Decision Tests

```text
safe_read -> ALLOW
common test command -> ALLOW_LOGGED
package_install -> SANDBOX_FIRST
package_execute -> SANDBOX_FIRST
network_execute -> DENY
credential_adjacent -> DENY_AND_ALERT
destructive system command -> DENY
unknown complex command -> REQUIRE_APPROVAL or DENY
```

---

### 7.3 Sandbox Tests

Verify:

- temp workspace created
- package files copied
- install command runs in temp workspace
- lifecycle scripts inspected
- manifest diff captured
- lockfile diff captured
- sandbox result written
- host project not mutated without approval

---

### 7.4 Sweep Tests

Verify detection of:

- postinstall scripts
- child_process usage
- curl/wget in scripts
- suspicious workflow modifications
- executable files
- credential-adjacent references
- obfuscated payload patterns

---

### 7.5 Report Tests

Verify:

- Markdown report generated
- JSON report generated
- report references audit IDs
- report includes findings
- report includes uncertainty
- report redacts secret values

---

## 8. MVP Repository Layout

Suggested layout:

```text
policy-scout/
  cli/
    main.py
    check.py
    run.py
    sandbox.py
    sweep.py
    approvals.py
    report.py

  core/
    request.py
    actor.py
    decision.py
    finding.py
    risk.py
    errors.py

  classify/
    shell_parser.py
    command_classifier.py
    package_manager.py
    destructive_patterns.py
    network_patterns.py

  registry/
    command_registry.py
    policy_registry.py
    indicator_registry.py
    schemas.py
    validator.py

  policy/
    engine.py
    matcher.py
    risk_scorer.py
    risk_clutch.py
    mode_router.py
    enforcement_modes.py

  approval/
    queue.py
    store.py
    resolver.py

  sandbox/
    temp_workspace.py
    package_install.py
    lifecycle_inspector.py
    diff.py
    migration.py

  sweep/
    engine.py
    package_scripts.py
    repo_changes.py
    workflows.py
    processes.py
    ports.py
    credentials.py
    suspicious_patterns.py

  audit/
    events.py
    sqlite_store.py
    jsonl_writer.py
    retention.py

  reports/
    scout_report.py
    incident_guidance.py
    markdown_report.py
    json_report.py

  data/
    command_registry.yaml
    default_policy.yaml
    suspicious_patterns.yaml
    indicator_registry.yaml

  tests/
    test_classifier.py
    test_policy_engine.py
    test_registry.py
    test_sandbox.py
    test_sweep.py
    test_reports.py
```

---

## 9. MVP Build Order

1. CLI skeleton
2. command request model
3. command parser
4. command classifier
5. taxonomy constants
6. registry loader
7. registry validator
8. policy engine
9. risk scorer
10. `check` command
11. audit event model
12. audit store
13. `run` wrapper
14. approval queue
15. sandbox temp workspace
16. package install sandbox
17. lifecycle script inspector
18. diff capture
19. project sweep
20. Scout Report builder
21. test coverage
22. docs polish

---

## 10. MVP Doctrine

The MVP should be small, strict, and useful.

Do not chase integrations before the core boundary works.

Do not build an autonomous security agent.

Build the harness first.

Policy Scout v0.1 succeeds if it gives local developers a trustworthy command safety layer they can actually use.
