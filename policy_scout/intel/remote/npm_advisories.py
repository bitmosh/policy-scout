# SPDX-License-Identifier: Apache-2.0
"""npm security advisory API adapter — stdlib only."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import List, Optional

from ..adapter import Advisory, IntelResult
from .cache import IntelCache, cache_key

_NPM_AUDIT_URL = "https://registry.npmjs.org/-/npm/v1/security/audits"
_TIMEOUT = 5

_cache = IntelCache()


def _query_npm_audit(name: str, version: Optional[str]) -> List[Advisory]:
    """Call the npm audit API for a single package."""
    ver = version or "latest"
    payload = json.dumps({
        "name": f"__policy_scout_probe_{name}__",
        "version": "1.0.0",
        "requires": {name: ver},
        "dependencies": {
            name: {"version": ver},
        },
    }).encode()

    req = urllib.request.Request(
        _NPM_AUDIT_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        body = json.loads(resp.read())

    advisories: List[Advisory] = []
    for advisory_id, adv in body.get("advisories", {}).items():
        sev = str(adv.get("severity", "moderate")).lower()
        if sev == "moderate":
            sev = "medium"
        elif sev not in ("critical", "high", "medium", "low"):
            sev = "medium"

        advisories.append(Advisory(
            advisory_id=f"NPMSA-{advisory_id}",
            title=adv.get("title", f"npm advisory {advisory_id}")[:200],
            severity=sev,
            cvss=adv.get("cvss", {}).get("score"),
            affected_versions=adv.get("vulnerable_versions", ""),
            fixed_version=adv.get("patched_versions") or None,
            source="npm_advisory",
        ))

    return advisories


class NpmAdvisoryAdapter:
    """Remote adapter: npm security advisory database."""

    def enrich_package(
        self,
        ecosystem: str,
        name: str,
        version: Optional[str] = None,
    ) -> IntelResult:
        if ecosystem != "npm":
            return IntelResult(package_name=name, ecosystem=ecosystem,
                               confidence="high", source="remote:npm_advisory")

        ck = f"npm_advisory:{cache_key(ecosystem, name, version)}"
        cached = _cache.get(ck)
        if cached is not None:
            advisories = [
                Advisory(
                    advisory_id=a["advisory_id"],
                    title=a["title"],
                    severity=a["severity"],
                    cvss=a.get("cvss"),
                    affected_versions=a.get("affected_versions", ""),
                    fixed_version=a.get("fixed_version"),
                    source="npm_advisory",
                )
                for a in cached.get("advisories", [])
            ]
            return IntelResult(
                package_name=name,
                ecosystem=ecosystem,
                advisories=advisories,
                confidence="high",
                source="cache",
            )

        try:
            advisories = _query_npm_audit(name, version)
            _cache.set(ck, {"advisories": [
                {
                    "advisory_id": a.advisory_id,
                    "title": a.title,
                    "severity": a.severity,
                    "cvss": a.cvss,
                    "affected_versions": a.affected_versions,
                    "fixed_version": a.fixed_version,
                }
                for a in advisories
            ]})
            return IntelResult(
                package_name=name,
                ecosystem=ecosystem,
                advisories=advisories,
                confidence="high",
                source="remote:npm_advisory",
            )
        except Exception as exc:
            return IntelResult(
                package_name=name,
                ecosystem=ecosystem,
                confidence="low",
                source="remote:npm_advisory",
                error=f"npm advisory lookup failed: {exc}",
            )
