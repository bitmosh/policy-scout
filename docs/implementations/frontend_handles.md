# Frontend Handles — Backend Wire-Up Reference

Tracks every backend feature that needs a corresponding Tauri command + React surface.
Written as Phase 1 wraps up; update as new phases land.

Each entry: CLI command → proposed Tauri command name → React home → menu location.
Validation notes flag what the Rust side must check before forwarding to the CLI.

---

## Menu Placement Summary

| Category | Menu | New or Existing |
|---|---|---|
| Lockdown kill switch | Persistent status bar (always visible) | New |
| Chain integrity | Audit section | Existing |
| Registry + system health | Doctor / Health panel | Existing (expanded) |
| Incident response (preserve, clearance) | Security menu | New |
| Playbook guidance | Inline in Finding detail card | Existing (enriched) |

---

## Lockdown Kill Switch

**Lives in: persistent status bar — always visible regardless of active view**

The lockdown state is the highest-severity control in the system. It must never be buried in a submenu. Recommended placement: a badge/pill in the top-right of the shell (near the window controls). Red pill = LOCKDOWN ACTIVE; grey pill = normal operation.

| Backend | CLI | Tauri command | Rust validation |
|---|---|---|---|
| Activate lockdown | `policy-scout lockdown on --reason "..."` | `activate_lockdown(reason: String)` | reason ≤ 500 chars, strip control chars |
| Deactivate lockdown | `policy-scout lockdown off` | `deactivate_lockdown()` | none |
| Read lockdown status | `policy-scout lockdown status` | `get_lockdown_status()` | none |

**React surfaces:**
- `LockdownStatusBadge` (status bar, always rendered) — polls `get_lockdown_status()` every 10 s; shows red "LOCKDOWN" pill or grey "Normal" badge
- `LockdownActivateModal` — two-step confirm (reason text → "Confirm Activate"), calls `activate_lockdown()`
- `LockdownDeactivateModal` — two-step confirm, calls `deactivate_lockdown()`

**Notes:**
- First click opens confirm modal, NOT the action itself. Lockdown is irreversible until manually cleared.
- Reason field pre-filled with "Manual activation" but editable.
- On activation, force-refresh the rest of the UI (approvals, doctor, audit) to reflect denied state.

---

## Audit: Chain Integrity

**Lives in: Audit section (existing) — new sub-tab or expandable row**

| Backend | CLI | Tauri command | Rust validation |
|---|---|---|---|
| Verify JSONL chain | `policy-scout audit verify-chain` | `verify_audit_chain()` | none |
| Read chain head seq | (reads `.chain_head` file) | `get_chain_head_status()` | none |

**React surfaces:**
- `AuditChainStatus` widget — inline in Audit header bar. Shows "Chain ✓ seq=N" or "Chain ✗ N error(s)" badge.
- `AuditChainVerifyPanel` — expanded view when badge is clicked. Shows per-error table (lineno, kind, detail) if any errors exist. "Re-verify" button.

**Data shape from `verify_audit_chain()`:**
```json
{
  "verified": true,
  "total_entries": 1247,
  "message": "All 1247 entries verified.",
  "errors": []
}
```

**Notes:**
- On first render, auto-run once. Don't re-run on every page visit (it reads the whole JSONL).
- `errors[].kind` values: `"tamper"` (red), `"gap"` (orange), `"parse_error"` (yellow). Color-code rows accordingly.
- If `total_entries === 0` and no errors, show "No chain data yet" rather than a green checkmark.

---

## Doctor / Health Panel

**Lives in: Doctor / Health panel (existing) — new check rows added**

All checks arrive via the existing `run_doctor()` Tauri command (or equivalent). These are new keys in the `checks` dict:

| Check key | Source | What to render |
|---|---|---|
| `lockdown_status` | `check_lockdown_status()` | `warning` if active (show reason), `ok` if not |
| `registry_integrity` | `check_registry_integrity()` | `ok` with file count, `error` with file list |
| `audit_chain_head` | `check_audit_chain_head()` | `ok` with seq=N, `warning` if absent |

**React surfaces:**
- These are new rows in the existing doctor check table — no new component needed, they use the existing `DoctorCheckRow` pattern.
- `registry_integrity` error state: expand to show the specific failed files (available in `errors[]`).
- `lockdown_status` warning state: show inline "Deactivate" button that opens `LockdownDeactivateModal`.

---

## Security Menu (New)

**New top-level menu item: "Security"**

Houses the incident response workflow. Subsections:

### Evidence Preservation

| Backend | CLI | Tauri command | Rust validation |
|---|---|---|---|
| Capture evidence archive | `policy-scout preserve` | `preserve_evidence(output_dir: Option<String>)` | if output_dir provided: validate it is an absolute path, no traversal |

**React surfaces:**
- `PreserveEvidenceCard` — button "Preserve Evidence Now", optional output path field, shows archive path + artifact list on success.

**Data shape:**
```json
{
  "path": "/home/user/.local/share/policy-scout/evidence/evidence_20260610_143022.zip",
  "artifact_count": 7,
  "artifacts": ["system_info.json", "audit.db", "audit.jsonl", "processes.txt", "ports.txt", "shell_profiles.json", "git_log.txt"],
  "errors": []
}
```

**Notes:**
- Offer a "Download" link to open the archive in the file manager after creation (use Tauri `shell.open()` on the archive path).
- Preserve should be the first suggested action when lockdown is activated — consider auto-suggesting it in the `LockdownActivateModal` as a second step.

### Clearance Check

| Backend | CLI | Tauri command | Rust validation |
|---|---|---|---|
| Run clearance checks | `policy-scout clearance` | `run_clearance_check()` | none |

**React surfaces:**
- `ClearanceCheckPanel` — "Run Clearance Check" button, per-check result rows (check name, ✓/✗, message), summary line.
- If all checks pass: show "Deactivate Lockdown" button (opens `LockdownDeactivateModal`).
- If any check fails: show "View Issues" and do NOT offer deactivate button automatically.

**Data shape:**
```json
{
  "cleared": false,
  "summary": "3/4 checks passed. Some checks failed. Review findings before deactivating lockdown.",
  "checks": [
    { "name": "lockdown_active", "passed": true, "message": "Lockdown is active" },
    { "name": "registry_integrity", "passed": true, "message": "All 4 registry files verified" },
    { "name": "audit_chain", "passed": true, "message": "Audit chain verified (1247 entries)" },
    { "name": "process_check", "passed": false, "message": "Suspicious process(es) found: 1 match(es)" }
  ]
}
```

### Integrity Check

| Backend | CLI | Tauri command | Rust validation |
|---|---|---|---|
| Verify registry files | `policy-scout integrity check` | `check_registry_integrity()` | none |
| Regenerate manifest (dev) | `policy-scout integrity update-manifest --version X` | `update_registry_manifest(version: String)` | version: alphanumeric + `.` + `-`, ≤ 30 chars |

**React surfaces:**
- `IntegrityCheckCard` — "Verify Integrity" button, shows files_checked count, error list if any.
- `update_registry_manifest` is dev-only; gate behind a `--dev` flag or hide behind an "Advanced" disclosure.

---

## Findings: Playbook Details (Inline Enrichment)

**Lives in: existing Finding detail card — no new menu needed**

When the backend enriches a finding with `response_playbook`, the frontend just needs to render it. The data is already attached to the finding dict.

**React surfaces:**
- `PlaybookDetailSection` — rendered inside `FindingDetailCard` (or `SweepFindingCard`) when `finding.response_playbook` is present.
- Collapsible — default collapsed to not overwhelm the card.
- Sections: "Immediate Actions" (red), "Investigation Steps" (orange), "Containment" (yellow), "Escalation Criteria" (grey).
- Only shown for `severity === "critical"` or `severity === "high"` (backend already gates this, but double-check client-side).

**Data shape (already in finding dict after enrichment):**
```json
{
  "response_playbook": {
    "id": "playbook_suspicious_package",
    "title": "Suspicious Package Installation",
    "summary": "A suspicious or potentially malicious package was detected.",
    "immediate_actions": ["Remove the package immediately if installed.", "..."],
    "investigation_steps": ["Run `policy-scout sweep --project .`", "..."],
    "containment": ["Activate lockdown if exfiltration is suspected.", "..."],
    "escalation_criteria": ["Network connections to unexpected hosts during install.", "..."]
  }
}
```

---

## Tauri Command Summary (Rust `lib.rs` additions)

Quick reference for the Rust side. All commands forward to CLI and return `Result<String, String>`.

```rust
// Lockdown
fn activate_lockdown(reason: String) -> Result<String, String>
fn deactivate_lockdown() -> Result<String, String>
fn get_lockdown_status() -> Result<String, String>

// Audit
fn verify_audit_chain() -> Result<String, String>
fn get_chain_head_status() -> Result<String, String>

// Integrity
fn check_registry_integrity() -> Result<String, String>
fn update_registry_manifest(version: String) -> Result<String, String>  // dev-only

// Incident Response
fn preserve_evidence(output_dir: Option<String>) -> Result<String, String>
fn run_clearance_check() -> Result<String, String>
```

All new commands follow the same input validation pattern as existing ones (regex-checked IDs, length bounds, no shell metacharacters in string args).

---

## Secret Scanning (New — Security Menu)

**Lives in: Security menu — "Secret Scan" subsection**

The scan commands surface credential-leak risk. All four scan modes (directory, file, staged, history) should be accessible from the UI, with the staged check surfacing prominently as a pre-commit safety net.

### Directory / File Scan

| Backend | CLI | Tauri command | Rust validation |
|---|---|---|---|
| Scan directory | `policy-scout scan dir <path>` | `scan_directory(path: String, entropy: bool)` | path must be absolute, no traversal, exists + is dir |
| Scan file | `policy-scout scan file <path>` | `scan_file(path: String, entropy: bool)` | path must be absolute, no traversal, exists + is file |

**React surfaces:**
- `SecretScanCard` — path picker (defaults to current project root), entropy toggle, "Scan" button.
- Results: severity-bucketed finding list. Each row: file+line, service/type, redacted value, action guidance.
- Exit code 2 (critical/high) renders a red banner. Exit code 1 (medium/low) renders orange. Exit code 0 renders green.

**Data shape from `scan_directory()` / `scan_file()`:**
```json
{
  "scan_id": "scan_a1b2c3d4e5f6",
  "scan_type": "directory",
  "target": "/home/user/project",
  "finding_count": 2,
  "severity_counts": { "critical": 1, "high": 1 },
  "files_scanned": 47,
  "duration_ms": 312,
  "errors": [],
  "findings": [
    {
      "secret_type": "aws_access_key",
      "service": "AWS",
      "severity": "critical",
      "source": "deploy/.env",
      "line": 3,
      "column": 20,
      "redacted_value": "AKIA***12",
      "guidance": "Rotate immediately at https://console.aws.amazon.com/iam/"
    }
  ]
}
```

### Staged Scan (Pre-Commit)

| Backend | CLI | Tauri command | Rust validation |
|---|---|---|---|
| Scan staged git files | `policy-scout scan staged --repo <path>` | `scan_staged(repo_path: Option<String>)` | if provided: absolute path, exists + is dir |

**React surfaces:**
- `StagedScanWidget` — lives in the Audit section header or as a "Pre-Commit Check" shortcut in Security. One-click trigger. Auto-runs when the user opens the Security view if there are staged files.
- Shows: files scanned, findings with severity color. Critical/high findings block with a red callout ("Resolve before committing").

### History Scan

| Backend | CLI | Tauri command | Rust validation |
|---|---|---|---|
| Scan git history | `policy-scout scan history --repo <path> --max-commits N --since <ref>` | `scan_history(repo_path: Option<String>, max_commits: u32, since_ref: Option<String>)` | max_commits 1–5000; since_ref: alphanumeric + `/` + `.` + `-`, ≤ 100 chars |

**React surfaces:**
- `HistoryScanPanel` — advanced option, collapsed by default. "Scan History" button, max-commits slider (default 200), optional "Since ref" input.
- Findings include `commit` field (short hash linked to `git show`). Display with commit column in the results table.
- History findings show the `HISTORY WARNING` callout from `generate_guidance(is_in_history=True)`: red box noting that removal alone is insufficient and rotation is required.

**Notes (all scan modes):**
- Findings with `commit` set = history finding; show history rewrite warning inline.
- `guidance` field is always actionable text; render as a yellow callout below the finding row (collapsed, expand on click).
- The scanner automatically skips binary files, `.git/`, `node_modules/`, `__pycache__`, `dist/`, etc. — no need to expose these skip rules in the UI.
- Pattern count comes from `scanner.pattern_count` (currently 22+). Surface as "Scanning with N credential patterns" in the panel header.

---

## Git Integration ([12] — Security Menu + Status Bar)

**Lives in: Security menu — "Git" subsection + status bar hook indicator**

Git integration adds hook installation, lockfile tamper detection, and git context enrichment to existing commands. The UI primarily needs to surface hook status and lockfile warnings.

### Git Hook Management

| Backend | CLI | Tauri command | Rust validation |
|---|---|---|---|
| Install git hooks | `policy-scout git hooks install --repo <path>` | `install_git_hooks(repo_path: Option<String>)` | optional absolute path |
| Uninstall git hooks | `policy-scout git hooks uninstall --repo <path>` | `uninstall_git_hooks(repo_path: Option<String>)` | optional absolute path |
| Hook status | `policy-scout git hooks status --repo <path>` | `get_git_hooks_status(repo_path: Option<String>)` | optional absolute path |

**React surfaces:**
- `GitHooksStatusCard` — shows installed/not-installed badge per hook type (pre-commit, post-commit). Toggle install/uninstall inline.
- On install: confirm dialog noting that the hook will run `policy-scout scan staged` before each commit.

### Lockfile Tamper / Manifest Mismatch

| Backend | CLI | Tauri command | Rust validation |
|---|---|---|---|
| Check lockfile diff | `policy-scout git lockfile-check --repo <path>` | `check_lockfile_integrity(repo_path: Option<String>)` | optional absolute path |

**React surfaces:**
- `LockfileDiffCard` — shows OK / MISMATCH status. Mismatch expands to show added/removed packages with their versions.
- Surfaced as a Doctor check row (read-only) and as an actionable card in Security → Git.

### Git Context (Enrichment — No Direct UI)

Git context (`branch`, `commit`, `dirty`, `remote`) is automatically attached to `policy-scout check` and sweep results when git is available. The frontend already renders these fields in report detail views; no new component needed.

**Data shape enriched on check/sweep results:**
```json
{
  "git_context": {
    "branch": "feature/new-package",
    "commit": "abc123de",
    "dirty": true,
    "remote": "origin"
  }
}
```

---

## Tauri Command Summary (additions since last update)

```rust
// [04] Secret Scanning
fn scan_directory(path: String, entropy: bool) -> Result<String, String>
fn scan_file(path: String, entropy: bool) -> Result<String, String>
fn scan_staged(repo_path: Option<String>) -> Result<String, String>
fn scan_history(repo_path: Option<String>, max_commits: u32, since_ref: Option<String>) -> Result<String, String>

// [12] Git Integration
fn install_git_hooks(repo_path: Option<String>) -> Result<String, String>
fn uninstall_git_hooks(repo_path: Option<String>) -> Result<String, String>
fn get_git_hooks_status(repo_path: Option<String>) -> Result<String, String>
fn check_lockfile_integrity(repo_path: Option<String>) -> Result<String, String>
```

---

## Open Questions for the Menus Conversation

1. **Lockdown status bar placement** — top-right shell vs. sidebar vs. floating badge? The requirement is "always visible." Top-right feels right but conflicts with window controls on some OSes.
2. **Security menu name** — "Security" vs. "Incident Response" vs. "Response"? "Security" is shorter but broader.
3. **Clearance → Deactivate flow** — should Clearance and Lockdown deactivate be a single guided wizard, or two separate actions the user composes?
4. **Doctor vs. Security overlap** — lockdown status appears in both Doctor (read-only health check) and Security (actionable toggle). That duplication is intentional: Doctor is a summary, Security is the action surface. Worth confirming this feels right in the actual UI.
5. **Playbook collapsing** — should playbooks be fully hidden until the user explicitly expands, or should "Immediate Actions" always show for critical findings?
