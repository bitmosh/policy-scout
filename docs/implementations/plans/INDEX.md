# Implementation Plans — Index

Companion to `docs/implementations/improve_suggestions.md`.
Each plan covers: problem, new modules, implementation approach, integration points, test strategy, effort estimate, open questions.

---

## Plans

| # | Gap | File | Tier | Est. Lines |
|---|-----|------|------|-----------|
| 01 | Continuous Monitoring (Watch Mode) | [01_watch_mode.md](01_watch_mode.md) | 2 | ~980 |
| 02 | Threat Intelligence Integration | [02_threat_intel.md](02_threat_intel.md) | 2 | ~1380 |
| 03 | Supply Chain Detection Depth | [03_supply_chain_depth.md](03_supply_chain_depth.md) | 3 | ~1860 |
| 04 | Secret Scanning | [04_secret_scanning.md](04_secret_scanning.md) | 1 | ~1350 |
| 05 | Tamper-Evident Audit Log | [05_tamper_evident_audit.md](05_tamper_evident_audit.md) | 1 | ~640 |
| 06 | MCP Server / Agent Integration | [06_mcp_server.md](06_mcp_server.md) | 2 | ~1200 |
| 07 | Prompt Injection Detection | [07_prompt_injection_detection.md](07_prompt_injection_detection.md) | 2 | ~1130 |
| 08 | Broader Sandbox (unshare + strace) | [08_broader_sandbox.md](08_broader_sandbox.md) | 3 | ~1630 |
| 09 | Incident Response Layer | [09_incident_response.md](09_incident_response.md) | 1 | ~1220 |
| 10 | Policy Management Tooling | [10_policy_management.md](10_policy_management.md) | 2 | ~1490 |
| 11 | Desktop UI Improvements | [11_desktop_ui.md](11_desktop_ui.md) | 2 | ~1190 |
| 12 | Git Integration | [12_git_integration.md](12_git_integration.md) | 1 | ~1370 |
| 13 | Self-Integrity | [13_self_integrity.md](13_self_integrity.md) | 1 | ~640 |

**Total estimated new code:** ~15,080 lines across all 13 plans.

---

## Implementation Tiers

**Tier 1 — High value, relatively contained (start here):**
- [05] Tamper-evident audit log — ~640 lines, zero new dependencies
- [13] Self-integrity — ~640 lines, zero new dependencies
- [09] Incident response (playbooks + lockdown) — ~1220 lines, primarily YAML data
- [12] Git integration (pre-commit hooks + lockfile tamper) — ~1370 lines
- [04] Secret scanning (entropy + patterns + staged) — ~1350 lines

**Tier 2 — High value, moderate complexity:**
- [01] Watch mode daemon — ~980 lines, requires `inotifywait` (system tool, no pip install)
- [02] Threat intel (typosquatting + OSV + lockfile integrity) — ~1380 lines
- [06] MCP server — ~1200 lines, enables in-loop agent governance
- [07] Prompt injection detection — ~1130 lines
- [10] Policy management (simulation + conflict detection) — ~1490 lines
- [11] Desktop UI (approvals + live stream + trend chart) — ~1190 lines

**Tier 3 — High value, significant complexity:**
- [03] Supply chain depth (AST analysis + dep confusion + transitive) — ~1860 lines
- [08] Broader sandbox (unshare + strace) — ~1630 lines, Linux kernel feature dependency

---

## Dependency Graph

Plans that build on each other:

```
[04] Secret Scanning
  └─ used by [12] Git Integration (staged scanner reuses scan engine)

[02] Threat Intel
  └─ used by [03] Supply Chain Depth (typosquatting + advisory lookup)

[06] MCP Server
  └─ used by [07] Prompt Injection Detection (response scanning hook)
  └─ requires CLI print/return separation (refactor inside [06])

[09] Incident Response (lockdown)
  └─ referenced by [13] Self-Integrity (startup check checks lockdown state)

[08] Broader Sandbox
  └─ extends [policy engine] SANDBOX_FIRST routing

[10] Policy Management
  └─ uses [09]'s lockdown state in simulation context
```

---

## What Each Plan Does NOT Cover

- Cross-plan integration testing (each plan tests its own modules; integration across plans is a separate pass)
- UI/visual verification (flagged in [11]; must be manually checked with `npm run dev`)
- Remote/cloud sync or multi-machine state
- Kernel-level detection (out of scope for the project)
- Windows/macOS platform parity for [08] (Linux only for now)
