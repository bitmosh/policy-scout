# SPDX-License-Identifier: Apache-2.0
"""Secret pattern registry loader and matcher."""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from .entropy import shannon_entropy

_PATTERNS_PATH = Path(__file__).parent.parent / "data" / "secret_patterns.yaml"


@dataclass
class PatternSpec:
    """A single secret pattern specification."""

    id: str
    service: str
    pattern: str
    severity: str
    guidance: str
    entropy_min: Optional[float] = None
    context_pattern: Optional[str] = None


@dataclass
class SecretFinding:
    """A single secret detected in source text."""

    secret_type: str
    service: str
    severity: str
    source: str           # file path or description
    line: int
    column: int
    redacted_value: str
    guidance: str
    commit: Optional[str] = None   # set when found in history
    entropy: Optional[float] = None

    def to_dict(self) -> dict:
        d = {
            "secret_type": self.secret_type,
            "service": self.service,
            "severity": self.severity,
            "source": self.source,
            "line": self.line,
            "column": self.column,
            "redacted_value": self.redacted_value,
            "guidance": self.guidance,
        }
        if self.commit:
            d["commit"] = self.commit
        return d


def _redact_value(value: str) -> str:
    """Show first 4 + last 2 chars with *** in between.

    Long enough to identify the credential type without revealing it.
    """
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-2:]}"


def load_patterns(path: Path = _PATTERNS_PATH) -> list[PatternSpec]:
    """Load secret patterns from YAML. Returns empty list on failure."""
    if yaml is None:
        return []
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text())
        raw = data.get("patterns", [])
        specs = []
        for entry in raw:
            try:
                specs.append(
                    PatternSpec(
                        id=entry["id"],
                        service=entry.get("service", "generic"),
                        pattern=entry["pattern"],
                        severity=entry.get("severity", "high"),
                        guidance=entry.get("guidance", ""),
                        entropy_min=entry.get("entropy_min"),
                        context_pattern=entry.get("context_pattern"),
                    )
                )
            except (KeyError, TypeError):
                pass
        return specs
    except Exception as e:
        print(f"Warning: Failed to load secret patterns: {e}", file=sys.stderr)
        return []


class SecretPatternMatcher:
    """Compiled secret pattern matcher."""

    def __init__(self, patterns: list[PatternSpec]):
        self._specs: list[tuple[PatternSpec, re.Pattern]] = []
        for spec in patterns:
            try:
                self._specs.append((spec, re.compile(spec.pattern)))
            except re.error as e:
                print(
                    f"Warning: Invalid pattern {spec.id!r}: {e}", file=sys.stderr
                )
        self._context_patterns: dict[str, re.Pattern] = {}
        for spec, _ in self._specs:
            if spec.context_pattern:
                try:
                    self._context_patterns[spec.id] = re.compile(spec.context_pattern)
                except re.error:
                    pass

    def __len__(self) -> int:
        return len(self._specs)

    def scan_text(
        self,
        text: str,
        source: str,
        line_offset: int = 0,
    ) -> list[SecretFinding]:
        """Scan text for secret patterns. Returns findings list."""
        findings: list[SecretFinding] = []
        lines = text.splitlines()

        for spec, regex in self._specs:
            for m in regex.finditer(text):
                value = m.group(0)

                # Entropy gate
                if spec.entropy_min is not None:
                    h = shannon_entropy(value)
                    if h < spec.entropy_min:
                        continue

                # Context pattern gate
                ctx_re = self._context_patterns.get(spec.id)
                if ctx_re is not None:
                    window_start = max(0, m.start() - 150)
                    window_end = min(len(text), m.end() + 150)
                    if not ctx_re.search(text[window_start:window_end]):
                        continue

                # Compute line/column
                line_num = text[: m.start()].count("\n") + 1 + line_offset
                last_nl = text.rfind("\n", 0, m.start())
                col = m.start() - last_nl

                # Skip obvious test/template placeholders
                lower_val = value.lower()
                if any(
                    skip in lower_val
                    for skip in ("example", "changeme", "placeholder", "your_", "insert_")
                ):
                    continue

                findings.append(
                    SecretFinding(
                        secret_type=spec.id,
                        service=spec.service,
                        severity=spec.severity,
                        source=source,
                        line=line_num,
                        column=col,
                        redacted_value=_redact_value(value),
                        guidance=spec.guidance,
                        entropy=shannon_entropy(value),
                    )
                )

        return findings
