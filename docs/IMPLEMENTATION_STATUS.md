# Policy Scout Implementation Status

## Version
v0.3.7

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
- `policy/management/validator.py` - Policy YAML schema validation
- `policy/management/simulator.py` - Decision simulation against command history
- `policy/management/history_tester.py` - Regression tests against audit history
- `policy/management/policy_commit.py` - Policy change commit with rollback support
- `policy/management/project_override.py` - Per-project policy override files

### Audit
- `audit/store.py` - Dual-write audit store (SQLite primary, JSONL secondary)
- `audit/sqlite_store.py` - SQLite audit persistence with query helpers
- `audit/jsonl_writer.py` - JSONL audit writer for debug/export
- `audit/events.py` - Audit event models (includes supply chain, git, scan, response, integrity events)
- `audit/redaction.py` - Secret redaction utilities
- `audit/chain_verifier.py` - Tamper-evident HMAC chain verification

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
- `sandbox/general/namespace_sandbox.py` - Linux namespace sandbox (unshare --mount --pid --net --user)
- `sandbox/general/overlay_fs.py` - OverlayFS setup and diff extraction
- `sandbox/general/strace_runner.py` - strace-based syscall capture
- `sandbox/general/syscall_analyzer.py` - Syscall log analyzer (network, file, process signals)
- `sandbox/general/behavior_report.py` - Behavior report builder
- `sandbox/general/prereqs.py` - Prerequisite checker for namespace sandbox

### Sweep
- `sweep/engine.py` - Sweep orchestration
- `sweep/package_scripts.py` - Package script checks
- `sweep/workflows.py` - GitHub workflow checks
- `sweep/executables.py` - Executable file checks
- `sweep/javascript_patterns.py` - JS pattern checks
- `sweep/shell_scripts.py` - Shell script checks
- `sweep/credentials.py` - Credential reference checks
- `sweep/repo_changes.py` - Repository mutation checks
- `sweep/prompt_injection.py` - Prompt injection detection in tool definitions, YAML, and Markdown

### Secret Scanning
- `scan/engine.py` - Scan orchestration with per-file and per-commit modes
- `scan/file_scanner.py` - File-level secret pattern matching
- `scan/git_scanner.py` - Git history secret scanning
- `scan/patterns.py` - Pattern registry loader (data/secret_patterns.yaml)
- `scan/entropy.py` - Shannon entropy scorer for high-entropy string flagging
- `scan/guidance.py` - Remediation guidance per finding type

### Threat Intel
- `intel/adapter.py` - Composable intel chain with local + remote tiers
- `intel/local/known_bad.py` - Local known-bad package registry
- `intel/local/typosquatting.py` - Typosquatting distance checks against popular packages
- `intel/local/lockfile_integrity.py` - Lockfile hash verification
- `intel/remote/npm_advisories.py` - npm security advisories API client
- `intel/remote/osv.py` - OSV (Open Source Vulnerabilities) API client
- `intel/remote/cache.py` - Response cache for remote intel queries

### Supply Chain Detection
- `supply_chain/js_analyzer.py` - Multi-layer JS static analysis (comment strip, base64 decode-and-recurse, 8 pattern families, escalation rules)
- `supply_chain/py_analyzer.py` - Python AST-based lifecycle script analysis
- `supply_chain/dep_confusion.py` - Dependency confusion signal detection
- `supply_chain/transitive.py` - Transitive npm dependency tree analysis via intel adapter
- `supply_chain/publish_anomaly.py` - Publish anomaly detection via npm registry metadata (opt-in)
- `supply_chain/patterns/js_patterns.yaml` - JS attack pattern definitions
- `supply_chain/patterns/py_patterns.yaml` - Python attack pattern definitions

### Git Integration
- `git/context.py` - Git repository context (branch, HEAD, staged files, remotes)
- `git/staged_scanner.py` - Staged file secret scanning before commit
- `git/lockfile_diff.py` - Lockfile change analysis for suspicious package additions
- `git/hooks.py` - Git hook installation and management

### Watch Mode
- `watch/daemon.py` - Background filesystem watch daemon
- `watch/fs_watcher.py` - inotify-based file event stream
- `watch/event_router.py` - Event routing and policy-matched alerting
- `watch/watch_config.py` - Watch configuration (paths, patterns, thresholds)

### Incident Response
- `response/playbooks.py` - Playbook loader and executor (data/playbooks.yaml)
- `response/lockdown.py` - Lockdown steps (kill processes, revoke tokens, notify)
- `response/preserve.py` - Evidence preservation (copy audit log, snapshot workspace)
- `response/clearance.py` - Clearance confirmation before resuming normal operation

### MCP Server
- `server/mcp_server.py` - MCP protocol server (stdio transport)
- `server/tool_definitions.py` - Tool schema definitions exposed to MCP clients
- `server/handlers.py` - Tool call dispatch and result formatting
- `server/session.py` - Session state and context tracking

### Integrity
- `integrity/registry_manifest.py` - Registry file hash manifest generation and verification
- `integrity/startup_check.py` - Startup integrity check against stored manifest

### Canary Tokens
- `canary/tokens.py` - Canary token generation (URL, DNS, file-based)
- `canary/installer.py` - Token placement in project files and directories
- `canary/checker.py` - Token exfiltration detection

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
- npm, pnpm, yarn, and bun sandbox installs implemented (PM-aware snapshots, pnpm transitive analysis)
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
- `audit list --json` and `audit type --json` return `{ events, total_count }` with `--limit` and `--offset` support
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
- Tauri desktop UI (ADR-008 complete through Phase 5), located in `ui/desktop/`
  - **Policy Scout CLI remains the authority. Tauri UI is a read-only / check-only surface.**
  - Rust backend (`src-tauri/src/lib.rs`) with 15 command wrappers:
    - `get_doctor_status` → `policy-scout doctor --json`
    - `get_data_status` → `policy-scout data status --json`
    - `list_reports_filtered(limit, offset, report_type?)` → `policy-scout report list --json --limit <n> --offset <n> [--type <type>]`
    - `show_report(report_id)` → `policy-scout report show --json <report_id>`
    - `get_audit_stats` → `policy-scout audit stats --json`
    - `list_audit_events_filtered(limit, offset, event_type?)` → `policy-scout audit list --json --limit <n> --offset <n>` (default) or `policy-scout audit type --json --limit <n> --offset <n> <event_type>` (filtered)
    - `show_audit_event(event_id)` → `policy-scout audit show --json <event_id>`
    - `get_cleanup_dry_run(target)` → `policy-scout data cleanup --target <target> --dry-run --json` (target allowlist: demo, sandbox, sandbox-results; always dry-run)
    - `run_eval` → `policy-scout eval run --json`
    - `run_sweep_quick` → `policy-scout sweep quick --json`
    - `run_sweep_project` → `policy-scout sweep project --json`
    - `list_sandbox_results` → `policy-scout report list --json --type sandbox_result --limit 5` (fixed; pagination pending)
    - `show_sandbox_result(report_id)` → `policy-scout report show --json <report_id>`
    - `get_policy_overview` → `policy-scout policy show --json`
    - `run_policy_validate` → `policy-scout policy validate --json`
  - ID arguments (`report_id`, `event_id`) validated in Rust: prefix check, character allowlist, shell metacharacter rejection
  - Audit event type filter validated in Rust against full 25-type allowlist; 12-type user-visible subset shown in dropdown
  - Limit validated in Rust against `[5, 10, 25, 50]` allowlist; offset validated ≤ 10,000
  - Cleanup target validated in Rust against 3-value allowlist (demo, sandbox, sandbox-results); `--dry-run` always included
  - TypeScript types split into `ui/desktop/src/types/` by domain (reports, audit, sandbox, sweep, doctor, eval, policy); strict mode enabled; no `any` fields
  - JSON Schema contracts in `ui/desktop/src/contracts/` validated by `tests/test_json_contracts.py` against live CLI output and mock fixtures
  - Mock fixtures in `ui/desktop/src/mocks/` serve as fallback in browser preview (`npm run dev`)
  - React/TypeScript frontend with `App.tsx` owning state and invoke calls
  - Current dashboard cards and views:
    - Overview Status Strip (cross-card summary)
    - Doctor Status
    - Data Status
    - Reports List (paginated: limit selector + prev/next + type filter)
    - Report Detail
    - Audit Stats
    - Audit Events List (paginated: limit selector + prev/next + type filter)
    - Audit Event Detail
    - Cleanup Dry-Run (demo, sandbox, sandbox-results targets)
    - Eval Results
    - Quick Sweep
    - Project Sweep
    - Sandbox Results List (fixed --limit 5; pagination pending — step 6)
    - Sandbox Result Detail
    - Policy Overview
    - Policy Validate
  - Shared components: StatusPill, EvidenceText, RedactionNotice, DetailHeader, SweepResultPreview, BoundaryNote
  - Visual system: calm dark theme, CSS variables, evidence-safe display, redaction styling
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
    - `npm run dev` — browser/Vite preview with mock fixtures; all cards render without native runtime
    - `npm run tauri dev` — native runtime with live CLI-backed data
    - `npm run build` — frontend build check (tsc strict + vite)
    - `cd src-tauri && cargo check && cargo test` — Rust compile + 18 validator unit tests
  - Known limitations:
    - Native click-level interaction requires manual verification (see `docs/compressed/TAURI_NATIVE_MANUAL_SMOKE_CHECKLIST_SOURCE.md`)
    - No project path selection for project sweep (hardcoded to CWD)
    - Sandbox Results List still uses fixed `--limit 5` — no pagination yet
    - No packaged installer; requires native Tauri build
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

### Near-term (no plans written yet)
- Sandbox Results List pagination — Tauri UI; `list_sandbox_results` still uses fixed `--limit 5` (boundary doc step 6)
- Client-side severity filter on Sweep findings preview (boundary doc step 7)
- Editor integrations (VS Code, Cursor)
- Packaged desktop installer

### Future
- Docker containment for sandbox
- ML-based secret detection
- Remote approval service
- Configurable audit retention policy
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

- Total Python tests: 1145 (as of v0.3.7)
- Rust unit tests: 18 (validator allowlist tests in `src-tauri/src/lib.rs`)
- Prior milestones (cumulative):
  - Plans 01–13 complete: 1098 Python tests (as of v0.3.3)
  - ADR-008 (JSON contracts, strict types, browser mocks, pagination, policy cards): added contract/pagination tests
  - v0.3.6–v0.3.7 (pnpm/bun sandbox, data cleanup deletion, audit pagination): 1098 → 1145

## CI Coverage

GitHub Actions (`ci.yml`) runs two parallel jobs on push/PR to main:

- **`test`** — Python 3.12, `pip install -e ".[dev]"`, doctor JSON, eval run, pytest (1145 tests as of v0.3.7)
- **`tauri-desktop`** — Node 22 + `npm ci` + `npm run build` (tsc strict + vite); then Rust stable + `cargo check` + `cargo test` (18 Rust validator unit tests). Requires `libwebkit2gtk-4.1-dev`, `libappindicator3-dev`, `librsvg2-dev`, `patchelf` on the ubuntu runner.

No native Tauri bundle (`npm run tauri build`) in CI. Bundle requires additional system deps and is not part of this workflow.

## Current Alpha Status

**Status**: v0.3.7-alpha

**Stability**: Alpha - Core functionality works, but not production-ready

**Pass Rate**: 100% on eval suite (44/44)

**Known Issues**:
- Redaction is regex-based only
- Sandbox Results List in UI still uses fixed `--limit 5` (pagination in progress)
- No packaged installer; requires local build

**Next Milestones**:
1. Sandbox Results List pagination (Tauri UI step 6)
2. Client-side severity filter on Sweep findings preview (step 7)
3. Editor integrations (VS Code, Cursor)
4. Packaged desktop installer

## v0.3.6–v0.3.7 Milestone Summary

**All prepared feature plans and ADR-008 phases complete.**

- pnpm/yarn/bun sandbox execution shipped (PM-aware snapshots, pnpm transitive dep analysis)
- Data cleanup deletion path shipped (`--apply` flag, confirmation prompt, path-safe execute)
- ADR-008 Phases 1–5 complete:
  - Phase 1: JSON Schema contracts + mock fixtures for all 14 Tauri commands
  - Phase 2: TypeScript strict mode, domain-split types, `noUncheckedIndexedAccess`
  - Phase 3: Browser preview (`npm run dev`) now shows mock data for all cards
  - Phase 4: Reports List and Audit Events List paginated (limit selector + prev/next + type filter)
  - Phase 5: Policy Overview and Policy Validate cards added
- `audit list` and `audit type` CLI gained `--offset` and `{ events, total_count }` JSON shape
- `report list` CLI gained `--offset` and `{ reports, total_count, offset }` JSON shape
- Python tests: 1098 → 1145; Rust tests: 18 (unchanged)
- CI green on both jobs

**Remaining Tauri pagination work:**
- Sandbox Results List (`list_sandbox_results`) still hardcoded at `--limit 5` — pagination is next

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

## Tier 2/3 Feature Plans — v0.2.1 through v0.3.3

All 13 feature plans implemented and shipped. Summarized below.

| Plan | Title | Version | Commit |
|------|-------|---------|--------|
| 01 | Watch Mode | v0.2.1 | — |
| 02 | Threat Intel | v0.2.2 | — |
| 03 | Supply Chain Detection Depth | v0.3.3 | 5807d23 |
| 04 | Secret Scanning | v0.2.3 | — |
| 05 | Tamper-Evident Audit | v0.2.4 | — |
| 06 | MCP Server | v0.3.0 | — |
| 07 | Prompt Injection Detection | v0.3.1 | — |
| 08 | Broader Sandbox | v0.3.2 | a1fe3a3 |
| 09 | Incident Response | v0.3.2 | a1fe3a3 |
| 10 | Policy Management | v0.3.2 | a1fe3a3 |
| 11 | Desktop UI | v0.3.2 | a1fe3a3 |
| 12 | Git Integration | v0.3.2 | a1fe3a3 |
| 13 | Self Integrity | v0.3.2 | a1fe3a3 |

**Test count after all plans: 1098** (up from 621 pre-Tier 2/3)

**Remaining deferred work post-Tier 2/3:**
- pnpm/yarn/bun sandbox execution
- Tauri audit/report list pagination and filters
- Data cleanup deletion path (dry-run only today)
- Editor integrations (VS Code, Cursor)
