# Implementation Plan — Gap 6: MCP Server / Agent Integration

## Problem
Policy Scout currently sits outside the agent tool-call loop. An agent using Claude Code, Cursor, or any MCP-capable client has no in-loop integration path — it calls tools directly, and Policy Scout can only evaluate after the fact or via manual `policy-scout check`. This defeats the core use case.

## Goal
A local MCP server that exposes Policy Scout's capabilities as MCP tools, enabling agents to query before acting. A Claude Code `settings.json` hook configuration that makes pre-tool-call policy checks automatic without agent cooperation.

---

## New Module: `policy_scout/server/`

```
policy_scout/server/
├── __init__.py
├── mcp_server.py       # MCP stdio server (JSON-RPC 2.0 over stdin/stdout)
├── tool_definitions.py # MCP tool schemas
├── handlers.py         # tool call handlers (delegate to existing CLI logic)
└── session.py          # per-connection session state + trust level
```

---

## Implementation Approach

### Step 1 — MCP Protocol (stdio transport)

MCP servers communicate over stdin/stdout using JSON-RPC 2.0 messages. The protocol is well-specified and simple enough to implement without a library.

Message framing: each message is a JSON object on its own line (newline-delimited). For large responses, use chunked tool results.

```python
# mcp_server.py

import sys
import json
import threading

class MCPServer:
    def __init__(self, handlers: dict):
        self._handlers = handlers

    def run(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
                response = self._dispatch(message)
                if response is not None:
                    print(json.dumps(response), flush=True)
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {"code": -32603, "message": str(e)},
                }
                print(json.dumps(error_response), flush=True)

    def _dispatch(self, message: dict) -> dict | None:
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")

        if method == "initialize":
            return self._handle_initialize(msg_id, params)
        elif method == "tools/list":
            return self._handle_tools_list(msg_id)
        elif method == "tools/call":
            return self._handle_tool_call(msg_id, params)
        elif method == "notifications/initialized":
            return None  # no response for notifications
        else:
            return {"jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}}
```

### Step 2 — Tool Definitions (`tool_definitions.py`)

```python
MCP_TOOLS = [
    {
        "name": "policy_scout_check",
        "description": (
            "Check whether a command is safe to run according to Policy Scout's "
            "registry-backed policy. Returns a decision (ALLOW/DENY/etc.) with reasons. "
            "Call this before executing any shell command, running a script, or installing packages."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The full shell command to evaluate, e.g. 'npm install lodash'",
                },
                "actor_type": {
                    "type": "string",
                    "enum": ["agent", "human", "ci"],
                    "default": "agent",
                    "description": "The type of actor requesting the command",
                },
                "intent": {
                    "type": "string",
                    "description": "Optional: natural-language description of why this command is needed",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "policy_scout_sandbox",
        "description": (
            "Run a package install in an isolated sandbox workspace and get a safety report "
            "before the install touches the real project. Use for npm install, pnpm add, yarn add, bun add."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_manager": {
                    "type": "string",
                    "enum": ["npm", "pnpm", "yarn", "bun"],
                },
                "package_spec": {
                    "type": "string",
                    "description": "Package name and optional version, e.g. 'lodash' or 'lodash@4.17.21'",
                },
            },
            "required": ["package_manager", "package_spec"],
        },
    },
    {
        "name": "policy_scout_sweep",
        "description": (
            "Run a project or system sweep to detect suspicious traces, "
            "malicious lifecycle scripts, persistence mechanisms, or credential exposure."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["project", "quick"],
                    "description": "'project' scans project files; 'quick' scans the system environment",
                },
            },
            "required": ["scope"],
        },
    },
    {
        "name": "policy_scout_get_report",
        "description": "Retrieve a previously generated Scout Report by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "report_id": {"type": "string"},
                "format": {"type": "string", "enum": ["markdown", "json"], "default": "json"},
            },
            "required": ["report_id"],
        },
    },
]
```

### Step 3 — Handlers (`handlers.py`)

Each tool call delegates to the existing CLI logic by invoking the Python API directly (not via subprocess — too slow for interactive use):

```python
from policy_scout.cli.check import run_check
from policy_scout.cli.sandbox import run_sandbox
from policy_scout.cli.sweep import run_sweep
from policy_scout.reports.scout_report import get_report

def handle_check(params: dict) -> dict:
    command = params["command"]
    actor_type = params.get("actor_type", "agent")
    intent = params.get("intent")

    result = run_check(
        command=command,
        actor_type=actor_type,
        intent=intent,
        output_format="dict",   # return dict, not print
    )
    return {
        "decision": result.decision.value,
        "risk_score": result.risk_score.score,
        "risk_band": result.risk_score.band,
        "reasons": result.reasons,
        "recommended_action": result.recommended_action,
        "report_id": result.report_id,
    }
```

This requires the existing CLI functions to support a `output_format="dict"` return path. Currently they print and return exit codes. This is the largest refactor in the plan — isolating the core logic from the print layer. It's worth doing regardless for testability.

### Step 4 — Claude Code Hook Integration

Claude Code supports `PreToolUse` hooks in `settings.json`. A hook is a shell command that runs before every tool call and can block it.

Policy Scout can be registered as a pre-tool-use hook that intercepts `Bash` and `computer_use` tool calls:

```json
// .claude/settings.json (project-level) or ~/.claude/settings.json (user-level)
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "policy-scout check --hook-mode -- $CLAUDE_TOOL_INPUT_COMMAND",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

`--hook-mode` is a new flag that:
- Reads the command from the argument
- Runs the policy check
- Exits 0 for ALLOW/ALLOW_LOGGED (hook passes)
- Exits non-zero with a JSON error message for DENY/DENY_AND_ALERT (hook blocks with explanation)
- Exits 0 with a warning message for REQUIRE_APPROVAL/SANDBOX_FIRST (hook passes but logs)

```python
# In cli/check.py
def run_check_hook_mode(command: str) -> None:
    result = run_check(command=command, actor_type="agent", output_format="dict")
    if result.decision in (Decision.DENY, Decision.DENY_AND_ALERT):
        # Hook blocks: print JSON error to stderr for Claude Code to surface
        error = {
            "decision": result.decision.value,
            "reasons": result.reasons,
            "policy_scout_report": result.report_id,
        }
        print(json.dumps(error), file=sys.stderr)
        sys.exit(1)
    elif result.decision == Decision.REQUIRE_APPROVAL:
        # Let it through but log loudly
        warning = {"decision": result.decision.value, "reasons": result.reasons}
        print(json.dumps(warning), file=sys.stderr)  # shows in Claude Code UI
        sys.exit(0)
    else:
        sys.exit(0)
```

### Step 5 — `policy-scout serve` CLI Command

```bash
# Start MCP server (stdio transport — used by MCP clients)
policy-scout serve --mcp

# Start with explicit trust level for this session's agents
policy-scout serve --mcp --agent-trust low|medium|high

# Check MCP server status (is it registered? is another instance running?)
policy-scout serve status
```

MCP server registration: Claude Code discovers MCP servers via `.mcp.json` in the project root or `~/.claude/mcp.json` globally:

```json
// .mcp.json
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

Policy Scout should provide a `policy-scout serve install` command that writes this file:

```bash
policy-scout serve install --scope project   # writes .mcp.json
policy-scout serve install --scope user      # writes ~/.claude/mcp.json
```

### Step 6 — Agent Trust Levels via Session Config

The existing `Actor` model has a `trust_level` field. The MCP session should allow configuring the default trust level for the agent connecting in this session, which feeds into the policy engine's mode selection:

```yaml
# ~/.config/policy-scout/config.yaml
server:
  default_agent_trust: medium    # low | medium | high
  require_check_before_run: true # agents must call policy_scout_check before any Bash tool
```

When `default_agent_trust: low`, the policy engine applies the `paranoid` mode automatically for all agent requests, regardless of what mode is specified in the request.

---

## New Audit Event Types

```
MCPServerStarted         — server came up, listening
MCPToolCallReceived      — agent called a tool
MCPToolCallCompleted     — tool returned (with latency)
MCPSessionEnded          — client disconnected
```

---

## Integration Points

- `cli/check.py` — add `--hook-mode` flag and `output_format` parameter
- `cli/main.py` — register `serve` command group
- `core/executor.py` — ensure logic is callable without print side-effects
- `audit/events.py` — add four new event types
- `doctor.py` — check MCP server registration status

---

## Test Strategy

- Unit test each tool handler with mocked policy engine
- Unit test MCP protocol dispatch (initialize, tools/list, tools/call)
- Unit test `--hook-mode` exit codes for each decision type
- Integration test: start server in a thread, send a check request over stdin/stdout pipe, verify response
- Manual verification: register with Claude Code, call a `Bash` command that Policy Scout would deny, verify the hook blocks it

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `mcp_server.py` (JSON-RPC protocol) | ~200 | Medium |
| `tool_definitions.py` | ~100 | Low |
| `handlers.py` (4 tools) | ~200 | Medium |
| `session.py` | ~60 | Low |
| `--hook-mode` in `cli/check.py` | ~60 | Low |
| `serve install` command | ~80 | Low |
| Refactor CLI print/return separation | ~200 | Medium |
| Tests | ~300 | Medium |
| **Total** | **~1200** | |

---

## Open Questions

1. Should the MCP server support HTTP/SSE transport in addition to stdio? Recommendation: stdio only for v1 — it's simpler, more secure (no network surface), and sufficient for local use. HTTP transport is a future addition.
2. Should the server enforce that agents call `policy_scout_check` before `policy_scout_run`? Recommendation: yes, via session state. If an agent calls `run` without a prior `check` for the same command in the same session, the server upgrades the mode to `paranoid` for that request.
3. What happens when `policy-scout serve --mcp` is started without a registered client? It should wait on stdin indefinitely (normal MCP behavior). `policy-scout serve status` lets users check without starting a server.
