"""Namespace-based process isolation using Linux unshare."""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .overlay_fs import FSChanges, OverlayFS
from .prereqs import check_sandbox_prerequisites
from .resource_limits import apply_resource_limits
from .syscall_analyzer import SyscallReport, SyscallAnalyzer
from .behavior_report import BehaviorReport, build_behavior_report

# unshare flags for a restrictive sandbox
_UNSHARE_FLAGS = [
    "--mount",          # new mount namespace (for overlayfs)
    "--pid",            # new PID namespace
    "--fork",           # required with --pid
    "--net",            # new network namespace (no outbound)
    "--user",           # new user namespace
    "--map-root-user",  # map current user to root inside namespace
]

# Safe environment variables passed into the sandbox
_SAFE_ENV_KEYS = frozenset({
    "PATH", "HOME", "USER", "SHELL", "LANG", "LC_ALL", "LC_CTYPE",
    "TERM", "TMPDIR",
})


@dataclass
class SandboxRunResult:
    """Raw result from running the sandboxed subprocess."""
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    fs_changes: FSChanges = field(default_factory=FSChanges)
    syscall_report: SyscallReport = field(default_factory=SyscallReport)
    overlayfs_used: bool = False
    error: str = ""


class NamespaceSandbox:
    """Run an arbitrary command inside a new Linux user+mount+pid+net namespace."""

    def __init__(
        self,
        work_dir: Optional[Path] = None,
        source_dir: Optional[Path] = None,
        allow_network: bool = False,
        use_strace: bool = True,
        use_overlayfs: bool = True,
    ) -> None:
        self._work_dir = work_dir
        self._source_dir = source_dir or Path.cwd()
        self._allow_network = allow_network
        self._use_strace = use_strace
        self._use_overlayfs = use_overlayfs

    def _clean_env(self) -> dict:
        return {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}

    def run(
        self,
        command: List[str],
        timeout: int = 30,
    ) -> SandboxRunResult:
        with tempfile.TemporaryDirectory(prefix="ps-sandbox-") as tmp:
            tmp_path = Path(tmp)
            return self._run_in_tmp(command, tmp_path, timeout)

    def _run_in_tmp(
        self,
        command: List[str],
        tmp_path: Path,
        timeout: int,
    ) -> SandboxRunResult:
        prereqs = check_sandbox_prerequisites()
        if not prereqs.available:
            return SandboxRunResult(
                exit_code=-1,
                stdout="",
                stderr="",
                error=f"Sandbox prerequisites not met: {prereqs.missing()}",
            )

        overlay = None
        overlayfs_used = False
        run_dir = self._source_dir
        fs_changes = FSChanges()

        # Try overlayfs if available
        if self._use_overlayfs and prereqs.overlayfs_available:
            try:
                overlay = OverlayFS(work_dir=tmp_path, source_dir=self._source_dir)
                run_dir = overlay.setup()
                overlayfs_used = True
            except subprocess.CalledProcessError:
                overlay = None
                run_dir = self._source_dir

        # Build unshare command
        flags = list(_UNSHARE_FLAGS)
        if self._allow_network:
            flags = [f for f in flags if f != "--net"]

        trace_file = tmp_path / "strace.out"
        use_strace = self._use_strace and prereqs.strace_available

        if use_strace:
            inner_cmd = ["strace", "-f",
                         "-e", "trace=" + ",".join([
                             "open", "openat", "creat", "write", "pwrite64",
                             "unlink", "unlinkat", "rmdir", "execve", "execveat",
                             "connect", "bind", "socket", "rename", "renameat2",
                             "chmod", "fchmod",
                         ]),
                         "-o", str(trace_file), "-s", "256", "--"] + command
        else:
            inner_cmd = command

        full_cmd = ["unshare"] + flags + ["--"] + inner_cmd

        try:
            proc = subprocess.run(
                full_cmd,
                cwd=str(run_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._clean_env(),
                preexec_fn=apply_resource_limits,
            )
            timed_out = False
            exit_code = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired as e:
            timed_out = True
            exit_code = -1
            stdout = (e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr = (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")

        # Capture fs diff before teardown
        if overlay is not None:
            try:
                fs_changes = overlay.get_diff()
            except Exception:
                pass
            overlay.teardown()

        # Analyze syscall trace
        syscall_report = SyscallReport()
        if use_strace and trace_file.exists():
            syscall_report = SyscallAnalyzer().analyze(trace_file)

        return SandboxRunResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
            fs_changes=fs_changes,
            syscall_report=syscall_report,
            overlayfs_used=overlayfs_used,
        )


def run_general_sandbox(
    command: str | List[str],
    timeout: int = 30,
    allow_network: bool = False,
    source_dir: Optional[Path] = None,
) -> BehaviorReport:
    """High-level entry point: sandbox a command and return a behavior report."""
    if isinstance(command, str):
        cmd_list = shlex.split(command)
        cmd_str = command
    else:
        cmd_list = command
        cmd_str = shlex.join(command)

    sandbox = NamespaceSandbox(
        source_dir=source_dir,
        allow_network=allow_network,
    )
    result = sandbox.run(cmd_list, timeout=timeout)

    return build_behavior_report(
        command=cmd_str,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        stdout=result.stdout,
        stderr=result.stderr,
        fs_changes=result.fs_changes,
        syscall_report=result.syscall_report,
        overlayfs_used=result.overlayfs_used,
    )
