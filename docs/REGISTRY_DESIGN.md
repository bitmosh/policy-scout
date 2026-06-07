# Policy Scout — Registry Design

## 1. Purpose

Policy Scout should be registry-first.

Command knowledge, policy rules, suspicious indicators, and recommended controls should live in data registries rather than scattered hardcoded conditionals.

This supports:

- maintainability
- transparency
- community rule packs
- testability
- local-first operation
- agent-readable policy context
- future LumaWeave/Cerebra visualization or memory integration

---

## 2. Registry Doctrine

Registries are policy data, not hidden code.

A registry entry should be:

1. Human-readable.
2. Versioned.
3. Testable.
4. Explainable.
5. Locally available.
6. Safe to inspect.
7. Schema-validated.
8. Conservative by default.

Registry changes should be auditable.

---

## 3. Initial Registry Types

Policy Scout v0.1 should define these registries:

```text
command_registry.yaml
default_policy.yaml
suspicious_patterns.yaml
indicator_registry.yaml
```

Later registries may include:

```text
package_manager_registry.yaml
report_templates.yaml
control_recommendations.yaml
mode_profiles.yaml
trusted_projects.yaml
community_rule_packs.yaml
```

---

## 4. Command Registry

The command registry defines known command families and command patterns.

Example:

```yaml
version: 1

commands:
  - id: npm.install
    title: npm install
    description: Installs npm dependencies and may execute lifecycle scripts.
    match:
      command_regex: "^(npm)\\s+(install|i)\\b"
    categories:
      - package_install
    capabilities:
      - network.fetch
      - filesystem.project_write
      - package.install
      - lifecycle.execute_possible
    default_risk: R5
    recommended_controls:
      - sandbox_first
      - inspect_lifecycle_scripts
      - audit_log
```

Command registry entries should not directly execute anything.

They describe behavior and risk.

---

## 5. Policy Registry

The policy registry maps conditions to decisions.

Example:

```yaml
version: 1

policies:
  - id: package_installs_sandbox_first
    title: Package installs should run in sandbox first
    priority: 500
    match:
      categories:
        - package_install
    decision: SANDBOX_FIRST
    reasons:
      - Package installs may execute third-party code.
      - Package installs can modify manifests and lockfiles.
    recommended_next_action: Run sandbox analysis before host install.

  - id: curl_pipe_shell_deny
    title: Deny network-fetched shell execution
    priority: 900
    match:
      categories:
        - network_execute
    decision: DENY
    reasons:
      - Network-fetched scripts piped directly into a shell are unsafe.
      - The fetched script may change between review and execution.
    recommended_next_action: Download and inspect the script manually if truly required.
```

Higher-priority policies should override lower-priority policies.

Deny policies should generally have high priority.

---

## 6. Suspicious Pattern Registry

The suspicious pattern registry defines known suspicious patterns for project and sandbox scanning.

Example:

```yaml
version: 1

patterns:
  - id: js.child_process_in_lifecycle
    title: Lifecycle script invokes child_process
    category: suspicious_lifecycle_script
    severity: high
    confidence: moderate
    languages:
      - javascript
    match:
      regex: "require\\(['\\\"]child_process['\\\"]\\)"
    why_it_matters: Lifecycle scripts can execute arbitrary child processes during install.
    recommended_action: Review the package before approving host install.
```

Patterns should avoid claiming compromise unless the indicator is confirmed.

---

## 7. Indicator Registry

The indicator registry tracks known suspicious or malicious indicators.

Example:

```yaml
version: 1

indicators:
  - id: known_bad_package.example
    title: Known suspicious package
    category: known_bad_package
    severity: critical
    confidence: confirmed
    match:
      package_name: "example-bad-package"
      ecosystem: npm
    why_it_matters: This package matches a known malicious indicator.
    recommended_action: Do not install. Review project for compromise and rotate exposed credentials if executed.
```

Indicator registries should support local updates later, but v0.1 can ship with static local files.

---

## 8. Registry Matching

Registry matching should produce structured hits.

Example:

```json
{
  "registry_hits": [
    {
      "registry": "command_registry",
      "id": "npm.install",
      "confidence": 0.96
    },
    {
      "registry": "default_policy",
      "id": "package_installs_sandbox_first",
      "confidence": 0.95
    }
  ]
}
```

These hits should be stored in the evaluation packet and referenced in Scout Reports.

---

## 9. Registry Entry Fields

Recommended common fields:

```yaml
id: string
title: string
description: string
version: integer
status: active | deprecated | experimental
category: string
severity: info | low | medium | high | critical
confidence: low | moderate | high | confirmed
match: object
reasons: list
recommended_controls: list
recommended_action: string
references: list
```

Not every registry type needs every field.

---

## 10. Match Types

Supported match types should start simple.

Initial match types:

```text
command_regex
argv_prefix
exact_command
category
capability
file_path_regex
package_name
script_name
content_regex
process_name
port
```

Complex shell syntax should be treated conservatively.

---

## 11. Policy Priority

Policies should have numeric priority.

Suggested ranges:

```text
0-199    informational or low-friction rules
200-399  logging rules
400-599  approval and sandbox rules
600-799  high-risk controls
800-999  deny and alert rules
```

When multiple policies match:

1. Highest severity wins.
2. Higher priority wins.
3. Deny beats approval.
4. Approval beats allow.
5. Sandbox beats direct allow.
6. All policy hits are still recorded.

---

## 12. Registry Validation

All registries should be schema-validated before use.

Validation should check:

- required fields
- unique IDs
- valid categories
- valid decisions
- valid severity values
- valid confidence values
- valid regex patterns
- no unknown capability names
- no duplicate priority collisions where forbidden

If validation fails, Policy Scout should fail safe for risky commands.

---

## 13. Registry Testing

Registries should have tests.

Example tests:

```text
npm install react -> npm.install
pnpm add zod -> pnpm.add
curl url | bash -> network_execute
rm -rf / -> destructive
cat README.md -> safe_read
```

Policy tests should verify:

```text
package_install -> SANDBOX_FIRST
network_execute -> DENY
credential_adjacent -> DENY_AND_ALERT
safe_read -> ALLOW
unknown_complex_command -> REQUIRE_APPROVAL or DENY
```

Tests should verify both final decisions and granular registry hits.

---

## 14. Local-First Registry Updates

Policy Scout should ship with built-in registries.

Future update model:

1. Local bundled registries.
2. User custom registries.
3. Optional downloaded rule packs.
4. Optional signed community packs.
5. Optional organization-specific packs.

Remote registries should never be required for core local operation.

---

## 15. User Custom Registries

Users should eventually be able to add local custom rules.

Example:

```yaml
version: 1

policies:
  - id: local.no_global_npm_installs
    title: Require approval for global npm installs
    priority: 700
    match:
      command_regex: "^npm\\s+install\\s+-g\\b"
    decision: REQUIRE_APPROVAL
    reasons:
      - Global installs modify user-level or system-level tool state.
```

Custom registry errors should be clear and actionable.

---

## 16. Registry Security

Registries influence security decisions, so they must be treated carefully.

Security rules:

1. Registries should not execute code.
2. Registries should be schema-validated.
3. Registry updates should be logged.
4. Remote rule packs should eventually be signed or checksum-verified.
5. User custom rules should be visibly identified.
6. Deprecated rules should not silently disappear from audit context.

---

## 17. Registry and Scout Reports

Scout Reports should include relevant registry and policy hits.

Example:

```text
Policy hits:
- package_installs_sandbox_first
- agent_package_installs_require_review

Command registry:
- npm.install

Recommended controls:
- sandbox_first
- inspect_lifecycle_scripts
- audit_log
```

This makes decisions explainable and testable.

---

## 18. Registry Doctrine

Policy Scout should not hide security logic in scattered code.

If a behavior can be expressed as a stable rule, taxonomy, command family, indicator, or recommended control, it should probably live in a registry.

Code should provide the engine.

Registries should provide the evolving knowledge.
