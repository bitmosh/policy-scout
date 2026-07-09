# SPDX-License-Identifier: Apache-2.0
"""Filesystem watcher — inotifywait primary, polling fallback."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Iterator, List, Optional


@dataclass
class FSEvent:
    path: str
    event_type: str       # create | modify | attrib | moved_to | close_write | delete
    timestamp: str
    detection_confidence: str = "high"  # "high" (inotify) | "low" (polling)


def _utcnow_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _inotifywait_available() -> bool:
    return shutil.which("inotifywait") is not None


def _is_linux() -> bool:
    return platform.system() == "Linux"


class InotifyWatcher:
    """Wraps inotifywait for real-time FS event delivery."""

    INOTIFY_EVENTS = "create,modify,attrib,moved_to,close_write,delete"
    FORMAT = "%w%f\t%e"

    def __init__(self, paths: List[str]):
        self._paths = [p for p in paths if os.path.exists(p) or p == "."]
        self._proc: Optional[subprocess.Popen] = None  # type: ignore[type-arg]

    def start(self) -> None:
        if not self._paths:
            return
        cmd = [
            "inotifywait",
            "--monitor",
            "--recursive",
            "--format", self.FORMAT,
            "--event", self.INOTIFY_EVENTS,
        ] + self._paths
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def watch(self) -> Iterator[FSEvent]:
        """Yield FSEvents continuously until stop() is called."""
        self.start()
        if self._proc is None or self._proc.stdout is None:
            return
        try:
            for line in self._proc.stdout:
                line = line.rstrip("\n")
                if "\t" not in line:
                    continue
                path_part, event_part = line.split("\t", 1)
                event_type = _normalize_inotify_event(event_part)
                if event_type:
                    yield FSEvent(
                        path=os.path.abspath(path_part),
                        event_type=event_type,
                        timestamp=_utcnow_iso(),
                        detection_confidence="high",
                    )
        except (ValueError, OSError):
            pass
        finally:
            self.stop()


def _normalize_inotify_event(raw: str) -> Optional[str]:
    """Map inotify event flags to our simplified event_type vocabulary."""
    raw_upper = raw.upper()
    if "CREATE" in raw_upper or "MOVED_TO" in raw_upper:
        return "create"
    if "CLOSE_WRITE" in raw_upper or "MODIFY" in raw_upper:
        return "modify"
    if "ATTRIB" in raw_upper:
        return "attrib"
    if "DELETE" in raw_upper:
        return "delete"
    return None


class PollingWatcher:
    """Fallback watcher using os.stat polling. Low confidence."""

    def __init__(self, paths: List[str], interval: float = 2.0):
        self._paths = paths
        self._interval = interval
        self._snapshot: dict[str, tuple[float, int]] = {}  # path -> (mtime, size)
        self._running = True  # set to False by stop() before or during watch()

    def _scan(self, root: str) -> dict[str, tuple[float, int]]:
        """Return {path: (mtime, size)} for all files under root."""
        result: dict[str, tuple[float, int]] = {}
        if os.path.isfile(root):
            try:
                st = os.stat(root)
                result[root] = (st.st_mtime, st.st_size)
            except OSError:
                pass
            return result
        for dirpath, _, files in os.walk(root):
            for fname in files:
                fpath = os.path.join(dirpath, fname)
                try:
                    st = os.stat(fpath)
                    result[fpath] = (st.st_mtime, st.st_size)
                except OSError:
                    pass
        return result

    def _build_snapshot(self) -> dict[str, tuple[float, int]]:
        combined: dict[str, tuple[float, int]] = {}
        for p in self._paths:
            combined.update(self._scan(os.path.expanduser(p)))
        return combined

    def watch(self) -> Iterator[FSEvent]:
        """Yield FSEvents by comparing successive snapshots."""
        if not self._running:
            return
        self._snapshot = self._build_snapshot()
        while self._running:
            time.sleep(self._interval)
            current = self._build_snapshot()
            now = _utcnow_iso()

            for path, (mtime, size) in current.items():
                if path not in self._snapshot:
                    yield FSEvent(path=path, event_type="create", timestamp=now,
                                  detection_confidence="low")
                else:
                    prev_mtime, prev_size = self._snapshot[path]
                    if mtime != prev_mtime or size != prev_size:
                        yield FSEvent(path=path, event_type="modify", timestamp=now,
                                      detection_confidence="low")

            for path in list(self._snapshot):
                if path not in current:
                    yield FSEvent(path=path, event_type="delete", timestamp=now,
                                  detection_confidence="low")

            self._snapshot = current

    def stop(self) -> None:
        self._running = False


def make_watcher(paths: List[str], poll_interval: float = 2.0) -> "InotifyWatcher | PollingWatcher":
    """Return the best available watcher for the current platform."""
    if _is_linux() and _inotifywait_available():
        return InotifyWatcher(paths)
    return PollingWatcher(paths, interval=poll_interval)


def platform_watch_supported() -> tuple[bool, str]:
    """Return (supported, reason) for the current platform."""
    if not _is_linux():
        return False, f"watch mode requires inotifywait (Linux only); current platform: {platform.system()}"
    if not _inotifywait_available():
        return False, "inotifywait not found on PATH — install inotify-tools (e.g. apt install inotify-tools)"
    return True, "inotifywait available"
