"""Tests for fs_watcher: FSEvent, PollingWatcher, platform helpers."""

import os
import tempfile
import time
from pathlib import Path

import pytest

from policy_scout.watch.fs_watcher import (
    FSEvent,
    PollingWatcher,
    make_watcher,
    platform_watch_supported,
)


def test_fsevent_dataclass():
    ev = FSEvent(path="/tmp/foo.sh", event_type="create", timestamp="2026-06-10T00:00:00Z")
    assert ev.path == "/tmp/foo.sh"
    assert ev.event_type == "create"
    assert ev.detection_confidence == "high"


def test_polling_watcher_detects_new_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = PollingWatcher(paths=[tmpdir], interval=0.05)
        events = []

        import threading

        def _collect():
            for ev in watcher.watch():
                events.append(ev)
                if len(events) >= 1:
                    watcher.stop()
                    break

        t = threading.Thread(target=_collect, daemon=True)
        t.start()
        time.sleep(0.12)  # let first snapshot settle
        Path(tmpdir, "newfile.txt").write_text("hello")
        t.join(timeout=2)

        assert len(events) >= 1
        assert events[0].event_type == "create"
        assert events[0].detection_confidence == "low"


def test_polling_watcher_detects_modification():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir, "existing.txt")
        target.write_text("original")

        watcher = PollingWatcher(paths=[tmpdir], interval=0.05)
        events = []

        import threading

        def _collect():
            for ev in watcher.watch():
                events.append(ev)
                if len(events) >= 1:
                    watcher.stop()
                    break

        t = threading.Thread(target=_collect, daemon=True)
        t.start()
        time.sleep(0.15)  # let first snapshot settle past interval
        target.write_text("modified content now")
        t.join(timeout=2)

        assert any(ev.event_type == "modify" for ev in events)


def test_polling_watcher_detects_deletion():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir, "todelete.txt")
        target.write_text("bye")

        watcher = PollingWatcher(paths=[tmpdir], interval=0.05)
        events = []

        import threading

        def _collect():
            for ev in watcher.watch():
                events.append(ev)
                if len(events) >= 1:
                    watcher.stop()
                    break

        t = threading.Thread(target=_collect, daemon=True)
        t.start()
        time.sleep(0.15)
        target.unlink()
        t.join(timeout=2)

        assert any(ev.event_type == "delete" for ev in events)


def test_polling_watcher_stop():
    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = PollingWatcher(paths=[tmpdir], interval=0.05)
        watcher.stop()
        # watch() should return immediately since _running is False
        count = 0
        for _ in watcher.watch():
            count += 1
            break
        assert count == 0


def test_make_watcher_returns_polling_fallback_on_nonlinux(monkeypatch):
    monkeypatch.setattr("policy_scout.watch.fs_watcher._is_linux", lambda: False)
    w = make_watcher(["."])
    assert isinstance(w, PollingWatcher)


def test_platform_watch_supported_nonlinux(monkeypatch):
    monkeypatch.setattr("policy_scout.watch.fs_watcher._is_linux", lambda: False)
    supported, reason = platform_watch_supported()
    assert not supported
    assert "inotifywait" in reason.lower() or "linux" in reason.lower()
