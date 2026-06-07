"""Repository mutation checks for sweep."""

import os
import subprocess
from typing import List
from .models import Finding


def check_repo_changes(
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check for repository mutations using git status.
    
    Args:
        project_root: Path to project root
        sweep_id: Sweep ID for findings
        
    Returns:
        List of findings
    """
    findings = []
    
    # Check if this is a git repository
    git_dir = os.path.join(project_root, ".git")
    if not os.path.exists(git_dir):
        # Not a git repo - add to could_not_verify later
        return findings
    
    try:
        # Get git status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode == 0:
            status_output = result.stdout
            
            # Count changes
            modified_count = status_output.count(" M")
            added_count = status_output.count("??")
            deleted_count = status_output.count(" D")
            
            total_changes = modified_count + added_count + deleted_count
            
            if total_changes > 0:
                findings.append(Finding(
                    sweep_id=sweep_id,
                    severity="low",
                    confidence="high",
                    category="repo_mutation",
                    title="Repository has uncommitted changes",
                    location="git status",
                    evidence_ref="git_status",
                    why_it_matters=f"Repository has {total_changes} uncommitted changes ({modified_count} modified, {added_count} added, {deleted_count} deleted).",
                    recommended_action="Review git status and commit or stash changes as appropriate.",
                ))
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        # Git not available or error - skip
        pass
    
    return findings
