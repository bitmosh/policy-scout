# Policy Scout — Agent Handoff

## 1. Purpose

This document gives instructions to AI agents working on Policy Scout.

Agents should treat Policy Scout as a clean-room security tool.

Do not port Bons.ai directly.

Use Bons.ai only as a source of useful control patterns.

---

## 2. Project Identity

Project name:

```text
Policy Scout
```

One-liner:

```text
Policy Scout is a local-first safety harness for agent commands, package installs, and suspicious project activity.
```

Short tagline:

```text
Policy Scout: light armor for fast agents.
```

---

## 3. Core Doctrine

Policy Scout is policy-centered, not agent-centered.

```text
Actors request.
Policy Scout classifies.
Policy Scout decides.
Executors obey.
Audit records everything.
```

Agents may request actions. Agents do not govern.

---

## 4. Non-Negotiable Rules

Agents working on this project must follow these rules:

1. Do not make LLMs the final policy authority.
2. Do not give agents direct unrestricted shell execution.
3. Do not hide policy logic in scattered code.
4. Do not silently weaken safety rules.
5. Do not auto-approve risky commands.
6. Do not print secrets into logs or reports.
7. Do not treat unknown commands as safe.
8. Do not build integrations before the CLI core works.
9. Do not build autonomous remediation in v0.1.
10. Do not mutate host projects from sandbox without explicit approval.

---

## 5. Required Reading

Before implementation work, read:

```text
PROJECT_SCOPE.md
ARCHITECTURE.md
TAXONOMIES.md
POLICY_DESIGN.md
EVALUATION_GRANULARITY.md
MVP_SPEC.md
IMPLEMENTATION_PLAN.md
TESTING_STRATEGY.md
```

For subsystem work, also read the relevant subsystem doc.

---

## 6. Bons.ai Pattern Guidance

Useful Bons.ai patterns:

- pure decision controller
- mode persistence
- granular metrics
- confidence and signal scoring
- structured event logging
- tool usage accounting
- adaptive behavior only for non-critical optimization

Do not port:

- agent-centered main loop
- idea-generation agents
- mutation manager
- old memory/vector store
- freeform tool-call parsing
- ungoverned adaptive decisions

Policy Scout needs security-specific models and deterministic policy authority.

---

## 7. Implementation Priorities

Build in order:

```text
1. models
2. parser
3. classifier
4. registry loader
5. registry validator
6. risk scorer
7. policy engine
8. check CLI
9. audit store
10. run wrapper
11. approval queue
12. sandbox install
13. sweep engine
14. reports
15. integrations
```

Do not jump ahead to integrations.

---

## 8. Granular Evaluation Requirement

Every critical action must preserve granular evaluation data.

Do not only return:

```text
risk = 7
```

Return:

```text
parse confidence
classification confidence
categories
capabilities
registry hits
risk components
policy hits
decision reasons
evidence strength
```

The clutch and audit layers depend on granular signals.

---

## 9. Testing Requirements

Every new behavior needs tests.

At minimum, update relevant tests for:

- parser behavior
- classifier behavior
- registry validation
- policy decision
- risk components
- audit event
- report output
- secret redaction
- fail-safe behavior

Security-relevant bug fixes require regression tests.

---

## 10. Fail-Safe Guidance

When uncertain, fail safely.

Examples:

```text
parser fails -> require approval or deny depending on risk
registry invalid -> block risky execution
policy engine error -> do not run risky commands
audit write fails -> do not run risky commands
sandbox fails -> do not migrate
sweep incomplete -> report what was not verified
```

---

## 11. LLM Usage Boundary

LLMs may help with:

- writing explanations
- summarizing findings
- drafting reports
- suggesting safer alternatives

LLMs may not:

- approve commands
- override policies
- rewrite policy files silently
- hide findings
- receive raw secrets
- execute commands directly

---

## 12. Privacy Rules

Agents must avoid exposing secrets.

Never intentionally print raw:

- `.env` values
- API keys
- npm tokens
- GitHub tokens
- cloud credentials
- SSH private keys
- private package credentials

Use redacted placeholders and evidence references.

---

## 13. Integration Rules

Integrations may submit requests.

Integrations may not bypass policy.

Future integrations should preserve:

- actor identity
- command text
- cwd
- request source
- policy decision
- audit events

---

## 14. Coding Style Guidance

Prefer:

- small pure functions
- explicit data models
- typed structures where possible
- simple registries
- readable policy matching
- clear errors
- conservative defaults
- tests near behavior

Avoid:

- hidden globals
- broad mutation
- scattered conditionals
- magic strings outside taxonomies
- freeform LLM tool parsing
- silent failure
- broad exception swallowing

---

## 15. Definition of Good Work

A good Policy Scout change:

1. Preserves the policy-centered boundary.
2. Adds or updates tests.
3. Preserves granular evaluation data.
4. Writes audit events where needed.
5. Redacts secrets.
6. Keeps behavior local-first.
7. Updates docs if it changes architecture, taxonomy, policy, or CLI behavior.

---

## 16. Agent Handoff Doctrine

Policy Scout is light armor for fast agents.

Do not make it heavy.

Do not make it porous.

Make it inspectable, local, disciplined, and trustworthy.
