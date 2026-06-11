# Implementation Plan — Gap 9: Incident Response Layer

## Problem
Policy Scout detects and reports but stops there. When a critical finding is generated — a malicious lifecycle script, a credential-exfiltrating process, a suspicious persistence mechanism — the tool produces a report and leaves the user staring at it without knowing what to do. A developer who doesn't know the response steps is as vulnerable as one who never ran the sweep.

## Goal
Structured incident playbooks embedded in Scout Reports, an evidence preservation command, a kill switch for immediate lockdown, and a post-incident clearance workflow.

---

## New Module: `policy_scout/response/`

```
policy_scout/response/
├── __init__.py
├── playbooks.py       # playbook registry + lookup by finding category
├── preserve.py        # evidence collection + archival
├── lockdown.py        # kill switch: set incident mode, deny all writes
└── clearance.py       # post-incident health verification
```

```
policy_scout/data/
└── playbooks.yaml     # playbook registry (finding_category → steps)
```

---

## Implementation Approach

### Step 1 — Playbook Registry (`data/playbooks.yaml`)

Each playbook is keyed by finding category and provides numbered response steps, categorized by urgency.

```yaml
malicious_lifecycle_script:
  title: "Malicious Lifecycle Script Detected"
  urgency: critical
  immediate_steps:
    - "Do NOT migrate the sandbox install to your project."
    - "If this package is already in your node_modules, run: npm uninstall <package-name>"
    - "Check git history to determine when this package was added: git log --all -S '<package-name>' -- package.json"
    - "Assume any credentials accessible during past installs may be compromised."
  credential_steps:
    - "Rotate all tokens stored in .env, .npmrc, and shell environment variables."
    - "Check ~/.npmrc and ~/.yarnrc for stolen registry tokens."
    - "Review GitHub tokens: https://github.com/settings/tokens — revoke any you don't recognize."
  investigation_steps:
    - "Run: policy-scout sweep project — check for persistence traces."
    - "Run: policy-scout sweep quick — check for unexpected processes and ports."
    - "Review recent shell history: cat ~/.bash_history | tail -100"
    - "Check for new cron jobs: crontab -l"
    - "Check systemd user services: systemctl --user list-units"
  cleanup_steps:
    - "Remove the malicious package from node_modules."
    - "Regenerate lockfile: npm install --package-lock-only"
    - "Commit the lockfile change with a note explaining the remediation."
  recovery_signal:
    - "Run: policy-scout clearance --since <incident-timestamp> — verify clean sweep."

possible_credential_exposure:
  title: "Possible Credential Exposure"
  urgency: critical
  immediate_steps:
    - "Identify which credentials were potentially exposed (see finding evidence)."
    - "Rotate immediately — do not wait to confirm exploitation."
    - "Generate new credentials before revoking old ones if the service supports it."
  service_specific:
    github_token: "Revoke at https://github.com/settings/tokens"
    npm_token: "Revoke at https://www.npmjs.com/settings/<username>/tokens"
    aws_key: "Rotate at https://console.aws.amazon.com/iam/ — also check CloudTrail for anomalous activity"
    generic: "Contact the service provider and follow their key rotation procedure."
  investigation_steps:
    - "Check if the secret was in git history: policy-scout scan --history"
    - "If in history, rewrite with: git filter-repo --path <file> --invert-paths"
    - "Check if the repo was ever public or pushed to a remote."
  recovery_signal:
    - "Run: policy-scout scan --project — verify no remaining exposed secrets."

suspicious_persistence:
  title: "Suspicious Persistence Mechanism Detected"
  urgency: high
  immediate_steps:
    - "Do not reboot yet — the persistence mechanism may re-establish itself on boot."
    - "Document exactly what was found before removing it."
    - "Run: policy-scout preserve --event <event-id> — archive evidence first."
  investigation_steps:
    - "Identify when the persistence entry was created: ls -la --time-style=long-iso <path>"
    - "Correlate with audit history: policy-scout audit list --since <date>"
    - "Check for related processes still running: policy-scout sweep quick"
  removal_steps:
    - "For crontab entries: crontab -e — remove the suspicious entry."
    - "For shell profile entries: edit ~/.bashrc, ~/.zshrc, ~/.profile — remove the injected line."
    - "For systemd user units: systemctl --user disable <unit> && rm ~/.config/systemd/user/<unit>.service"
  recovery_signal:
    - "Run: policy-scout sweep quick — verify persistence mechanism no longer appears."

network_callback_detected:
  title: "Unexpected Outbound Network Connection"
  urgency: critical
  immediate_steps:
    - "Identify the destination: use netstat/ss output from the sweep."
    - "Kill the responsible process if identified: kill <pid>"
    - "Consider isolating the machine from the network if the destination is unknown."
  investigation_steps:
    - "Identify the parent process: ps -ef | grep <pid>"
    - "Check what package or command spawned the process."
    - "Review recently installed packages and their postinstall scripts."
  recovery_signal:
    - "Run: policy-scout sweep quick — verify no remaining suspicious processes or ports."

workflow_injection:
  title: "CI/CD Workflow Modification Detected"
  urgency: high
  immediate_steps:
    - "Do not push this change."
    - "Review the specific modifications: git diff HEAD -- .github/workflows/"
    - "Check if any secrets are referenced that should not be."
  investigation_steps:
    - "Review git blame for who last modified the workflow: git blame <workflow-file>"
    - "Check recent commits touching workflow files: git log --oneline -- .github/workflows/"
    - "Verify the changes are authorized."
  recovery_signal:
    - "Run: policy-scout sweep project — verify no remaining workflow injection patterns."
```

### Step 2 — Playbook Integration with Scout Reports (`response/playbooks.py`)

```python
def load_playbooks() -> dict[str, Playbook]:
    path = Path(__file__).parent.parent / "data" / "playbooks.yaml"
    return {k: Playbook.from_dict(k, v) for k, v in yaml.safe_load(path.read_text()).items()}

def get_playbook_for_finding(finding: Finding) -> Playbook | None:
    playbooks = load_playbooks()
    return playbooks.get(finding.category)

def enrich_report_with_playbooks(report: ScoutReport) -> ScoutReport:
    """Add response playbooks to any critical/high findings in a report."""
    for finding in report.findings:
        if finding.severity in ("critical", "high"):
            playbook = get_playbook_for_finding(finding)
            if playbook:
                finding.response_playbook = playbook
    return report
```

This is called in `reports/scout_report.py` before the report is serialized. No new data model fields needed except `Finding.response_playbook: Playbook | None`.

In the Markdown report:

```markdown
## Finding: Malicious Lifecycle Script Detected
**Severity:** CRITICAL  
**Evidence:** node_modules/suspicious-pkg/scripts/postinstall.js:14

### Immediate Response Steps
1. Do NOT migrate the sandbox install to your project.
2. If this package is already in your node_modules, run: `npm uninstall suspicious-pkg`
...

### Investigation Steps
...
```

### Step 3 — Evidence Preservation (`response/preserve.py`)

```python
def preserve_evidence(event_id: str | None, output_dir: Path | None = None) -> EvidenceArchive:
    """
    Collect all evidence associated with an event or the current system state
    and write it to a timestamped zip archive.
    """
    archive_dir = output_dir or Path("~/.local/share/policy-scout/evidence").expanduser()
    archive_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_path = archive_dir / f"evidence_{timestamp}.zip"

    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        # Always include:
        _add_audit_events(zf, event_id)          # related audit events
        _add_sweep_snapshot(zf)                   # current sweep state
        _add_process_list(zf)                     # current ps output
        _add_port_list(zf)                        # current ss/netstat output
        _add_shell_profiles(zf)                   # ~/.bashrc, ~/.zshrc, ~/.profile (no values, just structure)
        _add_package_manifests(zf)                # package.json, requirements.txt etc.

        # If event_id provided, include event-specific evidence:
        if event_id:
            event = audit_store.get_event(event_id)
            if event and event.data.get("sandbox_id"):
                _add_sandbox_artifacts(zf, event.data["sandbox_id"])
            if event and event.data.get("report_id"):
                _add_scout_report(zf, event.data["report_id"])

    audit_store.write(EvidencePreserved(archive_path=str(archive_path), event_id=event_id))
    return EvidenceArchive(path=archive_path, timestamp=timestamp)
```

**Key constraint:** Shell profiles are included but their values are redacted (same redaction engine used in audit). The archive contains structure and timestamps, not credential values.

### Step 4 — Kill Switch (`response/lockdown.py`)

```python
LOCKDOWN_CONFIG_PATH = Path("~/.local/share/policy-scout/lockdown.active").expanduser()

def activate_lockdown(reason: str = "manual") -> LockdownState:
    """
    Immediately set the policy engine to incident mode:
    - All non-read commands → DENY
    - All package installs → DENY
    - All network commands → DENY_AND_ALERT
    Write a timestamped lockdown event to the audit log.
    """
    state = LockdownState(
        active=True,
        activated_at=datetime.now(UTC).isoformat(),
        reason=reason,
    )
    LOCKDOWN_CONFIG_PATH.write_text(json.dumps(state.to_dict()))
    audit_store.write(LockdownActivated(reason=reason))

    # Print human-readable guidance
    print("LOCKDOWN ACTIVATED", file=sys.stderr)
    print("All non-read operations are now DENIED.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Next steps:", file=sys.stderr)
    print("  1. Run: policy-scout sweep project", file=sys.stderr)
    print("  2. Run: policy-scout sweep quick", file=sys.stderr)
    print("  3. Review findings and consult playbooks.", file=sys.stderr)
    print("  4. When satisfied: policy-scout lockdown deactivate", file=sys.stderr)

    return state

def is_lockdown_active() -> bool:
    if LOCKDOWN_CONFIG_PATH.exists():
        state = json.loads(LOCKDOWN_CONFIG_PATH.read_text())
        return state.get("active", False)
    return False

def deactivate_lockdown() -> None:
    LOCKDOWN_CONFIG_PATH.unlink(missing_ok=True)
    audit_store.write(LockdownDeactivated())
```

The policy engine checks `is_lockdown_active()` at the start of every decision. When active, the effective mode is forced to `incident`:

```python
# In policy/engine.py
def decide(self, request: CommandRequest) -> PolicyDecision:
    if lockdown.is_lockdown_active():
        if request.classification.categories & SAFE_READ_CATEGORIES:
            return PolicyDecision(decision=Decision.ALLOW_LOGGED, reasons=["lockdown:read-only-allowed"])
        return PolicyDecision(decision=Decision.DENY, reasons=["lockdown:active"])
    ...
```

### Step 5 — Clearance Workflow (`response/clearance.py`)

```python
def run_clearance_check(since: str) -> ClearanceReport:
    """
    Run all sweeps and checks, then produce a 'clean bill of health' report
    relative to a given timestamp. Used after an incident to verify remediation.
    """
    since_dt = datetime.fromisoformat(since)

    # Run full sweeps
    project_sweep = sweep_engine.run_project_sweep(Path.cwd())
    system_sweep = sweep_engine.run_quick_sweep()

    # Check audit events since the timestamp
    events_since = audit_store.get_events_since(since_dt)
    critical_events = [e for e in events_since if e.data.get("severity") == "critical"]

    # Summarize
    all_findings = project_sweep.findings + system_sweep.findings
    critical_findings = [f for f in all_findings if f.severity == "critical"]

    clearance_granted = len(critical_findings) == 0 and len(critical_events) == 0

    return ClearanceReport(
        since=since,
        clearance_granted=clearance_granted,
        project_findings=project_sweep.findings,
        system_findings=system_sweep.findings,
        critical_events_since=critical_events,
        summary=(
            f"No critical findings detected since {since}. Environment appears clean."
            if clearance_granted else
            f"{len(critical_findings)} critical finding(s) remain. Review before resuming operations."
        ),
    )
```

---

## CLI Commands

```bash
# Evidence preservation
policy-scout preserve                      # preserve current system state
policy-scout preserve --event evt_abc123   # preserve evidence for a specific event

# Kill switch
policy-scout lockdown                      # activate lockdown (all writes → DENY)
policy-scout lockdown deactivate           # deactivate when remediation is complete
policy-scout lockdown status               # is lockdown active?

# Post-incident clearance
policy-scout clearance --since 2026-06-10T14:30:00  # run post-incident clean check
```

---

## New Audit Event Types

```
EvidencePreserved       — archive created
LockdownActivated       — lockdown mode engaged
LockdownDeactivated     — lockdown mode cleared
ClearanceCheckRun       — clearance workflow completed
```

---

## Integration Points

- `reports/scout_report.py` — call `enrich_report_with_playbooks()` before serializing
- `policy/engine.py` — check `is_lockdown_active()` at top of `decide()`
- `core/models.py` — add `response_playbook` field to `Finding`
- `cli/main.py` — register `preserve`, `lockdown`, `clearance` command groups
- `audit/events.py` — four new event types

---

## Test Strategy

- Unit test playbook lookup by finding category (all defined categories have a playbook)
- Unit test `activate_lockdown()` creates the sentinel file and writes the audit event
- Unit test policy engine with lockdown active: safe-read command → ALLOW_LOGGED, everything else → DENY
- Unit test `preserve_evidence()` creates a zip with expected files
- Unit test `run_clearance_check()` with mocked sweep engine (clean and with findings)
- Integration test: activate lockdown, run `policy-scout check -- npm install lodash`, verify DENY with lockdown reason

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `playbooks.yaml` (data) | ~200 entries | Research/writing |
| `playbooks.py` + integration with reports | ~120 | Low |
| `preserve.py` | ~200 | Medium |
| `lockdown.py` | ~100 | Low |
| `clearance.py` | ~150 | Low-Medium |
| Policy engine lockdown check | ~30 delta | Low |
| CLI commands | ~120 | Low |
| Tests | ~300 | Medium |
| **Total** | **~1220** | |

---

## Open Questions

1. Should lockdown be automatically activated when a critical finding is produced, or always require explicit activation? Recommendation: never automatic — auto-lockdown on a false positive would be very disruptive. The user activates lockdown deliberately; findings suggest they should.
2. Should the evidence archive include file contents from the project? Recommendation: only manifests and config files (never source code, node_modules, or binary artifacts) — the archive is for incident analysis, not backup. Keep it small enough to be useful.
3. Should clearance require human acknowledgment of each finding, or just a clean sweep? Recommendation: clean sweep is sufficient for clearance — the playbooks already guided remediation. Add a `--require-acknowledgment` flag for stricter workflows.
