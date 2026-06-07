# Policy Scout — Visual Style Guide

## 1. Purpose

This document defines the visual style direction for Policy Scout diagrams, charts, and future polished graphics.

Policy Scout should feel like:

```text
local-first
developer-friendly
lightweight
protective
precise
calm
technical
slightly game-inspired
```

The visual metaphor is:

```text
light armor for fast agents
```

---

## 2. Visual Personality

Policy Scout should not look like a heavy enterprise security product.

Avoid:

- fear-based red dashboards
- aggressive hacker aesthetics
- military overtones
- noisy cyberpunk clutter
- vague magical fantasy excess

Prefer:

- clean technical diagrams
- soft glowing boundaries
- precise policy layers
- calm alert states
- lightweight armor metaphor
- readable developer docs

---

## 3. Core Visual Metaphors

### 3.1 Scout

The scout is fast, observant, and ahead of danger.

Visual qualities:

```text
fast
light
aware
trail-reading
boundary-checking
reporting back
```

### 3.2 Light Armor

The armor is durable but not encumbering.

Visual qualities:

```text
thin protective layer
woven mesh
sigils/policy marks
transparent boundary
flexible protection
```

### 3.3 Harness

The harness routes power safely.

Visual qualities:

```text
straps
rails
gates
ports
bounded channels
safe routing
```

### 3.4 Scout Report

The report is calm field intelligence.

Visual qualities:

```text
field card
clean report
evidence trail
risk notes
recommended actions
```

---

## 4. Suggested Color Semantics

Use consistent colors across visuals.

```text
Blue/Cyan    -> request flow, normal operation
Amber/Gold   -> policy, approval, governance
Green        -> allow/safe path
Orange       -> sandbox/review/caution
Red          -> deny/alert/high risk
Purple       -> audit/report/memory bridge
Gray         -> registries/config/reference data
White/Slate  -> text and structure
```

Color should support meaning, not replace labels.

---

## 5. Suggested Palette

A possible dark-mode-friendly palette:

```text
Background:       #0B0F12
Panel:            #101820
Panel Border:     #22313A
Text Primary:     #E6EDF3
Text Secondary:   #9FB0BF
Cyan Flow:        #42D9FF
Amber Policy:     #F5B84B
Green Allow:      #5EE08B
Orange Sandbox:   #FF9F43
Red Deny:         #FF5C5C
Purple Audit:     #A78BFA
Muted Gray:       #6B7280
```

For light docs, invert carefully and preserve contrast.

---

## 6. Diagram Shape Semantics

Suggested shape meanings:

```text
Rounded rectangle -> process
Diamond           -> decision
Cylinder          -> storage/database
Document shape    -> report/artifact
Hexagon           -> policy/registry
Subgraph box      -> module/system boundary
Small pill        -> category/capability label
```

Keep shape semantics consistent.

---

## 7. Icon Concepts

Possible icons:

```text
Scout hood / small lantern
shield-weave
policy scroll
command prompt
package cube
sandbox/mirror box
audit ledger
report card
magnifying glass
gate/threshold
```

Avoid overly literal police/security icons.

---

## 8. Typography

For polished visuals:

- use clean sans-serif for diagrams
- use monospace for commands
- use bold labels sparingly
- avoid tiny text
- keep line lengths short

Suggested pairing:

```text
Sans-serif for labels
Monospace for commands and IDs
```

---

## 9. Diagram Density

Prefer multiple clear diagrams over one huge diagram.

A diagram should answer one main question.

Examples:

```text
How does a command become a decision?
How does sandboxing work?
How are findings reported?
How do integrations avoid bypassing policy?
```

If a diagram needs more than 20 nodes, consider splitting it.

---

## 10. README Visual Style

README visuals should be simplified.

Recommended README set:

```text
1. Core Safety Boundary
2. System Architecture Map
3. Command Decision Matrix
4. Sandbox Install Flow
5. Scout Report Anatomy
```

README visuals should be understandable in 10 seconds.

---

## 11. Technical Doc Visual Style

Technical docs can be denser.

Use these for:

```text
granular evaluation pipeline
risk and clutch flow
audit/report event chain
registry matching flow
integration boundary
```

Technical diagrams should still avoid visual clutter.

---

## 12. Scenario Card Style

Scenario cards should be compact.

Suggested card fields:

```text
Command
Actor
Category
Signals
Decision
Why
Next Action
```

Color accent should match decision:

```text
ALLOW -> green
ALLOW_LOGGED -> blue/green
REQUIRE_APPROVAL -> amber
SANDBOX_FIRST -> orange
DENY -> red
DENY_AND_ALERT -> red + report marker
```

---

## 13. Risk Chart Style

Risk charts should show component breakdown, not only final score.

Possible visual forms:

```text
stacked bar
radar/spider chart
component chips
vertical severity ladder
```

Always label components.

Avoid making risk appear more certain than it is.

Include confidence where relevant.

---

## 14. Severity/Confidence Matrix Style

Use a 2D matrix:

```text
Y axis: severity
X axis: confidence
```

The upper-right should indicate stronger response.

The upper-left should indicate cautious review because high impact remains important even with lower confidence.

---

## 15. Brand Tone

Policy Scout should feel like:

```text
friendly but serious
protective but not paranoid
technical but accessible
game-flavored but not unserious
```

The phrase "light armor for fast agents" should guide tone.

---

## 16. Visual Style Doctrine

Policy Scout's visual system should make safety feel understandable instead of scary.

Good visuals should reduce uncertainty.

They should show the harness, the path, the decision, and the evidence.
