# Policy Scout — Tauri Adapter Boundary Spec v0

## 1. Purpose

Define the future Tauri command surface, allowlisted Policy Scout CLI calls, forbidden UI capabilities, and first implementation sequence. This is a boundary spec, not an implementation. The UI is a viewer, not a bypass. Policy Scout decides. The UI displays decisions and evidence.

**Core principle:** The UI must preserve the policy boundary. All UI requests flow through governed adapters only. The UI never executes commands directly, bypasses policy decisions, or approves its own requests.

---

## 2. Non-goals

This spec does NOT:

- Implement Tauri, create frontend files, or add Rust code
- Add a Python API server, JSON schema registry, or local HTTP API
- Change CLI JSON shapes or command behavior
- Implement command execution UI, approval UI, or cleanup deletion UI
- Change Python code, tests, or CLI behavior
- Add dependencies or modify the codebase
- Commit until approved

---

## 3. Core Adapter Doctrine

### Policy Boundary Preservation

The UI must preserve the core boundary:

```text
UI Request -> CLI Subprocess -> Policy Scout Core -> Decision -> JSON Response -> UI Display
```

**Security rules:**

- UI displays and requests through governed adapters only
- UI must not bypass policy/audit/sandbox/approval/report boundaries
- Existing CLI JSON is the current source of truth until JSON API v1 is designed
- Redaction placeholders are protected evidence, not display errors
- Local-first: all durable state stays local under ~/.local/share/policy-scout/
- UI never executes user commands directly, bypasses policy decisions, or approves its own requests
- UI never reads raw secrets from files, mutates state without CLI commands, or exposes redacted secrets
- UI must treat all CLI JSON as untrusted input, validate before display, show redaction placeholders

### CLI Subprocess Boundary

The UI may only call allowlisted CLI commands with --json through a Rust wrapper. The wrapper rejects invalid commands and returns structured errors. No arbitrary shell passthrough.

**Frontend-to-backend boundary:**

- React/frontend requests named data operations only
- Frontend must not construct arbitrary shell commands
- Rust/Tauri backend must own allowlisted command construction
- Future adapter must call existing `policy-scout ... --json` commands or a narrow Python adapter, not inspect SQLite or report files directly

---

## 4. Threat Model for the UI Adapter

### Primary Threats

1. **Arbitrary command injection:** Frontend constructs shell strings to bypass policy
2. **Direct database access:** UI reads audit.db or report files directly, bypassing CLI redaction
3. **Approval bypass:** UI approves its own requests or approves without audit trail
4. **Sandbox migration bypass:** UI migrates sandbox results without policy re-evaluation
5. **Secret leakage:** UI displays raw secrets from JSON or files
6. **Filesystem abuse:** UI reads arbitrary files or writes outside controlled paths
7. **Remote exfiltration:** UI sends audit logs or reports to cloud without user consent
8. **Policy override:** UI modifies policy files or registry to weaken safety

### Mitigation Strategy

- Allowlist wrapper: Only known CLI subcommands permitted
- No shell plugin: Rust wrapper constructs commands, not frontend
- No direct file access: UI reads state through CLI JSON only
- No SQLite access: UI never reads audit.db directly
- Redaction enforcement: All JSON treated as potentially redacted
- Actor/source preservation: Future mutation flows must preserve actor metadata
- Local-only: No network access from UI adapter
- Exit code interpretation: Known risky/denied exit codes treated as valid data, not crashes

---

## 5. Frontend-to-Backend Boundary

### Request Flow

```text
Frontend (React) -> Tauri Command (named operation) -> Rust Wrapper (allowlist) -> CLI Subprocess (policy-scout ... --json) -> Policy Scout Core -> JSON Response -> Rust Parser -> Structured Response -> Frontend
```

### Frontend Responsibilities

- Request named data operations only (e.g., get_doctor_status, list_reports)
- Never construct shell command strings
- Never pass arbitrary argv arrays
- Display redaction placeholders as protected evidence
- Treat all responses as potentially containing redacted data

### Rust Wrapper Responsibilities

- Accept only allowlisted Tauri command names
- Map Tauri commands to exact CLI invocations
- Validate arguments before passing to CLI
- Reject invalid commands before subprocess execution
- Capture stdout/stderr, return structured result with exit code
- Never expose raw shell errors to frontend
- Never allow general shell plugin access

### CLI Responsibilities

- Execute allowlisted commands with --json
- Apply redaction before JSON output
- Return structured JSON with redaction metadata
- Use canonical exit codes for known outcomes

---

## 6. Allowed Future Tauri Commands

### v0 Read-Only Commands

**get_doctor_status()**
- Purpose: Display health diagnostics
- CLI: policy-scout doctor --json
- Returns: checks, registry entries, package manager availability, audit/report path status

**get_data_status()**
- Purpose: Display local data paths and counts
- CLI: policy-scout data status --json
- Returns: data_root, paths.exists, counts

**get_audit_stats()**
- Purpose: Display audit event statistics
- CLI: policy-scout audit stats --json
- Returns: total_events, event_counts, time_range, request_count

**list_audit_events(limit, event_type?)**
- Purpose: List audit events with optional filtering
- CLI: policy-scout audit list --json --limit <n> [--type <type>]
- Returns: events list with event_id, event_type, timestamp, request_id, summary

**show_audit_event(event_id)**
- Purpose: Display single audit event detail
- CLI: policy-scout audit show <event_id> --json
- Returns: event metadata, actor, summary, data_json

**list_reports(limit, report_type?)**
- Purpose: List Scout Reports with optional filtering
- CLI: policy-scout report list --json --limit <n> [--type <type>]
- Returns: reports list with report_id, report_type, title, created_at

**show_report(report_id)**
- Purpose: Display single Scout Report detail
- CLI: policy-scout report show <report_id> --json
- Returns: report metadata, decision/risk, findings, recommended_actions, credential_exposure_assessment, could_not_verify, redaction_applied

**get_cleanup_dry_run(target)**
- Purpose: Preview cleanup planning (dry-run only)
- CLI: policy-scout data cleanup --target <target> --dry-run --json
- Returns: target, planned_items, estimated_size, warnings
- Constraint: target must be one of demo, sandbox, sandbox-results

**run_eval()**
- Purpose: Run evaluation suite
- CLI: policy-scout eval run --json
- Returns: summary (total_cases, passed, failed, pass_rate, execution_time_ms, timestamp), results list

**run_sweep_project()**
- Purpose: Run project sweep
- CLI: policy-scout sweep project --json
- Returns: sweep_id, project_root, findings_count, findings, could_not_verify

**run_sweep_quick()**
- Purpose: Run quick system sweep
- CLI: policy-scout sweep quick --json
- Returns: sweep_id, platform, findings_count, findings, could_not_verify

### Optional Later/Deferred Commands

**check_command(command)**
- Purpose: Check a command without executing
- CLI: policy-scout check -- <command> --json
- Deferred: Requires safe command input validation and JSON API v1

**show_sandbox_result(sandbox_id)**
- Purpose: Display sandbox result detail
- CLI: policy-scout sandbox <sandbox_id> --json
- Deferred: Requires sandbox result viewing and migration planning

**list_sandbox_results()**
- Purpose: List sandbox results
- CLI: (command to be defined)
- Deferred: Requires sandbox result storage design

**show_approval(approval_id)**
- Purpose: Display approval detail
- CLI: policy-scout approvals show <approval_id> --json
- Deferred: Requires approval flow security review

**list_approvals()**
- Purpose: List pending approvals
- CLI: policy-scout approvals list --json
- Deferred: Requires approval flow security review

---

## 7. Explicitly Forbidden Tauri Commands

### Forbidden for v0

**run_arbitrary_command(command)**
- Reason: Arbitrary command injection bypasses policy
- Alternative: Use check_command(command) when implemented

**run_policy_scout_args(args_from_frontend)**
- Reason: Frontend-provided argv arrays bypass allowlist
- Alternative: Use named Tauri commands mapped to allowlisted CLI invocations

**resolve_approval(...)**
- Reason: UI approving its own requests bypasses actor separation
- Alternative: Approval flow deferred to v1 with security review

**approve_anything(...)**
- Reason: UI approval without audit trail bypasses governance
- Alternative: Approval flow deferred to v1 with security review

**migrate_sandbox(...)**
- Reason: Sandbox migration without policy re-evaluation bypasses safety
- Alternative: Sandbox migration deferred to v1 with high-friction confirmation

**delete_data(...)**
- Reason: Deletion without backup/rollback bypasses safety
- Alternative: Cleanup deletion deferred to v1 with safe deletion path

**cleanup_real(...)**
- Reason: Real deletion path does not exist in v1; dry-run only
- Alternative: Use get_cleanup_dry_run(target) for preview

**read_file(path)**
- Reason: Arbitrary file access bypasses CLI redaction and policy
- Alternative: All data access through CLI JSON commands

**write_file(path, content)**
- Reason: Arbitrary file write bypasses policy and audit
- Alternative: All mutations through CLI commands when implemented

**query_sql(sql)**
- Reason: Direct SQL access bypasses CLI redaction and policy
- Alternative: All audit data through audit CLI commands

**spawn_process(args_from_frontend)**
- Reason: Arbitrary process execution bypasses policy
- Alternative: All execution through CLI run/sandbox commands when implemented

**open_shell()**
- Reason: Shell access bypasses policy boundary
- Alternative: No shell access in UI

**load_remote_policy()**
- Reason: Remote policy loading bypasses local-first doctrine
- Alternative: Local policy files only

**upload_audit_logs()**
- Reason: Remote upload bypasses local-first doctrine
- Alternative: Local-only storage, export deferred to v1

**send_reports_to_cloud()**
- Reason: Cloud sync bypasses local-first doctrine
- Alternative: Local-only storage, export deferred to v1

---

## 8. CLI Subprocess Allowlist

### Exact CLI Invocations

| Tauri Command | CLI Invocation | Notes |
|---------------|----------------|-------|
| get_doctor_status | policy-scout doctor --json | Read-only health check |
| get_data_status | policy-scout data status --json | Read-only data status |
| get_audit_stats | policy-scout audit stats --json | Read-only audit stats |
| list_audit_events | policy-scout audit list --json --limit <n> [--type <type>] | limit must be bounded (1-1000) |
| show_audit_event | policy-scout audit show <event_id> --json | event_id must match evt_ prefix |
| list_reports | policy-scout report list --json --limit <n> [--type <type>] | limit must be bounded (1-1000) |
| show_report | policy-scout report show <report_id> --json | report_id must match report_ prefix |
| get_cleanup_dry_run | policy-scout data cleanup --target <target> --dry-run --json | target must be demo/sandbox/sandbox-results |
| run_eval | policy-scout eval run --json | User-triggered eval run |
| run_sweep_project | policy-scout sweep project --json | User-triggered project sweep |
| run_sweep_quick | policy-scout sweep quick --json | User-triggered quick sweep |

### Deferred Commands

| Tauri Command | CLI Invocation | Notes |
|---------------|----------------|-------|
| check_command | policy-scout check -- <command> --json | Deferred: safe input validation required |
| show_sandbox_result | policy-scout sandbox <sandbox_id> --json | Deferred: migration planning required |
| list_sandbox_results | (command to be defined) | Deferred: storage design required |
| show_approval | policy-scout approvals show <approval_id> --json | Deferred: security review required |
| list_approvals | policy-scout approvals list --json | Deferred: security review required |

---

## 9. Argument Validation Rules

### ID Validation

- **event_id**: Must match canonical prefix `evt_` followed by alphanumeric characters
- **report_id**: Must match canonical prefix `report_` followed by alphanumeric characters
- **sandbox_id**: Must match canonical prefix `sbx_` followed by alphanumeric characters
- **approval_id**: Must match canonical prefix `appr_` followed by alphanumeric characters

### Limit Validation

- **limit**: Must be bounded between 1 and 1000
- **Default limit**: 50 if not specified
- **Reject**: Negative values, zero, values > 1000

### Type Validation

- **report_type**: Must be one of command_decision, sandbox_result, sweep_result, or empty for all
- **event_type**: Must be a known event type or empty for all
- **Reject**: Unknown types, arbitrary strings

### Target Validation

- **cleanup target**: Must be one of demo, sandbox, sandbox-results
- **Reject**: Arbitrary strings, paths, or other values

### Command String Validation (deferred)

- **check_command**: Must be validated for shell injection before passing to CLI
- **Reject**: Shell metacharacters outside safe patterns, pipe operators, command chaining

### No Freeform Input

- No frontend-provided argv arrays in v0
- No freeform command strings in v0 dashboard path
- All inputs must be validated against known patterns

---

## 10. Output Parsing Rules

### JSON Parsing

- Parse stdout as JSON
- Treat JSON parse errors as "Invalid JSON response from CLI"
- Handle missing fields gracefully (defensive coding)
- Do not invent fields not present in CLI JSON

### Exit Code Interpretation

- **Exit code 0**: Success, parse JSON
- **Exit code 10**: Risky/approval/sandbox decision (valid data for check/run, should not occur in read-only commands)
- **Exit code 20**: Denied (valid data for check/run, should not occur in read-only commands)
- **Exit code 30**: Error, display error message from stderr
- **Exit code 40**: Policy/config error, display error message
- **Exit code 50**: Audit logging error, display error message
- **Exit code 60**: Sandbox error, display error message
- **Exit code 70**: Sweep error, display error message

**Key rule:** Expected non-zero safety exit codes (10, 20) are valid data when the command intentionally returns risky/denied status. They are not crashes.

### Stderr Handling

- Never parse stderr for secrets without redaction
- Display safe error summary to user
- Include exit code and command label in error display
- Include could_not_verify flag when relevant

### Raw JSON Preservation

- Preserve raw JSON object internally for debugging only if redacted and local
- UI components should consume typed parsed objects, not shell output strings
- Never display raw JSON to end users

---

## 11. Error and Exit-Code Handling

### Error Display

- Show error messages in dedicated error panel
- Preserve error context (which command failed, what was the error)
- Include: command label, exit code, safe stderr summary, could_not_verify flag
- Offer retry button for transient errors
- Never hide errors or silently fall back to unsafe behavior

### Rust Wrapper Error Handling

- Reject invalid commands before calling CLI
- Validate arguments before passing to CLI
- Return structured errors (not raw strings)
- Never expose raw shell errors to frontend
- Map CLI exit codes to structured error types

### CLI Error Handling

- Exit code 0: Success, parse JSON
- Exit code 10/20: Risky/denied (should not occur in read-only commands, but treat as valid data if they do)
- Exit code 30+: Error, display error message from stderr
- JSON parse error: Display "Invalid JSON response from CLI"
- Timeout: Display "CLI command timed out"
- Missing field: Display "Unexpected JSON response format"

---

## 12. Redaction Display Boundary

### Placeholder Display

- Display redaction placeholders as-is (e.g., `<redacted:possible_token>`)
- Style as protected evidence (monospace, muted, shield icon)
- Not as errors or warnings

### Redaction Indicator

- Show "redaction applied" indicator when redaction_applied flag is true
- Use amber/gold color for prominence
- Place prominently in report/event detail views

### Privacy Rules

- Never attempt to decode or reverse redaction
- Never cache raw secrets in memory
- Never display raw secrets from JSON responses
- Never log raw secrets to console
- Never include secrets in error messages
- Never store secrets in local storage
- Treat all JSON responses as potentially containing redacted data

### File Path Display

- Display file paths as-is from CLI JSON
- CLI already normalizes home paths to ~ where practical
- Do not attempt to resolve paths to absolute paths (privacy risk)
- Trust the CLI's path normalization

---

## 13. Local-First Data Boundary

### Data Locations

All durable state stays local under ~/.local/share/policy-scout/:

- audit.db (SQLite primary)
- audit.jsonl (JSONL secondary)
- approvals.jsonl
- reports/
- sandboxes/
- migrations/
- backups/
- sweeps/

### No Remote Access

- Adapter must not access cloud services
- Adapter must not access remote dashboards
- Adapter must not access hosted policy engines
- All data stays local unless user explicitly exports

### No Direct File Access

- UI never reads audit.db directly
- UI never reads report files directly
- UI never reads approval files directly
- All data access through CLI JSON commands

---

## 14. No Raw Database/Filesystem Access Rule

### Database Access Forbidden

- UI must never query SQLite audit.db directly
- UI must never inspect report files directly
- UI must never read approval files directly
- All data access through CLI JSON commands

### Filesystem Access Forbidden

- UI must never read arbitrary files
- UI must never write arbitrary files
- UI must never browse filesystem
- All file access through CLI commands when implemented

### Rationale

- CLI applies redaction before JSON output
- CLI enforces policy boundaries
- CLI provides audit trail
- Direct access bypasses all safety layers

---

## 15. First Implementation Sequence

### Phase 1: Rust Wrapper (future)

- Implement Rust command wrapper with allowlist
- Add unit tests for command validation
- Add integration tests for CLI subprocess calls
- Ensure wrapper rejects invalid commands
- Ensure wrapper returns structured errors
- Verify wrapper never exposes raw shell errors

### Phase 2: Tauri Scaffolding (future)

- Initialize Tauri v2 project
- Configure minimal capabilities
- Integrate Rust wrapper
- Set up basic window/navigation
- Do not implement screens yet

### Phase 3: Read-Only Screens (future)

- Implement get_doctor_status screen
- Implement get_data_status screen
- Implement list_reports/show_report screens
- Implement list_audit_events/show_audit_event screens
- Implement get_audit_stats screen
- Implement get_cleanup_dry_run screen
- Add navigation between screens
- Add error handling
- Add redaction display

### Phase 4: Sweep and Eval Screens (future)

- Implement run_sweep_project screen
- Implement run_sweep_quick screen
- Implement run_eval screen
- Add loading states for long-running commands
- Add user-triggered scan controls

### Phase 5: Testing (future)

- Add end-to-end tests for each screen
- Add error handling tests
- Add redaction tests
- Verify JSON contract compatibility
- Verify CLI subprocess integration
- Verify no arbitrary command execution surface

### Phase 6: Polish (future)

- Improve UI/UX
- Add loading states
- Add refresh controls
- Add dark mode support
- Add keyboard shortcuts

### Stop Before

- Stop before approvals, sandbox migration, deletion, or run-command UI
- These require v1 design, security review, and proven read-only UI

---

## 16. Test Strategy for Future Adapter

### Unit Tests

- Test command builder allowlist rejects invalid commands
- Test command builder accepts only allowlisted commands
- Test argument validation rejects unsafe values
- Test cleanup target whitelist
- Test report/event ID validation
- Test limit bounding

### Integration Tests

- Test stdout JSON parse success for all allowlisted commands
- Test stderr safe error handling
- Test expected exit codes do not crash UI
- Test CLI subprocess integration
- Test Rust wrapper error propagation

### Security Tests

- Test no arbitrary command function exists
- Test no general shell plugin access
- Test no direct SQLite access
- Test no direct file access
- Test redaction placeholders preserved
- Test raw secrets never displayed

### Manual Smoke Tests

- Test first screen against installed policy-scout
- Test error handling with invalid commands
- Test redaction display with redacted data
- Test exit code interpretation for risky/denied outcomes

---

## 17. Open Questions Before Scaffolding

### Packaging

- Should Policy Scout be bundled with Python runtime or assume system Python?
- Should sidecar packaging be used?
- Platform-specific considerations?

### JSON API v1

- Should schema_version be added to all JSON outputs before UI implementation?
- Should run --json shapes be unified (allowed vs blocked paths)?
- Should eval run --json execution_time_ms be aliased to duration_ms?

### Mutation Screens

- Should the UI allow command input for check or use pre-defined templates?
- How should approval flow work (via CLI or direct UI call)?
- Should sandbox migration be one-click or multi-step confirmation?

### Performance

- Acceptable latency for CLI subprocess calls?
- Should UI cache CLI responses or always refresh?
- How to handle long-running commands (sweep, eval)?

### Accessibility

- Accessibility requirements?
- Keyboard-only navigation?
- Screen reader support?

### Internationalization

- Multiple language support?
- Handle CLI error messages in different languages?

---

## 18. Implementation Handoff Checklist

### Before Phase 1 (Rust Wrapper)

- [ ] JSON Shape Consistency Review v1 completed and reviewed
- [ ] JSON contract tests passing for all read-only commands
- [ ] JSON API v1 design documented (if needed before mutation screens)
- [ ] Rust wrapper requirements finalized
- [ ] Command allowlist finalized
- [ ] Security review of subprocess boundary
- [ ] Privacy review of redaction strategy
- [ ] Packaging decision made (or deferred with rationale)

### Before Phase 3 (Read-Only Screens)

- [ ] Rust wrapper implemented and tested
- [ ] Tauri scaffolding configured with minimal capabilities
- [ ] CLI subprocess integration verified
- [ ] JSON parsing tested for all read-only commands
- [ ] Error handling strategy implemented
- [ ] Redaction display implemented

### Before Phase 6 (Mutation Screens)

- [ ] Read-only screens stable and tested
- [ ] JSON API v1 design complete
- [ ] Schema registry implemented (if needed)
- [ ] Approval flow security reviewed
- [ ] Sandbox migration security reviewed
- [ ] High-friction confirmation dialogs designed
- [ ] Rollback mechanisms tested (for cleanup)

### Before Commit

- [ ] No frontend files created
- [ ] No Rust files created
- [ ] No Tauri scaffolding created
- [ ] No dependencies added
- [ ] No Python behavior changed
- [ ] No CLI JSON shapes changed
- [ ] No local HTTP API added
- [ ] No MCP/editor integration added
- [ ] Spec reviewed and approved
