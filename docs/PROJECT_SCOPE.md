# Policy Scout — Project Scope

**One-liner:**  
Policy Scout is a local-first safety harness for agent commands, package installs, and suspicious project activity.

**Short tagline:**  
Policy Scout: light armor for fast agents.

---

## 0. Scope

Policy Scout v0.1 is a local-first Python CLI safety harness that:

1. checks commands without executing them
2. classifies command category/capabilities
3. evaluates deterministic registry-backed policy
4. returns ALLOW / ALLOW_LOGGED / REQUIRE_APPROVAL / SANDBOX_FIRST / DENY / DENY_AND_ALERT
5. logs important events locally
6. runs allowed commands through `policy-scout run`
7. stores pending approvals
8. sandboxes JS package installs in a temporary review workspace
9. inspects lifecycle scripts and package metadata
10. captures manifest/lockfile diffs
11. sweeps project files for suspicious traces
12. generates Markdown/JSON Scout Reports
13. preserves severity and confidence separately
14. redacts secrets
15. includes granular tests and eval cases

---

## 1. Purpose

Policy Scout protects developers from unsafe agent commands, risky dependency installs, suspicious project mutations, and supply-chain attack traces by placing a policy-centered decision boundary between actors and execution.

Policy Scout is designed for AI-assisted development workflows where commands may be suggested or requested by:

- AI coding agents
- IDE assistants
- local automation tools
- CLI wrappers
- future MCP-style tool callers
- human developers copy/pasting commands

The goal is not to slow agents down with heavy armor. The goal is to give them lightweight, durable protection: fast enough to preserve useful automation, strict enough to stop dangerous actions, and transparent enough that users understand what happened.

---

## 2. Core Doctrine

Policy Scout is policy-centered, not agent-centered.

An actor may request an action.  
The classifier interprets the action.  
The policy engine decides what is allowed.  
The executor obeys the decision.  
The audit layer records the event.  
The report layer explains what happened.

Agents may request, but agents do not govern.

---

## 3. Primary Boundary

Policy Scout sits between risky developer actions and the user's machine.

Examples of actions Policy Scout should evaluate:

```bash
npm install some-package
pnpm add unknown-lib
npx random-cli
curl https://example.com/install.sh | bash
python script_from_agent.py
rm -rf node_modules
npm test
git clean -fd
```

Policy Scout does not replace the agent, editor, package manager, antivirus, endpoint security tool, or dependency scanner.

Policy Scout is a local-first governance layer for command execution and project safety.

---

## 4. Product Pillars

### 4.1 Permission Firewall

Policy Scout evaluates commands before they execute.

Possible decisions:

- `ALLOW`
- `ALLOW_LOGGED`
- `REQUIRE_APPROVAL`
- `SANDBOX_FIRST`
- `DENY`
- `DENY_AND_ALERT`

The firewall should be explainable. Every decision must include reasons.

---

### 4.2 Registry-First Command Knowledge

Command behavior should be defined through registries, not hardcoded scattered conditionals.

Registries may include:

- command families
- package-manager behaviors
- risk categories
- known dangerous shell patterns
- suspicious indicators
- policy defaults
- recommended controls

Registries are data, not hidden logic.

---

### 4.3 Package Install Sandbox

Risky dependency installs should be tested away from the real project first.

Initial sandbox flow:

1. Create temporary workspace.
2. Copy manifest and lockfiles.
3. Run package install in the sandbox.
4. Inspect lifecycle scripts.
5. Capture manifest and lockfile diffs.
6. Scan sandbox artifacts.
7. Produce a Scout Report.
8. Ask before migrating approved changes back.

---

### 4.4 Sweep Engine

Policy Scout should inspect projects and local development environments for suspicious traces.

Initial project checks:

- package lifecycle scripts
- lockfile changes
- `node_modules` package manifests
- GitHub Actions workflows
- new executable files
- suspicious JavaScript patterns
- shell script payloads
- credential-adjacent file references
- unexpected project mutations

Initial system checks:

- unexpected open ports
- suspicious local development processes
- unexpected Node/Bun/Python processes
- recent shell profile changes
- npm/pnpm/yarn/bun config changes

Findings must be phrased carefully. Policy Scout should say "suspicious finding" or "possible exposure" unless there is a confirmed indicator.

---

### 4.5 Scout Reports

When Policy Scout blocks, sandboxes, or detects suspicious activity, it should produce a human-readable Scout Report.

Reports should include:

- summary
- risk level
- triggering command
- timeline
- findings
- evidence locations
- files changed
- possible credential exposure
- recommended response
- what Policy Scout could not verify
- audit event IDs

Scout Reports should be clear enough for beginners and precise enough for advanced developers.

---

## 5. Local-First Posture

Policy Scout should be local-first.

Durable state should remain on the user's machine by default:

- policies
- registries
- audit logs
- findings
- sandbox reports
- Scout Reports
- approval history

Cloud services, remote registries, and hosted lookups may exist later as optional adapters, but Policy Scout should not require them for core operation.

---

## 6. Non-Goals for v0.1

Policy Scout v0.1 should not attempt to be:

- a full antivirus engine
- a complete endpoint detection platform
- a replacement for `npm audit`, Snyk, Socket, OSV, or similar tools
- a cloud dashboard
- an enterprise policy server
- an automatic credential rotation tool
- a fully autonomous remediation system
- a kernel/system-call monitor
- a VS Code/Cursor extension
- a default Docker sandbox system
- a full MCP server

Policy Scout v0.1 should not automatically delete, quarantine, or modify suspicious files without explicit user approval.

---

## 7. Safety Principles

1. Governance before execution.
2. Every command is a request.
3. Every decision must be explainable.
4. Every risky action must be auditable.
5. No silent privilege escalation.
6. No automatic deletion in v0.1.
7. No secret values printed in logs.
8. Package installs are treated as untrusted code.
9. Agents do not get direct shell access by default.
10. Humans can override, but overrides are logged.
11. Registries are testable artifacts.
12. Findings require severity, confidence, evidence, and guidance.
13. LLMs may explain, but they do not decide whether commands run.

---

## 8. MVP Definition

Policy Scout v0.1 is done when:

1. A user can run `policy-scout check -- npm install lodash`.
2. Policy Scout classifies the command as a package install.
3. The policy engine returns `SANDBOX_FIRST`.
4. The user can run `policy-scout sandbox -- npm install lodash`.
5. The sandbox install runs in a temporary workspace.
6. Policy Scout inspects package lifecycle scripts.
7. Policy Scout produces a Scout Report.
8. The user can approve or deny migration of manifest/lockfile changes.
9. The user can run `policy-scout sweep project`.
10. Policy Scout logs every decision.
11. Tests cover classifier, policy engine, registry loading, sandbox flow, and sweep findings.

---

## 9. Project Split

Policy Scout is a clean-room security tool.

Bons.ai remains a reference lab for useful control patterns.

Cerebra remains the memory and cognition runtime.

LumaWeave remains the graph visualization and exploration layer.

Policy Scout may eventually emit data that Cerebra can remember and LumaWeave can visualize, but Policy Scout's first responsibility is safe local command governance.
