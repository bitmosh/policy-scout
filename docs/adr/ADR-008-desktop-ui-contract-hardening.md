# ADR-008: Desktop UI Contract Hardening

**Status:** Accepted  
**Date:** 2026-06-10  
**Deciders:** Developer (bitmosh)  
**Related ADRs:** [ADR-001](ADR-001-mcp-transport-and-trust-model.md) (CLI JSON contracts are the canonical interface; Tauri wraps them, not bypasses them), [ADR-006](ADR-006-report-and-data-lifecycle.md) (pagination requires `total_count` in list responses)

---

## Context

The Tauri desktop UI has three structural weaknesses that make it unreliable as a companion tool and expensive to maintain as the CLI evolves:

1. **Loose TypeScript types.** `types.ts` defines the TypeScript interfaces for CLI JSON output as approximate shapes — `any` fields, optional properties that are sometimes required, missing fields that the UI silently ignores. When the CLI changes a JSON shape, the frontend compiles fine and fails silently at runtime, visible only in native smoke testing.

2. **No browser preview with data.** `npm run dev` shows static empty shells. A developer working on the UI must run the full native Tauri runtime to see any real data. This makes UI development slow and means mistakes aren't caught until native smoke.

3. **No pagination.** `report list`, `audit list`, and `audit events` all use a fixed `--limit 10` or `--limit 5`. With 18,000+ audit events on the developer machine, the list views are permanently truncated. There is no way to navigate to older items in the UI.

A fourth problem is upstream of the UI but affects it: the CLI JSON contracts are not formally validated anywhere. The `test_json_contracts.py` suite tests some shapes, but it's manually maintained. When a new field is added to CLI output, the TypeScript types don't update automatically, and the contract tests don't catch it.

This ADR locks the approach for all four problems. The goal is that a CLI JSON shape change produces a visible TypeScript error or a test failure before it reaches native smoke, not after.

---

## Forces

- **CLI is the authority, not the UI.** The TypeScript types must be derived from or validated against the CLI output, not the other way around. If there's a conflict, the CLI wins. This means the type validation approach must test that CLI output conforms to the types, not that the types describe what the developer thinks the CLI does.
- **Browser preview must work without the native runtime.** The frontend should be testable without Tauri. Mock data fixtures must cover all 14 dashboard cards and be maintained alongside the TypeScript types. When a card's data shape changes, both the type and the mock fixture change together.
- **Pagination is a safety boundary.** The Tauri adapter currently passes `--limit 10` hardcoded in Rust. Pagination (offset/limit) must flow through the Rust adapter's validation layer — unvalidated `offset` values must not reach CLI argv. The adapter validates offset as a non-negative integer with a reasonable cap (≤ 10,000).
- **No new execution surface.** Adding pagination and mock data should not create any path for the frontend to pass arbitrary arguments to the CLI. Every parameter added to the Rust adapter gets a validator at the adapter layer. This is a binding requirement, not a guideline.

---

## Decision

### D1 — TypeScript type validation approach

Types in `types.ts` are validated against real CLI JSON output by an automated test in `tests/test_json_contracts.py`. For each type defined in `types.ts`, there is a corresponding JSON fixture in `ui/desktop/src/mocks/` that is also tested against a live CLI invocation.

The validation chain:
```
CLI command → stdout (JSON) → pytest asserts shape matches TypeScript interface definition
TypeScript interface → mock fixture (JSON) → pytest asserts mock matches the same shape
```

This means a CLI output change that isn't reflected in `types.ts` fails the contract test. A `types.ts` change that isn't reflected in the mock fixture fails a different test. Both failures are caught before native smoke.

The contract test does not generate TypeScript from Python or parse TypeScript. It maintains a parallel `contracts/` directory of JSON Schema files (one per type) that both the pytest test and a TypeScript `z.infer`-style validator can check against. The JSON Schema is the single source of truth — both sides validate against it.

```
ui/desktop/src/contracts/
  report_list_response.json     (JSON Schema)
  report_detail_response.json
  audit_stats_response.json
  audit_list_response.json
  ... (one per Tauri command)

ui/desktop/src/mocks/
  report_list.json              (mock fixture)
  report_detail.json
  audit_stats.json
  ... (one per card)
```

### D2 — TypeScript strict mode and type tightening

`types.ts` is split per-domain and moved to `ui/desktop/src/types/`:
```
types/reports.ts
types/audit.ts
types/sandbox.ts
types/sweep.ts
types/doctor.ts
types/eval.ts
types/policy.ts     (new, for [10] policy management CLI output)
```

All `any` fields are replaced with specific types or `unknown` (with an explicit comment explaining why). `tsconfig.json` enables `"strict": true` and `"noUncheckedIndexedAccess": true`. TypeScript compile errors on type regressions before the build.

The build step in CI (`npm run build`) already enforces typecheck. The only change is that the types get strict enough that TypeScript actually catches contract regressions.

### D3 — Browser preview with mock data

`npm run dev` loads mock fixtures when Tauri's `invoke` is not available. The detection is already implemented (a `try/catch` around `invoke` calls). Currently it falls back to an empty/error state. Under this ADR it falls back to the mock fixture instead.

```typescript
// Current behavior
try {
  data = await invoke('get_doctor_status')
} catch {
  data = null  // shows error card
}

// New behavior
try {
  data = await invoke('get_doctor_status')
} catch {
  data = MOCKS.doctor_status  // shows realistic mock data
}
```

Mock fixtures are imported at the top of each component file (tree-shaken in production builds — `invoke` succeeds in native context so the mock path is never reached at runtime).

This makes browser preview a usable development environment and means UI layout, styling, and component logic can be verified without native Tauri.

### D4 — Pagination in list views

The Tauri adapter gains `offset` and `limit` parameters on list commands. Validation in `lib.rs`:

```rust
fn validate_pagination(limit: Option<u32>, offset: Option<u32>) -> Result<(u32, u32), String> {
    let limit = limit.unwrap_or(20).min(100);     // cap at 100; default 20
    let offset = offset.unwrap_or(0).min(10_000); // cap at 10,000
    Ok((limit, offset))
}
```

CLI commands that receive these params:
- `list_reports_filtered(limit, offset, report_type?)` — was `limit` only
- `list_audit_events_filtered(limit, offset, event_type?)` — was `limit` only

JSON responses from these commands must include `total_count` (ADR-006 D4). The frontend uses `total_count` to compute total pages without a separate query.

Frontend pagination component: a simple prev/next control below each list card. No page numbers, no jump-to-page, no infinite scroll in v1 — prev/next with a "showing N–M of total" label.

### D5 — Policy management UI (new cards for [10])

The policy management CLI commands (`policy simulate`, `policy show`, `policy validate`, `policy test`) have no Tauri adapter yet. Under this ADR, read-only cards are added:

| Card | Adapter command | Notes |
|---|---|---|
| Policy Overview | `get_policy_overview` | wraps `policy-scout policy show --json` |
| Policy Validate | `run_policy_validate` | wraps `policy-scout policy validate --json` |

`policy simulate` and `policy test` are not added in v1 — they require command input from the user, which crosses the "no command execution UI" boundary. A simulate card that accepts a command string is a check-only surface (like Decision Check) and is in scope for a future pass.

### D6 — Safety boundary preservation

Adding pagination and mock data must not create new execution vectors. Explicitly prohibited additions:

- No user-provided command strings passed to CLI argv except through already-approved adapters (Decision Check via `check_command`)
- No new file path parameters from the frontend
- No new event type or report type values except those on the Rust allowlists
- `offset` and `limit` are integers validated in Rust before reaching CLI argv

The Tauri adapter allowlists (event types, report types, cleanup targets) gain automated tests in `tests/` that verify the allowlist values match what the CLI actually accepts. Currently these are spot-checked manually.

---

## Consequences

### Positive
- A CLI JSON shape change that breaks the TypeScript types is caught by `npm run build` before native smoke
- Browser preview with mock data is a usable development environment
- The policy management cards make the new [10] functionality visible in the dashboard
- Pagination makes `report list` and `audit list` usable with large datasets

### Negative / Risks
- The JSON Schema contract files are a new artifact that must be maintained. A type change that isn't reflected in the JSON Schema fails silently until the contract test runs. The contract test must run in CI (it does — it's in `test_json_contracts.py`). The JSON Schema files live in `ui/desktop/src/contracts/` so TypeScript tooling can also validate against them.
- Mock fixtures can become stale if they're not updated when the CLI output changes. The contract test catches this: the same JSON Schema validates both live CLI output and the mock fixture, so a stale mock fails the same test as a stale TypeScript type.
- `noUncheckedIndexedAccess: true` in TypeScript may cause a batch of compile errors on first enable. These are real bugs (unsafe array indexing) being surfaced, not noise. They must be fixed, not suppressed.

---

## Blast Radius

| File | Change |
|---|---|
| `ui/desktop/src/types.ts` | split into `types/` directory; all `any` removed |
| `ui/desktop/src/types/*.ts` | new — domain-split type files |
| `ui/desktop/src/contracts/*.json` | new — JSON Schema per adapter command |
| `ui/desktop/src/mocks/*.json` | new — mock fixtures per card |
| `ui/desktop/src/App.tsx` | modified — mock fallback in invoke wrappers |
| `ui/desktop/src-tauri/src/lib.rs` | modified — `offset` param on list commands, `validate_pagination()` |
| `ui/desktop/tsconfig.json` | modified — `strict: true`, `noUncheckedIndexedAccess: true` |
| `tests/test_json_contracts.py` | modified — validate against JSON Schema files; validate mocks |
| `ui/desktop/src/components/*.tsx` | modified — pagination controls on list cards |
| `ui/desktop/src/components/PolicyOverview.tsx` | new |
| `ui/desktop/src/components/PolicyValidate.tsx` | new |

---

## Implementation Phases

### Phase 1 — JSON Schema contracts and mock fixtures
- Write JSON Schema for each existing Tauri adapter command (14 total)
- Write mock fixtures for each card
- Update `test_json_contracts.py` to validate live CLI output against JSON Schema
- Update `test_json_contracts.py` to validate mock fixtures against JSON Schema

**STOP gate:** All contract tests pass against live CLI. All mock fixtures validate against schemas.

### Phase 2 — TypeScript strict mode
- Split `types.ts` into domain files
- Remove all `any` annotations
- Enable `strict: true` and `noUncheckedIndexedAccess: true` in `tsconfig.json`
- Fix compile errors (treat as real bugs)

**STOP gate:** `npm run build` passes cleanly with strict mode enabled.

### Phase 3 — Browser preview mock data
- Add mock fallback in `invoke` wrappers in `App.tsx`
- `npm run dev` shows realistic data for all 14 existing cards

**STOP gate:** `npm run dev` renders all cards with mock data. No "no data" empty states in browser preview.

### Phase 4 — Pagination
- `validate_pagination()` in `lib.rs`
- `offset` param on `list_reports_filtered` and `list_audit_events_filtered`
- `total_count` in list JSON responses (requires ADR-006 Phase 1)
- Prev/next pagination UI on Reports List and Audit Events List cards

**STOP gate:** Reports List card shows "showing 1–20 of 142" and prev/next controls work.

### Phase 5 — Policy management cards
- `get_policy_overview` adapter wrapping `policy show --json`
- `run_policy_validate` adapter wrapping `policy validate --json`
- Policy Overview and Policy Validate cards in dashboard
- Mock fixtures + JSON Schema for both

**STOP gate:** Policy Validate card shows validation results in native runtime.
