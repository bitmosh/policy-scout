1. v0.1 is Python CLI-first.
2. `check` is canonical; `explain` is not v0.1 canonical.
3. Docker is future sandbox backend, not required v0.1.
4. npm/pnpm/yarn/bun are v0.1 sandbox targets.
5. pip/generic shell sandboxing deferred.
6. Tauri UI deferred until CLI/report/audit spine is working.
7. TAXONOMIES.md decision/category names are canonical.
8. DATA_MODELS.md object shapes are canonical.

## 1. Language Boundary

Policy Scout v0.1 is Python CLI-first.

Python owns the initial implementation spine:

models -> parser -> classifier -> registry -> policy -> audit -> CLI -> approvals -> sandbox -> sweep -> reports

Rust is allowed only for isolated components after the Python spine is working and tests define stable behavior.

Rust should not be introduced in v0.1 if doing so delays:

- `policy-scout check -- npm install lodash`
- registry-backed decisions
- audit event persistence
- sandbox package install review
- project sweep
- Markdown/JSON Scout Reports

Potential Rust candidates after the spine works:

- shell parser
- process executor
- filesystem walker/diff engine
- redaction scanner
- future Tauri desktop core

The core contract between Python and any future Rust component must remain JSON-serializable and aligned with `DATA_MODELS.md`.