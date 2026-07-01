# Security model

Policy Scout is a policy gate for local development workflows. It reduces the
chance that an agent or automation tool performs a dangerous action without an
explicit, reviewable decision. It is not a general malware detector or a
complete containment system.

## Authority boundary

```text
actor -> request -> parser/classifier -> risk scorer -> policy engine
                                                       |
                                                       v
                    executor <- approval/sandbox/deny <- decision
                                                       |
                                                       v
                                                  audit/report
```

The policy engine is authoritative. Actors request actions; integrations carry
requests; executors obey decisions. Neither an LLM nor a caller-provided trust
claim can override policy.

## Protected assets

Policy Scout is designed to protect:

- project source, manifests, lockfiles, and Git state;
- credential-adjacent files and environment variables;
- the host filesystem from destructive command forms;
- dependency-install workflows from unreviewed lifecycle behavior;
- the integrity and traceability of policy decisions and approvals.

## Primary threats

### Unsafe or ambiguous commands

Shell text can hide behavior behind pipes, chains, substitutions, nested shells,
or unfamiliar command families. Policy Scout preserves structural signals and
fails conservatively when it cannot classify a request confidently.

### Network-fetched execution

Commands such as `curl URL | bash` combine unreviewed network content with
immediate execution. Default policy denies this pattern rather than treating it
as an ordinary download.

### Package lifecycle execution

Package managers can download third-party code, mutate manifests and lockfiles,
and run lifecycle scripts. Supported npm, pnpm, yarn, and bun install forms are
routed to `SANDBOX_FIRST`.

### Credential-adjacent access

Reads targeting `.env`, package-manager credentials, SSH keys, or similar paths
receive the strongest default decision. Evidence is redacted before terminal,
audit, report, and JSON output.

### Destructive mutation

System-scoped destructive commands are denied. Project-local destructive
commands require approval when a stricter rule does not already apply.

### Approval confusion

An approval is valid once and only for its exact command and working directory.
Execution also checks status, scope, expiration, and the current policy result.
An approval cannot downgrade a current hard denial or sandbox requirement.

### Unsafe migration

Sandbox output is not copied wholesale. Migration accepts only package manifests
and package-manager lockfiles, refuses secret/config files and `node_modules`,
blocks high or critical findings, validates source/destination roots, and backs
up overwritten host files.

## Trust and failure rules

- Unknown does not mean safe.
- `check` never executes.
- `run` executes only `ALLOW` and `ALLOW_LOGGED`, or a still-valid one-time
  approval for a command that remains `REQUIRE_APPROVAL`.
- `DENY`, `DENY_AND_ALERT`, and `SANDBOX_FIRST` cannot be bypassed by approval.
- Safety-critical audit failure blocks risky execution.
- Sandbox failure prevents migration.
- Partial sweep failure is reported through `could_not_verify`; it is not
  converted into “no findings.”
- Project policy overrides may tighten decisions but cannot add allow rules.

## Local-first data boundary

Default durable state is under `~/.local/share/policy-scout/`:

- `audit.db` and `audit.jsonl`;
- `approvals.jsonl`;
- `reports/`, `sandboxes/`, `migrations/`, and `backups/`;
- `fossic.db` when the Fossic binding is available.

Policy Scout itself performs no silent remote upload. Remote threat intelligence
is opt-in through `--with-intel`. Package managers and commands submitted by a
user may independently use the network.

Fossic emission remains local. A separate relay process may copy selected events
to Lattica's local hub store; that relay is experimental and is not part of the
core enforcement path.

## Redaction model

Redaction uses explicit regular-expression patterns for common tokens, bearer
credentials, key material, environment assignments, CLI secret flags, and URL
query parameters. Canonical placeholders include:

```text
<redacted:possible_token>
<redacted:ssh_private_key>
<redacted:env_value>
```

This is defense in depth, not a proof that arbitrary secrets cannot leak.
Novel formats, encoded values, or contextual secrets may evade regex detection.
Users should still review reports before sharing them.

## Sandbox boundary

There are two distinct sandbox features:

1. Package-install review copies a small set of project files into a separate
   workspace, runs the requested package manager there, inspects lifecycle
   scripts, records diffs, and produces a report.
2. `sandbox-run` uses Linux namespaces and optional syscall tracing when host
   prerequisites permit it.

Neither is equivalent to a hardened VM, container security product, or malware
analysis laboratory. Kernel features, local tooling, and network configuration
determine the actual containment available.

## Out of scope

- perfect shell parsing or secret detection;
- antivirus, EDR, memory forensics, or packet inspection;
- protection from actions that bypass Policy Scout entirely;
- automatic quarantine, deletion, credential rotation, or remediation;
- remote multi-user authorization;
- treating inference quality or LLM content as action-policy authority.

## Reporting security issues

This repository does not yet publish a formal vulnerability disclosure process.
Until one exists, avoid filing raw credentials, private reports, or sensitive
audit records in public issues.
