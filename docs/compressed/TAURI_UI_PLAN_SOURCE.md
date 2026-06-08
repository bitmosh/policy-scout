# Policy Scout — Tauri UI Plan v0

## 1. Purpose

Safety-first plan for a future Policy Scout Tauri UI using existing CLI JSON contracts. The UI is a read-only dashboard for v0. Mutation screens are deferred until the policy boundary is proven stable.

**Core principle:** The UI is a viewer, not a bypass. Policy Scout decides. The UI displays decisions and evidence.

---

## 2. Non-goals for v0

The first Tauri UI will NOT:

- Implement mutation screens (run command, sandbox migration, approval management, real cleanup deletion)
- Add a Python API server, JSON schema registry, or Tauri itself (planning only)
- Create frontend files, add dependencies, or change application code
- Allow arbitrary command input, read files directly from frontend, or implement cloud sync
- Implement MCP/editor integration, provide hidden cleanup/deletion paths
- Access raw audit DB or report files directly from frontend
- Bypass existing policy/approval/sandbox paths

---

## 3. Security Doctrine for UI

The UI must preserve the policy boundary:

```text
UI Request -> CLI Subprocess -> Policy Scout Core -> Decision -> JSON Response -> UI Display
```

**Security rules:**

- The UI never executes user commands directly, bypasses policy decisions, or approves its own requests.
- The UI never reads raw secrets from files, mutates state without CLI commands, or exposes redacted secrets.
- The UI must treat all CLI JSON as untrusted input, validate before display, show redaction placeholders, and communicate that it is a viewer not an authority.

---

## 4. Recommended Architecture

### v0 Architecture: CLI Subprocess Boundary

```
Tauri Frontend (Rust/Web) -> Rust Command Wrapper (allowlist only) -> policy-scout CLI (Python) --json -> Policy Scout Core (Python) -> JSON Response (redacted) -> UI Display
```

**Key design choices:**

- CLI subprocess only (no Python API server in v0)
- Allowlist wrapper (Rust wrapper only permits known Policy Scout subcommands)
- JSON-only interface (all communication uses existing `--json` flags)
- No direct file access (frontend reads state through CLI JSON, not file system)
- No arbitrary shell (UI cannot run arbitrary commands through the wrapper)

### Future v1 Architecture (deferred)

Add mutation commands to allowlist wrapper. Mutation screens added only after read-only screens are stable and JSON API v1 design is complete.

---

## 5. CLI Subprocess Boundary

### Command Allowlist (v0)

The UI may only call these CLI commands with `--json`:

```text
policy-scout doctor --json
policy-scout data status --json
policy-scout data cleanup --target <target> --dry-run --json
policy-scout report list --json [--type <type>]
policy-scout report show <report_id> --json
policy-scout audit list --json
policy-scout audit show <event_id> --json
policy-scout audit request <request_id> --json
policy-scout audit type <event_type> --json
policy-scout audit stats --json
policy-scout sweep project --json
policy-scout sweep quick --json
policy-scout eval run --json
```

### Command Blocklist (v0)

The UI must NOT call these commands directly in v0:

```text
policy-scout check -- <command> (deferred)
policy-scout run -- <command> (deferred)
policy-scout run --approval <approval_id> -- <command> (deferred)
policy-scout sandbox -- <command> (deferred)
policy-scout sandbox <sandbox_id> (deferred)
policy-scout sandbox --dry-run <sandbox_id> (deferred)
policy-scout sandbox --yes <sandbox_id> (deferred)
policy-scout approvals list/show/approve/deny (deferred)
policy-scout data cleanup --target <target> (no --dry-run, not implemented)
```

### Rust Wrapper Requirements

The Rust command wrapper must:

- Accept only allowlisted subcommands, reject any command not in the allowlist
- Reject arbitrary shell injection attempts and command strings with shell metacharacters outside safe patterns
- Pass only validated arguments to CLI, capture stdout/stderr, return structured result with exit code
- Never allow general shell plugin access

Prefer a dedicated Rust wrapper over Tauri's general shell plugin (too permissive for safety-critical policy enforcement).

---

## 6. Tauri Permissions/Capabilities Posture

### Minimal Permissions (v0)

- **File system:** No direct file system access (read state through CLI JSON)
- **Shell:** Scoped to Policy Scout binary only via Rust wrapper
- **Network:** No network access (Policy Scout CLI may need network for package installs, but UI does not)
- **Process:** No process control
- **Clipboard:** Read-only for copy-paste support (optional)

### Tauri v2 Capabilities

- Use scoped shell access to Policy Scout binary only
- Do not enable general shell plugin or arbitrary command execution
- Use capability manifest to restrict to allowlisted commands
- Prefer sidecar packaging only if Python CLI packaging becomes necessary (deferred decision)

---

## 7. Safe Read-Only First Screens

**Screen 1: Doctor Health Dashboard** (`policy-scout doctor --json`)
- Display overall health status, individual check statuses, CLI import health, Python version, registry load status, registry entry counts, audit store/report directory availability, optional package manager availability
- No user actions (read-only)

**Screen 2: Data Status** (`policy-scout data status --json`)
- Display data root path, all local state paths, existence status, counts for reports/sandbox results/demo workspaces/approvals/audit events
- No user actions (read-only)

**Screen 3: Data Cleanup Dry-Run Planner** (`policy-scout data cleanup --target <target> --dry-run --json`)
- Display planned items, estimated sizes, warnings for demo/sandbox/sandbox-results targets
- No user actions (read-only preview). Real deletion is deferred.

**Screen 4: Report List** (`policy-scout report list --json [--type <type>]`)
- Display report list with report_id, report_type, title, created_at, filter by type, sort by created_at
- Click report to view details

**Screen 5: Report Detail Viewer** (`policy-scout report show <report_id> --json`)
- Display report metadata, decision/risk information (if command_decision), findings (if sandbox_result/sweep_result), recommended actions, credential exposure assessment, could not verify items, redaction status
- No user actions (read-only)

**Screen 6: Audit Stats** (`policy-scout audit stats --json`)
- Display total event count, event counts by type, first/last event timestamps, request count
- No user actions (read-only)

**Screen 7: Audit List** (`policy-scout audit list --json`)
- Display event list with event_id, event_type, timestamp, request_id, summary, pagination controls
- Click event to view details

**Screen 8: Audit Detail Viewer** (`policy-scout audit show <event_id> --json`)
- Display event metadata, actor information, summary, structured data_json
- No user actions (read-only)

**Screen 9: Audit Request Timeline** (`policy-scout audit request <request_id> --json`)
- Display timeline of events for the request, event types in sequence, timestamps
- No user actions (read-only)

**Screen 10: Audit Type Browser** (`policy-scout audit type <event_type> --json`)
- Display list of events for the specified type, event metadata
- No user actions (read-only)

**Screen 11: Sweep Result Viewer** (`policy-scout sweep project --json` or `policy-scout sweep quick --json`)
- Display sweep metadata, findings count by severity, findings list with severity/title/location/category, could not verify items
- No user actions (read-only)

**Screen 12: Eval Run Results** (`policy-scout eval run --json`)
- Display summary (total_cases, passed, failed, pass_rate, execution_time_ms, timestamp), results list with case_id/expected_decision/actual_decision/passed
- No user actions (read-only)

---

## 8. High-Friction/Deferred Mutation Screens

**Deferred: Command Check Screen** - Requires arbitrary command input (injection risk). Must design safe input validation and JSON API v1 first.

**Deferred: Run Command Screen** - Highest risk screen. Requires policy stability, approval flow integration, and proven read-only UI.

**Deferred: Sandbox Review Screen** - Requires sandbox result viewing, migration planning, and high-friction confirmation flows.

**Deferred: Approval Management Screen** - Requires approval queue viewing, approval details, and approve/deny actions. Must ensure UI cannot approve its own requests.

**Deferred: Real Cleanup Deletion** - Cleanup command is preview-only in v1. Real deletion path does not exist. Must design safe deletion with backups and rollback.

---

## 9. Data Model for UI Panels

### UI State Model

```typescript
interface UIState {
  currentScreen: ScreenType;
  selectedReportId?: string;
  selectedEventId?: string;
  selectedRequestId?: string;
  selectedEventType?: string;
  selectedSweepId?: string;
  lastRefreshTime: number;
  refreshInterval: number;
}

type ScreenType = "doctor" | "data-status" | "cleanup-planner" | "report-list" | "report-detail" | "audit-stats" | "audit-list" | "audit-detail" | "audit-request" | "audit-type" | "sweep-result" | "eval-results";
```

### CLI Response Models

Parse CLI JSON responses into TypeScript interfaces matching current JSON shapes (derived from `tests/test_json_contracts.py` and `policy_scout/cli/main.py`):

- **DoctorResponse:** `checks: Record<string, { status: string; message: string }>`
- **DataStatusResponse:** `data_root, paths, counts`
- **ReportListResponse:** `reports: Array<{ report_id, report_type, title, created_at }>`
- **ReportDetailResponse:** `report_id, report_type, title, summary, created_at, decision?, risk_score?, risk_band?, command?, findings?, recommended_actions?, credential_exposure_assessment?, could_not_verify?, redaction_applied?`
- **AuditStatsResponse:** `total_events, event_counts, first_event_timestamp, last_event_timestamp, request_count`
- **AuditListResponse:** `events: Array<{ event_id, event_type, timestamp, request_id, summary }>`
- **AuditDetailResponse:** `event_id, event_type, timestamp, request_id, actor_type, actor_name, summary, data_json`
- **SweepResultResponse:** `sweep_id, project_root?, platform?, duration_ms, findings_count, findings, could_not_verify`
- **EvalRunResponse:** `summary: { total_cases, passed, failed, pass_rate, execution_time_ms, timestamp }, results: Array<{ case_id, expected_decision, actual_decision, passed }>`

---

## 10. JSON Commands the UI May Call

### Read-Only Commands (v0)

```text
policy-scout doctor --json
policy-scout data status --json
policy-scout data cleanup --target demo/sandbox/sandbox-results --dry-run --json
policy-scout report list --json [--type command_decision/sandbox_result/sweep_result]
policy-scout report show <report_id> --json
policy-scout audit list/show/request <id>/type <type>/stats --json
policy-scout sweep project/quick --json
policy-scout eval run --json
```

### Mutation Commands (deferred to v1)

```text
policy-scout check/run/sandbox --json -- <command>
policy-scout sandbox --dry-run/--yes <sandbox_id> --json
policy-scout approvals list/show --json
```

---

## 11. Commands the UI Must Not Call Directly

The UI must never call these commands directly in v0:

```text
policy-scout run -- <command> (without --json, unsafe)
policy-scout run --approval <approval_id> -- <command> (deferred)
policy-scout sandbox <sandbox_id> (interactive, unsafe)
policy-scout sandbox --yes <sandbox_id> (deferred)
policy-scout approvals approve/deny <approval_id> (deferred)
policy-scout data cleanup --target <target> (without --dry-run, not implemented)
```

These commands require interactive confirmation (unsafe for UI automation), are not implemented yet (real cleanup deletion), or are high-risk mutation actions (deferred to v1).

---

## 12. Error Handling Strategy

### CLI Error Handling

- Exit code 0: Success, parse JSON
- Exit code 10/20: Risky/denied (should not occur in read-only commands)
- Exit code 30: Error, display error message from stderr
- JSON parse error: Display "Invalid JSON response from CLI"
- Timeout: Display "CLI command timed out"
- Missing field: Display "Unexpected JSON response format" (defensive coding)

### UI Error Display

- Show error messages in dedicated error panel
- Preserve error context (which command failed, what was the error)
- Offer retry button for transient errors
- Never hide errors or silently fall back to unsafe behavior

### Rust Wrapper Error Handling

- Reject invalid commands before calling CLI
- Validate arguments before passing to CLI
- Return structured errors (not raw strings)
- Never expose raw shell errors to frontend

---

## 13. Redaction/Privacy Strategy

### Redaction Display

- Display redaction placeholders as-is (e.g., `<redacted:possible_token>`)
- Show "redaction applied" indicator when redaction_applied flag is true
- Never attempt to decode or reverse redaction
- Never cache raw secrets in memory

### Privacy Rules

- Never display raw secrets from JSON responses, log raw secrets to console, include secrets in error messages, or store secrets in local storage
- Treat all JSON responses as potentially containing redacted data

### File Path Display

- Display file paths as-is from CLI JSON (CLI already normalizes home paths to ~ where practical)
- Do not attempt to resolve paths to absolute paths (privacy risk)
- Trust the CLI's path normalization

---

## 14. Packaging/Distribution Concerns

### Packaging Options (deferred decision)

**Option 1: System Python + pip install** - User installs Policy Scout via pip, Tauri app assumes `policy-scout` is in PATH. Simplest for development, requires Python environment setup.

**Option 2: Bundled Python (PyOxidizer or similar)** - Bundle Python runtime with Policy Scout. Single binary distribution, more complex build process, larger download size.

**Option 3: Sidecar packaging** - Tauri app ships Policy Scout as a sidecar binary. Tauri manages sidecar lifecycle, cleaner separation, more complex Tauri configuration.

**Recommendation:** Defer packaging decision until v1. Use Option 1 for initial development (assume system Python).

### Distribution

- No cloud sync, automatic updates, or telemetry in v0
- Local-only installation only

---

## 15. Development Phases

**Phase 0: Planning (current)** - Document Tauri UI plan, define read-only screens, define command allowlist, define Rust wrapper requirements. Do not implement anything.

**Phase 1: Rust Wrapper (future)** - Implement Rust command wrapper with allowlist, add unit/integration tests for command validation and CLI subprocess calls, ensure wrapper rejects invalid commands and returns structured errors.

**Phase 2: Tauri Scaffolding (future)** - Initialize Tauri v2 project, configure minimal capabilities, integrate Rust wrapper, set up basic window/navigation. Do not implement screens yet.

**Phase 3: Read-Only Screens (future)** - Implement all 12 read-only screens, add navigation between screens, add error handling, add redaction display.

**Phase 4: Testing (future)** - Add end-to-end tests for each screen, add error handling tests, add redaction tests, verify JSON contract compatibility, verify CLI subprocess integration.

**Phase 5: Polish (future)** - Improve UI/UX, add loading states, refresh controls, dark mode support, keyboard shortcuts.

**Phase 6: Mutation Screens (deferred to v1)** - Design JSON API v1 and schema registry, implement mutation screens, add high-friction confirmation dialogs, add approval flow integration.

---

## 16. Readiness Checklist Before Implementation

**Before Phase 1 (Rust Wrapper):**

- [ ] JSON Shape Consistency Review v1 completed and reviewed
- [ ] JSON contract tests passing for all read-only commands
- [ ] JSON API v1 design documented (if needed before mutation screens)
- [ ] Rust wrapper requirements finalized
- [ ] Command allowlist finalized
- [ ] Security review of subprocess boundary
- [ ] Privacy review of redaction strategy
- [ ] Packaging decision made (or deferred with rationale)

**Before Phase 3 (Read-Only Screens):**

- [ ] Rust wrapper implemented and tested
- [ ] Tauri scaffolding configured with minimal capabilities
- [ ] CLI subprocess integration verified
- [ ] JSON parsing tested for all read-only commands
- [ ] Error handling strategy implemented
- [ ] Redaction display implemented

**Before Phase 6 (Mutation Screens):**

- [ ] Read-only screens stable and tested
- [ ] JSON API v1 design complete
- [ ] Schema registry implemented (if needed)
- [ ] Approval flow security reviewed
- [ ] Sandbox migration security reviewed
- [ ] High-friction confirmation dialogs designed
- [ ] Rollback mechanisms tested (for cleanup)

---

## 17. Open Questions

**Packaging:** Should Policy Scout be bundled with Python runtime or assume system Python? Should sidecar packaging be used? Platform-specific considerations?

**JSON API v1:** Should schema_version be added to all JSON outputs before UI implementation? Should run --json shapes be unified (allowed vs blocked paths)? Should eval run --json execution_time_ms be aliased to execution_time?

**Mutation Screens:** Should the UI allow command input for check or use pre-defined templates? How should approval flow work (via CLI or direct UI call)? Should sandbox migration be one-click or multi-step confirmation?

**Performance:** Acceptable latency for CLI subprocess calls? Should UI cache CLI responses or always refresh? How to handle long-running commands (sweep, eval)?

**Accessibility:** Accessibility requirements? Keyboard-only navigation? Screen reader support?

**Internationalization:** Multiple language support? Handle CLI error messages in different languages?
