# Policy Scout — Execution, Sandbox, CLI, and Approval Source

## 1. Purpose

This document is the compact source-of-truth for Policy Scout's execution-facing behavior.

It consolidates:

```text
CLI_SPEC.md
SANDBOX_DESIGN.md
APPROVAL_QUEUE_DESIGN.md
MVP_SPEC.md
```

Use this document when changing:

* CLI commands
* CLI output
* CLI exit codes
* command execution behavior
* sandbox package install review
* sandbox migration
* approval queue behavior
* approval storage
* approval expiration
* human override behavior
* execution audit events
* MVP acceptance behavior

Policy Scout must preserve the core boundary:

```text
request -> classify -> policy -> decision -> approval/sandbox/deny -> audit/report
```

The CLI, sandbox, and approval queue are execution adapters.

They do not own policy.

---

## 2. Execution Doctrine

Policy Scout is not an autonomous execution agent.

Policy Scout is a policy-gated safety harness.

Execution doctrine:

```text
Actors request.
Policy Scout decides.
Executors obey.
Audit records everything.
```

Execution-facing code must obey these rules:

1. `check` must never execute commands.
2. `run` must never execute before a policy decision.
3. `sandbox` must not mutate the host project by default.
4. denied commands must not execute.
5. risky commands should not run if audit logging fails.
6. approval is scoped and explicit.
7. agents cannot approve their own risky requests.
8. sandbox migration requires explicit approval.
9. reports and JSON output must not print raw secrets.
10. unsupported or failed verification must be visible.

---

## 3. MVP Execution Goal

Policy Scout v0.1 should prove that a local CLI can:

1. check whether a command is risky
2. explain the decision
3. run allowed commands
4. pause risky commands for approval
5. route package installs to sandbox-first flow
6. sweep a project for suspicious traces
7. produce Scout Reports
8. log decisions and execution results

v0.1 should be useful without:

* editor integration
* MCP integration
* cloud services
* remote policy service
* full malware detection
* automatic remediation

The CLI boundary comes first.

---

## 4. CLI Purpose

The Policy Scout CLI is the first user-facing interface.

It should be:

* clear
* local-first
* scriptable
* beginner-readable
* agent-readable through JSON mode
* conservative under uncertainty
* calm in wording
* auditable

Initial CLI commands:

```text
policy-scout check -- <command>
policy-scout run -- <command>
policy-scout sandbox -- <command>
policy-scout sweep project
policy-scout sweep quick
policy-scout approvals list
policy-scout approvals show <approval_or_request_id>
policy-scout approvals approve <approval_or_request_id>
policy-scout approvals deny <approval_or_request_id>
policy-scout report show <report_id>
policy-scout report export <report_id>
```

Optional later alias:

```text
pscout
```

Do not rely on the alias until packaging is settled.

---

## 5. Global CLI Options

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

### 5.1 `--json`

Outputs machine-readable JSON.

Required for agents, scripts, and future local API workflows.

JSON output must be redaction-safe.

### 5.2 `--mode`

Overrides enforcement mode for the current command.

Initial modes:

```text
beginner
balanced
paranoid
ci
incident
```

### 5.3 `--project`

Specifies project root.

### 5.4 `--config`

Specifies custom config path.

### 5.5 `--policy`

Specifies custom policy file.

### 5.6 `--no-color`

Disables terminal color.

### 5.7 `--verbose`

Shows more detail.

Verbose output must still redact secrets.

### 5.8 `--quiet`

Shows minimal output.

Quiet output must still show safety-critical decisions.

---

## 6. Exit Codes

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

Exit code rules should stay stable once documented.

---

## 7. `policy-scout check`

### Purpose

Analyze a command without executing it.

Usage:

```bash
policy-scout check -- npm install lodash
```

`check` must never execute the command.

### Human Output

Example:

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

Example:

```json
{
  "request_id": "req_123",
  "evaluation_id": "eval_123",
  "decision_id": "dec_123",
  "decision": "SANDBOX_FIRST",
  "risk_score": 7,
  "category": "package_install",
  "confidence": 0.91,
  "policy_hits": [
    "package_installs_sandbox_first"
  ],
  "reasons": [
    "Package installs may execute lifecycle scripts.",
    "Package installs download third-party code.",
    "Package installs can modify manifests and lockfiles."
  ],
  "recommended_next_action": "Run sandbox analysis before host install.",
  "redaction_applied": true
}
```

### `check` Safety Rules

1. Does not execute.
2. May write audit/evaluation records.
3. May return risky or denied decisions.
4. Should preserve granular evaluation data.
5. Should support JSON mode.
6. Should avoid raw secret output.

---

## 8. `policy-scout run`

### Purpose

Run a command through the policy gate.

Usage:

```bash
policy-scout run -- npm test
```

### Decision Handling

```text
ALLOW            -> execute
ALLOW_LOGGED     -> execute and log
REQUIRE_APPROVAL -> create approval request or prompt
SANDBOX_FIRST    -> do not execute directly; suggest sandbox
DENY             -> block
DENY_AND_ALERT   -> block and alert/report
```

### Allowed Example

```bash
policy-scout run -- npm test
```

Example output:

```text
Decision: ALLOW_LOGGED
Running command...
Exit code: 0
Audit event: evt_123
```

### Sandbox-Required Example

```bash
policy-scout run -- npm install lodash
```

Example output:

```text
Decision: SANDBOX_FIRST

This command can install third-party code and may execute lifecycle scripts.

Recommended:
  policy-scout sandbox -- npm install lodash

Command not executed on host.
```

### Run Safety Rules

1. Must classify before execution.
2. Must receive policy decision before execution.
3. Must not execute denied commands.
4. Must not directly execute `SANDBOX_FIRST` commands on host.
5. Must not execute approval-required commands without valid approval.
6. Must write execution events where required.
7. Must fail safely if audit is required but unavailable.

---

## 9. `policy-scout sandbox`

### Purpose

Run supported risky package install commands in a temporary review workspace.

Usage:

```bash
policy-scout sandbox -- npm install lodash
```

Sandbox v1 is not a perfect malware containment system.

It is a safer review workspace for inspecting package install effects before host mutation.

### Initial Sandbox Scope

Sandbox v1 should focus on:

```text
npm install
npm i
pnpm add
yarn add
bun add
```

Optional later:

```text
npx
pnpm dlx
bunx
pip install
cargo install
go install
Docker-backed sandboxing
network-restricted sandboxing
```

The initial sandbox should support package install review, not arbitrary command containment.

---

## 10. Sandbox Doctrine

The sandbox should be:

* local-first
* temporary
* explicit
* auditable
* non-mutating to the host project by default
* conservative about migration
* honest about limitations

Do not imply that v0.1 sandboxing guarantees perfect containment.

Preferred wording:

```text
Sandbox review completed.
Review findings before migrating changes.
Policy Scout could not verify all runtime behavior.
```

Avoid:

```text
Package is guaranteed safe.
Malware impossible.
Sandbox fully contained all behavior.
```

---

## 11. Sandbox Flow

Canonical flow:

```text
SandboxRequested
  -> create temp workspace
  -> copy manifest files
  -> copy lockfiles
  -> inspect/copy package manager config where safe
  -> scrub sensitive environment variables where feasible
  -> run install command
  -> capture output
  -> inspect lifecycle scripts
  -> scan installed package metadata
  -> capture manifest/lockfile diff
  -> run sandbox sweep
  -> produce SandboxResult
  -> produce Scout Report
  -> require approval before migration
```

Short flow:

```text
create temp workspace
copy package files
run install
inspect scripts
capture diffs
sweep sandbox
report findings
require approval before migration
```

---

## 12. Host Project Protection

The sandbox must not mutate the host project automatically.

Allowed host reads:

* package manifest
* lockfile
* package manager config where safe
* project metadata

Host writes:

* none by default
* report output to Policy Scout data directory
* migration only after approval

Do not migrate automatically.

Do not copy arbitrary files back to the host.

---

## 13. Temporary Workspace

The temp workspace should be isolated by path.

Example:

```text
~/.local/share/policy-scout/sandboxes/sbx_<id>/
```

or platform-appropriate cache/data path.

The workspace may include:

```text
package.json
package-lock.json
pnpm-lock.yaml
yarn.lock
bun.lockb
optional package manager config copies
install output logs
sandbox metadata
sandbox result
sandbox Scout Report
```

Debug mode may preserve the workspace.

Default mode should clean up when safe after report generation.

---

## 14. Files to Copy

For v0.1, copy only files needed for package install review.

Common files:

```text
package.json
package-lock.json
pnpm-lock.yaml
yarn.lock
bun.lockb
.npmrc when needed and safe
```

Be careful with `.npmrc`.

`.npmrc` may contain tokens.

If `.npmrc` contains token-like values:

1. detect token-like values
2. warn user
3. prefer redacted copy where possible
4. require explicit approval to copy token-bearing config
5. record decision in audit log

Private registry installs may need credentials.

Do not solve this with a blanket deny forever.

v0.1 should be conservative.

---

## 15. Environment Controls

Sandbox should reduce unnecessary exposure.

Recommended v0.1 controls:

* scrub sensitive environment variables where possible
* set clear sandbox cwd
* avoid copying secret files by default
* avoid reusing host `node_modules`
* capture command output
* record package manager version
* record OS/platform
* optionally support inspection mode without lifecycle scripts later

Sensitive variable values must not be printed.

Sensitive variable names may be referenced when useful.

Examples:

```text
TOKEN
API_KEY
SECRET
PASSWORD
NPM_TOKEN
GITHUB_TOKEN
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
OPENAI_API_KEY
ANTHROPIC_API_KEY
```

---

## 16. Package Manager Detection

Policy Scout should detect package manager from:

* command
* lockfile
* project files
* user override

Examples:

```text
npm install lodash -> npm
pnpm add zod -> pnpm
yarn add react -> yarn
bun add package -> bun
```

The sandbox should run the same package manager requested where available.

If the requested package manager is unavailable, record failure or `could_not_verify`.

Do not silently switch package managers unless explicitly configured.

---

## 17. Lifecycle Script Inspection

The sandbox should inspect lifecycle scripts from package manifests.

Scripts of interest:

```text
preinstall
install
postinstall
prepack
prepare
prepublish
prepublishOnly
```

Suspicious script features:

* shell execution
* child process usage
* network fetch
* credential access
* environment variable enumeration
* obfuscation
* binary download
* chmod/chown
* shell profile modification
* persistence behavior

Lifecycle script findings should feed into SandboxResult and Scout Reports.

---

## 18. Diff Capture

The sandbox should capture changes to:

```text
package.json
package-lock.json
pnpm-lock.yaml
yarn.lock
bun.lockb
```

Reports should show:

* which files changed
* dependency additions
* lockfile created or updated
* scripts added or changed
* package manager metadata changes

Do not migrate automatically.

---

## 19. Sandbox Sweep

After install, run a sandbox sweep.

Initial checks:

* installed package manifests
* lifecycle scripts
* suspicious script content
* unexpected executables
* obfuscated JavaScript patterns
* network fetch patterns
* credential-adjacent references
* workflow file changes if copied

Sandbox findings should feed into the Scout Report.

Findings should include:

* severity
* confidence
* category
* title
* location or evidence reference
* why it matters
* recommended action

---

## 20. Sandbox Result Object

Example:

```json
{
  "sandbox_id": "sbx_123",
  "request_id": "req_123",
  "command": "npm install lodash",
  "package_manager": "npm",
  "temp_workspace": "/path/to/sandbox",
  "exit_code": 0,
  "duration_ms": 2400,
  "manifest_changed": true,
  "lockfile_changed": true,
  "lifecycle_scripts_found": [],
  "findings": [],
  "migration_available": true,
  "migration_requires_approval": true,
  "could_not_verify": [],
  "redaction_applied": true
}
```

Recommended fields:

```text
sandbox_id
request_id
command
package_manager
temp_workspace
started_at
completed_at
exit_code
duration_ms
manifest_changed
lockfile_changed
lifecycle_scripts_found
findings
migration_available
migration_requires_approval
could_not_verify
redaction_applied
```

---

## 21. Sandbox Migration

Migration should be explicit.

Potential command:

```bash
policy-scout sandbox migrate sbx_123
```

For v0.1, migration should only copy approved manifest and lockfile changes.

Do not migrate:

* `node_modules`
* generated scripts
* unknown binaries
* shell profile changes
* arbitrary files
* package manager caches
* sandbox logs

Migration requires approval.

Migration should write audit events.

### Migration Verification

Before migration, verify:

* sandbox ID
* request ID
* source workspace
* target project
* approved files
* approval status
* expiration
* exact command or package manager context where relevant

If verification fails, do not migrate.

---

## 22. Sandbox Install Modes

Potential sandbox modes:

```text
normal_review
ignore_scripts_review
scripts_enabled_review
offline_if_possible
debug_keep_workspace
```

For v0.1, start simple:

```text
normal_review
debug_keep_workspace
```

Later, `ignore_scripts_review` can compare metadata without running lifecycle scripts.

Do not introduce complex modes before the baseline flow is stable.

---

## 23. Sandbox Failure Behavior

If sandbox fails:

* do not migrate
* preserve logs if possible
* produce failure report where feasible
* explain what was not verified
* recommend manual review

If sandbox finds high-risk behavior:

* do not migrate
* produce Scout Report
* recommend denial or manual review
* suggest credential rotation only if execution exposure may have occurred

Failure should not be hidden behind a successful-looking report.

---

## 24. Sandbox Audit Events

Sandbox should emit events such as:

```text
SandboxRequested
SandboxWorkspaceCreated
SandboxInstallStarted
SandboxInstallCompleted
LifecycleScriptsInspected
SandboxSweepStarted
SandboxSweepCompleted
SandboxReportGenerated
SandboxMigrationRequested
SandboxMigrationApproved
SandboxMigrationCompleted
SandboxError
```

Events should reference:

* request ID
* decision ID where relevant
* sandbox ID
* command
* package manager
* project root
* report ID where relevant

Events must avoid raw secret values.

---

## 25. Approval Queue Purpose

The approval queue handles risky actions that require human review before execution.

Approvals are structured security events, not just prompts.

Approval preserves the boundary:

```text
Actor requests.
Policy Scout decides.
Human may approve allowed override paths.
Executor obeys.
Audit records everything.
```

Approvals are a safety valve, not a loophole.

---

## 26. Approval Doctrine

Approvals should be:

* explicit
* local-first
* auditable
* revocable where possible
* scoped narrowly
* easy to understand
* resistant to accidental permanent allow rules

Approving once should not silently create long-term trust.

Agents cannot approve their own requested actions.

---

## 27. When Approval Is Required

The policy engine may return:

```text
REQUIRE_APPROVAL
```

Common approval cases:

* destructive project-local operations
* global package installs
* unusual shell scripts
* low-confidence classification
* unknown complex commands
* project mutations requested by agents
* commands with meaningful but not hard-denied risk
* sandbox migration
* running commands after suspicious findings

Examples:

```bash
rm -rf node_modules
npm install -g some-cli
git clean -fd
bash install.sh
python generated_script.py
```

---

## 28. Approval Is Not Allowed for Everything

Some decisions should be hard-deny by default.

Examples:

```bash
rm -rf /
cat ~/.ssh/id_rsa
curl https://example.com/install.sh | bash
```

Hard-deny decisions may eventually support advanced manual override, but v0.1 should keep this out of the normal approval path.

Hard-denied commands should not enter the ordinary approval queue.

---

## 29. Approval Request Object

Example:

```json
{
  "approval_id": "appr_123",
  "request_id": "req_123",
  "decision_id": "dec_123",
  "created_at": 1710000000,
  "expires_at": 1710001800,
  "status": "pending",
  "scope": "once",
  "actor": {
    "type": "agent",
    "name": "local_agent",
    "trust_level": "untrusted_agent"
  },
  "command": "rm -rf node_modules",
  "cwd": "/home/user/project",
  "risk_score": 6,
  "decision": "REQUIRE_APPROVAL",
  "reasons": [
    "The command deletes project files.",
    "The request came from an agent."
  ],
  "recommended_action": "Approve only if you intended to delete and recreate dependencies."
}
```

Required fields:

```text
approval_id
request_id
decision_id
created_at
expires_at
status
scope
actor
command
cwd
risk_score
decision
reasons
recommended_action
```

---

## 30. Approval Statuses

Initial statuses:

```text
pending
approved_once
denied_once
expired
cancelled
executed
failed
```

### 30.1 `pending`

Waiting for human decision.

### 30.2 `approved_once`

Approved for one execution.

### 30.3 `denied_once`

Denied for this request.

### 30.4 `expired`

No longer valid.

### 30.5 `cancelled`

Cancelled by the requesting actor or system.

### 30.6 `executed`

Approved command was executed.

### 30.7 `failed`

Approval flow failed before execution.

---

## 31. Approval Scope

Initial scopes:

```text
once
session
project
policy_rule
```

For v0.1, only this is required:

```text
once
```

Future scopes may include:

```text
session
project
policy_rule
```

Do not silently create permanent allow rules.

---

## 32. Approval CLI Commands

### List approvals

```bash
policy-scout approvals list
```

Example output:

```text
Pending Approvals

appr_123  risk=6  rm -rf node_modules
appr_124  risk=5  bash install.sh
```

### Show approval

```bash
policy-scout approvals show appr_123
```

Output should include:

* command
* actor
* cwd
* risk score
* decision
* reasons
* policy hits
* recommended action
* expiration
* audit IDs

### Approve once

```bash
policy-scout approvals approve appr_123
```

Approves one execution only.

### Deny once

```bash
policy-scout approvals deny appr_123
```

Denies this request.

Approvals and denials must be logged.

---

## 33. Approval Prompt UX

When a command requires approval, Policy Scout should explain clearly.

Example:

```text
Policy Scout paused this command.

Command:
  rm -rf node_modules

Decision:
  REQUIRE_APPROVAL

Why:
  - This command deletes project files.
  - The request came from an agent.
  - Deletion is reversible only if dependencies can be reinstalled.

Options:
  [a] approve once
  [d] deny
  [?] explain more
```

For package installs:

```text
Policy Scout recommends sandbox-first instead of direct approval.
```

Prompts should not use panic language.

Prompts should not hide uncertainty.

---

## 34. Approval Expiration

Pending approvals should expire.

Suggested defaults:

```text
interactive CLI prompt: immediate
stored pending approval: 30 minutes
CI mode: no prompts, fail closed
incident mode: shorter expiration
```

Expired approvals must not execute.

---

## 35. Approval and Execution

Approval should not directly imply execution unless the user command requested execution.

Flow:

```text
approval requested
user approves
executor verifies approval still valid
executor runs command
audit records execution
approval marked executed
```

Before execution, Policy Scout should re-check:

* approval status
* request ID
* command string
* cwd
* actor
* expiration
* policy version if relevant

This prevents approval confusion.

---

## 36. Approval Store

The approval store should be local.

Suggested storage:

```text
SQLite approvals table
```

Fields:

```text
approval_id
request_id
decision_id
status
scope
command
cwd
actor_type
actor_name
risk_score
created_at
expires_at
resolved_at
resolution
audit_event_ids
```

The approval store should be queryable and durable.

---

## 37. Approval Audit Events

Approval events:

```text
ApprovalRequested
ApprovalShown
ApprovalApprovedOnce
ApprovalDeniedOnce
ApprovalExpired
ApprovalCancelled
ApprovalExecutionStarted
ApprovalExecutionCompleted
ApprovalExecutionFailed
```

Approvals should reference:

* request ID
* decision ID
* approval ID
* actor
* user decision
* timestamp

Audit events must avoid raw secrets.

---

## 38. Approval Security Rules

Approval system rules:

1. Agents cannot approve their own requests.
2. Approval is scoped narrowly.
3. Approval must be logged.
4. Approval must expire.
5. Approval must match exact command and cwd unless explicitly broadened.
6. Approval must not print secrets.
7. Hard-denied commands do not enter the normal approval queue.
8. Approval does not silently create a permanent policy rule.
9. Expired approvals must not execute.
10. Approved-once approvals must not be reused.

---

## 39. CI Mode Behavior

CI mode should be non-interactive.

If a command requires approval in CI mode:

```text
fail closed
write JSON report
exit non-zero
```

No prompt should wait for user input.

CI output should be machine-readable where possible.

CI should not auto-approve.

---

## 40. Incident Mode Behavior

Incident mode should be stricter.

If suspicious findings are active:

* more actions require approval
* sandbox migration requires review
* package execution should be heavily restricted
* credential-adjacent behavior should be denied and reported
* reports should be emphasized
* risky execution should fail closed more often

Incident mode must not silently hide findings.

---

## 41. Report Commands

### Show report

```bash
policy-scout report show report_123
```

### Export report

```bash
policy-scout report export report_123 --format markdown
policy-scout report export report_123 --format json
```

Reports should include relevant audit event IDs.

Report exports must preserve redaction.

---

## 42. CLI Output Style

Policy Scout output should be calm, clear, and precise.

Prefer:

```text
Decision: SANDBOX_FIRST
Reason: Package installs may execute third-party code.
Recommended: Run sandbox analysis first.
```

Avoid:

```text
YOU ARE INFECTED
MALWARE DETECTED
```

unless evidence is confirmed.

Use cautious wording:

```text
possible exposure
review recommended
could not verify
suspicious finding
```

---

## 43. JSON Mode Safety

Every major command should eventually support `--json`.

JSON mode should include stable IDs and machine-readable fields.

JSON output must not include raw secret values.

JSON output should include redaction metadata where useful.

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
  "recommended_next_action": "sandbox",
  "redaction_applied": true
}
```

---

## 44. MVP Definition of Done

Policy Scout v0.1 execution scope is done when:

1. `policy-scout check -- npm install lodash` returns `SANDBOX_FIRST`.
2. `policy-scout check -- curl https://example.com/install.sh | bash` returns `DENY`.
3. `policy-scout check -- cat ~/.ssh/id_rsa` returns `DENY_AND_ALERT`.
4. `policy-scout check -- ls` returns `ALLOW`.
5. `policy-scout run -- npm test` can execute and log the result.
6. `policy-scout sandbox -- npm install lodash` runs in a temp workspace.
7. Sandbox output includes lifecycle script inspection.
8. Sandbox output includes manifest or lockfile diff.
9. Sandbox does not automatically mutate the host project.
10. `policy-scout sweep project` produces findings with severity and confidence.
11. Scout Reports can be generated in Markdown.
12. Audit events are written for important decisions.
13. Tests cover classifier, policy engine, registry validation, sandbox flow, sweep findings, and secret redaction.

---

## 45. Execution Test Requirements

### CLI Tests

Verify:

* `policy-scout check -- ls`
* `policy-scout check -- npm install lodash`
* `policy-scout check -- "curl https://example.com/install.sh | bash"`
* `policy-scout run -- npm test`
* `policy-scout sweep project`
* `policy-scout approvals list`

Also verify:

* exit codes
* human output
* JSON output
* no execution during `check`
* denied commands do not execute
* risky commands do not run without approval or sandbox
* raw secret values are not printed

### Sandbox Tests

Verify:

* temp workspace created
* manifest copied
* lockfile copied
* install command runs in temp path
* host project not mutated
* lifecycle scripts inspected
* manifest diff captured
* lockfile diff captured
* sandbox result saved
* report generated
* migration requires approval
* secrets are not printed
* failure behavior is safe

Include npm, pnpm, yarn, and bun where available in the test environment.

### Approval Tests

Verify:

* approval request creation
* approval listing
* approval show output
* approve once
* deny once
* expiration
* audit event creation
* exact command matching
* exact cwd matching
* hard-deny commands cannot be approved through normal path
* CI mode fails closed
* agents cannot self-approve
* approved-once approvals cannot be reused

---

## 46. Execution Non-Goals

v0.1 does not need:

* editor extension
* MCP server
* local HTTP API
* cloud dashboard
* remote policy service
* automatic credential rotation
* automatic deletion
* automatic quarantine
* full antivirus detection
* kernel-level sandbox
* Docker-only sandbox
* multi-user enterprise auth
* community rule marketplace
* remote registry updater
* deep network packet inspection
* arbitrary command containment
* perfect package malware detection

Do not add these before the CLI execution spine is reliable.

---

## 47. Execution Doctrine Recap

The CLI proves the boundary.

The sandbox reviews risky package installs before host mutation.

The approval queue lets humans stay in control without creating silent trust.

Execution adapters must obey policy decisions.

Reports explain.

Audit records.

The harness stays useful because it stays disciplined.
