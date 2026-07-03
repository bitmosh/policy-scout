# ADR-003: Graph Export Contract and LumaWeave Boundary

**Status:** Accepted
**Date:** 2026-06-10
**Deciders:** Developer (bitmosh)
**Related ADRs:** [ADR-001](ADR-001-mcp-transport-and-trust-model.md) (MCP tool calls are graph nodes), [ADR-002](ADR-002-policy-config-precedence.md) (policy version is a node property)

---

## Context

Policy Scout and LumaWeave have a clear conceptual boundary: Policy Scout decides, LumaWeave visualizes. This boundary is documented in `INTEGRATION_BOUNDARIES.md`. What those documents lack is a normative, versioned data contract — a JSON schema that both sides can implement against independently without coordination on every change.

Without a locked contract, two expensive failure modes are likely as Tier 2 lands:

1. **Premature emission in [06] MCP Server.** The MCP server is the first feature that naturally produces real-time graph-ready data: each `policy_scout_check` call is a node, each decision is an edge. If the MCP server emits graph data in an ad-hoc format, and LumaWeave builds an ingestion layer against that format, this creates a de facto contract that's hard to change later. Better to define the contract first.

2. **Audit event creep.** As Tier 2 adds new event types (MCPToolCallCompleted, ProjectOverrideLoaded, SecretScanCompleted, etc.) the audit store grows. If there's no defined mapping from audit event types to graph node/edge types, LumaWeave will either ignore the new events or require Policy Scout changes every time a new event type is added. A declared mapping table prevents this.

This ADR locks three things: the node/edge JSON schema, the mapping from audit events to graph elements, and the export mechanism. It does not specify anything about LumaWeave's internal representation — that is entirely LumaWeave's concern. The contract is the JSON that Policy Scout emits; how LumaWeave ingests and lays it out is out of scope here.

---

## Forces

- **Decoupling:** LumaWeave must be able to ingest graph exports without importing any Policy Scout code. The schema must be self-describing enough that a generic graph importer can use it without domain knowledge.
- **Privacy:** The audit store contains command text, file paths, and potentially redacted secrets. Graph exports must apply the same redaction rules as the audit query endpoints. No raw credentials may appear in exported nodes.
- **Incrementality:** The audit store may contain thousands of events. Full re-export on every query is impractical for large stores. The export format must support range-based export (export events since last_event_id) without requiring LumaWeave to implement delta-merging logic.
- **Schema stability:** LumaWeave ingestion code should not break when Policy Scout adds new node or edge types. The schema must be designed for forward compatibility — unknown types must be safely ignorable.
- **No new runtime deps:** The export layer must be implementable in stdlib only (json, pathlib). No graph libraries, no external serialization formats.
- **On-demand, not streaming:** For v1, graph export is triggered by a CLI command and produces a file. Real-time streaming (via MCP) is a Phase 3 addition, not a v1 requirement. This keeps the export infrastructure simple while leaving the hook point defined.
- **LumaWeave is passive:** Policy Scout emits. LumaWeave ingests. Policy Scout never calls back into LumaWeave, never writes to LumaWeave's storage, and never reads from LumaWeave's state. The data flow is strictly one-directional.

---

## Decision

### D1 — Export format: JSON Lines (NDJSON), one record per line

Each record is either a node or an edge, distinguished by a `"record_type"` field. The file has a header record on line 1 and then node/edge records in chronological order.

Rationale: JSON Lines is readable, appendable, and streamable. A full JSON array requires loading the entire file before parsing. NDJSON works correctly with `tail -f`, `jq`, and any streaming processor. It is the natural format for derived-from-audit-log data.

**Rejected:** GraphML, DOT, Cypher. These are graph-specific formats that require domain parsers. NDJSON + a simple type field is sufficient and requires no new dependencies on either side.

**Rejected:** Single JSON file. Requires full re-read for any incremental update. Not appendable.

### D2 — Node schema

```json
{
  "record_type": "node",
  "schema_version": 1,
  "id": "req_a1b2c3d4e5f6",
  "node_type": "CommandRequest",
  "label": "npm install lodash",
  "timestamp": "2026-06-10T14:23:11.000Z",
  "properties": {
    "actor_type": "agent",
    "trust_level": "untrusted_agent",
    "risk_band": "high",
    "decision": "SANDBOX_FIRST"
  },
  "source_event_id": "evt_abc123",
  "source_event_type": "DecisionIssued",
  "policy_scout_version": "0.x.x"
}
```

Required fields on every node: `record_type`, `schema_version`, `id`, `node_type`, `label`, `timestamp`.
Optional but recommended: `properties`, `source_event_id`, `source_event_type`.
`label` must be safe for display — apply redaction before populating it.
`properties` must not contain raw secrets. Values are strings, numbers, booleans, or arrays of those — no nested objects.

### D3 — Edge schema

```json
{
  "record_type": "edge",
  "schema_version": 1,
  "id": "edge_a1b2c3d4e5f6",
  "edge_type": "ISSUED_DECISION",
  "source_id": "req_a1b2c3d4e5f6",
  "target_id": "dec_b2c3d4e5f6a1",
  "label": "SANDBOX_FIRST",
  "timestamp": "2026-06-10T14:23:11.000Z",
  "properties": {}
}
```

Required fields: `record_type`, `schema_version`, `id`, `edge_type`, `source_id`, `target_id`.
`source_id` and `target_id` must reference node IDs that appear in the same export file (or a previously exported file in an incremental export).

### D4 — Header record (line 1 of every export file)

```json
{
  "record_type": "header",
  "schema_version": 1,
  "policy_scout_version": "0.x.x",
  "exported_at": "2026-06-10T14:30:00.000Z",
  "export_id": "export_a1b2c3d4",
  "export_range": {
    "from_event_id": null,
    "to_event_id": "evt_xyz999",
    "from_timestamp": "2026-06-01T00:00:00Z",
    "to_timestamp": "2026-06-10T14:30:00Z",
    "event_count": 1247
  },
  "node_type_counts": {
    "CommandRequest": 412,
    "PolicyDecision": 412,
    "SandboxResult": 38,
    "SweepResult": 6,
    "Finding": 102,
    "ScoutReport": 56,
    "AuditEvent": 221
  }
}
```

### D5 — Audit event → graph element mapping table

This is the normative mapping. Every event type gets at most one node and zero or more edges. "No mapping" means the event is not exported (it's internal bookkeeping, not meaningful to a graph viewer).

| Audit event type | → Node type | Node ID source | → Edge type | Edge connects |
|---|---|---|---|---|
| `DecisionIssued` | `CommandRequest` | `request_id` | `ISSUED_DECISION` | request → decision node |
| `DecisionIssued` | `PolicyDecision` | `evt_id` | — | — |
| `CommandClassified` | (no separate node) | — | `CLASSIFIED_AS` | request → category label node |
| `PolicyMatched` | (no separate node) | — | `MATCHED_POLICY` | request → policy rule node |
| `SandboxResultWritten` | `SandboxResult` | `data.sandbox_id` | `SANDBOXED_AS` | request → sandbox result |
| `SweepCompleted` | `SweepResult` | `data.sweep_id` | — | — |
| `SweepFindingCreated` | `Finding` | `data.finding_id` | `GENERATED_FINDING` | sweep → finding |
| `ScoutReportGenerated` | `ScoutReport` | `data.report_id` | `GENERATED_REPORT` | source → report |
| `ApprovalRequested` | `ApprovalRequest` | `data.approval_id` | `REQUIRED_APPROVAL` | request → approval |
| `ApprovalApprovedOnce` | (no new node) | — | `APPROVED` | actor → approval request |
| `ApprovalDeniedOnce` | (no new node) | — | `DENIED` | actor → approval request |
| `MCPToolCallCompleted` | `MCPToolCall` | `data.session_id + tool_name` | `VIA_MCP` | mcp call → decision node |
| `SecretScanCompleted` | `SecretScanResult` | `data.scan_id` | `GENERATED_SCAN` | source → scan result |
| `SecretFindingCreated` | `SecretFinding` | `data.scan_id + line` | `GENERATED_FINDING` | scan → finding |
| `ProjectOverrideLoaded` | (no node — internal) | — | — | — |
| `ChainVerificationCompleted` | (no node — internal) | — | — | — |
| `LockdownActivated` | `LockdownEvent` | `evt_id` | `ACTIVATED_LOCKDOWN` | actor → lockdown event |
| `EvidencePreserved` | `EvidenceArchive` | `data.archive_path` | `PRESERVED_EVIDENCE` | lockdown → archive |

Events not in this table (e.g., `AuditError`, `SandboxError`) produce no graph nodes. They remain queryable in the audit store but are not exported. This keeps the graph clean.

**Forward compatibility rule:** If LumaWeave encounters a `node_type` or `edge_type` it doesn't recognize, it must silently ignore that record. Policy Scout may add new node and edge types in future versions without incrementing `schema_version`, as long as existing types retain their semantics. `schema_version` is incremented only when the meaning of an existing field changes or a required field is removed.

### D6 — Export mechanism: on-demand CLI, file output

```bash
# Export all events as a graph file
policy-scout export graph --output graph.ndjson

# Export a time range
policy-scout export graph --since 2026-06-01 --until 2026-06-10 --output graph.ndjson

# Export since a previous export (incremental)
policy-scout export graph --since-export-id export_a1b2c3d4 --output graph-delta.ndjson

# Export to stdout (pipe to jq, etc.)
policy-scout export graph

# Print summary without writing
policy-scout export graph --dry-run
```

The export command reads from the audit SQLite store, applies the mapping table (D5), applies redaction, and writes NDJSON.

For v1 there is no push/streaming export. The MCP server (ADR-001) does not emit graph data in real-time in Phase 3. Phase 3 of this ADR (real-time emission via MCP) adds a `notifications/graphEvent` notification type for clients that opt in — this is deferred.

### D7 — Redaction rules for graph export

These are additive on top of the existing `audit.redaction` module:

1. `label` field: run through `redact_string()` (same function used in audit queries). Any value matching a secret pattern is replaced with `[REDACTED]`.
2. `properties` values: run through `redact_dict()`. Applies existing redaction patterns.
3. File paths: project-relative paths preferred. Absolute paths that fall outside the project root are truncated to the last two path components.
4. Command strings: the existing `redact_dict({"command": ...})` call handles this correctly — secret-like values in command strings are already redacted at the audit write layer.

The export layer does **not** re-run secret pattern matching on export. It trusts that audit events were already redacted at write time. If they weren't (audit store predates the redaction logic), the export applies a best-effort pass.

---

## Interface Definition

### New module: `policy_scout/export/`

```
policy_scout/export/
├── __init__.py
├── graph_exporter.py     # main export logic (audit → NDJSON)
├── node_factory.py       # audit event → node record
├── edge_factory.py       # audit event → edge record(s)
└── schema.py             # node_type / edge_type constants + schema_version
```

### `graph_exporter.py` public API

```python
def export_graph(
    audit_store: AuditStore,
    output: Path | None = None,    # None → stdout
    since: str | None = None,      # ISO timestamp or event ID
    until: str | None = None,
    since_export_id: str | None = None,
    dry_run: bool = False,
) -> ExportSummary:
    """Export audit events as NDJSON graph file."""

@dataclass
class ExportSummary:
    export_id: str
    node_count: int
    edge_count: int
    event_count: int
    node_type_counts: dict[str, int]
    output_path: str | None
    duration_ms: int
```

### Schema constants (`schema.py`)

```python
SCHEMA_VERSION = 1

class NodeType:
    COMMAND_REQUEST  = "CommandRequest"
    POLICY_DECISION  = "PolicyDecision"
    SANDBOX_RESULT   = "SandboxResult"
    SWEEP_RESULT     = "SweepResult"
    FINDING          = "Finding"
    SECRET_FINDING   = "SecretFinding"
    SECRET_SCAN      = "SecretScanResult"
    SCOUT_REPORT     = "ScoutReport"
    APPROVAL_REQUEST = "ApprovalRequest"
    MCP_TOOL_CALL    = "MCPToolCall"
    LOCKDOWN_EVENT   = "LockdownEvent"
    EVIDENCE_ARCHIVE = "EvidenceArchive"

class EdgeType:
    ISSUED_DECISION    = "ISSUED_DECISION"
    MATCHED_POLICY     = "MATCHED_POLICY"
    CLASSIFIED_AS      = "CLASSIFIED_AS"
    SANDBOXED_AS       = "SANDBOXED_AS"
    REQUIRED_APPROVAL  = "REQUIRED_APPROVAL"
    APPROVED           = "APPROVED"
    DENIED             = "DENIED"
    GENERATED_FINDING  = "GENERATED_FINDING"
    GENERATED_REPORT   = "GENERATED_REPORT"
    GENERATED_SCAN     = "GENERATED_SCAN"
    VIA_MCP            = "VIA_MCP"
    ACTIVATED_LOCKDOWN = "ACTIVATED_LOCKDOWN"
    PRESERVED_EVIDENCE = "PRESERVED_EVIDENCE"
```

### CLI additions (`cli/main.py`)

```
policy-scout export graph [--output <path>] [--since <ts>] [--until <ts>]
                          [--since-export-id <id>] [--dry-run] [--json]
```

The `--json` flag outputs the `ExportSummary` as JSON instead of human-readable text.

### New audit event type

```python
class EventType:
    GRAPH_EXPORTED = "GraphExported"
```

`GraphExported` data:
```json
{
  "export_id": "export_a1b2c3d4",
  "node_count": 412,
  "edge_count": 820,
  "output_path": "/home/user/graph.ndjson",
  "schema_version": 1
}
```

---

## Blast Radius

### Files changed

| File | Change type | Risk |
|---|---|---|
| `policy_scout/export/__init__.py` (new) | Package init | None |
| `policy_scout/export/graph_exporter.py` (new) | Export logic | Low (pure read + transform) |
| `policy_scout/export/node_factory.py` (new) | Event → node mapping | Low (new file, uses mapping table D5) |
| `policy_scout/export/edge_factory.py` (new) | Event → edge mapping | Low (new file) |
| `policy_scout/export/schema.py` (new) | Type constants | None |
| `policy_scout/audit/events.py` | 1 new event type (`GraphExported`) | Low (additive) |
| `policy_scout/cli/main.py` | Add `export` command group | Low (additive) |

### Files NOT changed

- Policy engine — completely unaffected. Export reads from the audit store, not from the running engine.
- Audit store — read-only from the exporter's perspective. No new write paths.
- Scan, git, integrity, response modules — no changes needed.
- All existing tests — no changes. The export layer is purely additive.

### Dependencies

None. `json`, `pathlib`, `dataclasses` from stdlib are sufficient.

### LumaWeave's responsibility (out of scope for Policy Scout)

LumaWeave must implement an NDJSON ingestion path that:
1. Reads the header record and validates `schema_version`
2. Creates or updates nodes by `id` (upsert semantics for incremental imports)
3. Creates edges after both source and target nodes are loaded
4. Ignores `node_type` and `edge_type` values it doesn't recognize

LumaWeave must NOT call back into Policy Scout at ingestion time. It must NOT modify the NDJSON files. It must NOT rely on fields not documented in this ADR without a corresponding ADR update.

---

## Implementation Phases

### Phase 1 — Schema and mapping table (~150 lines)

**Scope:** `schema.py` (constants), `node_factory.py` and `edge_factory.py` (event → node/edge transforms for the 18 event types in the mapping table D5), unit tests for each factory function.
**Acceptance:** Every event type in the mapping table has a test. Factory functions for unmapped event types return `None`. Schema constants are stable (no strings hardcoded outside `schema.py`).
**Commit:** `feat(export): graph schema constants and event-to-node/edge factory`
**Unlocks:** Phase 2.

### Phase 2 — Export engine and CLI (~200 lines)

**Scope:** `graph_exporter.py` (main export loop: query audit store → call factories → write NDJSON with header), `export` CLI command group, `GraphExported` audit event.
**Acceptance:** `policy-scout export graph --dry-run` runs against a populated test audit store, reports correct node/edge counts, writes no file. `policy-scout export graph --output /tmp/test.ndjson` writes valid NDJSON that passes a schema validator. Header record appears on line 1.
**Test:** Fixture audit store with 5 `DecisionIssued` events → export → verify node count = 10 (5 CommandRequest + 5 PolicyDecision), edge count = 5.
**Commit:** `feat(export): graph exporter CLI — on-demand NDJSON export`
**Unlocks:** Phase 3. LumaWeave can now begin building its ingestion layer against a stable file format.

### Phase 3 — Incremental export (~80 lines delta)

**Scope:** `--since-export-id` flag — reads the last exported event ID from the previous export's header, queries only events after that ID.
**Acceptance:** Two sequential exports with `--since-export-id` produce no overlap (no duplicate node IDs). Total nodes across both exports equals what a single full export would produce.
**Commit:** `feat(export): incremental graph export via since-export-id`

### Phase 4 — MCP real-time graph emission (deferred, Phase 3 of ADR-001)

**Scope:** When the MCP server is running and a LumaWeave client has subscribed (via `notifications/subscribe` to `graphEvent`), emit a `MCPToolCall` node record as a `notifications/graphEvent` notification after each tool call completes.
**Note:** This is a stretch goal for v1. The infrastructure (schema, factories) is ready after Phase 2. The MCP server needs `notifications/subscribe` support added. This is explicitly deferred to after ADR-001 Phase 3 is stable.
**Commit:** `feat(server): real-time graph event notifications for subscribed LumaWeave clients`

---

## Consequences

**Enabled:**
- LumaWeave can build an ingestion layer immediately against a stable schema after Phase 2 lands — without any further coordination with Policy Scout implementation work.
- The forward-compatibility rule (ignore unknown types) means LumaWeave doesn't break when new Tier 2 event types land. Adding `MCPToolCall` nodes doesn't require a LumaWeave update — LumaWeave starts seeing new node types in imports.
- The mapping table (D5) is a single canonical reference. When a new audit event type is added (e.g., in [07] injection detection), the mapping table gets one new row, the factory gets one new function, and the graph exporter picks it up automatically.
- Incremental export (Phase 3) makes continuous import practical — LumaWeave can poll for new exports on a schedule without duplicating data.
- The `--dry-run` flag makes the export safe to run in CI or in automated health checks without side effects.

**Given up / deferred:**
- Real-time streaming. Push-on-change from Policy Scout to LumaWeave requires either the MCP notification path (Phase 4, deferred) or a polling mechanism that LumaWeave drives. For v1, LumaWeave polls by running `policy-scout export graph` periodically.
- Bidirectional graph enrichment. LumaWeave cannot annotate Policy Scout's graph data (e.g., "this finding was investigated and closed"). That state lives in LumaWeave's own data model. The boundary is strictly one-directional.
- Fine-grained per-node redaction overrides. For v1, redaction is applied uniformly per the rules in D7. A user who wants to see unredacted command text in LumaWeave must do so in the audit query layer, not in graph exports.

**Risks to watch:**
- The mapping table (D5) must be kept current as new event types are added. Add a CI test that asserts every `EventType` constant is either in the mapping table or in an explicit "not exported" exclusion list. Missing entries should fail loudly, not silently produce an incomplete export.
- `schema_version = 1` should remain at 1 for as long as possible. Before incrementing it, consider whether the breaking change is truly necessary — each increment forces LumaWeave to update its ingestion code simultaneously.
- The header record `node_type_counts` is computed on export, not stored. If the mapping table changes between two exports, the counts across those exports are not directly comparable. Document this limitation in the export summary output.
