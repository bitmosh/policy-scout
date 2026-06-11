"""Canary token generation and extraction."""

from __future__ import annotations

import os
import re

_TOKEN_RE = re.compile(r"PSCANARY-[0-9a-f]{8}-DO-NOT-ACT")


def generate_canary_token() -> str:
    """Return a unique canary token string."""
    random_part = os.urandom(4).hex()
    return f"PSCANARY-{random_part}-DO-NOT-ACT"


def extract_canary_token(content: str) -> str | None:
    """Extract the first canary token found in content, or None."""
    m = _TOKEN_RE.search(content)
    return m.group(0) if m else None


def is_canary_token(text: str) -> bool:
    """Return True if text is a valid canary token."""
    return bool(_TOKEN_RE.fullmatch(text.strip()))
