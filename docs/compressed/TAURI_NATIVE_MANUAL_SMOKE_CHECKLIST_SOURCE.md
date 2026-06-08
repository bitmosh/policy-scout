# Tauri Native Manual Smoke Checklist

Source document for Policy Scout Tauri v0.2.x read-only UI manual verification.
Run at significant Tauri checkpoints and before each v0.3.x feature expansion.

---

## 1. Purpose

CI covers TypeScript compilation, Rust type-checking, and Rust unit tests for all
six validators. It does not validate native window startup, live data loading,
card rendering, selector behavior, or UI boundary enforcement.

This checklist fills that gap. It is a repeatable manual verification pass that
confirms the native Tauri app opens correctly, loads live Policy Scout CLI data,
and does not expose any mutation, execution, approval, or deletion surface.

---

## 2. Scope

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

## 3. Preconditions

Before running the native smoke checklist:

1. Policy Scout CLI is installed and accessible:

   ```bash
   policy-scout doctor --json
   ```

2. Audit data exists (run at least one sweep or command check to generate events):

   ```bash
   policy-scout sweep quick
   policy-scout check -- ls
   ```

3. At least one report exists:

   ```bash
   policy-scout report list --json --limit 5
   ```

4. Local automated checks pass:

   ```bash
   cd /home/boop/Projects/policy-scout
   python -m pytest -q
   PYTHONPATH=/home/boop/Projects/policy-scout python -m policy_scout.cli.main doctor --json
   PYTHONPATH=/home/boop/Projects/policy-scout python -m policy_scout.cli.main eval run

   cd /home/boop/Projects/policy-scout/ui/desktop
   npm run build

   cd /home/boop/Projects/policy-scout/ui/desktop/src-tauri
   cargo check
   cargo test
   ```

5. Record the current commit before starting:

   ```bash
   git -C /home/boop/Projects/policy-scout log --oneline -1
   ```

---

## 4. Commands to Start the Native App

### Native Tauri runtime (required for live data)

```bash
cd /home/boop/Projects/policy-scout/ui/desktop
npm run tauri dev
```

This launches the native Tauri application window. All live data comes from the installed
`policy-scout` CLI binary. The UI is read-only.

### Browser/Vite preview (static layout only — no live data)

```bash
cd /home/boop/Projects/policy-scout/ui/desktop
npm run dev
```

Opens a browser at `http://localhost:1420`. This mode cannot load live CLI data because
Tauri invoke APIs are unavailable in the browser. It should show the runtime unavailable
fallback message.

---

## 5. Global Safety Boundaries

Confirm at all times that the UI does **not** present:

- [ ] Any button or control to execute a Policy Scout command on behalf of the user
- [ ] Any approval resolution button or form
- [ ] Any sandbox migration button or trigger
- [ ] Any cleanup delete/apply button (dry-run preview only)
- [ ] Any free-text `<input>` field in a filter or selector context
- [ ] Any shell or command line input
- [ ] Any report or audit export/download button
- [ ] Any direct SQLite access or filesystem browsing control

If any of the above is present, this is a safety boundary regression. **Stop and report.**

---

## 6. Browser Preview Behavior

**Launch:** `npm run dev` → open `http://localhost:1420`

- [ ] App loads in browser without crashing
- [ ] Displays message: "Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data."
- [ ] No attempt to load live CLI data visible (no spinner-forever states on cards)
- [ ] No JavaScript console errors related to Tauri invoke (expected — invoke is unavailable)
- [ ] Layout is visible (not blank page)

---

## 7. Native App Startup Checks

**Launch:** `npm run tauri dev`

- [ ] Native window opens without crash
- [ ] Window has correct title (Policy Scout or similar)
- [ ] Dashboard loads without white screen
- [ ] No persistent "Tauri runtime unavailable" message visible
- [ ] No unhandled JavaScript error banner visible
- [ ] Cards begin loading (spinner or data visible)
- [ ] `BoundaryNote` component is visible at bottom of dashboard ("Read-only" boundary reminder)

---

## 8. Overview Status Strip Checks

The strip summarizes loaded state across cards.

- [ ] Strip is visible at the top of the dashboard
- [ ] Updates after cards load data
- [ ] Shows summary counts or status indicators
- [ ] Does not show any action buttons or mutation controls
- [ ] No free-text input in the strip

---

## 9. Doctor / Data Status Checks

**Doctor Status card** — invokes `policy-scout doctor --json`

- [ ] Card loads without crash
- [ ] Shows CLI version or OK status
- [ ] Shows registry counts (commands, policies, eval cases)
- [ ] No mutation controls

**Data Status card** — invokes `policy-scout data status --json`

- [ ] Card loads without crash
- [ ] Shows data directory path and counts
- [ ] No deletion or cleanup trigger button

---

## 10. Reports List Checks

**Card** — invokes `policy-scout report list --json --limit <n> [--type <type>]`

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

---

## 11. Report Detail Checks

**Triggered by** — clicking a report ID in the Reports List

- [ ] Clicking a report ID opens the detail view
- [ ] Detail header shows a close/back control
- [ ] Report content renders without crash
- [ ] Redaction placeholders visible where expected (see §20)
- [ ] No export, delete, or action buttons
- [ ] Closing the detail returns to the list
- [ ] Detail cannot be opened for an ID that was not selected from the list
  (no free-text ID input visible)

---

## 12. Audit Stats Checks

**Card** — invokes `policy-scout audit stats --json`

- [ ] Card loads without crash
- [ ] Shows event counts or summary stats
- [ ] No deletion, export, or audit-manipulation controls

---

## 13. Audit Events List Checks

**Card** — invokes `policy-scout audit list` or `audit type` depending on filter

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

### List behavior

- [ ] Changing event type clears any open event detail
- [ ] Event IDs are listed
- [ ] No deletion, export, or audit-manipulation controls

---

## 14. Audit Event Detail Checks

**Triggered by** — clicking an event ID in the Audit Events List

- [ ] Clicking an event ID opens the detail view
- [ ] Detail header shows a close/back control
- [ ] Event content renders without crash
- [ ] Redaction placeholders visible where expected (see §20)
- [ ] No export, delete, or action buttons
- [ ] Closing the detail returns to the list
- [ ] Detail cannot be opened for an ID not selected from the list

---

## 15. Cleanup Dry-Run Checks

**Card** — invokes `policy-scout data cleanup --target <target> --dry-run --json`

- [ ] Card header shows **"DRY RUN ONLY"** notice (or equivalent prominent label)
- [ ] `BoundaryNote` or similar reminder is visible

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

---

## 16. Eval Results Checks

**Card** — invokes `policy-scout eval run --json`

- [ ] Card loads without crash
- [ ] Shows pass/fail count and pass rate
- [ ] Eval run is triggered by user action or on load (not on a background loop)
- [ ] No controls to modify eval cases from the UI

---

## 17. Sweep Cards Checks

**Quick Sweep card** — invokes `policy-scout sweep quick --json`

- [ ] Card loads without crash
- [ ] Sweep is user-triggered (button) or on load
- [ ] Shows findings or "no findings" state
- [ ] Redacted values styled distinctly (see §20)
- [ ] No free-text path input
- [ ] No controls to modify sweep behavior

**Project Sweep card** — invokes `policy-scout sweep project --json`

- [ ] Card loads without crash
- [ ] Sweep is user-triggered (button) or on load
- [ ] Shows findings or "no findings" / "could not verify" states
- [ ] `SweepResultPreview` component renders findings list correctly
- [ ] Redacted values styled distinctly
- [ ] No project path selection input (uses CLI default working directory)
- [ ] No controls to modify sweep behavior

---

## 18. Sandbox Results Checks

**Sandbox Results List card** — invokes `policy-scout report list --json --type sandbox_result --limit 5`

- [ ] Card loads without crash
- [ ] Lists sandbox result reports by ID
- [ ] No pagination control yet (known limitation — limit 5, no page selector)
- [ ] No deletion controls

**Sandbox Result Detail** — triggered by clicking a result ID

- [ ] Clicking a result ID opens the detail view
- [ ] Detail renders without crash
- [ ] Redaction placeholders visible where expected
- [ ] No migration, apply, or delete buttons
- [ ] No lifecycle script execution controls

---

## 19. Empty / Error State Checks

- [ ] If a card has no data (empty list), it shows an empty state, not a crash or blank card
- [ ] If a CLI call fails (non-zero exit), the card shows an error state with a message
- [ ] Error states do not expose raw stack traces in the UI
- [ ] Error states do not expose the full `stderr` dump unredacted
- [ ] Loading states (spinner or placeholder) are visible during data fetch
- [ ] Timeout or slow CLI response does not freeze the entire UI

---

## 20. Redaction / Evidence Styling Checks

- [ ] Redacted values (e.g., `<redacted:possible_token>`) are displayed using the `EvidenceText` component styling — visually distinct, not plain unstyled text
- [ ] `RedactionNotice` component appears when redaction has been applied
- [ ] Could-not-verify findings in sweep results look like **review/unknown** states (amber/neutral), not critical danger states
- [ ] No raw secret-like strings visible in card output
- [ ] Redaction placeholders are not broken HTML (no raw `<` / `>` visible as markup)

---

## 21. Negative Safety Checks

Each of these should be **absent**. If present, it is a safety boundary regression.

- [ ] No `<input type="text">` for command entry
- [ ] No `<input type="text">` for report ID or event ID (IDs come from list selection only)
- [ ] No `<button>` labeled "Run", "Execute", "Apply", "Delete", "Approve", "Reject", "Migrate" or equivalent
- [ ] No `<textarea>` or code entry field
- [ ] No fetch/XHR calls to external URLs visible in browser network tab
- [ ] No Tauri invoke calls with unsanitized free-text values (validated in Rust layer)
- [ ] No `window.location` redirect to external URLs
- [ ] No clipboard-write of sensitive data on click

---

## 22. Pass/Fail Recording Template

Copy and fill in before archiving or filing as a CI gate note.

```
Date:
Commit (git log --oneline -1):
OS + version:
Policy Scout CLI version (policy-scout doctor --json):
Tauri version (npm run tauri dev output):

Native launch result:         [ ] PASS  [ ] FAIL  Notes:
Browser preview fallback:     [ ] PASS  [ ] FAIL  Notes:
Cards loaded (all 14):        [ ] PASS  [ ] FAIL  Notes:
Overview strip:                [ ] PASS  [ ] FAIL  Notes:
Reports selector (exact 4+4): [ ] PASS  [ ] FAIL  Notes:
Audit selector (exact 13):    [ ] PASS  [ ] FAIL  Notes:
Cleanup selector (exact 3):   [ ] PASS  [ ] FAIL  Notes:
Report detail flow:            [ ] PASS  [ ] FAIL  Notes:
Audit detail flow:             [ ] PASS  [ ] FAIL  Notes:
Sandbox detail flow:           [ ] PASS  [ ] FAIL  Notes:
Dry-run only (no delete):      [ ] PASS  [ ] FAIL  Notes:
Redaction display:             [ ] PASS  [ ] FAIL  Notes:
Negative safety checks:        [ ] PASS  [ ] FAIL  Notes:
Empty/error states:            [ ] PASS  [ ] FAIL  Notes:

Overall: [ ] PASS  [ ] FAIL
Signed:
```

---

## 23. Known Limitations

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

## 24. Future Automation Candidates

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

*Document version: v0.2.41 — Created as part of Tauri Native Manual Smoke Checklist v0*
