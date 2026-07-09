# SPDX-License-Identifier: Apache-2.0
"""Tests for the known-bad registry adapter."""

from policy_scout.intel.local.known_bad import KnownBadAdapter, _lookup


class TestKnownBadLookup:
    def test_unversioned_match(self):
        is_bad, evidence = _lookup("npm", "npmrc", None)
        assert is_bad is True
        assert evidence is not None

    def test_versioned_match(self):
        is_bad, evidence = _lookup("npm", "node-ipc", "10.1.1")
        assert is_bad is True

    def test_versioned_miss(self):
        # node-ipc 9.x is not in the registry
        is_bad, evidence = _lookup("npm", "node-ipc", "9.2.2")
        assert is_bad is False

    def test_clean_package(self):
        is_bad, evidence = _lookup("npm", "lodash", None)
        assert is_bad is False

    def test_case_insensitive(self):
        is_bad, evidence = _lookup("npm", "NPMRC", None)
        assert is_bad is True

    def test_unknown_ecosystem(self):
        is_bad, evidence = _lookup("cargo", "serde", None)
        assert is_bad is False

    def test_pypi_entry(self):
        is_bad, evidence = _lookup("pypi", "colourama", None)
        assert is_bad is True
        assert evidence is not None


class TestKnownBadAdapter:
    def test_bad_package(self):
        adapter = KnownBadAdapter()
        result = adapter.enrich_package("npm", "npmrc")
        assert result.known_bad is True
        assert result.known_bad_evidence is not None
        assert result.confidence == "high"

    def test_clean_package(self):
        adapter = KnownBadAdapter()
        result = adapter.enrich_package("npm", "lodash")
        assert result.known_bad is False
        assert result.known_bad_evidence is None

    def test_result_has_findings_property(self):
        adapter = KnownBadAdapter()
        result = adapter.enrich_package("npm", "npmrc")
        assert result.has_findings is True

    def test_clean_has_no_findings(self):
        adapter = KnownBadAdapter()
        result = adapter.enrich_package("npm", "express")
        assert result.has_findings is False
