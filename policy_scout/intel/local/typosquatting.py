# SPDX-License-Identifier: Apache-2.0
"""Typosquatting detection — edit distance + substitution patterns."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from ..adapter import IntelResult, TyposquatCandidate


# ── Homoglyph map (Unicode lookalikes → ASCII) ────────────────────────────────

_HOMOGLYPHS: dict[str, str] = {
    # Cyrillic
    "а": "a",  # а
    "е": "e",  # е
    "о": "o",  # о
    "р": "r",  # р
    "с": "c",  # с
    "х": "x",  # х
    "і": "i",  # і
    # Greek
    "α": "a",  # α
    "ε": "e",  # ε
    "ο": "o",  # ο
    "ρ": "p",  # ρ
    # Fullwidth
    **{chr(0xFF21 + i): chr(ord("A") + i) for i in range(26)},  # Ａ-Ｚ
    **{chr(0xFF41 + i): chr(ord("a") + i) for i in range(26)},  # ａ-ｚ
}

# Digit → letter normalizations for typosquat detection (one direction only)
_DIGIT_SUBS: dict[str, str] = {
    "0": "o",
    "1": "l",
    "3": "e",
    "4": "a",
    "5": "s",
}

# Common benign suffixes added to legitimate package names
_SQUATTING_SUFFIXES = ["-js", "-node", "-utils", "-helper", "-lib", "-core", "-es", "2", "-2"]


def _normalize_homoglyphs(name: str) -> str:
    """Replace Unicode homoglyphs with ASCII equivalents."""
    return "".join(_HOMOGLYPHS.get(ch, ch) for ch in name)


def _has_homoglyphs(name: str) -> bool:
    return any(ch in _HOMOGLYPHS for ch in name)


def _levenshtein(a: str, b: str) -> int:
    """Standard Levenshtein edit distance."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(a) + 1))
    for j, cb in enumerate(b, 1):
        curr = [j]
        for i, ca in enumerate(a, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[i] + 1, curr[i - 1] + 1, prev[i - 1] + cost))
        prev = curr
    return prev[-1]


def _classify_technique(suspect: str, legitimate: str) -> str:
    """Identify the typosquatting technique used."""
    if _has_homoglyphs(suspect):
        return "homoglyph"
    # Check digit substitution: normalize digits and compare
    norm_s = "".join(_DIGIT_SUBS.get(c, c) for c in suspect.lower())
    norm_l = "".join(_DIGIT_SUBS.get(c, c) for c in legitimate.lower())
    if norm_s == norm_l and suspect.lower() != legitimate.lower():
        return "digit_sub"
    # Suffix addition
    for suffix in _SQUATTING_SUFFIXES:
        if suspect.lower() == legitimate.lower() + suffix:
            return "suffix_addition"
        if suspect.lower() + suffix == legitimate.lower():
            return "suffix_addition"
    # Single char: transposition vs insertion vs deletion vs substitution
    dist = _levenshtein(suspect.lower(), legitimate.lower())
    if dist == 1:
        # Check transposition (swap adjacent chars)
        s, l = suspect.lower(), legitimate.lower()
        if len(s) == len(l):
            diffs = [(i, sc, lc) for i, (sc, lc) in enumerate(zip(s, l)) if sc != lc]
            if len(diffs) == 2 and diffs[0][1] == diffs[1][2] and diffs[0][2] == diffs[1][1]:
                return "transposition"
        return "edit_distance"
    return "edit_distance"


@lru_cache(maxsize=4)
def _load_top_packages(ecosystem: str) -> List[str]:
    """Load the top packages list for the given ecosystem (cached)."""
    import yaml  # bundled via PyYAML

    data_dir = Path(__file__).parent.parent.parent / "data"
    filenames = {
        "npm": "top_npm_packages.yaml",
        "pypi": "top_pypi_packages.yaml",
    }
    fname = filenames.get(ecosystem)
    if not fname:
        return []
    path = data_dir / fname
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text())
    pkgs = raw.get("packages", [])
    # Strip leading @ and scope for comparison (e.g. @babel/core -> babel/core)
    normalized = []
    for p in pkgs:
        if isinstance(p, str):
            normalized.append(p.lower().lstrip("@"))
    return normalized


def check_typosquatting(
    ecosystem: str,
    name: str,
    max_distance: int = 2,
) -> List[TyposquatCandidate]:
    """Return typosquatting candidates for the given package name."""
    top = _load_top_packages(ecosystem)
    if not top:
        return []

    lower_name = name.lower().lstrip("@")
    # Normalize homoglyphs before comparison
    norm_name = _normalize_homoglyphs(lower_name)

    candidates: List[TyposquatCandidate] = []
    for known in top:
        if lower_name == known:
            return []  # exact match — not a typosquat

        # Distance on normalized names (catches homoglyphs)
        dist = _levenshtein(norm_name, known)
        if 0 < dist <= max_distance:
            technique = _classify_technique(lower_name, known)
            candidates.append(TyposquatCandidate(
                original=known,
                distance=dist,
                technique=technique,
            ))
        # Also check with suffix removed
        elif any(lower_name == known + suffix for suffix in _SQUATTING_SUFFIXES):
            candidates.append(TyposquatCandidate(
                original=known,
                distance=1,
                technique="suffix_addition",
            ))

    # Sort: closer distance first, then alphabetically
    candidates.sort(key=lambda c: (c.distance, c.original))
    return candidates


class TyposquattingAdapter:
    """Local adapter: typosquatting detection against top-N package lists."""

    def enrich_package(
        self,
        ecosystem: str,
        name: str,
        version: Optional[str] = None,
    ) -> IntelResult:
        candidates = check_typosquatting(ecosystem, name)
        result = IntelResult(
            package_name=name,
            ecosystem=ecosystem,
            typosquatting_candidates=candidates,
            confidence="high",
            source="local",
        )
        return result
