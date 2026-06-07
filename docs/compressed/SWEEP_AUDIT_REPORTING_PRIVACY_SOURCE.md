# Policy Scout — Sweep, Audit, Reporting, Privacy, and Testing Source

## 1. Purpose

This document is the compact source-of-truth for Policy Scout's sweep engine, audit layer, Scout Reports, privacy rules, redaction requirements, and verification strategy.

It consolidates:

```text
SWEEP_ENGINE_DESIGN.md
AUDIT_AND_REPORTING.md
LOCAL_FIRST_AND_PRIVACY.md
TESTING_STRATEGY.md
SCOUT_REPORT_ANATOMY.md
```

Use this document when changing:

* project sweep behavior
* quick system sweep behavior
* sandbox sweep behavior
* findings
* severity/confidence handling
* `could_not_verify` behavior
* audit events
* audit persistence
* report generation
* report metadata
* credential exposure assessment
* redaction
* local data storage
* JSON/Markdown output safety
* sweep/report/audit/privacy tests

Policy Scout must preserve:

* local-first operation
* cautious wording
* evidence-based findings
* auditability
* structured report output
* secret redaction
* fail-safe behavior
* granular verification tests

---

## 2. Core Doctrine

Policy Scout is a safety harness, not a full endpoint security platform.

Sweep, audit, and report doctrine:

```text
Sweeps gather evidence.
Findings preserve uncertainty.
Audit records what happened.
Reports explain what happened.
Privacy rules prevent the explanation from leaking secrets.
Tests prove the boundary still holds.
```

Sweeps must not overclaim.

Use calm wording:

```text
suspicious finding
possible exposure
review recommended
could not verify
```

Avoid unsupported claims:

```text
malware confirmed
your machine is infected
credentials definitely stolen
```

unless evidence is confirmed.

---

## 3. Sweep Engine Purpose

The sweep engine checks projects and local development environments for suspicious traces.

Sweeps help answer:

```text
Did something suspicious get introduced?
Did a package install leave risky artifacts?
Did a workflow change?
Are there suspicious scripts?
Are there unexpected processes or ports?
Could credentials have been exposed?
What could Policy Scout not verify?
```

Sweeps are evidence-gathering.

Sweeps are not perfect malware detection.

---

## 4. Sweep Types

Initial sweep types:

```text
project
quick
sandbox
deep
```

### 4.1 Project Sweep

Scans the current project.

Command:

```bash
policy-scout sweep project
```

Purpose:

* inspect package scripts
* inspect workflow files
* inspect suspicious code patterns
* inspect credential-adjacent references
* inspect executable files
* inspect repository mutations

### 4.2 Quick System Sweep

Checks local system development signals.

Command:

```bash
policy-scout sweep quick
```

Purpose:

* inspect listening ports
* inspect suspicious development processes
* inspect recent shell profile changes
* inspect package manager config indicators
* inspect suspicious temp files
* inspect sensitive environment variable names

Quick sweep is Linux-first in v0.1.

Unsupported checks must be visible through `could_not_verify`.

### 4.3 Sandbox Sweep

Runs after sandbox package install.

Purpose:

* inspect installed package metadata
* inspect lifecycle scripts
* inspect generated files
* inspect suspicious JavaScript
* inspect network-fetch patterns
* inspect credential-adjacent references
* inspect unexpected executables

Sandbox findings feed into sandbox Scout Reports.

### 4.4 Deep Sweep

Future mode for more expensive checks.

Not required for v0.1.

---

## 5. Project Sweep Scope

Initial project sweep checks:

* package lifecycle scripts
* suspicious package manifests
* lockfile changes
* GitHub Actions workflows
* GitLab CI files
* new executable files
* suspicious JavaScript patterns
* shell scripts
* credential-adjacent references
* package manager config
* unexpected project mutations

Policy Scout should not assume all mutations are malicious.

It should report context and evidence.

---

## 6. Quick System Sweep Scope

Initial quick system checks:

* open ports
* listening processes
* suspicious Node/Bun/Python processes
* recent shell profile changes
* package manager config token indicators
* suspicious temp files
* sensitive environment variable names

Quick sweep findings should avoid panic.

Open ports are not automatically suspicious.

Developer tools commonly bind ports.

Process command lines may contain secrets and must be redacted.

---

## 7. Sandbox Sweep Scope

Sandbox sweeps should inspect:

* installed package manifests
* lifecycle scripts
* generated files
* package scripts
* obfuscated JavaScript
* network-fetch patterns
* child process usage
* credential-adjacent references
* unexpected executables

Sandbox sweep should never imply the package is guaranteed safe.

Preferred wording:

```text
Sandbox review completed.
Review findings before migrating changes.
Policy Scout could not verify all runtime behavior.
```

Avoid:

```text
Package is guaranteed safe.
Sandbox fully contained all behavior.
```

---

## 8. Sweep Result Model

A sweep result should include:

```json
{
  "sweep_id": "sweep_123",
  "sweep_type": "project",
  "started_at": 1710000000,
  "completed_at": 1710000042,
  "project_root": "/home/user/project",
  "platform": "linux",
  "findings_count": {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4
  },
  "findings": [],
  "could_not_verify": [
    "system process list unavailable"
  ],
  "redaction_applied": true,
  "schema_version": 1
}
```

Recommended sweep types:

```text
project
quick_system
sandbox
deep
```

Recommended report types:

```text
project_sweep
system_quick_sweep
sandbox_result
```

If code uses `quick_system` internally, reports should still label the report clearly as a quick system sweep.

---

## 9. Finding Model

Every finding should include:

```json
{
  "finding_id": "find_123",
  "sweep_id": "sweep_123",
  "severity": "high",
  "confidence": "moderate",
  "category": "suspicious_lifecycle_script",
  "title": "Package postinstall script invokes child_process",
  "location": "node_modules/example/package.json",
  "evidence_ref": "evidence_123",
  "why_it_matters": "Lifecycle scripts can execute arbitrary commands during install.",
  "recommended_action": "Review script before approving host install."
}
```

Required fields:

* finding ID
* sweep ID or parent ID
* severity
* confidence
* category
* title
* location or evidence reference
* why it matters
* recommended action

Findings must avoid raw secret values.

---

## 10. Severity and Confidence

Severity and confidence are separate.

Severity describes potential impact.

Confidence describes certainty.

Severity values:

```text
info
low
medium
high
critical
```

Confidence values:

```text
low
moderate
high
confirmed
```

Example:

```text
Severity: high
Confidence: moderate
```

Meaning:

```text
The possible impact is high, but the evidence is not definitive.
```

Do not flatten severity and confidence into a single score only.

---

## 11. Finding Categories

Initial project/sandbox categories:

```text
known_bad_package
suspicious_lifecycle_script
secret_harvesting_pattern
network_exfiltration_pattern
workflow_injection
unexpected_open_port
suspicious_process
credential_file_access
repo_mutation
package_publish_risk
destructive_payload
persistence_mechanism
obfuscated_payload
suspicious_shell_profile_change
suspicious_package_manifest
unknown_suspicious_artifact
```

Quick system sweep may use:

```text
open_port
suspicious_process
suspicious_temp_file
shell_profile_change
package_manager_config
credential_exposure_signal
```

Do not invent new categories casually.

If a category is added, update:

* compiled taxonomy/model source
* registry validation if relevant
* report handling if relevant
* tests

---

## 12. Common Sweep Checks

### 12.1 Package Script Checks

Inspect `package.json` scripts.

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

Suspicious indicators:

* `child_process`
* `curl`
* `wget`
* `bash`
* `sh`
* environment variable enumeration
* credential file paths
* obfuscated payloads
* binary downloads
* chmod/chown
* shell profile modification

### 12.2 Workflow Checks

Inspect:

```text
.github/workflows/*.yml
.github/workflows/*.yaml
.gitlab-ci.yml
```

Suspicious indicators:

* secret printing
* unexpected curl/wget execution
* package publishing changes
* credential exfiltration patterns
* unexpected new workflow files
* dangerous shell commands

### 12.3 Executable File Checks

Signals:

* executable bit set
* binary in unexpected path
* script with dangerous shebang
* recently created executable
* executable inside package scripts path
* executable referenced by lifecycle script

### 12.4 Obfuscation Checks

Initial suspicious JavaScript patterns:

* large base64 blobs
* `eval`
* `Function(...)`
* heavily encoded strings
* char-code reconstruction
* suspicious minified lifecycle scripts
* hidden network URLs

Obfuscation alone is not proof of compromise.

### 12.5 Credential-Adjacent Checks

Detect references to:

```text
.env
.npmrc
.ssh
id_rsa
id_ed25519
AWS_ACCESS_KEY
GITHUB_TOKEN
NPM_TOKEN
OPENAI_API_KEY
ANTHROPIC_API_KEY
```

Do not print secret values.

### 12.6 Open Port Checks

Quick system sweep may inspect listening ports.

Findings may include:

* port
* process name
* PID where available
* local bind
* remote bind where relevant
* redacted command summary
* confidence

Open ports are not automatically malicious.

Prefer:

```text
A development process appears to be listening on all interfaces. Review exposure if unexpected.
```

Avoid:

```text
Possible network backdoor.
```

unless evidence supports that stronger claim.

### 12.7 Process Checks

Quick system sweep may inspect processes.

Signals:

* unexpected `node`
* unexpected `bun`
* unexpected `python`
* process running from temp directory
* process command references suspicious script
* process spawned near suspicious install time

Process command lines must be redacted before JSON, Markdown, terminal, or audit output.

### 12.8 Shell Profile Checks

Quick system sweep may inspect:

```text
~/.bashrc
~/.bash_profile
~/.profile
~/.zshrc
~/.config/fish/config.fish
```

Possible findings:

* recent modification
* suspicious command added
* curl/wget pipe
* token-looking material
* PATH hijack pattern
* startup persistence signal

Recent modification alone may be noisy.

Use low or moderate confidence unless content is clearly suspicious.

### 12.9 Package Manager Config Checks

Quick system sweep may inspect:

```text
~/.npmrc
.npmrc
.yarnrc
.yarnrc.yml
.pnpmrc
```

These files may contain tokens.

Do not print token values.

Report token indicators with cautious wording.

### 12.10 Temp File Checks

Quick system sweep may inspect temp directories for suspicious files.

Signals:

* executable file in temp
* script-like names
* recent suspicious executable
* Node/Python/Bun scripts in temp
* file referenced by a suspicious process

Temp findings can be noisy.

Use evidence and confidence carefully.

---

## 13. `could_not_verify`

`could_not_verify` is a trust feature.

It should record checks Policy Scout could not complete.

Examples:

```text
ss unavailable; listening port check could not be verified
netstat unavailable; fallback port check could not be verified
ps unavailable; process check could not be verified
unsupported platform; shell profile check limited
permission denied reading package manager config
file decoding failed for shell profile
```

Rules:

1. Do not collapse failed checks into "no findings."
2. Do not hide failed checks because another check produced findings.
3. Use check-specific messages where practical.
4. Include `could_not_verify` in JSON and Markdown reports.
5. Use cautious language.
6. Failed verification should not crash the sweep.

For sweeps, fail-safe means preserving uncertainty.

---

## 14. False Positive Handling

False positives are expected.

Policy Scout should reduce harm by:

* separating severity from confidence
* explaining why a finding matters
* showing evidence location
* avoiding absolute claims
* allowing user review
* allowing future suppression rules with audit trail

Suppression rules are not required for v0.1.

If suppression is added later, it must be explicit and auditable.

---

## 15. Evidence and Redaction

Sweep evidence must avoid secret leakage.

Good:

```text
Credential-adjacent file referenced: .env
```

Bad:

```text
OPENAI_API_KEY=sk-actual-value
```

Use:

* evidence references
* redacted excerpts
* project-relative paths where possible
* `~` for home directory where practical
* process names instead of full command lines where possible
* redacted command summaries when necessary

---

## 16. Audit Layer Purpose

Policy Scout must make risky actions visible, explainable, and reviewable.

The audit layer records what happened.

The report layer explains what happened.

Policy Scout should not rely on terminal output as the only record.

Every important action should produce an audit event.

---

## 17. Audit Doctrine

Audit events should be:

* local-first
* append-first
* timestamped
* linked by IDs
* structured
* queryable
* redacted
* durable according to retention policy

Audit records are local durable state.

They may contain sensitive metadata.

Store them locally and document their location.

---

## 18. Audit Event Types

Core event types:

```text
CommandRequested
CommandParsed
CommandClassified
CapabilitiesDetected
ContextInspected
RegistryMatched
PolicyMatched
DecisionIssued
ApprovalRequested
ApprovalResolved
CommandExecutionStarted
CommandExecutionCompleted
SandboxStarted
SandboxCompleted
SweepStarted
SweepCompleted
SweepFindingCreated
ScoutReportGenerated
PolicyError
AuditError
SandboxError
SweepError
```

Subsystem-specific events may include:

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
SandboxMigrationPlanned
SandboxMigrationStarted
SandboxMigrationCompleted
SandboxMigrationBlocked
SandboxMigrationFailed
ApprovalApprovedOnce
ApprovalDeniedOnce
ApprovalExecutionStarted
ApprovalExecutionCompleted
ApprovalExecutionFailed
```

Risk/clutch events may include:

```text
RiskScored
RiskComponentAdded
ClutchEvaluated
ModeChanged
FrictionIncreased
FrictionReduced
IncidentModeEntered
IncidentModeCleared
```

---

## 19. Core Audit Event Shape

Example:

```json
{
  "event_id": "evt_123",
  "event_type": "DecisionIssued",
  "timestamp": 1710000000,
  "request_id": "req_123",
  "actor": {
    "type": "agent",
    "name": "local_agent"
  },
  "summary": "Policy decision issued for package install.",
  "data": {
    "decision": "SANDBOX_FIRST",
    "risk_score": 7,
    "policy_hits": [
      "package_installs_sandbox_first"
    ]
  },
  "redaction_applied": true
}
```

Event `data` should avoid raw secret values.

---

## 20. ID Relationships

Important IDs:

```text
request_id
evaluation_id
decision_id
approval_id
execution_id
sandbox_id
sweep_id
finding_id
report_id
event_id
```

Reports should reference relevant IDs.

Example:

```text
Scout Report report_123
  request_id: req_123
  decision_id: dec_123
  sandbox_id: sbx_123
  audit_events:
    - evt_100
    - evt_101
    - evt_102
```

---

## 21. Audit Storage

Initial storage options:

```text
SQLite
JSONL
```

Recommended:

```text
SQLite as primary
JSONL as optional export/debug stream
```

SQLite benefits:

* queryable
* structured
* local
* durable
* useful for future UI

JSONL benefits:

* easy to inspect
* easy to export
* easy to append

---

## 22. Audit Retention

Initial retention policy:

* keep all audit events locally by default
* allow user-configurable retention later
* allow export later
* allow manual purge later
* never print secrets into logs

For v0.1, avoid complicated retention automation.

Do not silently discard audit records.

---

## 23. Audit Failure Behavior

If audit logging fails:

* low-risk `check` may continue with warning
* risky `run` should not execute
* denied commands remain denied
* sandbox migration should not proceed
* report generation should warn that audit persistence failed

Policy Scout should not silently run risky commands without auditability.

---

## 24. Scout Report Purpose

Scout Reports are human-readable and machine-readable explanations of important actions or findings.

Reports should answer:

```text
What happened?
Why did Policy Scout care?
What evidence exists?
How confident is Policy Scout?
What should the user do next?
What could not be verified?
Which audit events support this?
```

Reports should make the user feel informed, not scared.

---

## 25. Scout Report Doctrine

A Scout Report should be:

* calm
* precise
* evidence-based
* redaction-safe
* useful for beginners
* useful for advanced developers
* machine-readable where possible
* linked to audit events

Reports should not overclaim.

---

## 26. Report Types

Initial report types:

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

Use `system_quick_sweep` for quick system sweep reports.

Use `project_sweep` for project sweep reports.

Do not label quick system sweeps as project sweeps.

---

## 27. Recommended Report Sections

Recommended Markdown sections:

```text
# Scout Report: <Title>

## 1. Summary

## 2. Decision / Risk Level

## 3. Triggering Command or Sweep

## 4. Timeline

## 5. Findings

## 6. Evidence

## 7. Credential Exposure Assessment

## 8. Recommended Actions

## 9. Files Changed

## 10. Open Ports / Processes

## 11. What Policy Scout Could Not Verify

## 12. Audit Event IDs
```

Not every report needs every section.

---

## 28. Report Fields

Reports should include where relevant:

* report ID
* report type
* title
* created timestamp
* request ID
* evaluation ID
* decision ID
* sandbox ID
* sweep ID
* finding IDs
* audit event IDs
* findings
* risk score
* risk band
* risk components
* confidence
* evidence strength
* credential exposure assessment
* recommended actions
* `could_not_verify`
* redaction metadata

---

## 29. Finding Presentation

Each finding should show:

```text
Finding: <title>
Severity: <severity>
Confidence: <confidence>
Category: <category>
Location: <location>

Why it matters:
<why_it_matters>

Recommended action:
<recommended_action>
```

Findings should preserve uncertainty.

---

## 30. Evidence Section

Evidence should reference locations.

Good:

```text
Evidence:
- package.json contains a postinstall script
- scripts/install.js imports child_process
- package-lock.json changed
```

Bad:

```text
OPENAI_API_KEY=sk-actual-value
```

Evidence should not reveal raw secrets.

---

## 31. Credential Exposure Assessment

Reports should include credential guidance when relevant.

Possible levels:

```text
none_detected
unlikely
possible
likely
confirmed
unknown
```

Use conservative wording.

Example:

```text
Credential exposure is possible because a lifecycle script referenced environment variables. Policy Scout did not verify exfiltration.
```

Do not claim confirmed exposure unless evidence confirms exposure.

### 31.1 Suggested Assessment Rules

Use `none_detected` when:

* no credential-adjacent findings exist
* no sensitive env/config indicators exist
* no secret-looking evidence appears

Use `possible` when:

* credential-adjacent files are referenced
* package-manager config token indicators are found
* sensitive environment variable names are present
* process command lines contain redacted secret-like values
* lifecycle scripts enumerate environment variables
* suspicious code references token-like names

Use `likely` when:

* a script accessed credential-adjacent files during execution
* evidence strongly suggests secret harvesting behavior
* a network-send path is paired with credential reads

Use `confirmed` only when:

* confirmed evidence shows credential material was exposed or transmitted

Use `unknown` when:

* checks failed
* evidence is incomplete
* unsupported platform prevents meaningful assessment

---

## 32. Recommended Actions

Recommended actions should be practical, ordered, and cautious.

Examples:

```text
Review the lifecycle script before approving migration.
Do not run this command on the host.
Run a project sweep.
Check whether .env or .npmrc was accessible.
Rotate tokens if the script executed and secrets may have been exposed.
Review recent package/lockfile changes.
Keep the Scout Report for audit context.
```

Distinguish between:

* immediate action
* optional follow-up
* manual review
* external tools
* what Policy Scout cannot verify

---

## 33. Report Tone

Good:

```text
Policy Scout found a suspicious lifecycle script. Review is recommended before host installation.
```

Bad:

```text
Your machine is infected.
```

unless supported by confirmed evidence.

Good:

```text
Credential exposure is possible. Policy Scout did not verify exfiltration.
```

Bad:

```text
Your credentials were stolen.
```

unless supported by confirmed evidence.

---

## 34. Agent-Readable Reports

JSON reports should include:

* IDs
* machine-readable findings
* policy hits
* risk components
* evidence references
* recommended actions
* uncertainty fields
* redaction metadata

Agents may summarize reports, but must not hide findings.

Agents should not receive raw secret evidence.

---

## 35. Local-First Doctrine

Policy Scout is local-first because durable state stays on the user's machine by default.

Local durable state includes:

* command requests
* policy decisions
* audit events
* approval history
* sandbox results
* Scout Reports
* local registries
* local policies
* sweep findings
* configuration

No automatic remote upload in v0.1.

---

## 36. Offline Capability

Policy Scout v0.1 should work offline for:

* command checking
* policy decisions
* registry matching
* local audit logging
* local package sandboxing where dependencies are cached or install network is user-approved
* project sweeps
* quick system sweeps
* report generation

Package installation itself may require network access because package managers use remote registries.

Policy Scout should distinguish between its own network needs and the command's network needs.

---

## 37. Local Data Locations

Suggested Linux paths:

```text
~/.config/policy-scout/
~/.local/share/policy-scout/
~/.cache/policy-scout/
```

Possible layout:

```text
~/.config/policy-scout/config.yaml
~/.config/policy-scout/policies/
~/.config/policy-scout/registries/
~/.local/share/policy-scout/audit.db
~/.local/share/policy-scout/audit.jsonl
~/.local/share/policy-scout/reports/
~/.local/share/policy-scout/sandboxes/
~/.cache/policy-scout/tmp/
```

---

## 38. What Stays Local

The following should stay local by default:

```text
audit.db
audit.jsonl
Scout Reports
approval records
sandbox logs
sandbox result metadata
registry files
policy files
config files
sweep findings
```

No automatic remote upload in v0.1.

---

## 39. Optional Future Network Features

Future optional features may include:

* rule pack updates
* known malicious indicator updates
* vulnerability database lookup
* package reputation lookup
* remote policy pack download
* cloud backup
* team policy sync

These are optional adapters, not core dependencies.

No silent telemetry in v0.1.

---

## 40. Privacy-Sensitive Data

Policy Scout may encounter:

* `.env`
* `.npmrc`
* SSH keys
* API keys
* package registry tokens
* cloud credentials
* shell history
* local file paths
* project names
* process command lines
* environment variables
* private package names

Policy Scout must avoid exposing this data unnecessarily.

---

## 41. Secret Redaction

Redact secrets in:

* terminal output
* audit logs
* Scout Reports
* JSON exports
* error messages
* sandbox logs where feasible

Preferred placeholders:

```text
<redacted:possible_token>
<redacted:ssh_private_key>
<redacted:env_value>
```

Good:

```text
Credential-adjacent file referenced: .env
```

Bad:

```text
OPENAI_API_KEY=sk-actual-value
```

---

## 42. Environment Variable Handling

Package installs and scripts may inherit environment variables.

Sandbox and quick sweep should reduce exposure where feasible.

Rules:

* remove obvious secret environment variables from sandbox child processes where possible
* log that environment was scrubbed
* allow user override for private registries when needed
* never print environment variable values
* record sensitive variable names only when safe and useful

Sensitive variable names include:

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

## 43. Package Manager Config Privacy

Package manager config files may contain tokens.

Examples:

```text
.npmrc
~/.npmrc
.yarnrc
.yarnrc.yml
.pnpmrc
```

Policy Scout should:

1. detect token-like values
2. avoid printing values
3. warn with cautious wording
4. prefer redacted evidence
5. require approval before copying token-bearing config into sandbox where relevant
6. record related decisions in audit log

Private registry installs may need credentials.

Do not solve this with a blanket deny forever.

---

## 44. Local Path Privacy

Local file paths can reveal private information.

Guidance:

* show project-relative paths where possible
* avoid exposing home directory unnecessarily
* normalize home paths to `~` in user-facing output where practical
* include full paths only in local audit when useful
* allow future sanitized export mode

---

## 45. Process Information Privacy

Process command lines can include secrets.

Policy Scout should:

* avoid printing full command lines by default
* redact token-like substrings
* include PID/process name when useful
* include redacted command summaries when useful
* avoid raw command line output in JSON and Markdown reports

Redact common forms:

```text
--token value
--api-key value
--password value
--secret value
TOKEN=value
API_KEY=value
SECRET=value
PASSWORD=value
Bearer <token>
?token=...
?api_key=...
?access_token=...
```

---

## 46. Report Privacy

Scout Reports should be safe to share when possible, but not assumed public.

Reports should:

* redact secrets
* include evidence references
* avoid raw secret values
* explain what was redacted
* support JSON and Markdown
* eventually support sanitized export

---

## 47. Audit Privacy

Audit logs are useful but sensitive.

They may contain:

* commands
* paths
* actor names
* package names
* findings
* process names
* approval history

Audit exports should warn users that exported logs may contain sensitive metadata.

---

## 48. Privacy and LLMs

If LLM explanation support is added later, LLMs should not receive:

* raw secrets
* private keys
* full `.env` contents
* unredacted credential files
* unnecessary command history
* full audit logs by default

LLMs may receive:

* redacted findings
* summarized evidence
* policy hits
* risk components
* report drafts

LLM use should be optional.

---

## 49. Privacy and Agent Integrations

Agents should receive the minimum information needed.

For a blocked command, an agent may receive:

```json
{
  "decision": "DENY",
  "reason": "Credential-adjacent file access is not allowed.",
  "allowed_next_actions": [
    "ask_user_for_manual_review",
    "request_non_secret_file"
  ]
}
```

Agents should not receive secret evidence.

---

## 50. Network Transparency

If Policy Scout itself uses network access in the future, it should disclose:

* destination
* purpose
* data sent
* data received
* whether result is cached
* whether user can disable it

No silent telemetry in v0.1.

---

## 51. Testing Doctrine

Policy Scout is security-adjacent.

Tests must verify more than happy paths.

Tests should prove that Policy Scout:

* classifies commands correctly
* preserves granular evaluation data
* applies policies deterministically
* fails safely under uncertainty
* logs important events
* redacts secrets
* blocks risky commands
* avoids silent safety regression

Do not only test final decisions.

Test granular signals.

---

## 52. Required Test Categories

Initial test categories:

```text
model tests
parser tests
classifier tests
capability tests
registry tests
policy tests
risk scoring tests
clutch/mode tests
audit tests
approval tests
sandbox tests
sweep tests
quick sweep tests
report tests
redaction tests
CLI tests
fail-safe tests
regression tests
```

---

## 53. Sweep Tests

Sweep tests should use fixtures and monkeypatching rather than actual host state.

Project sweep fixtures:

```text
package with postinstall script
package with child_process usage
workflow with suspicious curl
script referencing .env
obfuscated JS sample
new executable file
fake credential-looking value
```

Quick sweep fixtures:

```text
ss output for localhost bind
ss output for 0.0.0.0 bind
ss output with process info
ss output without process info
netstat output
malformed port rows
ps output with suspicious process
ps unavailable
unsupported platform
shell profile decode failure
package manager config token indicator
temp executable file
sensitive env var name
```

Verify:

* finding category
* severity
* confidence
* evidence location
* redaction
* recommended action
* report inclusion
* `could_not_verify`
* no dependency on actual open ports or real processes

---

## 54. Audit Tests

Verify:

* event written
* event has ID
* event references request ID
* event references decision ID where relevant
* event references sweep/report IDs where relevant
* event redacts secrets
* event can be queried
* audit failure blocks risky execution

Events to test:

```text
CommandRequested
CommandClassified
DecisionIssued
ApprovalRequested
ApprovalResolved
CommandExecutionStarted
CommandExecutionCompleted
SandboxStarted
SandboxCompleted
SweepStarted
SweepCompleted
SweepFindingCreated
ScoutReportGenerated
```

---

## 55. Report Tests

Verify:

* Markdown report generated
* JSON report generated
* report type is correct
* report title is correct
* report references audit event IDs
* report includes decision where relevant
* report includes risk components where relevant
* report includes findings
* report includes uncertainty
* report includes `could_not_verify`
* report includes credential exposure assessment
* report redacts secrets

Specific regression targets:

* quick system sweep reports must not be labeled as project sweep reports
* reports must not always claim `none_detected` for credential exposure
* report JSON must not contain raw secret values

---

## 56. Redaction Tests

Test secret-like values:

```text
OPENAI_API_KEY=sk-test
ANTHROPIC_API_KEY=...
NPM_TOKEN=...
GITHUB_TOKEN=...
AWS_SECRET_ACCESS_KEY=...
-----BEGIN OPENSSH PRIVATE KEY-----
--token abc123
--api-key abc123
TOKEN=abc123
Bearer abc123
?access_token=abc123
```

Verify raw values do not appear in:

* terminal output
* audit logs
* JSON reports
* Markdown reports
* error messages
* quick sweep JSON
* process command evidence

---

## 57. Fail-Safe Tests

Simulate failures:

* parser failure
* registry validation failure
* policy engine error
* audit store unavailable
* sandbox failure
* sweep partial failure
* report generation failure
* subprocess tool unavailable
* unsupported platform
* file decode failure

Verify:

* risky commands do not run when safety-critical components fail
* failures are reported clearly
* partial verification is documented
* safe commands may still be handled where appropriate
* sweeps include `could_not_verify` rather than pretending success

---

## 58. Regression Tests

Every fixed bug should get a regression test.

Security-relevant bugs should always get tests.

Examples:

* command variant bypass
* quoted curl-pipe bypass
* package manager variant bypass
* secret leaked to report
* secret leaked to audit event
* denied command executed
* sandbox mutates host project
* approval reused incorrectly
* quick sweep parser field regression
* quick sweep report type regression
* audit finding count regression

---

## 59. CI Expectations

CI should run:

```bash
python -m pytest
python -m pytest tests/test_cli_smoke.py
python -m pytest tests/test_sweep_quick.py
python -m pytest tests/test_sweep_reports.py
python -m pytest tests/test_cli_audit_sqlite.py
```

If tooling exists later, add:

```bash
python -m ruff check .
python -m pyright
```

Do not claim ruff or pyright are project-enforced unless configuration or CI requires them.

---

## 60. Non-Goals

Sweep/audit/report/privacy v0.1 does not need:

* full antivirus detection
* full static analysis
* memory forensics
* packet inspection
* real-time monitoring
* automatic quarantine
* automatic deletion
* automatic credential rotation
* cloud reporting
* remote telemetry
* enterprise retention controls
* sanitized public report sharing
* perfect secret detection
* ML-based secret detection

Do not add these before the CLI/report/audit spine is stable.

---

## 61. Doctrine Recap

Sweeps show evidence.

Audit records events.

Reports explain decisions and findings.

Privacy rules prevent safety tooling from becoming a leak.

Tests prove the system still behaves safely.

If Policy Scout cannot verify something, it should say so.

If Policy Scout sees sensitive data, it should redact it.

If Policy Scout generates a report, it should inform rather than scare.
