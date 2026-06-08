# Policy Scout — Tauri Component/Data Contract Map v0

## 1. Purpose

Planning document that maps future Tauri UI screens/components to existing Policy Scout CLI JSON commands, durable local data sources, and fields they will need. This is docs-only planning work, not implementation.

**Core principle:** The UI is a viewer, not a bypass. All screens display evidence from CLI JSON output. No mutation, no arbitrary command input, no direct filesystem access.

---

## 2. Non-goals

This document does NOT:

- Create frontend files, Rust/Tauri commands, or UI implementation code
- Add a Python API server, JSON schema registry, or Tauri itself
- Change JSON output shapes or command behavior
- Implement command execution UI, approval UI, or cleanup deletion UI
- Change Python code, tests, or CLI behavior
- Add dependencies or modify the codebase

---

## 3. Contract Doctrine

### UI Boundary

The UI must preserve the policy boundary:

```text
UI Request -> CLI Subprocess -> Policy Scout Core -> Decision -> JSON Response -> UI Display
```

### Security Rules

- UI displays and requests through governed adapters only
- UI must not bypass policy/audit/sandbox boundaries
- Existing CLI JSON is the current source of truth until JSON API v1 is designed
- Redaction placeholders are protected evidence, not display errors
- Local-first: all durable state stays local under ~/.local/share/policy-scout/
- UI never executes user commands directly, bypasses policy decisions, or approves its own requests
- UI never reads raw secrets from files, mutates state without CLI commands, or exposes redacted secrets

### CLI Subprocess Boundary

The UI may only call allowlisted CLI commands with --json through a Rust wrapper. The wrapper rejects invalid commands and returns structured errors. No arbitrary shell passthrough.

---

## 4. Screen/Component Map

### Screen 1: Dashboard / Status Overview

**Purpose:** Single-page health and activity overview.

**CLI commands:**
- `policy-scout doctor --json`
- `policy-scout data status --json`
- `policy-scout audit stats --json`
- `policy-scout report list --json --limit 5`

**Primary IDs:** None (health/status commands)

**Key fields:**
- doctor: checks.status, checks.message, registry entries, package managers
- data status: data_root, paths.path, paths.exists, counts
- audit stats: total_events, event_counts, time_range
- report list: report_id, report_type, title, created_at

**Redaction/privacy concerns:** Minimal (health/status data is low-sensitivity)

**Current limitations:** None known

---

### Screen 2: Decision Check Panel (deferred)

**Purpose:** Check a command without executing (deferred to v1).

**CLI command:** `policy-scout check -- <command> --json` (deferred)

**Primary IDs:** request_id, evaluation_id, decision_id

**Key fields:** command, decision, risk_score, risk_band, category, capabilities, reasons, recommended_next_action, confidence, redaction_applied

**Redaction/privacy concerns:** Command string may contain secrets; redaction applied by CLI

**Current limitations:** Deferred - requires safe command input validation and JSON API v1

---

### Screen 3: Audit Timeline

**Purpose:** Audit event statistics and list.

**CLI commands:**
- `policy-scout audit stats --json`
- `policy-scout audit list --json --limit <n>`

**Primary IDs:** event_id, request_id

**Key fields:**
- stats: total_events, event_counts, time_range (first_event, last_event), request_count
- list: event_id, event_type, timestamp, request_id, summary

**Redaction/privacy concerns:** Event data may contain redacted command strings or paths

**Current limitations:** None known

---

### Screen 4: Audit Event Detail

**Purpose:** View single audit event in detail.

**CLI commands:**
- `policy-scout audit show <event_id> --json`
- `policy-scout audit request <request_id> --json`

**Primary IDs:** event_id, request_id

**Key fields:** event_id, event_type, timestamp, request_id, actor_type, actor_name, summary, data_json

**Redaction/privacy concerns:** data_json may contain redacted values; display as protected evidence

**Current limitations:** None known

---

### Screen 5: Scout Report List

**Purpose:** List Scout Reports with filtering and sorting.

**CLI command:** `policy-scout report list --json --type <type> --limit <n>`

**Primary IDs:** report_id

**Key fields:** report_id, report_type, title, created_at, has_markdown, has_json

**Redaction/privacy concerns:** Report titles may contain project names (low sensitivity)

**Current limitations:** None known

---

### Screen 6: Scout Report Detail

**Purpose:** View single Scout Report in detail with redaction status.

**CLI command:** `policy-scout report show <report_id> --json`

**Primary IDs:** report_id, request_id, decision_id, sandbox_id, sweep_id

**Key fields:** report_id, report_type, title, summary, created_at, decision, risk_score, risk_band, command, findings, recommended_actions, credential_exposure_assessment, could_not_verify, redaction_applied

**Redaction/privacy concerns:** Command may be redacted; findings may contain redacted paths; redaction_applied flag must be displayed prominently

**Current limitations:** None known

---

### Screen 7: Sandbox Review List/Detail (deferred)

**Purpose:** View sandbox results and migration planning (deferred to v1).

**CLI commands:** (deferred)
- `policy-scout sandbox -- <command> --json` (install/review mode)
- `policy-scout sandbox <sandbox_id> --json` (migration mode)
- `policy-scout sandbox --dry-run <sandbox_id> --json`

**Primary IDs:** sandbox_id, request_id

**Key fields:** sandbox_id, request_id, command, package_manager, temp_workspace, exit_code, duration_ms, manifest_changed, lockfile_changed, lifecycle_scripts_found, findings, migration_available, migration_requires_approval, could_not_verify, redaction_applied

**Redaction/privacy concerns:** Sandbox workspace paths may contain temp filenames; findings may contain redacted paths

**Current limitations:** Deferred - requires sandbox result viewing, migration planning, high-friction confirmation flows

---

### Screen 8: Sweep Project Results

**Purpose:** View project sweep results.

**CLI command:** `policy-scout sweep project --json --project <path>`

**Primary IDs:** sweep_id

**Key fields:** sweep_id, sweep_type, project_root, platform, duration_ms, findings_count, findings, could_not_verify, schema_version

**Redaction/privacy concerns:** project_root may contain user paths; findings may contain redacted file paths

**Current limitations:** None known

---

### Screen 9: Quick Sweep Results

**Purpose:** View quick system sweep results.

**CLI command:** `policy-scout sweep quick --json`

**Primary IDs:** sweep_id

**Key fields:** sweep_id, sweep_type, platform, duration_ms, findings_count, findings, could_not_verify, schema_version

**Redaction/privacy concerns:** Findings may contain redacted process command lines, temp file paths, config paths

**Current limitations:** None known

---

### Screen 10: Data Status / Data Locations

**Purpose:** Detailed view of local data paths, existence status, and counts.

**CLI command:** `policy-scout data status --json`

**Primary IDs:** None (status command)

**Key fields:** data_root, paths.path, paths.exists, counts.reports, counts.sandbox_results, counts.demo_workspaces, counts.approvals, counts.audit_events

**Redaction/privacy concerns:** Paths may contain home directory; CLI normalizes to ~ where practical

**Current limitations:** None known

---

### Screen 11: Cleanup Dry-Run Preview

**Purpose:** Preview cleanup planning for low-risk temporary local state. Dry-run only.

**CLI command:** `policy-scout data cleanup --target <target> --dry-run --json`

**Primary IDs:** None (planning command)

**Key fields:** target, planned_items, estimated_size, warnings

**Redaction/privacy concerns:** Planned items may contain file paths; CLI normalizes to ~ where practical

**Current limitations:** Real deletion path does not exist in v1; dry-run only

---

### Screen 12: Settings / Mode (future placeholder)

**Purpose:** Future settings screen (placeholder only).

**CLI commands:** None (future)

**Primary IDs:** None

**Key fields:** None (future)

**Redaction/privacy concerns:** None (future)

**Current limitations:** Not implemented; future work

---

### Screen 13: Eval Results

**Purpose:** View evaluation suite results.

**CLI command:** `policy-scout eval run --json`

**Primary IDs:** None (eval command)

**Key fields:** summary.total_cases, summary.passed, summary.failed, summary.pass_rate, summary.execution_time_ms, summary.timestamp, results.case_id, results.expected_decision, results.actual_decision, results.passed

**Redaction/privacy concerns:** Minimal (eval case data is low-sensitivity)

**Current limitations:** None known

---

### Empty/Loading/Error States

**Purpose:** UI state handling for all screens.

**CLI commands:** None (UI state)

**Primary IDs:** None

**Key fields:** None (UI state)

**Redaction/privacy concerns:** None (UI state)

**Current limitations:** None known

---

## 5. Command/Data Source Table

| UI Area | CLI Command | JSON Support | Primary IDs | Key Fields | Redaction/Privacy Concerns | Current Limitations/Inconsistencies |
|---------|-------------|--------------|-------------|------------|---------------------------|-----------------------------------|
| Dashboard/Status | doctor --json | Yes | None | checks.status, checks.message, registry entries, package managers | Minimal | None known |
| Dashboard/Status | data status --json | Yes | None | data_root, paths.path, paths.exists, counts | Paths may contain home directory | None known |
| Dashboard/Status | audit stats --json | Yes | None | total_events, event_counts, time_range | Event data may contain redacted strings | None known |
| Dashboard/Status | report list --json | Yes | report_id | report_id, report_type, title, created_at | Report titles may contain project names | None known |
| Decision Check (deferred) | check -- <command> --json | Yes | request_id, evaluation_id, decision_id | command, decision, risk_score, risk_band, category, capabilities, reasons | Command string may contain secrets | Deferred - requires safe input validation |
| Audit Timeline | audit stats --json | Yes | None | total_events, event_counts, time_range | Event data may contain redacted strings | None known |
| Audit Timeline | audit list --json | Yes | event_id, request_id | event_id, event_type, timestamp, request_id, summary | Event data may contain redacted strings | None known |
| Audit Event Detail | audit show <event_id> --json | Yes | event_id, request_id | event_id, event_type, timestamp, request_id, summary, data_json | data_json may contain redacted values | None known |
| Audit Event Detail | audit request <request_id> --json | Yes | request_id | event_id, event_type, timestamp, request_id | Event data may contain redacted strings | None known |
| Scout Report List | report list --json | Yes | report_id | report_id, report_type, title, created_at | Report titles may contain project names | None known |
| Scout Report Detail | report show <report_id> --json | Yes | report_id, request_id, decision_id, sandbox_id, sweep_id | report_id, report_type, title, summary, decision, risk_score, findings, recommended_actions, credential_exposure_assessment, could_not_verify, redaction_applied | Command may be redacted; findings may contain redacted paths | None known |
| Sandbox Review (deferred) | sandbox -- <command> --json | Yes | sandbox_id, request_id | sandbox_id, command, package_manager, temp_workspace, findings, migration_available, redaction_applied | Workspace paths may contain temp filenames | Deferred - requires migration planning |
| Sandbox Review (deferred) | sandbox <sandbox_id> --json | Yes | sandbox_id | sandbox_id, migration_available, migration_requires_approval, planned_files | Planned files may contain paths | Deferred - requires high-friction confirmation |
| Sweep Project Results | sweep project --json | Yes | sweep_id | sweep_id, project_root, findings_count, findings, could_not_verify | project_root may contain user paths; findings may contain redacted paths | None known |
| Quick Sweep Results | sweep quick --json | Yes | sweep_id | sweep_id, platform, findings_count, findings, could_not_verify | Findings may contain redacted process command lines, temp paths | None known |
| Data Status | data status --json | Yes | None | data_root, paths.path, paths.exists, counts | Paths may contain home directory | None known |
| Cleanup Dry-Run Preview | data cleanup --target <target> --dry-run --json | Yes | None | target, planned_items, estimated_size, warnings | Planned items may contain file paths | Real deletion path does not exist in v1 |
| Eval Results | eval run --json | Yes | None | summary.total_cases, summary.passed, summary.failed, summary.pass_rate, summary.execution_time_ms, results.case_id, results.expected_decision, results.actual_decision | Minimal (eval case data is low-sensitivity) | None known |

---

## 6. Field-Level Notes

### Known JSON Inconsistencies (JSON API v1 Review Candidates)

**run --json allowed path uses decision_id, not decision:**
- Current: `run --json` allowed path returns `decision_id` field
- Inconsistency: Other commands use `decision` field directly
- Impact: UI must handle both field names for run results
- Review candidate: Unify to use `decision` field in JSON API v1

**run --json blocked path lacks risk_score:**
- Current: `run --json` blocked path (SANDBOX_FIRST, DENY) returns decision but may lack risk_score
- Inconsistency: `check --json` always returns risk_score
- Impact: UI may not have risk_score for blocked run results
- Review candidate: Ensure risk_score is present in all run --json paths

**eval run --json uses execution_time_ms:**
- Current: `eval run --json` uses `execution_time_ms` field name
- Inconsistency: Other time fields may use different naming (e.g., `duration_ms` in sweep)
- Impact: UI must handle inconsistent time field names
- Review candidate: Unify to `duration_ms` or add aliases in JSON API v1

**report list created_at field presence:**
- Current: `report list --json` includes `created_at` only for reports generated by current code path
- Inconsistency: Older reports may lack `created_at` field
- Impact: UI must handle missing `created_at` gracefully
- Review candidate: Ensure all reports have `created_at` in JSON API v1

**audit stats time_range presence:**
- Current: `audit stats --json` includes `time_range` only when events exist
- Inconsistency: Empty audit store lacks `time_range` field
- Impact: UI must handle missing `time_range` gracefully
- Review candidate: Always include `time_range` (null if empty) in JSON API v1

### Field Naming Patterns

**ID prefixes:**
- req_: request_id
- eval_: evaluation_id
- dec_: decision_id
- evt_: event_id
- sbx_: sandbox_id
- sweep_: sweep_id
- find_: finding_id
- report_: report_id
- appr_: approval_id

**Timestamp formats:**
- ISO 8601 strings (e.g., "2026-06-07T21:14:00Z")
- Unix epoch integers in some internal contexts
- UI should expect ISO 8601 from CLI JSON

**Risk band values:**
- low (1-3)
- medium (4-6)
- high (7-8)
- critical (9-10)

**Decision values:**
- ALLOW
- ALLOW_LOGGED
- REQUIRE_APPROVAL
- SANDBOX_FIRST
- DENY
- DENY_AND_ALERT

**Severity values:**
- info
- low
- medium
- high
- critical

**Confidence values:**
- low
- moderate
- high
- confirmed

---

## 7. UI Safety States

### Decision States

**ALLOW:**
- Command is safe to execute
- UI display: Green indicator, "Allowed"
- No user action required for read-only view

**ALLOW_LOGGED:**
- Command is safe to execute, logged
- UI display: Green indicator, "Allowed (Logged)"
- No user action required for read-only view

**REQUIRE_APPROVAL:**
- Command requires human approval before execution
- UI display: Amber indicator, "Approval Required"
- Deferred: Approval UI not implemented in v0

**SANDBOX_FIRST:**
- Command should run in sandbox before host execution
- UI display: Orange indicator, "Sandbox First"
- Deferred: Sandbox review UI not implemented in v0

**DENY:**
- Command is denied
- UI display: Red indicator, "Denied"
- No user action required for read-only view

**DENY_AND_ALERT:**
- Command is denied and alert raised
- UI display: Red indicator with alert icon, "Denied (Alert)"
- No user action required for read-only view

### System States

**could_not_verify:**
- Policy Scout could not complete a verification check
- UI display: Gray indicator, "Could Not Verify"
- Display list of unverified checks

**redaction_applied:**
- Redaction was applied to output
- UI display: Amber indicator, "Redaction Applied"
- Display redaction placeholders as protected evidence (monospace, muted, shield icon)

**audit_persistence_unavailable:**
- Audit store write failed
- UI display: Red indicator, "Audit Persistence Unavailable"
- Fail-safe: Risky commands should not run if audit fails

**report_unavailable:**
- Report file could not be read
- UI display: Gray indicator, "Report Unavailable"
- Offer retry or report regeneration

**sandbox_result_blocked_from_migration:**
- Sandbox result has high/critical findings, migration blocked
- UI display: Red indicator, "Migration Blocked"
- Display blocking findings

---

## 8. Future Adapter Boundary

### Rust Wrapper Requirements

The future Tauri adapter should call a narrow local command/data layer and must preserve:

**Actor identity:**
- actor_type (human, agent, ide, cli, ci, unknown)
- actor_name

**Source:**
- source (cli, ide, agent, ci)

**Context:**
- cwd (current working directory)
- request_id (unique request identifier)

**Decision metadata:**
- decision_id (unique decision identifier)
- decision (ALLOW, ALLOW_LOGGED, REQUIRE_APPROVAL, SANDBOX_FIRST, DENY, DENY_AND_ALERT)
- risk_score (1-10)
- risk_band (low, medium, high, critical)

**Audit trail:**
- audit event IDs (evt_*)
- request_id linkage
- timestamp

**Redaction metadata:**
- redaction_applied flag
- redaction placeholders preserved as-is

**No arbitrary shell passthrough:**
- Rust wrapper must reject any command not in allowlist
- Rust wrapper must validate arguments before passing to CLI
- Rust wrapper must return structured errors, not raw shell output

### Local Data Layer

The adapter should read from local durable state only:

**Audit store:**
- ~/.local/share/policy-scout/audit.db (SQLite primary)
- ~/.local/share/policy-scout/audit.jsonl (JSONL secondary)

**Approval store:**
- ~/.local/share/policy-scout/approvals.jsonl

**Report directory:**
- ~/.local/share/policy-scout/reports/

**Sandbox results:**
- ~/.local/share/policy-scout/sandboxes/

**Sweep results:**
- ~/.local/share/policy-scout/sweeps/

**No remote access:**
- Adapter must not access cloud services, remote dashboards, or hosted policy engines
- All data stays local unless user explicitly exports

---

## 9. Open Questions for JSON API v1

### Schema Versioning

**Should schema_version be added to all JSON outputs before UI implementation?**
- Current: Some commands have schema_version (sweep), others do not
- Question: Should all JSON outputs include schema_version for future compatibility?

### Field Name Unification

**Should run --json shapes be unified (allowed vs blocked paths)?**
- Current: Allowed path returns execution_id, decision_id; blocked path returns decision
- Question: Should both paths return the same field set for consistency?

**Should eval run --json execution_time_ms be aliased to duration_ms?**
- Current: eval run uses execution_time_ms, sweep uses duration_ms
- Question: Should time fields be unified across all commands?

### ID Consistency

**Should all commands return request_id in JSON output?**
- Current: check returns request_id, run returns execution_id, audit commands return event_id
- Question: Should request_id be present in all JSON outputs for traceability?

### Redaction Metadata

**Should redaction_applied be a required field in all JSON outputs?**
- Current: Present in some commands, missing in others
- Question: Should all JSON outputs include redaction_applied flag?

### Error Response Format

**Should error responses have a structured JSON format?**
- Current: Errors return non-zero exit code with stderr text
- Question: Should errors return JSON with error_code, error_message, error_type?

### Pagination

**Should list commands support cursor-based pagination?**
- Current: report list and audit list use --limit offset-style pagination
- Question: Should UI require cursor-based pagination for large datasets?

### Filtering

**Should filter parameters be standardized across list commands?**
- Current: report list supports --type, audit list supports --limit
- Question: Should all list commands support --type, --severity, --date-range filters?

---

## 10. Implementation Handoff Notes

### CLI Subprocess Integration

**UI calls only allowlisted `policy-scout ... --json` through Rust wrapper**
- Wrapper rejects invalid commands
- Wrapper returns structured errors
- Wrapper never exposes raw shell errors
- Wrapper validates arguments before passing to CLI

### JSON Contract Parsing

**Parse CLI JSON into TypeScript interfaces matching `tests/test_json_contracts.py`**
- Do not invent fields
- Mark deferred/untested contracts
- Handle missing fields gracefully (defensive coding)
- Treat all JSON as potentially containing redacted data

### Error Handling

**Exit code mapping:**
- 0: Success, parse JSON
- 10: Risky/approval/sandbox (should not occur in read-only commands)
- 20: Denied (should not occur in read-only commands)
- 30: Error, display error message from stderr
- JSON parse error: Display "Invalid JSON response from CLI"
- Timeout: Display "CLI command timed out"
- Missing field: Display "Unexpected JSON response format"

### Performance Considerations

**Acceptable latency:** TBD (needs benchmarking)
**Cache vs refresh:** TBD (needs performance testing)
**Long-running commands:** Handle with loading states (sweep, eval)

### Accessibility/i18n

**Requirements:** TBD
**Keyboard navigation:** TBD
**Screen reader:** TBD
**Multiple languages:** TBD
**CLI error messages in different languages:** TBD

### Tauri v2 Integration

**Scoped shell access to Policy Scout binary only**
- No general shell plugin
- No arbitrary execution
- Capability manifest for allowlisted commands
- Sidecar packaging deferred (decision pending)

### Packaging Decision

**Defer packaging decision until v1**
- Option 1: System Python + pip install (simplest for development)
- Option 2: Bundled Python (PyOxidizer or similar)
- Option 3: Sidecar packaging
- Use Option 1 for initial development (assume system Python)
