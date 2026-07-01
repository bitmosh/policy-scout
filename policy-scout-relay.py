#!/usr/bin/env python3
"""policy-scout-relay.py — relay policy-scout fossic events to the Lattica hub store.

Implements payload-conditional relay (CP-F-3): most event types relay unconditionally;
DecisionIssued relays only for DENY_AND_ALERT decisions or critical risk_band events.
CommandRequested and other intermediate audit stages stay local.

On startup, backfills all historical events from the local vault before subscribing
for new ones. Backfill is safe to overlap with the live subscription: relay_event()
is idempotent via read_by_external_id on the hub side.

Usage:
    python policy-scout-relay.py [--local-store PATH] [--hub-store PATH] [--log-level LEVEL]

Environment:
    POLICY_SCOUT_FOSSIC_DB_PATH  override local store path (same var used by sqlite_store.py)
    LATTICA_HUB_STORE_PATH       override hub store path
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

try:
    from fossic import RelayConfig, RelayAgent, StoredEvent, ReadQuery
    from fossic.exceptions import StorageError
except ImportError:
    print(
        "error: fossic-py is required — install it in your environment before running this relay",
        file=sys.stderr,
    )
    sys.exit(1)


_DEFAULT_LOCAL_STORE = str(Path.home() / ".local" / "share" / "policy-scout" / "fossic.db")
_DEFAULT_HUB_STORE   = str(Path.home() / ".lattica" / "fossic" / "store.db")


# ── Glob matching (mirrors fossic src/glob.rs segment-based rules) ────────────
# Verified against Rust tests by Fossic: * = one segment, ** = zero or more.

def _match_parts(p: list[str], s: list[str]) -> bool:
    if not p:
        return not s
    if p[0] == "**":
        for i in range(len(s) + 1):
            if _match_parts(p[1:], s[i:]):
                return True
        return False
    if not s:
        return False
    return (p[0] == "*" or p[0] == s[0]) and _match_parts(p[1:], s[1:])


def _stream_matches_pattern(stream_id: str, pattern: str) -> bool:
    return _match_parts(pattern.split("/"), stream_id.split("/"))


# ── Relay agent ───────────────────────────────────────────────────────────────

class PolicyScoutRelayAgent(RelayAgent):
    """Relay agent with startup backfill and payload-conditional filter.

    Backfills all historical events from the local vault before subscribing,
    so events written before the relay process started are not skipped.

    The base RelayAgent._should_relay applies relay_filter as an event_type set.
    PolicyScout requires payload inspection for DecisionIssued, so filter logic
    is lifted entirely into this subclass (relay_filter stays empty).
    """

    ALWAYS_RELAY_TYPES: frozenset[str] = frozenset({
        "LockdownActivated",
        "LockdownDeactivated",
        "WatchDaemonStarted",
        "WatchDaemonStopped",
        "ApprovalRequested",
        "ApprovalApprovedOnce",
        "ApprovalDeniedOnce",
        "IntelLookupCompleted",
    })

    def _should_relay(self, event: StoredEvent) -> bool:
        # Posture stream — singleton, always relay
        if event.stream_id == "policy-scout/posture":
            return True

        # Unconditional relay types
        if event.event_type in self.ALWAYS_RELAY_TYPES:
            return True

        # Payload-conditional: DecisionIssued relays only for high-signal decisions
        if event.event_type == "DecisionIssued":
            payload = event.payload()
            if isinstance(payload, dict):
                if payload.get("decision") == "DENY_AND_ALERT":
                    return True
                if payload.get("risk_band") == "critical":
                    return True
            return False

        # CommandRequested and all intermediate audit stages stay local
        return False

    def _backfill(self) -> None:
        """Relay all historical events from the local vault that match the subscribe pattern."""
        assert self.local_store is not None
        assert self.hub_store is not None

        count = 0
        for stream_info in self.local_store.streams():
            if not _stream_matches_pattern(stream_info.id, self.config.subscribe_pattern):
                continue
            events = self.local_store.read_range(ReadQuery(stream_id=stream_info.id, branch="main"))
            for event in events:
                try:
                    relayed = self.relay_event(event)
                    if relayed:
                        count += 1
                except Exception as exc:
                    self.logger.warning(
                        "backfill: skipping event after error",
                        extra={"event_id": event.id.hex(), "stream": event.stream_id, "error": str(exc)},
                    )

        self.logger.info("backfill complete", extra={"relayed": count})

    def run(self) -> None:
        from fossic import Store

        while True:
            try:
                self.local_store = Store.open(self.config.local_store_path)
                self.hub_store = Store.open(self.config.hub_store_path)

                self.logger.info("backfill: starting historical pass")
                self._backfill()

                self.logger.info("subscribe: entering live event loop")
                with self.local_store.subscribe(self.config.subscribe_pattern) as sub:
                    for event in sub:
                        self._relay_with_retry(event)

            except StorageError as exc:
                self.logger.warning(
                    "store error — reconnecting",
                    extra={"error": str(exc), "delay_ms": self.config.reconnect_delay_ms},
                )
                time.sleep(self.config.reconnect_delay_ms / 1000)
            except Exception:
                self.logger.error("relay fatal error", exc_info=True)
                raise


# ── Config + entry point ──────────────────────────────────────────────────────

def _build_config(local_store: str, hub_store: str) -> RelayConfig:
    return RelayConfig(
        local_store_path=local_store,
        hub_store_path=hub_store,
        source_prefix="policy-scout",
        subscribe_pattern="policy-scout/**",
        relay_filter=set(),
        batch_size=50,
        reconnect_delay_ms=5000,
        max_retry_attempts=5,
        retry_backoff_base_ms=100,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Relay policy-scout fossic events to the Lattica hub")
    parser.add_argument(
        "--local-store",
        default=os.environ.get("POLICY_SCOUT_FOSSIC_DB_PATH", _DEFAULT_LOCAL_STORE),
        help="path to local policy-scout fossic store (default: %(default)s)",
    )
    parser.add_argument(
        "--hub-store",
        default=os.environ.get("LATTICA_HUB_STORE_PATH", _DEFAULT_HUB_STORE),
        help="path to Lattica hub fossic store (default: %(default)s)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="logging level (default: %(default)s)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    local_path = os.path.expanduser(args.local_store)
    hub_path   = os.path.expanduser(args.hub_store)

    logger = logging.getLogger("policy-scout-relay")
    logger.info("starting", extra={"local_store": local_path, "hub_store": hub_path})

    config = _build_config(local_path, hub_path)
    agent  = PolicyScoutRelayAgent(config)
    agent.run()


if __name__ == "__main__":
    main()
