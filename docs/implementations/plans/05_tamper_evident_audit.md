# Implementation Plan — Gap 5: Tamper-Evident Audit Log

## Problem
The audit log is SQLite + JSONL. Both are append-only in practice but have no cryptographic integrity. An attacker who compromises the machine can delete or alter audit records before review, defeating the entire audit trail. The value of an audit log rests entirely on its trustworthiness.

## Goal
Add HMAC chaining to the JSONL stream, append-only enforcement to SQLite, and a verification command. Low implementation cost; high security value.

---

## Affected Files

```
policy_scout/audit/
├── jsonl_writer.py      # ADD: HMAC chain on write, chain head persistence
├── sqlite_store.py      # ADD: append-only triggers on CREATE TABLE
├── chain_verifier.py    # NEW: verify JSONL chain integrity
└── events.py            # ADD: ChainVerificationEvent type
```

---

## Implementation Approach

### Step 1 — HMAC Key Generation and Storage

Each Policy Scout installation gets a unique HMAC key, generated at first run and stored at:
`~/.local/share/policy-scout/audit_hmac.key`

```python
# In audit/jsonl_writer.py (initialization)
KEY_PATH = Path("~/.local/share/policy-scout/audit_hmac.key").expanduser()

def _get_or_create_hmac_key() -> bytes:
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes()
    key = os.urandom(32)  # 256-bit key
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEY_PATH.write_bytes(key)
    KEY_PATH.chmod(0o600)  # owner read-only
    return key
```

The key is local and not backed up by default. Its purpose is not to prove authenticity to a third party — it's to detect tampering. If the attacker has enough access to also steal the key and recompute all HMACs, you have bigger problems.

### Step 2 — HMAC Chain in JSONL Writer

Each JSONL line gets two additional fields: `chain_seq` (monotonically increasing sequence number) and `chain_mac` (HMAC-SHA256 of the chain state).

The chain input for entry N is:
```
HMAC-SHA256(key, previous_mac || seq_as_bytes || entry_json_without_chain_fields)
```

The first entry uses a zero-hash as the previous_mac.

```python
import hmac
import hashlib
import json

ZERO_HASH = b'\x00' * 32

class JSONLChainWriter:
    def __init__(self, path: Path):
        self._path = path
        self._key = _get_or_create_hmac_key()
        self._seq, self._prev_mac = self._load_chain_head()

    def write(self, event: AuditEvent) -> None:
        self._seq += 1
        # Serialize event without chain fields
        data = event.to_dict()
        entry_bytes = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
        # Compute HMAC
        mac_input = self._prev_mac + self._seq.to_bytes(8, 'big') + entry_bytes
        mac = hmac.new(self._key, mac_input, hashlib.sha256).digest()
        mac_hex = mac.hex()
        # Write full entry with chain fields
        full_entry = {**data, 'chain_seq': self._seq, 'chain_mac': mac_hex}
        with open(self._path, 'a') as f:
            f.write(json.dumps(full_entry) + '\n')
        # Update in-memory chain head
        self._prev_mac = mac
        self._save_chain_head()

    def _load_chain_head(self) -> tuple[int, bytes]:
        head_path = self._path.with_suffix('.chain_head')
        if head_path.exists():
            data = json.loads(head_path.read_text())
            return data['seq'], bytes.fromhex(data['mac'])
        return 0, ZERO_HASH

    def _save_chain_head(self) -> None:
        head_path = self._path.with_suffix('.chain_head')
        head_path.write_text(json.dumps({
            'seq': self._seq,
            'mac': self._prev_mac.hex(),
        }))
```

The `chain_head` file exists for fast chain continuation. It's not security-critical — the full chain can always be replayed from the JSONL file.

**Key design choice:** The HMAC fields are added to the JSONL output but NOT stored in SQLite. SQLite is the queryable store; JSONL is the tamper-evident record. They hold the same events; JSONL is truth for integrity.

### Step 3 — Chain Verifier (`audit/chain_verifier.py`)

```python
def verify_chain(path: Path, key: bytes) -> ChainVerificationResult:
    """
    Read the JSONL file, recompute every HMAC, and verify the chain is unbroken.
    Reports: total entries, first broken entry (if any), missing entries (gaps in chain_seq).
    """
    prev_mac = ZERO_HASH
    expected_seq = 1
    errors = []

    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            entry = json.loads(line.strip())
            seq = entry.pop('chain_seq', None)
            mac_hex = entry.pop('chain_mac', None)

            if seq != expected_seq:
                errors.append(ChainError(
                    lineno=lineno,
                    kind="gap",
                    detail=f"Expected seq {expected_seq}, got {seq}",
                ))
            expected_seq = (seq or expected_seq) + 1

            entry_bytes = json.dumps(entry, sort_keys=True, separators=(',', ':')).encode()
            mac_input = prev_mac + (seq or 0).to_bytes(8, 'big') + entry_bytes
            expected_mac = hmac.new(key, mac_input, hashlib.sha256).hexdigest()

            if mac_hex != expected_mac:
                errors.append(ChainError(
                    lineno=lineno,
                    kind="tamper",
                    detail=f"HMAC mismatch at seq {seq}",
                ))
            else:
                prev_mac = bytes.fromhex(mac_hex)

    return ChainVerificationResult(
        total_entries=expected_seq - 1,
        errors=errors,
        verified=(len(errors) == 0),
    )
```

### Step 4 — Append-Only SQLite

Two mechanisms:

**Triggers:** After table creation, add `BEFORE UPDATE` and `BEFORE DELETE` triggers that raise an error:

```sql
CREATE TRIGGER prevent_event_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'audit events are immutable');
END;

CREATE TRIGGER prevent_event_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'audit events cannot be deleted');
END;
```

This prevents casual tampering via SQL clients. It does not prevent someone with direct file access from modifying the SQLite file with a hex editor, but it catches any attempt through the normal database connection.

**WAL mode:** Enable Write-Ahead Logging (`PRAGMA journal_mode=WAL`) for better concurrent read performance and crash recovery. The WAL file also makes simple block-level tampering more complex.

Changes in `audit/sqlite_store.py`:

```python
# In _create_tables():
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("""
CREATE TRIGGER IF NOT EXISTS prevent_event_update ...
""")
conn.execute("""
CREATE TRIGGER IF NOT EXISTS prevent_event_delete ...
""")
```

**Migration:** For existing databases, add the triggers and change journal mode on first open with the new code. Existing records are not retroactively chain-verified.

### Step 5 — Streaming Export

For write-ahead export to a separate location or remote:

```python
# policy-scout audit export --stream /path/to/secondary.jsonl
# Continuously tail the primary JSONL and write to a second location

def stream_export(source: Path, dest: Path | None, stdout: bool = False):
    with open(source) as f:
        f.seek(0, 2)  # seek to end
        while True:
            line = f.readline()
            if line:
                if dest:
                    with open(dest, 'a') as d:
                        d.write(line)
                if stdout:
                    print(line, end='')
            else:
                time.sleep(0.1)
```

This is simple `tail -f` semantics. The copied stream inherits the HMAC chain, so the remote copy is also verifiable.

---

## CLI Commands

```bash
policy-scout audit verify-chain             # verify JSONL chain integrity
policy-scout audit verify-chain --verbose   # show each entry's verification status
policy-scout audit export --stream          # stream to stdout (for piping to SIEM)
policy-scout audit export --to /path/to/secondary.jsonl
```

Output of `verify-chain`:
```
Chain verification: PASSED
  Entries verified: 1,247
  Chain sequence: 1 → 1,247 (no gaps)
  HMAC algorithm: HMAC-SHA256

# or on failure:
Chain verification: FAILED
  Entries verified: 1,245
  Errors:
    [entry 891] HMAC mismatch — possible tampering at seq 891
    [entry 892] Sequence gap: expected 892, got 893
```

---

## New Audit Event Types

```
ChainVerificationCompleted   — result of verify-chain run
AuditExportStarted           — stream export began
```

---

## Integration Points

- `audit/jsonl_writer.py` — primary change location
- `audit/sqlite_store.py` — trigger + WAL mode additions
- `doctor.py` — add chain head status check: last verified seq, last written seq
- `cli/audit.py` — add `verify-chain` and `export` subcommands

---

## Backward Compatibility

Existing JSONL files without chain fields remain readable. The verifier should report "no chain data found — file predates chain integrity feature" rather than failing. New writes immediately start the chain from seq=1 even on an existing file (the chain starts fresh; there's no way to retroactively add HMACs to old entries).

---

## Test Strategy

- Unit test `JSONLChainWriter`: write N events, verify chain head matches final MAC
- Unit test `verify_chain`: write N events, corrupt one line, verify the error is reported at the correct line
- Unit test `verify_chain`: delete a line from the middle, verify gap detection
- Unit test SQLite triggers: attempt UPDATE/DELETE on an events row, verify exception is raised
- Unit test streaming export: write to source, stream to dest, verify dest matches source
- Regression: existing audit tests should continue to pass; only new fields are added

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| HMAC key management | ~50 | Low |
| `JSONLChainWriter` (chain on write) | ~80 | Low |
| `chain_verifier.py` | ~100 | Low-Medium |
| SQLite triggers + WAL | ~30 delta | Low |
| Streaming export | ~50 | Low |
| CLI commands | ~80 | Low |
| Tests | ~250 | Medium |
| **Total** | **~640** | |

This is the highest return-on-lines plan in the set. ~640 lines makes the audit trail meaningfully more trustworthy.

---

## Open Questions

1. Should the HMAC key be backed up or exportable? Recommendation: no automatic backup. Provide `policy-scout audit export-key` as an explicit command that prints the key in hex, with a warning. The key is for tamper detection on this machine; it's not a signing key.
2. Should chain verification run automatically on `doctor`? Recommendation: `doctor` should check that the chain head file exists and that the last N entries verify cleanly (last 100 entries, not the full chain — full chain verification is a separate explicit command).
3. What happens when the JSONL file is rotated (archived and a new file started)? Recommendation: the chain starts fresh in the new file. The archive file's final chain_mac should be recorded in the new file's first entry as a "chain_anchor" field for cross-file continuity — a deferred enhancement.
