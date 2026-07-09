# SPDX-License-Identifier: Apache-2.0
"""Sandbox result JSON artifact writing."""

import json
from pathlib import Path
from typing import Optional
from .models import SandboxResult


def write_sandbox_result(
    result: SandboxResult,
    output_path: Optional[Path] = None
) -> Path:
    """Write sandbox result to JSON artifact.
    
    Args:
        result: SandboxResult to write.
        output_path: Optional output path. If not provided, uses default.
        
    Returns:
        Path to the written result file.
    """
    if output_path is None:
        # Default: ~/.local/share/policy-scout/results/sbx_<id>.json
        from .temp_workspace import get_sandbox_root
        sandbox_root = get_sandbox_root()
        results_dir = sandbox_root.parent / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        output_path = results_dir / f"{result.sandbox_id}.json"
    
    # Write result as JSON
    with open(output_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    
    return output_path
