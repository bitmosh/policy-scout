# Architecture

Policy Scout is a Python CLI-first policy engine with local persistence and
optional adapters. The core boundary is deliberately one-way:

```text
actors request -> Policy Scout decides -> executors obey
```

## Decision path

```text
raw command
   |
   v
CommandRequest + Actor
   |
   v
ShellParser --------> structural flags: pipe, redirect, chain, substitution
   |
   v
CommandClassifier --> categories, capabilities, confidence, registry hits
   |
   v
RiskScorer ---------> component scores + summary risk band
   |
   v
PolicyEngine -------> matching rules, decisive rule, reasons, decision
   |
   +--> ALLOW / ALLOW_LOGGED --> DirectExecutor
   +--> REQUIRE_APPROVAL -----> ApprovalStore -> verified one-time execution
   +--> SANDBOX_FIRST --------> package review workspace
   `--> DENY / DENY_AND_ALERT -> no execution
                                |
                                v
                         AuditStore / reports
```

`policy_scout/cli/main.py` currently performs argument parsing and much of the
application orchestration. Subsystems remain separate modules, but the CLI layer
is larger than the desired long-term boundary.

## Core models

- `CommandRequest` records command text, working directory, actor, source, and ID.
- `ClassificationResult` records categories, capabilities, confidence, command
  family, structure, and registry evidence.
- `RiskScore` contains granular components and a derived summary.
- `PolicyDecision` contains the final decision, reasons, policy hits, and next
  action.
- `AuditEvent`, `ApprovalRequest`, `SandboxResult`, `SweepResult`, and report
  models carry durable subsystem outcomes.

These shapes are JSON-serializable because the CLI, tests, Tauri adapter, MCP
server, and local event integrations consume them.

## Registry and policy data

The normal policy path loads:

- `data/command_registry.yaml` — known command patterns and capabilities;
- `data/default_policy.yaml` — priority-ordered decisions;
- `data/eval_cases.yaml` — executable behavior oracle.

Other YAML files provide secret, prompt-injection, known-bad package, watch, and
incident-playbook data. Registry validators reject malformed required fields and
unknown taxonomy values before runtime use.

The engine retains a small set of hard-coded conservative fallbacks. They are
fail-safe behavior, not the preferred authoring surface.

## Execution and approval

`DirectExecutor` is downstream from policy and has no authority to reinterpret a
decision. Ordinary `run` executes only `ALLOW` and `ALLOW_LOGGED`.

Approval requests live in local JSONL state. Approved execution is a new policy
evaluation plus an exact approval match, not a continuation that trusts stale
state. This prevents one approval from authorizing a changed command, directory,
or policy outcome.

## Sandbox subsystem

Package review creates a separate workspace, copies a bounded package-file set,
runs the requested package manager, inspects lifecycle scripts, captures diffs,
and persists results and reports. Migration is a separate, explicit operation.

The general sandbox is another path: a Linux namespace runner with resource
limits and optional filesystem/syscall evidence. The two paths share a safety
goal but do not claim identical containment.

## Evidence subsystem

The audit layer writes redacted events to SQLite and JSONL. SQLite supports CLI
queries and correlation by request, decision, approval, sandbox, sweep, report,
and execution IDs. JSONL supports inspection and HMAC-chain verification.

Reports render command decisions, sandbox reviews, and sweep results as local
Markdown and JSON. Findings preserve severity, confidence, evidence location,
recommended action, and incomplete checks.

The optional Fossic adapter receives the already-redacted event dictionary and
emits request events and posture changes to a second local store. It is an
integration output, not the enforcement database.

## Analysis subsystems

- project sweep: scripts, workflows, executables, JavaScript/shell patterns,
  credential references, and repository changes;
- quick sweep: Linux ports, processes, profiles, package-manager config, temp
  files, and sensitive environment names;
- secret scan: file, directory, staged, and history scanning;
- supply-chain analysis: JavaScript/Python lifecycle behavior, dependency
  confusion, transitive npm data, and optional publish metadata;
- threat intelligence: local known-bad/typosquatting/integrity checks and opt-in
  remote advisory clients;
- prompt injection: configured patterns and canary artifacts.

## Adapter boundaries

### MCP

The stdio MCP server delegates to existing check, sandbox, sweep, report, and
scan behavior. It does not own a separate policy engine or remote trust model.

### Desktop

The Tauri backend invokes fixed CLI command shapes and validates user-selected
IDs and filters. The frontend does not read SQLite or arbitrary files directly.
The CLI remains the semantic authority.

### Lattica

Lattica is an external consumer. Its Policy Scout tile polls selected CLI state
and subscribes to Fossic streams. Generic Lattica agent-dispatch governance is a
future integration contract, not a current core guarantee.

## Dependency direction

```text
CLI / MCP / Tauri / hooks / Lattica adapters
                    |
                    v
       parser -> classifier -> policy
                    |
                    v
 approval / sandbox / executor / analysis
                    |
                    v
          audit -> reports -> adapters
```

Adapters may request or display decisions. They must not become alternative
policy authorities.
