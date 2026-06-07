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
- Show local data status
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
- No Tauri UI yet
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
- Tauri UI
- MCP server
- Editor integrations
- Data cleanup command (planned)

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

## Test Count

- Total tests: 591
- Policy Scout Doctor v1: 8 new tests (doctor human output, doctor JSON output, registry counts, package manager warnings, no secrets printed, audit/report paths, help message)
- Policy Scout Data v1: 11 new tests (data human output, data JSON output, path existence, counts, override env vars)
- Report/Audit UX Polish v1: 4 new tests (redaction section, created_at, audit redaction note, audit time range)
- Quick sweep hardening v1/v2 tests: 10 new tests
- Registry validation hardening v1 tests: 12 new tests
- Eval suite expansion v1: 14 new eval cases (30 → 44)
- JSON contracts v1: 12 new tests (check JSON redaction, sandbox JSON redaction_applied, sweep JSON redaction_applied, report list created_at)
- Existing tests: 520 (no regressions)

## Current Alpha Status

**Status**: v0.1-alpha

**Stability**: Alpha - Core functionality works, but not production-ready

**Pass Rate**: 100% on eval suite (44/44)

**Known Issues**:
- Sandbox is npm-only (pnpm/yarn/bun sandbox execution deferred)
- Redaction is regex-based only
- No automated data cleanup (manual cleanup only)

**Next Milestones**:
1. Add pnpm/yarn/bun sandbox execution
2. Add Tauri UI prototype
3. Add MCP server
4. Add editor integrations
5. Add data cleanup command

**Recommendation**: Use for development and testing only. Not recommended for production use without additional hardening.
