"""Tests for the general namespace sandbox (Plan 08)."""

from __future__ import annotations

import stat
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from policy_scout.sandbox.general.prereqs import (
    SandboxPrerequisites,
    check_sandbox_prerequisites,
)
from policy_scout.sandbox.general.overlay_fs import FSChanges, OverlayFS
from policy_scout.sandbox.general.syscall_analyzer import (
    SyscallAnalyzer,
    SyscallReport,
    SensitiveAccess,
)
from policy_scout.sandbox.general.behavior_report import (
    BehaviorFinding,
    BehaviorReport,
    build_behavior_report,
)
from policy_scout.sandbox.general.namespace_sandbox import (
    NamespaceSandbox,
    SandboxRunResult,
    run_general_sandbox,
)


# ─── SandboxPrerequisites ────────────────────────────────────────────────────


class TestCheckSandboxPrerequisites:
    def test_all_available(self):
        with (
            patch("shutil.which", return_value="/usr/bin/unshare"),
            patch("policy_scout.sandbox.general.prereqs._check_user_namespaces", return_value=True),
            patch("policy_scout.sandbox.general.prereqs._check_overlayfs", return_value=True),
        ):
            # patch strace check too
            orig_which = __import__("shutil").which
            with patch("shutil.which", side_effect=lambda x: "/usr/bin/" + x):
                prereqs = check_sandbox_prerequisites()
        assert prereqs.available is True
        assert prereqs.strace_available is True

    def test_unavailable_when_unshare_missing(self):
        with (
            patch("shutil.which", return_value=None),
            patch("policy_scout.sandbox.general.prereqs._check_user_namespaces", return_value=True),
            patch("policy_scout.sandbox.general.prereqs._check_overlayfs", return_value=False),
        ):
            prereqs = check_sandbox_prerequisites()
        assert prereqs.available is False

    def test_unavailable_when_user_namespaces_disabled(self):
        with (
            patch("shutil.which", side_effect=lambda x: "/usr/bin/" + x),
            patch("policy_scout.sandbox.general.prereqs._check_user_namespaces", return_value=False),
            patch("policy_scout.sandbox.general.prereqs._check_overlayfs", return_value=True),
        ):
            prereqs = check_sandbox_prerequisites()
        assert prereqs.available is False

    def test_missing_lists_what_is_absent(self):
        prereqs = SandboxPrerequisites(
            available=False,
            strace_available=False,
            overlayfs_available=False,
            details={"unshare": False, "user_namespaces": False, "overlayfs": False, "strace": False},
        )
        missing = prereqs.missing()
        assert any("unshare" in m for m in missing)
        assert any("namespace" in m for m in missing)

    def test_missing_empty_when_all_ok(self):
        prereqs = SandboxPrerequisites(
            available=True,
            strace_available=True,
            overlayfs_available=True,
            details={"unshare": True, "user_namespaces": True, "overlayfs": True, "strace": True},
        )
        assert prereqs.missing() == []

    def test_to_dict_has_required_keys(self):
        prereqs = SandboxPrerequisites(
            available=True,
            strace_available=False,
            overlayfs_available=True,
            details={"unshare": True, "user_namespaces": True},
        )
        d = prereqs.to_dict()
        assert "available" in d
        assert "strace_available" in d
        assert "overlayfs_available" in d
        assert "missing" in d


# ─── FSChanges / OverlayFS.get_diff ──────────────────────────────────────────


class TestFSChanges:
    def test_total_counts_all_lists(self):
        fc = FSChanges(created=["a", "b"], modified=["c"], deleted=[])
        assert fc.total == 3

    def test_to_dict(self):
        fc = FSChanges(created=["a"], modified=[], deleted=["b"])
        d = fc.to_dict()
        assert d["created"] == ["a"]
        assert d["deleted"] == ["b"]
        assert d["total"] == 2


class TestOverlayFSGetDiff:
    """Unit-test get_diff() by directly populating the upper dir."""

    def _make_overlay(self, tmp: Path) -> OverlayFS:
        ov = OverlayFS(work_dir=tmp, source_dir=tmp / "source")
        ov._upper = tmp / "upper"
        ov._lower = tmp / "lower"
        ov._upper.mkdir(parents=True, exist_ok=True)
        ov._lower.mkdir(parents=True, exist_ok=True)
        return ov

    def test_created_file_no_lower_counterpart(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ov = self._make_overlay(tmp)
            (ov._upper / "newfile.txt").write_text("hello")
            diff = ov.get_diff()
        assert "newfile.txt" in diff.created
        assert not diff.modified
        assert not diff.deleted

    def test_modified_file_exists_in_lower(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ov = self._make_overlay(tmp)
            (ov._lower / "existing.txt").write_text("original")
            (ov._upper / "existing.txt").write_text("changed")
            diff = ov.get_diff()
        assert "existing.txt" in diff.modified
        assert not diff.created

    def test_deleted_file_is_whiteout(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ov = self._make_overlay(tmp)
            whiteout = ov._upper / "deleted.txt"
            whiteout.touch()

            # We can't create actual char devices without root, so intercept
            # stat() only for the whiteout file and pass through for everything else.
            _real_stat = Path.stat

            def _fake_stat(self_path, *args, **kwargs):
                if self_path.name == "deleted.txt":
                    m = MagicMock()
                    m.st_mode = stat.S_IFCHR | 0o000
                    m.st_rdev = 0
                    return m
                return _real_stat(self_path, *args, **kwargs)

            with patch.object(Path, "stat", _fake_stat):
                diff = ov.get_diff()
        assert "deleted.txt" in diff.deleted

    def test_empty_upper_returns_empty_diff(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ov = self._make_overlay(tmp)
            diff = ov.get_diff()
        assert diff.total == 0


# ─── SyscallAnalyzer ─────────────────────────────────────────────────────────


FIXTURE_STRACE = """\
1234 openat(AT_FDCWD, "/home/user/.ssh/id_rsa", O_RDONLY) = 3
1234 openat(AT_FDCWD, "/home/user/project/main.py", O_RDONLY) = 4
1234 execve("/usr/bin/python3", ["python3", "main.py"], /* 10 vars */) = 0
1234 execve("/bin/sh", ["/bin/sh", "-c", "curl http://evil.com"], /* 10 vars */) = 0
1234 connect(3, {sa_family=AF_INET}, 16) = -1
1234 socket(AF_INET, SOCK_STREAM, IPPROTO_TCP) = 5
1234 unlink("/home/user/.aws/credentials") = 0
1234 notavalidsyscall
"""


class TestSyscallAnalyzer:
    def _write_fixture(self, tmp: Path) -> Path:
        f = tmp / "strace.out"
        f.write_text(FIXTURE_STRACE)
        return f

    def test_sensitive_ssh_access_detected(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._write_fixture(Path(td))
            report = SyscallAnalyzer().analyze(trace)
        paths = [a.path for a in report.sensitive_accesses]
        assert any(".ssh" in p for p in paths)

    def test_aws_credentials_deletion_detected(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._write_fixture(Path(td))
            report = SyscallAnalyzer().analyze(trace)
        paths = [a.path for a in report.sensitive_accesses]
        assert any("credentials" in p for p in paths)

    def test_network_attempts_detected(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._write_fixture(Path(td))
            report = SyscallAnalyzer().analyze(trace)
        syscalls = [n.syscall for n in report.network_attempts]
        assert "connect" in syscalls
        assert "socket" in syscalls

    def test_exec_calls_detected_excluding_strace_unshare(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._write_fixture(Path(td))
            report = SyscallAnalyzer().analyze(trace)
        cmds = [e.command for e in report.exec_calls]
        # /bin/sh should be detected, strace/unshare must be excluded
        assert any("/bin/sh" in c for c in cmds)
        assert all("strace" not in c for c in cmds)

    def test_non_sensitive_open_not_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._write_fixture(Path(td))
            report = SyscallAnalyzer().analyze(trace)
        paths = [a.path for a in report.sensitive_accesses]
        assert not any("main.py" in p for p in paths)

    def test_missing_trace_file_returns_empty_report(self):
        report = SyscallAnalyzer().analyze(Path("/nonexistent/strace.out"))
        assert report.total_lines == 0
        assert not report.sensitive_accesses

    def test_total_lines_counts_all(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._write_fixture(Path(td))
            report = SyscallAnalyzer().analyze(trace)
        assert report.total_lines == len(FIXTURE_STRACE.splitlines())

    def test_to_dict_serializable(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._write_fixture(Path(td))
            report = SyscallAnalyzer().analyze(trace)
        import json
        d = report.to_dict()
        json.dumps(d)  # must not raise


# ─── build_behavior_report ───────────────────────────────────────────────────


def _empty_fs() -> FSChanges:
    return FSChanges()


def _empty_syscalls() -> SyscallReport:
    return SyscallReport()


class TestBuildBehaviorReport:
    def test_clean_run_has_no_findings(self):
        report = build_behavior_report(
            command="echo hello",
            exit_code=0,
            timed_out=False,
            stdout="hello\n",
            stderr="",
            fs_changes=_empty_fs(),
            syscall_report=_empty_syscalls(),
        )
        assert report.findings == []
        assert report.worst_severity == "info"

    def test_network_attempt_produces_high_finding(self):
        from policy_scout.sandbox.general.syscall_analyzer import NetworkAttempt
        sc = _empty_syscalls()
        sc.network_attempts.append(NetworkAttempt(syscall="connect", details="..."))
        report = build_behavior_report(
            command="curl evil.com",
            exit_code=0,
            timed_out=False,
            stdout="",
            stderr="",
            fs_changes=_empty_fs(),
            syscall_report=sc,
        )
        assert any(f.category == "network_in_sandbox" for f in report.findings)
        assert report.worst_severity in ("high", "critical")

    def test_ssh_access_produces_critical_finding(self):
        sc = _empty_syscalls()
        sc.sensitive_accesses.append(
            SensitiveAccess(path="/home/user/.ssh/id_rsa", syscall="openat", flags="read")
        )
        report = build_behavior_report(
            command="cat ~/.ssh/id_rsa",
            exit_code=0,
            timed_out=False,
            stdout="",
            stderr="",
            fs_changes=_empty_fs(),
            syscall_report=sc,
        )
        assert any(f.severity == "critical" for f in report.findings)

    def test_file_creation_produces_low_finding(self):
        fs = FSChanges(created=["tmp/output.txt"])
        report = build_behavior_report(
            command="touch tmp/output.txt",
            exit_code=0,
            timed_out=False,
            stdout="",
            stderr="",
            fs_changes=fs,
            syscall_report=_empty_syscalls(),
        )
        assert any(f.category == "fs_created" for f in report.findings)

    def test_file_deletion_produces_high_finding(self):
        fs = FSChanges(deleted=["important.py"])
        report = build_behavior_report(
            command="rm important.py",
            exit_code=0,
            timed_out=False,
            stdout="",
            stderr="",
            fs_changes=fs,
            syscall_report=_empty_syscalls(),
        )
        assert any(f.category == "fs_deleted" for f in report.findings)
        assert any(f.severity == "high" for f in report.findings if f.category == "fs_deleted")

    def test_timeout_produces_medium_finding(self):
        report = build_behavior_report(
            command="sleep 999",
            exit_code=-1,
            timed_out=True,
            stdout="",
            stderr="",
            fs_changes=_empty_fs(),
            syscall_report=_empty_syscalls(),
        )
        assert any(f.category == "timeout" for f in report.findings)

    def test_overlayfs_used_sets_high_confidence(self):
        report = build_behavior_report(
            command="echo",
            exit_code=0,
            timed_out=False,
            stdout="",
            stderr="",
            fs_changes=_empty_fs(),
            syscall_report=_empty_syscalls(),
            overlayfs_used=True,
        )
        assert report.detection_confidence == "high"

    def test_no_overlayfs_sets_medium_confidence(self):
        report = build_behavior_report(
            command="echo",
            exit_code=0,
            timed_out=False,
            stdout="",
            stderr="",
            fs_changes=_empty_fs(),
            syscall_report=_empty_syscalls(),
            overlayfs_used=False,
        )
        assert report.detection_confidence == "medium"

    def test_to_dict_has_required_keys(self):
        import json
        report = build_behavior_report(
            command="ls",
            exit_code=0,
            timed_out=False,
            stdout="file.txt\n",
            stderr="",
            fs_changes=_empty_fs(),
            syscall_report=_empty_syscalls(),
        )
        d = report.to_dict()
        json.dumps(d)  # must be JSON-serializable
        for key in ("command", "exit_code", "findings", "fs_changes", "syscall_report"):
            assert key in d

    def test_worst_severity_ranks_correctly(self):
        from policy_scout.sandbox.general.syscall_analyzer import NetworkAttempt
        sc = _empty_syscalls()
        sc.network_attempts.append(NetworkAttempt(syscall="connect", details=""))
        sc.sensitive_accesses.append(
            SensitiveAccess(path="/root/.ssh/id_rsa", syscall="open", flags="read")
        )
        report = build_behavior_report(
            command="evil",
            exit_code=0,
            timed_out=False,
            stdout="",
            stderr="",
            fs_changes=_empty_fs(),
            syscall_report=sc,
        )
        assert report.worst_severity == "critical"


# ─── NamespaceSandbox platform guard ─────────────────────────────────────────


class TestNamespaceSandboxPlatformGuard:
    """When unshare is unavailable, run() returns an error result, never raises."""

    def test_missing_prereqs_returns_error_result(self):
        unavail = SandboxPrerequisites(
            available=False,
            strace_available=False,
            overlayfs_available=False,
            details={"unshare": False, "user_namespaces": False},
        )
        with patch(
            "policy_scout.sandbox.general.namespace_sandbox.check_sandbox_prerequisites",
            return_value=unavail,
        ):
            sb = NamespaceSandbox()
            result = sb.run(["echo", "hello"])
        assert result.exit_code == -1
        assert result.error
        assert "prerequisites" in result.error.lower()

    def test_run_general_sandbox_propagates_prereq_error(self):
        unavail = SandboxPrerequisites(
            available=False,
            strace_available=False,
            overlayfs_available=False,
            details={"unshare": False, "user_namespaces": False},
        )
        with patch(
            "policy_scout.sandbox.general.namespace_sandbox.check_sandbox_prerequisites",
            return_value=unavail,
        ):
            report = run_general_sandbox(["echo", "hello"])
        # Should return a BehaviorReport even on prereq failure
        assert isinstance(report, BehaviorReport)


# ─── Integration: sandbox a real command (skipped unless unshare available) ──


@pytest.mark.skipif(
    not __import__("shutil").which("unshare"),
    reason="unshare not available on this platform",
)
class TestNamespaceSandboxIntegration:
    def _skip_if_restricted(self, result: SandboxRunResult) -> None:
        if result.exit_code != 0 and result.stderr and any(
            phrase in result.stderr
            for phrase in ("fork failed", "Operation not permitted", "Permission denied")
        ):
            pytest.skip(f"Namespace sandbox restricted on this system: {result.stderr.strip()}")

    def test_echo_runs_and_exits_zero(self):
        sb = NamespaceSandbox(use_strace=False, use_overlayfs=False)
        result = sb.run(["echo", "hello from sandbox"])
        if result.exit_code == -1 and result.error:
            pytest.skip("User namespaces not available")
        self._skip_if_restricted(result)
        assert result.exit_code == 0
        assert "hello from sandbox" in result.stdout

    def test_timeout_is_respected(self):
        sb = NamespaceSandbox(use_strace=False, use_overlayfs=False)
        # Use a quick prereqs check first to avoid a 10s hang before skip
        result = sb.run(["sleep", "10"], timeout=1)
        if result.exit_code == -1 and result.error:
            pytest.skip("User namespaces not available")
        self._skip_if_restricted(result)
        assert result.timed_out is True
