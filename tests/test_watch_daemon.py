# SPDX-License-Identifier: Apache-2.0
"""Tests for watch daemon PID lifecycle helpers."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import policy_scout.watch.daemon as daemon_mod


@pytest.fixture(autouse=True)
def isolated_pid_dir(tmp_path, monkeypatch):
    """Redirect PID/log files into a temp dir for each test."""
    monkeypatch.setattr(daemon_mod, "_PID_DIR", tmp_path)
    monkeypatch.setattr(daemon_mod, "_PID_FILE", tmp_path / "watch.pid")
    monkeypatch.setattr(daemon_mod, "_LOG_FILE", tmp_path / "watch.log")


def test_read_pid_missing():
    assert daemon_mod._read_pid() is None


def test_write_and_read_pid():
    daemon_mod._write_pid(12345)
    assert daemon_mod._read_pid() == 12345


def test_clear_pid():
    daemon_mod._write_pid(99)
    daemon_mod._clear_pid()
    assert daemon_mod._read_pid() is None


def test_clear_pid_nonexistent_is_safe():
    daemon_mod._clear_pid()  # no file — should not raise


def test_daemon_status_no_pid():
    status = daemon_mod.daemon_status()
    assert status["running"] is False
    assert status["pid"] is None


def test_daemon_status_stale_pid():
    daemon_mod._write_pid(999999999)  # PID that doesn't exist
    status = daemon_mod.daemon_status()
    assert status["running"] is False
    assert status.get("stale") is True


def test_daemon_status_live_pid():
    daemon_mod._write_pid(os.getpid())  # current process is definitely alive
    status = daemon_mod.daemon_status()
    assert status["running"] is True
    assert status["pid"] == os.getpid()


def test_start_daemon_already_running():
    daemon_mod._write_pid(os.getpid())
    result = daemon_mod.start_daemon()
    assert result["ok"] is False
    assert "already running" in result["error"]


def test_stop_daemon_no_pid():
    result = daemon_mod.stop_daemon()
    assert result["ok"] is False
    assert "PID file" in result["error"]


def test_stop_daemon_stale_pid():
    daemon_mod._write_pid(999999999)
    result = daemon_mod.stop_daemon()
    assert result["ok"] is False
    assert "not alive" in result["error"]
    assert daemon_mod._read_pid() is None  # stale file cleared


def test_tail_logs_empty():
    lines = daemon_mod.tail_logs()
    assert lines == []


def test_tail_logs_returns_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(daemon_mod, "_LOG_FILE", tmp_path / "watch.log")
    log = tmp_path / "watch.log"
    log.write_text("line1\nline2\nline3\n")
    lines = daemon_mod.tail_logs(n=2)
    assert lines == ["line2", "line3"]


def test_pid_is_alive_current():
    assert daemon_mod._pid_is_alive(os.getpid()) is True


def test_pid_is_alive_nonexistent():
    assert daemon_mod._pid_is_alive(999999999) is False
