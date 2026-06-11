"""Shannon entropy calculation for high-entropy string detection."""

import math
import re
from collections import Counter
from dataclasses import dataclass

_CHARSET_PATTERNS = {
    "base64": re.compile(r"[A-Za-z0-9+/=]"),
    "hex": re.compile(r"[0-9a-fA-F]"),
}

# Strings that look high-entropy but are safe to ignore
_FALSE_POSITIVE_PREFIXES = (
    "sha256:",
    "sha1:",
    "md5:",
    "0000000",
    "1111111",
    "aaaaaaa",
    "fffffff",
    "version",
    "example",
    "placeholder",
    "changeme",
    "your-",
    "YOUR_",
    "<your",
    "INSERT_",
)

_FALSE_POSITIVE_PATTERNS = [
    re.compile(r"^[0-9a-f]{40}$"),          # git commit hash (all hex, exactly 40)
    re.compile(r"^[0-9a-f]{64}$"),          # sha256 hex (exactly 64)
    re.compile(r"https?://"),               # URLs
    re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),  # IP addresses
]


@dataclass
class HighEntropyMatch:
    """A single high-entropy string found in text."""

    value: str
    start: int
    entropy: float
    charset: str


def shannon_entropy(s: str) -> float:
    """Compute Shannon entropy (bits per character) for a string."""
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def _is_likely_false_positive(s: str) -> bool:
    """Return True if the string is likely a non-secret (commit hash, URL, etc.)."""
    if s.startswith(_FALSE_POSITIVE_PREFIXES):
        return True
    for pat in _FALSE_POSITIVE_PATTERNS:
        if pat.match(s):
            return True
    return False


def find_high_entropy_strings(
    text: str,
    min_length: int = 20,
    max_length: int = 100,
    min_entropy: float = 4.5,
    charset: str = "base64",
) -> list[HighEntropyMatch]:
    """Find high-entropy strings in text by sliding a character-class window.

    Extracts maximal runs of characters belonging to the charset, then
    checks entropy against the threshold. Filters known false-positive shapes.
    """
    charset_re = _CHARSET_PATTERNS.get(charset)
    if charset_re is None:
        charset_re = re.compile(r"\S")

    # Find all maximal runs of charset characters
    run_pattern = re.compile(
        r"[A-Za-z0-9+/=]+"
        if charset == "base64"
        else r"[0-9a-fA-F]+"
        if charset == "hex"
        else r"\S+"
    )

    matches: list[HighEntropyMatch] = []
    for m in run_pattern.finditer(text):
        candidate = m.group(0)
        if len(candidate) < min_length or len(candidate) > max_length:
            continue
        if _is_likely_false_positive(candidate):
            continue
        h = shannon_entropy(candidate)
        if h >= min_entropy:
            matches.append(
                HighEntropyMatch(
                    value=candidate,
                    start=m.start(),
                    entropy=h,
                    charset=charset,
                )
            )

    return matches
