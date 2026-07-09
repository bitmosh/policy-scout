# SPDX-License-Identifier: Apache-2.0
"""Tests for AdapterChain, IntelResult, and extract_packages."""

from policy_scout.intel.adapter import (
    Advisory,
    AdapterChain,
    IntelResult,
    TyposquatCandidate,
    _merge_results,
    extract_packages,
)


class TestIntelResult:
    def test_has_findings_known_bad(self):
        r = IntelResult(package_name="evil", ecosystem="npm", known_bad=True)
        assert r.has_findings is True

    def test_has_findings_typosquat(self):
        r = IntelResult(
            package_name="expres",
            ecosystem="npm",
            typosquatting_candidates=[TyposquatCandidate("express", 1, "edit_distance")],
        )
        assert r.has_findings is True

    def test_has_findings_advisory(self):
        r = IntelResult(
            package_name="lodash",
            ecosystem="npm",
            advisories=[Advisory("CVE-2021-1234", "Prototype pollution", "high", 7.5, "<4.17.21", "4.17.21", "osv")],
        )
        assert r.has_findings is True

    def test_has_findings_clean(self):
        r = IntelResult(package_name="lodash", ecosystem="npm")
        assert r.has_findings is False

    def test_top_severity_known_bad(self):
        r = IntelResult(package_name="evil", ecosystem="npm", known_bad=True)
        assert r.top_severity() == "critical"

    def test_top_severity_advisory(self):
        r = IntelResult(
            package_name="lodash",
            ecosystem="npm",
            advisories=[Advisory("CVE-x", "title", "high", 7.5, "<4", "4", "osv")],
        )
        assert r.top_severity() == "high"

    def test_top_severity_typosquat(self):
        r = IntelResult(
            package_name="1odash",
            ecosystem="npm",
            typosquatting_candidates=[TyposquatCandidate("lodash", 1, "digit_sub")],
        )
        assert r.top_severity() == "high"

    def test_to_dict_round_trip(self):
        r = IntelResult(
            package_name="lodash",
            ecosystem="npm",
            known_bad=False,
            confidence="high",
            source="local",
        )
        d = r.to_dict()
        assert d["package_name"] == "lodash"
        assert d["ecosystem"] == "npm"
        assert isinstance(d["advisories"], list)


class TestMergeResults:
    def test_deduplicates_advisories(self):
        base = IntelResult(
            package_name="pkg",
            ecosystem="npm",
            advisories=[Advisory("CVE-1", "t", "high", 7.0, "<1", "1", "osv")],
        )
        extra = IntelResult(
            package_name="pkg",
            ecosystem="npm",
            advisories=[
                Advisory("CVE-1", "t", "high", 7.0, "<1", "1", "osv"),  # dup
                Advisory("CVE-2", "t2", "medium", 5.0, "<2", "2", "osv"),  # new
            ],
        )
        merged = _merge_results(base, extra)
        assert len(merged.advisories) == 2
        ids = {a.advisory_id for a in merged.advisories}
        assert ids == {"CVE-1", "CVE-2"}

    def test_known_bad_propagates(self):
        base = IntelResult(package_name="p", ecosystem="npm")
        extra = IntelResult(package_name="p", ecosystem="npm", known_bad=True,
                            known_bad_evidence="evil!")
        merged = _merge_results(base, extra)
        assert merged.known_bad is True
        assert merged.known_bad_evidence == "evil!"

    def test_confidence_takes_lower(self):
        base = IntelResult(package_name="p", ecosystem="npm", confidence="high")
        extra = IntelResult(package_name="p", ecosystem="npm", confidence="low")
        merged = _merge_results(base, extra)
        assert merged.confidence == "low"

    def test_lockfile_false_propagates(self):
        base = IntelResult(package_name="p", ecosystem="npm", lockfile_integrity_ok=None)
        extra = IntelResult(package_name="p", ecosystem="npm", lockfile_integrity_ok=False)
        merged = _merge_results(base, extra)
        assert merged.lockfile_integrity_ok is False


class TestAdapterChain:
    def test_empty_chain_returns_empty_result(self):
        chain = AdapterChain()
        result = chain.enrich_package("npm", "lodash")
        assert result.package_name == "lodash"
        assert result.has_findings is False

    def test_failing_adapter_sets_error_and_low_confidence(self):
        class BrokenAdapter:
            def enrich_package(self, ecosystem, name, version=None):
                raise RuntimeError("network down")

        chain = AdapterChain([BrokenAdapter()])
        result = chain.enrich_package("npm", "lodash")
        assert result.confidence == "low"
        assert result.error is not None

    def test_chain_merges_multiple_adapters(self):
        class AdvisoryAdapter:
            def enrich_package(self, ecosystem, name, version=None):
                return IntelResult(
                    package_name=name,
                    ecosystem=ecosystem,
                    advisories=[Advisory("CVE-A", "t", "high", 7.0, "<1", "1", "test")],
                )

        class BadAdapter:
            def enrich_package(self, ecosystem, name, version=None):
                return IntelResult(
                    package_name=name,
                    ecosystem=ecosystem,
                    known_bad=True,
                    known_bad_evidence="test evidence",
                )

        chain = AdapterChain([AdvisoryAdapter(), BadAdapter()])
        result = chain.enrich_package("npm", "evil")
        assert len(result.advisories) == 1
        assert result.known_bad is True


class TestExtractPackages:
    def test_npm_install(self):
        pkgs = extract_packages("npm", "install", ["install", "lodash"])
        assert ("npm", "lodash") in pkgs

    def test_npm_i_shorthand(self):
        pkgs = extract_packages("npm", "i", ["i", "express"])
        assert ("npm", "express") in pkgs

    def test_version_stripped(self):
        pkgs = extract_packages("npm", "install", ["install", "lodash@4.17.21"])
        assert ("npm", "lodash") in pkgs

    def test_flags_ignored(self):
        pkgs = extract_packages("npm", "install", ["install", "--save-dev", "jest"])
        assert ("npm", "jest") in pkgs
        names = [p[1] for p in pkgs]
        assert "--save-dev" not in names

    def test_pip_install(self):
        pkgs = extract_packages("pip", "install", ["install", "requests"])
        assert ("pypi", "requests") in pkgs

    def test_pip_version_specifier(self):
        pkgs = extract_packages("pip", "install", ["install", "requests==2.28.0"])
        assert ("pypi", "requests") in pkgs

    def test_non_install_returns_empty(self):
        pkgs = extract_packages("npm", "run", ["run", "build"])
        assert pkgs == []

    def test_unknown_family_returns_empty(self):
        pkgs = extract_packages("go", "get", ["get", "github.com/pkg/errors"])
        assert pkgs == []
