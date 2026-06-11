# Implementation Plan — Gap 3: Supply Chain Attack Detection Depth

## Problem
The lifecycle script inspector uses regex over raw text. Modern supply-chain malware uses dynamic property access, base64-encoded payloads, indirect eval, and conditional activation (platform checks, env var checks) that regex patterns miss. Dependency confusion and transitive tree analysis are absent.

## Goal
Replace grep-based lifecycle inspection with a multi-layer analysis: pattern-level (enhanced regex), structural-level (AST where feasible), and graph-level (transitive dependencies). Add dependency confusion detection and publish-anomaly signals.

---

## Affected Module: `policy_scout/sandbox/lifecycle_inspector.py` + new `policy_scout/supply_chain/`

```
policy_scout/supply_chain/
├── __init__.py
├── js_analyzer.py          # multi-layer JS static analysis
├── py_analyzer.py          # Python AST-based analysis (stdlib ast)
├── dep_confusion.py        # dependency confusion detection
├── transitive.py           # transitive dependency tree analysis
├── publish_anomaly.py      # maintainer / publish-date signals
└── patterns/
    ├── js_patterns.yaml    # layered JS detection patterns
    └── py_patterns.yaml    # Python detection patterns
```

---

## Implementation Approach

### Step 1 — Enhanced JS Analysis (`js_analyzer.py`)

**Why not a full JS AST parser?** A proper JS AST parser (`acorn`, `esprima`) would require a new dependency, violating the package installation policy. Instead, implement a structural pattern matcher that operates at two levels above raw regex:

**Level 1 — Normalized text analysis:**
Before matching, normalize the source:
- Remove comments (single-line `//` and multi-line `/* */`)
- Collapse whitespace
- Decode obvious base64 strings (`Buffer.from('...', 'base64')`, `atob('...')`) and analyze the decoded content recursively

```python
def normalize_js(source: str) -> str:
    source = strip_js_comments(source)
    source = decode_base64_literals(source)  # recursive, depth-limited to 3
    return source
```

**Level 2 — Structural pattern registry:**

```yaml
# data/supply_chain/js_patterns.yaml

- id: dynamic_require
  description: "Dynamic property access to require child_process"
  patterns:
    - 'process\[.{0,30}\]\[.{0,30}\]\(.{0,30}child_process'
    - '\[.{0,20}require.{0,20}\]\(.{0,30}child_process'
    - 'global\[.{0,30}\]\(.{0,30}child_process'
  severity: critical
  confidence: high

- id: indirect_eval
  description: "Indirect eval or Function constructor used to run dynamic code"
  patterns:
    - '\beval\s*\('
    - 'new\s+Function\s*\('
    - 'setTimeout\s*\(\s*["\x27]'     # setTimeout with string argument
    - '\bsetInterval\s*\(\s*["\x27]'
  severity: high
  confidence: medium

- id: encoded_payload
  description: "Base64 or hex-encoded payload in a string literal"
  patterns:
    - 'Buffer\.from\s*\(\s*["\x27][A-Za-z0-9+/=]{40,}'
    - 'atob\s*\(\s*["\x27][A-Za-z0-9+/=]{40,}'
    - '\\\\x[0-9a-fA-F]{2}(\\\\x[0-9a-fA-F]{2}){20,}'
  severity: high
  confidence: medium

- id: env_exfiltration
  description: "Environment variable enumeration or targeted theft"
  patterns:
    - 'process\.env\b(?!\.NODE_ENV)(?!\.PATH)(?!\.HOME)'  # any env var except common benign ones
    - 'Object\.keys\s*\(\s*process\.env\s*\)'
    - 'JSON\.stringify\s*\(\s*process\.env'
  severity: high
  confidence: medium

- id: conditional_activation
  description: "Payload activates only on specific platforms or in CI"
  patterns:
    - 'process\.platform\s*===?\s*["\x27]linux'
    - 'process\.env\.CI\b'
    - 'process\.env\.GITHUB_ACTIONS\b'
    - 'process\.env\.GITLAB_CI\b'
  severity: medium
  confidence: low   # benign uses exist; escalate if combined with other patterns

- id: network_fetch
  description: "HTTP/HTTPS request in lifecycle script"
  patterns:
    - '\brequire\s*\(\s*["\x27]https?["\x27]\s*\)'
    - '\brequire\s*\(\s*["\x27]node-fetch["\x27]\s*\)'
    - '\bfetch\s*\('
    - 'axios\.'
    - 'http\.request\s*\('
  severity: high
  confidence: high

- id: shell_exec
  description: "Shell execution through child_process"
  patterns:
    - '\.exec\s*\('
    - '\.execSync\s*\('
    - '\.spawn\s*\('
    - '\.spawnSync\s*\('
    - '\.execFile\s*\('
    - 'shelljs\.'
  severity: high
  confidence: high  # when combined with child_process require

- id: file_write_sensitive
  description: "Writing to sensitive paths"
  patterns:
    - 'fs\.write.*\.bashrc'
    - 'fs\.write.*\.zshrc'
    - 'fs\.write.*\.profile'
    - 'fs\.write.*\.ssh'
    - 'fs\.append.*rc'
    - 'crontab'
  severity: critical
  confidence: high
```

**Level 3 — Pattern combination scoring:**
Some patterns are low-confidence alone but high-confidence in combination. Add a combinator:

```python
ESCALATION_RULES = [
    # (pattern_ids_present, escalated_severity, reason)
    ({"conditional_activation", "network_fetch"}, "critical", "CI-conditional network fetch"),
    ({"conditional_activation", "shell_exec"}, "critical", "CI-conditional shell execution"),
    ({"indirect_eval", "encoded_payload"}, "critical", "Encoded payload with dynamic eval"),
    ({"env_exfiltration", "network_fetch"}, "critical", "Env var theft + network exfiltration"),
]
```

### Step 2 — Python AST Analysis (`py_analyzer.py`)

For Python packages (pip/uv installs), use Python's stdlib `ast` module — no new dependencies needed. This is the one place we can do real AST analysis.

```python
import ast

class PythonSetupAnalyzer(ast.NodeVisitor):
    """Analyzes setup.py, pyproject.toml scripts, or any Python lifecycle script."""

    def visit_Call(self, node: ast.Call):
        # Detect: subprocess.run(), subprocess.Popen(), os.system(), os.popen()
        # Detect: exec(), eval(), compile() with dynamic strings
        # Detect: open() with write mode on sensitive paths
        # Detect: urllib.request, requests, httpx calls
        ...

    def visit_Import(self, node: ast.Import):
        # Flag: subprocess, os, socket, urllib, requests, httpx, paramiko
        ...
```

Findings produced here have `confidence: high` because they're based on parsed structure, not text patterns.

### Step 3 — Dependency Confusion Detection (`dep_confusion.py`)

Dependency confusion: an attacker publishes a package on the public npm/PyPI registry with the same name as a private/internal package used by a company.

Detection approach:
1. Read the project's `.npmrc` or pip config to find configured private registries.
2. For each package being installed, check if it appears on the public registry AND would be resolved from a private registry.
3. Also flag packages whose names match common internal naming patterns:
   - Contains the word `internal`, `private`, `corp`, `company`
   - Matches `<word>-internal`, `@<scope>/anything` (scoped packages on public registry that seem private)
   - Has no public description, very low downloads, and was published recently

```python
def check_dependency_confusion(
    package_name: str,
    ecosystem: str,
    project_registries: list[str],  # from .npmrc / pip.conf
    top_packages: set[str],
) -> DependencyConfusionResult:
    is_scoped = package_name.startswith("@")
    matches_internal_pattern = bool(re.search(r'\b(internal|private|corp)\b', package_name, re.I))
    ...
```

### Step 4 — Transitive Tree Analysis (`transitive.py`)

After a sandbox install, run `npm list --json --depth=999` (or `pnpm list --json --depth=999`) to get the full dependency tree. Walk the tree and:

1. Check every resolved package against the `known_bad_registry.yaml`
2. Check every resolved package name for typosquatting (using the intel layer from Gap 2)
3. Flag packages with very deep nesting (depth > 10) that introduce new binary/native dependencies — these are the packages most likely to be a confused dependency

```python
def analyze_tree(npm_list_json: dict, intel_adapter) -> list[Finding]:
    queue = [(pkg, 0) for pkg in npm_list_json.get("dependencies", {}).items()]
    seen = set()
    findings = []
    while queue:
        name, depth, meta = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        intel = intel_adapter.enrich_package("npm", name, meta.get("version"))
        if intel.known_bad or intel.typosquatting_candidates:
            findings.append(make_finding(name, depth, intel))
        queue.extend(...)
    return findings
```

### Step 5 — Publish Anomaly Detection (`publish_anomaly.py`)

This requires a remote call (npm registry API). Optional, activated with `--with-intel`.

Signals worth checking:
- Package existed for > 1 year, then got a new version from a different `_npmUser` account within the last 90 days → possible account takeover
- Package has > 1M weekly downloads but < 5 versions ever published → unusual, worth flagging
- Package `created` and `modified` timestamps in the registry are the same day and the package has low downloads → new, unknown package

```python
def check_publish_anomaly(name: str, version: str) -> PublishAnomalyResult:
    meta = fetch_npm_registry_meta(name)  # https://registry.npmjs.org/<name>
    ...
```

---

## Changes to Existing Files

### `sandbox/lifecycle_inspector.py`

Replace the existing regex-based `inspect_script()` with a call to `js_analyzer.analyze(source)`. The existing findings format is unchanged; the analyzer just produces richer findings.

```python
# Before:
findings = _grep_patterns(script_content, LEGACY_PATTERNS)

# After:
findings = js_analyzer.analyze(script_content, context={"script_name": script_name})
```

### `sandbox/package_install.py`

After sandbox install completes, add a call to `transitive.analyze_tree()` using the `npm list --json` output.

---

## New Audit Event Types

```
SupplyChainAnalysisCompleted   — transitive + AST analysis finished
DependencyConfusionSuspected   — a dependency confusion pattern matched
PublishAnomalyDetected         — maintainer or timing anomaly found
```

---

## Test Strategy

- Unit test each JS pattern against known-malicious snippets from public disclosures (use sanitized versions from public npm malware reports)
- Unit test base64 decoder with known payloads
- Unit test pattern combinator with known combinations
- Unit test `py_analyzer.py` against a malicious `setup.py` fixture
- Unit test `dep_confusion.py` with mocked `.npmrc` pointing to a private registry
- Unit test `transitive.py` against a fixture `npm list --json` output containing a known-bad package
- Regression: existing eval suite should continue to pass (existing patterns should still fire)

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `js_analyzer.py` (normalizer + pattern engine + combinator) | ~350 | Medium-High |
| `js_patterns.yaml` (pattern data) | ~200 entries | Medium (research) |
| `py_analyzer.py` (AST visitor) | ~200 | Medium |
| `dep_confusion.py` | ~180 | Medium |
| `transitive.py` | ~200 | Medium |
| `publish_anomaly.py` | ~150 | Low-Medium |
| Changes to `lifecycle_inspector.py` | ~50 delta | Low |
| Changes to `package_install.py` | ~30 delta | Low |
| Tests | ~500 | High |
| **Total** | **~1860** | |

---

## Open Questions

1. Should the JS pattern database be community-contributed? Recommendation: yes, but only via the signed bundle mechanism described in Gap 2. The patterns themselves are data and should evolve as malware evolves.
2. How do we handle minified code in lifecycle scripts? Minification defeats most structural patterns. Recommendation: flag heavily minified lifecycle scripts as medium-severity findings by default; a lifecycle script that is minified is itself suspicious.
3. Should `py_analyzer.py` handle `pyproject.toml` build hooks (e.g., `hatch`, `maturin` hooks)? Recommendation: yes — these are equivalent to npm postinstall scripts and are increasingly used for malicious code in Python packages.
