# Policy Scout — Integration Boundaries

## 1. Purpose

This document defines how Policy Scout should integrate with other tools without losing its safety boundary.

Policy Scout should be modular and recomposable, but integrations must not let agents or external tools bypass policy.

The core rule:

```text
Integrations may submit requests.
Policy Scout still decides.
```

---

## 2. Integration Doctrine

Policy Scout should expose structured boundaries.

It should not expose raw unrestricted shell access.

Every integration should preserve:

- actor identity
- request context
- policy evaluation
- decision reasons
- audit logging
- approval requirements
- sandbox routing
- report generation

---

## 3. Integration Tiers

Suggested integration tiers:

```text
Tier 1: CLI wrapper
Tier 2: shell shims
Tier 3: local HTTP API
Tier 4: MCP-style tool server
Tier 5: editor extensions
Tier 6: CI integration
```

Build in order.

Do not start with MCP or editor extensions.

---

## 4. Tier 1 — CLI Wrapper

The CLI is the first and most important integration.

Commands:

```bash
policy-scout check -- <command>
policy-scout run -- <command>
policy-scout sandbox -- <command>
policy-scout sweep project
```

Benefits:

- simple
- local
- testable
- useful immediately
- scriptable
- no agent dependency

The CLI proves the core boundary.

---

## 5. Tier 2 — Shell Shims

Shell shims can route common commands through Policy Scout.

Examples:

```text
npm -> policy-scout run -- npm
pnpm -> policy-scout run -- pnpm
npx -> policy-scout run -- npx
```

Shell shims should be opt-in.

Risks:

- user confusion
- path ordering issues
- bypass by absolute path
- shell differences
- unexpected tooling behavior

Do not make shell shims part of v0.1 default behavior.

---

## 6. Tier 3 — Local HTTP API

A local API can allow tools to call Policy Scout.

Possible endpoints:

```text
POST /check-command
POST /run-command
POST /sandbox-install
POST /sweep-project
GET /approvals
POST /approvals/{id}/approve
POST /approvals/{id}/deny
GET /reports/{id}
```

Security requirements:

- bind to localhost only by default
- disabled unless explicitly enabled
- require local token or socket auth
- log actor/source
- do not expose raw shell execution without policy
- support JSON only

---

## 7. Tier 4 — MCP-Style Tool Server

Policy Scout may eventually expose MCP-style tools.

Possible tools:

```text
policy_scout.check_command
policy_scout.run_command
policy_scout.sandbox_install
policy_scout.sweep_project
policy_scout.get_report
policy_scout.list_approvals
policy_scout.resolve_approval
```

Rules:

1. Agents cannot approve their own requests.
2. Tool calls must include actor identity.
3. Tool calls must produce audit events.
4. `run_command` must obey policy decisions.
5. Denied commands must not execute.
6. Risky commands must pause or sandbox.
7. Tool metadata must be clear and non-deceptive.
8. MCP server should be disabled by default.

MCP should come after the CLI and local API are stable.

---

## 8. Tier 5 — Editor Extensions

Possible editors:

- VS Code
- Cursor
- Windsurf
- JetBrains
- Zed

Editor extension features:

- show command decisions
- show approval prompts
- view Scout Reports
- run project sweeps
- configure mode
- show sandbox results

Risks:

- editor API churn
- UI complexity
- hidden execution pathways
- user confusion

Editor extensions are not v0.1.

---

## 9. Tier 6 — CI Integration

CI integration should be non-interactive.

Behavior:

```text
risky command -> fail closed
denied command -> fail
findings above threshold -> fail or warn based on config
report generated -> artifact output
```

CI mode should support JSON output.

Potential commands:

```bash
policy-scout check --json -- npm install
policy-scout sweep project --json
```

---

## 10. Cerebra Boundary

Cerebra is the memory/cognition runtime.

Policy Scout may eventually send Cerebra:

- Scout Reports
- audit summaries
- decision events
- incident summaries
- project risk history

Cerebra should not override Policy Scout policy decisions.

Cerebra may help remember and contextualize.

Policy Scout remains the enforcement boundary.

---

## 11. LumaWeave Boundary

LumaWeave is the graph visualization and exploration system.

Policy Scout may eventually emit graph-ready data:

- command request nodes
- decision nodes
- policy hit nodes
- finding nodes
- report nodes
- sandbox result nodes
- timeline edges

LumaWeave visualizes.

Policy Scout decides.

---

## 12. Bons.ai Boundary

Bons.ai is a reference lab for control patterns.

Useful patterns:

- pure decision controllers
- granular scoring
- mode persistence
- event logging
- adaptive non-critical strategy selection

Do not port Bons.ai's agent-centered loop into Policy Scout.

Policy Scout is not an idea-generation agent.

---

## 13. LLM Boundary

LLMs may assist with:

- explanation
- summarization
- report drafting
- safer alternative wording
- beginner guidance

LLMs may not:

- approve actions
- override policy
- execute commands directly
- hide findings
- rewrite policy silently
- receive raw secrets

LLM use should be optional.

---

## 14. Package Manager Boundary

Policy Scout wraps package manager actions but does not replace package managers.

Supported initially:

```text
npm
pnpm
yarn
bun
```

Policy Scout should not become a package manager.

It should classify, sandbox, inspect, and report.

---

## 15. Security Tool Boundary

Policy Scout does not replace:

- antivirus
- EDR
- OS package manager security
- npm audit
- Snyk
- Socket
- OSV
- cloud security tools
- secret scanners

Policy Scout may call or integrate with some tools later, but it should not claim their responsibilities.

---

## 16. Integration Data Contract

Integrations should send structured requests.

Example:

```json
{
  "actor": {
    "type": "agent",
    "name": "local_agent",
    "trust_level": "untrusted_agent"
  },
  "source": "mcp",
  "command": "npm install lodash",
  "cwd": "/home/user/project",
  "declared_intent": "Install lodash for utility helpers"
}
```

Policy Scout returns structured decisions.

Example:

```json
{
  "decision": "SANDBOX_FIRST",
  "risk_score": 7,
  "reasons": [
    "Package installs may execute lifecycle scripts."
  ],
  "allowed_next_actions": [
    "sandbox_install",
    "deny",
    "ask_human_approval"
  ]
}
```

---

## 17. Integration Safety Requirements

All integrations must:

1. Preserve actor identity.
2. Preserve working directory.
3. Preserve command text.
4. Receive structured decisions.
5. Obey denials.
6. Obey sandbox requirements.
7. Create audit events.
8. Avoid raw secret exposure.
9. Avoid unrestricted command execution.
10. Be disabled by default if network/API-based.

---

## 18. Integration Doctrine

Policy Scout should be easy to plug into other systems, but hard to bypass.

The harness is the product.

Integrations are adapters.

Adapters may change, but the policy boundary should not.
