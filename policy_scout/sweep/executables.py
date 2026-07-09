# SPDX-License-Identifier: Apache-2.0
"""Executable file checks for sweep."""

import os
import stat
from typing import List
from .models import Finding


# Directories to skip during executable scan
SKIP_DIRECTORIES = [
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
]


def check_executables(
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check for executable files in project.
    
    Args:
        project_root: Path to project root
        sweep_id: Sweep ID for findings
        
    Returns:
        List of findings
    """
    findings = []
    
    for root, dirs, files in os.walk(project_root):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRECTORIES]
        
        for filename in files:
            filepath = os.path.join(root, filename)
            
            # Check if file is executable
            if os.path.isfile(filepath):
                try:
                    st = os.stat(filepath)
                    if st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                        # File is executable
                        findings.append(Finding(
                            sweep_id=sweep_id,
                            severity="info",
                            confidence="high",
                            category="unknown_suspicious_artifact",
                            title="Executable file detected",
                            location=_get_relative_path(filepath, project_root),
                            evidence_ref="executable_bit",
                            why_it_matters="Executable files may execute arbitrary commands.",
                            recommended_action="Review executable file to ensure it is legitimate.",
                        ))
                except OSError:
                    # Skip files that can't be stat'd
                    continue
    
    return findings


def _get_relative_path(file_path: str, project_root: str) -> str:
    """Get relative path from project root."""
    try:
        return os.path.relpath(file_path, project_root)
    except ValueError:
        return file_path
