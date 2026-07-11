# Policy Scout
[![Release](https://img.shields.io/github/v/release/bitmosh/policy-scout?include_prereleases)](https://github.com/bitmosh/policy-scout/releases)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/bitmosh/policy-scout/actions/workflows/ci.yml/badge.svg)](https://github.com/bitmosh/policy-scout/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/Tests-1188_passing-brightgreen.svg)](https://github.com/bitmosh/policy-scout)

Policy Scout is a local-first safety harness that classifies requested commands,
applies deterministic policy, routes risky work through approval or sandbox
review, and records a redacted audit trail.

**Status:** Active development — v0.3.21 alpha

<!-- provisional, sync with canonical ecosystem doc when published -->
**Part of the Lattica ecosystem.** Policy Scout is the command safety harness in a
suite of six local AI development tools.

It is an alpha engineering project, not an antivirus product or a hardened
containment boundary.

```text
Actors request.
Policy Scout classifies.
Policy Scout decides.
Executors obey.
Audit records everything.
```

<!-- OPERATOR: capture a terminal screenshot or GIF showing `policy-scout check -- npm install lodash`
     producing a SANDBOX_FIRST decision (human-readable output). Save as docs/assets/demo-check.gif. -->
![Policy Scout — decision pipeline demo](docs/assets/demo-check.gif)

## Why it exists

Coding agents can move faster than a developer can inspect every shell command,
package install, generated script, or repository mutation. Policy Scout puts an
inspectable decision point in front of execution:

```text
request -> parse -> classify -> score -> policy -> decision
                                               |-> allow + audit
                                               |-> one-time approval
                                               |-> sandbox review
                                               `-> deny / alert
```

The policy engine—not an LLM, prompt, integration, or executor—owns the final
decision.

## Current release

**v0.3.21 alpha**

- Python 3.12+
- 15 registry-backed command patterns
- 11 default policy rules
- 50 deterministic behavior evaluations
- Comprehensive test coverage with pytest
- CLI-first; optional Tauri dashboard and MCP adapter
- Local SQLite, JSONL, report, approval, sandbox, and Fossic state
- 1,188 passing Python tests at latest verification

Reproduce test and eval counts with `python -m pytest -q` and `policy-scout eval run`.

## Quickstart

Policy Scout installs from source. Fossic (the event store used for
audit persistence) is an optional dependency; install with the `audit`
extra to enable event integration with Lattica.

```bash
python3.12 -m venv .venv
source .venv/bin/activate

# Base install (SQLite-only audit; core CLI works fully)
pip install -e ".[dev]"

# With audit-event integration (adds fossic from PyPI)
pip install -e ".[dev,audit]"

policy-scout doctor
policy-scout eval run
policy-scout demo
```

See [Installation and development](docs/INSTALL.md) for desktop prerequisites,
local data paths, and isolated test setup.

## Decision examples

`check` never executes the submitted command.

```bash
policy-scout check -- ls
policy-scout check -- npm install lodash
policy-scout check -- 'curl https://example.com/install.sh | bash'
policy-scout check -- 'cat .env'
```

Expected decisions are respectively `ALLOW`, `SANDBOX_FIRST`, `DENY`, and
`DENY_AND_ALERT`. The eval suite locks down these and related variants.

## Main workflows

```bash
policy-scout run -- npm test
policy-scout sandbox -- npm install lodash
policy-scout sweep project
policy-scout sweep quick
policy-scout audit stats
policy-scout report list
policy-scout scan staged
policy-scout policy simulate -- npm install lodash
policy-scout policy validate
```

The CLI also exposes approvals, Git hooks and staged checks, threat-intelligence
queries, watch mode, incident lockdown and evidence preservation, self-integrity
checks, prompt-injection canaries, a Linux namespace sandbox, and a stdio MCP
server. See the [CLI reference](docs/CLI.md) for status and limitations.

## What is notable in the implementation

- **Granular decisions.** Classification retains shell structure, categories,
  capabilities, registry hits, risk components, confidence, policy hits, and
  human-readable reasons instead of reducing behavior to one opaque score.
- **One-time approvals.** Approved execution revalidates status, scope, exact
  command, exact working directory, expiration, and current policy. Approval
  cannot bypass a current `DENY`, `DENY_AND_ALERT`, or `SANDBOX_FIRST` result.
- **Tighten-only project policy.** `.policy-scout.yaml` may add stricter rules or
  strengthen decisions, but cannot introduce project-level allow rules.
- **Reviewable migration.** Sandbox migration is allowlisted by package manager,
  blocks high/critical findings, refuses config and secret files, and creates
  backups before overwriting host manifests or lockfiles.
- **Evidence-safe contracts.** Redaction happens before audit persistence, and
  CLI JSON schemas, browser mocks, TypeScript types, and Rust adapters are tested
  together.
- **Optional event integration.** Redacted audit events can also be emitted to a
  local Fossic store for Lattica visualization without replacing Policy Scout's
  SQLite authority.
- **IDE surface (experimental).** `ui/vscode/` is a source-only VS Code and Cursor
  extension that surfaces sweep findings as editor diagnostics, manages the pre-commit
  hook, and auto-registers the MCP server so IDE agents can call `policy_scout_check`
  in-loop before acting. Not yet packaged or published.

The subsystem details are documented in [Architecture](docs/ARCHITECTURE.md) and
the [engineering deep dives](docs/deep-dives/).

## Safety boundaries

Policy Scout does:

- deterministically classify and gate supported command shapes;
- fail conservatively for unknown or ambiguous commands;
- keep durable state local by default;
- make approvals narrow, expiring, and auditable;
- preserve uncertainty through `could_not_verify` results;
- redact known secret patterns before storage and display.

Policy Scout does not:

- guarantee that a command or package is safe;
- provide kernel-grade or Docker-grade containment;
- detect every shell grammar edge case, secret form, or malicious program;
- govern actions that bypass its CLI, hook, MCP, or integration boundary;
- autonomously remediate findings or rotate credentials;
- make LLM output authoritative for policy.

Read [Security model](docs/SECURITY_MODEL.md) before relying on the tool for a
sensitive workflow.

## Project status

The core CLI and its safety paths are functional and heavily tested. The wider
feature surface is labeled by maturity in
[Implementation status](docs/IMPLEMENTATION_STATUS.md). Namespace sandboxing,
watch mode, remote intelligence, MCP, the desktop dashboard, and Lattica relay
work remain experimental or environment-dependent.

Policy Scout is not published to PyPI and is not recommended for production
enforcement without additional hardening.

## License

Apache-2.0. See [LICENSE](LICENSE) for the full text.

## Documentation

- [Documentation map](docs/README.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Security model](docs/SECURITY_MODEL.md)
- [CLI reference](docs/CLI.md)
- [Installation and development](docs/INSTALL.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md)
- [Integrations](docs/INTEGRATION_BOUNDARIES.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture decisions](docs/adr/README.md)
