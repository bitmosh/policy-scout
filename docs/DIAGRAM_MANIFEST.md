# Policy Scout — Diagram Manifest

## Purpose

This manifest lists the individual Mermaid source files for Policy Scout diagrams.

These `.mmd` files are extracted from `MERMAID_DIAGRAMS.md` so they can be rendered individually into SVG, PNG, or PDF.

## Diagram Files

| # | File | Purpose |
|---:|---|---|
| 1 | `01-system-architecture-map.mmd` | Full Policy Scout runtime spine. |
| 2 | `02-core-safety-boundary.mmd` | Shows bad vs good execution boundary. |
| 3 | `03-granular-evaluation-pipeline.mmd` | Shows evaluation packet layers. |
| 4 | `04-policy-decision-tree.mmd` | Shows default decision branches. |
| 5 | `05-sandbox-install-flow.mmd` | Shows package install sandbox flow. |
| 6 | `06-sweep-engine-flow.mmd` | Shows project/quick sweep flows. |
| 7 | `07-audit-reporting-flow.mmd` | Shows event and report chain. |
| 8 | `08-approval-queue-flow.mmd` | Shows scoped human approval. |
| 9 | `09-risk-clutch-flow.mmd` | Shows granular signals feeding clutch. |
| 10 | `10-integration-boundary.mmd` | Shows adapter boundaries. |
| 11 | `11-local-first-data-map.mmd` | Shows local data/storage map. |
| 12 | `12-cerebra-lumaweave-bridge.mmd` | Shows future ecosystem bridge. |

## Rendering Example

With Mermaid CLI installed:

```bash
mmdc -i diagrams/01-system-architecture-map.mmd -o docs/assets/diagrams/system-architecture-map.svg
```

## Maintenance Rule

If a `.mmd` file is updated, update `MERMAID_DIAGRAMS.md` or keep the individual file as the new source of truth.
