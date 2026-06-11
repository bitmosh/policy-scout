# ADR-007: Sweep Delta Mode and Exclusion Contract

**Status:** Accepted  
**Date:** 2026-06-10  
**Deciders:** Developer (bitmosh)  
**Related ADRs:** [ADR-002](ADR-002-policy-config-precedence.md) (exclusion patterns read from project config), [ADR-006](ADR-006-report-and-data-lifecycle.md) (sweep state storage uses the data lifecycle model)

---

## Context

The sweep engine runs a full project scan every time it's invoked. On a large project this is slow, on a small project it produces the same findings on every run, and as a pre-commit hook it's unusable because it checks files the current commit didn't touch.

The other persistent problem is false positives. The JavaScript pattern detector, credential reference checker, and shell script checker all produce false-positive findings on common code patterns that are benign in context (test fixtures, example configs, documentation code blocks, vendored libraries). There is no mechanism to suppress a known false positive short of patching the detection code itself.

These two problems compound: a slow full scan that produces the same false positives every run quickly trains developers to ignore sweep output entirely. A sweep that's ignored provides no safety value.

This ADR locks two features:
1. **Delta mode** — scan only files changed since the last clean sweep, using the git diff as the scope boundary
2. **Exclusion patterns** — a project-level allowlist of path patterns that sweep will not check

Both features must be designed carefully to avoid creating a bypass surface. A malicious file that's in the exclusion list should be excluded because the developer deliberately decided its content is not a threat, not because the attacker put it there. The exclusion contract must make this distinction clear.

---

## Forces

- **Delta mode must not miss new threats.** If a file wasn't changed since the last sweep, delta mode skips it. But if a new threat pattern is added to the sweep engine, files that haven't changed may now match. Delta mode must have a full-sweep fallback when the sweep engine version changes.
- **Exclusion is not exemption.** An excluded file is not trusted; it's deprioritized. The sweep still knows it exists. Excluded findings should appear in the report as suppressed, not absent. This matters for audit: a developer who adds `node_modules/` to the exclusion list should be able to see that they excluded it, not that it was never checked.
- **Git-based delta is more reliable than mtime-based delta.** File modification times are not reliable on many filesystems, can be set arbitrarily, and don't capture renames or moves. Git's `--diff-filter` is authoritative for changed files.
- **Pre-commit hook use case.** The entire value of delta mode is enabling sweep as a `pre-commit` hook in `.git/hooks/pre-commit` or via the Policy Scout pre-commit config. A full scan on every commit is too slow; a scan of only staged files is the right scope.
- **Sweep state must be auditable.** The last sweep timestamp and the git commit at last sweep must be recorded in the audit trail so that the scope of each sweep run is reconstructable.

---

## Decision

### D1 — Delta mode definition

Delta mode limits sweep scope to files that have changed since the last recorded clean sweep baseline.

**Baseline record:** After any successful sweep run, Policy Scout records a sweep baseline:

```json
{
  "baseline_id": "swb_abc123",
  "sweep_type": "project",
  "project_root": "/home/user/my-project",
  "git_commit": "abc123def456",
  "timestamp": "2026-06-10T14:30:00",
  "finding_count": 3,
  "excluded_count": 47,
  "engine_version": "0.5.0"
}
```

Stored in `~/.local/share/policy-scout/sweep-baselines/<project_hash>.json` where `project_hash` is a SHA-256 of the absolute project root path. One file per project.

**Delta scope computation:**
```
if no baseline exists for project:
    run full sweep (first run is always full)
elif baseline.engine_version != current_engine_version:
    run full sweep (engine changed; old baseline is stale)
elif not in a git repo:
    run full sweep (no diff available; fall back to full)
else:
    changed_files = git diff --name-only {baseline.git_commit}..HEAD
    run sweep on changed_files only
```

The delta scope includes files that were added, modified, or renamed since the baseline commit. Deleted files are excluded from scope (they can't be swept). Untracked files (not yet `git add`ed) are always included in delta scope since they have no git history.

**Full sweep triggers:**
- No baseline for this project
- Engine version changed since baseline
- Not in a git repo
- User passes `--full` flag explicitly
- The last sweep found critical findings (severity=critical forces the next run to be full)

### D2 — Pre-commit sweep scope

When sweep is invoked in pre-commit context (`policy-scout sweep project --pre-commit` or via git hook), the scope is restricted to **staged files only**:

```
git diff --cached --name-only --diff-filter=ACM
```

This is a subset of delta mode and is faster. Pre-commit mode uses a separate code path from standard delta mode because the scope boundary is the staging area, not the git commit history. Pre-commit mode does not update the sweep baseline (the commit hasn't happened yet).

Pre-commit mode is enabled by:
- `--pre-commit` flag on `policy-scout sweep project`
- `scan.pre_commit: true` in `.policy-scout.yaml` (triggers pre-commit mode automatically when called from a git hook)

### D3 — Exclusion pattern contract

Exclusion patterns are defined in `.policy-scout.yaml` under `sweep.exclude`:

```yaml
sweep:
  exclude:
    - "node_modules/"
    - "dist/"
    - ".venv/"
    - "**/*.min.js"
    - "**/vendor/**"
    - "tests/fixtures/malicious_example.py"   # known false positive; reviewed 2026-06-10
```

Pattern format: glob patterns using the same syntax as `.gitignore`. Paths are relative to the project root.

**What exclusion means:**
- The file is not read by the sweep engine
- The file's path appears in the sweep report under `excluded_paths` with a count
- The `SweepCompleted` audit event includes `excluded_count`
- Individual excluded patterns do not appear in the report (only the count)

**What exclusion does not mean:**
- The excluded path is not trusted or safe — it is deprioritized
- Exclusions do not affect the policy engine's command classification
- Exclusions do not affect the git staged scanner

**Exclusion security note (displayed prominently in sweep output and docs):**
```
Excluded paths are not scanned. If an excluded file contains malicious content,
Policy Scout will not detect it. Review your exclusion list periodically.
Exclusions are visible in sweep reports and audit events.
```

### D4 — False-positive suppression (per-finding, not per-file)

Beyond path-level exclusions, developers need to suppress specific known false positives without excluding the entire file. This is a separate mechanism from D3:

In `.policy-scout.yaml`:

```yaml
sweep:
  suppress:
    - id: "fp_001"
      file: "src/utils/shell_examples.py"
      finding_type: "shell_script_suspicious_pattern"
      reason: "This file contains intentional shell examples for documentation"
      reviewed_at: "2026-06-10"
    - id: "fp_002"
      file: "tests/test_credentials.py"
      finding_type: "credential_reference"
      reason: "Test file with dummy credentials; no real secrets"
      reviewed_at: "2026-06-10"
```

Suppressed findings appear in the sweep report under `suppressed_findings` with the suppression reason. They are never silently omitted. `policy-scout sweep project --show-suppressed` prints them with their reasons.

The `id` field on each suppression is mandatory and must be unique within the project config. This makes suppressions trackable and revocable.

### D5 — Sweep state storage

Sweep baselines are stored in the data directory alongside reports and audit events (`~/.local/share/policy-scout/sweep-baselines/`). The data lifecycle ADR (ADR-006) governs retention: baselines expire with the same default as reports (90 days) and are cleaned up by `data cleanup`.

A baseline that expires does not cause a problem — the next sweep run just treats it as a first run and does a full sweep.

### D6 — Engine version tracking

The sweep engine version is the Policy Scout version string. When the engine version changes between the baseline record and the current run, delta mode falls back to full sweep. This prevents a version upgrade from silently leaving previously-undetected findings unscanned.

The version comparison is an equality check, not semver comparison. Any version change triggers a full sweep. This is conservative — a patch release that doesn't change any sweep logic still triggers a full sweep — but it's simple and correct.

---

## Consequences

### Positive
- Sweep is usable as a pre-commit hook; staged-files-only scope makes it fast enough for interactive use
- Known false positives have a structured suppression path instead of requiring code patches
- Excluded paths are visible in reports — exclusions can be audited over time
- The baseline record gives each sweep run a reconstructable scope in the audit trail

### Negative / Risks
- Delta mode can miss a threat that arrived in a file before the baseline commit and wasn't changed since. Example: malicious code committed in week 1, sweep baseline set in week 2, no subsequent changes to that file — the file is never re-swept in delta mode. Mitigation: full sweep is triggered on engine version changes, and running a periodic `policy-scout sweep project --full` is documented as a monthly hygiene practice.
- The suppression list in `.policy-scout.yaml` is a file in the repository. A malicious PR could add a suppression for a file it's also adding malicious content to. Mitigation: suppressions require `reviewed_at` and `reason` fields; they appear explicitly in sweep reports; they should be reviewed in code review like any other security-adjacent config change. Policy Scout cannot enforce this review, but the visibility is there.
- Git-based delta requires the project to be a git repo. Non-git projects always get full sweep. This is documented but not a significant limitation (Policy Scout is primarily designed for git repos).

---

## Blast Radius

| File | Change |
|---|---|
| `sweep/engine.py` | modified — delta scope computation, baseline read/write |
| `sweep/baseline.py` | new — `SweepBaseline` dataclass, load/save, scope computation |
| `sweep/exclusions.py` | new — pattern matching, suppression matching |
| `sweep/models.py` | modified — `SweepResult` gets `excluded_count`, `suppressed_count`, `scope` |
| `audit/events.py` | modified — `SweepStarted`/`SweepCompleted` get `scope`, `baseline_id`, `excluded_count` |
| `cli/main.py` | modified — `--delta`, `--full`, `--pre-commit`, `--show-suppressed` flags |
| `policy_scout/data/` | new directory — `sweep-baselines/` storage |
| `tests/test_sweep_*.py` | modified — delta scope tests, exclusion tests |
| `tests/test_sweep_baseline.py` | new |

---

## Implementation Phases

### Phase 1 — Exclusion patterns
- `sweep/exclusions.py` — glob matching against `sweep.exclude` from project config (ADR-002)
- `SweepResult` gains `excluded_paths` count
- `SweepCompleted` audit event gains `excluded_count`
- Sweep report shows excluded paths section
- Tests: exclusion matching, excluded paths in report

**STOP gate:** `node_modules/` in sweep.exclude produces `excluded_count > 0` in audit event. Sweep report includes exclusion section.

### Phase 2 — Baseline record and delta mode
- `sweep/baseline.py` — baseline dataclass, storage, scope computation
- `sweep/engine.py` — delta scope wiring, full-sweep fallback conditions
- `--delta` and `--full` flags on `policy-scout sweep project`
- Baseline written after every successful sweep

**STOP gate:** Second sweep run on an unchanged project runs in delta mode and produces 0 new findings. Engine version change triggers full sweep.

### Phase 3 — Pre-commit scope
- `--pre-commit` flag: scopes to `git diff --cached --name-only`
- Does not update baseline
- `scan.pre_commit: true` in config enables pre-commit mode from git hooks
- Documented setup in `docs/INSTALL.md` for `pre-commit` hook registration

**STOP gate:** `policy-scout sweep project --pre-commit` on a clean staging area completes in < 2 seconds on a typical project.

### Phase 4 — Finding suppression
- `sweep.suppress` list in project config
- `SweepResult` gains `suppressed_findings` list with reasons
- `--show-suppressed` flag on `policy-scout sweep project`
- Validation: `id` must be unique, `reviewed_at` must be present

**STOP gate:** A suppressed finding appears in `suppressed_findings` in the report, not in `findings`. `--show-suppressed` prints it with reason.
