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

- [y] Native window opens without crash
- [n] Window has correct title (Policy Scout or similar) - it has uidesktop, change to PolicyScout
- [y] Dashboard loads without white screen
- [y] No persistent "Tauri runtime unavailable" message visible
- [y] No unhandled JavaScript error banner visible
- [y] No terminal panic
- [y] Cards begin loading (spinner or data visible)
- [y] `BoundaryNote` component is visible at bottom of dashboard ("Read-only" boundary reminder)

---

## C. Global Visual/Readability Checks

- [y] Dark theme readable
- [y] No light broken surfaces
- [y] Cards have readable text
- [y] Redaction placeholders look intentional

---

## D. Overview / Doctor / Data Checks

**Overview Status Strip** — summarizes loaded state across cards

- [y] Strip is visible at the top of the dashboard
- [y] Updates after cards load data
- [y] Shows summary counts or status indicators - reports and eval show 'unknown'
- [y] Does not show any action buttons or mutation controls
- [y] No free-text input in the strip

**Doctor Status card** — invokes `policy-scout doctor --json`

- [y] Card loads without crash
- [y] Shows CLI version or OK status
- [y] Shows registry counts (commands, policies, eval cases)
- [y] No mutation controls

**Data Status card** — invokes `policy-scout data status --json`

- [y] Card loads without crash
- [y] Shows data directory path and counts
- [y] No deletion or cleanup trigger button
- [y] **Contrast:** Count rows (`approvals`, `audit_events`, `reports`, etc.) are readable — dark elevated background, not white/light

---

## E. Decision Check Checks

**Decision Check card** — invokes `policy-scout check --json <command_text>` (check-only; never executes)

- [y] Card appears near top of dashboard
- [y] "CHECK ONLY — commands are classified, never executed" banner visible
- [y] Button says "Check command" (not "Run command" or "Execute")
- [y] Empty/whitespace input rejected with validation error
- [y] `git status` returns ALLOW decision
- [y] `npm install left-pad` returns SANDBOX_FIRST decision
- [y] `rm -rf /` returns DENY decision
- [y] Every result shows "NOT EXECUTED" marker prominently
- [y] FAQ buttons populate local explanation/command only
- [y] FAQ buttons do not auto-check (no CLI call on FAQ click)
- [y] Dangerous examples (e.g., `rm -rf /`) are clearly labeled "Example only — do not run"
- [y] Browser preview shows native-required error if attempting check
- [y] Audit Events list still populates after check probes
- [y] DecisionIssued filter populates after check probes

**v0.3.4 Native Smoke Finding Note:**

During v0.3.4 native smoke, CLI audit data was present (17,152+ events) but the UI did not render audit events. Root cause was a dual contract mismatch:
- Frontend passed `eventType` (camelCase) but Rust expected `event_type` (snake_case)
- CLI returned JSON arrays directly but frontend expected `{ "events": [...] }` wrapper

This validated why native smoke matters: CLI contract verification alone does not catch adapter/frontend shape mismatches. Fix committed in 0ebc137.

---

## F. Reports Checks

**Reports List card** — invokes `policy-scout report list --json --limit <n> [--type <type>]`

### Limit selector

- [y] Selector is visible
- [y] Options are exactly: **5, 10, 25, 50** — no other values
- [y] No free-text input
- [y] Selecting a value refreshes the list

### Type selector

- [y] Selector is visible
- [y] Options are exactly: **All, command_decision, sandbox_result, project_sweep, system_quick_sweep** — no other values
- [y] No free-text input
- [y] Selecting a type refreshes the list

### List behavior

- [y] Reports are listed with IDs
- [y] Changing either selector refreshes the list
- [y] No report deletion or export controls
- [y] IDs are not editable
- [y] Empty state is helpful if no reports exist

**Report Detail** — triggered by clicking a report ID

- [y] Clicking a report ID opens the detail view
- [y] Detail header shows a close/back control
- [y] Report content renders without crash
- [y] Redaction placeholders visible where expected
- [y] Redaction notice readable if present
- [y] Protected placeholders clear
- [y] "Could Not Verify" section appears when could_not_verify has items
- [y] Could-not-verify items are styled as review/unknown (not critical danger)
- [y] Long findings capped at 10 with message: "Showing first 10 of X findings — run from CLI for full results"
- [y] No export, delete, or action buttons
- [y] Closing the detail returns to the list
- [y] Detail cannot be opened for an ID that was not selected from the list (no free-text ID input visible)
- [y] **Contrast:** Report detail card background is dark (not white) — finding items and action items use dark elevated background

---

## G. Audit Checks

**Audit Stats card** — invokes `policy-scout audit stats --json`

- [y] Card loads without crash
- [y] Shows event counts or summary stats
- [y] No deletion, export, or audit-manipulation controls
- [y] **Contrast:** By-type rows (e.g., `ApprovalRequested`, `SweepCompleted`) are readable — dark elevated background, event type names and counts visible

**Audit Events List card** — invokes `policy-scout audit list` or `audit type` depending on filter

### Event type selector

- [y] Selector is visible
- [y] Options are exactly:

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

- [y] Selecting a type refreshes the list
- [y] Selecting "All recent events" returns to the unfiltered list
- [y?] Empty state helpful on fresh data
- [y] DecisionIssued filter works after check probes - the filtering here generally doesnt work, doesnt filter anything.

### List behavior

- [y] Changing event type clears any open event detail
- [y] Event IDs are listed
- [y] No deletion, export, or audit-manipulation controls

**Audit Event Detail** — triggered by clicking an event ID

- [y] Clicking an event ID opens the detail view
- [y] Detail header shows a close/back control
- [y] Event content renders without crash
- [y] Redaction placeholders visible where expected
- [y] Payload readable
- [y] No export, delete, or action buttons
- [y] Closing the detail returns to the list
- [?] Detail cannot be opened for an ID not selected from the list - i dont understand

---

## H. Cleanup / Eval Checks

**Cleanup Dry-Run card** — invokes `policy-scout data cleanup --target <target> --dry-run --json`

- [y] Card header shows **"DRY RUN ONLY"** notice (or equivalent prominent label)
- [y] `BoundaryNote` or similar reminder is visible
- [y] No delete/apply cleanup control

### Cleanup target selector

- [y] Selector is visible
- [y] Options are exactly: **Demo data, Sandbox workspaces, Sandbox results** — no other values
- [y] No free-text input
- [y] Selecting each target refreshes the dry-run result

### Dry-run result behavior

- [y] Result shows what *would* be cleaned, not a deletion confirmation
- [y] No "Delete", "Apply", "Confirm", or "Execute" button visible
- [y] No "Undo" button (nothing was done)
- [y] No network or remote calls implied

**Eval Results card** — invokes `policy-scout eval run --json`

- [y] Card loads without crash
- [y] Shows pass/fail count and pass rate
- [y] Eval run is triggered by user action or on load (not on a background loop)
- [y] No controls to modify eval cases from the UI
- [y] Eval errors visible if any

---

## I. Sweep Checks

**Quick Sweep card** — invokes `policy-scout sweep quick --json`

- [y] Card loads without crash
- [y] Sweep is user-triggered (button)
- [y] Shows findings or "no findings" state
- [y] Redacted values styled distinctly
- [y] No free-text path input
- [y] No controls to modify sweep behavior
- [y] Sweep results use evidence/uncertainty language
- [y] Could-not-verify not treated as confirmed compromise
- [y] Long finding preview cap copy visible if applicable
- [y] No remediation controls

**Project Sweep card** — invokes `policy-scout sweep project --json`

- [y] Card loads without crash
- [y] Sweep is user-triggered (button)
- [y] Shows findings or "no findings" / "could not verify" states
- [y] `SweepResultPreview` component renders findings list correctly
- [y] Redacted values styled distinctly
- [y] No project path selection input (uses CLI default working directory)
- [y] No controls to modify sweep behavior
- [y] Long finding preview cap copy visible if applicable
- [y] No remediation controls

---

## J. Sandbox Results Checks

**Sandbox Results List card** — invokes `policy-scout report list --json --type sandbox_result --limit 5`

- [y] Card loads without crash
- [y] Lists sandbox result reports by ID
- [y] No pagination control yet (known limitation — limit 5, no page selector)
- [y] No deletion controls
- [y] Empty state is helpful if no sandbox results exist

**Sandbox Result Detail** — triggered by clicking a result ID

- [y] Clicking a result ID opens the detail view
- [y] Detail renders without crash
- [y] Redaction placeholders visible where expected
- [y] No migrate/apply UI
- [y] No package install execution from dashboard
- [y] No lifecycle script execution controls

---

## K. Browser Preview Checks

**Launch:** `npm run dev` → open `http://localhost:1420`

- [y] App loads in browser without crashing
- [y] Displays message: "Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data."
- [y] No attempt to load live CLI data visible (no spinner-forever states on cards)
- [y] No JavaScript console errors related to Tauri invoke (expected — invoke is unavailable)
- [y] Layout is visible (not blank page)
- [y] Tauri-only actions show friendly native-required/runtime-unavailable error
- [y] No stack traces to user

---

## L. Negative Safety Checks

Confirm absent:

- [y] Command execution UI
- [y] Approval approve/deny UI
- [y] Sandbox migration/apply UI
- [y] Cleanup deletion/apply UI
- [y] Shell plugin UI
- [y] Arbitrary argv input
- [y] Auto-remediation
- [y] Broad cleanup controls
- [y] Direct filesystem/database browsing

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
  git status clean:           [x] PASS  [ ] FAIL  Notes:
  pytest:                    [x] PASS  [ ] FAIL  Notes:
  doctor:                     [x] PASS  [ ] FAIL  Notes:
  eval:                       [x] PASS  [ ] FAIL  Notes:
  npm build:                  [x] PASS  [ ] FAIL  Notes:
  cargo check:                [x] PASS  [ ] FAIL  Notes:
  cargo test:                 [x] PASS  [ ] FAIL  Notes:

Native launch:
  window opens:               [x] PASS  [ ] FAIL  Notes:
  no blank screen:            [x] PASS  [ ] FAIL  Notes:
  no runtime-unavailable:     [x] PASS  [ ] FAIL  Notes:
  no terminal panic:          [x] PASS  [ ] FAIL  Notes:

Global visual/readability:
  dark theme readable:        [x] PASS  [ ] FAIL  Notes:
  no light broken surfaces:   [x] PASS  [ ] FAIL  Notes:
  cards readable:             [x] PASS  [ ] FAIL  Notes:
  redaction intentional:      [x] PASS  [ ] FAIL  Notes:

Overview / Doctor / Data:
  Status Strip:               [x] PASS  [ ] FAIL  Notes:
  Doctor Status:              [x] PASS  [ ] FAIL  Notes:
  Data Status:                [x] PASS  [ ] FAIL  Notes:

Decision Check:
  card appears:               [x] PASS  [ ] FAIL  Notes:
  check-only language:        [x] PASS  [ ] FAIL  Notes:
  button label:               [x] PASS  [ ] FAIL  Notes:
  empty/whitespace rejected:  [x] PASS  [ ] FAIL  Notes:
  git status => ALLOW:        [x] PASS  [ ] FAIL  Notes:
  npm install => SANDBOX:     [ ] PASS  [x] FAIL  Notes:
  rm -rf / => DENY:           [ ] PASS  [x] FAIL  Notes:
  NOT EXECUTED markers:       [ ] PASS  [x] FAIL  Notes:
  FAQ local-only:             [x] PASS  [ ] FAIL  Notes:
  dangerous examples labeled: [x] PASS  [ ] FAIL  Notes:

Reports:
  list loads/empty state:     [x] PASS  [ ] FAIL  Notes:
  filter/limit controls:      [x] PASS  [ ] FAIL  Notes:
  detail opens:               [x] PASS  [ ] FAIL  Notes:
  redaction notice:           [x] PASS  [ ] FAIL  Notes:
  protected placeholders:     [x] PASS  [ ] FAIL  Notes:
  could-not-verify distinct:  [x] PASS  [ ] FAIL  Notes:
  long finding cap copy:     [x] PASS  [ ] FAIL  Notes:
  no mutation controls:       [x] PASS  [ ] FAIL  Notes:

Audit:
  stats visible:              [x] PASS  [ ] FAIL  Notes:
  events list loads/empty:    [x] PASS  [ ] FAIL  Notes:
  DecisionIssued filter:      [x] PASS  [ ] FAIL  Notes:
  event detail opens:         [x] PASS  [ ] FAIL  Notes:
  payload readable:           [x] PASS  [ ] FAIL  Notes:
  no mutation controls:       [x] PASS  [ ] FAIL  Notes:

Cleanup / Eval:
  cleanup dry-run only:       [x] PASS  [ ] FAIL  Notes:
  no delete/apply:            [x] PASS  [ ] FAIL  Notes:
  eval runs allowed:          [x] PASS  [ ] FAIL  Notes:
  eval errors visible:        [x] PASS  [ ] FAIL  Notes:

Sweeps:
  quick sweep user-triggered: [x] PASS  [ ] FAIL  Notes:
  project sweep user-triggered: [x] PASS  [ ] FAIL  Notes:
  evidence/uncertainty language: [x] PASS  [ ] FAIL  Notes:
  could-not-verify distinct:  [x] PASS  [ ] FAIL  Notes:
  long finding cap copy:      [x] PASS  [ ] FAIL  Notes:
  no remediation controls:    [x] PASS  [ ] FAIL  Notes:

Sandbox Results:
  list loads/empty state:     [x] PASS  [ ] FAIL  Notes:
  detail opens:               [x] PASS  [ ] FAIL  Notes:
  no migrate/apply UI:        [x] PASS  [ ] FAIL  Notes:
  no package install exec:    [x] PASS  [ ] FAIL  Notes:

Browser preview:
  static UI renders:          [x] PASS  [ ] FAIL  Notes:
  native-required error:      [x] PASS  [ ] FAIL  Notes:
  no blank page:              [x] PASS  [ ] FAIL  Notes:
  no stack traces:            [x] PASS  [ ] FAIL  Notes:

Negative safety:
  no command exec UI:         [x] PASS  [ ] FAIL  Notes:
  no approval UI:             [x] PASS  [ ] FAIL  Notes:
  no sandbox migration UI:     [x] PASS  [ ] FAIL  Notes:
  no cleanup deletion UI:     [x] PASS  [ ] FAIL  Notes:
  no shell plugin UI:         [x] PASS  [ ] FAIL  Notes:
  no arbitrary argv:          [x] PASS  [ ] FAIL  Notes:
  no auto-remediation:        [x] PASS  [ ] FAIL  Notes:
  no broad cleanup controls:   [x] PASS  [ ] FAIL  Notes:
  no direct fs/db browsing:   [x] PASS  [ ] FAIL  Notes:

Overall: [ ] PASS  [x] PASS WITH NOTES  [ ] FAIL
Notes: i added nots earlier in the testing at each item.
Signed: Love, boop.
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
