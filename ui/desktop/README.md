# Policy Scout Tauri UI

Experimental read-only desktop dashboard for Policy Scout. v0.2.x track.

**Policy Scout CLI remains the authority. This UI is a read-only preview surface only.**

## Status

Experimental — v0.2.x read-only UI. Not a mutation, execution, or approval surface.
Native Tauri runtime required for live data. Browser/Vite preview shows static layout only.

## Development Modes

### Browser/Vite Preview (Static Layout Only)

```bash
npm run dev
```

- Opens a browser preview at http://localhost:1420
- Useful for checking static layout and styling
- **Cannot load live Policy Scout CLI data** (Tauri invoke APIs unavailable in browser context)
- Shows friendly message: "Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data."

### Native Tauri Runtime (Live Data)

```bash
npm run tauri dev
```

- Launches the native Tauri application window
- Required for live data in all cards
- Uses Tauri invoke APIs to call Policy Scout CLI commands
- All data comes from the CLI (read-only, no mutations from UI)

### Build Checks

```bash
# Frontend TypeScript + Vite build
npm run build

# Rust backend compile check
cd src-tauri && cargo check
```

## Current Dashboard Cards and Views

| Card | CLI Command |
|---|---|
| Overview Status Strip | Summarizes loaded state across all cards |
| Doctor Status | `policy-scout doctor --json` |
| Data Status | `policy-scout data status --json` |
| Reports List | `policy-scout report list --json --limit 5` |
| Report Detail | `policy-scout report show --json <report_id>` |
| Audit Stats | `policy-scout audit stats --json` |
| Audit Events List | `policy-scout audit list --json --limit 10` |
| Audit Event Detail | `policy-scout audit show --json <event_id>` |
| Cleanup Dry-Run | `policy-scout data cleanup --target <target> --dry-run --json` (demo, sandbox, sandbox-results) |
| Eval Results | `policy-scout eval run --json` |
| Quick Sweep | `policy-scout sweep quick --json` |
| Project Sweep | `policy-scout sweep project --json` |
| Sandbox Results List | `policy-scout report list --json --type sandbox_result --limit 5` |
| Sandbox Result Detail | `policy-scout report show --json <report_id>` |

## Rust Backend Command Wrappers

All Tauri commands are defined in `src-tauri/src/lib.rs` and invoke the installed `policy-scout` CLI binary.
ID arguments (`report_id`, `event_id`) are validated in Rust before being passed to the CLI (prefix check, character allowlist, rejection of shell metacharacters). Event type filter (`event_type`) is validated against a 12-value allowlist in Rust before any CLI call.

| Tauri Command | CLI Invocation |
|---|---|
| `get_doctor_status` | `policy-scout doctor --json` |
| `get_data_status` | `policy-scout data status --json` |
| `list_reports_filtered(limit, report_type?)` | `policy-scout report list --json --limit <n> [--type <type>]` |
| `show_report(report_id)` | `policy-scout report show --json <report_id>` |
| `get_audit_stats` | `policy-scout audit stats --json` |
| `list_audit_events_filtered(event_type?)` | `policy-scout audit list --json --limit 10` (default) or `policy-scout audit type --json <event_type>` (filtered); event_type allowlisted in Rust |
| `show_audit_event(event_id)` | `policy-scout audit show --json <event_id>` |
| `get_cleanup_dry_run(target)` | `policy-scout data cleanup --target <target> --dry-run --json`; target Rust-validated against allowlist (demo, sandbox, sandbox-results); always dry-run |
| `run_eval` | `policy-scout eval run --json` |
| `run_sweep_quick` | `policy-scout sweep quick --json` |
| `run_sweep_project` | `policy-scout sweep project --json` |
| `check_command(command_text)` | `policy-scout check --json <command_text>` (check-only; never executes command) |
| `list_sandbox_results` | `policy-scout report list --json --type sandbox_result --limit 5` |
| `show_sandbox_result(report_id)` | `policy-scout report show --json <report_id>` |

## Frontend Architecture

- **App.tsx** — owns all state, issues `invoke()` calls, passes typed data to cards
- **Components** — presentational where practical; receive typed props, no direct invoke
- **types.ts** — loose current-contract TypeScript interfaces for CLI JSON shapes; not strict runtime validation

### Shared Components

| Component | Purpose |
|---|---|
| `StatusPill` | Severity/decision badges with tone mapping |
| `EvidenceText` | Redaction-aware text display |
| `RedactionNotice` | Shows redaction warning when applied |
| `DetailHeader` | Shared header for detail views with close button |
| `SweepResultPreview` | Reusable finding/could-not-verify list for sweep cards |
| `BoundaryNote` | Persistent read-only boundary reminder |

### Visual System

- Calm dark theme using CSS variables
- Evidence-safe display: redacted values styled distinctly
- Status pills for severity, decision, and eval status tones

## Safety Boundaries

The Tauri UI is explicitly constrained to read-only display:

- No command execution UI
- No approval resolution UI
- No sandbox migration UI
- No cleanup deletion (dry-run preview only)
- No report export or deletion UI
- No audit export or deletion UI
- No arbitrary shell access
- No frontend-provided argv arrays
- No direct SQLite reads from frontend
- No direct filesystem browsing from frontend
- Sweeps are user-triggered only — no background scanning or daemon
- Cleanup is dry-run preview only — no actual deletion
- Report and audit detail IDs are selected from loaded lists and validated in Rust before CLI invocation

## Manual Smoke Checklist

A repeatable native smoke checklist for verifying all cards, selectors, detail flows, and
safety boundaries in the native Tauri window is maintained at:

`docs/compressed/TAURI_NATIVE_MANUAL_SMOKE_CHECKLIST_SOURCE.md`

Run it at significant Tauri checkpoints and before v0.3.x feature expansion.

## Known Limitations

- Native click-level interaction requires manual or GUI automation verification (not automated)
- No pagination or filtering for reports or audit events lists yet
- No project path selection for project sweep (uses current working directory of the `policy-scout` process)
- No strict JSON API v1 envelope yet — types are current-contract/loose
- Types in `types.ts` document actual shapes but do not enforce them at runtime
- Browser preview (`npm run dev`) cannot load live Tauri invoke data
- No sandbox results read-only list/detail yet
- No Decision Check UI yet

## Recommended Next Steps

1. Manual native click verification across all cards
2. Audit/report list pagination or filter controls
3. Visual polish continuation
4. Sandbox results read-only list/detail view
5. Decision Check UI (check-only, not run) — boundary spec at `docs/compressed/TAURI_DECISION_CHECK_GUIDED_FAQ_BOUNDARY_SOURCE.md`

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
