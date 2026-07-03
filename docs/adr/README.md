# Architecture decision records

`Accepted` means a design decision was approved. It does not mean every phase in
the ADR is implemented. This index records the v0.3.19 code status independently.

| ADR | Decision | Implementation status |
|---|---|---|
| [001](ADR-001-mcp-transport-and-trust-model.md) | MCP transport and trust | **Partial:** stdio server, tools, session state, hook mode, install/status scaffolding; wider agent-dispatch enforcement remains integration work |
| [002](ADR-002-policy-config-precedence.md) | Config precedence and project overrides | **Partial:** tighten-only project overrides, simulator, validator, history tester, and commit helper exist; complete user-global precedence/version UX is not demonstrated as a finished public contract |
| [003](ADR-003-graph-export-contract.md) | Graph export | **Planned:** no `policy_scout/export/` package or `export graph` CLI exists |
| [004](ADR-004-sandbox-backend-abstraction.md) | Sandbox backends and containment levels | **Partial:** package review and Linux namespace sandbox exist; backend protocol, Docker/Podman/bubblewrap/firejail implementations, and setup wizard do not |
| [005](ADR-005-registry-coverage-expansion.md) | Registry and eval coverage | **Planned/partial:** current registry remains 15 entries; eval is at 50 cases (up from 44 at ADR acceptance); proposed coverage command and ecosystem expansion are absent |
| [006](ADR-006-report-and-data-lifecycle.md) | Report and data lifecycle | **Partial:** list pagination/filtering and allowlisted temporary cleanup exist; retention, startup cleanup, and report deletion do not |
| [007](ADR-007-sweep-delta-and-exclusions.md) | Sweep delta and exclusions | **Planned:** no public delta/baseline/exclusion CLI contract is implemented |
| [008](ADR-008-desktop-ui-contract-hardening.md) | Desktop contract hardening | **Mostly implemented:** strict types, schemas, mocks, pagination, filters, and policy cards exist; native interaction remains manually verified |

When an ADR and executable behavior differ, code and tests describe the current
release while the ADR preserves the intended decision and rationale.
