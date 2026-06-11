# Implementation Plan — Gap 13: Self-Integrity

## Problem
Policy Scout doesn't verify its own integrity. An attacker who compromises the developer's machine could tamper with Policy Scout's registry files to always return `ALLOW`, or modify the policy engine itself. A security tool that provides false assurance is worse than no tool at all.

## Goal
Registry checksum verification, startup self-check, and self-protection policy rules that treat commands targeting Policy Scout's own infrastructure as high-risk.

---

## New Module: `policy_scout/integrity/`

```
policy_scout/integrity/
├── __init__.py
├── registry_manifest.py    # generate + verify registry checksums
├── startup_check.py        # lightweight self-check on startup
└── self_protection.py      # policy rules for commands targeting PS itself
```

```
policy_scout/data/
└── registry_manifest.json  # checksums of bundled registry files (generated at build time)
```

---

## Implementation Approach

### Step 1 — Registry Manifest (`registry_manifest.py`)

The manifest records the SHA-256 of each bundled data file at release time. It's generated during the build process and bundled with the package.

**Schema (`data/registry_manifest.json`):**

```json
{
  "version": "0.1.0",
  "generated_at": "2026-06-10T00:00:00Z",
  "algorithm": "sha256",
  "files": {
    "command_registry.yaml": "a3f4e...",
    "default_policy.yaml": "b2c1d...",
    "suspicious_patterns.yaml": "f7e8a...",
    "top_npm_packages.yaml": "d9f0b...",
    "known_bad_registry.yaml": "e1a2c...",
    "playbooks.yaml": "c3b4d...",
    "secret_patterns.yaml": "f5e6a...",
    "injection_patterns.yaml": "a7b8c...",
    "watch_config.yaml": "d1e2f..."
  },
  "manifest_mac": "..."  # HMAC of the above content, key derived from package version
}
```

**Verification:**

```python
def verify_registry_integrity() -> IntegrityCheckResult:
    manifest_path = Path(__file__).parent.parent / "data" / "registry_manifest.json"
    data_dir = manifest_path.parent

    if not manifest_path.exists():
        return IntegrityCheckResult(
            passed=False,
            reason="Registry manifest not found — Policy Scout may not be correctly installed.",
        )

    manifest = json.loads(manifest_path.read_text())
    errors = []

    for filename, expected_hash in manifest["files"].items():
        file_path = data_dir / filename
        if not file_path.exists():
            errors.append(f"{filename}: file missing")
            continue
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            errors.append(f"{filename}: checksum mismatch (expected {expected_hash[:16]}…, got {actual_hash[:16]}…)")

    return IntegrityCheckResult(
        passed=(len(errors) == 0),
        errors=errors,
        files_checked=len(manifest["files"]),
        reason="All registry files verified." if not errors else f"{len(errors)} file(s) failed verification.",
    )
```

**Manifest generation script (for build process):**

```python
# scripts/generate_registry_manifest.py
# Run during release: python scripts/generate_registry_manifest.py

import hashlib, json, os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "policy_scout" / "data"
REGISTRY_FILES = [
    "command_registry.yaml",
    "default_policy.yaml",
    # ... all data files
]

manifest = {
    "version": os.environ["POLICY_SCOUT_VERSION"],
    "algorithm": "sha256",
    "files": {
        name: hashlib.sha256((DATA_DIR / name).read_bytes()).hexdigest()
        for name in REGISTRY_FILES
    },
}
(DATA_DIR / "registry_manifest.json").write_text(json.dumps(manifest, indent=2))
print(f"Manifest generated for {len(REGISTRY_FILES)} files.")
```

This script runs in CI before packaging and the resulting `registry_manifest.json` is committed to the repo.

### Step 2 — Startup Check (`startup_check.py`)

A lightweight check that runs on every Policy Scout invocation. It should be fast (< 50ms) to avoid adding perceptible latency:

```python
_startup_check_done = False  # module-level, avoids re-checking within a process

def run_startup_check() -> StartupCheckResult:
    global _startup_check_done
    if _startup_check_done:
        return StartupCheckResult(passed=True, from_cache=True)

    integrity = verify_registry_integrity()
    lockdown = is_lockdown_active()  # from Gap 9

    if not integrity.passed:
        # Write to stderr immediately — this is critical
        print(
            f"POLICY SCOUT INTEGRITY WARNING: {integrity.reason}\n"
            "Registry files may have been tampered with.\n"
            "Run 'policy-scout doctor --verbose' for details.",
            file=sys.stderr,
        )
        # Write an audit event (best-effort; the audit store itself could be tampered)
        try:
            audit_store.write(IntegrityCheckFailed(errors=integrity.errors))
        except Exception:
            pass
        # Do NOT exit — continue operating but flag all decisions as potentially untrustworthy
        # (better to operate with a warning than to become a denial-of-service vector)

    _startup_check_done = True
    return StartupCheckResult(
        passed=integrity.passed,
        lockdown_active=lockdown,
        integrity_errors=integrity.errors,
    )
```

**Why not exit on failure?** If we exit when a registry file is modified, an attacker who knows about Policy Scout could corrupt a registry file to prevent it from running, disabling the safety harness entirely. The correct behavior is to warn loudly, continue operating, and record the anomaly. The user decides what to do.

**Performance:** The startup check reads and hashes the registry files. On SSDs, SHA-256 of ~20 YAML files (total ~200KB) takes < 5ms. Acceptable.

### Step 3 — Self-Protection Policy Rules

Add rules to `default_policy.yaml` that flag commands targeting Policy Scout's own infrastructure:

```yaml
# In data/default_policy.yaml

- id: policy_scout_self_attack
  description: "Command appears to target Policy Scout's own data or configuration"
  match:
    command_patterns:
      # Deleting audit database
      - 'rm.*policy-scout'
      - 'rm.*audit\.db'
      - 'rm.*audit\.jsonl'
      # Modifying policy files directly (rather than via policy-scout commands)
      - 'echo.*default_policy\.yaml'
      - 'sed.*command_registry\.yaml'
      - 'python.*policy_scout.*registry'
      # Accessing audit data with suspicious intent
      - 'sqlite3.*audit\.db.*DELETE'
      - 'sqlite3.*audit\.db.*DROP'
  decision: DENY_AND_ALERT
  reasons:
    - "This command appears to target Policy Scout's own audit or registry data."
    - "Modifying or deleting audit data through external commands bypasses the safety harness."

- id: policy_scout_python_import
  description: "Directly importing policy_scout internals may bypass policy enforcement"
  match:
    command_patterns:
      - 'python.*-c.*import policy_scout'
      - 'python.*-c.*from policy_scout'
  decision: REQUIRE_APPROVAL
  reasons:
    - "Direct Python import of policy_scout internals could bypass normal policy enforcement."
```

These rules protect against naive tampering via agent commands. They don't protect against a sophisticated attacker with direct file system access — that's out of scope — but they catch the most likely scenario: an agent being tricked into deleting audit data.

### Step 4 — Doctor Integration

Add integrity checks to `doctor.py`:

```python
def check_integrity(verbose: bool = False) -> DoctorCheck:
    result = verify_registry_integrity()

    if result.passed:
        return DoctorCheck(
            name="Registry Integrity",
            status="ok",
            detail=f"All {result.files_checked} registry files verified.",
        )
    else:
        details = [f"  ✗ {e}" for e in result.errors] if verbose else []
        return DoctorCheck(
            name="Registry Integrity",
            status="error",
            detail="\n".join([
                f"{len(result.errors)} registry file(s) failed integrity check.",
                *details,
                "Run 'policy-scout doctor --verbose' for details.",
            ]),
        )
```

**Extended `doctor` output:**

```
policy-scout doctor

System:
  Python:              3.12.4 ✓
  Installation:        /home/user/.local/lib/python3.12/site-packages/policy_scout ✓

Registry:
  Command registry:    15 entries ✓
  Policy registry:     11 entries ✓
  Integrity:           All 9 registry files verified ✓
  Last manifest:       2026-06-10 (current) ✓

Data:
  Audit DB:            ~/.local/share/policy-scout/audit.db (2.4 MB) ✓
  Chain head:          seq=1247, verified ✓
  Watch daemon:        stopped (run 'policy-scout watch start' to enable)
  Lockdown:            inactive ✓

Integrations:
  MCP server:          not registered (run 'policy-scout serve install' to register)
  Git hooks:           not installed (run 'policy-scout git install-hooks' to install)
  Intel (remote):      disabled (set intel.remote: true in config to enable)
```

### Step 5 — Audit Event for Integrity Failures

```python
@dataclass
class IntegrityCheckFailed(AuditEvent):
    event_type: str = "IntegrityCheckFailed"
    errors: list[str] = field(default_factory=list)
```

Because the integrity check happens at startup, this event may be written to a potentially-tampered store. That's acceptable — the warning on stderr is the primary signal. The audit event exists so that if someone checks the audit log later, they can see the integrity failure was recorded.

---

## CLI Commands

```bash
# Explicit integrity check (also runs in doctor)
policy-scout integrity check
policy-scout integrity check --verbose   # show file-by-file results

# Regenerate manifest (for development / post-update)
policy-scout integrity update-manifest   # re-hashes all data files and updates manifest
# Note: this would let someone with CLI access whitewash a tampered registry.
# In production, the manifest is generated in CI, not by users.
# This command is dev-only, gated by an --dev flag.
```

---

## New Audit Event Types

```
IntegrityCheckFailed    — registry integrity verification failed on startup
IntegrityCheckPassed    — periodic explicit check passed (written by doctor only, not every startup)
```

---

## Integration Points

- `cli/main.py` — call `run_startup_check()` at CLI entry point (before any command runs)
- `doctor.py` — add `check_integrity()` health check
- `registry/` — load functions call `verify_registry_integrity()` and warn if not passed
- `data/default_policy.yaml` — add self-protection rules
- `audit/events.py` — two new event types
- Build/CI process — add `scripts/generate_registry_manifest.py` step

---

## Test Strategy

- Unit test `verify_registry_integrity()` with correct checksums → passes
- Unit test `verify_registry_integrity()` with one modified file → reports the specific file
- Unit test `verify_registry_integrity()` with a missing file → reports missing
- Unit test startup check deduplication (`_startup_check_done` prevents re-check)
- Unit test self-protection rules match `rm ~/.local/share/policy-scout/audit.db`
- Unit test self-protection rules do NOT match `rm node_modules`
- Integration test: modify `command_registry.yaml`, run any command, verify warning appears on stderr
- Integration test: restore `command_registry.yaml`, verify warning is gone

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `registry_manifest.py` (verify) | ~100 | Low |
| `scripts/generate_registry_manifest.py` (build) | ~50 | Low |
| `startup_check.py` | ~80 | Low |
| `self_protection.py` + policy rules | ~40 + YAML | Low |
| Doctor integration | ~60 delta | Low |
| CLI `integrity` command | ~60 | Low |
| Tests | ~250 | Low-Medium |
| **Total** | **~640** | |

---

## Open Questions

1. Should the manifest itself be in version control (committed to the repo)? Recommendation: yes — it's generated at release time, committed, and the commit history shows when it was last updated. Any change to the manifest outside of a release is suspicious.
2. What if the user has legitimately modified a registry file (e.g., added a custom rule)? Recommendation: modified registry files should be re-manifested via `policy-scout integrity update-manifest`. The doctor check should distinguish between "file checksum doesn't match manifest" and "manifest is absent" — the former is informational when the user has made intentional local changes; the latter is an error.
3. Should integrity failures escalate to `DENY_AND_ALERT` for all decisions? Recommendation: no — that's too disruptive and creates a denial-of-service vector. Warn loudly, continue operating, let the user investigate.
