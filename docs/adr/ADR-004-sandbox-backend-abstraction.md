# ADR-004: Sandbox Backend Abstraction and Containment Levels

**Status:** Accepted  
**Date:** 2026-06-10  
**Deciders:** Developer (bitmosh)  
**Related Plans:** [09_sandbox.md](../implementations/plans/09_sandbox.md)  
**Related ADRs:** [ADR-002](ADR-002-policy-config-precedence.md) (sandbox backend config reads from the same config chain), [ADR-005](ADR-005-registry-coverage-expansion.md) (sandbox eval cases require backend-aware decisions)

---

## Context

The current sandbox is a **review workspace, not an isolation boundary.** `npm_runner.py` runs `npm install` directly in a temp directory with the host process's environment, network access, and filesystem visibility. A lifecycle script with a `curl | bash` payload, a process that phones home, or a script that reads `~/.ssh/id_rsa` is not stopped. The only protection is the diff and lifecycle inspection after the fact — which is useful evidence, but not containment.

The implementation doc says "Sandbox is a review workspace, not perfect malware containment" and that is honest, but the product promise of `SANDBOX_FIRST` implies more isolation than exists. An agent told to `SANDBOX_FIRST` a `pip install` has a reasonable expectation that the install runs in a constrained environment. The current implementation doesn't deliver that.

Three things need to change:

1. **Backend abstraction** — the execution layer must be a swappable protocol, not a direct call to `npm_runner.py`. Different users have different containment tools available.
2. **Containment taxonomy** — Policy Scout must make honest, explicit claims about what level of isolation each backend provides. A user who chose `firejail` should know what it can and cannot stop; a user who chose `docker` should know the same.
3. **User-facing setup** — sandboxing tools are not zero-config. Docker needs a socket, Bubblewrap needs to be installed, Firejail has gotchas on some distros. A setup wizard that detects, validates, and writes config is required before this is usable by anyone other than the developer who built it.

This ADR also unlocks pnpm/yarn/bun sandbox execution, which currently classifies as `SANDBOX_FIRST` but falls through to a "not yet supported" error because the execution layer was tied to npm.

---

## Forces

- **Honest capability claims.** Policy Scout cannot claim to contain a lifecycle script if the process has unfiltered network access. The containment level must be declared in the audit trail and surfaced in the report. Users must be able to make an informed choice about which backend to use.
- **No daemon as a hard requirement.** Docker requires the Docker daemon. On Linux developer machines this is common but not universal, and CI pipelines may not have it. The architecture must support daemon-free backends (Bubblewrap, Firejail, Podman rootless).
- **Graceful degradation.** If the configured backend is not available at runtime, Policy Scout must not silently fall back to the uncontained local backend. It must halt and report the missing dependency. Silent fallback defeats the entire feature.
- **Package manager independence.** The current `npm_runner.py` is npm-specific. The backend abstraction must generalize across npm, pnpm, yarn, and bun without backend-specific code for each PM/backend combination.
- **Environment isolation.** Lifecycle scripts must not inherit the host environment. At minimum, `HOME`, `SSH_AUTH_SOCK`, `AWS_*`, `GITHUB_*`, `NPM_TOKEN`, and all `*_TOKEN` / `*_KEY` env vars must be stripped before the sandbox process starts. This applies regardless of which backend is used.
- **Audit completeness.** The containment level and backend used must appear in the `SandboxStarted` audit event and the Scout Report. "What ran in what sandbox" must be reconstructable from the audit trail.
- **Test isolation.** Backend implementations must be testable without the actual backend being present. The protocol must be injectable; tests use a `FakeBackend` that records calls and returns fixed results.

---

## Decision

### D1 — SandboxBackend protocol

All sandbox execution goes through a single `SandboxBackend` protocol defined in `sandbox/backends/base.py`:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Literal

ContainmentLevel = Literal["none", "namespace", "container"]

@dataclass
class BackendCapabilities:
    network_isolation: bool
    filesystem_isolation: bool   # workspace is the only writable path
    syscall_filtering: bool      # seccomp or equivalent
    resource_limits: bool        # memory/CPU caps
    env_scrubbing: bool          # guaranteed; true for all backends (enforced in base)
    containment_level: ContainmentLevel

@dataclass
class SandboxRunSpec:
    command: list[str]           # e.g. ["npm", "install", "lodash"]
    workspace: Path
    env_overrides: dict          # additional safe env vars to inject (e.g. NODE_ENV)
    network: bool = False        # request network access; backend may deny
    memory_mb: int = 512
    cpu_fraction: float = 0.5
    timeout_seconds: int = 120

@dataclass
class SandboxRunResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    backend_id: str
    containment_level: ContainmentLevel
    network_was_isolated: bool
    env_was_scrubbed: bool

class SandboxBackend(Protocol):
    backend_id: str
    containment_level: ContainmentLevel

    def is_available(self) -> bool: ...
    def capabilities(self) -> BackendCapabilities: ...
    def validate(self) -> list[str]: ...   # returns list of config problems; empty = ok
    def run(self, spec: SandboxRunSpec) -> SandboxRunResult: ...
```

`env_scrubbing` is marked `True` for all backends because env scrubbing happens in the **caller** (`sandbox/runner.py`), not inside each backend. Every backend receives a pre-scrubbed env from the runner. Backends may additionally scrub, but cannot un-scrub.

### D2 — Containment taxonomy

Three levels, each with defined claims and explicit non-claims:

```
none        (local backend)
  Claims:     isolated temp directory, env stripped
  Non-claims: no network restriction, no filesystem isolation beyond the workspace,
              no syscall filtering, no resource limits
  Use case:   diff/lifecycle inspection only; explicitly labeled "uncontained" in output

namespace   (bubblewrap, firejail)
  Claims:     network isolation (--net=none by default), workspace is the only
              writable path, env stripped
  Non-claims: does not stop exfiltration via pre-loaded env values that survived
              scrubbing, does not protect against kernel exploits, not a VM boundary
  Use case:   real containment for most common supply-chain attack vectors

container   (docker, podman)
  Claims:     network isolation (--network=none by default), filesystem isolated
              to the container image + bind-mounted workspace, syscall filtering
              via default seccomp profile, resource limits enforced, env stripped
  Non-claims: does not stop attacks that escape the container runtime,
              does not protect against Docker socket abuse if socket is mounted,
              does not sandbox the image pull itself
  Use case:   strongest available local isolation without a VM
```

The containment level is printed in `policy-scout sandbox` output, written to the `SandboxStarted` audit event, and included in the Scout Report under `sandbox_metadata.containment_level`. Users and agents must be able to see what level ran.

### D3 — Supported backends and capability table

Five backends, in detection priority order:

| Backend | ID | Level | Network | Filesystem | Syscall | Resources | Daemon |
|---|---|---|---|---|---|---|---|
| Podman (rootless) | `podman` | container | yes | yes | yes | yes | no |
| Docker | `docker` | container | yes | yes | yes | yes | yes |
| Bubblewrap | `bubblewrap` | namespace | yes | yes | partial | no | no |
| Firejail | `firejail` | namespace | yes | yes | yes | partial | no |
| Local (uncontained) | `local` | none | no | no | no | no | no |

**Podman is preferred over Docker** when both are available. Rootless Podman has no daemon requirement, does not require root, and has equivalent security properties for this use case.

**Bubblewrap is preferred over Firejail** when both are available and no container runtime is present. Bubblewrap has a smaller attack surface (it does less) and is the backend used by Flatpak. Firejail's profile system adds complexity without adding isolation benefit for this narrow use case.

**The `local` backend is never auto-selected** when other backends are available. It is only selected if:
- The user explicitly sets `sandbox.backend: local` in config, or
- No other backend is available AND the user has confirmed they understand `local` provides no containment (the setup wizard records this acceptance).

If the configured backend is unavailable at runtime, `sandbox/runner.py` raises `SandboxBackendUnavailable` and the command does not execute. There is no silent fallback.

### D4 — Config schema

The sandbox block in `.policy-scout.yaml` or `~/.config/policy-scout/config.yaml`:

```yaml
sandbox:
  backend: podman              # auto | podman | docker | bubblewrap | firejail | local
  network_isolation: true      # default true; set false only if the backend supports it
                               # and you have a specific reason to allow network
  resource_limits:
    memory_mb: 512             # 0 = no limit (not recommended)
    cpu_fraction: 0.5          # fraction of one core; 0 = no limit
    timeout_seconds: 120
  docker:
    socket: ""                 # default: /var/run/docker.sock; override for remote
    image: ""                  # default: auto-selected per package manager (see D5)
  podman:
    socket: ""                 # default: unix:///run/user/$UID/podman/podman.sock
    image: ""
  local:
    accepted_no_containment: false   # must be true to use local backend
```

`backend: auto` (the default when no config exists) runs detection in priority order and selects the best available backend. On first use without a config, the setup wizard must run before `auto` selection is honored.

### D5 — Container base images per package manager

When using Docker or Podman, the base image must match the package manager:

| Package manager | Default image | Notes |
|---|---|---|
| npm | `node:22-slim` | slim variant to minimize attack surface |
| pnpm | `node:22-slim` | pnpm installed as part of corepack |
| yarn | `node:22-slim` | yarn via corepack |
| bun | `oven/bun:latest` | official Bun image |
| pip / uv | `python:3.12-slim` | future |
| cargo | `rust:slim` | future |

Images are pinned by digest in a version file (`data/sandbox_images.yaml`) rather than by tag. Tag-pinning (`node:22-slim`) is a supply-chain risk. Digest-pinning is required for any backend that uses container images. The digest file is updated deliberately, not on every run. This is explicitly a manual governance step.

### D6 — Environment scrubbing contract

Before every backend invocation, `sandbox/runner.py` produces a scrubbed environment:

```
Allowed through:  PATH, LANG, LC_*, TERM, HOME (rewritten to a temp dir), USER,
                  NODE_ENV=sandbox, CI=true, package-manager-specific safe vars
                  (NPM_CONFIG_CACHE pointed to sandbox temp dir, etc.)

Stripped by name: *_TOKEN, *_KEY, *_SECRET, *_PASSWORD, *_CREDENTIAL,
                  SSH_*, AWS_*, GCP_*, AZURE_*, GITHUB_*, GITLAB_*,
                  NPM_TOKEN, NODE_AUTH_TOKEN, CARGO_REGISTRY_TOKEN,
                  PYPI_TOKEN, GEM_HOME, BUNDLE_GEMFILE (unless in workspace)

Stripped by value: values matching the secret pattern registry (same patterns as
                   audit/redaction.py) are stripped even if the key name is unknown
```

The scrubbing is applied in `sandbox/env_scrubber.py` (new module). Every backend receives the scrubbed dict. The list of stripped keys is logged to the audit event (key names only, not values). This makes scrubbing auditable without leaking secrets.

### D7 — Setup wizard (`policy-scout sandbox setup`)

A guided flow that runs once per machine and writes `~/.config/policy-scout/config.yaml`:

```
Step 1: Detect available backends
  - Check for: podman, docker, bwrap, firejail
  - Show detection results with version numbers

Step 2: Recommend a backend
  - If podman available:     "Recommended: Podman (rootless, no daemon, container-grade)"
  - Else if docker available: "Recommended: Docker (container-grade, daemon required)"
  - Else if bwrap available:  "Recommended: Bubblewrap (namespace isolation, no daemon)"
  - Else if firejail:         "Recommended: Firejail (namespace isolation, no daemon)"
  - Else:                     "Warning: No containment backend found. Local mode only."

Step 3: For selected backend, run validation
  - Docker/Podman: test socket, test `docker run --rm alpine echo ok`, confirm network=none works
  - bwrap: test `bwrap --unshare-all --ro-bind /usr /usr echo ok`
  - firejail: test `firejail --net=none echo ok`
  - local: display the containment warning, require typed confirmation "I understand"

Step 4: Configure network isolation and resource limits (with safe defaults)

Step 5: Write config, display what was written, show test command
  Output: "Run `policy-scout sandbox npm install express` to test your configuration."
```

The wizard does not run automatically. It runs when explicitly invoked or when `auto` backend detection finds no config and the user runs a sandbox command for the first time. In the latter case, the error message is:

```
Sandbox backend not configured. Run `policy-scout sandbox setup` first.
```

### D8 — Package manager extension

With the backend abstraction in place, pnpm/yarn/bun sandbox execution becomes a routing problem, not an isolation problem. `sandbox/runner.py` dispatches based on detected package manager (already in `package_manager.py`). The install command for each PM is already in `get_install_command()`. No backend-specific code is needed per PM.

pnpm/yarn/bun sandbox execution lands in the same phase as the backend implementations. The `"pnpm/yarn/bun sandbox deferred"` note in IMPLEMENTATION_STATUS is resolved.

---

## Consequences

### Positive
- Policy Scout can make honest containment claims. The containment level in every audit event and Scout Report is a real property, not aspirational.
- `SANDBOX_FIRST` decisions now deliver what the decision name implies.
- pnpm, yarn, and bun sandbox execution comes for free once any backend is implemented.
- The backend abstraction makes future backends (gVisor, nsjail, macOS Seatbelt) additive without touching the core flow.

### Negative / Risks
- Docker image digest pinning is a new governance obligation. The `sandbox_images.yaml` file must be updated when image security updates land. This is a manual process with no automation.
- Bubblewrap and Firejail are Linux-only. macOS users who don't have Docker get `local` backend only. This is acceptable for v1 (Policy Scout is Linux-first) but must be noted in the setup wizard.
- Container image pull happens before the first sandbox run and requires network access. Subsequent runs use the cached image. The pull step is not sandboxed (you're pulling from Docker Hub to sandbox what you install from npm — circular trust problem for the image itself). Mitigated by digest pinning and using official images only.
- `env_scrubbing.py` must be maintained as new token patterns emerge. A pattern that's missing silently fails. The secret pattern registry (already in `data/secret_patterns.yaml`) should be the source of truth — `env_scrubber.py` uses the same patterns as `audit/redaction.py`.

---

## Blast Radius

| File | Change |
|---|---|
| `sandbox/backends/__init__.py` | new package |
| `sandbox/backends/base.py` | new — protocol, dataclasses, ContainmentLevel |
| `sandbox/backends/local.py` | new — wraps current npm_runner behavior |
| `sandbox/backends/docker.py` | new |
| `sandbox/backends/podman.py` | new |
| `sandbox/backends/bubblewrap.py` | new |
| `sandbox/backends/firejail.py` | new |
| `sandbox/backends/fake.py` | new — test double |
| `sandbox/env_scrubber.py` | new |
| `sandbox/backend_detector.py` | new — detection + priority logic |
| `sandbox/setup_wizard.py` | new — `policy-scout sandbox setup` |
| `sandbox/runner.py` | modified — dispatch through backend protocol |
| `sandbox/npm_runner.py` | deprecated — logic moves to `backends/local.py` |
| `sandbox/models.py` | modified — `SandboxResult` gets `containment_level`, `backend_id` |
| `audit/events.py` | modified — `SandboxStarted` gets `backend_id`, `containment_level` |
| `data/sandbox_images.yaml` | new — container image digest registry |
| `cli/main.py` | modified — `sandbox setup` subcommand |
| `tests/test_sandbox_*.py` | modified — inject `FakeBackend` |

---

## Implementation Phases

### Phase 1 — Backend protocol + LocalBackend
- Define protocol, `BackendCapabilities`, `SandboxRunSpec`, `SandboxRunResult` in `backends/base.py`
- Implement `LocalBackend` wrapping the current `npm_runner.py` behavior exactly
- Implement `FakeBackend` for tests
- Implement `env_scrubber.py` using `data/secret_patterns.yaml`
- Wire `sandbox/runner.py` to accept a `backend` parameter, defaulting to `LocalBackend`
- All existing sandbox tests pass with no behavior change

**STOP gate:** All 832 tests pass. `SandboxResult` serialization includes `backend_id` and `containment_level` without breaking existing report reads.

### Phase 2 — DockerBackend + PodmanBackend
- Implement `DockerBackend` and `PodmanBackend` with `--network=none`, bind-mount workspace
- Add `data/sandbox_images.yaml` with initial digests for `node:22-slim` and `oven/bun`
- Implement `backend_detector.py` — detection priority: podman → docker → bubblewrap → firejail → local
- Integration tests that skip if neither Docker nor Podman is available (`pytest.mark.requires_docker`)

**STOP gate:** `policy-scout sandbox npm install express` works with Docker and Podman and produces a Scout Report with `containment_level: container`.

### Phase 3 — BubblewrapBackend + FirejailBackend
- Implement `BubblewrapBackend`: `bwrap --unshare-all --ro-bind / / --bind {workspace} {workspace} ...`
- Implement `FirejailBackend`: `firejail --net=none --private={workspace} ...`
- Integration tests that skip if the respective tool is not installed
- `validate()` method on each backend returns specific error messages for common misconfigurations

**STOP gate:** Namespace-level sandbox produces correct diff and lifecycle output. `containment_level: namespace` in audit event.

### Phase 4 — Setup wizard
- Implement `setup_wizard.py` with the 5-step flow from D7
- Wire to `policy-scout sandbox setup` subcommand
- Wizard writes `~/.config/policy-scout/config.yaml` using the config chain from ADR-002
- Test: wizard with each backend type; wizard with no backends available; wizard re-run overwrites config

**STOP gate:** `policy-scout sandbox setup` runs on a clean machine and produces a valid config.

### Phase 5 — pnpm/yarn/bun execution
- Route pnpm/yarn/bun through the same backend dispatch as npm
- Test `pnpm install`, `yarn install`, `bun install` through the local and (if available) container backends
- Update IMPLEMENTATION_STATUS — "pnpm/yarn/bun sandbox deferred" removed

**STOP gate:** `policy-scout sandbox pnpm install express` works end-to-end.

### Phase 6 — Audit events + containment-level reporting
- `SandboxStarted` event gains `backend_id`, `containment_level`, `network_isolated`, `env_vars_stripped_count`
- Scout Report `sandbox_metadata` block populated with containment info
- `policy-scout sandbox show <id>` prints containment level prominently
- Doctor check: if backend is configured but unavailable, doctor reports warning

**STOP gate:** Audit event for a sandbox run includes containment metadata. Scout Report includes containment section.
