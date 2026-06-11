"""File-based secret scanner."""

import time
from dataclasses import dataclass, field
from pathlib import Path

from .patterns import SecretFinding, SecretPatternMatcher
from .entropy import find_high_entropy_strings

_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".mypy_cache", ".pytest_cache", ".tox",
    ".eggs", "*.egg-info", ".cache",
}

_SCAN_EXTENSIONS = {
    ".env", ".cfg", ".conf", ".config", ".ini", ".json", ".yaml", ".yml",
    ".toml", ".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".bash", ".zsh",
    ".fish", ".tf", ".tfvars", ".properties", ".xml", ".pem", ".key",
    ".env.local", ".env.development", ".env.production", "",
}

_MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB
_BINARY_CHECK_BYTES = 8192


@dataclass
class ScanResult:
    """Result of a scan operation."""

    findings: list = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    duration_ms: int = 0
    errors: list = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def severity_exit_code(self) -> int:
        """0=clean, 1=medium/low, 2=high/critical."""
        if self.critical_count > 0 or self.high_count > 0:
            return 2
        if self.findings:
            return 1
        return 0


def _is_binary(path: Path) -> bool:
    """Return True if the file appears to be binary."""
    try:
        chunk = path.read_bytes()[:_BINARY_CHECK_BYTES]
        return b"\x00" in chunk
    except OSError:
        return True


def _should_scan(path: Path) -> bool:
    """Return True if the file should be scanned based on extension and size."""
    if path.suffix.lower() in _SCAN_EXTENSIONS or path.suffix == "":
        return True
    # Also scan common dotfiles
    if path.name.startswith(".env"):
        return True
    return False


def scan_file(
    path: Path,
    matcher: SecretPatternMatcher,
    run_entropy: bool = False,
) -> list[SecretFinding]:
    """Scan a single file for secrets. Returns list of findings."""
    if not path.is_file():
        return []

    try:
        size = path.stat().st_size
    except OSError:
        return []

    if size > _MAX_FILE_SIZE:
        return []

    if _is_binary(path):
        return []

    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []

    source = str(path)
    findings = matcher.scan_text(text, source)

    # Entropy scan for .env files (higher false-positive tolerance)
    if run_entropy and path.name.startswith(".env"):
        for m in find_high_entropy_strings(text, min_entropy=4.8):
            # Avoid double-reporting values already caught by pattern matcher
            already_found = any(
                f.line == text[:m.start].count("\n") + 1 for f in findings
            )
            if not already_found:
                from .patterns import SecretFinding
                findings.append(
                    SecretFinding(
                        secret_type="high_entropy",
                        service="generic",
                        severity="medium",
                        source=source,
                        line=text[:m.start].count("\n") + 1,
                        column=0,
                        redacted_value=f"{m.value[:4]}***",
                        guidance="High-entropy string — may be a secret. Verify and rotate if so.",
                        entropy=m.entropy,
                    )
                )

    return findings


def scan_directory(
    root: Path,
    matcher: SecretPatternMatcher,
    run_entropy: bool = False,
) -> ScanResult:
    """Recursively scan a directory for secrets."""
    start = time.monotonic()
    result = ScanResult()

    if not root.is_dir():
        result.errors.append(f"Not a directory: {root}")
        return result

    for path in root.rglob("*"):
        # Skip directories in the skip list
        if any(skip in path.parts for skip in _SKIP_DIRS):
            continue

        if not path.is_file():
            continue

        if not _should_scan(path):
            result.files_skipped += 1
            continue

        try:
            findings = scan_file(path, matcher, run_entropy=run_entropy)
            result.files_scanned += 1
            result.findings.extend(findings)
        except Exception as e:
            result.errors.append(f"{path}: {e}")
            result.files_skipped += 1

    result.duration_ms = int((time.monotonic() - start) * 1000)
    return result
