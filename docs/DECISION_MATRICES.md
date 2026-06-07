# Policy Scout — Decision Matrices

## 1. Purpose

This document collects practical matrices that can be used for implementation, tests, README docs, and visual aids.

Matrices are useful because they show defaults clearly without hiding nuance.

The policy engine still uses granular evaluation packets, registry hits, risk components, and context. These matrices are summaries, not replacements for policy logic.

---

## 2. Command Category Decision Matrix

| Command Category | Example | Core Capabilities | Default Risk Band | Default Decision | Notes |
|---|---|---|---|---|---|
| `safe_read` | `ls`, `pwd`, `cat README.md` | `filesystem.read` | low | `ALLOW` | Safe only when not credential-adjacent. |
| `local_inspection` | `git status`, `ps aux` | `filesystem.read`, `process.inspect` | low-medium | `ALLOW_LOGGED` | Process output may contain sensitive metadata. |
| `project_write` | `touch file.py`, formatters | `filesystem.project_write` | medium | `REQUIRE_APPROVAL` or `ALLOW_LOGGED` | Depends on actor and project context. |
| `package_install` | `npm install lodash` | `network.fetch`, `package.install`, `filesystem.project_write`, `lifecycle.execute_possible` | high | `SANDBOX_FIRST` | Package installs are untrusted by default. |
| `package_execute` | `npx unknown-tool` | `network.fetch`, `package.execute`, `shell.execute` | high | `SANDBOX_FIRST` | Often riskier than install. |
| `lifecycle_execute` | `npm rebuild`, `postinstall` | `shell.execute`, `lifecycle.execute` | high | `REQUIRE_APPROVAL` or `DENY` | Depends on script content and context. |
| `network_fetch` | `curl https://site/file.sh` | `network.fetch` | medium | `REQUIRE_APPROVAL` | Fetching is not the same as executing. |
| `network_execute` | `curl URL \| bash` | `network.fetch`, `shell.execute` | severe | `DENY` | Deny by default. |
| `shell_script` | `bash install.sh` | `shell.execute` | medium-high | `REQUIRE_APPROVAL` | Inspect script where possible. |
| `credential_adjacent` | `cat ~/.ssh/id_rsa`, `cat .env` | `credential.access_possible` | severe-critical | `DENY_AND_ALERT` | Never expose secrets to agents. |
| `system_mutation` | `systemctl enable`, `sudo apt install` | `filesystem.system_write`, `system.mutation` | severe | `REQUIRE_APPROVAL` or `DENY` | v0.1 should be conservative. |
| `destructive` | `rm -rf /`, `git clean -fdx` | `destructive.mutation` | high-critical | `REQUIRE_APPROVAL` or `DENY` | Project-local may be approvable; system destructive should deny. |
| `persistence_mechanism` | crontab/service/profile modification | `persistence.modify` | severe | `DENY_AND_ALERT` | Especially suspicious when agent-requested. |
| `unknown` | unrecognized complex shell | unknown | medium-high | `REQUIRE_APPROVAL` or `DENY` | Unknown does not mean safe. |

---

## 3. Decision Severity Ladder

| Decision | Meaning | Friction Level | Execution Allowed? | Audit Required? |
|---|---|---:|---|---|
| `ALLOW` | Safe enough to run. | 0 | Yes | Optional |
| `ALLOW_LOGGED` | Allowed but worth recording. | 1 | Yes | Yes |
| `REQUIRE_APPROVAL` | Human must approve. | 2 | Only after approval | Yes |
| `SANDBOX_FIRST` | Analyze away from host first. | 3 | Not directly on host | Yes |
| `DENY` | Do not run. | 4 | No | Yes |
| `DENY_AND_ALERT` | Do not run; warn/report. | 5 | No | Yes |

---

## 4. Severity vs Confidence Matrix

Severity describes potential impact. Confidence describes certainty.

| Severity \ Confidence | Low | Moderate | High | Confirmed |
|---|---|---|---|---|
| `info` | Mention quietly | Mention quietly | Mention normally | Mention normally |
| `low` | Optional review | Review if nearby risk exists | Review recommended | Review recommended |
| `medium` | Review recommended | Review recommended | Strong review | Strong review |
| `high` | Caution, explain uncertainty | Strong review | Block/make report likely | Block/report |
| `critical` | Treat cautiously, require review | Block/report | Block/report | Block/report + incident guidance |

Important rule:

```text
High severity + moderate confidence is still important.
Low confidence should not hide high potential impact.
```

---

## 5. Enforcement Mode Matrix

| Mode | Intended Use | Approval Behavior | Sandbox Behavior | Deny Behavior | Report Verbosity | Interactivity |
|---|---|---|---|---|---|---|
| `beginner` | Newer users / extra guidance | More prompts and explanation | Strongly recommended | Calm, educational | High | Interactive |
| `balanced` | Default local developer mode | Moderate | Package installs sandbox-first | Normal | Medium | Interactive |
| `paranoid` | Sensitive projects / high caution | More approvals | More sandboxing | Stricter | High | Interactive |
| `ci` | Automation | No prompts, fail closed | Only if explicitly configured | Strict | JSON-friendly | Non-interactive |
| `incident` | After suspicious finding | Heavy review | Migration restricted | Deny-heavy | High | Interactive or report-first |

---

## 6. Actor Trust Matrix

| Actor Type | Trust Default | Safe Read | Package Install | Credential Access | Destructive Command |
|---|---|---|---|---|---|
| `human` | trusted_local | `ALLOW` | `SANDBOX_FIRST` | `DENY_AND_ALERT` | approval/deny based on scope |
| `agent` | untrusted_agent | `ALLOW` or `ALLOW_LOGGED` | `SANDBOX_FIRST` | `DENY_AND_ALERT` | usually `DENY` or `REQUIRE_APPROVAL` |
| `ide` | known_tool | `ALLOW_LOGGED` | `SANDBOX_FIRST` | `DENY_AND_ALERT` | approval/deny |
| `cli` | known_tool or unknown | depends | `SANDBOX_FIRST` | `DENY_AND_ALERT` | approval/deny |
| `ci` | ci_actor | allow/log if configured | fail/sandbox/report | deny | fail closed |
| `unknown` | unknown_actor | `ALLOW_LOGGED` | `REQUIRE_APPROVAL` or `SANDBOX_FIRST` | `DENY_AND_ALERT` | deny/approval |

Actor trust affects friction, not hard safety rules.

---

## 7. Risk Component Matrix

| Component | Typical Source | Weight Range | Notes |
|---|---|---:|---|
| `parse_uncertainty` | parser confidence | 0-2 | Complex shell should increase risk. |
| `classification_uncertainty` | classifier confidence | 0-2 | Unknown does not mean safe. |
| `actor_trust_penalty` | actor type/trust | 0-2 | Agent/unknown actors get more friction. |
| `package_install` | command category | 2 | Package installs are untrusted. |
| `package_execution` | npx/dlx/bunx | 3 | Remote execution risk. |
| `lifecycle_script_possible` | package manager behavior | 2 | Install scripts can run code. |
| `network_fetch` | curl/wget/package install | 1 | Fetch alone is lower than execute. |
| `network_execution` | curl pipe shell | 4 | Deny by default. |
| `project_write` | file mutation | 1 | Often legitimate but should be visible. |
| `system_write` | system-level mutation | 3 | Requires strong review. |
| `credential_adjacency` | secret-like file/path | 4 | Usually deny/alert. |
| `destructive_potential` | rm/git clean/delete | 4 | Scope matters. |
| `persistence_potential` | startup/services/profile | 4 | Suspicious in agent context. |
| `sandbox_unavailable` | sandbox check | 1-2 | Raises friction if sandbox-first cannot run. |
| `known_bad_indicator` | indicator registry | 10 | Critical. |
| `suspicious_pattern` | sweep/pattern registry | 1-5 | Severity/context dependent. |
| `incident_context` | active incident mode | 1-3 | Raises friction during incident. |

---

## 8. Report Type Matrix

| Report Type | Trigger | Main Audience | Format | Required Sections |
|---|---|---|---|---|
| `command_decision` | command checked/blocked | human + agent | Markdown/JSON | command, decision, reasons, risk |
| `package_install_review` | sandbox package install | developer | Markdown/JSON | diff, lifecycle scripts, findings |
| `sandbox_result` | sandbox completed | developer | Markdown/JSON | command, result, findings, migration |
| `project_sweep` | project sweep | developer | Markdown/JSON | findings, evidence, recommendations |
| `system_quick_sweep` | quick sweep | developer | Markdown/JSON | processes, ports, limitations |
| `possible_credential_exposure` | credential risk | developer | Markdown/JSON | evidence, exposure assessment, next steps |
| `blocked_command` | deny/alert | human + agent | Markdown/JSON | command, deny reason, safer alternatives |
| `incident_summary` | high/critical findings | developer | Markdown/JSON | timeline, findings, guidance |

---

## 9. Matrix Doctrine

Matrices are useful for clarity, but they are not the policy engine.

The policy engine should still read:

```text
evaluation packet
registry hits
risk components
actor context
project context
enforcement mode
```

The matrices help humans and agents understand default behavior.
