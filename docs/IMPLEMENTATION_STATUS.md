# Policy Scout Implementation Status

## Version
v0.1-alpha

## Implemented Commands

### policy-scout check
- Analyze commands without executing
- Returns policy decision, risk score, category, capabilities, and reasons
- Exit codes: 0 (success), 10 (risky), 20 (denied), 30 (error)

### policy-scout run
- Execute commands through policy gate
- Only executes ALLOW and ALLOW_LOGGED commands
- Blocks DENY, DENY_AND_ALERT, SANDBOX_FIRST, REQUIRE_APPROVAL
- Creates approval requests for REQUIRE_APPROVAL
- Recommends sandbox for SANDBOX_FIRST
- Supports `--approval <approval_id>` flag for one-time execution of approved commands
- Exit codes: 0 (success), 10 (risky/approval/sandbox), 20 (denied), 30 (error)

### policy-scout approvals
- `list` - Show pending approval requests
- `show <approval_id>` - Show approval details
- `approve <approval_id>` - Approve once
- `deny <approval_id>` - Deny once

### policy-scout sandbox
- Run package installs in temporary review workspace
- Currently supports npm only
- Inspects lifecycle scripts
- Captures manifest/lockfile diffs
- Generates Scout Reports
- Does not mutate host project without approval

### policy-scout sweep project
- Scan project for suspicious traces
- Checks package lifecycle scripts
- Checks GitHub workflows
- Checks executable files
- Checks JavaScript patterns
- Checks shell scripts
- Checks credential references
- Generates Scout Reports

### policy-scout sweep quick
- Quick system signal scan (Linux-first, implemented and hardened)
- Checks listening ports (via ss/netstat) with header-only regression fix
- Checks suspicious development processes with broadened command redaction
- Checks recent shell profile changes with UnicodeDecodeError handling
- Checks package manager config files for tokens with UnicodeDecodeError handling
- Checks suspicious temp files with token-like filename redaction
- Checks sensitive environment variable names
- Severity/confidence-aware findings
- Redaction-safe output with home path normalization
- Report metadata uses system_quick_sweep type
- Credential exposure assessment dynamic (not hardcoded)
- SweepCompleted audit summary count fixed
- Generates Scout Reports

### policy-scout eval run
- Run evaluation suite
- 44 test cases covering command classification and policy decisions
- Reports pass rate and execution time
- Eval suite expansion v1: added 14 cases for credential-adjacent commands, safe inspection, package install variants, network execution, and destructive commands

### policy-scout doctor
- Run health diagnostics
- Checks CLI import health, Python version compatibility, Policy Scout version
- Checks command_registry.yaml, default_policy.yaml, eval_cases.yaml load successfully
- Reports registry entry counts (15 commands, 11 policies, 44 eval cases)
- Checks audit store and report directory availability
- Checks optional package manager availability (npm, pnpm, yarn, bun)
- Human-readable output by default, JSON with --json
- Read-only checks, no system mutation
- No network access

### policy-scout data
- `status` - Show local data status
- `cleanup` - Preview-only cleanup planning for low-risk temporary local state (v1 dry-run only)
- Reports data root path, all local state paths, and existence status
- Reports counts for reports, sandbox results, demo workspaces, approvals, audit events
- Human-readable output by default, JSON with --json
- Read-only checks, no system mutation
- No network access

## Implemented Modules

### Core
- `core/ids.py` - ID generation and timestamp utilities
- `core/request.py` - Command request model
- `core/decision.py` - Policy decision and risk score models
- `core/actor.py` - Actor model

### Classification
- `classify/shell_parser.py` - Shell command parsing
- `classify/command_classifier.py` - Command classification

### Registry
- `registry/loader.py` - Registry YAML loader with structure validation
- `registry/validator.py` - Registry validation with schema enforcement
- `registry/schemas.py` - Canonical taxonomies for validation
- Registry validation hardening completed (v1)
- Current valid registries load: command_registry.yaml (15 entries), default_policy.yaml (11 entries)
- Validation improvements: empty YAML rejected, non-dict top-level rejected, commands/policies must be lists, required fields checked before dataclass, file path in errors, entry IDs in errors, priority type/range validation, version type/range validation, match/exclude key validation, recommended_controls validation
- Eval suite expansion v1: added pnpm.install, yarn.install, bun.install registry entries for install command classification

### Policy
- `policy/engine.py` - Policy evaluation engine
- `policy/risk_scorer.py` - Risk scoring with components

### Audit
- `audit/store.py` - Dual-write audit store (SQLite primary, JSONL secondary)
- `audit/sqlite_store.py` - SQLite audit persistence with query helpers
- `audit/jsonl_writer.py` - JSONL audit writer for debug/export
- `audit/events.py` - Audit event models
- `audit/redaction.py` - Secret redaction utilities

### Approvals
- `approvals/store.py` - Approval request storage
- `approvals/models.py` - Approval request models

### Sandbox
- `sandbox/temp_workspace.py` - Temporary workspace creation
- `sandbox/package_files.py` - Package file copying
- `sandbox/npm_runner.py` - npm install execution
- `sandbox/lifecycle_inspector.py` - Lifecycle script inspection
- `sandbox/diff.py` - Manifest/lockfile diff capture
- `sandbox/result_writer.py` - Sandbox result persistence

### Sweep
- `sweep/engine.py` - Sweep orchestration
- `sweep/package_scripts.py` - Package script checks
- `sweep/workflows.py` - GitHub workflow checks
- `sweep/executables.py` - Executable file checks
- `sweep/javascript_patterns.py` - JS pattern checks
- `sweep/shell_scripts.py` - Shell script checks
- `sweep/credentials.py` - Credential reference checks
- `sweep/repo_changes.py` - Repository mutation checks

### Reports
- `reports/command_decision_report.py` - Command decision reports
- `reports/sandbox_report.py` - Sandbox result reports
- `reports/sweep_report.py` - Sweep result reports
- `reports/markdown_report.py` - Markdown report generation
- `reports/json_report.py` - JSON report generation

### Executor
- `executor/direct_executor.py` - Direct command execution
- `executor/models.py` - Execution result models

### Eval
- `evals/loader.py` - Eval case loader
- `evals/runner.py` - Eval suite runner
- `evals/report.py` - Eval report generation

### Doctor
- `doctor.py` - Health diagnostics for CLI, registries, data directories, and package managers

### Data
- `data_status.py` - Local data visibility and counts

### CLI
- `cli/main.py` - Main CLI entry point

## Current Limitations

### Sandbox
- npm sandbox install implemented
- pnpm/yarn/bun package installs classify as SANDBOX_FIRST but sandbox execution support is deferred
- No Docker containment
- Sandbox is a review workspace, not perfect malware containment
- Migration command implemented: `policy-scout sandbox <sandbox_id>`
- Migration copies package-manager-specific lockfiles (npm: package-lock.json, npm-shrinkwrap.json; pnpm: pnpm-lock.yaml; yarn: yarn.lock; bun: bun.lockb, bun.lock)
- Migration never copies node_modules or arbitrary files
- Migration creates backups before overwriting host files
- Migration blocked on high/critical findings
- Migration requires explicit confirmation (unless --yes)
- Migration supports --dry-run for preview
- Migration audit events: SandboxMigrationRequested, Planned, Started, Completed, Blocked, Failed

### Approvals
- Approval-to-execution flow implemented
- Approvals are local-only (no remote approval service)
- One-time execution with `--approval <approval_id>` flag
- Approval validation: status, scope, command match, CWD match, expiration
- Policy re-evaluation before execution (cannot bypass DENY or SANDBOX_FIRST)
- Approval status transitions: approved_once → executed/failed
- Audit events for approval execution lifecycle
- Self-approval protection: Local human CLI users can approve their own requests, but agents and automated actors cannot approve their own requests
- Audit clarity: original_policy_decision and execution_route preserved in audit events

### Audit
- SQLite audit store implemented as primary queryable persistence
- JSONL audit remains available as debug/export stream
- Critical audit write flag for fail-safe execution
- CLI SQLite integration tests for check, run, approvals, sweep, sandbox
- Audit query CLI commands (list, show, request, type, stats)
- JSON output support for audit CLI commands
- Report/Audit UX Polish v1: audit show human output includes redaction note and pretty-printed structured data, audit stats includes first/last event timestamps
- No configurable retention policy
- No audit export to other formats

### Reports
- Scout Reports generated for command decisions, sandbox results, project sweeps
- Reports written to local report root (~/.local/share/policy-scout/reports/)
- Markdown and JSON report formats
- Report CLI commands (list, show, export)
- JSON output support for report list/show
- Redaction applied on read for report CLI output
- Report/Audit UX Polish v1: Markdown reports now include explicit "Redaction Applied" section, command_decision JSON reports include created_at field
- No report deletion command
- No report retention policy
- No report export to other formats

### Sweep
- Quick system sweep implemented and hardened (v1 + v2)
- Sweep is project-only (no system-wide scanning beyond quick sweep)
- Quick sweep is Linux-first with platform limitation notes
- Quick sweep is evidence-gathering, not malware confirmation

### UI/Integration
- Experimental Tauri desktop UI (v0.2.x, read-only)
  - Located in `ui/desktop/`
  - **Policy Scout CLI remains the authority. Tauri UI is a read-only preview surface only.**
  - Rust backend (`src-tauri/src/lib.rs`) with 13 command wrappers:
    - `get_doctor_status` → `policy-scout doctor --json`
    - `get_data_status` → `policy-scout data status --json`
    - `list_reports_filtered(limit, report_type?)` → `policy-scout report list --json --limit <n> [--type <type>]`
    - `show_report(report_id)` → `policy-scout report show --json <report_id>`
    - `get_audit_stats` → `policy-scout audit stats --json`
    - `list_audit_events_filtered(event_type?)` → `policy-scout audit list --json --limit 10` (default) or `policy-scout audit type --json <event_type>` (filtered)
    - `show_audit_event(event_id)` → `policy-scout audit show --json <event_id>`
    - `get_cleanup_dry_run(target)` → `policy-scout data cleanup --target <target> --dry-run --json` (target allowlist: demo, sandbox, sandbox-results; always dry-run)
    - `run_eval` → `policy-scout eval run --json`
    - `run_sweep_quick` → `policy-scout sweep quick --json`
    - `run_sweep_project` → `policy-scout sweep project --json`
    - `list_sandbox_results` → `policy-scout report list --json --type sandbox_result --limit 5`
    - `show_sandbox_result(report_id)` → `policy-scout report show --json <report_id>`
  - ID arguments (`report_id`, `event_id`) validated in Rust: prefix check, character allowlist, shell metacharacter rejection
  - Audit event type filter validated in Rust against 12-value allowlist; no unvalidated strings reach CLI argv
  - Cleanup target validated in Rust against 3-value allowlist (demo, sandbox, sandbox-results); `--dry-run` always included; no real deletion path exposed
  - Adapter validation test plan: `docs/compressed/TAURI_ADAPTER_VALIDATION_TEST_PLAN_SOURCE.md`
  - React/TypeScript frontend with `App.tsx` owning state and invoke calls
  - Current dashboard cards and views:
    - Overview Status Strip (cross-card summary)
    - Doctor Status
    - Data Status
    - Reports List
    - Report Detail
    - Audit Stats
    - Audit Events List
    - Audit Event Detail
    - Cleanup Dry-Run (demo, sandbox, sandbox-results targets)
    - Eval Results
    - Quick Sweep
    - Project Sweep
    - Sandbox Results List
    - Sandbox Result Detail
  - Shared components: StatusPill, EvidenceText, RedactionNotice, DetailHeader, SweepResultPreview, BoundaryNote
  - `types.ts` provides loose current-contract TypeScript interfaces for CLI JSON shapes
  - Visual system: calm dark theme, CSS variables, evidence-safe display, redaction styling
  - Boundary note: "Read-only preview. Policy Scout CLI remains the authority."
  - Safety boundaries enforced:
    - No command execution UI
    - No approval resolution UI
    - No sandbox migration UI
    - No cleanup deletion (dry-run only)
    - No report/audit export or deletion UI
    - No arbitrary shell access or frontend-provided argv arrays
    - No direct SQLite or filesystem access from frontend
    - Sweeps are user-triggered only (no background scanning)
  - Dev workflow:
    - `npm run dev` — browser/Vite preview, static layout only, no live CLI data
    - `npm run tauri dev` — native runtime with live CLI-backed data
    - `npm run build` — frontend build check
    - `cd src-tauri && cargo check` — Rust compile check
  - Known limitations:
    - Native click-level interaction requires manual verification
    - No pagination/filtering for reports or audit event lists
    - No project path selection for project sweep
    - No strict JSON API v1 envelope (types are current-contract/loose)
    - Browser preview cannot load live Tauri invoke data
- No MCP/editor integrations yet
- No VS Code extension
- No Cursor extension

### Redaction
- Redaction is regex-based and may miss novel secrets
- No ML-based secret detection
- Temp filename redaction is heuristic (20+ alphanumeric strings, UUIDs, base64-like patterns)
- Unicode decode fallback does not attempt alternate encodings

### Registry
- Registry validation hardening completed (v1)
- Current valid registries load: command_registry.yaml (15 entries), default_policy.yaml (11 entries)
- Validation improvements: empty YAML rejected, non-dict top-level rejected, commands/policies must be lists, required fields checked before dataclass, file path in errors, entry IDs in errors, priority type/range validation, version type/range validation, match/exclude key validation, recommended_controls validation
- Eval suite expansion v1: added pnpm.install, yarn.install, bun.install registry entries for install command classification
- Unknown top-level keys are currently tolerated
- Reasons list structure not yet validated
- Recommended_next_action format not yet validated
- Regex validation checks compilation, not semantic intent
- YAML encoding validation is not explicit

## Deferred Features

### v0.2+
- pnpm/yarn/bun sandbox execution
- Tauri UI (v0.2.x experimental read-only UI is active; full UI deferred)
- MCP server
- Editor integrations
- Data cleanup deletion path (v1 dry-run planning implemented)
- Tauri: sandbox results read-only list/detail
- Tauri: audit/report list pagination and filters
- Tauri: Decision Check UI (check-only, not run)
- Tauri: manual native click verification pass

### Future
- Docker containment for sandbox
- ML-based secret detection
- Remote approval service
- Configurable audit retention
- Multi-user enterprise auth
- Community rule marketplace

## Known Technical Debt

- Registry validation hardening completed (schema validation layer added)
- Multiple learning pathways (duplication risk in eval system)
- No centralized error handling
- Some tests may depend on internet access (should be mocked)
- Deprecation warnings for datetime.utcnow() now fixed
- No performance profiling
- No benchmarking suite

## Development Notes

### CLI Invocation Patterns

- **Installed console script:** `policy-scout <command>` - Works from any directory after `pip install -e .`
- **Module invocation from repo root:** `python -m policy_scout.cli.main <command>` - Works from repo root only (current directory in sys.path)
- **Module invocation with PYTHONPATH:** `PYTHONPATH=/home/boop/Projects/policy-scout python -m policy_scout.cli.main <command>` - Works from any directory

Most CLI tests use `PYTHONPATH` intentionally for subprocess checkout isolation. Smoke tests (`test_cli_smoke.py`) do not set `PYTHONPATH` and inherit CWD — always run the full suite from the repo root: `cd /home/boop/Projects/policy-scout && python -m pytest`.

## Test Count

- Total tests: 621 (30 added in v0.2.x test suite expansions)
- Policy Scout Doctor v1: 8 new tests (doctor human output, doctor JSON output, registry counts, package manager warnings, no secrets printed, audit/report paths, help message)
- Policy Scout Data v1: 11 new tests (data human output, data JSON output, path existence, counts, override env vars)
- Report/Audit UX Polish v1: 4 new tests (redaction section, created_at, audit redaction note, audit time range)
- Quick sweep hardening v1/v2 tests: 10 new tests
- Registry validation hardening v1 tests: 12 new tests
- Eval suite expansion v1: 14 new eval cases (30 → 44)
- JSON contracts v1: 12 new tests (check JSON redaction, sandbox JSON redaction_applied, sweep JSON redaction_applied, report list created_at)
- Existing tests: 520 (no regressions, as of v0.1 accounting)

## CI Coverage

GitHub Actions (`ci.yml`) runs two parallel jobs on push/PR to main:

- **`test`** — Python 3.12, `pip install -e ".[dev]"`, doctor JSON, eval run, pytest (621 tests)
- **`tauri-desktop`** — Node 22 + `npm ci` + `npm run build` (tsc + vite); then Rust stable + `cargo check` + `cargo test` (12 Rust validator unit tests). Requires `libwebkit2gtk-4.1-dev`, `libappindicator3-dev`, `librsvg2-dev`, `patchelf` on the ubuntu runner.

No native Tauri bundle (`npm run tauri build`) in CI. Bundle requires additional system deps and is not part of this workflow.

## Current Alpha Status

**Status**: v0.1-alpha

**Stability**: Alpha - Core functionality works, but not production-ready

**Pass Rate**: 100% on eval suite (44/44)

**Known Issues**:
- Sandbox is npm-only (pnpm/yarn/bun sandbox execution deferred)
- Redaction is regex-based only
- Data cleanup is preview-only (no deletion path in v1)

**Next Milestones**:
1. Add pnpm/yarn/bun sandbox execution
2. Manual native click verification of Tauri UI cards — checklist at `docs/compressed/TAURI_NATIVE_MANUAL_SMOKE_CHECKLIST_SOURCE.md`
3. Tauri audit/report list pagination or filters
4. Decision Check + Guided FAQ UI (check-only, not run) — boundary spec at `docs/compressed/TAURI_DECISION_CHECK_GUIDED_FAQ_BOUNDARY_SOURCE.md`, CLI contract probe at `docs/compressed/TAURI_DECISION_CHECK_CLI_CONTRACT_SOURCE.md`, Rust adapter implemented (check_command wrapper added, 14 total wrappers), v0.3.3: TypeScript types + static card shell added, v0.3.4: Tauri invoke wired, result display with NOT EXECUTED marker, decision/risk styling, browser preview graceful error handling
5. Add MCP server
6. Add editor integrations
7. Add data cleanup deletion path (v1 dry-run planning implemented)

## v0.3.5 Notes

- v0.3.4 CI green (pytest 621 passed, cargo test 18 passed, npm build success)
- Native smoke documented with Decision Check section in TAURI_NATIVE_MANUAL_SMOKE_CHECKLIST_SOURCE.md
- Audit Events rendering regression found/fixed before push (argument casing + response shape mismatch, fix committed in 0ebc137)
- Decision Check QA section added to ui/desktop/README.md
- No new behavior in this pass (documentation/polish only)

## v0.3 Milestone Summary

**Decision Check is implemented as check-only.**

- UI can classify commands through `check_command` Rust adapter
- No command execution UI exists
- No approval resolution UI exists
- No sandbox migration UI exists
- No cleanup deletion UI exists (dry-run only)
- Native smoke checklist documented with Decision Check section
- Audit Events rendering contract issue found/fixed during native smoke
- CI green: pytest 621 passed, cargo test 18 passed, npm build success

**v0.4 next focus:**
- Shipping hardening (install docs, data path hardening)
- Report/audit polish
- Manual native click verification pass

**Recommendation**: Use for development and testing only. Not recommended for production use without additional hardening.

## v0.4.0 Shipping-Hardening Audit

**Fresh install and development setup audit completed.**

- Created `docs/INSTALL.md` with complete setup instructions:
  - System requirements (Python 3.12+, Node.js 22, Rust stable, Linux Tauri dependencies)
  - Python setup with virtual environment guidance
  - CLI verification commands (doctor, eval, check)
  - Desktop setup (npm install, build, Tauri system dependencies, cargo check/test)
  - Data locations and environment variable overrides
  - Green checkpoint command list
  - Native smoke checklist pointer
  - Safety boundaries (read-only UI, dry-run cleanup, no risky setup commands)
  - Troubleshooting (externally-managed Python, Tauri build failures, pytest from subdirectory)
- Updated `README.md` with pointer to `docs/INSTALL.md` and shipping model note
- Updated `ui/desktop/README.md` with pointer to root install docs and shipping model note
- Added shipping model documentation: CLI-first, desktop dogfooded
  - CLI is source of truth for policy decisions, audit, reports, sweeps, JSON contracts
  - Desktop app is optional read-only/check-only companion
  - Desktop app should be verified through CLI checks, tests, and native smoke before use
  - Decision Check remains check-only through bounded adapter
  - No command execution, approval resolution, sandbox migration, cleanup deletion, shell plugin, or arbitrary argv UI shipped in v0.4
- Added Desktop Dogfood Checklist to docs/INSTALL.md
- No new behavior introduced — documentation and audit only
- v0.4 focus remains shipping hardening (install/docs, data path clarity, repeatable verification)

## v0.4.1 Data Path + Empty-State Hardening Audit

**Data path and empty-state audit completed.**

- Verified canonical data directory: `~/.local/share/policy-scout/` by default
- Confirmed all environment variable overrides are documented and consistent with code:
  - `POLICY_SCOUT_AUDIT_DB_PATH` - SQLite database path
  - `POLICY_SCOUT_AUDIT_PATH` - JSONL file path
  - `POLICY_SCOUT_APPROVAL_PATH` - Approvals storage path
  - `POLICY_SCOUT_REPORT_ROOT` - Reports directory path
  - `POLICY_SCOUT_SANDBOX_ROOT` - Sandbox workspaces path
  - `POLICY_SCOUT_SWEEP_ROOT` - Sweep outputs path
  - `POLICY_SCOUT_MIGRATION_ROOT` - Migration backups path
  - `POLICY_SCOUT_BACKUP_ROOT` - General backups path
- Verified fresh install behavior with isolated temp data home:
  - `doctor --json` passes with warning for report directory (not created until first report)
  - `audit stats --json` returns `{"total_events": 0, "by_type": {}}`
  - `audit list --json` returns empty array `[]`
  - `report list --json` returns error: "No Scout Reports found. Run a Policy Scout command with --report, sandbox, or sweep first."
  - `data cleanup --dry-run` works safely on empty state
- Updated docs/INSTALL.md with detailed empty-state guidance and safe demo data generation commands
- Updated ui/desktop/README.md with empty-state behavior section
- Verified mature data behavior on current developer machine (18,330 audit events, reports list correctly)
- Verified UI empty-state copy is actionable and calm ("No reports found", "No sandbox results found")
- No deletion/apply behavior added
- Cleanup remains dry-run only
- No fake record generation on missing data

## v0.4.4 Dashboard Native Smoke Consolidation

**Native smoke checklist consolidation completed.**

- Consolidated `docs/compressed/TAURI_NATIVE_MANUAL_SMOKE_CHECKLIST_SOURCE.md` as the authoritative native dashboard smoke checklist for v0.4 CLI-first local alpha
- Reorganized checklist into ordered sections (A-M) for practical, runnable verification:
  - A. Preflight Gates (git status, pytest, doctor, eval, npm build, cargo check/test)
  - B. Launch Native App
  - C. Global Visual/Readability Checks
  - D. Overview / Doctor / Data Checks
  - E. Decision Check Checks
  - F. Reports Checks
  - G. Audit Checks
  - H. Cleanup / Eval Checks
  - I. Sweep Checks
  - J. Sandbox Results Checks
  - K. Browser Preview Checks
  - L. Negative Safety Checks
  - M. Recording Template
- Added explicit authoritative statement: "This is the authoritative, repeatable native QA path for the v0.4 CLI-first local alpha"
- Emphasized browser preview is not sufficient for native invoke validation
- Updated docs/INSTALL.md with pointer to consolidated native smoke checklist and emphasis on native runtime requirement
- Updated ui/desktop/README.md with pointer to consolidated native smoke checklist and emphasis on native runtime requirement
- No behavior changes — documentation consolidation only
- No new features added
- No CLI, Rust, or frontend code changes
- Future documentation candidates noted (not created in this pass):
  - Audit event anatomy detailed boundary doc
  - Sweep boundary detailed doc
  - Sandbox boundary detailed doc
  - Cleanup boundary detailed doc
- No broad cleanup of user data
- No new behavior introduced — documentation and audit only
- v0.4.1 focus: data path hardening, empty-state clarity, fresh install experience

## v0.4.5 Local Alpha Release Checklist

**Local alpha release checklist created.**

- Created `docs/LOCAL_ALPHA_RELEASE_CHECKLIST.md` as the authoritative release-readiness audit and checklist for v0.4.0 Local Alpha
- Classified known limitations as blocker or non-blocker:
  - Blockers: None identified
  - Non-blockers: Browser preview Tauri invoke limitation, native Tauri runtime requirement, no packaged installer, no approval/migration/deletion UI by design, manual native smoke, no full frontend automated tests, detailed boundary docs deferred, long findings capped in UI
- Documented release identity: Policy Scout v0.4.0 Local Alpha, CLI-first with optional dogfooded desktop dashboard
- Documented shipping model: CLI authority, desktop read-only/check-only, no execution/mutation/approval UI
- Documented required automated gates: pytest, doctor, eval, npm build, cargo check/test
- Documented required manual/native gates: native smoke checklist completion
- Documented safety boundary checklist: CLI authority, desktop read-only, no execution/mutation/approval UI, secret redaction
- Documented data/readiness checklist: local data paths, empty states, report/audit/evidence surfaces
- Documented CI/tag checklist: CI green, git clean, HEAD matches origin/main
- Documented rollback/undo guidance
- Documented final release decision template
- Recommended git tag: `v0.4.0`
- Discord/dev-log version: `v0.4.5` (for this checklist pass)
- No code changes — documentation and audit only
- No new features added
- No CLI, Rust, or frontend behavior changes
- Next step: Run checklist gates and decide tag readiness
