# Policy Scout — Visual Production Plan

## 1. Purpose

This document defines the first visual-aid set for Policy Scout.

The diagrams should help humans and agents understand the system without blurring boundaries.

The core visual doctrine:

```text
Actors request.
Policy Scout decides.
Executors obey.
Audit records everything.
```

The first visuals should be clean, practical, and source-of-truth aligned.

---

## 2. Visual Design Doctrine

Policy Scout visuals should be:

- readable
- calm
- implementation-aligned
- boundary-focused
- consistent across docs
- useful for humans and agents
- simple enough to maintain

Avoid visuals that make Policy Scout look like an autonomous agent.

Policy Scout is a harness, not an agent brain.

---

## 3. Suggested Visual Language

Suggested semantic colors:

```text
blue/cyan    -> normal request flow
amber/gold   -> policy, approval, governance
green        -> allowed path
orange       -> sandbox/review path
red          -> deny/alert path
purple       -> audit/report/memory bridge
gray         -> registries/config/reference data
```

Suggested shape semantics:

```text
rounded rectangle -> process/component
diamond           -> decision
cylinder/database -> storage
document          -> report/artifact
subgraph          -> bounded system/module
```

---

## 4. First Visual Batch

The first batch should include these diagrams:

```text
1. System Architecture Map
2. Core Safety Boundary Diagram
3. Granular Evaluation Pipeline
4. Policy Decision Tree
5. Sandbox Install Flow
6. Sweep Engine Flow
7. Audit and Reporting Flow
8. Approval Queue Flow
9. Risk and Clutch Flow
10. Integration Boundary Diagram
```

These cover the core conceptual and implementation boundaries.

---

## 5. Visual 1 — System Architecture Map

### Purpose

Show the whole Policy Scout runtime spine.

### Source Docs

```text
ARCHITECTURE.md
PROJECT_SCOPE.md
DATA_MODELS.md
```

### Key Message

Policy Scout is a structured decision boundary.

### Nodes

```text
Actor
Request Normalizer
Command Parser
Command Classifier
Capability Detector
Context Inspector
Registry Matcher
Risk Scorer
Policy Engine
Decision
Executor
Approval Queue
Sandbox
Denial
Audit Store
Scout Reports
Registries
```

---

## 6. Visual 2 — Core Safety Boundary

### Purpose

Show the most important design law.

### Source Docs

```text
PROJECT_SCOPE.md
ARCHITECTURE.md
INTEGRATION_BOUNDARIES.md
AGENT_HANDOFF.md
```

### Key Message

Bad: agent decides and maybe logs.  
Good: actor requests, Policy Scout decides, executor obeys.

---

## 7. Visual 3 — Granular Evaluation Pipeline

### Purpose

Show why lump-sum scoring is not enough.

### Source Docs

```text
EVALUATION_GRANULARITY.md
DATA_MODELS.md
RISK_SCORING_AND_CLUTCH.md
```

### Key Message

Final risk score is a summary, not the source of truth.

---

## 8. Visual 4 — Policy Decision Tree

### Purpose

Show default decision logic.

### Source Docs

```text
POLICY_DESIGN.md
TAXONOMIES.md
REGISTRY_DESIGN.md
```

### Key Message

Hard-deny and high-risk branches are evaluated before allow paths.

---

## 9. Visual 5 — Sandbox Install Flow

### Purpose

Show that package installs are analyzed away from the host project.

### Source Docs

```text
SANDBOX_DESIGN.md
MVP_SPEC.md
THREAT_MODEL.md
```

### Key Message

Sandbox is a review mirror, not automatic trust.

---

## 10. Visual 6 — Sweep Engine Flow

### Purpose

Show project, quick, and sandbox sweeps.

### Source Docs

```text
SWEEP_ENGINE_DESIGN.md
AUDIT_AND_REPORTING.md
THREAT_MODEL.md
```

### Key Message

Sweeps gather evidence and produce findings, not magical certainty.

---

## 11. Visual 7 — Audit and Reporting Flow

### Purpose

Show the evidence chain.

### Source Docs

```text
AUDIT_AND_REPORTING.md
DATA_MODELS.md
LOCAL_FIRST_AND_PRIVACY.md
```

### Key Message

Audit and reporting are part of the protection layer.

---

## 12. Visual 8 — Approval Queue Flow

### Purpose

Show scoped human approval.

### Source Docs

```text
APPROVAL_QUEUE_DESIGN.md
POLICY_DESIGN.md
CLI_SPEC.md
```

### Key Message

Approval is a safety valve, not a loophole.

---

## 13. Visual 9 — Risk and Clutch Flow

### Purpose

Show how granular scoring feeds adaptive friction.

### Source Docs

```text
RISK_SCORING_AND_CLUTCH.md
EVALUATION_GRANULARITY.md
TESTING_STRATEGY.md
```

### Key Message

The clutch works only if granular signals remain visible.

---

## 14. Visual 10 — Integration Boundary Diagram

### Purpose

Show how future adapters route through the same core.

### Source Docs

```text
INTEGRATION_BOUNDARIES.md
LOCAL_FIRST_AND_PRIVACY.md
ARCHITECTURE.md
```

### Key Message

Integrations may submit requests. They do not bypass policy.

---

## 15. Recommended Rendering Formats

Use Markdown + Mermaid first.

Benefits:

- readable by agents
- version-control friendly
- renderable in GitHub/Obsidian
- easy to maintain
- editable by humans

Later, the Mermaid diagrams can be converted to:

- SVG
- PNG
- PDF
- presentation slides
- LumaWeave graph views

---

## 16. Visual Production Doctrine

Diagrams should not become decorative drift.

Every diagram should answer:

```text
What boundary does this clarify?
What implementation behavior does this preserve?
What mistake does this prevent?
```

If a diagram does not answer those questions, it probably is not needed yet.
