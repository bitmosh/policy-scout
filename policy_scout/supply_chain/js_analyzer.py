"""Multi-layer JS static analysis for lifecycle script inspection."""

from __future__ import annotations

import base64
import re
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


_PATTERNS_PATH = Path(__file__).parent / "patterns" / "js_patterns.yaml"

# Combination rules: if this set of pattern IDs fires, escalate to severity+reason
_ESCALATION_RULES: List[Tuple[Set[str], str, str]] = [
    ({"conditional_activation", "network_fetch"}, "critical", "CI-conditional network fetch"),
    ({"conditional_activation", "shell_exec"}, "critical", "CI-conditional shell execution"),
    ({"indirect_eval", "encoded_payload"}, "critical", "Encoded payload with dynamic eval"),
    ({"env_exfiltration", "network_fetch"}, "critical", "Env var theft with network exfiltration"),
    ({"shell_exec", "encoded_payload"}, "critical", "Encoded payload executed via shell"),
]

# Base64 extraction: find Buffer.from('...', 'base64') or atob('...')
_B64_BUFFER_RE = re.compile(
    r"""Buffer\.from\s*\(\s*['"]([A-Za-z0-9+/]{20,}={0,2})['"]\s*,\s*['"]base64['"]\s*\)""",
    re.IGNORECASE,
)
_B64_ATOB_RE = re.compile(
    r"""atob\s*\(\s*['"]([A-Za-z0-9+/]{20,}={0,2})['"]\s*\)""",
    re.IGNORECASE,
)

# Minification threshold: average chars per line
_MINIFIED_AVG_LINE_LEN = 200
_MINIFIED_MIN_LINES_CHECKED = 3


@dataclass
class ScriptFinding:
    pattern_id: str
    description: str
    severity: str
    confidence: str
    matched_text: str
    line_number: int
    source: str = "js_analyzer"
    escalated: bool = False
    escalation_reason: str = ""

    def to_dict(self) -> dict:
        d = {
            "type": "supply_chain",
            "pattern_id": self.pattern_id,
            "description": self.description,
            "severity": self.severity,
            "confidence": self.confidence,
            "matched_text": self.matched_text[:200],
            "line_number": self.line_number,
            "source": self.source,
        }
        if self.escalated:
            d["escalated"] = True
            d["escalation_reason"] = self.escalation_reason
        return d


def strip_js_comments(source: str) -> str:
    """Remove single-line (//) and multi-line (/* */) JS comments.

    Intentionally simple: does not parse string literals, so patterns inside
    strings may be stripped if they look like comments. Acceptable for our
    threat-detection use case — false negatives here are rare.
    """
    # Multi-line comments first
    source = re.sub(r'/\*.*?\*/', ' ', source, flags=re.DOTALL)
    # Single-line comments (but not URLs like https://)
    source = re.sub(r'(?<![:/])//[^\n]*', ' ', source)
    return source


def decode_base64_literals(source: str, _depth: int = 0) -> str:
    """Find and decode base64 literals (Buffer.from/atob), replacing with decoded text.

    Recursive up to depth 3 to handle double-encoded payloads.
    """
    if _depth >= 3:
        return source

    decoded_any = False
    result = source

    for pattern in (_B64_BUFFER_RE, _B64_ATOB_RE):
        def _replace(m: re.Match) -> str:
            nonlocal decoded_any
            try:
                decoded = base64.b64decode(m.group(1) + "==").decode("utf-8", errors="replace")
                decoded_any = True
                return f" /* decoded_b64: {decoded} */ "
            except Exception:
                return m.group(0)
        result = pattern.sub(_replace, result)

    if decoded_any:
        return decode_base64_literals(result, _depth + 1)
    return result


def normalize_js(source: str) -> str:
    source = strip_js_comments(source)
    source = decode_base64_literals(source)
    return source


def _is_minified(source: str) -> bool:
    lines = [ln for ln in source.splitlines() if ln.strip()]
    if len(lines) < _MINIFIED_MIN_LINES_CHECKED:
        return False
    avg = sum(len(ln) for ln in lines) / len(lines)
    return avg >= _MINIFIED_AVG_LINE_LEN


def _load_patterns() -> List[Dict]:
    if not _PATTERNS_PATH.exists():
        return []
    with _PATTERNS_PATH.open() as f:
        data = yaml.safe_load(f)
    return data.get("patterns", [])


def _compile_entry(entry: Dict) -> List[re.Pattern]:
    compiled = []
    for raw in entry.get("patterns", []):
        try:
            compiled.append(re.compile(raw, re.IGNORECASE | re.MULTILINE))
        except re.error:
            pass
    return compiled


class JSAnalyzer:
    """Multi-layer JS static analyzer for lifecycle scripts."""

    def __init__(self) -> None:
        self._entries = _load_patterns()
        self._compiled: Dict[str, List[re.Pattern]] = {
            e["id"]: _compile_entry(e) for e in self._entries
        }
        self._meta: Dict[str, Dict] = {e["id"]: e for e in self._entries}

    def analyze(
        self,
        source: str,
        context: Optional[Dict] = None,
    ) -> List[ScriptFinding]:
        findings: List[ScriptFinding] = []

        # Build a line-offset map for accurate line numbers
        line_starts = [0]
        for i, ch in enumerate(source):
            if ch == "\n":
                line_starts.append(i + 1)

        def _line_of(pos: int) -> int:
            lo, hi = 0, len(line_starts) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if line_starts[mid] <= pos:
                    lo = mid
                else:
                    hi = mid - 1
            return lo + 1

        normalized = normalize_js(source)

        # Phase 1: pattern matching on normalized source
        for entry in self._entries:
            pid = entry["id"]
            for pat in self._compiled.get(pid, []):
                for m in pat.finditer(normalized):
                    findings.append(ScriptFinding(
                        pattern_id=pid,
                        description=entry["description"],
                        severity=entry["severity"],
                        confidence=entry["confidence"],
                        matched_text=m.group(0).strip(),
                        line_number=_line_of(m.start()),
                    ))

        # Phase 2: minification check on original source
        if _is_minified(source):
            findings.append(ScriptFinding(
                pattern_id="minified_code",
                description="Heavily minified lifecycle script is itself suspicious",
                severity="medium",
                confidence="low",
                matched_text="<minified>",
                line_number=1,
            ))

        # Phase 3: escalation rules
        findings = _apply_escalation(findings)

        return findings


def _apply_escalation(findings: List[ScriptFinding]) -> List[ScriptFinding]:
    """Upgrade severity for dangerous pattern combinations."""
    fired_ids: Set[str] = {f.pattern_id for f in findings}
    _SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

    for required_ids, escalated_severity, reason in _ESCALATION_RULES:
        if required_ids.issubset(fired_ids):
            for finding in findings:
                if finding.pattern_id in required_ids:
                    if _SEVERITY_ORDER.get(escalated_severity, 0) > _SEVERITY_ORDER.get(finding.severity, 0):
                        finding.severity = escalated_severity
                        finding.escalated = True
                        finding.escalation_reason = reason

    return findings
