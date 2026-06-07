"""JavaScript pattern checks for sweep."""

import os
import re
from typing import List
from .models import Finding


# Suspicious JavaScript patterns
SUSPICIOUS_JS_PATTERNS = [
    r"eval\s*\(",
    r"new\s+Function\s*\(",
    r"Function\s*\(",
    r"child_process",
    r"\.exec\s*\(",
    r"\.spawn\s*\(",
    r"base64",
    r"Buffer\.from.*base64",
    r"atob\s*\(",
    r"btoa\s*\(",
    r"process\.env",
    r"\.env\.",
    r"\.npmrc",
    r"\.ssh",
]

# File extensions to check
JS_EXTENSIONS = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]


def check_javascript_patterns(
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check JavaScript files for suspicious patterns.
    
    Args:
        project_root: Path to project root
        sweep_id: Sweep ID for findings
        
    Returns:
        List of findings
    """
    findings = []
    
    for root, dirs, files in os.walk(project_root):
        # Skip node_modules to avoid false positives
        if "node_modules" in dirs:
            dirs.remove("node_modules")
        
        for filename in files:
            if any(filename.endswith(ext) for ext in JS_EXTENSIONS):
                filepath = os.path.join(root, filename)
                findings.extend(_check_js_file(filepath, project_root, sweep_id))
    
    return findings


def _check_js_file(
    filepath: str,
    project_root: str,
    sweep_id: str,
) -> List[Finding]:
    """Check a single JavaScript file for suspicious patterns."""
    findings = []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        # Unreadable file - skip
        return findings
    
    # Check for suspicious patterns
    suspicious_found = []
    for pattern in SUSPICIOUS_JS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            suspicious_found.append(pattern)
    
    if suspicious_found:
        severity = _determine_js_severity(suspicious_found, content)
        findings.append(Finding(
            sweep_id=sweep_id,
            severity=severity,
            confidence="moderate",
            category="obfuscated_payload",
            title="Suspicious JavaScript pattern detected",
            location=_get_relative_path(filepath, project_root),
            evidence_ref="js_pattern",
            why_it_matters=f"File contains suspicious patterns: {', '.join(suspicious_found)}.",
            recommended_action="Review code for obfuscation or dynamic execution.",
        ))
    
    return findings


def _determine_js_severity(
    suspicious_patterns: List[str],
    content: str,
) -> str:
    """Determine severity based on suspicious patterns."""
    # High severity patterns
    high_severity = [r"eval\s*\(", r"new\s+Function\s*\(", r"child_process"]
    
    # Medium severity patterns
    medium_severity = [r"\.exec\s*\(", r"\.spawn\s*\(", r"base64"]
    
    for pattern in suspicious_patterns:
        if pattern in high_severity:
            return "high"
        if pattern in medium_severity:
            return "medium"
    
    return "low"


def _get_relative_path(file_path: str, project_root: str) -> str:
    """Get relative path from project root."""
    try:
        return os.path.relpath(file_path, project_root)
    except ValueError:
        return file_path
