# ADR-001: MCP Server Transport and Agent Trust Model

**Status:** Accepted  
**Date:** 2026-06-10  
**Deciders:** Developer (bitmosh)  
**Related Plans:** [06_mcp_server.md](../implementations/plans/06_mcp_server.md), [07_prompt_injection_detection.md](../implementations/plans/07_prompt_injection_detection.md)  
**Related ADRs:** [ADR-002](ADR-002-policy-config-precedence.md) (trust level feeds into effective policy chain), [ADR-003](ADR-003-graph-export-contract.md) (MCP tool calls are graph nodes)

---

## Context

Policy Scout currently sits outside the agent tool-call loop. Agents can be advised to run `policy-scout check` manually, but there is no in-loop enforcement path. The two integration needs are:

1. **MCP server** — a process that exposes Policy Scout's capabilities as MCP tools, so agents can call `policy_scout_check` before running a command. This requires deciding what transport protocol to use, how to manage sessions, and — most critically — what trust level to assign to requests arriving via MCP vs. the CLI.

2. **Claude Code hook integration** — a `--hook-mode` flag that lets Policy Scout be registered as a `PreToolUse` hook in `.claude/settings.json`. When Claude Code is about to run a Bash command, the hook fires, Policy Scout evaluates the command, and exits non-zero to block it if DENY or DENY_AND_ALERT.

The trust model question is the load-bearing architectural choice. The existing `Actor` model has a `trust_level` field with values `"developer"`, `"trusted_agent"`, `"untrusted_agent"`, `"ci"`. Every MCP request arriving at the server needs a trust level assigned to it. That assignment affects which policy rules fire, which modes apply, and what the approval threshold is. Getting this wrong in either direction is expensive: too permissive defeats the product; too restrictive makes it unusable.

There is also the **print/return separation problem**: the current CLI functions print to stdout and return exit codes. The MCP server cannot use subprocess invocation (too slow for interactive use) — it must call Python functions directly. Those functions currently mix policy logic with print side-effects. This refactor must happen before the MCP server can be built.

---

## Forces

- **Security:** An agent calling Policy Scout via MCP should not be able to self-escalate to a trust level that bypasses its own restrictions. The trust level must be set by the server configuration, not by the MCP caller.
- **Simplicity:** stdio transport is simpler, more secure (no network surface), sufficient for local use, and what other MCP servers use. HTTP/SSE would add authentication complexity without benefit at this scope.
- **Latency:** MCP tool calls happen in the agent's decision loop. A `policy_scout_check` call that takes >500ms breaks interactive flow. Subprocess invocation is ruled out; direct Python API calls are required.
- **Testability:** The print/return refactor is valuable regardless — it makes every CLI handler independently testable without capturing stdout. This is worth doing before MCP, not as an MCP side effect.
- **Auditability:** Every MCP tool call must produce an audit event. The server is a new actor in the system; its calls must be distinguishable from CLI calls in the audit log.
- **Extensibility:** [07] Prompt Injection (planned) adds a response-scanning hook in the MCP handler layer. The server architecture must leave room for `PostToolResponse` hooks without structural rework.

---

## Decision

### D1 — Transport: stdio-only for v1

The MCP server uses JSON-RPC 2.0 over stdin/stdout exclusively. HTTP/SSE transport is deferred to v2 and is not in scope for the Tier 2 implementation.

**Rationale:** stdio is the standard MCP transport, needs no authentication layer, leaves no listening socket, and is sufficient for local use. Claude Code, Cursor, and all primary MCP clients support it. Adding HTTP/SSE adds ~400 lines of auth/CORS/socket code with no v1 benefit.

**Rejected alternative:** HTTP with localhost binding and a local token. Rejected because it increases attack surface (process that listens on a port) and adds session authentication complexity that isn't needed when the caller is always a local process.

### D2 — Trust model: server-assigned, not caller-supplied

The trust level for every MCP session is set by the server's own configuration, not by any field the calling agent provides. The `actor_type` field in the `policy_scout_check` tool schema exists for logging purposes only — it does not influence the trust level used for policy evaluation.

The trust assignment hierarchy is:

```
~/.config/policy-scout/config.yaml  →  server.default_agent_trust
.policy-scout.yaml (project)         →  server.agent_trust_override (see ADR-002)
Hardcoded floor                      →  "untrusted_agent" (can never go below this)
```

| Config value | Effective trust level | Audit actor label |
|---|---|---|
| `low` | `untrusted_agent` | `mcp_agent_low` |
| `medium` (default) | `untrusted_agent` | `mcp_agent_medium` |
| `high` | `trusted_agent` | `mcp_agent_high` |

`medium` maps to `untrusted_agent` because the agent is still not human and still cannot approve its own requests. The only difference between `medium` and `low` is mode selection: `low` forces `paranoid` mode; `medium` uses the configured mode; `high` allows `trusted_agent` fast-path (fewer rules fire).

**Agents cannot self-approve regardless of trust level.** Approval resolution always requires a human `actor_type: "developer"` or CLI interaction. This is enforced in the approval store, not in the trust model — it is not configurable.

### D3 — Check-before-run enforcement (session state)

The server tracks whether an agent has called `policy_scout_check` for a given command in the current session before calling any execution-adjacent tool. If an agent attempts to call `policy_scout_sandbox` or `policy_scout_sweep` without a prior `check` for a related command, the server logs a `MCPUncheckedExecution` audit event and forces `paranoid` mode for that call.

This is a soft enforcement: it does not block the call, but it escalates the scrutiny. Blocking on missing-check would make the server too brittle — an agent might legitimately decide to sandbox without a check if the result of the check is already known from a prior session.

### D4 — Print/return separation is a prerequisite

The CLI handler refactor (separating policy logic from print side-effects) must land as a standalone commit **before** the MCP server is built. Every handler that will be exposed as an MCP tool gets an `output_format: Literal["print", "dict"]` parameter. When `"dict"`, the function returns a structured dict and does not print. When `"print"` (default), behavior is unchanged.

This is scoped to only the handlers the MCP server exposes:
- `check_command()` in `cli/main.py` (or extracted to `cli/check.py`)
- The sandbox run path
- The sweep run path

Handlers that are not MCP-exposed are not refactored in this pass.

### D5 — Hook mode flag

A `--hook-mode` flag is added to `policy-scout check`. In hook mode:
- Exit 0 for ALLOW, ALLOW_LOGGED
- Exit 0 with a JSON warning on stderr for REQUIRE_APPROVAL, SANDBOX_FIRST (hook passes but the agent sees the annotation)
- Exit 1 with a JSON error on stderr for DENY, DENY_AND_ALERT (hook blocks)

The JSON on stderr follows a stable schema (see Interface section). Claude Code surfaces stderr content to the user when a hook exits non-zero.

---

## Interface Definition

### MCP Tool Call Flow

```
MCP client (agent)
  → JSON-RPC 2.0 line on stdin
  → MCPServer._dispatch()
  → MCPSession.assign_trust(request)   # D2: trust from config, not caller
  → handler(params, trust_level)
  → policy_engine.decide(request)
  → audit_store.write(MCPToolCallCompleted)
  → return structured dict on stdout
```

### Hook Mode stderr schema (stable contract for Claude Code)

```json
{
  "policy_scout_version": "0.x.x",
  "decision": "DENY",
  "risk_score": 9,
  "risk_band": "critical",
  "command": "rm -rf /",
  "reasons": [
    "Destructive command matches deny pattern",
    "No recovery path"
  ],
  "report_id": "report_abc123",
  "recommended_action": "Do not execute. Review the Scout Report for alternatives."
}
```

### New audit event types

```python
class EventType:
    MCP_SERVER_STARTED      = "MCPServerStarted"
    MCP_TOOL_CALL_RECEIVED  = "MCPToolCallReceived"
    MCP_TOOL_CALL_COMPLETED = "MCPToolCallCompleted"
    MCP_SESSION_ENDED       = "MCPSessionEnded"
    MCP_UNCHECKED_EXECUTION = "MCPUncheckedExecution"  # D3: session enforcement
```

`MCPToolCallCompleted` data payload:
```json
{
  "tool_name": "policy_scout_check",
  "actor_trust": "untrusted_agent",
  "actor_label": "mcp_agent_medium",
  "command": "npm install lodash",
  "decision": "SANDBOX_FIRST",
  "latency_ms": 42,
  "session_id": "sess_abc123"
}
```

### `policy-scout serve` CLI commands

```bash
policy-scout serve --mcp                         # start MCP server (stdio, blocks until EOF)
policy-scout serve --mcp --agent-trust low       # override trust for this session
policy-scout serve install --scope project       # write .mcp.json to project root
policy-scout serve install --scope user          # write ~/.claude/mcp.json
policy-scout serve status                        # check registration + running status
```

### `.mcp.json` schema (project root)

```json
{
  "mcpServers": {
    "policy-scout": {
      "command": "policy-scout",
      "args": ["serve", "--mcp"],
      "description": "Policy Scout — command safety harness"
    }
  }
}
```

### `~/.config/policy-scout/config.yaml` additions

```yaml
server:
  default_agent_trust: medium    # low | medium | high  (default: medium)
  require_check_before_run: true # D3: session enforcement (default: true)
```

---

## Blast Radius

### Files changed

| File | Change type | Risk |
|---|---|---|
| `policy_scout/cli/main.py` | Add `serve` command group; add `--hook-mode` to `check` | Medium — large file |
| `policy_scout/cli/check.py` (new or extracted) | `output_format` parameter; hook mode exit logic | Medium |
| `policy_scout/server/mcp_server.py` (new) | JSON-RPC 2.0 loop | Low (new file) |
| `policy_scout/server/tool_definitions.py` (new) | MCP tool schemas | Low (new file) |
| `policy_scout/server/handlers.py` (new) | Tool call handlers | Medium (depends on print/return refactor) |
| `policy_scout/server/session.py` (new) | Per-session trust assignment | Low (new file) |
| `policy_scout/audit/events.py` | 5 new event types + factory functions | Low (additive) |
| `policy_scout/core/ids.py` | Add `"sess"` prefix to `generate_id` Literal | Minimal |
| `policy_scout/doctor.py` | Add MCP registration status check | Low (additive) |

### Tests requiring changes

- All tests that call `check_command()` directly and assert on stdout will break if print/return separation changes the function signature. **Scope:** any test that uses `capsys` or `capfd` to capture check output. These need updating to call with `output_format="dict"` and assert on the return value.
- Existing doctor tests — add new MCP status check row.

### Tests not affected

- Policy engine tests (no print dependency)
- Audit store tests
- Scan/git integration tests
- Everything that goes through the CLI via `subprocess.run(["policy-scout", ...])` style (these go through print mode unchanged)

### Dependencies

No new runtime packages. The MCP protocol is implemented from scratch (JSON-RPC 2.0 is simple enough). `threading` from stdlib is sufficient for the server loop.

---

## Implementation Phases

These phases are ordered so each one is independently mergeable and leaves the codebase in a working state.

### Phase 1 — Print/Return Separation (prerequisite, ~200 lines delta)

**Scope:** `cli/check.py` (or extract from `main.py`), the sandbox run path, the sweep run path.  
**Acceptance:** All 758 existing tests still pass. The refactored functions return dicts when called with `output_format="dict"`. CLI behavior (`print` mode) is unchanged.  
**Commit:** `refactor(cli): extract check/sandbox/sweep logic from print layer`  
**Unlocks:** Phase 2 and Phase 3.

### Phase 2 — Hook Mode (~60 lines)

**Scope:** `--hook-mode` flag in `cli/check.py`, hook mode exit logic, JSON stderr schema.  
**Acceptance:** `policy-scout check --hook-mode -- rm -rf /` exits 1 with correct JSON on stderr. `policy-scout check --hook-mode -- ls` exits 0.  
**Commit:** `feat(cli): add --hook-mode for Claude Code PreToolUse hook integration`  
**Unlocks:** Users can immediately register the hook in `.claude/settings.json` without waiting for the full MCP server. Delivers value independently.

### Phase 3 — MCP Server Core (~560 lines)

**Scope:** `server/mcp_server.py`, `server/tool_definitions.py`, `server/handlers.py` (4 tools: check, sandbox, sweep, get_report), `server/session.py`, `serve install` command.  
**Acceptance:** Server starts, responds to `initialize`, returns tool list, handles `policy_scout_check` call, returns structured response, writes audit event.  
**Test:** Unit test each handler with mocked policy engine. Integration test: start server in thread, pipe JSON-RPC request, verify response.  
**Commit:** `feat(server): MCP server v1 — stdio transport, 4 tools, session trust model`  
**Unlocks:** Phase 4. Also enables [11] Desktop UI to display MCP session status.

### Phase 4 — Response Scanning Hook for [07] (~80 lines delta to handlers.py)

**Scope:** Add `PostToolResponse` hook slot in `handlers.py`. `PromptInjectionAnalyzer` (from [07]) plugs in here.  
**Note:** This phase is owned by [07], not [06]. Phase 3 must leave the hook slot visible in the code with a `# [07]: inject response scanner here` comment.  
**Acceptance:** Phase 3 tests still pass. The hook slot exists and is documented.  
**Unlocks:** [07] can be implemented without touching the MCP server structure.

### Phase 5 — `serve install` and `.mcp.json` scaffolding (~80 lines)

**Scope:** `policy-scout serve install --scope project|user`, writes `.mcp.json`.  
**Acceptance:** Running `policy-scout serve install --scope project` creates `.mcp.json` with correct content. `policy-scout serve status` reports registration found.  
**Commit:** `feat(server): serve install — scaffold MCP registration files`

---

## Consequences

**Enabled:**
- Agents using Claude Code can be governed in-loop without cooperation — the `PreToolUse` hook operates at the harness level regardless of what the agent attempts.
- The print/return separation makes every policy-evaluating function independently testable as a unit.
- The session trust model gives the operator (the developer) full control over how permissive the agent's operating context is.
- [07] Prompt Injection gets a clean hook point in Phase 4 without needing to restructure the server.

**Given up / deferred:**
- HTTP/SSE transport. Any use case requiring remote MCP access (cloud agent, second machine) is deferred to v2.
- Multi-tool session enforcement ("agent must check before sandbox") is soft in v1 — it audits but does not hard-block. Hard enforcement is a v2 option.
- Fine-grained per-tool trust escalation. All tools in a session share the same trust level. Per-tool trust differentiation is a v2 option if the need arises.

**Risks to watch:**
- If the print/return separation has subtle bugs, it could change exit-code behavior for existing users. Guard with full test suite run before merging Phase 1.
- The `--hook-mode` stderr JSON schema is a public contract once registered in `.claude/settings.json`. Version it from the start (`"policy_scout_version"` field in the response) so future changes can be detected.
