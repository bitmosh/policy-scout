"""OSV (Open Source Vulnerabilities) remote adapter — stdlib only, no new deps."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import List, Optional

from ..adapter import Advisory, IntelResult
from .cache import IntelCache, cache_key

_OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
_TIMEOUT = 5  # seconds

# OSV ecosystem names differ slightly from our internal names
_ECOSYSTEM_MAP = {
    "npm": "npm",
    "pypi": "PyPI",
    "cargo": "crates.io",
    "rubygems": "RubyGems",
    "go": "Go",
}

_cache = IntelCache()


def _network_available() -> bool:
    try:
        urllib.request.urlopen("https://api.osv.dev", timeout=2)
        return True
    except Exception:
        return False


def _query_osv(ecosystem: str, name: str, version: Optional[str]) -> List[Advisory]:
    osv_eco = _ECOSYSTEM_MAP.get(ecosystem, ecosystem)
    query: dict = {"package": {"name": name, "ecosystem": osv_eco}}
    if version:
        query["version"] = version

    payload = json.dumps({"queries": [query]}).encode()
    req = urllib.request.Request(
        _OSV_BATCH_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        body = json.loads(resp.read())

    results = body.get("results", [{}])
    vulns = results[0].get("vulns", []) if results else []

    advisories = []
    for vuln in vulns:
        vuln_id = vuln.get("id", "UNKNOWN")
        summary = vuln.get("summary", vuln_id)

        # Parse severity from CVSS
        cvss_val: Optional[float] = None
        severity_str = "medium"
        for sev in vuln.get("severity", []):
            if sev.get("type") in ("CVSS_V3", "CVSS_V2"):
                raw = sev.get("score", "")
                try:
                    cvss_val = float(raw.split("/CVSS:")[0]) if "/" in raw else float(raw)
                except (ValueError, TypeError):
                    pass
        for db_sev in vuln.get("database_specific", {}).get("severity", []):
            s = str(db_sev).lower()
            if s in ("critical", "high", "medium", "low"):
                severity_str = s
                break
        if cvss_val is not None:
            if cvss_val >= 9.0:
                severity_str = "critical"
            elif cvss_val >= 7.0:
                severity_str = "high"
            elif cvss_val >= 4.0:
                severity_str = "medium"
            else:
                severity_str = "low"

        # Find fixed version
        fixed: Optional[str] = None
        affected_summary = ""
        for affected in vuln.get("affected", []):
            ranges = affected.get("ranges", [])
            for r in ranges:
                for event in r.get("events", []):
                    if "fixed" in event:
                        fixed = event["fixed"]
                        break
            versions = affected.get("versions", [])
            if versions:
                affected_summary = f"<= {versions[-1]}" if not fixed else f"< {fixed}"

        advisories.append(Advisory(
            advisory_id=vuln_id,
            title=summary[:200],
            severity=severity_str,
            cvss=cvss_val,
            affected_versions=affected_summary or "see advisory",
            fixed_version=fixed,
            source="osv",
        ))

    return advisories


class OsvAdapter:
    """Remote adapter: OSV vulnerability database."""

    def enrich_package(
        self,
        ecosystem: str,
        name: str,
        version: Optional[str] = None,
    ) -> IntelResult:
        ck = cache_key(ecosystem, name, version)
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
                    source="osv",
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
            advisories = _query_osv(ecosystem, name, version)
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
                source="remote:osv",
            )
        except Exception as exc:
            return IntelResult(
                package_name=name,
                ecosystem=ecosystem,
                confidence="low",
                source="remote:osv",
                error=f"OSV lookup failed: {exc}",
            )
