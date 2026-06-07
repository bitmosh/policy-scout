# Policy Scout — Risk Scoring and Clutch Design

## 1. Purpose

This document defines how Policy Scout should score risk and how the clutch layer should use granular signals to adjust decisions and enforcement modes.

Policy Scout must not rely on a single lump-sum score.

The final risk score is useful for humans, but the clutch needs granular signals.

---

## 2. Core Doctrine

Granular scoring is required.

Policy Scout should preserve separate signals for:

- parse confidence
- classification confidence
- actor trust
- command category
- capability risk
- policy hits
- credential adjacency
- destructive potential
- system mutation
- network execution
- sandbox availability
- evidence strength
- recent actor behavior
- incident trajectory

The clutch should read these signals and produce explainable control adjustments.

---

## 3. Risk Score Is a Summary

Policy Scout may display:

```text
Risk: 7/10
```

But internally this score should be built from components.

Example:

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
  }
}
```

The components matter more than the final number.

---

## 4. Risk Component Categories

Initial components:

```text
parse_uncertainty
classification_uncertainty
actor_trust_penalty
package_install
package_execution
lifecycle_script_possible
network_fetch
network_execution
project_write
system_write
credential_adjacency
destructive_potential
persistence_potential
sandbox_unavailable
known_bad_indicator
suspicious_pattern
incident_context
```

---

## 5. Suggested Component Weights

Initial weights should be conservative and adjustable.

```text
parse_uncertainty              0-2
classification_uncertainty     0-2
actor_trust_penalty            0-2
package_install                2
package_execution              3
lifecycle_script_possible      2
network_fetch                  1
network_execution              4
project_write                  1
system_write                   3
credential_adjacency           4
destructive_potential          4
persistence_potential          4
sandbox_unavailable            1-2
known_bad_indicator            10
suspicious_pattern             1-5
incident_context               1-3
```

Clamp final risk score to 0-10.

---

## 6. Risk Bands

Suggested internal bands:

```text
0-1   minimal
2-3   low
4-5   medium
6-7   high
8-9   severe
10    critical
```

Risk bands should guide defaults, not replace policy rules.

A hard-deny policy can override a low computed score.

---

## 7. Confidence

Confidence measures how reliable the evaluation is.

Inputs:

- parse confidence
- classification confidence
- registry match confidence
- evidence strength
- platform support
- scanner completeness

Example:

```json
{
  "confidence": 0.82,
  "confidence_components": {
    "parse_confidence": 0.91,
    "classification_confidence": 0.96,
    "registry_confidence": 0.95,
    "sweep_coverage": 0.55
  }
}
```

Low confidence should increase friction.

---

## 8. Evidence Strength

Evidence strength measures the quality of the supporting evidence.

Examples:

```text
exact command registry match -> strong
known malicious package indicator -> confirmed
regex suspicious pattern -> moderate
unknown shell syntax -> weak
unsupported platform check -> low
```

Evidence strength should appear in findings and reports.

---

## 9. Risk Scoring Flow

```text
ParseResult
  -> ClassificationResult
  -> CapabilitySet
  -> ContextResult
  -> RegistryHits
  -> RiskComponents
  -> RiskScore
  -> PolicyEngine
  -> Clutch adjustment
  -> Decision
```

The risk scorer should not execute commands.

---

## 10. Clutch Purpose

The clutch layer adjusts enforcement based on granular signals and recent state.

It should help Policy Scout respond to changing risk without becoming autonomous or unpredictable.

Examples:

```text
repeated risky agent requests -> cautious mode
confirmed suspicious finding -> incident mode
low classifier confidence -> require approval
sandbox failure with high risk -> deny/manual review
safe read with high confidence -> allow
```

---

## 11. Clutch Inputs

Initial clutch inputs:

```text
risk_score
risk_components
confidence
evidence_strength
actor_type
actor_trust
recent_denials
recent_approvals
recent_findings
highest_finding_severity
incident_mode_active
sandbox_available
sandbox_failure_rate
mode_duration
last_mode
policy_hits
```

---

## 12. Clutch Outputs

Initial clutch outputs:

```json
{
  "mode": "cautious",
  "action": "increase_friction",
  "reason": "repeated_risky_agent_requests",
  "confidence": 0.84
}
```

or:

```json
{
  "mode": "incident",
  "action": "deny_heavy",
  "reason": "high_severity_finding_active",
  "confidence": 0.91
}
```

The clutch should explain itself.

---

## 13. Enforcement Modes

Modes:

```text
beginner
balanced
paranoid
ci
incident
```

Mode affects policy friction and report verbosity.

Mode should not allow unsafe behavior.

---

## 14. Mode Persistence

Avoid mode flapping.

If the system enters cautious or incident mode, hold it for a minimum duration unless a stronger signal overrides.

Example:

```text
minimum incident mode duration: until user clears/reviews report
minimum cautious mode duration: current session or N commands
```

Mode persistence should be explicit and auditable.

---

## 15. Clutch Rules v0.1

Initial rules:

### 15.1 High-Severity Finding

```text
if highest_finding_severity in [high, critical]:
  mode = incident
  action = increase_friction
```

### 15.2 Repeated Risky Agent Requests

```text
if actor_type == agent and recent_denials >= 2:
  mode = cautious
  action = require_more_approval
```

### 15.3 Low Classification Confidence

```text
if classification_confidence < 0.70:
  action = require_approval
```

### 15.4 Sandbox Failure on High-Risk Install

```text
if decision == SANDBOX_FIRST and sandbox_failed and risk_score >= 6:
  action = manual_review
```

### 15.5 Credential Adjacency

```text
if credential_adjacency > 0:
  action = deny_and_alert
```

### 15.6 Known Bad Indicator

```text
if known_bad_indicator:
  action = deny_and_alert
  mode = incident
```

---

## 16. Adaptive Learning Boundary

Policy Scout may use bandit-style or adaptive learning for non-critical optimization.

Allowed:

- explanation style
- report verbosity
- finding prioritization
- sandbox recommendation ordering
- noisy check tuning suggestions

Disallowed:

- automatically weakening deny rules
- auto-allowing high-risk commands
- letting user approval once become permanent trust
- letting an LLM rewrite policies silently
- hiding findings because they are inconvenient

Adaptive learning can improve fit, not lower armor.

---

## 17. Audit Events

Risk and clutch events:

```text
RiskScored
RiskComponentAdded
ClutchEvaluated
ModeChanged
FrictionIncreased
FrictionReduced
IncidentModeEntered
IncidentModeCleared
```

Each event should include reasons and signal values.

---

## 18. Report Integration

Scout Reports should include:

- risk score
- risk components
- confidence
- evidence strength
- decisive policy hits
- clutch mode if relevant
- mode changes if relevant
- recommended next action

This makes the decision understandable.

---

## 19. Testing Requirements

Tests should verify:

- risk components are computed separately
- risk score clamps to 0-10
- high-risk components trigger expected decisions
- low confidence increases friction
- known bad indicators force deny/alert
- credential adjacency forces deny/alert
- mode persistence works
- incident mode does not flap
- adaptive layer cannot weaken safety rules

---

## 20. Risk and Clutch Doctrine

Policy Scout should be swift, but not careless.

The final score is the label on the armor.

The granular signals are the actual weave.

The clutch works only if the weave stays visible.
