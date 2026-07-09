# SPDX-License-Identifier: Apache-2.0
"""Per-connection MCP session state."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class McpSession:
    """Tracks state for one MCP stdio connection."""

    session_id: str
    client_name: str = "unknown"
    client_version: str = "unknown"
    initialized: bool = False
    tool_calls: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def record_tool_call(self) -> None:
        with self._lock:
            self.tool_calls += 1

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "client_name": self.client_name,
            "client_version": self.client_version,
            "initialized": self.initialized,
            "tool_calls": self.tool_calls,
        }


# Module-level singleton for the current stdio session
_current_session: Optional[McpSession] = None


def get_session() -> Optional[McpSession]:
    return _current_session


def set_session(session: McpSession) -> None:
    global _current_session
    _current_session = session
