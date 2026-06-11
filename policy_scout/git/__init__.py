"""Git integration package."""

from .context import GitContext, get_git_context
from .hooks import HookStatus, HooksReport, get_hooks_status, install_hooks, uninstall_hooks
from .lockfile_diff import LockfileDiff, LockfileCheckResult, check_lockfile_changes
from .staged_scanner import StagedCheckResult, SensitiveFileWarning, scan_staged_full

__all__ = [
    "GitContext",
    "get_git_context",
    "HookStatus",
    "HooksReport",
    "get_hooks_status",
    "install_hooks",
    "uninstall_hooks",
    "LockfileDiff",
    "LockfileCheckResult",
    "check_lockfile_changes",
    "StagedCheckResult",
    "SensitiveFileWarning",
    "scan_staged_full",
]
