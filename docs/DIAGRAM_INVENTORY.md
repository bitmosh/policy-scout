# Policy Scout — Diagram Inventory

## 1. Purpose

This document lists the charts, diagrams, and graph visuals that should be created for Policy Scout.

The goal is to make the system easy for humans and agents to understand.

Policy Scout has several important flows:

- command request flow
- policy decision flow
- granular evaluation flow
- sandbox install flow
- sweep flow
- approval flow
- audit/report flow
- future integration flow
- Cerebra/LumaWeave data bridge

Each visual should reflect the architecture docs and avoid inventing new behavior.

---

## 2. Diagram Doctrine

Policy Scout diagrams should be:

- clear
- accurate
- implementation-aligned
- useful for agents
- useful for humans
- not over-stylized at the expense of meaning

Use consistent names from the docs.

Do not diagram agent-centered control as the authority.

Always preserve:

```text
Actors request.
Policy Scout decides.
Executors obey.
Audit records everything.
```

---

## 3. Visual Style Suggestions

Suggested visual language:

```text
Actor/request nodes      -> left side
Policy Scout core        -> center
Execution/sandbox/report -> right side
Audit/event store        -> lower persistent layer
Registries              -> upper reference layer
```

Consistent colors can be chosen later, but conceptually:

```text
blue/cyan    -> requests and normal flow
gold/amber   -> policy decisions and approvals
green        -> allowed/safe path
orange       -> sandbox/review path
red          -> deny/alert path
purple       -> audit/report/memory bridge
gray         -> registries/config
```

---

## 4. Required Diagrams

### 4.1 High-Level Architecture Map

Shows the full system:

```text
Actor
  -> Request Normalizer
  -> Parser
  -> Classifier
  -> Capability Detector
  -> Context Inspector
  -> Registry Matcher
  -> Risk Scorer
  -> Policy Engine
  -> Decision
  -> Executor / Approval / Sandbox / Denial
  -> Audit / Scout Report
```

Purpose:

- explain the whole project in one image
- anchor new contributors
- show policy-centered structure

---

### 4.2 Core Safety Boundary Diagram

Shows the doctrine:

```text
Bad:
  Agent -> shell -> maybe log

Good:
  Actor -> Policy Scout -> allowed path
                     -> approval path
                     -> sandbox path
                     -> denial path
```

Purpose:

- prevent agent-centered implementations
- clarify authority boundary

---

### 4.3 Granular Evaluation Packet Diagram

Shows the evaluation packet layers:

```text
Parse
Classification
Capabilities
Actor
Context
Registry Hits
Risk Components
Policy Hits
Decision
Execution
Findings
```

Purpose:

- reinforce that final score is not the source of truth
- help implement tests and audit records

---

### 4.4 Command Classifier Pipeline

Shows:

```text
raw command
  -> tokenize
  -> detect shell structure
  -> command family
  -> subcommand
  -> registry match
  -> category
  -> capabilities
  -> confidence
```

Purpose:

- guide classifier implementation
- show fail-safe uncertainty behavior

---

### 4.5 Policy Decision Tree

Shows decision branches:

```text
known hard deny?
  yes -> DENY/DENY_AND_ALERT

package install?
  yes -> SANDBOX_FIRST

credential-adjacent?
  yes -> DENY_AND_ALERT

unknown low confidence?
  yes -> REQUIRE_APPROVAL

safe read?
  yes -> ALLOW

default
  -> REQUIRE_APPROVAL
```

Purpose:

- clarify default policy logic
- make tests easier to derive

---

### 4.6 Sandbox Install Flow

Shows:

```text
package install request
  -> sandbox required
  -> create temp workspace
  -> copy manifest/lockfile
  -> run install
  -> inspect lifecycle scripts
  -> capture diffs
  -> sandbox sweep
  -> Scout Report
  -> migration approval
```

Purpose:

- make sandbox boundaries obvious
- show host project is not mutated automatically

---

### 4.7 Sweep Engine Flow

Shows:

```text
project sweep
  -> package scripts
  -> workflows
  -> suspicious patterns
  -> executables
  -> credential references
  -> findings
  -> report

quick sweep
  -> ports
  -> processes
  -> config changes
  -> findings
  -> report
```

Purpose:

- separate project and system checks
- prevent overclaiming

---

### 4.8 Approval Queue Flow

Shows:

```text
REQUIRE_APPROVAL
  -> approval request
  -> human review
  -> approve once / deny once / expire
  -> executor re-validates
  -> execution/audit
```

Purpose:

- show approval is scoped and auditable
- show agents cannot self-approve

---

### 4.9 Audit and Reporting Flow

Shows:

```text
request events
classification events
decision events
approval events
execution events
sandbox events
sweep findings
Scout Reports
```

Purpose:

- explain durable evidence chain
- show reports are built from audit/evaluation data

---

### 4.10 Risk and Clutch Flow

Shows:

```text
granular signals
  -> risk components
  -> confidence/evidence strength
  -> clutch/mode router
  -> friction adjustment
  -> final decision context
```

Purpose:

- show why granular scoring matters
- prevent lump-sum scoring

---

### 4.11 Local-First Data Map

Shows local storage locations:

```text
config
registries
audit.db
reports
sandboxes
cache
logs
```

Purpose:

- show what stays local
- support privacy explanation

---

### 4.12 Future Integration Boundary

Shows:

```text
CLI
shell shim
local API
MCP server
editor extension
CI

all route through:
  Policy Scout core
```

Purpose:

- show adapters cannot bypass policy
- guide future integrations

---

### 4.13 Cerebra / LumaWeave Bridge

Shows:

```text
Policy Scout
  -> audit events
  -> Scout Reports
  -> finding graph
  -> Cerebra memory
  -> LumaWeave visualization
```

Purpose:

- clarify future connection
- keep responsibilities separate

---

## 5. Optional Diagrams

### 5.1 RPG Armor Metaphor Diagram

Shows:

```text
Actor = fast agent
Policy Scout = light armor
Policy Engine = armor weave
Sandbox = mirror plane
Scout Report = field report
Audit = memory trail
```

Purpose:

- branding/concept explanation
- not required for engineering docs

---

### 5.2 Decision Severity Ladder

Shows:

```text
ALLOW
ALLOW_LOGGED
REQUIRE_APPROVAL
SANDBOX_FIRST
DENY
DENY_AND_ALERT
```

Purpose:

- explain increasing friction

---

### 5.3 Risk Component Radar

Shows component categories:

```text
network
package
lifecycle
credential
destructive
system mutation
actor trust
confidence
```

Purpose:

- help visualize why a decision was made

---

### 5.4 Scout Report Anatomy

Shows sections of a report:

```text
summary
decision
findings
evidence
credential exposure
recommended actions
audit IDs
```

Purpose:

- guide report implementation

---

## 6. Recommended Creation Order

Create diagrams in this order:

```text
1. High-Level Architecture Map
2. Core Safety Boundary Diagram
3. Granular Evaluation Packet Diagram
4. Policy Decision Tree
5. Sandbox Install Flow
6. Sweep Engine Flow
7. Audit and Reporting Flow
8. Approval Queue Flow
9. Risk and Clutch Flow
10. Local-First Data Map
11. Integration Boundary Diagram
12. Cerebra/LumaWeave Bridge
```

---

## 7. Diagram Source of Truth

Diagrams should be derived from:

```text
ARCHITECTURE.md
POLICY_DESIGN.md
EVALUATION_GRANULARITY.md
SANDBOX_DESIGN.md
SWEEP_ENGINE_DESIGN.md
AUDIT_AND_REPORTING.md
INTEGRATION_BOUNDARIES.md
DATA_MODELS.md
```

If a diagram disagrees with a doc, update one or the other.

Do not let diagrams drift.

---

## 8. Diagram Doctrine

Policy Scout diagrams should make hidden safety boundaries visible.

The most important thing to show is not that Policy Scout has many components.

The most important thing to show is that every risky action passes through a structured, auditable decision boundary.
