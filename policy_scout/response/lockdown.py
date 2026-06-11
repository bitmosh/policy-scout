"""Lockdown kill switch for Policy Scout.

When lockdown is active, the policy engine forces DENY for all non-read
operations. This is a last resort after detecting an active attack.

The lockdown state is a sentinel file on disk so it persists across
process restarts and is visible to all Policy Scout invocations.
"""

import json
import sys
from pathlib import Path
from typing import Optional

LOCKDOWN_PATH = Path.home() / ".local" / "share" / "policy-scout" / "lockdown.active"


def is_lockdown_active() -> bool:
    """Return True if lockdown mode is currently active."""
    return LOCKDOWN_PATH.exists()


def get_lockdown_reason() -> Optional[str]:
    """Return the reason lockdown was activated, or None if inactive."""
    if not LOCKDOWN_PATH.exists():
        return None
    try:
        data = json.loads(LOCKDOWN_PATH.read_text())
        return data.get("reason", "No reason recorded")
    except Exception:
        return "Lockdown file present but unreadable"


def activate_lockdown(reason: str = "", audit_store=None) -> bool:
    """Activate lockdown mode by creating the sentinel file.

    Returns True on success, False if the sentinel could not be created.
    """
    try:
        LOCKDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"reason": reason or "Manually activated"}
        LOCKDOWN_PATH.write_text(json.dumps(payload))
    except OSError as e:
        print(f"Error: Failed to activate lockdown: {e}", file=sys.stderr)
        return False

    if audit_store is not None:
        try:
            from ..audit.events import create_lockdown_activated_event
            audit_store.write(create_lockdown_activated_event(reason))
        except Exception:
            pass

    return True


def deactivate_lockdown(cleared_by: str = "", audit_store=None) -> bool:
    """Deactivate lockdown mode by removing the sentinel file.

    Returns True on success (or if lockdown was already inactive),
    False if the file could not be removed.
    """
    if not LOCKDOWN_PATH.exists():
        return True

    try:
        LOCKDOWN_PATH.unlink()
    except OSError as e:
        print(f"Error: Failed to deactivate lockdown: {e}", file=sys.stderr)
        return False

    if audit_store is not None:
        try:
            from ..audit.events import create_lockdown_deactivated_event
            audit_store.write(create_lockdown_deactivated_event(cleared_by))
        except Exception:
            pass

    return True
