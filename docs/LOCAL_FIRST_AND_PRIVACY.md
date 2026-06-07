# Policy Scout — Local-First and Privacy Design

## 1. Purpose

Policy Scout should be local-first by default.

This document defines what local-first means for Policy Scout and how privacy-sensitive data should be handled.

Policy Scout protects local development workflows. It should not require cloud services, remote dashboards, or hosted policy systems for core operation.

---

## 2. Local-First Doctrine

Policy Scout is local-first because durable state stays on the user's machine by default.

Local durable state includes:

- command requests
- policy decisions
- audit events
- approval history
- sandbox results
- Scout Reports
- local registries
- local policies
- sweep findings
- configuration

Network access may exist later as an optional capability, but it should not be required for v0.1.

---

## 3. Offline Capability

Policy Scout v0.1 should work offline for:

- command checking
- policy decisions
- registry matching
- local audit logging
- local package sandboxing where dependencies are already cached or install network is user-approved
- project sweeps
- report generation

Package installation itself may require network access because package managers often need registries. Policy Scout should distinguish between its own network needs and the command's network needs.

---

## 4. What Should Stay Local

The following should stay local by default:

```text
audit.db
audit.jsonl
Scout Reports
approval records
sandbox logs
sandbox result metadata
registry files
policy files
config files
sweep findings
```

No automatic remote upload in v0.1.

---

## 5. Optional Future Network Features

Future optional features may include:

- rule pack updates
- known malicious indicator updates
- vulnerability database lookup
- package reputation lookup
- remote policy pack download
- cloud backup
- team policy sync

These should be optional adapters, not core dependencies.

---

## 6. Privacy-Sensitive Data

Policy Scout may encounter sensitive data.

Examples:

- `.env`
- `.npmrc`
- SSH keys
- API keys
- package registry tokens
- cloud credentials
- shell history
- local file paths
- project names
- process command lines
- environment variables
- private package names

Policy Scout must avoid exposing this data unnecessarily.

---

## 7. Secret Redaction

Policy Scout should redact secrets in:

- terminal output
- audit logs
- Scout Reports
- JSON exports
- error messages
- sandbox logs where feasible

Redaction should prefer:

```text
<redacted:possible_token>
<redacted:ssh_private_key>
<redacted:env_value>
```

Policy Scout should preserve evidence location without printing secret values.

Good:

```text
Credential-adjacent file referenced: .env
```

Bad:

```text
OPENAI_API_KEY=sk-actual-value
```

---

## 8. Environment Variable Handling

Package installs and scripts may inherit environment variables.

Sandbox v1 should reduce exposure where feasible.

Recommended behavior:

- remove obvious secret environment variables from sandbox child process where possible
- log that environment was scrubbed
- allow user override for private registries when needed
- never print environment variable values
- record names of sensitive variables only if safe and useful

Examples of sensitive variable names:

```text
TOKEN
API_KEY
SECRET
PASSWORD
NPM_TOKEN
GITHUB_TOKEN
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
OPENAI_API_KEY
ANTHROPIC_API_KEY
```

---

## 9. `.npmrc` and Package Registry Tokens

`.npmrc` may contain tokens.

Policy Scout should be careful when copying `.npmrc` into a sandbox.

Possible behavior:

1. Detect token-like values.
2. Warn user.
3. Prefer redacted copy if possible.
4. Require explicit approval to copy token-bearing config.
5. Record decision in audit log.

Private registry installs may need credentials, so this cannot be handled with a blanket deny forever.

v0.1 should be conservative.

---

## 10. Local File Paths

Local file paths can reveal private information.

Policy Scout may need to show paths for evidence.

Guidance:

- show project-relative paths where possible
- avoid exposing home directory unnecessarily in reports
- include full paths only in local audit when useful
- allow future redaction setting for exported reports

---

## 11. Process Information

Quick system sweep may inspect processes.

Process command lines can include secrets.

Policy Scout should:

- avoid printing full command lines by default
- redact token-like substrings
- include PID/process name when useful
- include full command line only in verbose/debug mode with redaction

---

## 12. Audit Privacy

Audit logs are useful but sensitive.

They may contain:

- commands
- paths
- actor names
- package names
- findings
- process names
- approval history

Policy Scout should store audit logs locally and document their location.

Future export should warn users that exports may contain sensitive metadata.

---

## 13. Report Privacy

Scout Reports should be safe to share when possible, but not assumed public.

Reports should:

- redact secrets
- include evidence references
- avoid raw secret values
- explain what was redacted
- support JSON and Markdown
- eventually support a sanitized export mode

---

## 14. Sandbox Privacy

Sandbox logs may contain sensitive package manager output.

Policy Scout should:

- store sandbox logs locally
- redact obvious secrets
- avoid copying secret files by default
- require approval for token-bearing config
- delete sandbox workspace after report unless debug mode is enabled

---

## 15. Data Locations

Suggested Linux paths:

```text
~/.local/share/policy-scout/
~/.config/policy-scout/
~/.cache/policy-scout/
```

Possible layout:

```text
~/.config/policy-scout/config.yaml
~/.config/policy-scout/policies/
~/.local/share/policy-scout/audit.db
~/.local/share/policy-scout/reports/
~/.local/share/policy-scout/sandboxes/
~/.cache/policy-scout/tmp/
```

Platform-specific paths can be refined later.

---

## 16. Data Deletion

v0.1 should support basic local cleanup commands later.

Potential commands:

```bash
policy-scout data locations
policy-scout data prune --reports older-than:30d
policy-scout data export
policy-scout data delete-report report_123
```

Do not implement complex retention automation until audit requirements are stable.

---

## 17. Privacy and LLMs

If LLM explanation support is added later, it must follow strict boundaries.

LLMs should not receive:

- raw secrets
- private keys
- full `.env` contents
- unredacted credential files
- unnecessary command history
- full audit logs by default

LLMs may receive:

- redacted findings
- summarized evidence
- policy hits
- risk components
- report drafts

LLM use should be optional.

---

## 18. Privacy and Agent Integrations

Agents should receive the minimum information needed.

For a blocked command, an agent may receive:

```json
{
  "decision": "DENY",
  "reason": "Credential-adjacent file access is not allowed.",
  "allowed_next_actions": [
    "ask_user_for_manual_review",
    "request_non_secret_file"
  ]
}
```

Agents should not receive secret evidence.

---

## 19. Network Transparency

If Policy Scout itself uses network access in the future, it should disclose:

- destination
- purpose
- data sent
- data received
- whether result is cached
- whether user can disable it

No silent telemetry in v0.1.

---

## 20. Local-First Doctrine

Policy Scout's job is to protect local developer work without becoming another opaque remote dependency.

The user should be able to inspect:

- policies
- registries
- decisions
- audit events
- reports
- local data locations

Local-first is not just where data lives. It is the user's ability to understand and control the safety layer.
