# Policy Scout — Scout Report Anatomy

## 1. Purpose

This document defines the visual and structural anatomy of a Scout Report.

Scout Reports explain important Policy Scout decisions, sandbox results, sweep findings, or possible incidents.

A report should answer:

```text
What happened?
Why did Policy Scout care?
What evidence exists?
How confident is Policy Scout?
What should the user do next?
What could not be verified?
```

---

## 2. Scout Report Doctrine

A Scout Report should be:

- calm
- precise
- evidence-based
- redaction-safe
- useful for beginners
- useful for advanced developers
- machine-readable where possible
- linked to audit events

Reports should not overclaim.

---

## 3. Recommended Report Sections

```text
1. Summary
2. Decision / Risk Level
3. Triggering Command or Sweep
4. Timeline
5. Findings
6. Evidence
7. Credential Exposure Assessment
8. Recommended Actions
9. Files Changed
10. Open Ports / Processes
11. What Policy Scout Could Not Verify
12. Audit Event IDs
```

Not every report needs every section.

---

## 4. Visual Layout

Suggested report card layout:

```text
┌────────────────────────────────────┐
│ Scout Report: <Title>              │
├────────────────────────────────────┤
│ Summary                            │
│ Decision / Risk                    │
│ Trigger                            │
├────────────────────────────────────┤
│ Findings                           │
│ - severity                         │
│ - confidence                       │
│ - category                         │
├────────────────────────────────────┤
│ Evidence                           │
│ Recommended Actions                │
│ Could Not Verify                   │
├────────────────────────────────────┤
│ Audit IDs                          │
└────────────────────────────────────┘
```

---

## 5. Summary Section

The summary should be short.

Example:

```text
Policy Scout routed an agent-requested package install to sandbox review. The sandbox completed, but one high-severity lifecycle script finding requires manual review before migration.
```

---

## 6. Decision / Risk Section

Should include:

```text
Decision: SANDBOX_FIRST
Risk: 7/10
Risk Band: high
Confidence: 0.91
Evidence Strength: 0.86
```

Also include risk components when relevant.

Example:

```text
Risk Components:
- package_install: 2
- lifecycle_script_possible: 2
- network_fetch: 1
- actor_trust_penalty: 1
- project_write: 1
```

---

## 7. Trigger Section

For command reports:

```text
Command:
  npm install lodash

Actor:
  agent

Working Directory:
  <project-relative path where possible>
```

For sweeps:

```text
Sweep:
  project

Scope:
  package scripts, workflows, executable files, credential references
```

---

## 8. Findings Section

Each finding should include:

```text
Severity
Confidence
Category
Title
Location
Why it matters
Recommended action
```

Example:

```text
Finding: Package postinstall script invokes child_process
Severity: high
Confidence: moderate
Category: suspicious_lifecycle_script
Location: node_modules/example/package.json

Why it matters:
Lifecycle scripts can execute arbitrary commands during package installation.

Recommended action:
Review the script before approving host migration.
```

---

## 9. Evidence Section

Evidence should reference locations.

Good:

```text
Evidence:
- package.json contains a postinstall script
- scripts/install.js imports child_process
- package-lock.json changed
```

Avoid raw secrets.

Bad:

```text
OPENAI_API_KEY=sk-actual-value
```

---

## 10. Credential Exposure Assessment

Possible values:

```text
none_detected
unlikely
possible
likely
confirmed
unknown
```

Example:

```text
Credential Exposure Assessment:
possible

Reason:
The lifecycle script references environment variables. Policy Scout did not verify exfiltration.
```

---

## 11. Recommended Actions

Actions should be practical and ordered.

Example:

```text
1. Do not migrate sandbox changes yet.
2. Review the lifecycle script.
3. Run a project sweep.
4. If the script executed with access to secrets, consider rotating exposed tokens.
5. Keep the Scout Report for audit context.
```

---

## 12. What Could Not Be Verified

Reports should explicitly state limitations.

Examples:

```text
Policy Scout could not verify whether the remote URL changed after fetch.
Policy Scout did not inspect network packets.
Policy Scout did not perform full malware analysis.
Policy Scout could not inspect unsupported package manager behavior.
```

This builds trust.

---

## 13. Audit Event IDs

Reports should include relevant IDs:

```text
request_id: req_123
evaluation_id: eval_123
decision_id: dec_123
sandbox_id: sbx_123
audit_events:
  - evt_100
  - evt_101
  - evt_102
```

---

## 14. Markdown Report Template

```md
# Scout Report: <Title>

## 1. Summary

<summary>

## 2. Decision / Risk

- Decision: `<decision>`
- Risk: `<risk_score>/10`
- Risk Band: `<risk_band>`
- Confidence: `<confidence>`
- Evidence Strength: `<evidence_strength>`

## 3. Trigger

```text
<command or sweep trigger>
```

## 4. Findings

### Finding: <title>

- Severity: `<severity>`
- Confidence: `<confidence>`
- Category: `<category>`
- Location: `<location>`

Why it matters:

<why_it_matters>

Recommended action:

<recommended_action>

## 5. Evidence

- <evidence item>
- <evidence item>

## 6. Credential Exposure Assessment

- Assessment: `<level>`
- Notes: <notes>

## 7. Recommended Actions

1. <action>
2. <action>

## 8. What Policy Scout Could Not Verify

- <limitation>
- <limitation>

## 9. Audit IDs

- request_id: `<request_id>`
- evaluation_id: `<evaluation_id>`
- decision_id: `<decision_id>`
- report_id: `<report_id>`
```

---

## 15. Report Doctrine

A good Scout Report should make the user feel informed, not scared.

It should preserve evidence, uncertainty, and next steps.

It should be light armor in written form.
