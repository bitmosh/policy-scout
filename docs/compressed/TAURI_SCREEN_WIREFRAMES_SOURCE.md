# Policy Scout — Tauri Screen Wireframes v0

## 1. Purpose

Compact wireframe documentation for the first read-only Policy Scout Tauri UI screens. These wireframes define the visual structure, data sources, and safety boundaries for the initial dashboard implementation.

**Core principle:** The UI is a viewer, not a bypass. All screens display evidence from CLI JSON output. No mutation, no arbitrary command input, no direct filesystem access.

---

## 2. UI Principles

**Visual doctrine:** Calm, local-first, lightweight, boundary-focused, implementation-aligned.

**Color semantics:** Blue/Cyan (flow), Amber/Gold (policy/approval), Green (allow), Orange (sandbox), Red (deny/alert), Purple (audit/report), Gray (registry/config).

**Dark-mode palette:** Background #0B0F12, Panel #101820, Text #E6EDF3, Cyan #42D9FF, Amber #F5B84B, Green #5EE08B, Orange #FF9F43, Red #FF5C5C, Purple #A78BFA, Gray #6B7280.

---

## 3. Navigation Model

**Sidebar:** Overview | Data | Reports | Audit | Sweeps | Evals

**Mapping:** Overview→Screen1, Data→Screen2/3, Reports→Screen4/5, Audit→Screen6/7, Sweeps→Screen8, Evals→Screen9

**Behavior:** Click sidebar to switch content, click list items for detail views. No browser history or deep linking in v0.

---

## 4. Global Layout

**Top bar:** [Logo+version] [Screen title] [Refresh]

**Sidebar:** Collapsible navigation tree

**Main content:** Scrollable screen-specific panels

**Footer:** [CLI status] [Last refresh] [Version]

---

## 5. Screen 1: Overview Dashboard

**Purpose:** Single-page health and activity overview.

**CLI commands:** `doctor --json`, `data status --json`, `audit stats --json`, `report list --json --limit 5`

**Wireframe:**
```
[Panel: Doctor Health] Overall status, CLI import, Python version, registry entries, audit/store/report availability, package managers
[Panel: Data Status Summary] Data root, reports/sandbox/demo/approvals/audit counts
[Panel: Recent Activity] Audit stats (total, types, timestamps), recent reports (top 5)
```

**Key fields:** checks.status/message, entry counts, data_root, paths.exists, counts, total_events, event_counts, report_id/type/title/created_at

**Actions allowed:** Refresh, click report for detail, collapse panels

**Actions not allowed:** Command execution, approval management, sandbox migration, cleanup deletion, arbitrary shell input

**Safety notes:** CLI JSON only, no direct filesystem reads, no raw audit DB access

---

## 6. Screen 2: Data Status

**Purpose:** Detailed view of local data paths, existence status, and counts.

**CLI command:** `data status --json`

**Wireframe:**
```
[Panel: Data Root] Path, status
[Panel: Local State Paths] audit.db, audit.jsonl, approvals.jsonl, reports/, sandboxes/, migrations/, backups/ existence
[Panel: Counts] Reports, sandbox results, demo workspaces, approvals, audit events
```

**Key fields:** data_root, paths.path/exists, counts.reports/sandbox_results/demo_workspaces/approvals/audit_events

**Actions allowed:** Refresh, navigate to Cleanup Planner

**Actions not allowed:** Direct file browsing, deletion, path modification

**Safety notes:** Paths as-is from CLI (normalizes ~), no absolute path resolution

---

## 7. Screen 3: Cleanup Dry-Run Planner

**Purpose:** Preview cleanup planning for low-risk temporary local state. Dry-run only. No deletion path exists.

**CLI commands:** `data cleanup --target demo/sandbox/sandbox-results --dry-run --json`

**Wireframe:**
```
[Banner: DRY-RUN ONLY - NO DELETION]
[Panel: Target Selection] Radio: demo/sandbox/sandbox-results, Preview button
[Panel: Planned Items] Target, planned items, estimated size, warnings
[Panel: Status] DRY-RUN COMPLETE, note: real deletion not available in v0
```

**Key fields:** target, planned_items, estimated_size, warnings

**Actions allowed:** Select target, click Preview, view planned items

**Actions not allowed:** Delete button, confirmation dialog, real cleanup execution, --yes flag

**Safety notes:** Banner required "DRY-RUN ONLY - NO DELETION", no UI element implies deletion available

---

## 8. Screen 4: Reports

**Purpose:** List Scout Reports with filtering and sorting.

**CLI command:** `report list --json --type <type> --limit <n>`

**Wireframe:**
```
[Panel: Filter Bar] Type filter (All/command_decision/sandbox_result/sweep_result), sort, Refresh
[Panel: Report List] report_id, report_type, title, created_at (pagination)
```

**Key fields:** report_id, report_type, title, created_at

**Actions allowed:** Select type filter, click report for detail, pagination

**Actions not allowed:** Report deletion/modification, direct file access

**Safety notes:** CLI JSON only, no direct report file reads

---

## 9. Screen 5: Report Detail

**Purpose:** View single Scout Report in detail with redaction status.

**CLI command:** `report show <report_id> --json`

**Wireframe:**
```
[Panel: Metadata] report_id, report_type, title, summary, created_at, redaction_applied indicator
[Panel: Decision] (if command_decision) decision, risk_score, risk_band, command (redacted)
[Panel: Findings] (if sandbox_result/sweep_result) findings count, findings list (severity/title/location/category)
[Panel: Recommended Actions] actions list
[Panel: Credential Exposure] level, notes
[Panel: Could Not Verify] list
```

**Key fields:** report_id/type/title/summary/created_at, decision/risk_score/risk_band/command, findings, recommended_actions, credential_exposure_assessment, could_not_verify, redaction_applied

**Actions allowed:** Back to list, copy report ID

**Actions not allowed:** Report modification/deletion, approval actions

**Safety notes:** Display redaction_applied prominently, placeholders styled as protected evidence (not errors)

---

## 10. Screen 6: Audit

**Purpose:** Audit event statistics, list, and type browser.

**CLI commands:** `audit stats --json`, `audit list --json --limit <n>`, `audit type <event_type> --json`

**Wireframe:**
```
[Panel: Audit Stats] total_events, event_counts, first/last timestamps, request_count
[Panel: Event Type Filter] All types, specific selector
[Panel: Audit List] event_id, event_type, timestamp, request_id, summary (pagination)
```

**Key fields:** total_events, event_counts, first/last timestamps, request_count, event_id/type/timestamp/request_id/summary

**Actions allowed:** Select type filter, click event for detail, pagination

**Actions not allowed:** Direct audit DB access, event deletion/modification

**Safety notes:** CLI JSON only, no raw SQLite DB reads

---

## 11. Screen 7: Audit Event Detail

**Purpose:** View single audit event in detail with request timeline.

**CLI commands:** `audit show <event_id> --json`, `audit request <request_id> --json`

**Wireframe:**
```
[Panel: Metadata] event_id, event_type, timestamp, request_id
[Panel: Actor] actor_type, actor_name
[Panel: Summary] summary
[Panel: Request Timeline] (if request_id) event types, timestamps
[Panel: Structured Data] data_json (pretty-printed, collapsible)
```

**Key fields:** event_id/type/timestamp/request_id, actor_type/name, summary, data_json

**Actions allowed:** Back to list, copy event ID, collapse/expand data

**Actions not allowed:** Event modification/deletion, approval actions

**Safety notes:** CLI JSON only, data_json may contain redacted values, placeholders as protected evidence

---

## 12. Screen 8: Sweep Results

**Purpose:** View sweep results (project or quick). User-triggered scans, not background/daemon.

**CLI commands:** `sweep quick --json`, `sweep project --json`

**Wireframe:**
```
[Panel: Type Selection] Radio: Quick/Project, Run Scan button
[Panel: Metadata] sweep_id, platform or project_root, duration_ms
[Panel: Findings Summary] findings count by severity
[Panel: Findings List] severity, title, location, category
[Panel: Could Not Verify] list
```

**Key fields:** sweep_id, project_root/platform, duration_ms, findings_count, findings (severity/title/location/category), could_not_verify

**Actions allowed:** Select type, click Run Scan (user-triggered), view findings

**Actions not allowed:** Background sweeps, daemon mode, result deletion/modification

**Safety notes:** User-triggered not background/daemon, CLI JSON only, findings may contain redacted paths

---

## 13. Screen 9: Eval Results

**Purpose:** View evaluation suite results.

**CLI command:** `eval run --json`

**Wireframe:**
```
[Panel: Summary] total_cases, passed, failed, pass_rate, execution_time_ms, timestamp
[Panel: Results List] case_id, expected_decision, actual_decision, passed
```

**Key fields:** summary (total_cases/passed/failed/pass_rate/execution_time_ms/timestamp), results (case_id/expected_decision/actual_decision/passed)

**Actions allowed:** Refresh, view results

**Actions not allowed:** Eval case modification/deletion, configuration changes

**Safety notes:** CLI JSON only, no direct eval case file access

---

## 14. Empty/Loading/Error States

**Loading:** Spinner + "Loading from Policy Scout CLI..."

**Empty:** Icon + "No reports/events/results" + "Run Policy Scout commands to generate data"

**Error:** Icon + "Failed to load data" + command/exit code/stderr + Retry button

**Error rules:** Display command/exit code/safe stderr, offer retry, never hide errors, never silently fall back to unsafe behavior

---

## 15. Redaction Display Rules

**Placeholder styling:** Display as-is (e.g., `<redacted:possible_token>`), style as protected evidence (monospace, muted, shield icon), not as errors

**Indicator:** Show "redaction applied" when redaction_applied=true, amber/gold color, prominent placement

**Privacy rules:** Never decode/reverse redaction, never cache raw secrets, never display/log/store secrets, treat all JSON as potentially redacted

**File paths:** Display as-is from CLI (normalizes ~), no absolute path resolution, trust CLI normalization

---

## 16. Deferred Screens

**Command Check Screen:** Requires arbitrary command input (injection risk), needs safe input validation + JSON API v1

**Run Command Screen:** Highest risk, needs policy stability + approval flow + proven read-only UI

**Sandbox Review Screen:** Needs sandbox result viewing + migration planning + high-friction confirmation

**Approval Management Screen:** Needs approval queue viewing + approve/deny actions, ensure UI cannot approve own requests

**Real Cleanup Deletion:** Cleanup is preview-only in v1, needs safe deletion + backups + rollback

---

## 17. Implementation Handoff Notes

**CLI subprocess:** UI calls only allowlisted `policy-scout ... --json` through Rust wrapper, wrapper rejects invalid commands, returns structured errors, never exposes raw shell errors

**JSON contracts:** Parse CLI JSON into TypeScript interfaces matching `tests/test_json_contracts.py`, do not invent fields, mark deferred/untested contracts

**Error handling:** Exit 0=success, 10/20=risky/denied (should not occur in read-only), 30=error, JSON parse=invalid response, timeout=CLI timed out, missing field=unexpected format

**Performance:** Acceptable latency TBD, cache vs refresh TBD, handle long-running commands with loading states

**Accessibility/i18n:** Requirements TBD, keyboard navigation TBD, screen reader TBD, multiple languages TBD, CLI error messages in different languages TBD

**Tauri v2:** Scoped shell access to Policy Scout binary only, no general shell plugin, no arbitrary execution, capability manifest for allowlisted commands, sidecar packaging deferred
