"""ID generation utilities."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Literal


def generate_id(
    prefix: Literal[
        "req",
        "parse",
        "class",
        "dec",
        "risk",
        "appr",
        "exec",
        "sbx",
        "sweep",
        "find",
        "evt",
        "report",
        "scan",
    ],
) -> str:
    """Generate a unique ID with the given prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utcnow_iso() -> str:
    """Get current UTC time as ISO 8601 string with 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utcnow_timestamp() -> float:
    """Get current UTC time as Unix timestamp."""
    return datetime.now(timezone.utc).timestamp()


def utcnow_plus_hours_iso(hours: int) -> str:
    """Get current UTC time plus hours as ISO 8601 string with 'Z' suffix."""
    return (
        (datetime.now(timezone.utc) + timedelta(hours=hours))
        .isoformat()
        .replace("+00:00", "Z")
    )
