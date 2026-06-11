"""Secret scanning package."""

from .engine import SecretScanner, ScanSummary
from .patterns import SecretFinding, SecretPatternMatcher, load_patterns
from .file_scanner import ScanResult, scan_file, scan_directory
from .git_scanner import GitScanResult, scan_staged, scan_history
from .guidance import generate_guidance

__all__ = [
    "SecretScanner",
    "ScanSummary",
    "SecretFinding",
    "SecretPatternMatcher",
    "load_patterns",
    "ScanResult",
    "scan_file",
    "scan_directory",
    "GitScanResult",
    "scan_staged",
    "scan_history",
    "generate_guidance",
]
