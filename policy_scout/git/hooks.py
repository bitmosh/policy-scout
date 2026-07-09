# SPDX-License-Identifier: Apache-2.0
"""Git hook installation and management for policy-scout."""

import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


_HOOK_TEMPLATE = """\
#!/bin/sh
# Installed by policy-scout — secret scanning pre-commit hook.
# Do not edit manually; reinstall with: policy-scout git hooks install

set -e
policy-scout scan staged --no-audit
"""

_HOOK_MARKER = "# Installed by policy-scout"

_MANAGED_HOOKS = ["pre-commit"]


@dataclass
class HookStatus:
    """Status of a single git hook."""

    name: str
    installed: bool
    path: Optional[str]
    managed: bool   # True if it was installed by policy-scout

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "installed": self.installed,
            "path": self.path,
            "managed": self.managed,
        }


@dataclass
class HooksReport:
    """Status of all managed hooks."""

    hooks: list
    repo_root: str
    hooks_dir: str

    def to_dict(self) -> dict:
        return {
            "repo_root": self.repo_root,
            "hooks_dir": self.hooks_dir,
            "hooks": [h.to_dict() for h in self.hooks],
        }


def _find_hooks_dir(repo_root: Path) -> Optional[Path]:
    """Return the .git/hooks directory for a repo, or None."""
    git_dir = repo_root / ".git"
    if git_dir.is_dir():
        return git_dir / "hooks"
    # Handle worktrees / git submodules (`.git` may be a file)
    if git_dir.is_file():
        content = git_dir.read_text().strip()
        if content.startswith("gitdir:"):
            alt = Path(content.split(":", 1)[1].strip())
            return alt / "hooks"
    return None


def get_hooks_status(repo_root: Optional[Path] = None) -> HooksReport:
    """Return installation status for all managed hooks."""
    root = Path(repo_root or ".").resolve()
    hooks_dir = _find_hooks_dir(root)

    statuses = []
    for name in _MANAGED_HOOKS:
        if hooks_dir is None:
            statuses.append(HookStatus(name=name, installed=False, path=None, managed=False))
            continue
        hook_path = hooks_dir / name
        if hook_path.exists():
            content = hook_path.read_text(errors="replace")
            managed = _HOOK_MARKER in content
            statuses.append(
                HookStatus(
                    name=name,
                    installed=True,
                    path=str(hook_path),
                    managed=managed,
                )
            )
        else:
            statuses.append(HookStatus(name=name, installed=False, path=None, managed=False))

    return HooksReport(
        repo_root=str(root),
        hooks_dir=str(hooks_dir) if hooks_dir else "",
        hooks=statuses,
    )


def install_hooks(repo_root: Optional[Path] = None) -> HooksReport:
    """Install policy-scout managed hooks. Returns final status."""
    root = Path(repo_root or ".").resolve()
    hooks_dir = _find_hooks_dir(root)
    if hooks_dir is None:
        raise RuntimeError(f"Not a git repository or cannot locate hooks dir: {root}")

    hooks_dir.mkdir(parents=True, exist_ok=True)

    for name in _MANAGED_HOOKS:
        hook_path = hooks_dir / name
        if hook_path.exists():
            existing = hook_path.read_text(errors="replace")
            if _HOOK_MARKER in existing:
                # Already managed by us — overwrite to upgrade
                pass
            else:
                # Third-party hook — append our block
                combined = existing.rstrip() + "\n\n" + _HOOK_TEMPLATE
                hook_path.write_text(combined)
                _make_executable(hook_path)
                continue

        hook_path.write_text(_HOOK_TEMPLATE)
        _make_executable(hook_path)

    return get_hooks_status(root)


def uninstall_hooks(repo_root: Optional[Path] = None) -> HooksReport:
    """Remove policy-scout managed hooks. Returns final status."""
    root = Path(repo_root or ".").resolve()
    hooks_dir = _find_hooks_dir(root)
    if hooks_dir is None:
        raise RuntimeError(f"Not a git repository or cannot locate hooks dir: {root}")

    for name in _MANAGED_HOOKS:
        hook_path = hooks_dir / name
        if not hook_path.exists():
            continue
        content = hook_path.read_text(errors="replace")
        if _HOOK_MARKER not in content:
            continue  # Not managed by us — don't touch

        # If the file ONLY contains our hook (possibly with shebang), remove entirely
        lines_without_ours = [
            line for line in content.splitlines()
            if not (
                line.startswith("#!/") or
                line.strip().startswith("# Installed by policy-scout") or
                line.strip().startswith("# Do not edit manually") or
                line.strip().startswith("set -e") or
                "policy-scout scan staged" in line
            )
        ]
        remaining = "\n".join(lines_without_ours).strip()
        if remaining:
            # Preserve any pre-existing third-party content
            hook_path.write_text("#!/bin/sh\n" + remaining + "\n")
        else:
            hook_path.unlink()

    return get_hooks_status(root)


def _make_executable(path: Path) -> None:
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
