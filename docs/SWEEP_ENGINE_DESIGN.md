# Policy Scout — Sweep Engine Design

## 1. Purpose

The sweep engine checks projects and local development environments for suspicious traces.

Sweeps help answer:

```text
Did something suspicious get introduced?
Did a package install leave risky artifacts?
Did a workflow change?
Are there suspicious scripts?
Are there unexpected processes or ports?
Could credentials have been exposed?
```

Policy Scout should treat sweeps as evidence-gathering, not perfect malware detection.

---

## 2. Sweep Doctrine

The sweep engine should be:

- local-first
- evidence-based
- granular
- cautious in wording
- severity/confidence aware
- redaction-safe
- useful without overclaiming

Policy Scout should say:

```text
suspicious finding
possible exposure
review recommended
could not verify
```

unless there is confirmed evidence.

---

## 3. Sweep Types

Initial sweep types:

```text
project
quick
sandbox
deep
```

### 3.1 Project Sweep

Scans the current project.

Command:

```bash
policy-scout sweep project
```

### 3.2 Quick System Sweep

Checks local system development signals.

Command:

```bash
policy-scout sweep quick
```

### 3.3 Sandbox Sweep

Runs after sandbox package install.

Internal command or automatic phase.

### 3.4 Deep Sweep

Future mode for more expensive checks.

Not required for v0.1.

---

## 4. Project Sweep Scope

Initial project sweep checks:

- package lifecycle scripts
- suspicious package manifests
- lockfile changes
- GitHub Actions workflows
- new executable files
- suspicious JavaScript patterns
- shell scripts
- credential-adjacent references
- package manager config
- unexpected project mutations

---

## 5. Quick System Sweep Scope

Initial quick system checks:

- open ports
- listening processes
- suspicious Node/Bun/Python processes
- recent shell profile changes
- package manager config changes
- suspicious temp files

Platform support can start Linux-first.

Unsupported checks should be reported clearly.

---

## 6. Sandbox Sweep Scope

Sandbox sweeps should inspect:

- installed package manifests
- lifecycle scripts
- generated files
- package scripts
- obfuscated JavaScript
- network-fetch patterns
- child process usage
- credential-adjacent references
- unexpected executables

Sandbox findings should feed into sandbox Scout Reports.

---

## 7. Finding Model

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

- finding ID
- sweep ID
- severity
- confidence
- category
- title
- location or evidence reference
- why it matters
- recommended action

---

## 8. Severity Levels

```text
info
low
medium
high
critical
```

Severity describes potential impact.

---

## 9. Confidence Levels

```text
low
moderate
high
confirmed
```

Confidence describes certainty.

Severity and confidence must remain separate.

Example:

```text
Severity: high
Confidence: moderate
```

This means the behavior could matter a lot, but evidence is not definitive.

---

## 10. Finding Categories

Initial categories:

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

---

## 11. Package Script Checks

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

- `child_process`
- `curl`
- `wget`
- `bash`
- `sh`
- environment variable enumeration
- credential file paths
- obfuscated payloads
- binary downloads
- chmod/chown
- shell profile modification

---

## 12. Workflow Checks

Inspect CI workflow files.

Initial paths:

```text
.github/workflows/*.yml
.github/workflows/*.yaml
.gitlab-ci.yml
```

Suspicious indicators:

- secret printing
- unexpected curl/wget execution
- package publishing changes
- credential exfiltration patterns
- unexpected new workflow files
- dangerous shell commands

---

## 13. Executable File Checks

Detect new or suspicious executable files.

Signals:

- executable bit set
- binary in unexpected path
- script with dangerous shebang
- recently created executable
- executable inside package scripts path
- executable referenced by lifecycle script

---

## 14. Obfuscation Checks

Initial suspicious JavaScript patterns:

- large base64 blobs
- `eval`
- `Function(...)`
- heavily encoded strings
- char-code reconstruction
- suspicious minified lifecycle scripts
- hidden network URLs

Obfuscation alone is not proof of compromise.

It should usually be medium/high severity with moderate confidence depending on context.

---

## 15. Credential-Adjacent Checks

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

Report references to locations, not raw secrets.

---

## 16. Open Port Checks

Quick system sweep may inspect listening ports.

Findings should include:

- port
- process name
- PID where available
- command line summary where safe
- local/remote bind
- confidence

Be careful: open ports are not necessarily suspicious.

Developer tools often open ports.

---

## 17. Process Checks

Quick system sweep may inspect processes.

Initial suspicious process signals:

- unexpected `node`
- unexpected `bun`
- unexpected `python`
- process running from temp directory
- process command references suspicious script
- process spawned near suspicious install time

Findings should avoid panic.

---

## 18. Repository Mutation Checks

Project sweep may inspect Git status.

Useful signals:

- new files
- modified package manifests
- modified lockfiles
- modified workflows
- new executable files
- deleted files
- unexpected binary files

Policy Scout should not assume all mutations are bad.

It should report context.

---

## 19. Evidence Redaction

Sweep evidence must avoid secret leakage.

Good:

```text
Credential-adjacent file referenced: .env
```

Bad:

```text
OPENAI_API_KEY=sk-actual-value
```

Use evidence references and redacted excerpts.

---

## 20. Sweep Result Object

Example:

```json
{
  "sweep_id": "sweep_123",
  "sweep_type": "project",
  "started_at": 1710000000,
  "completed_at": 1710000042,
  "project_root": "/home/user/project",
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
  ]
}
```

---

## 21. Report Integration

Every sweep should be able to produce:

```text
Markdown Scout Report
JSON Scout Report
```

Reports should include:

- summary
- sweep scope
- findings
- evidence
- credential exposure assessment
- recommended actions
- what could not be verified
- audit event IDs

---

## 22. False Positive Handling

False positives are expected.

Policy Scout should reduce harm by:

- separating severity from confidence
- explaining why a finding matters
- showing evidence location
- avoiding absolute claims
- allowing user review
- allowing future suppression rules with audit trail

Suppression rules should not be part of v0.1 unless simple and explicit.

---

## 23. Audit Events

Sweep events:

```text
SweepStarted
SweepCompleted
SweepFindingCreated
SweepError
ScoutReportGenerated
```

Each finding should be auditable.

---

## 24. Non-Goals for v0.1

The sweep engine does not need to:

- detect all malware
- perform full static analysis
- perform memory forensics
- inspect all network traffic
- monitor processes in real time
- automatically quarantine files
- automatically delete files
- rotate credentials
- support every OS equally

---

## 25. Testing Requirements

Sweep tests should verify:

- lifecycle script detection
- workflow detection
- executable file detection
- suspicious JS pattern detection
- credential reference detection
- secret redaction
- severity/confidence handling
- report generation
- unsupported platform warnings
- audit event generation

---

## 26. Sweep Doctrine

The sweep engine is not a crystal ball.

It is a local evidence collector that helps the user see suspicious traces, understand risk, and decide what to do next.
