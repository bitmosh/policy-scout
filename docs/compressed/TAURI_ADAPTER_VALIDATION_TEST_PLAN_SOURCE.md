# Policy Scout — Tauri Adapter Validation Test Plan v0

## 1. Purpose

Capture the current Rust-side validation layer for Tauri adapter inputs, define the correct
invalid-input behavior, and specify the recommended future test strategy.

This document does not implement tests. It records what has been built, what the security
boundaries are, and what tests should be added when testing infrastructure is ready.

Related docs:
- `docs/compressed/TAURI_ADAPTER_BOUNDARY_SOURCE.md` — original adapter boundary spec
- `docs/compressed/TAURI_PAGINATION_CLI_CAPABILITY_AUDIT_SOURCE.md` — CLI pagination capability audit
- `docs/compressed/TAURI_PAGINATION_FILTERING_BOUNDARY_SOURCE.md` — filtering boundary plan
- `docs/TESTING_STRATEGY.md` — overall Policy Scout testing doctrine
- `docs/IMPLEMENTATION_STATUS.md` — current UI/integration implementation status

---

## 2. Current Validated Adapter Inputs

The Tauri adapter currently validates six categories of input before any CLI call is made.

### 2.1 Report limit (`validate_limit`)

- **Input type:** `u32`
- **Allowlist:** `5`, `10`, `25`, `50`
- **Used by:** `list_reports_filtered`
- **Source:** `lib.rs` `validate_limit`

### 2.2 Report type (`validate_report_type`)

- **Input type:** `Option<String>` (skipped if None or empty)
- **Allowlist:**
  - `command_decision`
  - `sandbox_result`
  - `project_sweep`
  - `system_quick_sweep`
- **Used by:** `list_reports_filtered`
- **Source:** `lib.rs` `validate_report_type`

### 2.3 Audit event type (`validate_audit_event_type`)

- **Input type:** `Option<String>` (skipped if None, empty, or `"all"`)
- **Allowlist (12 values):**
  - `SweepCompleted`
  - `SweepError`
  - `SandboxInstallCompleted`
  - `SandboxInstallStarted`
  - `SandboxResultWritten`
  - `ScoutReportGenerated`
  - `CommandExecutionCompleted`
  - `CommandExecutionBlocked`
  - `ApprovalRequested`
  - `ApprovalApprovedOnce`
  - `ApprovalDeniedOnce`
  - `DecisionIssued`
- **Used by:** `list_audit_events_filtered`
- **Source:** `lib.rs` `validate_audit_event_type`

### 2.4 Cleanup target (`validate_cleanup_target`)

- **Input type:** `String` (required)
- **Allowlist:**
  - `demo`
  - `sandbox`
  - `sandbox-results`
- **Used by:** `get_cleanup_dry_run`
- **Source:** `lib.rs` `validate_cleanup_target`
- **Additional constraint:** `--dry-run` is always appended by Rust; no non-dry-run path exists

### 2.5 Report ID (`validate_report_id`)

- **Input type:** `String`
- **Rules:**
  - Must not be empty
  - Must start with `report_`
  - Must not contain: ` / \ \t \n \r ; & | $ \` ( ) < >`
- **Used by:** `show_report`, `show_sandbox_result`
- **Source:** `lib.rs` `validate_report_id`

### 2.6 Audit event ID (inline in `show_audit_event`)

- **Input type:** `String`
- **Rules:**
  - Must not be empty
  - Must start with `evt_`
  - Must not contain: ` / \ \t \n \r ; & | $ \` ( ) < >`
- **Used by:** `show_audit_event`
- **Source:** `lib.rs` `show_audit_event`

---

## 3. Active Allowlists (Summary Reference)

| Validator | Type | Values |
|---|---|---|
| `validate_limit` | u32 set | 5, 10, 25, 50 |
| `validate_report_type` | string set | command_decision, sandbox_result, project_sweep, system_quick_sweep |
| `validate_audit_event_type` | string set | 12 values (see §2.3) |
| `validate_cleanup_target` | string set | demo, sandbox, sandbox-results |
| `validate_report_id` | prefix + metachar | starts with `report_`, no shell chars |
| `show_audit_event` (inline) | prefix + metachar | starts with `evt_`, no shell chars |

---

## 4. Invalid Input Behavior

All validators follow this contract:

1. **Return early** — the CLI subprocess is never called.
2. **Return `CliJsonResponse { ok: false, exit_code: -1, data: None, error: Some("...") }`**.
3. **Error message** includes the invalid value and a human-readable description of the constraint.
4. **No side effects** — no file writes, no subprocess spawning, no state mutation.

The error response is structurally identical to a failed CLI response. The frontend handles
it the same way as any `ok=false` result: shows error state, does not crash.

No validator throws a panic or returns an unstructured error.

---

## 5. Frontend Selector Constraints

Frontend selectors (React `<select>` elements) currently constrain user choices to allowlisted
values at the UI level. This is convenience, not a security boundary.

**Selectors that exist:**

| Component | Selector options |
|---|---|
| `ReportsListCard` | Limit: 5/10/25/50; Type: All/command_decision/sandbox_result/project_sweep/system_quick_sweep |
| `AuditEventsListCard` | Type: All recent events + 12 audit event types |
| `CleanupDryRunCard` | Target: Demo data / Sandbox workspaces / Sandbox results |

**What selectors do:**
- Prevent accidental UI bypass of valid inputs
- Surface allowlisted options as labeled strings
- Disable while loading to prevent double-submit

**What selectors do not do:**
- Selectors are not the security boundary
- A modified or injected frontend could call invoke with any string
- Rust validation must remain the final gatekeeper for all controlled inputs

TypeScript union types (`ReportTypeFilter`, `AuditEventTypeFilter`, `CleanupTarget`) mirror the
Rust allowlists. They add compile-time type safety but are a build-time check only.

---

## 6. Rust Adapter Responsibilities

The Rust adapter (`src-tauri/src/lib.rs`) is responsible for:

1. **Owning allowlist validation** — no unvalidated string from the frontend reaches CLI argv
2. **Constructing CLI argv** — the adapter builds the exact arg slice; the frontend never provides argv
3. **Hardcoding safe flags** — `--dry-run`, `--json`, `--limit <validated>` are set by Rust
4. **Returning structured errors** — invalid inputs produce `ok=false` responses, not panics
5. **No shell passthrough** — the adapter calls `policy-scout` via `std::process::Command`, not a shell
6. **No direct SQLite/filesystem reads** — all data goes through CLI JSON output

The adapter does not:
- Evaluate policy decisions
- Write audit events (that is the CLI's responsibility)
- Mutate any local state
- Accept arbitrary argv arrays from the frontend

---

## 7. CLI Responsibilities

The Policy Scout CLI remains the authority for:

- Data retrieval and formatting
- Audit writing
- Policy decisions
- Report generation
- Sweep execution
- Sandbox management
- Doctor health checks

The Tauri adapter does not replicate CLI logic. It calls CLI commands and passes JSON output
to the frontend unchanged.

CLI JSON contract tests in `tests/test_json_contracts.py` cover CLI behavior independently.
Those tests do not need to be replicated through Tauri.

---

## 8. What Must Never Be Accepted From Frontend

The following inputs must **never** be accepted from the frontend and passed to CLI argv:

| Forbidden | Reason |
|---|---|
| Arbitrary argv arrays | Enables injection of unallowlisted flags or commands |
| Free-text event type strings | Would bypass `validate_audit_event_type` |
| Free-text cleanup target strings | Would bypass `validate_cleanup_target`; could reach non-dry-run path if `--dry-run` were ever omitted |
| Free-text report type strings | Would bypass `validate_report_type` |
| Arbitrary limit integers | Would allow `--limit 0` or very large values |
| Shell metacharacters in IDs | Would enable shell injection in `report show` or `audit show` |
| Approval IDs or approval actions | Approvals are not a UI concern in v0.2.x |
| Sandbox migration arguments | Migration is not a UI concern in v0.2.x |
| Non-dry-run cleanup flags | No real deletion path may be reachable from the UI |
| Direct SQLite paths or queries | All data goes through CLI JSON |

**Current enforcement:** All of the above are enforced by the Rust validation layer. The
frontend does not have the ability to supply argv arrays or call CLI directly.

---

## 9. Current Wrapper Inventory Summary

**Total wrappers after cleanup consolidation pass: 13**

| Wrapper | CLI Command | Validation |
|---|---|---|
| `get_doctor_status` | `doctor --json` | none (no user input) |
| `get_data_status` | `data status --json` | none |
| `get_audit_stats` | `audit stats --json` | none |
| `get_cleanup_dry_run(target)` | `data cleanup --target <t> --dry-run --json` | `validate_cleanup_target` |
| `run_eval` | `eval run --json` | none |
| `run_sweep_quick` | `sweep quick --json` | none |
| `run_sweep_project` | `sweep project --json` | none |
| `list_sandbox_results` | `report list --json --type sandbox_result --limit 5` | none (hardcoded) |
| `list_reports_filtered(limit, type?)` | `report list --json --limit <n> [--type <t>]` | `validate_limit` + `validate_report_type` |
| `show_report(report_id)` | `report show <id> --json` | `validate_report_id` |
| `show_sandbox_result(report_id)` | `report show <id> --json` | `validate_report_id` |
| `list_audit_events_filtered(event_type?)` | `audit list --json --limit 10` or `audit type --json <t>` | `validate_audit_event_type` |
| `show_audit_event(event_id)` | `audit show <id> --json` | inline prefix + metachar check |

Wrappers with no user input (get_doctor_status, get_data_status, etc.) require no validation
because they call hardcoded CLI commands with no variable argv.

---

## 10. Test Strategy Overview

### Coverage layers

```
Rust validation helpers  ← unit-level: small, deterministic, no I/O
Tauri commands           ← integration-level: require Tauri test harness or native binary
TypeScript types         ← compile-time only: covered by `npm run build` or `tsc`
Frontend selectors       ← component-level: not yet covered; would require a test framework
CLI JSON contracts       ← already covered by tests/test_json_contracts.py
Manual native smoke      ← manual; run via `npm run tauri dev`
```

### Priority

1. Rust validation helpers — highest value, easiest to add, no external dependencies
2. TypeScript compile safety — free check via `npm run build`
3. CLI JSON contracts — already done, do not duplicate
4. Manual native smoke — document and run at checkpoints
5. Frontend component tests — lowest priority in v0.2.x; defer unless test framework added

---

## 11. Recommended Rust Tests

These tests do not exist yet. Add them to `src-tauri/src/lib.rs` or a separate test file when ready.

### `validate_limit`

```rust
// acceptance
assert!(validate_limit(5).is_ok());
assert!(validate_limit(10).is_ok());
assert!(validate_limit(25).is_ok());
assert!(validate_limit(50).is_ok());

// rejection
assert!(validate_limit(0).is_err());
assert!(validate_limit(1).is_err());
assert!(validate_limit(100).is_err());
assert!(validate_limit(u32::MAX).is_err());
```

### `validate_report_type`

```rust
// acceptance
assert!(validate_report_type("command_decision").is_ok());
assert!(validate_report_type("sandbox_result").is_ok());
assert!(validate_report_type("project_sweep").is_ok());
assert!(validate_report_type("system_quick_sweep").is_ok());

// rejection
assert!(validate_report_type("").is_err());
assert!(validate_report_type("all").is_err());
assert!(validate_report_type("CommandDecision").is_err()); // case mismatch
assert!(validate_report_type("../../etc/passwd").is_err());
assert!(validate_report_type("command_decision; rm -rf /").is_err());
```

### `validate_audit_event_type`

```rust
// acceptance — all 12 values
for t in ["SweepCompleted", "SweepError", "SandboxInstallCompleted",
          "SandboxInstallStarted", "SandboxResultWritten", "ScoutReportGenerated",
          "CommandExecutionCompleted", "CommandExecutionBlocked",
          "ApprovalRequested", "ApprovalApprovedOnce", "ApprovalDeniedOnce",
          "DecisionIssued"] {
    assert!(validate_audit_event_type(t).is_ok(), "should accept: {}", t);
}

// rejection
assert!(validate_audit_event_type("all").is_err());
assert!(validate_audit_event_type("").is_err());
assert!(validate_audit_event_type("sweepcompleted").is_err()); // case mismatch
assert!(validate_audit_event_type("SweepCompleted; ls").is_err());
assert!(validate_audit_event_type("unknown_type").is_err());
```

### `validate_cleanup_target`

```rust
// acceptance
assert!(validate_cleanup_target("demo").is_ok());
assert!(validate_cleanup_target("sandbox").is_ok());
assert!(validate_cleanup_target("sandbox-results").is_ok());

// rejection
assert!(validate_cleanup_target("").is_err());
assert!(validate_cleanup_target("all").is_err());
assert!(validate_cleanup_target("Demo").is_err()); // case mismatch
assert!(validate_cleanup_target("sandbox-results; rm -rf /").is_err());
assert!(validate_cleanup_target("../../local").is_err());
```

### `validate_report_id`

```rust
// acceptance
assert!(validate_report_id("report_abc123").is_ok());
assert!(validate_report_id("report_20260607_160025").is_ok());

// rejection — empty
assert!(validate_report_id("").is_err());

// rejection — wrong prefix
assert!(validate_report_id("evt_abc").is_err());
assert!(validate_report_id("abc123").is_err());

// rejection — shell metacharacters
for bad in ["report_a/b", "report_ x", "report_a;b", "report_a|b",
            "report_a&b", "report_a$b", "report_a`b"] {
    assert!(validate_report_id(bad).is_err(), "should reject: {}", bad);
}
```

### `validate_audit_event_id`

```rust
// acceptance
assert!(validate_audit_event_id("evt_abc123").is_ok());

// rejection — wrong prefix
assert!(validate_audit_event_id("report_abc").is_err());
assert!(validate_audit_event_id("abc123").is_err());
assert!(validate_audit_event_id("").is_err());

// rejection — shell metacharacters
for bad in ["evt_a/b", "evt_ x", "evt_a;b", "evt_a|b", "evt_a&b"] {
    assert!(validate_audit_event_id(bad).is_err(), "should reject: {}", bad);
}
```

Note: `validate_audit_event_id` is now a named helper (extracted in v0.2.37). Unit tests
can be added without further refactoring (see §15 hardening sequence — step 1 completed).

### Error response contract

For each validator, also assert the error shape:

```rust
let e = validate_limit(99).unwrap_err();
assert!(!e.ok);
assert_eq!(e.exit_code, -1);
assert!(e.data.is_none());
assert!(e.error.is_some());
assert!(e.stderr_summary.is_none());
```

---

## 12. Recommended Frontend / Type Tests

### TypeScript compile safety (already active)

`npm run build` and `tsc` will catch type mismatches if a value outside the union is passed
to a selector handler. This is the current coverage.

Union types that mirror Rust allowlists:

```typescript
type ReportTypeFilter = "" | "command_decision" | "sandbox_result" | "project_sweep" | "system_quick_sweep";
type AuditEventTypeFilter = AuditEventType | "all";  // AuditEventType has 12 values
type CleanupTarget = "demo" | "sandbox" | "sandbox-results";
```

These types will cause a compile error if a value outside the union is passed to a handler.

### Component tests (deferred)

If Vitest or React Testing Library is added to the project, consider:

- Render `CleanupDryRunCard` and assert selector contains exactly 3 options
- Render `AuditEventsListCard` and assert selector contains exactly 13 options (12 types + "all")
- Render `ReportsListCard` and assert limit selector contains exactly 4 options
- Assert no free-text `<input>` elements exist in these cards

Do not add a test framework solely for these checks. Do them if the framework is already present.

---

## 13. Recommended Integration / Manual Checks

### Manual native smoke (run with `npm run tauri dev`)

Run these checks at significant Tauri checkpoints:

```
Cleanup card:
[ ] Selector shows: Demo data / Sandbox workspaces / Sandbox results
[ ] Selecting each refreshes the dry-run result
[ ] No delete/apply/execute button visible
[ ] Card header shows "DRY RUN ONLY" notice

Audit events card:
[ ] Selector shows "All recent events" + 12 event type options
[ ] Selecting a type refreshes the list
[ ] Changing type clears open event detail

Reports list card:
[ ] Limit selector shows 5/10/25/50 only
[ ] Type selector shows All + 4 named types
[ ] Changing either refreshes the list

ID detail flows:
[ ] Clicking a report ID opens the report detail
[ ] Clicking an audit event ID opens the event detail
[ ] Invalid IDs (if reachable) return error state, not crash

Global:
[ ] Page loads without Tauri runtime shows boundary note / error message
[ ] No free-text input fields exist in any selector control
```

### CLI contract smoke (already automated)

`tests/test_json_contracts.py` covers CLI JSON shapes independently. These do not need to be
re-run through Tauri. The CLI tests are the source of truth for data correctness.

---

## 14. Out-of-Scope Items

The following are explicitly not in scope for Tauri adapter testing:

| Item | Reason |
|---|---|
| CLI command correctness | Covered by `tests/test_json_contracts.py` and CLI unit tests |
| Policy engine behavior | Core Policy Scout, not Tauri adapter |
| Audit write correctness | CLI responsibility, not UI |
| Sandbox execution | Deferred from UI scope in v0.2.x |
| Approval resolution | Not a UI concern in v0.2.x |
| Non-dry-run cleanup | Explicitly forbidden from Tauri surface |
| Network/remote calls | Not in v0.2.x scope |
| Any CRUD via Tauri | UI is read-only; no writes through adapter |
| Test framework selection | Deferred until build system decision is made |

---

## 15. Future Hardening Sequence

1. ✅ **Extract `validate_audit_event_id` helper** from `show_audit_event` inline validation.
   Completed in v0.2.37. Function is now unit-testable at the same level as other validators.

2. ✅ **Add Rust `#[cfg(test)]` module** to `lib.rs` with unit tests for all six validators.
   Completed in v0.2.39. 12 tests added, all pass. No new dependencies required.

   **Test readiness (verified v0.2.38):** `cargo test` already ran cleanly in `src-tauri`
   with 0 tests. Crate type includes `rlib`. `#[cfg(test)]` module in `lib.rs` compiled
   and ran without any additional setup.

3. **Add minimal frontend component tests** only if Vitest or another test framework is
   already introduced for another reason. Do not add a test framework solely for selector tests.

4. **Create native smoke checklist** document and run it at each Tauri release checkpoint.
   The checklist in §13 is the starting point.

5. **Revisit CLI-side `audit type` validation** — the CLI currently accepts any string as the
   audit event type argument. If the UI allowlist and the CLI allowlist diverge in a future pass,
   consider whether CLI-side validation should be tightened or whether the Rust layer is
   sufficient as the UI boundary.

6. **Extract shared allowlist constants** if the same values appear in both Rust and TypeScript
   and begin to drift. A source-of-truth registry (YAML or JSON) could drive both, but only
   if duplication becomes a maintenance problem.

---

## 16. Acceptance Checklist

Use this checklist to confirm the adapter validation layer is complete and correctly specified.

### Allowlists

- [x] Report limit allowlist: `5, 10, 25, 50` — implemented in `validate_limit`
- [x] Report type allowlist: 4 values — implemented in `validate_report_type`
- [x] Audit event type allowlist: 12 values — implemented in `validate_audit_event_type`
- [x] Cleanup target allowlist: 3 values — implemented in `validate_cleanup_target`
- [x] Report ID prefix + metachar check — implemented in `validate_report_id`
- [x] Audit event ID prefix + metachar check — implemented in `validate_audit_event_id`

### Invalid input behavior

- [x] All validators return `ok=false` on invalid input
- [x] No CLI call is made on invalid input
- [x] Error response shape matches `CliJsonResponse` struct
- [x] No panic, no unstructured error

### Security boundaries

- [x] No arbitrary argv arrays accepted from frontend
- [x] No shell plugin used
- [x] No direct SQLite or filesystem reads
- [x] `--dry-run` hardcoded for `get_cleanup_dry_run`; no real deletion path
- [x] No command execution, approval resolution, sandbox migration, or non-dry-run cleanup UI

### Wrapper count

- [x] Current wrapper count: 13 (verified against `lib.rs` `generate_handler!`)

### Frontend mirrors

- [x] `ReportTypeFilter` TypeScript union mirrors `validate_report_type` allowlist
- [x] `AuditEventTypeFilter` TypeScript union mirrors `validate_audit_event_type` allowlist
- [x] `CleanupTarget` TypeScript union mirrors `validate_cleanup_target` allowlist
- [x] Selectors in components constrain to allowlisted options only

### Tests

- [x] Rust unit tests for `validate_limit` — **done** (v0.2.39)
- [x] Rust unit tests for `validate_report_type` — **done** (v0.2.39)
- [x] Rust unit tests for `validate_audit_event_type` — **done** (v0.2.39)
- [x] Rust unit tests for `validate_cleanup_target` — **done** (v0.2.39)
- [x] Rust unit tests for `validate_report_id` — **done** (v0.2.39)
- [x] `validate_audit_event_id` extracted — **done** (v0.2.37)
- [x] Unit tests for `validate_audit_event_id` — **done** (v0.2.39)
- [ ] Native smoke checklist run — **pending** (see §13)
- [x] TypeScript compile check via `npm run build` — active
- [x] CLI JSON contract tests via `pytest tests/test_json_contracts.py` — active
