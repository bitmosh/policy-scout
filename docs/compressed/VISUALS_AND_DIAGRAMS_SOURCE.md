# Policy Scout — Visuals and Diagrams Source

## 1. Purpose

This document consolidates visual and diagram guidance for Policy Scout. It defines the visual doctrine, diagram inventory, rendering workflow, style guide, and maintenance rules.

The core visual doctrine:

```text
Actors request.
Policy Scout decides.
Executors obey.
Audit records everything.
```

Diagrams should clarify the safety boundary, not depict Policy Scout as an autonomous agent brain. Policy Scout is a harness, not an agent.

---

## 2. Visual Doctrine

### 2.1 Core Principles

Policy Scout visuals should be:
- **Calm** — Not fear-based red dashboards or aggressive hacker aesthetics
- **Local-first** — Emphasize on-machine state, not cloud dashboards
- **Lightweight** — Precise, protective, developer-friendly
- **Boundary-focused** — Show the decision gate, not component clutter
- **Implementation-aligned** — Derived from source docs, not invented behavior

### 2.2 Visual Metaphor

The visual metaphor is "light armor for fast agents":
- Scout = fast, observant, ahead of danger
- Light armor = thin protective layer, woven mesh, transparent boundary
- Harness = straps, rails, gates, bounded channels, safe routing
- Scout Report = calm field intelligence, evidence trail

### 2.3 Key Doctrine

The most important concept is not that Policy Scout has many modules. The most important concept is that every risky action passes through a structured, auditable decision boundary.

Bad: Agent → shell → maybe log  
Good: Actor → Policy Scout → allowed/approval/sandbox/deny → audit

---

## 3. Current Diagram Sources

### 3.1 Mermaid Source Files

Primary source: `docs/MERMAID_DIAGRAMS.md` (combined file)

Individual split files in `docs/diagrams/`:
- `01-system-architecture-map.mmd` — Full Policy Scout runtime spine
- `02-core-safety-boundary.mmd` — Bad vs good execution boundary
- `03-granular-evaluation-pipeline.mmd` — Evaluation packet layers
- `04-policy-decision-tree.mmd` — Default decision branches
- `05-sandbox-install-flow.mmd` — Package install sandbox flow
- `06-sweep-engine-flow.mmd` — Project/quick sweep flows
- `07-audit-reporting-flow.mmd` — Event and report chain
- `08-approval-queue-flow.mmd` — Scoped human approval
- `09-risk-clutch-flow.mmd` — Granular signals feeding clutch
- `10-integration-boundary.mmd` — Adapter boundaries
- `11-local-first-data-map.mmd` — Local data/storage map
- `12-cerebra-lumaweave-bridge.mmd` — Future ecosystem bridge (DEFERRED)

### 3.2 Source Docs for Diagrams

Diagrams should be derived from:
- Core doctrine docs (compressed/)
- Implementation docs (docs/implementations/)
- Current code behavior (policy_scout/**/*.py)

If a diagram disagrees with a source doc, fix the conflict. Do not let diagrams drift.

---

## 4. Diagram Inventory

### 4.1 Required Diagrams (v0.1)

These cover core conceptual and implementation boundaries:

1. **System Architecture Map** — Full runtime spine from actor to audit
2. **Core Safety Boundary** — Bad vs good execution boundary
3. **Granular Evaluation Pipeline** — Evaluation packet layers
4. **Policy Decision Tree** — Default decision branches
5. **Sandbox Install Flow** — Package install sandbox flow
6. **Sweep Engine Flow** — Project/quick sweep flows
7. **Audit and Reporting Flow** — Event and report chain
8. **Approval Queue Flow** — Scoped human approval
9. **Risk and Clutch Flow** — Granular signals feeding clutch
10. **Integration Boundary** — Adapter boundaries (CLI, shell, API, MCP, editor, CI)
11. **Local-First Data Map** — Local data/storage map

### 4.2 Deferred/Future Diagrams

These are not implemented in v0.1:

- **Cerebra/LumaWeave Bridge** — Future ecosystem bridge (diagram exists but system not implemented)
- **Risk Clutch Mode Router** — Future adaptive friction system
- **RPG Armor Metaphor Diagram** — Branding/concept (not required for engineering)
- **Decision Severity Ladder** — Educational (not required for engineering)
- **Risk Component Radar** — Optional visualization
- **Scout Report Anatomy** — Report structure guide

---

## 5. README-Safe Diagrams

For README use, simplify to these 5 diagrams:

1. **Core Safety Boundary** — Most important design law
2. **System Architecture Map** — Full runtime spine
3. **Policy Decision Tree** — Default decision logic
4. **Sandbox Install Flow** — Package install sandboxing
5. **Scout Report Anatomy** — Report structure (if rendered)

README visuals should be understandable in 10 seconds. Use simplified versions for presentation slides.

---

## 6. Rendering Workflow

### 6.1 Source Format

Start with Mermaid text. Benefits:
- Version-control friendly
- Readable by agents and humans
- Easy to diff and update
- Renderable in GitHub/Obsidian/VS Code

Do not begin with static images that are hard to revise.

### 6.2 Rendering Targets

Mermaid can be rendered in:
- GitHub/GitLab Markdown
- Obsidian
- VS Code Markdown preview with Mermaid support
- Mermaid Live Editor
- Mermaid CLI (if installed)

Export formats (when ready):
- SVG (preferred for docs, stays crisp)
- PNG (for previews/social/README)
- PDF (for printing)

### 6.3 Export Workflow (When Ready)

```text
1. Write Mermaid in MERMAID_DIAGRAMS.md or .mmd files
2. Preview in Markdown viewer
3. Fix syntax and labels
4. Export to SVG via Mermaid CLI (when installed)
5. Store exports in docs/assets/diagrams/
6. Reference SVGs from README/docs
7. Keep Mermaid source next to exported assets
```

### 6.4 Naming Exports

Use lowercase kebab case:
- `system-architecture-map.svg`
- `core-safety-boundary.svg`
- `granular-evaluation-pipeline.svg`
- `policy-decision-tree.svg`
- `sandbox-install-flow.svg`
- `sweep-engine-flow.svg`
- `audit-reporting-flow.svg`
- `approval-queue-flow.svg`
- `risk-clutch-flow.svg`
- `integration-boundary.svg`
- `local-first-data-map.svg`

---

## 7. Style Guide

### 7.1 Color Semantics

Use consistent colors to support meaning (not replace labels):

```text
Blue/Cyan    -> request flow, normal operation
Amber/Gold   -> policy, approval, governance
Green        -> allow/safe path
Orange       -> sandbox/review/caution
Red          -> deny/alert/high risk
Purple       -> audit/report/memory bridge
Gray         -> registries/config/reference data
```

Suggested dark-mode palette:
- Background: #0B0F12
- Panel: #101820
- Text Primary: #E6EDF3
- Cyan Flow: #42D9FF
- Amber Policy: #F5B84B
- Green Allow: #5EE08B
- Orange Sandbox: #FF9F43
- Red Deny: #FF5C5C
- Purple Audit: #A78BFA
- Muted Gray: #6B7280

### 7.2 Shape Semantics

```text
Rounded rectangle -> process/component
Diamond           -> decision
Cylinder/database -> storage
Document          -> report/artifact
Hexagon           -> policy/registry
Subgraph box      -> module/system boundary
Small pill        -> category/capability label
```

### 7.3 Mermaid Syntax Guidance

- Use `flowchart LR` for left-to-right pipelines
- Use `flowchart TD` for decision trees
- Use `subgraph` for bounded systems
- Keep labels short (use docs for detail)
- Avoid huge node labels

### 7.4 Diagram Density

Prefer multiple clear diagrams over one huge diagram. A diagram should answer one main question:
- How does a command become a decision?
- How does sandboxing work?
- How are findings reported?
- How do integrations avoid bypassing policy?

If a diagram needs more than 20 nodes, consider splitting it.

---

## 8. Accessibility and Readability Rules

### 8.1 Accessibility

Diagrams should not rely only on color. Use:
- Text labels
- Clear node names
- Meaningful arrows
- Captions
- Adjacent prose summary

For every diagram, provide a short text description.

### 8.2 Captions

Every rendered diagram should have a caption:

```text
Figure <n>. <Title>. <One-sentence purpose.>
```

Example:
```text
Figure 1. System Architecture Map. Shows how actor requests pass through Policy Scout classification, policy, execution, and audit layers.
```

### 8.3 Typography

For polished visuals:
- Use clean sans-serif for diagrams
- Use monospace for commands
- Use bold labels sparingly
- Avoid tiny text
- Keep line lengths short

---

## 9. Maintenance Rules

### 9.1 Alignment with Implementation

If a diagram conflicts with source docs or code:
1. Report the conflict
2. Fix the source doc or the diagram
3. Do not let diagrams drift

Diagrams should not invent behavior. Source docs define behavior. Diagrams communicate behavior.

### 9.2 Update Trigger

If implementation changes affect the safety boundary, update relevant diagrams. Examples:
- New decision type added
- New integration boundary
- New data flow
- Policy rule changes

### 9.3 Source of Truth

Mermaid text is the source of truth. Rendered assets (SVG/PNG) are derived outputs. If Mermaid and rendered assets disagree, the Mermaid text wins.

### 9.4 Maintenance Rule

If a `.mmd` file is updated, update `MERMAID_DIAGRAMS.md` or keep the individual file as the new source of truth.

---

## 10. Future Graph/LumaWeave Compatibility

### 10.1 Deferred Integration

Cerebra/LumaWeave integration is deferred. The diagram exists but the system is not implemented in v0.1.

### 10.2 Future Graph Exports

When graph exports are implemented, map Policy Scout concepts to nodes and edges:

Example nodes:
- Actor, CommandRequest, EvaluationPacket, PolicyDecision, AuditEvent, Finding, ScoutReport, SandboxResult

Example edges:
- REQUESTED, EVALUATED_BY, MATCHED_POLICY, ISSUED_DECISION, GENERATED_EVENT, GENERATED_REPORT, FOUND

LumaWeave visuals can show dynamic relationships, while Mermaid docs show static architecture.

---

## 11. Not Required for v0.1

The following are not required for v0.1 alpha:

- Rendered SVG/PNG assets (Mermaid text is sufficient)
- Mermaid CLI installation (preview in Markdown viewers)
- LumaWeave/Cerebra integration (deferred)
- Risk clutch mode router (deferred)
- Presentation slide decks (deferred)
- Marketing graphics (deferred)
- Animated diagrams (deferred)
- Interactive graph visualizations (deferred)

---

## 12. Visual Production Doctrine

Diagrams should not become decorative drift. Every diagram should answer:

```text
What boundary does this clarify?
What implementation behavior does this preserve?
What mistake does this prevent?
```

If a diagram does not answer those questions, it probably is not needed yet.

Diagrams are part of the architecture, not decorative extras. They should make the safety boundary easier to understand and harder to accidentally break.
