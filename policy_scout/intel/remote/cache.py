# SPDX-License-Identifier: Apache-2.0
"""SQLite TTL cache for remote intel results."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

_DEFAULT_TTL_SECONDS = 4 * 60 * 60  # 4 hours
_DB_PATH = Path.home() / ".local" / "share" / "policy-scout" / "intel_cache.db"

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS intel_cache (
    key         TEXT PRIMARY KEY,
    data        TEXT NOT NULL,
    fetched_at  INTEGER NOT NULL,
    expires_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expires ON intel_cache (expires_at);
"""


def _db_path() -> Path:
    env = __import__("os").environ.get("POLICY_SCOUT_INTEL_CACHE_PATH")
    return Path(env) if env else _DB_PATH


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=5)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(_CREATE_SQL)
        yield con
    finally:
        con.close()


class IntelCache:
    """Get/set intel results with TTL expiry."""

    def get(self, key: str) -> Optional[dict]:
        """Return cached data dict if present and unexpired; else None."""
        now = int(time.time())
        try:
            with _conn() as con:
                row = con.execute(
                    "SELECT data FROM intel_cache WHERE key=? AND expires_at > ?",
                    (key, now),
                ).fetchone()
            return json.loads(row["data"]) if row else None
        except Exception:
            return None

    def set(self, key: str, data: dict, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
        now = int(time.time())
        try:
            with _conn() as con:
                con.execute(
                    "INSERT OR REPLACE INTO intel_cache (key, data, fetched_at, expires_at) "
                    "VALUES (?, ?, ?, ?)",
                    (key, json.dumps(data), now, now + ttl_seconds),
                )
                con.commit()
        except Exception:
            pass

    def clear(self) -> int:
        """Delete all cache entries. Returns number of rows deleted."""
        try:
            with _conn() as con:
                cur = con.execute("DELETE FROM intel_cache")
                con.commit()
                return cur.rowcount
        except Exception:
            return 0

    def evict_expired(self) -> int:
        """Remove expired entries. Returns number of rows deleted."""
        now = int(time.time())
        try:
            with _conn() as con:
                cur = con.execute("DELETE FROM intel_cache WHERE expires_at <= ?", (now,))
                con.commit()
                return cur.rowcount
        except Exception:
            return 0

    def stats(self) -> dict:
        """Return cache statistics."""
        now = int(time.time())
        try:
            with _conn() as con:
                total = con.execute("SELECT COUNT(*) FROM intel_cache").fetchone()[0]
                live = con.execute(
                    "SELECT COUNT(*) FROM intel_cache WHERE expires_at > ?", (now,)
                ).fetchone()[0]
            return {"total_entries": total, "live_entries": live, "expired": total - live}
        except Exception:
            return {"total_entries": 0, "live_entries": 0, "expired": 0}


def cache_key(ecosystem: str, name: str, version: Optional[str]) -> str:
    v = version or "*"
    return f"{ecosystem}:{name.lower()}:{v}"
