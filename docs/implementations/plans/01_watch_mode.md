# Implementation Plan — Gap 1: Continuous Monitoring (Watch Mode)

## Problem
Sweeps are manual and point-in-time. Malware installs persistence and goes quiet; a sweep that passes two minutes after infection and two minutes before the callback provides false assurance.

## Goal
A lightweight daemon that continuously monitors filesystem events and feeds them into the existing audit + classifier pipeline. No new decision logic — just continuous intake.

---

## New Module: `policy_scout/watch/`

```
policy_scout/watch/
├── __init__.py
├── daemon.py          # PID file, start/stop/status lifecycle
├── fs_watcher.py      # inotifywait wrapper (Linux) + fallback
├── event_router.py    # routes FS events to classifier/audit
└── watch_config.py    # what paths to watch, what events to care about
```

---

## Implementation Approach

### Step 1 — `fs_watcher.py`

Use `inotifywait` (from `inotify-tools`, present on virtually all Linux systems) as the primary backend. Invoke it as a subprocess with `--monitor --recursive --format '%w%f %e' --event create,modify,attrib,moved_to,close_write`. Parse its stdout line by line.

```python
# No new packages required — subprocess only
class InotifyWatcher:
    def __init__(self, paths: list[str], events: list[str]):
        ...
    def watch(self) -> Iterator[FSEvent]:
        # yields FSEvent(path, event_type, timestamp) continuously
        ...
```

Fallback: if `inotifywait` is not found on `PATH`, fall back to a polling loop (`os.stat` on watched paths, compare mtime/size). Mark findings from the polling path with `detection_confidence: low` to distinguish from inotify-sourced events.

macOS note: `inotifywait` doesn't exist on macOS; `fsevents` via the `watchdog` Python library would be needed there. For now, `doctor` should report "watch mode: not available on this platform" on non-Linux systems rather than failing silently.

### Step 2 — `watch_config.py`

Define what paths to watch and what events constitute a trigger. This should be registry-driven, not hardcoded.

```yaml
# data/watch_config.yaml
watch_paths:
  project:
    - "."                    # project root
    - "~/.npmrc"
    - "~/.yarnrc"
  system:
    - "~/.bashrc"
    - "~/.zshrc"
    - "~/.profile"
    - "~/.bash_profile"
    - "~/.config/systemd/user/"
    - "/tmp"                 # new executable files in /tmp

trigger_patterns:
  - path_glob: "**/.env"
    event_types: [create, modify]
    severity: high
  - path_glob: "**/node_modules/.bin/*"
    event_types: [create, modify]
    severity: medium
  - path_glob: "**/.github/workflows/*.yml"
    event_types: [create, modify]
    severity: high
  - path_glob: "/tmp/**"
    event_types: [create]
    mode_filter: executable
    severity: high
  - path_glob: "~/.ssh/authorized_keys"
    event_types: [modify]
    severity: critical
  - path_glob: "**/package.json"
    event_types: [modify]
    severity: medium
```

### Step 3 — `event_router.py`

Each `FSEvent` is evaluated against the trigger patterns. Matching events:
1. Create an `AuditEvent` of type `WatchTriggerDetected`
2. For file-write events on classifiable content (shell scripts, JS, package.json), feed the file path into the sweep engine's relevant sub-checker
3. For new executable files, flag directly as a finding

```python
class EventRouter:
    def __init__(self, audit_store, sweep_engine, config):
        ...
    def route(self, event: FSEvent) -> list[Finding]:
        # match against trigger_patterns
        # emit audit event
        # conditionally run sub-sweep
        # return findings
```

### Step 4 — `daemon.py`

Simple daemon lifecycle:
- PID file at `~/.local/share/policy-scout/watch.pid`
- `start`: fork, write PID, begin watch loop
- `stop`: read PID, send SIGTERM
- `status`: check if PID is alive

No exotic process management. Use `os.fork()` + `os.setsid()` for the daemon. Write a heartbeat timestamp every 60 seconds to a `watch.status` file so `doctor` can report whether watch mode is alive.

### Step 5 — CLI command

```
policy-scout watch start [--project] [--system] [--both]
policy-scout watch stop
policy-scout watch status
policy-scout watch logs [--tail N]
```

`--project` watches the current working directory tree + project-adjacent config files.
`--system` watches shell profiles, systemd user units, SSH config.
`--both` is the default when no flag is given.

---

## New Audit Event Types

```
WatchTriggerDetected   — a watched path matched a trigger pattern
WatchDaemonStarted     — daemon came up (with watched paths in data)
WatchDaemonStopped     — daemon went down cleanly
WatchDaemonHeartbeat   — periodic liveness event (every 60s)
```

---

## Integration Points

- `audit/events.py` — add the four new event types
- `doctor.py` — add watch daemon status check (alive/stopped/not-supported)
- `sweep/engine.py` — expose individual sub-checkers so the event router can call them on single files rather than full project traversals
- `cli/main.py` — register the `watch` command group

---

## Test Strategy

- Unit test `fs_watcher.py` with a temporary directory and actual file operations (create/modify/chmod)
- Unit test `event_router.py` with mocked FSEvents against known trigger patterns
- Unit test `daemon.py` lifecycle (start/stop/status) against a mock watch loop
- Integration test: start daemon, create a test `.env` file, verify `WatchTriggerDetected` event appears in audit store within 2 seconds

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `fs_watcher.py` (inotify + polling fallback) | ~200 | Medium |
| `watch_config.py` + YAML | ~80 + ~50 | Low |
| `event_router.py` | ~150 | Medium |
| `daemon.py` | ~120 | Low-Medium |
| CLI command | ~80 | Low |
| Tests | ~300 | Medium |
| **Total** | **~980** | |

---

## Open Questions

1. Should watch mode auto-start on login (via systemd user unit or launchd plist), or always be manually started? Recommendation: manual start for v1; add auto-start as an opt-in config flag.
2. What's the right throttle on findings from high-churn paths (e.g., `node_modules` during an install)? Recommendation: suppress findings from paths that are currently under an active sandbox run.
3. How should watch events interact with the approval queue? A watch trigger is not a command request. Recommendation: watch triggers produce findings and audit events only — they do not create approval requests.
