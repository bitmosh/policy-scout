# Policy Scout — Audit and Reporting

## 1. Purpose

Policy Scout must make risky actions visible, explainable, and reviewable.

The audit layer records what happened.

The report layer explains what happened.

Both layers are core to trust.

---

## 2. Audit Doctrine

Every important action should produce an audit event.

Audit events should be:

- local-first
- append-first
- timestamped
- linked by IDs
- structured
- queryable
- redacted
- durable according to retention policy

Policy Scout should not rely on terminal output as the only record.

---

## 3. Audit Event Types

Initial event types:

```text
CommandRequested
CommandParsed
CommandClassified
CapabilitiesDetected
ContextInspected
RegistryMatched
PolicyMatched
DecisionIssued
ApprovalRequested
ApprovalResolved
CommandExecutionStarted
CommandExecutionCompleted
SandboxStarted
SandboxCompleted
SweepStarted
SweepFindingCreated
ScoutReportGenerated
PolicyError
AuditError
SandboxError
SweepError
```

---

## 4. Core Audit Event Shape

Example:

```json
{
  "event_id": "evt_123",
  "event_type": "DecisionIssued",
  "timestamp": 1710000000,
  "request_id": "req_123",
  "actor": {
    "type": "agent",
    "name": "local_agent"
  },
  "summary": "Policy decision issued for package install.",
  "data": {
    "decision": "SANDBOX_FIRST",
    "risk_score": 7,
    "policy_hits": [
      "package_installs_sandbox_first"
    ]
  }
}
```

Event `data` should avoid raw secret values.

---

## 5. ID Relationships

Important IDs:

```text
request_id
evaluation_id
decision_id
approval_id
execution_id
sandbox_id
sweep_id
finding_id
report_id
event_id
```

Reports should reference relevant IDs.

Example:

```text
Scout Report report_123
  request_id: req_123
  decision_id: dec_123
  sandbox_id: sbx_123
  audit_events:
    - evt_100
    - evt_101
    - evt_102
```

---

## 6. Audit Storage

Initial options:

```text
SQLite
JSONL
```

Recommended:

```text
SQLite as primary
JSONL as optional export/debug stream
```

SQLite benefits:

- queryable
- structured
- local
- durable
- useful for future UI

JSONL benefits:

- easy to inspect
- easy to export
- easy to append

---

## 7. Audit Retention

Audit records should not be silently discarded.

Initial retention policy:

- keep all audit events locally by default
- allow user-configurable retention later
- allow export
- allow manual purge later
- never print secrets into logs

For v0.1, avoid complicated retention automation.

---

## 8. Redaction Rules

Policy Scout must avoid logging secret values.

Redact:

- API keys
- tokens
- private keys
- `.env` values
- npm tokens
- GitHub tokens
- cloud credentials
- SSH private key contents

Prefer evidence references:

```text
credential-adjacent file referenced: .env
```

Avoid:

```text
SECRET_KEY=actual_secret_value
```

---

## 9. Scout Reports

Scout Reports are human-readable explanations of important actions or findings.

Report formats:

```text
Markdown
JSON
```

Initial report types:

```text
command_decision
package_install_review
sandbox_result
project_sweep
system_quick_sweep
possible_credential_exposure
blocked_command
incident_summary
```

---

## 10. Scout Report Structure

Recommended Markdown structure:

```text
# Scout Report: <Title>

## 1. Summary

## 2. Decision / Risk Level

## 3. Triggering Command or Sweep

## 4. Timeline

## 5. Findings

## 6. Evidence

## 7. Credential Exposure Assessment

## 8. Recommended Actions

## 9. Files Changed

## 10. Open Ports / Processes

## 11. What Policy Scout Could Not Verify

## 12. Audit Event IDs
```

Not every report needs every section.

---

## 11. Finding Shape

Example:

```json
{
  "finding_id": "find_123",
  "severity": "high",
  "confidence": "moderate",
  "category": "suspicious_lifecycle_script",
  "title": "Package postinstall script invokes child_process",
  "location": "node_modules/example/package.json",
  "evidence_ref": "evidence_123",
  "why_it_matters": "Lifecycle scripts can execute arbitrary commands during install.",
  "recommended_action": "Review script before approving host install."
}
```

Findings should always include:

- severity
- confidence
- category
- title
- location or evidence reference
- why it matters
- recommended action

---

## 12. Severity vs Confidence

Severity and confidence are different.

Example:

```text
Severity: high
Confidence: moderate
```

This means the issue could be serious if true, but Policy Scout is not fully certain.

Do not flatten this into a single score only.

---

## 13. Credential Exposure Assessment

Reports should include credential guidance when relevant.

Possible levels:

```text
none_detected
unlikely
possible
likely
confirmed
unknown
```

Use conservative wording.

Example:

```text
Credential exposure is possible because a lifecycle script attempted to read environment variables during install. Policy Scout did not verify exfiltration.
```

Avoid unsupported claims.

---

## 14. Recommended Actions

Recommended actions should be practical.

Examples:

```text
Review the lifecycle script before approving migration.
Do not run this command on the host.
Run a project sweep.
Check whether .env or .npmrc was accessible.
Rotate tokens if the script executed and secrets may have been exposed.
Review recent package/lockfile changes.
```

Policy Scout should distinguish between:

- immediate action
- optional follow-up
- manual review
- external tools
- what Policy Scout cannot verify

---

## 15. Report Tone

Reports should be calm and precise.

Good:

```text
Policy Scout found a suspicious lifecycle script. Review is recommended before host installation.
```

Bad:

```text
Your machine is infected.
```

unless supported by confirmed evidence.

---

## 16. Audit Failure Behavior

If audit logging fails:

- low-risk `check` may continue with warning
- risky `run` should not execute
- denied commands remain denied
- sandbox migration should not proceed
- report generation should warn that audit persistence failed

Policy Scout should not silently run risky commands without auditability.

---

## 17. Report Generation Triggers

Generate or offer Scout Reports when:

- command is denied
- command is denied and alerting
- sandbox finds suspicious behavior
- project sweep finds medium/high findings
- possible credential exposure exists
- user requests a report
- CI mode needs machine-readable output

---

## 18. Agent-Readable Reports

Reports should be usable by future agents.

JSON reports should include:

- IDs
- machine-readable findings
- policy hits
- risk components
- evidence references
- recommended actions
- uncertainty fields

Agents may summarize reports, but must not hide findings.

---

## 19. LumaWeave and Cerebra Compatibility

Future integrations may use audit/report data.

Cerebra may store and reason over Scout Reports.

LumaWeave may visualize:

- command request graph
- decision graph
- finding graph
- package install sandbox graph
- incident timeline

For v0.1, Policy Scout should simply keep data structured enough to make this possible later.

---

## 20. Audit and Reporting Doctrine

If Policy Scout cannot explain a decision, the decision is not good enough.

If Policy Scout cannot show what it checked, the user cannot trust the result.

If Policy Scout cannot preserve evidence without leaking secrets, the reporting system is unsafe.

Audit and reporting are not extras. They are part of the protection layer.
