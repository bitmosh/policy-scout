# Policy Scout v0.4.0 Local Alpha Release Checklist

## Purpose

This checklist verifies that Policy Scout is ready to tag as a CLI-first local alpha with an optional dogfooded desktop dashboard.

This is a release-readiness audit and checklist pass. No new features are added. No code changes are made unless a tiny docs reference fix is required and reported.

---

## Release Identity

**What is being shipped:**
- Policy Scout v0.4.0 Local Alpha
- CLI-first local safety harness for agent commands, package installs, and suspicious project activity
- Optional Tauri desktop dashboard (read-only/check-only, dogfooded)

**Shipping model:**
- CLI-first: The CLI is the source of truth for policy decisions, audit, reports, and JSON contracts
- Desktop dogfooded: The Tauri desktop app is an optional read-only/check-only companion verified through Policy Scout's own CLI checks, tests, and native smoke

**Release name:** Policy Scout v0.4.0 Local Alpha

**Recommended git tag:** `v0.4.0`

**Discord/dev-log version:** `v0.4.5` (as specified for this checklist pass)

---

## Shipping Model

**CLI-first, desktop dogfooded.**

The CLI is the authority. The desktop dashboard is optional, read-only, and check-only. Desktop verification happens through CLI checks, tests, and native smoke.

Not promised:
- Packaged desktop installer
- Autonomous remediation
- UI mutation controls
- Approval/migration/deletion UI
- Background daemon

---

## Scope

**In scope for v0.4.0 Local Alpha:**
- CLI command checking, policy decisions, registry matching, local audit logging, local package sandboxing (npm), project sweeps, report generation
- Optional Tauri desktop dashboard for read-only viewing of reports, evidence, and audit events
- Local-first data storage under `~/.local/share/policy-scout/`, `~/.config/policy-scout/`, `~/.cache/policy-scout/`
- Secret redaction in logs, reports, and outputs
- Green checkpoint automated verification (pytest, doctor, eval, npm build, cargo check/test)
- Native smoke manual verification for desktop

**Out of scope for v0.4.0 Local Alpha:**
- Packaged desktop installer
- UI mutation controls (command execution, approval resolution, sandbox migration, cleanup deletion)
- Shell plugin
- Arbitrary argv UI
- Auto-remediation
- Full frontend automated tests
- Sweep/sandbox/cleanup detailed boundary docs

---

## Non-Goals

For v0.4.0 Local Alpha, the following are explicitly non-goals:

- Desktop is not a standalone product
- Desktop does not replace CLI authority
- Desktop does not provide execution, mutation, or approval capabilities
- Desktop is not packaged as an installer
- No autonomous remediation
- No background daemon
- No cloud sync or remote dashboards

---

## Blocking Criteria

A release is **blocked** if any of the following are true:

- Green checkpoint fails (pytest, doctor, eval, npm build, cargo check/test)
- Safety boundaries are violated (desktop has execution, mutation, or approval UI)
- CLI authority is not preserved (desktop can override CLI decisions)
- Secret redaction is broken (secrets leak into logs, reports, or outputs)
- Data paths are not documented or are incorrect
- Install documentation is incomplete or incorrect
- CI gates are not green
- Git working tree is dirty (uncommitted changes)
- HEAD does not match origin/main

---

## Non-Blocking Known Limitations

The following are **non-blocking** for v0.4.0 Local Alpha:

- Browser preview cannot call Tauri invoke (documented limitation)
- Desktop requires native Tauri runtime (inherent to Tauri)
- Desktop is not packaged as installer yet (documented limitation)
- No approval/migration/deletion UI by design (intentional boundary)
- Native smoke is manual (documented limitation)
- Full frontend automated tests are not yet introduced (documented limitation)
- Sweep/sandbox/cleanup detailed boundary docs are future candidates (documented limitation)
- Long findings are capped in UI with CLI fallback (documented limitation)

---

## Required Automated Gates

Before tagging, the following automated gates must pass:

```bash
# From repo root
python -m pytest -q
PYTHONPATH=/home/boop/Projects/policy-scout python -m policy_scout.cli.main doctor --json
PYTHONPATH=/home/boop/Projects/policy-scout python -m policy_scout.cli.main eval run

# From ui/desktop
npm run build

# From ui/desktop/src-tauri
cargo check
cargo test
```

These gates are also run in CI (`.github/workflows/ci.yml`).

---

## Required Manual/Native Gates

Before tagging, the following manual verification is recommended:

- Complete the native smoke checklist in `docs/compressed/TAURI_NATIVE_MANUAL_SMOKE_CHECKLIST_SOURCE.md`
- Verify desktop launches and displays empty state correctly
- Verify report/evidence/audit cards display correctly
- Verify browser preview limitations are understood
- Verify negative safety checks (no execution, no mutation, no approval UI)

---

## CLI-First Verification

Verify CLI is the authority:

- CLI commands work without desktop running
- CLI policy decisions are final
- CLI audit logs are complete
- CLI reports are complete
- CLI JSON contracts are stable
- Desktop does not override CLI decisions
- Desktop can be ignored entirely

---

## Desktop Dogfood Verification

Verify desktop is optional and read-only:

- Desktop launches from CLI checks/tests/native smoke
- Desktop displays reports, evidence, and audit events
- Desktop does not provide command execution UI
- Desktop does not provide approval resolution UI
- Desktop does not provide sandbox migration/apply UI
- Desktop does not provide cleanup deletion/apply UI
- Desktop does not provide shell plugin
- Desktop does not provide arbitrary argv UI
- Desktop is read-only/check-only

---

## Safety Boundary Checklist

Verify safety boundaries are preserved:

- [ ] CLI authority is preserved
- [ ] Desktop is read-only/check-only
- [ ] No command execution UI in desktop
- [ ] No approval resolution UI in desktop
- [ ] No sandbox migration/apply UI in desktop
- [ ] No cleanup deletion/apply UI in desktop
- [ ] No shell plugin
- [ ] No arbitrary argv UI
- [ ] No auto-remediation
- [ ] Secret redaction works in logs, reports, and outputs
- [ ] Data paths are documented and correct
- [ ] Install documentation is complete and correct

---

## Data/Readiness Checklist

Verify data handling is correct:

- [ ] Local data paths are documented (`~/.local/share/policy-scout/`, `~/.config/policy-scout/`, `~/.cache/policy-scout/`)
- [ ] Fresh empty states are documented
- [ ] Mature data states are documented
- [ ] Report surfaces are documented
- [ ] Audit surfaces are documented
- [ ] Evidence surfaces are documented
- [ ] No automatic remote upload in v0.1
- [ ] Local-first doctrine is documented

---

## Documentation Checklist

Verify documentation is complete:

- [ ] README.md states CLI-first, desktop dogfooded
- [ ] docs/INSTALL.md is complete and correct
- [ ] docs/IMPLEMENTATION_STATUS.md is up to date
- [ ] ui/desktop/README.md states CLI-first, desktop dogfooded
- [ ] docs/compressed/TAURI_NATIVE_MANUAL_SMOKE_CHECKLIST_SOURCE.md is authoritative
- [ ] docs/compressed/CORE_DOCTRINE_AND_BOUNDARIES.md is current
- [ ] docs/LOCAL_FIRST_AND_PRIVACY.md is current
- [ ] docs/AUDIT_AND_REPORTING.md is current
- [ ] docs/SCOUT_REPORT_ANATOMY.md is current
- [ ] pyproject.toml version is consistent
- [ ] ui/desktop/package.json version is consistent
- [ ] ui/desktop/src-tauri/Cargo.toml version is consistent

---

## CI/Tag Checklist

Verify CI and tag readiness:

- [ ] CI is green (`.github/workflows/ci.yml`)
- [ ] pytest passes
- [ ] doctor passes
- [ ] eval passes
- [ ] npm build passes
- [ ] cargo check passes
- [ ] cargo test passes
- [ ] Git working tree is clean
- [ ] HEAD matches origin/main
- [ ] No uncommitted changes
- [ ] Tag strategy is decided (`v0.4.0` recommended)
- [ ] Discord/dev-log version is decided (`v0.4.5` for this checklist pass)

---

## Rollback/Undo Guidance

If a release is blocked or fails:

1. Do not tag
2. Fix the blocking issue
3. Re-run green checkpoint
4. Re-run native smoke if desktop is affected
5. Re-verify safety boundaries
6. Re-verify data paths
7. Re-verify documentation
8. Re-run this checklist

If a tag is already pushed and a critical issue is found:

1. Communicate the issue in #changelog
2. Document the issue in docs/IMPLEMENTATION_STATUS.md
3. Fix the issue
4. Increment version (v0.4.1, etc.)
5. Re-run this checklist
6. Tag new version

---

## Final Release Decision Template

**Release:** Policy Scout v0.4.0 Local Alpha

**Git tag:** `v0.4.0`

**Discord/dev-log version:** `v0.4.5`

**Blockers found:** [None / List blockers]

**Non-blocking limitations:** [List non-blocking limitations]

**Required gates status:**
- pytest: [PASS/FAIL]
- doctor: [PASS/FAIL]
- eval: [PASS/FAIL]
- npm build: [PASS/FAIL]
- cargo check: [PASS/FAIL]
- cargo test: [PASS/FAIL]

**Native smoke status:** [COMPLETE / INCOMPLETE / SKIPPED]

**Safety boundary verification:** [PASS/FAIL]

**Data/readiness verification:** [PASS/FAIL]

**Documentation verification:** [PASS/FAIL]

**CI status:** [GREEN / RED]

**Git status:** [CLEAN / DIRTY]

**HEAD vs origin/main:** [MATCH / MISMATCH]

**Decision:** [READY TO TAG / NOT READY - fix blockers]

**Signed:** [Date and approver]
