# SPDX-License-Identifier: Apache-2.0
"""Platform prerequisites check for the general namespace sandbox."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxPrerequisites:
    available: bool
    strace_available: bool
    overlayfs_available: bool
    details: dict

    def missing(self) -> list[str]:
        out = []
        if not self.details.get("unshare"):
            out.append("unshare not found in PATH")
        if not self.details.get("user_namespaces"):
            out.append("unprivileged user namespaces disabled (/proc/sys/kernel/unprivileged_userns_clone != 1)")
        return out

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "strace_available": self.strace_available,
            "overlayfs_available": self.overlayfs_available,
            "details": self.details,
            "missing": self.missing(),
        }


def _check_user_namespaces() -> bool:
    path = Path("/proc/sys/kernel/unprivileged_userns_clone")
    if path.exists():
        return path.read_text().strip() == "1"
    return True  # absent = enabled by default on most distros


def _check_overlayfs() -> bool:
    proc_fs = Path("/proc/filesystems")
    if proc_fs.exists():
        return "overlay" in proc_fs.read_text()
    return False


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
