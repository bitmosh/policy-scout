"""Tests for typosquatting detection."""

import pytest
from policy_scout.intel.local.typosquatting import (
    _levenshtein,
    _normalize_homoglyphs,
    _classify_technique,
    check_typosquatting,
    TyposquattingAdapter,
)


class TestLevenshtein:
    def test_identical(self):
        assert _levenshtein("lodash", "lodash") == 0

    def test_one_insertion(self):
        assert _levenshtein("lodash", "loadash") == 1

    def test_one_deletion(self):
        assert _levenshtein("expres", "express") == 1

    def test_one_substitution(self):
        assert _levenshtein("1odash", "lodash") == 1

    def test_insertion(self):
        # standard Levenshtein: one extra char = distance 1
        assert _levenshtein("recact", "react") == 1

    def test_empty_strings(self):
        assert _levenshtein("", "") == 0
        assert _levenshtein("", "abc") == 3
        assert _levenshtein("abc", "") == 3


class TestNormalizeHomoglyphs:
    def test_cyrillic_a(self):
        # Cyrillic 'а' looks like Latin 'a'
        result = _normalize_homoglyphs("lаdash")
        assert result == "ladash"

    def test_no_homoglyphs(self):
        assert _normalize_homoglyphs("lodash") == "lodash"


class TestClassifyTechnique:
    def test_digit_sub(self):
        technique = _classify_technique("1odash", "lodash")
        assert technique == "digit_sub"

    def test_suffix_addition(self):
        technique = _classify_technique("lodash-js", "lodash")
        assert technique == "suffix_addition"

    def test_generic_close_edit(self):
        # "lodsha" vs "lodash" is a 2-char permutation — classified as edit_distance
        technique = _classify_technique("lodsha", "lodash")
        assert technique == "edit_distance"

    def test_generic_edit(self):
        technique = _classify_technique("expres", "express")
        assert technique == "edit_distance"


class TestCheckTyposquatting:
    def test_exact_match_not_flagged(self):
        # lodash is in the top list — exact match should return empty
        candidates = check_typosquatting("npm", "lodash")
        assert candidates == []

    def test_close_name_flagged(self):
        # "1odash" is distance-1 from "lodash"
        candidates = check_typosquatting("npm", "1odash")
        assert any(c.original == "lodash" for c in candidates)

    def test_unknown_package_no_crash(self):
        # Completely unknown package — shouldn't match common ones
        candidates = check_typosquatting("npm", "zzz_totally_unique_xyz987")
        assert isinstance(candidates, list)

    def test_unsupported_ecosystem_returns_empty(self):
        candidates = check_typosquatting("cargo", "serde")
        assert candidates == []

    def test_suffix_typosquat(self):
        candidates = check_typosquatting("npm", "lodash-js")
        assert any(c.original == "lodash" and c.technique == "suffix_addition" for c in candidates)

    def test_expres_flagged(self):
        candidates = check_typosquatting("npm", "expres")
        originals = [c.original for c in candidates]
        assert "express" in originals

    def test_pypi_supported(self):
        # "panda" is in known_bad but "pandas" should be in top pypi list
        candidates = check_typosquatting("pypi", "panda")
        originals = [c.original for c in candidates]
        assert "pandas" in originals


class TestTyposquattingAdapter:
    def test_enrich_known_bad_name(self):
        adapter = TyposquattingAdapter()
        result = adapter.enrich_package("npm", "1odash")
        assert result.package_name == "1odash"
        assert result.ecosystem == "npm"
        assert isinstance(result.typosquatting_candidates, list)

    def test_enrich_clean_package(self):
        adapter = TyposquattingAdapter()
        result = adapter.enrich_package("npm", "lodash")
        assert result.typosquatting_candidates == []
