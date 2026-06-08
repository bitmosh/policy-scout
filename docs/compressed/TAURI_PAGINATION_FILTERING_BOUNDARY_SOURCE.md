# Policy Scout — Tauri Pagination and Filtering Boundary Plan v0

## 1. Purpose

Define the safety boundary for future list pagination and filtering controls in the
experimental Tauri read-only UI. This document must be accepted before any pagination
or filtering UI is implemented.

The UI is a read-only viewer. Pagination and filtering must not become a vector for
arbitrary CLI argument construction, arbitrary query strings, or policy bypass.

**Core principle:** The Rust backend owns command construction. The frontend may only
choose from bounded, allowlisted UI controls. The CLI remains the authority.

---

## 2. Non-Goals

This document does NOT:

- Implement pagination, filtering, or any list controls
- Change CLI JSON shapes or CLI behavior
- Change Python code, tests, or Rust behavior
- Add new Tauri commands
- Add frontend-provided argv arrays
- Add free-text search UI
- Add approval, migration, execution, or mutation UI
- Add direct filesystem or database access
- Commit until approved

---

## 3. Current Fixed-List Behavior

All current lists are hard-coded in Rust. The frontend sends no parameters.

| Tauri Command | CLI Invocation | Fixed Limit |
|---|---|---|
| `list_reports` | `report list --json --limit 5` | 5 |
| `list_sandbox_results` | `report list --json --type sandbox_result --limit 5` | 5 |
| `list_audit_events` | `audit list --json --limit 10` | 10 |
| `run_sweep_quick` | `sweep quick --json` | n/a (single run, all findings returned) |
| `run_sweep_project` | `sweep project --json` | n/a (single run, all findings returned) |

**Sweep findings** are capped client-side in `SweepResultPreview`:
- `maxFindings = 10` (prop, caller-defined)
- `maxCouldNotVerify = 5` (prop, caller-defined)
- Truncation message shown when findings exceed cap
- No backend re-fetch triggered by client-side cap

**Detail views** are selection-only: `show_report(report_id)`, `show_audit_event(event_id)`,
`show_sandbox_result(report_id)` accept only IDs selected from already-loaded list data.
Frontend never types a raw ID. IDs are validated in Rust before CLI call.

---

## 4. Pagination Doctrine

### Allowed

- Bounded limit selector: frontend sends an integer from an allowlisted set only.
  Allowlisted values: `[5, 10, 25, 50]`. No other values accepted.
- Offset-based pagination if and only if the CLI supports `--offset` reliably.
  Frontend sends a non-negative integer. Rust validates it is non-negative and below
  a safe ceiling (e.g., 10000).
- Cursor/token-based pagination if the CLI returns a pagination token in JSON.
  Frontend sends the token verbatim from the previous response. Rust must verify the
  token contains only safe characters before passing it.
- A Refresh button to re-fetch the current page with the current limit.

### Not Allowed in v0.2

- Frontend-constructed offset arithmetic
- Arbitrary integer limits not in the allowlisted set
- Multi-page pre-fetch or background auto-refresh
- Auto-load-more on scroll
- Infinite scroll

### Rust Validation for Limits

```rust
fn validate_limit(limit: u32) -> Result<u32, CliJsonResponse> {
    match limit {
        5 | 10 | 25 | 50 => Ok(limit),
        _ => Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some(format!("Invalid limit: {}. Must be 5, 10, 25, or 50.", limit)),
            stderr_summary: None,
        }),
    }
}
```

### Rust Validation for Offset

```rust
fn validate_offset(offset: u32) -> Result<u32, CliJsonResponse> {
    if offset > 10_000 {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Offset exceeds maximum safe value (10000).".to_string()),
            stderr_summary: None,
        });
    }
    Ok(offset)
}
```

---

## 5. Filtering Doctrine

### Allowed

- Report type filter from a hardcoded allowlisted set only.
  Current CLI-confirmed values: `["sandbox_result", "sweep_report", "audit_summary"]`.
  Rust must validate the filter value is in this exact set before constructing the
  CLI call. Frontend sends a typed enum value, not a raw string.
- Audit event type filter from a hardcoded allowlisted set.
  Values must be confirmed from CLI docs/tests before enabling.
- Severity filter for already-loaded sweep findings — **client-side only**.
  No backend re-fetch. Frontend filters the in-memory findings array.
- Local sort of already-loaded records by timestamp — **client-side only**.
  No backend re-fetch. No SQL involved.

### Not Allowed in v0.2

- Free-text search or substring filtering
- Arbitrary string filter values passed to CLI
- Filesystem path filter (e.g., filter by project root)
- Date range filter unless CLI supports it natively with validated ISO 8601 dates
- Combined multi-filter queries unless each filter is independently validated
- SQL WHERE clause construction of any kind
- Filter by arbitrary report/event/sandbox ID entered by user

### Rust Validation for Report Type Filter

```rust
const ALLOWED_REPORT_TYPES: &[&str] = &["sandbox_result", "sweep_report", "audit_summary"];

fn validate_report_type(report_type: &str) -> Result<(), CliJsonResponse> {
    if ALLOWED_REPORT_TYPES.contains(&report_type) {
        Ok(())
    } else {
        Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some(format!(
                "Invalid report type: '{}'. Must be one of: {:?}",
                report_type, ALLOWED_REPORT_TYPES
            )),
            stderr_summary: None,
        })
    }
}
```

---

## 6. Allowed Future Controls

The following controls are explicitly permitted if implemented per this doctrine:

| Control | Where | Mechanism |
|---|---|---|
| Limit selector (5/10/25/50) | Reports List, Audit Events, Sandbox List | Frontend dropdown → Rust validates → CLI `--limit N` |
| Next / Previous page | Reports List, Audit Events | Frontend sends offset → Rust validates → CLI `--offset N` (if CLI supports) |
| Report type filter | Reports List | Frontend dropdown from allowlisted values → Rust validates → CLI `--type <type>` |
| Audit event type filter | Audit Events List | Frontend dropdown from allowlisted values → Rust validates → CLI `--type <type>` |
| Severity filter | Sweep findings preview | **Client-side only**, no re-fetch, no backend involved |
| Timestamp sort | Any loaded list | **Client-side only**, no re-fetch, no backend involved |
| Refresh button | Any list card | Re-invokes existing Tauri command with current parameters |

---

## 7. Forbidden Controls

The following must never appear in the v0.2.x Tauri UI:

| Forbidden | Reason |
|---|---|
| Arbitrary CLI argument input | Becomes CLI injection vector |
| Raw query string entry | Becomes SQL/CLI injection vector |
| Arbitrary SQL | Bypasses CLI redaction and audit trail |
| Filesystem path filter | Arbitrary file access, privacy violation |
| Project path picker | Opens filesystem browsing, out of scope |
| Shell command input | Bypasses policy engine entirely |
| Freeform report/event/sandbox ID entry | Must come from loaded list only |
| Delete / export / migrate buttons | Mutation operations, not allowed in read-only UI |
| Background auto-refresh of sweeps | Sweeps are expensive and user-triggered only |
| Remediation actions | Policy boundary violation |
| Arbitrary limit integer (not in allowlist) | Unbounded CLI argument risk |
| Multi-word free-text search | Not supported by CLI in v0.2 |
| Date range picker (unless CLI supports it) | Requires CLI pagination design first |

---

## 8. Rust Validation Rules

All validation happens in Rust before CLI invocation. Frontend sends typed, bounded values.

### Rules Summary

1. **Limits** must be one of `[5, 10, 25, 50]`. Reject all other values.
2. **Offsets** must be a non-negative integer ≤ 10,000. Reject negatives and excessively large values.
3. **Type filters** must be in the explicit allowlist for the command. Reject unknown values.
4. **IDs** (report_id, event_id) must start with their expected prefix, contain no spaces,
   path separators, or shell metacharacters. Use `validate_report_id` / `validate_event_id`
   helpers (already implemented).
5. **All validated parameters** must be assembled into the CLI argument array by Rust.
   Frontend never provides a pre-assembled command string or argv array.
6. **On validation failure**, return `CliJsonResponse { ok: false, ... }` with a safe,
   non-secret error message. Do not fall through to CLI execution.
7. **No dynamic code paths**: `run_policy_scout_json` receives a concrete `&[&str]` slice
   constructed by the command function, never a frontend-provided slice.

### Shared Helper Pattern (proposed)

```rust
fn build_list_args<'a>(
    base: &[&'a str],
    limit: u32,
    offset: Option<u32>,
    type_filter: Option<&'a str>,
) -> Result<Vec<&'a str>, CliJsonResponse> {
    let limit = validate_limit(limit)?;
    // ...build bounded, allowlisted arg list
}
```

This helper should be private. It must not be exposed as a Tauri command.

---

## 9. Per-List Future Plan

### Reports List (`list_reports`)

Current: `report list --json --limit 5`

Future v0.2.x:
- Add bounded limit selector (5/10/25/50)
- Add offset pagination if `report list` supports `--offset`
- Add report type filter dropdown (allowlisted values only)
- Detail view remains selection-from-list only

Rust changes: new `list_reports_page(limit: u32, offset: u32, report_type: Option<String>)`
command with full validation. Keep `list_reports` for no-arg default load.

### Sandbox Results List (`list_sandbox_results`)

Current: `report list --json --type sandbox_result --limit 5`

Future v0.2.x:
- Add bounded limit selector
- Add offset pagination if supported
- Type filter is fixed to `sandbox_result` — no type selector needed here
- Detail view remains selection-from-list only

Rust changes: new `list_sandbox_results_page(limit: u32, offset: u32)`.
Type filter hardcoded in Rust, not passed from frontend.

### Audit Events List (`list_audit_events`)

Current: `audit list --json --limit 10`

Future v0.2.x:
- Add bounded limit selector
- Add offset pagination if `audit list` supports `--offset`
- Add event type filter if CLI supports `--type` on `audit list`
- Detail view remains selection-from-list only

Rust changes: new `list_audit_events_page(limit: u32, offset: u32, event_type: Option<String>)`
with allowlisted event_type values confirmed from CLI docs.

### Sweep Findings Preview

Current: Single-run, all findings returned, client-side cap via `maxFindings` / `maxCouldNotVerify` props.

Future v0.2.x:
- Severity filter — **client-side only**, no backend change
- Sort by severity — **client-side only**, no backend change
- No pagination: sweeps return a single batch result, not a paginated stream
- No backend re-fetch from filter interaction

### Cleanup Dry-Run Preview

Current: Three fixed commands (`demo`, `sandbox`, `sandbox-results`). Target is hardcoded.

Future v0.2.x:
- No pagination needed: dry-run results are small
- No filter needed: results are pre-categorized
- Target remains hardcoded in Rust (allowlisted: `demo`, `sandbox`, `sandbox-results`)

### Eval Results

Current: Single run, all results returned.

Future v0.2.x:
- Client-side filter by pass/fail status only
- No pagination: eval is a fixed test suite
- No backend changes

---

## 10. Error / Empty / Loading Behavior

All list cards must handle three states. These are already implemented for current fixed lists
and must be preserved for paginated variants.

| State | Required behavior |
|---|---|
| Loading | Show loading indicator. Do not clear previous results until new data arrives. |
| Empty | Show "No items found" message. Do not show error state for empty. |
| Error | Show safe error message from `CliJsonResponse.error`. Never show raw stderr. |
| Validation rejection | Show safe validation error message returned by Rust. No CLI call made. |
| Pagination boundary | On last page: disable Next button. On first page: disable Previous button. |
| Offset out of range | CLI may return empty. Treat as empty state, not error. |

---

## 11. Security and Privacy Boundaries

### Must Hold Across All Pagination/Filtering Additions

- Frontend never constructs CLI argument arrays.
- Frontend never passes raw strings as filter values without Rust validation.
- Rust owns allowlist enforcement. Frontend dropdown values are a UI hint only.
- All ID arguments (report_id, event_id) must pass existing `validate_report_id` /
  `validate_event_id` helpers. Detail views remain selection-from-list only.
- `run_policy_scout_json` is never called with frontend-provided `&[&str]`.
- No direct SQLite (`audit.db`) reads from UI.
- No direct report file reads from UI.
- Sweep findings display via `EvidenceText` component — redaction placeholders preserved.
- No network calls from UI. All data comes from local CLI subprocess.
- No background polling. All data fetches are explicit user actions.
- Pagination state (current page/offset) is ephemeral frontend state only,
  not persisted to disk.

---

## 12. Implementation Sequence

Implement in this order. Do not skip steps.

1. **Accept this boundary doc.** No pagination/filtering code until this doc is committed.
2. **Audit CLI support.** Confirm whether `report list`, `audit list` support `--offset`.
   Do not implement offset pagination until confirmed with a live test.
3. **Add Rust validation helpers** (`validate_limit`, `validate_offset`, `validate_report_type`,
   `validate_audit_event_type`) with unit-testable logic. No frontend changes yet.
4. **Add first paginated command** — `list_reports_page(limit, offset)` with full validation.
   Wire into Reports List card with limit selector and prev/next buttons.
5. **Add `list_audit_events_page`** after Reports List pagination is stable.
6. **Add `list_sandbox_results_page`** after audit pagination is stable.
7. **Add client-side severity filter** to Sweep findings preview.
8. **Add report type filter** to Reports List if needed after pagination is stable.
9. **Do not add free-text search** until JSON API v1 / CLI search support is designed.
10. **Do not add date range filter** until CLI date filter support is confirmed and
    ISO 8601 validation is designed.

---

## 13. Test Strategy

### Rust Unit Tests (New)

- `validate_limit`: confirm 5/10/25/50 pass; confirm all other values rejected.
- `validate_offset`: confirm 0 passes; confirm 10001 rejected; confirm negatives rejected
  (note: u32 makes negatives impossible at type level, but boundary still tested).
- `validate_report_type`: confirm each allowlisted value passes; confirm unknown value rejected.
- `validate_audit_event_type`: same pattern.

### CLI Contract Tests (Python, existing pattern)

- Add `test_report_list_json_limit` confirming `--limit 5` returns ≤5 items.
- Add `test_audit_list_json_limit` confirming `--limit 10` returns ≤10 items.
- Confirm `--offset` behavior when added to CLI: empty result at out-of-range offset
  returns `[]` or `{"events": []}`, not an error.

### Frontend Behavior Tests (future, if Playwright added)

- Limit selector changes displayed count.
- Next/Previous buttons disable at list boundaries.
- Filter dropdown only shows allowlisted values.
- Clicking filter does not change URL (no router).
- No text input field for IDs or query strings.

---

## 14. Open Questions

These must be answered before implementing specific features.

| Question | Blocks |
|---|---|
| Does `report list --json` support `--offset`? | Offset pagination for Reports List |
| Does `audit list --json` support `--offset`? | Offset pagination for Audit Events List |
| What are the valid `--type` values for `audit list`? | Audit event type filter allowlist |
| Does `report list --json` support `--type` values beyond `sandbox_result`? | Report type filter allowlist |
| Is there a max-limit above 50 the CLI would accept safely? | Potential future limit expansion |
| Does CLI return a pagination token or total count in the list response? | Frontend prev/next UX |
| Should sandbox result list ever expose a type selector, or remain fixed `sandbox_result`? | Sandbox list filter design |
| What is the expected behavior when `--offset` exceeds total record count? | Empty vs error treatment |

---

## 15. Handoff Checklist

Before implementing any pagination or filtering control, confirm:

- [ ] This document committed and accepted
- [ ] CLI `--offset` support confirmed by live test for each affected command
- [ ] Allowlisted filter values confirmed from CLI docs and `eval_cases.yaml`
- [ ] `validate_limit` helper written and unit tested
- [ ] `validate_offset` helper written and unit tested
- [ ] `validate_report_type` helper written and unit tested (if report type filter planned)
- [ ] First paginated Rust command (`list_reports_page`) written with validation
- [ ] No frontend text input for IDs confirmed
- [ ] No arbitrary argv passthrough confirmed
- [ ] `run_policy_scout_json` still called with Rust-owned `&[&str]` only
- [ ] Loading / empty / error / boundary states handled in new card variant
- [ ] No new mutation, migration, or execution UI introduced alongside pagination

---

*Status: Pending acceptance. No implementation until this document is committed and
the open questions are resolved.*

*Track: Policy Scout v0.2.x Tauri read-only UI*
*Created: v0.2.27 pass*
