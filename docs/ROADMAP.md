# Roadmap

The roadmap lists verified gaps, not completed milestones. Prior implementation
plans are preserved in Git history.

## Current priorities

### 1. Contract and packaging hardening

- make package versioning single-source;
- decide whether Fossic is a required install dependency or an optional adapter;
- publish stable JSON envelopes for remaining machine-consumed commands;
- add a supported release process and vulnerability-reporting path.

### 2. CLI decomposition

- separate `argparse`, formatting, and orchestration from subsystem services;
- replace broad exception swallowing on safety-relevant paths with typed results;
- distinguish empty-store results from storage/query failure;
- preserve exit codes and JSON behavior through contract tests.

### 3. Registry and eval coverage

- expand beyond 15 registry entries for Python, Rust, Go, and system package
  managers;
- add measurable registry-to-eval coverage;
- pair security-sensitive registry additions with granular eval and regression
  cases;
- keep network execution and credential access at least as strict as today.

### 4. Sandbox capability model

- expose a truthful containment level for every result;
- formalize backend interfaces before adding Docker/Podman;
- adversarially test environment scrubbing and path containment;
- add an explicit manual rollback command for migrated files.

### 5. Evidence lifecycle

- configurable retention and archival for reports and audit data;
- safe report deletion without erasing approval accountability;
- audited startup cleanup only when explicitly configured;
- sanitized report-export profiles.

### 6. Sweep workflow

- incremental baselines and delta scans;
- repository-scoped exclusions with visible counts;
- explicit, audited finding suppression;
- performance profiling for large repositories.

## Integration roadmap

### Lattica and Fossic

- bring the standalone relay into tracked source with isolated tests;
- define process startup, shutdown, health, and replay ownership;
- verify cross-project causation end to end;
- keep SQLite authoritative until a deliberate migration is designed;
- do not claim generic file-mutation governance until a structured action API and
  mandatory dispatch chokepoint exist.

### Eval core

Lattica proposes extracting neutral eval primitives. This remains future work.
Extraction should happen only if Policy Scout-specific classification and policy
logic can remain injected behind a small evaluator function; governance code
must not become a shared infrastructure dependency.

### Desktop and editors

- complete repeatable native interaction testing and packaging;
- retain the desktop's bounded CLI adapter;
- build editor integrations after hook, JSON, and actor contracts stabilize.

## Long-term, explicitly optional

- remote/team approval adapters;
- signed community rule packs;
- optional reputation and vulnerability services;
- additional operating-system support;
- stronger container/VM-backed analysis.

These must remain optional adapters. Core command checking, local policy, audit,
and reports should continue to function without a cloud service.

## Non-goals

- autonomous remediation or credential rotation;
- LLM-controlled policy decisions;
- full endpoint detection and response;
- silent telemetry or mandatory hosted control planes;
- weakening default policy to improve demo success rates.
