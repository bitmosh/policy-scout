"""Strace subprocess wrapper for syscall capture."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

RELEVANT_SYSCALLS = [
    "open", "openat", "creat",
    "write", "pwrite64",
    "unlink", "unlinkat", "rmdir",
    "execve", "execveat",
    "connect", "bind",
    "socket",
    "rename", "renameat2",
    "chmod", "fchmod",
]


@dataclass
class StraceResult:
    exit_code: int
    trace_file: Path
    timed_out: bool = False
    error: str = ""


class StraceRunner:
    """Wrap a command with strace, writing output to trace_file."""

    def run(
        self,
        command: List[str],
        trace_file: Path,
        cwd: str | Path | None = None,
        timeout: int = 30,
        env: dict | None = None,
    ) -> StraceResult:
        syscall_filter = ",".join(RELEVANT_SYSCALLS)
        strace_cmd = [
            "strace",
            "-f",                           # follow forks
            "-e", f"trace={syscall_filter}",
            "-o", str(trace_file),
            "-s", "256",                    # max string length per arg
            "--",
        ] + command

        try:
            proc = subprocess.run(
                strace_cmd,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            return StraceResult(exit_code=proc.returncode, trace_file=trace_file)
        except subprocess.TimeoutExpired:
            return StraceResult(exit_code=-1, trace_file=trace_file, timed_out=True)
        except FileNotFoundError:
            return StraceResult(
                exit_code=-1, trace_file=trace_file,
                error="strace not found in PATH",
            )
