# Tauri Native Manual Smoke Checklist

Source document for Policy Scout Tauri v0.2.x read-only UI manual verification.
Run at significant Tauri checkpoints and before each v0.3.x feature expansion.

---

## v0.4 Dashboard Native Smoke Checklist

**This is the authoritative, repeatable native QA path for the v0.4 CLI-first local alpha.**

### Purpose

CI covers TypeScript compilation, Rust type-checking, and Rust unit tests for all
six validators. It does not validate native window startup, live data loading,
card rendering, selector behavior, or UI boundary enforcement.

This checklist fills that gap. It is a repeatable manual verification pass that
confirms the native Tauri app opens correctly, loads live Policy Scout CLI data,
and does not expose any mutation, execution, approval, or deletion surface.

### Important Notes

- **Browser preview is not sufficient** for native invoke validation. The native Tauri runtime (`npm run tauri dev`) is required to validate live data loading and Rust adapter behavior.
- **Run this checklist after automated green checkpoint commands** (pytest, doctor, eval, npm build, cargo check, cargo test).
- This checklist is the authoritative native dashboard smoke path for v0.4 local alpha.

---

## A. Preflight Gates

Before running the native smoke checklist, ensure all automated checks pass:

```bash
cd /home/boop/Projects/policy-scout

# 1. Git status clean
git status

# 2. Python tests
python -m pytest -q

# 3. Doctor check
PYTHONPATH=/home/boop/Projects/policy-scout python -m policy_scout.cli.main doctor --json

# 4. Eval suite
PYTHONPATH=/home/boop/Projects/policy-scout python -m policy_scout.cli.main eval run

# 5. Frontend build
cd /home/boop/Projects/policy-scout/ui/desktop
npm run build

# 6. Rust checks
cd /home/boop/Projects/policy-scout/ui/desktop/src-tauri
cargo check
cargo test
```

Record the current commit before starting:

```bash
git -C /home/boop/Projects/policy-scout log --oneline -1
```

---

## B. Launch Native App

**Launch:** `npm run tauri dev` from `ui/desktop`

- [ ] Native window opens without crash
- [ ] Window has correct title (Policy Scout or similar)
- [ ] Dashboard loads without white screen
- [ ] No persistent "Tauri runtime unavailable" message visible
- [ ] No unhandled JavaScript error banner visible
- [ ] No terminal panic
- [ ] Cards begin loading (spinner or data visible)
- [ ] `BoundaryNote` component is visible at bottom of dashboard ("Read-only" boundary reminder)

---

## C. Global Visual/Readability Checks

- [ ] Dark theme readable
- [ ] No light broken surfaces
- [ ] Cards have readable text
- [ ] Redaction placeholders look intentional

---

## D. Overview / Doctor / Data Checks

**Overview Status Strip** — summarizes loaded state across cards

- [ ] Strip is visible at the top of the dashboard
- [ ] Updates after cards load data
- [ ] Shows summary counts or status indicators
- [ ] Does not show any action buttons or mutation controls
- [ ] No free-text input in the strip

**Doctor Status card** — invokes `policy-scout doctor --json`

- [ ] Card loads without crash
- [ ] Shows CLI version or OK status
- [ ] Shows registry counts (commands, policies, eval cases)
- [ ] No mutation controls

**Data Status card** — invokes `policy-scout data status --json`

- [ ] Card loads without crash
- [ ] Shows data directory path and counts
- [ ] No deletion or cleanup trigger button
- [ ] **Contrast:** Count rows (`approvals`, `audit_events`, `reports`, etc.) are readable — dark elevated background, not white/light

---

## E. Decision Check Checks

**Decision Check card** — invokes `policy-scout check --json <command_text>` (check-only; never executes)

- [ ] Card appears near top of dashboard
- [ ] "CHECK ONLY — commands are classified, never executed" banner visible
- [ ] Button says "Check command" (not "Run command" or "Execute")
- [ ] Empty/whitespace input rejected with validation error
- [ ] `git status` returns ALLOW decision
- [ ] `npm install left-pad` returns SANDBOX_FIRST decision
- [ ] `rm -rf /` returns DENY decision
- [ ] Every result shows "NOT EXECUTED" marker prominently
- [ ] FAQ buttons populate local explanation/command only
- [ ] FAQ buttons do not auto-check (no CLI call on FAQ click)
- [ ] Dangerous examples (e.g., `rm -rf /`) are clearly labeled "Example only — do not run"
- [ ] Browser preview shows native-required error if attempting check
- [ ] Audit Events list still populates after check probes
- [ ] DecisionIssued filter populates after check probes

**v0.3.4 Native Smoke Finding Note:**

During v0.3.4 native smoke, CLI audit data was present (17,152+ events) but the UI did not render audit events. Root cause was a dual contract mismatch:
- Frontend passed `eventType` (camelCase) but Rust expected `event_type` (snake_case)
- CLI returned JSON arrays directly but frontend expected `{ "events": [...] }` wrapper

This validated why native smoke matters: CLI contract verification alone does not catch adapter/frontend shape mismatches. Fix committed in 0ebc137.

---

## F. Reports Checks

**Reports List card** — invokes `policy-scout report list --json --limit <n> [--type <type>]`

### Limit selector

- [ ] Selector is visible
- [ ] Options are exactly: **5, 10, 25, 50** — no other values
- [ ] No free-text input
- [ ] Selecting a value refreshes the list

### Type selector

- [ ] Selector is visible
- [ ] Options are exactly: **All, command_decision, sandbox_result, project_sweep, system_quick_sweep** — no other values
- [ ] No free-text input
- [ ] Selecting a type refreshes the list

### List behavior

- [ ] Reports are listed with IDs
- [ ] Changing either selector refreshes the list
- [ ] No report deletion or export controls
- [ ] IDs are not editable
- [ ] Empty state is helpful if no reports exist

**Report Detail** — triggered by clicking a report ID

- [ ] Clicking a report ID opens the detail view
- [ ] Detail header shows a close/back control
- [ ] Report content renders without crash
- [ ] Redaction placeholders visible where expected
- [ ] Redaction notice readable if present
- [ ] Protected placeholders clear
- [ ] "Could Not Verify" section appears when could_not_verify has items
- [ ] Could-not-verify items are styled as review/unknown (not critical danger)
- [ ] Long findings capped at 10 with message: "Showing first 10 of X findings — run from CLI for full results"
- [ ] No export, delete, or action buttons
- [ ] Closing the detail returns to the list
- [ ] Detail cannot be opened for an ID that was not selected from the list (no free-text ID input visible)
- [ ] **Contrast:** Report detail card background is dark (not white) — finding items and action items use dark elevated background

---

## G. Audit Checks

**Audit Stats card** — invokes `policy-scout audit stats --json`

- [ ] Card loads without crash
- [ ] Shows event counts or summary stats
- [ ] No deletion, export, or audit-manipulation controls
- [ ] **Contrast:** By-type rows (e.g., `ApprovalRequested`, `SweepCompleted`) are readable — dark elevated background, event type names and counts visible

**Audit Events List card** — invokes `policy-scout audit list` or `audit type` depending on filter

### Event type selector

- [ ] Selector is visible
- [ ] Options are exactly:

  - All recent events
  - SweepCompleted
  - SweepError
  - SandboxInstallCompleted
  - SandboxInstallStarted
  - SandboxResultWritten
  - ScoutReportGenerated
  - CommandExecutionCompleted
  - CommandExecutionBlocked
  - ApprovalRequested
  - ApprovalApprovedOnce
  - ApprovalDeniedOnce
  - DecisionIssued

  **Total: 13 options. No other values present. No free-text input.**

- [ ] Selecting a type refreshes the list
- [ ] Selecting "All recent events" returns to the unfiltered list
- [ ] Empty state helpful on fresh data
- [ ] DecisionIssued filter works after check probes

### List behavior

- [ ] Changing event type clears any open event detail
- [ ] Event IDs are listed
- [ ] No deletion, export, or audit-manipulation controls

**Audit Event Detail** — triggered by clicking an event ID

- [ ] Clicking an event ID opens the detail view
- [ ] Detail header shows a close/back control
- [ ] Event content renders without crash
- [ ] Redaction placeholders visible where expected
- [ ] Payload readable
- [ ] No export, delete, or action buttons
- [ ] Closing the detail returns to the list
- [ ] Detail cannot be opened for an ID not selected from the list

---

## H. Cleanup / Eval Checks

**Cleanup Dry-Run card** — invokes `policy-scout data cleanup --target <target> --dry-run --json`

- [ ] Card header shows **"DRY RUN ONLY"** notice (or equivalent prominent label)
- [ ] `BoundaryNote` or similar reminder is visible
- [ ] No delete/apply cleanup control

### Cleanup target selector

- [ ] Selector is visible
- [ ] Options are exactly: **Demo data, Sandbox workspaces, Sandbox results** — no other values
- [ ] No free-text input
- [ ] Selecting each target refreshes the dry-run result

### Dry-run result behavior

- [ ] Result shows what *would* be cleaned, not a deletion confirmation
- [ ] No "Delete", "Apply", "Confirm", or "Execute" button visible
- [ ] No "Undo" button (nothing was done)
- [ ] No network or remote calls implied

**Eval Results card** — invokes `policy-scout eval run --json`

- [ ] Card loads without crash
- [ ] Shows pass/fail count and pass rate
- [ ] Eval run is triggered by user action or on load (not on a background loop)
- [ ] No controls to modify eval cases from the UI
- [ ] Eval errors visible if any

---

## I. Sweep Checks

**Quick Sweep card** — invokes `policy-scout sweep quick --json`

- [ ] Card loads without crash
- [ ] Sweep is user-triggered (button)
- [ ] Shows findings or "no findings" state
- [ ] Redacted values styled distinctly
- [ ] No free-text path input
- [ ] No controls to modify sweep behavior
- [ ] Sweep results use evidence/uncertainty language
- [ ] Could-not-verify not treated as confirmed compromise
- [ ] Long finding preview cap copy visible if applicable
- [ ] No remediation controls

**Project Sweep card** — invokes `policy-scout sweep project --json`

- [ ] Card loads without crash
- [ ] Sweep is user-triggered (button)
- [ ] Shows findings or "no findings" / "could not verify" states
- [ ] `SweepResultPreview` component renders findings list correctly
- [ ] Redacted values styled distinctly
- [ ] No project path selection input (uses CLI default working directory)
- [ ] No controls to modify sweep behavior
- [ ] Long finding preview cap copy visible if applicable
- [ ] No remediation controls

---

## J. Sandbox Results Checks

**Sandbox Results List card** — invokes `policy-scout report list --json --type sandbox_result --limit 5`

- [ ] Card loads without crash
- [ ] Lists sandbox result reports by ID
- [ ] No pagination control yet (known limitation — limit 5, no page selector)
- [ ] No deletion controls
- [ ] Empty state is helpful if no sandbox results exist

**Sandbox Result Detail** — triggered by clicking a result ID

- [ ] Clicking a result ID opens the detail view
- [ ] Detail renders without crash
- [ ] Redaction placeholders visible where expected
- [ ] No migrate/apply UI
- [ ] No package install execution from dashboard
- [ ] No lifecycle script execution controls

---

## K. Browser Preview Checks

**Launch:** `npm run dev` → open `http://localhost:1420`

- [ ] App loads in browser without crashing
- [ ] Displays message: "Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data."
- [ ] No attempt to load live CLI data visible (no spinner-forever states on cards)
- [ ] No JavaScript console errors related to Tauri invoke (expected — invoke is unavailable)
- [ ] Layout is visible (not blank page)
- [ ] Tauri-only actions show friendly native-required/runtime-unavailable error
- [ ] No stack traces to user

---

## L. Negative Safety Checks

Confirm absent:

- [ ] Command execution UI
- [ ] Approval approve/deny UI
- [ ] Sandbox migration/apply UI
- [ ] Cleanup deletion/apply UI
- [ ] Shell plugin UI
- [ ] Arbitrary argv input
- [ ] Auto-remediation
- [ ] Broad cleanup controls
- [ ] Direct filesystem/database browsing

Each of these should be **absent**. If present, it is a safety boundary regression. **Stop and report.**

---

## M. Recording Template

Copy and fill in before archiving or filing as a CI gate note.

```
Date:
Commit (git log --oneline -1):
OS + version:
Policy Scout CLI version (policy-scout doctor --json):
Tauri version (npm run tauri dev output):

Preflight gates:
  git status clean:           [ ] PASS  [ ] FAIL  Notes:
  pytest:                    [ ] PASS  [ ] FAIL  Notes:
  doctor:                     [ ] PASS  [ ] FAIL  Notes:
  eval:                       [ ] PASS  [ ] FAIL  Notes:
  npm build:                  [ ] PASS  [ ] FAIL  Notes:
  cargo check:                [ ] PASS  [ ] FAIL  Notes:
  cargo test:                 [ ] PASS  [ ] FAIL  Notes:

Native launch:
  window opens:               [ ] PASS  [ ] FAIL  Notes:
  no blank screen:            [ ] PASS  [ ] FAIL  Notes:
  no runtime-unavailable:     [ ] PASS  [ ] FAIL  Notes:
  no terminal panic:          [ ] PASS  [ ] FAIL  Notes:

Global visual/readability:
  dark theme readable:        [ ] PASS  [ ] FAIL  Notes:
  no light broken surfaces:   [ ] PASS  [ ] FAIL  Notes:
  cards readable:             [ ] PASS  [ ] FAIL  Notes:
  redaction intentional:      [ ] PASS  [ ] FAIL  Notes:

Overview / Doctor / Data:
  Status Strip:               [ ] PASS  [ ] FAIL  Notes:
  Doctor Status:              [ ] PASS  [ ] FAIL  Notes:
  Data Status:                [ ] PASS  [ ] FAIL  Notes:

Decision Check:
  card appears:               [ ] PASS  [ ] FAIL  Notes:
  check-only language:        [ ] PASS  [ ] FAIL  Notes:
  button label:               [ ] PASS  [ ] FAIL  Notes:
  empty/whitespace rejected:  [ ] PASS  [ ] FAIL  Notes:
  git status => ALLOW:        [ ] PASS  [ ] FAIL  Notes:
  npm install => SANDBOX:     [ ] PASS  [ ] FAIL  Notes:
  rm -rf / => DENY:           [ ] PASS  [ ] FAIL  Notes:
  NOT EXECUTED markers:       [ ] PASS  [ ] FAIL  Notes:
  FAQ local-only:             [ ] PASS  [ ] FAIL  Notes:
  dangerous examples labeled: [ ] PASS  [ ] FAIL  Notes:

Reports:
  list loads/empty state:     [ ] PASS  [ ] FAIL  Notes:
  filter/limit controls:      [ ] PASS  [ ] FAIL  Notes:
  detail opens:               [ ] PASS  [ ] FAIL  Notes:
  redaction notice:           [ ] PASS  [ ] FAIL  Notes:
  protected placeholders:     [ ] PASS  [ ] FAIL  Notes:
  could-not-verify distinct:  [ ] PASS  [ ] FAIL  Notes:
  long finding cap copy:     [ ] PASS  [ ] FAIL  Notes:
  no mutation controls:       [ ] PASS  [ ] FAIL  Notes:

Audit:
  stats visible:              [ ] PASS  [ ] FAIL  Notes:
  events list loads/empty:    [ ] PASS  [ ] FAIL  Notes:
  DecisionIssued filter:      [ ] PASS  [ ] FAIL  Notes:
  event detail opens:         [ ] PASS  [ ] FAIL  Notes:
  payload readable:           [ ] PASS  [ ] FAIL  Notes:
  no mutation controls:       [ ] PASS  [ ] FAIL  Notes:

Cleanup / Eval:
  cleanup dry-run only:       [ ] PASS  [ ] FAIL  Notes:
  no delete/apply:            [ ] PASS  [ ] FAIL  Notes:
  eval runs allowed:          [ ] PASS  [ ] FAIL  Notes:
  eval errors visible:        [ ] PASS  [ ] FAIL  Notes:

Sweeps:
  quick sweep user-triggered: [ ] PASS  [ ] FAIL  Notes:
  project sweep user-triggered: [ ] PASS  [ ] FAIL  Notes:
  evidence/uncertainty language: [ ] PASS  [ ] FAIL  Notes:
  could-not-verify distinct:  [ ] PASS  [ ] FAIL  Notes:
  long finding cap copy:      [ ] PASS  [ ] FAIL  Notes:
  no remediation controls:    [ ] PASS  [ ] FAIL  Notes:

Sandbox Results:
  list loads/empty state:     [ ] PASS  [ ] FAIL  Notes:
  detail opens:               [ ] PASS  [ ] FAIL  Notes:
  no migrate/apply UI:        [ ] PASS  [ ] FAIL  Notes:
  no package install exec:    [ ] PASS  [ ] FAIL  Notes:

Browser preview:
  static UI renders:          [ ] PASS  [ ] FAIL  Notes:
  native-required error:      [ ] PASS  [ ] FAIL  Notes:
  no blank page:              [ ] PASS  [ ] FAIL  Notes:
  no stack traces:            [ ] PASS  [ ] FAIL  Notes:

Negative safety:
  no command exec UI:         [ ] PASS  [ ] FAIL  Notes:
  no approval UI:             [ ] PASS  [ ] FAIL  Notes:
  no sandbox migration UI:     [ ] PASS  [ ] FAIL  Notes:
  no cleanup deletion UI:     [ ] PASS  [ ] FAIL  Notes:
  no shell plugin UI:         [ ] PASS  [ ] FAIL  Notes:
  no arbitrary argv:          [ ] PASS  [ ] FAIL  Notes:
  no auto-remediation:        [ ] PASS  [ ] FAIL  Notes:
  no broad cleanup controls:   [ ] PASS  [ ] FAIL  Notes:
  no direct fs/db browsing:   [ ] PASS  [ ] FAIL  Notes:

Overall: [ ] PASS  [ ] PASS WITH NOTES  [ ] FAIL
Notes:
Signed:
```

---

## Scope

### In scope

- Native Tauri app startup and window behavior
- Dashboard card data loading
- Overview Status Strip summary
- Bounded selector behavior (reports limit, report type, audit event type, cleanup target)
- Report and audit event detail flows
- Cleanup dry-run card behavior
- Sweep card trigger and result display
- Eval results card
- Sandbox results list and detail
- Safety boundary enforcement (no execution, no mutation, no approval, no deletion UI)
- Redaction styling
- Browser preview fallback behavior
- Error/empty state display

### Out of scope

- CLI command correctness (covered by `tests/test_json_contracts.py`)
- Policy engine behavior (CLI responsibility)
- Sandbox execution (deferred from UI in v0.2.x)
- Approval resolution (not a UI concern in v0.2.x)
- Report or audit export/deletion
- Background scanning or daemon behavior

---

## Known Limitations

| Limitation | Status |
|---|---|
| No automated native window testing | Deferred — no GUI automation framework in v0.2.x |
| No pagination in reports or audit lists | Reports limited to selected value (5/10/25/50); audit list limited to 10 |
| No project path selection for project sweep | Uses CLI working directory at launch |
| No sandbox results pagination | Fixed at 5 results |
| Browser preview cannot show live data | Expected behavior — fallback message shown |
| No strict JSON API envelope | Types are current-contract/loose; no runtime validation |
| Sweeps are user-triggered only | No background scanning or daemon |
| `npm run tauri dev` requires Rust toolchain and system WebKit/GTK dependencies | See `ui/desktop/README.md` for setup |

---

## Future Automation Candidates

These checks could be automated once a GUI test framework is introduced:

| Check | Suggested Approach |
|---|---|
| Native window opens and title is correct | Tauri WebDriver or Playwright with Tauri driver |
| All 14 cards render without error | Snapshot or element-present check |
| Selector option counts (4 limit, 5 type, 13 audit, 3 cleanup) | DOM assertion on `<select>` option counts |
| No free-text inputs in filter positions | `querySelectorAll('input[type=text]')` count check |
| No mutation buttons present | `querySelectorAll('button')` text content assertion |
| Detail view opens on list item click | Click + presence check for detail header |
| Changing audit filter clears detail | Click filter + assert detail header absent |
| Dry-run card shows no delete button | Button absence assertion |
| Redaction notice appears when applied | Element presence check |

Automation is deferred. Do not add a GUI test framework solely for these checks unless
it is already introduced for another reason.

---

*Document version: v0.4.0 — Consolidated authoritative native dashboard smoke checklist for v0.4 CLI-first local alpha*
