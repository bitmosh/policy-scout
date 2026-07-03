# Implementation status

**Release:** v0.3.19 alpha
**Verified:** 2026-07-02

This is a capability snapshot, not a milestone log. “Implemented” means an
executable code path and focused tests exist. It does not imply production
hardening or complete platform support.

## Verification baseline

| Signal | Verified result |
|---|---:|
| Python tests | 1,188 passed, 2 skipped |
| Behavior evals | 50/50 passed |
| Command-registry entries | 15 |
| Default policy rules | 11 |
| Python requirement | 3.12+ |

Reproduce with:

```bash
python -m pytest -q
python -m policy_scout.cli.main eval run
python -m policy_scout.cli.main doctor --json
```

## Capability matrix

| Area | Status | Current boundary |
|---|---|---|
| Command parsing, classification, risk, policy | **Implemented** | Deterministic core with registry data and conservative fallbacks |
| `check` and policy-gated `run` | **Implemented** | Only `ALLOW`/`ALLOW_LOGGED` execute directly |
| One-time approvals | **Implemented** | Exact command/cwd, expiration, status, scope, current-policy recheck |
| Package sandbox review | **Implemented** | npm, pnpm, yarn, bun; separate workspace, lifecycle inspection, diffs, reports |
| Sandbox migration | **Implemented** | Explicit confirmation, allowlisted files, high/critical block, backups |
| Project and quick sweeps | **Implemented** | Project analysis plus Linux-first host signals; evidence, not malware proof |
| Audit and reports | **Implemented** | SQLite primary, JSONL, Markdown/JSON reports, read-time redaction |
| Secret and prompt-injection scans | **Implemented alpha** | Pattern/entropy based; false positives and false negatives expected |
| Policy management | **Implemented alpha** | Tighten-only project overrides, simulation, validation, history testing |
| Git integration | **Implemented alpha** | Context, hooks, staged checks, lockfile comparison |
| Incident response | **Implemented alpha** | Lockdown, evidence preservation, clearance checks; no autonomous remediation |
| Watch mode | **Experimental** | Local daemon and event routing; platform/tool dependent |
| Threat intelligence | **Experimental** | Local checks plus opt-in OSV/npm network clients and cache |
| General namespace sandbox | **Experimental** | Linux `unshare`, optional OverlayFS/strace; host prerequisites determine containment |
| Self-integrity | **Implemented alpha** | Registry manifest generation and verification; no self-repair |
| MCP server | **Experimental adapter** | Local stdio transport and bounded tools; not remote/multi-user auth |
| Tauri desktop | **Experimental companion** | CLI-backed read/check surfaces; no general command execution UI |
| Fossic emission | **Implemented adapter** | Redacted best-effort local secondary store; SQLite remains authority |
| Lattica integration | **Live (two paths)** | Track A: 4 Tauri commands in Lattica shell out to policy-scout CLI with --json; Track B: Fossic relay backfills and streams posture/decision events. Both paths confirmed live as of v0.3.9. |
| VS Code / Cursor extension | **Experimental alpha (source only)** | Sweep-on-save diagnostics, pre-commit hook management, MCP auto-registration for VS Code agent mode and Cursor; not packaged or published |

## Verified design strengths

- Granular evaluation signals are retained and tested, not replaced by a single
  risk score.
- Hard denial and sandbox decisions cannot be bypassed through approvals.
- Critical audit failure blocks approved execution.
- Project policy files can tighten but not loosen global policy.
- Sandbox migration validates roots and allowlists and creates backups.
- Sweep results preserve failed checks through `could_not_verify`.
- CLI JSON, schemas, mocks, TypeScript types, and Rust adapter validation share
  regression coverage.

## Known limitations

- Shell interpretation is heuristic rather than a complete shell grammar.
- Fifteen registry entries are narrow relative to the full command ecosystem;
  classifier code contains additional hard-coded detection paths.
- Redaction and secret scanning are regex/entropy based.
- CLI was decomposed from a 4,443-line monolith into 18 command modules in v0.3.18/0.3.19; residual orchestration coupling remains.
- Several optional features depend on Linux tools, kernel capabilities, package
  managers, Git, network access, or a native Tauri toolchain.
- The Fossic adapter is best-effort at runtime; its vendored PyO3 binding adds a
  Rust build step before Policy Scout installation.
- The desktop UI still relies on manual native interaction verification.
- The desktop cleanup wrapper still passes a legacy `--dry-run` flag that the CLI no longer accepts.
- There is no packaged installer, PyPI release, remote approval service, or
  enterprise authorization model.

## Deferred work

Only unimplemented work belongs here; completed milestones live in Git history.

- expand registry/eval coverage with measurable coverage reporting;
- split CLI parsing/orchestration from subsystem services;
- formalize sandbox backend capabilities and containment reporting;
- add configurable audit/report retention and safe archival;
- add sweep delta, baselines, exclusions, and audited suppression;
- track and test the Policy Scout-to-Lattica relay lifecycle;
- extract a neutral eval core only if the cross-project interface is proven;
- package and harden the desktop application;
- package and publish the VS Code/Cursor extension; add integration tests;
- build JetBrains, Zed, and other editor integrations after the core contracts stabilize.
