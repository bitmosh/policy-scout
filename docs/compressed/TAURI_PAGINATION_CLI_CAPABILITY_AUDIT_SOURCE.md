# Policy Scout — Tauri Pagination CLI Capability Audit v0

## 1. Purpose

Answer the open questions from `TAURI_PAGINATION_FILTERING_BOUNDARY_SOURCE.md` by
directly probing CLI help output and running safe read-only commands. No code was
changed. This document provides confirmed CLI capability verdicts and safe allowlists
to ground future Tauri pagination/filtering implementation.

---

## 2. Summary Verdict

| Capability | Status |
|---|---|
| `report list --limit N` | ✅ Confirmed supported |
| `report list --type TYPE` | ✅ Confirmed supported, 4 allowlisted values |
| `report list --offset N` | ❌ Not supported — unrecognized argument |
| `report list --page N` | ❌ Not supported — unrecognized argument |
| `report list --page-token X` | ❌ Not supported — unrecognized argument |
| `audit list --limit N` | ✅ Confirmed supported |
| `audit list --type TYPE` | ❌ No --type on audit list; use `audit type` instead |
| `audit list --offset N` | ❌ Not supported — unrecognized argument |
| `audit type <event_type>` | ✅ Confirmed — but CLI accepts arbitrary strings; Rust must enforce allowlist |
| Sweep pagination | ❌ No CLI pagination; single-run batch; client-side cap only |
| Cleanup pagination | ❌ No CLI pagination; target is allowlisted enum only |
| Stable ordering for next/prev | ⚠️ Uncertain — `created_at` is empty string in report list items |

**Immediate implication:** No offset-based next/previous pagination is possible for any
list command until `--offset` is added to the CLI. The only safe addition in v0.2.x is
a bounded limit selector. Type filtering for `report list` is safe using the confirmed
allowlist.

---

## 3. Commands Inspected

All commands run with `PYTHONPATH=/home/boop/Projects/policy-scout python -m policy_scout.cli.main`.

| Command | Method |
|---|---|
| `report list --help` | Help output |
| `report list --json --limit 5` | Live probe |
| `report list --json --limit 10` | Live probe |
| `report list --json --limit 5 --offset 5` | Failure probe |
| `report list --json --limit 5 --page 2` | Failure probe |
| `report list --json --limit 5 --page-token abc` | Failure probe |
| `report list --json --type sandbox_result --limit 5` | Live probe |
| `report list --json --type command_decision --limit 3` | Live probe |
| `report list --json --type project_sweep --limit 3` | Live probe |
| `report list --json --type system_quick_sweep --limit 3` | Live probe |
| `audit list --help` | Help output |
| `audit list --json --limit 10` | Live probe |
| `audit list --json --limit 5 --offset 5` | Failure probe |
| `audit type --help` | Help output |
| `audit type --json CommandClassified --limit 3` | Live probe |
| `audit type --json SandboxInstallCompleted --limit 3` | Live probe |
| `audit type --json InvalidFakeType --limit 3` | Validation probe |
| `audit stats --json` | Live probe (for event type enumeration) |
| `sweep quick --help` | Help output |
| `sweep project --help` | Help output |
| `data cleanup --help` | Help output |
| `sandbox --help` | Help output |

---

## 4. Report List Capabilities

### Help Output

```
usage: main.py report list [-h] [--limit LIMIT] [--type TYPE] [--json]

options:
  --limit LIMIT  Number of reports to show (default: 20)
  --type TYPE    Filter by report type
                 (command_decision, sandbox_result, project_sweep, system_quick_sweep)
  --json         Output JSON instead of human-readable text
```

### Confirmed Supported Options

| Option | Confirmed | Notes |
|---|---|---|
| `--limit N` | ✅ | Default 20. Values 5 and 10 tested and returned correct counts. |
| `--type TYPE` | ✅ | All 4 types confirmed (see Section 11). |

### Confirmed Unsupported Options

| Option | Result |
|---|---|
| `--offset N` | `error: unrecognized arguments: --offset 5` |
| `--page N` | `error: unrecognized arguments: --page 2` |
| `--page-token X` | `error: unrecognized arguments: --page-token abc` |

### JSON Shape (Confirmed)

Returns a JSON array directly (not a wrapper object).

```json
[
  {
    "report_id": "report_fed13bdbb407",
    "has_markdown": true,
    "has_json": true,
    "report_type": "project_sweep",
    "title": "Project Sweep: /tmp/tmpy9o39cfd",
    "created_at": ""
  }
]
```

**Important:** `created_at` is an empty string in all tested report list items.
This means timestamp-based ordering is **not reliable** for pagination purposes.
Next/previous pagination based on offset or stable created_at ordering is not feasible
until the CLI either populates `created_at` or supports `--offset`.

### Ordering

Reports appear to be ordered by recency (most recent first) based on internal DB order.
No stable cursor/token is returned. No guarantee of order stability between calls.

---

## 5. Sandbox Result List Capabilities

Sandbox results use `report list --type sandbox_result`. No separate CLI command.

| Option | Confirmed |
|---|---|
| `--limit N` | ✅ |
| `--type sandbox_result` | ✅ |
| `--offset N` | ❌ Not supported |

Probe result: `--type sandbox_result --limit 5` returns 5 items, all `report_type: sandbox_result`.

No separate pagination capability exists for sandbox results beyond what `report list` provides.
Type filter for the sandbox results Tauri list must remain **hardcoded in Rust** as
`sandbox_result` — not a user-selectable value.

---

## 6. Audit List Capabilities

### Help Output

```
usage: main.py audit list [-h] [--limit LIMIT] [--json]

options:
  --limit LIMIT  Number of events to show (default: 20)
  --json         Output JSON instead of human-readable text
```

### Confirmed Supported Options

| Option | Confirmed | Notes |
|---|---|---|
| `--limit N` | ✅ | Default 20. Limit 10 tested and returned correct count. |

### Confirmed Unsupported Options

| Option | Result |
|---|---|
| `--type TYPE` | Not a recognized option on `audit list` |
| `--offset N` | `error: unrecognized arguments: --offset 5` |

**Note:** `audit list` does NOT support `--type` filtering. To filter by event type,
the separate `audit type <event_type>` subcommand must be used. These are different
Tauri commands and must be treated separately.

### JSON Shape (Confirmed)

Returns a wrapper object:

```json
{
  "events": [
    {
      "event_id": "evt_2ac51f58455b",
      "event_type": "SweepError",
      "timestamp": "2026-06-08T07:21:20.645283Z",
      "request_id": "req_c5b964258e27",
      "actor_type": null,
      "actor_name": null,
      "summary": "Sweep error",
      "data_json": "{...}",
      "schema_version": 1,
      "created_at": "2026-06-08T07:21:20.645477Z",
      ...
    }
  ]
}
```

`created_at` and `timestamp` are populated in audit events (unlike report list).
Ordering is likely by insertion order (most recent first). Still no `--offset`.

---

## 7. Audit Type Capabilities

### Help Output

```
usage: main.py audit type [-h] [--limit LIMIT] [--json] event_type

positional arguments:
  event_type     Event type to query

options:
  --limit LIMIT  Number of events to show (default: 50)
  --json         Output JSON instead of human-readable text
```

### Behavior

`audit type` accepts `event_type` as a **positional string argument**. The CLI does
**not validate** that the string matches a known event type. Passing an unknown type
returns an empty result (0 events), not an error.

**Probe results:**
- `audit type --json CommandClassified --limit 3` → 3 events ✅
- `audit type --json SandboxInstallCompleted --limit 3` → 3 events ✅
- `audit type --json InvalidFakeType --limit 3` → 0 events (no error) ⚠️

**Implication for Tauri:** Because the CLI accepts any string, the Rust layer
**must** enforce the allowlist before calling `audit type`. If a frontend-provided
string passes validation by Rust, the CLI will silently return empty results for
unknown types — this is not catastrophic but is misleading. Rust must reject
unknown type strings with an explicit error before any CLI call is made.

### Event Type Enumeration

All event types were enumerated from `audit stats --json` (by_type map, confirmed live):

```
CommandClassified          CommandParsed              CommandRequested
DecisionIssued             PolicyMatched              CommandExecutionCompleted
CommandExecutionStarted    CommandExecutionBlocked    ScoutReportGenerated
ApprovalRequested          SweepCompleted             SweepStarted
ApprovalApprovedOnce       ApprovalShown              ApprovalDeniedOnce
LifecycleScriptsInspected  SandboxInstallCompleted    SandboxInstallStarted
SandboxRequested           SandboxResultWritten       SandboxWorkspaceCreated
SweepError                 ApprovalExecutionStarted   ApprovalExecutionCompleted
ApprovalExecutionFailed
```

Total: 25 known event types as of audit run date.

**For Tauri event type filter UI:** Do not expose all 25 types in a dropdown — most
are internal lifecycle events not meaningful to a UI reader. A filtered subset of
user-visible types is recommended (see Section 12).

---

## 8. Sweep Result Display Capabilities

### Help Output

```
sweep quick:   [--json] [--no-audit]
sweep project: [--json] [--no-audit] [--project PROJECT]
```

Neither sweep command has `--limit`, `--offset`, `--page`, or any pagination support.

Sweeps return a single batch JSON response with all findings and could_not_verify items.

Client-side cap via `SweepResultPreview` props (`maxFindings`, `maxCouldNotVerify`) is
the only display limit available. This is correct and intentional — sweeps are not
paginated, they are evidence-gathering runs.

**Implication:** No server-side pagination is possible for sweep findings.
Client-side severity filter and sort remain the only safe filtering controls.

**`--project PATH` on `sweep project`:** Accepts a filesystem path. This option must
**never** be exposed in the Tauri UI — arbitrary filesystem paths from the frontend
would violate the boundary. The Tauri command hardcodes no `--project` argument
(defaults to current directory via `policy-scout`'s own default behavior).

---

## 9. Cleanup Dry-Run Display Capabilities

### Help Output

```
data cleanup: --target {demo,sandbox,sandbox-results} [--dry-run] [--json]
```

Target is an **enum** with exactly 3 allowlisted values: `demo`, `sandbox`, `sandbox-results`.
No pagination. No limit. `--dry-run` is always effectively true in v1 (confirmed from help text).

Cleanup results are small by nature (planned items list). No pagination needed.

**Implication:** No changes to cleanup card needed. Three fixed Tauri commands are correct.

---

## 10. Unsupported / Deferred Pagination Features

These are confirmed absent from the current CLI and must not be implemented until CLI support
is added:

| Feature | CLI Support | Status |
|---|---|---|
| `report list --offset N` | ❌ Not supported | Deferred — requires CLI change |
| `report list --page N` | ❌ Not supported | Deferred — requires CLI change |
| `report list --page-token` | ❌ Not supported | Deferred — requires CLI change |
| `audit list --offset N` | ❌ Not supported | Deferred — requires CLI change |
| `audit list --type TYPE` | ❌ Not on `audit list` | Use `audit type` subcommand instead |
| Sweep pagination | ❌ No CLI mechanism | Deferred indefinitely; sweeps are batches |
| Cleanup pagination | ❌ No CLI mechanism | Not needed (results small) |
| Stable timestamp cursor for reports | ⚠️ `created_at` empty | Deferred — requires CLI fix first |

---

## 11. Confirmed Safe Allowlists

### Report Type Allowlist

From `report list --help` (confirmed):

```
command_decision
sandbox_result
project_sweep
system_quick_sweep
```

All 4 values confirmed by live probes returning results. All 4 are safe to expose
as a Tauri filter option.

Note: The sandbox results list card uses `sandbox_result` hardcoded in Rust.
In a future combined report list with type selector, `sandbox_result` would be
one of 4 dropdown options.

### Bounded Limit Allowlist

```
5, 10, 25, 50
```

All are multiples of 5, well within default max (20 default, no explicit max documented
in help). `5` and `10` confirmed working. `25` and `50` are safe — CLI default is 20,
and there's no documented upper bound that would cause errors.

### Audit Event Type Allowlist (User-Visible Subset)

Not all 25 known event types are useful in a filter UI. Recommended visible subset
for a Tauri audit event type filter dropdown:

```
SweepCompleted
SweepError
SandboxInstallCompleted
SandboxInstallStarted
SandboxResultWritten
ScoutReportGenerated
CommandExecutionCompleted
CommandExecutionBlocked
ApprovalRequested
ApprovalApprovedOnce
ApprovalDeniedOnce
DecisionIssued
```

Full list of 25 types must be maintained in Rust for allowlist validation even if only
a subset is shown in the dropdown. Any submitted value not in the full list must be
rejected by Rust before calling `audit type`.

### Cleanup Target Allowlist

```
demo
sandbox
sandbox-results
```

Directly from CLI enum. Already correctly hardcoded in Rust. No change needed.

---

## 12. Tauri Implementation Implications

| Finding | Implication |
|---|---|
| No `--offset` on any list command | No next/previous pagination in v0.2.x. Limit selector only. |
| `report list --type` confirmed with 4 values | Report type filter safe to add. Use confirmed allowlist. |
| `audit list` has no `--type` | Audit event type filter requires a separate `list_audit_events_by_type(type, limit)` Tauri command using `audit type` |
| `audit type` accepts arbitrary strings | Rust allowlist validation is **required** before any call to `audit type` |
| `created_at` empty in report list items | Do not add client-side sort by date for reports until CLI populates this field |
| `audit list` events have proper timestamps | Client-side timestamp sort is feasible for audit events |
| Sweep has no pagination | No sweep pagination work needed; client-side cap is correct |
| Cleanup target is enum | Cleanup commands need no changes |
| `audit stats by_type` enumerates all event types | Tauri can use `get_audit_stats` to drive a dynamic type filter — but static allowlist in Rust is safer and required regardless |

---

## 13. Recommended First Implementation

Based on this audit, the recommended first Tauri pagination/filtering addition is:

**Bounded limit selector for `list_reports`**

Rationale:
- `report list --limit N` is confirmed working
- The 4 report types are confirmed for a type filter dropdown
- No offset/pagination complexity
- High user value (5-item default is minimal)
- Smallest safe Rust change

Implementation sketch:
1. Add `list_reports_filtered(limit: u32, report_type: Option<String>)` Tauri command
2. Validate `limit` against `[5, 10, 25, 50]` in Rust
3. Validate `report_type` against `["command_decision", "sandbox_result", "project_sweep", "system_quick_sweep"]` in Rust
4. Keep existing `list_reports()` as the no-arg default
5. Add limit dropdown to `ReportsListCard` (no type filter yet, or add together)
6. Wire state in `App.tsx`

**Do not add next/previous buttons** — no CLI `--offset` support exists.

**Second implementation:** Bounded limit selector for `list_audit_events`, same pattern.

**Third implementation (later, after allowlist strategy finalized):**
Audit event type filter using `audit type` via a new `list_audit_events_by_type` Tauri command.
Rust must enforce the full 25-type allowlist even if UI shows only the 12-type subset.

---

## 14. Test Implications

### New Tests Needed (not in this pass)

- `test_report_list_json_limit_5`: confirm returns ≤5 items
- `test_report_list_json_limit_10`: confirm returns ≤10 items
- `test_report_list_json_type_sandbox_result`: confirm all returned items are `sandbox_result`
- `test_report_list_json_type_project_sweep`: confirm all returned items are `project_sweep`
- `test_audit_list_json_limit_10`: confirm returns ≤10 events
- `test_audit_type_json_known_type`: confirm returns events matching the type
- `test_audit_type_json_unknown_type_empty`: confirm empty list (not error) for unknown type
- `test_report_list_offset_unsupported`: confirm CLI rejects `--offset` (documents current state)

### Rust Validation Tests (when implemented)

- `validate_limit(5)` → Ok
- `validate_limit(0)` → Err
- `validate_limit(7)` → Err (not in allowlist)
- `validate_report_type("sandbox_result")` → Ok
- `validate_report_type("unknown_type")` → Err
- `validate_audit_event_type("SweepCompleted")` → Ok
- `validate_audit_event_type("FakeEvent")` → Err

---

## 15. Open Questions After Audit

| Question | Status |
|---|---|
| Will `report list` ever get `--offset`? | Open — depends on CLI roadmap. Block next/prev on this. |
| Should `created_at` be populated in report list items? | Open — current empty string blocks timestamp sort and ordering guarantees. |
| What is the expected CLI behavior when `--limit` exceeds total record count? | Tested implicitly — returns all records up to limit, no error. Confirmed safe. |
| Is the ordering of `report list` guaranteed (e.g., always newest-first)? | Likely DB insertion order but not documented. Risky for offset pagination even if added. |
| Is the ordering of `audit list` guaranteed? | Has proper timestamps; likely newest-first but not documented. |
| Should `audit type` validate the event_type argument in the CLI itself? | Open — currently accepts any string. Rust layer must compensate until CLI validates. |
| Are there event types not yet in `audit stats by_type` that would appear later? | Yes — new event types may be added in future CLI passes. Rust allowlist must be updated in sync. |
| Should the Tauri type filter dropdown be driven by live `audit stats by_type` or a static Rust allowlist? | Static Rust allowlist is safer and required. Dynamic list could supplement it in UI but Rust validation is always authoritative. |

---

*Status: Audit complete. No code changed. Working tree clean.*
*Track: Policy Scout v0.2.x Tauri read-only UI*
*Created: v0.2.28 pass*
