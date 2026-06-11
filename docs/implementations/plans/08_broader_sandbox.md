# Implementation Plan — Gap 8: Broader Sandbox

## Problem
The current sandbox handles only JavaScript package installs for four package managers. Approximately 70% of commands that receive `REQUIRE_APPROVAL` — shell scripts, Python scripts, Makefiles, build tools, arbitrary binaries — run directly on the host machine with no preview of their behavior. A user who approves an ambiguous command is flying blind.

## Goal
A general-purpose sandbox that can run any command in an isolated Linux namespace, capture all filesystem changes and process activity via strace, and produce a behavior report before the user decides whether to allow it on the real machine.

---

## New Module: `policy_scout/sandbox/general/`

```
policy_scout/sandbox/general/
├── __init__.py
├── namespace_sandbox.py    # unshare-based process isolation
├── overlay_fs.py           # overlayfs for filesystem change capture
├── strace_runner.py        # strace subprocess wrapper
├── syscall_analyzer.py     # strace output parser + classifier
├── resource_limits.py      # ulimit / cgroup-v2 constraints
└── behavior_report.py      # combine fs diff + syscall analysis into a report
```

---

## Implementation Approach

### Step 1 — Prerequisites and Platform Gating

This feature requires Linux with unprivileged user namespaces enabled. Check at startup:

```python
def check_sandbox_prerequisites() -> SandboxPrerequisites:
    checks = {
        "unshare": shutil.which("unshare") is not None,
        "user_namespaces": _check_user_namespaces(),
        "overlayfs": _check_overlayfs(),
        "strace": shutil.which("strace") is not None,
    }
    return SandboxPrerequisites(
        available=checks["unshare"] and checks["user_namespaces"],
        strace_available=checks["strace"],
        overlayfs_available=checks["overlayfs"],
        details=checks,
    )

def _check_user_namespaces() -> bool:
    # /proc/sys/kernel/unprivileged_userns_clone must be 1 (or not exist)
    path = Path("/proc/sys/kernel/unprivileged_userns_clone")
    if path.exists():
        return path.read_text().strip() == "1"
    return True  # not present = enabled by default on most distros

def _check_overlayfs() -> bool:
    # Check if overlay is in /proc/filesystems
    return "overlay" in Path("/proc/filesystems").read_text()
```

If `unshare` or user namespaces are unavailable, `doctor` reports "general sandbox: not available" and the feature degrades gracefully — commands get the existing policy check without sandboxing. No silent failure.

### Step 2 — Namespace Sandbox (`namespace_sandbox.py`)

The core isolation uses `unshare` to create new mount, PID, network, and user namespaces:

```python
import subprocess
import tempfile
import os

UNSHARE_FLAGS = [
    "--mount",   # new mount namespace (for overlayfs)
    "--pid",     # new PID namespace
    "--fork",    # required with --pid
    "--net",     # new network namespace (no network access by default)
    "--user",    # new user namespace (enables unprivileged operation)
    "--map-root-user",  # map current user to root inside namespace
]

class NamespaceSandbox:
    def __init__(self, work_dir: Path, allow_network: bool = False):
        self._work_dir = work_dir
        self._allow_network = allow_network
        self._overlay = OverlayFS(work_dir)

    def run(self, command: list[str], timeout: int = 30) -> SandboxRunResult:
        # Set up overlayfs first
        lower_dir, upper_dir, merged_dir = self._overlay.setup()

        cmd = ["unshare"] + UNSHARE_FLAGS
        if not self._allow_network:
            pass  # --net already in UNSHARE_FLAGS, network is isolated
        cmd += ["--", "sh", "-c", shlex.join(command)]

        proc = subprocess.run(
            cmd,
            cwd=str(merged_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=self._clean_env(),
        )

        fs_diff = self._overlay.get_diff()  # files in upper_dir
        return SandboxRunResult(
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            timed_out=(proc.returncode == -signal.SIGTERM),
            fs_changes=fs_diff,
        )

    def _clean_env(self) -> dict:
        # Strip sensitive env vars before passing to sandbox
        safe_keys = {'PATH', 'HOME', 'USER', 'SHELL', 'LANG', 'LC_ALL', 'TERM'}
        return {k: v for k, v in os.environ.items() if k in safe_keys}
```

**Network isolation:** The `--net` flag creates a new network namespace with no interfaces except loopback. The sandboxed process cannot make outbound connections. This is intentional and the default. `--allow-network` opt-in creates a `veth` pair instead — a future enhancement for sandboxing install scripts that legitimately need network.

### Step 3 — OverlayFS (`overlay_fs.py`)

OverlayFS requires at minimum three directories: lower (read-only original), upper (where writes go), and merged (the unified view). After the sandbox run, everything in `upper` is what the process changed.

```python
class OverlayFS:
    def __init__(self, work_dir: Path):
        self._lower = work_dir / "lower"
        self._upper = work_dir / "upper"
        self._work = work_dir / "work"     # required by overlayfs kernel driver
        self._merged = work_dir / "merged"

    def setup(self) -> tuple[Path, Path, Path]:
        for d in [self._lower, self._upper, self._work, self._merged]:
            d.mkdir(parents=True, exist_ok=True)
        # Bind-mount current directory as lower layer
        subprocess.run([
            "mount", "--bind", str(Path.cwd()), str(self._lower)
        ], check=True)
        # Mount overlay
        subprocess.run([
            "mount", "-t", "overlay", "overlay",
            "-o", f"lowerdir={self._lower},upperdir={self._upper},workdir={self._work}",
            str(self._merged)
        ], check=True)
        return self._lower, self._upper, self._merged

    def get_diff(self) -> FSChanges:
        """Walk upper_dir; everything here was written/modified/deleted."""
        created, modified, deleted = [], [], []
        for path in self._upper.rglob("*"):
            rel = path.relative_to(self._upper)
            # Overlay uses whiteout files for deletions (char device 0,0)
            if path.stat().st_rdev == 0 and stat.S_ISCHR(path.stat().st_mode):
                deleted.append(str(rel))
            elif (self._lower / rel).exists():
                modified.append(str(rel))
            else:
                created.append(str(rel))
        return FSChanges(created=created, modified=modified, deleted=deleted)

    def teardown(self):
        subprocess.run(["umount", str(self._merged)], check=False)
        subprocess.run(["umount", str(self._lower)], check=False)
```

**Note:** OverlayFS mount requires `CAP_SYS_ADMIN`. Inside a user namespace with `--map-root-user`, this is available without real root. This is the correct approach — it works in unprivileged user namespaces on kernel ≥ 5.11.

### Step 4 — Strace Runner (`strace_runner.py`)

Run the command under strace to capture syscall activity:

```python
RELEVANT_SYSCALLS = [
    "open", "openat", "creat",       # file opens
    "write", "pwrite64",              # file writes
    "unlink", "unlinkat", "rmdir",   # deletions
    "execve", "execveat",            # process execution
    "connect", "bind",               # network (should be empty with --net)
    "socket",                         # socket creation
    "rename", "renameat2",           # renames
    "chmod", "fchmod",               # permission changes
]

class StraceRunner:
    def run(self, command: list[str], output_file: Path, timeout: int = 30) -> StraceResult:
        syscall_filter = ",".join(RELEVANT_SYSCALLS)
        strace_cmd = [
            "strace",
            "-f",                          # follow forks
            "-e", f"trace={syscall_filter}",
            "-o", str(output_file),
            "-s", "256",                   # max string length
            "--",
        ] + command

        proc = subprocess.run(strace_cmd, capture_output=True, text=True, timeout=timeout)
        return StraceResult(
            exit_code=proc.returncode,
            trace_file=output_file,
        )
```

Strace is run as a wrapper around the sandboxed command, not in addition to namespace isolation — the combination is `unshare ... strace ... command`.

### Step 5 — Syscall Analyzer (`syscall_analyzer.py`)

Parse strace output and classify behaviors:

```python
class SyscallAnalyzer:
    def analyze(self, trace_file: Path) -> SyscallReport:
        file_opens = []
        network_attempts = []
        exec_calls = []
        sensitive_writes = []

        for line in trace_file.read_text().splitlines():
            parsed = self._parse_strace_line(line)
            if not parsed:
                continue
            syscall, args, retval = parsed

            if syscall in ("open", "openat"):
                path = self._extract_path(args)
                if path and self._is_sensitive_path(path):
                    sensitive_writes.append(SensitiveAccess(path=path, mode=self._extract_flags(args)))

            if syscall in ("connect", "socket"):
                network_attempts.append(NetworkAttempt(details=args))

            if syscall == "execve":
                exec_calls.append(ExecCall(command=self._extract_path(args), args=args))

        return SyscallReport(
            file_opens=file_opens,
            network_attempts=network_attempts,
            exec_calls=exec_calls,
            sensitive_writes=sensitive_writes,
        )

    def _is_sensitive_path(self, path: str) -> bool:
        SENSITIVE_PATTERNS = [
            r'\.env$', r'\.ssh/', r'\.npmrc', r'\.config/', r'~/',
            r'/etc/', r'/usr/local/bin/',
        ]
        return any(re.search(p, path) for p in SENSITIVE_PATTERNS)
```

### Step 6 — Resource Limits (`resource_limits.py`)

Apply `ulimit` constraints before running the sandboxed command:

```python
def apply_resource_limits():
    import resource
    # Max CPU time: 30 seconds
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    # Max file size: 100MB
    resource.setrlimit(resource.RLIMIT_FSIZE, (100 * 1024 * 1024, 100 * 1024 * 1024))
    # Max open files: 64
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    # Max processes: 32
    resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
    # Max address space: 512MB
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
```

These are conservative defaults. A config entry allows per-command type adjustment.

### Step 7 — Behavior Report (`behavior_report.py`)

Combine fs diff + syscall analysis into a human-readable Scout Report:

```python
def build_behavior_report(
    command: str,
    sandbox_result: SandboxRunResult,
    syscall_report: SyscallReport,
) -> ScoutReport:
    findings = []

    # Network attempts inside isolated namespace
    if syscall_report.network_attempts:
        findings.append(Finding(
            severity="high",
            category="network_in_sandbox",
            title="Command attempted network connections",
            evidence=str(syscall_report.network_attempts),
            why_it_matters="This command tried to make network connections during execution.",
        ))

    # Sensitive file access
    for access in syscall_report.sensitive_writes:
        findings.append(Finding(
            severity="critical" if ".ssh" in access.path else "high",
            category="sensitive_file_access",
            title=f"Accessed sensitive path: {access.path}",
            ...
        ))

    # Unexpected subprocess execution
    if syscall_report.exec_calls:
        findings.append(Finding(
            severity="medium",
            category="subprocess_execution",
            title=f"Command spawned {len(syscall_report.exec_calls)} subprocesses",
            evidence=str([e.command for e in syscall_report.exec_calls]),
            ...
        ))

    # Filesystem changes summary
    if sandbox_result.fs_changes.modified or sandbox_result.fs_changes.created:
        # Produce a diff-style summary
        ...

    return ScoutReport(
        report_type="general_sandbox",
        command=command,
        findings=findings,
        summary=_build_summary(sandbox_result, syscall_report, findings),
    )
```

---

## CLI Commands

```bash
# Sandbox any command
policy-scout sandbox run -- ./install.sh
policy-scout sandbox run -- python setup.py install
policy-scout sandbox run -- make install
policy-scout sandbox run -- bash -c "curl ... | sh"  # will be denied at policy level first

# With options
policy-scout sandbox run --timeout 60 --allow-network -- npm install

# Check sandbox prerequisites
policy-scout sandbox check-prereqs

# Existing package-manager sandbox still works as before
policy-scout sandbox -- npm install lodash
```

---

## Integration with Policy Engine

When the policy engine produces `SANDBOX_FIRST` for a non-package-manager command, it now has a meaningful sandbox to route to:

```python
# In executor/run.py
if decision.decision == Decision.SANDBOX_FIRST:
    if is_package_manager_command(request.command):
        return run_package_sandbox(request)
    elif sandbox_prerequisites.available:
        return run_general_sandbox(request)
    else:
        return prompt_manual_review(request, reason="sandbox not available on this platform")
```

---

## New Audit Event Types

```
GeneralSandboxStarted      — sandbox run began
GeneralSandboxCompleted    — sandbox run finished
SandboxBehaviorFinding     — a finding from syscall/fs analysis
```

---

## Test Strategy

- Unit test `_check_user_namespaces()` on the test machine
- Unit test `OverlayFS.get_diff()` against a controlled set of file operations
- Unit test `SyscallAnalyzer.analyze()` against fixture strace output files
- Unit test `build_behavior_report()` with mock sandbox + syscall results
- Integration test: sandbox `echo hello` — verify exit_code=0, no findings, empty fs_changes
- Integration test: sandbox `touch /tmp/test_secret` — verify the created file appears in fs_changes
- Integration test: sandbox `python -c "import os; os.system('ls')"` — verify exec_calls is populated
- Platform guard test: on a system without `unshare`, verify graceful degradation with clear error

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `namespace_sandbox.py` | ~200 | High |
| `overlay_fs.py` | ~150 | High |
| `strace_runner.py` | ~120 | Medium |
| `syscall_analyzer.py` | ~250 | Medium-High |
| `resource_limits.py` | ~60 | Low |
| `behavior_report.py` | ~200 | Medium |
| CLI integration | ~100 | Low |
| Policy engine routing | ~50 delta | Low |
| Tests | ~500 | High |
| **Total** | **~1630** | |

---

## Open Questions

1. What happens when overlayfs is not available but unshare is? Recommendation: fall back to a simpler approach — copy the project directory to a temp location, run the command there, diff the result. Less efficient but works everywhere. Flag findings as `detection_confidence: medium` instead of `high`.
2. Should strace output be stored in the audit store? It can be verbose. Recommendation: store a summary (finding categories, exec count, network attempt count) in the audit event; store the raw trace file on disk linked by the event ID. Clean up trace files as part of `data cleanup`.
3. What's the right timeout default? Recommendation: 30 seconds for general commands, 120 seconds for install scripts. User-configurable per command type.
