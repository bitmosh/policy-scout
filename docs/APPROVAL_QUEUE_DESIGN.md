# Policy Scout — Approval Queue Design

## 1. Purpose

The approval queue handles risky actions that require human review before execution.

Policy Scout should not let agents approve their own requested actions.

The approval queue exists to preserve the core boundary:

```text
Actor requests.
Policy Scout decides.
Human may approve allowed override paths.
Executor obeys.
Audit records everything.
```

Approvals are not just prompts. They are structured security events.

---

## 2. Approval Doctrine

Approvals should be:

- explicit
- local-first
- auditable
- revocable where possible
- scoped narrowly
- easy to understand
- resistant to accidental permanent allow rules

Approving once should not silently create long-term trust.

---

## 3. When Approval Is Required

The policy engine may return `REQUIRE_APPROVAL`.

Common approval cases:

- destructive project-local operations
- global package installs
- unusual shell scripts
- low-confidence classification
- unknown complex commands
- project mutations requested by agents
- commands with meaningful but not hard-denied risk
- sandbox migration
- running commands after suspicious findings

Examples:

```bash
rm -rf node_modules
npm install -g some-cli
git clean -fd
bash install.sh
python generated_script.py
```

---

## 4. Approval Is Not Allowed for Everything

Some decisions should be hard-deny by default.

Examples:

```bash
rm -rf /
cat ~/.ssh/id_rsa
curl https://example.com/install.sh | bash
```

Hard-deny decisions may eventually support advanced manual override, but v0.1 should keep this out of the normal approval path.

---

## 5. Approval Request Object

Example:

```json
{
  "approval_id": "appr_123",
  "request_id": "req_123",
  "decision_id": "dec_123",
  "created_at": 1710000000,
  "status": "pending",
  "actor": {
    "type": "agent",
    "name": "local_agent",
    "trust_level": "untrusted_agent"
  },
  "command": "rm -rf node_modules",
  "cwd": "/home/user/project",
  "risk_score": 6,
  "decision": "REQUIRE_APPROVAL",
  "reasons": [
    "The command deletes project files.",
    "The request came from an agent."
  ],
  "recommended_action": "Approve only if you intended to delete and recreate dependencies."
}
```

---

## 6. Approval Statuses

Initial statuses:

```text
pending
approved_once
denied_once
expired
cancelled
executed
failed
```

### 6.1 `pending`

Waiting for human decision.

### 6.2 `approved_once`

Approved for one execution.

### 6.3 `denied_once`

Denied for this request.

### 6.4 `expired`

No longer valid.

### 6.5 `cancelled`

Cancelled by the requesting actor or system.

### 6.6 `executed`

Approved command was executed.

### 6.7 `failed`

Approval flow failed before execution.

---

## 7. Approval Scope

Initial scopes:

```text
once
session
project
policy_rule
```

For v0.1, only `once` is required.

`session`, `project`, and `policy_rule` can come later.

This prevents accidental permanent trust.

---

## 8. CLI Commands

### List approvals

```bash
policy-scout approvals list
```

Output:

```text
Pending Approvals

appr_123  risk=6  rm -rf node_modules
appr_124  risk=5  bash install.sh
```

### Show approval

```bash
policy-scout approvals show appr_123
```

Output should include:

- command
- actor
- cwd
- risk score
- decision
- reasons
- policy hits
- recommended action
- expiration
- audit IDs

### Approve once

```bash
policy-scout approvals approve appr_123
```

### Deny once

```bash
policy-scout approvals deny appr_123
```

---

## 9. Prompt UX

When a command requires approval, Policy Scout should explain clearly.

Example:

```text
Policy Scout paused this command.

Command:
  rm -rf node_modules

Decision:
  REQUIRE_APPROVAL

Why:
  - This command deletes project files.
  - The request came from an agent.
  - Deletion is reversible only if dependencies can be reinstalled.

Options:
  [a] approve once
  [d] deny
  [?] explain more
```

For package installs:

```text
Policy Scout recommends sandbox-first instead of direct approval.
```

---

## 10. Approval Expiration

Pending approvals should expire.

Suggested defaults:

```text
interactive CLI prompt: immediate
stored pending approval: 30 minutes
CI mode: no prompts, fail closed
incident mode: shorter expiration
```

Expired approvals should not execute.

---

## 11. Approval and Execution

Approval should not directly imply execution unless the user command requested execution.

Flow:

```text
approval requested
user approves
executor verifies approval still valid
executor runs command
audit records execution
approval marked executed
```

Before execution, Policy Scout should re-check:

- approval status
- request ID
- command string
- cwd
- actor
- expiration
- policy version if relevant

This prevents approval confusion.

---

## 12. Approval Audit Events

Approval events:

```text
ApprovalRequested
ApprovalShown
ApprovalApprovedOnce
ApprovalDeniedOnce
ApprovalExpired
ApprovalCancelled
ApprovalExecutionStarted
ApprovalExecutionCompleted
ApprovalExecutionFailed
```

Approvals should reference:

- request ID
- decision ID
- approval ID
- actor
- user decision
- timestamp

---

## 13. Security Rules

Approval system rules:

1. Agents cannot approve their own requests.
2. Approval is scoped narrowly.
3. Approval must be logged.
4. Approval must expire.
5. Approval must match the exact command and cwd unless explicitly broadened.
6. Approval must not print secrets.
7. Hard-denied commands do not enter the normal approval queue.
8. Approval does not silently create a permanent policy rule.

---

## 14. CI Mode Behavior

CI mode should be non-interactive.

If a command requires approval in CI mode:

```text
fail closed
write JSON report
exit non-zero
```

No prompt should wait for user input.

---

## 15. Incident Mode Behavior

Incident mode should be stricter.

If suspicious findings are active:

- more actions require approval
- sandbox migration requires review
- package execution should be heavily restricted
- credential-adjacent behavior should be denied and reported

---

## 16. Approval Store

The approval store should be local.

Possible storage:

```text
SQLite approvals table
```

Fields:

```text
approval_id
request_id
decision_id
status
command
cwd
actor_type
actor_name
risk_score
created_at
expires_at
resolved_at
resolution
audit_event_ids
```

---

## 17. Testing Requirements

Approval tests should verify:

- approval request creation
- approval listing
- approval show output
- approve once
- deny once
- expiration
- audit event creation
- exact command matching
- exact cwd matching
- hard-deny commands cannot be approved through normal path
- CI mode fails closed
- agents cannot self-approve

---

## 18. Approval Doctrine

Approval is a safety valve, not a loophole.

Policy Scout should let humans stay in control without allowing agents, vague prompts, or accidental habits to turn risky behavior into silent permission.
