# Policy Scout Diagrams

This folder contains individual Mermaid diagram source files.

The main combined diagram doc is:

```text
../MERMAID_DIAGRAMS.md
```

These split `.mmd` files are easier to render one-by-one.

## Suggested Use

1. Preview the `.mmd` file.
2. Export to SVG or PNG.
3. Store rendered assets in `docs/assets/diagrams/`.
4. Reference rendered diagrams from README and docs.

## Recommended First Renders

```text
01-system-architecture-map.mmd
02-core-safety-boundary.mmd
03-granular-evaluation-pipeline.mmd
05-sandbox-install-flow.mmd
07-audit-reporting-flow.mmd
```

## Doctrine

Diagrams should clarify the safety boundary:

```text
Actors request.
Policy Scout decides.
Executors obey.
Audit records everything.
```
