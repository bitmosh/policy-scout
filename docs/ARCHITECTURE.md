# Policy Scout — Architecture

## 1. Architectural Purpose

Policy Scout is a local-first safety harness for agent commands, package installs, and suspicious project activity.

The architecture must keep one boundary clear:

```text
Actors request actions.
Policy Scout classifies and decides.
Executors obey.
Everything important is logged.
```

Policy Scout is not agent-centered. It is policy-centered.

The agent, human, IDE, CLI wrapper, CI job, or future MCP caller is an actor. The actor may request an action, but the actor does not own the final decision about whether that action is allowed.

---

## 2. Core Flow

The primary runtime flow is:

```text
Command / Tool Request
        ↓
Request Normalizer
        ↓
Command Parser
        ↓
Command Classifier
        ↓
Capability Detector
        ↓
Context Inspector
        ↓
Registry Matcher
        ↓
Risk Scorer
        ↓
Policy Engine
        ↓
Decision
        ↓
Approval / Sandbox / Direct Executor / Denial
        ↓
Audit Event
        ↓
Scout Report when needed
```

The short version:

```text
request -> classify -> policy -> decision -> approval/sandbox/deny -> audit
```

---

## 3. Primary Runtime Components

### 3.1 Actor

An actor is anything requesting an action.

Initial actor types:

- `human`
- `agent`
- `ide`
- `cli`
- `ci`
- `unknown`

Actors do not execute directly through Policy Scout. Actors submit requests.

---

### 3.2 Command Request

A command request is the normalized object representing the action being requested.

Example:

```json
{
  "request_id": "req_123",
  "timestamp": 1710000000,
  "actor": {
    "type": "agent",
    "name": "local_agent",
    "trust_level": "untrusted_agent"
  },
  "source": "cli",
  "command": "npm install unknown-package",
  "cwd": "/home/user/project",
  "declared_intent": "Install dependency"
}
```

The command request is the first durable unit of governance.

---

### 3.3 Request Normalizer

The request normalizer converts incoming input into a standard `CommandRequest`.

Inputs may come from:

- CLI
- shell shim
- local HTTP API
- future MCP-style server
- IDE integration
- CI integration

The normalizer should not make policy decisions. It prepares data for downstream evaluation.

---

### 3.4 Command Parser

The command parser attempts to tokenize and understand shell structure.

It should detect:

- command name
- arguments
- pipes
- redirects
- chained commands
- subshells
- command substitution
- environment variable usage
- obvious destructive patterns
- network-piped execution

The parser should fail safely.

If parsing confidence is low, the command should be treated as higher risk.

---

### 3.5 Command Classifier

The classifier maps the parsed command into one or more command categories.

Examples:

```text
npm install react      -> package_install
npx random-cli         -> package_execute
curl url | bash        -> network_execute
cat README.md          -> safe_read
rm -rf /               -> destructive
```

The classifier should preserve its method and confidence:

```json
{
  "classification_method": "registry_regex",
  "classification_confidence": 0.96
}
```

---

### 3.6 Capability Detector

The capability detector identifies what the command could do.

Capabilities may include:

- `filesystem.read`
- `filesystem.project_write`
- `filesystem.system_write`
- `network.fetch`
- `network.execute`
- `package.install`
- `package.execute`
- `lifecycle.execute_possible`
- `credential.access_possible`
- `process.spawn`
- `process.inspect`
- `system.mutation`
- `destructive.mutation`

Capabilities are more important than command names.

For example, `npm install`, `pnpm add`, `yarn add`, and `bun add` are different command forms but imply similar risk capabilities.

---

### 3.7 Context Inspector

The context inspector reads environmental details relevant to safety.

It may inspect:

- current working directory
- project type
- package manager files
- Git status
- lockfiles
- `.env` / `.npmrc` / config files nearby
- whether path is inside project, home, temp, or system scope
- operating system
- shell
- known workspace boundaries

The context inspector should not read sensitive file contents unless explicitly required and policy-allowed.

---

### 3.8 Registry Matcher

The registry matcher compares parsed/classified requests against known registry entries.

Registry sources:

- command registry
- policy registry
- indicator registry
- suspicious pattern registry

Registries should be data-driven and testable.

Registry matching should produce explainable hits:

```json
{
  "registry_hits": [
    "npm.install",
    "package_install.lifecycle_possible",
    "agent_package_installs_sandbox_first"
  ]
}
```

---

### 3.9 Risk Scorer

The risk scorer computes granular risk components and a summary risk score.

The final risk score is only a summary. It must not replace granular evidence.

Example:

```json
{
  "risk_score": 7,
  "risk_components": {
    "network_execution": 2,
    "package_install": 2,
    "lifecycle_script_possible": 2,
    "actor_trust_penalty": 1,
    "credential_adjacency": 0,
    "destructive_potential": 0
  },
  "confidence": 0.91,
  "evidence_strength": 0.86
}
```

The scorer should support tuning, but safety-critical defaults must remain conservative.

---

### 3.10 Policy Engine

The policy engine is the authority.

It consumes:

- command request
- parsed command
- classification
- capabilities
- actor information
- context
- registry hits
- risk scores
- current enforcement mode

It emits a decision:

- `ALLOW`
- `ALLOW_LOGGED`
- `REQUIRE_APPROVAL`
- `SANDBOX_FIRST`
- `DENY`
- `DENY_AND_ALERT`

Every decision must include reasons.

The policy engine must not delegate final authority to an LLM.

---

### 3.11 Approval Queue

The approval queue holds pending requests that require human decision.

Approvals should support:

- approve once
- deny once
- explain
- show evidence
- show policy hits
- show recommended action

Approvals must be logged.

Approving once should not silently create a permanent allow rule.

---

### 3.12 Sandbox Executor

The sandbox executor runs risky package installs or other supported actions away from the real project.

Initial sandbox responsibilities:

1. Create temporary workspace.
2. Copy package manifest and lockfiles.
3. Run install command in sandbox.
4. Capture output and exit code.
5. Inspect lifecycle scripts.
6. Capture manifest/lockfile diffs.
7. Run sandbox sweep.
8. Produce result object.
9. Ask before migrating changes.

Sandbox execution should be considered untrusted.

---

### 3.13 Direct Executor

The direct executor runs commands that are allowed by policy.

The direct executor should only run commands after a final decision has authorized execution.

It should record:

- command
- cwd
- actor
- decision id
- start time
- exit code
- duration
- execution route

---

### 3.14 Sweep Engine

The sweep engine checks for suspicious project or local environment traces.

Initial project sweep checks:

- package lifecycle scripts
- suspicious package manifests
- lockfile changes
- GitHub Actions workflow changes
- new executable files
- suspicious JavaScript patterns
- shell profile modifications inside project
- credential-adjacent references

Initial system quick sweep checks:

- open ports
- listening processes
- suspicious Node/Bun/Python processes
- recent temp files
- npm/pnpm/yarn/bun config changes
- recent shell profile changes

Findings should have severity and confidence.

---

### 3.15 Audit Store

The audit store records durable events.

Initial storage may be SQLite, JSONL, or both. SQLite is preferred for querying; JSONL is useful for simple inspection and export.

Audit events should be append-first. Updates should be explicit events rather than silent mutation.

Example events:

- `CommandRequested`
- `CommandParsed`
- `CommandClassified`
- `PolicyMatched`
- `DecisionIssued`
- `ApprovalRequested`
- `ApprovalResolved`
- `CommandExecuted`
- `SandboxStarted`
- `SandboxCompleted`
- `SweepStarted`
- `SweepFindingCreated`
- `ScoutReportGenerated`

---

### 3.16 Scout Report Builder

The report builder creates human-readable and machine-readable reports.

Formats:

- Markdown
- JSON

Report types:

- package install review
- blocked command
- suspicious project finding
- possible credential exposure
- system quick sweep
- incident summary

Reports should preserve granular evidence and avoid printing secret values.

---

## 4. Enforcement Modes

Policy Scout should support enforcement modes.

Initial modes:

- `beginner`
- `balanced`
- `paranoid`
- `ci`
- `incident`

Mode affects defaults, not the basic doctrine.

Example:

```text
beginner  -> more explanation, safe defaults
balanced  -> default local developer mode
paranoid  -> stricter approvals and sandboxing
ci        -> non-interactive, fail closed
incident  -> deny-heavy, report-focused
```

Mode switching should use hysteresis/persistence to avoid flapping.

---

## 5. Local-First Architecture

Policy Scout should run locally by default.

Local durable state:

- registry files
- policy files
- audit database
- JSONL audit export
- sandbox reports
- Scout Reports
- approval history

Network features should be optional and explicit.

Policy Scout must not require a cloud account, remote policy server, or hosted dashboard for v0.1.

---

## 6. LLM Boundary

LLMs may help with:

- explaining decisions
- summarizing reports
- generating safer alternative suggestions
- converting technical findings into beginner-friendly language

LLMs must not:

- decide whether a command runs
- override policy
- directly execute shell commands
- directly read secrets
- silently modify registries
- silently approve actions

The LLM is an assistant. The policy engine is the authority.

---

## 7. Agent Integration Boundary

Future agent integrations should call Policy Scout through structured APIs.

Potential future tool calls:

```text
policy_scout.check_command
policy_scout.run_command
policy_scout.sandbox_install
policy_scout.sweep_project
policy_scout.get_report
policy_scout.list_approvals
policy_scout.resolve_approval
```

Agents should receive structured decisions and allowed next actions.

Agents should not receive raw unconstrained shell access through Policy Scout.

---

## 8. Failure Behavior

Policy Scout should fail safely.

Examples:

- parser uncertainty -> require approval or deny based on risk
- registry load failure -> deny risky commands
- policy engine failure -> deny execution
- audit store failure -> do not run risky commands
- sandbox failure -> do not migrate changes
- sweep error -> report incomplete verification

Policy Scout should tell the user what failed and what was not verified.

---

## 9. Architecture Doctrine

Policy Scout should remain modular, inspectable, and conservative.

Core principles:

1. Policy-centered, not agent-centered.
2. Registries before cleverness.
3. Granular evaluation before final scoring.
4. Human-readable decisions.
5. Durable audit events.
6. No silent safety regression.
7. Local-first by default.
8. LLMs explain; policy decides.
9. Sandbox before trust when risk is high.
10. Scout Reports preserve evidence and uncertainty.
