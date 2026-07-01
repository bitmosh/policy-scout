# Architecture diagrams

Mermaid source files in this directory illustrate important Policy Scout flows.
They are explanatory and may omit newer optional subsystems.

| File | Subject |
|---|---|
| `01-system-architecture-map.mmd` | High-level component map |
| `02-core-safety-boundary.mmd` | Actor, policy, execution, and audit boundary |
| `03-granular-evaluation-pipeline.mmd` | Parse/classify/score/decide signals |
| `04-policy-decision-tree.mmd` | Decision routing |
| `05-sandbox-install-flow.mmd` | Package review path |
| `06-sweep-engine-flow.mmd` | Sweep evidence path |
| `07-audit-reporting-flow.mmd` | Audit and report outputs |
| `08-approval-queue-flow.mmd` | One-time approval lifecycle |
| `09-risk-clutch-flow.mmd` | Earlier risk/mode design; partly aspirational |
| `10-integration-boundary.mmd` | Adapter boundary |
| `11-local-first-data-map.mmd` | Local durable state |
| `12-cerebra-lumaweave-bridge.mmd` | Historical ecosystem design; not a core guarantee |

Current behavior is defined by code, tests, YAML registries, and
`docs/IMPLEMENTATION_STATUS.md`, not by a diagram.
