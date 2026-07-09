# SPDX-License-Identifier: Apache-2.0
"""Rotation guidance generator for secret findings."""

from .patterns import SecretFinding

_HISTORY_SUFFIX = (
    "\n\n"
    "IMPORTANT: This secret was found in git history. "
    "Removing it from the working tree is not enough — it remains in all historical commits.\n"
    "You must either:\n"
    "  1. Assume it is compromised and rotate/revoke it immediately, OR\n"
    "  2. Rewrite history with 'git filter-repo' to remove it (complex, irreversible).\n"
    "If this repository has ever been pushed to a remote, assume the secret was already harvested."
)


def generate_guidance(finding: SecretFinding, is_in_history: bool = False) -> str:
    """Return actionable rotation guidance for a secret finding."""
    guidance = finding.guidance or f"Identified as {finding.service} {finding.secret_type}. Rotate immediately."
    if is_in_history:
        guidance += _HISTORY_SUFFIX
    return guidance
