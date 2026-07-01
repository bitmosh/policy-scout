# CLI reference

The installed entry point is `policy-scout`. Run `policy-scout --help` and
`policy-scout <command> --help` for the executable argument contract; this page
explains intent and maturity.

## Core policy path

| Command | Purpose | Maturity |
|---|---|---|
| `check -- <command>` | Classify and decide without execution | Core alpha |
| `run -- <command>` | Execute only through the policy gate | Core alpha |
| `approvals ...` | List, inspect, approve, deny, and configure expiry | Core alpha |
| `sandbox -- <install>` | Review npm/pnpm/yarn/bun installation effects | Core alpha |
| `sandbox <sbx_id>` | Preview or confirm allowlisted host migration | Core alpha |
| `policy ...` | Show, simulate, validate, and history-test policy | Alpha |

### Decisions and exit codes

| Decision | Direct execution | `check` exit |
|---|---:|---:|
| `ALLOW` | yes | 0 |
| `ALLOW_LOGGED` | yes, audited | 0 |
| `REQUIRE_APPROVAL` | no without a valid one-time approval | 10 |
| `SANDBOX_FIRST` | no | 10 |
| `DENY` | no | 20 |
| `DENY_AND_ALERT` | no | 20 |

Errors generally exit non-zero. Scripts should consume `--json` rather than
parsing human output.

### One-time approval flow

```bash
policy-scout run -- rm -rf build-output
policy-scout approvals show <approval_id>
policy-scout approvals approve <approval_id>
policy-scout run --approval <approval_id> -- rm -rf build-output
```

The final command must match the approval's command and working directory, the
approval must be unexpired and unused, and current policy must still return
`REQUIRE_APPROVAL`.

### Package review and migration

```bash
policy-scout sandbox -- pnpm add zod
policy-scout sandbox --dry-run <sbx_id>
policy-scout sandbox --yes <sbx_id>
policy-scout sandbox <sbx_id>
```

`--dry-run` previews migration. `--yes` confirms without an interactive prompt.
Plain migration asks interactively. These flags apply to migration, not package
installation.

## Evidence and diagnostics

| Command | Purpose | Maturity |
|---|---|---|
| `doctor` | Validate imports, versions, registries, storage, and optional tools | Core alpha |
| `eval run` | Execute the 44-case policy behavior oracle | Core alpha |
| `demo` | Run a safe local demonstration | Alpha |
| `audit ...` | Query SQLite audit history and verify the JSONL chain | Core alpha |
| `report ...` | List, show, and export redacted Scout Reports | Core alpha |
| `data status` | Show local state locations and counts | Alpha |
| `data cleanup` | Preview or apply cleanup for allowlisted temporary data | Alpha |

Cleanup supports only `demo`, `sandbox`, and `sandbox-results`. Destructive
cleanup requires `--apply`; `--yes` skips its confirmation. Audit, approvals,
reports, migrations, and backups are not cleanup targets.

## Scanning and repository controls

| Command | Purpose | Maturity |
|---|---|---|
| `sweep project` | Inspect project scripts, workflows, executables, code patterns, credentials, and Git changes | Core alpha |
| `sweep quick` | Inspect Linux ports, processes, profiles, temp files, package config, and environment names | Alpha, Linux-first |
| `scan dir|file` | Detect configured secret patterns and optional entropy signals | Alpha |
| `scan staged|history` | Scan staged files or Git history | Alpha |
| `scan injection` | Detect configured prompt-injection patterns | Experimental |
| `git context` | Show repository context | Alpha |
| `git staged-check` | Combine staged secret and workflow checks | Alpha |
| `git lockfile-check` | Inspect lockfile changes against a Git ref | Alpha |
| `git hooks ...` | Install, remove, or inspect the Policy Scout pre-commit hook | Alpha; mutates `.git/hooks` |
| `canary ...` | Install, inspect, or remove a prompt-injection canary file | Experimental; mutating |

Findings are evidence, not proof of compromise. Severity and confidence remain
separate, and failed checks appear under `could_not_verify`.

## Experimental and environment-dependent commands

| Command | Purpose | Important constraint |
|---|---|---|
| `sandbox-run` | Run a command in Linux user/mount/PID/network namespaces | Requires compatible `unshare`; optional `strace`/OverlayFS |
| `sandbox-check-prereqs` | Report general sandbox prerequisites | Diagnostic only |
| `intel status|clear-cache|evict-expired` | Inspect or maintain the remote-intel cache | `check --with-intel` is the network-using path |
| `check --with-intel` | Enrich a check with OSV/npm advisory data | Explicit network use |
| `watch start|status|stop` | Monitor configured filesystem paths | Linux/system-tool dependent |
| `integrity check` | Verify registry hashes | Detects mismatch; does not repair |
| `integrity update-manifest` | Regenerate the integrity manifest | Developer mutation command |
| `lockdown ...` | Force policy into deny-by-default incident posture | Persists local posture state |
| `preserve` | Capture an evidence archive | May contain sensitive metadata |
| `clearance` | Run post-incident checks | Advisory; not proof of safety |
| `serve` | Run or register the stdio MCP server | Local experimental adapter |

## Machine-readable output

Major read and decision commands support `--json`. Stable fields are covered by
tests and, for desktop consumers, JSON schemas under
`ui/desktop/src/contracts/`. Decision exits remain meaningful even when valid
JSON is written; callers must accept exit 10 and 20 for risky/denied checks.

## State isolation

Tests and automation should override durable paths. See
[Installation and development](INSTALL.md#isolated-state) for the complete list.
