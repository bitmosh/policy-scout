# SPDX-License-Identifier: Apache-2.0
"""Prompt injection pattern detector for agent-readable files."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from .models import Finding


# Files that agents commonly read — high-value scanning targets
AGENT_READABLE_GLOBS = [
    "README.md", "README.rst", "README.txt",
    "AGENTS.md", "CLAUDE.md", ".cursorrules", ".windsurfrules",
    "CONTRIBUTING.md", "SECURITY.md",
    "package.json",
    "pyproject.toml",
]

AGENT_READABLE_GLOB_PATTERNS = [
    "docs/**/*.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/**",
]

# Files we never flag (they discuss injection by design)
_SUPPRESSION_COMMENT = "# policy-scout-injection-allow"
_SUPPRESSION_FRONTMATTER = "suppress_injection_scan: true"

# Zero-width and invisible Unicode characters
_ZERO_WIDTH = frozenset([
    "​",  # zero-width space
    "‌",  # zero-width non-joiner
    "‍",  # zero-width joiner
    "⁠",  # word joiner
    "﻿",  # BOM / zero-width no-break space
])


@dataclass
class InjectionSpec:
    pattern_id: str
    description: str
    severity: str
    confidence: str
    compiled: List[re.Pattern]


@dataclass
class InjectionFinding:
    pattern_id: str
    description: str
    severity: str
    confidence: str
    path: str
    line_number: int
    matched_text: str
    context: str = ""

    def to_sweep_finding(self, sweep_id: str = "") -> Finding:
        return Finding(
            sweep_id=sweep_id,
            severity=self.severity,
            confidence=self.confidence,
            category="prompt_injection",
            title=f"Prompt injection pattern: {self.pattern_id}",
            location=f"{self.path}:{self.line_number}",
            evidence_ref=self.matched_text[:120],
            why_it_matters=(
                f"{self.description}. An agent reading this file may be influenced "
                "to take unsafe actions."
            ),
            recommended_action=(
                "Review the flagged content and remove or sanitize embedded instructions. "
                "If this is intentional security documentation, add "
                "'# policy-scout-injection-allow' to suppress."
            ),
        )


@lru_cache(maxsize=1)
def _load_patterns() -> List[InjectionSpec]:
    import yaml
    data_path = Path(__file__).parent.parent / "data" / "injection_patterns.yaml"
    raw = yaml.safe_load(data_path.read_text())
    specs = []
    for entry in raw:
        compiled = []
        for p in entry.get("patterns", []):
            try:
                compiled.append(re.compile(p))
            except re.error:
                pass
        specs.append(InjectionSpec(
            pattern_id=entry["id"],
            description=entry["description"],
            severity=entry["severity"],
            confidence=entry["confidence"],
            compiled=compiled,
        ))
    return specs


def _is_suppressed(content: str) -> bool:
    return _SUPPRESSION_COMMENT in content or _SUPPRESSION_FRONTMATTER in content


def _has_zero_width(content: str) -> bool:
    return any(c in content for c in _ZERO_WIDTH)


def _extract_b64_segments(content: str) -> List[str]:
    """Find base64 blobs ≥40 chars and attempt to decode them.

    Uses a regex that excludes '=' from the core character class so that
    URL-style 'key=<b64>' separators do not contaminate the match.
    """
    decoded: List[str] = []
    # [A-Za-z0-9+/]{40,} = core base64 chars (no = in middle), ={0,2} = optional padding
    for m in re.finditer(r"[A-Za-z0-9+/]{40,}={0,2}", content):
        candidate = m.group(0)
        padded = candidate.rstrip("=")
        padded = padded + "=" * (-len(padded) % 4)
        try:
            raw = base64.b64decode(padded, validate=False)
            text = raw.decode("utf-8", errors="ignore")
            if len(text) >= 20 and sum(c.isprintable() for c in text) / max(len(text), 1) > 0.8:
                decoded.append(text)
        except Exception:
            pass
    return decoded


def _line_number_for(content: str, pos: int) -> int:
    return content[:pos].count("\n") + 1


def _context_for(content: str, pos: int, radius: int = 60) -> str:
    start = max(0, pos - radius)
    end = min(len(content), pos + radius)
    return content[start:end].replace("\n", "↵")


class PromptInjectionAnalyzer:
    """Scan text content for prompt injection patterns."""

    def __init__(self) -> None:
        self._patterns = _load_patterns()

    def analyze_file(self, path: Path, content: Optional[str] = None) -> List[InjectionFinding]:
        """Analyze a file for injection patterns. Reads the file if content is None."""
        if content is None:
            try:
                content = path.read_text(errors="replace")
            except OSError:
                return []

        if _is_suppressed(content):
            return []

        findings: List[InjectionFinding] = []

        # Phase 1: direct pattern matching
        findings.extend(self._match_patterns(str(path), content))

        # Phase 2: zero-width character check
        if _has_zero_width(content):
            findings.append(InjectionFinding(
                pattern_id="hidden_content_zwsp",
                description="Zero-width or invisible Unicode characters found",
                severity="high",
                confidence="medium",
                path=str(path),
                line_number=1,
                matched_text="[zero-width characters]",
                context="",
            ))

        # Phase 3: base64 decode-and-rescan
        for segment in _extract_b64_segments(content):
            sub = self._match_patterns(f"{path} [base64-decoded]", segment)
            findings.extend(sub)

        return findings

    def analyze_text(self, text: str, source: str = "<text>") -> List[InjectionFinding]:
        """Analyze arbitrary text content (e.g. a tool response)."""
        if _is_suppressed(text):
            return []
        findings = self._match_patterns(source, text)
        if _has_zero_width(text):
            findings.append(InjectionFinding(
                pattern_id="hidden_content_zwsp",
                description="Zero-width or invisible Unicode characters found",
                severity="high",
                confidence="medium",
                path=source,
                line_number=1,
                matched_text="[zero-width characters]",
            ))
        # Base64 decode-and-rescan
        for segment in _extract_b64_segments(text):
            sub = self._match_patterns(f"{source} [base64-decoded]", segment)
            findings.extend(sub)
        return findings

    def _match_patterns(self, source: str, content: str) -> List[InjectionFinding]:
        findings: List[InjectionFinding] = []
        for spec in self._patterns:
            for regex in spec.compiled:
                for m in regex.finditer(content):
                    findings.append(InjectionFinding(
                        pattern_id=spec.pattern_id,
                        description=spec.description,
                        severity=spec.severity,
                        confidence=spec.confidence,
                        path=source,
                        line_number=_line_number_for(content, m.start()),
                        matched_text=m.group(0)[:120],
                        context=_context_for(content, m.start()),
                    ))
        return findings


def scan_agent_readable_files(
    project_root: str | Path,
    sweep_id: str = "",
) -> List[Finding]:
    """Scan all agent-readable files in project_root for injection patterns."""
    import fnmatch

    root = Path(project_root)
    analyzer = PromptInjectionAnalyzer()
    findings: List[Finding] = []

    # Direct filename matches
    for name in AGENT_READABLE_GLOBS:
        path = root / name
        if path.is_file():
            for inj in analyzer.analyze_file(path):
                findings.append(inj.to_sweep_finding(sweep_id))

    # Glob pattern matches
    for glob in AGENT_READABLE_GLOB_PATTERNS:
        for path in root.glob(glob):
            if path.is_file():
                for inj in analyzer.analyze_file(path):
                    findings.append(inj.to_sweep_finding(sweep_id))

    return findings
