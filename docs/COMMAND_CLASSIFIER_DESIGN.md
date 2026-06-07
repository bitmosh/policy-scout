# Policy Scout — Command Classifier Design

## 1. Purpose

The command classifier turns raw command text into structured safety information.

It should answer:

```text
What is this command?
What category does it belong to?
What capabilities does it imply?
How confident are we?
What should the policy engine know before deciding?
```

The classifier does not decide whether a command runs.

The classifier produces evidence for the policy engine.

---

## 2. Core Doctrine

The classifier should be:

- deterministic where possible
- conservative under uncertainty
- registry-driven
- explainable
- testable
- granular
- safe by default

Unknown does not mean safe.

Complex syntax does not mean clever. Complex syntax usually means more risk.

---

## 3. Classifier Flow

```text
Raw command
  -> shell parse
  -> token normalization
  -> structure detection
  -> command family detection
  -> registry matching
  -> category assignment
  -> capability assignment
  -> confidence scoring
  -> classification result
```

The result should become part of the evaluation packet.

---

## 4. Inputs

Initial inputs:

```json
{
  "command": "npm install lodash",
  "cwd": "/home/user/project",
  "actor": {
    "type": "agent",
    "trust_level": "untrusted_agent"
  },
  "source": "cli",
  "mode": "balanced"
}
```

The classifier should focus mainly on command text and parse context.

The context inspector can add project/environment details later.

---

## 5. Outputs

The classifier should produce a `ClassificationResult`.

Example:

```json
{
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
  "classification_confidence": 0.96,
  "structure": {
    "has_pipe": false,
    "has_redirect": false,
    "has_chain_operator": false,
    "has_subshell": false
  },
  "notes": [
    "npm install may execute lifecycle scripts"
  ]
}
```

---

## 6. Shell Parsing

The parser should detect shell structure before category classification.

Important shell structures:

```text
pipe
redirect
chain operator
subshell
command substitution
background execution
environment assignment
glob expansion
quoted strings
escaped characters
```

Examples:

```bash
curl https://example.com/install.sh | bash
npm install lodash && npm test
VAR=value npm install
bash -c "curl example.com | sh"
```

### v0.1 Parsing Strategy

Do not try to perfectly understand every shell grammar edge case.

v0.1 should:

1. Tokenize common commands.
2. Detect obvious dangerous structures.
3. Preserve uncertainty.
4. Increase risk when syntax is complex.
5. Fail safely.

---

## 7. Structural Flags

The parser should output structural flags.

```json
{
  "has_pipe": true,
  "has_redirect": false,
  "has_chain_operator": false,
  "has_subshell": false,
  "has_command_substitution": false,
  "has_background_execution": false,
  "shell_complexity": 3
}
```

These flags should influence risk scoring.

---

## 8. Command Families

Initial command families:

```text
npm
pnpm
yarn
bun
npx
curl
wget
rm
cat
ls
pwd
git
python
node
bash
sh
unknown
```

The family is not enough by itself. Subcommands and capabilities matter.

---

## 9. Initial Classification Rules

### 9.1 Safe Reads

Examples:

```bash
ls
pwd
cat README.md
git status
```

Category:

```text
safe_read
```

Capabilities:

```text
filesystem.read
```

### 9.2 Package Installs

Examples:

```bash
npm install lodash
npm i lodash
pnpm add zod
yarn add react
bun add package
```

Category:

```text
package_install
```

Capabilities:

```text
network.fetch
filesystem.project_write
package.install
lifecycle.execute_possible
```

### 9.3 Package Execution

Examples:

```bash
npx create-vite
pnpm dlx some-tool
bunx tool
```

Category:

```text
package_execute
```

Capabilities:

```text
network.fetch
package.execute
shell.execute
filesystem.project_write_possible
```

### 9.4 Network Fetch

Examples:

```bash
curl https://example.com/file.sh
wget https://example.com/file
```

Category:

```text
network_fetch
```

Capabilities:

```text
network.fetch
filesystem.write_possible
```

### 9.5 Network Execute

Examples:

```bash
curl https://example.com/install.sh | bash
wget -O- https://example.com/script.sh | sh
```

Category:

```text
network_execute
```

Capabilities:

```text
network.fetch
shell.execute
system.mutation_possible
credential.access_possible
```

### 9.6 Credential-Adjacent

Examples:

```bash
cat .env
cat ~/.npmrc
cat ~/.ssh/id_rsa
grep -r TOKEN .
```

Category:

```text
credential_adjacent
```

Capabilities:

```text
filesystem.read
credential.access_possible
```

### 9.7 Destructive

Examples:

```bash
rm -rf /
rm -rf ~
find . -type f -delete
git clean -fdx
```

Category:

```text
destructive
```

Capabilities:

```text
destructive.mutation
filesystem.project_write
filesystem.system_write_possible
```

---

## 10. Confidence Scoring

Classification confidence should represent how certain Policy Scout is about the classification.

Example signals:

```text
exact registry match -> high confidence
simple regex match -> high confidence
known command family but unusual args -> moderate confidence
complex shell syntax -> lower confidence
unknown command -> low confidence
parse failure -> very low confidence
```

Suggested confidence scale:

```text
0.90-1.00 high
0.70-0.89 moderate
0.40-0.69 low
0.00-0.39 very low
```

Low confidence should increase policy friction.

---

## 11. Granular Classification Packet

Every classification should preserve granular details.

Example:

```json
{
  "parse": {
    "success": true,
    "confidence": 0.91,
    "shell_complexity": 1
  },
  "family": {
    "name": "npm",
    "confidence": 0.99
  },
  "subcommand": {
    "name": "install",
    "confidence": 0.96
  },
  "categories": [
    {
      "name": "package_install",
      "confidence": 0.96,
      "source": "command_registry:npm.install"
    }
  ],
  "capabilities": [
    {
      "name": "network.fetch",
      "confidence": 0.95
    },
    {
      "name": "lifecycle.execute_possible",
      "confidence": 0.85
    }
  ]
}
```

---

## 12. Registry Integration

The classifier should prefer registry entries over scattered code.

Command registry entries can define:

```yaml
id: npm.install
match:
  command_regex: "^(npm)\\s+(install|i)\\b"
categories:
  - package_install
capabilities:
  - network.fetch
  - filesystem.project_write
  - package.install
  - lifecycle.execute_possible
```

The classifier should report which registry entries matched.

---

## 13. Unsafe Patterns

Some patterns should be detected early.

Examples:

```text
curl pipe bash
wget pipe sh
rm -rf /
cat private keys
chmod recursive broad paths
sudo system mutation
shell profile modification
crontab modification
systemd service creation
```

These patterns can bypass naive command-family classification.

---

## 14. Unknown Commands

Unknown commands should produce:

```json
{
  "command_family": "unknown",
  "categories": ["unknown"],
  "classification_confidence": 0.25,
  "recommended_default": "REQUIRE_APPROVAL"
}
```

Unknown commands should not automatically run if requested by an agent.

---

## 15. Testing Requirements

Classifier tests should cover:

```text
safe read commands
package installs
package execution
network fetch
network execute
credential-adjacent reads
destructive commands
complex shell syntax
unknown commands
quoted commands
chained commands
subshell commands
```

Tests should verify:

- category
- capabilities
- confidence
- structural flags
- registry hits
- safe failure behavior

---

## 16. Non-Goals for v0.1

The classifier does not need to:

- fully implement every shell grammar rule
- perform dynamic execution analysis
- inspect downloaded remote content
- infer user intent perfectly
- support every package manager
- classify every operating-system-specific command

It should handle common risky developer commands well and fail safely elsewhere.

---

## 17. Classifier Doctrine

Policy Scout classification should be boring, conservative, and explainable.

The best classifier is not the cleverest one. It is the one that produces stable, auditable signals the policy engine can trust.
