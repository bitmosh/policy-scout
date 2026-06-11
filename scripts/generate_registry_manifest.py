#!/usr/bin/env python
"""Generate registry_manifest.json for Policy Scout data files.

Run after any data file change:
    python scripts/generate_registry_manifest.py

The generated file is committed to the repository. CI verifies it matches
the actual data files on every build.
"""

import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from policy_scout.integrity.registry_manifest import (
    generate_manifest,
    write_manifest,
    _DATA_DIR,
    _MANIFEST_PATH,
)


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else "dev"

    manifest = generate_manifest(data_dir=_DATA_DIR, version=version)

    write_manifest(manifest, _MANIFEST_PATH)

    print(f"Manifest generated: {_MANIFEST_PATH}")
    print(f"  Version: {version}")
    print(f"  Algorithm: sha256")
    print(f"  Files ({len(manifest['files'])}):")
    for name, digest in manifest["files"].items():
        print(f"    {name}: {digest[:16]}...")


if __name__ == "__main__":
    main()
