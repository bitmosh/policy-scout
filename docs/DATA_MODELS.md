# Policy Scout — Data Models

## 1. Purpose

This document defines the canonical data models for Policy Scout.

The models should support:

- command requests
- granular evaluation
- policy decisions
- approvals
- sandbox results
- sweep findings
- audit events
- Scout Reports

Models should be stable, serializable, testable, and local-first.

---

## 2. Model Doctrine

Policy Scout models should be:

- explicit
- JSON-serializable
- versionable
- audit-friendly
- redaction-aware
- granular
- stable enough for agents to use

Every important object should have an ID.

---

## 3. ID Conventions

Suggested prefixes:

```text
req_     CommandRequest
eval_    EvaluationPacket
parse_   ParseResult
class_   ClassificationResult
dec_     PolicyDecision
risk_    RiskScore
appr_    ApprovalRequest
exec_    ExecutionResult
sbx_     SandboxResult
sweep_   SweepResult
find_    Finding
evt_     AuditEvent
report_  ScoutReport
```

IDs should be unique and locally generated.

---

## 4. Actor

Represents who or what requested an action.

```json
{
  "actor_id": "actor_local_agent",
  "type": "agent",
  "name": "local_agent",
  "trust_level": "untrusted_agent",
  "source": "cli"
}
```

Fields:

```text
actor_id
type
name
trust_level
source
metadata
```

Allowed actor types:

```text
human
agent
ide
cli
ci
unknown
```

---

## 5. CommandRequest

Represents a requested command or action.

```json
{
  "request_id": "req_123",
  "schema_version": 1,
  "timestamp": 1710000000,
  "actor": {
    "type": "agent",
    "name": "local_agent",
    "trust_level": "untrusted_agent"
  },
  "source": "cli",
  "command": "npm install lodash",
  "cwd": "/home/user/project",
  "declared_intent": "Install lodash dependency",
  "mode": "balanced"
}
```

Required fields:

```text
request_id
schema_version
timestamp
actor
source
command
cwd
mode
```

---

## 6. ParseResult

Represents parsed shell structure.

```json
{
  "parse_id": "parse_123",
  "request_id": "req_123",
  "success": true,
  "confidence": 0.92,
  "tokens": ["npm", "install", "lodash"],
  "primary_command": "npm",
  "args": ["install", "lodash"],
  "structure": {
    "has_pipe": false,
    "has_redirect": false,
    "has_chain_operator": false,
    "has_subshell": false,
    "has_command_substitution": false,
    "has_background_execution": false,
    "shell_complexity": 1
  },
  "warnings": []
}
```

---

## 7. ClassificationResult

Represents command classification.

```json
{
  "classification_id": "class_123",
  "request_id": "req_123",
  "command_family": "npm",
  "subcommand": "install",
  "categories": [
    "package_install"
  ],
  "capabilities": [
    "network.fetch",
    "filesystem.project_write",
    "package.install",
    "lifecycle.execute_possible"
  ],
  "classification_method": "registry_regex",
  "confidence": 0.96,
  "registry_hits": [
    {
      "registry": "command_registry",
      "id": "npm.install",
      "confidence": 0.96
    }
  ],
  "notes": [
    "npm install may execute lifecycle scripts"
  ]
}
```

---

## 8. ContextResult

Represents project and environment context.

```json
{
  "context_id": "ctx_123",
  "request_id": "req_123",
  "cwd_scope": "project",
  "project_root": "/home/user/project",
  "project_type": "node",
  "repo_detected": true,
  "lockfiles": [
    "package-lock.json"
  ],
  "sensitive_files_nearby": [
    ".env",
    ".npmrc"
  ],
  "os": "linux",
  "shell": "bash",
  "warnings": []
}
```

Sensitive files should be referenced by path, not read by default.

---

## 9. RegistryHit

Represents a registry match.

```json
{
  "registry": "default_policy",
  "id": "package_installs_sandbox_first",
  "confidence": 0.95,
  "matched_fields": [
    "category:package_install"
  ]
}
```

Registry hits should be preserved in evaluation packets and reports.

---

## 10. RiskScore

Represents granular risk scoring.

```json
{
  "risk_id": "risk_123",
  "request_id": "req_123",
  "risk_score": 7,
  "risk_band": "high",
  "components": {
    "package_install": 2,
    "network_fetch": 1,
    "lifecycle_script_possible": 2,
    "actor_trust_penalty": 1,
    "project_write": 1
  },
  "confidence": 0.91,
  "evidence_strength": 0.86,
  "notes": []
}
```

The final `risk_score` is a summary. Components are the source of truth.

---

## 11. PolicyDecision

Represents the final policy decision.

```json
{
  "decision_id": "dec_123",
  "request_id": "req_123",
  "decision": "SANDBOX_FIRST",
  "risk_score": 7,
  "confidence": 0.91,
  "category": "package_install",
  "policy_hits": [
    "package_installs_sandbox_first"
  ],
  "reasons": [
    "Package installs may execute lifecycle scripts.",
    "Package installs download third-party code.",
    "Package installs can modify manifests and lockfiles."
  ],
  "recommended_next_action": "Run sandbox analysis before host install.",
  "override_allowed": true,
  "requires_audit": true
}
```

Allowed decisions:

```text
ALLOW
ALLOW_LOGGED
REQUIRE_APPROVAL
SANDBOX_FIRST
DENY
DENY_AND_ALERT
```

---

## 12. EvaluationPacket

Represents the complete granular evaluation.

```json
{
  "evaluation_id": "eval_123",
  "request_id": "req_123",
  "schema_version": 1,
  "parse": {},
  "classification": {},
  "context": {},
  "registry_hits": [],
  "risk": {},
  "decision": {},
  "findings": [],
  "created_at": 1710000000
}
```

The evaluation packet should be referenced by audit events and Scout Reports.

---

## 13. ApprovalRequest

Represents a pending or resolved approval.

```json
{
  "approval_id": "appr_123",
  "request_id": "req_123",
  "decision_id": "dec_123",
  "created_at": 1710000000,
  "expires_at": 1710001800,
  "status": "pending",
  "scope": "once",
  "command": "rm -rf node_modules",
  "cwd": "/home/user/project",
  "risk_score": 6,
  "reasons": [
    "The command deletes project files."
  ]
}
```

Statuses:

```text
pending
approved_once
denied_once
expired
cancelled
executed
failed
```

---

## 14. ExecutionResult

Represents command execution result.

```json
{
  "execution_id": "exec_123",
  "request_id": "req_123",
  "decision_id": "dec_123",
  "command": "npm test",
  "cwd": "/home/user/project",
  "route": "direct",
  "started_at": 1710000000,
  "completed_at": 1710000042,
  "exit_code": 0,
  "duration_ms": 42000,
  "stdout_ref": "artifact_stdout_123",
  "stderr_ref": "artifact_stderr_123"
}
```

Do not store large raw output directly if it may contain secrets. Use references and redaction.

---

## 15. SandboxResult

Represents sandbox package install review.

```json
{
  "sandbox_id": "sbx_123",
  "request_id": "req_123",
  "command": "npm install lodash",
  "package_manager": "npm",
  "temp_workspace": "/home/user/.local/share/policy-scout/sandboxes/sbx_123",
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

## 16. SweepResult

Represents sweep execution.

```json
{
  "sweep_id": "sweep_123",
  "sweep_type": "project",
  "started_at": 1710000000,
  "completed_at": 1710000042,
  "project_root": "/home/user/project",
  "findings_count": {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4
  },
  "findings": [],
  "could_not_verify": [
    "system process list unavailable"
  ]
}
```

---

## 17. Finding

Represents a suspicious or informative finding.

```json
{
  "finding_id": "find_123",
  "sweep_id": "sweep_123",
  "severity": "high",
  "confidence": "moderate",
  "category": "suspicious_lifecycle_script",
  "title": "Package postinstall script invokes child_process",
  "location": "node_modules/example/package.json",
  "evidence_ref": "evidence_123",
  "why_it_matters": "Lifecycle scripts can execute arbitrary commands during install.",
  "recommended_action": "Review script before approving host install."
}
```

Severity and confidence must remain separate.

---

## 18. AuditEvent

Represents a durable event.

```json
{
  "event_id": "evt_123",
  "event_type": "DecisionIssued",
  "timestamp": 1710000000,
  "request_id": "req_123",
  "actor": {
    "type": "agent",
    "name": "local_agent"
  },
  "summary": "Policy decision issued for package install.",
  "data": {
    "decision": "SANDBOX_FIRST",
    "risk_score": 7,
    "policy_hits": [
      "package_installs_sandbox_first"
    ]
  }
}
```

Audit events should avoid raw secret values.

---

## 19. ScoutReport

Represents a human-readable and machine-readable report.

```json
{
  "report_id": "report_123",
  "report_type": "sandbox_result",
  "title": "Scout Report: Package Install Review",
  "created_at": 1710000000,
  "request_id": "req_123",
  "evaluation_id": "eval_123",
  "decision_id": "dec_123",
  "sandbox_id": "sbx_123",
  "findings": [],
  "audit_event_ids": [
    "evt_100",
    "evt_101",
    "evt_102"
  ],
  "markdown_path": "reports/report_123.md",
  "json_path": "reports/report_123.json"
}
```

---

## 20. Redaction Metadata

Objects that may contain sensitive text should support redaction metadata.

Example:

```json
{
  "redaction_applied": true,
  "redaction_notes": [
    "Token-like environment variable value redacted."
  ]
}
```

---

## 21. Schema Versioning

Every durable model should include a schema version where appropriate.

Recommended:

```text
schema_version: 1
```

Schema migrations can come later, but model versioning should start immediately.

---

## 22. Data Model Doctrine

The models are the spine of Policy Scout.

If the models are vague, the policy engine becomes vague.

If the policy engine is vague, the harness cannot be trusted.

Keep models explicit, granular, and auditable.
