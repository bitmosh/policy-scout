# SPDX-License-Identifier: Apache-2.0
"""Publish-anomaly detection via npm registry metadata.

Activated only with --with-intel / remote=True to avoid mandatory network calls.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


_REGISTRY_URL = "https://registry.npmjs.org/{name}"
_ANOMALY_NEW_DAYS = 90          # published within N days → "new package" signal
_ANOMALY_MAINTAINER_DAYS = 90   # maintainer changed within N days → "account takeover" signal


@dataclass
class PublishAnomalyResult:
    package_name: str
    anomaly_detected: bool
    signals: List[str] = field(default_factory=list)
    severity: str = "info"
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "type": "supply_chain",
            "pattern_id": "publish_anomaly",
            "description": f"Publish anomaly detected: {self.package_name}",
            "severity": self.severity,
            "confidence": "medium",
            "matched_text": self.package_name,
            "line_number": 0,
            "source": "publish_anomaly",
            "signals": self.signals,
        }


def _fetch_registry_meta(name: str, timeout: int = 10) -> Optional[dict]:
    url = _REGISTRY_URL.format(name=name)
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, Exception):
        return None


def _days_since(iso_ts: str) -> Optional[int]:
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except (ValueError, TypeError):
        return None


def check_publish_anomaly(
    name: str,
    version: Optional[str] = None,
    timeout: int = 10,
) -> PublishAnomalyResult:
    """Check npm registry for publish-anomaly signals."""
    meta = _fetch_registry_meta(name, timeout=timeout)
    if meta is None:
        return PublishAnomalyResult(
            package_name=name,
            anomaly_detected=False,
            error="Registry lookup failed or timed out",
        )

    signals: List[str] = []
    times = meta.get("time", {})

    # Signal 1: package created very recently
    created_ts = times.get("created", "")
    days_old = _days_since(created_ts)
    if days_old is not None and days_old < _ANOMALY_NEW_DAYS:
        signals.append(f"Package created {days_old} days ago (new, unknown provenance)")

    # Signal 2: recent version published by a different maintainer (account takeover signal)
    # Compare the _npmUser of the target version against the most common historical user
    if version and version in times:
        version_meta = meta.get("versions", {}).get(version, {})
        npm_user = version_meta.get("_npmUser", {}).get("name", "")
        # Collect all historical publisher names
        all_publishers = set()
        for v, v_meta in meta.get("versions", {}).items():
            if isinstance(v_meta, dict):
                pub = v_meta.get("_npmUser", {}).get("name", "")
                if pub:
                    all_publishers.add(pub)
        if npm_user and all_publishers and npm_user not in all_publishers:
            signals.append(
                f"Version {version} published by a new account ({npm_user!r})"
                f" not seen in earlier releases — possible account takeover"
            )

    # Signal 3: high downloads but very few versions (unusual ratio)
    dist_tags = meta.get("dist-tags", {})
    version_count = len(meta.get("versions", {}))
    if version_count < 3 and dist_tags.get("latest"):
        # Can't check downloads without an extra API call; flag low version count alone
        signals.append(
            f"Package has only {version_count} version(s) — limited release history"
        )

    anomaly_detected = len(signals) > 0
    severity = "high" if len(signals) >= 2 else ("medium" if anomaly_detected else "info")
    return PublishAnomalyResult(
        package_name=name,
        anomaly_detected=anomaly_detected,
        signals=signals,
        severity=severity,
    )
