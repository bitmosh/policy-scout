# SPDX-License-Identifier: Apache-2.0
"""Watch mode configuration — paths, trigger patterns, and loader."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class TriggerPattern:
    path_glob: str
    event_types: List[str]
    severity: str
    mode_filter: Optional[str] = None  # "executable" | None

    def matches(self, abs_path: str, event_type: str) -> bool:
        """Return True if this pattern matches the given path and event type."""
        if event_type not in self.event_types:
            return False
        expanded = os.path.expanduser(self.path_glob)
        if fnmatch.fnmatch(abs_path, expanded):
            if self.mode_filter == "executable":
                try:
                    return os.access(abs_path, os.X_OK)
                except OSError:
                    return False
            return True
        return False


@dataclass
class WatchConfig:
    project_paths: List[str] = field(default_factory=list)
    system_paths: List[str] = field(default_factory=list)
    trigger_patterns: List[TriggerPattern] = field(default_factory=list)

    def all_paths(self, mode: str = "both") -> List[str]:
        """Return expanded watch paths for the given mode."""
        paths: List[str] = []
        if mode in ("project", "both"):
            paths.extend(self.project_paths)
        if mode in ("system", "both"):
            paths.extend(self.system_paths)
        expanded = []
        for p in paths:
            exp = os.path.expanduser(p)
            if os.path.exists(exp) or exp == ".":
                expanded.append(exp)
        return expanded

    def matching_patterns(self, abs_path: str, event_type: str) -> List[TriggerPattern]:
        """Return all patterns that match this path/event combination."""
        return [p for p in self.trigger_patterns if p.matches(abs_path, event_type)]


def load_watch_config() -> WatchConfig:
    """Load watch_config.yaml from the data directory."""
    import yaml  # bundled with policy-scout via PyYAML

    data_dir = Path(__file__).parent.parent / "data"
    config_path = data_dir / "watch_config.yaml"

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    project_paths = raw.get("watch_paths", {}).get("project", [])
    system_paths = raw.get("watch_paths", {}).get("system", [])

    trigger_patterns = []
    for tp in raw.get("trigger_patterns", []):
        trigger_patterns.append(TriggerPattern(
            path_glob=tp["path_glob"],
            event_types=tp.get("event_types", []),
            severity=tp.get("severity", "medium"),
            mode_filter=tp.get("mode_filter"),
        ))

    return WatchConfig(
        project_paths=project_paths,
        system_paths=system_paths,
        trigger_patterns=trigger_patterns,
    )
