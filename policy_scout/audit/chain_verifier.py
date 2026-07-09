# SPDX-License-Identifier: Apache-2.0
"""HMAC chain verifier for JSONL audit logs."""

import hashlib
import hmac as hmac_module
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ZERO_MAC = b"\x00" * 32


@dataclass
class ChainError:
    """A single error found during chain verification."""

    lineno: int
    kind: str  # "tamper" | "gap" | "parse_error"
    detail: str


@dataclass
class ChainVerificationResult:
    """Result of HMAC chain verification."""

    verified: bool
    total_entries: int
    errors: list = field(default_factory=list)
    message: str = ""


def verify_chain(
    jsonl_path: Path, key: Optional[bytes] = None
) -> ChainVerificationResult:
    """Verify the HMAC chain integrity of a JSONL audit log.

    Returns a ChainVerificationResult. verified=True means all entries with
    chain_seq/chain_mac fields passed HMAC validation. Entries without those
    fields (pre-chain) are skipped without error.
    """
    if key is None:
        key_path = jsonl_path.parent / "audit_hmac.key"
        if not key_path.exists():
            return ChainVerificationResult(
                verified=False,
                total_entries=0,
                message=(
                    "HMAC key not found. Chain cannot be verified. "
                    "File may predate chain integrity feature."
                ),
            )
        try:
            key = key_path.read_bytes()
        except OSError as e:
            return ChainVerificationResult(
                verified=False,
                total_entries=0,
                message=f"Could not read HMAC key: {e}",
            )

    if not jsonl_path.exists():
        return ChainVerificationResult(
            verified=True,
            total_entries=0,
            message="Audit file not found. No entries to verify.",
        )

    prev_mac = ZERO_MAC
    expected_seq = 1
    errors: list[ChainError] = []
    total = 0
    has_any_chain_data = False

    with open(jsonl_path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(
                    ChainError(lineno=lineno, kind="parse_error", detail=str(e))
                )
                continue

            seq = entry.get("chain_seq")
            mac_hex = entry.get("chain_mac")

            if seq is None or mac_hex is None:
                # Pre-chain entry — skip without error
                continue

            has_any_chain_data = True
            total += 1

            if seq != expected_seq:
                errors.append(
                    ChainError(
                        lineno=lineno,
                        kind="gap",
                        detail=f"Expected seq {expected_seq}, got {seq}",
                    )
                )
            expected_seq = seq + 1

            # Reconstruct canonical entry bytes (without chain fields)
            entry_without_chain = {
                k: v for k, v in entry.items() if k not in ("chain_seq", "chain_mac")
            }
            entry_bytes = json.dumps(
                entry_without_chain, sort_keys=True, separators=(",", ":")
            ).encode()

            mac_input = prev_mac + seq.to_bytes(8, "big") + entry_bytes
            expected_mac = hmac_module.new(
                key, mac_input, hashlib.sha256
            ).hexdigest()

            if mac_hex != expected_mac:
                errors.append(
                    ChainError(
                        lineno=lineno,
                        kind="tamper",
                        detail=f"HMAC mismatch at seq {seq}",
                    )
                )
                # Continue with current stored mac so we can detect further gaps
                prev_mac = bytes.fromhex(mac_hex) if len(mac_hex) == 64 else ZERO_MAC
            else:
                prev_mac = bytes.fromhex(mac_hex)

    if not has_any_chain_data:
        return ChainVerificationResult(
            verified=True,
            total_entries=0,
            message=(
                "No chain data found. File may predate chain integrity feature."
            ),
        )

    verified = len(errors) == 0
    return ChainVerificationResult(
        verified=verified,
        total_entries=total,
        errors=errors,
        message=(
            f"All {total} entries verified."
            if verified
            else f"{len(errors)} integrity error(s) found in {total} entries."
        ),
    )
