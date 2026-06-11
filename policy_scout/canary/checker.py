"""Verify canary file state and search audit log for canary token hits."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .installer import CANARY_FILENAME, canary_path_for
from .tokens import extract_canary_token


@dataclass
class CanaryStatus:
    installed: bool
    path: str = ""
    token: str = ""
    audit_hits: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "installed": self.installed,
            "path": self.path,
            "token": self.token,
            "audit_hit_count": len(self.audit_hits),
            "audit_hits": self.audit_hits[:10],
        }


def check_canary_status(project_root: str | Path | None = None) -> CanaryStatus:
    """Return canary installation state and any audit log hits for the token."""
    canary_path = canary_path_for(project_root)

    if not canary_path.exists():
        return CanaryStatus(installed=False)

    content = canary_path.read_text()
    token = extract_canary_token(content)
    if not token:
        return CanaryStatus(installed=True, path=str(canary_path), token="")

    hits = _search_audit_log(token)
    return CanaryStatus(
        installed=True,
        path=str(canary_path),
        token=token,
        audit_hits=hits,
    )


def _search_audit_log(token: str) -> List[dict]:
    """Scan the JSONL audit log for events whose data field contains the token."""
    log_path = Path.home() / ".local" / "share" / "policy-scout" / "audit.jsonl"

    env_path_str = __import__("os").environ.get("POLICY_SCOUT_AUDIT_PATH")
    if env_path_str:
        log_path = Path(env_path_str)

    if not log_path.exists():
        return []

    hits: List[dict] = []
    try:
        for line in log_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            if token not in line:
                continue
            try:
                entry = json.loads(line)
                hits.append({
                    "event_id": entry.get("event_id", ""),
                    "event_type": entry.get("event_type", ""),
                    "timestamp": entry.get("timestamp", ""),
                    "summary": entry.get("summary", ""),
                })
            except json.JSONDecodeError:
                hits.append({"raw": line[:200]})
    except OSError:
        pass

    return hits
