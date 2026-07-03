# Integration boundaries

Integrations may submit requests, display decisions, and carry redacted events.
They do not become policy authorities.

## Boundary table

| Surface | Current role | Authority |
|---|---|---|
| CLI | Canonical user and automation interface | Policy Scout core |
| Claude Code hook mode | Pre-command check adapter | Returns the core decision |
| MCP stdio server | Local tool adapter | Delegates to core services |
| Tauri desktop | Read/check companion | Invokes fixed CLI commands |
| Git hooks | Opt-in staged-change adapter | Calls Policy Scout checks; bypass remains possible |
| Fossic | Local secondary event store | Observability only; SQLite remains operational authority |
| Lattica | External dashboard and coordination consumer | Invokes CLI actions and renders events |
| VS Code / Cursor extension | Experimental sweep diagnostics and MCP registration | Delegates all decisions to core CLI |

## MCP

`policy-scout serve` implements local JSON-RPC over stdio. Handlers expose bounded
Policy Scout operations and delegate to existing application code. There is no
HTTP/SSE listener, remote identity system, or multi-user authorization service.

Caller-provided identity must not grant additional trust. The server/session
layer owns trust context and audit linkage.

## Desktop

The Tauri backend invokes the installed `policy-scout` binary with constructed
argument vectors. It validates report/event IDs, event filters, pagination
values, and cleanup targets. The frontend does not receive an arbitrary argv
execution primitive and does not read SQLite directly.

Decision Check calls `check`, never `run`. Cleanup is forced through dry-run in
the desktop adapter even though the CLI has an explicit `--apply` path.

## Fossic

After SQLite redaction and persistence, the audit adapter can append selected
event payloads to `~/.local/share/policy-scout/fossic.db`:

- request events: `policy-scout/audit/<request_id>`;
- global lockdown/watch posture: `policy-scout/posture`.

Indexed tags carry source and selected correlation metadata. An optional
`upstream_causation_id` can connect a request to an event proposed by another
local system.

Fossic writes are best-effort. A Fossic failure does not erase the successful
SQLite record. Fossic must not receive unredacted payloads merely because it is
local.

## Lattica

Lattica contains a Policy Scout tile with two live data paths:

1. **Track A — CLI polling**: four Tauri commands (`ps_watch_status`,
   `ps_approvals_list`, `ps_approve_once`, `ps_deny`) are fully implemented in
   Lattica's `src-tauri/src/lib.rs` and shell out to the policy-scout CLI with
   `--json` flags. Watch, lockdown, and approval state surface in the tile;
   approval and lockdown controls invoke the same CLI paths.
2. **Track B — Fossic events**: subscription and startup backfill from
   `policy-scout/**` streams relay posture and decision events to the tile via
   `policy-scout-relay.py`.

Both paths are live. Lattica's controls remain external consumers of Policy
Scout's CLI — they do not alter policy or bypass the decision engine.

The standalone `policy-scout-relay.py` is tracked source and can backfill and
relay selected local Fossic events to Lattica's local hub. It is experimental
and has no isolated test coverage; it is not part of the core v0.3.19 release
guarantee.

### Contracts that remain planned

Lattica's accepted governance ADR describes a broader target: every agent action
with side effects on files, packages, or system state passes through a mandatory
dispatch gate. Policy Scout does not currently provide complete structured
governance for arbitrary non-shell file mutations, and event subscription alone
cannot establish that guarantee.

Also planned rather than current:

- medium-risk asynchronous approval/review semantics;
- a complete per-request causal pipeline visualization;
- managed relay lifecycle and health;
- extraction of a cross-project neutral eval-core package.

These ideas belong in the roadmap until both repositories contain tested code.

## VS Code and Cursor

`ui/vscode/` contains an experimental extension with three capabilities:

- **Sweep diagnostics**: on save of `package.json`, lockfiles, GitHub Actions workflows,
  or shell scripts, runs `policy-scout sweep project --json` and populates VS Code's
  `DiagnosticCollection`. Critical/high findings appear as editor errors; medium as
  warnings.
- **Hook management**: detects whether the pre-commit hook is installed and offers
  install/uninstall via VS Code commands and a one-time notification.
- **MCP registration**: in VS Code agent mode, registers the stdio MCP server via
  `vscode.lm.registerMcpServerDefinitionProvider` so the editor's AI can call
  `policy_scout_check` before acting. In Cursor, writes the server entry into
  `.cursor/mcp.json` on activation.

The extension is source-only — it is not packaged or listed in any marketplace.
It does not add trust claims or alter policy; it surfaces the same decisions the
CLI produces.

## Side-effect boundary

The useful long-term rule from the Lattica design is:

> Policy Scout governs consequential actions; it does not judge internal
> inference or cognition.

Shell commands, package installs, file mutations, and system mutations are valid
governance targets. LLM classifications, in-memory scoring, and private return
values are not action-policy decisions. Prompt-injection scanning is a bounded
input analysis feature, not authority over all LLM calls.

## Integration requirements

Every future adapter must preserve:

- actor and request source;
- exact action and working context;
- core policy decision and reasons;
- approval/sandbox routing;
- audit correlation IDs;
- secret redaction;
- fail-closed behavior for decisions that cannot safely proceed.

No adapter may add permanent trust from a one-time approval or silently convert a
hard denial into an executable route.
