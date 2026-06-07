# Policy Scout — Mermaid Diagrams

## 1. System Architecture Map

```mermaid
flowchart LR
  actor[Actor<br/>human / agent / IDE / CLI / CI] --> normalizer[Request Normalizer]
  normalizer --> parser[Command Parser]
  parser --> classifier[Command Classifier]
  classifier --> capability[Capability Detector]
  capability --> context[Context Inspector]
  context --> registry[Registry Matcher]
  registry --> risk[Risk Scorer]
  risk --> policy[Policy Engine]
  policy --> decision{Decision}

  registries[(Local Registries<br/>commands / policies / indicators)] -.-> registry
  registries -.-> policy

  decision -->|ALLOW / ALLOW_LOGGED| executor[Direct Executor]
  decision -->|REQUIRE_APPROVAL| approval[Approval Queue]
  decision -->|SANDBOX_FIRST| sandbox[Sandbox Executor]
  decision -->|DENY / DENY_AND_ALERT| denied[Blocked Path]

  executor --> audit[(Audit Store)]
  approval --> audit
  sandbox --> audit
  denied --> audit

  sandbox --> report[Scout Report]
  denied --> report
  audit --> report
```

---

## 2. Core Safety Boundary

```mermaid
flowchart TB
  subgraph bad[Bad Boundary]
    bad_agent[Agent] --> bad_shell[Shell / Tool Execution]
    bad_shell --> bad_log[Maybe Log Later]
  end

  subgraph good[Policy Scout Boundary]
    actor[Actor] --> request[Structured Request]
    request --> scout[Policy Scout Core]
    scout --> allow[Allowed Path]
    scout --> approval[Approval Path]
    scout --> sandbox[Sandbox Path]
    scout --> deny[Deny / Alert Path]
    allow --> audit[(Audit)]
    approval --> audit
    sandbox --> audit
    deny --> audit
  end
```

---

## 3. Granular Evaluation Pipeline

```mermaid
flowchart LR
  request[Command Request] --> parse[Parse Layer]
  parse --> classify[Classification Layer]
  classify --> caps[Capability Layer]
  caps --> actor[Actor Layer]
  actor --> context[Context Layer]
  context --> registry[Registry Hits]
  registry --> risk[Risk Components]
  risk --> policy[Policy Hits]
  policy --> decision[Decision]
  decision --> execution[Execution / Sandbox / Denial]
  execution --> findings[Findings]
  findings --> packet[(Evaluation Packet)]

  parse --> packet
  classify --> packet
  caps --> packet
  actor --> packet
  context --> packet
  registry --> packet
  risk --> packet
  policy --> packet
  decision --> packet
```

---

## 4. Policy Decision Tree

```mermaid
flowchart TD
  start[Evaluated Command] --> harddeny{Known hard deny?}
  harddeny -->|yes| denyalert[DENY / DENY_AND_ALERT]
  harddeny -->|no| credential{Credential-adjacent?}

  credential -->|yes| denyalert
  credential -->|no| networkexec{Network-fetched shell execution?}

  networkexec -->|yes| deny[DENY]
  networkexec -->|no| destructive{Destructive system mutation?}

  destructive -->|yes| deny
  destructive -->|no| package{Package install or execution?}

  package -->|yes| sandbox[SANDBOX_FIRST]
  package -->|no| unknown{Unknown or low confidence?}

  unknown -->|yes| approval[REQUIRE_APPROVAL]
  unknown -->|no| saferead{Safe read?}

  saferead -->|yes| allow[ALLOW]
  saferead -->|no| defaultapproval[REQUIRE_APPROVAL]
```

---

## 5. Sandbox Install Flow

```mermaid
flowchart TD
  request[Package Install Request] --> decision[SANDBOX_FIRST]
  decision --> temp[Create Temp Workspace]
  temp --> copy[Copy Manifest / Lockfile]
  copy --> scrub[Scrub Sensitive Environment]
  scrub --> install[Run Install in Sandbox]
  install --> lifecycle[Inspect Lifecycle Scripts]
  lifecycle --> diff[Capture Manifest / Lockfile Diff]
  diff --> sweep[Run Sandbox Sweep]
  sweep --> result[Sandbox Result]
  result --> report[Scout Report]
  report --> migrate{Migrate Changes?}
  migrate -->|approve once| host[Apply Approved Manifest / Lockfile Changes]
  migrate -->|deny| stop[Do Not Mutate Host Project]

  host --> audit[(Audit)]
  stop --> audit
  report --> audit
```

---

## 6. Sweep Engine Flow

```mermaid
flowchart LR
  subgraph project[Project Sweep]
    ps_start[Project Root] --> scripts[Package Scripts]
    ps_start --> workflows[Workflow Files]
    ps_start --> patterns[Suspicious Patterns]
    ps_start --> executables[Executable Files]
    ps_start --> credentials[Credential References]
  end

  subgraph quick[Quick System Sweep]
    qs_start[Local System] --> ports[Open Ports]
    qs_start --> processes[Processes]
    qs_start --> shell[Shell Profiles]
    qs_start --> temp[Temp Files]
  end

  scripts --> findings[Findings]
  workflows --> findings
  patterns --> findings
  executables --> findings
  credentials --> findings
  ports --> findings
  processes --> findings
  shell --> findings
  temp --> findings

  findings --> severity[Severity + Confidence]
  severity --> report[Scout Report]
  severity --> audit[(Audit)]
```

---

## 7. Audit and Reporting Flow

```mermaid
flowchart TD
  req[CommandRequested] --> parsed[CommandParsed]
  parsed --> classified[CommandClassified]
  classified --> matched[PolicyMatched]
  matched --> decided[DecisionIssued]

  decided --> approval[Approval Events]
  decided --> execution[Execution Events]
  decided --> sandbox[Sandbox Events]
  decided --> denied[Denied / Alert Events]

  sandbox --> findings[SweepFindingCreated]
  execution --> findings
  denied --> report[ScoutReportGenerated]
  findings --> report
  approval --> audit[(Audit Store)]
  execution --> audit
  sandbox --> audit
  denied --> audit
  report --> audit

  audit --> md[Markdown Report]
  audit --> json[JSON Report]
```

---

## 8. Approval Queue Flow

```mermaid
flowchart TD
  decision[Decision: REQUIRE_APPROVAL] --> create[Create Approval Request]
  create --> pending[Pending Approval]
  pending --> review[Human Review]
  review --> approve[Approve Once]
  review --> deny[Deny Once]
  review --> expire[Expire]

  approve --> recheck[Re-validate Request]
  recheck --> match{Exact command + cwd match?}
  match -->|yes| execute[Execute]
  match -->|no| block[Block]

  deny --> block
  expire --> block

  execute --> audit[(Audit)]
  block --> audit
```

---

## 9. Risk and Clutch Flow

```mermaid
flowchart LR
  signals[Granular Signals] --> components[Risk Components]
  components --> score[Risk Score]
  components --> confidence[Confidence]
  components --> evidence[Evidence Strength]

  score --> clutch[Risk Clutch / Mode Router]
  confidence --> clutch
  evidence --> clutch
  state[Recent State<br/>denials / findings / mode duration] --> clutch

  clutch --> mode[Enforcement Mode]
  clutch --> friction[Friction Adjustment]
  mode --> policy[Policy Engine Context]
  friction --> policy
  policy --> decision[Final Decision]
```

---

## 10. Integration Boundary

```mermaid
flowchart LR
  cli[CLI] --> core[Policy Scout Core]
  shell[Shell Shim] --> core
  api[Local API] --> core
  mcp[MCP-style Tool Server] --> core
  editor[Editor Extension] --> core
  ci[CI Integration] --> core

  core --> parser[Parser / Classifier]
  parser --> policy[Policy Engine]
  policy --> decision{Decision}
  decision --> executor[Executor]
  decision --> sandbox[Sandbox]
  decision --> approval[Approval]
  decision --> deny[Deny]

  executor --> audit[(Audit)]
  sandbox --> audit
  approval --> audit
  deny --> audit
```

---

## 11. Local-First Data Map

```mermaid
flowchart TD
  user[User Machine] --> config[~/.config/policy-scout/]
  user --> data[~/.local/share/policy-scout/]
  user --> cache[~/.cache/policy-scout/]

  config --> cfg[config.yaml]
  config --> policies[policies/]
  config --> registries[registries/]

  data --> audit[(audit.db)]
  data --> reports[reports/]
  data --> sandboxes[sandboxes/]
  data --> approvals[approvals]

  cache --> tmp[tmp/]
  cache --> logs[temporary logs]

  audit --> report[Scout Reports]
  sandboxes --> report
```

---

## 12. Cerebra / LumaWeave Bridge

```mermaid
flowchart LR
  scout[Policy Scout] --> events[Audit Events]
  scout --> reports[Scout Reports]
  scout --> findings[Findings]
  scout --> sandbox[Sandbox Results]

  events --> cerebra[Cerebra Memory Runtime]
  reports --> cerebra
  findings --> cerebra
  sandbox --> cerebra

  cerebra --> graph[Graph-ready Memory]
  graph --> luma[LumaWeave Visualization]

  luma --> view[Decision Graphs<br/>Incident Timelines<br/>Package Risk Maps]
```
