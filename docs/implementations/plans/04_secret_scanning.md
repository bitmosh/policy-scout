# Implementation Plan — Gap 4: Secret Scanning

## Problem
Policy Scout redacts secrets from its own output but has no capability to find secrets in project files, staged changes, or git history. The most common pre-compromise indicator for developer machines is a leaked secret. It should be found before the commit, not after the breach.

## Goal
An offensive secret scanning capability: entropy-based and pattern-based detection across staged changes, full project files, and git history. Runnable as a pre-commit hook or standalone command.

---

## New Module: `policy_scout/scan/`

```
policy_scout/scan/
├── __init__.py
├── engine.py           # main scan orchestrator
├── entropy.py          # Shannon entropy calculator + high-entropy string detection
├── patterns.py         # pattern registry loader + matcher
├── git_scanner.py      # scan staged files + git history
├── file_scanner.py     # scan arbitrary files
└── guidance.py         # rotation guidance by detected secret type
```

```
policy_scout/data/
└── secret_patterns.yaml    # pattern registry for known secret formats
```

---

## Implementation Approach

### Step 1 — Pattern Registry (`data/secret_patterns.yaml`)

Curated list of known secret formats. Each entry includes the pattern, a type identifier, a service name, and rotation guidance.

```yaml
- id: aws_access_key
  service: "AWS"
  pattern: '\bAKIA[0-9A-Z]{16}\b'
  severity: critical
  guidance: "Rotate immediately at https://console.aws.amazon.com/iam/ — assume compromised if in any committed history."

- id: aws_secret_key
  service: "AWS"
  pattern: '[0-9a-zA-Z/+]{40}'
  entropy_min: 4.5        # require high entropy to reduce false positives
  context_pattern: '(?i)(aws_secret|AWS_SECRET_ACCESS_KEY)'
  severity: critical
  guidance: "Rotate the associated AWS Access Key ID immediately."

- id: github_token_classic
  service: "GitHub"
  pattern: '\bghp_[a-zA-Z0-9]{36}\b'
  severity: critical
  guidance: "Revoke at https://github.com/settings/tokens"

- id: github_token_fine_grained
  service: "GitHub"
  pattern: '\bgithub_pat_[a-zA-Z0-9_]{82}\b'
  severity: critical
  guidance: "Revoke at https://github.com/settings/personal-access-tokens"

- id: github_oauth
  service: "GitHub"
  pattern: '\bgho_[a-zA-Z0-9]{36}\b'
  severity: critical
  guidance: "Revoke at https://github.com/settings/applications"

- id: npm_token
  service: "npm"
  pattern: '\bnpm_[a-zA-Z0-9]{36}\b'
  severity: critical
  guidance: "Revoke at https://www.npmjs.com/settings/<username>/tokens"

- id: stripe_live_key
  service: "Stripe"
  pattern: '\bsk_live_[a-zA-Z0-9]{24,}\b'
  severity: critical
  guidance: "Rotate at https://dashboard.stripe.com/apikeys — if exposed, review recent charges."

- id: stripe_test_key
  service: "Stripe"
  pattern: '\bsk_test_[a-zA-Z0-9]{24,}\b'
  severity: medium
  guidance: "Test key — rotate at https://dashboard.stripe.com/apikeys"

- id: sendgrid_key
  service: "SendGrid"
  pattern: '\bSG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}\b'
  severity: critical
  guidance: "Revoke at https://app.sendgrid.com/settings/api_keys"

- id: private_key_pem
  service: "generic"
  pattern: '-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'
  severity: critical
  guidance: "Private key — determine usage (SSH, TLS, signing) and rotate the associated public key/certificate."

- id: generic_api_key
  service: "generic"
  pattern: '(?i)(?:api[_-]?key|apikey|api[_-]?secret)\s*[:=]\s*["\x27]?([a-zA-Z0-9_\-]{20,})["\x27]?'
  severity: high
  entropy_min: 3.5
  guidance: "Identify the service and rotate the key."

- id: env_assignment_secret
  service: "generic"
  pattern: '(?i)(?:password|passwd|secret|token|credential|auth)\s*=\s*["\x27]([^"\x27\s]{8,})["\x27]'
  severity: high
  entropy_min: 3.0
  guidance: "Review the assignment context and rotate if this is a real credential."
```

### Step 2 — Entropy Calculator (`entropy.py`)

Shannon entropy per character:

```python
import math
from collections import Counter

def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())

def find_high_entropy_strings(
    text: str,
    min_length: int = 20,
    max_length: int = 80,
    min_entropy: float = 4.5,
    charset: str = "base64",  # "base64" | "hex" | "any"
) -> list[HighEntropyMatch]:
    """
    Slide a window over the text, extract candidate strings,
    filter by charset membership and entropy threshold.
    """
    ...
```

Charset definitions:
- `base64`: `[A-Za-z0-9+/=]`
- `hex`: `[0-9a-fA-F]`
- `any`: everything except whitespace

Entropy threshold recommendations:
- base64 strings: 4.5 bits/char (random base64 is ~6.0; threshold catches most real secrets)
- hex strings: 3.5 bits/char

False positive reduction: skip strings that appear in known safe contexts — URL paths, version strings, commit hashes in git output. A simple blocklist of common false-positive prefixes (e.g., `sha256:`, `version`, `0000000`) reduces noise significantly.

### Step 3 — Pattern Matcher (`patterns.py`)

```python
class SecretPatternMatcher:
    def __init__(self, patterns: list[PatternSpec]):
        self._compiled = [(p, re.compile(p.pattern)) for p in patterns]

    def scan_text(self, text: str, source: str) -> list[SecretFinding]:
        findings = []
        for spec, regex in self._compiled:
            for match in regex.finditer(text):
                value = match.group(0)
                # Check optional entropy_min
                if spec.entropy_min:
                    if shannon_entropy(value) < spec.entropy_min:
                        continue
                # Check optional context_pattern
                if spec.context_pattern:
                    context_window = text[max(0, match.start()-100):match.end()+100]
                    if not re.search(spec.context_pattern, context_window):
                        continue
                findings.append(SecretFinding(
                    secret_type=spec.id,
                    service=spec.service,
                    severity=spec.severity,
                    source=source,
                    line=text[:match.start()].count('\n') + 1,
                    column=match.start() - text.rfind('\n', 0, match.start()),
                    redacted_value=redact_value(value),
                    guidance=spec.guidance,
                ))
        return findings
```

Note: `redacted_value` shows first 4 + last 2 chars with `***` in between — enough to identify the credential type without revealing it.

### Step 4 — File Scanner (`file_scanner.py`)

```python
SKIP_PATHS = {
    'node_modules', '.git', '__pycache__', '.venv', 'dist', 'build',
    '.mypy_cache', '.pytest_cache',
}

SCAN_EXTENSIONS = {
    '.env', '.cfg', '.conf', '.config', '.ini', '.json', '.yaml', '.yml',
    '.toml', '.py', '.js', '.ts', '.sh', '.bash', '.zsh', '.fish',
    '.tf', '.tfvars', '',  # no extension (scripts)
}

def scan_file(path: Path, matcher: SecretPatternMatcher) -> list[SecretFinding]:
    ...

def scan_directory(root: Path, matcher: SecretPatternMatcher) -> ScanResult:
    ...
```

Binary files (detected by checking for null bytes in the first 8KB) are skipped entirely. Files larger than 1MB are skipped with a warning.

### Step 5 — Git Scanner (`git_scanner.py`)

**Staged files:**

```python
def scan_staged(matcher: SecretPatternMatcher) -> ScanResult:
    # git diff --cached --unified=0
    diff_output = subprocess.run(
        ['git', 'diff', '--cached', '--unified=0'],
        capture_output=True, text=True
    ).stdout
    # Parse unified diff format: only scan added lines (lines starting with '+')
    ...
```

Only added lines are scanned — removed lines don't introduce new secrets.

**Git history:**

```python
def scan_history(
    matcher: SecretPatternMatcher,
    depth: int = 50,           # commits to scan
    since: str | None = None,  # ISO date string
) -> ScanResult:
    # git log --oneline --format="%H" [-n depth] [--since=since]
    # For each commit: git show <hash> --unified=0
    # Parse diff, scan added lines only
    # Track which commit introduced the finding
    ...
```

History scanning includes a deduplication step — the same secret found in multiple commits is one finding with a list of commits, not one finding per commit.

### Step 6 — Rotation Guidance (`guidance.py`)

When a finding is produced, look up the `guidance` field from the pattern spec and enhance it with context:

```python
def generate_guidance(finding: SecretFinding, is_in_history: bool) -> str:
    base = finding.guidance
    if is_in_history:
        base += (
            "\n\nIMPORTANT: This secret was found in git history. "
            "Removing it from the working tree is not enough — it remains in history. "
            "You must either:\n"
            "  1. Assume it's compromised and rotate it immediately, OR\n"
            "  2. Rewrite history with 'git filter-repo' to remove it.\n"
            "If this repo has ever been pushed to a remote, assume the secret was already harvested."
        )
    return base
```

---

## CLI Commands

```bash
# Scan staged changes (for use as pre-commit hook)
policy-scout scan --staged

# Scan entire project directory
policy-scout scan --project [--path /some/dir]

# Scan git history
policy-scout scan --history [--depth 50] [--since 2026-01-01]

# Scan a single file
policy-scout scan --file /path/to/file

# Install as git pre-commit hook
policy-scout git install-hooks  # covered in Gap 12 plan; scan --staged is the underlying command

# Combined: staged + history
policy-scout scan --all
```

Exit codes:
- `0` — no findings
- `1` — findings of severity medium or lower
- `2` — findings of severity high or critical (causes pre-commit hook to block)

---

## New Audit Event Types

```
SecretScanCompleted    — scan finished (files scanned, findings count, severity breakdown)
SecretFindingCreated   — individual secret finding
```

---

## Integration Points

- `sweep/credentials.py` — the existing credential sweep should call the scan engine on found credential-adjacent files; findings feed into the same `Finding` model
- `reports/scout_report.py` — `SecretScanResult` becomes a new report type
- `cli/main.py` — register `scan` command group
- `audit/events.py` — add two new event types
- `doctor.py` — report pattern registry health (count, last updated)

---

## Test Strategy

- Unit test entropy calculator with known-random and known-low-entropy strings
- Unit test pattern matcher against fixtures containing known patterns (use patterns that don't look like real secrets — randomized or clearly fake)
- Unit test staged scanner against a fixture git diff output
- Unit test history scanner against a fixture git log
- Unit test rotation guidance for each severity level and is_in_history flag
- Integration test: create a temp git repo with a staged `.env` containing a mock API key; verify finding is produced

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `entropy.py` | ~100 | Low |
| `patterns.py` + matcher | ~150 | Low |
| `secret_patterns.yaml` (data) | ~150 entries | Research |
| `file_scanner.py` | ~150 | Low |
| `git_scanner.py` (staged + history) | ~200 | Medium |
| `guidance.py` | ~80 | Low |
| CLI commands | ~120 | Low |
| Tests | ~400 | Medium |
| **Total** | **~1350** | |

---

## Open Questions

1. Should the scanner produce findings for test fixtures that obviously contain fake keys (e.g., `test_api_key = "fakekeyfakekeyfakefakekey"`)? Recommendation: add a `# nosec` or `# policy-scout-ignore` comment suppressor, similar to `# noqa`. This is necessary to avoid blocking legitimate test file commits.
2. What's the right entropy threshold to avoid false positives on things like long URLs or long commit hashes? Recommendation: skip strings that match known URL or git-hash patterns before entropy scoring.
3. Should git history scanning be default or opt-in for the `--all` flag? Recommendation: opt-in via `--history` flag because it can be slow on large repos. `--all` without `--history` scans project + staged.
