"""Resource limits applied to sandboxed processes."""

from __future__ import annotations

import resource


_LIMITS = [
    (resource.RLIMIT_CPU,   30,              30),               # 30s CPU
    (resource.RLIMIT_FSIZE, 100 * 1024**2,   100 * 1024**2),   # 100 MB file size
    (resource.RLIMIT_NOFILE, 64,             64),               # 64 open files
    (resource.RLIMIT_NPROC,  32,             32),               # 32 processes
    (resource.RLIMIT_AS,    512 * 1024**2,   512 * 1024**2),   # 512 MB address space
]


def apply_resource_limits() -> None:
    """Apply conservative rlimits. Called in the child process before exec."""
    for res, soft, hard in _LIMITS:
        try:
            resource.setrlimit(res, (soft, hard))
        except (ValueError, resource.error):
            pass  # some limits can't be tightened (e.g. NPROC on some kernels)
