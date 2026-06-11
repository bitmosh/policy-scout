# ADR-006: Report and Data Lifecycle Management

**Status:** Accepted  
**Date:** 2026-06-10  
**Deciders:** Developer (bitmosh)  
**Related ADRs:** [ADR-002](ADR-002-policy-config-precedence.md) (retention config reads from the same config chain)

---

## Context

Reports, audit events, sandbox workspaces, and approval records accumulate indefinitely. There is no deletion path, no retention policy, and no filtering beyond `--limit`. The data cleanup command exists but is dry-run only.

The operational consequences for a developer using Policy Scout daily:
- `policy-scout report list` grows without bound; the 10-result default means old reports are invisible, not gone
- The SQLite audit database grows without a pruning path; at 18,000+ events (documented in IMPLEMENTATION_STATUS), query performance degrades without indexing
- Sandbox workspaces left over from interrupted installs are never cleaned up unless manually deleted
- There is no way to find "the report for that sandbox run last Thursday" without knowing the report ID

None of this matters at v0.1 alpha. It matters significantly by v0.5 when a developer has months of data. Fixing it later requires migrating existing records and working around undocumented invariants that will have accumulated. The right time to lock the contract is before the data volume becomes the problem.

---

## Forces

- **No accidental deletion.** A `report delete` command that doesn't confirm before deleting is a footgun. Audit events in particular should require explicit confirmation and be hard to delete accidentally.
- **Audit events have different deletion semantics from reports.** Reports are output — they're safe to delete (they can be regenerated). Audit events are the tamper-evident trail — deleting them silently would defeat the audit chain. Audit deletion needs a higher confirmation bar than report deletion.
- **Retention should be declarative.** A developer should be able to set `reports.max_age_days: 90` in config and not think about it again. The cleanup should run automatically at a predictable time (startup or explicit cleanup command), not require a cron job.
- **Filtering matters more than pagination for daily use.** Finding "all sweep reports from last week" is more common than needing page 3 of all reports. `--since`, `--type`, and `--before` filters on `report list` will cover 90% of use cases. Pagination (`--offset`) is secondary.
- **Safe defaults.** The default retention for audit events should be long (365 days) to preserve investigative value. The default for reports and sandbox workspaces should be shorter (90 days) since they're reconstructable. Both defaults should be explicit in the config schema.
- **Cross-reference integrity.** A report that references an audit event ID should not become silently dangling if the audit event is deleted. The deletion contract must define what happens to cross-references.

---

## Decision

### D1 — Data categories and their deletion semantics

Five data categories, each with different deletion rules:

| Category | Default retention | Deletable? | Confirmation required |
|---|---|---|---|
| Scout Reports | 90 days | yes | report ID + `--confirm` |
| Audit events | 365 days | yes, with restrictions | typed `"I understand"` phrase |
| Sandbox workspaces | 30 days (post-migration) | yes | `--confirm` |
| Approval records | 365 days | no (v1) | n/a |
| Migration backups | 90 days | yes | `--confirm` |

**Audit event deletion restriction:** Audit events may only be deleted via the retention cleanup path (time-based, bulk). Individual audit event deletion is not supported in v1. This prevents targeted log tampering while still enabling eventual disk reclamation. The restriction is documented prominently in `policy-scout audit delete --help` (which explains the batch-only path).

**Approval record deletion:** Approval records are not deletable in v1. An approval is a signed decision — deleting it would silently erase the record that a command was approved for execution. The value of the approval record outlives its operational use. Deferred to v2 with an archive-not-delete approach.

### D2 — Retention config schema

In `.policy-scout.yaml` or `~/.config/policy-scout/config.yaml`, under the existing config chain (ADR-002):

```yaml
retention:
  reports_max_age_days: 90           # 0 = keep forever
  audit_events_max_age_days: 365     # 0 = keep forever
  sandbox_workspaces_max_age_days: 30
  migration_backups_max_age_days: 90
  run_cleanup_on_startup: false      # if true, prune expired data on every startup
                                     # default false to avoid startup latency surprises
```

Retention config lives at Layer 2 (user global config) or Layer 3 (project override). Layer 3 may only tighten (shorter retention is stricter, so a project may set shorter retention but not longer than the global). This follows the tighten-only semantics from ADR-002.

`0` means "keep forever" and is the behavior when no config exists (backward compatibility — existing installs don't lose data on upgrade).

### D3 — Report deletion command

```bash
policy-scout report delete <report_id>
policy-scout report delete <report_id> --confirm
policy-scout report delete --before <date> --type <type> --confirm   # bulk delete
policy-scout report delete --older-than <days> --confirm             # by age
```

Without `--confirm`, `delete` prints a preview of what would be deleted and exits with code 0. With `--confirm`, it deletes and writes a `ReportDeleted` audit event for each report removed.

The `ReportDeleted` audit event records: `report_id`, `report_type`, `created_at`, `deleted_at`, `reason` (retention/manual). It does **not** record report content. Once deleted, the report content is gone.

Cross-reference behavior: if a deleted report was referenced by an audit event, the audit event is not modified. The `report_id` in the audit event becomes a dangling reference. `policy-scout report show <id>` on a deleted report returns a structured error: `{"error": "report_not_found", "report_id": "...", "note": "Report was deleted"}`. This is preferable to silently returning empty data.

### D4 — Filtering on `report list` and `audit list`

```bash
# report list additions
policy-scout report list --type sweep_result --since 2026-06-01 --before 2026-06-10
policy-scout report list --limit 20 --offset 40   # pagination
policy-scout report list --json                   # already exists; must include total_count

# audit list additions  
policy-scout audit list --since 2026-06-01 --event-type DecisionIssued --limit 50
policy-scout audit list --request-id req_abc123   # group by request (already: audit request)
```

`--since` and `--before` accept ISO dates (`2026-06-01`) or relative values (`7d`, `30d`). Relative values are resolved against the current timestamp at invocation time, not stored.

JSON output for `report list` gains a `total_count` field representing the total number of matching reports (before `--limit` is applied). This enables pagination without multiple queries:

```json
{
  "reports": [...],
  "total_count": 142,
  "limit": 20,
  "offset": 0
}
```

### D5 — Cleanup command completion

`policy-scout data cleanup` currently runs dry-run only. The deletion path is unlocked in this ADR:

```bash
policy-scout data cleanup --dry-run          # existing behavior; no change
policy-scout data cleanup --target reports --older-than 90d --confirm
policy-scout data cleanup --target sandbox --older-than 30d --confirm
policy-scout data cleanup --target all --confirm    # applies per-category retention config
```

`--target all` applies the retention config values (D2). It is the "run retention policy now" command. When `run_cleanup_on_startup: true` is set, this is what runs at startup.

Each cleanup run writes a `DataCleanupCompleted` audit event with counts by category (reports_deleted, sandbox_workspaces_deleted, etc.) but not the deleted IDs (to keep the event small).

### D6 — Startup cleanup

When `run_cleanup_on_startup: true`:
- Cleanup runs asynchronously in the background on every CLI invocation
- It does not block the primary command
- It does not produce stdout output (progress goes to the audit event only)
- Failures are logged as `DataCleanupFailed` audit events and do not affect the primary command

The background execution uses `subprocess.Popen` with `nohup` so it survives the parent process exiting. This is simpler than a thread and avoids cleanup affecting CLI exit codes.

---

## Consequences

### Positive
- Reports and workspaces stop accumulating without bound for active users
- `--since`/`--before`/`--type` filters make finding specific reports practical
- `total_count` in JSON output enables the Tauri UI to show pagination controls without an additional query
- Deletion is auditable — `ReportDeleted` events are written, so you can tell when a report was deleted even after it's gone

### Negative / Risks
- The dry-run-only cleanup in the Tauri UI (currently exposed as a safe preview) must not be confused with the new actual-deletion path. The Tauri cleanup adapter must remain dry-run-only; the actual deletion path is CLI-only. This is a safety boundary that must be preserved in the Rust adapter allowlist.
- `run_cleanup_on_startup: true` with a short retention window could delete data a developer still needs. The default is `false` exactly to prevent this. The user must opt in explicitly.
- Dangling report references in audit events (D3) are a mild consistency gap. The `report_not_found` error is acceptable but could confuse tooling that assumes `report_id` in an audit event is always resolvable. Document this in the audit event schema.

---

## Blast Radius

| File | Change |
|---|---|
| `audit/sqlite_store.py` | modified — `delete_before(timestamp)`, `list_with_filters()` |
| `audit/events.py` | modified — `ReportDeleted`, `DataCleanupCompleted`, `DataCleanupFailed` |
| `reports/store.py` (new or existing) | modified/new — `delete_report()`, `list_with_filters()` |
| `data_cleanup.py` | modified — unlock actual deletion behind `--confirm` |
| `data_status.py` | modified — include `oldest_report_age_days`, `oldest_audit_age_days` |
| `cli/main.py` | modified — `report delete`, `report list` filter flags, `data cleanup` flags |
| `policy_scout/core/retention.py` | new — retention config reader, cleanup orchestrator |
| `data/default_policy.yaml` (or config) | no change — retention config is separate from policy |
| `tests/test_cli_reports.py` | modified — deletion, filtering tests |
| `tests/test_cli_data.py` | modified — cleanup with --confirm tests |
| `ui/desktop/src-tauri/src/lib.rs` | modified — `list_reports_filtered` passes new filter params; cleanup adapter remains dry-run |

---

## Implementation Phases

### Phase 1 — Filtering on list commands
- `--since`, `--before`, `--type`, `--limit`, `--offset` on `report list`
- `--since`, `--before`, `--event-type`, `--limit` on `audit list`
- `total_count` in JSON output for both
- SQLite query updates in `sqlite_store.py`

**STOP gate:** `report list --since 2026-01-01 --type sweep_result --json` returns correct results with `total_count`.

### Phase 2 — Retention config
- Add `retention:` block to config schema (ADR-002 config chain)
- `data_status.py` shows retention config alongside data counts
- `policy-scout doctor` warns if no retention config is set (informational, not error)

**STOP gate:** `policy-scout data status --json` includes retention config values.

### Phase 3 — Report deletion
- `policy-scout report delete <id> --confirm`
- `policy-scout report delete --before <date> --confirm`
- `ReportDeleted` audit event
- `report_not_found` structured error on `report show` for deleted reports

**STOP gate:** Deleted report ID returns structured error. `ReportDeleted` event appears in audit log.

### Phase 4 — Data cleanup completion
- Unlock `data cleanup --confirm` (actual deletion)
- Per-category `--target` flag
- `DataCleanupCompleted` audit event with counts

**STOP gate:** `data cleanup --target reports --older-than 30d --dry-run` shows correct preview. `--confirm` deletes and writes audit event.

### Phase 5 — Startup cleanup (optional, config-gated)
- `run_cleanup_on_startup: true` config key
- Background `Popen` execution
- `DataCleanupFailed` audit event on error

**STOP gate:** With `run_cleanup_on_startup: true`, cleanup runs in background and audit event is written. Primary CLI command is not delayed.
