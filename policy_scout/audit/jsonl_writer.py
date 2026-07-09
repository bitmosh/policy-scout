# SPDX-License-Identifier: Apache-2.0
"""JSONL audit writer with HMAC chain integrity."""

import hashlib
import hmac as hmac_module
import json
import os
import sys
from pathlib import Path
from typing import Optional

from .events import AuditEvent
from .redaction import redact_dict

ZERO_MAC = b"\x00" * 32


def _get_or_create_hmac_key(key_path: Path) -> bytes:
    """Load or generate the HMAC key for chain integrity."""
    if key_path.exists():
        return key_path.read_bytes()
    key = os.urandom(32)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    return key


def _load_chain_head(head_path: Path) -> tuple[int, bytes]:
    """Load chain head (seq, prev_mac) from file, or return initial state."""
    if head_path.exists():
        try:
            data = json.loads(head_path.read_text())
            return data["seq"], bytes.fromhex(data["mac"])
        except Exception:
            pass
    return 0, ZERO_MAC


def _save_chain_head(head_path: Path, seq: int, mac: bytes) -> None:
    """Persist chain head state. Best-effort; chain can be rebuilt from JSONL."""
    try:
        head_path.write_text(json.dumps({"seq": seq, "mac": mac.hex()}))
    except Exception:
        pass


class JSONLWriter:
    """Writes audit events to a JSONL file.

    Each entry includes chain_seq and chain_mac fields that form an
    HMAC-SHA256 chain. The chain detects tampering, deletion, or
    reordering of entries. Verification: policy-scout audit verify-chain.
    """

    def __init__(self, path: Optional[Path] = None):
        """Initialize writer with audit file path."""
        if path is None:
            path = Path.home() / ".local" / "share" / "policy-scout" / "audit.jsonl"

        env_path = os.environ.get("POLICY_SCOUT_AUDIT_PATH")
        if env_path:
            path = Path(env_path)

        self.path = path
        self._key_path = self.path.parent / "audit_hmac.key"
        self._head_path = Path(str(self.path) + ".chain_head")
        self._ensure_directory()

        self._key = _get_or_create_hmac_key(self._key_path)
        self._seq, self._prev_mac = _load_chain_head(self._head_path)

    def _ensure_directory(self):
        """Ensure the audit directory exists."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _compute_mac(self, seq: int, entry_bytes: bytes) -> bytes:
        """Compute HMAC-SHA256 for a chain entry."""
        mac_input = self._prev_mac + seq.to_bytes(8, "big") + entry_bytes
        return hmac_module.new(self._key, mac_input, hashlib.sha256).digest()

    def write_event(self, event: AuditEvent) -> bool:
        """Write a single audit event to the JSONL file with chain integrity."""
        try:
            event_data = event.to_dict()
            redacted_data = redact_dict(event_data)

            self._seq += 1

            # Canonical serialization without chain fields — this is what the MAC covers.
            entry_bytes = json.dumps(
                redacted_data, sort_keys=True, separators=(",", ":")
            ).encode()

            mac = self._compute_mac(self._seq, entry_bytes)
            mac_hex = mac.hex()

            full_entry = dict(redacted_data)
            full_entry["chain_seq"] = self._seq
            full_entry["chain_mac"] = mac_hex

            with open(self.path, "a") as f:
                f.write(json.dumps(full_entry) + "\n")

            self._prev_mac = mac
            _save_chain_head(self._head_path, self._seq, self._prev_mac)

            return True
        except Exception as e:
            self._seq -= 1
            print(f"Warning: Failed to write audit event: {e}", file=sys.stderr)
            return False

    def write_events(self, events: list) -> int:
        """Write multiple audit events to the JSONL file."""
        success_count = 0
        for event in events:
            if self.write_event(event):
                success_count += 1
        return success_count

    def read_events(self) -> list:
        """Read all events from the JSONL file."""
        events = []
        if not self.path.exists():
            return events
        try:
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except Exception as e:
            print(f"Warning: Failed to read audit events: {e}", file=sys.stderr)
        return events

    def clear(self):
        """Clear the audit file and reset chain state."""
        if self.path.exists():
            self.path.unlink()
        if self._head_path.exists():
            self._head_path.unlink()
        self._seq = 0
        self._prev_mac = ZERO_MAC
