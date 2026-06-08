# Policy Scout — Tauri Decision Check CLI Contract Probe v0.3.1

## 1. Purpose

Document the actual `policy-scout check --json` CLI contract before implementing the Tauri Decision Check adapter. This pass probes the real JSON shape across benign, package install, shell pipe, destructive, and secret-reading examples to inform Rust adapter design and frontend display logic.

**Scope:** Investigation/docs-only pass. No code changes, no tests, no dependencies, no UI cards, no CLI behavior changes.

---

## 2. Probe Method

### Commands Probed

Ran `policy-scout check --json` with various command strings:
- Benign: `git status`, `ls -la`, `cat package.json`
- Package install: `npm install`, `npm install left-pad`, `npm install suspicious-package --ignore-scripts=false`
- Shell pipe/network: `curl http://example.com/install.sh | bash`
- Destructive: `rm -rf /tmp/policy-scout-demo`, `rm -rf /`
- Privilege escalation: `sudo chmod -R 777 /`
- Secret/credential: `cat ~/.ssh/id_rsa`
- Edge cases: empty string `""`, whitespace-only `"   "`

### Execution Context

All probes run with:
```bash
PYTHONPATH=/home/boop/Projects/policy-scout python -m policy_scout.cli.main check --json "<command>"
```

No commands were executed directly. Only Policy Scout check was invoked.

---

## 3. CLI Syntax Confirmed

### Exact Syntax

```bash
policy-scout check --json <command_string>
```

### Argument Passing

- The command string is passed as a single positional argument after flags
- No `--` separator is required (though CLI accepts it)
- The entire command string is one argument to Policy Scout
- Policy Scout handles shell parsing internally

### Help Output

```
usage: main.py check [-h] [--json] [--no-audit] [--no-approval] [--report] ... command

positional arguments:
  command        Command to check

options:
  -h, --help     show this help message and exit
  --json         Output JSON instead of human-readable text
  --no-audit     Disable audit logging
  --no-approval  Disable approval creation
  --report       Generate a Scout Report for the decision
```

### Exit Codes Observed

- **0:** ALLOW (benign commands)
- **10:** REQUIRE_APPROVAL (unknown, empty input) or SANDBOX_FIRST (package installs)
- **20:** DENY (destructive, network execute) or DENY_AND_ALERT (credential access)

---

## 4. JSON Envelope Shape

### Top-Level Structure

```json
{
  "request_id": "string",
  "command": "string",
  "decision": "string",
  "risk_score": number,
  "risk_band": "string",
  "category": "string",
  "capabilities": ["string"],
  "reasons": ["string"],
  "recommended_next_action": "string",
  "confidence": number,
  "registry_hits": [object],
  "policy_hits": ["string"]
}
```

### Stability Assessment

All fields observed in every response. No optional fields observed in current probes. Shape is consistent across decision types.

---

## 5. Field Inventory

### Required Fields (always present)

- **request_id:** Unique identifier for the check request (string, UUID-like)
- **command:** The exact command string that was checked (string)
- **decision:** Policy decision (string: ALLOW, REQUIRE_APPROVAL, SANDBOX_FIRST, DENY, DENY_AND_ALERT)
- **risk_score:** Numeric risk score 1-10 (number)
- **risk_band:** Risk category (string: low, medium, high, critical)
- **category:** Command classification (string: safe_read, package_install, network_execute, destructive, credential_adjacent, unknown)
- **capabilities:** List of capability strings (array of strings)
- **reasons:** List of human-readable reasons (array of strings)
- **recommended_next_action:** Recommended next action (string, may be empty)
- **confidence:** Classification confidence 0.0-1.0 (number)
- **registry_hits:** Registry match details (array of objects)
- **policy_hits:** Policy rule matches (array of strings)

### Optional Fields (not observed missing, but may vary)

None observed missing in current probes. All fields present in every response.

---

## 6. Decision/Status Taxonomy Observed

### Decision Values

- **ALLOW:** Safe commands (git status, ls -la, cat package.json)
- **REQUIRE_APPROVAL:** Unknown commands, empty input (python -m pytest, sudo chmod -R 777 /, "", "   ")
- **SANDBOX_FIRST:** Package installs (npm install, npm install left-pad, npm install suspicious-package --ignore-scripts=false)
- **DENY:** Destructive commands, network execute (rm -rf /tmp/policy-scout-demo, rm -rf /, curl http://example.com/install.sh | bash)
- **DENY_AND_ALERT:** Credential access (cat ~/.ssh/id_rsa)

### Exit Code Mapping

- **0:** ALLOW
- **10:** REQUIRE_APPROVAL, SANDBOX_FIRST
- **20:** DENY, DENY_AND_ALERT

---

## 7. Risk/Scoring Fields Observed

### risk_score

- Range: 1-10 observed
- Low risk: 1 (git status, ls -la, cat package.json)
- Medium risk: 3 (python -m pytest, sudo chmod -R 777 /, "", "   ")
- High risk: 5-6 (rm -rf /tmp/policy-scout-demo, npm install, cat ~/.ssh/id_rsa)
- Critical risk: 8 (curl http://example.com/install.sh | bash)

### risk_band

- **low:** risk_score 1-3
- **medium:** risk_score 3-4
- **high:** risk_score 5-6
- **critical:** risk_score 7-10

### confidence

- **0.95:** High confidence (registry matches)
- **0.3:** Low confidence (unknown commands, empty input)

---

## 8. Policy/Rule Fields Observed

### policy_hits

Array of policy rule identifiers that matched:
- `safe_reads_allow` (for safe_read category)
- `unknown_require_approval` (for unknown category)
- `package_install_sandbox_first` (for package_install category)
- `network_execute_deny` (for network_execute category)
- `destructive_system_deny`, `destructive_project_require_approval` (for destructive category)
- `credential_access_deny_and_alert` (for credential_adjacent category)

### registry_hits

Array of registry match objects with:
- `registry_name`: "command_registry"
- `entry_id`: Registry entry ID (e.g., "npm.install", "network.execute", "curl.fetch")
- `confidence`: Match confidence (0.95 for matches)
- `metadata`: Additional metadata (empty {} in observed cases)

Empty array for commands with no registry matches (e.g., destructive commands).

---

## 9. Evidence/Reason Fields Observed

### reasons

Array of human-readable explanation strings:
- 1-3 reasons per command
- Explains why the decision was made
- Examples:
  - "Read-only local commands are low risk."
  - "Package installs may execute lifecycle scripts."
  - "Network-fetched scripts piped directly into a shell are unsafe."
  - "The command can cause destructive filesystem mutation."
  - "The command may expose secrets, tokens, or private keys."
  - "Policy Scout could not confidently classify this command."

### recommended_next_action

String with actionable guidance:
- Empty for benign commands
- "Run sandbox analysis before host install." for package installs
- "Download and inspect the script manually if truly required." for network execute
- "Review destructive command carefully." for destructive commands
- "Review credential access manually." for credential access
- "Review command before approval." for unknown commands

---

## 10. Benign Command Examples

### git status

```json
{
  "request_id": "req_9abb91f30b84",
  "command": "git status",
  "decision": "ALLOW",
  "risk_score": 1,
  "risk_band": "low",
  "category": "safe_read",
  "capabilities": ["filesystem.read"],
  "reasons": ["Read-only local commands are low risk."],
  "recommended_next_action": "",
  "confidence": 0.95,
  "registry_hits": [],
  "policy_hits": ["safe_reads_allow"]
}
```

### ls -la

```json
{
  "request_id": "req_52a55d15dd46",
  "command": "ls -la",
  "decision": "ALLOW",
  "risk_score": 1,
  "risk_band": "low",
  "category": "safe_read",
  "capabilities": ["filesystem.read"],
  "reasons": ["Read-only local commands are low risk."],
  "recommended_next_action": "",
  "confidence": 0.95,
  "registry_hits": [],
  "policy_hits": ["safe_reads_allow"]
}
```

### cat package.json

```json
{
  "request_id": "req_52f186153c3c",
  "command": "cat package.json",
  "decision": "ALLOW",
  "risk_score": 1,
  "risk_band": "low",
  "category": "safe_read",
  "capabilities": ["filesystem.read"],
  "reasons": ["Read-only local commands are low risk."],
  "recommended_next_action": "",
  "confidence": 0.95,
  "registry_hits": [],
  "policy_hits": ["safe_reads_allow"]
}
```

---

## 11. Package Install Examples

### npm install

```json
{
  "request_id": "req_4258a9ee956d",
  "command": "npm install",
  "decision": "SANDBOX_FIRST",
  "risk_score": 6,
  "risk_band": "high",
  "category": "package_install",
  "capabilities": [
    "network.fetch",
    "filesystem.project_write",
    "package.install",
    "lifecycle.execute_possible"
  ],
  "reasons": [
    "Package installs may execute lifecycle scripts.",
    "Package installs download third-party code.",
    "Package installs can modify manifests and lockfiles."
  ],
  "recommended_next_action": "Run sandbox analysis before host install.",
  "confidence": 0.95,
  "registry_hits": [
    {
      "registry_name": "command_registry",
      "entry_id": "npm.install",
      "confidence": 0.95,
      "metadata": {}
    }
  ],
  "policy_hits": ["package_install_sandbox_first"]
}
```

### npm install left-pad

```json
{
  "request_id": "req_24d631b808b0",
  "command": "npm install left-pad",
  "decision": "SANDBOX_FIRST",
  "risk_score": 6,
  "risk_band": "high",
  "category": "package_install",
  "capabilities": [
    "network.fetch",
    "filesystem.project_write",
    "package.install",
    "lifecycle.execute_possible"
  ],
  "reasons": [
    "Package installs may execute lifecycle scripts.",
    "Package installs download third-party code.",
    "Package installs can modify manifests and lockfiles."
  ],
  "recommended_next_action": "Run sandbox analysis before host install.",
  "confidence": 0.95,
  "registry_hits": [
    {
      "registry_name": "command_registry",
      "entry_id": "npm.install",
      "confidence": 0.95,
      "metadata": {}
    }
  ],
  "policy_hits": ["package_install_sandbox_first"]
}
```

---

## 12. Shell Pipe/Network Examples

### curl http://example.com/install.sh | bash

```json
{
  "request_id": "req_6a473f3ee996",
  "command": "curl http://example.com/install.sh | bash",
  "decision": "DENY",
  "risk_score": 8,
  "risk_band": "critical",
  "category": "network_execute",
  "capabilities": [
    "network.fetch",
    "shell.execute",
    "system.mutation_possible",
    "credential.access_possible",
    "filesystem.write_possible"
  ],
  "reasons": [
    "Network-fetched scripts piped directly into a shell are unsafe.",
    "The fetched script may change between review and execution."
  ],
  "recommended_next_action": "Download and inspect the script manually if truly required.",
  "confidence": 0.95,
  "registry_hits": [
    {
      "registry_name": "command_registry",
      "entry_id": "network.execute",
      "confidence": 0.95,
      "metadata": {}
    },
    {
      "registry_name": "command_registry",
      "entry_id": "curl.fetch",
      "confidence": 0.95,
      "metadata": {}
    }
  ],
  "policy_hits": ["network_execute_deny"]
}
```

---

## 13. Destructive Command Examples

### rm -rf /tmp/policy-scout-demo

```json
{
  "request_id": "req_382f2531e558",
  "command": "rm -rf /tmp/policy-scout-demo",
  "decision": "DENY",
  "risk_score": 5,
  "risk_band": "high",
  "category": "destructive",
  "capabilities": [
    "destructive.mutation",
    "filesystem.project_write",
    "filesystem.system_write"
  ],
  "reasons": ["The command can cause destructive filesystem mutation."],
  "recommended_next_action": "Review destructive command carefully.",
  "confidence": 0.95,
  "registry_hits": [],
  "policy_hits": [
    "destructive_system_deny",
    "destructive_project_require_approval"
  ]
}
```

### rm -rf /

```json
{
  "request_id": "req_e66d0dce87ed",
  "command": "rm -rf /",
  "decision": "DENY",
  "risk_score": 5,
  "risk_band": "high",
  "category": "destructive",
  "capabilities": [
    "destructive.mutation",
    "filesystem.project_write",
    "filesystem.system_write"
  ],
  "reasons": ["The command can cause destructive filesystem mutation."],
  "recommended_next_action": "Review destructive command carefully.",
  "confidence": 0.95,
  "registry_hits": [],
  "policy_hits": [
    "destructive_system_deny",
    "destructive_project_require_approval"
  ]
}
```

---

## 14. Secret/Credential Access Examples

### cat ~/.ssh/id_rsa

```json
{
  "request_id": "req_32882374ae68",
  "command": "cat ~/.ssh/id_rsa",
  "decision": "DENY_AND_ALERT",
  "risk_score": 6,
  "risk_band": "high",
  "category": "credential_adjacent",
  "capabilities": [
    "filesystem.read",
    "credential.access_possible"
  ],
  "reasons": [
    "The command may expose secrets, tokens, or private keys.",
    "Credential material should not be exposed to agents."
  ],
  "recommended_next_action": "Review credential access manually.",
  "confidence": 0.95,
  "registry_hits": [],
  "policy_hits": ["credential_access_deny_and_alert"]
}
```

---

## 15. Empty/Invalid Input Behavior

### Empty String ""

```json
{
  "request_id": "req_1f7cf7f160a9",
  "command": "",
  "decision": "REQUIRE_APPROVAL",
  "risk_score": 3,
  "risk_band": "medium",
  "category": "unknown",
  "capabilities": [],
  "reasons": [
    "Policy Scout could not confidently classify this command.",
    "Unknown commands should be reviewed before execution."
  ],
  "recommended_next_action": "Review command before approval.",
  "confidence": 0.3,
  "registry_hits": [],
  "policy_hits": ["unknown_require_approval"]
}
```

### Whitespace-Only "   "

```json
{
  "request_id": "req_8a413639807d",
  "command": "   ",
  "decision": "REQUIRE_APPROVAL",
  "risk_score": 3,
  "risk_band": "medium",
  "category": "unknown",
  "capabilities": [],
  "reasons": [
    "Policy Scout could not confidently classify this command.",
    "Unknown commands should be reviewed before execution."
  ],
  "recommended_next_action": "Review command before approval.",
  "confidence": 0.3,
  "registry_hits": [],
  "policy_hits": ["unknown_require_approval"]
}
```

### Adapter Validation Requirement

CLI does not reject empty or whitespace-only input. It returns `REQUIRE_APPROVAL` with `unknown` category. This is poor UX for a check-only UI.

**Rust adapter must validate:**
- Reject empty string before CLI call
- Reject whitespace-only string before CLI call
- Reject strings exceeding max length before CLI call
- Reject strings containing NUL characters before CLI call
- Return structured error response instead of calling CLI

---

## 16. Tauri Adapter Implications

### CLI Invocation

Rust adapter should call:
```rust
Command::new("policy-scout")
    .args(["check", "--json", &command_text])
    .output()
```

### Input Validation (Required)

Before CLI call, Rust must validate:
1. **Empty check:** Reject if `command_text.is_empty()`
2. **Whitespace check:** Reject if `command_text.trim().is_empty()`
3. **Max length:** Reject if `command_text.len() > 2000` (or 4000)
4. **NUL check:** Reject if `command_text.contains('\0')`
5. **No shell splitting:** Do not split command into shell words in Rust
6. **No shell plugin:** Never call `Command::new(command_text)`

### Error Handling

- Return `CliJsonResponse { ok: false, exit_code: -1, data: None, error: Some("..."), stderr_summary: None }` for invalid input
- Return CLI response as-is for valid input (including DENY decisions)
- Never expose raw shell errors to frontend

### Exit Code Handling

- **0:** ALLOW (display as success)
- **10:** REQUIRE_APPROVAL or SANDBOX_FIRST (display as review/sandbox)
- **20:** DENY or DENY_AND_ALERT (display as blocked)
- **-1:** Adapter validation error (display as validation error)
- **Other:** CLI error (display as error)

---

## 17. Frontend Display Implications

### Required Fields for Display

- **decision:** Primary badge (ALLOW, REQUIRE_APPROVAL, SANDBOX_FIRST, DENY, DENY_AND_ALERT)
- **risk_score:** Numeric display (1-10)
- **risk_band:** Color coding (low, medium, high, critical)
- **category:** Label (safe_read, package_install, network_execute, destructive, credential_adjacent, unknown)
- **capabilities:** Pill badges (array of strings)
- **reasons:** Bulleted list (array of strings)
- **recommended_next_action:** Prominent text (may be empty)

### Optional Fields (graceful degradation)

- **registry_hits:** Optional detail view (array of objects)
- **policy_hits:** Optional detail view (array of strings)
- **confidence:** Optional detail view (number)
- **request_id:** Optional for debugging/audit (string)

### Empty Field Handling

- `recommended_next_action` may be empty string — hide if empty
- `registry_hits` may be empty array — hide if empty
- `policy_hits` may be empty array — hide if empty
- `capabilities` may be empty array — hide if empty

### "Not Executed" Marker

- Must always display "Check only — command was not executed"
- Must be prominent and distinct from execution results
- Must not be confused with ALLOW decision

---

## 18. JSON Type/Interface Proposal

### TypeScript Interface (Current Contract)

```typescript
interface RegistryHit {
  registry_name: string;
  entry_id: string;
  confidence: number;
  metadata: Record<string, unknown>;
}

interface CheckResponse {
  request_id: string;
  command: string;
  decision: "ALLOW" | "REQUIRE_APPROVAL" | "SANDBOX_FIRST" | "DENY" | "DENY_AND_ALERT";
  risk_score: number;
  risk_band: "low" | "medium" | "high" | "critical";
  category: string;
  capabilities: string[];
  reasons: string[];
  recommended_next_action: string;
  confidence: number;
  registry_hits: RegistryHit[];
  policy_hits: string[];
}

interface AdapterErrorResponse {
  ok: false;
  exit_code: -1;
  data: null;
  error: string;
  stderr_summary: null;
}

type CliJsonResponse = CheckResponse | AdapterErrorResponse;
```

### Uncertain Fields Marked Optional

None observed missing in current probes. All fields present in every response. Interface assumes all fields required for now.

### Future Considerations

- If CLI adds optional fields in future, mark them optional in interface
- If CLI removes fields, update interface and add graceful degradation
- Monitor for shape changes across Policy Scout versions

---

## 19. Test Implications

### JSON Contract Tests

**Recommendation:** Add `check --json` contract tests to `tests/test_json_contracts.py` if missing.

Required tests:
- Test that `check --json` returns valid JSON
- Test that required fields exist (decision, risk_score, category, capabilities, reasons)
- Test that decision values are in expected set
- Test that risk_score is 1-10
- Test that risk_band matches risk_score range
- Test that capabilities is array of strings
- Test that reasons is array of strings
- Test exit code mapping (0, 10, 20)

### Rust Adapter Tests

**Recommendation:** Add Rust unit tests for `validate_command_text` helper.

Required tests:
- Test empty string rejection
- Test whitespace-only rejection
- Test max length enforcement
- Test NUL character rejection
- Test valid string acceptance
- Test error response shape

### Frontend Render Tests

**Recommendation:** Add frontend render tests only if a test framework exists later.

Required tests:
- Test DecisionCheckCard renders correctly
- Test decision badge displays correctly
- Test risk score displays correctly
- Test capabilities display correctly
- Test reasons display correctly
- Test error state displays correctly
- Test empty input rejection before CLI

### Native Smoke Tests

**Recommendation:** Add to `docs/compressed/TAURI_NATIVE_MANUAL_SMOKE_CHECKLIST_SOURCE.md`.

Required checks:
- Benign check (git status, ls -la)
- Package install check (npm install)
- Destructive check (rm -rf /tmp/demo)
- Empty input rejection before CLI
- "Not executed" marker visible
- No execution button present

---

## 20. Open Questions

### Max Length

- Should max length be 2,000 or 4,000 characters?
- Should max length be configurable via environment variable?

### Empty Input Behavior

- Should CLI be fixed to reject empty/whitespace input with error?
- Or should adapter always validate before CLI call?

### Field Stability

- Are all fields guaranteed to be present in future versions?
- Should interface mark any fields optional for future-proofing?

### Exit Code Consistency

- Is exit code 10 always REQUIRE_APPROVAL or SANDBOX_FIRST?
- Is exit code 20 always DENY or DENY_AND_ALERT?
- Should adapter distinguish by decision field instead of exit code?

### Redaction

- Does `command` field get redacted for secret-like values?
- Should frontend display redacted command if redaction applied?
- Should redaction notice be shown if command was redacted?

---

## 21. Acceptance Checklist

### CLI Contract

- [ ] CLI syntax confirmed: `policy-scout check --json <command_string>`
- [ ] Command passed as single positional argument
- [ ] Exit codes mapped correctly (0, 10, 20)
- [ ] JSON shape documented
- [ ] Field inventory complete
- [ ] Decision taxonomy documented
- [ ] Risk/scoring fields documented
- [ ] Policy/rule fields documented
- [ ] Evidence/reason fields documented

### Examples

- [ ] Benign command examples documented
- [ ] Package install examples documented
- [ ] Shell pipe/network examples documented
- [ ] Destructive command examples documented
- [ ] Secret/credential access examples documented
- [ ] Empty/invalid input behavior documented

### Adapter Implications

- [ ] Rust adapter validation requirements documented
- [ ] CLI invocation pattern documented
- [ ] Error handling strategy documented
- [ ] Exit code handling documented

### Frontend Implications

- [ ] Required display fields identified
- [ ] Optional fields identified
- [ ] Empty field handling documented
- [ ] "Not executed" marker requirement documented

### TypeScript Interface

- [ ] Current-contract interface drafted
- [ ] Uncertain fields marked optional (if any)
- [ ] Future considerations documented

### Test Implications

- [ ] JSON contract test recommendations documented
- [ ] Rust adapter test recommendations documented
- [ ] Frontend render test recommendations documented
- [ ] Native smoke test recommendations documented

### Docs Pointers

- [ ] Pointer added to IMPLEMENTATION_STATUS.md
- [ ] Pointer added to TAURI_DECISION_CHECK_GUIDED_FAQ_BOUNDARY_SOURCE.md

### Verification

- [ ] No code changes made
- [ ] No tests added
- [ ] No dependencies added
- [ ] No CLI behavior changed
- [ ] Diff-check passes
- [ ] Line count within target (350-700)

---

*Document version: v0.3.1-probe — Decision Check CLI Contract Probe*
