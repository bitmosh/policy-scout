# AGENTS.md — Persistent Agent Reference

Loaded every session. Overrides default behavior where specified.

## Identity

You are **bandit**, building Policy Scout v0.1 alpha. This is a Python CLI-first, local-first safety harness for agent commands, package installs, and suspicious project activity.

## Reading Order

If context is lost, re-read in this order:
1. `docs/implementations/CORE_DOCTRINE_AND_BOUNDARIES.md`
2. `docs/implementations/POLICY_CLASSIFIER_AND_REGISTRY_SOURCE.md`
3. `docs/implementations/EXECUTION_SANDBOX_APPROVAL_SOURCE.md`
4. `docs/implementations/SWEEP_AUDIT_REPORTING_PRIVACY_SOURCE.md`
5. `docs/IMPLEMENTATION_STATUS.md`
6. `docs/implementations/IMPLEMENTATION_LOCKS.md`
7. `docs/agent/POLICY_SCOUT_DISCORD_PROTOCOL.md` (gates, channels)
8. The task you're working on

## Current Alpha State

Policy Scout v0.1 alpha is in active development. Key implementation milestones:
- Doctor command implemented (health diagnostics)
- Quick sweep implemented and hardened
- Eval suite: 44 test cases
- Command registry: 15 entries
- Default policy: 11 entries
- Full test suite: 554 passed
- Report list Created fields fixed
- GitHub gate scaffolding added (CI workflow, PR template, commit/bump gate)

## Versioning

`v<arc>.<sub-arc>.<pass>[letter]` — increment pass digit every PASS COMPLETE.
Developer signals sub-arc and arc bumps. Current: v0.0.0.

## Discord Gates

Full protocol: `docs/agent/POLICY_SCOUT_DISCORD_PROTOCOL.md`.

Ping #approve-this before: any commit, push, merge, destructive git, dependency install.
Never ping for: reads, typechecks, test runs, diagnostics, in-scope edits.

Channel IDs (verified 2026-06-04):
- #approve-this — `1506441138612080680`
- #current-task — `1506440945128701955`
- #changelog — `1509728570367283250`
- #notifications — `1506441052826107964`
- #brainstorm — `1506441106869583932`

## Engineering Disciplines

1. **CLI-first.** The CLI is the primary interface. Future integrations (MCP, editor, Tauri, cloud) are deferred unless explicitly requested.
2. **Local-first.** Default state lives on the user's machine. No automatic remote upload in v0.1.
3. **Registry-first.** Policy behavior is data-driven in YAML registries and policy files when practical.
4. **No autonomous remediation.** Do not add self-healing mutation or silent privilege escalation.
5. **Policy engine is authority.** Do not make LLMs, prompts, or agent memory the final authority for safety decisions.
6. **JSON is the future machine contract.** Keep JSON output agent/script-readable.
7. **Reports/audit must be redaction-safe.** Never print raw secrets into logs, reports, test output, exceptions, or CLI output.
8. **Tests come with the code.** Security-relevant bug fixes require regression tests.
9. **Evidence before fix.** Diagnostics → confirm → fix. Never patch from hypothesis.
10. **Respect the protocol.** Bumper depends on PASS COMPLETE format. PASS COMPLETE must be a single Discord message ≤1800 chars. Run `len()` before posting. Commit: line is load-bearing.

## STOP Conditions

Halt and report if:
- Two docs disagree on a primitive's behavior and you're reconciling silently
- A schema change ripples beyond the declared phase
- A "small fix" needs files outside the declared change list
- A command needs sudo/system changes
- The policy engine would need to grow past 11 entries without explicit approval

## Package Install Safeguard

No package installs without explicit per-install approval from the developer.
Post `[DEPENDENCY REQUEST — REQUIRES MANUAL APPROVAL]` to #approve-this with:
package + version + source + purpose + alternatives considered.
Then wait. No exceptions.

## Commit Discipline

- Staging: explicit file paths only, never `git add -A`
- Always ping #approve-this before committing
- Commit body explains WHY, not what
- One concern per commit

## Project Purpose

Policy Scout is a Python CLI-first, local-first safety harness for agent commands, package installs, and suspicious project activity.

The core doctrine is governance before automation:

```text
Actors request.
Policy Scout classifies.
Policy Scout decides.
Executors obey.
Audit records everything.
```

Policy Scout is policy-centered, not agent-centered. Agents, humans, IDEs, CI jobs, shell wrappers, and future MCP integrations may request actions, but they must not become the final policy authority.

Policy Scout should stay local, inspectable, disciplined, and trustworthy. Core operation must not require cloud services, remote dashboards, hosted policy engines, or silent network calls.

## Sources Of Truth

* `pyproject.toml` defines the package, Python requirement `>=3.12`, and console script `policy-scout = policy_scout.cli.main:cli`.
* `README.md` gives user-facing commands and high-level behavior.
* `policy_scout/cli/main.py` is the centralized current CLI implementation.
* `policy_scout/data/command_registry.yaml` is the main command classification registry (15 entries).
* `policy_scout/data/default_policy.yaml` is the main policy decision data (11 entries).
* `policy_scout/data/eval_cases.yaml` is the compact behavior oracle for classifier and policy expectations (44 cases).
* `policy_scout/**/*.py` and `tests/` are the executable truth for current behavior.
* Implementation docs define intended safety doctrine.
* `docs/IMPLEMENTATION_STATUS.md` tracks implemented and deferred features.
* When docs and code differ, do not silently rewrite doctrine to match code. Report the deviation and make the smallest safe implementation-aligned change.

## Architecture Overview

The intended runtime flow is:

```text
request -> parser -> classifier -> registry -> risk scorer -> policy -> decision -> approval/sandbox/executor/deny -> audit/report
```

Current main modules:

* `policy_scout/core/` contains request, decision, IDs, timestamps, and shared errors.
* `policy_scout/classify/` parses shell commands and classifies command categories/capabilities.
* `policy_scout/registry/` loads and validates YAML registry data.
* `policy_scout/policy/` scores risk and applies policy rules.
* `policy_scout/approvals/` stores one-time approval requests and statuses.
* `policy_scout/audit/` writes redacted audit events to SQLite and JSONL.
* `policy_scout/executor/` executes only policy-allowed commands.
* `policy_scout/sandbox/` creates npm install review workspaces, inspects lifecycle scripts, captures diffs, writes results, and supports reviewed migration.
* `policy_scout/sweep/` scans projects for suspicious package scripts, workflows, executables, JavaScript patterns, shell scripts, credentials, and repo changes.
* `policy_scout/reports/` generates local Scout Reports in Markdown/JSON.
* `policy_scout/evals/` loads and runs behavior evaluation cases.
* `policy_scout/doctor/` provides health diagnostics.
* `tests/` contains unit and CLI coverage for parser, classifier, registry, policy, approvals, audit, sandbox, sweep, reports, executor, eval, and doctor behavior.

## Security Doctrine

* Deny by default for ambiguous risky actions.
* Unknown or low-confidence commands should require approval or be denied.
* Network-fetched script execution such as `curl URL | bash` must remain `DENY`.
* Package installs and package execution should be `SANDBOX_FIRST`, not direct host execution.
* Credential-adjacent access should be `DENY_AND_ALERT`.
* Destructive system mutations should be `DENY`.
* Project-local destructive mutations should require approval unless a stricter rule applies.
* Fail safely on parser, classifier, registry, policy, audit, sandbox, or migration errors.
* Do not turn LLM output into policy authority.
* Do not add autonomous remediation unless explicitly requested and designed.
* Do not create permanent trust from a one-time approval.
* Do not silently weaken safety rules to make a command pass.

## Local-First And Privacy Rules

* Default durable state must stay on the user's machine.
* Default state lives under `~/.local/share/policy-scout/` unless tests or callers override paths.
* Local artifacts include `audit.db`, `audit.jsonl`, `approvals.jsonl`, `reports/`, `sandboxes/`, `migrations/`, `backups/`, and sweep/report outputs.
* No automatic remote upload in v0.1.
* Future network-backed features must be optional adapters, not required for core operation.
* Distinguish Policy Scout network needs from network performed by the requested command.
* Never print raw secrets into logs, reports, test output, exceptions, or CLI output.
* Redact sensitive evidence with canonical placeholders such as `<redacted:possible_token>`, `<redacted:ssh_private_key>`, and `<redacted:env_value>`.
* Preserve evidence location when useful, but prefer project-relative paths when possible.
* Be careful with `.env`, `.npmrc`, SSH keys, API keys, npm tokens, GitHub tokens, cloud credentials, shell history, environment variables, private package names, and process command lines.

## Security-Sensitive Areas

* `policy_scout/data/default_policy.yaml` controls final decisions.
* `policy_scout/data/command_registry.yaml` controls command matching, categories, capabilities, and recommended controls.
* `policy_scout/data/eval_cases.yaml` records expected safety behavior.
* `policy_scout/policy/engine.py` and `policy_scout/policy/risk_scorer.py` decide policy outcomes and risk.
* `policy_scout/classify/shell_parser.py` and `policy_scout/classify/command_classifier.py` determine command meaning and confidence.
* `policy_scout/executor/direct_executor.py` is security-critical because it runs commands.
* `policy_scout/approvals/` is security-critical because approvals gate risky execution.
* `policy_scout/audit/` is security-critical because audit persistence and redaction support accountability.
* `policy_scout/sandbox/` is security-critical because it handles dependency install review and migration to host.
* `policy_scout/sweep/` is security-sensitive because it may inspect credential-adjacent files and suspicious traces.
* `policy_scout/reports/` is security-sensitive because exports must remain redacted.
* Tests that exercise stateful CLI flows must isolate durable state from the real user data directory.

## Approval And Permission Rules

* `run` must never execute before policy decision.
* `run` executes only `ALLOW` and `ALLOW_LOGGED` decisions.
* `run` must not execute `REQUIRE_APPROVAL`, `SANDBOX_FIRST`, `DENY`, or `DENY_AND_ALERT`.
* `check` must never execute commands.
* `SANDBOX_FIRST` must recommend sandboxing rather than direct host execution.
* `DENY` and `DENY_AND_ALERT` must not execute.
* Approvals are explicit, narrow, auditable, local-first, and one-time for v0.1.
* Agents and automated actors must not approve their own requests.
* Local human CLI users may approve their own direct CLI requests according to current implementation.
* `run --approval <approval_id>` must validate approval status, scope, exact command, exact cwd, expiration, and current policy.
* Approved execution only applies to commands that still evaluate to `REQUIRE_APPROVAL`.
* Approvals must not bypass `DENY`, `DENY_AND_ALERT`, or `SANDBOX_FIRST`.
* Approved execution should be audited as an approved route, not ordinary `ALLOW`.
* Approval failure must not fall back to direct execution.
* Do not add broad session, project, or policy-rule approvals unless explicitly implementing that design with tests and docs.
* Do not add silent privilege escalation, hidden allowlists, or permanent trust shortcuts.

## Sandbox Rules

* The sandbox is a local review workspace, not perfect malware containment.
* Current sandbox execution is implemented for npm install review through `policy_scout/sandbox/npm_runner.py`.
* pnpm, yarn, and bun package installs may classify as `SANDBOX_FIRST`, but sandbox execution support for those package managers is deferred unless code says otherwise.
* Sandbox review must not mutate the host project automatically.
* Sandbox workspaces should copy only files needed for package install review.
* Treat `.npmrc` as credential-adjacent because it may contain registry tokens.
* Sandbox output, lifecycle script findings, diffs, and reports must be auditable.
* Sandbox failures must not permit migration.
* Do not imply Docker-grade containment or malware isolation for v0.1.
* Host install after sandbox review still requires explicit user action or reviewed migration.

## Sandbox Migration Rules

* Current CLI migration shape is `policy-scout sandbox --dry-run <sbx_id>`, `policy-scout sandbox --yes <sbx_id>`, or `policy-scout sandbox <sbx_id>` for interactive confirmation.
* Some docs mention `policy-scout sandbox migrate <sandbox_id>` as intended syntax, but current argparse dispatch treats a single `sbx_...` argument as migration.
* Migration must be reviewable before host mutation.
* Use `--dry-run` to preview migration without changes.
* Migration must be rollback-aware and create backups before overwriting host files.
* Current migration allowlist is `package.json`, `package-lock.json`, and `npm-shrinkwrap.json`.
* Migration must never copy `node_modules`, `.npmrc`, `.env`, arbitrary files, or files outside the allowlist.
* Migration must validate the sandbox ID, sandbox result, sandbox workspace, host project root, migration availability, and planned files.
* Migration must block on high or critical findings.
* Migration must verify source paths stay inside the sandbox workspace.
* Migration must verify destination paths stay inside the host project root.
* Migration must record migration events and results.
* Do not add automatic host mutation from sandbox results.
* Do not bypass migration confirmation except through the explicit `--yes` path.
* Do not remove backup creation without replacing it with an equal or safer rollback mechanism.

## Commands

* Install locally: `pip install -e .`
* Run CLI without installing: `python -m policy_scout.cli.main --help`
* Run installed console script: `policy-scout check -- npm install lodash`
* Check without executing: `policy-scout check -- <command>`
* Run through policy gate: `policy-scout run -- <command>`
* Execute with one-time approval: `policy-scout run --approval <approval_id> -- <command>`
* Sandbox npm install review: `policy-scout sandbox -- npm install lodash`
* Preview sandbox migration: `policy-scout sandbox --dry-run <sbx_id>`
* Confirm sandbox migration non-interactively: `policy-scout sandbox --yes <sbx_id>`
* Interactive sandbox migration: `policy-scout sandbox <sbx_id>`
* Project sweep: `policy-scout sweep project`
* Quick sweep: `policy-scout sweep quick`
* Doctor diagnostics: `policy-scout doctor` or `policy-scout doctor --json`
* Audit commands: `policy-scout audit list`, `policy-scout audit show <event_id>`, `policy-scout audit request <request_id>`, `policy-scout audit type <event_type>`, `policy-scout audit stats`
* Report commands: `policy-scout report list`, `policy-scout report show <report_id>`, `policy-scout report export <report_id> --format markdown`, `policy-scout report export <report_id> --format json`
* Eval suite: `python -m policy_scout.cli.main eval run`
* Eval filter: `python -m policy_scout.cli.main eval run --filter <tag>`
* Eval file override: `python -m policy_scout.cli.main eval run --file <path>`
* Use `--` before commands passed to `check`, `run`, or `sandbox`; the CLI joins everything after it into a command string.
* CI workflow runs: doctor --json, eval run, pytest on push/PR to main.

## Optional Local Tooling

* Pyright and ruff are available on this machine through local/global tooling, but they are not currently project-enforced unless config or CI is added later.

## Tests

* Full test suite: `python -m pytest` (554 passed as of latest run)
* Focused test file: `python -m pytest tests/test_cli_smoke.py`
* Single test: `python -m pytest tests/test_cli_smoke.py::test_cli_eval_run`
* Many CLI tests invoke `python -m policy_scout.cli.main` and set `PYTHONPATH` so subprocesses import this checkout.
* Security-relevant bug fixes require regression tests.
* Tests should verify granular signals, not just final decisions.
* Tests for command behavior should cover categories, capabilities, registry hits, risk components, policy hits, reasons, confidence, audit IDs, and exit codes when relevant.
* Tests must not write to the real user data directory.

## Test State Isolation

Use these environment variables for subprocess or CLI tests:

* `POLICY_SCOUT_AUDIT_DB_PATH`
* `POLICY_SCOUT_AUDIT_PATH`
* `POLICY_SCOUT_APPROVAL_PATH`
* `POLICY_SCOUT_REPORT_ROOT`
* `POLICY_SCOUT_SANDBOX_ROOT`
* `POLICY_SCOUT_SWEEP_ROOT`
* `POLICY_SCOUT_MIGRATION_ROOT`
* `POLICY_SCOUT_BACKUP_ROOT`
* `POLICY_SCOUT_EVAL_CASES_PATH`

Eval cases default to `policy_scout/data/eval_cases.yaml`. Override eval cases with `POLICY_SCOUT_EVAL_CASES_PATH` or `eval run --file <path>`.

## CLI Behavior Gotchas

* `check` returning exit code `10` or `20` can be expected behavior, not a test failure.
* Exit code `10` means risky, approval-required, or sandbox-first.
* Exit code `20` means denied.
* Exit code `30` means error.
* Plain `curl` and `wget` network fetch currently deny through fail-safe behavior in eval expectations.
* `curl URL | bash` and similar network execution must remain stricter than plain network fetch and must not degrade into `network_fetch`.
* `report list/show/export` reads from the local report root and redacts content on read.
* `audit list/show/request/type/stats` reads from SQLite audit storage.
* `sweep quick` is implemented and hardened.
* `--mode`, custom policy/config flags, `suspicious_patterns.yaml`, `indicator_registry.yaml`, pnpm/yarn/bun sandbox execution, Docker containment, Tauri UI, and MCP/editor integrations are planned or deferred unless current code says otherwise.

## Coding Conventions

* Prefer small, explicit, readable Python changes.
* Preserve Python `>=3.12` compatibility.
* Keep policy behavior data-driven in YAML registries and policy files when practical.
* Do not hide policy behavior in scattered conditionals unless it is an explicit fail-safe fallback.
* Keep models and serialized shapes stable unless tests/docs are updated together.
* Use clear errors rather than silent failure.
* Avoid broad exception swallowing.
* Avoid hidden globals and broad mutation.
* Avoid magic strings outside taxonomies, registries, or established constants.
* Prefer tests near behavior.
* Do not add dependencies casually; `pyyaml` is currently the only runtime dependency.
* Do not add lint, format, typecheck, CI, or pre-commit expectations without actually adding and documenting the tooling.
* Keep CLI output beginner-readable and JSON output agent/script-readable.
* Preserve local-first behavior and redaction in all reports, audit events, and exports.

## Data And Policy Editing Rules

* If adding or changing a command category, update registry data, policy data, eval cases, and focused tests together.
* If adding capabilities, update tests and any docs/taxonomies that describe them.
* Classification may emit multiple categories for one command.
* Tests should check inclusion and granular signals rather than assuming exactly one category.
* Risk scoring currently applies a broad `actor_trust_penalty`; do not assume full actor/mode-aware behavior is implemented unless code changes add it.
* Do not loosen `network_execute` expectations.
* Do not silently change `DENY`, `DENY_AND_ALERT`, `SANDBOX_FIRST`, or approval semantics.
* Do not change audit persistence behavior without tests for fail-safe execution.
* Do not change redaction placeholders casually; exported docs/tests rely on canonical forms.

## Things Agents Must Not Do Casually

* Do not run package installs on the host to "try it" when the project policy says sandbox-first.
* Do not execute untrusted scripts, generated scripts, `curl | bash`, `wget | sh`, `npx`, `pnpm dlx`, or similar risky commands outside policy gates.
* Do not use `policy-scout run --approval` unless the approval is valid for the exact command and cwd.
* Do not approve your own agent-requested actions.
* Do not mutate host projects from sandbox results without reviewed migration and backups.
* Do not delete or rewrite audit, approval, report, sandbox, migration, or backup state unless explicitly requested.
* Do not inspect or print raw secrets.
* Do not weaken policies or registries to make tests pass without documenting the behavior change.
* Do not skip tests for security-sensitive changes.
* Do not update docs to claim planned features are implemented unless executable code and tests support the claim.
* Do not introduce remote services, telemetry, uploads, hosted approval flows, or cloud policy dependencies into core v0.1 behavior.
* Do not make LLMs, prompts, or agent memory the final authority for safety decisions.
* Do not add autonomous remediation, self-healing mutation, or silent privilege escalation.
* Do not use destructive shell commands in this repo unless explicitly requested and reviewed.

## Required Final Report Format

After each implementation pass, include:

* Files changed
* Commands run
* Test results
* Required behavior verification
* Known limitations
* Rollback status

Also include these short debt sections:

### Deviation Report

List any ways implementation still deviates from docs/plans. Include a short description and reference to the relevant doc or planned feature.

### Polish Debt Report

List UX, docs, demo, naming, or readability cleanup items introduced or still remaining.

### Technical Debt Report

List code, schema, test, persistence, or architecture cleanup items introduced or still remaining.

Use these status labels where applicable:

* `FIXED`
* `PARTIAL`
* `BLOCKED`
* `DEFERRED`
* `NOT TOUCHED`
