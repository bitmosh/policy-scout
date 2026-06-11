"""Parse strace output and classify behaviors."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Sensitive path patterns — access to these is flagged
_SENSITIVE_PATTERNS = [
    re.compile(r, re.IGNORECASE)
    for r in [
        r'\.env$',
        r'\.ssh/',
        r'\.npmrc',
        r'\.config/',
        r'/etc/',
        r'/usr/local/bin/',
        r'\.aws/',
        r'id_rsa',
        r'id_ed25519',
        r'credentials',
        r'\.gnupg/',
    ]
]

# Parse a single strace line: pid syscall(args) = retval
_STRACE_LINE_RE = re.compile(
    r'^\s*(\d+)\s+(\w+)\s*\(([^)]*)\)\s*=\s*(.+)$'
)

# Extract quoted string from strace args (first quoted arg is usually the path)
_QUOTED_ARG_RE = re.compile(r'"([^"]*)"')


@dataclass
class SensitiveAccess:
    path: str
    syscall: str
    flags: str = ""


@dataclass
class NetworkAttempt:
    syscall: str
    details: str


@dataclass
class ExecCall:
    command: str
    args: str


@dataclass
class SyscallReport:
    sensitive_accesses: List[SensitiveAccess] = field(default_factory=list)
    network_attempts: List[NetworkAttempt] = field(default_factory=list)
    exec_calls: List[ExecCall] = field(default_factory=list)
    total_lines: int = 0
    parse_errors: int = 0

    def to_dict(self) -> dict:
        return {
            "sensitive_accesses": [
                {"path": a.path, "syscall": a.syscall, "flags": a.flags}
                for a in self.sensitive_accesses
            ],
            "network_attempts": [
                {"syscall": n.syscall, "details": n.details}
                for n in self.network_attempts
            ],
            "exec_calls": [
                {"command": e.command, "args": e.args[:200]}
                for e in self.exec_calls
            ],
            "total_lines": self.total_lines,
        }


def _is_sensitive(path: str) -> bool:
    return any(p.search(path) for p in _SENSITIVE_PATTERNS)


def _extract_first_path(args: str) -> Optional[str]:
    m = _QUOTED_ARG_RE.search(args)
    return m.group(1) if m else None



class SyscallAnalyzer:
    """Parse a strace trace file into a structured report."""

    def analyze(self, trace_file: Path) -> SyscallReport:
        report = SyscallReport()
        if not trace_file.exists():
            return report

        for line in trace_file.read_text(errors="replace").splitlines():
            report.total_lines += 1
            m = _STRACE_LINE_RE.match(line)
            if not m:
                continue

            syscall = m.group(2)
            args = m.group(3)

            if syscall in ("open", "openat", "creat"):
                path = _extract_first_path(args)
                if path and _is_sensitive(path):
                    # Extract O_WRONLY/O_RDWR flags for context
                    flags = "write" if ("O_WRONLY" in args or "O_RDWR" in args) else "read"
                    report.sensitive_accesses.append(
                        SensitiveAccess(path=path, syscall=syscall, flags=flags)
                    )

            elif syscall in ("write", "pwrite64"):
                # Check if the fd was opened on a sensitive path — can't easily correlate
                # without full fd table tracking; skip for now
                pass

            elif syscall in ("connect", "socket", "bind"):
                report.network_attempts.append(
                    NetworkAttempt(syscall=syscall, details=args[:200])
                )

            elif syscall in ("execve", "execveat"):
                cmd = _extract_first_path(args) or ""
                # Exclude the initial strace/unshare invocations
                if cmd and not any(skip in cmd for skip in ("strace", "unshare", "/proc/")):
                    report.exec_calls.append(ExecCall(command=cmd, args=args[:200]))

            elif syscall in ("unlink", "unlinkat", "rmdir"):
                path = _extract_first_path(args)
                if path and _is_sensitive(path):
                    report.sensitive_accesses.append(
                        SensitiveAccess(path=path, syscall=syscall, flags="delete")
                    )

        return report
