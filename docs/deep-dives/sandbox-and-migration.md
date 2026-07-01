# Sandbox review and migration

Policy Scout has two sandbox concepts with different guarantees.

## Package-install review

The package workflow supports npm, pnpm, yarn, and bun. It:

1. classifies the install request through normal policy;
2. creates a separate workspace under the Policy Scout data root;
3. copies only the package manifest, relevant lockfile, and selected package
   manager configuration;
4. runs the requested package manager in that workspace;
5. inspects lifecycle scripts and package metadata;
6. captures manifest and lockfile changes;
7. persists a sandbox result and Scout Report.

The host project is not automatically mutated. Package-manager binaries must be
installed separately, and real installs may use the network.

This is a review workspace. It is useful for making install effects visible, but
it is not a strong malware-containment claim.

## Migration as a separate transaction

Migration consumes a persisted sandbox result rather than blindly copying a
directory. Before any host write it verifies:

- sandbox ID and result shape;
- workspace and recorded host root;
- migration availability and approval requirement;
- absence of high/critical findings;
- package-manager-specific allowlist membership;
- source and destination containment.

The common allowlist contains `package.json`; lockfiles are selected by package
manager. Forbidden content includes `node_modules`, `.env`, `.npmrc`, `.pnpmrc`,
`.yarnrc.yml`, and `bunfig.toml`.

Existing host files are copied into a migration-specific backup directory before
replacement. The CLI supports a dry-run plan, interactive confirmation, and an
explicit `--yes` route. Audit events record requested, planned, started,
completed, blocked, and failed states.

## General namespace sandbox

`sandbox-run` is a separate Linux-only experiment. It uses `unshare` namespaces,
scrubs the child environment, applies resource limits, optionally captures an
OverlayFS diff, and can analyze selected syscalls through `strace`.

Available protection depends on kernel configuration and host privileges.
`sandbox-check-prereqs` reports what can be used. The implementation must not be
described as equivalent to a hardened container or VM.

## Limits

- Package-install review can still execute untrusted lifecycle scripts inside a
  workspace with host-kernel access.
- Network isolation is not guaranteed by the package-manager review path.
- Private registry configuration remains credential-adjacent and requires care.
- Migration backup creation is rollback-aware, but there is no automated
  rollback command.
- Only supported package-manager manifests and lockfiles can be migrated.
