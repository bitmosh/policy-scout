# SPDX-License-Identifier: Apache-2.0
"""Persistent settings store for policy-scout."""

import json
import os
import sys
from pathlib import Path

_DEFAULT_PATH = Path.home() / ".local" / "share" / "policy-scout" / "settings.json"


def _settings_path() -> Path:
    custom = os.environ.get("POLICY_SCOUT_SETTINGS_PATH")
    return Path(custom) if custom else _DEFAULT_PATH


def read_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"Warning: settings file at {path} is corrupt and will be ignored: {exc}", file=sys.stderr)
        return {}
    except Exception as exc:
        print(f"Warning: could not read settings from {path}: {exc}", file=sys.stderr)
        return {}


def write_setting(key: str, value: object) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    settings = read_settings()
    settings[key] = value
    path.write_text(json.dumps(settings, indent=2))


def get_approval_timeout_hours() -> int:
    """Return configured approval timeout in hours (default: 24)."""
    return int(read_settings().get("approval_timeout_hours", 24))
