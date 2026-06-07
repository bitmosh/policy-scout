# Policy Scout — Taxonomies

## 1. Purpose

This document defines the early taxonomies for Policy Scout.

Taxonomies should be stable, simple, and testable. They give the classifier, policy engine, sweep engine, audit log, and Scout Reports a shared language.

The goal is not to perfectly describe every possible command. The goal is to create a coherent baseline that can evolve through registries.

---

## 2. Actor Types

Actors request actions.

```text
human
agent
ide
cli
ci
unknown
```

### 2.1 `human`

A local human user directly requested the command.

### 2.2 `agent`

An AI agent requested the command or tool call.

### 2.3 `ide`

An IDE, editor plugin, or assistant integration requested the command.

### 2.4 `cli`

A CLI wrapper or script requested the command.

### 2.5 `ci`

A CI system requested the action.

### 2.6 `unknown`

The actor could not be confidently identified.

Unknown actors should be treated conservatively.

---

## 3. Actor Trust Levels

```text
trusted_local
known_tool
untrusted_agent
unknown_actor
ci_actor
```

Trust level should affect friction and review requirements, but it should not bypass hard safety rules.

---

## 4. Command Categories

Initial command categories:

```text
safe_read
local_inspection
project_write
package_install
package_execute
lifecycle_execute
network_fetch
network_execute
shell_script
credential_adjacent
system_mutation
destructive
persistence_mechanism
unknown
```

### 4.1 `safe_read`

Commands that read low-risk local data.

Examples:

```bash
ls
cat README.md
pwd
git status
```

### 4.2 `local_inspection`

Commands that inspect local state without intended mutation.

Examples:

```bash
ps aux
lsof -i
npm config list
```

### 4.3 `project_write`

Commands that modify project files.

Examples:

```bash
npm run format
python generate.py
touch new_file.py
```

### 4.4 `package_install`

Commands that add or install dependencies.

Examples:

```bash
npm install package
pnpm add package
yarn add package
bun add package
pip install package
```

Initial v0.1 focus should be npm/pnpm/yarn/bun. Python package managers can come later.

### 4.5 `package_execute`

Commands that execute package-provided tools, especially from remote or temporary sources.

Examples:

```bash
npx random-cli
pnpm dlx tool
bunx tool
```

### 4.6 `lifecycle_execute`

Commands or package scripts that may trigger lifecycle behavior.

Examples:

```bash
npm install
npm rebuild
npm run postinstall
```

Lifecycle execution matters because it can run arbitrary code.

### 4.7 `network_fetch`

Commands that fetch remote content.

Examples:

```bash
curl https://example.com/file.sh
wget https://example.com/file
```

### 4.8 `network_execute`

Commands that fetch remote content and execute it.

Examples:

```bash
curl https://example.com/install.sh | bash
wget -O- https://example.com/script.sh | sh
```

This is high risk and should usually be denied.

### 4.9 `shell_script`

Commands that execute local shell scripts or generated scripts.

Examples:

```bash
bash script.sh
sh install.sh
chmod +x script && ./script
```

### 4.10 `credential_adjacent`

Commands that access or may expose credentials, tokens, keys, or environment secrets.

Examples:

```bash
cat ~/.ssh/id_rsa
cat .env
grep -r "TOKEN" .
```

### 4.11 `system_mutation`

Commands that change system-level state.

Examples:

```bash
sudo apt install package
systemctl enable service
chmod -R 777 /usr/local
```

### 4.12 `destructive`

Commands that delete, overwrite, wipe, or heavily mutate files.

Examples:

```bash
rm -rf /
rm -rf ~
git clean -fdx
find . -type f -delete
```

### 4.13 `persistence_mechanism`

Commands or findings that suggest persistence.

Examples:

```bash
crontab modification
systemd user service creation
shell profile modification
startup script modification
```

### 4.14 `unknown`

Commands that cannot be confidently classified.

Unknown should not mean safe.

---

## 5. Capabilities

Capabilities describe what the command can do.

```text
filesystem.read
filesystem.project_write
filesystem.system_write
network.fetch
network.execute
package.install
package.execute
lifecycle.execute_possible
shell.execute
credential.access_possible
process.spawn
process.inspect
system.mutation
destructive.mutation
persistence.modify
```

Policies should prefer capability matching over command-name-only matching.

---

## 6. Decisions

Policy Scout decisions:

```text
ALLOW
ALLOW_LOGGED
REQUIRE_APPROVAL
SANDBOX_FIRST
DENY
DENY_AND_ALERT
```

### 6.1 `ALLOW`

The command may run without special logging beyond optional baseline telemetry.

### 6.2 `ALLOW_LOGGED`

The command may run, but the decision and execution should be logged.

### 6.3 `REQUIRE_APPROVAL`

The command must pause for explicit human approval.

### 6.4 `SANDBOX_FIRST`

The command should run in a sandbox or temporary workspace before host execution.

### 6.5 `DENY`

The command should not run.

### 6.6 `DENY_AND_ALERT`

The command should not run, and Policy Scout should alert the user or produce a Scout Report.

---

## 7. Risk Levels

Internal risk levels:

```text
R0 informational
R1 read-only local
R2 local inspection
R3 project-local write
R4 dependency or package metadata change
R5 package install or package execution
R6 lifecycle script execution possible
R7 network plus execution
R8 credential-adjacent or system mutation
R9 destructive or persistence-related
R10 known malicious or confirmed compromise
```

User-facing summaries may be simpler:

```text
low
medium
high
critical
```

---

## 8. Finding Severities

```text
info
low
medium
high
critical
```

### 8.1 `info`

Useful information, not suspicious by itself.

### 8.2 `low`

Mild concern or weak signal.

### 8.3 `medium`

Review recommended.

### 8.4 `high`

Suspicious behavior or meaningful exposure possibility.

### 8.5 `critical`

Confirmed dangerous behavior, likely credential exposure, destructive action, or known malicious indicator.

---

## 9. Finding Confidence

```text
low
moderate
high
confirmed
```

Severity and confidence are different.

A finding can be high severity but moderate confidence.

Example:

```text
Severity: high
Confidence: moderate
Reason: lifecycle script contains suspicious obfuscation pattern, but intent is not confirmed.
```

---

## 10. Finding Categories

Initial finding categories:

```text
known_bad_package
suspicious_lifecycle_script
secret_harvesting_pattern
network_exfiltration_pattern
workflow_injection
unexpected_open_port
suspicious_process
credential_file_access
repo_mutation
package_publish_risk
destructive_payload
persistence_mechanism
obfuscated_payload
suspicious_shell_profile_change
suspicious_package_manifest
unknown_suspicious_artifact
```

---

## 11. Enforcement Modes

```text
beginner
balanced
paranoid
ci
incident
```

### 11.1 `beginner`

More explanation, safer defaults, stronger guidance.

### 11.2 `balanced`

Default local developer mode.

### 11.3 `paranoid`

More approvals, more sandboxing, fewer silent allows.

### 11.4 `ci`

Non-interactive mode. Fail closed.

### 11.5 `incident`

Used after suspicious findings. Deny-heavy and report-focused.

---

## 12. Report Types

```text
command_decision
package_install_review
sandbox_result
project_sweep
system_quick_sweep
possible_credential_exposure
blocked_command
incident_summary
```

All report types should preserve evidence and uncertainty.

---

## 13. Evidence Types

```text
command
file_path
file_diff
package_manifest
lockfile_diff
process
open_port
script_content_excerpt
registry_match
policy_hit
audit_event
```

Secret values must be redacted.

Evidence should point to locations and references, not expose sensitive contents.

---

## 14. Default Command Examples

```text
ls
  category: safe_read
  decision: ALLOW

cat README.md
  category: safe_read
  decision: ALLOW

npm test
  category: local_inspection/project_execution
  decision: ALLOW_LOGGED

npm install react
  category: package_install
  decision: SANDBOX_FIRST

npm install -g some-cli
  category: package_install/system_mutation
  decision: REQUIRE_APPROVAL

npx unknown-tool
  category: package_execute
  decision: SANDBOX_FIRST

curl https://site/install.sh | bash
  category: network_execute
  decision: DENY

rm -rf node_modules
  category: destructive
  decision: REQUIRE_APPROVAL

rm -rf /
  category: destructive
  decision: DENY

cat ~/.ssh/id_rsa
  category: credential_adjacent
  decision: DENY_AND_ALERT
```

---

## 15. Taxonomy Doctrine

Taxonomies should be:

1. Human-readable.
2. Testable.
3. Registry-friendly.
4. Conservative under uncertainty.
5. Stable enough for agents to rely on.
6. Flexible enough to grow through rule packs.

When uncertain, Policy Scout should preserve uncertainty rather than flatten it into false confidence.
