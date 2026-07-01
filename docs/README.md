# Documentation

The documentation is organized around current behavior. Historical plans and
superseded specifications are intentionally excluded; Git history preserves the
development path without making readers reconcile several conflicting eras.

## Start here

| Document | Question answered |
|---|---|
| [Project README](../README.md) | What is Policy Scout and why does it exist? |
| [Implementation status](IMPLEMENTATION_STATUS.md) | What is implemented, experimental, partial, or planned? |
| [Architecture](ARCHITECTURE.md) | How does the current system fit together? |
| [Security model](SECURITY_MODEL.md) | What does Policy Scout protect, and what does it not guarantee? |
| [CLI reference](CLI.md) | Which commands exist and how mature are they? |
| [Installation](INSTALL.md) | How do I run and verify the project? |
| [Integrations](INTEGRATION_BOUNDARIES.md) | How do MCP, Tauri, Fossic, and Lattica relate to the core? |
| [Roadmap](ROADMAP.md) | Which verified gaps are intentionally future work? |

## Engineering detail

The [deep dives](deep-dives/) explain the most consequential implementation
choices:

- granular policy decisions and one-time approvals;
- package review, allowlisted migration, and namespace sandboxing;
- audit persistence, redaction ordering, Fossic emission, and JSON contracts.

## Decision records

Accepted decisions remain under [adr/](adr/). The
[ADR implementation index](adr/README.md) distinguishes an accepted design from
completed code. This distinction is essential: several ADRs deliberately define
future phases.

## Diagrams

Mermaid sources live under [diagrams/](diagrams/). The diagrams are explanatory;
code, tests, registries, and the capability status document are authoritative for
the current release.

## Maintainer operations

`agent/DISCORD_PROTOCOL.md` documents project coordination and release gates. It
is maintainer process, not part of the product contract.

## Sources of truth

In descending order for current behavior:

1. executable code and tests;
2. YAML command, policy, eval, scan, and playbook data;
3. current-state documents listed above;
4. ADRs for rationale and intended direction;
5. Git history for superseded plans and milestone notes.
