# Policy Scout — CLI Specification

## 1. CLI Purpose

The Policy Scout CLI is the first user-facing interface.

It should provide command checking, policy-gated execution, sandbox package installs, sweeps, approvals, and reports without requiring an editor extension or agent integration.

The CLI should be:

- clear
- local-first
- scriptable
- beginner-readable
- agent-readable through JSON mode
- conservative under uncertainty

---

## 2. Command Overview

Initial CLI commands:

```text
policy-scout check -- <command>
policy-scout run -- <command>
policy-scout sandbox -- <command>
policy-scout sweep project
policy-scout sweep quick
policy-scout approvals list
policy-scout approvals show <request_id>
policy-scout approvals approve <request_id>
policy-scout approvals deny <request_id>
policy-scout report show <report_id>
policy-scout report export <report_id>
```

Optional short alias later:

```text
pscout
```

Avoid relying on the alias in docs until packaging is settled.

---

## 3. Global Options

Suggested global options:

```text
--json
--mode <beginner|balanced|paranoid|ci|incident>
--project <path>
--config <path>
--policy <path>
--no-color
--verbose
--quiet
```

### 3.1 `--json`

Outputs machine-readable JSON.

Required for future agents and scripts.

### 3.2 `--mode`

Overrides enforcement mode for the current command.

### 3.3 `--project`

Specifies project root.

### 3.4 `--config`

Specifies custom config path.

### 3.5 `--policy`

Specifies custom policy file.

### 3.6 `--no-color`

Disables terminal color.

### 3.7 `--verbose`

Shows more detail.

### 3.8 `--quiet`

Shows minimal output.

---

## 4. `policy-scout check`

### Purpose

Analyze a command without executing it.

### Usage

```bash
policy-scout check -- npm install lodash
```

### Human Output

```text
Policy Scout Check

Command:
  npm install lodash

Decision:
  SANDBOX_FIRST

Risk:
  7/10

Category:
  package_install

Why:
  - Package installs may execute lifecycle scripts.
  - Package installs download third-party code.
  - Package installs can modify manifests and lockfiles.

Recommended:
  Run sandbox analysis before host install.
```

### JSON Output

```json
{
  "request_id": "req_123",
  "decision": "SANDBOX_FIRST",
  "risk_score": 7,
  "category": "package_install",
  "reasons": [
    "Package installs may execute lifecycle scripts.",
    "Package installs download third-party code.",
    "Package installs can modify manifests and lockfiles."
  ],
  "recommended_next_action": "Run sandbox analysis before host install."
}
```

### Exit Codes

```text
0  allowed or check completed successfully
10 risky but not denied
20 denied
30 error
```

---

## 5. `policy-scout run`

### Purpose

Run a command through the policy gate.

### Usage

```bash
policy-scout run -- npm test
```

### Behavior

```text
ALLOW         -> execute
ALLOW_LOGGED  -> execute and log
REQUIRE_APPROVAL -> create approval request or prompt
SANDBOX_FIRST -> do not execute directly; suggest sandbox
DENY          -> block
DENY_AND_ALERT -> block and alert/report
```

### Example: Allowed

```bash
policy-scout run -- npm test
```

Output:

```text
Decision: ALLOW_LOGGED
Running command...
Exit code: 0
Audit event: evt_123
```

### Example: Sandbox Required

```bash
policy-scout run -- npm install lodash
```

Output:

```text
Decision: SANDBOX_FIRST

This command can install third-party code and may execute lifecycle scripts.

Recommended:
  policy-scout sandbox -- npm install lodash

Command not executed on host.
```

---

## 6. `policy-scout sandbox`

### Purpose

Run supported risky commands in a temporary workspace.

### Usage

```bash
policy-scout sandbox -- npm install lodash
```

### Behavior

1. Create temp workspace.
2. Copy relevant project files.
3. Run install command.
4. Inspect lifecycle scripts.
5. Capture manifest/lockfile diff.
6. Produce sandbox result.
7. Produce Scout Report.
8. Ask before migration.

### Output

```text
Sandbox complete.

Command:
  npm install lodash

Findings:
  0 high
  0 medium
  1 info

Manifest changes:
  package.json changed
  package-lock.json changed

Report:
  scout_report_123.md

Next:
  Review report before migrating changes.
```

### Migration

For v0.1, migration should require explicit approval.

Potential command:

```bash
policy-scout sandbox migrate <sandbox_id>
```

This may be implemented later if needed.

---

## 7. `policy-scout sweep project`

### Purpose

Scan the current project for suspicious traces.

### Usage

```bash
policy-scout sweep project
```

### Checks

- package lifecycle scripts
- suspicious package manifests
- lockfile changes
- GitHub workflows
- executable files
- suspicious JavaScript patterns
- credential-adjacent references

### Output

```text
Project Sweep Complete

Findings:
  High: 1
  Medium: 2
  Low: 3

Report:
  scout_report_project_123.md
```

---

## 8. `policy-scout sweep quick`

### Purpose

Run quick local system checks.

### Usage

```bash
policy-scout sweep quick
```

### Checks

- open ports
- suspicious Node/Bun/Python processes
- package-manager config
- recent shell profile changes
- suspicious temp files

### Output

```text
Quick Sweep Complete

Findings:
  High: 0
  Medium: 1
  Low: 2

Report:
  scout_report_quick_123.md
```

---

## 9. `policy-scout approvals`

### Purpose

Manage pending approvals.

### List

```bash
policy-scout approvals list
```

Output:

```text
Pending Approvals

req_123  SANDBOX_FIRST  npm install lodash
req_124  REQUIRE_APPROVAL  rm -rf node_modules
```

### Show

```bash
policy-scout approvals show req_123
```

Output should include:

- command
- actor
- cwd
- decision
- risk score
- reasons
- policy hits
- recommended action

### Approve

```bash
policy-scout approvals approve req_123
```

Approves once.

### Deny

```bash
policy-scout approvals deny req_123
```

Denies once.

Approvals and denials must be logged.

---

## 10. `policy-scout report`

### Purpose

View and export Scout Reports.

### Show

```bash
policy-scout report show report_123
```

### Export

```bash
policy-scout report export report_123 --format markdown
policy-scout report export report_123 --format json
```

---

## 11. Output Style

Policy Scout output should be clear and calm.

Prefer:

```text
Decision: SANDBOX_FIRST
Reason: Package installs may execute third-party code.
Recommended: Run sandbox analysis first.
```

Avoid panic language unless truly justified.

Avoid:

```text
YOU ARE INFECTED
MALWARE DETECTED
```

unless the finding is confirmed.

---

## 12. JSON Mode

Every major command should eventually support `--json`.

JSON mode should include stable IDs and machine-readable fields.

Example:

```json
{
  "request_id": "req_123",
  "evaluation_id": "eval_123",
  "decision_id": "dec_123",
  "decision": "SANDBOX_FIRST",
  "risk_score": 7,
  "confidence": 0.91,
  "policy_hits": [
    "package_installs_sandbox_first"
  ],
  "recommended_next_action": "sandbox"
}
```

---

## 13. Exit Codes

Suggested exit codes:

```text
0   success / allowed / completed
10  risky decision returned
20  denied
30  command error
40  policy/config error
50  audit logging error
60  sandbox error
70  sweep error
```

CI mode may treat risky decisions as non-zero depending on configuration.

---

## 14. CLI Safety Rules

1. `check` must never execute.
2. `run` must never execute before policy decision.
3. `sandbox` must not mutate host project without approval.
4. denied commands must not execute.
5. secret values must not be printed.
6. risky commands should not run if audit logging fails.
7. unknown complex commands should fail safely.
8. JSON output should not include raw secret values.

---

## 15. CLI Doctrine

The CLI is the first proof that Policy Scout is useful.

It should be boring, clear, fast, and trustworthy.

Do not add agent integration until the CLI boundary works.
