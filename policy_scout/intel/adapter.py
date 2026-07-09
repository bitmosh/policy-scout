# SPDX-License-Identifier: Apache-2.0
"""ThreatIntelAdapter protocol, IntelResult dataclass, and AdapterChain."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol, runtime_checkable


@dataclass
class Advisory:
    """A known vulnerability or advisory for a package."""
    advisory_id: str          # CVE-XXXX-XXXX, GHSA-xxx, OSV-xxx
    title: str
    severity: str             # "critical" | "high" | "medium" | "low"
    cvss: Optional[float]
    affected_versions: str    # e.g. "<4.17.21"
    fixed_version: Optional[str]
    source: str               # "osv" | "npm_advisory" | "known_bad"


@dataclass
class TyposquatCandidate:
    """A known package that a given name is suspiciously close to."""
    original: str         # the legitimate package name
    distance: int         # edit distance
    technique: str        # "digit_sub" | "homoglyph" | "extra_char" | "edit_distance"


@dataclass
class IntelResult:
    """Aggregated threat intelligence for a package."""
    package_name: str
    ecosystem: str                                    # "npm" | "pypi" | "cargo"
    advisories: List[Advisory] = field(default_factory=list)
    typosquatting_candidates: List[TyposquatCandidate] = field(default_factory=list)
    known_bad: bool = False
    known_bad_evidence: Optional[str] = None
    lockfile_integrity_ok: Optional[bool] = None      # None = not checked
    publish_anomaly: Optional[bool] = None             # None = not checked
    confidence: str = "high"                          # "high" | "medium" | "low"
    source: str = "local"                             # "local" | "remote:osv" | "cache"
    error: Optional[str] = None                       # set if lookup partially failed

    @property
    def has_findings(self) -> bool:
        return bool(
            self.advisories
            or self.typosquatting_candidates
            or self.known_bad
            or self.lockfile_integrity_ok is False
        )

    def top_severity(self) -> str:
        if self.known_bad:
            return "critical"
        order = ["critical", "high", "medium", "low", "info"]
        severities = [a.severity for a in self.advisories]
        for level in order:
            if level in severities:
                return level
        if self.typosquatting_candidates:
            return "high"
        return "info"

    def to_dict(self) -> dict:
        return {
            "package_name": self.package_name,
            "ecosystem": self.ecosystem,
            "advisories": [
                {
                    "advisory_id": a.advisory_id,
                    "title": a.title,
                    "severity": a.severity,
                    "cvss": a.cvss,
                    "affected_versions": a.affected_versions,
                    "fixed_version": a.fixed_version,
                    "source": a.source,
                }
                for a in self.advisories
            ],
            "typosquatting_candidates": [
                {
                    "original": c.original,
                    "distance": c.distance,
                    "technique": c.technique,
                }
                for c in self.typosquatting_candidates
            ],
            "known_bad": self.known_bad,
            "known_bad_evidence": self.known_bad_evidence,
            "lockfile_integrity_ok": self.lockfile_integrity_ok,
            "publish_anomaly": self.publish_anomaly,
            "confidence": self.confidence,
            "source": self.source,
            "error": self.error,
        }


@runtime_checkable
class ThreatIntelAdapter(Protocol):
    """Protocol for all threat intel adapters."""

    def enrich_package(
        self,
        ecosystem: str,
        name: str,
        version: Optional[str] = None,
    ) -> IntelResult: ...


def _empty_result(ecosystem: str, name: str) -> IntelResult:
    return IntelResult(package_name=name, ecosystem=ecosystem)


def _merge_results(base: IntelResult, extra: IntelResult) -> IntelResult:
    """Merge extra into base, deduplicating advisories by ID."""
    seen_ids = {a.advisory_id for a in base.advisories}
    for adv in extra.advisories:
        if adv.advisory_id not in seen_ids:
            base.advisories.append(adv)
            seen_ids.add(adv.advisory_id)

    seen_originals = {c.original for c in base.typosquatting_candidates}
    for cand in extra.typosquatting_candidates:
        if cand.original not in seen_originals:
            base.typosquatting_candidates.append(cand)
            seen_originals.add(cand.original)

    if extra.known_bad:
        base.known_bad = True
        base.known_bad_evidence = extra.known_bad_evidence

    if extra.lockfile_integrity_ok is False:
        base.lockfile_integrity_ok = False
    elif extra.lockfile_integrity_ok is True and base.lockfile_integrity_ok is None:
        base.lockfile_integrity_ok = True

    # Confidence: take the lower of the two
    conf_order = {"high": 2, "medium": 1, "low": 0}
    if conf_order.get(extra.confidence, 1) < conf_order.get(base.confidence, 1):
        base.confidence = extra.confidence

    # Source: join unique sources
    sources = {s.strip() for s in base.source.split(",") if s.strip()}
    sources.add(extra.source)
    base.source = ", ".join(sorted(sources))

    return base


class AdapterChain:
    """Runs all registered adapters and merges results."""

    def __init__(self, adapters: Optional[List[ThreatIntelAdapter]] = None):
        self._adapters: List[ThreatIntelAdapter] = adapters or []

    def register(self, adapter: ThreatIntelAdapter) -> None:
        self._adapters.append(adapter)

    def enrich_package(
        self,
        ecosystem: str,
        name: str,
        version: Optional[str] = None,
    ) -> IntelResult:
        result = _empty_result(ecosystem, name)
        for adapter in self._adapters:
            try:
                partial = adapter.enrich_package(ecosystem, name, version)
                result = _merge_results(result, partial)
            except Exception as exc:
                if result.error:
                    result.error += f"; {exc}"
                else:
                    result.error = str(exc)
                result.confidence = "low"
        return result


def extract_packages(command_family: str, subcommand: str, args: List[str]) -> List[tuple[str, str]]:
    """Extract (ecosystem, package_name) pairs from parsed command args.

    Returns empty list if the command doesn't look like a package install.
    """
    PKG_MANAGERS: dict[str, str] = {
        "npm": "npm",
        "yarn": "npm",
        "pnpm": "npm",
        "bun": "npm",
        "pip": "pypi",
        "pip3": "pypi",
        "uv": "pypi",
        "poetry": "pypi",
        "cargo": "cargo",
        "gem": "rubygems",
    }
    INSTALL_SUBCOMMANDS = {"install", "add", "i", "require"}

    ecosystem = PKG_MANAGERS.get(command_family)
    if not ecosystem:
        return []
    if subcommand.lower() not in INSTALL_SUBCOMMANDS:
        return []

    packages = []
    for arg in args[1:]:  # skip subcommand itself
        if arg.startswith("-"):
            continue
        # Strip version specifier: lodash@4.17.21 -> lodash
        name = arg.split("@")[0].split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0]
        name = name.strip()
        if name:
            packages.append((ecosystem, name))
    return packages


def build_default_chain(remote: bool = False) -> AdapterChain:
    """Build the standard adapter chain (local always, remote opt-in)."""
    from .local.typosquatting import TyposquattingAdapter
    from .local.known_bad import KnownBadAdapter
    from .local.lockfile_integrity import LockfileIntegrityAdapter

    chain = AdapterChain()
    chain.register(KnownBadAdapter())
    chain.register(TyposquattingAdapter())
    chain.register(LockfileIntegrityAdapter())

    if remote:
        from .remote.osv import OsvAdapter
        from .remote.npm_advisories import NpmAdvisoryAdapter
        chain.register(OsvAdapter())
        chain.register(NpmAdvisoryAdapter())

    return chain
