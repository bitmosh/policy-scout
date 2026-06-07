# Policy Scout — Sandbox Design

## 1. Purpose

The sandbox system lets Policy Scout analyze risky package installs before they mutate the real project.

The sandbox is not a perfect malware containment system in v0.1.

It is a safer review workspace that helps users inspect:

- manifest changes
- lockfile changes
- lifecycle scripts
- suspicious package behavior
- sweep findings
- migration risk

The initial sandbox should support package install review, not arbitrary command containment.

---

## 2. Sandbox Doctrine

The sandbox should be:

- local-first
- temporary
- explicit
- auditable
- non-mutating to the host project by default
- conservative about migration
- honest about limitations

Policy Scout should never imply that v0.1 sandboxing guarantees perfect containment.

---

## 3. Initial Scope

Sandbox v1 should focus on:

```text
npm install
npm i
pnpm add
yarn add
bun add
```

Optional later:

```text
npx
pnpm dlx
bunx
pip install
cargo install
go install
Docker-backed sandboxing
network-restricted sandboxing
```

---

## 4. Sandbox Flow

```text
SandboxRequested
  -> create temp workspace
  -> copy manifest files
  -> copy lockfiles
  -> run install command
  -> capture output
  -> inspect lifecycle scripts
  -> scan installed package metadata
  -> capture manifest/lockfile diff
  -> run sandbox sweep
  -> produce SandboxResult
  -> produce Scout Report
  -> require approval before migration
```

---

## 5. Host Project Protection

The sandbox must not mutate the host project automatically.

Host mutation should require explicit user approval.

Allowed host reads:

- package manifest
- lockfile
- package manager config where safe
- project metadata

Host writes:

- none by default
- report output to Policy Scout data directory
- migration only after approval

---

## 6. Temporary Workspace

The temp workspace should be isolated by path.

Example:

```text
~/.local/share/policy-scout/sandboxes/sbx_<id>/
```

or platform-appropriate cache/data path.

The workspace should include:

```text
package.json
package-lock.json / pnpm-lock.yaml / yarn.lock / bun.lockb
optional package manager config copies
install output logs
sandbox metadata
sandbox result
```

---

## 7. Files to Copy

For v0.1, copy only files needed for package install review.

Common files:

```text
package.json
package-lock.json
pnpm-lock.yaml
yarn.lock
bun.lockb
.npmrc when needed and safe
```

Be careful with `.npmrc` because it may contain tokens.

If `.npmrc` contains token-like values, prefer redacted copy or require explicit approval.

---

## 8. Package Manager Behavior

Policy Scout should detect package manager from:

- command
- lockfile
- project files
- user override

Examples:

```text
npm install lodash -> npm
pnpm add zod -> pnpm
yarn add react -> yarn
bun add package -> bun
```

The sandbox should run the same package manager requested, where available.

---

## 9. Lifecycle Script Inspection

The sandbox should inspect lifecycle scripts from package manifests.

Initial scripts of interest:

```text
preinstall
install
postinstall
prepack
prepare
prepublish
prepublishOnly
```

Suspicious script features:

- shell execution
- child process usage
- network fetch
- credential access
- environment variable enumeration
- obfuscation
- binary download
- chmod/chown
- shell profile modification
- persistence behavior

---

## 10. Diff Capture

The sandbox should capture changes to:

```text
package.json
package-lock.json
pnpm-lock.yaml
yarn.lock
bun.lockb
```

The report should show:

- which files changed
- dependency additions
- lockfile created/updated
- scripts added/changed
- package manager metadata changes

Do not migrate automatically.

---

## 11. Sandbox Result Object

Example:

```json
{
  "sandbox_id": "sbx_123",
  "request_id": "req_123",
  "command": "npm install lodash",
  "package_manager": "npm",
  "temp_workspace": "/path/to/sandbox",
  "exit_code": 0,
  "duration_ms": 2400,
  "manifest_changed": true,
  "lockfile_changed": true,
  "lifecycle_scripts_found": [],
  "findings": [],
  "migration_available": true,
  "migration_requires_approval": true
}
```

---

## 12. Migration

Migration should be explicit.

Potential command:

```bash
policy-scout sandbox migrate sbx_123
```

For v0.1, migration should only copy approved manifest/lockfile changes.

Do not migrate:

- `node_modules`
- generated scripts
- unknown binaries
- shell profile changes
- arbitrary files

Migration should write an audit event.

---

## 13. Sandbox Sweep

After install, run a sandbox sweep.

Initial checks:

- installed package manifests
- lifecycle scripts
- suspicious script content
- unexpected executables
- obfuscated JS patterns
- network fetch patterns
- credential-adjacent references
- workflow file changes if copied

Findings should feed into the Scout Report.

---

## 14. Limitations

Sandbox v1 limitations must be documented.

Potential limitations:

- temp directory is not a full security boundary
- install scripts may still access network
- private registry behavior may differ
- native builds may behave differently
- monorepos/workspaces are complex
- package manager cache may affect behavior
- environment variables may leak if not scrubbed
- not all malicious behavior can be detected statically

Policy Scout should phrase this honestly.

---

## 15. Environment Controls

Sandbox should reduce unnecessary exposure.

Recommended v0.1 controls:

- scrub sensitive environment variables where possible
- set clear sandbox cwd
- avoid copying secret files by default
- avoid reusing host `node_modules`
- capture command output
- record package manager version
- record OS/platform
- optionally disable scripts in an inspection mode

Potential future controls:

- Docker sandbox
- network restriction
- seccomp/profile-based containment
- read-only mounts
- package-manager cache isolation

---

## 16. Install Modes

Potential sandbox modes:

```text
normal_review
ignore_scripts_review
scripts_enabled_review
offline_if_possible
debug_keep_workspace
```

For v0.1, start simple:

```text
normal_review
debug_keep_workspace
```

Later, `ignore_scripts_review` can compare metadata without running lifecycle scripts.

---

## 17. Audit Events

Sandbox should emit events:

```text
SandboxRequested
SandboxWorkspaceCreated
SandboxInstallStarted
SandboxInstallCompleted
LifecycleScriptsInspected
SandboxSweepStarted
SandboxSweepCompleted
SandboxReportGenerated
SandboxMigrationRequested
SandboxMigrationApproved
SandboxMigrationCompleted
SandboxError
```

---

## 18. Failure Behavior

If sandbox fails:

- do not migrate
- preserve logs if possible
- produce failure report
- explain what was not verified
- recommend manual review

If sandbox finds high-risk behavior:

- do not migrate
- produce Scout Report
- recommend denial or manual review
- suggest credential rotation only if execution exposure may have occurred

---

## 19. Testing Requirements

Sandbox tests should verify:

- temp workspace creation
- manifest copy
- lockfile copy
- install execution in temp path
- host project not mutated
- lifecycle script detection
- diff capture
- report generation
- migration requires approval
- secrets are not printed
- failure behavior is safe

---

## 20. Sandbox Doctrine

The sandbox is a review mirror, not a magic shield.

It exists to move risky package behavior away from the real project long enough to inspect it, report on it, and require explicit approval before migration.
