# Changelog

Per-pass change detail lives in Git history (`git log --oneline`). This file
records significant milestones. v0.1 through v0.3.8 are consolidated below;
v0.3.9 entries reflect the current baseline.

## v0.3.9

### Added
- MIT license
- SECURITY.md with vulnerability reporting path
- `policy-scout-relay.py` — Lattica hub relay with startup backfill
- VS Code / Cursor extension source (`ui/vscode/`) — sweep diagnostics, hook
  management, MCP server registration
- Vendored Fossic 1.8.1 PyO3 binding (`vendor/fossic/`)
- Lattica integration Track A confirmed live (4 Tauri commands shelling out to
  policy-scout CLI)
- CLI JSON output on approvals/lockdown, `set-timeout` subcommand, approval expiry

### Changed
- CI: replaced private git dep with local vendor build
- Docs baseline: removed ~40 stale design docs, rewrote core docs to match v0.3.9
- `.gitignore`: exclude internal agent coordination files and editor lock files

---

## v0.1 – v0.3 (consolidated)

### Added
- Decision Check UI in Tauri desktop dashboard (check-only, never executes)
- Rust `check_command` adapter for `policy-scout check --json` CLI invocation
- TypeScript current-contract types for Decision Check JSON response
- Static Decision Check card shell with command input and FAQ buttons
- Tauri invoke wiring for Decision Check with live CLI data
- "NOT EXECUTED" result marker prominently displayed on all check results
- Frontend validation for empty/whitespace/NUL/length on command input
- Guided FAQ prompt behavior (populates input/explanation, no auto-check)
- Native smoke checklist section for Decision Check verification
- Decision Check QA section in ui/desktop/README.md
- Audit Events empty-state copy polish with actionable guidance

### Fixed
- Audit Events rendering regression (v0.3.4): argument casing mismatch (eventType vs event_type) and response shape mismatch (CLI array vs expected {events: [...]}) fixed before push (commit 0ebc137)

### Implementation Notes
- Decision Check is check-only — no command execution, approval, sandbox migration, or cleanup deletion UI
- Rust adapter validates command_text (max length, rejects empty/whitespace/NUL)
- CLI remains policy authority — UI is a viewer only
- CI green: pytest 621 passed, cargo test 18 passed, npm build success
- Native smoke documented with Decision Check section and v0.3.4 audit events finding note

---

## v0.1-alpha

### Added
- Command classifier and policy engine with registry-backed matching
- SQLite audit store as primary queryable persistence
- JSONL audit stream for debug/export
- Query helpers for audit timeline/history (list_recent, list_by_request_id, etc.)
- Critical audit write flag for fail-safe execution
- CLI SQLite integration tests for check, run, approvals, sweep, sandbox
- Audit query CLI commands (list, show, request, type, stats)
- JSON output support for audit CLI commands
- Report CLI commands (list, show, export)
- JSON output support for report list/show
- Redaction applied on read for report CLI output
- Approval queue for command execution requests
- Approval-to-execution flow with `--approval <approval_id>` flag
- Approval validation: status, scope, command match, CWD match, expiration
- Policy re-evaluation before execution (cannot bypass DENY or SANDBOX_FIRST)
- Approval status transitions: approved_once → executed/failed
- Audit events for approval execution lifecycle (ApprovalExecutionStarted, ApprovalExecutionCompleted, ApprovalExecutionFailed)
- Self-approval protection: Local human CLI users can approve their own requests, but agents and automated actors cannot approve their own requests
- Audit clarity: original_policy_decision and execution_route preserved in audit events
- npm, pnpm, yarn, and bun sandbox install review workspaces
- Sandbox migration command: `policy-scout sandbox migrate <sandbox_id>`
- Migration copies package-manager-specific lockfiles (npm: package-lock.json, npm-shrinkwrap.json; pnpm: pnpm-lock.yaml; yarn: yarn.lock; bun: bun.lockb, bun.lock)
- Migration never copies node_modules or arbitrary files
- Migration creates backups before overwriting host files
- Migration blocked on high/critical findings
- Migration requires explicit confirmation (unless --yes)
- Migration supports --dry-run for preview
- Migration audit events: SandboxMigrationRequested, Planned, Started, Completed, Blocked, Failed
- Scout Reports in Markdown and JSON formats
- Project sweep for suspicious trace detection
- Quick system sweep for local environment signal checks (Linux-first)
- Quick sweep checks: listening ports, suspicious processes, shell profiles, package manager configs, temp files, environment variables
- Quick sweep findings are severity/confidence-aware with categories: open_port, suspicious_process, shell_profile_change, package_manager_config, credential_exposure_signal, suspicious_temp_file
- Quick sweep output is redaction-safe and does not print secret values
- Eval harness for regression testing
- Policy-gated `run` command with direct executor
- Risk band derivation from risk scores
- CLI smoke tests for main flows
- README with demo sequence and v0.1 limitations
- Eval suite expansion v1: 14 new eval cases (30 → 44 total) covering credential-adjacent commands (.npmrc, id_ed25519, SECRET grep, AWS credentials), safe inspection (git status/log/diff, head README.md), package install variants (npm --save-dev, pnpm install, yarn install, bun install), network execution (sh -c wget), and destructive home deletion (rm -rf ~)
- AWS credentials pattern added to classifier for credential-adjacent detection
- pnpm.install, yarn.install, bun.install registry entries added for install command classification
- Report/Audit UX Polish v1: Markdown reports now include explicit "Redaction Applied" section explaining secret redaction
- Report/Audit UX Polish v1: command_decision JSON reports include created_at field (ISO timestamp)
- Report/Audit UX Polish v1: audit show human output includes redaction note and pretty-printed structured data (JSON mode unchanged)
- Report/Audit UX Polish v1: audit stats includes first/last event timestamps (human and JSON modes)
- Report/Audit UX Polish v1: No policy/classifier/registry semantics changed, JSON output remains machine-readable
- Policy Scout Doctor v1: Added `policy-scout doctor` command for health diagnostics
- Policy Scout Doctor v1: Checks CLI import health, Python version compatibility, Policy Scout version
- Policy Scout Doctor v1: Checks command_registry.yaml (15 entries), default_policy.yaml (11 entries), eval_cases.yaml (44 entries)
- Policy Scout Doctor v1: Checks audit store and report directory availability (read-only, no mutation)
- Policy Scout Doctor v1: Checks optional package manager availability (npm, pnpm, yarn, bun)
- Policy Scout Doctor v1: Human-readable output by default, JSON with --json
- Policy Scout Doctor v1: No network access, no system mutation

### Fixed
- Hardcoded `risk_band` in DecisionIssued event now derived from risk_score
- Replaced deprecated `datetime.utcnow()` with timezone-aware UTC
- All timestamp generation centralized in `core/ids.py`
- `policy-scout run` now fails safe if critical audit persistence fails
- CLI SQLite integration tests with proper subprocess environment setup
- Quick system sweep hardening v1:
  - ss/netstat parser fixture hardening
  - granular could_not_verify for unavailable tools/platform limitations
  - quick system sweep report metadata uses system_quick_sweep
  - credential exposure assessment no longer hardcoded to none_detected
  - SweepCompleted audit summary count fixed
  - process command redaction broadened for flag/env/bearer/query-token forms
  - home path normalization for shell profile and package-manager config findings
  - UnicodeDecodeError handling for shell profiles and package-manager config readers
- Quick system sweep hardening v2:
  - netstat header-only/no-data regression fix
  - temp filename/path privacy redaction for token-like filenames
  - cautious open-port wording (no compromise claims)
  - 10 new regression tests for hardening behavior
- Registry validation hardening v1:
  - empty YAML rejected
  - non-dict top-level YAML rejected
  - commands/policies must be lists
  - required id/title checked before dataclass construction
  - file path included in validation errors
  - entry IDs included in validation errors where available
  - policy priority type/range validation (int, 0-1000)
  - version type/range validation (int, >= 1)
  - match/exclude block key validation
  - recommended_controls validation against canonical set
  - 12 new regression tests for validation behavior

### Implemented Commands
- `policy-scout check` - Analyze commands without executing
- `policy-scout run` - Execute commands through policy gate
- `policy-scout approvals list/show/approve/deny` - Manage approval requests
- `policy-scout sandbox` - Run package installs in review workspace
- `policy-scout sweep project` - Scan project for suspicious traces
- `policy-scout eval run` - Run evaluation suite

### Current Limitations
- Only npm sandbox install implemented (pnpm/yarn/bun deferred)
- No Docker containment
- Sandbox is a review workspace, not perfect malware containment
- No migration command yet
- No Tauri UI yet
- No MCP/editor integrations yet
- Redaction is regex-based and may miss novel secrets
- No configurable audit retention policy
- No audit export to other formats
