# SPDX-License-Identifier: Apache-2.0
"""Tests for [12] Git Integration."""

import stat
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# GitContext
# ──────────────────────────────────────────────────────────────────────────────

from policy_scout.git.context import get_git_context, GitContext


def test_get_git_context_in_real_repo():
    """policy-scout itself is a git repo — should return valid context."""
    ctx = get_git_context()
    assert ctx is not None
    assert isinstance(ctx, GitContext)
    # Should have a branch or commit
    assert ctx.branch or ctx.commit
    # repo_root should exist
    assert ctx.repo_root is not None
    assert Path(ctx.repo_root).is_dir()


def test_get_git_context_not_a_repo(tmp_path):
    ctx = get_git_context(cwd=tmp_path)
    assert ctx is None


def test_git_context_to_dict():
    ctx = GitContext(branch="main", commit="abc123", dirty=False, remote="origin", repo_root="/repo")
    d = ctx.to_dict()
    assert d["branch"] == "main"
    assert d["commit"] == "abc123"
    assert d["dirty"] is False
    assert d["remote"] == "origin"


# ──────────────────────────────────────────────────────────────────────────────
# Hooks
# ──────────────────────────────────────────────────────────────────────────────

from policy_scout.git.hooks import (
    get_hooks_status,
    install_hooks,
    uninstall_hooks,
    HooksReport,
    HookStatus,
    _HOOK_MARKER,
)


def _make_git_repo(tmp_path: Path) -> Path:
    """Create a minimal fake git repo at tmp_path."""
    git_dir = tmp_path / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True)
    return tmp_path


def test_install_hooks_creates_file(tmp_path):
    repo = _make_git_repo(tmp_path)
    report = install_hooks(repo_root=repo)
    assert isinstance(report, HooksReport)
    hook_path = repo / ".git" / "hooks" / "pre-commit"
    assert hook_path.exists()
    content = hook_path.read_text()
    assert _HOOK_MARKER in content
    assert "policy-scout scan staged" in content


def test_install_hooks_is_executable(tmp_path):
    repo = _make_git_repo(tmp_path)
    install_hooks(repo_root=repo)
    hook_path = repo / ".git" / "hooks" / "pre-commit"
    mode = hook_path.stat().st_mode
    assert mode & stat.S_IXUSR


def test_hooks_status_shows_installed(tmp_path):
    repo = _make_git_repo(tmp_path)
    install_hooks(repo_root=repo)
    report = get_hooks_status(repo_root=repo)
    pre_commit = next((h for h in report.hooks if h.name == "pre-commit"), None)
    assert pre_commit is not None
    assert pre_commit.installed is True
    assert pre_commit.managed is True


def test_hooks_status_not_installed(tmp_path):
    repo = _make_git_repo(tmp_path)
    report = get_hooks_status(repo_root=repo)
    pre_commit = next((h for h in report.hooks if h.name == "pre-commit"), None)
    assert pre_commit is not None
    assert pre_commit.installed is False


def test_uninstall_hooks_removes_file(tmp_path):
    repo = _make_git_repo(tmp_path)
    install_hooks(repo_root=repo)
    hook_path = repo / ".git" / "hooks" / "pre-commit"
    assert hook_path.exists()
    uninstall_hooks(repo_root=repo)
    assert not hook_path.exists()


def test_uninstall_hooks_preserves_third_party(tmp_path):
    """Uninstall should not remove a third-party hook that we appended to."""
    repo = _make_git_repo(tmp_path)
    hook_path = repo / ".git" / "hooks" / "pre-commit"
    # Write a pre-existing third-party hook
    existing = "#!/bin/sh\n# third-party check\necho 'running tests'\n"
    hook_path.write_text(existing)
    # Install ours (which appends)
    install_hooks(repo_root=repo)
    # Uninstall ours
    uninstall_hooks(repo_root=repo)
    # The third-party content should remain
    assert hook_path.exists()
    remaining = hook_path.read_text()
    assert "third-party" in remaining or "running tests" in remaining


def test_install_hooks_not_git_repo(tmp_path):
    with pytest.raises(RuntimeError, match="git repository"):
        install_hooks(repo_root=tmp_path)


def test_hooks_to_dict():
    hook = HookStatus(name="pre-commit", installed=True, path="/repo/.git/hooks/pre-commit", managed=True)
    d = hook.to_dict()
    assert d["name"] == "pre-commit"
    assert d["installed"] is True
    assert d["managed"] is True


# ──────────────────────────────────────────────────────────────────────────────
# Lockfile diff
# ──────────────────────────────────────────────────────────────────────────────

from policy_scout.git.lockfile_diff import (
    check_lockfile_changes,
    LockfileCheckResult,
    LockfileDiff,
)


def test_lockfile_check_no_lockfiles(monkeypatch):
    def fake_run(args, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""  # no tracked lockfiles
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = check_lockfile_changes()
    assert result.lockfiles_found == 0
    assert result.lockfiles_changed == 0
    assert not result.any_changes


def test_lockfile_check_detects_change(monkeypatch):
    call_count = [0]

    def fake_run(args, **kwargs):
        r = MagicMock()
        r.returncode = 0
        call_count[0] += 1
        if "ls-files" in args:
            r.stdout = "package-lock.json\n"
        else:
            # git diff output
            r.stdout = (
                "diff --git a/package-lock.json b/package-lock.json\n"
                "--- a/package-lock.json\n"
                "+++ b/package-lock.json\n"
                '@@ -10,3 +10,4 @@\n'
                '+  "evil-package": "^1.0.0",\n'
                '-  "lodash": "4.17.21",\n'
            )
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = check_lockfile_changes()
    assert result.lockfiles_found == 1
    assert result.lockfiles_changed == 1
    assert result.any_changes
    diff = result.diffs[0]
    assert diff.has_changes
    assert any("evil-package" in a for a in diff.added)


def test_lockfile_check_no_changes(monkeypatch):
    def fake_run(args, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "ls-files" in args:
            r.stdout = "package-lock.json\n"
        else:
            r.stdout = ""  # empty diff = no change
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = check_lockfile_changes()
    assert result.lockfiles_found == 1
    assert result.lockfiles_changed == 0


def test_lockfile_diff_to_dict():
    diff = LockfileDiff(
        lockfile="package-lock.json",
        added=["evil-pkg"],
        removed=[],
        modified=0,
    )
    d = diff.to_dict()
    assert d["lockfile"] == "package-lock.json"
    assert d["has_changes"] is True
    assert d["added"] == ["evil-pkg"]


# ──────────────────────────────────────────────────────────────────────────────
# Staged scanner
# ──────────────────────────────────────────────────────────────────────────────

from policy_scout.git.staged_scanner import (
    scan_staged_full,
    StagedCheckResult,
    _is_sensitive_file,
    _is_ci_workflow,
)


def test_is_sensitive_file_env():
    assert _is_sensitive_file(".env") is not None
    assert _is_sensitive_file(".env.local") is not None
    assert _is_sensitive_file("config/.env.production") is not None


def test_is_sensitive_file_pem():
    assert _is_sensitive_file("certs/server.pem") is not None


def test_is_sensitive_file_private_key():
    assert _is_sensitive_file("keys/id_rsa") is not None


def test_is_sensitive_file_clean():
    assert _is_sensitive_file("src/main.py") is None
    assert _is_sensitive_file("package.json") is None
    assert _is_sensitive_file("README.md") is None


def test_is_ci_workflow_github():
    assert _is_ci_workflow(".github/workflows/ci.yml") is True


def test_is_ci_workflow_gitlab():
    assert _is_ci_workflow(".gitlab-ci.yml") is True


def test_is_ci_workflow_not():
    assert _is_ci_workflow("src/app.py") is False
    assert _is_ci_workflow("package.json") is False


def test_scan_staged_full_clean(monkeypatch):
    """All-clean staged scan (no staged files)."""
    def fake_run(args, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = scan_staged_full()
    assert result.is_clean
    assert not result.has_sensitive_files
    assert result.severity_exit_code == 0


def test_scan_staged_full_detects_sensitive_file(monkeypatch):
    """Sensitive file staged → non-clean result."""
    call_count = [0]

    def fake_run(args, **kwargs):
        r = MagicMock()
        r.returncode = 0
        call_count[0] += 1
        # First call is the secret scan's git diff --cached --name-only
        # Second call is also git diff (name-only for staged_scanner)
        r.stdout = ".env\n"
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = scan_staged_full()
    assert result.has_sensitive_files
    assert any(w.path == ".env" for w in result.sensitive_files)
    assert result.severity_exit_code == 2


def test_scan_staged_full_detects_ci_change(monkeypatch):
    def fake_run(args, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ".github/workflows/deploy.yml\n"
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = scan_staged_full()
    assert result.has_ci_changes
    assert ".github/workflows/deploy.yml" in result.ci_workflow_changes


def test_staged_check_result_to_dict():
    result = StagedCheckResult()
    d = result.to_dict()
    assert "has_secrets" in d
    assert "has_sensitive_files" in d
    assert "is_clean" in d
    assert d["is_clean"] is True
