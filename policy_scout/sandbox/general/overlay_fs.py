# SPDX-License-Identifier: Apache-2.0
"""OverlayFS mount management for filesystem change capture."""

from __future__ import annotations

import shutil
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class FSChanges:
    created: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.modified) + len(self.deleted)

    def to_dict(self) -> dict:
        return {
            "created": self.created,
            "modified": self.modified,
            "deleted": self.deleted,
            "total": self.total,
        }


class OverlayFS:
    """Manage an overlayfs mount for a sandbox run.

    Lower layer = bind-mount of the project directory (read-only view).
    Upper layer = where all writes land; diffed after the run.
    Merged layer = unified view seen by the sandboxed process.
    """

    def __init__(self, work_dir: Path, source_dir: Path | None = None) -> None:
        self._work_dir = work_dir
        self._source_dir = source_dir or Path.cwd()
        self._lower = work_dir / "lower"
        self._upper = work_dir / "upper"
        self._work = work_dir / "work"
        self._merged = work_dir / "merged"
        self._mounted = False

    @property
    def merged(self) -> Path:
        return self._merged

    def setup(self) -> Path:
        """Create directories and mount the overlay. Returns merged path."""
        for d in [self._lower, self._upper, self._work, self._merged]:
            d.mkdir(parents=True, exist_ok=True)

        # Bind-mount source dir as lower layer
        subprocess.run(
            ["mount", "--bind", str(self._source_dir), str(self._lower)],
            check=True, capture_output=True,
        )
        # Mount overlay
        opts = (
            f"lowerdir={self._lower},"
            f"upperdir={self._upper},"
            f"workdir={self._work}"
        )
        subprocess.run(
            ["mount", "-t", "overlay", "overlay", "-o", opts, str(self._merged)],
            check=True, capture_output=True,
        )
        self._mounted = True
        return self._merged

    def get_diff(self) -> FSChanges:
        """Walk upper dir; everything written during the sandbox run is here."""
        created, modified, deleted = [], [], []
        if not self._upper.exists():
            return FSChanges()
        for path in self._upper.rglob("*"):
            if path.is_dir():
                continue
            try:
                st = path.stat()
                rel = str(path.relative_to(self._upper))
                # Overlay whiteout = char device 0,0
                if stat.S_ISCHR(st.st_mode) and st.st_rdev == 0:
                    deleted.append(rel)
                elif (self._lower / rel).exists():
                    modified.append(rel)
                else:
                    created.append(rel)
            except OSError:
                pass
        return FSChanges(created=created, modified=modified, deleted=deleted)

    def teardown(self) -> None:
        """Unmount and clean up. Best-effort."""
        if self._mounted:
            subprocess.run(["umount", str(self._merged)], check=False, capture_output=True)
            subprocess.run(["umount", str(self._lower)], check=False, capture_output=True)
            self._mounted = False

    def __enter__(self) -> "OverlayFS":
        self.setup()
        return self

    def __exit__(self, *_) -> None:
        self.teardown()
