# Implementation Plan — Gap 2: Threat Intelligence Integration

## Problem
The classifier knows command families and capability patterns but nothing about the specific packages, URLs, or domains referenced in those commands. `npm install lodash` and `npm install 1odash` produce identical classification outcomes despite the second being a known typosquatting attack pattern.

## Goal
A pluggable threat intelligence layer that enriches classification results with external signal — package reputation, known-bad advisories, typosquatting detection, lockfile integrity — without coupling core policy decisions to network availability.

---

## New Module: `policy_scout/intel/`

```
policy_scout/intel/
├── __init__.py
├── adapter.py          # ThreatIntelAdapter protocol + registry
├── local/
│   ├── __init__.py
│   ├── typosquatting.py    # edit-distance check against top-N list
│   ├── lockfile_integrity.py
│   └── known_bad.py        # local YAML registry of known-bad hashes/names
└── remote/
    ├── __init__.py
    ├── osv.py              # OSV database API adapter
    ├── npm_advisories.py   # npm security advisory API
    └── cache.py            # TTL cache for remote responses
```

```
policy_scout/data/
├── top_npm_packages.yaml      # top ~1000 npm packages by weekly downloads
├── top_pypi_packages.yaml     # top ~500 PyPI packages
└── known_bad_registry.yaml    # curated known-bad package names + hashes
```

---

## Implementation Approach

### Step 1 — `adapter.py`: Protocol Definition

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ThreatIntelAdapter(Protocol):
    def enrich_package(
        self,
        ecosystem: str,          # "npm" | "pypi" | "cargo" etc.
        name: str,
        version: str | None,
    ) -> "IntelResult": ...

@dataclass
class IntelResult:
    package_name: str
    ecosystem: str
    advisories: list[Advisory]        # known CVEs/advisories
    typosquatting_candidates: list[str]  # packages this name is close to
    known_bad: bool
    known_bad_evidence: str | None
    lockfile_integrity_ok: bool | None  # None = not checked
    publish_anomaly: bool | None       # None = not checked (remote only)
    confidence: str                    # "high" | "medium" | "low"
    source: str                        # "local" | "remote:osv" etc.
```

An `AdapterChain` runs all registered adapters and merges results, deduplicating advisories by ID.

### Step 2 — `local/typosquatting.py`

Load the top-N package list from `data/top_npm_packages.yaml`. For a given package name, compute:

1. **Edit distance** (Levenshtein, implemented locally — no packages) against every name in the top-N list. Flag any match with distance ≤ 2 and a download ratio > 1000:1.
2. **Common substitution patterns**: digit-for-letter (`1` → `l`, `0` → `o`), hyphen insertion/removal, common suffix additions (`-utils`, `-helper`, `-js`, `-node`).
3. **Homoglyph substitution**: Unicode characters that visually resemble ASCII (Cyrillic `а` vs Latin `a`).

```python
def check_typosquatting(name: str, ecosystem: str) -> list[TyposquatCandidate]:
    top = load_top_packages(ecosystem)
    candidates = []
    for known in top:
        dist = levenshtein(name, known)
        if dist <= 2 and dist > 0:
            candidates.append(TyposquatCandidate(
                original=known,
                distance=dist,
                technique=classify_substitution(name, known),
            ))
    return candidates
```

The top package lists are static YAML files bundled with the package. They should be updated as part of the release process (a simple script that calls `https://api.npmjs.org/downloads/range/last-month` and takes the top 1000), but never auto-updated at runtime.

### Step 3 — `local/lockfile_integrity.py`

`package-lock.json` contains an `integrity` field per package (`sha512-...` in SRI format). These hashes are computed from the tarball content as published to the registry.

Check: for each package in the lockfile, compare the stored `integrity` hash against the hash Policy Scout computes from the cached tarball in `node_modules/.cache` (if present) or from the installed package content.

A simpler but still effective check: verify that the `integrity` field exists, is non-empty, and has the `sha512-` prefix. A lockfile where integrity fields have been stripped or zeroed out is a tamper indicator even without re-downloading content.

Full integrity verification (re-downloading and hashing) is opt-in and marked as a remote operation.

### Step 4 — `local/known_bad.py`

A YAML registry of confirmed-malicious packages:

```yaml
# data/known_bad_registry.yaml
# Format: ecosystem:name[:version] -> evidence
npm:
  "event-source-polyfill@1.0.31":
    hash: "sha512-abc123..."
    reason: "credential harvesting postinstall script, reported 2024-03"
    source: "https://socket.dev/npm/package/event-source-polyfill/1.0.31"
  "node-ipc@10.1.1":
    reason: "intentional sabotage by maintainer"
    source: "CVE-2022-23812"
```

This file is bundled with the package and is a curated, manually-verified list. It is not auto-updated. A `policy-scout intel update-local` command could refresh it from a signed upstream source in a future version.

### Step 5 — `remote/osv.py`

OSV (Open Source Vulnerabilities) provides a free, unauthenticated batch API:

```
POST https://api.osv.dev/v1/querybatch
{
  "queries": [
    {"package": {"name": "lodash", "ecosystem": "npm"}, "version": "4.17.20"}
  ]
}
```

Returns known vulnerabilities with CVSS scores, affected versions, and fix availability.

The adapter calls this only when:
- Network is available (checked via a fast HEAD request with 2s timeout)
- The user has opted in via config (`intel.remote: true` or `--with-intel` flag)
- The result is not in the TTL cache (default TTL: 4 hours)

### Step 6 — `remote/cache.py`

SQLite-backed TTL cache stored at `~/.local/share/policy-scout/intel_cache.db`. Schema:

```sql
CREATE TABLE intel_cache (
    key TEXT PRIMARY KEY,          -- "ecosystem:name:version"
    data TEXT NOT NULL,            -- JSON-serialized IntelResult
    fetched_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);
```

Cache misses fall through to the remote adapter; errors from remote adapters return a degraded `IntelResult` with `confidence: low` rather than failing the whole check.

### Step 7 — Integration with Risk Scorer

The `IntelResult` feeds into the existing `RiskScore` as additional evidence:

```python
# In risk_scorer.py
if intel_result.known_bad:
    score.add_component("known_bad_package", weight=9.0, evidence=intel_result.known_bad_evidence)
if intel_result.typosquatting_candidates:
    score.add_component("typosquatting_risk", weight=6.0, evidence=str(intel_result.typosquatting_candidates))
if intel_result.advisories:
    max_cvss = max(a.cvss for a in intel_result.advisories if a.cvss)
    score.add_component("known_advisory", weight=min(max_cvss, 9.0), evidence=...)
```

Intel results are included in the `ClassificationResult` as an optional `intel` field so the Scout Report can surface them.

---

## New Audit Event Types

```
IntelLookupCompleted   — intel enrichment ran (source, package, findings summary)
IntelCacheHit          — result served from cache
IntelLookupFailed      — remote lookup failed (degraded mode)
```

---

## CLI Changes

```
policy-scout check -- npm install <pkg>   # now includes intel enrichment automatically (local only by default)
policy-scout check --with-intel -- npm install <pkg>   # include remote intel

policy-scout intel status                 # show cache stats, last update times
policy-scout intel update-local           # refresh known_bad_registry.yaml from signed source (future)
policy-scout intel clear-cache            # flush the TTL cache
```

---

## Configuration

In the user config (`~/.config/policy-scout/config.yaml`):

```yaml
intel:
  local: true          # always on
  remote: false        # opt-in; requires network
  cache_ttl_hours: 4
  typosquatting_distance: 2
  top_packages_max: 1000
```

---

## Integration Points

- `policy/risk_scorer.py` — consume `IntelResult` as risk score components
- `classify/command_classifier.py` — trigger intel lookup when command involves a package name
- `reports/scout_report.py` — surface intel findings in the Scout Report
- `audit/events.py` — add three new event types
- `cli/check.py` — add `--with-intel` flag
- `doctor.py` — report intel adapter status (local: ok, remote: disabled/available/error)

---

## Test Strategy

- Unit test `typosquatting.py` with known squatting pairs (`lodash`/`1odash`, `react`/`reaact`)
- Unit test `lockfile_integrity.py` against a fixture lockfile with and without tampered integrity fields
- Unit test `known_bad.py` against the bundled registry
- Unit test `AdapterChain` merge behavior (dedup advisories, merge confidence levels)
- Mock test for OSV adapter (mock `requests` — but note: `requests` needs to be a dependency or we use `urllib.request` from stdlib)
- Integration test: `check -- npm install known-bad-package-name` produces advisory findings

**Note:** Remote adapter uses `urllib.request` from stdlib (no new dependency). JSON parsing uses stdlib `json`.

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `adapter.py` + protocol | ~100 | Low |
| `local/typosquatting.py` + Levenshtein | ~200 | Low-Medium |
| `local/lockfile_integrity.py` | ~150 | Low |
| `local/known_bad.py` + YAML | ~80 + data | Low |
| `remote/osv.py` | ~150 | Low |
| `remote/npm_advisories.py` | ~120 | Low |
| `remote/cache.py` | ~120 | Low |
| Data files (YAML) | ~500 entries | Data work |
| Risk scorer integration | ~60 | Low |
| Tests | ~400 | Medium |
| **Total** | **~1380 + data** | |

---

## Open Questions

1. Should typosquatting checks run on every `policy-scout check` or only when a package manager command is detected? Recommendation: only when `package_install` or `package_execute` is in the classification categories.
2. How do we keep `top_npm_packages.yaml` from going stale? Recommendation: include a `generated_at` field and have `doctor` warn if it's > 90 days old.
3. Should `known_bad_registry.yaml` be community-maintainable? Recommendation: yes, but only via a signed bundle from a controlled source — not arbitrary user-provided files — to prevent the registry itself from becoming an attack surface.
