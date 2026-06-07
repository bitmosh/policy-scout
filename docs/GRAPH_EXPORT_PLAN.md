# Policy Scout — Graph Export Plan

## 1. Purpose

This document defines how Policy Scout data can eventually be exported as graph-ready structures for LumaWeave and memory-ready structures for Cerebra.

Policy Scout v0.1 does not need graph export.

But its data models should be structured so graph export is easy later.

---

## 2. Core Boundary

Policy Scout owns:

- command safety decisions
- audit events
- findings
- sandbox results
- Scout Reports

Cerebra owns:

- memory
- long-term context
- retrieval
- consolidation
- reasoning over historical records

LumaWeave owns:

- graph visualization
- exploration
- layout
- visual navigation

Policy Scout should not become the graph viewer.

---

## 3. Graph Export Goals

Future graph exports should help users see:

- which actors requested which commands
- which policies fired
- which decisions were issued
- which commands produced findings
- which sandbox runs created reports
- which packages or files were involved
- how incidents unfolded over time

---

## 4. Core Node Types

Suggested graph node types:

```text
Actor
CommandRequest
ParseResult
ClassificationResult
Capability
RegistryEntry
Policy
RiskScore
PolicyDecision
ApprovalRequest
ExecutionResult
SandboxResult
SweepResult
Finding
AuditEvent
ScoutReport
File
Package
Process
Port
Project
```

---

## 5. Core Edge Types

Suggested graph edge types:

```text
REQUESTED
PARSED_AS
CLASSIFIED_AS
HAS_CAPABILITY
MATCHED_REGISTRY
MATCHED_POLICY
SCORED_AS
ISSUED_DECISION
REQUIRED_APPROVAL
APPROVED
DENIED
EXECUTED_AS
SANDBOXED_AS
GENERATED_FINDING
GENERATED_REPORT
WROTE_EVENT
REFERENCES_FILE
REFERENCES_PACKAGE
REFERENCES_PROCESS
REFERENCES_PORT
BELONGS_TO_PROJECT
OCCURRED_AFTER
```

---

## 6. Example Graph

For:

```bash
npm install lodash
```

Graph shape:

```text
Actor
  REQUESTED -> CommandRequest
CommandRequest
  CLASSIFIED_AS -> package_install
CommandRequest
  HAS_CAPABILITY -> network.fetch
CommandRequest
  HAS_CAPABILITY -> lifecycle.execute_possible
CommandRequest
  MATCHED_POLICY -> package_installs_sandbox_first
RiskScore
  SCORED_AS -> high
PolicyDecision
  ISSUED_DECISION -> SANDBOX_FIRST
SandboxResult
  GENERATED_REPORT -> ScoutReport
AuditEvent
  WROTE_EVENT -> DecisionIssued
```

---

## 7. Export Format v1

Future export format can be JSON.

Example:

```json
{
  "schema_version": 1,
  "nodes": [
    {
      "id": "req_123",
      "type": "CommandRequest",
      "label": "npm install lodash",
      "properties": {
        "command": "npm install lodash",
        "actor_type": "agent"
      }
    }
  ],
  "edges": [
    {
      "id": "edge_123",
      "type": "MATCHED_POLICY",
      "source": "req_123",
      "target": "policy_package_installs_sandbox_first",
      "properties": {
        "confidence": 0.95
      }
    }
  ]
}
```

---

## 8. Graph Export Sources

Graph export can be built from:

```text
audit events
evaluation packets
policy decisions
sandbox results
sweep results
Scout Reports
```

Do not require a separate graph write path in v0.1.

The graph can be derived from durable records.

---

## 9. Time and Incident Views

Useful graph views:

```text
command timeline
incident timeline
actor activity graph
package risk graph
policy hit graph
finding graph
sandbox review graph
credential-adjacent access graph
```

---

## 10. LumaWeave Visual Concepts

Possible LumaWeave views:

### 10.1 Decision Trail

Shows:

```text
Actor -> CommandRequest -> Evaluation -> Decision -> Audit -> Report
```

### 10.2 Package Install Review

Shows:

```text
Package install -> sandbox -> lifecycle scripts -> findings -> migration decision
```

### 10.3 Incident Map

Shows:

```text
Findings
  -> affected files
  -> suspicious package
  -> commands
  -> reports
  -> recommended actions
```

### 10.4 Policy Heatmap

Shows:

```text
which policies fire most often
which commands trigger review
which actors request risky actions
```

---

## 11. Cerebra Memory Concepts

Cerebra may ingest:

```text
Scout Reports
incident summaries
audit event summaries
policy decision history
project risk history
package install review summaries
```

Cerebra should treat Policy Scout data as structured evidence, not vague memory.

Potential Cerebra memory object:

```json
{
  "memory_type": "policy_scout_report",
  "source": "Policy Scout",
  "report_id": "report_123",
  "project": "example-project",
  "summary": "Agent-requested package install was sandboxed and one suspicious lifecycle script was found.",
  "severity": "high",
  "confidence": "moderate",
  "created_at": 1710000000
}
```

---

## 12. Privacy for Graph Export

Graph export must preserve privacy.

Rules:

1. Do not export raw secrets.
2. Redact token-like values.
3. Prefer project-relative paths.
4. Allow local-only graph export.
5. Mark sensitive nodes.
6. Support sanitized export later.

---

## 13. Schema Versioning

Graph exports should include:

```text
schema_version
exported_at
policy_scout_version
source_event_range
```

This makes future migration easier.

---

## 14. Not Required for v0.1

Do not build graph export before:

```text
CLI check works
policy engine works
audit store works
sandbox works
sweep works
reports work
```

Graph export is a later integration layer.

---

## 15. Graph Export Doctrine

Policy Scout should produce structured records first.

Graphs should be derived from those records.

This keeps the security boundary simple and lets LumaWeave visualize without owning policy logic.
