# Policy Scout Evaluation Granularity

## 1. Core Rule

Policy Scout must evaluate granular steps, not lump-sum processes.

A command should not receive only one vague score such as:

```text
npm install unknown-lib -> risk 7/10
```

Instead, Policy Scout should decompose the action into smaller evaluable units:

```text
command family detected -> package install
package source -> external registry
lifecycle script possibility -> yes
project mutation -> package manifest and lockfile
network access -> required
credential adjacency -> possible
sandbox availability -> yes
rollback path -> partial
actor trust -> agent/untrusted
policy match -> sandbox_first
```

This improves:

- policy precision
- clutch behavior
- audit clarity
- Scout Report quality
- false-positive handling
- later learning and tuning

---

## 2. Why Granularity Matters

The clutch cannot work well if it only receives lump-sum outcomes.

A lump-sum score hides important differences:

```text
risk 7/10 because of lifecycle scripts
risk 7/10 because of credential access
risk 7/10 because of destructive filesystem mutation
risk 7/10 because the classifier is uncertain
```

Those are not the same situation.

Policy Scout should preserve the small signals that led to the final decision.

---

## 3. Evaluation Layers

Policy Scout should evaluate at these layers:

1. Parse layer
2. Command classification layer
3. Capability layer
4. Actor layer
5. Context layer
6. Policy match layer
7. Risk scoring layer
8. Decision layer
9. Execution layer
10. Sweep/finding layer

---

## 3.1 Parse Layer

Questions:

- Did the command parse cleanly?
- Is shell syntax simple or complex?
- Are pipes, redirects, subshells, or chained commands present?
- Are there quoted or escaped segments?
- Is there hidden execution behavior?

Possible fields:

```json
{
  "parse_success": true,
  "parse_confidence": 0.92,
  "shell_complexity": 2,
  "has_pipe": false,
  "has_subshell": false,
  "has_redirect": false,
  "has_chain_operator": false
}
```

---

## 3.2 Command Classification Layer

Questions:

- What command family is this?
- Is it read-only, project-writing, package-installing, network-fetching, destructive, or unknown?
- Was classification exact, regex-based, heuristic, or fallback?

Possible fields:

```json
{
  "command_family": "npm",
  "command_category": "package_install",
  "classification_method": "registry_regex",
  "classification_confidence": 0.96
}
```

---

## 3.3 Capability Layer

Questions:

What capabilities does this command imply?

Capabilities may include:

- local read
- project write
- system write
- network fetch
- package install
- lifecycle execution
- shell execution
- credential-adjacent access
- process inspection
- process creation
- destructive mutation

Possible fields:

```json
{
  "capabilities": {
    "filesystem.project_write": true,
    "network.fetch": true,
    "package.install": true,
    "lifecycle.execute_possible": true,
    "credential.access_possible": false,
    "system.mutation": false
  }
}
```

---

## 3.4 Actor Layer

Questions:

- Who requested the action?
- Is the actor a human, agent, IDE, CI job, or unknown caller?
- Has this actor made risky requests recently?
- Is this actor allowed to request this capability?

Possible fields:

```json
{
  "actor_type": "agent",
  "actor_name": "local_agent",
  "actor_trust": "untrusted_agent",
  "recent_denials": 2,
  "recent_approvals": 1
}
```

---

## 3.5 Context Layer

Questions:

- What project is this command running in?
- Is the project trusted?
- Is this a package-managed project?
- Are sensitive files nearby?
- Is this inside a repo, temp folder, home folder, or system path?

Possible fields:

```json
{
  "cwd_scope": "project",
  "project_type": "node",
  "repo_detected": true,
  "sensitive_files_nearby": [".env", ".npmrc"],
  "lockfile_present": true
}
```

---

## 3.6 Policy Match Layer

Questions:

- Which policies matched?
- Which policy had priority?
- Did any deny rule fire?
- Did any sandbox-first rule fire?
- Did user profile mode affect the decision?

Possible fields:

```json
{
  "policy_hits": [
    "package_installs_sandbox_first",
    "agent_package_installs_require_review"
  ],
  "highest_priority_policy": "package_installs_sandbox_first",
  "policy_confidence": 0.95,
  "mode": "balanced"
}
```

---

## 3.7 Risk Scoring Layer

Risk score should be decomposed.

Possible fields:

```json
{
  "risk_score": 7,
  "risk_components": {
    "network_execution": 2,
    "package_install": 2,
    "lifecycle_script_possible": 2,
    "actor_trust_penalty": 1,
    "credential_adjacency": 0,
    "destructive_potential": 0
  },
  "confidence": 0.91,
  "evidence_strength": 0.86
}
```

---

## 3.8 Decision Layer

Questions:

- What is the final decision?
- Why?
- What should happen next?
- Can the user override?
- Is sandboxing available?
- Is denial hard or soft?

Possible fields:

```json
{
  "decision": "SANDBOX_FIRST",
  "reasons": [
    "Package installs may execute lifecycle scripts.",
    "The request came from an agent.",
    "The package is new to this project."
  ],
  "recommended_next_action": "Run sandbox analysis before host install.",
  "override_allowed": true,
  "requires_audit": true
}
```

---

## 3.9 Execution Layer

Questions:

- Was the command executed?
- Was it blocked?
- Was it routed to sandbox?
- Did execution succeed?
- What changed?

Possible fields:

```json
{
  "execution_route": "sandbox",
  "executed": true,
  "exit_code": 0,
  "duration_ms": 1832,
  "files_changed_count": 2,
  "network_required": true
}
```

---

## 3.10 Sweep/Finding Layer

Questions:

- What was found?
- How severe is it?
- How confident is the finding?
- Where is the evidence?
- Does it imply credential exposure?
- What should the user do?

Possible fields:

```json
{
  "finding_category": "suspicious_lifecycle_script",
  "severity": "high",
  "confidence": "moderate",
  "evidence_location": "node_modules/example/package.json",
  "credential_exposure_possible": true,
  "recommended_action": "Review script and rotate exposed tokens if execution occurred."
}
```

---

## 4. Final Score Is a Summary, Not the Source of Truth

Policy Scout may display:

```text
Risk: 7/10
Decision: SANDBOX_FIRST
```

But internally, the final risk score is only a summary.

The source of truth is the granular evaluation packet.

---

## 5. Evaluation Packet

Every evaluated command should produce an evaluation packet.

```json
{
  "evaluation_id": "eval_123",
  "request_id": "req_123",
  "parse": {},
  "classification": {},
  "capabilities": {},
  "actor": {},
  "context": {},
  "policy": {},
  "risk": {},
  "decision": {},
  "execution": {},
  "findings": []
}
```

This packet should be written to audit storage and referenced by any Scout Report.

---

## 6. Clutch Compatibility

The clutch layer should not read only final decisions.

It should read granular signals such as:

- risk score
- confidence
- evidence strength
- failure streak
- repeated denials
- repeated approvals
- actor trust
- command category
- policy hit severity
- recent incident trajectory
- classifier uncertainty
- sandbox failure rate
- sweep finding severity

This allows Policy Scout to respond intelligently:

```text
Low classifier confidence -> require approval.
Repeated risky agent requests -> cautious mode.
Confirmed suspicious finding -> incident mode.
Sandbox failure with high risk -> deny or manual review.
High-risk command with credential adjacency -> deny and alert.
Safe read command with high confidence -> allow.
```

---

## 7. No Silent Safety Regression

Adaptive systems may improve comfort, wording, and routing.

They must not silently weaken safety.

Allowed adaptive improvements:

- better explanations
- fewer noisy prompts
- better default report detail
- improved sandbox recommendations
- better sweep prioritization
- remembered user preference for concise/verbose reports

Disallowed adaptive behavior in v0.1:

- auto-allowing dangerous commands because the user approved once
- disabling safety checks because they are annoying
- letting an LLM override policy
- treating repeated agent requests as proof of safety
- hiding findings because they are low confidence

---

## 8. Report Granularity

Scout Reports should preserve granular details.

A report should not say only:

```text
Risky command blocked.
```

It should explain:

```text
Command: npm install unknown-lib
Decision: SANDBOX_FIRST
Risk: 7/10

Why:
- package install may execute lifecycle scripts
- package downloads third-party code
- request came from an agent
- package is new to this project

Recommended:
Run sandbox install first.
```

Granularity makes Policy Scout trustworthy.

---

## 9. Testing Requirements

Tests should verify granular outputs, not only final decisions.

Example tests:

- command is classified correctly
- capability flags are correct
- policy hits are recorded
- risk components sum correctly
- final decision is correct
- reasons are human-readable
- audit event is written
- Scout Report references the evaluation packet
- secret values are redacted from evidence
- unknown commands fail safely

---

## 10. Evaluation Doctrine

Policy Scout evaluates small steps so that big mistakes have fewer places to hide.

Granular scoring is not extra complexity. It is the foundation that makes the clutch, audit log, policy engine, and Scout Reports work correctly.
