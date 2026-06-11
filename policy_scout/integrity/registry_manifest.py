"""Registry file checksum verification."""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path


_DATA_DIR = Path(__file__).parent.parent / "data"
_MANIFEST_PATH = _DATA_DIR / "registry_manifest.json"


@dataclass
class IntegrityCheckResult:
    """Result of a registry integrity check."""

    passed: bool
    files_checked: int = 0
    errors: list = field(default_factory=list)
    reason: str = ""


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_registry_integrity(
    manifest_path: Path = _MANIFEST_PATH,
    data_dir: Path = _DATA_DIR,
) -> IntegrityCheckResult:
    """Verify all registry files against the bundled manifest.

    Returns IntegrityCheckResult with passed=True when every file matches
    its expected checksum. Files listed in the manifest that are absent
    count as errors. Files not listed are not checked.
    """
    if not manifest_path.exists():
        return IntegrityCheckResult(
            passed=False,
            reason=(
                "Registry manifest not found. "
                "Run 'python scripts/generate_registry_manifest.py' to create it."
            ),
        )

    try:
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return IntegrityCheckResult(
            passed=False,
            reason=f"Registry manifest unreadable: {e}",
        )

    registry_files = manifest.get("files", {})
    if not registry_files:
        return IntegrityCheckResult(
            passed=False,
            reason="Registry manifest has no files listed.",
        )

    errors: list[str] = []
    for filename, expected_hash in registry_files.items():
        file_path = data_dir / filename
        if not file_path.exists():
            errors.append(f"{filename}: file missing")
            continue
        actual_hash = _sha256_file(file_path)
        if actual_hash != expected_hash:
            errors.append(
                f"{filename}: checksum mismatch "
                f"(expected {expected_hash[:16]}…, got {actual_hash[:16]}…)"
            )

    return IntegrityCheckResult(
        passed=(len(errors) == 0),
        files_checked=len(registry_files),
        errors=errors,
        reason=(
            f"All {len(registry_files)} registry files verified."
            if not errors
            else f"{len(errors)} file(s) failed verification."
        ),
    )


def generate_manifest(
    data_dir: Path = _DATA_DIR,
    filenames: list[str] | None = None,
    version: str = "dev",
) -> dict:
    """Generate a manifest dict for the given data files."""
    if filenames is None:
        filenames = sorted(
            f.name for f in data_dir.iterdir() if f.suffix in (".yaml", ".json") and f.name != "registry_manifest.json"
        )

    file_hashes = {}
    for name in filenames:
        path = data_dir / name
        if path.exists():
            file_hashes[name] = _sha256_file(path)

    return {
        "version": version,
        "algorithm": "sha256",
        "files": file_hashes,
    }


def write_manifest(
    manifest: dict,
    manifest_path: Path = _MANIFEST_PATH,
) -> None:
    """Write a manifest dict to disk."""
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
