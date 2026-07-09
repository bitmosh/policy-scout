# SPDX-License-Identifier: Apache-2.0
"""Redaction utility for sensitive data."""

import re
from typing import List, Tuple


# Secret patterns to redact
SECRET_PATTERNS: List[Tuple[str, str]] = [
    # API keys with common prefixes -> possible_token
    (r"OPENAI_API_KEY\s*=\s*[\"']?[A-Za-z0-9_\-]+[\"']?", "possible_token"),
    (r"ANTHROPIC_API_KEY\s*=\s*[\"']?[A-Za-z0-9_\-]+[\"']?", "possible_token"),
    (r"NPM_TOKEN\s*=\s*[\"']?[A-Za-z0-9_\-]+[\"']?", "possible_token"),
    (r"GITHUB_TOKEN\s*=\s*[\"']?[A-Za-z0-9_\-]+[\"']?", "possible_token"),
    (r"AWS_SECRET_ACCESS_KEY\s*=\s*[\"']?[A-Za-z0-9/+=]+[\"']?", "possible_token"),
    (r"_authToken\s*=\s*[^\s\"']+", "possible_token"),
    # Generic patterns
    (r"\bsk-[A-Za-z0-9]+", "possible_token"),
    (r"Bearer\s+[A-Za-z0-9._~+/=-]+", "possible_token"),
    (r"-----BEGIN\s+.*PRIVATE\s+KEY-----", "ssh_private_key"),
    # env-style assignments -> env_value
    (r"TOKEN\s*=\s*[\"']?[A-Za-z0-9_\-]+[\"']?", "env_value"),
    (r"API_KEY\s*=\s*[\"']?[A-Za-z0-9_\-]+[\"']?", "env_value"),
    (r"SECRET\s*=\s*[\"']?[A-Za-z0-9_\-]+[\"']?", "env_value"),
    (r"PASSWORD\s*=\s*[\"']?[^\s\"']+[\"']?", "env_value"),
    (r"--?(token|api-key|apikey|secret|password|auth|key|npm-token|github-token)(=|\s+)[^\s\"']+", "possible_token"),
    # URL-encoded secrets -> possible_token
    (r"(api_key|token|secret|password)=[A-Za-z0-9_\-]+", "possible_token"),
]


def redact_string(text: str) -> str:
    """Redact sensitive patterns from a string."""
    if not text:
        return text

    redacted = text
    for pattern, label in SECRET_PATTERNS:
        redacted = re.sub(
            pattern,
            f"<redacted:{label}>",
            redacted,
            flags=re.IGNORECASE,
        )

    return redacted


# Keys whose values must never be redacted — cross-store IDs used for causation/correlation.
# A hex EventId like upstream_causation_id looks like a secret to naive regex patterns;
# exempting by key prevents future pattern additions from silently breaking the causal chain.
_EXEMPT_KEYS = frozenset({"upstream_causation_id"})


def redact_dict(data: dict) -> dict:
    """Recursively redact sensitive values in a dictionary."""
    if not isinstance(data, dict):
        return data

    redacted = {}
    for key, value in data.items():
        if key in _EXEMPT_KEYS:
            redacted[key] = value
        elif isinstance(value, str):
            redacted[key] = redact_string(value)
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value)
        elif isinstance(value, list):
            redacted[key] = redact_list(value)
        else:
            redacted[key] = value

    return redacted


def redact_list(data: list) -> list:
    """Recursively redact sensitive values in a list."""
    if not isinstance(data, list):
        return data

    redacted = []
    for item in data:
        if isinstance(item, str):
            redacted.append(redact_string(item))
        elif isinstance(item, dict):
            redacted.append(redact_dict(item))
        elif isinstance(item, list):
            redacted.append(redact_list(item))
        else:
            redacted.append(item)

    return redacted
