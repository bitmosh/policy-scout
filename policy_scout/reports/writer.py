# SPDX-License-Identifier: Apache-2.0
"""Report writer utilities."""

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ScoutReport


def get_report_root() -> Path:
    """Get the report root directory.

    Uses POLICY_SCOUT_REPORT_ROOT env var if set for testing.
    Otherwise uses ~/.local/share/policy-scout/reports/
    """
    override = os.environ.get("POLICY_SCOUT_REPORT_ROOT")
    if override:
        return Path(override)

    return Path.home() / ".local" / "share" / "policy-scout" / "reports"


def write_report(report: "ScoutReport") -> Path:
    """Write report metadata and return report root.

    The actual Markdown and JSON content is written by the specific
    report generators. This function ensures the directory exists
    and returns the path for file writing.

    Args:
        report: ScoutReport with report_id populated

    Returns:
        Path to the report directory
    """
    report_root = get_report_root()
    report_dir = report_root / report.report_id
    report_dir.mkdir(parents=True, exist_ok=True)

    return report_dir
