# Audit, redaction, and JSON contracts

## Primary audit record

SQLite is the queryable source for CLI audit commands. JSONL is an append-oriented
debug/export stream. Events carry stable IDs and correlation fields for requests,
decisions, approvals, executions, sandboxes, sweeps, findings, and reports.

Important execution paths distinguish ordinary writes from critical audit
writes. If a critical event cannot be persisted, risky execution stops rather
than continuing without accountability.

## Redact before persistence

Event dictionaries pass through recursive redaction before insertion. The same
redaction utilities protect terminal output, reports, and exports. This ordering
matters: storage should not receive a raw secret and rely on presentation code to
hide it later.

The redaction layer preserves `upstream_causation_id` explicitly because Fossic
event IDs can resemble high-entropy tokens. That exception is key-based and
narrow; ordinary strings still pass through secret-pattern matching.

Regex redaction is intentionally documented as incomplete. The safety property
is “known forms are consistently removed,” not “arbitrary sensitive data can
never enter an artifact.”

## Tamper evidence and Fossic

The JSONL stream supports HMAC-chain verification. This detects modification or
reordering relative to the chain material; it does not make local files
undeletable or replace access controls.

When the Fossic binding is available, redacted events are also emitted
best-effort to a local Fossic database. Request-scoped events use
`policy-scout/audit/<request_id>` and posture events use
`policy-scout/posture`. SQLite remains Policy Scout's operational audit
authority. Fossic emission failure is reported but does not invalidate a
successful SQLite write.

## Consumer contracts

The Tauri dashboard invokes the installed CLI instead of reading SQLite or
project files directly. Rust adapters build fixed argument vectors and validate
IDs, event types, pagination values, and cleanup targets before invocation.

CLI JSON examples are represented in three places:

- JSON Schema files under `ui/desktop/src/contracts/`;
- TypeScript domain types;
- browser-preview mock fixtures.

`tests/test_json_contracts.py` compares live CLI output and mocks against the
same schemas when the optional `jsonschema` package is available. Rust unit tests
cover adapter allowlists. This keeps the CLI as the authority while making
frontend drift visible.

## Limits

- Fossic emission is best-effort at runtime, but the vendored PyO3 binding must
  be built before the adapter can be imported.
- The standalone Policy Scout-to-Lattica relay is experimental and currently
  outside the tracked core.
- JSON schemas cover dashboard-consumed surfaces, not every CLI payload.
- Several storage query methods convert failures into warnings and empty results;
  callers must distinguish operational failure from a genuinely empty store.
